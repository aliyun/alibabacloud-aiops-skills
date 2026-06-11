"""
dns_analyzer.py - DNS diagnostic core analysis engine.

Executes 6 root-cause checks + config vs. probe cross-reference, generates conclusions.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dns_common import (
    CheckResult, DiagnosisResult, Discrepancy, DomainDiagContext,
    is_alicloud_ns, ALICLOUD_NS_PATTERNS,
)

HIJACK_IPS = frozenset({
    "127.0.0.1", "0.0.0.0", "127.0.0.2",
    "0.0.0.1", "192.0.0.1",
})

ICP_BLOCK_STATUS_CODES = frozenset({"610", "613", "614"})

HTTP_INTERNAL_CODES = frozenset({"610", "613", "614"})


class DnsAnalyzer:
    """
    DNS diagnostic analysis engine.

    Takes complete diagnostic context data, executes 6 root-cause checks
    and cross-references, outputs structured diagnostic conclusions.
    """

    def __init__(self, context: DomainDiagContext):
        self.ctx = context
        self.checks = []
        self.discrepancies = []

    def analyze(self) -> DiagnosisResult:
        """
        Execute all analyses and return diagnosis result.
        All checks run to completion (no early exit) to catch multiple issues.
        """
        # P0 checks
        self.checks.append(self.check_domain_expiry())
        self.checks.append(self.check_domain_hold())

        # P1 checks
        self.checks.append(self.check_dns_vendor())
        self.checks.append(self.check_recursive_resolution())

        # P2 checks
        self.checks.append(self.check_icp_filing())
        self.checks.append(self.check_dns_config())

        # Product-specific checks
        if self.ctx.product_type == "gtm":
            self.checks.append(self.check_gtm_health())
        elif self.ctx.product_type == "privatezone":
            self.checks.append(self.check_privatezone_binding())

        # Cross-reference
        self.discrepancies = self.cross_reference_config_vs_probe()

        # Aggregate root causes and suggestions
        root_causes = []
        suggestions = []
        severity = "normal"

        for check in self.checks:
            if check.status == "critical":
                severity = "critical"
                root_causes.append(check.summary)
                if check.suggestion:
                    suggestions.append(check.suggestion)
            elif check.status == "warning":
                if severity not in ("critical",):
                    severity = "warning"
                root_causes.append(check.summary)
                if check.suggestion:
                    suggestions.append(check.suggestion)

        for disc in self.discrepancies:
            if disc.severity == "critical":
                severity = "critical"
            root_causes.append(disc.description)

        if not root_causes:
            severity = "normal"

        return DiagnosisResult(
            checks=self.checks,
            discrepancies=self.discrepancies,
            root_causes=root_causes,
            suggestions=suggestions,
            severity=severity,
        )

    # --- P0: Domain expiry check ---

    def check_domain_expiry(self) -> CheckResult:
        """Check whether domain has expired."""
        whois = self.ctx.whois_result
        if not whois:
            return CheckResult(
                name="Domain Expiry",
                status="skipped",
                summary="No WHOIS data available, skipping expiry check",
            )

        expiry = whois.get("expiry_check", {})
        status = expiry.get("status", "unknown")

        if status == "critical":
            return CheckResult(
                name="Domain Expiry",
                status="critical",
                summary=expiry.get("summary", "Domain has expired"),
                details=f"Expiry date: {expiry.get('expiry_date', 'unknown')}",
                suggestion="Renew the domain immediately to restore DNS resolution",
            )
        elif status == "warning":
            return CheckResult(
                name="Domain Expiry",
                status="warning",
                summary=expiry.get("summary", "Domain expiring soon"),
                details=f"Expiry date: {expiry.get('expiry_date', 'unknown')}, {expiry.get('days_remaining', '?')} days remaining",
                suggestion="Renew the domain as soon as possible",
            )
        elif status == "ok":
            return CheckResult(
                name="Domain Expiry",
                status="ok",
                summary=expiry.get("summary", "Domain expiry normal"),
                details=f"{expiry.get('days_remaining', '?')} days remaining",
            )
        else:
            return CheckResult(
                name="Domain Expiry",
                status="warning",
                summary="Cannot confirm domain expiry status",
                details=expiry.get("summary", ""),
            )

    # --- P0: Domain hold status check ---

    def check_domain_hold(self) -> CheckResult:
        """Check whether domain is locked by serverHold/clientHold."""
        whois = self.ctx.whois_result
        if not whois:
            return CheckResult(
                name="Domain Status",
                status="skipped",
                summary="No WHOIS data available, skipping status check",
            )

        dangerous = whois.get("dangerous_statuses", [])
        all_statuses = whois.get("status_check", [])

        if dangerous:
            status_names = [d["status_code"] for d in dangerous]
            meanings = [f"{d['status_code']}: {d['meaning']}" for d in dangerous]
            sug_list = [d["suggestion"] for d in dangerous if d.get("suggestion")]

            return CheckResult(
                name="Domain Status",
                status="critical",
                summary=f"Domain has abnormal status: {', '.join(status_names)}, DNS resolution disabled",
                details="\n".join(meanings),
                suggestion=sug_list[0] if sug_list else "Contact domain registrar",
            )

        normal_codes = {"ok", "active"}
        non_normal = [s for s in all_statuses
                      if s["status_code"] not in normal_codes and not s["is_dangerous"]]

        if non_normal:
            return CheckResult(
                name="Domain Status",
                status="ok",
                summary="Domain status normal (lock protections present, do not affect resolution)",
                details=", ".join(s["status_code"] for s in non_normal),
            )

        return CheckResult(
            name="Domain Status",
            status="ok",
            summary="Domain status normal",
        )

    # --- P1: DNS vendor check ---

    def check_dns_vendor(self) -> CheckResult:
        """Check whether domain NS points to Alibaba Cloud DNS."""
        ns_records = self.ctx.ns_records

        if not ns_records:
            return CheckResult(
                name="DNS Vendor",
                status="warning",
                summary="No NS records found",
                suggestion="Verify that domain has DNS servers configured",
            )

        if is_alicloud_ns(ns_records):
            return CheckResult(
                name="DNS Vendor",
                status="ok",
                summary="Domain uses Alibaba Cloud DNS",
                details=f"NS: {', '.join(ns_records)}",
            )
        else:
            return CheckResult(
                name="DNS Vendor",
                status="warning",
                summary="Domain does not use Alibaba Cloud DNS, using third-party DNS provider",
                details=f"Current NS: {', '.join(ns_records)}",
                suggestion="If this is an Alibaba Cloud DNS issue, change NS to Alibaba Cloud DNS first; if using third-party DNS, contact that provider",
            )

    # --- P1: Recursive resolution trace check ---

    def check_recursive_resolution(self) -> CheckResult:
        """Check whether recursive resolution chain is complete."""
        multi = self.ctx.multi_server_results
        trace = self.ctx.trace_result

        if not multi and not trace:
            return CheckResult(
                name="Recursive Resolution",
                status="skipped",
                summary="Recursive resolution check not performed",
            )

        issues = []

        if trace and isinstance(trace, str):
            if "SERVFAIL" in trace:
                issues.append("SERVFAIL error during recursive resolution")
            if "REFUSED" in trace:
                issues.append("Recursive resolution request refused (REFUSED)")
            if "NXDOMAIN" in trace and "IN NS" not in trace.split("NXDOMAIN")[0][-200:]:
                issues.append("Domain resolution returns NXDOMAIN (domain not found)")
            if "connection timed out" in trace.lower():
                issues.append("Recursive resolution timeout")

        if multi and isinstance(multi, dict):
            empty_servers = []
            all_empty = True
            has_hijack = False

            for server_name, data in multi.items():
                values = data if isinstance(data, list) else data.get("values", [])
                if not values:
                    empty_servers.append(server_name)
                else:
                    all_empty = False
                    for v in values:
                        if v in HIJACK_IPS:
                            has_hijack = True
                            issues.append(f"{server_name} returned hijack IP: {v}")

            if all_empty:
                issues.append("All public DNS servers failed to resolve this domain")
            elif empty_servers:
                issues.append(f"These DNS servers failed to resolve: {', '.join(empty_servers)}")

        if issues:
            return CheckResult(
                name="Recursive Resolution",
                status="critical" if any("hijack" in i or "failed to resolve" in i for i in issues) else "warning",
                summary="; ".join(issues[:3]),
                details="\n".join(issues),
                suggestion="Resolution blocked by upstream network or hijacked; consider changing domain or contacting ISP",
            )

        return CheckResult(
            name="Recursive Resolution",
            status="ok",
            summary="Recursive resolution chain normal",
        )

    # --- P2: ICP filing check ---

    def check_icp_filing(self) -> CheckResult:
        """Determine ICP filing status from HTTP probe results."""
        http_result = self.ctx.http_probe_result
        if not http_result:
            return CheckResult(
                name="ICP Filing Status",
                status="skipped",
                summary="HTTP probe not performed, skipping ICP check",
            )

        status_map = http_result.get("status_code_map", {})
        if not status_map:
            return CheckResult(
                name="ICP Filing Status",
                status="skipped",
                summary="HTTP probe returned no results",
            )

        icp_block_rate = sum(
            float(rate) for code, rate in status_map.items()
            if code in ICP_BLOCK_STATUS_CODES
        )

        if icp_block_rate > 0.5:
            return CheckResult(
                name="ICP Filing Status",
                status="warning",
                summary=f"Domain may lack ICP filing, {icp_block_rate*100:.0f}% of nodes returned filing block",
                details=f"ICP block status code rate: {icp_block_rate*100:.1f}%",
                suggestion="Missing ICP filing does not affect DNS resolution itself, but blocks HTTP access in mainland China. Complete ICP filing if mainland access is needed.",
            )

        return CheckResult(
            name="ICP Filing Status",
            status="ok",
            summary="No ICP filing block detected",
        )

    # --- P2: DNS config check ---

    def check_dns_config(self) -> CheckResult:
        """Check DNS record configuration."""
        records = self.ctx.config_records

        if not records and self.ctx.product_type in ("public_dns", "gtm"):
            return CheckResult(
                name="DNS Configuration",
                status="warning",
                summary="No DNS records found for this domain",
                suggestion="Check whether DNS records have been added",
            )
        elif not records:
            return CheckResult(
                name="DNS Configuration",
                status="skipped",
                summary="Not hosted on Alibaba Cloud DNS, skipping config check",
            )

        paused = [r for r in records if r.get("Status") in ("Disable", "DISABLE", "0", 0)]
        if paused:
            rr_list = [r.get("RR", "?") for r in paused]
            return CheckResult(
                name="DNS Configuration",
                status="warning",
                summary=f"{len(paused)} paused DNS records found: {', '.join(rr_list[:5])}",
                suggestion="Check whether paused records need to be enabled",
            )

        return CheckResult(
            name="DNS Configuration",
            status="ok",
            summary=f"DNS config normal, {len(records)} records total",
        )

    # --- GTM health check ---

    def check_gtm_health(self) -> CheckResult:
        """Check GTM instance health status."""
        gtm = self.ctx.gtm_info
        if not gtm:
            return CheckResult(
                name="GTM Health",
                status="skipped",
                summary="No GTM config info available",
            )

        issues = []

        if gtm.get("InstanceExpired") or gtm.get("ExpireTimestamp"):
            import time
            exp = gtm.get("ExpireTimestamp", 0)
            if exp and exp < time.time() * 1000:
                issues.append("GTM instance has expired")

        cname = gtm.get("Cname") or (gtm.get("Config", {}).get("PublicCnameMode", ""))
        if not cname:
            issues.append("GTM CNAME not configured")

        if issues:
            return CheckResult(
                name="GTM Health",
                status="critical" if "expired" in str(issues) else "warning",
                summary="; ".join(issues),
                suggestion="Check GTM instance configuration and expiry date",
            )

        return CheckResult(
            name="GTM Health",
            status="ok",
            summary="GTM instance config normal",
        )

    # --- PrivateZone binding check ---

    def check_privatezone_binding(self) -> CheckResult:
        """Check PrivateZone VPC binding."""
        pz = self.ctx.privatezone_info
        if not pz:
            return CheckResult(
                name="PrivateZone VPC Binding",
                status="skipped",
                summary="No PrivateZone info available",
            )

        vpcs = pz.get("BindVpcs", {}).get("Vpc", [])
        if not vpcs:
            return CheckResult(
                name="PrivateZone VPC Binding",
                status="critical",
                summary="PrivateZone not bound to any VPC, resolution will fail within VPC",
                suggestion="Bind PrivateZone to the target VPC",
            )

        vpc_ids = [v.get("VpcId", "") for v in vpcs]
        return CheckResult(
            name="PrivateZone VPC Binding",
            status="ok",
            summary=f"PrivateZone bound to {len(vpcs)} VPC(s)",
            details=f"VPC: {', '.join(vpc_ids[:5])}",
        )

    # --- Cross-reference ---

    def cross_reference_config_vs_probe(self) -> list:
        """Compare authoritative config records with DNS probe results to find inconsistencies."""
        config = self.ctx.config_records
        probe = self.ctx.dns_probe_result

        if not config or not probe:
            return []

        discrepancies = []

        expected_ips = set()
        expected_cnames = set()
        for rec in config:
            rtype = rec.get("Type", "")
            value = rec.get("Value", "").rstrip(".")
            status = rec.get("Status", "Enable")
            if status in ("Disable", "DISABLE", "0", 0):
                continue
            if rtype == "A":
                expected_ips.add(value)
            elif rtype == "AAAA":
                expected_ips.add(value)
            elif rtype == "CNAME":
                expected_cnames.add(value.lower())

        ip_count_map = probe.get("ip_count_map", {})
        actual_ips = set()
        hijack_ips = set()
        empty_count = 0

        for ip, count in ip_count_map.items():
            ip_clean = ip.strip().rstrip(".")
            if ip_clean == "-" or not ip_clean:
                empty_count = count
            elif ip_clean in HIJACK_IPS:
                hijack_ips.add(ip_clean)
            else:
                actual_ips.add(ip_clean)

        total = sum(ip_count_map.values()) if ip_count_map else 0

        if hijack_ips:
            hijack_count = sum(ip_count_map.get(ip, 0) for ip in hijack_ips)
            rate = hijack_count / total if total else 0
            discrepancies.append(Discrepancy(
                description=f"ISP hijacking detected: {rate*100:.1f}% of nodes resolved to hijack IPs ({', '.join(hijack_ips)})",
                expected=", ".join(expected_ips) if expected_ips else "(CNAME record)",
                actual=", ".join(hijack_ips),
                severity="critical",
            ))

        if total > 0 and empty_count > 0:
            empty_rate = empty_count / total
            if empty_rate > 0.5:
                discrepancies.append(Discrepancy(
                    description=f"{empty_rate*100:.0f}% of probe nodes failed to resolve this domain",
                    expected=", ".join(expected_ips) if expected_ips else "Valid resolution result",
                    actual="Resolution failed (no result)",
                    severity="critical",
                ))

        if expected_ips and actual_ips:
            unexpected_ips = actual_ips - expected_ips
            if unexpected_ips and not expected_cnames:
                discrepancies.append(Discrepancy(
                    description=f"Some nodes resolved to unexpected IPs: {', '.join(unexpected_ips)}",
                    expected=", ".join(expected_ips),
                    actual=", ".join(actual_ips),
                    severity="warning",
                ))

        return discrepancies


# --- CLI entry point ---

def main():
    import json
    print(json.dumps({
        "message": "dns_analyzer.py is a library module, use via DnsAnalyzer class.",
        "usage": "from dns_analyzer import DnsAnalyzer; analyzer = DnsAnalyzer(context); result = analyzer.analyze()",
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
