#!/usr/bin/env python3
"""
assess_spec_change.py -- single entry script for the spec-change & purchase
feasibility skill (query-only cloud calls + rule guidance)
===========================================================================
SECURITY: This script performs nothing but the whitelisted QUERY actions of
this skill -- DescribeInstances, DescribeInstanceAttribute,
DescribeResourcesModification (query semantics only: it lists what COULD be
changed and stock; it changes nothing), DescribeAvailableResource,
DescribeInstanceTypes, DescribePricingModule, GetSubscriptionPrice and
get-caller-identity -- all through scripts/areas/spec_change_purchase/_cli.py. It never calls a
mutating API, never runs anything inside a customer instance, and never
reads, prints or passes credentials: the aliyun CLI default credential chain
is the only authentication source. Every subprocess call carries the
per-run observability user-agent and a hard timeout (constants define it).

WHAT IT ANSWERS (the five questions of the tier):
  which target specs are selectable - is there stock by zone - what does the
  error/quota wording mean - what does it approximately cost (ESTIMATE only)
  - and what makes a change take effect. The customer performs every change
  action in the ECS console after the mandatory risk notices are relayed.

Examples:
  python3 scripts/areas/spec_change_purchase/assess_spec_change.py --error-string "Your available quota is insufficient."
  python3 scripts/areas/spec_change_purchase/assess_spec_change.py --change-object bandwidth
  python3 scripts/areas/spec_change_purchase/assess_spec_change.py --region-id cn-hangzhou --instance-id i-bp1xxxxxxx
  python3 scripts/areas/spec_change_purchase/assess_spec_change.py --region-id cn-hangzhou --instance-id i-bp1xxxxxxx \
      --target-type ecs.u1-c1m2.xlarge --direction downgrade --list-targets --estimate
  python3 scripts/areas/spec_change_purchase/assess_spec_change.py --region-id us-west-1 --check-inventory \
      --target-type ecs.g7.large --charge-type PrePaid
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import re
import sys

import _cli
from _constants import (
    API_VERSIONS,
    CHANGE_NOTICES,
    CHANGE_SET_VS_BUY_PAGE,
    DEFAULT_REGION,
    DYNAMIC_PRICE_NOTICE,
    EFFECT_STATEMENTS,
    ERROR_RULES,
    FIVE_QUESTIONS,
    INVENTORY_CAVEAT,
    INSTANCE_ID_RE,
    IRREVERSIBLE_NOTICES,
    MAX_TARGET_DISPLAY,
    PRICE_DISCLAIMER,
    RED_LINE_NO_STOCK_REFUND,
    REGION_ID_RE,
    RESTART_RISK,
    SKILL_NAME,
    SNAPSHOT_ADVICE,
    SPEC_CHANGE_SAFETY_PRELUDE,
    SPEC_RULE_ACTIVITY_TOPICS,
    SPEC_RULE_CONSOLE_PATH,
    SPEC_RULE_INTENT_PATTERNS,
    SPEC_RULE_MONEY_NOTICES,
    SPEC_RULE_MONEY_TOPICS,
    SPEC_RULE_ONLY_TOPICS,
    SPEC_RULE_SAFETY_TOPICS,
    SPEC_RULE_TAILS,
    SPEC_RULE_TOPICS,
    ACTIVITY_REFERENCE_NOTICE,
    TEMP_BANDWIDTH_RULES,
    TYPE_ID_RE,
    ZONE_ID_RE,
)

DISK_HANDOFF = (
    "Disk CAPACITY questions (a resized disk not visible inside the OS) are "
    "not this tier: hand off to area:disk-expand-diagnosis; this "
    "skill covers spec / bandwidth / billing / inventory / quota only."
)
DISK_TYPE_NOTE = (
    "A disk CATEGORY / performance-level change belongs to this tier; only a "
    "capacity increase that is not visible inside the OS goes to "
    "area:disk-expand-diagnosis."
)
OTHER_HANDOFF = (
    "This request is outside ECS spec-change / purchase feasibility "
    "(another product or a customer-side program). Name the boundary and "
    "route to the owning product or the customer's own operations staff; "
    "do not answer its quota/cap rules from this skill."
)
BILLING_CONVERSION_NOTE = (
    "Charge-type conversion (pay-as-you-go <-> subscription) is decided on "
    "the console conversion page; associated resources such as an EIP keep "
    "their own billing and do NOT convert with the instance. Related "
    "resources such as EIP remain billed by traffic even after the instance "
    "becomes a subscription one. Conversion itself is executed by the "
    "customer."
)
_REFUND_VCPU_RE = re.compile(
    r"quota limited by user quota:\s*\[?(\d+)\]?\s*used:\s*\[?(\d+)\]?\s*"
    r"need:\s*\[?(\d+)\]?", re.I)


class Report:
    def __init__(self):
        self.lines = []        # list[str] human-readable findings
        self.warnings = []     # list[str] degradations (also on stderr)
        self.auto_filled = []  # list[str] declared auto-fills
        self.data = {}         # machine-readable evidence
        self.fatal = None      # str | None
        self.fatal_next = ""

    def find(self, line):
        self.lines.append(line)

    def section(self, title):
        self.lines.append("")
        self.lines.append(f"--- {title} ---")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"[WARN] {msg}", file=sys.stderr)

    def degrade(self, label, err):
        code = getattr(err, "code", "") or "Unknown"
        self.warn(f"{label} unavailable (Code: {code}); this part degrades "
                  f"to console self-check guidance instead of a cloud reading")

    def fail(self, message, next_action):
        self.fatal = message
        self.fatal_next = next_action


def _dig(node, path, default=None):
    cur = node
    for key in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return default if cur is None else cur


def _collect_supported(node, zone=None, bucket=None, depth=0):
    """Recursively gather {type,status,zone} from an ECS AvailableZones-style
    response (works for DescribeResourcesModification too). Defensive: the
    exact nesting is walked, not assumed."""
    if depth > 14:
        return bucket if bucket is not None else []
    if bucket is None:
        bucket = []
    if isinstance(node, dict):
        zone_here = node.get("ZoneId") or zone
        value, status = node.get("Value"), node.get("Status")
        if (isinstance(value, str) and isinstance(status, str)
                and value.startswith("ecs.")):
            entry = {"type": value, "status": status, "zone": zone_here or ""}
            if entry not in bucket:
                bucket.append(entry)
        for child in node.values():
            if isinstance(child, (dict, list)):
                _collect_supported(child, zone_here, bucket, depth + 1)
    elif isinstance(node, list):
        for item in node:
            _collect_supported(item, zone, bucket, depth + 1)
    return bucket


# ---------------------------------------------------------------------------
# S1 identity gate (C1)
# ---------------------------------------------------------------------------

def do_identity(rep, profile):
    _cli.check_cli_available()
    try:
        body = _cli.call("sts", "GetCallerIdentity", {}, profile=profile)
    except _cli.CliError as err:
        code = getattr(err, "code", "") or "NoPermission"
        rep.fail(f"Identity pre-check failed (Code: {code}). Credentials come "
                 f"only from the aliyun CLI default credential chain.",
                 "check the CLI credential chain (run `aliyun sts get-caller-identity`), "
                 "then re-run; never pass credential values explicitly")
        return None
    uid = str(body.get("AccountId") or "")
    # Only the tail of the caller account id is reportable; the full number is an
    # internal identifier the customer cannot verify and gains nothing from.
    uid_tail = ("****" + uid[-4:]) if uid else "not reported"
    rep.find(f"[S1 identity] caller account UID: {uid_tail}")
    rep.data["uid"] = uid_tail
    return uid


# ---------------------------------------------------------------------------
# S2 current instance facts (C2)
# ---------------------------------------------------------------------------

def do_instance(rep, region, instance_id, profile):
    try:
        body = _cli.call("ecs", "DescribeInstances",
                         {"RegionId": region,
                          "InstanceIds": json.dumps([instance_id])},
                         region=region, profile=profile)
    except _cli.CliError as err:
        rep.degrade("DescribeInstances", err)
        return None
    rows = _dig(body, ["Instances", "Instance"], []) or []
    if not rows:
        rep.fail(f"Instance {instance_id} was not found in region '{region}'.",
                 "re-run with the correct --region-id (the console instance "
                 "list shows the owning region); never guess other regions")
        return None
    inst = dict(rows[0])
    try:
        attr = _cli.call("ecs", "DescribeInstanceAttribute",
                         {"InstanceId": instance_id}, region=region,
                         profile=profile)
        for key in ("InstanceType", "Status", "InstanceChargeType", "ZoneId",
                    "InternetChargeType", "InternetMaxBandwidthOut"):
            if attr.get(key) is not None:
                inst[key] = attr[key]
    except _cli.CliError as err:
        rep.degrade("DescribeInstanceAttribute", err)
    inst["_region"] = str(inst.get("RegionId") or region)
    inst["_zone"] = str(inst.get("ZoneId") or "")
    rep.data["instance"] = {
        "instance_id": inst.get("InstanceId"),
        "instance_type": inst.get("InstanceType"),
        "cpu": inst.get("Cpu"), "memory_mib": inst.get("Memory"),
        "status": inst.get("Status"),
        "charge_type": inst.get("InstanceChargeType"),
        "region": inst["_region"], "zone": inst["_zone"],
        "internet_charge_type": inst.get("InternetChargeType"),
        "bandwidth_mbps": inst.get("InternetMaxBandwidthOut"),
        "public_ips": _dig(inst, ["PublicIpAddress", "IpAddress"], []) or [],
        "eip": inst.get("EipAddress") or {},
    }
    rep.section("S2 current instance (cloud reading)")
    rep.find(f"spec {inst.get('InstanceType', 'N/A')} "
             f"(vCPU {inst.get('Cpu', 'N/A')}, memory {inst.get('Memory', 'N/A')} "
             f"Mib) | status {inst.get('Status', 'N/A')} | billing "
             f"{inst.get('InstanceChargeType', 'N/A')} (PrePaid = subscription)")
    rep.find(f"region {inst['_region']} | zone {inst['_zone'] or 'N/A'} | "
             f"public bandwidth {inst.get('InternetMaxBandwidthOut', 'N/A')} "
             f"Mbps metered {inst.get('InternetChargeType', 'N/A')}")
    eip = inst.get("EipAddress") or {}
    pub = _dig(inst, ["PublicIpAddress", "IpAddress"], []) or []
    if eip.get("IpAddress"):
        rep.find(f"public address: EIP {eip.get('IpAddress')} "
                 f"(billing {eip.get('InternetChargeType', 'N/A')})")
    elif pub:
        rep.find(f"public address: fixed public IP {', '.join(pub)}")
    else:
        rep.find("public address: none attached")
    return inst


# ---------------------------------------------------------------------------
# S4 modifiable target set for the instance (C3)
# ---------------------------------------------------------------------------

def _query_targets(rep, params, profile, with_operation):
    p = dict(params)
    if not with_operation:
        p.pop("OperationType", None)
    return _cli.call("ecs", "DescribeResourcesModification", p,
                     region=str(params.get("RegionId")), profile=profile)


def do_targets(rep, region, instance_id, direction, target_type, profile):
    params = {"RegionId": region, "ResourceId": instance_id,
              "DestinationResource": "InstanceType"}
    if direction:
        params["OperationType"] = ("Upgrade" if direction == "upgrade"
                                   else "Downgrade")
    try:
        body = _query_targets(rep, params, profile, True)
    except _cli.CliError as err:
        if direction:
            rep.warn(f"DescribeResourcesModification with OperationType "
                     f"rejected ({getattr(err, 'code', '') or 'Unknown'}); "
                     f"retrying without the direction filter")
            try:
                body = _query_targets(rep, params, profile, False)
            except _cli.CliError as err2:
                rep.degrade("DescribeResourcesModification", err2)
                return None
        else:
            rep.degrade("DescribeResourcesModification", err)
            return None
    entries = _collect_supported(body)
    available = [e for e in entries if e["status"].lower().startswith("avail")]
    sold_out = [e for e in entries if "sold" in e["status"].lower()]
    rep.data["targets"] = entries
    rep.section("S4 modifiable target set for this instance (cloud reading)")
    rep.find(f"{len(entries)} target entries: {len(available)} Available, "
             f"{len(sold_out)} SoldOut, "
             f"{len(entries) - len(available) - len(sold_out)} other state")
    for e in available[:MAX_TARGET_DISPLAY]:
        rep.find(f"  [Available] {e['type']} (zone {e['zone'] or 'n/a'})")
    if len(available) > MAX_TARGET_DISPLAY:
        rep.find(f"  ... {len(available) - MAX_TARGET_DISPLAY} more "
                 f"(full list in --json)")
    if target_type:
        hits = [e for e in entries if e["type"] == target_type]
        in_set = bool(hits)
        rep.data["target_in_set"] = in_set
        if in_set:
            states = sorted({h["status"] for h in hits})
            rep.find(f"TARGET {target_type}: in the change set, state(s): "
                     f"{', '.join(states)}")
        else:
            rep.find(f"TARGET {target_type}: NOT in this instance's change "
                     f"set")
            rep.find(CHANGE_SET_VS_BUY_PAGE)
    return entries


# ---------------------------------------------------------------------------
# S5 inventory scan for a region (C4) + substitute candidates (C5)
# ---------------------------------------------------------------------------

def do_inventory(rep, region, target_type, charge_type, zone_id, profile):
    params = {"RegionId": region, "DestinationResource": "InstanceType"}
    if charge_type:
        params["InstanceChargeType"] = charge_type
    if zone_id:
        params["ZoneId"] = zone_id
    try:
        body = _cli.call("ecs", "DescribeAvailableResource", params,
                         region=region, profile=profile)
    except _cli.CliError as err:
        rep.degrade("DescribeAvailableResource", err)
        return None
    entries = _collect_supported(body)
    rep.data["inventory"] = entries
    rep.section("S5 region inventory (cloud reading)")
    avail_by_zone = {}
    for e in entries:
        if e["status"].lower().startswith("avail"):
            avail_by_zone.setdefault(e["zone"] or "n/a", []).append(e["type"])
    if target_type:
        zones_with = sorted(z for z, types in avail_by_zone.items()
                            if target_type in types)
        rep.data["target_zones"] = zones_with
        if zones_with:
            rep.find(f"{target_type} is AVAILABLE in zone(s): "
                     + ", ".join(zones_with))
        else:
            seen = sorted({e["zone"] for e in entries if e["type"] == target_type})
            rep.find(f"{target_type} is NOT available in any zone of region "
                     f"{region}" + (f" (listed SoldOut/Unavailable in "
                                    f"{', '.join(seen)})" if seen else
                                    " (no sellable entry at all in this "
                                    "region)"))
        rep.find(f"in-stock type count by zone: "
                 + ", ".join(f"{z}={len(t)}" for z, t in
                             sorted(avail_by_zone.items())[:10]))
    else:
        rep.find(f"region {region}: "
                 + ", ".join(f"{z}={len(t)} available types"
                             for z, t in sorted(avail_by_zone.items())[:10]))
    rep.find(INVENTORY_CAVEAT)
    return entries


def do_substitutes(rep, region, target_type, cores, memory, entries, profile):
    if not cores or not memory or entries is None:
        return
    params = {"MinimumCpuCoreCount": str(cores), "MaximumCpuCoreCount": str(cores),
              "MinimumMemorySize": str(memory), "MaximumMemorySize": str(memory)}
    try:
        items = _cli.paginate_next_token(
            "ecs", "DescribeInstanceTypes", params, region=region,
            items_path=["InstanceTypes", "InstanceType"],
            token_resp_path=["NextToken"])
    except _cli.CliError as err:
        rep.degrade("DescribeInstanceTypes", err)
        return
    catalog = [str(i.get("InstanceTypeId")) for i in items
               if isinstance(i, dict) and i.get("InstanceTypeId")]
    in_stock = {e["type"] for e in entries
                if e["status"].lower().startswith("avail")}
    subs = [t for t in catalog if t in in_stock and t != target_type]
    rep.data["substitutes"] = subs
    rep.section("S5 substitute candidates, same vCPU/memory tier (C5)")
    rep.find(f"{len(catalog)} catalog types at {cores} vCPU / {memory} GiB; "
             f"in stock in this region: "
             + (", ".join(subs[:MAX_TARGET_DISPLAY]) if subs
                else "none -- widen zones or regions and re-scan"))


# ---------------------------------------------------------------------------
# C8 effectiveness check: inventory spec vs claimed target
# ---------------------------------------------------------------------------

def do_verify(rep, inst, target_type):
    current = str(inst.get("InstanceType") or "")
    match = current == target_type
    rep.data["effective_check"] = {"inventory_spec": current,
                                   "expected": target_type, "match": match}
    rep.section("S8 does the change take effect? (C8)")
    if match:
        rep.find(f"The inventory spec already equals {target_type}: the "
                 f"platform applied the change. If the OS still shows old "
                 f"values, the restart step is pending -- relay the three "
                 f"effectiveness statements below.")
    else:
        rep.find(f"The inventory spec is {current}, not {target_type}: the "
                 f"change is NOT visible at the platform level. Split the "
                 f"cases: unpaid or cancelled order, order with a later "
                 f"scheduled effective time (check the order), or a failed "
                 f"change.")
        rep.find("Order-side facts (paid-but-not-applied, auto-refund, exact "
                 "effective timestamps) are OUT of this tier's API contract: "
                 "register the order number and hand off to a human.")
        rep.find(RED_LINE_NO_STOCK_REFUND)
    for s in EFFECT_STATEMENTS:
        rep.find(f"* {s}")
    rep.find(f"* {RESTART_RISK}")
    for s in SNAPSHOT_ADVICE:
        rep.find(f"* {s}")


# ---------------------------------------------------------------------------
# C7 error triage (offline, pure text rules)
# ---------------------------------------------------------------------------

def do_triage(rep, error_text):
    rep.section("C7 error-string triage (rule table, no cloud call)")
    rep.find(f"customer text: {error_text[:300]}")
    matched = None
    for rule in ERROR_RULES:
        for pat in rule["patterns"]:
            if re.search(pat, error_text):
                matched = rule
                break
        if matched:
            break
    if matched is None:
        rep.find("No known signature matched. Keep the VERBATIM text and "
                 "collect region / zone / instance IDs, then run the "
                 "inventory or quota lines on the facts.")
        rep.data["triage"] = "unknown"
        return
    rep.data["triage"] = matched["category"]
    rep.find(f"category : {matched['category']} ({matched['kind']})")
    rep.find(f"meaning  : {matched['meaning']}")
    for h in matched["handling"]:
        rep.find(f"handling : {h}")
    for a in matched["next_actions"]:
        rep.find(f"next     : {a}")
    rep.find(f"deep dive: {matched['reference']}")
    nums = _REFUND_VCPU_RE.search(error_text)
    if nums:
        quota, used, need = nums.groups()
        rep.data["quota_terms"] = {"quota": quota, "used": used, "need": need}
        rep.find(f"parsed quota terms: limit [{quota}] used [{used}] "
                 f"need [{need}] -- echo these verbatim to the customer")
    if matched["kind"] == "observed_string":
        rep.find("note: this string is ticket-observed console text, not an "
                 "official error code of this tier; route on it, do not "
                 "restate it as a code.")


def spec_rule_for(question):
    """The rule topic this first question earns, or ('', '') when none matches."""
    for pattern, topic in SPEC_RULE_INTENT_PATTERNS:
        if re.search(pattern, question or ""):
            return topic, SPEC_RULE_TOPICS.get(topic, {})
    return "", {}


def do_rule_answer(rep, question, change_object=""):
    """C10: the knowledge answer the question earns, before any id is demanded."""
    topic, entry = spec_rule_for(question)
    if not topic or not entry:
        return ""
    rep.section("C10 rule answer for the asked question (offline rule, no cloud read)")
    answer = entry["answer"]
    sentences = answer.split(". ")
    count = 2 if len(". ".join(sentences[:2]).rstrip(".")) <= 300 else 1
    lead = ". ".join(sentences[:count]).rstrip(".")
    if (topic in SPEC_RULE_SAFETY_TOPICS and change_object != "bandwidth"
            and "snapshot" not in lead.lower()):
        count = 1
        lead = (sentences[0].rstrip(".") + ". "
                + SPEC_CHANGE_SAFETY_PRELUDE.rstrip("."))
    rep.find("Have the customer take the rule answer first: " + lead + ".")
    tail = ". ".join(sentences[count:]).strip()
    if tail:
        rep.find("Have the customer also know: " + tail)
    path = SPEC_RULE_CONSOLE_PATH.get(topic)
    if path:
        rep.find("Have the customer use this entry: " + path + ".")
    for notice in SPEC_RULE_TAILS.get(topic, ()):
        rep.find(notice)
    if topic in SPEC_RULE_MONEY_TOPICS:
        for notice in SPEC_RULE_MONEY_NOTICES:
            rep.find(notice)
    if topic in SPEC_RULE_ACTIVITY_TOPICS:
        rep.find(ACTIVITY_REFERENCE_NOTICE)
    rep.data["rule_topic"] = topic
    rep.data["rule_only"] = topic in SPEC_RULE_ONLY_TOPICS
    return topic


# ---------------------------------------------------------------------------
# S3 change-object routing + guidance-only paths (C9, offline)
# ---------------------------------------------------------------------------

def do_guidance(rep, obj, availability_blocker=False):
    rep.section("C9 guidance for the chosen change object")
    if obj == "spec":
        rep.find("Spec change feasibility needs the instance line: run with "
                 "--instance-id (plus --target-type). Meanwhile relay the "
                 "five mandatory notices:")
        notices = CHANGE_NOTICES
        if availability_blocker:
            notices = CHANGE_NOTICES[4:5] + CHANGE_NOTICES[:4]
        for notice in notices:
            rep.find(f"* {notice}")
        rep.find("* " + DYNAMIC_PRICE_NOTICE)
        rep.find(f"* {EFFECT_STATEMENTS[0]}")
        rep.find(f"* {RESTART_RISK}")
        for s in (SNAPSHOT_ADVICE[:1] if availability_blocker else SNAPSHOT_ADVICE):
            rep.find(f"* {s}")
        if availability_blocker:
            rep.find("* Have the customer re-check the change page (stock is "
                     "instantaneous, no restock promise); try another zone/family, "
                     "or buy + migrate (public IP may change).")
        else:
            rep.find("* Disk resize (system/data disk) is a separate flow, not part "
                     "of an instance-type change.")
    elif obj == "bandwidth":
        for r in TEMP_BANDWIDTH_RULES:
            rep.find(f"* {r}")
        rep.find("* " + BILLING_CONVERSION_NOTE)
        rep.find("* " + DYNAMIC_PRICE_NOTICE)
    elif obj == "billing-conversion":
        rep.find("* " + BILLING_CONVERSION_NOTE)
        for line in IRREVERSIBLE_NOTICES["bandwidth_eip"]:
            rep.find(f"* {line}")
        rep.find("* " + PRICE_DISCLAIMER[0])
        rep.find("* " + PRICE_DISCLAIMER[1])
    elif obj == "disk":
        rep.find("* " + DISK_HANDOFF)
    elif obj == "disk-type":
        rep.find("* " + DISK_TYPE_NOTE)
        for line in CHANGE_NOTICES[:2]:
            rep.find(f"* {line}")
    else:
        rep.find("* " + OTHER_HANDOFF)


# ---------------------------------------------------------------------------
# C6 estimate line (best-effort query; console self-check as fallback)
# ---------------------------------------------------------------------------

def do_estimate(rep, inst, target_type, direction, profile):
    region = str(inst.get("_region") or DEFAULT_REGION)
    rep.section("C6 estimated change cost (ESTIMATE ONLY)")
    try:
        pmod = _cli.call("bssopenapi", "DescribePricingModule",
                         {"ProductCode": "ecs",
                          "SubscriptionType": "Subscription"},
                         region=region, profile=profile)
        modules = _dig(pmod, ["Data", "ModuleList", "Module"], []) or []
        codes = sorted({str(m.get("ModuleCode")) for m in modules
                        if isinstance(m, dict) and m.get("ModuleCode")})
        rep.data["pricing_modules"] = codes
        rep.find(f"pricing modules (ecs / Subscription): "
                 f"{', '.join(codes) if codes else 'none reported'}")
    except _cli.CliError as err:
        rep.degrade("DescribePricingModule", err)
    order_type = "Upgrade" if direction != "downgrade" else "Downgrade"
    try:
        price = _cli.call("bssopenapi", "GetSubscriptionPrice",
                          {"ProductCode": "ecs",
                           "SubscriptionType": "Subscription",
                           "OrderType": order_type,
                           "InstanceId": inst.get("InstanceId"),
                           "ModuleList.1.ModuleCode": "instance_type",
                           "ModuleList.1.Config":
                               f"InstanceType:{target_type},Region:{region}"},
                          region=region, profile=profile)
        data = price.get("Data") or {}
        rep.data["estimate"] = {
            "original_price": data.get("OriginalPrice"),
            "discount_price": data.get("DiscountPrice"),
            "trade_amount": data.get("TradeAmount"),
            "currency": data.get("Currency"),
        }
        rep.find(f"query-channel estimate: original "
                 f"{data.get('OriginalPrice', 'n/a')} / discount "
                 f"{data.get('DiscountPrice', 'n/a')} / payable "
                 f"{data.get('TradeAmount', 'n/a')} "
                 f"{data.get('Currency', '')}")
    except _cli.CliError as err:
        rep.degrade("GetSubscriptionPrice", err)
        rep.find("no numeric estimate from the query channel (module config "
                 "rejected or permission gap); fall back to the console "
                 "change page reading below")
    for s in PRICE_DISCLAIMER:
        rep.find(f"* {s}")


# ---------------------------------------------------------------------------
# Mandatory notice bundle (C9 / inform-first gate)
# ---------------------------------------------------------------------------

def do_notices(rep, direction):
    rep.section("MANDATORY notices (relay every line to the customer)")
    for n in CHANGE_NOTICES:
        rep.find(f"* {n}")
    for s in EFFECT_STATEMENTS:
        rep.find(f"* {s}")
    if direction == "downgrade":
        rep.find(f"* {RESTART_RISK}")
    for s in SNAPSHOT_ADVICE:
        rep.find(f"* {s}")


# ---------------------------------------------------------------------------
# CLI plumbing / flow
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        prog="assess_spec_change.py",
        description=(f"{SKILL_NAME}: feasibility assessment for ECS spec "
                     f"change and purchase using query-only cloud calls; "
                     f"answers {FIVE_QUESTIONS} Every change action itself "
                     f"is executed by the customer in the console."),
        epilog=("Only the whitelisted actions declared in related_apis.yaml "
                "are ever invoked. Exit codes: 0 = OK or DEGRADED, "
                "1 = FAIL (missing input or failed identity gate)."),
    )
    p.add_argument("--region-id", default=None,
                   help=f"region id; auto-filled to {DEFAULT_REGION} when "
                        f"cloud calls are needed and the region is unknown "
                        f"(declared in the report)")
    p.add_argument("--instance-id", default=None,
                   help="ECS instance id (i-...); an ecs.* value is a spec "
                        "name, not an instance id, and gets corrected")
    p.add_argument("--target-type", default=None,
                   help="target instance type (ecs.*)")
    p.add_argument("--direction", choices=["upgrade", "downgrade"],
                   default=None)
    p.add_argument("--charge-type", choices=["PrePaid", "PostPaid"],
                   default=None,
                   help="billing filter for the inventory scan "
                        "(PrePaid = subscription)")
    p.add_argument("--zone-id", default=None,
                   help="restrict the inventory scan to one zone")
    p.add_argument("--cores", type=int, default=None,
                   help="vCPU tier for the substitute scan")
    p.add_argument("--memory", type=float, default=None,
                   help="memory tier in GiB for the substitute scan")
    p.add_argument("--error-string", default=None,
                   help="verbatim error text to triage (C7, offline)")
    p.add_argument("--change-object",
                   choices=["spec", "bandwidth", "billing-conversion",
                            "disk", "disk-type", "other-product"],
                   default=None, help="S3 routing (guidance output)")
    p.add_argument("--availability-blocker", action="store_true",
                   help="the customer reports the target type is missing from the "
                        "change page or sold out; adds the change-set/stock rules")
    p.add_argument("--list-targets", action="store_true",
                   help="print this instance's modifiable target set")
    p.add_argument("--check-inventory", action="store_true",
                   help="run the region inventory scan (C4)")
    p.add_argument("--verify-effective", action="store_true",
                   help="compare the inventory spec vs --target-type (C8)")
    p.add_argument("--estimate", action="store_true",
                   help="run the estimate-only pricing line (C6)")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI profile name")
    p.add_argument("--json", action="store_true", help="JSON output")
    return p


def _validate(rep, args):
    if args.instance_id:
        if TYPE_ID_RE.match(args.instance_id):
            rep.fail(f"'{args.instance_id}' is an instance TYPE name, not an "
                     f"instance ID.",
                     "ask the customer for the i-... instance ID from the "
                     "console instance list, then re-run")
            return False
        if not INSTANCE_ID_RE.match(args.instance_id):
            rep.warn("instance id does not match the usual i-... shape; "
                     "proceeding, the lookup will confirm")
    if args.target_type and not TYPE_ID_RE.match(args.target_type):
        rep.fail(f"'{args.target_type}' is not an ecs.* instance type.",
                 "confirm the exact type name with the customer (console "
                 "spec column) and re-run")
        return False
    if args.region_id and not REGION_ID_RE.match(args.region_id):
        rep.fail(f"invalid --region-id '{args.region_id}'",
                 "use a region id such as cn-hangzhou from the console "
                 "region picker")
        return False
    if args.zone_id and not ZONE_ID_RE.match(args.zone_id):
        rep.fail(f"invalid --zone-id '{args.zone_id}'",
                 "use a zone id such as cn-hangzhou-h")
        return False
    if args.cores is not None and not 1 <= args.cores <= 512:
        rep.fail("--cores out of range (1..512)", "correct the tier and re-run")
        return False
    if args.memory is not None and not 0.5 <= args.memory <= 8192:
        rep.fail("--memory out of range (0.5..8192 GiB)",
                 "correct the tier and re-run")
        return False
    return True


def cloud_needed(args):
    return bool(args.instance_id or args.list_targets or args.estimate
                or args.check_inventory or args.verify_effective)


def run(args):
    rep = Report()
    if not _validate(rep, args):
        return rep
    do_rule_answer(rep, os.environ.get("ECS_CUSTOMER_QUESTION", ""),
                   args.change_object)
    if args.error_string:
        do_triage(rep, args.error_string)
    if args.change_object:
        do_guidance(rep, args.change_object, args.availability_blocker)
    if not cloud_needed(args):
        if not (args.error_string or args.change_object
                or rep.data.get("rule_topic")):
            rep.fail("nothing to do: pass --instance-id (with optional "
                     "--target-type / --list-targets / --estimate / "
                     "--verify-effective), or --check-inventory with "
                     "--region-id and --target-type, or --error-string, or "
                     "--change-object",
                     "collect the missing input from the customer (instance "
                     "id / region / verbatim error text) and re-run")
        return rep

    region = args.region_id
    if not region and args.instance_id:
        region = DEFAULT_REGION
        rep.auto_filled.append(
            f"--region-id defaulted to {DEFAULT_REGION}; if the instance "
            f"lives in another region the lookup fails and the report says "
            f"so -- re-run with the real region instead of guessing")
    if not region and (args.check_inventory or args.list_targets
                       or args.verify_effective or args.estimate):
        region = DEFAULT_REGION
        rep.auto_filled.append(
            f"--region-id defaulted to {DEFAULT_REGION} for the "
            f"inventory/pricing scan")

    if do_identity(rep, args.profile) is None:
        return rep

    inst = None
    if args.instance_id:
        inst = do_instance(rep, region, args.instance_id, args.profile)
        if inst is None:
            return rep
        region = inst["_region"]

    entries = None
    if inst is not None and (args.target_type or args.list_targets):
        entries = do_targets(rep, region, args.instance_id, args.direction,
                             args.target_type, args.profile)

    if args.check_inventory or (
            args.target_type and entries is not None
            and not rep.data.get("target_in_set", True)):
        inv = do_inventory(rep, region, args.target_type, args.charge_type,
                           args.zone_id, args.profile)
        if args.target_type and inv is not None and not rep.data.get(
                "target_zones"):
            cores = args.cores or _dig(rep.data, ["instance", "cpu"])
            mem_gib = args.memory
            if mem_gib is None:
                mib = _dig(rep.data, ["instance", "memory_mib"])
                if isinstance(mib, (int, float)):
                    mem_gib = mib / 1024.0
            do_substitutes(rep, region, args.target_type, cores, mem_gib,
                           inv, args.profile)

    if inst is not None and args.verify_effective and args.target_type:
        do_verify(rep, inst, args.target_type)

    if inst is not None and args.estimate and args.target_type:
        do_estimate(rep, inst, args.target_type, args.direction, args.profile)

    if inst is not None:
        do_notices(rep, args.direction)
    return rep


def next_action_for(rep, args):
    """Mandatory output contract for the agent: what to do with the report."""
    if rep.fatal:
        return rep.fatal_next
    cat = rep.data.get("triage")
    d = rep.data
    if d.get("effective_check"):
        return ("relay the C8 verdict plus the three effectiveness "
                "statements and the snapshot advice; the customer restarts "
                "in the console themselves; if the order was paid but the "
                "spec differs, record the order number and hand off to a "
                "human (this tier has no order APIs)")
    if d.get("target_in_set") is True:
        return ("change is feasible at the platform level; relay the full "
                "MANDATORY notices bundle (stop window for downgrades, "
                "refund-may-be-0, promotion loss, family limits, snapshot "
                "advice, estimate disclaimer) BEFORE the customer performs "
                "the change in the ECS console")
    if d.get("target_in_set") is False:
        return ("explain change-set vs buy-page difference with the listed "
                "evidence; offer the in-stock substitutes from S5; if the "
                "customer prefers a new purchase or clone, prepend the "
                "IP-change risk notice from references/spec-change-purchase__change-rules.md")
    if cat in ("quota-refund-vcpu", "quota-regional",
               "quota-insufficient-multi-cause"):
        return ("follow references/spec-change-purchase__quota-triage.md: billing-center check "
                "first for 'quota insufficient' wording, then the quota "
                "material template; submission and approval are human-only")
    if cat == "inventory-nostock" or cat == "inventory-wording":
        return ("relay the per-zone stock from S5 with substitutes; state "
                "the instantaneous-stock caveat verbatim; reservation or "
                "business coordination goes to a human plus business manager")
    if cat == "guest-side-after-change":
        return ("confirm the inventory spec first, then hand off the "
                "in-guest symptom per references/spec-change-purchase__handoff-map.md (snapshot + "
                "downtime window + authorization are the usual on-machine "
                "prerequisites)")
    if cat == "storage-performance-limit":
        return ("do not improvise a disposition: acknowledge the code, and "
                "for disk IO symptoms route to area:resource-bottleneck per"
                "references/spec-change-purchase__error-codes.md (pending review "
                "item 8-7)")
    if d.get("inventory"):
        return ("relay the stock table with the caveat verbatim; suggest "
                "only substitutes proven by the scan; never promise a "
                "time when stock returns")
    if args.change_object in ("disk", "other-product"):
        return ("deliver the boundary sentence and the receiving skill / "
                "product route; no further ECS change guidance from this "
                "tier")
    if RED_LINE_NO_STOCK_REFUND and d.get("estimate"):
        return ("relay the estimate ONLY with both disclaimer lines, then "
                "point the customer to the console change page expected "
                "values before they confirm anything themselves")
    return ("relay findings, apply the mandatory notices where a change is "
            "discussed, and hand off anything order-, approval- or "
            "guest-side per references/spec-change-purchase__handoff-map.md")


def emit(rep, args):
    status = "FAIL" if rep.fatal else ("DEGRADED" if rep.warnings else "OK")
    nxt = next_action_for(rep, args)
    if args.json:
        out = {
            "skill": SKILL_NAME,
            "status": status,
            "next_action": nxt,
            "findings": rep.lines,
            "warnings": rep.warnings,
            "auto_filled": rep.auto_filled,
            "data": rep.data,
            "api_versions": API_VERSIONS,
        }
        if rep.fatal:
            out["fatal"] = rep.fatal
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print("=" * 72)
        print(f"{SKILL_NAME} -- assessment (query-only; changes are made "
              f"by the customer in the console)")
        print("=" * 72)
        if rep.fatal:
            print(f"[FAIL] {rep.fatal}")
        for line in rep.lines:
            print(line)
        if rep.auto_filled:
            print("\n--- auto-filled parameters (declared) ---")
            for a in rep.auto_filled:
                print(f"* {a}")
        if rep.warnings:
            print("\n--- degradations (named gaps; report still usable) ---")
            for w in rep.warnings:
                print(f"! {w}")
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {nxt}")
    return 1 if rep.fatal else 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    rep = run(args)
    return emit(rep, args)


if __name__ == "__main__":
    sys.exit(main())
