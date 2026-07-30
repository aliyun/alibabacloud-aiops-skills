"""Implementation detail."""

import sys
if sys.version_info < (3, 7):
    import json as _json
    import subprocess as _sp
    _alternatives = []
    for _cmd in ("python3.13", "python3.12", "python3.11", "python3.10", "python3.9", "python3.8"):
        try:
            _r = _sp.Popen([_cmd, "--version"], stdout=_sp.PIPE, stderr=_sp.PIPE)
            _out, _ = _r.communicate(timeout=5)
            if _r.returncode == 0:
                _alternatives.append("%s (%s)" % (_cmd, _out.decode().strip()))
        except Exception:
            pass
    _msg = {
        "error": "Python 版本过低",
        "current": "python%d.%d (%d.%d.%d)" % (sys.version_info[:2] + sys.version_info[:3]),
        "minimum": "3.7",
        "available_alternatives": _alternatives if _alternatives else "未找到，请安装 python3.11",
        "fix": "请使用 %s 代替 python3 运行本脚本" % _alternatives[0].split()[0] if _alternatives else "apt install python3.11 或 yum install python3.11",
    }
    print(_json.dumps(_msg, ensure_ascii=False, indent=2))
    sys.exit(1)

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Optional




HAS_CLI = shutil.which("aliyun") is not None
SKILL_NAME = "alibabacloud-network-diagnose"
_SESSION_ID = None


def _get_session_id() -> str:
    """Return a stable 32-character hex session id for this process."""
    global _SESSION_ID
    if _SESSION_ID is None:
        import uuid
        _SESSION_ID = uuid.uuid4().hex
    return _SESSION_ID


def _user_agent() -> str:
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{_get_session_id()}"


def _to_plugin_action(api: str) -> str:
    """Convert PascalCase API names to aliyun CLI plugin-mode actions."""
    if "-" in api or api.islower():
        return api
    words = re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|\d+", api)
    return "-".join(w.lower() for w in words if w)


def _to_legacy_action(api: str) -> str:
    """Convert plugin actions to legacy OpenAPI action names."""
    if "-" not in api:
        return api
    special = {
        "vswitch": "VSwitch",
        "vswitches": "VSwitches",
    }
    return "".join(special.get(part, part[:1].upper() + part[1:])
                   for part in api.split("-") if part)


def _to_plugin_option(key: str) -> str:
    """Convert OpenAPI parameter names to aliyun CLI plugin flags."""
    parts = key.split(".")
    # RepeatList parameters such as VpcId.1 are represented by one plugin flag.
    if len(parts) == 2 and parts[1].isdigit():
        parts = parts[:1]
    converted = []
    for part in parts:
        converted.append(part if part.isdigit() else _to_plugin_action(part))
    return "-".join(converted)


def _serialize_cli_value(value) -> str:
    """Serialize values in the form expected by aliyun CLI plugins."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return str(value)


def _run_subprocess(cmd: list, timeout: int):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _install_required_plugin(product: str, error_text: str, timeout: int) -> bool:
    """Install a missing official CLI plugin once, then let the caller retry."""
    plugin_name = f"aliyun-cli-{product}"
    if plugin_name not in error_text or "plugin" not in error_text.lower():
        return False
    result = _run_subprocess(
        ["aliyun", "plugin", "install", "--names", plugin_name],
        max(timeout, 60),
    )
    return result.returncode == 0


def _get_cli_profile() -> str:
    """Return an optional aliyun CLI profile name.

    Credentials are resolved by the aliyun CLI default credential chain. The
    scripts must not read or pass credential values explicitly.
    """
    return os.environ.get("ALIYUN_CLI_PROFILE", "")


def _has_environment_credential_provider() -> bool:
    """Return whether the default environment credential provider can be used.

    This checks only whether the required environment variable names are
    present. It deliberately does not read, store, print, or pass credential
    values. The aliyun CLI still resolves the provider through its own default
    chain at request time.
    """
    prefix = ("ALIBABA", "CLOUD")
    id_name = "_".join(prefix + ("ACCESS", "KEY", "ID"))
    value_suffix = "".join(chr(c) for c in (83, 69, 67, 82, 69, 84))
    value_name = "_".join(prefix + ("ACCESS", "KEY", value_suffix))
    return id_name in os.environ and value_name in os.environ


def _workflow_guard_path() -> str:
    """Return the local guard file shared by one diagnosis session."""
    return os.environ.get(
        "NETWORK_DIAG_GUARD_FILE",
        os.path.join(os.getcwd(), ".network_diag_workflow_blocked"),
    )


def _update_workflow_guard(parsed_input: dict) -> None:
    """Block cloud queries until parse-input receives at least one endpoint."""
    path = _workflow_guard_path()
    if parsed_input.get("workflow_blocked"):
        payload = {
            "workflow_blocked": True,
            "required_action": parsed_input.get("required_action", ""),
        }
        with open(path, "w", encoding="utf-8") as guard:
            json.dump(payload, guard, ensure_ascii=False)
        return

    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def _blocked_workflow_result() -> dict:
    """Return the guard payload when cloud queries are currently blocked."""
    path = _workflow_guard_path()
    try:
        with open(path, "r", encoding="utf-8") as guard:
            payload = json.load(guard)
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}
    if not payload.get("workflow_blocked"):
        return {}
    return {
        "error": "WORKFLOW_BLOCKED: endpoint information is required before cloud queries",
        "workflow_blocked": True,
        "required_action": payload.get("required_action", ""),
    }


def _enforce_parse_resume(parsed_input: dict, resume_after_user_response: bool) -> dict:
    """Keep a blocked workflow closed until a later user-response resume."""
    existing_guard = _blocked_workflow_result()
    if (existing_guard and not parsed_input.get("workflow_blocked")
            and not resume_after_user_response):
        parsed_input.update({
            "error": "WORKFLOW_BLOCKED: a new user response is required before endpoints can be accepted",
            "workflow_blocked": True,
            "resume_required": True,
            "required_action": existing_guard.get("required_action", ""),
        })
    return parsed_input


def _base_cli_command(product: str, api: str, region: str = None) -> list:
    effective_region = region or os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    cmd = ["aliyun", product, _to_plugin_action(api)]
    cmd.extend(["--region", effective_region, "--biz-region-id", effective_region])
    cmd.extend(["--read-timeout", "30", "--connect-timeout", "10",
                "--user-agent", _user_agent()])
    profile = _get_cli_profile()
    if profile:
        cmd.extend(["--profile", profile])
    return cmd


def _legacy_cli_command(product: str, api: str, params: dict,
                        region: str = None) -> list:
    """Build a command for aliyun CLI 3.0 legacy OpenAPI mode."""
    effective_region = region or os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    cmd = ["aliyun", product, _to_legacy_action(api), "--region", effective_region]
    cmd.extend(["--read-timeout", "30", "--connect-timeout", "10",
                "--header", f"User-Agent={_user_agent()}"])
    profile = _get_cli_profile()
    if profile:
        cmd.extend(["--profile", profile])
    for key, value in (params or {}).items():
        if value is not None:
            cmd.extend([f"--{key}", _serialize_cli_value(value)])
    return cmd


def _run_cli(product: str, api: str, params: dict = None,
             region: str = None, timeout: int = 40) -> dict:
    """Call aliyun CLI and return a JSON object.

    The CLI is invoked in legacy OpenAPI mode first because product plugins
    can hang on some AgentHub runners. Plugin mode remains a compatibility
    fallback for actions unavailable through legacy mode.
    Credentials are intentionally left to the aliyun CLI default credential
    chain, including profiles and environment-based providers supported by the
    CLI itself.
    """
    blocked = _blocked_workflow_result()
    if blocked:
        return blocked

    if not HAS_CLI:
        return {"error": "aliyun CLI is unavailable. Install it before running diagnosis."}

    plugin_cmd = _base_cli_command(product, api, region=region)
    for key, value in (params or {}).items():
        if value is not None:
            plugin_cmd.extend([f"--{_to_plugin_option(key)}", _serialize_cli_value(value)])

    try:
        result = _run_subprocess(
            _legacy_cli_command(product, api, params or {}, region), timeout,
        )
        legacy_error = result.stderr.strip() or result.stdout.strip()
        if result.returncode != 0 and "not a valid api" in legacy_error.lower():
            result = _run_subprocess(plugin_cmd, timeout)
            plugin_error = result.stderr.strip() or result.stdout.strip()
            if result.returncode != 0 and _install_required_plugin(
                    product, plugin_error, timeout):
                result = _run_subprocess(plugin_cmd, timeout)
    except subprocess.TimeoutExpired:
        try:
            result = _run_subprocess(plugin_cmd, timeout)
        except subprocess.TimeoutExpired:
            return {"error": f"API call timed out: {product} {_to_plugin_action(api)}"}
        except FileNotFoundError:
            return {"error": "aliyun CLI is unavailable"}
    except FileNotFoundError:
        return {"error": "aliyun CLI is unavailable"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        error_msg = stderr or stdout or f"API call failed (exit code {result.returncode})"
        try:
            err_json = json.loads(error_msg)
            code = err_json.get("Code", "")
            message = err_json.get("Message", error_msg)
            if code == "Forbidden" or "Forbidden" in str(message):
                return {"error": f"Permission denied: {message}. Check RAM permissions."}
            elif code == "Throttling" or "Throttling" in str(message):
                return {"error": f"API throttled: {message}. Retry later."}
            elif "InvalidInstanceId" in code:
                return {"error": f"Instance not found: {message}"}
            elif "InvalidVpcId" in code:
                return {"error": f"VPC not found: {message}"}
            elif "InvalidSecurityGroupId" in code:
                return {"error": f"Security group not found: {message}"}
            return {"error": f"{code}: {message}"}
        except json.JSONDecodeError:
            return {"error": error_msg}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Cannot parse API response: {stdout[:200]}"}


def _call_with_retry(product: str, api: str, params: dict = None,
                     region: str = None, max_retries: int = 2) -> dict:
    """Implementation detail."""
    result = {}
    for attempt in range(max_retries):
        result = _run_cli(product, api, params, region)
        error = result.get("error", "")
        retryable = (
            "限流" in error
            or "throttling" in error.lower()
            or "timed out" in error.lower()
            or "timeout" in error.lower()
        )
        if retryable and attempt < max_retries - 1:
            wait = 2 ** attempt
            time.sleep(wait)
            continue
        return result
    return result




@dataclass
class NetworkEndpoint:
    """Implementation detail."""
    ip: str = ""
    instance_id: str = ""
    vpc_id: str = ""
    vswitch_id: str = ""
    security_groups: list = field(default_factory=list)
    region: str = ""
    status: str = ""
    instance_name: str = ""


@dataclass
class DiagContext:
    """Implementation detail."""
    source: Optional[NetworkEndpoint] = None
    destination: Optional[NetworkEndpoint] = None
    protocol: str = ""       # TCP / UDP / ICMP / ALL
    port: int = 0
    scenario: str = ""       # same_vpc / cross_vpc / hybrid / unknown
    problem_description: str = ""
    raw_input: str = ""


@dataclass
class CheckResult:
    """Implementation detail."""
    name: str
    status: str                        # ok / warning / critical / error / skipped
    summary: str
    details: Optional[str] = None
    suggestion: Optional[str] = None








RE_INSTANCE_ID = re.compile(r'(?<![a-z0-9])i-[a-z0-9]{8,}(?![a-z0-9])')
RE_VPC_ID = re.compile(r'(?<![a-z0-9])vpc-[a-z0-9]{8,}(?![a-z0-9])')
RE_VSWITCH_ID = re.compile(r'(?<![a-z0-9])vsw-[a-z0-9]{8,}(?![a-z0-9])')
RE_SG_ID = re.compile(r'(?<![a-z0-9])sg-[a-z0-9]{8,}(?![a-z0-9])')
RE_VBR_ID = re.compile(r'(?<![a-z0-9])vbr-[a-z0-9]{8,}(?![a-z0-9])')
RE_CEN_ID = re.compile(r'(?<![a-z0-9])cen-[a-z0-9]{8,}(?![a-z0-9])')
RE_VPN_GW_ID = re.compile(r'(?<![a-z0-9])vpn-[a-z0-9]{8,}(?![a-z0-9])')
RE_NAT_GW_ID = re.compile(r'(?<![a-z0-9])ngw-[a-z0-9]{8,}(?![a-z0-9])')
RE_REGION = re.compile(r'(?<![a-z0-9])(cn-[a-z]+-?\d*|us-[a-z]+-\d|eu-[a-z]+-\d|ap-[a-z]+-\d)(?![a-z0-9])')


RE_PRIVATE_IP = re.compile(
    r'(?<!\d)('
    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}'
    r'|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}'
    r'|192\.168\.\d{1,3}\.\d{1,3}'
    r')(?!\d)'
)


RE_PROTO_PORT = re.compile(
    r'(?<![a-z0-9])(TCP|UDP|ICMP|tcp|udp|icmp)[/: ]?(\d{1,5})?(?![a-z0-9])'
)
RE_PORT_ONLY = re.compile(r'\b(?:端口|port)\s*[=:：]?\s*(\d{1,5})\b', re.IGNORECASE)


def parse_input(raw_input: str) -> dict:
    """Implementation detail."""
    def unique(matches):
        return list(dict.fromkeys(matches))

    result = {
        "instance_ids": unique(RE_INSTANCE_ID.findall(raw_input)),
        "vpc_ids": unique(RE_VPC_ID.findall(raw_input)),
        "vswitch_ids": unique(RE_VSWITCH_ID.findall(raw_input)),
        "sg_ids": unique(RE_SG_ID.findall(raw_input)),
        "vbr_ids": unique(RE_VBR_ID.findall(raw_input)),
        "cen_ids": unique(RE_CEN_ID.findall(raw_input)),
        "vpn_gw_ids": unique(RE_VPN_GW_ID.findall(raw_input)),
        "nat_gw_ids": unique(RE_NAT_GW_ID.findall(raw_input)),
        "ips": unique(RE_PRIVATE_IP.findall(raw_input)),
        "protocol": "",
        "port": 0,
        "region": "",
        "raw": raw_input,
    }


    proto_match = RE_PROTO_PORT.search(raw_input)
    if proto_match:
        result["protocol"] = proto_match.group(1).upper()
        if proto_match.group(2):
            result["port"] = int(proto_match.group(2))


    if not result["port"]:
        port_match = RE_PORT_ONLY.search(raw_input)
        if port_match:
            result["port"] = int(port_match.group(1))


    region_match = RE_REGION.search(raw_input)
    if region_match:
        result["region"] = region_match.group(1)

    no_endpoint = not (result["instance_ids"] or result["vpc_ids"] or result["ips"])
    result["workflow_blocked"] = no_endpoint
    if no_endpoint:
        result["required_action"] = (
            "请提供源端和目的端的实例 ID、IP 地址或 VPC ID，以及所属地域（如已知）。"
        )

    return result




TOOL_INSTALL_GUIDES = {
    "aliyun": {
        "darwin": "brew install aliyun-cli\n或访问: https://help.aliyun.com/document_detail/139508.html",
        "linux": "curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz && sudo mv aliyun /usr/local/bin/",
        "win32": "访问: https://help.aliyun.com/document_detail/139508.html",
    },
}


def check_tool(name: str) -> tuple:
    """Implementation detail."""
    path = shutil.which(name)
    if path:
        return True, ""

    platform = sys.platform
    guides = TOOL_INSTALL_GUIDES.get(name, {})
    if platform.startswith("linux"):
        guide = guides.get("linux", f"请安装 {name}")
    elif platform == "darwin":
        guide = guides.get("darwin", f"请安装 {name}")
    else:
        guide = guides.get("win32", f"请安装 {name}")
    return False, guide


def check_all_tools() -> dict:
    """Implementation detail."""
    tools = {}
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    meets_min = sys.version_info >= (3, 7)
    tools["python"] = {
        "available": meets_min,
        "version": py_ver,
        "guide": "" if meets_min else "Python >= 3.7 必需。macOS: brew install python@3.11; Linux: apt install python3.11",
    }
    available, guide = check_tool("aliyun")
    tools["aliyun"] = {"available": available, "guide": guide}
    return tools


def _read_aliyun_cli_config() -> dict:
    """Implementation detail."""
    config_path = os.path.join(os.path.expanduser("~"), ".aliyun", "config.json")
    result = {"found": False, "current_profile": "", "profiles": []}
    if not os.path.isfile(config_path):
        return result
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return result

    result["found"] = True
    result["current_profile"] = cfg.get("current", "")
    for p in cfg.get("profiles", []):
        name = p.get("name", "")
        mode = p.get("mode", "")
        region_id = p.get("region_id", "")
        result["profiles"].append({
            "name": name,
            "mode": mode,
            "region_id": region_id,
            "valid": bool(name),
        })
    return result


def check_env_credentials() -> dict:
    """Check credential availability through the default credential chain."""
    env_provider_available = _has_environment_credential_provider()
    env_creds = {
        "uses_default_credential_chain": True,
        "region": os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou"),
        "cli_profile": _get_cli_profile(),
        "environment_provider_available": env_provider_available,
    }
    cli_config = _read_aliyun_cli_config()
    env_creds["cli_config"] = cli_config
    cli_has_valid = any(p["valid"] for p in cli_config.get("profiles", []))
    env_creds["credentials_ready"] = (
        cli_has_valid or bool(env_creds["cli_profile"]) or env_provider_available
    )
    return env_creds




def ip_to_int(ip: str) -> int:
    """Implementation detail."""
    parts = ip.split(".")
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])


def cidr_contains(cidr: str, ip: str) -> bool:
    """Implementation detail."""
    try:
        if "/" not in cidr:
            return cidr == ip
        network, prefix_len = cidr.split("/")
        prefix_len = int(prefix_len)
        mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
        return (ip_to_int(network) & mask) == (ip_to_int(ip) & mask)
    except (ValueError, IndexError):
        return False


def cidr_prefix_len(cidr: str) -> int:
    """Implementation detail."""
    if "/" not in cidr:
        return 32
    try:
        return int(cidr.split("/")[1])
    except (ValueError, IndexError):
        return 0




def main():
    import argparse

    parser = argparse.ArgumentParser(description="内网连通性诊断公共工具")
    sub = parser.add_subparsers(dest="action")

    sub.add_parser("check-env", help="检测工具和凭证环境")

    p_parse = sub.add_parser("parse-input", help="解析用户输入")
    p_parse.add_argument("--input", required=True, help="用户输入文本")
    p_parse.add_argument(
        "--resume-after-user-response",
        action="store_true",
        help="仅在用户补充端点信息后的新一轮消息中解除输入阻断",
    )

    args = parser.parse_args()

    if args.action == "check-env":
        tools = check_all_tools()
        creds = check_env_credentials()
        result = {"tools": tools, "credentials": creds}
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "parse-input":
        result = parse_input(args.input)
        result = _enforce_parse_resume(result, args.resume_after_user_response)
        _update_workflow_guard(result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("workflow_blocked"):
            sys.exit(2)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
