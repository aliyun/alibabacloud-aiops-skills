#!/usr/bin/env python3
"""
deploy_toolkit.py - deploy-to-ecs 统一部署工具

子命令:
    check       环境预检（aliyun CLI版本 + appmanager-cli版本 + 凭证）
    price       部署前询价（调用 appmanager price，输出费用摘要）
    deploy      分组冲突自动处理 + 执行部署
    verify      部署后日志验证（云助手优先 → deployCommandOutput 回退）

用法:
    python3 deploy_toolkit.py check
    python3 deploy_toolkit.py price   [--config PATH]
    python3 deploy_toolkit.py deploy  [--type T --name N --group G --region R]
    python3 deploy_toolkit.py verify  [--type T --name N --group G --region R] [--wait S]

退出码:
    check:      0=通过, 1=有问题
    price:      0=询价成功, 1=失败
    deploy:     0=部署提交成功, 1=失败
    verify:     0=运行中, 1=失败, 2=不确定
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time


# ============================================================
# Shared utilities
# ============================================================

def run_cmd(cmd, capture=True, stream=False, env_override=None, timeout=None):
    """Run a shell command, return (exit_code, stdout, stderr)."""
    env = env_override or os.environ.copy()
    if stream:
        tmp = os.path.join("/tmp", f"deploy_toolkit_{os.getpid()}.log")
        with open(tmp, "w") as f:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
            output_lines = []
            for line in proc.stdout:
                sys.stdout.write(line)
                sys.stdout.flush()
                output_lines.append(line)
            proc.wait()
        stdout = "".join(output_lines)
        return proc.returncode, stdout, ""
    else:
        try:
            proc = subprocess.run(cmd, capture_output=capture, text=True, env=env, timeout=timeout)
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "Command timed out"
        except FileNotFoundError:
            return 127, "", f"Command not found: {cmd[0]}"


def auto_read_config(config_path=".appmanager/config.yaml"):
    """Read metadata from .appmanager/config.yaml, return dict with type/name/groupName/regionId."""
    result = {"type": "", "name": "", "groupName": "", "regionId": ""}
    if not os.path.isfile(config_path):
        return result
    try:
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        meta = config.get("metadata", {})
        result["type"] = meta.get("type", "")
        result["name"] = meta.get("name", "")
        result["groupName"] = meta.get("groupName", "")
        result["regionId"] = meta.get("regionId", "")
    except Exception:
        pass
    return result


def _validate_param(value, name, pattern, max_len):
    """Validate a deployment param against an allow-list regex and length limit.

    Although subprocess list-passing already prevents shell injection, we still
    enforce strict format checks for defense-in-depth and to surface bad config
    early (e.g. a typo in regionId would otherwise reach the API).
    """
    if not value:
        return
    if len(value) > max_len:
        print(f"❌ Invalid --{name}: length {len(value)} > {max_len}")
        sys.exit(1)
    if not re.fullmatch(pattern, value):
        print(f"❌ Invalid --{name} format: '{value}' (allowed pattern: {pattern})")
        sys.exit(1)


def fill_params(args, config_path=".appmanager/config.yaml"):
    """Fill missing --type/--name/--group/--region from config.yaml."""
    needs_fill = (not args.type or not args.name or not args.group or not args.region)
    if needs_fill:
        print(f"ℹ️  Auto-reading params from {config_path} ...")
        cfg = auto_read_config(config_path)
        if not args.type:
            args.type = cfg["type"]
        if not args.name:
            args.name = cfg["name"]
        if not args.group:
            args.group = cfg["groupName"]
        if not args.region:
            args.region = cfg["regionId"]
    if not args.type or not args.name or not args.group or not args.region:
        print("❌ Missing required params. Provide --type/--name/--group/--region or run from a dir with .appmanager/config.yaml")
        sys.exit(1)

    # Format/length validation (defense-in-depth even though we use subprocess list mode)
    _validate_param(args.type,   "type",   r"agent|app",                   8)
    _validate_param(args.name,   "name",   r"[A-Za-z][A-Za-z0-9_-]{0,63}", 64)
    _validate_param(args.group,  "group",  r"[A-Za-z][A-Za-z0-9_-]{0,63}", 64)
    _validate_param(args.region, "region", r"[a-z]{2,8}-[a-z]+(-\d+)?",    32)
    return args


def version_gte(ver, required):
    """Check if version string ver >= required (semver-like)."""
    def parse(v):
        return [int(x) for x in re.findall(r'\d+', v)]
    return parse(ver) >= parse(required)


# ============================================================
# Subcommand: check
# ============================================================

def cmd_check(_args):
    """Environment check: aliyun CLI version, appmanager-cli version, credentials."""
    print("=== Environment Check ===")
    errors = 0

    # 1. Check aliyun CLI
    code, stdout, _ = run_cmd(["aliyun", "version"])
    cli_ver = ""
    if code == 0 and stdout:
        m = re.search(r'(\d+\.\d+\.\d+)', stdout)
        if m:
            cli_ver = m.group(1)
    if not cli_ver:
        print("❌ aliyun CLI: NOT INSTALLED")
        # NOTE: We DO NOT execute install commands automatically — installing software
        # to system directories (/usr/local/bin) requires elevated privileges and should
        # only run after explicit user consent. We print the suggested command so the
        # user/Agent can review and run it manually.
        print("   → AGENT: DO NOT stop. ASK the user: '检测到未安装 aliyun CLI，是否同意自动安装到 /usr/local/bin（需要 sudo）？' On 'yes', run the command below; on 'no', stop with that reason.")
        print("   → 推荐安装命令（写入 /usr/local/bin 需要 sudo，请人工确认后执行）：")
        print("     curl --connect-timeout 30 --max-time 120 -fsSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | sudo tar xz -C /usr/local/bin/")
        print("     # 或参考 references/init-and-credentials.md 选择对应平台的命令")
        errors += 1
    elif version_gte(cli_ver, "3.3.14"):
        print(f"✅ aliyun CLI: {cli_ver} (≥3.3.14)")
    else:
        print(f"❌ aliyun CLI: {cli_ver} (requires ≥3.3.14)")
        print(f"   → AGENT: DO NOT stop. ASK the user: '当前 aliyun CLI 版本 {cli_ver} 低于 appmanager 所需的 ≥3.3.14，是否同意升级（覆盖安装到 /usr/local/bin，需要 sudo）？' On 'yes', run the install command below to upgrade in-place; on 'no', stop with that reason.")
        print("   → 推荐升级命令（与全新安装相同，将覆盖旧版本，请人工确认后执行）：")
        print("     curl --connect-timeout 30 --max-time 120 -fsSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | sudo tar xz -C /usr/local/bin/")
        print("     # 或参考 references/init-and-credentials.md 选择对应平台的命令")
        errors += 1

    # 2. Check appmanager-cli
    venv_dir = os.path.expanduser("~/.aliyun/appmanager-venv")
    required_app = "1.0.9"
    if os.path.isdir(venv_dir):
        venv_python = os.path.join(venv_dir, "bin", "python")
        code, stdout, _ = run_cmd([venv_python, "-c",
            "from importlib.metadata import version; print(version('appmanager-cli'))"])
        app_ver = stdout.strip() if code == 0 else ""
        if not app_ver:
            print(f"❌ appmanager-cli: BROKEN venv (fix: rm -rf {venv_dir})")
            print(f"   → AGENT: DO NOT stop. ASK the user '检测到 appmanager-cli 虚拟环境损坏，是否同意删除 {venv_dir} 并由 aliyun CLI 自动重建？' On 'yes' run: rm -rf {venv_dir}")
            errors += 1
        elif version_gte(app_ver, required_app):
            print(f"✅ appmanager-cli: {app_ver} (≥{required_app})")
        else:
            print(f"❌ appmanager-cli: {app_ver} (requires ≥{required_app}, fix: rm -rf {venv_dir})")
            print(f"   → AGENT: DO NOT stop. ASK the user '当前 appmanager-cli {app_ver} 低于所需 ≥{required_app}，是否同意删除 {venv_dir} 让 aliyun CLI 自动重建到最新版？' On 'yes' run: rm -rf {venv_dir}")
            errors += 1
    else:
        print("⚠️  appmanager-cli: not installed yet (will auto-install on first aliyun appmanager run)")

    # 3. Check credentials
    config_file = os.path.expanduser("~/.aliyun/config.json")
    if os.path.isfile(config_file):
        try:
            with open(config_file) as f:
                d = json.load(f)
            current = d.get("current", "")
            profiles = d.get("profiles", [])
            p = next((x for x in profiles if x.get("name") == current), {})
            ak = p.get("access_key_id", "")
            region = p.get("region_id", "")
            if ak:
                # Mask AK: show only the prefix tag (4 chars) + last 4 chars, redact middle.
                # This avoids leaking enough characters for reconnaissance while still
                # letting the user identify which key is in use.
                if len(ak) >= 12:
                    masked = f"{ak[:4]}***{ak[-4:]}"
                else:
                    masked = "***"
                print(f"✅ credentials: profile={current} region={region} ak={masked}")
            else:
                print("❌ credentials: config.json exists but no valid AK found")
                print("   → SA-2.12: configure credentials via the default credential chain (do NOT paste AK/SK to the agent).")
                print("     A) ECS RAM Role: aliyun configure --mode EcsRamRole --ram-role-name <role>")
                print("     B) Env vars (in your shell profile): export ALIBABA_CLOUD_ACCESS_KEY_ID=... ; export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...")
                print("     C) Interactive: aliyun configure --mode AK   (enter values at the terminal prompt)")
                errors += 1
        except Exception:
            print("❌ credentials: failed to parse config.json")
            errors += 1
    else:
        print("❌ credentials: ~/.aliyun/config.json not found")
        print("   → SA-2.12: configure credentials via the default credential chain (do NOT paste AK/SK to the agent).")
        print("     A) ECS RAM Role: aliyun configure --mode EcsRamRole --ram-role-name <role>")
        print("     B) Env vars (in your shell profile): export ALIBABA_CLOUD_ACCESS_KEY_ID=... ; export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...")
        print("     C) Interactive: aliyun configure --mode AK   (enter values at the terminal prompt)")
        errors += 1

    print("=== Environment Check Done ===")
    if errors > 0:
        print(f"\n⚠️  {errors} issue(s) found. Please fix before deploying.")
        sys.exit(1)
    else:
        print("\n✅ All checks passed. Ready to deploy.")
        sys.exit(0)


# ============================================================
# Subcommand: price
# ============================================================

def cmd_price(args):
    """Query deployment price estimation and output summary."""
    config_path = args.config
    if not os.path.isfile(config_path):
        print(f"❌ 配置文件不存在: {config_path}")
        print("请先运行 'aliyun appmanager init' 生成配置文件。")
        sys.exit(1)

    cmd = ["aliyun", "appmanager", "price",
           "--config", os.path.abspath(config_path),
           "--target", args.target.upper(),
           "--output", "json"]
    if args.region:
        cmd += ["--region", args.region]

    # Don't pass expired STS tokens
    env = {k: v for k, v in os.environ.items() if k != "ALIBABA_CLOUD_SECURITY_TOKEN"}

    print("🔍 正在询价，请稍候...\n")
    try:
        code, stdout, stderr = run_cmd(cmd, env_override=env, timeout=60)
    except Exception as e:
        print(f"❌ 询价失败: {e}")
        sys.exit(1)

    # Parse NDJSON for last result/error
    last_event = None
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            if ev.get("type") in ("result", "error"):
                last_event = ev
        except json.JSONDecodeError:
            continue

    if code != 0 or not last_event or last_event.get("type") == "error":
        msg = (last_event or {}).get("error") or stderr or "unknown error"
        print(f"❌ 询价失败: {msg}")
        print("\n可能的原因:")
        print("  1. 阿里云凭证无效或过期")
        print("  2. config.yaml 参数不完整")
        print("  3. 网络连接问题")
        print("\n建议: 检查凭证后重试")
        sys.exit(1)

    result = last_event
    # Build summary
    lines = [
        "=" * 50, "📊 部署费用预估", "=" * 50,
        f"区域          : {result['region_id']}",
        f"部署目标      : {result['deploy_target']}",
        f"服务ID        : {result['service_id']}",
        f"模板名称      : {result['template_name']}",
        "-" * 50,
    ]
    total_hourly = 0.0
    for res in result["resources"]:
        lines.append(f"\n📦 资源: {res['name']}")
        lines.append(f"   类型        : {res['type']}")
        lines.append(f"   计费方式    : {res['charge_type']} ({res['price_unit']})")
        lines.append(f"   数量        : {res['quantity']}")
        lines.append("")
        for item in res["items"]:
            lines.append(f"   ├─ {item['resource']:<12} ¥{item['trade_amount']:>10.5f}/h  ({item['attributes']})")
        lines.append(f"   └─ 小计       : ¥{res['total_trade']:.5f}/h")
        if res["price_unit"] == "/Hour":
            total_hourly += res["total_trade"]
        for assoc in res.get("association", []):
            lines.append(
                f"   ⚡ 关联计费 : {assoc['charge_type']} ¥{assoc['trade_amount']}{assoc['currency']}{assoc['price_unit']} "
                f"（按实际使用量结算，不计入合计）")
    lines.append("")
    lines.append("=" * 50)
    if total_hourly > 0:
        monthly = total_hourly * 24 * 30
        lines.append(f"💰 合计: ¥{total_hourly:.5f}/小时")
        lines.append(f"   月度预估: ¥{monthly:.2f}/月（按 30 天 × 24 小时计算）")
    else:
        lines.append("💰 合计: 免费（或无按量计费资源）")
    lines.append("=" * 50)
    lines.append("\n⚠️  以上为预估价格，实际费用以账单为准。")
    lines.append("⚠️  关联计费项（如按流量计费的网络带宽）按实际使用量结算。")
    lines.append(f"\n📋 RequestID: {result.get('request_id', 'N/A')}\n")
    print("\n".join(lines))

    print("=== AGENT_CONFIRM_REQUIRED ===")
    print("Agent 需向用户展示以上价格信息并询问：是否确认以上价格并继续部署？")
    sys.exit(0)


# ============================================================
# Subcommand: deploy
# ============================================================

def cmd_deploy(args):
    """Pre-deploy group check + execute deployment.

    Idempotency note (RECOMMEND §1.4.2):
        `aliyun appmanager deploy` does not currently expose a ClientToken parameter,
        so true server-side idempotency is not available at the CLI layer. This
        function instead implements a check-then-act pattern:
          1. Status query (`aliyun appmanager <type> status`) determines whether a
             group already exists with active ECS — in that case `--overwrite`
             updates the existing instance instead of creating a new one.
          2. If a previous failed deploy left a group with NO active ECS
             (NO_ECS state), a suffixed group name is allocated to avoid
             accidental resource duplication on retry.
        Agents that retry on transient errors (timeout, network) should call this
        subcommand again — the status check makes the operation safe to repeat.
    """
    args = fill_params(args)
    app_type, app_name, group_name, region = args.type, args.name, args.group, args.region

    print("=== Pre-deploy Group Check + Deploy ===")
    print(f"Type: {app_type} | Name: {app_name} | Group: {group_name} | Region: {region}\n")

    # Step 1: Check group status
    print("--- Step 1: Checking group status ---")
    code, stdout, _ = run_cmd(["aliyun", "appmanager", app_type, "status",
                               "--name", app_name, "--group_name", group_name, "--output", "json"])
    print(stdout)

    # Determine group state
    group_state = "UNKNOWN"
    if "EntityNotExists" in stdout:
        group_state = "NOT_EXISTS"
    else:
        try:
            data = json.loads(stdout)
            d = data.get("data", data)
            ids = d.get("ecs_instance_ids", [])
            group_state = "HAS_ECS" if ids and len(ids) > 0 else "NO_ECS"
        except Exception:
            if "EntityNotExists" in stdout:
                group_state = "NOT_EXISTS"

    print(f"Group state: {group_state}\n")

    # Step 2: Handle group state
    final_group = group_name
    if group_state == "NOT_EXISTS":
        print("✅ Group does not exist — will be created during deploy.")
    elif group_state == "HAS_ECS":
        print("✅ Group exists with active ECS — deploy will update existing instance.")
    elif group_state == "NO_ECS":
        print("⚠️  Group exists but has NO active ECS instance (likely a failed previous deployment).")
        print("   Auto-resolving: appending suffix to create a new group...\n")
        for suffix in range(2, 11):
            new_group = f"{group_name}-{suffix}"
            c, out, _ = run_cmd(["aliyun", "appmanager", app_type, "status",
                                 "--name", app_name, "--group_name", new_group, "--output", "json"])
            if "EntityNotExists" in out:
                final_group = new_group
                break
        else:
            print("❌ Too many conflicting groups (tried up to suffix -10). Please clean up manually.")
            sys.exit(1)
        print(f"   New group name: {final_group}")
        # Update config.yaml
        config_file = ".appmanager/config.yaml"
        if os.path.isfile(config_file):
            try:
                import yaml
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                config.setdefault("metadata", {})["groupName"] = final_group
                with open(config_file, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
                print(f"   Updated .appmanager/config.yaml → groupName: {final_group}")
            except Exception:
                print("   ⚠️  Failed to update config.yaml — Agent must update groupName manually.")
        print()
    else:
        print("⚠️  Could not determine group state (status check may have failed).")
        print("   Proceeding with deploy anyway...")

    # Step 3: Execute deploy
    print("--- Step 3: Deploying ---")
    print(f"Command: aliyun appmanager {app_type} deploy --overwrite --output json\n")
    deploy_exit, deploy_output, _ = run_cmd(
        ["aliyun", "appmanager", app_type, "deploy", "--overwrite", "--output", "json"],
        stream=True)
    print()

    # Step 4: Post-deploy summary
    if deploy_exit == 0:
        print("--- Deploy command completed (exit 0) ---")
        if final_group != group_name:
            print(f"""
===========================================
⚠️  分组冲突自动处理说明：
   原分组 '{group_name}' 已存在但没有关联的 ECS 实例
   （可能是之前部署失败遗留的）。
   已自动创建新分组 '{final_group}' 完成部署。

   旧分组处理建议：
   - 如不再需要，可删除：
     aliyun appmanager {app_type} delete --name {app_name} --group_name {group_name}
   - 如需复用已有 ECS，可在 config.yaml 中设置
     common.deployment.instanceId 将其导入旧分组
===========================================""")
        print(f"\n✅ Deploy submitted. Use 'deploy_toolkit.py verify' to check if app is actually running.")
        sys.exit(0)
    else:
        print(f"--- Deploy command FAILED (exit {deploy_exit}) ---")
        # Extract error status
        deploy_status = ""
        script_error = ""
        for line in deploy_output.splitlines():
            line = line.strip()
            try:
                d = json.loads(line)
                if d.get("type") == "error":
                    deploy_status = d.get("error", "")
                for key in ("data", "execution_log"):
                    sub = d.get(key, {})
                    if isinstance(sub, dict):
                        outputs = sub.get("Outputs", {})
                        if isinstance(outputs, dict):
                            dco = outputs.get("deployCommandOutput")
                            if dco and dco not in ("null", None, [None]):
                                script_error = dco if isinstance(dco, str) else str(dco)
            except (json.JSONDecodeError, AttributeError):
                pass

        is_cancelled = "ReleaseCancelled" in deploy_status
        is_failed = "ReleaseFailed" in deploy_status
        is_balance = "NotEnoughBalance" in deploy_output or "NotEnoughBalance" in deploy_status

        if is_balance:
            print("\n❌ 部署失败：账户余额不足")
            print("   ⚠️  错误码: InvalidAccountStatus.NotEnoughBalance")
            print("   ⚠️  创建按量付费 ECS 实例要求账户余额 ≥ 100 元。")
            print("   ⚠️  请前往阿里云控制台充值后重试：https://usercenter2.aliyun.com/finance/fund-management")
            print("   提示：如果使用已有 ECS 实例部署则不受此限制。")
        elif is_cancelled or is_failed:
            status_label = "ReleaseCancelled" if is_cancelled else "ReleaseFailed"
            print(f"\n❌ 部署失败（状态: {status_label}）")
            print('   ⚠️  含义：start 脚本在 ECS 上执行失败或超时，系统强制终止了发布。')
            print('   ⚠️  这不是"有正在进行的部署"，不是"等一等再重试就好"。')
            print("   ⚠️  唯一正确的下一步：立即运行 deploy_toolkit.py verify 查看实际报错日志。")
        elif deploy_status:
            print(f"\n❌ Deploy error: {deploy_status}")

        if script_error:
            print(f"\n=== 脚本执行错误（deployCommandOutput）===\n{script_error}")
            print("===========================================\n")
            print("👆 以上是 ECS 上 start 脚本的实际报错。请根据上述错误修复 .appmanager/config.yaml 中的 start 脚本后重新部署。")
        else:
            print("\n❌ 未能从部署输出中提取到脚本日志。")
            print("   请运行 deploy_toolkit.py verify 查询 ECS 上的实际部署日志以定位失败原因。")
        sys.exit(1)


# ============================================================
# Subcommand: verify
# ============================================================

def cmd_verify(args):
    """Post-deploy verification: fetch logs and present for Agent analysis."""
    args = fill_params(args)
    app_type, app_name, group_name, region = args.type, args.name, args.group, args.region
    wait_seconds = args.wait

    print("=== Post-deploy Verification ===")
    print(f"Type: {app_type} | Name: {app_name} | Group: {group_name} | Region: {region}")
    print(f"Wait: {wait_seconds}s\n")

    # Step 1: Get deployment status
    print("--- Step 1: Querying deployment status ---")
    code, stdout, _ = run_cmd(["aliyun", "appmanager", app_type, "status",
                               "--name", app_name, "--group_name", group_name, "--output", "json"])
    print(stdout)

    # Extract ECS instance ID
    instance_id = ""
    deploy_cmd_output = ""
    try:
        data = json.loads(stdout)
        d = data.get("data", data)
        ids = d.get("ecs_instance_ids", [])
        if ids:
            instance_id = ids[0]
        # Extract deployCommandOutput for fallback
        log = d.get("execution_log", {})
        outputs_str = log.get("Outputs", "") or log.get("LastTriggerOutputs", "")
        if isinstance(outputs_str, str) and outputs_str:
            outputs = json.loads(outputs_str)
        elif isinstance(outputs_str, dict):
            outputs = outputs_str
        else:
            outputs = {}
        dco = outputs.get("deployCommandOutput")
        if isinstance(dco, list):
            dco = dco[0] if dco else None
        if dco and dco != "null":
            deploy_cmd_output = dco
    except Exception:
        pass

    print(f"ECS Instance: {instance_id or '(not found)'}\n")

    # Resolve public IP
    ecs_public_ip = ""
    if instance_id:
        code, stdout, _ = run_cmd(["aliyun", "ecs", "DescribeInstances",
                                   "--RegionId", region,
                                   "--InstanceIds", json.dumps([instance_id])])
        if code == 0:
            try:
                d = json.loads(stdout)
                inst = d["Instances"]["Instance"][0]
                ips = inst.get("PublicIpAddress", {}).get("IpAddress", [])
                if ips:
                    ecs_public_ip = ips[0]
            except Exception:
                pass
        if ecs_public_ip:
            print(f"ECS Public IP: {ecs_public_ip}\n")

    # Step 2: Wait
    print(f"--- Step 2: Waiting {wait_seconds}s for application to start... ---")
    time.sleep(wait_seconds)
    print("Done.\n")

    # Step 3: Try Cloud Assistant (Path A)
    app_log = ""
    log_source = ""

    if instance_id:
        print("--- Step 3: Trying Cloud Assistant to fetch /root/app.log ---")
        code, stdout, _ = run_cmd(["aliyun", "ecs", "RunCommand",
                                   "--RegionId", region,
                                   "--Type", "RunShellScript",
                                   "--CommandContent", "cat /root/app.log 2>/dev/null || echo 'LOG_FILE_NOT_FOUND'",
                                   "--InstanceId.1", instance_id,
                                   "--Timeout", "30"])
        invoke_id = ""
        if code == 0:
            try:
                invoke_id = json.loads(stdout).get("InvokeId", "")
            except Exception:
                pass

        if not invoke_id:
            print(f"   云助手调用原始响应：{stdout}\n")
            # Cloud Assistant failed — show fallback
            ssh_target = ecs_public_ip or "<ECS_IP>"
            print("⚠️  无法通过云助手获取 ECS 应用日志")
            print("   原因：当前 RAM 账号缺少 ecs:RunCommand 权限（云助手调用被拒绝）")
            print(f"\n   ▶ 替代方案：手动 SSH 查看日志")
            print(f"     ssh root@{ssh_target} 'tail -100 /root/app.log'\n")

            # HTTP port probe fallback
            cfg = auto_read_config()
            try:
                import yaml
                with open(".appmanager/config.yaml") as f:
                    c = yaml.safe_load(f)
                app_port = str(c.get("common", {}).get("deployment", {}).get("port", ""))
            except Exception:
                app_port = ""
            if ecs_public_ip and app_port:
                print(f"   ▶ 尝试 HTTP 端口探测 ({ecs_public_ip}:{app_port})...")
                hcode, hout, _ = run_cmd(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                          "--connect-timeout", "8", "--max-time", "10",
                                          f"http://{ecs_public_ip}:{app_port}/"])
                http_code = hout.strip() if hcode == 0 else "000"
                print(f"   HTTP 响应码: {http_code}")
                if http_code not in ("000", "502", "503"):
                    app_log = f"HTTP_CHECK_PASSED: port {app_port} responded with HTTP {http_code}"
                    log_source = "http_check"
                    print(f"   ✅ 端口 {app_port} 已响应，应用正在运行！")
                else:
                    print(f"   ⚠️  端口 {app_port} 暂未响应（HTTP {http_code}）")
                    print("      可能原因：① 应用仍在安装/构建中  ② 安全组未开放端口  ③ 应用启动失败")
                print()
        else:
            print(f"InvokeId: {invoke_id} — waiting 10s for execution...")
            time.sleep(10)
            code2, stdout2, _ = run_cmd(["aliyun", "ecs", "DescribeInvocationResults",
                                         "--RegionId", region, "--InvokeId", invoke_id])
            fetched_log = ""
            if code2 == 0:
                try:
                    data2 = json.loads(stdout2)
                    results = data2.get("Invocation", {}).get("InvocationResults", {}).get("InvocationResult", [])
                    if results:
                        output = results[0].get("Output", "")
                        if output:
                            fetched_log = base64.b64decode(output).decode("utf-8", errors="replace")
                except Exception:
                    pass
            if fetched_log and fetched_log.strip() != "LOG_FILE_NOT_FOUND":
                app_log = fetched_log
                log_source = "cloud_assistant"
                print("✅ Cloud Assistant: Successfully fetched /root/app.log\n")
            else:
                print("⚠️  Cloud Assistant: /root/app.log not found or empty on ECS.")
                print("   应用可能尚未启动完成，或日志路径不是 /root/app.log。\n")
    else:
        print("--- Step 3: 未获取到 ECS 实例 ID，无法使用云助手 ---")
        print("   将使用 deployCommandOutput 中的有限日志进行分析。\n")

    # Step 4: Fallback to deployCommandOutput (Path B)
    if not app_log:
        if deploy_cmd_output:
            app_log = deploy_cmd_output
            log_source = "deployCommandOutput"
            print("--- Step 4: Using deployCommandOutput as log source ---\n")
        else:
            print("--- Step 4: deployCommandOutput is also NULL/empty ---")
            print("   Neither Cloud Assistant nor deployCommandOutput returned logs.\n")
            log_source = "none"

    # Step 5: Display log
    if app_log and log_source != "none":
        print(f"--- Application Log (source: {log_source}) ---")
        print(app_log)
        print()

    # Step 6: AGENT_ANALYZE_REQUIRED
    ssh_hint = ecs_public_ip or "<ECS_IP>"
    if not app_log or log_source == "none":
        print("\n=== AGENT_ANALYZE_REQUIRED ===")
        print("log_source: none")
        print("No application log was retrieved.")
        if instance_id:
            print(f"manual_check: ssh root@{ssh_hint} 'tail -200 /root/app.log'")
        print("=== END_AGENT_ANALYZE_REQUIRED ===")
        sys.exit(0)

    print("\n=== AGENT_ANALYZE_REQUIRED ===")
    print(f"log_source: {log_source}")
    print(f"ecs_instance: {instance_id or 'unknown'}")
    print(f"ecs_public_ip: {ecs_public_ip or 'unknown'}")
    print()
    print("Instructions for Agent:")
    print(f"  Read the full application log printed above (source: {log_source}).")
    print("  Analyze it directly — do NOT rely on keyword matching.")
    print("  Determine:")
    print("    1. Did the application start successfully?")
    print("    2. Are there errors, crashes, missing config, or startup failures?")
    print("    3. If failed: what is the root cause and how should config.yaml be fixed?")
    print("    4. If succeeded: what is the access method (URL / SSH / background service)?")
    print("  Then take action:")
    print("    - App running → proceed to output final results")
    print("    - App failed  → fix common.scripts.start in config.yaml, re-deploy, re-verify")
    print("    - Needs setup → inform user of required manual steps (e.g. openclaw setup)")
    print("=== END_AGENT_ANALYZE_REQUIRED ===")
    sys.exit(0)


# ============================================================
# Main: argparse dispatcher
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        prog="deploy_toolkit.py",
        description="deploy-to-ecs unified deployment toolkit")
    sub = parser.add_subparsers(dest="command", help="Available commands")
    sub.required = True

    # check
    sub.add_parser("check", help="Environment pre-check (CLI + credentials)")

    # price
    p_price = sub.add_parser("price", help="Pre-deploy price estimation")
    p_price.add_argument("--config", default=".appmanager/config.yaml", help="Config file path")
    p_price.add_argument("--target", default="ECS", help="Deploy target (default: ECS)")
    p_price.add_argument("--region", default=None, help="Override region")

    # deploy
    p_deploy = sub.add_parser("deploy", help="Group conflict check + deploy")
    p_deploy.add_argument("--type", default="", help="Project type (agent|app)")
    p_deploy.add_argument("--name", default="", help="App name")
    p_deploy.add_argument("--group", default="", help="Group name")
    p_deploy.add_argument("--region", default="", help="Region ID")

    # verify
    p_verify = sub.add_parser("verify", help="Post-deploy log verification")
    p_verify.add_argument("--type", default="", help="Project type (agent|app)")
    p_verify.add_argument("--name", default="", help="App name")
    p_verify.add_argument("--group", default="", help="Group name")
    p_verify.add_argument("--region", default="", help="Region ID")
    p_verify.add_argument("--wait", type=int, default=3, help="Wait seconds before checking (default: 3)")

    args = parser.parse_args()

    dispatch = {
        "check": cmd_check,
        "price": cmd_price,
        "deploy": cmd_deploy,
        "verify": cmd_verify,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
