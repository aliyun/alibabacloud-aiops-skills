"""
dns_whois.py - WHOIS query wrapper.

Provides domain WHOIS information lookup, including expiry check and status analysis.
Compatible with CNNIC, ICANN, and other registry formats.
"""

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

HAS_WHOIS = shutil.which("whois") is not None

DOMAIN_STATUS_MAP = {
    "clienthold": {
        "meaning": "Registrar has suspended resolution",
        "impact": "DNS resolution completely disabled",
        "suggestion": "Contact registrar to remove clientHold status",
    },
    "serverhold": {
        "meaning": "Registry has suspended resolution (typically due to missing real-name verification or violation)",
        "impact": "DNS resolution completely disabled",
        "suggestion": "Check domain real-name verification status; contact registry if violation",
    },
    "clienttransferprohibited": {
        "meaning": "Registrar has locked transfer",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "servertransferprohibited": {
        "meaning": "Registry has locked transfer",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "clientupdateprohibited": {
        "meaning": "Registrar has locked updates",
        "impact": "Does not affect existing resolution, but cannot modify DNS config",
        "suggestion": "Contact registrar to unlock if DNS changes needed",
    },
    "serverupdateprohibited": {
        "meaning": "Registry has locked updates",
        "impact": "Does not affect existing resolution, but cannot modify DNS config",
        "suggestion": None,
    },
    "clientdeleteprohibited": {
        "meaning": "Registrar has locked deletion",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "serverdeleteprohibited": {
        "meaning": "Registry has locked deletion",
        "impact": "Does not affect resolution",
        "suggestion": None,
    },
    "pendingdelete": {
        "meaning": "Domain pending deletion (redemption period expired)",
        "impact": "Domain will be released soon, resolution may already be disabled",
        "suggestion": "Domain cannot be recovered; wait for release and re-register",
    },
    "redemptionperiod": {
        "meaning": "Domain in redemption period",
        "impact": "DNS resolution disabled",
        "suggestion": "Contact registrar to redeem the domain",
    },
    "pendingtransfer": {
        "meaning": "Domain transfer in progress",
        "impact": "Resolution may be unstable during transfer",
        "suggestion": "Wait for transfer to complete, then verify DNS config",
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

DANGEROUS_STATUSES = frozenset({
    "clienthold", "serverhold", "pendingdelete", "redemptionperiod",
})


def _run_cmd(cmd: list, timeout: int = 15) -> tuple:
    """Execute a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"


# --- WHOIS query ---

def whois_query(domain: str) -> dict:
    """
    Execute WHOIS query and parse results.

    Returns:
        dict: {
            "raw": str,
            "domain": str,
            "registrar": str,
            "creation_date": str,
            "expiry_date": str,
            "updated_date": str,
            "status": [str],
            "name_servers": [str],
            "registrant": str,
            "error": str or None,
        }
    """
    if not HAS_WHOIS:
        return {
            "raw": "",
            "domain": domain,
            "error": "whois command not available, please install whois tool",
        }

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
    """Extract root domain from a full domain (remove subdomain prefix)."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    try:
        from dns_common import split_domain
        candidates = split_domain(domain)
        if candidates:
            return candidates[0].zone
    except ImportError:
        pass

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

        if _match_key(low, ["registrar:", "sponsoring registrar:"]):
            result["registrar"] = _extract_value(line_stripped)

        elif _match_key(low, [
            "creation date:", "registration time:", "created:",
            "domain registration date:", "registration date:",
            "created on:", "create date:",
        ]):
            result["creation_date"] = _extract_value(line_stripped)

        elif _match_key(low, [
            "registry expiry date:", "expiration time:", "expiry date:",
            "domain expiration date:", "registrar registration expiration date:",
            "expires:", "expired:", "expire date:", "expiration date:",
            "paid-till:",
        ]):
            result["expiry_date"] = _extract_value(line_stripped)

        elif _match_key(low, [
            "updated date:", "last modified:", "last updated:",
            "updated:", "last update:",
        ]):
            result["updated_date"] = _extract_value(line_stripped)

        elif _match_key(low, ["domain status:", "status:"]):
            status_val = _extract_value(line_stripped)
            status_code = status_val.split()[0] if status_val else ""
            if status_code:
                result["status"].append(status_code)

        elif _match_key(low, [
            "name server:", "nserver:", "dns:",
            "name servers:", "nameserver:",
        ]):
            ns = _extract_value(line_stripped)
            if ns:
                result["name_servers"].append(ns.lower())

        elif _match_key(low, [
            "registrant:", "registrant organization:",
            "registrant name:", "registrant contact name:",
        ]):
            if not result["registrant"]:
                result["registrant"] = _extract_value(line_stripped)

    return result


def _match_key(low_line: str, keys: list) -> bool:
    """Check whether a line starts with one of the specified keys."""
    return any(low_line.startswith(k) for k in keys)


def _extract_value(line: str) -> str:
    """Extract value from 'Key: Value' format."""
    idx = line.find(":")
    if idx >= 0:
        return line[idx + 1:].strip()
    return line.strip()


# --- Expiry check ---

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
            "summary": "Cannot determine domain expiry date",
        }

    expiry_dt = _parse_date(expiry_str)
    if not expiry_dt:
        return {
            "status": "unknown",
            "expiry_date": expiry_str,
            "days_remaining": None,
            "summary": f"Cannot parse expiry date format: {expiry_str}",
        }

    now = datetime.now(timezone.utc)
    if expiry_dt.tzinfo is None:
        expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)

    delta = expiry_dt - now
    days = delta.days

    if days < 0:
        return {
            "status": "critical",
            "expiry_date": expiry_str,
            "days_remaining": days,
            "summary": f"Domain expired {abs(days)} days ago, DNS resolution will be completely disabled",
        }
    elif days < 30:
        return {
            "status": "warning",
            "expiry_date": expiry_str,
            "days_remaining": days,
            "summary": f"Domain expires in {days} days, renewal recommended",
        }
    else:
        return {
            "status": "ok",
            "expiry_date": expiry_str,
            "days_remaining": days,
            "summary": f"Domain expiry normal, {days} days remaining",
        }


def _parse_date(date_str: str) -> Optional[datetime]:
    """Try to parse multiple date formats."""
    date_str = date_str.strip()

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M:%S",
        "%d %b %Y",
        "%a %b %d %H:%M:%S %Z %Y",
        "%Y.%m.%d",
        "%Y. %m. %d.",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue

    match = re.search(r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})", date_str)
    if match:
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]:
            try:
                return datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue

    return None


# --- Domain status check ---

def check_hold_status(whois_result: dict) -> list:
    """
    Check domain status codes for resolution-affecting abnormalities.

    Returns:
        list[dict]: Each containing:
            {status_code, meaning, impact, suggestion, is_dangerous}
    """
    statuses = whois_result.get("status", [])
    issues = []

    for status in statuses:
        code = status.split()[0].strip().lower()
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
                "impact": "Needs further investigation",
                "suggestion": "Check registry documentation",
                "is_dangerous": False,
            })

    return issues


def get_dangerous_statuses(whois_result: dict) -> list:
    """
    Return only statuses that affect DNS resolution.

    Returns:
        list[dict]: Dangerous status list
    """
    all_issues = check_hold_status(whois_result)
    return [i for i in all_issues if i["is_dangerous"]]


# --- CLI entry point ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="DNS WHOIS query tool")
    parser.add_argument("--domain", required=True, help="Target domain")
    parser.add_argument(
        "--action",
        choices=["query", "expiry", "status", "full"],
        default="full",
        help="Action type (default: full)",
    )

    args = parser.parse_args()
    result = whois_query(args.domain)

    if result.get("error"):
        print(json.dumps({"error": result["error"]}, ensure_ascii=False, indent=2))
        return

    if args.action == "query":
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
