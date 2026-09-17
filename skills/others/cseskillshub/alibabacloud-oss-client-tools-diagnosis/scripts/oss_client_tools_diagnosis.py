#!/usr/bin/env python3
# SECURITY: knowledge-driven diagnosis only. This script performs NO network
# calls, invokes NO aliyun CLI, calls NO cloud API, and NEVER executes any
# ossutil/ossbrowser command. It maps a user-supplied client-tool error or
# symptom to root-cause directions using the embedded catalog, then emits
# structured JSON plus STATUS/NEXT_ACTION.
"""Entry script for alibabacloud-oss-client-tools-diagnosis.

Usage (all parameters optional):
  python3 oss_client_tools_diagnosis.py \
      [--tool ossbrowser|ossutil] [--error-code CODE] [--ec-code EC] \
      [--symptom TEXT] [--endpoint URL] [--client-version VER]

Matching ladder (pure functions, unit-testable):
  1. exact alias lookup in the catalog (case-insensitive) -> STATUS: OK
  2. fuzzy substring match / symptom scoring                -> STATUS: DEGRADED
  3. tool-only input: candidate list for that tool          -> STATUS: DEGRADED
  4. nothing recognizable                                   -> STATUS: FAIL (exit 1)
"""

import re
import argparse
import json
import sys
import uuid

import _doc_lookup

from _tools_catalog import (
    ALIAS_TO_KEY,
    CATEGORY_LABELS,
    LEAST_PRIVILEGE_POLICY_TEMPLATE,
    OSSUTIL_CONFIG_TEMPLATE,
    TOOL_ALIASES,
    TOOL_LABELS,
    TOOLS_CATALOG,
)

SKILL_NAME = "alibabacloud-oss-client-tools-diagnosis"

# --- Observability: session id + User-Agent template ------------------------
# Even though this skill makes zero cloud API calls, the session id and the
# User-Agent string are generated here so any future HTTP usage is traceable.
SESSION_ID = uuid.uuid4().hex  # 32-char lowercase hex
SKILL_VERSION = "1.0.0"  # UA skill-version; matches references/manifest.json
USER_AGENT = "AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{version}".format(
    skill=SKILL_NAME, session_id=SESSION_ID, version=SKILL_VERSION
)

ALIAS_KEYS = sorted(ALIAS_TO_KEY.keys())


# --- Pure matching functions (no I/O, no side effects) ----------------------

def normalize_text(value):
    """Return stripped string, or '' for None/non-str input."""
    if not isinstance(value, str):
        return ""
    return value.strip()


def normalize_tool(raw_tool):
    """Normalize a tool-name variant to 'ossbrowser'/'ossutil'/''.

    Handles case, spacing and common ticket typos ('osstuil', 'ossutil64',
    'oss-browser2', 'ob2'). Empty/unknown input yields ''.
    """
    tool = normalize_text(raw_tool).lower()
    if not tool:
        return ""
    if tool in TOOL_ALIASES:
        return TOOL_ALIASES[tool]
    if "browser" in tool:
        return "ossbrowser"
    if "util" in tool:
        return "ossutil"
    return ""


def tool_compatible(entry_tool, tool):
    """True when the catalog entry applies to the requested tool."""
    if not tool:
        return True
    return entry_tool in ("any", tool)


def match_error_code(raw_code, tool=""):
    """Match a raw error-code/EC-code string against the catalog aliases.

    Returns (match_type, keys):
      ("exact",    [key...])  case-insensitive exact alias hit(s)
      ("fuzzy",    [key...])  substring hits against aliases
      ("none",     [])        no hit / empty input
    """
    code = normalize_text(raw_code)
    if not code:
        return ("none", [])
    lowered = code.lower()
    if lowered in ALIAS_TO_KEY:
        return ("exact", [ALIAS_TO_KEY[lowered]])
    fuzzy_hits = []
    for alias in ALIAS_KEYS:
        if alias in lowered or lowered in alias:
            key = ALIAS_TO_KEY[alias]
            if key not in fuzzy_hits:
                fuzzy_hits.append(key)
    return ("fuzzy", fuzzy_hits) if fuzzy_hits else ("none", [])


def score_symptom(raw_symptom, tool=""):
    """Score catalog entries against a free-text symptom description.

    Returns a list of (score, key) sorted by score desc, score > 0 only.
    """
    text = normalize_text(raw_symptom).lower()
    if not text:
        return []
    scored = []
    for key, entry in TOOLS_CATALOG.items():
        if not tool_compatible(entry["tool"], tool):
            continue
        score = sum(1 for pat in entry["symptom_patterns"] if pat in text)
        if score > 0:
            scored.append((score, key))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored


def candidates_for_tool(tool):
    """Common-issue candidate keys for a tool (used when only tool known)."""
    return [key for key, entry in TOOLS_CATALOG.items()
            if tool_compatible(entry["tool"], tool)]


def build_diagnosis(key):
    """Build the diagnosis block for one canonical catalog entry (pure)."""
    entry = TOOLS_CATALOG[key]
    block = {
        "key": key,
        "tool": entry["tool"],
        "tool_label": TOOL_LABELS[entry["tool"]],
        "category": entry["category"],
        "category_label": CATEGORY_LABELS[entry["category"]],
        "root_cause_directions": list(entry["root_cause_directions"]),
        "troubleshooting_steps": list(entry["troubleshooting_steps"]),
        "official_doc_ref": entry["official_doc_ref"],
    }
    if "ec_decision_table" in entry:
        block["ec_decision_table"] = dict(entry["ec_decision_table"])
    if entry.get("config_template"):
        block["ossutil_config_template"] = OSSUTIL_CONFIG_TEMPLATE
    if entry.get("least_privilege_template"):
        block["least_privilege_policy_template"] = LEAST_PRIVILEGE_POLICY_TEMPLATE
    return block


def summarize(keys):
    """Compact summaries for candidate lists."""
    return [
        {
            "key": k,
            "tool": TOOLS_CATALOG[k]["tool"],
            "category": TOOLS_CATALOG[k]["category"],
            "category_label": CATEGORY_LABELS[TOOLS_CATALOG[k]["category"]],
        }
        for k in keys
    ]


def diagnose(tool=None, error_code=None, ec_code=None, symptom=None,
             endpoint=None, client_version=None):
    """Pure decision function. Returns (exit_code, result_dict)."""
    norm_tool = normalize_tool(tool)
    result = {
        "skill": SKILL_NAME,
        "session_id": SESSION_ID,
        "user_agent": USER_AGENT,
        "inputs": {
            "tool": norm_tool,
            "error_code": normalize_text(error_code),
            "ec_code": normalize_text(ec_code),
            "symptom": normalize_text(symptom),
            "endpoint": normalize_text(endpoint),
            "client_version": normalize_text(client_version),
        },
        "references": [
            "references/tool-troubleshooting.md",
            "references/config-templates.md",
            "references/scope-and-limitations.md",
        ],
    }

    # Rung 1: exact alias hit (error code or EC code).
    for source in (error_code, ec_code):
        match_type, keys = match_error_code(source, norm_tool)
        if match_type == "exact":
            compatible = [k for k in keys
                          if tool_compatible(TOOLS_CATALOG[k]["tool"], norm_tool)]
            if len(compatible) == 1:
                key = compatible[0]
                result["match"] = {"type": "exact", "key": key}
                result["diagnosis"] = build_diagnosis(key)
                ec = normalize_text(ec_code)
                table = TOOLS_CATALOG[key].get("ec_decision_table")
                if ec and table and ec in table:
                    result["diagnosis"]["ec_interpretation"] = table[ec]
                result["status"] = "OK"
                result["next_action"] = (
                    "Report the root-cause directions and troubleshooting "
                    "steps for {key} verbatim from the diagnosis block; "
                    "follow references/tool-troubleshooting.md for the "
                    "{cat} track."
                ).format(key=key, cat=TOOLS_CATALOG[key]["category"])
                return (0, result)

    # Rung 2: symptom scoring.
    scored = score_symptom(symptom, norm_tool)
    if scored:
        top = scored[0][0]
        winners = [k for s, k in scored if s == top]
        if len(winners) == 1 and top >= 1:
            key = winners[0]
            result["match"] = {"type": "symptom", "key": key}
            result["diagnosis"] = build_diagnosis(key)
            ec = normalize_text(ec_code)
            table = TOOLS_CATALOG[key].get("ec_decision_table")
            if ec and table and ec in table:
                result["diagnosis"]["ec_interpretation"] = table[ec]
            result["status"] = "OK"
            result["next_action"] = (
                "Report the root-cause directions and troubleshooting steps "
                "for {key} verbatim from the diagnosis block; the match was "
                "symptom-based, so quote the user's symptom back when "
                "answering."
            ).format(key=key)
            return (0, result)
        result["match"] = {"type": "symptom_ambiguous", "key": None}
        result["candidates"] = winners
        result["candidate_summaries"] = summarize(winners)
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "Ask the user for the exact error text from the tool (ossbrowser "
            "dialog / ossutil stderr, including the EC code if present) to "
            "pick one candidate; present the candidate list until then."
        )
        return (0, result)

    # Rung 2b: fuzzy alias match when no symptom matched.
    for source in (error_code, ec_code):
        match_type, keys = match_error_code(source, norm_tool)
        if match_type == "fuzzy" and keys:
            compatible = [k for k in keys
                          if tool_compatible(TOOLS_CATALOG[k]["tool"], norm_tool)]
            picks = compatible if compatible else keys
            if len(picks) == 1:
                key = picks[0]
                result["match"] = {"type": "fuzzy", "key": key}
                result["diagnosis"] = build_diagnosis(key)
                result["status"] = "DEGRADED"
                result["next_action"] = (
                    "The error text only fuzzily matches {key}; present the "
                    "diagnosis but ask the user to confirm the exact error "
                    "message before concluding."
                ).format(key=key)
                return (0, result)
            result["match"] = {"type": "fuzzy_ambiguous", "key": None}
            result["candidates"] = picks
            result["candidate_summaries"] = summarize(picks)
            result["status"] = "DEGRADED"
            result["next_action"] = (
                "Ask the user to paste the complete error message from the "
                "tool; the partial text matches multiple catalog entries."
            )
            return (0, result)

    # Rung 3: tool-only input -> degraded candidate list for that tool.
    if norm_tool:
        result["match"] = {"type": "tool_only", "key": None}
        result["candidates"] = candidates_for_tool(norm_tool)
        result["candidate_summaries"] = summarize(result["candidates"])
        result["status"] = "DEGRADED"
        result["next_action"] = (
            "Only the tool name is known. Ask the user for the exact error "
            "message or symptom; present the common {tool} issue list above "
            "as orientation only."
        ).format(tool=norm_tool)
        return (0, result)

    # Rung 4: nothing recognizable.
    result["match"] = {"type": "none", "key": None}
    result["status"] = "FAIL"
    result["next_action"] = (
        "No recognizable tool, error code or symptom was provided. Ask the "
        "user which tool is used (ossbrowser or ossutil, with version) and "
        "for the complete error message (including any EC code) before "
        "diagnosing; consult references/tool-troubleshooting.md."
    )
    return (1, result)


# --- Inline boundary assertions (normal / boundary / invalid) ---------------
# Executed on every run before main; a failure here means the catalog or the
# matching ladder is broken and the script must not emit a diagnosis.

# normal: tool-name variants
assert normalize_tool("OSSBrowser") == "ossbrowser"
assert normalize_tool("oss-browser2") == "ossbrowser"
assert normalize_tool("ob2") == "ossbrowser"
assert normalize_tool("ossutil64") == "ossutil"
assert normalize_tool("osstuil") == "ossutil"  # ticket typo
assert normalize_tool("ossutil 2.x") == "ossutil"
assert normalize_tool("  OssUtil ") == "ossutil"

# boundary: exact alias hits (canonical + case variants + EC codes)
assert match_error_code("InvalidAccessKeyId") == ("exact", ["ossutil-invalidaccesskeyid"])
assert match_error_code("invalidaccesskeyid") == ("exact", ["ossutil-invalidaccesskeyid"])
assert match_error_code("RequestTimeTooSkewed") == ("exact", ["clock-skew-requesttimetooskewed"])
assert match_error_code("0003-00000101") == ("exact", ["ossutil-accessdenied-ec"])
assert match_error_code("The Security Token may be lost") == ("exact", ["ossutil-invalidaccesskeyid"])

# boundary: symptom scoring with tool filter
_scored = score_symptom("ossbrowser 2.0 login failed, says the bucket does not belong to me", "ossbrowser")
assert _scored[0][1] == "ossbrowser-login-getbucketinfo"
_scored = score_symptom("login failed, you are forbidden to list buckets", "ossbrowser")
assert _scored[0][1] == "ossbrowser-login-listbuckets-denied"
_scored = score_symptom("cannot connect to OSS at all, proxy enabled", "")
assert _scored and _scored[0][0] >= 2

# invalid: unknown / empty / None inputs
assert match_error_code("NoSuchCodeXyz") == ("none", [])
assert match_error_code("") == ("none", [])
assert match_error_code(None) == ("none", [])
assert normalize_tool(None) == ""
assert normalize_tool("terraform") == ""
assert score_symptom("", "ossutil") == []

# ladder: OK / DEGRADED / FAIL end-to-end
_ok_exit, _ok_result = diagnose(tool="ossutil", error_code="InvalidAccessKeyId")
assert _ok_exit == 0 and _ok_result["status"] == "OK"
assert _ok_result["diagnosis"]["key"] == "ossutil-invalidaccesskeyid"
assert "ossutil_config_template" in _ok_result["diagnosis"]
_ok2_exit, _ok2_result = diagnose(tool="ossbrowser",
                                  error_code="AccessDenied",
                                  symptom="login failed, The bucket you access does not belong to you")
assert _ok2_exit == 0 and _ok2_result["status"] == "OK"
assert _ok2_result["diagnosis"]["key"] == "ossbrowser-login-getbucketinfo"
_ec_exit, _ec_result = diagnose(tool="ossutil", error_code="AccessDenied",
                                ec_code="0003-00000301")
assert _ec_exit == 0 and _ec_result["status"] == "OK"
assert "ec_interpretation" in _ec_result["diagnosis"]
_deg_exit, _deg_result = diagnose(tool="ossbrowser")
assert _deg_exit == 0 and _deg_result["status"] == "DEGRADED"
assert _deg_result["match"]["type"] == "tool_only"
assert len(_deg_result["candidates"]) >= 5
_fail_exit, _fail_result = diagnose()
assert _fail_exit == 1 and _fail_result["status"] == "FAIL"
_fail2_exit, _fail2_result = diagnose(error_code="NoSuchCodeXyz")
assert _fail2_exit == 1 and _fail2_result["status"] == "FAIL"
assert len(TOOLS_CATALOG) == 13 and len(ALIAS_TO_KEY) >= 13


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
    """[WARN] trace line emitted on stderr when the knowledge diagnosis
    cannot reach a full conclusion.

    F-3 fix: aligns the zero-cloud knowledge skills with the cloud-chain
    skills' dual-channel degradation trace (stdout JSON status + stderr
    [WARN]). Returns the formatted line; never raises.
    """
    return "[WARN] {0} degraded: {1}".format(
        SKILL_NAME, match_type or status.lower())


assert degrade_warn_line("DEGRADED", "tool_only") == "[WARN] " + SKILL_NAME + " degraded: tool_only"  # normal
assert degrade_warn_line("FAIL", "none").endswith("degraded: none")  # boundary: FAIL path
assert degrade_warn_line("FAIL", "") == "[WARN] " + SKILL_NAME + " degraded: fail"  # invalid: missing match type falls back to status


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Knowledge-driven OSS client-tool diagnosis "
                    "(ossbrowser/ossutil; zero cloud API calls)."
    )
    parser.add_argument("--tool", dest="tool", default=None,
                        help="Client tool: ossbrowser or ossutil (variants OK)")
    parser.add_argument("--error-code", dest="error_code", default=None,
                        help="Error text from the tool (fuzzy OK), e.g. AccessDenied")
    parser.add_argument("--ec-code", dest="ec_code", default=None,
                        help="EC code from the error body, e.g. 0003-00000101")
    parser.add_argument("--symptom", dest="symptom", default=None,
                        help="Free-text symptom, e.g. 'login failed'")
    parser.add_argument("--endpoint", dest="endpoint", default=None,
                        help="Endpoint in use, echoed for region-mismatch context")
    parser.add_argument("--client-version", dest="client_version", default=None,
                        help="Tool version, e.g. ossbrowser 2.1.1 / ossutil 2.x")
    parser.add_argument("--question", dest="question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    args = parser.parse_args(argv)
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    # Symptom-only routing: customers describe failures in their own words and
    # rarely pass a structured EC or tool name. When nothing structured was
    # given, drive the catalog from --question so a symptom-only request still
    # reaches a conclusion instead of "nothing recognizable".
    if args.question and not (args.tool or args.error_code or args.ec_code
                              or args.symptom):
        _m_ec = re.search(r"\b\d{4}-\d{6,8}\b", args.question)
        if _m_ec:
            args.ec_code = _m_ec.group(0)
        _m_tool = normalize_tool(args.question)
        if _m_tool:
            args.tool = _m_tool
        args.symptom = args.question

    exit_code, result = diagnose(
        tool=args.tool,
        error_code=args.error_code,
        ec_code=args.ec_code,
        symptom=args.symptom,
        endpoint=args.endpoint,
        client_version=args.client_version,
    )
    dv = _doc_verification(result["status"])
    if dv is not None:
        result["doc_verification"] = dv
    if result["status"] in ("DEGRADED", "FAIL"):
        # F-3: stderr [WARN] trace for degraded/failed knowledge runs.
        print(degrade_warn_line(result["status"],
                                (result.get("match") or {}).get("type") or ""),
              file=sys.stderr)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("STATUS: {0}".format(result["status"]))
    print("NEXT_ACTION: {0}".format(result["next_action"]))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
