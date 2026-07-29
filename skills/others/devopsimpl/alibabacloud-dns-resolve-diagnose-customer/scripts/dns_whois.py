"""
dns_whois.py - WHOIS query wrapper

Provides domain WHOIS lookup: expiry check, domain status check, etc.
Compatible with multiple registry formats such as CNNIC and ICANN.
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

HAS_WHOIS = shutil.which("whois") is not None

# Domain status code meaning map
DOMAIN_STATUS_MAP = {
    "clienthold": {
        "meaning": "Registrar has suspended resolution",
        "impact": "Domain resolution completely broken",
        "suggestion": "Contact the registrar to remove clientHold status",
    },
    "serverhold": {
        "meaning": "Registry has suspended resolution (usually due to missing real-name verification or violation)",
        "impact": "Domain resolution completely broken",
        "suggestion": "Check real-name verification status; contact the registry if there is a violation",
    },
    "clienttransferprohibited": {
        "meaning": "Registrar transfer prohibited",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "servertransferprohibited": {
        "meaning": "Registry transfer prohibited",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "clientupdateprohibited": {
        "meaning": "Registrar update prohibited",
        "impact": "Existing resolution unaffected, but DNS config cannot be modified",
        "suggestion": "To modify DNS config, contact the registrar to remove this lock",
    },
    "serverupdateprohibited": {
        "meaning": "Registry update prohibited",
        "impact": "Existing resolution unaffected, but DNS config cannot be modified",
        "suggestion": None,
    },
    "clientdeleteprohibited": {
        "meaning": "Registrar delete prohibited",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "serverdeleteprohibited": {
        "meaning": "Registry delete prohibited",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "pendingdelete": {
        "meaning": "Domain pending delete (redemption period passed)",
        "impact": "Domain about to be released; resolution likely broken",
        "suggestion": "Domain cannot be recovered; wait for release and re-register",
    },
    "redemptionperiod": {
        "meaning": "Domain in redemption period",
        "impact": "Domain resolution is broken",
        "suggestion": "Contact the registrar to redeem the domain",
    },
    "pendingtransfer": {
        "meaning": "Domain transfer in progress",
        "impact": "Resolution may be unstable during transfer",
        "suggestion": "Check DNS config after the transfer completes",
    },
    "ok": {
        "meaning": "Normal status",
        "impact": "No impact",
        "suggestion": None,
    },
    "active": {
        "meaning": "Normal active status",
        "impact": "No impact",
        "suggestion": None,
    },
}

# Dangerous status codes affecting DNS resolution
DANGEROUS_STATUSES = frozenset({
    "clienthold", "serverhold", "pendingdelete", "redemptionperiod",
})


def _run_cmd(cmd: list, timeout: int = 15) -> tuple:
    """Run command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


# ─── WHOIS query ───────────────────────────────────────────────────

def whois_query(domain: str) -> dict:
    """
    Run WHOIS query and parse the result.

    Returns:
        dict: {
            "raw": str,              # Raw WHOIS output
            "domain": str,
            "registrar": str,
            "creation_date": str,
            "expiry_date": str,
            "updated_date": str,
            "status": [str],         # Domain status code list
            "name_servers": [str],   # DNS server list
            "registrant": str,
            "error": str or None,
        }
    """
    if not HAS_WHOIS:
        return {
            "raw": "",
            "domain": domain,
            "error": "whois command unavailable, please install whois",
        }

    # Extract root domain for query (strip subdomain prefix)
    root = _extract_root_domain(domain)

    rc, out, err = _run_cmd(["whois", root], timeout=20)
    if rc != 0 and not out:
        return {
            "raw": err,
            "domain": root,
            "error": f"WHOIS query failed: {err}",
        }

    parsed = parse_whois_output(out)
    parsed["raw"] = out
    parsed["domain"] = root
    parsed["error"] = None

    return parsed


def _extract_root_domain(domain: str) -> str:
    """Extract root domain from full domain (strip subdomain prefix)."""
    # Use dns_common's splitting logic
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    try:
        from dns_common import split_domain
        candidates = split_domain(domain)
        if candidates:
            # Use the shortest zone (i.e. root domain)
            return candidates[0].zone
    except ImportError:
        pass

    # Fallback: simply take the last two segments
    parts = domain.rstrip(".").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return domain


def parse_whois_output(raw: str) -> dict:
    """
    Parse raw WHOIS output, compatible with multiple registry formats.

    Returns:
        dict with keys: registrar, creation_date, expiry_date, updated_date,
                        status, name_servers, registrant
    """
    result = {
        "registrar": "",
        "creation_date": "",
        "expiry_date": "",
        "updated_date": "",
        "status": [],
        "name_servers": [],
        "registrant": "",
    }

    lines = raw.splitlines()

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped or line_stripped.startswith("%") or line_stripped.startswith("#"):
            continue

        low = line_stripped.lower()

        # Registrar
        if _match_key(low, ["registrar:", "sponsoring registrar:"]):
            result["registrar"] = _extract_value(line_stripped)

        # Creation date
        elif _match_key(low, [
            "creation date:", "registration time:", "created:",
            "domain registration date:", "registration date:",
            "created on:", "create date:",
        ]):
            result["creation_date"] = _extract_value(line_stripped)

        # Expiry date
        elif _match_key(low, [
            "registry expiry date:", "expiration time:", "expiry date:",
            "domain expiration date:", "registrar registration expiration date:",
            "expires:", "expired:", "expire date:", "expiration date:",
            "paid-till:",
        ]):
            result["expiry_date"] = _extract_value(line_stripped)

        # Update date
        elif _match_key(low, [
            "updated date:", "last modified:", "last updated:",
            "updated:", "last update:",
        ]):
            result["updated_date"] = _extract_value(line_stripped)

        # Domain status
        elif _match_key(low, ["domain status:", "status:"]):
            status_val = _extract_value(line_stripped)
            # Status may carry a URL, e.g. "clientTransferProhibited https://..."
            status_code = status_val.split()[0] if status_val else ""
            if status_code:
                result["status"].append(status_code)

        # DNS servers
        elif _match_key(low, [
            "name server:", "nserver:", "dns:",
            "name servers:", "nameserver:",
        ]):
            ns = _extract_value(line_stripped)
            if ns:
                result["name_servers"].append(ns.lower())

        # Registrant
        elif _match_key(low, [
            "registrant:", "registrant organization:",
            "registrant name:", "registrant contact name:",
        ]):
            if not result["registrant"]:
                result["registrant"] = _extract_value(line_stripped)

    return result


def _match_key(low_line: str, keys: list) -> bool:
    """Check if a line starts with the given key."""
    return any(low_line.startswith(k) for k in keys)


def _extract_value(line: str) -> str:
    """Extract Value from 'Key: Value' format."""
    idx = line.find(":")
    if idx >= 0:
        return line[idx + 1:].strip()
    return line.strip()


# ─── Expiry check ──────────────────────────────────────────────────

def check_expiry(whois_result: dict) -> dict:
    """
    Check domain expiry status.

    Returns:
        dict: {
            "status": "ok" / "warning" / "critical" / "unknown",
            "expiry_date": str,
            "days_remaining": int or None,
            "summary": str,
        }
    """
    expiry_str = whois_result.get("expiry_date", "")
    if not expiry_str:
        return {
            "status": "unknown",
            "expiry_date": "",
            "days_remaining": None,
            "summary": "Cannot get domain expiry time",
        }

    expiry_dt = _parse_date(expiry_str)
    if not expiry_dt:
        return {
            "status": "unknown",
            "expiry_date": expiry_str,
            "days_remaining": None,
            "summary": f"Cannot parse expiry time format: {expiry_str}",
        }

    now = datetime.now(timezone.utc)
    if expiry_dt.tzinfo is None:
        # Assume UTC
        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

    delta = expiry_dt - now
    days = delta.days

    if days < 0:
        return {
            "status": "critical",
            "expiry_date": expiry_str,
            "days_remaining": days,
            "summary": f"Domain expired {abs(days)} days ago; this breaks DNS resolution entirely",
        }
    elif days < 30:
        return {
            "status": "warning",
            "expiry_date": expiry_str,
            "days_remaining": days,
            "summary": f"Domain expires in {days} days; renew as soon as possible",
        }
    else:
        return {
            "status": "ok",
            "expiry_date": expiry_str,
            "days_remaining": days,
            "summary": f"Domain validity OK, {days} days remaining",
        }


def _parse_date(date_str: str) -> Optional[datetime]:
    """Try parsing multiple date formats."""
    date_str = date_str.strip()

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",           # ISO 8601
        "%Y-%m-%dT%H:%M:%S%z",          # ISO 8601 with tz
        "%Y-%m-%d %H:%M:%S",            # Standard
        "%Y-%m-%d",                      # Date only
        "%d-%b-%Y",                      # 01-Jan-2025
        "%Y/%m/%d",                      # 2025/01/01
        "%Y/%m/%d %H:%M:%S",            # 2025/01/01 00:00:00
        "%d %b %Y",                      # 01 Jan 2025
        "%a %b %d %H:%M:%S %Z %Y",     # Thu Jan 01 00:00:00 UTC 2025
        "%Y.%m.%d",                      # 2025.01.01
        "%Y. %m. %d.",                   # Korean format
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    # Try extracting the date part via regex
    match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_str)
    if match:
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
            try:
                return datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue

    return None


# ─── Domain status check ───────────────────────────────────────────

def check_hold_status(whois_result: dict) -> list:
    """
    Check whether status codes contain anomalies that affect resolution.

    Returns:
        list[dict]: anomaly status list, each item contains:
            {status_code, meaning, impact, suggestion, is_dangerous}
    """
    statuses = whois_result.get("status", [])
    issues = []

    for status in statuses:
        # Extract pure status code (strip URL suffix, etc.)
        code = status.split()[0].strip().lower()
        # Strip possible prefix "https://icann.org/epp#"
        if "#" in code:
            code = code.split("#")[-1]

        info = DOMAIN_STATUS_MAP.get(code, {})
        is_dangerous = code in DANGEROUS_STATUSES

        if info:
            issues.append({
                "status_code": code,
                "meaning": info.get("meaning", ""),
                "impact": info.get("impact", ""),
                "suggestion": info.get("suggestion", ""),
                "is_dangerous": is_dangerous,
            })
        elif code and code not in ("ok", "active"):
            issues.append({
                "status_code": code,
                "meaning": f"Unknown status code: {code}",
                "impact": "Needs further confirmation",
                "suggestion": "Please refer to the domain registry documentation",
                "is_dangerous": False,
            })

    return issues


def get_dangerous_statuses(whois_result: dict) -> list:
    """
    Return only dangerous statuses affecting DNS resolution.

    Returns:
        list[dict]: dangerous status list
    """
    all_issues = check_hold_status(whois_result)
    return [i for i in all_issues if i["is_dangerous"]]


# ─── CLI entry point ──────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="DNS WHOIS query tool")
    parser.add_argument("--domain", required=True, help="Target domain")
    parser.add_argument(
        "--action",
        choices=["query", "expiry", "status", "full"],
        default="full",
        help="Operation type (default full)",
    )

    args = parser.parse_args()
    result = whois_query(args.domain)

    if result.get("error"):
        print(json.dumps({"error": result["error"]}, ensure_ascii=False, indent=2))
        return

    if args.action == "query":
        # Output parsed WHOIS info (without raw)
        output = {k: v for k, v in result.items() if k != "raw"}
        print(json.dumps(output, ensure_ascii=False, indent=2))

    elif args.action == "expiry":
        expiry = check_expiry(result)
        print(json.dumps(expiry, ensure_ascii=False, indent=2))

    elif args.action == "status":
        issues = check_hold_status(result)
        print(json.dumps(issues, ensure_ascii=False, indent=2))

    elif args.action == "full":
        output = {
            "whois": {k: v for k, v in result.items() if k != "raw"},
            "expiry_check": check_expiry(result),
            "status_check": check_hold_status(result),
            "dangerous_statuses": get_dangerous_statuses(result),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
