"""sr-doctor: diagnose connection failures and produce actionable next steps.

EMR Serverless StarRocks exposes two FE endpoint suffixes:

  - "-internal.starrocks.aliyuncs.com"  → VPC internal
  - ".starrocks.aliyuncs.com"           → Public

The diagnostic logic branches on the suffix:

  - VPC + unreachable  → suggest the public swap (and enabling it in the console
                         if the instance hasn't yet).
  - Public + unreachable → discover the client's egress IP via ipinfo.io and
                           suggest a /24 whitelist CIDR (the /24 buffers for NAT
                           IP drift within a typical datacenter).
"""

from __future__ import annotations

import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal

EndpointKind = Literal["vpc", "public", "custom"]

VPC_SUFFIX = "-internal.starrocks.aliyuncs.com"
PUBLIC_SUFFIX = ".starrocks.aliyuncs.com"
IPINFO_URL = "https://ipinfo.io/ip"


def classify_endpoint(host: str) -> EndpointKind:
    """Classify an FE host by its DNS suffix."""
    h = host.lower().strip()
    if h.endswith(VPC_SUFFIX):
        return "vpc"
    if h.endswith(PUBLIC_SUFFIX):
        return "public"
    return "custom"


def can_reach(host: str, port: int, timeout: float = 5.0) -> bool:
    """TCP-probe host:port. Returns True if a connection can be established."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def get_egress_ip(timeout: float = 5.0) -> str | None:
    """Discover the client's public egress IP via ipinfo.io.

    Returns the IPv4 string on success, or None if the lookup fails or the
    response doesn't look like an IPv4 address. ipinfo.io was picked over
    api.ipify.org and the Aliyun ECS metadata service because those two were
    observed to be unreliable in agenthub sandboxes (empty body / hangs).
    """
    try:
        req = urllib.request.Request(
            IPINFO_URL, headers={"User-Agent": "sr-doctor/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8").strip()
    except (urllib.error.URLError, OSError, ValueError):
        return None
    parts = body.split(".")
    if len(parts) != 4:
        return None
    try:
        if all(0 <= int(p) <= 255 for p in parts):
            return body
    except ValueError:
        pass
    return None


def mask_to_24(ip: str) -> str:
    """Return the /24 CIDR for an IPv4 address (e.g. '1.2.3.4' -> '1.2.3.0/24')."""
    parts = ip.split(".")
    if len(parts) != 4:
        raise ValueError(f"Not an IPv4 address: {ip!r}")
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"


def vpc_to_public(host: str) -> str:
    """Rewrite a VPC -internal host to its public counterpart.

    Returns the input unchanged if it isn't a -internal host.
    """
    lower = host.lower()
    if not lower.endswith(VPC_SUFFIX):
        return host
    idx = lower.rfind(VPC_SUFFIX)
    return host[:idx] + PUBLIC_SUFFIX


@dataclass
class Diagnosis:
    host: str
    port: int
    endpoint_kind: EndpointKind
    reachable: bool
    egress_ip: str | None = None
    suggested_cidr: str | None = None
    suggested_alternate_host: str | None = None


def diagnose(host: str, port: int) -> Diagnosis:
    """Run the full diagnostic pipeline for a single host:port."""
    kind = classify_endpoint(host)
    reachable = can_reach(host, port)
    d = Diagnosis(host=host, port=port, endpoint_kind=kind, reachable=reachable)
    if reachable:
        return d
    if kind == "vpc":
        d.suggested_alternate_host = vpc_to_public(host)
    elif kind == "public":
        ip = get_egress_ip()
        if ip:
            d.egress_ip = ip
            d.suggested_cidr = mask_to_24(ip)
    return d


def _describe_kind(kind: EndpointKind) -> str:
    return {
        "vpc": "VPC (-internal.starrocks.aliyuncs.com)",
        "public": "Public (.starrocks.aliyuncs.com)",
        "custom": "Custom (not a recognized EMR Serverless suffix)",
    }[kind]


def format_diagnosis(d: Diagnosis) -> str:
    """Render a Diagnosis as a user-facing multi-line message."""
    lines: list[str] = []

    if d.reachable:
        lines.append(f"[OK] {d.host}:{d.port} is reachable.")
        lines.append(f"     Endpoint type: {_describe_kind(d.endpoint_kind)}")
        return "\n".join(lines)

    lines.append(f"[!] Cannot reach {d.host}:{d.port}")
    lines.append("")
    lines.append(f"Endpoint type: {_describe_kind(d.endpoint_kind)}")

    if d.endpoint_kind == "vpc":
        lines.append("Cause: Your client is not inside the cluster's VPC.")
        lines.append("")
        lines.append('Fix: Switch to the public endpoint by removing "-internal" from the host:')
        lines.append("")
        lines.append(f"    export SR_HOST={d.suggested_alternate_host}")
        lines.append("    sr-login --from-env")
        lines.append("")
        lines.append("If the instance has not enabled the public endpoint yet:")
        lines.append("    Console -> EMR Serverless StarRocks -> instance details")
        lines.append("    -> Gateway info -> Provision SLB  (prerequisite)")
        lines.append("    -> Public address -> Enable public endpoint")
        lines.append("    (creates a billable CLB; provisioning takes a few minutes)")
        lines.append("    Docs: https://help.aliyun.com/zh/emr/emr-serverless-starrocks/manage-gateways")

    elif d.endpoint_kind == "public":
        if d.egress_ip and d.suggested_cidr:
            lines.append(f"Your public egress IP: {d.egress_ip}")
            lines.append(f"Suggested whitelist CIDR: {d.suggested_cidr}")
            lines.append("    (/24 buffers for NAT IP drift within a cluster)")
            lines.append("")
            lines.append("Fix: Add the CIDR to the cluster whitelist:")
            lines.append("    Console -> EMR Serverless -> instance details")
            lines.append("    -> Network -> Whitelist -> Add CIDR -> Save")
            lines.append("")
            lines.append("Then retry: sr-login --from-env")
        else:
            lines.append("Could not auto-discover your public egress IP (ipinfo.io unreachable).")
            lines.append("")
            lines.append("Fix: Find your egress IP manually (curl ipinfo.io from this host,")
            lines.append("     or ask the platform team) and add it to the cluster whitelist:")
            lines.append("    Console -> EMR Serverless -> instance details")
            lines.append("    -> Network -> Whitelist -> Add IP/CIDR -> Save")

    else:
        lines.append("Cause: Host is not a recognized EMR Serverless StarRocks endpoint.")
        lines.append("       Verify the address is correct and that the network path is open.")

    return "\n".join(lines)


def run_doctor(host: str, port: int) -> int:
    """sr-doctor entry-point logic. Returns shell exit code (0 reachable, 1 not)."""
    d = diagnose(host, port)
    print(format_diagnosis(d))
    return 0 if d.reachable else 1
