#!/usr/bin/env python3
"""
deploy_toolkit.py - Unified deploy-to-ECS toolkit.

Subcommands:
    check       Environment pre-check (aliyun CLI version + appmanager-cli version + credentials)
    price       Pre-deploy price query (calls `appmanager price`, prints a cost summary)
    deploy      Group-conflict auto-resolution + deployment execution
    verify      Post-deploy log verification (Cloud Assistant first, fallback to deployCommandOutput)

Usage:
    python3 deploy_toolkit.py check
    python3 deploy_toolkit.py price   [--config PATH]
    python3 deploy_toolkit.py deploy  [--type T --name N --group G --region R]
    python3 deploy_toolkit.py verify  [--type T --name N --group G --region R] [--wait S]

Exit codes:
    check:      0 = pass, 1 = issues found
    price:      0 = price query succeeded, 1 = failed
    deploy:     0 = deploy submitted, 1 = failed
    verify:     0 = running, 1 = failed, 2 = inconclusive

Dependencies:
    PyYAML==6.0.2  (declared in scripts/requirements.txt; install with
                    `pip install -r scripts/requirements.txt`,
                    or rely on the system python3-yaml package.)
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

def _detect_aliyun_paths():
    """Return list of all `aliyun` binaries on PATH (in PATH order).

    Used to surface multi-binary conflicts (e.g. brew /opt/homebrew/bin/aliyun
    shadowing a fresh /usr/local/bin/aliyun on macOS Apple Silicon, which is
    the typical reason an "upgrade succeeded" appears to revert in the next
    shell session).
    """
    paths = []
    for d in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(d, "aliyun")
        if os.path.isfile(cand) and os.access(cand, os.X_OK) and cand not in paths:
            paths.append(cand)
    return paths


def _arch_install_cmd(target_dir):
    """Build the platform/arch-specific aliyun CLI install command.

    target_dir: where to extract the binary (e.g. /usr/local/bin or ~/bin).
    Returns (cmd_string, needs_sudo).
    """
    plat = sys.platform
    machine = os.uname().machine.lower() if hasattr(os, "uname") else ""
    if plat == "darwin":
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        url = f"https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-macosx-latest-{arch}.tgz"
    else:
        arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
        url = f"https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-linux-latest-{arch}.tgz"
    needs_sudo = target_dir.startswith("/usr/") or target_dir.startswith("/opt/")
    sudo = "sudo " if needs_sudo else ""
    cmd = (f"mkdir -p {target_dir} && "
           f"curl --connect-timeout 30 --max-time 120 -fsSL {url} | {sudo}tar xz -C {target_dir}/")
    return cmd, needs_sudo


def _has_brew_aliyun():
    """Detect whether Homebrew manages an `aliyun` formula on this host."""
    if sys.platform != "darwin":
        return False
    code, out, _ = run_cmd(["brew", "list", "--formula"])
    if code != 0:
        return False
    return any(line.strip() in ("aliyun-cli", "aliyun") for line in out.splitlines())


def _print_install_guidance(action_label, current_ver=""):
    """Print install/upgrade guidance with PATH-conflict awareness.

    action_label: 'install' or 'upgrade', used in the prompt to the user.
    """
    paths = _detect_aliyun_paths()
    brew_managed = _has_brew_aliyun()

    # Surface multi-binary conflict explicitly — this is the #1 reason
    # "upgrade looked fine but next session reverts to the old version".
    if len(paths) > 1:
        print(f"   ⚠️  Multiple aliyun binaries detected on PATH (the earlier one wins):")
        for p in paths:
            print(f"        - {p}")
        print(f"   → Writing a new version to /usr/local/bin alone may be shadowed by an older binary in a PATH directory listed earlier (typical case: on macOS Apple Silicon, /opt/homebrew/bin precedes /usr/local/bin).")

    if brew_managed:
        print(f"   → Homebrew is managing aliyun-cli; prefer `brew {action_label}` to avoid PATH-precedence shadowing:")
        print(f"     brew upgrade aliyun-cli   # or: brew install aliyun-cli")
        print(f"   → AGENT: ASK the user 'The current aliyun CLI {current_ver} is managed by Homebrew. Do you agree to run `brew upgrade aliyun-cli`?' After consent, run the command and re-run check.")
        return

    # Default: tarball install. Prefer /usr/local/bin (with sudo); fall back to ~/bin.
    sys_cmd, _ = _arch_install_cmd("/usr/local/bin")
    user_dir = os.path.expanduser("~/bin")
    user_cmd, _ = _arch_install_cmd(user_dir)

    print(f"   → AGENT: DO NOT stop. ASK the user: 'Do you agree to {action_label} aliyun CLI under /usr/local/bin (sudo required)? Without sudo, install under ~/bin instead (PATH must be appended).' After consent, run the corresponding command below, then re-run check.")
    print(f"   → Recommended {action_label} command (system dir, requires sudo):")
    print(f"     {sys_cmd}")
    print(f"   → Sudo-free fallback (user dir, no privilege escalation):")
    print(f"     {user_cmd}")
    print(f"     # Also append ~/bin to PATH; otherwise the next shell session reverts to the old version:")
    print(f"     echo 'export PATH=\"$HOME/bin:$PATH\"' >> ~/.zshrc   # bash users edit ~/.bashrc")
    print(f"     hash -r   # or under zsh: rehash; makes the current session pick up the new version immediately")
    print(f"   → After install/upgrade, you MUST run `which -a aliyun` and `aliyun version` to double-check the effective path and version, then re-run check.")


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

    aliyun_paths = _detect_aliyun_paths()
    active_path = aliyun_paths[0] if aliyun_paths else ""

    if not cli_ver:
        print("❌ aliyun CLI: NOT INSTALLED")
        # NOTE: We DO NOT execute install commands automatically — installing software
        # to system directories (/usr/local/bin) requires elevated privileges and should
        # only run after explicit user consent. We print the suggested command so the
        # user/Agent can review and run it manually.
        _print_install_guidance("install")
        errors += 1
    elif version_gte(cli_ver, "3.3.19"):
        print(f"✅ aliyun CLI: {cli_ver} (≥3.3.19) [active: {active_path or 'unknown'}]")
        # Even when version is OK, warn on multi-binary PATH conflicts so users
        # can avoid future "upgrade reverts in next session" surprises.
        if len(aliyun_paths) > 1:
            print(f"   ⚠️  Multiple aliyun binaries on PATH (the earlier one wins); watch out for path conflicts on future upgrades:")
            for p in aliyun_paths:
                print(f"        - {p}")
    else:
        print(f"❌ aliyun CLI: {cli_ver} (requires ≥3.3.19) [active: {active_path or 'unknown'}]")
        _print_install_guidance("upgrade", current_ver=cli_ver)
        errors += 1

    # 2. Check appmanager-cli
    venv_dir = os.path.expanduser("~/.aliyun/appmanager-venv")
    required_app = "1.1.1"
    if os.path.isdir(venv_dir):
        venv_python = os.path.join(venv_dir, "bin", "python")
        code, stdout, _ = run_cmd([venv_python, "-c",
            "from importlib.metadata import version; print(version('appmanager-cli'))"])
        app_ver = stdout.strip() if code == 0 else ""
        if not app_ver:
            print(f"❌ appmanager-cli: BROKEN venv (fix: rm -rf {venv_dir})")
            print(f"   → AGENT: DO NOT stop. ASK the user 'The appmanager-cli virtualenv appears broken. Do you agree to remove {venv_dir} and let aliyun CLI rebuild it automatically?' On 'yes' run: rm -rf {venv_dir}")
            errors += 1
        elif version_gte(app_ver, required_app):
            print(f"✅ appmanager-cli: {app_ver} (≥{required_app})")
        else:
            print(f"❌ appmanager-cli: {app_ver} (requires ≥{required_app}, fix: rm -rf {venv_dir})")
            print(f"   → AGENT: DO NOT stop. ASK the user 'The current appmanager-cli {app_ver} is below the required ≥{required_app}. Do you agree to remove {venv_dir} so aliyun CLI can rebuild it to the latest version?' On 'yes' run: rm -rf {venv_dir}")
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
        print(f"❌ Config file not found: {config_path}")
        print("Please run 'aliyun appmanager init' first to generate the config file.")
        sys.exit(1)

    cmd = ["aliyun", "appmanager", "price",
           "--config", os.path.abspath(config_path),
           "--target", args.target.upper(),
           "--output", "json"]
    if args.region:
        cmd += ["--region", args.region]

    # Don't pass expired STS tokens
    env = {k: v for k, v in os.environ.items() if k != "ALIBABA_CLOUD_SECURITY_TOKEN"}

    print("🔍 Querying price, please wait...\n")
    try:
        code, stdout, stderr = run_cmd(cmd, env_override=env, timeout=60)
    except Exception as e:
        print(f"❌ Price query failed: {e}")
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
        print(f"❌ Price query failed: {msg}")
        print("\nPossible causes:")
        print("  1. Alibaba Cloud credentials are invalid or expired")
        print("  2. config.yaml parameters are incomplete")
        print("  3. Network connectivity issue")
        print("\nSuggestion: verify credentials and retry")
        sys.exit(1)

    result = last_event
    # Build summary
    lines = [
        "=" * 50, "📊 Deployment Cost Estimate", "=" * 50,
        f"Region        : {result['region_id']}",
        f"Deploy Target : {result['deploy_target']}",
        f"Service ID    : {result['service_id']}",
        f"Template Name : {result['template_name']}",
    ]
    # Display real instance type spec (CPU/Memory) to avoid Agent guessing from the name
    instance_spec = result.get('instance_type_spec') or {}
    instance_type = result.get('instance_type') or ''
    if instance_type:
        if instance_spec and instance_spec.get('cpu_core_count'):
            cpu = instance_spec['cpu_core_count']
            mem = instance_spec.get('memory_size', 0)
            mem_str = f"{int(mem)}GiB" if float(mem) == int(mem) else f"{mem}GiB"
            lines.append(f"Instance Type : {instance_type}  ({cpu}vCPU {mem_str})")
        else:
            lines.append(f"Instance Type : {instance_type}")
    lines.append("-" * 50)
    total_hourly = 0.0
    for res in result["resources"]:
        lines.append(f"\n📦 Resource: {res['name']}")
        lines.append(f"   Type        : {res['type']}")
        lines.append(f"   Charge Type : {res['charge_type']} ({res['price_unit']})")
        lines.append(f"   Quantity    : {res['quantity']}")
        lines.append("")
        for item in res["items"]:
            lines.append(f"   ├─ {item['resource']:<12} ¥{item['trade_amount']:>10.5f}/h  ({item['attributes']})")
        lines.append(f"   └─ Subtotal   : ¥{res['total_trade']:.5f}/h")
        if res["price_unit"] == "/Hour":
            total_hourly += res["total_trade"]
        for assoc in res.get("association", []):
            lines.append(
                f"   ⚡ Associated charge: {assoc['charge_type']} ¥{assoc['trade_amount']}{assoc['currency']}{assoc['price_unit']} "
                f"(billed by actual usage; not included in the total)")
    lines.append("")
    lines.append("=" * 50)
    if total_hourly > 0:
        monthly = total_hourly * 24 * 30
        lines.append(f"💰 Total: ¥{total_hourly:.5f}/hour")
        lines.append(f"   Monthly estimate: ¥{monthly:.2f}/month (assuming 30 days × 24 hours)")
    else:
        lines.append("💰 Total: free (or no pay-as-you-go resources)")
    lines.append("=" * 50)
    lines.append("\n⚠️  These are estimated prices; the final amount is subject to your bill.")
    lines.append("⚠️  Associated charges (e.g. traffic-based network bandwidth) are billed by actual usage.")
    lines.append("")
    lines.append("📦 OSS extra charges (not covered by `appmanager price`; please relay to the user):")
    lines.append("    - OSS Standard storage: ~¥0.12/GB/month (project code packages are usually KB~MB; small but non-zero)")
    lines.append("    - OSS public-network egress: ~¥0.50/GB (free when ECS and OSS are in the same region via intranet; cross-region traffic is billed)")
    lines.append("    - OSS Put/Get requests: billed per 10K requests; negligible")
    lines.append(f"\n📋 RequestID: {result.get('request_id', 'N/A')}\n")
    print("\n".join(lines))

    # =====================================================================
    # Risk warnings (key confirmation items beyond pricing)
    # =====================================================================
    risks = _collect_deploy_risks(config_path, args.region)
    has_warning = bool(risks["existing_ecs"]) or risks["group_state"] in ("HAS_ECS", "NO_ECS")
    if has_warning:
        print("\n" + "=" * 50)
        print("⚠️  Deployment Risk Warnings (please confirm each item with the user)")
        print("=" * 50)

    # R1: Existing-ECS deployment impact
    if risks["existing_ecs"]:
        print(f"🖥️  [Existing-ECS deployment risk] Will deploy to the user-specified existing ECS instance: {risks['existing_ecs']}")
        print("    - The deploy process will run stop → upload new code → start scripts on this instance")
        print("    - If other services are also running on this ECS, they may be killed by the stop script or have their ports taken by the new process")
        print("    - Files with the same name under deploy directories such as /root/ may be overwritten")
        print("    → AGENT: ASK the user 'Deploy is about to target existing ECS instance {iid}. Other applications running on it may be affected (stopped/port conflict/file overwrite). Do you confirm to proceed?'".format(iid=risks["existing_ecs"]))

    # R2: Existing app-group overwrite
    if risks["group_state"] == "HAS_ECS":
        if risks["existing_ecs"]:
            print("")
        print(f"📁 [App-group overwrite risk] Group '{risks['group_name']}' of app '{risks['app_name']}' already exists and is bound to ECS ({risks['ecs_ids']}).")
        print("    - Default behavior: use --overwrite to deploy onto the existing ECS in the existing group (replace app code, restart processes)")
        print("    - Alternative: create a brand-new group (preserve the existing deployment; spin up another ECS in the new group to run the new version)")
        print("    → AGENT: ASK the user 'App group {grp} already has a deployment. Please choose: A) overwrite the existing group (replace code, restart); B) create a brand-new group (keep the existing deployment intact).'".format(grp=risks["group_name"]))
        print("    → If the user chooses A: run deploy_toolkit.py deploy directly (default overwrite)")
        print("    → If the user chooses B: run deploy_toolkit.py deploy --force-new-group; the script will allocate a new group name and write it back to config.yaml")
    elif risks["group_state"] == "NO_ECS":
        if risks["existing_ecs"]:
            print("")
        print(f"📁 [Failed-leftover group] Group '{risks['group_name']}' exists but has no active ECS (likely a leftover from a previous failed deploy); a suffix will be appended to allocate a new group automatically.")

    if has_warning:
        print("=" * 50)

    print("=== AGENT_CONFIRM_REQUIRED ===")
    print("The Agent MUST ask the user to confirm each of the following based on the information above:")
    print("  1) Price confirmation (including the OSS extra-charge reminder)")
    if risks["existing_ecs"]:
        print(f"  2) Whether to agree to deploy to existing ECS instance {risks['existing_ecs']} (other apps on it may be affected)")
    if risks["group_state"] == "HAS_ECS":
        print(f"  3) App group '{risks['group_name']}' already has a deployment: overwrite (A) or create a brand-new group (B)")
    print("Only invoke deploy_toolkit.py deploy after every item has been confirmed.")
    sys.exit(0)


def _collect_deploy_risks(config_path, region_arg=""):
    """Collect deployment risk signals from config.yaml + appmanager status.

    Returns dict:
      - existing_ecs: instance id string if user-supplied existing ECS (else "")
      - group_state: NOT_EXISTS / HAS_ECS / NO_ECS / UNKNOWN
      - app_name, group_name, app_type, ecs_ids
    """
    risks = {"existing_ecs": "", "group_state": "UNKNOWN",
             "app_name": "", "group_name": "", "app_type": "", "ecs_ids": []}
    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f) or {}
    except Exception:
        return risks

    meta = cfg.get("metadata", {}) or {}
    risks["app_type"] = meta.get("type", "")
    risks["app_name"] = meta.get("name", "")
    risks["group_name"] = meta.get("groupName", "")

    # existing-ECS detection: instanceId field is set when user chose existing ECS
    common = (cfg.get("common", {}) or {}).get("deployment", {}) or {}
    iid = common.get("instanceId") or common.get("instance_id") or ""
    if iid:
        risks["existing_ecs"] = iid

    # status check: only meaningful if all key fields present
    if risks["app_type"] and risks["app_name"] and risks["group_name"]:
        cmd = ["aliyun", "appmanager", risks["app_type"], "status",
               "--name", risks["app_name"],
               "--group_name", risks["group_name"],
               "--output", "json"]
        env = {k: v for k, v in os.environ.items() if k != "ALIBABA_CLOUD_SECURITY_TOKEN"}
        code, stdout, _ = run_cmd(cmd, env_override=env, timeout=30)
        if "EntityNotExists" in stdout:
            risks["group_state"] = "NOT_EXISTS"
        else:
            try:
                d = json.loads(stdout)
                d = d.get("data", d)
                ids = d.get("ecs_instance_ids", []) or []
                risks["ecs_ids"] = ids
                risks["group_state"] = "HAS_ECS" if ids else "NO_ECS"
            except Exception:
                risks["group_state"] = "UNKNOWN"
    return risks


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
    force_new = getattr(args, "force_new_group", False)
    if force_new and group_state in ("HAS_ECS", "NO_ECS"):
        # User explicitly chose option B (brand-new group) at the price-and-risk gate.
        print("ℹ️  --force-new-group specified — allocating a brand-new group (preserving existing deployment).")
        group_state = "NO_ECS"  # Reuse the suffix-allocation branch below

    if group_state == "NOT_EXISTS":
        print("✅ Group does not exist — will be created during deploy.")
    elif group_state == "HAS_ECS":
        print("✅ Group exists with active ECS — deploy will update existing instance.")
    elif group_state == "NO_ECS":
        if force_new:
            print("⚠️  Force-new-group mode: appending suffix to create a brand-new group...\n")
        else:
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
    # appmanager-cli deploy does NOT auto-resolve region from config.yaml or
    # profile; without an explicit --region (and matching env var) it fails
    # with `InvalidParameter: DeployRegionId is invalid`. Pass both for
    # defense-in-depth so the call works across appmanager-cli minor versions.
    deploy_cmd = ["aliyun", "appmanager", app_type, "deploy", "--overwrite", "--output", "json"]
    if region:
        deploy_cmd += ["--region", region]
    print(f"Command: {' '.join(deploy_cmd)}\n")
    deploy_env = os.environ.copy()
    if region:
        deploy_env.setdefault("ALIBABA_CLOUD_REGION_ID", region)
    deploy_exit, deploy_output, _ = run_cmd(deploy_cmd, stream=True, env_override=deploy_env)
    print()

    # Step 4: Post-deploy summary
    if deploy_exit == 0:
        print("--- Deploy command completed (exit 0) ---")
        if final_group != group_name:
            print(f"""
===========================================
⚠️  Group-conflict auto-resolution notice:
   The original group '{group_name}' exists but has no associated ECS instance
   (likely a leftover from a previous failed deploy).
   A new group '{final_group}' has been created automatically and the deploy completed there.

   Suggestions for the old group:
   - Delete it if no longer needed:
     aliyun appmanager {app_type} delete --name {app_name} --group_name {group_name}
   - To reuse an existing ECS, set
     common.deployment.instanceId in config.yaml to import that ECS into the old group
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
            print("\n❌ Deploy failed: insufficient account balance")
            print("   ⚠️  Error code: InvalidAccountStatus.NotEnoughBalance")
            print("   ⚠️  Creating a pay-as-you-go ECS instance requires an account balance ≥ ¥100.")
            print("   ⚠️  Please top up via the Alibaba Cloud console and retry: https://usercenter2.aliyun.com/finance/fund-management")
            print("   Tip: this restriction does not apply when deploying to an existing ECS instance.")
        elif is_cancelled or is_failed:
            status_label = "ReleaseCancelled" if is_cancelled else "ReleaseFailed"
            print(f"\n❌ Deploy failed (status: {status_label})")
            print('   ⚠️  Meaning: the start script failed or timed out on ECS, and the platform forcibly terminated the release.')
            print('   ⚠️  This is NOT "a deploy is still in progress"; it is NOT "wait a moment and retry".')
            print("   ⚠️  The only correct next step: immediately run deploy_toolkit.py verify to inspect the actual error log.")
        elif deploy_status:
            print(f"\n❌ Deploy error: {deploy_status}")

        if script_error:
            print(f"\n=== Script execution error (deployCommandOutput) ===\n{script_error}")
            print("===========================================\n")
            print("👆 The above is the actual error from the start script on ECS. Fix the start script in .appmanager/config.yaml accordingly, then redeploy.")
        else:
            print("\n❌ Failed to extract a script log from the deploy output.")
            print("   Please run deploy_toolkit.py verify to query the actual deploy log on ECS and locate the failure cause.")
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
            print(f"   Cloud Assistant raw response: {stdout}\n")
            # Cloud Assistant failed — show fallback
            ssh_target = ecs_public_ip or "<ECS_IP>"
            print("⚠️  Unable to fetch the ECS application log via Cloud Assistant")
            print("   Reason: the current RAM account lacks the ecs:RunCommand permission (Cloud Assistant call rejected)")
            print(f"\n   ▶ Fallback: SSH manually to inspect the log")
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
                print(f"   ▶ Trying HTTP port probe ({ecs_public_ip}:{app_port})...")
                hcode, hout, _ = run_cmd(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                                          "--connect-timeout", "8", "--max-time", "10",
                                          f"http://{ecs_public_ip}:{app_port}/"])
                http_code = hout.strip() if hcode == 0 else "000"
                print(f"   HTTP response code: {http_code}")
                if http_code not in ("000", "502", "503"):
                    app_log = f"HTTP_CHECK_PASSED: port {app_port} responded with HTTP {http_code}"
                    log_source = "http_check"
                    print(f"   ✅ Port {app_port} responded — the application is running!")
                else:
                    print(f"   ⚠️  Port {app_port} did not respond (HTTP {http_code})")
                    print("      Possible causes: ① the app is still installing/building  ② the security group has not opened the port  ③ the app failed to start")
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
                print("   The application may not have finished starting, or the log path may not be /root/app.log.\n")
    else:
        print("--- Step 3: ECS instance ID not found; cannot use Cloud Assistant ---")
        print("   Falling back to the limited log inside deployCommandOutput for analysis.\n")

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
    p_deploy.add_argument("--force-new-group", dest="force_new_group", action="store_true",
                          help="Force allocating a brand-new group (suffix -2..-10) even when the current group already has active ECS. Used when the user chose option B (brand-new group) at the price-and-risk gate.")

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
