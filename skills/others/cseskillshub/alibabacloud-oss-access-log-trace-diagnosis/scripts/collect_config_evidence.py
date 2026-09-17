#!/usr/bin/env python3
"""
collect_config_evidence.py -- Authorization evidence from the customer's own
===========================================================================
configuration
SECURITY: READ-ONLY. This script only reads bucket-level and object-level
configuration that the caller already owns or has been granted read access to.
It never reads, prints or stores credentials, and it never changes any
configuration. Credentials are resolved by the default credential chain inside
_oss_client (environment variables) and by the aliyun CLI for the RAM reads.

Purpose
-------
Turn "the request was denied" into "this statement, with these conditions,
matched these logged request attributes". Authorization decisions come from
several independent configuration layers, and a denial can only be explained by
reading all of them:

  unconditional evidence set:
    oss GetBucketInfo          - creation date, region, storage class, owner,
                                 versioning, redundancy, replication
    oss GetBucketAcl           - bucket ACL
    oss GetBucketPolicy        - the policy document, or proof that none exists
    oss GetPublicAccessBlock   - whether public access is blocked

  conditional evidence (reached only on a matching branch, therefore NOT
  declared in related_apis.yaml):
    oss GetBucketReferer       - hotlink whitelist AND blacklist
    oss GetObjectAcl           - per-object ACL override
    oss GetBucketWebsite       - static website index/error documents
    oss GetBucketLogging       - periodic log shipping configuration
    ram ListPoliciesForUser + GetPolicy - explicit Deny scan on the caller
    ram GetRole                - assumed-role trust relationship

Channel note: the OSS reads go through the oss2 SDK (the aliyun CLI carries no
OSS control-plane metadata), so their results are parsed objects rather than
raw XML. The RAM reads go through the aliyun CLI.

Every failure degrades: the field is marked unavailable with the reason, the
rest of the evidence is still collected, and the script exits 0.

Usage:
  python3 collect_config_evidence.py --bucket my-bucket --region cn-hangzhou
  python3 collect_config_evidence.py --bucket my-bucket --object images/a.png
  python3 collect_config_evidence.py --bucket my-bucket --with-referer --json
"""

from __future__ import annotations

import argparse
import json
import sys

import _cli
import _oss_client
from _constants import DEFAULT_TIMEOUT

# Actions whose "not configured" outcome is a positive finding.
OPTIONAL_CONFIG_ACTIONS = frozenset({
    "GetBucketPolicy", "GetBucketReferer", "GetBucketWebsite",
    "GetBucketLogging", "GetPublicAccessBlock",
})


def _warn(message: str) -> None:
    print(f"[WARN] {message}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Evidence collectors (adapter layer over _oss_client.read_config)
# ---------------------------------------------------------------------------

def collect(action: str, bucket: str, region: str,
            profile: str | None = None, extra: dict | None = None,
            tolerate: tuple[str, ...] = (),
            endpoint: str = "") -> dict:
    """Run one OSS read and normalize the outcome into a stable shape.

    The returned dict always carries the same keys so downstream rules and the
    JSON contract never depend on which read succeeded:
      available, configured, action, data,
      error_code, error_category, error_message, error_hint
    """
    key = (extra or {}).get("key", "")
    result = _oss_client.read_config(action, bucket, region,
                                    endpoint=endpoint, key=key,
                                    timeout=DEFAULT_TIMEOUT)
    error = result.get("error") or {}
    data = result.get("data") or {}
    available = bool(result.get("available"))
    configured = bool(result.get("configured"))

    if not available and error:
        _warn(f"oss {action} unavailable [{error.get('category')}]: "
              f"{error.get('code') or error.get('message')}")

    out = {
        "available": available,
        "configured": configured,
        "action": action,
        "data": data,
        "error_code": error.get("code", ""),
        "error_category": error.get("category", ""),
        "error_message": error.get("message", ""),
        "error_hint": error.get("hint", ""),
    }
    if action == "GetBucketPolicy":
        # Expose the parsed document under the key the rule engine consumes.
        out["policy"] = data.get("document") or {}
        out["statement_count"] = int(data.get("statement_count") or 0)
        out["deny_count"] = int(data.get("deny_count") or 0)
        out["raw"] = data.get("raw", "")
        if available and not configured:
            out["finding"] = (
                "No bucket policy is configured. A 'not configured' result on "
                "this read is expected and is NOT a permission failure.")
    return out


def collect_bucket_policy(bucket: str, region: str,
                          profile: str | None = None,
                          endpoint: str = "") -> dict:
    """Read the bucket policy; the document is parsed by _oss_client."""
    return collect("GetBucketPolicy", bucket, region, profile=profile,
                   endpoint=endpoint)


def collect_ram_evidence(caller_id: str, role_name: str, region: str,
                         profile: str | None) -> dict:
    """Conditional RAM evidence: explicit-Deny scan and role trust policy.

    Reached only when the denial points at a RAM identity policy or an assumed
    role. These calls go through the aliyun CLI (a POP channel) and are
    intentionally absent from related_apis.yaml because they are conditional.
    """
    evidence: dict = {"queried": False, "policies": [], "role": {},
                      "trust_policy": {}, "oss_service_trusted": None,
                      "deny_statements": [], "errors": []}
    if not caller_id and not role_name:
        return evidence
    evidence["queried"] = True

    if caller_id:
        try:
            body = _cli.call("ram", "ListPoliciesForUser",
                             {"UserName": caller_id}, region=region,
                             profile=profile, timeout=DEFAULT_TIMEOUT)
            policies = (body.get("Policies") or {}).get("Policy") or []
            if isinstance(policies, dict):
                policies = [policies]
            evidence["policies"] = policies
            for policy in policies:
                name = policy.get("PolicyName")
                ptype = policy.get("PolicyType", "Custom")
                if not name:
                    continue
                try:
                    detail = _cli.call(
                        "ram", "GetPolicy",
                        {"PolicyName": name, "PolicyType": ptype},
                        region=region, profile=profile,
                        timeout=DEFAULT_TIMEOUT)
                except _cli.CliError as e:
                    evidence["errors"].append(f"GetPolicy {name}: {e}")
                    continue
                document = ((detail.get("DefaultPolicyVersion") or {})
                            .get("PolicyDocument") or "")
                if not document:
                    continue
                parsed = document if isinstance(document, dict) else None
                if parsed is None:
                    try:
                        parsed = json.loads(document)
                    except (json.JSONDecodeError, TypeError):
                        continue
                for statement in (parsed or {}).get("Statement") or []:
                    if str(statement.get("Effect", "")).lower() == "deny":
                        evidence["deny_statements"].append({
                            "policy_name": name,
                            "policy_type": ptype,
                            "statement": statement,
                        })
        except _cli.CliError as e:
            _warn(f"ram ListPoliciesForUser failed: {e}")
            evidence["errors"].append(f"ListPoliciesForUser: {e}")

    if role_name:
        try:
            body = _cli.call("ram", "GetRole", {"RoleName": role_name},
                             region=region, profile=profile,
                             timeout=DEFAULT_TIMEOUT)
            role = body.get("Role") or {}
            evidence["role"] = role
            trust = role.get("AssumeRolePolicyDocument", "")
            if isinstance(trust, str) and trust.strip():
                try:
                    evidence["trust_policy"] = json.loads(trust)
                except json.JSONDecodeError:
                    evidence["trust_policy"] = {"_raw": trust[:1000]}
            elif isinstance(trust, dict):
                evidence["trust_policy"] = trust
            # The decisive question for replication-style denials: does the
            # trust relationship let the OSS service assume this role?
            services = json.dumps(evidence.get("trust_policy") or {})
            evidence["oss_service_trusted"] = "oss.aliyuncs.com" in services
        except _cli.CliError as e:
            _warn(f"ram GetRole failed: {e}")
            evidence["errors"].append(f"GetRole {role_name}: {e}")

    return evidence


# ---------------------------------------------------------------------------
# Derived facts (so the report states findings, not raw SDK objects)
# ---------------------------------------------------------------------------

def derive_facts(info: dict, acl: dict, policy: dict,
                 public_block: dict) -> dict:
    """Cross-correlate the unconditional evidence set into plain findings.

    Field names follow the oss2 result attributes verified against 2.19.1
    (snake_case), not the XML tag names of the raw API response.
    """
    facts: dict = {}
    d = info.get("data") or {}

    facts["bucket_name"] = d.get("name", "")
    facts["location"] = d.get("location", "")
    facts["region"] = d.get("region", "")
    facts["creation_date"] = d.get("creation_date", "")
    facts["storage_class"] = d.get("storage_class", "")
    facts["owner_id"] = d.get("owner_id", "")
    facts["owner_display_name"] = d.get("owner_display_name", "")
    facts["versioning"] = d.get("versioning_status", "")
    facts["data_redundancy_type"] = d.get("data_redundancy_type", "")
    facts["cross_region_replication"] = d.get("cross_region_replication", "")
    facts["transfer_acceleration"] = d.get("transfer_acceleration", "")
    facts["access_monitor"] = d.get("access_monitor", "")
    facts["extranet_endpoint"] = d.get("extranet_endpoint", "")
    facts["intranet_endpoint"] = d.get("intranet_endpoint", "")

    # GetBucketInfo already carries the ACL; the dedicated read is the fallback
    # and the cross-check.
    facts["bucket_acl"] = d.get("acl", "") or (acl.get("data") or {}).get("acl", "")
    facts["acl_source"] = ("GetBucketInfo" if d.get("acl")
                           else ("GetBucketAcl" if (acl.get("data") or {}).get("acl")
                                 else "unavailable"))

    facts["policy_available"] = bool(policy.get("available"))
    facts["policy_configured"] = bool(policy.get("statement_count"))
    facts["policy_statement_count"] = int(policy.get("statement_count") or 0)
    facts["policy_deny_count"] = int(policy.get("deny_count") or 0)
    statements = (policy.get("policy") or {}).get("Statement") or []
    if not isinstance(statements, list):
        statements = []
    facts["policy_allows_anonymous"] = any(
        isinstance(s, dict)
        and str(s.get("Effect", "")).lower() == "allow"
        and "*" in json.dumps(s.get("Principal") or "")
        for s in statements)

    block_value = (public_block.get("data") or {}).get("block_public_access")
    if block_value is None:
        block_value = False
    facts["block_public_access"] = bool(block_value)
    facts["block_public_access_available"] = bool(
        public_block.get("available"))

    # Cross-correlation: the combination is what decides anonymous reachability.
    facts["anonymous_read_possible"] = (
        facts["bucket_acl"] in ("public-read", "public-read-write")
        and not facts["block_public_access"]
    )
    facts["anonymous_list_possible"] = (
        facts["anonymous_read_possible"] and facts["policy_allows_anonymous"]
    )

    notes = []
    if not info.get("available"):
        notes.append(
            "Bucket information could not be read "
            f"({info.get('error_code') or info.get('error_category') or 'unknown'}), "
            "so creation date, region and versioning are unknown. Existence and "
            "ownership are therefore unconfirmed rather than disproved.")
    if facts["bucket_acl"] in ("public-read", "public-read-write"):
        notes.append(
            "Bucket ACL is public: anonymous reads are allowed by the ACL, but "
            "anonymous LISTING still requires a bucket policy statement, "
            "because neither public-read nor public-read-write grants it.")
    if facts["block_public_access"]:
        notes.append(
            "Block public access is ON: it overrides bucket ACL and object ACL, "
            "so a public-read setting will not make objects reachable.")
    if facts["policy_deny_count"]:
        notes.append(
            f"The bucket policy contains {facts['policy_deny_count']} Deny "
            f"statement(s). An explicit Deny outranks every Allow, including "
            f"any Allow in a RAM policy.")
    if info.get("available") and not facts["policy_configured"]:
        notes.append(
            "No bucket policy is configured, so no policy statement can be the "
            "cause of a denial on this bucket.")
    if facts["versioning"] and facts["versioning"] != "Suspended":
        notes.append(
            f"Versioning is '{facts['versioning']}': a removal writes a delete "
            f"marker instead of erasing data, and a request-level "
            f"do-not-overwrite header has no effect on this bucket.")
    facts["notes"] = notes
    return facts


def render_referer(referer: dict) -> dict:
    """Flatten the referer read into report-friendly fields."""
    if not referer or not referer.get("available"):
        return {}
    data = referer.get("data") or {}
    return {
        "configured": bool(referer.get("configured")),
        "allow_empty_referer": data.get("allow_empty_referer"),
        "allow_truncate_query_string": data.get("allow_truncate_query_string"),
        "whitelist_count": int(data.get("whitelist_count") or 0),
        "whitelist": list(data.get("whitelist") or [])[:50],
        "blacklist_count": int(data.get("blacklist_count") or 0),
        "blacklist": list(data.get("blacklist") or [])[:50],
    }


def collect_all(bucket: str, region: str, profile: str | None = None,
                object_key: str = "", with_referer: bool = False,
                with_website: bool = False, with_logging: bool = False,
                ram_user: str = "", role_name: str = "",
                endpoint: str = "", prefetched_info: dict | None = None) -> dict:
    """Collect the unconditional set plus whichever conditional reads apply.

    `prefetched_info` reuses a GetBucketInfo result already obtained while
    resolving the bucket region, so the unconditional evidence call is not
    issued twice in one run.
    """
    print("[1/4] bucket info + ACL", file=sys.stderr)
    if prefetched_info and prefetched_info.get("available"):
        info = prefetched_info
    else:
        info = collect("GetBucketInfo", bucket, region, profile, endpoint=endpoint)
    acl = collect("GetBucketAcl", bucket, region, profile, endpoint=endpoint)

    print("[2/4] bucket policy", file=sys.stderr)
    policy = collect_bucket_policy(bucket, region, profile, endpoint=endpoint)

    print("[3/4] block-public-access state", file=sys.stderr)
    public_block = collect("GetPublicAccessBlock", bucket, region, profile,
                           endpoint=endpoint)

    print("[4/4] conditional evidence", file=sys.stderr)
    conditional: dict = {}
    if object_key:
        conditional["object_acl"] = collect(
            "GetObjectAcl", bucket, region, profile,
            extra={"key": object_key}, endpoint=endpoint)
    if with_referer:
        conditional["referer"] = collect(
            "GetBucketReferer", bucket, region, profile, endpoint=endpoint)
    if with_website:
        conditional["website"] = collect(
            "GetBucketWebsite", bucket, region, profile, endpoint=endpoint)
    if with_logging:
        conditional["logging"] = collect(
            "GetBucketLogging", bucket, region, profile, endpoint=endpoint)

    ram = {"queried": False, "policies": [], "role": {}, "trust_policy": {},
           "oss_service_trusted": None, "deny_statements": [], "errors": []}
    if ram_user or role_name:
        ram = collect_ram_evidence(ram_user, role_name, region, profile)

    facts = derive_facts(info, acl, policy, public_block)

    degradation = []
    for name, item in [("GetBucketInfo", info), ("GetBucketAcl", acl),
                       ("GetBucketPolicy", policy),
                       ("GetPublicAccessBlock", public_block)]:
        if not item.get("available"):
            degradation.append(
                f"{name}: unavailable "
                f"[{item.get('error_category') or '?'}] "
                f"{item.get('error_code') or item.get('error_message') or ''}")
    for name, item in conditional.items():
        if isinstance(item, dict) and not item.get("available"):
            degradation.append(
                f"{item.get('action', name)}: unavailable "
                f"[{item.get('error_category') or '?'}] "
                f"{item.get('error_code') or ''}")
    degradation += [f"ram: {err}" for err in ram.get("errors", [])]

    return {
        "bucket": bucket,
        "region": region,
        "object": object_key,
        "facts": facts,
        "referer": render_referer(conditional.get("referer") or {}),
        "evidence": {
            "bucket_info": info,
            "bucket_acl": acl,
            "bucket_policy": policy,
            "public_access_block": public_block,
            "conditional": conditional,
            "ram": ram,
        },
        "degradation_log": degradation,
    }


def build_summary(payload: dict) -> dict:
    """Attach the dual-audience summary fields consumed by a later stage."""
    facts = payload["facts"]
    referer = payload.get("referer") or {}
    ram = payload["evidence"].get("ram") or {}

    key_findings = [
        f"Bucket ACL: {facts.get('bucket_acl') or 'unavailable'} "
        f"(source: {facts.get('acl_source', '-')})",
        f"Bucket policy: {facts.get('policy_statement_count', 0)} statement(s), "
        f"{facts.get('policy_deny_count', 0)} Deny",
        f"Block public access: {facts.get('block_public_access')} "
        f"(readable: {facts.get('block_public_access_available')})",
        f"Anonymous read possible: {facts.get('anonymous_read_possible')}",
        f"Anonymous list possible: {facts.get('anonymous_list_possible')}",
        f"Bucket created: {facts.get('creation_date') or 'unavailable'}",
        f"Region: {facts.get('region') or 'unresolved'} "
        f"(location {facts.get('location') or '-'})",
        f"Versioning: {facts.get('versioning') or 'unavailable'}",
    ]
    if referer:
        key_findings.append(
            f"Hotlink protection: whitelist {referer.get('whitelist_count', 0)} "
            f"entry(ies), blacklist {referer.get('blacklist_count', 0)} "
            f"entry(ies), allow empty referer = "
            f"{referer.get('allow_empty_referer')}")
    if ram.get("queried"):
        key_findings.append(
            f"RAM explicit Deny statements found: "
            f"{len(ram.get('deny_statements') or [])}")
        if ram.get("oss_service_trusted") is not None:
            key_findings.append(
                f"Role trusts the OSS service: {ram['oss_service_trusted']}")

    suggestions = list(facts.get("notes") or [])
    suggestions.append(
        "Pass this evidence together with the traced log row to "
        "diagnose_access_log.py to obtain the statement-level hit analysis.")

    payload["key_findings"] = key_findings
    payload["suggestions"] = suggestions
    payload["summary"] = (
        f"Collected authorization evidence for bucket {payload['bucket']}: "
        f"ACL {facts.get('bucket_acl') or 'unavailable'}, "
        f"{facts.get('policy_statement_count', 0)} policy statement(s), "
        f"block public access {facts.get('block_public_access')}, "
        f"region {facts.get('region') or 'unresolved'}.")
    return payload


def render_text(payload: dict) -> str:
    """Human-readable report."""
    facts = payload["facts"]
    referer = payload.get("referer") or {}
    ram = payload["evidence"].get("ram") or {}
    conditional = payload["evidence"].get("conditional") or {}
    lines: list[str] = []

    lines.append("=" * 72)
    lines.append("Authorization configuration evidence")
    lines.append("=" * 72)
    lines.append(f"  Bucket               : {payload['bucket']}")
    lines.append(f"  Region (resolved)    : {facts.get('region') or '-'}")
    lines.append(f"  Location             : {facts.get('location') or '-'}")
    lines.append(f"  Owner UID            : {facts.get('owner_id') or '-'}")
    lines.append(f"  Created              : {facts.get('creation_date') or '-'}")
    lines.append(f"  Storage class        : {facts.get('storage_class') or '-'}")
    lines.append(f"  Redundancy           : {facts.get('data_redundancy_type') or '-'}")
    lines.append(f"  Versioning           : {facts.get('versioning') or '-'}")
    lines.append(f"  Transfer acceleration: {facts.get('transfer_acceleration') or '-'}")
    lines.append(f"  Bucket ACL           : {facts.get('bucket_acl') or '-'} "
                 f"(from {facts.get('acl_source', '-')})")
    lines.append(f"  Block public access  : {facts.get('block_public_access')}")
    lines.append(f"  Policy statements    : {facts.get('policy_statement_count', 0)} "
                 f"(Deny: {facts.get('policy_deny_count', 0)})")
    lines.append(f"  Anonymous read       : {facts.get('anonymous_read_possible')}")
    lines.append(f"  Anonymous list       : {facts.get('anonymous_list_possible')}")

    if referer:
        lines.append(f"  Referer whitelist    : {referer.get('whitelist_count', 0)} "
                     f"entry(ies), allow empty = "
                     f"{referer.get('allow_empty_referer')}")
        if referer.get("blacklist_count"):
            lines.append(f"  Referer blacklist    : "
                         f"{referer.get('blacklist_count', 0)} entry(ies)")

    object_acl = conditional.get("object_acl")
    if object_acl:
        grant = (object_acl.get("data") or {}).get("acl", "")
        state = grant or (f"unavailable: {object_acl.get('error_code') or object_acl.get('error_category')}")
        lines.append(f"  Object ACL           : {state}")

    website = conditional.get("website")
    if website and website.get("available"):
        wd = website.get("data") or {}
        lines.append(f"  Website index/error  : "
                     f"{wd.get('index_file') or '-'} / {wd.get('error_file') or '-'}")
        if wd.get("mirror_rules_exposed") is False:
            lines.append("  Mirror back-to-origin: NOT readable through the SDK "
                         "(console only)")

    logging_cfg = conditional.get("logging")
    if logging_cfg and logging_cfg.get("available"):
        ld = logging_cfg.get("data") or {}
        lines.append(f"  Log shipping         : enabled={ld.get('enabled')} "
                     f"target={ld.get('target_bucket') or '-'}"
                     f"{ld.get('target_prefix') or ''}")

    if ram.get("queried"):
        lines.append(f"  RAM policies scanned : {len(ram.get('policies') or [])}")
        lines.append(f"  RAM Deny statements  : {len(ram.get('deny_statements') or [])}")
        if ram.get("oss_service_trusted") is not None:
            lines.append(f"  Role trusts OSS svc  : {ram.get('oss_service_trusted')}")

    statements = (payload["evidence"]["bucket_policy"].get("policy") or {}).get("Statement") or []
    if statements:
        lines.append("-" * 72)
        lines.append("  Bucket policy statements (verbatim):")
        for index, statement in enumerate(statements, 1):
            rendered = json.dumps(statement, ensure_ascii=False, indent=2)
            lines.append(f"  [{index}] " + rendered.replace("\n", "\n      "))

    denies = ram.get("deny_statements") or []
    if denies:
        lines.append("-" * 72)
        lines.append("  RAM explicit Deny statements (verbatim):")
        for item in denies[:10]:
            lines.append(f"  policy {item.get('policy_name')} "
                         f"({item.get('policy_type')}):")
            rendered = json.dumps(item.get("statement"), ensure_ascii=False, indent=2)
            lines.append("      " + rendered.replace("\n", "\n      "))

    lines.append("-" * 72)
    lines.append("Graceful Degradation Log")
    if payload["degradation_log"]:
        for item in payload["degradation_log"]:
            lines.append(f"  [WARN] {item}")
    else:
        lines.append("  none")
    lines.append("=" * 72)
    lines.append("")
    lines.append("Summary")
    lines.append("-------")
    for finding in payload["key_findings"]:
        lines.append(f"  - {finding}")
    if facts.get("notes"):
        lines.append("Correlated notes:")
        for note in facts["notes"]:
            lines.append(f"  * {note}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Collect read-only bucket, object and RAM configuration "
                    "evidence needed to explain an OSS access denial.",
    )
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument("--region", default="cn-hangzhou",
                        help="Region of the bucket (default: cn-hangzhou); "
                             "resolved from the bucket itself when wrong")
    parser.add_argument("--object", default="",
                        help="Object key; enables the per-object ACL read")
    parser.add_argument("--with-referer", action="store_true",
                        help="Also read the hotlink protection lists")
    parser.add_argument("--with-website", action="store_true",
                        help="Also read the static website documents")
    parser.add_argument("--with-logging", action="store_true",
                        help="Also read the periodic log shipping config")
    parser.add_argument("--ram-user", default="",
                        help="RAM user name for the explicit-Deny scan")
    parser.add_argument("--role-name", default="",
                        help="RAM role name whose trust policy should be read")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name "
                             "(applies to the RAM reads)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    available, why = _oss_client.sdk_available()
    if not available:
        print(f"[ERROR] the oss2 SDK is unavailable ({why}); install it with: "
              f"pip install 'oss2>=2.19.0,<3'", file=sys.stderr)
        return 1

    # Resolve the real region first: a wrong region surfaces as AccessDenied
    # "does not belong to you" rather than as a region error (measured), so
    # every later read would fail misleadingly.
    resolution = _oss_client.resolve_bucket_region(args.bucket, args.region)
    region = resolution.get("region") or args.region
    endpoint = _oss_client.endpoint_for_region(region)
    for warning in resolution.get("warnings") or []:
        _warn(warning)
    if resolution.get("source") != "get_bucket_info":
        print(f"[info] region source: {resolution.get('source')} "
              f"-> {region} (declared as auto-filled)", file=sys.stderr)

    payload = collect_all(
        args.bucket, region, profile=args.profile, object_key=args.object,
        with_referer=args.with_referer, with_website=args.with_website,
        with_logging=args.with_logging, ram_user=args.ram_user,
        role_name=args.role_name, endpoint=endpoint)
    payload["region_source"] = resolution.get("source", "unresolved")
    payload["endpoint"] = endpoint
    payload = build_summary(payload)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    else:
        print(render_text(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
