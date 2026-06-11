"""
dns_report.py - DNS diagnostic report generator.

Formats DnsAnalyzer diagnosis results into Markdown reports in two versions:
customer-facing (easy to understand) and support-facing (technically detailed).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dns_common import DiagnosisResult, DomainDiagContext

STATUS_ICONS = {
    "ok": "Normal",
    "warning": "Warning",
    "critical": "Critical",
    "error": "Error",
    "skipped": "Skipped",
}

PRODUCT_NAMES = {
    "public_dns": "Public Authoritative DNS (Alibaba Cloud DNS)",
    "gtm": "Global Traffic Manager (GTM)",
    "privatezone": "Private DNS (PrivateZone)",
    "third_party": "Third-party DNS",
    "third_party_with_alicloud_domain": "Alibaba Cloud Domain + Third-party DNS",
    "unknown": "Unknown",
}


def generate_customer_report(result: DiagnosisResult,
                             context: DomainDiagContext) -> str:
    """
    Generate customer-facing diagnostic report.
    Uses plain language, actionable suggestions, hides internal technical details.
    """
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("## DNS Resolution Diagnostic Report")
    lines.append("")
    lines.append(f"**Domain**: `{context.domain}`")
    lines.append(f"**Time**: {now}")
    lines.append(f"**Product Type**: {PRODUCT_NAMES.get(context.product_type, context.product_type)}")
    if context.problem_description:
        lines.append(f"**Problem**: {context.problem_description}")
    lines.append("")

    lines.append("### Diagnosis Conclusion")
    lines.append("")
    if result.severity == "normal":
        lines.append("DNS diagnosis found no issues, all checks passed.")
    elif result.severity == "critical":
        lines.append("**Critical issues found**, details below:")
    else:
        lines.append("The following issues need attention:")
    lines.append("")

    lines.append("### Check Results Summary")
    lines.append("")
    lines.append("| Check Item | Status | Details |")
    lines.append("|------------|--------|---------|")

    for check in result.checks:
        status_text = STATUS_ICONS.get(check.status, check.status)
        lines.append(f"| {check.name} | {status_text} | {check.summary} |")
    lines.append("")

    issues = [c for c in result.checks if c.status in ("critical", "warning")]
    if issues or result.discrepancies:
        lines.append("### Issues Found")
        lines.append("")

        for i, check in enumerate(issues, 1):
            lines.append(f"**{i}. {check.name}** ({STATUS_ICONS.get(check.status, check.status)})")
            lines.append(f"   - {check.summary}")
            if check.details:
                lines.append(f"   - Details: {check.details}")
            lines.append("")

        for disc in result.discrepancies:
            lines.append(f"**{len(issues) + 1}. Config vs Probe Inconsistency**")
            lines.append(f"   - {disc.description}")
            if disc.expected:
                lines.append(f"   - Expected: {disc.expected}")
            if disc.actual:
                lines.append(f"   - Actual: {disc.actual}")
            lines.append("")

    if result.suggestions:
        lines.append("### Recommended Actions")
        lines.append("")
        for i, sug in enumerate(result.suggestions, 1):
            lines.append(f"{i}. {sug}")
        lines.append("")

    if context.dns_probe_result:
        lines.append("### DNS Probe Results")
        lines.append("")
        _append_dns_probe_summary(lines, context.dns_probe_result)

    if context.http_probe_result:
        lines.append("### HTTP Probe Results")
        lines.append("")
        _append_http_probe_summary(lines, context.http_probe_result)

    if context.config_records:
        lines.append("### Current DNS Record Configuration")
        lines.append("")
        _append_config_records(lines, context.config_records)

    return "\n".join(lines)


def generate_support_report(result: DiagnosisResult,
                            context: DomainDiagContext) -> str:
    """
    Generate support engineer-facing technical diagnostic report.
    Includes full technical details, root cause chain, internal operation suggestions.
    """
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines.append("## DNS Resolution Diagnostic Report (Support Version)")
    lines.append("")
    lines.append(f"**Domain**: `{context.domain}`")
    lines.append(f"**Time**: {now}")
    lines.append(f"**Product**: {PRODUCT_NAMES.get(context.product_type, context.product_type)}")
    lines.append(f"**Severity**: {result.severity.upper()}")
    if context.problem_description:
        lines.append(f"**Customer Description**: {context.problem_description}")
    lines.append("")

    lines.append("### Quick Summary")
    lines.append("")
    if result.root_causes:
        for cause in result.root_causes:
            lines.append(f"- {cause}")
    else:
        lines.append("- No issues found")
    lines.append("")

    lines.append("### Detailed Check Results")
    lines.append("")
    lines.append("| # | Check Item | Status | Details | Suggestion |")
    lines.append("|---|------------|--------|---------|------------|")

    for i, check in enumerate(result.checks, 1):
        status_text = STATUS_ICONS.get(check.status, check.status)
        suggestion = check.suggestion or "-"
        lines.append(f"| {i} | {check.name} | {status_text} | {check.summary} | {suggestion} |")
    lines.append("")

    if result.discrepancies:
        lines.append("### Config vs Probe Cross-Reference")
        lines.append("")
        for disc in result.discrepancies:
            lines.append(f"- **{disc.severity.upper()}**: {disc.description}")
            lines.append(f"  - Expected: `{disc.expected}`")
            lines.append(f"  - Actual: `{disc.actual}`")
            if disc.affected_regions:
                lines.append(f"  - Affected regions: {', '.join(disc.affected_regions)}")
        lines.append("")

    if context.ns_records:
        lines.append("### NS Records")
        lines.append("")
        for ns in context.ns_records:
            lines.append(f"- `{ns}`")
        lines.append("")

    if context.trace_result and isinstance(context.trace_result, str):
        lines.append("### dig +trace Result")
        lines.append("")
        lines.append("```")
        trace_lines = context.trace_result.splitlines()
        if len(trace_lines) > 50:
            lines.extend(trace_lines[:50])
            lines.append(f"... ({len(trace_lines)} lines total, truncated)")
        else:
            lines.extend(trace_lines)
        lines.append("```")
        lines.append("")

    if context.multi_server_results and isinstance(context.multi_server_results, dict):
        lines.append("### Multi-DNS Server Comparison")
        lines.append("")
        lines.append("| DNS Server | Resolution Result |")
        lines.append("|-----------|------------------|")
        for name, data in context.multi_server_results.items():
            values = data if isinstance(data, list) else data.get("values", [])
            values_str = ", ".join(str(v) for v in values) if values else "(no result)"
            lines.append(f"| {name} | `{values_str}` |")
        lines.append("")

    if context.config_records:
        lines.append("### Authoritative DNS Record Configuration")
        lines.append("")
        _append_config_records(lines, context.config_records, detailed=True)

    if context.abc2_records:
        lines.append("### abc2 Internal Query Results")
        lines.append("")
        _append_config_records(lines, context.abc2_records, detailed=True)

    if context.dns_probe_result:
        lines.append("### DNS Probe Details")
        lines.append("")
        _append_dns_probe_summary(lines, context.dns_probe_result, detailed=True)

    if context.http_probe_result:
        lines.append("### HTTP Probe Details")
        lines.append("")
        _append_http_probe_summary(lines, context.http_probe_result, detailed=True)

    if result.suggestions:
        lines.append("### Recommended Actions")
        lines.append("")
        for i, sug in enumerate(result.suggestions, 1):
            lines.append(f"{i}. {sug}")
        lines.append("")

    if result.severity == "critical":
        lines.append("### Escalation Path")
        lines.append("")
        lines.append("If above troubleshooting cannot resolve the issue, escalate to:")
        if context.product_type == "public_dns":
            lines.append("1. Alibaba Cloud DNS team on-call")
        elif context.product_type == "gtm":
            lines.append("1. GTM product team")
        elif context.product_type == "privatezone":
            lines.append("1. PrivateZone product team")
        else:
            lines.append("1. Network product line on-call")
        lines.append("")

    return "\n".join(lines)


# --- Helper functions ---

def _append_dns_probe_summary(lines: list, probe: dict, detailed: bool = False):
    """Append DNS probe result summary."""
    ip_count = probe.get("ip_count_map", {})
    ip_rate = probe.get("ip_rate_map", {})
    total = probe.get("total_nodes", 0)
    share_url = probe.get("share_url", "")

    if not ip_count and not ip_rate:
        lines.append("DNS probe returned no results.")
        lines.append("")
        return

    lines.append(f"Probe nodes: {total}")
    lines.append("")

    lines.append("| Resolution Result | Node Count | Rate |")
    lines.append("|-------------------|-----------|------|")

    sorted_ips = sorted(ip_count.items(), key=lambda x: x[1], reverse=True)
    for ip, count in sorted_ips:
        rate = ip_rate.get(ip, count / total if total else 0)
        display_ip = "(no result)" if ip == "-" else f"`{ip}`"
        lines.append(f"| {display_ip} | {count} | {rate*100:.1f}% |")

    lines.append("")

    if share_url:
        lines.append(f"Detailed results: {share_url}")
        lines.append("")


def _append_http_probe_summary(lines: list, probe: dict, detailed: bool = False):
    """Append HTTP probe result summary."""
    status_map = probe.get("status_code_map", {})
    total = probe.get("total_nodes", 0)
    share_url = probe.get("share_url", "")

    if not status_map:
        lines.append("HTTP probe returned no results.")
        lines.append("")
        return

    lines.append(f"Probe nodes: {total}")
    lines.append("")

    lines.append("| Status Code | Rate |")
    lines.append("|-------------|------|")

    sorted_codes = sorted(status_map.items(), key=lambda x: float(x[1]), reverse=True)
    for code, rate in sorted_codes:
        rate_float = float(rate)
        lines.append(f"| {code} | {rate_float*100:.1f}% |")

    lines.append("")

    if share_url:
        lines.append(f"Detailed results: {share_url}")
        lines.append("")


def _append_config_records(lines: list, records: list, detailed: bool = False):
    """Append DNS record table."""
    if not records:
        lines.append("No DNS records.")
        lines.append("")
        return

    if detailed:
        lines.append("| Host Record | Type | Value | Line | TTL | Status |")
        lines.append("|-------------|------|-------|------|-----|--------|")
        for rec in records[:50]:
            rr = rec.get("RR", rec.get("Rr", ""))
            rtype = rec.get("Type", "")
            value = rec.get("Value", "")
            line = rec.get("Line", "default")
            ttl = rec.get("TTL", rec.get("Ttl", ""))
            status = rec.get("Status", "")
            if status in ("Enable", "ENABLE", "1"):
                status = "Active"
            elif status in ("Disable", "DISABLE", "0"):
                status = "Paused"
            lines.append(f"| {rr} | {rtype} | `{value}` | {line} | {ttl} | {status} |")
    else:
        lines.append("| Host Record | Type | Value | TTL |")
        lines.append("|-------------|------|-------|-----|")
        for rec in records[:20]:
            rr = rec.get("RR", rec.get("Rr", ""))
            rtype = rec.get("Type", "")
            value = rec.get("Value", "")
            ttl = rec.get("TTL", rec.get("Ttl", ""))
            lines.append(f"| {rr} | {rtype} | `{value}` | {ttl} |")

    if len(records) > (50 if detailed else 20):
        lines.append(f"... ({len(records)} records total)")
    lines.append("")


# --- CLI entry point ---

def main():
    print(json.dumps({
        "message": "dns_report.py is a library module.",
        "usage": "from dns_report import generate_customer_report, generate_support_report",
        "functions": [
            "generate_customer_report(result, context) -> str",
            "generate_support_report(result, context) -> str",
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
