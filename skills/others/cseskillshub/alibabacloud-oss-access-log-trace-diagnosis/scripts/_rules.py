#!/usr/bin/env python3
"""
_rules.py -- EC knowledge resolution and the rule dispatch table
================================================================
SECURITY: READ-ONLY. This module performs no I/O against any cloud service: it
is pure logic over evidence that other modules already collected. It never
reads, prints or stores credentials.

This is the façade of the rule layer. The rules themselves live in the modules
below, one concern per module, so that no single file grows past the size the
sibling skills keep themselves to:

  * _policy_hit.py      statement matching, CIDR, principal and condition
                        evaluation, cross-account and naming derivations
  * _rule_common.py     the logged-attribute view, verdict C, ticket package
  * _rules_authz.py     policy / ACL / RAM denial rules
  * _rules_resource.py  bucket and object existence, naming, serving rules
  * _rules_signature.py signature, clock skew, form upload, write contention

What stays here: EC knowledge resolution, the diagnosis-kind dispatch table and
the inline boundary assertions covering all of the above.

The honesty contract: every rule returns a verdict class (A provable / B
narrowed / C escalate) and downgrades itself when the evidence it depends on is
missing, rather than asserting a cause.

Self-test:
  python3 _rules.py --self-test
"""

from __future__ import annotations

import json

from _constants import (
    ESCALATION_ERROR_CODES,
    ESCALATION_STATUS_FLOOR,
    MIRROR_RULES_NOT_EXPOSED,
    VERDICT_ESCALATE,
    VERDICT_NEEDS_CONFIRMATION,
    VERDICT_SELF_DIAGNOSABLE,
)
from _ec_knowledge import EC_KNOWLEDGE
from _policy_hit import (  # noqa: F401  (re-exported; exercised by _self_test)
    OPERATION_TO_ACTION,
    _action_matches,
    _evaluate_condition_block,
    _ip_in_cidr_list,
    _principal_matches,
    _resource_matches,
    _wildcard_match,
    analyze_policy_hit,
    decode_post_policy,
    determine_account_relation,
    validate_bucket_name_from_host,
)
from _rule_common import (  # noqa: F401  (re-exported; used by the entry script)
    SKILL_NAME,
    _request_attributes,
    build_escalation_package,
    rule_escalate,
)
from _rules_authz import (  # noqa: F401
    _policy_grammar_warnings,
    _render_hit_explanation,
    _render_implicit_deny,
    rule_anonymous_denied,
    rule_object_read_denied,
    rule_policy_hit_analysis,
    rule_ram_deny_scan,
)
from _rules_resource import (  # noqa: F401
    rule_bucket_existence,
    rule_bucket_name_validation,
    rule_forced_download,
    rule_image_source_validation,
    rule_knowledge_rule,
    rule_object_existence,
)
from _rules_signature import (  # noqa: F401
    rule_clock_skew,
    rule_concurrent_write_scan,
    rule_post_policy_expiry,
    rule_signature_mismatch,
)


# ---------------------------------------------------------------------------
# EC resolution
# ---------------------------------------------------------------------------

def lookup_knowledge(ec: str, error_code: str, http_status: str) -> dict:
    """Find the knowledge entry for an EC code, with documented fallbacks.

    Order of resolution:
      1. exact EC code;
      2. an error code listed as always-escalating;
      3. a 5xx status with no explaining code;
      4. no match - reported as unknown rather than guessed.
    """
    ec = (ec or "").strip()
    error_code = (error_code or "").strip()
    http_status = (http_status or "").strip()

    if ec and ec in EC_KNOWLEDGE:
        entry = dict(EC_KNOWLEDGE[ec])
        entry["ec"] = ec
        entry["matched_by"] = "ec"
        return entry

    if error_code and error_code in ESCALATION_ERROR_CODES:
        is_mirror = error_code == "MirrorFailed"
        return {
            "ec": ec or "-",
            "error_code": error_code,
            "http_status": http_status or "-",
            "meaning": ESCALATION_ERROR_CODES[error_code],
            "verdict": (VERDICT_NEEDS_CONFIRMATION if is_mirror
                        else VERDICT_ESCALATE),
            "diagnosis": "mirror_failure" if is_mirror else "escalate",
            "evidence_apis": [],
            "log_fields": [],
            # The origin address of a mirror rule is NOT readable through the
            # SDK, so this cause cannot be resolved programmatically.
            "note": MIRROR_RULES_NOT_EXPOSED if is_mirror else "",
            "matched_by": "error_code",
        }

    if http_status.isdigit() and int(http_status) >= ESCALATION_STATUS_FLOOR:
        return {
            "ec": ec or "-", "error_code": error_code or "-",
            "http_status": http_status,
            "meaning": "A server-side failure occurred while handling the request.",
            "verdict": VERDICT_ESCALATE,
            "diagnosis": "escalate",
            "evidence_apis": [], "log_fields": [],
            "note": ("A 5xx status means the service could not fulfil the "
                     "request. Nothing in the customer-side log or "
                     "configuration explains it, so it is escalated rather "
                     "than attributed."),
            "matched_by": "http_status",
        }

    # Search by error code when the EC field was empty in the log.
    for code, entry in EC_KNOWLEDGE.items():
        if error_code and entry.get("error_code") == error_code:
            found = dict(entry)
            found["ec"] = code
            found["matched_by"] = "error_code_to_ec"
            return found

    return {
        "ec": ec or "-", "error_code": error_code or "-",
        "http_status": http_status or "-",
        "meaning": "", "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "unknown", "evidence_apis": [], "log_fields": [],
        "note": "", "matched_by": "none",
    }

def rule_unknown(row: dict, entry: dict, ctx: dict) -> dict:
    """Fallback when the error is not in the knowledge base."""
    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": ("The observed error is not covered by the built-in "
                       "knowledge base, so no root cause is asserted."),
        "root_cause": (
            f"The traced request returned status "
            f"{row.get('http_status', '-')}, error code "
            f"'{row.get('error_code', '-')}' and EC '{row.get('ec', '-')}'. "
            f"This combination is not in the knowledge base of this skill. "
            f"Asserting a cause here would be a guess, so the raw evidence is "
            f"reported instead."),
        "recommendations": [
            "Look up the EC code in the public OSS error-code documentation; "
            "each code has its own page explaining the cause and the fix.",
            "If the EC code is empty, capture the full error response body "
            "from the client, which carries both the error code and the EC.",
            "Open a support ticket with the escalation package below if the "
            "documentation does not resolve it.",
        ],
        "evidence": {"request_attributes": _request_attributes(row),
                     "collected_facts": ctx["facts"]},
    }

RULES = {
    "policy_hit_analysis": rule_policy_hit_analysis,
    "anonymous_denied": rule_anonymous_denied,
    "object_read_denied": rule_object_read_denied,
    "bucket_name_validation": rule_bucket_name_validation,
    "bucket_existence": rule_bucket_existence,
    "object_existence": rule_object_existence,
    "knowledge_rule": rule_knowledge_rule,
    "forced_download": rule_forced_download,
    "signature_mismatch": rule_signature_mismatch,
    "clock_skew": rule_clock_skew,
    "post_policy_expiry": rule_post_policy_expiry,
    "image_source_validation": rule_image_source_validation,
    "concurrent_write_scan": rule_concurrent_write_scan,
    "ram_deny_scan": rule_ram_deny_scan,
    "escalate": rule_escalate,
}
RULES["unknown"] = rule_unknown
RULES["mirror_failure"] = rule_escalate

# ---------------------------------------------------------------------------
# Inline boundary assertions for the pure functions above
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Assert normal / boundary / invalid behaviour of the pure functions.

    No test framework is used, per the development standard: the assertions
    live next to the functions they cover. Run with --self-test.
    """
    # --- bucket name extraction from the host header ---
    ok = validate_bucket_name_from_host("my-valid-bucket.oss-cn-beijing.aliyuncs.com")
    assert ok["extracted_name"] == "my-valid-bucket" and ok["name_valid"], ok
    dotted = validate_bucket_name_from_host("a.com-eu.oss-cn-hangzhou.aliyuncs.com")
    assert not dotted["name_valid"] and dotted["looks_like_domain"], dotted
    assert any("dot" in r for r in dotted["reasons"]), dotted
    # boundary: empty and unparseable hosts must not raise
    assert validate_bucket_name_from_host("")["extracted_name"] == ""
    assert not validate_bucket_name_from_host("not-an-oss-host")["name_valid"]

    # --- CIDR matching ---
    assert _ip_in_cidr_list("10.1.2.3", ["10.0.0.0/8"]) is True
    assert _ip_in_cidr_list("203.0.113.7", ["10.0.0.0/8"]) is False
    assert _ip_in_cidr_list("10.1.2.3", ["10.1.2.3"]) is True          # exact IP
    assert _ip_in_cidr_list("2001:db8::1", ["10.0.0.0/8"]) is False    # family mismatch
    assert _ip_in_cidr_list("not-an-ip", ["10.0.0.0/8"]) is False      # invalid input
    assert _ip_in_cidr_list("10.1.2.3", ["bad-cidr"]) is False         # invalid entry
    assert _ip_in_cidr_list("", []) is False                           # empty

    # --- action / resource coverage ---
    assert _action_matches(["oss:GetObject"], "GetObject") is True
    assert _action_matches(["oss:*"], "GetObject") is True
    assert _action_matches(["oss:ListObjects"], "GetBucket") is True   # alias mapping
    assert _action_matches(["oss:PutObject"], "GetObject") is False
    assert _resource_matches(["acs:oss:*:*:b1"], "b1", "") is True
    assert _resource_matches(["acs:oss:*:*:b1/*"], "b1", "k/o.png") is True
    assert _resource_matches(["acs:oss:*:*:b2"], "b1", "") is False

    # --- principal matching ---
    row_uid = {"requester_id": "1234", "access_id": "LTAI5tEXAMPLE",
               "extend_information": "-"}
    assert _principal_matches(["1234"], row_uid, "")[0] is True
    assert _principal_matches(["*"], row_uid, "")[0] is True
    assert _principal_matches(["9999"], row_uid, "")[0] is False
    row_role = {"requester_id": "-", "access_id": "STS.EXAMPLE",
                "extend_information": "1111,MyRole,sess-abc,2222"}
    assert _principal_matches(
        ["arn:sts::2222:assumed-role/MyRole/*"], row_role, "2222")[0] is True
    # a hardcoded session name must not match a dynamic session
    assert _principal_matches(
        ["arn:sts::2222:assumed-role/MyRole/fixed"], row_role, "2222")[0] is False
    # role/ instead of assumed-role/ never matches
    assert _principal_matches(
        ["arn:sts::2222:role/MyRole"], row_role, "2222")[0] is False

    # --- policy hit analysis: deny hit, deny miss, implicit deny ---
    deny = [{"Effect": "Deny", "Principal": ["*"], "Action": ["oss:GetObject"],
             "Resource": ["*"],
             "Condition": {"StringNotLike": {"acs:SourceVpc": ["vpc-*"]},
                           "NotIpAddress": {"acs:SourceIp": ["10.0.0.0/8"]}}}]
    public_row = {"operation": "GetObject", "object": "a.png",
                  "client_ip": "203.0.113.7", "vpc_id": "-",
                  "access_id": "LTAI5tEXAMPLE", "requester_id": "1234",
                  "extend_information": "-"}
    hit = analyze_policy_hit(deny, public_row, "b1", "1234")
    assert hit["decision"] == "explicit_deny", hit
    assert len(hit["deny_hits"]) == 1
    vpc_row = dict(public_row, vpc_id="vpc-abc", client_ip="10.1.2.3")
    assert analyze_policy_hit(deny, vpc_row, "b1", "1234")["decision"] == "implicit_deny"
    # an Allow covering the request must be reported as explicit_allow
    allow = [{"Effect": "Allow", "Principal": ["*"],
              "Action": ["oss:GetObject"], "Resource": ["acs:oss:*:*:b1/*"]}]
    assert analyze_policy_hit(allow, public_row, "b1", "1234")["decision"] == "explicit_allow"
    # boundary: empty statement list must not raise
    assert analyze_policy_hit([], public_row, "b1", "1234")["decision"] == "implicit_deny"

    # --- wildcard misuse with a non-wildcard operator is flagged ---
    misuse = [{"Effect": "Allow", "Principal": ["*"], "Action": ["oss:GetObject"],
               "Resource": ["*"],
               "Condition": {"StringEquals": {"acs:SourceVpc": ["*"]}}}]
    result = analyze_policy_hit(misuse, public_row, "b1", "1234")
    notes = [c["note"] for c in result["evaluated"][0]["conditions"]]
    assert any("CONFIGURATION BUG" in n for n in notes), notes

    # --- unsupported condition keys are refused, not invented ---
    bad_key = [{"Effect": "Deny", "Principal": ["*"], "Action": ["oss:GetObject"],
                "Resource": ["*"],
                "Condition": {"StringNotLike": {"acs:Referer": ["*.example.com"]}}}]
    result = analyze_policy_hit(bad_key, public_row, "b1", "1234")
    notes = [c["note"] for c in result["evaluated"][0]["conditions"]]
    assert any("UNSUPPORTED CONDITION KEY" in n for n in notes), notes

    # --- cross-account determination ---
    same = determine_account_relation(row_role, "2222")
    assert same["cross_account"] is False and same["role_owner_id"] == "2222", same
    cross = determine_account_relation(row_role, "3333")
    assert cross["cross_account"] is True, cross
    anon = determine_account_relation(
        {"requester_id": "-", "access_id": "-", "extend_information": "-"}, "2222")
    assert anon["cross_account"] is None, anon

    # --- EC knowledge resolution and its fallbacks ---
    assert lookup_knowledge("0003-00000101", "", "")["diagnosis"] == "policy_hit_analysis"
    assert lookup_knowledge("0003-00000101", "", "")["verdict"] == VERDICT_SELF_DIAGNOSABLE
    assert lookup_knowledge("0002-00000040", "", "")["verdict"] == VERDICT_NEEDS_CONFIRMATION
    assert lookup_knowledge("", "InternalError", "500")["verdict"] == VERDICT_ESCALATE
    assert lookup_knowledge("", "", "503")["verdict"] == VERDICT_ESCALATE
    unknown = lookup_knowledge("9999-99999999", "Weird", "418")
    assert unknown["matched_by"] == "none" and unknown["diagnosis"] == "unknown"
    # boundary: all-empty input must not raise and must not assert a cause
    assert lookup_knowledge("", "", "")["diagnosis"] == "unknown"
    # error_code -> ec fallback when the log row carried no ec field
    assert lookup_knowledge("", "NoSuchBucketPolicy", "404")["ec"] == "0030-00000006"

    # --- form-upload policy decoding ---
    import base64 as _b64
    doc = {"expiration": "2020-01-01T00:00:00.000Z", "conditions": [{"bucket": "b"}]}
    decoded = decode_post_policy(_b64.b64encode(json.dumps(doc).encode()).decode())
    assert decoded["decoded"] is True and decoded["expiration_is_utc"] is True
    assert decoded["expired_relative_to_now"] is True
    assert decode_post_policy("")["decoded"] is False                 # empty
    assert decode_post_policy("!!!not-base64!!!")["decoded"] is False  # invalid
    future = {"expiration": "2999-01-01T00:00:00.000Z"}
    assert decode_post_policy(
        _b64.b64encode(json.dumps(future).encode()).decode()
    )["expired_relative_to_now"] is False

    # --- rules must degrade instead of raising when evidence is missing ---
    empty_ctx = {"bucket": "b1", "region": "cn-hangzhou", "owner_id": "",
                 "facts": {}, "evidence": {"bucket_policy": {}, "ram": {},
                                           "conditional": {}, "bucket_info": {}},
                 "account_relation": {}, "object_history": [],
                 "concurrent_writes": [], "post_policy": {}, "mime_hint": "",
                 "verified": [], "unverifiable": []}
    for kind in ("policy_hit_analysis", "anonymous_denied", "object_read_denied",
                 "bucket_name_validation", "bucket_existence", "object_existence",
                 "knowledge_rule", "forced_download", "signature_mismatch",
                 "clock_skew", "post_policy_expiry", "image_source_validation",
                 "concurrent_write_scan", "ram_deny_scan", "escalate", "unknown"):
        out = RULES[kind]({}, {"ec": "", "meaning": "", "note": ""}, empty_ctx)
        assert out.get("verdict") in (VERDICT_SELF_DIAGNOSABLE,
                                      VERDICT_NEEDS_CONFIRMATION,
                                      VERDICT_ESCALATE), (kind, out)
        assert out.get("conclusion"), kind
        assert isinstance(out.get("recommendations"), list), kind

    # --- honesty contract: downgrade the verdict when evidence is missing ---
    # where the bucket name came from decides how strong the claim may be
    assert validate_bucket_name_from_host(
        "a.com-eu.oss-cn-hangzhou.aliyuncs.com")["name_source"] == "host"
    assert validate_bucket_name_from_host("", "b1")["name_source"] == "caller-provided"
    assert validate_bucket_name_from_host("", "")["name_source"] == ""
    # an invalid name that only came from the caller is a hint, not proof
    out = rule_bucket_name_validation({}, {"ec": ""}, empty_ctx)
    assert out["verdict"] == VERDICT_NEEDS_CONFIRMATION, out
    assert "caller" in out["root_cause"], out
    # the same invalid name read from a logged host header IS provable
    out = rule_bucket_name_validation(
        {"host": "a.com-eu.oss-cn-hangzhou.aliyuncs.com"}, {"ec": ""}, empty_ctx)
    assert out["verdict"] == VERDICT_SELF_DIAGNOSABLE, out
    assert out["evidence"]["name_source"] == "host", out
    # no name at all (neither host nor caller) -> nothing may be claimed
    out = rule_bucket_name_validation({}, {"ec": ""}, dict(empty_ctx, bucket=""))
    assert out["verdict"] == VERDICT_NEEDS_CONFIRMATION, out
    assert "could not be extracted" in out["conclusion"], out
    # a valid caller-supplied name must not be reported as invalid
    out = rule_bucket_name_validation({}, {"ec": ""},
                                      dict(empty_ctx, bucket="valid-name"))
    assert out["verdict"] == VERDICT_NEEDS_CONFIRMATION, out
    assert "satisfies the naming rules" in out["conclusion"], out
    # bucket information read failed -> must not claim the bucket is absent
    out = rule_bucket_existence({}, {"ec": ""}, empty_ctx)
    assert out["verdict"] == VERDICT_NEEDS_CONFIRMATION, out
    assert "could not be determined" in out["conclusion"], out
    # no logged row -> must not claim the request succeeded
    out = rule_forced_download({}, {"ec": ""}, empty_ctx)
    assert out["verdict"] == VERDICT_NEEDS_CONFIRMATION, out
    # an undocumented knowledge entry still yields a usable, non-empty answer
    out = rule_knowledge_rule({}, {"ec": "", "meaning": "", "note": ""}, empty_ctx)
    assert out["conclusion"] and out["root_cause"], out
    assert out["verdict"] == VERDICT_NEEDS_CONFIRMATION, out
    # a documented entry keeps the stronger verdict
    out = rule_knowledge_rule({}, {"ec": "0030-00000006", "meaning": "m",
                                  "note": "n"}, empty_ctx)
    assert out["verdict"] == VERDICT_SELF_DIAGNOSABLE, out

    # --- regression: the ticket package must resolve every name it uses -----
    # build_escalation_package once referenced a SKILL_NAME that this module
    # never defined, so EVERY verdict-C run aborted with a NameError. The
    # assertion below is what keeps that class of bug from coming back.
    pkg_ctx = dict(empty_ctx)
    pkg_ctx["owner_id"] = "2222"
    pkg = build_escalation_package(
        {"request_id": "REQ1", "time": "01/Jan/2026:00:00:00 +0800",
         "operation": "GetObject", "http_status": "500",
         "error_code": "InternalError", "ec": "0001-00000000",
         "object": "a.png", "client_ip": "203.0.113.7",
         "host": "b1.oss-cn-hangzhou.aliyuncs.com", "sign_type": "-"},
        pkg_ctx, {"conclusion": "server-side failure"})
    assert pkg["skill"] == SKILL_NAME, pkg
    assert pkg["bucket"] == "b1" and pkg["owner_uid"] == "2222", pkg
    assert pkg["request_id"] == "REQ1" and pkg["error_code"] == "InternalError", pkg
    # boundary: an unresolved owner and an empty row must still produce a package
    edge = build_escalation_package({}, dict(empty_ctx, owner_id=""), {})
    assert edge["owner_uid"] == "(not resolved)", edge
    assert edge["http_status"] == "-", edge
    # the session id is the one shared with the API calls, not a second random one
    assert len(pkg["session_id"]) == 32, pkg
    assert pkg["session_id"] == edge["session_id"], pkg
    # rule_escalate is the verdict-C entry point and must stay class C
    esc = rule_escalate({"http_status": "503"}, {"ec": ""}, empty_ctx)
    assert esc["verdict"] == VERDICT_ESCALATE, esc
    print("rules self-test passed")

if __name__ == "__main__":
    import sys
    if "--self-test" in sys.argv:
        _self_test()
        sys.exit(0)
    print("internal module; run with --self-test", file=sys.stderr)
    sys.exit(2)
