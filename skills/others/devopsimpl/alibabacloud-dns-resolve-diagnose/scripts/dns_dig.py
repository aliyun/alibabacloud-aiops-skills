"""
dns_dig.py - dig/nslookup command wrapper.

Provides Python wrappers for DNS queries: NS lookup, trace, multi-server comparison.
Falls back to nslookup when dig is unavailable.
"""

import json
import re
import shutil
import subprocess
import sys
from typing import Optional

DEFAULT_SERVERS = [
    ("223.5.5.5", "Alibaba DNS"),
    ("8.8.8.8", "Google DNS"),
    ("114.114.114.114", "114 DNS"),
]

HAS_DIG = shutil.which("dig") is not None


def _run_cmd(cmd: list, timeout: int = 15) -> tuple:
    """Execute a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


# --- dig wrappers ---

def dig_ns(domain: str) -> list:
    """
    Query NS records for a domain.

    Returns:
        list[str]: NS server list, e.g. ["ns1.alidns.com.", "ns2.alidns.com."]
    """
    if not HAS_DIG:
        return _nslookup_ns(domain)

    rc, out, err = _run_cmd(["dig", "NS", domain, "+short", "+time=5", "+tries=2"])
    if rc != 0 or not out:
        return _nslookup_ns(domain)

    return [line.strip() for line in out.splitlines() if line.strip()]


def dig_trace(domain: str, rtype: str = "A") -> str:
    """
    Execute dig +trace to get full recursive resolution chain.

    Returns:
        str: Full trace output text
    """
    if not HAS_DIG:
        return "(dig not available, cannot perform trace. Please install dig.)"

    rc, out, err = _run_cmd(
        ["dig", "+trace", "+nodnssec", domain, rtype, "+time=5", "+tries=2"],
        timeout=30,
    )
    if rc != 0:
        return f"dig +trace failed: {err}"
    return out


def dig_at(domain: str, server: str, rtype: str = "A") -> list:
    """
    Query a domain using a specific DNS server.

    Returns:
        list[dict]: Resolution results, each containing {value, ttl, type}
    """
    if not HAS_DIG:
        return nslookup_fallback(domain, server)

    rc, out, err = _run_cmd(
        ["dig", f"@{server}", domain, rtype, "+noall", "+answer", "+time=5", "+tries=2"]
    )
    if rc != 0 or not out:
        return []

    records = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        parts = line.split()
        if len(parts) >= 5:
            records.append({
                "name": parts[0],
                "ttl": int(parts[1]) if parts[1].isdigit() else 0,
                "type": parts[3],
                "value": parts[4],
            })
    return records


def dig_short(domain: str, server: str = None, rtype: str = "A") -> list:
    """
    Short query returning only record values.

    Returns:
        list[str]: Record values, e.g. ["1.2.3.4", "5.6.7.8"]
    """
    if not HAS_DIG:
        results = nslookup_fallback(domain, server)
        return [r["value"] for r in results]

    cmd = ["dig", domain, rtype, "+short", "+time=5", "+tries=2"]
    if server:
        cmd.insert(1, f"@{server}")

    rc, out, err = _run_cmd(cmd)
    if rc != 0 or not out:
        return []

    return [line.strip() for line in out.splitlines() if line.strip()]


def dig_soa(domain: str) -> dict:
    """
    Query SOA record for a domain.

    Returns:
        dict: {primary_ns, admin_email, serial, refresh, retry, expire, minimum_ttl}
    """
    if not HAS_DIG:
        return {}

    rc, out, err = _run_cmd(
        ["dig", "SOA", domain, "+short", "+time=5", "+tries=2"]
    )
    if rc != 0 or not out:
        return {}

    parts = out.split()
    if len(parts) >= 7:
        return {
            "primary_ns": parts[0],
            "admin_email": parts[1],
            "serial": parts[2],
            "refresh": parts[3],
            "retry": parts[4],
            "expire": parts[5],
            "minimum_ttl": parts[6],
        }
    return {}


def batch_resolve(domain: str, servers: list = None, rtype: str = "A") -> dict:
    """
    Query a domain from multiple DNS servers for comparison analysis.

    Args:
        domain: Domain name
        servers: [(server_ip, server_name), ...], defaults to DEFAULT_SERVERS
        rtype: Record type

    Returns:
        dict: {server_name: {"server": ip, "results": [...], "values": [...]}}
    """
    if servers is None:
        servers = DEFAULT_SERVERS

    results = {}
    for server_ip, server_name in servers:
        records = dig_at(domain, server_ip, rtype)
        values = [r["value"] for r in records]
        results[server_name] = {
            "server": server_ip,
            "results": records,
            "values": values,
        }

    return results


def check_recursive_health(domain: str) -> dict:
    """
    Check recursive resolution health by comparing results across public DNS servers.

    Returns:
        dict: {
            "consistent": bool,
            "all_empty": bool,
            "results": {server_name: [values]},
            "summary": str
        }
    """
    multi = batch_resolve(domain)

    all_values = {}
    all_empty = True
    for name, data in multi.items():
        all_values[name] = data["values"]
        if data["values"]:
            all_empty = False

    value_sets = [frozenset(v) for v in all_values.values() if v]
    consistent = len(set(value_sets)) <= 1 if value_sets else True

    if all_empty:
        summary = "All public DNS servers failed to resolve this domain"
    elif consistent:
        summary = "All public DNS servers return consistent results"
    else:
        summary = "Inconsistent results across DNS servers, possible hijacking or propagation delay"

    return {
        "consistent": consistent,
        "all_empty": all_empty,
        "results": all_values,
        "summary": summary,
    }


# --- nslookup fallback ---

def _nslookup_ns(domain: str) -> list:
    """Query NS records via nslookup (fallback when dig unavailable)."""
    rc, out, err = _run_cmd(["nslookup", "-type=NS", domain])
    if rc != 0:
        return []

    ns_list = []
    for line in out.splitlines():
        line = line.strip()
        match = re.search(r"nameserver\s*=\s*(\S+)", line, re.IGNORECASE)
        if match:
            ns_list.append(match.group(1))
    return ns_list


def nslookup_fallback(domain: str, server: str = None) -> list:
    """
    Query a domain via nslookup (fallback when dig unavailable).

    Returns:
        list[dict]: [{value, type}]
    """
    cmd = ["nslookup", domain]
    if server:
        cmd.append(server)

    rc, out, err = _run_cmd(cmd)
    if rc != 0:
        return []

    records = []
    in_answer = False
    for line in out.splitlines():
        line = line.strip()
        if "Non-authoritative answer:" in line or "Name:" in line:
            in_answer = True
            continue
        if in_answer:
            match = re.match(r"Address:\s*(\S+)", line)
            if match:
                value = match.group(1)
                if "#" not in value:
                    rtype = "AAAA" if ":" in value else "A"
                    records.append({"value": value, "type": rtype})
            alias_match = re.search(r"canonical name\s*=\s*(\S+)", line, re.IGNORECASE)
            if alias_match:
                records.append({"value": alias_match.group(1), "type": "CNAME"})

    return records


# --- CLI entry point ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="DNS dig/nslookup wrapper tool")
    parser.add_argument("--domain", required=True, help="Target domain")
    parser.add_argument(
        "--action",
        choices=["ns", "trace", "resolve", "batch", "health", "soa"],
        default="resolve",
        help="Action type",
    )
    parser.add_argument("--server", help="DNS server (resolve mode only)")
    parser.add_argument("--type", default="A", help="Record type, default A")

    args = parser.parse_args()

    if args.action == "ns":
        result = dig_ns(args.domain)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "trace":
        result = dig_trace(args.domain, args.type)
        print(result)

    elif args.action == "resolve":
        if args.server:
            result = dig_at(args.domain, args.server, args.type)
        else:
            result = dig_at(args.domain, "223.5.5.5", args.type)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "batch":
        result = batch_resolve(args.domain, rtype=args.type)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "health":
        result = check_recursive_health(args.domain)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "soa":
        result = dig_soa(args.domain)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
