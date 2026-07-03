"""
mtr_analyze.py - MTR result parsing and analysis engine

Parses mtr -r text output into structured data, classifies network problems, identifies ISPs,
and supports bidirectional MTR comparison and ICMP/TCP MTR comparison analysis.
"""

import sys
import os
import json
import re
import urllib.request
import urllib.error
import ssl
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mtr_common import _is_private_ip, _is_valid_ipv4, cidr_contains


# --- MTR output parsing -----------------------------------------------

# mtr -r report format: "HOST: hostname  Loss%  Snt  Last  Avg  Best  Wrst  StDev"
# Example line: "  1.|-- 192.168.1.1  0.0%   100   1.2   1.5   0.8   3.2   0.5"
RE_MTR_HOP = re.compile(
    r'^\s*(\d+)\.\|--\s+'     # Hop number
    r'(\S+)\s+'                # Hostname or IP or ???
    r'([\d.]+)%\s+'            # Loss percentage
    r'(\d+)\s+'                # Sent count
    r'([\d.]+)\s+'             # Last
    r'([\d.]+)\s+'             # Avg
    r'([\d.]+)\s+'             # Best
    r'([\d.]+)'                # Worst
    r'(?:\s+([\d.]+))?',       # StDev (optional)
    re.MULTILINE
)

# Alternative format (some mtr versions or WinMTR output format)
# "Hop  Hostname      Loss%  Sent  Last  Avg   Best  Wrst"
RE_MTR_HOP_ALT = re.compile(
    r'^\s*(\d+)\s+'            # Hop number
    r'(\S+)\s+'                # Hostname or IP
    r'([\d.]+)%?\s+'           # Loss percentage
    r'(\d+)\s+'                # Sent count
    r'([\d.]+)\s+'             # Last
    r'([\d.]+)\s+'             # Avg
    r'([\d.]+)\s+'             # Best
    r'([\d.]+)',               # Worst
    re.MULTILINE
)


def parse_mtr_output(raw_text: str) -> List[dict]:
    """
    Parse mtr -r output into structured data.

    Returns:
        list[dict]: Per-hop data, e.g.:
        [{"hop": 1, "hostname": "192.168.1.1", "loss_pct": 0.0,
          "sent": 100, "last": 1.2, "avg": 1.5, "best": 0.8, "worst": 3.2}]
    """
    hops = []

    # Try standard mtr -r format
    matches = RE_MTR_HOP.findall(raw_text)
    if matches:
        for m in matches:
            hops.append({
                "hop": int(m[0]),
                "hostname": m[1],
                "loss_pct": float(m[2]),
                "sent": int(m[3]),
                "last": float(m[4]),
                "avg": float(m[5]),
                "best": float(m[6]),
                "worst": float(m[7]),
                "stdev": float(m[8]) if m[8] else 0.0,
            })
        return hops

    # Try alternative format
    matches = RE_MTR_HOP_ALT.findall(raw_text)
    if matches:
        for m in matches:
            hops.append({
                "hop": int(m[0]),
                "hostname": m[1],
                "loss_pct": float(m[2]),
                "sent": int(m[3]),
                "last": float(m[4]),
                "avg": float(m[5]),
                "best": float(m[6]),
                "worst": float(m[7]),
                "stdev": 0.0,
            })
        return hops

    return hops


def parse_ping_output(raw_text: str) -> dict:
    """
    Parse ping output summary.

    Returns:
        dict: {"packets_sent": int, "packets_received": int,
               "loss_pct": float, "min": float, "avg": float,
               "max": float, "mdev": float}
    """
    result = {
        "packets_sent": 0, "packets_received": 0,
        "loss_pct": 0.0, "min": 0.0, "avg": 0.0,
        "max": 0.0, "mdev": 0.0,
    }

    # Parse loss line: "X packets transmitted, Y received, Z% packet loss"
    loss_match = re.search(
        r'(\d+)\s+packets?\s+transmitted.*?(\d+)\s+received.*?([\d.]+)%\s+packet\s+loss',
        raw_text, re.IGNORECASE
    )
    if loss_match:
        result["packets_sent"] = int(loss_match.group(1))
        result["packets_received"] = int(loss_match.group(2))
        result["loss_pct"] = float(loss_match.group(3))

    # Parse latency line: "rtt min/avg/max/mdev = X/X/X/X ms"
    rtt_match = re.search(
        r'(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*'
        r'([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
        raw_text, re.IGNORECASE
    )
    if rtt_match:
        result["min"] = float(rtt_match.group(1))
        result["avg"] = float(rtt_match.group(2))
        result["max"] = float(rtt_match.group(3))
        result["mdev"] = float(rtt_match.group(4))

    return result


# --- ISP identification -----------------------------------------------

# High-confidence backbone fast-match table (only highly deterministic prefixes)
ISP_FAST_PREFIXES = [
    # China Telecom backbone
    ("202.97.", "China Telecom (Backbone/International Gateway)"),
    ("202.96.", "China Telecom (Backbone)"),
    # China Unicom backbone - 219.158.x.x is Unicom, NOT Telecom
    ("219.158.", "China Unicom (Backbone/International Gateway)"),
    ("221.4.", "China Unicom"),
    # China Mobile backbone
    ("221.183.", "China Mobile"),
    ("223.120.", "China Mobile (International Gateway)"),
    ("223.119.", "China Mobile (International Gateway)"),
    ("111.13.", "China Mobile"),
]

ISP_HOSTNAME_PATTERNS = [
    # China Telecom
    ("chinanet", "China Telecom"),
    ("telecom", "China Telecom"),
    # China Unicom
    ("chinaunicom", "China Unicom"),
    ("unicom", "China Unicom"),
    ("cnc.cn", "China Unicom"),
    # China Mobile
    ("chinamobile", "China Mobile"),
    ("cmcc", "China Mobile"),
    # International ISPs
    ("telia.net", "Telia"),
    ("level3.net", "Level3/Lumen"),
    ("ntt.net", "NTT"),
    ("pccwglobal.net", "PCCW"),
    ("he.net", "Hurricane Electric"),
    ("cogentco.com", "Cogent"),
    ("gtt.net", "GTT"),
]

# ASN -> ISP name mapping (for parsing ipinfo.io org field)
ASN_ISP_MAP = {
    "AS4134": "China Telecom",
    "AS4812": "China Telecom",
    "AS4837": "China Unicom (Backbone)",
    "AS9929": "China Unicom (Premium)",
    "AS4808": "China Unicom",
    "AS9808": "China Mobile",
    "AS58453": "China Mobile (International)",
    "AS56040": "China Mobile",
    "AS37963": "Alibaba Cloud",
    "AS45102": "Alibaba Cloud (International)",
    "AS13335": "Cloudflare",
    "AS16509": "AWS",
    "AS15169": "Google",
    "AS8075": "Microsoft",
    "AS14618": "AWS",
    "AS20940": "Akamai",
}

# org field keywords -> ISP (fallback when ASN doesn't match)
ORG_KEYWORD_MAP = [
    ("CHINANET", "China Telecom"),
    ("ChinaTelecom", "China Telecom"),
    ("China169", "China Unicom"),
    ("UNICOM", "China Unicom"),
    ("CMNET", "China Mobile"),
    ("ChinaMobile", "China Mobile"),
    ("ALIBABA", "Alibaba Cloud"),
    ("Alicloud", "Alibaba Cloud"),
    ("Aliyun", "Alibaba Cloud"),
    ("TENCENT", "Tencent Cloud"),
    ("HUAWEI", "Huawei Cloud"),
]

# Module-level cache and state
_isp_cache: dict = {}
_ipinfo_disabled: bool = False
_ssl_ctx: Optional[ssl.SSLContext] = None


def _get_ssl_ctx() -> ssl.SSLContext:
    """Lazily create SSL context; falls back to unverified on first SSL error."""
    global _ssl_ctx
    if _ssl_ctx is not None:
        return _ssl_ctx
    _ssl_ctx = ssl.create_default_context()
    return _ssl_ctx


def _is_internal_ip(ip: str) -> str:
    """Check whether the IP is a cloud provider/CGNAT internal IP. Returns label or empty string."""
    if not _is_valid_ipv4(ip):
        return ""
    first = int(ip.split(".")[0])
    if first in (10, 11, 30):
        return "Alibaba Cloud Internal"
    if _is_private_ip(ip):
        return ""
    if cidr_contains("100.64.0.0/10", ip):
        return "Alibaba Cloud Internal"
    return ""


def _lookup_ipinfo(ip: str) -> str:
    """Query ipinfo.io and return ISP name. Returns empty string on failure."""
    global _ipinfo_disabled
    if _ipinfo_disabled:
        return ""
    try:
        req = urllib.request.Request(
            f"https://ipinfo.io/{ip}/json",
            headers={"Accept": "application/json", "User-Agent": "mtr-diag/1.0"},
        )
        with urllib.request.urlopen(req, timeout=3, context=_get_ssl_ctx()) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.URLError as e:
        # SSL certificate verification failure (common on macOS Python), fall back to unverified
        if isinstance(e.reason, ssl.SSLCertVerificationError):
            global _ssl_ctx
            _ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            _ssl_ctx.check_hostname = False
            _ssl_ctx.verify_mode = ssl.CERT_NONE
            try:
                req = urllib.request.Request(
                    f"https://ipinfo.io/{ip}/json",
                    headers={"Accept": "application/json", "User-Agent": "mtr-diag/1.0"},
                )
                with urllib.request.urlopen(req, timeout=3, context=_ssl_ctx) as resp:
                    data = json.loads(resp.read().decode())
            except Exception:
                return ""
        else:
            return ""
    except urllib.error.HTTPError as e:
        if e.code == 429:
            _ipinfo_disabled = True
        return ""
    except Exception:
        return ""

    org = data.get("org", "")
    if not org:
        return ""
    # 1) Exact ASN match
    asn_match = re.match(r"(AS\d+)", org)
    if asn_match and asn_match.group(1) in ASN_ISP_MAP:
        return ASN_ISP_MAP[asn_match.group(1)]
    # 2) org keyword match
    org_upper = org.upper()
    for kw, isp in ORG_KEYWORD_MAP:
        if kw.upper() in org_upper:
            return isp
    # 3) Return raw org (strip ASN prefix)
    return re.sub(r"^AS\d+\s*", "", org).strip()


def prefetch_isp(hops: List[dict]) -> None:
    """Batch-prefetch ISP information for all hops, concurrently populating the cache."""
    ips_to_lookup = []
    for h in hops:
        ip = h.get("hostname", "")
        if ip in ("???", "*", "") or ip in _isp_cache:
            continue
        if not _is_valid_ipv4(ip):
            continue
        if _is_private_ip(ip) or _is_internal_ip(ip):
            continue
        matched = any(ip.startswith(p) for p, _ in ISP_FAST_PREFIXES)
        if not matched and ip not in ips_to_lookup:
            ips_to_lookup.append(ip)

    if not ips_to_lookup:
        return
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_lookup_ipinfo, ip): ip for ip in ips_to_lookup}
        for fut in as_completed(futures):
            ip = futures[fut]
            _isp_cache[ip] = fut.result()


def identify_isp(hostname: str) -> str:
    """
    Identify the ISP based on IP address or hostname.

    Priority: skip placeholders -> internal IP -> backbone fast match -> cache -> ipinfo.io API -> hostname pattern -> empty

    Args:
        hostname: IP address or hostname

    Returns:
        str: ISP name, empty string if unknown
    """
    if hostname in ("???", "*", ""):
        return ""

    # Check whether it's an IPv4 address
    is_ipv4 = _is_valid_ipv4(hostname)

    if is_ipv4:
        # RFC1918 private -> no label
        if _is_private_ip(hostname):
            return ""

        # Alibaba Cloud/CGNAT internal
        internal = _is_internal_ip(hostname)
        if internal:
            return internal

        # Backbone fast prefix match
        for prefix, isp in ISP_FAST_PREFIXES:
            if hostname.startswith(prefix):
                return isp

        # Cache hit
        if hostname in _isp_cache:
            return _isp_cache[hostname]

        # ipinfo.io query
        result = _lookup_ipinfo(hostname)
        _isp_cache[hostname] = result
        if result:
            return result

    # Hostname pattern match (fallback)
    hostname_lower = hostname.lower()
    for pattern, isp in ISP_HOSTNAME_PATTERNS:
        if pattern in hostname_lower:
            return isp

    return ""


# --- Problem classification -------------------------------------------

def classify_problem(hops: List[dict]) -> dict:
    """
    Analyze MTR hop data and classify network problems.

    Returns:
        dict: {
            "pattern": str,  # local/isp_access/backbone/destination/icmp_ratelimit/route_detour/normal
            "severity": str, # critical/warning/normal
            "problem_hop": int or None,
            "description": str,
            "suggestion": str,
            "details": list[str]
        }
    """
    if not hops:
        return {
            "pattern": "no_data",
            "severity": "warning",
            "problem_hop": None,
            "description": "No MTR data available for analysis",
            "suggestion": "Please verify that MTR was executed correctly",
            "details": [],
        }

    total_hops = len(hops)
    last_hop = hops[-1]
    details = []

    # Check packet loss and latency for each hop
    high_loss_hops = [h for h in hops if h["loss_pct"] > 5.0]
    persistent_loss_start = None

    for i, hop in enumerate(hops):
        if hop["loss_pct"] > 5.0:
            # Check whether subsequent hops show persistent loss
            subsequent_loss = all(
                h["loss_pct"] > 3.0 for h in hops[i:]
            )
            if subsequent_loss and persistent_loss_start is None:
                persistent_loss_start = i
            break

    # Pattern 1: Local network issue - persistent loss starting from hop 1-2
    if persistent_loss_start is not None and persistent_loss_start <= 1:
        return {
            "pattern": "local",
            "severity": "critical",
            "problem_hop": hops[persistent_loss_start]["hop"],
            "description": f"Persistent packet loss ({hops[persistent_loss_start]['loss_pct']}%) "
                           f"starting from hop {hops[persistent_loss_start]['hop']} "
                           f"({hops[persistent_loss_start]['hostname']}), "
                           f"likely a local network issue",
            "suggestion": "Check local network connection, WiFi signal, cable/interface, and local router load",
            "details": [f"Hop {h['hop']}: {h['hostname']} - {h['loss_pct']}% loss" for h in high_loss_hops],
        }

    # Pattern 5: ICMP rate limiting (false packet loss) - intermediate hop loss that recovers
    icmp_ratelimit_hops = []
    for i, hop in enumerate(hops):
        if hop["loss_pct"] > 10.0 and i < total_hops - 1:
            # Subsequent hops recover to low loss levels
            subsequent = hops[i + 1:]
            if subsequent and all(h["loss_pct"] < 3.0 for h in subsequent):
                icmp_ratelimit_hops.append(hop)

    if icmp_ratelimit_hops and last_hop["loss_pct"] < 3.0:
        return {
            "pattern": "icmp_ratelimit",
            "severity": "normal",
            "problem_hop": None,
            "description": "ICMP rate limiting at intermediate nodes (not real packet loss): " +
                           ", ".join(f"hop {h['hop']} {h['hostname']} shows {h['loss_pct']}% loss"
                                    for h in icmp_ratelimit_hops) +
                           f", but final destination loss is only {last_hop['loss_pct']}%",
            "suggestion": "This is normal behavior - intermediate routers are rate-limiting ICMP probe packets. Focus on the final destination loss rate",
            "details": [f"Hop {h['hop']}: {h['hostname']} - {h['loss_pct']}% loss (ICMP rate limiting)"
                        for h in icmp_ratelimit_hops],
        }

    # Pattern 4: Destination issue - only the last few hops show loss
    if last_hop["loss_pct"] > 5.0:
        # Check whether preceding hops are normal
        if persistent_loss_start is not None and persistent_loss_start >= total_hops - 2:
            return {
                "pattern": "destination",
                "severity": "warning" if last_hop["loss_pct"] < 20 else "critical",
                "problem_hop": last_hop["hop"],
                "description": f"Last hop ({last_hop['hostname']}) shows {last_hop['loss_pct']}% packet loss, "
                               f"preceding link is normal. Likely a target server or ingress network issue",
                "suggestion": "Contact the target service provider. Possible causes: high server load, firewall restrictions, or ingress congestion",
                "details": [f"Final destination: {last_hop['hostname']} - {last_hop['loss_pct']}% loss, "
                            f"{last_hop['avg']}ms latency"],
            }

    # Pattern 2: ISP access issue - persistent loss starting from hop 2-4
    if persistent_loss_start is not None and 2 <= persistent_loss_start <= 4:
        problem = hops[persistent_loss_start]
        isp = identify_isp(problem["hostname"])
        isp_text = f" ({isp})" if isp else ""
        return {
            "pattern": "isp_access",
            "severity": "critical",
            "problem_hop": problem["hop"],
            "description": f"Persistent packet loss ({problem['loss_pct']}%) starting from "
                           f"hop {problem['hop']}{isp_text} ({problem['hostname']}), "
                           f"likely an ISP access layer issue",
            "suggestion": "Contact your local ISP to report the issue and inquire about regional network outages",
            "details": [f"Hop {h['hop']}: {h['hostname']} - {h['loss_pct']}% loss" for h in high_loss_hops],
        }

    # Pattern 3: Backbone issue - high loss at intermediate hops
    if persistent_loss_start is not None and persistent_loss_start > 4:
        problem = hops[persistent_loss_start]
        isp = identify_isp(problem["hostname"])
        isp_text = f" ({isp})" if isp else ""
        return {
            "pattern": "backbone",
            "severity": "critical",
            "problem_hop": problem["hop"],
            "description": f"Persistent packet loss ({problem['loss_pct']}%) starting from "
                           f"hop {problem['hop']}{isp_text} ({problem['hostname']}), "
                           f"likely backbone congestion or failure",
            "suggestion": "Wait for ISP repair, or try using a proxy/VPN to bypass the problematic node",
            "details": [f"Hop {h['hop']}: {h['hostname']} - {h['loss_pct']}% loss" for h in high_loss_hops],
        }

    # Pattern 6: Route detour - sudden large latency increase
    for i in range(1, len(hops)):
        latency_jump = hops[i]["avg"] - hops[i - 1]["avg"]
        if latency_jump > 50:
            isp = identify_isp(hops[i]["hostname"])
            isp_text = f" ({isp})" if isp else ""
            details.append(
                f"Hop {hops[i]['hop']}{isp_text}: latency jumped from {hops[i-1]['avg']}ms to "
                f"{hops[i]['avg']}ms (increase of {latency_jump:.1f}ms)"
            )

    if details and not high_loss_hops:
        return {
            "pattern": "route_detour",
            "severity": "warning",
            "problem_hop": None,
            "description": "Route detour detected with significant latency jumps: " + "; ".join(details),
            "suggestion": "This may be a route detour (longer path), international link, or node congestion. "
                          "Compare MTR results from different time periods to confirm if this is temporary",
            "details": details,
        }

    # Normal
    return {
        "pattern": "normal",
        "severity": "normal",
        "problem_hop": None,
        "description": f"Link is normal. Final destination loss: {last_hop['loss_pct']}%, latency: {last_hop['avg']}ms",
        "suggestion": "Link is healthy, no action needed",
        "details": [],
    }


# --- Bidirectional analysis -------------------------------------------

def analyze_bidirectional(forward_hops: List[dict],
                          reverse_hops: List[dict]) -> dict:
    """
    Compare forward and reverse MTR results to detect asymmetric routing and directional issues.

    Returns:
        dict: {
            "forward_analysis": dict,
            "reverse_analysis": dict,
            "asymmetric_routing": bool,
            "problem_direction": str,  # "forward"/"reverse"/"both"/"none"
            "summary": str,
            "details": list[str]
        }
    """
    forward_result = classify_problem(forward_hops)
    reverse_result = classify_problem(reverse_hops)

    details = []
    asymmetric = False
    problem_direction = "none"

    # Check for asymmetric routing (forward and reverse paths differ)
    if forward_hops and reverse_hops:
        forward_isps = set()
        reverse_isps = set()
        for h in forward_hops:
            isp = identify_isp(h["hostname"])
            if isp:
                forward_isps.add(isp)
        for h in reverse_hops:
            isp = identify_isp(h["hostname"])
            if isp:
                reverse_isps.add(isp)

        if forward_isps != reverse_isps and forward_isps and reverse_isps:
            asymmetric = True
            details.append(
                f"Forward path ISPs: {', '.join(forward_isps)}; "
                f"Reverse path ISPs: {', '.join(reverse_isps)}"
            )

    # Determine problem direction
    forward_ok = forward_result["severity"] == "normal"
    reverse_ok = reverse_result["severity"] == "normal"

    if not forward_ok and not reverse_ok:
        problem_direction = "both"
    elif not forward_ok:
        problem_direction = "forward"
    elif not reverse_ok:
        problem_direction = "reverse"

    # Generate summary
    if problem_direction == "none":
        summary = "Both forward and reverse links are normal"
    elif problem_direction == "forward":
        summary = f"Forward link abnormal ({forward_result['pattern']}), reverse link normal"
    elif problem_direction == "reverse":
        summary = f"Reverse link abnormal ({reverse_result['pattern']}), forward link normal"
    else:
        summary = f"Both links abnormal: forward {forward_result['pattern']}, reverse {reverse_result['pattern']}"

    if asymmetric:
        summary += ". Asymmetric routing detected (forward and reverse paths differ)"

    return {
        "forward_analysis": forward_result,
        "reverse_analysis": reverse_result,
        "asymmetric_routing": asymmetric,
        "problem_direction": problem_direction,
        "summary": summary,
        "details": details,
    }


# --- ICMP vs TCP comparison -------------------------------------------

def compare_icmp_vs_tcp(icmp_hops: List[dict],
                        tcp_hops: List[dict]) -> dict:
    """
    Compare ICMP MTR and TCP MTR results.

    Returns:
        dict: {
            "icmp_analysis": dict,
            "tcp_analysis": dict,
            "icmp_filtered": bool,      # ICMP filtered/rate-limited
            "tcp_port_blocked": bool,    # TCP port blocked
            "summary": str,
            "recommendation": str
        }
    """
    icmp_result = classify_problem(icmp_hops)
    tcp_result = classify_problem(tcp_hops)

    icmp_last_loss = icmp_hops[-1]["loss_pct"] if icmp_hops else 0
    tcp_last_loss = tcp_hops[-1]["loss_pct"] if tcp_hops else 0

    icmp_filtered = False
    tcp_port_blocked = False

    # High ICMP loss but normal TCP -> ICMP filtered
    if icmp_last_loss > 10 and tcp_last_loss < 3:
        icmp_filtered = True
        summary = (f"ICMP loss {icmp_last_loss}% but TCP loss only {tcp_last_loss}%. "
                   f"ICMP is being filtered by firewall or ACL; actual service link is normal")
        recommendation = "Use TCP MTR results as the reference. ICMP loss is caused by firewall policy"
    # High TCP loss but normal ICMP -> port blocked
    elif tcp_last_loss > 10 and icmp_last_loss < 3:
        tcp_port_blocked = True
        summary = (f"TCP loss {tcp_last_loss}% but ICMP loss only {icmp_last_loss}%. "
                   f"The target port may be blocked by firewall or security group")
        recommendation = "Check whether the target security group/firewall allows the corresponding TCP port"
    # Both show loss -> real link issue
    elif icmp_last_loss > 10 and tcp_last_loss > 10:
        summary = (f"Both ICMP and TCP show packet loss (ICMP: {icmp_last_loss}%, TCP: {tcp_last_loss}%). "
                   f"This is likely a real link issue")
        recommendation = "Refer to the MTR analysis results to locate the specific problem node"
    else:
        summary = f"ICMP and TCP results are consistent. Link is normal (ICMP: {icmp_last_loss}%, TCP: {tcp_last_loss}%)"
        recommendation = "Link is healthy"

    return {
        "icmp_analysis": icmp_result,
        "tcp_analysis": tcp_result,
        "icmp_filtered": icmp_filtered,
        "tcp_port_blocked": tcp_port_blocked,
        "summary": summary,
        "recommendation": recommendation,
    }


# --- Report generation ------------------------------------------------

def generate_report(data_dir: str) -> dict:
    """
    Read all JSON results from the data directory and generate a comprehensive diagnostic report.

    Args:
        data_dir: Data directory path (containing forward_mtr.json, reverse_mtr.json, etc.)

    Returns:
        dict: Comprehensive report
    """
    report = {
        "conclusion": "",
        "severity": "normal",
        "forward_analysis": None,
        "reverse_analysis": None,
        "bidirectional_analysis": None,
        "icmp_tcp_comparison": None,
        "isp_path": [],
        "recommendations": [],
    }

    # Read forward MTR
    forward_file = os.path.join(data_dir, "forward_mtr.json")
    forward_data = None
    if os.path.isfile(forward_file):
        with open(forward_file, "r", encoding="utf-8") as f:
            forward_data = json.load(f)

    # Read reverse MTR
    reverse_file = os.path.join(data_dir, "reverse_mtr.json")
    reverse_data = None
    if os.path.isfile(reverse_file):
        with open(reverse_file, "r", encoding="utf-8") as f:
            reverse_data = json.load(f)

    # Parse MTR output
    forward_hops = []
    reverse_hops = []
    icmp_hops = []
    tcp_hops = []

    if forward_data:
        icmp_text = forward_data.get("icmp_mtr", "")
        tcp_text = forward_data.get("tcp_mtr", "")
        forward_hops = parse_mtr_output(icmp_text)
        icmp_hops = forward_hops
        if tcp_text:
            tcp_hops = parse_mtr_output(tcp_text)

        # ISP path
        for h in forward_hops:
            isp = identify_isp(h["hostname"])
            if isp and (not report["isp_path"] or report["isp_path"][-1] != isp):
                report["isp_path"].append(isp)

    if reverse_data:
        reverse_hops = parse_mtr_output(reverse_data.get("icmp_mtr", ""))

    # Batch-prefetch ISP info for all hops
    prefetch_isp(forward_hops + reverse_hops + tcp_hops)

    # Analysis
    if forward_hops:
        report["forward_analysis"] = classify_problem(forward_hops)

    if reverse_hops:
        report["reverse_analysis"] = classify_problem(reverse_hops)

    # Bidirectional comparison
    if forward_hops and reverse_hops:
        report["bidirectional_analysis"] = analyze_bidirectional(forward_hops, reverse_hops)

    # ICMP vs TCP comparison
    if icmp_hops and tcp_hops:
        report["icmp_tcp_comparison"] = compare_icmp_vs_tcp(icmp_hops, tcp_hops)

    # Overall conclusion
    severities = []
    if report["forward_analysis"]:
        severities.append(report["forward_analysis"]["severity"])
        if report["forward_analysis"]["suggestion"]:
            report["recommendations"].append(f"[Forward] {report['forward_analysis']['suggestion']}")
    if report["reverse_analysis"]:
        severities.append(report["reverse_analysis"]["severity"])
        if report["reverse_analysis"]["suggestion"]:
            report["recommendations"].append(f"[Reverse] {report['reverse_analysis']['suggestion']}")
    if report["icmp_tcp_comparison"]:
        if report["icmp_tcp_comparison"]["recommendation"]:
            report["recommendations"].append(
                f"[ICMP/TCP] {report['icmp_tcp_comparison']['recommendation']}")

    if "critical" in severities:
        report["severity"] = "critical"
    elif "warning" in severities:
        report["severity"] = "warning"

    # Generate conclusion text
    if report["bidirectional_analysis"]:
        report["conclusion"] = report["bidirectional_analysis"]["summary"]
    elif report["forward_analysis"]:
        report["conclusion"] = report["forward_analysis"]["description"]
    else:
        report["conclusion"] = "No valid data available for analysis"

    return report


# --- CLI entry point --------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="MTR result analysis engine")
    sub = parser.add_subparsers(dest="action")

    # parse: parse raw MTR text
    p_parse = sub.add_parser("parse", help="Parse MTR text output")
    p_parse.add_argument("--input", required=True, help="Raw MTR text (can be a file path or text content)")

    # analyze: analyze MTR result files
    p_analyze = sub.add_parser("analyze", help="Analyze MTR results")
    p_analyze.add_argument("--forward", required=True, help="Forward MTR result JSON file")
    p_analyze.add_argument("--reverse", default=None, help="Reverse MTR result JSON file (optional)")

    # report: generate comprehensive report
    p_report = sub.add_parser("report", help="Generate comprehensive diagnostic report")
    p_report.add_argument("--dir", required=True, help="Data directory path")

    args = parser.parse_args()

    if args.action == "parse":
        # If input is a file path, read the file
        text = args.input
        if os.path.isfile(text):
            with open(text, "r", encoding="utf-8") as f:
                text = f.read()
        hops = parse_mtr_output(text)
        prefetch_isp(hops)
        result = {
            "hops": hops,
            "analysis": classify_problem(hops),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "analyze":
        # Read forward results
        with open(args.forward, "r", encoding="utf-8") as f:
            forward_data = json.load(f)
        forward_hops = parse_mtr_output(forward_data.get("icmp_mtr", ""))

        # Batch-prefetch ISP info for all hops
        all_hops = list(forward_hops)
        reverse_hops = []
        if args.reverse:
            with open(args.reverse, "r", encoding="utf-8") as f:
                reverse_data = json.load(f)
            reverse_hops = parse_mtr_output(reverse_data.get("icmp_mtr", ""))
            all_hops.extend(reverse_hops)
        tcp_text = forward_data.get("tcp_mtr", "")
        if tcp_text:
            all_hops.extend(parse_mtr_output(tcp_text))
        prefetch_isp(all_hops)

        result = {"forward_analysis": classify_problem(forward_hops)}

        # If reverse results are available
        if reverse_hops:
            result["reverse_analysis"] = classify_problem(reverse_hops)
            result["bidirectional"] = analyze_bidirectional(forward_hops, reverse_hops)

        # If TCP MTR is available
        if tcp_text:
            tcp_hops = parse_mtr_output(tcp_text)
            if tcp_hops:
                result["icmp_tcp_comparison"] = compare_icmp_vs_tcp(forward_hops, tcp_hops)

        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "report":
        result = generate_report(args.dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
