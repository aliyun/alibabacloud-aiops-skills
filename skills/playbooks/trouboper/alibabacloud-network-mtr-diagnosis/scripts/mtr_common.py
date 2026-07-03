"""
mtr_common.py - Public network MTR diagnosis shared utility library

Provides aliyun CLI wrapper, input parsing, environment detection, and other common utilities.
"""

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
        "error": "Python version too low",
        "current": "python%d.%d (%d.%d.%d)" % (sys.version_info[:2] + sys.version_info[:3]),
        "minimum": "3.7",
        "available_alternatives": _alternatives if _alternatives else "Not found, please install python3.11",
        "fix": "Please use %s instead of python3 to run this script" % _alternatives[0].split()[0] if _alternatives else "apt install python3.11 or yum install python3.11",
    }
    print(_json.dumps(_msg, ensure_ascii=False, indent=2))
    sys.exit(1)

import json
import os
import re
import shlex
import shutil
import subprocess
import time
from typing import Optional


# --- aliyun CLI wrapper -----------------------------------------------

HAS_CLI = shutil.which("aliyun") is not None

# Session-ID for Observability (per-command --user-agent)
# Generated once per module load, reused across all CLI calls in this session
import uuid as _uuid

_SESSION_ID = _uuid.uuid4().hex  # 32-char hex string
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-network-mtr-diagnosis/{_SESSION_ID}"


def _is_transient_error(output: str) -> bool:
    """Detect transient errors that may succeed on retry."""
    return ("Deny" in output and "Unauthorized" in output) or \
           ("Deny" in output and "source ip" in output) or \
           ("Throttling" in output)


def _get_cli_profile() -> str:
    """Get the aliyun CLI profile name to use."""
    return os.environ.get("ALIYUN_CLI_PROFILE", "")


def _run_cli(product: str, api: str, params: dict = None,
             region: str = None, timeout: int = 120) -> dict:
    """
    Call aliyun CLI and return JSON result.

    Relies on aliyun CLI's default credential chain:
    - Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET)
    - CLI profile (~/.aliyun/config.json)
    - ECS RAM Role
    """
    if not HAS_CLI:
        return {"error": "aliyun CLI not available, please install: https://help.aliyun.com/document_detail/139508.html"}

    cmd = ["aliyun", product, api]

    effective_region = region or os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    cmd.extend(["--region", effective_region])

    # Per-command --user-agent for Observability (per Observability section)
    cmd.extend(["--user-agent", _USER_AGENT])

    if params:
        for key, value in params.items():
            if value is not None:
                cmd.extend([f"--{key}", str(value)])

    profile = _get_cli_profile()
    if profile:
        cmd.extend(["--profile", profile])

    shell_cmd = " ".join(shlex.quote(c) for c in cmd)
    try:
        result = subprocess.run(
            shell_cmd, shell=True, capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"API call timed out: {product} {api}"}
    except FileNotFoundError:
        return {"error": "aliyun CLI not available"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        if _is_transient_error(stderr) or _is_transient_error(stdout):
            print(f"[WARNING] Transient error for {product} {api}, retrying...",
                  file=sys.stderr)
            try:
                retry_result = subprocess.run(
                    shell_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
                if retry_result.returncode == 0:
                    try:
                        return json.loads(retry_result.stdout.strip())
                    except json.JSONDecodeError:
                        pass
                print("[WARNING] Retry still failed", file=sys.stderr)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                print("[WARNING] Retry timed out or failed", file=sys.stderr)

        error_msg = stderr or stdout or f"API call failed (exit code {result.returncode})"
        try:
            err_json = json.loads(error_msg)
            code = err_json.get("Code", "")
            message = err_json.get("Message", error_msg)
            if code == "Forbidden" or "Forbidden" in str(message):
                return {"error": f"Insufficient permissions: {message}. Please check RAM permission configuration, see references/ram-permissions.md."}
            elif code == "Throttling" or "Throttling" in str(message):
                return {"error": f"API throttled: {message}. Please retry later."}
            elif "InvalidInstanceId" in code:
                return {"error": f"Instance not found: {message}"}
            return {"error": f"{code}: {message}"}
        except json.JSONDecodeError:
            return {"error": error_msg}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Unable to parse API response: {stdout[:200]}"}


def _call_with_retry(product: str, api: str, params: dict = None,
                     region: str = None, max_retries: int = 3) -> dict:
    """API call with retry (handles throttling and other transient errors)."""
    result = {}
    for attempt in range(max_retries):
        result = _run_cli(product, api, params, region)
        error = result.get("error", "")
        if "Throttling" in error:
            wait = 2 ** attempt
            time.sleep(wait)
            continue
        return result
    return result


# --- Input parsing ----------------------------------------------------

# Alibaba Cloud resource ID patterns
RE_INSTANCE_ID = re.compile(r'(?<![a-z0-9])i-[a-z0-9]{8,}(?![a-z0-9])')
RE_REGION = re.compile(r'(?<![a-z0-9])(cn-[a-z]+-?\d*|us-[a-z]+-\d|eu-[a-z]+-\d|ap-[a-z]+-\d)(?![a-z0-9])')

# IPv4 pattern (public + private)
RE_IPV4 = re.compile(
    r'(?<!\d)(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d)'
)

# Domain name pattern
RE_DOMAIN = re.compile(
    r'(?<![a-zA-Z0-9._-])([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'
    r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*'
    r'\.[a-zA-Z]{2,})(?![a-zA-Z0-9._-])'
)

# Protocol and port
RE_PROTO_PORT = re.compile(
    r'(?<![a-z0-9])(TCP|UDP|ICMP|tcp|udp|icmp)[/: ]?(\d{1,5})?(?![a-z0-9])'
)
RE_PORT_ONLY = re.compile(r'\b(?:port)\s*[=:]?\s*(\d{1,5})\b', re.IGNORECASE)


def _is_valid_ipv4(ip: str) -> bool:
    """Check whether the string is a valid IPv4 address."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    for p in parts:
        try:
            n = int(p)
            if n < 0 or n > 255:
                return False
        except ValueError:
            return False
    return True


def _is_private_ip(ip: str) -> bool:
    """Check whether the IP is an RFC1918 private address."""
    parts = ip.split(".")
    first, second = int(parts[0]), int(parts[1])
    if first == 10:
        return True
    if first == 172 and 16 <= second <= 31:
        return True
    if first == 192 and second == 168:
        return True
    return False


def _is_domain(text: str) -> bool:
    """Filter out obvious non-domain matches (e.g., version numbers, IP addresses)."""
    # Exclude strings consisting only of digits and dots (IP addresses)
    if all(c.isdigit() or c == '.' for c in text):
        return False
    # Exclude common file extension false matches
    if text.endswith(('.py', '.sh', '.json', '.md', '.txt', '.log')):
        return False
    return True


def parse_input(raw_input: str) -> dict:
    """
    Extract structured diagnostic information from user free-text input.

    Returns:
        dict: {
            "instance_ids": [...],
            "ips": [...],
            "public_ips": [...],
            "private_ips": [...],
            "domains": [...],
            "protocol": str,
            "port": int,
            "region": str,
            "raw": str,
        }
    """
    # Extract IPs
    all_ips = list(set(ip for ip in RE_IPV4.findall(raw_input) if _is_valid_ipv4(ip)))
    public_ips = [ip for ip in all_ips if not _is_private_ip(ip)]
    private_ips = [ip for ip in all_ips if _is_private_ip(ip)]

    # Extract domains (excluding already identified IPs)
    domains = list(set(d for d in RE_DOMAIN.findall(raw_input) if _is_domain(d)))

    result = {
        "instance_ids": list(set(RE_INSTANCE_ID.findall(raw_input))),
        "ips": all_ips,
        "public_ips": public_ips,
        "private_ips": private_ips,
        "domains": domains,
        "protocol": "",
        "port": 0,
        "region": "",
        "raw": raw_input,
    }

    # Extract protocol and port
    proto_match = RE_PROTO_PORT.search(raw_input)
    if proto_match:
        result["protocol"] = proto_match.group(1).upper()
        if proto_match.group(2):
            result["port"] = int(proto_match.group(2))

    if not result["port"]:
        port_match = RE_PORT_ONLY.search(raw_input)
        if port_match:
            result["port"] = int(port_match.group(1))

    # Extract region
    region_match = RE_REGION.search(raw_input)
    if region_match:
        result["region"] = region_match.group(1)

    return result


# --- Environment detection --------------------------------------------

TOOL_INSTALL_GUIDES = {
    "aliyun": {
        "darwin": "brew install aliyun-cli\nor visit: https://help.aliyun.com/document_detail/139508.html",
        "linux": "curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz && sudo mv aliyun /usr/local/bin/",
        "win32": "Visit: https://help.aliyun.com/document_detail/139508.html",
    },
}


def check_tool(name: str) -> tuple:
    """Detect whether a tool is available."""
    path = shutil.which(name)
    if path:
        return True, ""

    platform = sys.platform
    guides = TOOL_INSTALL_GUIDES.get(name, {})
    if platform.startswith("linux"):
        guide = guides.get("linux", f"Please install {name}")
    elif platform == "darwin":
        guide = guides.get("darwin", f"Please install {name}")
    else:
        guide = guides.get("win32", f"Please install {name}")
    return False, guide


def check_all_tools() -> dict:
    """Detect availability of all required tools."""
    tools = {}
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    meets_min = sys.version_info >= (3, 7)
    tools["python"] = {
        "available": meets_min,
        "version": py_ver,
        "guide": "" if meets_min else "Python >= 3.7 required. macOS: brew install python@3.11; Linux: apt install python3.11",
    }
    available, guide = check_tool("aliyun")
    tools["aliyun"] = {"available": available, "guide": guide}
    return tools


def _read_aliyun_cli_config() -> dict:
    """Read aliyun CLI configuration file (~/.aliyun/config.json)."""
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
        has_creds = False
        if mode == "AK":
            has_creds = bool(p.get("access_key_id")) and bool(p.get("access_key_secret"))
        elif mode == "StsToken":
            has_creds = bool(p.get("access_key_id")) and bool(p.get("sts_token"))
        elif mode == "RamRoleArn":
            has_creds = bool(p.get("access_key_id")) and bool(p.get("ram_role_arn"))
        elif mode == "EcsRamRole":
            has_creds = True
        result["profiles"].append({
            "name": name,
            "mode": mode,
            "region_id": region_id,
            "valid": has_creds,
        })
    return result


def check_env_credentials() -> dict:
    """Detect Alibaba Cloud credential configuration."""
    env_creds = {
        "ak_set": bool(os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")),
        "sk_set": bool(os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")),
        "role_arn": os.environ.get("ALIBABA_CLOUD_ROLE_ARN", ""),
        "region": os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou"),
    }
    cli_config = _read_aliyun_cli_config()
    env_creds["cli_config"] = cli_config
    cli_has_valid = any(p["valid"] for p in cli_config.get("profiles", []))
    env_creds["credentials_ready"] = (env_creds["ak_set"] and env_creds["sk_set"]) or cli_has_valid
    return env_creds


# --- CIDR utility functions -------------------------------------------

def ip_to_int(ip: str) -> int:
    """Convert an IP address to an integer."""
    parts = ip.split(".")
    return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])


def cidr_contains(cidr: str, ip: str) -> bool:
    """Check whether an IP falls within a CIDR range."""
    try:
        if "/" not in cidr:
            return cidr == ip
        network, prefix_len = cidr.split("/")
        prefix_len = int(prefix_len)
        mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
        return (ip_to_int(network) & mask) == (ip_to_int(ip) & mask)
    except (ValueError, IndexError):
        return False


# --- CLI entry point --------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Public network MTR diagnosis common utilities")
    sub = parser.add_subparsers(dest="action")

    sub.add_parser("check-env", help="Detect tool and credential environment")

    p_parse = sub.add_parser("parse-input", help="Parse user input")
    p_parse.add_argument("--input", required=True, help="User input text")

    args = parser.parse_args()

    if args.action == "check-env":
        tools = check_all_tools()
        creds = check_env_credentials()
        result = {"tools": tools, "credentials": creds}
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "parse-input":
        result = parse_input(args.input)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
