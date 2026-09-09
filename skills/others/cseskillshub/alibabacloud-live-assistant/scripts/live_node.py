#!/usr/bin/env python3
"""
Live streaming node analysis.

Probes and analyzes live CDN nodes:
- DNS resolution to discover edge nodes
- ICMP/TCP latency probing
- Origin path tracing
- Node health assessment
"""

import argparse
import json
import socket
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import urlparse


def run_cmd(cmd, timeout=10):
    """Run a command and return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        return "", -1
    except FileNotFoundError:
        return "", -2


def resolve_domain(domain):
    """Resolve a domain to a list of IP addresses via DNS."""
    try:
        ips = socket.getaddrinfo(domain, None, socket.AF_INET)
        seen = set()
        result = []
        for ip_info in ips:
            ip = ip_info[4][0]
            if ip not in seen:
                seen.add(ip)
                result.append(ip)
        return result
    except socket.gaierror:
        return []


def ping_host(ip, count=3, timeout=2):
    """Probe latency via ICMP ping."""
    # macOS ping -W expects milliseconds; Linux (GNU iputils) expects seconds.
    wait_arg = str(timeout * 1000) if sys.platform == "darwin" else str(timeout)
    cmd = ["ping", "-c", str(count), "-W", wait_arg, ip]
    stdout, rc = run_cmd(cmd, timeout=timeout * count + 5)

    if rc != 0:
        return {"ip": ip, "reachable": False, "avg_ms": None, "loss": 100}

    # Parse ping output
    avg_ms = None
    loss = 100
    for line in stdout.split("\n"):
        # Latency line: round-trip min/avg/max/stddev = ... ms
        if "round-trip" in line or "avg" in line:
            try:
                parts = line.split("=")[-1].strip().split("/")
                avg_ms = float(parts[1]) if len(parts) >= 2 else None
            except (ValueError, IndexError):
                pass
        # Loss line: 3 packets transmitted, 3 received, 0% packet loss
        if "packet loss" in line:
            try:
                loss_str = line.split(",")[-1].strip().split("%")[0].strip()
                loss = float(loss_str)
            except (ValueError, IndexError):
                pass

    return {
        "ip": ip,
        "reachable": avg_ms is not None,
        "avg_ms": avg_ms,
        "loss": loss,
    }


def tcp_probe(ip, port=1935, timeout=3):
    """Probe reachability via a TCP connection."""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        elapsed_ms = int((time.time() - start) * 1000)
        sock.close()
        return {"ip": ip, "port": port, "reachable": True, "latency_ms": elapsed_ms}
    except (socket.timeout, ConnectionRefusedError, OSError):
        return {"ip": ip, "port": port, "reachable": False, "latency_ms": None}


def http_probe(url, timeout=5):
    """Check HTTP availability."""
    cmd = ["curl", "-sI", "-o", "/dev/null", "-w",
           "%{http_code}|%{time_total}", "--connect-timeout", str(timeout), url]
    stdout, rc = run_cmd(cmd, timeout=timeout + 5)

    if rc != 0 or not stdout:
        return {"url": url, "status_code": None, "response_time_ms": None, "reachable": False}

    parts = stdout.strip().split("|")
    try:
        status_code = int(parts[0]) if parts[0] else None
        response_time = float(parts[1]) * 1000 if len(parts) > 1 and parts[1] else None
    except (ValueError, IndexError):
        status_code = None
        response_time = None

    return {
        "url": url,
        "status_code": status_code,
        "response_time_ms": round(response_time, 1) if response_time else None,
        "reachable": status_code in (200, 206) if status_code else False,
    }


def traceroute_host(ip, max_hops=15, timeout=2):
    """Trace the network path to a target."""
    cmd = ["traceroute", "-m", str(max_hops), "-w", str(timeout), ip]
    stdout, rc = run_cmd(cmd, timeout=max_hops * timeout + 10)

    hops = []
    if rc == 0 or stdout:
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("traceroute"):
                continue
            # Simplified parsing: extract IP and latency
            parts = line.split()
            hop = {"raw": line}
            if len(parts) >= 2:
                try:
                    hop_num = int(parts[0])
                    # Look for the IP address
                    for p in parts[1:]:
                        if p.startswith("(") and p.endswith(")"):
                            hop["ip"] = p[1:-1]
                            break
                        elif p.replace(".", "").isdigit() and "." in p:
                            hop["ip"] = p
                            break
                    hops.append(hop)
                except ValueError:
                    pass

    return hops


def get_ip_region(ip):
    """Get IP geolocation info (best effort).

    Falls back to 'unknown' on any failure so that the main analysis
    flow is never blocked by the geolocation lookup.
    """
    try:
        cmd = ["curl", "-s", "--connect-timeout", "3", "--max-time", "5",
               f"https://ipinfo.io/{ip}/json"]
        stdout, rc = run_cmd(cmd, timeout=8)
        if rc == 0 and stdout:
            data = json.loads(stdout)
            return {
                "ip": ip,
                "country": data.get("country", "unknown"),
                "region": data.get("region", "unknown"),
                "city": data.get("city", "unknown"),
                "org": data.get("org", "unknown"),
            }
    except Exception:
        pass
    return {"ip": ip, "country": "unknown", "region": "unknown", "city": "unknown", "org": "unknown"}


def analyze_nodes(url, trace_origin=False, verbose=False):
    """Run node analysis for a live stream URL."""
    parsed = urlparse(url)
    domain = parsed.hostname or parsed.path.split("/")[0] if not parsed.hostname else parsed.hostname
    port = parsed.port or (1935 if parsed.scheme in ("rtmp", "rtmps") else 80)

    result = {
        "stream_url": url,
        "domain": domain,
        "timestamp": datetime.now().isoformat(),
        "nodes": [],
        "origin": None,
        "trace": [],
        "summary": {},
    }

    # 1. DNS resolution
    ips = resolve_domain(domain)
    if not ips:
        result["summary"] = {"total_nodes": 0, "healthy": 0, "warning": 0, "error": 1,
                             "avg_latency_ms": None, "error_msg": "DNS resolution failed"}
        result["overall_status"] = "failed"
        result["severity"] = "critical"
        result["overall_summary"] = (
            f"DNS resolution failed for {domain}: no CDN edge nodes could be found. "
            "Next: Verify the domain's CNAME resolution is configured."
        )
        result["suggestion"] = "Verify the domain's CNAME resolution is configured."
        return result

    if verbose:
        print(f"[info] DNS resolved {len(ips)} node IP(s)", file=sys.stderr)

    # 2. Per-node probing
    healthy_count = 0
    warning_count = 0
    error_count = 0
    total_latency = 0
    latency_count = 0

    for ip in ips:
        node = {"ip": ip, "status": "unknown", "is_edge": True}

        # ICMP ping probe
        ping_result = ping_host(ip, count=2, timeout=2)
        node["ping_ms"] = ping_result.get("avg_ms")
        node["ping_loss"] = ping_result.get("loss", 100)

        # TCP probe
        tcp_result = tcp_probe(ip, port=port, timeout=3)
        node["tcp_reachable"] = tcp_result["reachable"]
        node["tcp_latency_ms"] = tcp_result.get("latency_ms")

        # Assess node health
        if not tcp_result["reachable"]:
            node["status"] = "error"
            error_count += 1
        elif node["ping_loss"] and node["ping_loss"] > 50:
            node["status"] = "warning"
            warning_count += 1
        else:
            node["status"] = "healthy"
            healthy_count += 1

        if node.get("ping_ms"):
            total_latency += node["ping_ms"]
            latency_count += 1

        # Region info (verbose mode only)
        if verbose:
            region_info = get_ip_region(ip)
            node["region"] = region_info.get("region", "unknown")
            node["city"] = region_info.get("city", "unknown")
            node["org"] = region_info.get("org", "unknown")

        result["nodes"].append(node)

    # 3. Origin path tracing
    if trace_origin and ips:
        target_ip = ips[0]
        hops = traceroute_host(target_ip, max_hops=10)
        result["trace"] = hops
        if verbose:
            print(f"[info] traceroute to {target_ip}: {len(hops)} hop(s)", file=sys.stderr)

    # 4. Origin probing (if the pull domain differs from the push domain,
    #    try probing the inferred push domain)
    if trace_origin:
        push_domain = domain.replace("pull", "push").replace("live", "push")
        if push_domain != domain:
            push_ips = resolve_domain(push_domain)
            if push_ips:
                origin_result = ping_host(push_ips[0], count=2)
                result["origin"] = {
                    "domain": push_domain,
                    "ip": push_ips[0],
                    "reachable": origin_result["reachable"],
                    "latency_ms": origin_result.get("avg_ms"),
                }

    # 5. Build summary
    avg_latency = round(total_latency / latency_count, 1) if latency_count else None
    result["summary"] = {
        "total_nodes": len(ips),
        "healthy": healthy_count,
        "warning": warning_count,
        "error": error_count,
        "avg_latency_ms": avg_latency,
    }

    # Dual-friendly top-level fields. The one-line conclusion uses
    # "overall_summary" because "summary" already holds the statistics dict.
    if error_count == len(ips):
        result["overall_status"] = "failed"
        result["severity"] = "critical"
        result["overall_summary"] = (
            f"All {len(ips)} CDN node(s) of {domain} are unreachable on port {port}. "
            "Next: check whether the live service is running and the network path is open."
        )
    elif error_count or warning_count:
        result["overall_status"] = "warning"
        result["severity"] = "medium"
        result["overall_summary"] = (
            f"{healthy_count} of {len(ips)} CDN node(s) are healthy "
            f"({error_count} error, {warning_count} warning). "
            "Next: review the unhealthy nodes below; retry later if the issue persists."
        )
    else:
        result["overall_status"] = "ok"
        result["severity"] = "info"
        avg_desc = f"{avg_latency} ms" if avg_latency is not None else "n/a"
        result["overall_summary"] = (
            f"All {len(ips)} CDN node(s) of {domain} are healthy "
            f"(average latency {avg_desc}); the network path to the CDN looks good. "
            "Next: if the stream still has issues, run the stream quality diagnosis."
        )

    # Build a path description
    if result["nodes"]:
        result["trace_description"] = (
            f"client -> edge nodes ({domain}, {len(ips)} IP(s)) -> origin"
        )

    return result


def main():
    parser = argparse.ArgumentParser(description="Live streaming node analysis")
    parser.add_argument("url", help="Live stream URL or domain")
    parser.add_argument("--trace-origin", action="store_true", help="Trace the origin path")
    parser.add_argument("--verbose", action="store_true", help="Verbose output (includes region info)")

    args = parser.parse_args()

    result = analyze_nodes(
        url=args.url,
        trace_origin=args.trace_origin,
        verbose=args.verbose,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # DNS resolution failure is a critical failure: exit non-zero so that
    # callers can detect it, while the JSON above is still emitted.
    if result.get("overall_status") == "failed":
        sys.exit(1)


if __name__ == "__main__":
    main()
