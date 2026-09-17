#!/usr/bin/env python3
# SECURITY: knowledge-driven diagnosis only. This script performs NO network
# calls, invokes NO aliyun CLI, and calls NO cloud API. It maps a backup-tool
# x symptom combination to configuration guidance using the embedded catalog,
# then emits structured JSON plus STATUS/NEXT_ACTION.
"""Entry script for alibabacloud-oss-backup-integration-diagnosis.

Usage (all parameters optional):
  python3 oss_backup_integration_diagnosis.py \
      [--tool veeam|synology|generic|<name>] [--error-code TEXT] \
      [--symptom TEXT] [--storage-class standard|ia|archive|coldarchive|deepcoldarchive] \
      [--bucket BUCKET] [--region REGION]

Matching ladder (pure functions, unit-testable):
  1. error-message routing (exact/fuzzy alias hit)    -> STATUS: OK / DEGRADED
  2. tool catalog match (exact/fuzzy alias hit)       -> STATUS: OK / DEGRADED
  3. symptom routing (whitelist/path-style/V1/format) -> STATUS: OK
     symptom routing (retrieval fee):
        storage class known                              -> STATUS: OK
        storage class missing                            -> STATUS: DEGRADED
  4. storage class only                               -> STATUS: DEGRADED
  5. nothing recognizable                             -> STATUS: FAIL (exit 1)
"""

import argparse
import json
import sys
import uuid

import _doc_lookup

from _integration_catalog import (
    CATEGORY_LABELS,
    ERROR_ROUTES,
    FORMAT_NOTE,
    RETRIEVAL_RULES,
    S3_ENDPOINT_FORMS,
    STORAGE_CLASS_ALIASES,
    SYMPTOM_ROUTES,
    TOOL_CATALOG,
    TOOL_KEYS,
    WHITELIST_GUIDANCE,
)

SKILL_NAME = "alibabacloud-oss-backup-integration-diagnosis"

# --- Observability (SA-2.11c): session id + User-Agent template ------------
# Even though this skill makes zero cloud API calls, the session id and the
# User-Agent string are generated here so any future HTTP usage is traceable.
SESSION_ID = uuid.uuid4().hex  # 32-char lowercase hex
SKILL_VERSION = "1.0.0"  # UA skill-version; matches references/manifest.json
USER_AGENT = "AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{version}".format(
    skill=SKILL_NAME, session_id=SESSION_ID, version=SKILL_VERSION
)

ROUTE_KEYS = sorted(ERROR_ROUTES.keys())


# --- Pure matching functions (no I/O, no side effects) ----------------------

def normalize_text(value):
    """Return stripped string, or '' for None/non-str input."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def match_tool(raw_tool):
    """Match a raw tool name against TOOL_CATALOG aliases.

    Returns (match_type, canonical_tool):
      ("exact",   key)  alias equals input (case-insensitive)
      ("fuzzy",   key)  unique alias substring overlap
      ("ambiguous", None) multiple tools matched
      ("none",    None) no hit / empty input
    """
    tool = normalize_text(raw_tool)
    if not tool:
        return ("none", None)
    lowered = tool.lower()
    hits = []
    for key in TOOL_KEYS:
        aliases = TOOL_CATALOG[key]["aliases"]
        for alias in aliases:
            a = alias.lower()
            if lowered == a:
                return ("exact", key)
            if a in lowered or lowered in a:
                hits.append(key)
                break
    hits = sorted(set(hits))
    if len(hits) == 1:
        # 'generic' alias list is broad; prefer a specific tool if it was the
        # only fuzzy hit - already guaranteed here.
        return ("fuzzy", hits[0])
    if len(hits) > 1:
        return ("ambiguous", None)
    return ("none", None)


def match_error_route(raw_code):
    """Match raw error text against ERROR_ROUTES aliases.

    Returns (match_type, canonical_route):
      ("exact",   key)  an alias equals the input (case-insensitive)
      ("fuzzy",   key)  unique alias substring overlap
      ("ambiguous", None) multiple routes matched
      ("none",    None) no hit / empty input
    """
    code = normalize_text(raw_code)
    if not code:
        return ("none", None)
    lowered = code.lower()
    hits = []
    for key in ROUTE_KEYS:
        for alias in ERROR_ROUTES[key]["aliases"]:
            a = alias.lower()
            if lowered == a:
                return ("exact", key)
            if a in lowered or lowered in a:
                hits.append(key)
                break
    hits = sorted(set(hits))
    if len(hits) == 1:
        return ("fuzzy", hits[0])
    if len(hits) > 1:
        return ("ambiguous", None)
    return ("none", None)


def match_symptom_route(raw_symptom):
    """Route free-form symptom text; returns route_id or None (first hit wins)."""
    symptom = normalize_text(raw_symptom)
    if not symptom:
        return None
    for route_id, pattern in SYMPTOM_ROUTES:
        if pattern.search(symptom):
            return route_id
    return None


def resolve_storage_class(raw_class):
    """Map a raw storage-class string to a canonical RETRIEVAL_RULES key or ''."""
    text = normalize_text(raw_class)
    if not text:
        return ""
    lowered = text.lower()
    for canonical, aliases in STORAGE_CLASS_ALIASES.items():
        if lowered == canonical:
            return canonical
        for alias in aliases:
            if lowered == alias.lower():
                return canonical
    for canonical, aliases in STORAGE_CLASS_ALIASES.items():
        for alias in aliases:
            a = alias.lower()
            # Short aliases (<=3 chars, e.g. "ia") are excluded from the
            # bidirectional substring pass: an incidental substring hit
            # ("california" contains "ia") outweighs fuzzy recall; they
            # are still matched by the exact alias table above.
            if len(a) <= 3:
                continue
            if a in lowered or lowered in a:
                return canonical
    return ""


def build_route_block(route_id):
    """Build the diagnosis block for one error route (pure)."""
    entry = ERROR_ROUTES[route_id]
    return {
        "route": route_id,
        "category": entry["category"],
        "category_label": CATEGORY_LABELS[entry["category"]],
        "side": entry["side"],
        "root_cause_directions": list(entry["root_cause_directions"]),
        "configuration_advice": list(entry["configuration_advice"]),
        "official_doc_ref": entry["official_doc_ref"],
    }


def build_tool_block(tool_key):
    """Build the diagnosis block for one tool catalog entry (pure)."""
    entry = TOOL_CATALOG[tool_key]
    return {
        "tool": tool_key,
        "category": entry["category"],
        "category_label": CATEGORY_LABELS[entry["category"]],
        "side": entry["side"],
        "summary": entry["summary"],
        "config_checklist": list(entry["config_checklist"]),
        "known_issues": list(entry["known_issues"]),
        "remediation_boundary": entry["remediation_boundary"],
        "s3_endpoint_forms": list(S3_ENDPOINT_FORMS),
        "official_doc_ref": entry["official_doc_ref"],
    }


def build_retrieval_block(storage_class):
    """Build the retrieval-fee judgment block for a canonical class (pure)."""
    entry = RETRIEVAL_RULES[storage_class]
    return {
        "storage_class": storage_class,
        "storage_class_label": entry["label"],
        "retrieval_fee_applies": entry["retrieval_fee"],
        "category": "retrieval_fee",
        "category_label": CATEGORY_LABELS["retrieval_fee"],
        "judgment": list(entry["judgment"]),
        "recommendations": list(entry["recommendations"]),
    }


def diagnose(tool=None, error_code=None, symptom=None, storage_class=None,
             bucket=None, region=None):
    """Pure decision function. Returns (exit_code, result_dict)."""
    result = {
        "skill": SKILL_NAME,
        "session_id": SESSION_ID,
        "user_agent": USER_AGENT,
        "inputs": {
            "tool": normalize_text(tool),
            "error_code": normalize_text(error_code),
            "symptom": normalize_text(symptom),
            "storage_class": normalize_text(storage_class),
            "bucket": normalize_text(bucket),
            "region": normalize_text(region),
        },
        "references": [
            "references/integration-playbook.md",
            "references/s3-compat-notes.md",
            "references/retrieval-fee-guide.md",
        ],
        "boundary": (
            "Configuration advice only: this skill performs no cloud API "
            "calls, never modifies buckets/RAM/tools, and never submits "
            "whitelist requests on the user's behalf."
        ),
    }

    sc = resolve_storage_class(storage_class)
    if storage_class and not sc:
        result["storage_class_warning"] = (
            "Unrecognized --storage-class value '{0}'; expected one of: "
            "standard, ia, archive, coldarchive, deepcoldarchive.".format(
                normalize_text(storage_class))
        )

    # Ladder 1: error-message routing.
    route_type, route_key = match_error_route(error_code)
    if route_type in ("exact", "fuzzy"):
        result["match"] = {"type": "error_route", "route": route_key,
                           "match_kind": route_type}
        result["diagnosis"] = build_route_block(route_key)
        tool_type, tool_key = match_tool(tool)
        if tool_type in ("exact", "fuzzy"):
            result["tool_context"] = build_tool_block(tool_key)
        status = "OK" if route_type == "exact" else "DEGRADED"
        result["status"] = status
        result["next_action"] = (
            "Report the root-cause directions and configuration advice for "
            "route {key} verbatim from the diagnosis block; include the tool "
            "checklist when tool_context is present; do not execute any "
            "change."
        ).format(key=route_key)
        return (0, result)
    if route_type == "ambiguous":
        result["match"] = {"type": "ambiguous_error", "route": None}
        result["candidates"] = [
            k for k in ROUTE_KEYS
            if any(a.lower() in normalize_text(error_code).lower()
                   or normalize_text(error_code).lower() in a.lower()
                   for a in ERROR_ROUTES[k]["aliases"])
        ]
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "Ask the user for the complete error message text; the partial "
            "input matches multiple routing entries."
        )
        return (0, result)

    # Ladder 2: tool catalog.
    tool_type, tool_key = match_tool(tool)
    if tool_type in ("exact", "fuzzy"):
        result["match"] = {"type": "tool", "tool": tool_key,
                           "match_kind": tool_type}
        result["diagnosis"] = build_tool_block(tool_key)
        if sc:
            result["retrieval_judgment"] = build_retrieval_block(sc)
        # Attach symptom-specific blocks that the tool branch must not hide
        # (whitelist requests and format complaints arrive together with a tool).
        attached_route = match_symptom_route(symptom)
        if attached_route == "whitelist":
            result["whitelist_guidance"] = dict(WHITELIST_GUIDANCE)
        elif attached_route == "format_unreadable":
            result["format_note"] = dict(FORMAT_NOTE)
        status = "OK" if tool_type == "exact" else "DEGRADED"
        result["status"] = status
        result["next_action"] = (
            "Report the tool checklist and known issues for {key} verbatim; "
            "if a retrieval judgment is attached, attribute the fee per it; "
            "provide advice only, never execute configuration changes."
        ).format(key=tool_key)
        return (0, result)
    if tool and tool_type == "none":
        result["tool_warning"] = (
            "Unknown backup tool '{0}'. Known profiles: veeam, synology, "
            "generic (rclone / AWS CLI-SDK / s3cmd / ...). Continuing with "
            "symptom-based routing.".format(normalize_text(tool))
        )

    # Ladder 3: symptom routing.
    route_id = match_symptom_route(symptom)
    if route_id == "retrieval_fee":
        if sc:
            result["match"] = {"type": "symptom", "route": "retrieval_fee"}
            result["diagnosis"] = build_retrieval_block(sc)
            result["status"] = "OK"
            result["next_action"] = (
                "Attribute the retrieval/minimum-duration fee per the "
                "judgment block for storage class {cls} verbatim; recommend "
                "the listed mitigations; do not modify storage classes or "
                "lifecycle rules yourself."
            ).format(cls=sc)
            return (0, result)
        result["match"] = {"type": "symptom", "route": "retrieval_fee"}
        result["candidates"] = sorted(RETRIEVAL_RULES.keys())
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "Ask the user for the storage class of the billed objects "
            "(standard / ia / archive / coldarchive / deepcoldarchive, or "
            "the billing line-item name) before attributing the retrieval "
            "fee."
        )
        return (0, result)
    if route_id == "whitelist":
        result["match"] = {"type": "symptom", "route": "whitelist"}
        result["diagnosis"] = dict(WHITELIST_GUIDANCE)
        result["status"] = "OK"
        result["next_action"] = (
            "Report the whitelist provisioning guidance verbatim (support "
            "ticket with UID, bucket, region, tool version); never claim the "
            "whitelist has been opened."
        )
        return (0, result)
    if route_id == "path_style":
        result["match"] = {"type": "symptom", "route": "path_style"}
        result["diagnosis"] = build_route_block("PathStyleRejected")
        result["status"] = "OK"
        result["next_action"] = (
            "Report the virtual-hosted style configuration advice verbatim."
        )
        return (0, result)
    if route_id == "v1_forbidden":
        result["match"] = {"type": "symptom", "route": "v1_forbidden"}
        result["diagnosis"] = build_route_block("V1SignatureRejected")
        result["status"] = "OK"
        result["next_action"] = (
            "Report the V1->V4 adaptation advice verbatim, including the "
            "minimum V4-capable tool versions and the region requirement."
        )
        return (0, result)
    if route_id == "format_unreadable":
        result["match"] = {"type": "symptom", "route": "format_unreadable"}
        result["diagnosis"] = dict(FORMAT_NOTE)
        result["status"] = "OK"
        result["next_action"] = (
            "Report the proprietary-format note verbatim: restore through "
            "the backup software console, not by direct download."
        )
        return (0, result)

    # Ladder 4: storage class only.
    if sc:
        result["match"] = {"type": "storage_class_only", "storage_class": sc}
        result["diagnosis"] = build_retrieval_block(sc)
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "Present the retrieval-fee profile of storage class {cls} and "
            "ask which symptom applies (unexpected fee, restore behavior, "
            "backup job failure) before concluding."
        ).format(cls=sc)
        return (0, result)

    # Ladder 5: nothing recognizable.
    result["match"] = {"type": "none", "route": None}
    result["status"] = "FAIL"
    result["next_action"] = (
        "No recognizable tool, error message, symptom or storage class was "
        "provided. Ask the user for: the backup tool name/version, the exact "
        "error message, the symptom (connection failure / retrieval fee / "
        "whitelist), and the bucket storage class; consult "
        "references/integration-playbook.md."
    )
    return (1, result)


# --- Inline boundary assertions (normal / boundary / invalid) ---------------
# Executed on every run before main; a failure here means the catalog or the
# matching ladder is broken and the script must not emit a diagnosis.

# normal: exact tool / error / storage-class hits
assert match_tool("Veeam") == ("exact", "veeam")
assert match_tool("群晖") == ("exact", "synology")
assert match_tool("rclone") == ("exact", "generic")
assert match_tool("our rclone sync job") == ("fuzzy", "generic")
assert match_error_route("V1 signature is forbidden") == ("exact", "V1SignatureRejected")
assert match_error_route("path-style requests rejected") == ("fuzzy", "PathStyleRejected")
assert resolve_storage_class("低频") == "ia"
assert resolve_storage_class("ColdArchive") == "coldarchive"
assert resolve_storage_class("DEEP COLD ARCHIVE") == "deepcoldarchive"
assert resolve_storage_class("California") == ""  # boundary: substring 'ia' inside an unrelated word must not fuzzy-match
assert resolve_storage_class("ia") == "ia"  # boundary: short alias still exact-matches

# boundary: symptom routing combinations
assert match_symptom_route("账单里出现很高的取回费") == "retrieval_fee"
assert match_symptom_route("please help add the bucket to whitelist") == "whitelist"
assert match_symptom_route("client uses path style urls") == "path_style"
assert match_symptom_route("报错 v1 signature forbidden") == "v1_forbidden"
assert match_symptom_route("下载下来的备份文件格式无法识别") == "format_unreadable"
_r_ok_exit, _r_ok = diagnose(symptom="high retrieval fee from backup", storage_class="ia")
assert _r_ok_exit == 0 and _r_ok["status"] == "OK"
assert _r_ok["diagnosis"]["storage_class"] == "ia"
_r_deg_exit, _r_deg = diagnose(symptom="unexpected retrieval fee")
assert _r_deg_exit == 0 and _r_deg["status"] == "DEGRADED"
assert sorted(_r_deg["candidates"]) == sorted(RETRIEVAL_RULES.keys())

# invalid: unknown inputs / empty / None
assert match_tool("NoSuchToolXyz") == ("none", None)
assert match_tool("") == ("none", None)
assert match_tool(None) == ("none", None)
assert match_error_route("NoSuchErrorXyz") == ("none", None)
assert match_symptom_route("") is None
assert match_symptom_route(None) is None
assert resolve_storage_class("platinum-tier") == ""
fail_exit, fail_result = diagnose()
assert fail_exit == 1 and fail_result["status"] == "FAIL"
assert fail_result["match"]["type"] == "none"
_unk_exit, _unk_result = diagnose(tool="acme-backup-3000")
assert _unk_exit == 1 and _unk_result["status"] == "FAIL"
assert "tool_warning" in _unk_result
# storage class only -> degraded profile, never a conclusion
_sc_exit, _sc_result = diagnose(storage_class="archive")
assert _sc_exit == 0 and _sc_result["status"] == "DEGRADED"
assert _sc_result["match"]["type"] == "storage_class_only"
# tool + storage class combination attaches retrieval judgment
_combo_exit, _combo = diagnose(tool="veeam", storage_class="低频")
assert _combo_exit == 0 and _combo["status"] == "OK"
assert _combo["retrieval_judgment"]["storage_class"] == "ia"
# tool + whitelist symptom attaches the whitelist guidance block
_wl_exit, _wl = diagnose(tool="veeam", symptom="请帮我加白", bucket="b", region="cn-shanghai")
assert _wl_exit == 0 and _wl["status"] == "OK"
assert "whitelist_guidance" in _wl and _wl["match"]["type"] == "tool"
# error route + tool context
_route_exit, _route = diagnose(error_code="V1 signature is forbidden", tool="veeam")
assert _route_exit == 0 and _route["status"] == "OK"
assert _route["match"]["type"] == "error_route"
assert _route["tool_context"]["tool"] == "veeam"
assert len(TOOL_CATALOG) == 3 and len(ERROR_ROUTES) == 5
assert len(RETRIEVAL_RULES) == 5


# --- Official-doc verification hook (runtime doc lookup, batch-3) -----------

_CUSTOMER_QUESTION = ""


def _doc_verification(status: str):
    """Step B: verify the customer's original wording against official OSS
    docs. Skipped when --question is absent (no-arg regression unchanged)
    or when Step A already answered (status OK) a non-consultation error
    question. Returns the constant four-key dict from _doc_lookup; never
    raises and never blocks the main diagnosis."""
    q = _CUSTOMER_QUESTION.strip()
    if not q:
        return None
    if status == "OK" and not _doc_lookup.is_consult_question(q):
        return None  # Step A hit on a pure error question
    return _doc_lookup.lookup_config_topic(q)


assert _doc_verification("OK") is None  # invalid: no --question -> unchanged
_CUSTOMER_QUESTION = "InvalidObjectState error, rule not effective"
assert _doc_verification("OK") is None  # normal: Step A hit, non-consultation
_CUSTOMER_QUESTION = "how to configure it?"
assert _doc_lookup.is_consult_question(_CUSTOMER_QUESTION) is True  # signal
_CUSTOMER_QUESTION = ""


def degrade_warn_line(status: str, match_type: str) -> str:
    """Build the stderr [WARN] trace line for DEGRADED/FAIL outcomes.

    Keeps the knowledge-driven skill aligned with the cloud-link skills:
    a non-OK conclusion must leave an observable [WARN] trace on stderr
    while the stdout JSON/contract lines stay machine-parseable.
    """
    return "[WARN] {0} degraded: {1}".format(
        SKILL_NAME, match_type or status.lower())


assert degrade_warn_line("DEGRADED", "symptom_only").startswith("[WARN]")
assert "alibabacloud-oss-backup-integration-diagnosis" in degrade_warn_line(
    "DEGRADED", "symptom_only")
assert degrade_warn_line("FAIL", "").endswith("fail")  # boundary: empty match type falls back to the status word


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Knowledge-driven OSS backup-tool integration diagnosis "
                    "(zero cloud API calls)."
    )
    parser.add_argument("--tool", dest="tool", default=None,
                        help="backup tool: veeam, synology, generic (rclone/AWS CLI/SDK/...)")
    parser.add_argument("--error-code", dest="error_code", default=None,
                        help="exact error message from the tool, e.g. 'V1 signature is forbidden'")
    parser.add_argument("--symptom", dest="symptom", default=None,
                        help="free-form symptom, e.g. 'high retrieval fee', '加白', 'path style'")
    parser.add_argument("--storage-class", dest="storage_class", default=None,
                        help="standard, ia, archive, coldarchive or deepcoldarchive")
    parser.add_argument("--bucket", dest="bucket", default=None,
                        help="Bucket name for context (not validated remotely)")
    parser.add_argument("--region", dest="region", default=None,
                        help="Bucket region for context, e.g. cn-hangzhou")
    parser.add_argument("--question", dest="question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    args = parser.parse_args(argv)
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    exit_code, result = diagnose(
        tool=args.tool,
        error_code=args.error_code,
        symptom=args.symptom,
        storage_class=args.storage_class,
        bucket=args.bucket,
        region=args.region,
    )
    dv = _doc_verification(result["status"])
    if dv is not None:
        result["doc_verification"] = dv
    if result["status"] in ("DEGRADED", "FAIL"):
        print(degrade_warn_line(result["status"],
                                (result.get("match") or {}).get("type") or ""),
              file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("STATUS: {0}".format(result["status"]))
    print("NEXT_ACTION: {0}".format(result["next_action"]))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
