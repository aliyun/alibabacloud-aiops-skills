"""
dns_analyze.py - DNS diagnostic data analysis script.

Automatically extracts and analyzes JSON data from each diagnostic step,
reducing manual reading of large raw datasets.

Usage:
    # Analyze quick_check output (step 0)
    python3 dns_quick_check.py --domain xxx | python3 dns_analyze.py quick

    # Analyze probe output (step 2)
    python3 dns_boce.py dns --domain xxx > /tmp/dns.json
    python3 dns_boce.py http --url xxx > /tmp/http.json
    python3 dns_analyze.py probe --dns /tmp/dns.json --http /tmp/http.json

    # Full analysis (step 3, all data combined)
    python3 dns_analyze.py all --quick /tmp/quick.json --dns /tmp/dns.json --http /tmp/http.json

Output: Condensed analysis JSON with findings, issues, severity, recommendations
"""

import json
import sys
import os


# --- quick_check analysis ---

def analyze_quick(data: dict) -> dict:
    """
    Analyze quick_check.py output and extract key findings.

    Returns:
        dict: {
            "env_status": str,          # "ready" / "missing_tools"
            "missing_tools": [str],
            "credentials": str,         # "ready" / "no_credentials" / "with_role"
            "domain": str,
            "root_domain": str,
            "product_type": str,
            "ns_servers": [str],
            "whois_summary": str,
            "whois_issues": [str],
            "trace_ok": bool,
            "trace_issues": [str],
            "health_consistent": bool,
            "health_ips": {ip: [server_names]},
            "issues": [{severity, title, detail, suggestion}],
        }
    """
    result = {
        "domain": data.get("summary", {}).get("domain", ""),
        "root_domain": data.get("summary", {}).get("root_domain", ""),
        "issues": [],
    }

    # -- Environment --
    env = data.get("env", {})
    tools = env.get("tools", {})
    missing = [t for t, info in tools.items() if not info.get("available")]
    result["env_status"] = "ready" if not missing else "missing_tools"
    result["missing_tools"] = missing

    creds = env.get("credentials", {})
    if creds.get("has_credentials"):
        result["credentials"] = "with_role" if creds.get("role_arn") else "ready"
    else:
        result["credentials"] = "no_credentials"

    if missing:
        result["issues"].append({
            "severity": "warning",
            "title": "Missing tools",
            "detail": f"Missing: {', '.join(missing)}",
            "suggestion": "Install missing tools per SKILL.md prerequisites",
        })

    # -- NS / product type --
    ns_info = data.get("ns", {})
    result["product_type"] = ns_info.get("product_type", "unknown")
    result["ns_servers"] = ns_info.get("records", [])

    # -- WHOIS --
    whois = data.get("whois", {})
    expiry = whois.get("expiry_check", {})
    dangerous = whois.get("dangerous_statuses", [])

    if expiry.get("status") == "critical":
        result["whois_summary"] = f"Expired ({expiry.get('summary', '')})"
        result["issues"].append({
            "severity": "critical",
            "title": "Domain expired",
            "detail": expiry.get("summary", ""),
            "suggestion": "Renew domain immediately",
        })
    elif expiry.get("status") == "warning":
        result["whois_summary"] = f"Expiring soon ({expiry.get('summary', '')})"
        result["issues"].append({
            "severity": "warning",
            "title": "Domain expiring soon",
            "detail": expiry.get("summary", ""),
            "suggestion": "Renew domain as soon as possible",
        })
    elif expiry.get("status") == "ok":
        result["whois_summary"] = f"Normal ({expiry.get('days_remaining', '?')} days remaining)"
    else:
        result["whois_summary"] = expiry.get("summary", "Unknown")

    result["whois_issues"] = []
    for ds in dangerous:
        result["whois_issues"].append(ds.get("status_code", ""))
        result["issues"].append({
            "severity": "critical",
            "title": f"Dangerous domain status: {ds.get('status_code', '')}",
            "detail": ds.get("meaning", ""),
            "suggestion": ds.get("suggestion", ""),
        })

    # -- Trace --
    trace = data.get("trace", {})
    result["trace_ok"] = trace.get("ok", True)
    result["trace_issues"] = []
    if trace.get("has_servfail"):
        result["trace_issues"].append("SERVFAIL")
    if trace.get("has_refused"):
        result["trace_issues"].append("REFUSED")
    if trace.get("has_timeout"):
        result["trace_issues"].append("timeout")

    if result["trace_issues"]:
        result["issues"].append({
            "severity": "critical",
            "title": "Recursive trace anomaly",
            "detail": f"Trace chain contains: {', '.join(result['trace_issues'])}",
            "suggestion": "Check NS server status and domain delegation",
        })

    # -- Health --
    health = data.get("health", {})
    result["health_consistent"] = health.get("consistent", True)
    result["health_all_empty"] = health.get("all_empty", False)

    health_ips = {}
    for server_name, values in health.get("results", {}).items():
        for v in values:
            if _is_ip(v):
                health_ips.setdefault(v, []).append(server_name)
    result["health_ips"] = health_ips

    if health.get("all_empty"):
        result["issues"].append({
            "severity": "critical",
            "title": "All DNS servers failed to resolve",
            "detail": "Alibaba DNS, Google DNS, 114 DNS all returned empty results",
            "suggestion": "Check domain existence, NS records, and Hold status",
        })
    elif not health.get("consistent", True):
        if len(health_ips) <= 1:
            result["health_consistent"] = True
        else:
            result["issues"].append({
                "severity": "warning",
                "title": "Inconsistent multi-DNS results",
                "detail": f"Resolved to {len(health_ips)} different IPs: {', '.join(health_ips.keys())}",
                "suggestion": "Possible DNS hijacking or propagation delay",
            })

    # -- Overall summary --
    critical_count = sum(1 for i in result["issues"] if i["severity"] == "critical")
    warning_count = sum(1 for i in result["issues"] if i["severity"] == "warning")

    if critical_count > 0:
        result["overall_severity"] = "critical"
    elif warning_count > 0:
        result["overall_severity"] = "warning"
    else:
        result["overall_severity"] = "normal"

    result["summary_line"] = _build_quick_summary(result)

    return result


def _build_quick_summary(r: dict) -> str:
    """Generate one-line quick summary."""
    parts = []
    parts.append(f"domain={r['domain']}")
    parts.append(f"product={r['product_type']}")
    parts.append(f"whois={r['whois_summary']}")
    parts.append(f"trace={'ok' if r['trace_ok'] else 'anomaly'}")
    parts.append(f"multi-dns={'consistent' if r['health_consistent'] else 'inconsistent'}")

    ips = list(r.get("health_ips", {}).keys())
    if ips:
        parts.append(f"resolved_ips={','.join(ips[:3])}")

    if r["issues"]:
        parts.append(f"issues={len(r['issues'])}")
    else:
        parts.append("no_issues")

    return " | ".join(parts)


# --- Probe result analysis ---

def analyze_probe(dns_data: dict = None, http_data: dict = None) -> dict:
    """
    Analyze boce DNS and/or HTTP probe results.

    Returns:
        dict: {
            "dns": {total, unique_ips, ip_distribution, anomalies, share_url},
            "http": {total, status_distribution, timeout_nodes, timeout_pattern, share_url},
            "issues": [{severity, title, detail, suggestion}],
        }
    """
    result = {"issues": []}

    # -- DNS probe --
    if dns_data and dns_data.get("success"):
        ip_map = dns_data.get("ip_count_map", {})
        total = dns_data.get("total_nodes", 0)

        ip_dist = []
        for ip, count in sorted(ip_map.items(), key=lambda x: -x[1]):
            pct = f"{count / total * 100:.1f}%" if total > 0 else "0%"
            ip_dist.append({"ip": ip, "count": count, "percent": pct})

        result["dns"] = {
            "total_nodes": total,
            "unique_ips": len(ip_map),
            "ip_distribution": ip_dist,
            "share_url": dns_data.get("share_url", ""),
            "all_same_ip": len(ip_map) == 1,
        }

        if len(ip_map) > 1:
            result["issues"].append({
                "severity": "warning",
                "title": "Multiple DNS resolution IPs",
                "detail": f"Nationwide probe found {len(ip_map)} different IPs",
                "suggestion": "Check if smart DNS/GeoDNS is configured, or if DNS hijacking exists",
            })
    elif dns_data:
        result["dns"] = {"error": dns_data.get("error", "Probe failed")}

    # -- HTTP probe --
    if http_data and http_data.get("success"):
        status_map = http_data.get("status_code_map", {})
        total = http_data.get("total_nodes", 0)
        details = http_data.get("details", [])

        status_dist = []
        for code, count in sorted(status_map.items(), key=lambda x: -x[1]):
            pct = f"{count / total * 100:.1f}%" if total > 0 else "0%"
            status_dist.append({"status_code": code, "count": count, "percent": pct})

        timeout_nodes = []
        for d in details:
            code = str(d.get("status_code", ""))
            if code in ("610", "61"):
                timeout_nodes.append({
                    "location": d.get("location", ""),
                    "resolve_ip": d.get("resolve_ip", ""),
                })

        timeout_count = len(timeout_nodes)
        if timeout_count == 0:
            timeout_pattern = "none"
        elif timeout_count == total:
            timeout_pattern = "all"
        else:
            locations = [n["location"] for n in timeout_nodes]
            timeout_pattern = _classify_timeout_pattern(locations, total)

        result["http"] = {
            "total_nodes": total,
            "status_distribution": status_dist,
            "timeout_nodes": timeout_nodes,
            "timeout_count": timeout_count,
            "timeout_pattern": timeout_pattern,
            "share_url": http_data.get("share_url", ""),
        }

        if timeout_pattern == "all":
            result["issues"].append({
                "severity": "critical",
                "title": "Suspected ICP filing block",
                "detail": f"All {total} nodes returned 610 (connection timeout)",
                "suggestion": "Check if domain has completed ICP filing. Overseas domains may be blocked in mainland China",
            })
        elif timeout_pattern != "none":
            result["issues"].append({
                "severity": "warning",
                "title": f"Partial route timeout ({timeout_count}/{total})",
                "detail": f"Timeout nodes: {', '.join(n['location'] for n in timeout_nodes)}",
                "suggestion": f"Pattern: {timeout_pattern}. Not ICP block (only partial nodes timeout), likely route-specific network issue",
            })
    elif http_data:
        result["http"] = {"error": http_data.get("error", "Probe failed")}

    return result


def _classify_timeout_pattern(locations: list, total: int) -> str:
    """Analyze distribution pattern of 610 timeout nodes."""
    alibaba_count = sum(1 for l in locations if "alibaba" in l.lower() or "aliyun" in l.lower())
    north_keywords = ["beijing", "hebei", "tianjin", "neimenggu", "shanxi", "shandong",
                      "liaoning", "jilin", "heilongjiang"]
    north_count = sum(1 for l in locations if any(k in l.lower() for k in north_keywords))

    parts = []

    if alibaba_count > len(locations) * 0.5:
        parts.append("concentrated on Alibaba Cloud nodes")
    if north_count > len(locations) * 0.5:
        parts.append("concentrated in North China")

    if parts:
        return "Specific route failure: " + ", ".join(parts)
    else:
        return f"Partial route failure ({len(locations)}/{total})"


# --- Full aggregation analysis ---

def analyze_all(quick_data: dict = None, dns_probe: dict = None,
                http_probe: dict = None, openapi_data: dict = None) -> dict:
    """
    Aggregate all step data, perform root-cause checks, generate final diagnosis.

    Returns:
        dict: {
            "conclusion": str,
            "severity": str,             # critical / warning / normal
            "root_causes": [str],
            "check_table": [{item, status, detail}],
            "recommendations": [str],
            "quick_analysis": {...},
            "probe_analysis": {...},
        }
    """
    quick_analysis = analyze_quick(quick_data) if quick_data else {}
    probe_analysis = analyze_probe(dns_probe, http_probe) if (dns_probe or http_probe) else {}

    all_issues = quick_analysis.get("issues", []) + probe_analysis.get("issues", [])

    # -- Root cause check table (priority ordered) --
    check_table = []
    root_causes = []
    recommendations = []

    # P0: Domain expiry
    whois_summary = quick_analysis.get("whois_summary", "")
    expired = any(i["title"] == "Domain expired" for i in all_issues)
    check_table.append({
        "item": "Domain Expiry",
        "status": "Critical" if expired else "Normal",
        "detail": whois_summary,
    })
    if expired:
        root_causes.append("Domain has expired")
        recommendations.append("Renew domain immediately")

    # P0: Domain hold
    hold_issues = [i for i in all_issues if "Dangerous domain status" in i.get("title", "")]
    check_table.append({
        "item": "Domain Status",
        "status": "Critical" if hold_issues else "Normal",
        "detail": ", ".join(i["detail"] for i in hold_issues) if hold_issues else "Normal",
    })
    if hold_issues:
        root_causes.append("Domain is on Hold")
        recommendations.extend(i.get("suggestion", "") for i in hold_issues if i.get("suggestion"))

    # P1: DNS vendor
    product_type = quick_analysis.get("product_type", "unknown")
    ns_servers = quick_analysis.get("ns_servers", [])
    check_table.append({
        "item": "DNS Vendor",
        "status": "Normal",
        "detail": f"{product_type} ({', '.join(ns_servers[:2])})" if ns_servers else product_type,
    })

    # P1: Recursive resolution
    trace_ok = quick_analysis.get("trace_ok", True)
    check_table.append({
        "item": "Recursive Resolution",
        "status": "Critical" if not trace_ok else "Normal",
        "detail": f"Anomaly: {', '.join(quick_analysis.get('trace_issues', []))}" if not trace_ok else "Trace complete",
    })
    if not trace_ok:
        root_causes.append("Recursive resolution chain anomaly")
        recommendations.append("Check NS server status and domain delegation config")

    # P1: Multi-DNS consistency
    health_consistent = quick_analysis.get("health_consistent", True)
    health_ips = quick_analysis.get("health_ips", {})
    check_table.append({
        "item": "Multi-DNS Consistency",
        "status": "Warning" if not health_consistent else "Normal",
        "detail": f"IPs: {', '.join(health_ips.keys())}" if health_ips else "No data",
    })

    # P1: DNS probe consistency
    dns_analysis = probe_analysis.get("dns", {})
    if dns_analysis and not dns_analysis.get("error"):
        dns_ok = dns_analysis.get("all_same_ip", True)
        ip_dist = dns_analysis.get("ip_distribution", [])
        ip_summary = ", ".join(f"{d['ip']}({d['percent']})" for d in ip_dist[:3])
        check_table.append({
            "item": "Nationwide DNS Probe",
            "status": "Normal" if dns_ok else "Warning",
            "detail": f"{dns_analysis.get('total_nodes', 0)} nodes, {ip_summary}",
        })

    # P2: ICP filing block
    http_analysis = probe_analysis.get("http", {})
    if http_analysis and not http_analysis.get("error"):
        timeout_pattern = http_analysis.get("timeout_pattern", "none")
        timeout_count = http_analysis.get("timeout_count", 0)
        http_total = http_analysis.get("total_nodes", 0)
        status_dist = http_analysis.get("status_distribution", [])
        status_summary = ", ".join(f"{d['status_code']}:{d['count']}" for d in status_dist)

        if timeout_pattern == "all":
            check_table.append({
                "item": "ICP Filing Block",
                "status": "Critical",
                "detail": f"All {http_total} nodes returned 610 timeout",
            })
            root_causes.append("Suspected ICP filing block")
            recommendations.append("Verify domain ICP filing status")
        else:
            check_table.append({
                "item": "ICP Filing Block",
                "status": "Excluded",
                "detail": f"Only {timeout_count}/{http_total} nodes timeout, not nationwide block",
            })

        if timeout_pattern not in ("none", "all"):
            timeout_locs = [n["location"] for n in http_analysis.get("timeout_nodes", [])]
            check_table.append({
                "item": "Partial Route Failure",
                "status": "Warning",
                "detail": f"{timeout_count}/{http_total} nodes timeout ({', '.join(timeout_locs)})",
            })
            root_causes.append(timeout_pattern)
            recommendations.append("Try alternative exit routes (switch ISP), or use proxy/acceleration to bypass problematic routes")
        elif timeout_pattern == "none":
            check_table.append({
                "item": "Route Connectivity",
                "status": "Normal",
                "detail": f"All {http_total} nodes reachable",
            })

        check_table.append({
            "item": "HTTP Status Distribution",
            "status": "Info",
            "detail": status_summary,
        })

    # -- Generate conclusion --
    if root_causes:
        severity = "critical" if any(
            "expired" in r.lower() or "hold" in r.lower() or "icp" in r.lower() or "recursive" in r.lower()
            for r in root_causes
        ) else "warning"
        conclusion = f"Found {len(root_causes)} issue(s): {'; '.join(root_causes)}"
    else:
        severity = "normal"
        conclusion = "DNS resolution normal, no issues found"

    return {
        "conclusion": conclusion,
        "severity": severity,
        "root_causes": root_causes,
        "check_table": check_table,
        "recommendations": recommendations,
        "quick_analysis": quick_analysis,
        "probe_analysis": probe_analysis,
    }


# --- Utility functions ---

def _is_ip(s: str) -> bool:
    """Simple check whether string is an IPv4 address."""
    parts = s.rstrip(".").split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _load_json_file(path: str) -> dict:
    """Load JSON from file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- CLI entry point ---

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="DNS diagnostic data analysis tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze quick_check output (from stdin)
  python3 dns_quick_check.py --domain example.com | python3 dns_analyze.py quick

  # Analyze quick_check output (from file)
  python3 dns_analyze.py quick --file /tmp/quick.json

  # Analyze probe data
  python3 dns_analyze.py probe --dns /tmp/dns.json --http /tmp/http.json

  # Full aggregation analysis
  python3 dns_analyze.py all --quick /tmp/quick.json --dns /tmp/dns.json --http /tmp/http.json
""",
    )
    sub = parser.add_subparsers(dest="action")

    p = sub.add_parser("quick", help="Analyze quick_check.py output")
    p.add_argument("--file", help="JSON file path (reads from stdin if not specified)")

    p = sub.add_parser("probe", help="Analyze probe results")
    p.add_argument("--dns", help="DNS probe JSON file path")
    p.add_argument("--http", help="HTTP probe JSON file path")

    p = sub.add_parser("all", help="Full aggregation analysis")
    p.add_argument("--quick", help="quick_check JSON file path")
    p.add_argument("--dns", help="DNS probe JSON file path")
    p.add_argument("--http", help="HTTP probe JSON file path")
    p.add_argument("--openapi", help="OpenAPI query JSON file path")

    args = parser.parse_args()

    if args.action == "quick":
        if args.file:
            data = _load_json_file(args.file)
        else:
            data = json.load(sys.stdin)
        result = analyze_quick(data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "probe":
        dns_data = _load_json_file(args.dns) if args.dns else None
        http_data = _load_json_file(args.http) if args.http else None
        result = analyze_probe(dns_data, http_data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "all":
        quick_data = _load_json_file(args.quick) if args.quick else None
        dns_data = _load_json_file(args.dns) if args.dns else None
        http_data = _load_json_file(args.http) if args.http else None
        openapi_data = _load_json_file(args.openapi) if getattr(args, "openapi", None) else None
        result = analyze_all(quick_data, dns_data, http_data, openapi_data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
