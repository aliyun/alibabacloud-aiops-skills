#!/usr/bin/env python3
"""
oss_cross_account_auth_diagnosis.py -- OSS cross-account access /
replication / migration authorization-failure diagnosis
===========================================================================
SECURITY: READ-ONLY. Only issues GetBucketInfo, GetBucketPolicy
(+ ListBuckets fallback) to the OSS control plane and GetCallerIdentity to
STS. It NEVER applies any authorization change: no PutBucketPolicy, no RAM
policy create/attach, no trust-policy edit, no replication configuration --
every fix is emitted as a configuration TEMPLATE (JSON) for the user to
apply manually. Credentials come exclusively from the default credential
chain (environment variables for the OSS SDK, aliyun CLI default chain for
STS); AK/SK are never read, printed, or passed explicitly.

Diagnoses:
  * cross-account access failures (AccessDenied / NoPermission) --
    ownership check, Bucket Policy existence + Principal-format check,
    RAM-policy-vs-Bucket-Policy dual-grant requirement
  * cross-account / cross-region replication NoPermission -- attribution
    method: server-log carries an STS RequestId -> trust policy missing
    oss.aliyuncs.com; no STS RequestId -> RAM policy missing the
    Replicate* actions (ticket case-law, see
    references/cross-account-auth-decision-tree.md)
  * cross-account migration authorization failures -- service-role trust
    policy and target-bucket Bucket Policy requirements
  * AssumeRole failure routing -- wrong-account role ARN, RAM-user ARN
    instead of role ARN, account-level vs resource-group grant, role-name
    case rules
  * outputs ready-to-apply authorization templates (trust policy with the
    oss.aliyuncs.com service principal, cross-account RAM policy,
    replication Bucket Policy) -- user applies them, never this skill

Output contract (04-spec): stdout carries a structured JSON report followed
by the machine-consumable lines:
    STATUS: OK | DEGRADED
    NEXT_ACTION: <one actionable sentence>

Usage:
  python3 oss_cross_account_auth_diagnosis.py --bucket <name> \
      [--scenario access|replication|migration|all] [--peer-uid <uid>] \
      [--role-name <name>] [--region <expected-region>]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

import _oss_client
import _doc_lookup
from _oss_client import OssClientError

# Inline contract assertion: an illegal bucket name must degrade to the
# unified OssClientError(category="invalid") -- never a bare oss2
# ClientError Traceback (measured on oss2 2.19.1: oss2.Bucket.__init__
# raises ClientError 'The bucket_name is invalid'; _build_bucket converts
# it, the entry records [WARN] + errors[] and still emits STATUS: DEGRADED
# with exit 0). No network call happens on this path.
try:
    _oss_client._build_bucket("Invalid_Bucket!", "oss-cn-hangzhou.aliyuncs.com")
    _INVALID_BUCKET_CATEGORY = "no-error"
except OssClientError as _e:
    _INVALID_BUCKET_CATEGORY = _e.category
except Exception:  # pragma: no cover - regression guard
    _INVALID_BUCKET_CATEGORY = "unexpected-traceback"
assert _INVALID_BUCKET_CATEGORY == "invalid"  # invalid: illegal bucket name

_DEFAULT_ENDPOINT = "oss-cn-hangzhou.aliyuncs.com"
_VALID_SCENARIOS = ("access", "replication", "migration", "all")


# ---------------------------------------------------------------------------
# Pure verdict functions (each carries inline boundary assertions:
# normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------

def endpoint_from_location(location: str) -> str:
    """Derive the public query endpoint from a bucket location string."""
    loc = (location or "").strip().lower()
    if not loc:
        return ""
    if not loc.startswith("oss-"):
        loc = "oss-" + loc
    return loc + ".aliyuncs.com"


assert endpoint_from_location("oss-cn-hangzhou") == "oss-cn-hangzhou.aliyuncs.com"  # normal
assert endpoint_from_location("cn-shanghai") == "oss-cn-shanghai.aliyuncs.com"  # boundary: bare region
assert endpoint_from_location("") == ""  # invalid: empty


def normalize_policy_state(raw) -> str:
    """Normalize a GetBucketPolicy result state.

    Returns one of: present | not_configured | unknown.
    Measured: oss2 raises NoSuchBucketPolicy (404) when no policy exists;
    the shared client converts it to state 'not_configured', which is a
    normal configuration fact, NOT an error.
    """
    s = (str(raw).strip().lower() if raw is not None else "")
    if s == "present":
        return "present"
    if s in ("not_configured", "none", "", "null"):
        return "not_configured"
    return "unknown"


assert normalize_policy_state("present") == "present"  # normal
assert normalize_policy_state("not_configured") == "not_configured"  # normal
assert normalize_policy_state(None) == "not_configured"  # boundary: None
assert normalize_policy_state("  PRESENT ") == "present"  # boundary: case+whitespace
assert normalize_policy_state("weird-value") == "unknown"  # invalid


def ownership_relation(caller_uid: str, owner_id: str) -> str:
    """Compare the caller account UID with the bucket owner UID.

    Returns same_account | cross_account | unknown. Note (measured
    semantics): for an assumed-role STS credential, GetCallerIdentity
    returns the AccountId of the account OWNING the role, so the
    comparison stays meaningful. An empty UID on either side means the
    fact could not be established -> unknown (never guess).
    """
    c = str(caller_uid or "").strip()
    o = str(owner_id or "").strip()
    if not c or not o:
        return "unknown"
    return "same_account" if c == o else "cross_account"


assert ownership_relation("1552974654746705", "1552974654746705") == "same_account"  # normal
assert ownership_relation("1111111111111111", "2222222222222222") == "cross_account"  # normal
assert ownership_relation("", "2222222222222222") == "unknown"  # boundary: caller degraded
assert ownership_relation("1111111111111111", "") == "unknown"  # boundary: owner degraded
assert ownership_relation(None, None) == "unknown"  # invalid


def ownership_identity_caveat(caller_uid: str, owner_id: str) -> str:
    """F-1 guard: annotate the ownership relation when the caller UID and
    the bucket owner UID (GetBucketInfo owner_id) differ.

    The caller UID comes from the aliyun CLI default credential chain,
    which may be a DIFFERENT account than the data-plane credential that
    actually read the bucket (ALIBABA_CLOUD_* environment variables). The
    caveat makes that skew visible instead of letting a cross_account
    verdict be silently trusted. Returns '' when the relation carries no
    skew signal (consistent, or either side missing).
    """
    c = str(caller_uid or "").strip()
    o = str(owner_id or "").strip()
    if not c or not o or c == o:
        return ""
    return ("caller UID comes from the aliyun CLI default credential "
            "chain; if the data-plane credential (ALIBABA_CLOUD_* "
            "environment variables) that read this bucket belongs to a "
            "different account, this relation may reflect an "
            "identity-chain skew rather than real cross-account access "
            "-- align the identity chain with the data plane (e.g. lock "
            "ALIBABA_CLOUD_PROFILE) before acting on it")


assert ownership_identity_caveat("1552974654746705", "1552974654746705") == ""  # normal: consistent -> no caveat
assert "identity-chain skew" in ownership_identity_caveat("1772241626973633", "1552974654746705")  # normal: skew -> caveat
assert ownership_identity_caveat("", "1552974654746705") == ""  # boundary: caller degraded
assert ownership_identity_caveat("1552974654746705", "") == ""  # boundary: owner degraded
assert ownership_identity_caveat(None, None) == ""  # invalid


def attribute_no_permission(has_sts_request_id) -> dict:
    """Attribute a replication/migration NoPermission via the STS-RequestId
    method (ticket case 2: PutBucketReplication 403 NoPermission).

    has_sts_request_id:
      True  -- server-log shows a separate STS RequestId -> OSS internally
               AssumeRole'd the configured role and STS rejected it ->
               TRUST POLICY problem (Principal.Service must contain
               oss.aliyuncs.com).
      False -- no STS RequestId in server-log -> OSS never attempted to
               assume the role -> RAM POLICY problem (missing Replicate*
               actions / wrong Resource granularity).
      None  -- server-log not collected -> inconclusive; both branches are
               returned for manual checking.
    """
    if has_sts_request_id is True:
        return {
            "attribution": "trust_policy",
            "evidence": "server-log carries a separate STS RequestId: OSS "
                        "attempted AssumeRole on the configured replication "
                        "role and STS rejected it",
            "fix_direction": "add oss.aliyuncs.com to the role trust "
                             "policy Principal.Service; after editing the "
                             "trust policy NO re-submission of the "
                             "replication rule is needed (takes effect on "
                             "the next assume attempt)",
        }
    if has_sts_request_id is False:
        return {
            "attribution": "ram_policy",
            "evidence": "server-log has NO STS RequestId: OSS never "
                        "attempted to assume the role, so the role's "
                        "permission policy is the blocker",
            "fix_direction": "grant the role the Replicate* actions with "
                             "the exact source/destination bucket ARNs "
                             "(resource granularity matters: a missing or "
                             "misspelled bucket in Resource fails the "
                             "authorization check)",
        }
    return {
        "attribution": "inconclusive",
        "evidence": "server-log / STS RequestId not collected yet; both "
                    "branches must be checked",
        "fix_direction": "check BOTH: (1) role trust policy contains "
                         "oss.aliyuncs.com under Principal.Service; (2) "
                         "role permission policy grants oss:ReplicateList/"
                         "oss:ReplicateGet on the exact source bucket ARN "
                         "(and the destination bucket is covered by a "
                         "Bucket Policy in the destination account for "
                         "cross-account replication)",
    }


_a = attribute_no_permission(True)
assert _a["attribution"] == "trust_policy" and "oss.aliyuncs.com" in _a["fix_direction"]  # normal
_a = attribute_no_permission(False)
assert _a["attribution"] == "ram_policy" and "Replicate" in _a["fix_direction"]  # normal
_a = attribute_no_permission(None)
assert _a["attribution"] == "inconclusive" and "BOTH" in _a["fix_direction"]  # boundary: no evidence
del _a


def _split_principals(policy: dict) -> dict:
    """Split every Statement's Principal values by Effect (CAA-1).

    Measured OSS Bucket Policy syntax: Principal is a LIST of strings
    (bare account UID, RAM-user UID, or
    arn:sts::<uid>:assumed-role/<role>/<session-or-*>); a dict-form
    Principal is RAM-policy syntax and is flagged as misuse.
    Only Allow statements carry authorization semantics: a Deny
    statement's principals must never be treated as a grant (the
    measured false positive: Alibaba Cloud automatic security-protection
    Deny statements carry Principal "*" and were misread as anonymous
    grants). Deny statement originals are returned separately so the
    report can carry the hit Statement text (EC 0003-00000101).
    """
    statements = policy.get("Statement") or []
    if isinstance(statements, dict):
        statements = [statements]
    allow: list = []
    deny: list = []
    all_principals: list = []
    deny_statements: list = []
    for st in statements:
        if not isinstance(st, dict):
            continue
        effect = str(st.get("Effect") or "").strip().lower()
        p = st.get("Principal")
        plist: list = []
        if isinstance(p, str):
            plist = [p]
        elif isinstance(p, list):
            plist = [str(x) for x in p]
        elif isinstance(p, dict):
            plist = ["__RAM_POLICY_STYLE_DICT__"]
        all_principals.extend(plist)
        if effect == "deny":
            deny_statements.append(st)
            deny.extend(plist)
        else:
            allow.extend(plist)
    return {"allow": allow, "deny": deny, "all": all_principals,
            "deny_statements": deny_statements}


def check_bucket_policy(policy_str: str, peer_uid: str = "",
                        role_name: str = "") -> dict:
    """Static sanity check of a Bucket Policy for cross-account grants.

    policy_str: raw policy JSON ("" / None = no policy configured).
    peer_uid:   the other account's UID expected in the Principal list.
    role_name:  the replication/migration role name expected inside an
                assumed-role principal.
    Returns {"verdict": ok|missing|malformed|gaps, "principals": [...],
             "deny_statements": [...], "findings": [{"severity":
             "error"|"warn"|"info", "message": str}]}.

    CAA-1 semantics (Effect-aware): a Deny statement with Principal
    "*" is the measured shape of the Alibaba Cloud automatic
    security-protection deny (statement text commonly annotated
    "Created by Alibaba Cloud Security, do not modify this action") --
    it is reported as ONE informational protective-deny finding
    (identical statements are deduplicated), never as anonymous
    access, and never triggers a replace/re-create recommendation.
    Peer/role presence checks run against Allow principals only; a
    peer found in a Deny statement is an explicit-deny finding.
    Syntax checks (dict-form Principal, acs:ram:: ARN misuse,
    role-name case) still apply to every statement. Verdict is "gaps"
    only when an error/warn finding exists; info-only policies are
    "ok". deny_statements carries the Deny statement originals for
    EC 0003-00000101 attribution ("naming the policy is not a
    diagnosis -- quote the hit Statement").
    """
    findings: list = []
    raw = (policy_str or "").strip()
    if not raw:
        return {
            "verdict": "missing",
            "principals": [],
            "deny_statements": [],
            "findings": [{
                "severity": "error",
                "message": "no Bucket Policy is configured on this bucket "
                           "(GetBucketPolicy returned NoSuchBucketPolicy); "
                           "for cross-account access/replication the "
                           "bucket-owning account MUST add a Bucket Policy "
                           "granting the peer account or the peer's "
                           "assumed role",
            }],
        }
    try:
        policy = json.loads(raw)
    except (ValueError, TypeError):
        return {
            "verdict": "malformed",
            "principals": [],
            "deny_statements": [],
            "findings": [{
                "severity": "error",
                "message": "the Bucket Policy is not valid JSON; it cannot "
                           "be evaluated -- re-create it from the template "
                           "in references/auth-config-templates.md",
            }],
        }
    parts = _split_principals(policy)
    principals = parts["all"]
    allow_principals = parts["allow"]
    deny_principals = parts["deny"]
    deny_statements = parts["deny_statements"]
    if "__RAM_POLICY_STYLE_DICT__" in principals:
        findings.append({
            "severity": "error",
            "message": "a Statement uses dict-form Principal (RAM-policy "
                       "syntax); Bucket Policy requires a LIST of strings: "
                       "bare UID digits or "
                       "arn:sts::<uid>:assumed-role/<role>/<session> -- "
                       "the two syntaxes must not be mixed",
        })
    # Syntax checks apply to every statement regardless of Effect.
    for p in principals:
        if p == "__RAM_POLICY_STYLE_DICT__":
            continue
        if p.startswith("acs:ram::"):
            findings.append({
                "severity": "error",
                "message": f"Principal '{p}' uses the RAM-policy ARN form "
                           "(acs:ram::...); in a Bucket Policy write the "
                           "bare account UID digits, or "
                           "arn:sts::<uid>:assumed-role/<role>/<session> "
                           "for an assumed-role identity",
            })
        elif any(ch.isupper() for ch in p) and "assumed-role" in p:
            findings.append({
                "severity": "warn",
                "message": f"Principal '{p}' contains uppercase letters in "
                           "the role part; OSS role names are all-lowercase "
                           "and an assumed-role principal must match "
                           "exactly",
            })
    # CAA-1: '*' handling is split by Effect. Only an ALLOW statement
    # with Principal '*' grants anonymous access; Deny statements with
    # '*' are protective denies (deduplicated into one info finding).
    allow_wild = sum(1 for p in allow_principals if p == "*")
    deny_wild = sum(1 for p in deny_principals if p == "*")
    if allow_wild:
        findings.append({
            "severity": "warn",
            "message": f"Principal '*' appears in {allow_wild} Allow "
                       "statement(s) and grants anonymous access; for "
                       "cross-account authorization replace it with the "
                       "peer account UID or the assumed-role ARN",
        })
    if deny_wild:
        findings.append({
            "severity": "info",
            "message": f"{deny_wild} Deny statement(s) with Principal '*' "
                       "detected: these are protective denies (the "
                       "measured Alibaba Cloud automatic security-"
                       "protection shape, commonly annotated 'Created by "
                       "Alibaba Cloud Security, do not modify this "
                       "action') -- a normal security configuration, NOT "
                       "anonymous access; do NOT remove or re-create them",
        })
    # Peer/role presence checks run against Allow principals only
    # (a Deny statement never grants anything).
    peer = str(peer_uid or "").strip()
    if peer:
        hit = any(peer in p for p in allow_principals
                  if p != "__RAM_POLICY_STYLE_DICT__")
        if not hit:
            findings.append({
                "severity": "error",
                "message": f"no Allow statement Principal references the "
                           f"peer account UID {peer}; add '{peer}' (direct "
                           f"access) or 'arn:sts::{peer}:assumed-role/"
                           "<role>/*' (role-based access) to the Principal "
                           "list",
            })
        if any(peer in p for p in deny_principals
               if p != "__RAM_POLICY_STYLE_DICT__"):
            findings.append({
                "severity": "warn",
                "message": f"the peer account UID {peer} appears in a Deny "
                           "statement: the peer is explicitly DENIED, and "
                           "an explicit Deny always wins over every Allow "
                           "(see references/cross-account-auth-decision-"
                           "tree.md EC 0003-00000201) -- remove or narrow "
                           "the Deny instead of adding more Allows",
            })
    role = str(role_name or "").strip()
    if role:
        lowered = role.lower()
        # Normalize the user input first: a role name typed with mixed
        # case still matches the policy case-insensitively and is NOT an
        # error by itself.
        exact = any(f"assumed-role/{lowered}/" in p
                    for p in allow_principals)
        # A case error exists ONLY when the policy TEXT itself carries a
        # non-lowercase variant of the role name (OSS role names are
        # all-lowercase and the principal must match exactly).
        case_variant = any(
            "assumed-role" in p and f"assumed-role/{lowered}/" in
            p.lower() and f"assumed-role/{lowered}/" not in p
            for p in allow_principals)
        if case_variant:
            findings.append({
                "severity": "error",
                "message": f"the assumed-role Principal references role "
                           f"'{role}' with different case in the policy "
                           "text; OSS role names are all-lowercase and "
                           "the principal must match exactly",
            })
        elif not exact:
            findings.append({
                "severity": "warn",
                "message": f"no Allow statement assumed-role Principal "
                           f"references role '{role}'; for replication/"
                           f"migration add arn:sts::<src-uid>:assumed-role/"
                           f"{lowered}/*",
            })
    verdict = "gaps" if any(f["severity"] in ("error", "warn")
                            for f in findings) else "ok"
    return {"verdict": verdict, "principals": principals,
            "deny_statements": deny_statements,
            "findings": findings}


_c = check_bucket_policy("")
assert _c["verdict"] == "missing" and _c["findings"][0]["severity"] == "error"  # boundary: no policy
_c = check_bucket_policy("{not-json")
assert _c["verdict"] == "malformed"  # invalid: broken JSON
_c = check_bucket_policy(json.dumps({"Version": "1", "Statement": [
    {"Effect": "Allow", "Principal": ["1111111111111111"],
     "Action": ["oss:GetObject"], "Resource": ["acs:oss:*:*:b"]}]}))
assert _c["verdict"] == "ok" and _c["principals"] == ["1111111111111111"]  # normal: clean policy
_c = check_bucket_policy(json.dumps({"Statement": [
    {"Principal": ["acs:ram::1111111111111111:root"]}]}), peer_uid="2222222222222222")
assert any("acs:ram::" in f["message"] for f in _c["findings"])  # normal: ARN misuse detected
assert any("2222222222222222" in f["message"] for f in _c["findings"])  # normal: peer missing
_c = check_bucket_policy(json.dumps({"Statement": [
    {"Principal": ["arn:sts::1111111111111111:assumed-role/MyRole/*"]}]}),
    role_name="myrole")
assert any("different case" in f["message"] for f in _c["findings"])  # boundary: case mismatch
_c = check_bucket_policy(json.dumps({"Statement": [
    {"Principal": ["arn:sts::1111111111111111:assumed-role/myrole/*"]}]}),
    role_name="MyRole")
assert not any("case" in f["message"] for f in _c["findings"])  # boundary: user-input case normalized -> no false positive
assert _c["verdict"] == "ok"  # boundary: case-insensitive hit counts as present

# CAA-1 regression guards: Effect-aware '*' and Deny handling (three
# shapes measured on buckets nicer / daolingtest20240409 -- Alibaba Cloud
# automatic security-protection Deny statements carry Principal '*' and
# were previously misreported as anonymous-access grants with a
# replace/re-create recommendation; that P0 false positive must never
# come back).
_p = json.dumps({"Statement": [
    {"Effect": "Allow", "Principal": ["*"], "Action": ["oss:GetObject"],
     "Resource": ["acs:oss:*:*:b"]}]})
_c = check_bucket_policy(_p)
assert _c["verdict"] == "gaps"  # shape 1: Allow+'*' IS anonymous access
assert len(_c["findings"]) == 1 and _c["findings"][0]["severity"] == "warn"
assert "anonymous access" in _c["findings"][0]["message"]
assert _c["deny_statements"] == []
_p = json.dumps({"Statement": [
    {"Effect": "Deny", "Principal": ["*"], "Action": ["oss:*"],
     "Resource": ["acs:oss:*:*:b"],
     "Condition": {"NotIpAddress": {"acs:SourceIp": ["127.0.0.1/32"]}}}] * 3})
_c = check_bucket_policy(_p)
assert _c["verdict"] == "ok"  # shape 2: Deny+'*' x3 -> protective, NOT gaps
assert len(_c["findings"]) == 1 and _c["findings"][0]["severity"] == "info"
assert "protective" in _c["findings"][0]["message"]
assert "grants anonymous access" not in _c["findings"][0]["message"]  # (the info text says "NOT anonymous access" -- only the Allow-warn wording 'grants anonymous access' must be absent)
assert len(_c["deny_statements"]) == 3  # EC 0003-00000101: originals carried
_p = json.dumps({"Statement": [
    {"Effect": "Allow", "Principal": ["*"], "Action": ["oss:GetObject"],
     "Resource": ["acs:oss:*:*:b"]},
    {"Effect": "Deny", "Principal": ["*"], "Action": ["oss:*"],
     "Resource": ["acs:oss:*:*:b"]}]})
_c = check_bucket_policy(_p)
assert _c["verdict"] == "gaps"  # shape 3: mixed -- warn + info coexist
assert sorted(f["severity"] for f in _c["findings"]) == ["info", "warn"]
# EC 0003-00000201 shape: peer granted in Allow BUT explicitly denied too.
_p = json.dumps({"Statement": [
    {"Effect": "Allow", "Principal": ["2222222222222222"],
     "Action": ["oss:GetObject"], "Resource": ["acs:oss:*:*:b"]},
    {"Effect": "Deny", "Principal": ["2222222222222222"], "Action": ["oss:*"],
     "Resource": ["acs:oss:*:*:b"]}]})
_c = check_bucket_policy(_p, peer_uid="2222222222222222")
assert _c["verdict"] == "gaps"  # explicit Deny always wins over the Allow
assert any("explicitly DENIED" in f["message"] for f in _c["findings"])
assert not any("no Allow statement Principal references" in f["message"]
               for f in _c["findings"])  # the Allow itself is well-formed
del _c
del _p


def account_scope_note(uid: str) -> str:
    """CAA-4: account-scope statement attached to every report.

    Forensics-precedent wording: conclusions reflect ONLY the account
    of the current credential; under an assumed-role credential the
    caller UID is the role-owning account. A not_configured/empty
    result is visibility-scoped ("not visible to THIS account's
    credential"), never absolute ("no policy exists").
    """
    u = str(uid or "").strip()
    who = f" (caller UID {u})" if u else ""
    return (
        "All conclusions reflect ONLY the account of the current "
        f"credential{who}; under an assumed-role STS credential the "
        "caller UID is the role-owning account. A not_configured or "
        "empty result means 'not visible to this account's "
        "credential', NOT that no policy exists in absolute terms."
    )


_n = account_scope_note("1552974654746705")
assert "1552974654746705" in _n and "ONLY" in _n  # normal: uid embedded
assert "role-owning account" in _n  # normal: assumed-role semantics
assert "not visible to this account" in _n  # visibility-scoped wording
_n = account_scope_note("")
assert "(caller UID" not in _n  # boundary: no uid -> no "(caller UID ...)" label
del _n


def trust_policy_template(trust: str = "service", peer_uid: str = "") -> dict:
    """Build a RAM role TRUST POLICY template.

    trust: service  -> Principal.Service ["oss.aliyuncs.com"] (replication /
                       migration service roles; official doc shape)
           account  -> Principal.RAM ["acs:ram::<peer_uid>:root"] (peer
                       account may assume this role)
           both     -> both principals combined
    Returns {"json": <formatted string>, "notes": [str]}. The JSON is a
    TEMPLATE ONLY -- applying it is a write operation the user performs.
    """
    peer = str(peer_uid or "").strip()
    principal: dict = {}
    notes: list = []
    if trust in ("service", "both"):
        principal["Service"] = ["oss.aliyuncs.com"]
        notes.append(
            "Principal.Service oss.aliyuncs.com lets the OSS service "
            "assume this role for replication/migration; without it the "
            "service's internal AssumeRole is rejected and the task "
            "reports NoPermission.")
    if trust in ("account", "both"):
        uid = peer if peer.isdigit() else "<peer-account-UID>"
        principal["RAM"] = [f"acs:ram::{uid}:root"]
        notes.append(
            "Principal.RAM acs:ram::<peer-account-UID>:root trusts the "
            "WHOLE peer account; to narrow it, replace :root with "
            "user/<ram-user-name> (official RAM cross-account pattern).")
    if trust not in ("service", "account", "both"):
        raise ValueError(f"unknown trust type: {trust}")
    doc = {"Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow",
                          "Principal": principal}], "Version": "1"}
    return {"json": json.dumps(doc, indent=2, ensure_ascii=False),
            "notes": notes}


_t = trust_policy_template("service")
assert "oss.aliyuncs.com" in _t["json"] and "sts:AssumeRole" in _t["json"]  # normal
_t = trust_policy_template("account", "2222222222222222")
assert "acs:ram::2222222222222222:root" in _t["json"]  # normal: peer UID filled
_t = trust_policy_template("account")
assert "<peer-account-UID>" in _t["json"]  # boundary: placeholder kept
_t = trust_policy_template("both", "2222222222222222")
assert "oss.aliyuncs.com" in _t["json"] and "2222222222222222" in _t["json"]  # boundary: combined
try:
    trust_policy_template("weird")
    _RAISED = False
except ValueError:
    _RAISED = True
assert _RAISED  # invalid: unknown trust type
del _t, _RAISED


def cross_account_access_ram_policy_template(bucket: str) -> dict:
    """RAM permission policy template attached to the cross-account role in
    the BUCKET-OWNER's account (official least-privilege shape)."""
    b = (bucket or "").strip() or "<bucket-name>"
    doc = {
        "Version": "1",
        "Statement": [
            {"Effect": "Allow",
             "Action": ["oss:ListObjects"],
             "Resource": [f"acs:oss:*:*:{b}"]},
            {"Effect": "Allow",
             "Action": ["oss:GetObject", "oss:PutObject"],
             "Resource": [f"acs:oss:*:*:{b}/*"]},
        ],
    }
    return {
        "json": json.dumps(doc, indent=2, ensure_ascii=False),
        "notes": [
            "Attach this policy to the RAM role created in the "
            "bucket-OWNER's account; the peer account assumes the role via "
            "STS and accesses the bucket with the temporary credential.",
            "Resource granularity is the classic pitfall: the bucket-level "
            "ARN (no trailing /*) covers ListObjects, the object-level ARN "
            "with /* covers GetObject/PutObject -- one missing ARN fails "
            "the whole flow.",
        ],
    }


_p = cross_account_access_ram_policy_template("test-agentceping")
assert "acs:oss:*:*:test-agentceping/*" in _p["json"] and "oss:ListObjects" in _p["json"]  # normal
_p = cross_account_access_ram_policy_template("")
assert "<bucket-name>" in _p["json"]  # boundary: placeholder
del _p


def replication_ram_policy_template(src_bucket: str) -> dict:
    """RAM permission policy for the replication role in the SOURCE account
    (official data-replication-permissions shape)."""
    b = (src_bucket or "").strip() or "<src-bucket>"
    doc = {
        "Version": "1",
        "Statement": [
            {"Effect": "Allow",
             "Action": ["oss:ReplicateList", "oss:ReplicateGet"],
             "Resource": [f"acs:oss:*:*:{b}", f"acs:oss:*:*:{b}/*"]},
        ],
    }
    return {
        "json": json.dumps(doc, indent=2, ensure_ascii=False),
        "notes": [
            "Attach to the replication RAM role of the SOURCE-bucket "
            "account; the Resource MUST name the exact source bucket -- a "
            "misspelled bucket ARN is a measured top cause of replication "
            "NoPermission.",
            "For same-account replication extend this policy with the "
            "destination bucket ARN plus oss:ReplicatePut (and "
            "oss:ReplicateDelete for add/delete/change sync).",
        ],
    }


_p = replication_ram_policy_template("src-bucket")
assert "oss:ReplicateList" in _p["json"] and "acs:oss:*:*:src-bucket/*" in _p["json"]  # normal
_p = replication_ram_policy_template("")
assert "<src-bucket>" in _p["json"]  # boundary
del _p


def replication_bucket_policy_template(src_uid: str, role_name: str,
                                       dest_uid: str,
                                       dest_bucket: str) -> dict:
    """Bucket Policy template for the DESTINATION bucket (cross-account
    replication dual-grant requirement, official doc shape)."""
    su = (src_uid or "").strip() or "<src-uid>"
    rn = (role_name or "").strip().lower() or "<role-name>"
    du = (dest_uid or "").strip() or "<dest-uid>"
    db = (dest_bucket or "").strip() or "<dest-bucket>"
    doc = {
        "Version": "1",
        "Statement": [
            {"Effect": "Allow",
             "Action": ["oss:ReplicateList", "oss:ReplicateGet",
                        "oss:ReplicatePut", "oss:ReplicateDelete"],
             "Principal": [f"arn:sts::{su}:assumed-role/{rn}/*"],
             "Resource": [f"acs:oss:*:{du}:{db}", f"acs:oss:*:{du}:{db}/*"]},
        ],
    }
    return {
        "json": json.dumps(doc, indent=2, ensure_ascii=False),
        "notes": [
            "Cross-account replication is a DUAL grant: the source account "
            "gives the role a RAM Policy, the destination account adds THIS "
            "Bucket Policy on the destination bucket -- one side missing "
            "fails with NoPermission.",
            "Bucket Policy Principal syntax differs from RAM Policy: here "
            "it is the assumed-role ARN arn:sts::<src-uid>:assumed-role/"
            "<role>/*; the role name is all-lowercase and must match "
            "exactly.",
        ],
    }


_p = replication_bucket_policy_template("1111111111111111", "MyRole",
                                        "2222222222222222", "dest-bkt")
assert "arn:sts::1111111111111111:assumed-role/myrole/*" in _p["json"]  # normal: lowercased role
assert "acs:oss:*:2222222222222222:dest-bkt" in _p["json"]  # normal
_p = replication_bucket_policy_template("", "", "", "")
assert "<src-uid>" in _p["json"] and "<role-name>" in _p["json"]  # boundary: placeholders
del _p


def assume_role_failure_routes() -> list:
    """Knowledge ladder for AssumeRole failures on the OSS cross-account
    path (distilled from real tickets; no cloud call involved)."""
    return [
        "The RoleArn points at the WRONG account (acs:ram::<other-uid>:"
        "role/... copied from documentation or another account) -- STS "
        "cannot find/trust it; use the role ARN of the account that owns "
        "the role.",
        "A RAM-USER ARN (acs:ram::<uid>:user/<name>) was passed as RoleArn "
        "-- AssumeRole only accepts RAM ROLES (acs:ram::<uid>:role/<name>); "
        "STS answers 'The specified Role not exists'.",
        "AliyunSTSAssumeRoleAccess was granted at RESOURCE-GROUP scope -- "
        "AssumeRole is an account-level action; the grant must be at "
        "ACCOUNT level.",
        "The role's trust policy does not include the caller (peer account "
        "root / RAM user, or the oss.aliyuncs.com service principal for "
        "OSS-internal assumes); STS rejects the assume and OSS surfaces "
        "NoPermission.",
        "The STS temporary credential was obtained but the client keeps "
        "using the original account's long-lived AK (or omits the "
        "SecurityToken) -- cross-account access only works through the "
        "assumed-role credential.",
    ]


_routes = assume_role_failure_routes()
assert len(_routes) >= 5 and any("RoleArn" in r for r in _routes)  # normal
assert any("resource-group" in r.lower() for r in _routes)  # boundary: account-level fact present
assert all(isinstance(r, str) and r for r in _routes)  # invalid guard: no empty entries
del _routes


def build_recommendations(scenario: str, ownership: str,
                          policy_state: str, policy_verdict: str,
                          attribution: dict) -> list:
    """Compose evidence-based next-step recommendations."""
    recs: list = []
    if ownership == "cross_account":
        recs.append(
            "The caller account does NOT own this bucket: access must come "
            "through authorization granted BY the owning account (Bucket "
            "Policy on the bucket and/or a RAM role created in the owning "
            "account) -- check both sides, one-sided grants are a top "
            "failure cause.")
    elif ownership == "same_account":
        recs.append(
            "The caller account owns this bucket; if a peer account "
            "reports the failure, the missing grant is on THIS account "
            "side (Bucket Policy / RAM role).")
    if policy_state == "not_configured" and scenario in ("access",
                                                         "replication",
                                                         "all"):
        recs.append(
            "No Bucket Policy is configured on the bucket (measured); for "
            "cross-account access or cross-account replication the owning "
            "account must add one -- use the template emitted by this "
            "report (references/auth-config-templates.md).")
    elif policy_state == "present" and policy_verdict in ("gaps",
                                                           "malformed"):
        recs.append(
            "The existing Bucket Policy has structural problems listed in "
            "policy_check.findings (Principal syntax / missing peer "
            "UID / case mismatch); re-create it from the template.")
    if scenario in ("replication", "migration", "all"):
        recs.append(
            "Replication/migration NoPermission attribution: if the "
            "server-log carries a separate STS RequestId the fix is the "
            "role TRUST POLICY (add oss.aliyuncs.com to Principal.Service); "
            "without an STS RequestId the fix is the role PERMISSION "
            "POLICY (Replicate* actions on the exact bucket ARNs).")
        recs.append(
            "Cross-account replication requires the DUAL grant: RAM Policy "
            "on the replication role in the source account PLUS Bucket "
            "Policy on the destination bucket naming the assumed role -- "
            "granting AliyunOSSFullAccess on one side is NOT sufficient.")
    if attribution.get("attribution") == "inconclusive":
        recs.append(
            "Collect the failing request's reqId and ask for the "
            "server-log to apply the STS-RequestId attribution method; "
            "until then both trust-policy and permission-policy branches "
            "must be verified.")
    recs.append(
        "Apply the emitted JSON templates MANUALLY (RAM console role trust "
        "policy / permission policy, OSS console Bucket Policy); this "
        "skill is read-only and never applies authorization changes. After "
        "a trust-policy fix, replication picks it up automatically on the "
        "next attempt -- no need to re-submit the replication rule.")
    recs.append(
        "Verify the assumed credential is actually used by the client "
        "(AssumeRole -> use the STS AccessKeyId/Secret/SecurityToken "
        "together); continuing with the original long-lived AK keeps the "
        "cross-account AccessDenied.")
    return recs


assert any("does NOT own" in r for r in build_recommendations(
    "access", "cross_account", "not_configured", "missing",
    attribute_no_permission(None)))  # normal: cross-account + no policy
assert any("DUAL grant" in r for r in build_recommendations(
    "replication", "same_account", "present", "ok",
    attribute_no_permission(True)))  # normal: replication branch
assert isinstance(build_recommendations(
    "migration", "unknown", "unknown", "unknown", {}), list)  # invalid: all unknown
assert any("MANUALLY" in r for r in build_recommendations(
    "all", "unknown", "not_configured", "missing", {}))  # boundary: read-only reminder


# ---------------------------------------------------------------------------
# RAM 403 localization main path (G3-5): EncodedDiagnosticMessage extraction,
# AccessDeniedDetail interpretation and decoded-diagnostic interpretation.
# Official sources (verified 2026-09-07):
#   * help.aliyun.com/zh/oss/user-guide/0003-00000201 (OSS 403 XML carrying
#     <AccessDeniedDetail> + <EncodedDiagnosticMessage>; RAM diagnosis page)
#   * help.aliyun.com/zh/ram/support/how-to-troubleshoot-an-access-denied-error
#     (the official 4-step interpretation + OpenAPI AccessDeniedDetail shape)
#   * RAM DecodeDiagnosticMessage (Ram/2015-05-01) response schema
#     (DecodedDiagnosticMessage: ExplicitDeny / NoPermissionPolicyType /
#      AuthAction / AuthResource / AuthPrincipal / AuthConditions /
#      MatchedPolicies)
# ---------------------------------------------------------------------------

# Official RAM permission-diagnosis console page (paste the
# EncodedDiagnosticMessage here; requires ram:DecodeDiagnosticMessage).
_RAM_DIAGNOSIS_CONSOLE_URL = "https://ram.console.aliyun.com/permissions/troubleshoot"
# OpenAPI Explorer debug page for the decode API (alternative manual decode).
_RAM_DECODE_OPENAPI_URL = (
    "https://api.aliyun.com/api/Ram/2015-05-01/DecodeDiagnosticMessage")
_RAM_TROUBLESHOOT_DOC = (
    "https://help.aliyun.com/zh/ram/support/how-to-troubleshoot-an-access-denied-error")

# Official NoPermissionPolicyType -> fix-direction mapping (verbatim semantics
# from the RAM access-denied troubleshooting doc). Enum values are
# case-sensitive PascalCase; only whitespace is trimmed.
_POLICY_TYPE_FIX = {
    "ControlPolicy": (
        "denied by a resource-directory CONTROL POLICY (a permission boundary "
        "set by the enterprise's resource-directory management account, higher "
        "priority than in-account judgments): contact the resource-directory "
        "management account to grant the action"),
    "SessionPolicy": (
        "denied by the SESSION POLICY attached at AssumeRole: ask the account "
        "administrator to check the session policy passed to the AssumeRole "
        "call"),
    "AssumeRolePolicy": (
        "denied by the role TRUST POLICY (AssumeRolePolicy): ask the account "
        "administrator to check the trust policy of the assumed RAM role"),
    "AccountLevelIdentityBasedPolicy": (
        "denied by an ACCOUNT-LEVEL IDENTITY-BASED policy (a RAM policy "
        "attached to the caller identity): ask the account administrator to "
        "check the permission policies attached to the caller RAM user / role"),
    "ResourceGroupLevelIdentityBasedPolicy": (
        "denied by a RESOURCE-GROUP-LEVEL identity-based policy: ask the "
        "account administrator to check the permission policies scoped to the "
        "resource group"),
}

# Identity-based (RAM-policy-side) policy types -- a deny attributed to one of
# these is NOT a Bucket-Policy decision, even when the Message text says so.
_IDENTITY_POLICY_TYPES = frozenset({
    "AccountLevelIdentityBasedPolicy",
    "ResourceGroupLevelIdentityBasedPolicy",
})
# OSS EC codes that mean a RAM-Policy-side deny / not-authorized (NOT a Bucket
# Policy deny, which is 0003-00000101): see references/auth-config-templates.md
# section 6.5.
_RAM_SIDE_EC = frozenset({"0003-00000201", "0003-00000202", "0003-00000203"})

_ACCESS_DENIED_DETAIL_RE = re.compile(
    r"<AccessDeniedDetail>(.*?)</AccessDeniedDetail>", re.S)


def _xml_tag(block: str, tag: str) -> str:
    """Extract the trimmed text of the first <tag>...</tag> in block."""
    m = re.search(r"<%s>\s*(.*?)\s*</%s>" % (re.escape(tag), re.escape(tag)),
                  block or "", re.S)
    return m.group(1).strip() if m else ""


def extract_access_denied_detail(text: str) -> dict:
    """Parse a 403 AccessDenied response body (OSS XML or POP-gateway JSON) and
    pull out the AccessDeniedDetail fields plus the top-level Code / Message /
    EC / RequestId.

    Handles BOTH shapes (never raises; unrecognized/empty input yields an
    all-empty dict with source=""):
      * OSS XML: <Error><Code>..<Message>..<EC>..<AccessDeniedDetail>
        <PolicyType>..<AuthAction>..<NoPermissionType>..
        <EncodedDiagnosticMessage>..</AccessDeniedDetail></Error>
      * POP JSON: {"Code":..,"Message":..,"EC":..,
        "AccessDeniedDetail":{"PolicyType":..,"AuthAction":..,
        "NoPermissionType":..,"EncodedDiagnosticMessage":..}}
    """
    out = {
        "code": "", "message": "", "request_id": "", "ec": "",
        "recommend_doc": "", "policy_type": "", "auth_action": "",
        "no_permission_type": "", "auth_principal_type": "",
        "auth_principal_display_name": "", "auth_principal_owner_id": "",
        "encoded_diagnostic_message": "", "source": "",
    }
    text = text or ""
    if not text.strip():
        return out
    m = _ACCESS_DENIED_DETAIL_RE.search(text)
    if m:
        block = m.group(1)
        out["source"] = "xml"
        out["policy_type"] = _xml_tag(block, "PolicyType")
        out["auth_principal_owner_id"] = _xml_tag(block, "AuthPrincipalOwnerId")
        out["auth_principal_type"] = _xml_tag(block, "AuthPrincipalType")
        out["auth_principal_display_name"] = _xml_tag(
            block, "AuthPrincipalDisplayName")
        out["no_permission_type"] = _xml_tag(block, "NoPermissionType")
        out["auth_action"] = _xml_tag(block, "AuthAction")
        out["encoded_diagnostic_message"] = _xml_tag(
            block, "EncodedDiagnosticMessage")
        out["code"] = _xml_tag(text, "Code")
        out["message"] = _xml_tag(text, "Message")
        out["request_id"] = _xml_tag(text, "RequestId")
        out["ec"] = _xml_tag(text, "EC")
        out["recommend_doc"] = _xml_tag(text, "RecommendDoc")
        return out
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return out
        if isinstance(data, dict):
            out["source"] = "json"
            out["code"] = str(data.get("Code") or "")
            out["message"] = str(data.get("Message") or "")
            out["request_id"] = str(data.get("RequestId") or "")
            out["ec"] = str(data.get("EC") or data.get("Ec") or "")
            add = data.get("AccessDeniedDetail")
            if isinstance(add, dict):
                out["policy_type"] = str(add.get("PolicyType") or "")
                out["auth_action"] = str(add.get("AuthAction") or "")
                out["no_permission_type"] = str(add.get("NoPermissionType") or "")
                out["auth_principal_type"] = str(
                    add.get("AuthPrincipalType") or "")
                out["auth_principal_display_name"] = str(
                    add.get("AuthPrincipalDisplayName") or "")
                out["auth_principal_owner_id"] = str(
                    add.get("AuthPrincipalOwnerId") or "")
                out["encoded_diagnostic_message"] = str(
                    add.get("EncodedDiagnosticMessage") or "")
    return out


# Official 0003-00000201 XML example: Message misleadingly says "Access denied
# by bucket policy." while EC=0003-00000201 + PolicyType=
# AccountLevelIdentityBasedPolicy prove a RAM identity-policy-side deny.
_OSS_403_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Error>\n'
    '  <Code>AccessDenied</Code>\n'
    '  <Message>Access denied by bucket policy.</Message>\n'
    '  <RequestId>65AF50375347E6D09</RequestId>\n'
    '  <HostId>mybucket.oss-cn-hangzhou.aliyuncs.com</HostId>\n'
    '  <AccessDeniedDetail>\n'
    '    <PolicyType>AccountLevelIdentityBasedPolicy</PolicyType>\n'
    '    <AuthPrincipalOwnerId>103232056</AuthPrincipalOwnerId>\n'
    '    <AuthPrincipalType>SubUser</AuthPrincipalType>\n'
    '    <AuthPrincipalDisplayName>2058754611</AuthPrincipalDisplayName>\n'
    '    <NoPermissionType>ExplicitDeny</NoPermissionType>\n'
    '    <AuthAction>oss:PutBucketReferer</AuthAction>\n'
    '    <EncodedDiagnosticMessage>AQIBIAAAACB1EXAMPLE==</EncodedDiagnosticMessage>\n'
    '  </AccessDeniedDetail>\n'
    '  <EC>0003-00000201</EC>\n'
    '  <RecommendDoc>https://api.aliyun.com/troubleshoot?q=0003-00000201</RecommendDoc>\n'
    '</Error>\n')
_d = extract_access_denied_detail(_OSS_403_XML)
assert _d["source"] == "xml" and _d["ec"] == "0003-00000201"  # normal: XML top-level
assert _d["auth_action"] == "oss:PutBucketReferer"  # normal: detail action
assert _d["policy_type"] == "AccountLevelIdentityBasedPolicy"  # normal: policy layer
assert _d["no_permission_type"] == "ExplicitDeny"  # normal: deny kind
assert _d["encoded_diagnostic_message"] == "AQIBIAAAACB1EXAMPLE=="  # normal: encoded msg
_dj = extract_access_denied_detail(
    '{"Code":"NoPermission","EC":"0003-00000202",'
    '"AccessDeniedDetail":{"PolicyType":"ControlPolicy",'
    '"AuthAction":"oss:GetObject","NoPermissionType":"ImplicitDeny",'
    '"EncodedDiagnosticMessage":"AQIBx=="}}')
assert _dj["source"] == "json" and _dj["policy_type"] == "ControlPolicy"  # boundary: JSON shape
assert _dj["ec"] == "0003-00000202" and _dj["auth_action"] == "oss:GetObject"  # boundary
assert extract_access_denied_detail("")["source"] == ""  # invalid: empty
assert extract_access_denied_detail("not-an-error-body")["source"] == ""  # invalid: garbage
assert extract_access_denied_detail("{broken json")["source"] == ""  # invalid: malformed JSON


def policy_type_fix_direction(policy_type: str) -> str:
    """Map an official NoPermissionPolicyType / PolicyType enum value to the
    fix direction (verbatim semantics from the RAM access-denied doc). Unknown
    or empty -> "" (never fabricate a layer)."""
    return _POLICY_TYPE_FIX.get((policy_type or "").strip(), "")


assert "IDENTITY-BASED" in policy_type_fix_direction(
    "AccountLevelIdentityBasedPolicy")  # normal
assert "CONTROL POLICY" in policy_type_fix_direction("ControlPolicy")  # normal
assert "TRUST POLICY" in policy_type_fix_direction("AssumeRolePolicy")  # boundary: trust layer
assert "SESSION POLICY" in policy_type_fix_direction("  SessionPolicy  ")  # boundary: whitespace
assert policy_type_fix_direction("") == ""  # invalid: empty
assert policy_type_fix_direction("BogusType") == ""  # invalid: unknown enum


def interpret_access_denied_detail(detail: dict) -> dict:
    """Apply the OFFICIAL 4-step interpretation to the PLAIN AccessDeniedDetail
    fields -- this needs NO decode and NO extra permission, so it works even
    when the credential lacks ram:DecodeDiagnosticMessage.

    Steps (official RAM access-denied doc): (1) who = AuthPrincipal*; (2) the
    missing/denied action = AuthAction; (3) which policy layer = PolicyType ->
    fix direction; (4) deny kind = NoPermissionType (ExplicitDeny -> remove the
    Deny; ImplicitDeny -> add an Allow). Also detects the Message/EC trap: when
    the Message text blames a "bucket policy" but EC / PolicyType prove a
    RAM-side decision, trust EC + PolicyType, never the Message wording.
    """
    detail = detail or {}
    action = str(detail.get("auth_action") or "").strip()
    ptype = str(detail.get("policy_type") or "").strip()
    nptype = str(detail.get("no_permission_type") or "").strip()
    ec = str(detail.get("ec") or "").strip()
    message = str(detail.get("message") or "").strip()
    out = {
        "missing_action": action,
        "policy_layer": ptype,
        "policy_layer_fix": policy_type_fix_direction(ptype),
        "deny_kind": nptype,
        "deny_kind_fix": "",
        "message_ec_trap": "",
        "principal": {
            "type": str(detail.get("auth_principal_type") or ""),
            "owner_id": str(detail.get("auth_principal_owner_id") or ""),
            "display_name": str(detail.get("auth_principal_display_name") or ""),
        },
        "has_encoded_message": bool(
            str(detail.get("encoded_diagnostic_message") or "").strip()),
    }
    if not any([action, ptype, nptype, ec]):
        return out  # nothing to interpret (empty/unrecognized detail)
    if nptype == "ExplicitDeny":
        out["deny_kind_fix"] = (
            "the action is EXPLICITLY denied: an explicit Deny always wins "
            "over every Allow, so adding more Allow statements CANNOT fix it "
            "-- find and remove/narrow the Deny statement covering "
            f"{action or 'the action'}")
    elif nptype == "ImplicitDeny":
        out["deny_kind_fix"] = (
            "the action is NOT explicitly authorized (implicit deny): the "
            "account administrator must ADD an Allow statement for "
            f"{action or 'the action'} on the layer named by policy_layer")
    low_msg = message.lower()
    ram_side = (ec in _RAM_SIDE_EC) or (ptype in _IDENTITY_POLICY_TYPES)
    if "bucket policy" in low_msg and ram_side:
        out["message_ec_trap"] = (
            f'TRAP: the response Message says "{message}" but '
            + (f"EC={ec} " if ec else "")
            + (f"and PolicyType={ptype} " if ptype else "")
            + "point to a RAM identity-policy-side decision, NOT a Bucket "
            "Policy. Per the official 0003-00000201 example the Message text "
            "is misleading -- attribute the deny by EC + PolicyType (and the "
            "decoded MatchedPolicies), never by the Message wording.")
    return out


_i = interpret_access_denied_detail(_d)
assert _i["deny_kind"] == "ExplicitDeny" and "CANNOT fix it" in _i["deny_kind_fix"]  # normal
assert _i["message_ec_trap"] and "TRAP" in _i["message_ec_trap"]  # normal: Message/EC trap fires
assert "IDENTITY-BASED" in _i["policy_layer_fix"]  # normal: layer fix
assert _i["missing_action"] == "oss:PutBucketReferer"  # normal: action carried
_ij = interpret_access_denied_detail(_dj)
assert _ij["deny_kind"] == "ImplicitDeny" and "ADD an Allow" in _ij["deny_kind_fix"]  # boundary: implicit
assert _ij["message_ec_trap"] == ""  # boundary: no misleading Message -> no trap
# boundary: Message blames bucket policy AND it really is a bucket-policy deny
_bp = interpret_access_denied_detail({
    "message": "Access denied by bucket policy.", "ec": "0003-00000101",
    "policy_type": "", "no_permission_type": "", "auth_action": ""})
assert _bp["message_ec_trap"] == ""  # boundary: EC 0003-00000101 is bucket-policy-side -> no trap
_e = interpret_access_denied_detail({})
assert _e["missing_action"] == "" and _e["deny_kind_fix"] == ""  # invalid: empty detail
assert interpret_access_denied_detail(None)["message_ec_trap"] == ""  # invalid: None


def interpret_decoded_diagnostic(decoded: dict) -> dict:
    """Interpret the DecodedDiagnosticMessage returned by
    ram:DecodeDiagnosticMessage (the decode of an EncodedDiagnosticMessage).

    Official RAM 2015-05-01 schema: ExplicitDeny (bool),
    NoPermissionPolicyType (enum), AuthAction, AuthResource,
    AuthPrincipal{AuthPrincipalType, AuthPrincipalOwnerId,
    AuthPrincipalDisplayName}, AuthConditions[{ConditionKey, ConditionValues}],
    MatchedPolicies[{Effect, PolicyIdentifier, PolicyType, PolicyVersion,
    AttachedEntityType, AttachedScope}]. Never raises; empty input -> an
    all-empty result with a generic fix_direction.
    """
    decoded = decoded or {}
    ptype = str(decoded.get("NoPermissionPolicyType") or "")
    out = {
        "explicit_deny": bool(decoded.get("ExplicitDeny")),
        "missing_action": str(decoded.get("AuthAction") or ""),
        "missing_resource": str(decoded.get("AuthResource") or ""),
        "policy_layer": ptype,
        "policy_layer_fix": policy_type_fix_direction(ptype),
        "principal": {},
        "conditions": [],
        "deny_policies": [],
        "fix_direction": "",
    }
    principal = decoded.get("AuthPrincipal")
    if isinstance(principal, dict):
        out["principal"] = {
            "type": str(principal.get("AuthPrincipalType") or ""),
            "owner_id": str(principal.get("AuthPrincipalOwnerId") or ""),
            "display_name": str(principal.get("AuthPrincipalDisplayName") or ""),
        }
    conds = decoded.get("AuthConditions")
    if isinstance(conds, list):
        for c in conds:
            if isinstance(c, dict):
                out["conditions"].append({
                    "key": str(c.get("ConditionKey") or ""),
                    "values": [str(v) for v in (c.get("ConditionValues") or [])],
                })
    matched = decoded.get("MatchedPolicies")
    if isinstance(matched, list):
        for p in matched:
            if isinstance(p, dict) and str(p.get("Effect") or "") == "Deny":
                out["deny_policies"].append({
                    "policy": str(p.get("PolicyIdentifier") or ""),
                    "policy_type": str(p.get("PolicyType") or ""),
                    "version": str(p.get("PolicyVersion") or ""),
                    "attached_to": str(p.get("AttachedEntityType") or ""),
                    "scope": str(p.get("AttachedScope") or ""),
                })
    if out["explicit_deny"]:
        out["fix_direction"] = (
            "EXPLICIT deny: remove/narrow the Deny statement in the matched "
            "policy(ies) listed in deny_policies (quote them in the answer); "
            "adding Allow statements cannot fix an explicit Deny")
    else:
        out["fix_direction"] = (
            "NOT explicitly authorized (implicit deny): add an Allow for "
            "missing_action on missing_resource at the layer named by "
            "policy_layer")
    return out


_dec = interpret_decoded_diagnostic({
    "ExplicitDeny": True, "NoPermissionPolicyType": "AccountLevelIdentityBasedPolicy",
    "AuthAction": "oss:GetObject", "AuthResource": "acs:oss:*:1552:bkt/obj",
    "AuthPrincipal": {"AuthPrincipalType": "AssumedRoleUser",
                      "AuthPrincipalOwnerId": "1552974654746705",
                      "AuthPrincipalDisplayName": "role:sess"},
    "AuthConditions": [{"ConditionKey": "acs:SourceIp",
                        "ConditionValues": ["1.2.3.4"]}],
    "MatchedPolicies": [{"Effect": "Deny", "PolicyIdentifier": "MyDenyPolicy",
                         "PolicyType": "Custom", "PolicyVersion": "v1",
                         "AttachedEntityType": "RamUser",
                         "AttachedScope": "Account"},
                        {"Effect": "Allow", "PolicyIdentifier": "AnAllow",
                         "PolicyType": "System"}],
})
assert _dec["explicit_deny"] is True and "EXPLICIT" in _dec["fix_direction"]  # normal
assert len(_dec["deny_policies"]) == 1  # normal: only the Deny policy is carried
assert _dec["deny_policies"][0]["policy"] == "MyDenyPolicy"  # normal: identifier quoted
assert _dec["missing_resource"] == "acs:oss:*:1552:bkt/obj"  # normal: resource
assert _dec["conditions"][0]["key"] == "acs:SourceIp"  # normal: condition key
assert _dec["principal"]["type"] == "AssumedRoleUser"  # normal: principal
_dec2 = interpret_decoded_diagnostic({"ExplicitDeny": False,
                                      "AuthAction": "oss:PutObject"})
assert _dec2["explicit_deny"] is False and "implicit" in _dec2["fix_direction"]  # boundary: implicit
assert _dec2["deny_policies"] == [] and _dec2["conditions"] == []  # boundary: no lists
assert _dec2["principal"] == {}  # boundary: no principal block
_dec3 = interpret_decoded_diagnostic({})
assert _dec3["missing_action"] == "" and _dec3["explicit_deny"] is False  # invalid: empty
assert interpret_decoded_diagnostic(None)["deny_policies"] == []  # invalid: None


def manual_decode_guidance() -> dict:
    """Official guidance for decoding an EncodedDiagnosticMessage when the
    current credential LACKS ram:DecodeDiagnosticMessage (the measured state
    for the evaluation role). Constant builder -- the skill never fabricates a
    console menu path; it cites the verified page URLs only."""
    return {
        "required_permission": "ram:DecodeDiagnosticMessage",
        "ram_permission_diagnosis_page": _RAM_DIAGNOSIS_CONSOLE_URL,
        "openapi_explorer_decode": _RAM_DECODE_OPENAPI_URL,
        "official_doc": _RAM_TROUBLESHOOT_DOC,
        "steps": [
            "Paste the EncodedDiagnosticMessage into the RAM "
            "permission-diagnosis page (ram_permission_diagnosis_page); this "
            "requires the account to hold ram:DecodeDiagnosticMessage.",
            "If the current credential lacks that permission (the official "
            "'lack-diagnosis-permission' branch), hand the "
            "EncodedDiagnosticMessage to an account ADMINISTRATOR who holds "
            "it and have them open the same page, then apply the authorization "
            "fix the diagnosis names.",
            "Alternatively decode via OpenAPI Explorer "
            "(openapi_explorer_decode) with a credential that has the "
            "permission.",
        ],
    }


assert manual_decode_guidance()["required_permission"] == "ram:DecodeDiagnosticMessage"
assert _RAM_DIAGNOSIS_CONSOLE_URL in manual_decode_guidance()[
    "ram_permission_diagnosis_page"]  # normal: verified URL cited
assert len(manual_decode_guidance()["steps"]) >= 2  # boundary: admin-handoff step present


# ---------------------------------------------------------------------------
# Diagnosis orchestration
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Official-doc verification hook (runtime doc lookup, batch-3 integration)
# ---------------------------------------------------------------------------

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


def _emit(report: dict, status: str, next_action: str) -> int:
    """Print the structured report + STATUS/NEXT_ACTION contract lines."""
    report["status"] = status
    report["next_action"] = next_action
    dv = _doc_verification(status)
    if dv is not None:
        report["doc_verification"] = dv
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Diagnose OSS cross-account access / replication / "
                    "migration authorization failures and emit authorization "
                    "templates (read-only; never applies any change)",
    )
    parser.add_argument("--bucket", default="", required=False,
                        help="OSS bucket name to diagnose (required; when absent the script emits FAIL and asks)")
    parser.add_argument("--scenario", default="all",
                        choices=_VALID_SCENARIOS,
                        help="access = cross-account access failure; "
                             "replication = cross-account replication "
                             "NoPermission; migration = cross-account "
                             "migration authorization; all (default)")
    parser.add_argument("--peer-uid", default="",
                        help="The other account's UID (optional; used to "
                             "verify the Bucket Policy Principal list and "
                             "to fill the cross-account trust policy)")
    parser.add_argument("--role-name", default="",
                        help="The replication/migration RAM role name "
                             "(optional; used in the assumed-role "
                             "Principal checks and templates)")
    parser.add_argument("--region", default="",
                        help="Expected region (optional; used to build the "
                             "query endpoint)")
    parser.add_argument("--question", default="",
                        help="Customer's original wording (optional); when "
                             "provided, the report carries a doc_verification "
                             "section matched against official OSS docs")
    parser.add_argument("--encoded-diagnostic-message", default="",
                        help="The EncodedDiagnosticMessage copied from a 403 "
                             "AccessDeniedDetail, OR the whole 403 error body "
                             "(OSS XML / POP JSON) that carries it (optional). "
                             "When provided the report adds a ram_403_diagnosis "
                             "section: the plain AccessDeniedDetail fields are "
                             "interpreted with the official 4-step method, and "
                             "the message is decoded via "
                             "ram:DecodeDiagnosticMessage -- degrading to the "
                             "official manual-decode guidance (RAM "
                             "permission-diagnosis page / administrator "
                             "handoff) when the credential lacks that "
                             "permission")
    args = parser.parse_args()

    # UA-SKILL-VERSION: resolve and validate the skill version from
    # references/manifest.json BEFORE the first cloud call of this run. The
    # version is never invented, guessed or reused -- a missing or invalid
    # manifest stops the run (STATUS: FAIL, exit 1) with no cloud call made.
    try:
        _oss_client.skill_version()
    except _oss_client.SkillVersionError as _e:
        print(f"[WARN] skill version unavailable: {_e}", file=sys.stderr)
        print(json.dumps({
            "skill": "alibabacloud-oss-cross-account-auth-diagnosis",
            "status": "FAIL",
            "errors": [{"category": "invalid_arguments",
                        "code": "SkillVersionUnavailable",
                        "message": str(_e)[:200]}],
        }, ensure_ascii=False, indent=2))
        print("STATUS: FAIL")
        print("NEXT_ACTION: Fix this skill's references/manifest.json (a valid "
              "`version` field is required to build the User-Agent); no cloud "
              "call was made and no conclusion can be drawn without it.")
        sys.exit(1)

    # Missing-bucket guard: most real tickets never name a bucket, so a bare
    # argparse exit 2 leaves the customer with no next step. Ask for the name
    # and surface the buckets this credential can actually see.
    if not (args.bucket or "").strip():
        _hint = []
        _herrs = []
        try:
            try:
                _all = _oss_client.list_buckets()
            except TypeError:
                _all = _oss_client.list_buckets(prefix="")
            _hint = [b["name"] for b in _all][:30]
        except Exception as e:
            _herrs.append({"category": "degraded", "code": "ListBucketsFailed",
                           "message": str(e)[:200]})
            print(f"[WARN] ListBuckets bucket-name hint degraded: {e}",
                  file=sys.stderr)
        _rep = {
            "skill": globals().get("_SKILL_NAME", "alibabacloud-oss-cross-account-auth-diagnosis"),
            "bucket": "",
            "buckets_in_account": _hint,
            "errors": _herrs,
            "auto_filled": [],
        }
        _na = ("Ask the user which OSS bucket the issue concerns; "
               "buckets_in_account lists up to 30 buckets visible to the "
               "current credential.")
        if not _hint:
            _na += (" No bucket is listable with the current credential: ask "
                    "for the exact bucket name and its region instead.")
        return _emit(_rep, "FAIL", _na)
    global _CUSTOMER_QUESTION
    _CUSTOMER_QUESTION = args.question or ""

    auto_filled = []
    degraded_steps = 0

    # Step 1: identity pre-check / UID derivation (unconditional, degraded
    # with [WARN] on failure -- UID is only a traceability label and feeds
    # the ownership comparison).
    uid = _oss_client.resolve_uid()

    # Step 2: resolve the initial query endpoint.
    if args.region.strip():
        region = args.region.strip().lower()
        query_endpoint = f"oss-{region}.aliyuncs.com"
        auto_filled.append(f"query endpoint derived from --region: "
                           f"{query_endpoint}")
    else:
        query_endpoint = _DEFAULT_ENDPOINT
        auto_filled.append(
            f"query endpoint auto-defaulted to {query_endpoint} "
            "(no --region provided)")

    report = {
        "skill": "alibabacloud-oss-cross-account-auth-diagnosis",
        "bucket": args.bucket,
        "scenario": args.scenario,
        "peer_uid": args.peer_uid or None,
        "role_name": args.role_name or None,
        "identity": {"uid": uid,
                     "note": "derived via sts get-caller-identity (aliyun "
                             "CLI default credential chain); empty means "
                             "the identity pre-check degraded. The bucket "
                             "owner side of the ownership relation always "
                             "comes from GetBucketInfo owner_id "
                             "(data-plane credential)."},
        "query_endpoint": query_endpoint,
        "auto_filled": auto_filled,
        "bucket_info": None,
        "ownership": None,
        "bucket_policy": None,
        "policy_check": None,
        "attribution": None,
        "ram_403_diagnosis": None,
        "templates": {},
        "assume_role_failure_routes": [],
        "recommendations": [],
        "errors": [],
    }

    # Step 3: GetBucketInfo -- core evidence call (ownership + location).
    bucket_info = None
    oss_403_detail = None  # AccessDeniedDetail parsed from a 403 body (G3-5)
    try:
        bucket_info = _oss_client.get_bucket_info(args.bucket, query_endpoint)
        report["bucket_info"] = bucket_info
    except OssClientError as e:
        degraded_steps += 1
        print(f"[WARN] GetBucketInfo degraded ({e.category}): {e}",
              file=sys.stderr)
        report["errors"].append(e.to_dict())
        # G3-5: a 403 body carries <AccessDeniedDetail> (PolicyType /
        # NoPermissionType / AuthAction / EncodedDiagnosticMessage) + the OSS
        # EC code -- capture them for the RAM 403 localization section below.
        if e.category == "permission" and (e.body or e.ec):
            oss_403_detail = extract_access_denied_detail(e.body)
            if not oss_403_detail.get("ec") and e.ec:
                oss_403_detail["ec"] = e.ec
            if not oss_403_detail.get("source") and e.ec:
                oss_403_detail["source"] = "ec-only"
        # Fallback: ListBuckets prefix lookup to locate the bucket region.
        try:
            located = _oss_client.list_buckets(prefix=args.bucket)
            hits = [b for b in located if b["name"] == args.bucket]
            if hits:
                report["bucket_info"] = {
                    "name": hits[0]["name"],
                    "location": hits[0]["location"],
                    "source": "ListBuckets fallback (GetBucketInfo degraded)",
                }
                bucket_info = report["bucket_info"]
            elif located is not None:
                report["errors"].append({
                    "category": "not_found",
                    "code": "ListBucketsNoMatch",
                    "message": f"ListBuckets(prefix={args.bucket}) returned "
                               f"{len(located)} bucket(s), none named "
                               f"'{args.bucket}' in this account -- a "
                               "cross-account bucket is invisible to "
                               "ListBuckets of a non-owning account",
                })
        except OssClientError as e2:
            degraded_steps += 1
            print(f"[WARN] ListBuckets fallback degraded ({e2.category}): {e2}",
                  file=sys.stderr)
            report["errors"].append(e2.to_dict())

    # Use the bucket's real location for subsequent metadata calls.
    if bucket_info and bucket_info.get("location"):
        located_endpoint = endpoint_from_location(bucket_info["location"])
        if located_endpoint and located_endpoint != query_endpoint:
            auto_filled.append(
                f"query endpoint re-derived from bucket location "
                f"{bucket_info['location']}: {located_endpoint}")
            query_endpoint = located_endpoint
            report["query_endpoint"] = query_endpoint

    have_bucket = bucket_info is not None

    # Ownership relation: caller UID vs bucket owner UID.
    # F-1 guard: the bucket side is anchored on GetBucketInfo owner_id
    # (data-plane credential); when the CLI identity UID differs AND the
    # data-plane credential is supplied via ALIBABA_CLOUD_* env vars, a
    # cross_account verdict may be an identity-chain skew, so surface a
    # [WARN] and annotate the relation.
    owner_id = str((bucket_info or {}).get("owner_id") or "")
    ownership = ownership_relation(uid, owner_id)
    caveat = ownership_identity_caveat(uid, owner_id)
    if caveat and os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip():
        print(f"[WARN] identity consistency: caller UID {uid} (aliyun CLI "
              f"default profile) differs from the bucket owner UID "
              f"{owner_id} (GetBucketInfo via the data-plane credential); "
              f"{caveat}.",
              file=sys.stderr)
    report["ownership"] = {
        "caller_uid": uid or None,
        "bucket_owner_uid": owner_id or None,
        "relation": ownership,
        "note": "for an assumed-role STS credential the caller UID is the "
                "account owning the role; compare main-account UIDs, a "
                "RAM-user UID differing from the main-account UID does NOT "
                "by itself mean cross-account"
                + (f"; CAVEAT: {caveat}" if caveat else ""),
    }
    # CAA-4: explicit account-scope statement on every report (forensics
    # precedent) -- conclusions are visibility-scoped to the current
    # credential's account, an empty/not_configured result is not absolute.
    report["account_scope"] = account_scope_note(uid)

    # Step 4: GetBucketPolicy -- existence + static sanity check (optional,
    # degraded with [WARN]; NoSuchBucketPolicy is the measured
    # "not configured" fact, not an error).
    policy_state = None
    policy_str = ""
    if have_bucket:
        try:
            pres = _oss_client.get_bucket_policy(args.bucket, query_endpoint)
            policy_str = pres.get("policy") or ""
            policy_state = normalize_policy_state(pres.get("state"))
            report["bucket_policy"] = {
                "state": policy_state,
                "policy_length": len(policy_str),
            }
        except OssClientError as e:
            degraded_steps += 1
            print(f"[WARN] GetBucketPolicy degraded ({e.category}): {e}",
                  file=sys.stderr)
            report["errors"].append(e.to_dict())
            policy_state = "unknown"
            report["bucket_policy"] = {"state": "unknown",
                                       "policy_length": 0}

    if policy_state is not None:
        pcheck = check_bucket_policy(policy_str, args.peer_uid,
                                     args.role_name)
        report["policy_check"] = pcheck
    policy_verdict = (report["policy_check"] or {}).get("verdict", "unknown")

    # Step 4.5: RAM 403 localization main path (G3-5). Interpret the plain
    # AccessDeniedDetail fields (official 4-step, needs NO decode and NO extra
    # permission) and, when an EncodedDiagnosticMessage is available, decode it
    # via ram:DecodeDiagnosticMessage -- degrading to the official manual-decode
    # guidance (RAM permission-diagnosis page / administrator handoff) when the
    # credential lacks that permission (the measured state for the eval role).
    edm_arg = (args.encoded_diagnostic_message or "").strip()
    detail = None
    encoded_message = ""
    detail_origin = ""
    if edm_arg:
        parsed = extract_access_denied_detail(edm_arg)
        if parsed.get("source"):
            detail = parsed
            encoded_message = parsed.get("encoded_diagnostic_message") or ""
            detail_origin = ("--encoded-diagnostic-message (parsed as a 403 "
                             "error body)")
        else:
            encoded_message = edm_arg
            detail_origin = "--encoded-diagnostic-message (bare encoded value)"
    elif oss_403_detail is not None:
        detail = oss_403_detail
        encoded_message = oss_403_detail.get("encoded_diagnostic_message") or ""
        detail_origin = ("extracted from the OSS GetBucketInfo 403 response "
                         "body")

    if detail is not None or encoded_message:
        ram_diag = {
            "origin": detail_origin,
            "access_denied_detail": detail or {},
            "interpretation": interpret_access_denied_detail(detail or {}),
            "decode": None,
            "decoded_interpretation": None,
            "manual_decode_guidance": None,
            "note": ("the plain AccessDeniedDetail fields (AuthAction / "
                     "PolicyType / NoPermissionType) already localize the deny "
                     "WITHOUT any decode and WITHOUT ram:DecodeDiagnosticMessage; "
                     "decoding adds AuthResource / AuthConditions / the exact "
                     "MatchedPolicies. Trust EC + PolicyType over the response "
                     "Message text. Conclusions reflect only the current "
                     "credential's account."),
        }
        if encoded_message:
            decode = _oss_client.decode_diagnostic_message(encoded_message)
            if decode.get("available"):
                ram_diag["decode"] = {
                    "available": True,
                    "request_id": decode.get("request_id", ""),
                }
                ram_diag["decoded_interpretation"] = (
                    interpret_decoded_diagnostic(decode.get("decoded") or {}))
            else:
                # Expected degradation (the eval role lacks the permission):
                # leave a [WARN] trace + the official manual-decode guidance.
                # This does NOT flip the core STATUS to DEGRADED -- the plain
                # AccessDeniedDetail interpretation already succeeded.
                print(f"[WARN] ram:DecodeDiagnosticMessage degraded "
                      f"({decode.get('reason')}): {decode.get('message')}",
                      file=sys.stderr)
                ram_diag["decode"] = {
                    "available": False,
                    "reason": decode.get("reason", ""),
                    "message": decode.get("message", ""),
                    "request_id": decode.get("request_id", ""),
                    "needs_permission": decode.get(
                        "needs_permission", "ram:DecodeDiagnosticMessage"),
                }
                ram_diag["manual_decode_guidance"] = manual_decode_guidance()
        report["ram_403_diagnosis"] = ram_diag

    # Step 5: attribution knowledge + templates per scenario.
    if args.scenario in ("replication", "migration", "all"):
        report["attribution"] = attribute_no_permission(None)
        report["assume_role_failure_routes"] = assume_role_failure_routes()

    templates = report["templates"]
    if args.scenario in ("access", "all"):
        t = trust_policy_template("account", args.peer_uid)
        templates["trust_policy_cross_account"] = t
        templates["cross_account_ram_policy"] = (
            cross_account_access_ram_policy_template(args.bucket))
    if args.scenario in ("replication", "migration", "all"):
        templates["trust_policy_oss_service"] = trust_policy_template(
            "service")
        templates["replication_ram_policy"] = replication_ram_policy_template(
            args.bucket)
        templates["replication_bucket_policy"] = (
            replication_bucket_policy_template(
                args.peer_uid, args.role_name, owner_id, args.bucket))

    # Step 6: recommendations from the collected evidence.
    report["recommendations"] = build_recommendations(
        args.scenario, ownership, policy_state or "unknown",
        policy_verdict, report["attribution"] or {})

    # Step 7: status + next action.
    if have_bucket:
        if degraded_steps:
            next_action = (
                "Diagnosis partially degraded: review the recorded [WARN] "
                "errors (permissions/endpoint/network), fix them, and "
                "re-run to complete the evidence set; the templates above "
                "remain valid for manual application.")
            sys.exit(_emit(report, "DEGRADED", next_action))
        if ownership == "cross_account":
            next_action = (
                "Cross-account situation confirmed (caller != bucket "
                "owner): the owning account must apply the emitted Bucket "
                "Policy / RAM role templates manually; this skill never "
                "applies changes.")
        elif policy_state == "not_configured" and args.scenario in (
                "access", "replication", "all"):
            next_action = (
                "No Bucket Policy on the bucket: for cross-account "
                "access/replication add the emitted Bucket Policy template "
                "on the owning account side, then retry the failing "
                "operation.")
        elif policy_verdict in ("gaps", "malformed"):
            next_action = (
                "The existing Bucket Policy has the findings listed in "
                "policy_check; re-create it from the emitted template and "
                "retry.")
        else:
            next_action = (
                "Bucket ownership and policy state verified; if the "
                "failing side is the peer account, apply the trust-policy "
                "and RAM-policy templates on that side (see "
                "recommendations), then retry.")
        sys.exit(_emit(report, "OK", next_action))

    # Degraded: no bucket info obtained -- attribute the root error.
    root = report["errors"][0] if report["errors"] else {"category": "unknown"}
    cat = root.get("category", "unknown")
    if cat == "not_found":
        next_action = (
            f"Bucket '{args.bucket}' was not found (NoSuchBucket) for this "
            "caller: either the name is misspelled or the bucket belongs "
            "to ANOTHER account (cross-account buckets are invisible to "
            "GetBucketInfo/ListBuckets of non-owners) -- confirm the "
            "owning account, then run this diagnosis from that account.")
    elif cat == "permission":
        next_action = (
            "Access denied (403): grant the caller oss:GetBucketInfo / "
            "oss:GetBucketPolicy / oss:ListBuckets (see "
            "references/ram-policies.md) or confirm the bucket belongs to "
            "this account, then re-run.")
        if report.get("ram_403_diagnosis"):
            next_action += (
                " The 403 body carried an AccessDeniedDetail: relay "
                "ram_403_diagnosis for the official EC/PolicyType "
                "attribution (trust EC + PolicyType over the Message text) "
                "and, when an EncodedDiagnosticMessage is present, the RAM "
                "permission-diagnosis decode path -- or the "
                "administrator-handoff guidance in manual_decode_guidance if "
                "this credential lacks ram:DecodeDiagnosticMessage.")
    elif cat == "endpoint":
        next_action = (
            "The request hit the wrong region's endpoint; re-run with "
            "--region of the region where the bucket was created.")
    elif cat == "network":
        next_action = (
            "Network/DNS failure reaching the endpoint host; verify the "
            "network and re-run -- never conclude 'no authorization' from "
            "a failed call.")
    elif cat == "credentials":
        next_action = (
            "No credentials in the environment credential chain; configure "
            "the default credential chain (aliyun configure / environment "
            "variables), never pass AK/SK manually.")
    else:
        next_action = (
            "OSS control-plane query failed; review the recorded errors "
            "and re-run after fixing the root cause.")
    sys.exit(_emit(report, "DEGRADED", next_action))


if __name__ == "__main__":
    sys.exit(main())
