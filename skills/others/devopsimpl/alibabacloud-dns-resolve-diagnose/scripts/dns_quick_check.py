"""
dns_quick_check.py - DNS quick pre-check script (merged steps 0-2).

Combines environment check, domain splitting, NS query, WHOIS query, dig trace,
and multi-DNS health check into one parallel-execution script to minimize
diagnostic startup time.

Usage:
    python3 dns_quick_check.py --domain www.example.com

Output JSON contains:
    - env:        Environment detection results (tools + credentials)
    - split:      Domain split candidate list
    - ns:         NS records and product type determination
    - whois:      WHOIS query + expiry check + status check
    - trace:      dig +trace recursive tracing
    - health:     Multi-DNS server comparison
"""

import json
import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dns_common import split_domain, check_all_tools, check_env_credentials, is_alicloud_ns
from dns_dig import dig_ns, dig_trace, check_recursive_health
from dns_whois import whois_query, check_expiry, check_hold_status, get_dangerous_statuses


def _run_threaded(tasks: dict) -> dict:
    """
    Execute multiple functions in parallel and collect results.

    Args:
        tasks: {key: (func, args, kwargs)} dict

    Returns:
        {key: result} dict
    """
    results = {}
    errors = {}
    lock = threading.Lock()

    def _worker(key, func, args, kwargs):
        try:
            result = func(*args, **kwargs)
            with lock:
                results[key] = result
        except Exception as e:
            with lock:
                errors[key] = str(e)

    threads = []
    for key, (func, args, kwargs) in tasks.items():
        t = threading.Thread(target=_worker, args=(key, func, args, kwargs))
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=60)

    for key, err in errors.items():
        results[key] = {"error": err}

    return results


def quick_check(domain: str) -> dict:
    """
    Execute quick pre-check: merge steps 0-2, run independent tasks in parallel.

    Execution order:
      Phase A (immediate): Environment detection + domain splitting (fast, serial)
      Phase B (parallel): NS query / WHOIS / dig trace / multi-DNS health

    Args:
        domain: Full domain name, e.g. "www.example.com"

    Returns:
        dict: Complete result containing env, split, ns, whois, trace, health
    """
    output = {}

    # -- Phase A: Environment detection + domain splitting (milliseconds, serial) --
    tools = check_all_tools()
    creds = check_env_credentials()
    output["env"] = {"tools": tools, "credentials": creds}

    candidates = split_domain(domain)
    output["split"] = [{"zone": c.zone, "rr": c.rr} for c in candidates]

    root_domain = candidates[0].zone if candidates else domain

    # -- Phase B: Parallel NS / WHOIS / trace / health --
    parallel_tasks = {
        "ns": (dig_ns, [root_domain], {}),
        "whois_raw": (whois_query, [domain], {}),
        "trace": (dig_trace, [domain, "A"], {}),
        "health": (check_recursive_health, [domain], {}),
    }

    parallel_results = _run_threaded(parallel_tasks)

    # -- Assemble NS results + product type --
    ns_records = parallel_results.get("ns", [])
    if isinstance(ns_records, dict) and "error" in ns_records:
        output["ns"] = {"records": [], "error": ns_records["error"], "product_type": "unknown"}
    else:
        is_alicloud = is_alicloud_ns(ns_records) if ns_records else False
        product_type = "public_dns" if is_alicloud else "third_party"
        output["ns"] = {
            "records": ns_records,
            "is_alicloud": is_alicloud,
            "product_type": product_type,
        }

    # -- Assemble WHOIS results --
    whois_raw = parallel_results.get("whois_raw", {})
    if isinstance(whois_raw, dict) and whois_raw.get("error"):
        output["whois"] = {"error": whois_raw["error"]}
    else:
        whois_info = {k: v for k, v in whois_raw.items() if k != "raw"}
        output["whois"] = {
            "info": whois_info,
            "expiry_check": check_expiry(whois_raw),
            "status_check": check_hold_status(whois_raw),
            "dangerous_statuses": get_dangerous_statuses(whois_raw),
        }

    # -- Assemble trace results --
    trace_result = parallel_results.get("trace", "")
    if isinstance(trace_result, dict) and "error" in trace_result:
        output["trace"] = {"raw": "", "error": trace_result["error"]}
    else:
        trace_str = str(trace_result)
        has_servfail = "SERVFAIL" in trace_str
        has_refused = "REFUSED" in trace_str
        has_timeout = "timed out" in trace_str.lower() or "connection timed out" in trace_str.lower()
        trace_ok = not (has_servfail or has_refused or has_timeout)

        output["trace"] = {
            "raw": trace_str,
            "ok": trace_ok,
            "has_servfail": has_servfail,
            "has_refused": has_refused,
            "has_timeout": has_timeout,
        }

    # -- Assemble health results --
    health_result = parallel_results.get("health", {})
    if isinstance(health_result, dict) and "error" in health_result:
        output["health"] = {"error": health_result["error"]}
    else:
        output["health"] = health_result

    # -- Generate summary --
    issues = []
    missing_tools = [t for t, info in tools.items() if not info.get("available")]
    if missing_tools:
        issues.append(f"Missing tools: {', '.join(missing_tools)}")

    if output.get("whois", {}).get("expiry_check", {}).get("status") == "critical":
        issues.append("Domain has expired")
    if output.get("whois", {}).get("dangerous_statuses"):
        statuses = [s["status_code"] for s in output["whois"]["dangerous_statuses"]]
        issues.append(f"Dangerous statuses: {', '.join(statuses)}")

    if not output.get("trace", {}).get("ok", True):
        trace_issues = []
        if output["trace"].get("has_servfail"):
            trace_issues.append("SERVFAIL")
        if output["trace"].get("has_refused"):
            trace_issues.append("REFUSED")
        if output["trace"].get("has_timeout"):
            trace_issues.append("timeout")
        issues.append(f"Recursive trace anomaly: {', '.join(trace_issues)}")

    if output.get("health", {}).get("all_empty"):
        issues.append("All DNS servers failed to resolve")
    elif not output.get("health", {}).get("consistent", True):
        issues.append("DNS resolution results inconsistent across servers")

    output["summary"] = {
        "domain": domain,
        "root_domain": root_domain,
        "product_type": output.get("ns", {}).get("product_type", "unknown"),
        "issues_found": len(issues),
        "issues": issues,
        "env_ready": len(missing_tools) == 0,
        "credentials_ready": creds.get("has_credentials", False),
    }

    return output


# --- CLI entry point ---

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="DNS quick pre-check (merged steps 0-2, parallel execution)"
    )
    parser.add_argument("--domain", required=True, help="Target domain")

    args = parser.parse_args()
    result = quick_check(args.domain)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
