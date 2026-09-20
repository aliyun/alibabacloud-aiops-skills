#!/usr/bin/env python3
"""
[转换工具] lookup_rules - 通过 aliyun CLI（lhm 插件）查询方言转换规则

请求通道（由环境变量 SQLT_RULES_BACKEND 路由）：
    - aliyun（默认） : `aliyun lhm <subcommand> --source .. --target .. --endpoint ..`
    - a1（回退）     : `a1 mcp --env pre call-tool tam-migration::sql-conversion-*`

前置检查（backend=aliyun 时自动执行，进程内仅一次）：
    1. aliyun CLI 已安装且版本 >= 3.3.8（aliyun version）
    2. lhm 插件已安装（aliyun plugin list；已公开，从公共插件索引安装）
    3. 凭证已配置（aliyun configure list 存在有效 profile，
       或已设置 ALIBABA_CLOUD_ACCESS_KEY_ID 环境变量）
    检查失败时打印引导信息（含 `aliyun configure --profile <ProfileName>` 等命令）并退出。
    本脚本不代替用户安装 CLI / 配置凭证，且遵循安全红线：绝不读取、回显、要求粘贴 AK/SK。

相关环境变量：
    SQLT_RULES_BACKEND   请求通道，'aliyun'（默认）| 'a1'
    SQLT_LHM_ENDPOINT    lhm 服务 endpoint（优先以 credentials.json 的 lhm.endpoint 为准），
                         默认 lhm.cn-hangzhou.aliyuncs.com
    SQLT_LHM_REGION      lhm 服务 region（优先以 credentials.json 的 lhm.region_id 为准），
                         默认 cn-hangzhou
    SQLT_ALIYUN_PROFILE  指定 aliyun 配置集名（对应 `aliyun configure --profile <name>`）；
                         留空则使用 CLI 当前默认 profile

Usage:
    # 列出所有分类（调 get-all-rules-summary）
    python3 scripts/lookup_rules.py \
        --source clickhouse --target maxcompute --list-categories

    # 查看指定分类的规则详情（调 get-category-detail，支持逗号分隔批量查询）
    python3 scripts/lookup_rules.py \
        --source clickhouse --target maxcompute --category "ddl/alter-table"

    # 批量查看多个分类
    python3 scripts/lookup_rules.py \
        --source clickhouse --target maxcompute \
        --category "functions/date-functions,functions/string-functions,ddl/alter-table"

Output:
    --list-categories: 输出所有唯一 source_category 值（每行一个）
    --category: 输出该分类下所有规则（id / source_syntax / target_syntax / examples）
"""
import argparse
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import uuid

# ── 请求通道配置 ─────────────────────────────────────────────────────────────

_BACKEND = (os.environ.get("SQLT_RULES_BACKEND") or "aliyun").strip().lower()


# credentials.json（LHM 统一配置）候选路径，与其它子技能保持一致：
# 会话配置($LHM_SESSION_FILE) > $LHM_CREDENTIALS_FILE > ./config/lhm_credentials.json
# > ~/.lhm/credentials.json
def _credentials_search_paths() -> list:
    paths = []
    session_file = (os.environ.get("LHM_SESSION_FILE") or "").strip()
    if session_file:
        paths.append(os.path.expanduser(session_file))
    explicit = (os.environ.get("LHM_CREDENTIALS_FILE") or "").strip()
    if explicit:
        paths.append(os.path.expanduser(explicit))
    paths.append(os.path.join("config", "lhm_credentials.json"))
    paths.append(os.path.join(os.path.expanduser("~"), ".lhm", "credentials.json"))
    return paths


def _clean_cfg_value(value) -> str:
    """非字符串 / 空 / 占位符(<...>) 一律视为未填写。"""
    if not isinstance(value, str):
        return ""
    value = value.strip()
    if not value or value.startswith("<"):
        return ""
    return value


def _read_lhm_endpoint_region() -> tuple:
    """从 credentials.json 的 `lhm` 段读取固定参数 endpoint / region_id。

    兼容嵌套 {"lhm": {"endpoint":..,"region_id":..}} 与顶层扁平写法。
    返回 (endpoint, region_id)，缺失时对应项为空串。
    """
    for path in _credentials_search_paths():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        lhm = data.get("lhm")
        lhm = lhm if isinstance(lhm, dict) else {}
        endpoint = _clean_cfg_value(lhm.get("endpoint") or data.get("endpoint"))
        region_id = _clean_cfg_value(lhm.get("region_id") or data.get("region_id"))
        if endpoint or region_id:
            return endpoint, region_id
    return "", ""


# endpoint / region 固定参数：优先取 credentials.json 的 lhm 段，其次环境变量，最后默认值
_CFG_ENDPOINT, _CFG_REGION_ID = _read_lhm_endpoint_region()
_LHM_ENDPOINT = (
    _CFG_ENDPOINT
    or os.environ.get("SQLT_LHM_ENDPOINT")
    or "lhm.cn-hangzhou.aliyuncs.com"
)
_LHM_REGION = (
    _CFG_REGION_ID
    or (os.environ.get("SQLT_LHM_REGION") or "").strip()
    or (os.environ.get("REGION_ID") or "").strip()
    or "cn-hangzhou"
)
_MIN_ALIYUN_VERSION = (3, 3, 8)

# lhm 插件 API 版本：优先环境变量 ALIBABA_CLOUD_LHM_API_VERSION，默认 2025-01-16。
# 与 install_lhm_plugin.sh 及其它子技能的 aliyun_cli 封装保持一致——不显式指定时 CLI
# 会用最新版本，导致仅在旧版本可用的命令（如 save-skill-audit-record）被拒绝。
_LHM_API_VERSION = (os.environ.get("ALIBABA_CLOUD_LHM_API_VERSION") or "2025-01-16").strip()

# 版本不匹配时插件提示：`Available versions for this command: [2025-01-16]`
_VERSION_HINT_RE = re.compile(r"Available versions for this command:\s*\[([^\]]+)\]")
# 进程内缓存：subcommand -> 修正后的 api-version
_VERSION_OVERRIDES = {}

# 指定使用哪个 aliyun 配置集（profile）。为空时用 CLI 当前默认 profile。
_ALIYUN_PROFILE = (os.environ.get("SQLT_ALIYUN_PROFILE") or "").strip()

def _find_aliyun_binary() -> str:
    """定位 aliyun CLI 二进制；沙箱环境中优先使用 aliyun_real。
    
    沙箱环境中 aliyun CLI 可能被封装为代理，实际调用需要使用 aliyun_real。
    优先检测 aliyun_real，如果存在则使用它；否则回退到 aliyun。
    """
    real_binary = shutil.which("aliyun_real")
    if real_binary is not None:
        return "aliyun_real"
    binary = shutil.which("aliyun")
    if binary is not None:
        return "aliyun"
    return "aliyun"  # 返回默认值，后续检查会处理未找到的情况


def _profile_args() -> list:
    """需要显式指定 profile 时返回 ['--profile', name]，否则返回空列表。"""
    return ["--profile", _ALIYUN_PROFILE] if _ALIYUN_PROFILE else []


def _credential_hint() -> str:
    """返回凭证配置引导文案。"""
    name = _ALIYUN_PROFILE or "<ProfileName>"
    cli_cmd = _find_aliyun_binary()
    return "\n".join([
        "  请在本会话外执行以下命令完成配置（建议使用具名 profile，便于多环境隔离）：",
        f"    {cli_cmd} configure --profile {name}",
        "    # 也可指定认证方式，如 --mode AK / --mode EcsRamRole（ECS 实例角色）/ --mode OAuth",
        f"  配置完成后可通过 `{cli_cmd} configure list` 确认；若使用非默认 profile，",
        "  请设置环境变量 SQLT_ALIYUN_PROFILE=<ProfileName> 让本工具使用该配置集。",
        "  （安全提示：请勿在对话中粘贴 AK/SK）",
    ])


# aliyun CLI 官方下载地址（阿里云 CDN，国内可直连）
_CLI_DOC_URL = "https://help.aliyun.com/zh/cli/installation-guide"
_CLI_CDN = "https://aliyuncli.alicdn.com"


def _cli_install_hint() -> str:
    """返回 aliyun CLI 安装引导文案（按当前平台给出可直接复制的命令）。

    只输出命令供用户自行执行，不代替用户安装。
    """
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "amd64"
    is_mac = sys.platform == "darwin"
    pkg = f"aliyun-cli-{'macosx' if is_mac else 'linux'}-latest-{arch}.tgz"

    lines = [f"  安装 aliyun CLI（当前平台：{sys.platform}/{machine}）："]
    if is_mac:
        lines += [
            "  方式 A（Homebrew，最简）：",
            "    brew install aliyun-cli",
            "  方式 B（官方 CDN 下载）：",
        ]
    else:
        lines += ["  方式 A（官方 CDN 下载，适用 ECS）："]
    lines += [
        f"    curl -o /tmp/{pkg} {_CLI_CDN}/{pkg}",
        f"    tar -xzf /tmp/{pkg} -C /tmp",
        "    sudo mv /tmp/aliyun /usr/local/bin/ && aliyun version",
    ]
    lines += [f"  完整文档：{_CLI_DOC_URL}"]
    return "\n".join(lines)


def _install_hint() -> str:
    """返回 lhm 插件安装引导文案（始终从公共插件索引在线安装最新版）。"""
    cli_cmd = _find_aliyun_binary()
    return "\n".join([
        "  安装 lhm 插件（已公开，始终从公共插件索引安装最新版）：",
        f"    {cli_cmd} plugin install --names lhm",
    ])

# 会话级 session-id（32 位小写 hex，进程内生成一次），用于 API 调用归因
_SESSION_ID = uuid.uuid4().hex
# skill-version 优先取环境变量 LHM_SKILL_VERSION（dispatcher 从 manifest.json 读取并导出），未设置时兜底 1.0.0
_SKILL_VERSION = os.environ.get("LHM_SKILL_VERSION", "").strip() or "1.0.0"
_USER_AGENT = f"AlibabaCloud-Agent-Skills/sql-conversion-skill/{_SESSION_ID} skill-version/{_SKILL_VERSION}"

_prereq_checked = False


def _run(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


# ── 前置检查（对齐 alibabacloud-sls-query skill 的 Prerequisites 模式）──────────

def _check_aliyun_prerequisites() -> None:
    """检查 aliyun CLI 可用性与凭证配置，进程内仅执行一次。

    不满足时打印引导信息并退出（exit 1），不代替用户安装/配置。
    安全红线：只用 `aliyun configure list` 判断凭证状态，绝不读取/回显 AK/SK。
    """
    global _prereq_checked
    if _prereq_checked:
        return

    cli_cmd = _find_aliyun_binary()

    # 1. aliyun CLI 已安装且版本 >= 3.3.8
    try:
        result = _run([cli_cmd, "version"])
    except FileNotFoundError:
        print(
            "[ERROR] 未检测到 aliyun CLI（规则查询依赖它，要求版本 >= 3.3.8）。\n"
            f"{_cli_install_hint()}\n"
            "  装好 CLI 后还需两步：\n"
            f"{_install_hint()}\n"
            "  以及配置凭证：\n"
            f"{_credential_hint()}",
            file=sys.stderr,
        )
        sys.exit(1)
    if result.returncode != 0:
        print(f"[ERROR] `{cli_cmd} version` 执行失败: {result.stderr.strip() or result.stdout.strip()}",
              file=sys.stderr)
        sys.exit(1)
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout + result.stderr)
    if m and tuple(int(x) for x in m.groups()) < _MIN_ALIYUN_VERSION:
        min_ver = ".".join(str(v) for v in _MIN_ALIYUN_VERSION)
        print(
            f"[ERROR] aliyun CLI 版本过低（当前 {m.group(0)}，要求 >= {min_ver}）。\n"
            f"{_cli_install_hint()}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. lhm 插件已安装（已公开，从公共插件索引安装）
    result = _run([cli_cmd, "plugin", "list"])
    if "aliyun-cli-lhm" not in result.stdout:
        print(f"[ERROR] 未检测到 lhm 插件。\n{_install_hint()}", file=sys.stderr)
        sys.exit(1)

    # 3. 凭证已配置（环境变量凭证优先；否则检查 configure profile）
    if not os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID"):
        result = _run([cli_cmd, "configure", "list"])
        # 输出为表格：Profile | Credential | Valid | Region | Language
        # "Invalid" 包含子串 "Valid"，必须按单元格精确匹配
        # 指定了 SQLT_ALIYUN_PROFILE 时，只认该 profile 那一行（默认 profile 名带 ' *' 后缀）
        has_valid_profile = False
        for line in result.stdout.splitlines():
            if line.lstrip().startswith("Profile"):
                continue  # 表头
            cells = [c.strip() for c in line.split("|")]
            if not any(c == "Valid" for c in cells):
                continue
            if _ALIYUN_PROFILE:
                if cells and cells[0].rstrip(" *") == _ALIYUN_PROFILE:
                    has_valid_profile = True
                    break
            else:
                has_valid_profile = True
                break
        if result.returncode != 0 or not has_valid_profile:
            scope = f"名为 '{_ALIYUN_PROFILE}' 的" if _ALIYUN_PROFILE else ""
            print(
                f"[ERROR] 未检测到有效的{scope}阿里云凭证 profile。\n"
                f"{_credential_hint()}",
                file=sys.stderr,
            )
            sys.exit(1)

    _prereq_checked = True


# ── 响应解析 ─────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """从命令输出中提取 JSON（跳过非 JSON 前缀行，兼容 a1 的日志前缀）。"""
    lines = [line for line in text.splitlines() if not line.startswith("[")]
    cleaned = "\n".join(lines).strip()
    if not cleaned:
        raise ValueError(f"输出中未找到 JSON: {text[:200]}")
    for i, ch in enumerate(cleaned):
        if ch in ('{', '['):
            return json.loads(cleaned[i:])
    raise ValueError(f"输出中未找到 JSON: {cleaned[:200]}")


def _unwrap_response(resp: dict) -> dict:
    """兼容两种响应结构：{success, errMessage, data} 包装层 或 直接返回数据体。"""
    if isinstance(resp, dict) and "success" in resp:
        if not resp.get("success"):
            err = resp.get("errMessage") or resp.get("errCode") or "unknown error"
            print(f"[ERROR] 规则服务返回失败: {err}", file=sys.stderr)
            sys.exit(1)
        data = resp.get("data")
        if isinstance(data, str):
            return json.loads(data)
        return data
    return resp


# ── 请求通道实现 ─────────────────────────────────────────────────────────────

def _aliyun_call(subcommand: str, params: dict) -> dict:
    """通过 aliyun CLI（lhm 插件）调用规则查询接口，返回解析后的数据体。

    显式携带 --api-version（默认 2025-01-16，可用 ALIBABA_CLOUD_LHM_API_VERSION 覆盖）：
    不指定时 CLI 会用最新版本，导致仅在旧版本可用的命令（如 save-skill-audit-record）被
    拒绝。若插件回提示可用版本，则按提示自适应重试一次。
    """
    _check_aliyun_prerequisites()
    cli_cmd = _find_aliyun_binary()
    version = _VERSION_OVERRIDES.get(subcommand) or _LHM_API_VERSION

    for attempt in range(2):
        cmd = [cli_cmd, "lhm", subcommand]
        for k, v in params.items():
            cmd += [f"--{k}", str(v)]
        cmd += ["--api-version", version]
        cmd += ["--endpoint", _LHM_ENDPOINT]
        cmd += ["--region", _LHM_REGION]
        cmd += _profile_args()
        # 可观测性归因（对齐参考 skill 的 Observability 规则）
        cmd_with_ua = cmd + ["--user-agent", _USER_AGENT]
        result = _run(cmd_with_ua)
        if result.returncode != 0 and "user-agent" in (result.stderr + result.stdout).lower():
            # 插件版本不支持 --user-agent 时去掉该参数重试
            result = _run(cmd)
        if result.returncode == 0:
            return _unwrap_response(_extract_json(result.stdout))

        detail = result.stderr.strip() or result.stdout.strip()
        # api-version 不匹配：按插件提示的可用版本自适应重试一次
        if attempt == 0:
            hint = _VERSION_HINT_RE.search(detail)
            if hint and subcommand not in _VERSION_OVERRIDES:
                fixed = hint.group(1).split(",")[0].strip()
                if fixed and fixed != version:
                    _VERSION_OVERRIDES[subcommand] = fixed
                    version = fixed
                    continue

        detail = detail or (
            f"无输出（exit={result.returncode}）。可能原因：lhm 插件损坏或被本机安全软件拦截、"
            "endpoint 不可达"
        )
        print(f"[ERROR] aliyun lhm {subcommand} 失败: {detail}\n{_install_hint()}",
              file=sys.stderr)
        sys.exit(1)

    sys.exit(1)  # 理论不可达：循环内必定 return 或 exit


def _mcp_call(tool_name: str, body: dict) -> dict:
    """[legacy 回退通道] 通过 a1 mcp call-tool 调用 MCP Tool，返回解析后的 data。"""
    cmd = [
        "a1", "mcp", "--env", "pre",
        "call-tool", tool_name,
        json.dumps(body),
    ]
    result = subprocess.run(
        " ".join(shlex.quote(c) for c in cmd) + " 2>&1",
        shell=True, capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"[ERROR] a1 mcp call-tool 失败: {result.stdout.strip()}", file=sys.stderr)
        sys.exit(1)
    return _unwrap_response(_extract_json(result.stdout))


def _call_rules_summary(source: str, target: str) -> dict:
    if _BACKEND == "a1":
        return _mcp_call(
            "tam-migration::sql-conversion-getAllRulesSummary",
            {"source": source, "target": target},
        )
    return _aliyun_call("get-all-rules-summary", {"source": source, "target": target})


def _call_category_detail(source: str, target: str, category: str) -> dict:
    if _BACKEND == "a1":
        return _mcp_call(
            "tam-migration::sql-conversion-getCategoryDetail",
            {"source": source, "target": target, "category": category},
        )
    return _aliyun_call(
        "get-category-detail",
        {"source": source, "target": target, "category": category},
    )


# ── 命令实现 ─────────────────────────────────────────────────────────────────

def cmd_list_categories(source: str, target: str) -> None:
    data = _call_rules_summary(source, target)
    rules = data.get("rules", [])
    categories = sorted({r.get("source_category", "") for r in rules if r.get("source_category")})
    for cat in categories:
        print(cat)


def cmd_category(source: str, target: str, category: str) -> None:
    cat_list = [c.strip() for c in category.split(",") if c.strip()]
    results = {}
    for cat in cat_list:
        data = _call_category_detail(source, target, cat)
        results[cat] = data

    all_rules = []
    for cat_data in results.values():
        if isinstance(cat_data, dict):
            all_rules.extend(cat_data.get("rules", []))
        elif isinstance(cat_data, list):
            all_rules.extend(cat_data)

    if not all_rules:
        print(f"[WARN] 未找到分类 '{category}' 下的规则", file=sys.stderr)
        return

    confirmed = [r for r in all_rules if r.get("status") in ("confirmed", "unconfirmed")]
    unsupported = [r for r in all_rules if r.get("status") in ("unsupported", "doc_confirmed_unsupported")]

    for rule in confirmed:
        print(f"--- {rule.get('id', '?')} ---")
        print(f"source_syntax : {rule.get('source_syntax', '')}")
        print(f"target_syntax : {rule.get('target_syntax', '')}")
        audit_note = rule.get("audit_note", "")
        if audit_note:
            print(f"audit_note    : {audit_note}")
        examples = rule.get("examples", [])
        if examples:
            print("examples:")
            for ex in examples:
                print(f"  source: {ex.get('source_sql', '')}")
                print(f"  target: {ex.get('target_sql', '')}")
                ex_note = ex.get("audit_note", "")
                if ex_note:
                    print(f"  audit_note: {ex_note}")
        print()

    if unsupported:
        print(f"--- 以下 {len(unsupported)} 条规则标记为不支持（源 SQL 应原样保留）---")
        for rule in unsupported:
            print(f"  {rule.get('id', '?')}: {rule.get('source_syntax', '')} → UNSUPPORTED")
        print()


def cmd_search(source: str, target: str, keyword: str) -> None:
    """按关键词模糊搜索规则（匹配 id / source_syntax / target_syntax / examples）。"""
    data = _call_rules_summary(source, target)
    rules = data.get("rules", [])
    kw = keyword.lower()
    matched = []
    for r in rules:
        searchable = " ".join([
            str(r.get("id", "")),
            str(r.get("source_syntax", "")),
            str(r.get("target_syntax", "")),
            " ".join(str(ex.get("source_sql", "")) + " " + str(ex.get("target_sql", ""))
                     for ex in r.get("examples", [])),
        ]).lower()
        if kw in searchable:
            matched.append(r)
    if not matched:
        print(f"[WARN] 未找到包含 '{keyword}' 的规则", file=sys.stderr)
        return
    print(f"=== 搜索 '{keyword}' 命中 {len(matched)} 条规则 ===\n")
    for rule in matched:
        print(f"--- {rule.get('id', '?')} ---")
        print(f"source_syntax : {rule.get('source_syntax', '')}")
        print(f"target_syntax : {rule.get('target_syntax', '')}")
        audit_note = rule.get("audit_note", "")
        if audit_note:
            print(f"audit_note    : {audit_note}")
        examples = rule.get("examples", [])
        if examples:
            print("examples:")
            for ex in examples:
                print(f"  source: {ex.get('source_sql', '')}")
                print(f"  target: {ex.get('target_sql', '')}")
                ex_note = ex.get("audit_note", "")
                if ex_note:
                    print(f"  audit_note: {ex_note}")
        print()


def main() -> None:
    p = argparse.ArgumentParser(description="通过 aliyun CLI（lhm 插件）查询方言转换规则")
    p.add_argument("--source", required=True, help="源方言，如 clickhouse")
    p.add_argument("--target", required=True, help="目标方言，如 maxcompute")
    p.add_argument("--list-categories", action="store_true", help="列出所有规则分类")
    p.add_argument("--category", help="查看指定分类的规则详情（支持逗号分隔批量查询多个分类）")
    p.add_argument("--search", help="按关键词模糊搜索规则（匹配 id/source_syntax/target_syntax/examples）")
    args = p.parse_args()

    if args.search:
        cmd_search(args.source, args.target, args.search)
    elif args.list_categories:
        cmd_list_categories(args.source, args.target)
    elif args.category:
        cmd_category(args.source, args.target, args.category)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
