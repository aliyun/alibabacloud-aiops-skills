#!/usr/bin/env python3
"""

_policy_hit.py -- Bucket-policy hit analysis and log-free local derivations
===========================================================================
SECURITY: READ-ONLY. Pure logic over evidence that other modules collected.
No cloud I/O, no credential handling.

Internal module (prefixed with `_`). Do NOT run directly.

Contents
--------
  * OPERATION_TO_ACTION            log operation name -> policy action suffix
  * _action_matches / _resource_matches / _principal_matches /
    _ip_in_cidr_list / _wildcard_match / _evaluate_condition_block
                                   statement-level coverage tests
  * analyze_policy_hit             the verdict-A workhorse: which statement
                                   matched, and why, condition by condition
  * determine_account_relation     cross-account decision from the documented
                                   extend_information layout
  * validate_bucket_name_from_host naming-rule verdict that also records where
                                   the candidate name came from
  * decode_post_policy             base64 form-upload policy decoding

Every function here is total: empty or malformed input yields a result, never
an exception, because a missing field is evidence about the diagnosis rather
than a reason to abort it.
"""

from __future__ import annotations

import fnmatch
import ipaddress
import json
import re

from _constants import (
    BUCKET_NAME_PATTERN,
    POLICY_CONDITION_LOG_FIELDS,
    POLICY_OPERATOR_WILDCARD,
    POLICY_UNSUPPORTED_CONDITIONS,
    TEMPORARY_CREDENTIAL_PREFIXES,
)


OPERATION_TO_ACTION = {
    "GetBucket": "ListObjects",
    "GetBucketV2": "ListObjectsV2",
    "InitiateMultipartUpload": "InitiateMultipartUpload",
    "CompleteUploadPart": "CompleteMultipartUpload",
}

# ---------------------------------------------------------------------------
# Bucket-policy hit analysis (verdict A workhorse)
# ---------------------------------------------------------------------------

def _action_matches(statement_action, operation: str) -> bool:
    """Does the statement's Action cover the logged operation?"""
    wanted = OPERATION_TO_ACTION.get(operation, operation)
    actions = statement_action if isinstance(statement_action, list) \
        else [statement_action]
    for action in actions:
        name = str(action).strip()
        if name in ("*", "oss:*"):
            return True
        suffix = name.split(":", 1)[-1]
        if fnmatch.fnmatchcase(wanted, suffix) or suffix == wanted:
            return True
    return False


def _resource_matches(statement_resource, bucket: str, object_key: str) -> bool:
    """Does the statement's Resource cover this bucket / object?"""
    resources = statement_resource if isinstance(statement_resource, list) \
        else [statement_resource]
    for resource in resources:
        text = str(resource).strip()
        if text == "*":
            return True
        tail = text.split(":", 4)[-1] if text.count(":") >= 4 else text
        if fnmatch.fnmatchcase(bucket, tail):
            return True
        if object_key and fnmatch.fnmatchcase(f"{bucket}/{object_key}", tail):
            return True
        # acs:oss:*:*:bucket/* covers every object of the bucket.
        if tail.endswith("/*") and fnmatch.fnmatchcase(
                bucket, tail[:-2].rstrip("/")):
            return bool(object_key) or tail == f"{bucket}/*"
    return False


def _principal_matches(statement_principal, row: dict,
                       owner_id: str) -> tuple[bool, str]:
    """Does the statement's Principal cover the requester?

    Returns (matched, explanation). The logged requester_id of a RAM user
    differs from the account UID, so a bare inequality proves nothing; the
    RAM-role case is resolved through extend_information, whose documented
    layout is requesterParentId,roleName,roleSessionName,roleOwnerId.
    """
    principals = statement_principal if isinstance(statement_principal, list) \
        else [statement_principal]
    requester = str(row.get("requester_id") or "")
    access_id = str(row.get("access_id") or "")
    extend = str(row.get("extend_information") or "")

    parts = [p for p in extend.split(",") if p] if extend and extend != "-" else []
    role_owner = parts[3] if len(parts) >= 4 else ""
    role_name = parts[1] if len(parts) >= 2 else ""
    requester_parent = parts[0] if parts else ""

    for principal in principals:
        text = str(principal).strip()
        if text == "*":
            return True, 'Principal ["*"] covers every caller, including anonymous'
        if text.isdigit():
            if requester and text == requester:
                return True, f"Principal UID {text} equals the logged requester_id"
            if requester_parent and text == requester_parent:
                return True, (f"Principal UID {text} equals requesterParentId "
                              f"from extend_information")
            if role_owner and text == role_owner:
                return True, (f"Principal UID {text} equals roleOwnerId from "
                              f"extend_information (the account owning the "
                              f"assumed role)")
            if owner_id and text == owner_id:
                return True, f"Principal UID {text} equals the bucket owner"
        if text.startswith("arn:sts::"):
            # arn:sts::<uid>:assumed-role/<roleName>/<sessionName>
            match = re.match(
                r"arn:sts::(\d+):assumed-role/([^/]+)/(.+)$", text)
            if match:
                arn_uid, arn_role, arn_session = match.groups()
                if role_owner and arn_uid != role_owner:
                    continue
                if role_name and not fnmatch.fnmatchcase(role_name, arn_role):
                    continue
                if arn_session != "*" and parts and len(parts) >= 3:
                    if not fnmatch.fnmatchcase(parts[2], arn_session):
                        continue
                return True, (f"Principal ARN matches the assumed role "
                              f"{arn_role} (session pattern {arn_session})")
    return False, "No principal entry covers the logged requester"


def _ip_in_cidr_list(ip_text: str, cidrs: list) -> bool:
    """True when the logged client IP falls in any of the CIDR/IP entries."""
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return False
    for entry in cidrs:
        text = str(entry).strip()
        try:
            if "/" in text:
                if ip in ipaddress.ip_network(text, strict=False):
                    return True
            elif text == ip_text:
                return True
        except ValueError:
            continue
    return False


def _wildcard_match(value: str, pattern: str) -> bool:
    return fnmatch.fnmatchcase(value, pattern)


def _evaluate_condition_block(conditions: dict, row: dict) -> list[dict]:
    """Evaluate every operator/condition-key pair into a hit-analysis row."""
    results: list[dict] = []
    for operator, pairs in (conditions or {}).items():
        wildcard_ok = POLICY_OPERATOR_WILDCARD.get(operator, False)
        if not isinstance(pairs, dict):
            continue
        for condition_key, expected in pairs.items():
            expected_list = expected if isinstance(expected, list) else [expected]
            log_field = POLICY_CONDITION_LOG_FIELDS.get(condition_key)
            actual = str(row.get(log_field) or "") if log_field else ""

            unsupported = POLICY_UNSUPPORTED_CONDITIONS.get(condition_key)
            if unsupported:
                results.append({
                    "operator": operator, "condition_key": condition_key,
                    "expected": expected_list, "actual": actual,
                    "matched": False,
                    "note": f"UNSUPPORTED CONDITION KEY: {unsupported}",
                })
                continue

            if log_field is None:
                results.append({
                    "operator": operator, "condition_key": condition_key,
                    "expected": expected_list, "actual": "(no log field maps "
                                                        "to this key)",
                    "matched": None,
                    "note": "Cannot be evaluated from the access log; verify "
                            "manually.",
                })
                continue

            # Wildcard used with an operator that does not honour wildcards is a
            # configuration bug and silently never matches.
            wildcard_misuse = (not wildcard_ok) and any(
                "*" in str(e) for e in expected_list)

            if operator in ("IpAddress", "NotIpAddress"):
                inside = _ip_in_cidr_list(actual, expected_list)
                matched = inside if operator == "IpAddress" else not inside
            elif operator in ("StringEquals", "StringNotEquals"):
                equals = any(actual == str(e) for e in expected_list)
                matched = equals if operator == "StringEquals" else not equals
            elif operator in ("StringLike", "StringNotLike"):
                like = any(_wildcard_match(actual, str(e)) for e in expected_list)
                matched = like if operator == "StringLike" else not like
            elif operator == "Bool":
                flag = actual.lower() in ("true", "1", "yes")
                wanted = str(expected_list[0]).lower() in ("true", "1", "yes")
                matched = flag == wanted
            else:
                matched = None

            note = ""
            if wildcard_misuse:
                note = (f"CONFIGURATION BUG: {operator} does not honour "
                        f"wildcards, so a '*' entry is compared literally and "
                        f"will never match. Use StringLike for wildcards.")
            if condition_key == "oss:Prefix":
                note = ((note + " " if note else "") +
                        "oss:Prefix only applies to APIs carrying a prefix "
                        "parameter (listing). On object reads and writes the "
                        "condition never matches, so it restricts nothing.")
            if condition_key == "acs:SourceIp" and not any(
                    k == "acs:SourceVpc" for k in pairs):
                note = ((note + " " if note else "") +
                        "acs:SourceIp should be paired with acs:SourceVpc in a "
                        "bucket policy; without it the same IP range inside "
                        "another VPC also matches.")

            results.append({
                "operator": operator, "condition_key": condition_key,
                "expected": [str(e) for e in expected_list][:20],
                "actual": actual or "-", "matched": matched, "note": note,
            })
    return results


def analyze_policy_hit(statements: list, row: dict, bucket: str,
                       owner_id: str) -> dict:
    """Walk every statement and report which ones apply to this request.

    Explicit Deny outranks every Allow. When no Allow applies, the denial is
    implicit. Both outcomes are reported with the statement quoted verbatim so
    the customer can verify the reasoning without re-reading the log.
    """
    operation = str(row.get("operation") or "")
    object_key = str(row.get("object") or "")

    evaluated = []
    deny_hits = []
    allow_hits = []

    for index, statement in enumerate(statements, 1):
        if not isinstance(statement, dict):
            continue
        effect = str(statement.get("Effect") or "")
        action_ok = _action_matches(statement.get("Action"), operation)
        resource_ok = _resource_matches(statement.get("Resource"), bucket,
                                       object_key)
        principal_ok, principal_note = _principal_matches(
            statement.get("Principal"), row, owner_id)
        condition_rows = _evaluate_condition_block(
            statement.get("Condition") or {}, row)

        # A statement applies only when action, resource and principal all
        # cover the request; conditions then decide the outcome.
        applies = action_ok and resource_ok and principal_ok
        condition_decides = True
        if applies and condition_rows:
            for item in condition_rows:
                if item["matched"] is False:
                    condition_decides = False
                    break
                if item["matched"] is None:
                    condition_decides = None  # not evaluable from the log
        applies = applies and condition_decides is not False

        entry = {
            "index": index,
            "effect": effect,
            "statement": statement,
            "action_covers": action_ok,
            "resource_covers": resource_ok,
            "principal_covers": principal_ok,
            "principal_note": principal_note,
            "conditions": condition_rows,
            "applies": applies,
            "evaluable": condition_decides is not None,
        }
        evaluated.append(entry)
        if applies and effect.lower() == "deny":
            deny_hits.append(entry)
        elif applies and effect.lower() == "allow":
            allow_hits.append(entry)

    if deny_hits:
        decision = "explicit_deny"
    elif allow_hits:
        decision = "explicit_allow"
    else:
        decision = "implicit_deny"

    return {
        "decision": decision,
        "deny_hits": deny_hits,
        "allow_hits": allow_hits,
        "evaluated": evaluated,
        "statement_count": len(evaluated),
    }

# ---------------------------------------------------------------------------
# Cross-account determination
# ---------------------------------------------------------------------------

def determine_account_relation(row: dict, owner_id: str) -> dict:
    """Decide whether the request came from another account.

    A RAM user's requester_id always differs from the account UID, so a bare
    inequality proves nothing. For an assumed role the decisive value is
    roleOwnerId (the 4th field of extend_information), not the caller's own
    parent id.
    """
    extend = str(row.get("extend_information") or "")
    parts = [p for p in extend.split(",") if p] if extend and extend != "-" else []
    access_id = str(row.get("access_id") or "")
    requester = str(row.get("requester_id") or "")
    sign_type = str(row.get("sign_type") or "")

    is_temporary = access_id.startswith(TEMPORARY_CREDENTIAL_PREFIXES)
    result = {
        "sign_type": sign_type,
        "access_id_is_temporary": is_temporary,
        "requester_id": requester,
        "owner_id": owner_id,
        "extend_information_parts": parts,
        "cross_account": None,
        "basis": "",
    }
    if len(parts) >= 4:
        role_owner = parts[3]
        result["role_name"] = parts[1] if len(parts) > 1 else ""
        result["role_owner_id"] = role_owner
        result["cross_account"] = bool(owner_id) and role_owner != owner_id
        result["basis"] = (
            "Assumed-role request: roleOwnerId (4th field of "
            "extend_information) compared with the bucket owner. The session "
            "name is dynamic, so the role ARN in a policy must wildcard it.")
    elif requester and requester != "-":
        result["cross_account"] = bool(owner_id) and requester != owner_id
        result["basis"] = (
            "Direct request: requester_id compared with the bucket owner. Note "
            "that a RAM user's id always differs from the account uid, so a "
            "difference alone does not prove cross-account access.")
    else:
        result["cross_account"] = None
        result["basis"] = ("Anonymous request (no requester id), or the log row "
                           "carries no identity field to compare.")
    return result

# ---------------------------------------------------------------------------
# Local (log-free) rules
# ---------------------------------------------------------------------------

def validate_bucket_name_from_host(host: str, bucket_hint: str = "") -> dict:
    """Extract the bucket name from the host header and validate the name.

    A name containing a dot or an underscore can never exist, which makes the
    conclusion provable without any API call.
    """
    host = (host or "").strip()
    extracted = ""
    match = re.match(r"^(.+?)\.oss-[a-z0-9-]+\.[a-z0-9.-]+$", host)
    if match:
        extracted = match.group(1)
    candidate = extracted or bucket_hint
    # Where the candidate name came from decides how strong the conclusion can
    # be: a name read from the logged host header is evidence about the failing
    # request, while a name supplied by the caller is only a hint.
    name_source = "host" if extracted else (
        "caller-provided" if candidate else "")
    valid = bool(candidate) and bool(re.match(BUCKET_NAME_PATTERN, candidate))
    reasons = []
    if not candidate:
        reasons.append("No bucket name could be extracted from the host header.")
    else:
        if "." in candidate:
            reasons.append("The name contains a dot, which is not allowed.")
        if "_" in candidate:
            reasons.append("The name contains an underscore, which is not allowed.")
        if candidate != candidate.lower():
            reasons.append("The name contains uppercase characters.")
        if not 3 <= len(candidate) <= 63:
            reasons.append(f"The name length {len(candidate)} is outside 3-63.")
        if candidate and candidate[0] == "-" or candidate[-1:] == "-":
            reasons.append("The name must not start or end with a hyphen.")
    return {
        "host": host,
        "extracted_name": candidate,
        "name_source": name_source,
        "name_valid": valid,
        "reasons": reasons,
        "looks_like_domain": bool(candidate) and "." in candidate,
    }


def decode_post_policy(policy_b64: str) -> dict:
    """Decode a form-upload policy field and read its expiration."""
    import base64
    import datetime as dt
    if not policy_b64:
        return {"decoded": False}
    try:
        raw = base64.b64decode(policy_b64.strip(), validate=False)
        document = json.loads(raw.decode("utf-8", errors="replace"))
    except (ValueError, json.JSONDecodeError) as e:
        return {"decoded": False, "error": str(e)}
    expiration = str(document.get("expiration") or "")
    expired_at_request_time = None
    if expiration:
        try:
            when = expiration.replace("Z", "+00:00")
            parsed = dt.datetime.fromisoformat(when)
            expired_at_request_time = parsed < dt.datetime.now(dt.timezone.utc)
        except ValueError:
            pass
    return {
        "decoded": True,
        "expiration": expiration,
        "expiration_is_utc": expiration.endswith("Z"),
        "expired_relative_to_now": expired_at_request_time,
        "condition_count": len(document.get("conditions") or []),
        "document": document,
    }
