#!/usr/bin/env python3
"""

_rules_authz.py -- Authorization-denial rules (bucket policy, ACL, RAM)
=======================================================================
SECURITY: READ-ONLY. Pure logic over collected evidence; no cloud I/O.

Internal module (prefixed with `_`). Do NOT run directly.

Contents
--------
  * rule_policy_hit_analysis   verdict A: name the statement that denied it
  * _render_hit_explanation    turn a hit into sentences a human can act on
  * _render_implicit_deny      explain "no Allow existed" without inventing one
  * _policy_grammar_warnings   flag policy shapes that cannot work as written
  * rule_anonymous_denied      anonymous access refused by block-public-access
  * rule_object_read_denied    object read refused by an ACL
  * rule_ram_deny_scan         an explicit Deny in an identity policy
"""

from __future__ import annotations

import json
import re

from _constants import (
    POLICY_PRINCIPAL_ANTIPATTERNS,
    VERDICT_ESCALATE,
    VERDICT_NEEDS_CONFIRMATION,
    VERDICT_SELF_DIAGNOSABLE,
)
from _policy_hit import analyze_policy_hit
from _rule_common import _request_attributes


# ---------------------------------------------------------------------------
# Rule implementations, one per diagnosis kind declared in EC_KNOWLEDGE
# ---------------------------------------------------------------------------

def rule_policy_hit_analysis(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A: prove which statement denied the request."""
    policy = ctx["evidence"].get("bucket_policy", {}) or {}
    statements = (policy.get("policy") or {}).get("Statement") or []
    if not statements:
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The denial is reported as a bucket-policy "
                           "rejection, but no policy could be read."),
            "root_cause": ("The policy read either failed or returned no "
                           "document. Without the document the matching "
                           "statement cannot be identified, and guessing one "
                           "would be fabrication."),
            "recommendations": [
                "Re-run collect_config_evidence.py and confirm the policy read "
                "succeeded; check the degradation log for the exact error.",
                "If the read is denied, the credential lacks the bucket policy "
                "read permission; grant it per references/ram-policies.md.",
            ],
            "evidence": {"policy_available": policy.get("available"),
                         "error_code": policy.get("error_code", "")},
        }

    analysis = analyze_policy_hit(statements, row, ctx["bucket"],
                                  ctx["owner_id"])
    decision = analysis["decision"]
    hits = analysis["deny_hits"] or analysis["allow_hits"]

    if decision == "explicit_deny":
        verdict = VERDICT_SELF_DIAGNOSABLE
        conclusion = ("The request matched an explicit Deny statement in the "
                      "bucket policy and was rejected.")
        root_cause = _render_hit_explanation(analysis["deny_hits"], row, ctx)
        recommendations = [
            "Adjust the matched Deny statement so this request path is no "
            "longer covered, or move the request inside the allowed condition "
            "(for example issue it from the permitted VPC or IP range).",
            "If the caller uses temporary credentials, note that an AccessId "
            "condition keyed on a temporary prefix can be the intended bypass; "
            "verify which form the policy expects.",
            "Remember that an explicit Deny outranks every Allow, so adding an "
            "Allow statement elsewhere will not fix this.",
        ]
    elif decision == "implicit_deny":
        verdict = VERDICT_SELF_DIAGNOSABLE
        conclusion = ("No bucket policy statement allows this request, so it "
                      "was implicitly denied.")
        root_cause = _render_implicit_deny(analysis, row, ctx)
        recommendations = [
            "Add an Allow statement covering this action, resource and "
            "principal; see references/module4_policy_analysis.md for the "
            "exact bucket-policy grammar.",
            "If the caller is an assumed role, the principal must be written "
            "as an assumed-role ARN with a wildcard session name, otherwise a "
            "dynamic session never matches.",
        ]
    else:
        verdict = VERDICT_NEEDS_CONFIRMATION
        conclusion = ("A bucket policy Allow statement matches this request, "
                      "so the denial comes from another layer.")
        root_cause = ("The policy evaluation reached an explicit Allow, which "
                      "means the rejection was produced elsewhere - most likely "
                      "a RAM identity policy Deny, which outranks a bucket "
                      "policy Allow.")
        recommendations = [
            "Re-run with --ram-user <name> to scan the caller's RAM identity "
            "policies for an explicit Deny.",
            "Check whether a resource-directory control policy applies to this "
            "account; it produces the same rejection and is not visible in the "
            "bucket policy.",
        ]

    return {
        "verdict": verdict,
        "conclusion": conclusion,
        "root_cause": root_cause,
        "recommendations": recommendations,
        "evidence": {
            "decision": decision,
            "statement_count": analysis["statement_count"],
            "matched_statements": [h["statement"] for h in hits],
            "condition_analysis": [
                {"statement_index": h["index"], "conditions": h["conditions"]}
                for h in hits],
            "request_attributes": _request_attributes(row),
            "account_relation": ctx["account_relation"],
            "policy_grammar_warnings": _policy_grammar_warnings(analysis),
        },
    }

def _render_hit_explanation(deny_hits: list, row: dict, ctx: dict) -> str:
    """Explain, condition by condition, why the Deny statement matched."""
    lines = []
    for hit in deny_hits:
        lines.append(f"Statement #{hit['index']} (Effect: Deny) applies:")
        lines.append(f"  Action covers the logged operation "
                     f"'{row.get('operation', '-')}': yes")
        lines.append(f"  Resource covers '{ctx['bucket']}"
                     f"{('/' + str(row.get('object'))) if row.get('object') else ''}': yes")
        lines.append(f"  Principal: {hit['principal_note']}")
        for condition in hit["conditions"]:
            state = {True: "MET", False: "not met",
                     None: "not evaluable from the log"}[condition["matched"]]
            lines.append(
                f"  Condition {condition['operator']} "
                f"{condition['condition_key']}: expected "
                f"{condition['expected']}, actual '{condition['actual']}' "
                f"-> {state}")
            if condition.get("note"):
                lines.append(f"    note: {condition['note']}")
        lines.append("  Every required condition is satisfied, so the Deny "
                     "takes effect.")
    return "\n".join(lines)

def _render_implicit_deny(analysis: dict, row: dict, ctx: dict) -> str:
    """Explain why no statement allowed the request."""
    lines = [f"The bucket policy holds {analysis['statement_count']} "
             f"statement(s); none of them allows this request:"]
    for entry in analysis["evaluated"]:
        reason = []
        if not entry["action_covers"]:
            reason.append("action does not cover the logged operation")
        if not entry["resource_covers"]:
            reason.append("resource does not cover this bucket/object")
        if not entry["principal_covers"]:
            reason.append(f"principal does not cover the caller "
                          f"({entry['principal_note']})")
        if not entry["evaluable"]:
            reason.append("at least one condition cannot be evaluated from "
                          "the log")
        elif entry["conditions"] and all(
                c["matched"] is False for c in entry["conditions"]):
            reason.append("condition not satisfied")
        lines.append(f"  #{entry['index']} ({entry['effect']}): "
                     + ("; ".join(reason) if reason else "applies"))
    lines.append("With no Allow covering the request, access is implicitly "
                 "denied.")
    return "\n".join(lines)

def _policy_grammar_warnings(analysis: dict) -> list:
    """Surface configuration bugs found while evaluating the statements."""
    warnings = []
    for entry in analysis["evaluated"]:
        for condition in entry["conditions"]:
            if condition.get("note"):
                warnings.append(
                    f"statement #{entry['index']}, "
                    f"{condition['condition_key']}: {condition['note']}")
        principal = entry["statement"].get("Principal")
        if isinstance(principal, dict):
            warnings.append(
                f"statement #{entry['index']}: "
                + POLICY_PRINCIPAL_ANTIPATTERNS[0])
    return warnings

def rule_anonymous_denied(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A: an anonymous request was denied."""
    facts = ctx["facts"]
    operation = str(row.get("operation") or "")
    listing = operation in ("GetBucket", "GetBucketV2", "ListObjects")

    if listing and facts.get("bucket_acl") in ("public-read", "public-read-write"):
        conclusion = ("The anonymous listing request was denied even though "
                      "the bucket ACL is public.")
        root_cause = (
            f"Logged operation '{operation}' is the object-listing API. "
            f"Bucket ACL is {facts.get('bucket_acl')}. Neither public-read nor "
            f"public-read-write grants anonymous listing - the ACL only grants "
            f"anonymous object reads (and writes, for public-read-write). "
            f"Anonymous listing requires a bucket policy statement whose "
            f"principal is '*' and whose action covers listing. Policy "
            f"statements found: {facts.get('policy_statement_count', 0)}; "
            f"anonymous Allow present: {facts.get('policy_allows_anonymous')}.")
        recommendations = [
            "To allow anonymous listing, add a bucket policy Allow statement "
            'with Principal ["*"] and the listing action on '
            f"acs:oss:*:*:{ctx['bucket']}.",
            "If anonymous listing is not intended, no change is needed - this "
            "denial is the expected behaviour.",
        ]
    elif facts.get("block_public_access"):
        conclusion = "The anonymous request was denied by block-public-access."
        root_cause = (
            "Block public access is enabled, which overrides both bucket ACL "
            "and object ACL. Any anonymous request is therefore rejected "
            f"regardless of the ACL value ({facts.get('bucket_acl')}).")
        recommendations = [
            "If anonymous access is intended, turn off block public access for "
            "this bucket, then re-check the ACL and the policy.",
            "Otherwise switch the caller to a signed request (presigned URL or "
            "temporary credentials).",
        ]
    else:
        conclusion = "The anonymous request was denied by the bucket ACL."
        root_cause = (
            f"The request carried no signature (sign_type "
            f"'{row.get('sign_type', '-')}') and the bucket ACL is "
            f"{facts.get('bucket_acl')}, which does not permit anonymous "
            f"access to this operation ('{operation}').")
        recommendations = [
            "Use a presigned URL or temporary credentials for this request.",
            "Or grant the required access through a bucket policy statement.",
        ]

    return {
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "conclusion": conclusion,
        "root_cause": root_cause,
        "recommendations": recommendations,
        "evidence": {
            "request_attributes": _request_attributes(row),
            "bucket_acl": facts.get("bucket_acl"),
            "block_public_access": facts.get("block_public_access"),
            "policy_statement_count": facts.get("policy_statement_count"),
            "policy_allows_anonymous": facts.get("policy_allows_anonymous"),
        },
    }

def rule_object_read_denied(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A when the object ACL explains it, otherwise verdict C."""
    facts = ctx["facts"]
    conditional = ctx["evidence"].get("conditional", {}) or {}
    object_acl = conditional.get("object_acl") or {}
    grant = ""
    if object_acl.get("available"):
        # The SDK read is already parsed: the ACL is a plain string attribute.
        grant = str((object_acl.get("data") or {}).get("acl", "") or "")

    bucket_public = facts.get("bucket_acl") in ("public-read",
                                                 "public-read-write")

    if bucket_public and grant == "private":
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": ("The object carries its own private ACL, which "
                           "overrides the public bucket ACL."),
            "root_cause": (
                f"Bucket ACL is {facts.get('bucket_acl')} but the object ACL "
                f"read back as 'private'. An object-level ACL takes precedence "
                f"over the bucket ACL, so this single object stays unreadable "
                f"anonymously even though the bucket is public."),
            "recommendations": [
                "Set the object ACL back to default so it inherits the bucket "
                "setting, or grant access through a bucket policy.",
                "If many objects are affected, the writes that created them "
                "explicitly set a private ACL; fix the upload path as well.",
                "This skill is read-only and will not change the ACL for you.",
            ],
            "evidence": {"bucket_acl": facts.get("bucket_acl"),
                         "object_acl": grant,
                         "request_attributes": _request_attributes(row)},
        }

    # Object ACL is not private, or could not be read: the remaining cause is a
    # platform-level block, which no customer-facing API can confirm.
    return {
        "verdict": VERDICT_ESCALATE,
        "conclusion": ("The object cannot be read and the object ACL does not "
                       "explain it."),
        "root_cause": (
            "This error code has exactly two causes: an object-level private "
            "ACL, or a platform-level block on the object. The object ACL read "
            f"back as '{grant or 'unavailable'}' and the bucket ACL is "
            f"{facts.get('bucket_acl')}, so the first cause is not confirmed. "
            "Whether a platform-level block exists is not exposed through any "
            "customer-facing API, so this skill cannot verify it and will not "
            "guess. It is specifically not a content-security or firewall "
            "interception that you can inspect yourself."),
        "recommendations": [
            "Open a support ticket with the escalation package below; the "
            "platform-side block status has to be checked by support.",
            "Meanwhile confirm the object ACL and the bucket policy yourself, "
            "since those are the only causes you can rule out.",
        ],
        "evidence": {"bucket_acl": facts.get("bucket_acl"),
                     "object_acl": grant or "unavailable",
                     "object_acl_error": object_acl.get("error_code", ""),
                     "request_attributes": _request_attributes(row)},
    }

def rule_ram_deny_scan(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict B: an explicit Deny somewhere in the identity chain."""
    ram = ctx["evidence"].get("ram", {}) or {}
    denies = ram.get("deny_statements") or []
    if denies:
        lines = ["Explicit Deny statement(s) found on the caller's identity:"]
        for item in denies[:10]:
            lines.append(
                f"  policy {item.get('policy_name')} "
                f"({item.get('policy_type')}): "
                + json.dumps(item.get("statement"), ensure_ascii=False))
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": "An explicit Deny in a RAM identity policy rejected the request.",
            "root_cause": "\n".join(lines) + (
                "\nAn explicit Deny outranks every Allow, including any Allow "
                "in the bucket policy, so widening the bucket policy cannot fix "
                "this."),
            "recommendations": [
                "Narrow or remove the Deny statement identified above.",
                "Re-test after the change; policy evaluation is immediate.",
            ],
            "evidence": {"deny_statements": denies[:20],
                         "policies_scanned": len(ram.get("policies") or []),
                         "request_attributes": _request_attributes(row)},
        }
    if not ram.get("queried"):
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The request was denied by a RAM policy, but the "
                           "identity policies were not scanned."),
            "root_cause": (
                "This code means an explicit Deny in the caller's RAM identity "
                "policy, or a resource-directory control policy applied to the "
                "account. For object-level operations the log does not say "
                "which of the two produced it. No RAM scan was requested, so "
                "neither could be confirmed here."),
            "recommendations": [
                "Re-run with --ram-user <name> to scan the caller's identity "
                "policies for an explicit Deny.",
                "If no Deny is found there, check the resource-directory "
                "control policies applied to this account.",
                "Do not add an Allow to the bucket policy: a Deny outranks it.",
            ],
            "evidence": {"ram_scanned": False,
                         "request_attributes": _request_attributes(row)},
        }
    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": ("No explicit Deny was found on the scanned identity, so "
                       "a control policy is the remaining candidate."),
        "root_cause": (
            f"{len(ram.get('policies') or [])} identity policy(ies) were "
            f"scanned and none contains an explicit Deny for this request. The "
            f"remaining source of this error code is a resource-directory "
            f"control policy applied to the account, which is not readable "
            f"through the bucket-side configuration and cannot be confirmed "
            f"from the access log."),
        "recommendations": [
            "Check the resource-directory control policies applied to this "
            "account or to the folder containing it.",
            "Confirm the caller identity is the one you expect; a different "
            "RAM user or role may carry the Deny.",
        ],
        "evidence": {"policies_scanned": len(ram.get("policies") or []),
                     "deny_statements": [],
                     "ram_errors": ram.get("errors", []),
                     "request_attributes": _request_attributes(row)},
    }
