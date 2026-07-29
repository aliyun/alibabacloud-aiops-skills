"""
dns_common.py - DNS diagnosis shared utilities

Provides domain splitting, data structure definitions, environment detection, and other common functions.
"""

import sys
if sys.version_info < (3, 7):
    import json as _json
    import subprocess as _sp
    # Try to detect higher version Python in the system
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

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional


# ─── Public suffix list (common multi-segment TLDs) ─────────────────────────────
# Used for correct domain level splitting, avoiding misidentification of .com.cn / .co.uk etc.
MULTI_SEGMENT_TLDS = frozenset({
    # China
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn", "ac.cn",
    "mil.cn", "ah.cn", "bj.cn", "cq.cn", "fj.cn", "gd.cn",
    "gs.cn", "gz.cn", "gx.cn", "ha.cn", "hb.cn", "he.cn",
    "hi.cn", "hk.cn", "hl.cn", "hn.cn", "jl.cn", "js.cn",
    "jx.cn", "ln.cn", "mo.cn", "nm.cn", "nx.cn", "qh.cn",
    "sc.cn", "sd.cn", "sh.cn", "sn.cn", "sx.cn", "tj.cn",
    "tw.cn", "xj.cn", "xz.cn", "yn.cn", "zj.cn",
    # UK
    "co.uk", "org.uk", "me.uk", "net.uk", "ac.uk", "gov.uk",
    "ltd.uk", "plc.uk", "sch.uk",
    # Japan
    "co.jp", "ac.jp", "ne.jp", "or.jp", "go.jp", "ed.jp",
    # Australia
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    # Brazil
    "com.br", "net.br", "org.br", "gov.br",
    # India
    "co.in", "net.in", "org.in", "gen.in", "firm.in", "ind.in",
    # South Korea
    "co.kr", "ne.kr", "or.kr", "re.kr", "pe.kr",
    # Other common
    "com.hk", "org.hk", "edu.hk", "gov.hk",
    "com.tw", "org.tw", "edu.tw", "gov.tw",
    "com.sg", "org.sg", "edu.sg", "gov.sg",
    "com.my", "net.my", "org.my", "gov.my",
    "co.nz", "net.nz", "org.nz",
    "co.za", "org.za", "web.za",
    "com.ru", "net.ru", "org.ru",
    "co.id", "web.id", "or.id",
    "com.vn", "net.vn", "org.vn",
    "com.ph", "net.ph", "org.ph",
    "co.th", "in.th", "or.th",
})

# Alibaba Cloud DNS server signature identifiers
ALICLOUD_NS_PATTERNS = (
    "alidns.com",
    "hichina.com",
    "alibabacloud.com",
    "aliyun.com",
)


# ─── Data structures ──────────────────────────────────────────────────────

@dataclass
class DomainCandidate:
    """Domain split candidate"""
    zone: str   # Predicted root domain, e.g. "example.com"
    rr: str     # Host record, e.g. "www", "@", "*"


@dataclass
class CheckResult:
    """Single check result"""
    name: str                          # Check item name
    status: str                        # ok / warning / critical / error / skipped
    summary: str                       # One-line conclusion
    details: Optional[str] = None      # Detailed information
    suggestion: Optional[str] = None   # Fix suggestion


@dataclass
class Discrepancy:
    """Config vs probing inconsistency item"""
    description: str
    expected: str       # Expected value from authoritative config
    actual: str         # Actual value from probing
    affected_regions: list = field(default_factory=list)
    severity: str = "warning"  # warning / critical


@dataclass
class DiagnosisResult:
    """Final diagnosis result"""
    checks: list = field(default_factory=list)            # list[CheckResult]
    discrepancies: list = field(default_factory=list)      # list[Discrepancy]
    root_causes: list = field(default_factory=list)        # list[str]
    suggestions: list = field(default_factory=list)        # list[str]
    severity: str = "normal"  # critical / warning / info / normal


@dataclass
class DomainDiagContext:
    """Context data shared across the whole diagnosis flow"""
    domain: str                                             # Original input domain
    problem_description: str = ""                           # Problem described by the user
    candidates: list = field(default_factory=list)          # list[DomainCandidate]
    product_type: str = "unknown"                           # public_dns/gtm/privatezone/third_party
    # Phase 3 results
    whois_result: Optional[dict] = None
    ns_records: list = field(default_factory=list)
    trace_result: Optional[str] = None
    multi_server_results: Optional[dict] = None
    # Phase 4 results
    config_records: list = field(default_factory=list)      # Authoritative DNS records
    domain_info: Optional[dict] = None                      # DescribeDomainInfo result
    gtm_info: Optional[dict] = None                         # GTM instance info
    privatezone_info: Optional[dict] = None                 # PrivateZone info
# Phase 5 results
    dns_probe_result: Optional[dict] = None
    http_probe_result: Optional[dict] = None
# Internal platform query results (internal edition only)
    internal_records: Optional[list] = None


# ─── Domain splitting ──────────────────────────────────────────────────────

def _extract_tld(domain: str) -> tuple:
    """
    Extract the TLD part and remaining parts of a domain.

    Returns:
        (tld, remaining_parts) - e.g. ("com.cn", ["www", "example"])
    """
    parts = domain.lower().rstrip(".").split(".")

    if len(parts) < 2:
        return domain, []

# Try matching multi-segment TLD (start from 2 segments)
    for i in range(2, min(len(parts), 4)):
        candidate_tld = ".".join(parts[-i:])
        if candidate_tld in MULTI_SEGMENT_TLDS:
            return candidate_tld, parts[:-i]

# Default single-segment TLD
    return parts[-1], parts[:-1]


def split_domain(domain: str) -> list:
    """
    Split a full domain into multiple predicted candidates.

    For example, input "aaa.ce.boce.cn.com" outputs:
    - zone=cn.com,           rr=aaa.ce.boce
    - zone=boce.cn.com,      rr=aaa.ce
    - zone=ce.boce.cn.com,   rr=aaa
    - zone=aaa.ce.boce.cn.com, rr=@

    Returns:
        list[DomainCandidate]
    """
    domain = domain.lower().rstrip(".")
    tld, remaining = _extract_tld(domain)

    if not remaining:
# Input is already a bare domain, e.g. "cn.com"
        return [DomainCandidate(zone=domain, rr="@")]

    candidates = []

# Start from shortest root domain, extend gradually
    # remaining = ["aaa", "ce", "boce"], tld = "cn.com"
    for i in range(len(remaining)):
        zone_parts = remaining[i:] + [tld]
        zone = ".".join(zone_parts)

        if i == 0:
            rr = "@" if len(remaining) == 1 else ".".join(remaining[:i]) or "@"
# This is the most complete domain itself
            pass
        rr_parts = remaining[:i]
        rr = ".".join(rr_parts) if rr_parts else "@"

        candidates.append(DomainCandidate(zone=zone, rr=rr))

# Finally add the full domain itself (rr=@)
    if candidates and candidates[-1].rr != "@":
        candidates.append(DomainCandidate(zone=domain, rr="@"))

# Deduplicate
    seen = set()
    unique = []
    for c in candidates:
        key = (c.zone, c.rr)
        if key not in seen:
            seen.add(key)
            unique.append(c)

# Sort by zone from short to long (more likely match first)
    unique.sort(key=lambda c: len(c.zone))

    return unique


# ─── Product type determination ───────────────────────────────────────────────────

def is_alicloud_ns(ns_list: list) -> bool:
    """Determine whether NS records point to Alibaba Cloud DNS"""
    for ns in ns_list:
        ns_lower = ns.lower().rstrip(".")
        if any(pattern in ns_lower for pattern in ALICLOUD_NS_PATTERNS):
            return True
    return False


def detect_product_type(ns_records: list, api_results: dict = None) -> str:
    """
    Determine product type from NS records and API query results.

    Args:
        ns_records: dig NS query results
        api_results: dict with keys "domains", "gtm_instances", "pvtz_zones"

    Returns:
        "public_dns" / "gtm" / "privatezone" / "third_party" / "third_party_with_alicloud_domain"
    """
    api_results = api_results or {}

    if is_alicloud_ns(ns_records):
# NS points to Alibaba Cloud, further determine if GTM or standard DNS
        if api_results.get("gtm_instances"):
            return "gtm"
        if api_results.get("pvtz_zones"):
            return "privatezone"
        return "public_dns"
    else:
# NS is not Alibaba Cloud
        if api_results.get("domains"):
            return "third_party_with_alicloud_domain"
        return "third_party"


# ─── Environment detection ──────────────────────────────────────────────────────

TOOL_INSTALL_GUIDES = {
    "dig": {
        "darwin": "macOS has dig built-in. If issues: brew install bind",
        "linux": "Ubuntu/Debian: sudo apt install dnsutils\nCentOS/RHEL: sudo yum install bind-utils",
        "win32": "Windows: install BIND toolkit, or use nslookup instead",
    },
    "whois": {
        "darwin": "macOS has whois built-in. If issues: brew install whois",
        "linux": "Ubuntu/Debian: sudo apt install whois\nCentOS/RHEL: sudo yum install whois",
        "win32": "Windows: use OpenAPI as whois alternative",
    },
    "aliyun": {
        "darwin": "brew install aliyun-cli\nor visit: https://help.aliyun.com/document_detail/139508.html",
        "linux": "See: https://help.aliyun.com/document_detail/139508.html or use: wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz && tar xzf aliyun-cli-linux-latest-amd64.tgz && mkdir -p ~/.local/bin && mv aliyun ~/.local/bin/",
        "win32": "Visit: https://help.aliyun.com/document_detail/139508.html",
    },
    "playwright": {
        "all": "pip install playwright && playwright install chromium",
    },
}


def check_tool(name: str) -> tuple:
    """
    Check whether a tool is available.

    Args:
        name: tool name ("dig", "whois", "aliyun", "playwright")

    Returns:
        (is_available: bool, install_guide: str)
    """
    if name == "playwright":
        try:
            import playwright  # noqa: F401
            return True, ""
        except ImportError:
            guide = TOOL_INSTALL_GUIDES["playwright"]["all"]
            return False, guide

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
    """
    Check availability of all required tools (including Python version check).

    Returns:
        dict: {tool_name: {"available": bool, "guide": str, ...}}
    """
    tools = {}
    # Python version detection
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    meets_min = sys.version_info >= (3, 7)
    tools["python"] = {
        "available": meets_min,
        "version": py_ver,
        "guide": "" if meets_min else "Python >= 3.7 required. macOS: brew install python@3.11; Linux: apt install python3.11",
    }
    for name in ("dig", "whois", "aliyun", "playwright"):
        available, guide = check_tool(name)
        tools[name] = {"available": available, "guide": guide}
    return tools


def check_env_credentials() -> dict:
    """
    Check Alibaba Cloud credential environment variables.

    Returns:
        dict with keys: ak_set, sk_set, role_arn, region
    """
    return {
        "ak_set": bool(os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")),
        "sk_set": bool(os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")),
        "role_arn": os.environ.get("ALIBABA_CLOUD_ROLE_ARN", ""),
        "region": os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou"),
    }


# ─── CLI entry point ──────────────────────────────────────────────────────

def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="DNS diagnosis common utilities")
    sub = parser.add_subparsers(dest="action")

    # Domain splitting
    p_split = sub.add_parser("split", help="Split domain into predicted candidate list")
    p_split.add_argument("--domain", required=True, help="Full domain")

    # Environment detection
    sub.add_parser("check-env", help="Check tool and credential environment")

    args = parser.parse_args()

    if args.action == "split":
        candidates = split_domain(args.domain)
        result = [{"zone": c.zone, "rr": c.rr} for c in candidates]
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "check-env":
        tools = check_all_tools()
        creds = check_env_credentials()
        result = {"tools": tools, "credentials": creds}
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
