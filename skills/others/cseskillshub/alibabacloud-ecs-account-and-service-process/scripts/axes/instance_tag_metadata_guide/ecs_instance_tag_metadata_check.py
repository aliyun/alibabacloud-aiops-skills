#!/usr/bin/env python3
"""
ecs_instance_tag_metadata_check.py -- single entry point of the skill
=====================================================================
SECURITY: strictly READ-ONLY guidance skill.
  * It calls only the whitelisted read actions (ecs:DescribeInstances,
    ecs:DescribeInstanceStatus, sts:GetCallerIdentity); ``_guarded_call``
    refuses anything else, so no code path in this file can mutate a resource.
  * It never runs anything inside an instance and never emits a mutating
    command for this skill to execute: the in-guest checks it prints are a
    checklist the CUSTOMER runs in their own shell, and the report says so.
  * Credentials come from the aliyun CLI default credential chain only; this
    file never reads, prints, caches or asks for an access key or secret.
  * Only the resources named by the caller (or the inventory visible to the
    current credential in the queried regions) are reported on.

WHAT THIS SKILL DOES
  1. Ownership and tag facts: reads which resource group, tags, region, zone,
     status, VPC / security groups and metadata-option values an instance
     actually carries, in one or more regions, and answers "is this instance
     really in that resource group / carrying that tag".
  2. Rule answers: classifies pasted authorization-error wording
     (ImplicitDeny / resource-group policy type / a permission point the
     console says is missing) and explains metadata-service
     (100.100.100.200, IMDS, hardening) and tag questions from the embedded,
     source-labelled knowledge set.

CONTRACT: every run ends with
    STATUS: OK|DEGRADED|FAIL
    NEXT_ACTION: <what to do next, or what to ask the customer for>
Exit codes: 0 = OK or DEGRADED (a usable conclusion), 1 = no usable conclusion
(FAIL), 2 = argparse usage error only.

Usage examples:
  python3 ecs_instance_tag_metadata_check.py --region cn-hangzhou \
      --instance-id i-bp1xxxxxxxx
  python3 ecs_instance_tag_metadata_check.py --region cn-hangzhou \
      --resource-group-id rg-xxxxxxxx --status-check
  python3 ecs_instance_tag_metadata_check.py --region cn-hangzhou \
      --region cn-beijing --tag-key env --tag-value prod --json
  python3 ecs_instance_tag_metadata_check.py --metadata-check \
      --region cn-hangzhou --instance-id i-bp1xxxxxxxx
  python3 ecs_instance_tag_metadata_check.py --question \
      "NoPermissionType: ImplicitDeny PolicyType: ResourceGroupLevelIdentityBasedPolicy"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Optional

import _cli
from _cli import CliError
from _constants import (
    API_SHAPE_DATE,
    AUTH_ERROR_RULES,
    DEFAULT_GROUP_LABEL,
    DEFAULT_REGION,
    DOC_GAPS,
    DOC_LINKS,
    ECS_API_VERSION,
    ECS_PRODUCT,
    EVIDENCE_DATE,
    HANDOFF_RULES,
    HANDOFF_SENTENCE,
    HARD_LIMITATION,
    KNOWLEDGE_TOPICS,
    MAX_REGIONS,
    MAX_RESULTS,
    MAX_STATUS_IDS,
    METADATA_IP,
    METADATA_URL_V1,
    READ_ACTION_WHITELIST,
    REPORT_BANNER,
    SKILL_NAME,
    STATUS_PAGE_SIZE,
    SYSTEM_TAG_PREFIX,
    TOPIC_DOC_GAPS,
    VISIBILITY_DECLARATION,
)

LINE = "=" * 78

# Parameter shapes, validated before any call leaves the skill.
_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9][a-z0-9-]{2,62}$")
_REGION_RE = re.compile(r"^[a-z]{2}-[a-z0-9-]{2,28}$")
_RESOURCE_GROUP_RE = re.compile(r"^rg-[a-z0-9][a-z0-9-]{2,62}$")
_MAX_TAG_KEY_LEN = 128
_MAX_ID_BATCH = 100


# ---------------------------------------------------------------------------
# Guarded API access
# ---------------------------------------------------------------------------

def _assert_whitelisted(action: str) -> None:
    """Refuse any action outside the read-only whitelist before it is called."""
    permission = f"{ECS_PRODUCT}:{action}"
    if permission not in READ_ACTION_WHITELIST:
        raise CliError(
            f"{permission} is not on this skill's read-only action "
            f"whitelist {list(READ_ACTION_WHITELIST)}; the request was refused "
            f"inside the script and never reached the network.",
            code="LocalPolicyViolation",
        )

# ---------------------------------------------------------------------------
# Pure judgement functions (boundary assertions at the end of this block)
# ---------------------------------------------------------------------------

def parse_list(values: Optional[list[str]]) -> list[str]:
    """Flatten repeatable and comma-separated arguments, deduplicated."""
    out: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def validate_inputs(regions: list[str], instance_ids: list[str],
                    resource_group_id: str, tag_key: str) -> list[str]:
    """Human-readable parameter problems; empty list means the input is clean."""
    problems: list[str] = []
    for region in regions:
        if not _REGION_RE.match(region):
            problems.append(f"region id {region!r} is not a valid region id")
    for instance_id in instance_ids:
        if not _INSTANCE_ID_RE.match(instance_id):
            problems.append(
                f"instance id {instance_id!r} does not look like an ECS "
                f"instance id (expected the form i-xxxxxxxx)")
    if resource_group_id and not _RESOURCE_GROUP_RE.match(resource_group_id):
        problems.append(
            f"resource group id {resource_group_id!r} does not look valid "
            f"(expected the form rg-xxxxxxxx)")
    if tag_key:
        if len(tag_key) > _MAX_TAG_KEY_LEN:
            problems.append(f"tag key is longer than {_MAX_TAG_KEY_LEN} characters")
        if "=" in tag_key:
            problems.append("tag key must not contain '=' "
                            "(pass the value with --tag-value)")
    return problems


def is_service_tag(key: str) -> bool:
    """True for tag keys created by Alibaba Cloud services, not the customer."""
    return key.startswith(SYSTEM_TAG_PREFIX)


def extract_tags(instance: dict[str, Any]) -> list[tuple[str, str]]:
    """Tag (key, value) pairs of one instance record; empty values kept."""
    raw = instance.get("Tags") or {}
    entries = raw.get("Tag") if isinstance(raw, dict) else raw
    if not isinstance(entries, list):
        return []
    pairs: list[tuple[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = str(entry.get("TagKey") or entry.get("key") or "")
        value = entry.get("TagValue")
        if value is None:
            value = entry.get("value") or ""
        pairs.append((key, str(value)))
    return pairs


def split_tags(pairs: list[tuple[str, str]]) -> tuple[list[tuple[str, str]],
                                                     list[tuple[str, str]]]:
    """(customer tags, service-created tags) by the reserved key prefix."""
    return ([p for p in pairs if not is_service_tag(p[0])],
            [p for p in pairs if is_service_tag(p[0])])


def normalize_group(resource_group_id: Any) -> str:
    """Resource group id exactly as reported ("" means the default group)."""
    return str(resource_group_id or "").strip()


def group_verdict(actual: str, requested: str) -> str:
    """IN_GROUP | NOT_IN_GROUP | DEFAULT_GROUP | SET (pure function)."""
    if requested:
        return "IN_GROUP" if actual and actual == requested else "NOT_IN_GROUP"
    return "SET" if actual else "DEFAULT_GROUP"


def tag_inventory(instances: list[dict[str, Any]]) -> dict[str, Any]:
    """Fleet-level tag audit built from the instance records themselves."""
    untagged: list[str] = []
    keys: dict[str, int] = {}
    key_values: dict[str, set[str]] = {}
    for instance in instances:
        instance_id = str(instance.get("InstanceId") or "?")
        customer, _service = split_tags(extract_tags(instance))
        if not customer:
            untagged.append(instance_id)
        for key, value in customer:
            keys[key] = keys.get(key, 0) + 1
            key_values.setdefault(key, set()).add(value)
    return {
        "instances_scanned": len(instances),
        "untagged_instance_ids": untagged,
        "tag_keys": dict(sorted(keys.items())),
        "keys_with_conflicting_values": {
            key: sorted(values) for key, values in sorted(key_values.items())
            if len(values) > 1
        },
        "service_created_tag_prefix": SYSTEM_TAG_PREFIX,
    }


def metadata_facts(instance: dict[str, Any]) -> dict[str, str]:
    """Metadata-option values as returned; an unset value stays empty."""
    options = instance.get("MetadataOptions") or {}
    if not isinstance(options, dict):
        options = {}
    return {
        "http_endpoint": str(options.get("HttpEndpoint") or ""),
        "http_tokens": str(options.get("HttpTokens") or ""),
    }


def security_groups(instance: dict[str, Any]) -> list[str]:
    raw = instance.get("SecurityGroupIds") or {}
    groups = raw.get("SecurityGroupId") if isinstance(raw, dict) else raw
    return [str(x) for x in groups] if isinstance(groups, list) else []


def vpc_of(instance: dict[str, Any]) -> tuple[str, str]:
    attrs = instance.get("VpcAttributes") or {}
    if not isinstance(attrs, dict):
        return "", ""
    inner = attrs.get("PrivateIpAddress") or {}
    ips = inner.get("IpAddress") if isinstance(inner, dict) else None
    vswitch = str(attrs.get("VSwitchId") or "")
    if not vswitch and isinstance(ips, list) and ips:
        vswitch = str(ips[0])
    return str(attrs.get("VpcId") or ""), vswitch


def cross_check_status(instances: list[dict[str, Any]],
                       status_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare DescribeInstances status against DescribeInstanceStatus."""
    by_id = {str(r.get("InstanceId")): str(r.get("Status") or "")
             for r in status_rows if isinstance(r, dict)}
    consistent: list[str] = []
    mismatch: list[str] = []
    missing: list[str] = []
    for instance in instances:
        instance_id = str(instance.get("InstanceId") or "")
        listed = str(instance.get("Status") or "")
        if instance_id not in by_id:
            missing.append(instance_id)
        elif by_id[instance_id] != listed:
            mismatch.append(f"{instance_id}: listing={listed or '-'} "
                            f"status-api={by_id[instance_id] or '-'}")
        else:
            consistent.append(instance_id)
    return {"consistent": consistent, "mismatched": mismatch,
            "absent_from_status_api": missing}


def classify_error_text(text: str) -> list[dict[str, Any]]:
    """Match pasted error wording against the embedded authorization rules."""
    haystack = (text or "").lower()
    return [rule for rule in AUTH_ERROR_RULES
            if any(signal.lower() in haystack for signal in rule["signals"])]


def match_topics(text: str) -> list[tuple[dict[str, Any], int]]:
    """Knowledge topics ordered by how many match tokens the text contains."""
    haystack = (text or "").lower()
    scored = [(topic, sum(1 for token in topic["match"]
                         if token.lower() in haystack))
              for topic in KNOWLEDGE_TOPICS]
    scored = [item for item in scored if item[1]]
    scored.sort(key=lambda item: -item[1])
    return scored


def detect_handoff(text: str) -> list[dict[str, Any]]:
    """Out-of-scope signals worth naming in the answer."""
    haystack = (text or "").lower()
    return [rule for rule in HANDOFF_RULES
            if any(signal.lower() in haystack for signal in rule["signals"])]


def evidence_caveat(sources: str) -> str:
    """How strong is the ticket evidence behind an embedded answer."""
    if "summary:" in sources:
        return ("PARTIAL EVIDENCE: part of this answer rests on a ticket "
                "summary whose conversation was not re-pulled; that item is "
                "reported, not verified.")
    return "CONVERSATION-BACKED: the ticket conversation behind this answer was read."


def chunked(items: list[str], size: int) -> list[list[str]]:
    """Split a list into batches of at most ``size`` items."""
    return [items[i:i + size] for i in range(0, len(items), max(1, size))]


# Credential-chain and authorization failure classes. A credential failure must
# never be reported as a missing permission, and never as an empty inventory.
_CREDENTIAL_MARKERS = ("securitytoken", "accesskey", "signature", "credential",
                       "unauthorized")
_PERMISSION_MARKERS = ("nopermission", "accessdenied", "implicitdeny")


def classify_failure(errors: list[dict[str, str]]) -> str:
    """`credential` | `permission` | `other` from recorded error codes."""
    codes = [str(entry.get("error") or "").lower() for entry in errors]
    if any(marker in code for code in codes for marker in _CREDENTIAL_MARKERS):
        return "credential"
    if any(marker in code for code in codes for marker in _PERMISSION_MARKERS):
        return "permission"
    return "other"



# --- Inline boundary assertions (normal / boundary / invalid) -------------
assert parse_list(["i-a,i-b", "i-a", " i-c "]) == ["i-a", "i-b", "i-c"]
assert parse_list(None) == []                                      # boundary
assert validate_inputs(["cn-hangzhou"], ["i-bp1abc123"], "rg-aek1abc", "env") == []
assert len(validate_inputs(["Nowhere"], ["bad id"], "nope", "a=b")) == 4
assert validate_inputs([], [], "", "") == []                        # boundary
assert extract_tags({"Tags": {"Tag": [{"TagKey": "env", "TagValue": "prod"},
                                      {"TagKey": "acs:tag:createdby",
                                       "TagValue": "sub:1:x"}]}}) == \
    [("env", "prod"), ("acs:tag:createdby", "sub:1:x")]
assert extract_tags({"Tags": {"Tag": [{"TagKey": "k"}]}}) == [("k", "")]
assert extract_tags({}) == []                                       # boundary
assert extract_tags({"Tags": "unexpected"}) == []                   # invalid
assert split_tags([("env", "prod"), ("acs:x", "y")])[0] == [("env", "prod")]
assert group_verdict("rg-a", "rg-a") == "IN_GROUP"
assert group_verdict("rg-b", "rg-a") == "NOT_IN_GROUP"
assert group_verdict("", "rg-a") == "NOT_IN_GROUP"
assert group_verdict("", "") == "DEFAULT_GROUP"
assert group_verdict("rg-a", "") == "SET"
assert normalize_group(None) == ""                                  # boundary
_inventory = tag_inventory([
    {"InstanceId": "i-1", "Tags": {"Tag": [{"TagKey": "env", "TagValue": "a"}]}},
    {"InstanceId": "i-2", "Tags": {"Tag": [{"TagKey": "env", "TagValue": "b"},
                                           {"TagKey": "acs:x", "TagValue": "1"}]}},
    {"InstanceId": "i-3", "Tags": {"Tag": []}},
])
assert _inventory["untagged_instance_ids"] == ["i-3"]
assert _inventory["tag_keys"] == {"env": 2}
assert _inventory["keys_with_conflicting_values"] == {"env": ["a", "b"]}
assert tag_inventory([])["instances_scanned"] == 0                  # boundary
assert metadata_facts({}) == {"http_endpoint": "", "http_tokens": ""}
assert metadata_facts({"MetadataOptions": "bad"})["http_tokens"] == ""  # invalid
assert metadata_facts({"MetadataOptions": {"HttpTokens": "required"}}) == \
    {"http_endpoint": "", "http_tokens": "required"}
assert security_groups({"SecurityGroupIds": {"SecurityGroupId": ["sg-1"]}}) == ["sg-1"]
assert security_groups({}) == []                                    # boundary
assert vpc_of({"VpcAttributes": {"VpcId": "vpc-1", "VSwitchId": "vsw-1"}}) == \
    ("vpc-1", "vsw-1")
assert vpc_of({}) == ("", "")                                       # boundary
assert cross_check_status([{"InstanceId": "i-1", "Status": "Running"}],
                          [{"InstanceId": "i-1", "Status": "Running"}])[
    "consistent"] == ["i-1"]
assert cross_check_status([{"InstanceId": "i-1", "Status": "Running"}],
                          [{"InstanceId": "i-1", "Status": "Stopped"}])[
    "mismatched"] == ["i-1: listing=Running status-api=Stopped"]
assert cross_check_status([{"InstanceId": "i-1", "Status": "Running"}],
                          [])["absent_from_status_api"] == ["i-1"]
assert classify_error_text("NoPermissionType: ImplicitDeny PolicyType: "
                           "ResourceGroupLevelIdentityBasedPolicy")[0]["id"] == \
    "implicit-deny-in-resource-group"
assert classify_error_text("the console says ecs:ListTagResources is not "
                           "authorized")[0]["id"] == "list-tag-resources-no-group-scope"
assert classify_error_text("plain english, nothing to match") == []  # boundary
assert match_topics("curl 100.100.100.200 metadata timeout cloud-init")[0][
    0]["id"] == "metadata-service"
assert match_topics("zzz") == []                                     # boundary
assert detect_handoff("the cloud assistant agent keeps restarting") != []
assert detect_handoff("nothing relevant here") == []
assert "PARTIAL EVIDENCE" in evidence_caveat("summary:0001X")
assert "CONVERSATION-BACKED" in evidence_caveat("ticket:0001X")
assert chunked(["a", "b", "c"], 2) == [["a", "b"], ["c"]]
assert chunked([], 10) == []                                         # boundary
assert classify_failure([{"error": "InvalidSecurityToken.Expired"}]) == \
    "credential"
assert classify_failure([{"error": "NoPermission"}]) == "permission"
assert classify_failure([{"error": "Throttling.User"}]) == "other"
assert classify_failure([]) == "other"                    # boundary: no errors
assert classify_failure([{"error": ""}]) == "other"        # invalid: no code


# ---------------------------------------------------------------------------
# Evidence collection
# ---------------------------------------------------------------------------

def read_region_instances(region: str, params: dict[str, Any],
                          profile: Optional[str],
                          errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    """One region's DescribeInstances page walk; records failures in errors."""
    _assert_whitelisted("DescribeInstances")
    request = dict(params)
    request["RegionId"] = region
    items, err_code = _cli.paginate_next_token(
        ECS_PRODUCT, "DescribeInstances", request,
        items_path=["Instances", "Instance"],
        token_path=["NextToken"],
        region=region, profile=profile, max_results=MAX_RESULTS,
    )
    if err_code:
        note = f"{region}: ecs DescribeInstances failed ({err_code})"
        errors.append({"stage": "DescribeInstances", "region": region,
                       "error": err_code, "note": note})
        print(f"[WARN] {note}", file=sys.stderr)
        return []
    rows = [item for item in items if isinstance(item, dict)]
    for row in rows:
        row["_QueriedRegion"] = region
    return rows


def build_request_filters(args: argparse.Namespace,
                          instance_ids: list[str]) -> list[dict[str, Any]]:
    """Request parameter sets.

    When instance ids were named, ONLY the id filter is sent: adding the
    resource-group or tag filter server-side would make "exists but in another
    group" and "does not exist" return the same empty answer, and the whole
    point of this skill is to tell those two apart locally.
    """
    if instance_ids:
        return [{"InstanceIds": json.dumps(batch, separators=(",", ":"))}
                for batch in chunked(instance_ids, _MAX_ID_BATCH)]
    params: dict[str, Any] = {}
    if args.resource_group_id:
        params["ResourceGroupId"] = args.resource_group_id
    if args.tag_key:
        params["Tag.1.Key"] = args.tag_key
        if args.tag_value:
            params["Tag.1.Value"] = args.tag_value
    if args.instance_name:
        params["InstanceName"] = args.instance_name
    return [params]


def read_instances(args: argparse.Namespace, regions: list[str],
                   instance_ids: list[str],
                   errors: list[dict[str, str]]) -> tuple[list[dict[str, Any]],
                                                          dict[str, int]]:
    """Collect instance records for every requested region (bounded)."""
    rows: list[dict[str, Any]] = []
    per_region: dict[str, int] = {}
    for region in regions:
        region_rows: list[dict[str, Any]] = []
        before = len(errors)
        for request in build_request_filters(args, instance_ids):
            region_rows.extend(read_region_instances(region, request,
                                                    args.profile, errors))
        seen: set[str] = set()
        for row in region_rows:
            instance_id = str(row.get("InstanceId") or "")
            if instance_id and instance_id not in seen:
                seen.add(instance_id)
                rows.append(row)
        per_region[region] = -1 if len(errors) > before else len(seen)
    return rows, per_region


def read_status(args: argparse.Namespace, instances: list[dict[str, Any]],
                errors: list[dict[str, str]]) -> list[dict[str, Any]]:
    """DescribeInstanceStatus rows for the located instances (batched)."""
    rows: list[dict[str, Any]] = []
    by_region: dict[str, list[str]] = {}
    for instance in instances:
        region = str(instance.get("_QueriedRegion") or DEFAULT_REGION)
        by_region.setdefault(region, []).append(str(instance.get("InstanceId")))
    for region, ids in by_region.items():
        for batch in chunked(ids, MAX_STATUS_IDS):
            _assert_whitelisted("DescribeInstanceStatus")
            params: dict[str, Any] = {}
            for index, instance_id in enumerate(batch, start=1):
                params[f"InstanceId.{index}"] = instance_id
            page_size = min(STATUS_PAGE_SIZE, max(1, len(batch)))
            items, err_code = _cli.paginate_pages(
                ECS_PRODUCT, "DescribeInstanceStatus", params,
                items_path=["InstanceStatuses", "InstanceStatus"],
                region=region, profile=args.profile, page_size=page_size,
            )
            if err_code:
                note = f"{region}: ecs DescribeInstanceStatus failed ({err_code})"
                errors.append({"stage": "DescribeInstanceStatus",
                               "region": region, "error": err_code,
                               "note": note})
                print(f"[WARN] {note}", file=sys.stderr)
                continue
            rows.extend([item for item in items if isinstance(item, dict)])
    return rows


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_row(instance: dict[str, Any]) -> list[str]:
    customer, service = split_tags(extract_tags(instance))
    tag_text = ", ".join(f"{key}={value}" if value else key
                         for key, value in customer) or "(none)"
    group = normalize_group(instance.get("ResourceGroupId")) or DEFAULT_GROUP_LABEL
    options = metadata_facts(instance)
    vpc_id, vswitch = vpc_of(instance)
    return [
        f"  {instance.get('InstanceId', '?')}  "
        f"region={instance.get('_QueriedRegion', '?')}  "
        f"zone={instance.get('ZoneId') or '-'}  "
        f"status={instance.get('Status') or '-'}",
        f"    resource group  : {group}",
        f"    tags            : {tag_text}",
        f"    service tags    : {', '.join(k for k, _ in service) or '(none)'}",
        f"    vpc / vswitch   : {vpc_id or '-'} / {vswitch or '-'}",
        f"    security groups : {', '.join(security_groups(instance)) or '-'}",
        f"    metadata options: HttpEndpoint={options['http_endpoint'] or '(empty)'}, "
        f"HttpTokens={options['http_tokens'] or '(empty)'} "
        f"(read from the instance record; '(empty)' means the value was never "
        f"set, not that hardening is off)",
        f"    name / os       : {instance.get('InstanceName') or '-'} "
        f"[{instance.get('OSType') or '-'} network="
        f"{instance.get('InstanceNetworkType') or '-'}]",
    ]


def render_scope(out: list[str], errors: list[dict[str, str]]) -> None:
    """Shared tail: degradation log, scope, limitations, sources."""
    out.append(LINE)
    out.append("GRACEFUL DEGRADATION LOG")
    out.append(LINE)
    if errors:
        for entry in errors:
            out.append(f"  [{entry['stage']}][{entry['region']}] "
                       f"{entry['error']}: {entry['note']}")
    else:
        out.append("  none")
    out.append("")
    kind = classify_failure(errors)
    if kind == "credential":
        out.append("CREDENTIAL CHECK FIRST: the failures above are on the")
        out.append("credential chain itself. Ask the customer to refresh their")
        out.append("own credential (the CLI profile or the injected credential")
        out.append("environment). This is NOT a missing permission and NOT an")
        out.append("empty inventory: do not invent an instance, a group or a")
        out.append("tag to continue, and do not ask the customer to paste a key")
        out.append("or a secret -- this skill resolves credentials through the")
        out.append("CLI default chain only.")
        out.append("")
    elif kind == "permission":
        out.append("AUTHORIZATION GAP: an action this skill needs was denied.")
        out.append("Name the action and the code, and send the administrator to")
        out.append("references/ram-policies.md for the read-only grant; never")
        out.append("widen the grant or call another action to route around it.")
        out.append("")
    out.append(LINE)
    out.append("SCOPE, LIMITATIONS AND EVIDENCE")
    out.append(LINE)
    out.append(f"  {VISIBILITY_DECLARATION}")
    out.append(f"  {HARD_LIMITATION}")
    out.append(f"  {HANDOFF_SENTENCE}")
    out.append("  Actions used: " + ", ".join(READ_ACTION_WHITELIST) +
               f" (ECS API version {ECS_API_VERSION}); any other action is")
    out.append("  refused inside the script before it reaches the network.")
    out.append("  This run changed, moved, tagged or freed nothing; anything")
    out.append("  that has to change is a console step you perform yourself,")
    out.append("  after which this skill can re-read the facts read-only.")
    out.append(f"  Rule wording cross-checked {EVIDENCE_DATE}; response field")
    out.append(f"  shapes live-verified {API_SHAPE_DATE}. Verified doc links:")
    for key in ("ram-resource-group-grant", "ram-ecs-in-one-group",
                "tag-auto-snapshot", "ecs-feature-list"):
        title, url = DOC_LINKS[key]
        out.append(f"    - {title}: {url}")
    out.append(f"  No verified doc URL exists in this skill's evidence set for:")
    for gap in DOC_GAPS:
        out.append(f"    - {gap}")
    out.append("")


def render_question(text: str, out: list[str]) -> bool:
    """Knowledge-mode section; returns whether anything actually matched."""
    out.append(LINE)
    out.append("RULE ANSWERS (embedded knowledge; nothing was configured)")
    out.append(LINE)
    out.append(f"Question as received: {text}")
    out.append("")
    error_rules = classify_error_text(text)
    topics = match_topics(text)
    if not error_rules and not topics:
        out.append("No entry in this skill's verified knowledge matched that")
        out.append("wording, so no answer is given. Quote the exact error text")
        out.append("(the code, the NoPermissionType / PolicyType fields, the")
        out.append("permission point named by the console) or the symptom")
        out.append("sentence, or open a support ticket.")
        for rule in detect_handoff(text):
            out.append(f"  hand-off candidate: {rule['skill']} ({rule['note']})")
        out.append("")
        return False
    for rule in error_rules:
        out.append(f"* Authorization-error match: {rule['id']}")
        out.append(f"  verdict : {rule['verdict']}")
        out.append("  what YOU can do (this skill never edits a policy or a group):")
        for step in rule["customer_steps"]:
            out.append(f"    - {step}")
        out.append(f"  source  : {rule['source']}")
        out.append("")
    for topic, score in topics[:3]:
        out.append(f"* Topic: {topic['title']}  (matched {score} signal"
                   f"{'s' if score != 1 else ''})")
        for finding in topic["findings"]:
            out.append(f"  - {finding}")
        if topic["customer_steps"]:
            out.append("  Steps for YOU to run (this skill runs nothing inside")
            out.append("  an instance and applies no change):")
            for step in topic["customer_steps"]:
                out.append(f"    - {step}")
        for doc_key in topic["docs"]:
            title, url = DOC_LINKS[doc_key]
            out.append(f"  doc: {title} -> {url}")
        for gap_index in TOPIC_DOC_GAPS.get(topic["id"], ()):
            out.append(f"  doc gap: no verified official URL in this skill's "
                       f"evidence set for {DOC_GAPS[gap_index]}; none is quoted.")
        out.append(f"  source: {topic['source']}")
        out.append(f"  evidence strength: {evidence_caveat(topic['source'])}")
        out.append("")
    for rule in detect_handoff(text):
        out.append(f"* Out-of-scope signal -> {rule['skill']} ({rule['note']}). "
                   f"This skill only reads instance tag / metadata / "
                   f"resource-group facts and explains the related rules.")
        out.append("")
    out.append(f"Cross-check the rule wording against the linked docs before")
    out.append(f"quoting it to a customer: documented behaviour changes with")
    out.append(f"product versions (wording checked {EVIDENCE_DATE}).")
    out.append("")
    return True


def render_metadata_guidance(out: list[str]) -> None:
    """Cloud-side exclusion plus the customer-run checklist."""
    topic = next(t for t in KNOWLEDGE_TOPICS if t["id"] == "metadata-service")
    out.append(LINE)
    out.append("METADATA SERVICE: WHAT THE CLOUD SIDE CAN AND CANNOT PROVE")
    out.append(LINE)
    out.append(f"The endpoint read from inside the instance is {METADATA_IP}.")
    out.append(f"Example read used in reported cases: {METADATA_URL_V1}")
    out.append("")
    for finding in topic["findings"]:
        out.append(f"  - {finding}")
    out.append("")
    out.append("Customer-run self-check (executed by the customer in the")
    out.append("instance's own shell; this skill runs none of it):")
    for step in topic["customer_steps"]:
        out.append(f"  - {step}")
    out.append("")
    for doc_key in topic["docs"]:
        title, url = DOC_LINKS[doc_key]
        out.append(f"  doc: {title} -> {url}")
    for gap_index in TOPIC_DOC_GAPS.get(topic["id"], ()):
        out.append(f"  doc gap: no verified official URL in this skill's evidence")
        out.append(f"  set for {DOC_GAPS[gap_index]}; none is quoted here.")
    out.append("")
    for rule in HANDOFF_RULES:
        if "cloud assistant" in rule["signals"]:
            out.append(f"  If the in-guest agent itself reports a network block,")
            out.append(f"  that is {rule['skill']} territory ({rule['note']}).")
            break
    out.append("")


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

def build_report(args: argparse.Namespace) -> tuple[list[str], dict[str, Any],
                                                   str, str]:
    """Assemble the report lines, the JSON payload, STATUS and NEXT_ACTION."""
    out: list[str] = []
    errors: list[dict[str, str]] = []
    regions = parse_list(args.region_list) or [DEFAULT_REGION]
    regions_auto_filled = not args.region_list
    if len(regions) > MAX_REGIONS:
        print(f"[WARN] more than {MAX_REGIONS} regions requested; using the "
              f"first {MAX_REGIONS}", file=sys.stderr)
        errors.append({"stage": "inputs", "region": "-", "error": "RegionCap",
                       "note": f"region list truncated to {MAX_REGIONS}"})
        regions = regions[:MAX_REGIONS]
    instance_ids = parse_list(args.instance_id_list_arg)
    has_locator = bool(instance_ids or args.resource_group_id or args.tag_key
                       or args.instance_name)

    payload: dict[str, Any] = {
        "skill": SKILL_NAME,
        "session_id": _cli.session_id(),
        "user_agent": _cli.user_agent(),
        "read_only": True,
        "changed_resources": 0,
        "actions_allowed": list(READ_ACTION_WHITELIST),
        "ecs_api_version": ECS_API_VERSION,
        "regions_queried": regions,
        "filters": {
            "instance_ids": instance_ids,
            "resource_group_id": args.resource_group_id or "",
            "tag_key": args.tag_key or "",
            "tag_value": args.tag_value or "",
            "instance_name": args.instance_name or "",
        },
        "auto_filled": ({"region": DEFAULT_REGION,
                         "reason": "--region was omitted; defaulted and "
                                   "declared here"}
                        if regions_auto_filled else {}),
        "mode": ("question" if args.question else
                 "metadata-check" if args.metadata_check else
                 "fleet-inventory" if (args.inventory and not has_locator)
                 else "filtered-read"),
        "locator_given": has_locator,
        "errors": errors,
    }

    out.append(LINE)
    out.append(f" {REPORT_BANNER}")
    out.append(f" {SKILL_NAME}")
    out.append(LINE)

    problems = validate_inputs(regions, instance_ids, args.resource_group_id,
                              args.tag_key)
    if problems:
        for problem in problems:
            errors.append({"stage": "inputs", "region": "-",
                           "error": "InvalidParameter", "note": problem})
            print(f"[WARN] InvalidParameter: {problem}", file=sys.stderr)
        out.append("Parameter validation failed, so no cloud call was made.")
        out.append("Fix the value(s) above and re-run: this skill does not")
        out.append("guess ids, and it does not fall back to hand-typed calls.")
        out.append("")
        render_scope(out, errors)
        payload["summary"] = ("No conclusion: the request carried invalid "
                              "parameter values which are listed above.")
        return out, payload, "FAIL", (
            "ask the customer for a well-formed region id, instance id "
            "(i-xxxxxxxx) or resource group id (rg-xxxxxxxx), then re-run "
            "this same command")

    caller = _cli.resolve_caller(region=regions[0], profile=args.profile)
    payload["caller"] = caller
    if not caller["account_id"]:
        errors.append({"stage": "GetCallerIdentity", "region": "-",
                       "error": "CredentialUnavailable",
                       "note": "sts get-caller-identity returned no AccountId; "
                               "this report cannot be attributed to an account"})
        print("[WARN] CredentialUnavailable: the account UID could not be "
              "resolved; ask the customer to check their own credential chain",
              file=sys.stderr)
    out.append(f"Account behind this credential : "
               f"{caller['account_id'] or 'unresolved'}")
    out.append(f"Identity type                  : "
               f"{caller['identity_type'] or '-'}")
    if regions_auto_filled:
        out.append(f"Region auto-filled to {DEFAULT_REGION} (--region omitted); "
                   f"declare this in the answer.")
    out.append(f"Regions queried                : {', '.join(regions)}")
    active = [f"{key}={value}" for key, value in payload["filters"].items() if value]
    out.append(f"Locators                       : {', '.join(active) or 'none'}")
    if args.status_check:
        out.append("Status cross-check             : requested "
                   "(DescribeInstanceStatus)")
    out.append("")

    if args.question:
        matched = render_question(args.question, out)
        # A rule answer needs no cloud read, so an unresolved identity is a
        # note here, not a degradation of the answer itself.
        payload["matched"] = matched
        payload["identity_attributed"] = bool(caller["account_id"])
        if not caller["account_id"]:
            out.append("Note: the account UID behind this run is unresolved "
                       "(see the degradation log). That does not change a rule")
            out.append("answer, but any run that reads instances must wait "
                       "until the customer refreshes their credential.")
            out.append("")
        render_scope(out, errors)
        status = "OK" if matched else "FAIL"
        payload["matched"] = matched
        payload["summary"] = (
            f"Answered from the embedded rule set ({'match found' if matched else 'no match'}); "
            f"no cloud read was needed and nothing was changed."
        )
        return out, payload, status, (
            "if the answer also needs the instance's real values, re-run with "
            "--instance-id/--resource-group-id so the facts replace the rule"
            if matched else
            "ask the customer to paste the exact error text or symptom "
            "sentence; do not answer from model memory")

    if args.metadata_check and not instance_ids:
        out.append(f"No instance id was given, so there is nothing to exclude on")
        out.append(f"the cloud side for this {METADATA_IP} report.")
        out.append("")
        render_metadata_guidance(out)
        render_scope(out, errors)
        payload["summary"] = ("No conclusion: the metadata check needs the "
                              "instance id whose metadata endpoint fails.")
        return out, payload, "FAIL", (
            f"ask which instance id (and in which region) cannot reach "
            f"{METADATA_IP}, then re-run this command with --instance-id")

    instances, per_region = read_instances(args, regions, instance_ids, errors)
    payload["per_region_counts"] = per_region
    payload["instance_count"] = len(instances)

    out.append(LINE)
    out.append("INSTANCE FACTS (read-only)")
    out.append(LINE)
    if not instances:
        out.append("No instance record matched those locators in the regions")
        out.append("queried. An empty result is a finding, not a permission")
        out.append("failure - and this skill does not react to it by writing.")
        for region, count in per_region.items():
            out.append(f"  {region}: "
                       + ("query FAILED (see the degradation log)" if count < 0
                          else f"{count} matching instance(s)"))
        out.append("")
    limit = args.limit if args.limit and args.limit > 0 else 50
    for index, instance in enumerate(instances[:limit], start=1):
        out.append(f"[{index}]")
        out.extend(render_row(instance))
        out.append("")
    if len(instances) > limit:
        out.append(f"  {len(instances) - limit} more record(s) not printed; "
                   f"raise --limit or narrow the locators.")
        out.append("")

    if not has_locator and not args.inventory:
        out.append(LINE)
        out.append("NO TARGET NAMED")
        out.append(LINE)
        out.append("No locator was supplied, so the records above are only what")
        out.append("this credential can see in the regions queried: they are a")
        out.append("pick-list, not an answer. Ask which instance id, resource")
        out.append("group id or tag key the question is about and re-run; a")
        out.append("deliberate fleet-wide inventory needs the --inventory flag.")
        out.append("")
        render_scope(out, errors)
        payload["summary"] = (
            f"No conclusion drawn: {len(instances)} visible record(s) listed "
            f"for selection in {len(regions)} region(s), but no target was "
            f"named and nothing was changed."
        )
        return out, payload, "FAIL", (
            "ask the customer to name the target -- an instance id "
            "(i-xxxxxxxx), a resource group id (rg-xxxxxxxx) or a tag key -- "
            "then re-run this command with it; use --inventory only for an "
            "intentional fleet-wide read")

    if instance_ids:
        out.append(LINE)
        out.append("OWNERSHIP VERDICT (from what the API returns, not the console)")
        out.append(LINE)
        by_id = {str(item.get("InstanceId")): item for item in instances}
        for instance_id in instance_ids:
            instance = by_id.get(instance_id)
            if not instance:
                out.append(f"  {instance_id}: NOT FOUND in the regions queried "
                           f"({', '.join(regions)}). Possible reasons, not")
                out.append("     distinguishable from here: the instance is in "
                           "another region, it belongs to another account, or")
                out.append("     the current credential cannot see it. It is "
                           "NOT proof that the instance was deleted.")
                continue
            actual = normalize_group(instance.get("ResourceGroupId"))
            verdict = group_verdict(actual, args.resource_group_id)
            out.append(f"  {instance_id}: resource group = "
                       f"{actual or DEFAULT_GROUP_LABEL} -> {verdict}"
                       + (f" (asked about {args.resource_group_id})"
                          if args.resource_group_id else ""))
        out.append("")
        out.append("  A correct grant is not the same thing as a visible list.")
        out.append("  When the verdict above says the instance IS in the group")
        out.append("  the RAM user is authorized for, the remaining step is the")
        out.append("  customer's own: switch the console resource-group")
        out.append("  selector, drop any ResourceGroupId parameter left in the")
        out.append("  URL, and check the region selector. Console and browser")
        out.append("  filter state is invisible to every cloud API.")
        out.append("")

    inventory = tag_inventory(instances)
    payload["tag_inventory"] = inventory
    out.append(LINE)
    out.append("TAG INVENTORY")
    out.append(LINE)
    out.append(f"  instances scanned        : {inventory['instances_scanned']}")
    out.append(f"  without a customer tag   : {len(inventory['untagged_instance_ids'])}"
               + (f" -> {', '.join(inventory['untagged_instance_ids'][:20])}"
                  if inventory["untagged_instance_ids"] else ""))
    if inventory["tag_keys"]:
        out.append("  tag key -> instance count:")
        for key, count in inventory["tag_keys"].items():
            out.append(f"    - {key}: {count}")
    else:
        out.append("  tag keys                 : none on the scanned instances")
    if inventory["keys_with_conflicting_values"]:
        out.append("  keys carrying more than one distinct value:")
        for key, values in inventory["keys_with_conflicting_values"].items():
            out.append(f"    - {key}: {', '.join(values[:10])}"
                       + (" ..." if len(values) > 10 else ""))
    out.append(f"  keys with the service prefix "
               f"{SYSTEM_TAG_PREFIX} are created by Alibaba")
    out.append("  Cloud itself and are excluded from the counts above.")
    out.append("  Tagging is something you do in the console or with your own")
    out.append("  tooling; this skill only reads the result back.")
    out.append("")

    if args.status_check:
        status_rows = read_status(args, instances, errors)
        verdict = cross_check_status(instances, status_rows)
        payload["status_cross_check"] = verdict
        out.append(LINE)
        out.append("STATUS CROSS-CHECK (DescribeInstances vs DescribeInstanceStatus)")
        out.append(LINE)
        out.append(f"  consistent           : {len(verdict['consistent'])}")
        for line in verdict["mismatched"]:
            out.append(f"  MISMATCH             : {line}")
        for instance_id in verdict["absent_from_status_api"]:
            out.append(f"  absent from status api: {instance_id} (another region "
                       f"or not visible to this credential)")
        out.append("  A stopped instance explains an unreachable service inside")
        out.append("  it, but it does not by itself explain a metadata failure:")
        out.append("  that reading lives in the guest, which this skill cannot")
        out.append("  and does not touch.")
        out.append("")

    if args.metadata_check:
        render_metadata_guidance(out)

    render_scope(out, errors)

    failed = [region for region, count in per_region.items() if count < 0]
    failure_kind = classify_failure(errors)
    payload["failure_kind"] = failure_kind
    if not instances and failed and len(failed) == len(regions):
        status = "FAIL"
        if failure_kind == "credential":
            next_action = (
                "credential-chain failure, not a permission gap and not an "
                "empty fleet: report the code and ask the customer to refresh "
                "their own CLI credential (aliyun configure or the injected "
                "environment); never fabricate an instance, group or tag to "
                "fill the gap")
        elif failure_kind == "permission":
            next_action = (
                "authorization gap on every region: report the code, name the "
                "missing read action from references/ram-policies.md, and let "
                "the customer's administrator attach it")
        else:
            next_action = (
                "every region read failed: report the codes from the "
                "degradation log, retry once, and if it persists hand the "
                "failure to a support ticket instead of concluding")
    elif not instances:
        status, next_action = "DEGRADED", (
            "state the not-found result honestly and ask for the region the "
            "instance was created in, the exact instance id, or the resource "
            "group id; never invent an owner or a group")
    elif errors:
        status, next_action = "DEGRADED", (
            "relay the facts that were read, name the part of the evidence "
            "that is missing and the error code behind it, and retry only "
            "that read")
    else:
        status, next_action = "OK", (
            "answer the customer from the facts above; for visibility "
            "questions pair the verdict with the console resource-group "
            "switch steps; for authorization questions run --question with "
            "the pasted error text")
    payload["status"] = status
    payload["next_action"] = next_action
    payload["summary"] = (
        f"Read {len(instances)} instance record(s) across {len(regions)} "
        f"region(s) with {', '.join(READ_ACTION_WHITELIST)}; "
        f"{len(errors)} degradation note(s); nothing was changed."
    )
    return out, payload, status, next_action


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ecs_instance_tag_metadata_check.py",
        description=(
            "Read-only facts and rule answers for ECS instance tags, "
            "resource-group ownership and the instance metadata service "
            f"(ECS API version {ECS_API_VERSION})"
        ),
    )
    parser.add_argument("--region", dest="region_list", action="append",
                        metavar="REGION_ID",
                        help=f"Region to read; repeatable. Defaults to "
                             f"{DEFAULT_REGION} (auto-filled and declared)")
    parser.add_argument("--instance-id", dest="instance_id_list_arg",
                        action="append", metavar="ID",
                        help="Instance id(s); repeatable or comma separated")
    parser.add_argument("--resource-group-id", default="", metavar="RG_ID",
                        help="Restrict the listing to one resource group id")
    parser.add_argument("--tag-key", default="", metavar="KEY",
                        help="Restrict the listing to a tag key "
                             "(combine with --tag-value)")
    parser.add_argument("--tag-value", default="", metavar="VALUE",
                        help="Value for --tag-key")
    parser.add_argument("--instance-name", default="", metavar="NAME",
                        help="Restrict the listing to an instance name")
    parser.add_argument("--status-check", action="store_true",
                        help="Also read DescribeInstanceStatus and compare it")
    parser.add_argument("--inventory", action="store_true",
                        help="Intentional fleet-wide read when no locator is "
                             "given (otherwise a locator-free run ends FAIL "
                             "with the visible records as a pick-list)")
    parser.add_argument("--metadata-check", action="store_true",
                        help=f"Add the cloud-side exclusion for {METADATA_IP} "
                             f"plus the customer-run self-check list")
    parser.add_argument("--question", default="",
                        help="Customer wording, or a pasted error text, to "
                             "answer from the embedded source-labelled rules")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max instance records to print (default 50)")
    parser.add_argument("--json", action="store_true",
                        help="Emit the structured payload instead of the report")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    args = parser.parse_args()

    _cli.check_cli_available()
    report, payload, status, next_action = build_report(args)

    if args.json:
        payload["report_lines"] = report
        payload["status"] = status
        payload["next_action"] = next_action
        # stdout stays a single JSON document; the contract lines go to stderr
        # so they are still in the transcript.
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        print(f"STATUS: {status}", file=sys.stderr)
        print(f"NEXT_ACTION: {next_action}", file=sys.stderr)
    else:
        print("\n".join(report))
        print("Summary")
        print(payload.get("summary") or "No summary produced.")
        print("")
        print(f"STATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    sys.exit(0 if status in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
