#!/usr/bin/env python3
"""Opt-in endpoint contract probe (N14): ALIYUN_HELP_PROBE=1 python3 scripts/aliyun_help.py

The documentation endpoints used here are public but carry no SLA, and several of their
degradation modes are silent (an out-of-range pageSize answers HTTP 200 with totalCount=0).
This probe re-checks those contracts live so drift is noticed by a scheduled run instead of by
a wrong answer in production. It is never part of the default path, never blocks a command and
issues a handful of read-only requests.

Output: one JSON object on stdout. Exit code 0 = every contract holds, 1 = at least one drift
signal, 2 = the probe could not run (no reachable endpoint at all).
"""

from __future__ import annotations

import json
import re
import sys

from help_core import (
    INTL_SEARCH_PAGESIZE_MAX,
    META_BASE,
    SEARCH_JSON_API,
    SITES,
    _master_llms_url,
)
from help_http import (
    _is_err,
    _looks_like_html,
    fetch,
)

# A pageSize above the documented maximum must still degrade to totalCount=0 (envelope C).
_PAGESIZE_PROBE = INTL_SEARCH_PAGESIZE_MAX + 1


def _probe_search_paging() -> dict:
    """Does an out-of-range pageSize still answer the empty-degradation envelope?"""
    url = (f"{SEARCH_JSON_API}?keywords=oss&pageNum=1&pageSize={_PAGESIZE_PROBE}"
           f"&website=intl&language=en")
    text = fetch(url, max_bytes=2 * 1024 * 1024)
    out = {"check": "search.json pageSize cap", "ok": False, "detail": ""}
    if _is_err(text) or _looks_like_html(text):
        out["detail"] = "endpoint unreachable or interstitial page"
        return out
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        out["detail"] = "non-JSON body"
        return out
    documents = ((data.get("data") or {}).get("documents")) or {}
    total = documents.get("totalCount")
    # The documented contract is 'silently collapses to 0'; anything else is drift.
    out["ok"] = total == 0
    out["detail"] = f"pageSize={_PAGESIZE_PROBE} echoed totalCount={total}"
    return out


def _probe_master_indexes() -> list:
    """Are both master indexes still plain text with real entries?"""
    rows = []
    for site, lang in (("cn", "zh"), ("intl", "en")):
        url = _master_llms_url(site, lang)
        text = fetch(url, allow_redirects=False, max_bytes=8 * 1024 * 1024)
        ok = (not _is_err(text)) and (not _looks_like_html(text)) and text.strip()
        rows.append({"check": f"{site} master llms.txt", "ok": bool(ok),
                     "detail": f"{len(text)} chars" if ok else text[:80]})
    return rows


def _probe_bundle_version() -> dict:
    """Record the help-portal front-end bundle version that renders the pages."""
    url = f"https://{SITES['cn']['result_host']}/zh/oss/"
    text = fetch(url, max_bytes=4 * 1024 * 1024)
    match = re.search(r"aliyun-help/help-portal-fe/([0-9.]+)/", text or "")
    return {"check": "help-portal-fe bundle version", "ok": bool(match),
            "detail": match.group(1) if match else "not found in the served page"}


def _probe_metadata_leg() -> dict:
    """Is the OpenAPI metadata list still served (the api-* legs depend on it)?"""
    url = f"{META_BASE}/products" if META_BASE.rstrip("/").endswith("v1") else META_BASE
    text = fetch(url, max_bytes=4 * 1024 * 1024)
    ok = (not _is_err(text)) and text.strip()
    return {"check": "api.aliyun.com metadata", "ok": bool(ok),
            "detail": f"{len(text)} chars" if ok else text[:80]}


def run_probe() -> int:
    """Run every probe, print the result as JSON, and map it onto an exit code."""
    checks = [_probe_search_paging()] + _probe_master_indexes() + [_probe_bundle_version(),
                                                                  _probe_metadata_leg()]
    reachable = sum(1 for c in checks if "unreachable" not in c["detail"]
                    and "no response" not in c["detail"])
    payload = {"probe": "aliyun-help-endpoint-contract", "checks": checks,
               "drift": [c["check"] for c in checks if not c["ok"]]}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if reachable == 0:
        print("WARN[unreachable]: no probed endpoint answered; the probe says nothing about "
              "contract drift", file=sys.stderr)
        return 2
    return 0 if not payload["drift"] else 1


if __name__ == "__main__":
    sys.exit(run_probe())
