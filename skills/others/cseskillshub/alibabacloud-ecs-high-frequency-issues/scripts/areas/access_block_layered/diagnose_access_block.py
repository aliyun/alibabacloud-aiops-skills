#!/usr/bin/env python3
"""
diagnose_access_block.py -- Single entry point for layered access-block
diagnosis of Alibaba Cloud ECS instances.

WHAT THIS TOOL DOES
  Walks the block layers self-outside-in (L0 client -> L7 outside-platform,
  see references/access-block-layered__layer-model.md) and produces a per-layer verdict table with
  evidence, exact manual remediation steps, the evidence list to request
  from the customer, and handoff suggestions.

CLOUD ACTIONS IT CALLS (whitelist enforced in _constants.py):
  * identity check via STS GetCallerIdentity
  * ecs product reads: DescribeInstances, DescribeSecurityGroups,
    DescribeSecurityGroupAttribute, DescribeInvocations
  * cloud firewall policy read (describe-control-policy) and WAF instance
    existence read (describe-instance), both degrading gracefully
  * ONE gated action: the RunCommand action of the ecs product, used ONLY to
    execute a single whitelisted non-mutating inspection command from
    GUEST_CHECKS in _constants.py. The whitelist is read-only and double-guarded
    by PROHIBITED_COMMAND_TOKENS, so these checks are query-only and
    auto-approved (no confirmation gate); --user-confirmed is still accepted
    for backward compatibility. Any check not on the whitelist is refused.

The tool NEVER executes rule changes, firewall toggles, kernel parameter
writes, captures, restarts or any other mutation - those appear only as
manual guidance text. Failures are [WARN] lines + entries in errors[]; the
report is still emitted. Output ends with STATUS: OK|DEGRADED|BLOCKED and
NEXT_ACTION: <instruction> (exit 0 for OK/DEGRADED, exit 1 for BLOCKED or
hard failure, 2 for argparse usage errors).

Usage examples:
  python3 diagnose_access_block.py --region-id cn-hangzhou \
      --instance-id i-example --direction ingress --port 443 \
      --protocol tcp --source-ip 203.0.113.9 \
      --symptom "Connection timed out"
  python3 diagnose_access_block.py --region-id cn-hangzhou --ip 101.37.0.42 \
      --direction internal --port 9101 --source-ip 172.25.0.9 \
      --target-ip 172.25.197.63 --symptom "No route to host"
  python3 diagnose_access_block.py --region-id cn-hangzhou \
      --instance-id i-example --guest-check firewalld-rules --user-confirmed
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import ipaddress
import json
import os
import re
import sys
import time
from typing import Any, Optional

import _cli
from _constants import (
    ALIYUN_INTERNAL_RANGE,
    CAPABILITY_GAPS,
    CFW_ACTION_DROP,
    CFW_ACTION_LOG,
    CFW_DIRECTION_IN,
    CFW_PAGE_SIZE,
    DEFAULT_REGION,
    DOC_LINKS,
    EGRESS_IP_LOOKUP,
    GUEST_CHECKS,
    GUEST_MAX_WAIT_SECONDS,
    GUEST_POLL_INTERVAL_SECONDS,
    GUEST_RUN_TIMEOUT,
    LAYER_NAMES,
    POLICY_ACCEPT,
    POLICY_DROP,
    PROHIBITED_COMMAND_TOKENS,
    SG_TYPE_ENTERPRISE,
    SYMPTOM_LAYER_MAP,
    WELL_KNOWN_PORTS,
)

EXCLUDED = "EXCLUDED"
HIT = "HIT"
UNKNOWN = "UNKNOWN"
NOT_APPLICABLE = "NOT_APPLICABLE"


# ---------------------------------------------------------------------------
# Small parse helpers (defensive against response-shape drift)
# ---------------------------------------------------------------------------

def _dig(obj: Any, path: list[str]) -> Any:
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _find_dicts(node: Any, required_keys: tuple[str, ...]) -> list[dict]:
    """Return every dict under an arbitrary nested list/dict shape carrying
    all of required_keys (tolerates Item-wrapper drift across API versions)."""
    found: list[dict] = []
    if isinstance(node, dict):
        if all(k in node for k in required_keys):
            found.append(node)
        for value in node.values():
            found.extend(_find_dicts(value, required_keys))
    elif isinstance(node, list):
        for item in node:
            found.extend(_find_dicts(item, required_keys))
    return found


# ---------------------------------------------------------------------------
# 5-tuple matching primitives (security-group rule semantics)
# ---------------------------------------------------------------------------

def _port_matches(port_range: str, port: Optional[int]) -> bool:
    pr = (port_range or "").strip().lower()
    if pr in ("-1/-1", "", "any", "0/0"):
        return True  # all ports (also ICMP/ALL convention)
    try:
        lo_s, _, hi_s = pr.partition("/")
        lo, hi = int(lo_s), int(hi_s or lo_s)
    except ValueError:
        return False
    if port is None:
        return True
    return lo <= port <= hi


def _protocol_matches(rule_proto: str, proto: str) -> bool:
    rp = (rule_proto or "").upper()
    return rp in ("ALL", proto.upper())


def _normalize_peer(peer: Optional[str]) -> Optional[str]:
    """Accept a bare IP or a CIDR; collapse a CIDR to its network address so
    coverage math stays single-address based."""
    if not peer:
        return None
    peer = peer.strip()
    if "/" in peer:
        try:
            return str(ipaddress.ip_network(peer, strict=False).network_address)
        except ValueError:
            return peer
    return peer


def _cidr_covers(rule_cidr: str, peer: Optional[str]) -> bool:
    """True when the rule's address range covers the peer address.
    peer None means 'any source' - covered only by an all-address rule."""
    cidr = (rule_cidr or "").strip() or "0.0.0.0/0"
    if peer is None:
        return cidr == "0.0.0.0/0"
    try:
        peer_obj = ipaddress.ip_address(peer)
        net = ipaddress.ip_network(cidr, strict=False)
        return peer_obj in net
    except ValueError:
        return False


def _peer_covers(rule: dict, direction: str, peer: Optional[str]) -> bool:
    """Stack-aware source/dest match. An empty IPv4 field on a rule that carries
    an explicit IPv6 range means the rule is IPv6-only - it must NOT be treated
    as an all-address allow for IPv4 peers (found by the faultlab state flip:
    the ALL/-1/-1 rule with only Ipv6SourceCidrIp wrongly 'allowed' TCP 8080)."""
    if direction == "ingress":
        v4 = (rule.get("SourceCidrIp") or "").strip()
        v6 = (rule.get("Ipv6SourceCidrIp") or "").strip()
    else:
        v4 = (rule.get("DestCidrIp") or "").strip()
        v6 = (rule.get("Ipv6DestCidrIp") or "").strip()
    if peer is None:
        if v6 and v6 != "::/0" and not v4:
            return False  # restricted to one address family: not "any"
        return v4 in ("", "0.0.0.0/0")
    if ":" in peer:
        if not v6 and v4:
            return False  # IPv4-only rule cannot match an IPv6 peer
        return _cidr_covers(v6 or v4, peer)
    if not v4 and v6:
        return False      # IPv6-only rule cannot match an IPv4 peer
    return _cidr_covers(v4, peer)


def _looks_like_ip(text: str) -> bool:
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False


def _eval_sg(rules: list[dict], direction: str, peer: Optional[str],
             proto: str, port: Optional[int]) -> dict:
    """Evaluate the merged rule set of all bound groups for one direction.

    Returns a verdict dict:
      result: 'allow' | 'drop' | 'no-cover' | 'unevaluable'
      matched_rule: the first-match rule (dict) when one matched
    First match wins: ascending Priority, Drop before Accept at equal
    priority (official semantics, references/access-block-layered__security-group-pitfalls.md).
    """
    unevaluable = False
    candidates: list[tuple[int, int, dict]] = []
    for idx, rule in enumerate(rules):
        if (rule.get("Direction") or "").lower() != direction:
            continue
        has_peer = ((rule.get("SourceCidrIp") or rule.get("DestCidrIp")
                     or rule.get("Ipv6SourceCidrIp") or rule.get("Ipv6DestCidrIp")
                     or rule.get("SourcePrefixListId") or rule.get("DestPrefixListId")
                     or rule.get("SourceGroupId") or rule.get("DestGroupId")))
        if has_peer and (rule.get("SourceGroupId") or rule.get("DestGroupId")
                         or rule.get("SourcePrefixListId") or rule.get("DestPrefixListId")):
            unevaluable = True  # group/prefix-list peer: cannot expand here
            continue
        if not _protocol_matches(rule.get("IpProtocol", "ALL"), proto):
            continue
        if direction == "ingress" and not _peer_covers(rule, "ingress", peer):
            continue
        if direction == "egress" and not _peer_covers(rule, "egress", peer):
            continue
        if not _port_matches(rule.get("PortRange", "-1/-1"), port):
            continue
        try:
            prio = int(rule.get("Priority") or 1)
        except (TypeError, ValueError):
            prio = 1
        order = 0 if (rule.get("Policy") or "").lower() == "drop" else 1
        candidates.append((prio, order * 1000 + idx, rule))

    if not candidates:
        return {"result": "unevaluable" if unevaluable else "no-cover",
                "matched_rule": None}
    candidates.sort(key=lambda t: (t[0], t[1]))
    first = candidates[0][2]
    result = "drop" if (first.get("Policy") or "").lower() == "drop" else "allow"
    return {"result": result, "matched_rule": first}


# ---------------------------------------------------------------------------
# Target resolution (instance / IP -> instance fact sheet)
# ---------------------------------------------------------------------------

def resolve_instance(region: str, instance_id: Optional[str], ip: Optional[str],
                     profile: Optional[str], errors: list[str]) -> Optional[dict]:
    """Return the DescribeInstances record for the target, or None."""
    params: dict[str, Any] = {"RegionId": region, "PageSize": 10}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    elif ip:
        probe = dict(params)
        probe["PublicIpAddresses"] = ip
        body = _cli.call("ecs", "DescribeInstances", probe, region=region, profile=profile)
        insts = _dig(body, ["Instances", "Instance"]) or []
        if not insts:
            probe = dict(params)
            probe["PrivateIpAddresses"] = ip
            body = _cli.call("ecs", "DescribeInstances", probe, region=region, profile=profile)
            insts = _dig(body, ["Instances", "Instance"]) or []
        if not insts:
            # same-VPC peer of another instance is not resolvable region-wide:
            # fall through with an inner-ip probe, else report not-found
            probe = dict(params)
            probe["InnerIpAddresses"] = ip
            try:
                body = _cli.call("ecs", "DescribeInstances", probe,
                                 region=region, profile=profile)
                insts = _dig(body, ["Instances", "Instance"]) or []
            except _cli.CliError as e:
                errors.append(f"resolve ip: {e}")
        if not insts:
            errors.append(f"no instance found in {region} for ip {ip}")
            return None
        return insts[0] if insts else None
    try:
        body = _cli.call("ecs", "DescribeInstances", params, region=region, profile=profile)
    except _cli.CliError as e:
        errors.append(f"resolve instance: {e}")
        return None
    insts = _dig(body, ["Instances", "Instance"]) or []
    if not insts:
        errors.append(f"instance {instance_id} not found in region {region}")
        return None
    return insts[0]


# ---------------------------------------------------------------------------
# L4 security-group layer
# ---------------------------------------------------------------------------

def check_security_groups(region: str, instance: dict, direction: str,
                          peer: Optional[str], proto: str, port: Optional[int],
                          profile: Optional[str], errors: list[str]) -> dict:
    sg_ids = _dig(instance, ["SecurityGroupIds", "SecurityGroupId"]) or []
    if isinstance(sg_ids, str):
        sg_ids = [sg_ids]
    verdict: dict[str, Any] = {
        "layer": "L4", "name": LAYER_NAMES["L4"], "state": UNKNOWN,
        "evidence": [], "manual_steps": [],
    }
    if not sg_ids:
        verdict["evidence"].append("instance reports no bound security groups")
        return verdict

    # Types (normal vs enterprise) - the enterprise default-deny egress fact
    # is decisive for outbound cases (evidence ticket T-B091EED8).
    types: dict[str, str] = {}
    try:
        body = _cli.call("ecs", "DescribeSecurityGroups",
                         {"RegionId": region, "SecurityGroupIds": json.dumps(sg_ids),
                          "PageSize": 50},
                         region=region, profile=profile)
        for sg in _find_dicts(_dig(body, ["SecurityGroups"]) or body, ("SecurityGroupId",)):
            types[str(sg.get("SecurityGroupId"))] = str(sg.get("SecurityGroupType") or "normal")
    except _cli.CliError as e:
        errors.append(f"describe security groups: {e}")
        verdict["evidence"].append(f"security group type query failed: {e}")

    all_rules: list[dict] = []
    failed_sgs: list[str] = []
    for sg_id in sg_ids:
        try:
            # DescribeSecurityGroupAttribute takes NO pagination parameters (verified
            # 2026-09-24: PageNumber/PageSize/NextToken all rejected by the CLI); it
            # returns the full rule set in one call - paginating it used to fail the
            # query silently and fake a no-cover HIT on an empty rule list.
            body = _cli.call("ecs", "DescribeSecurityGroupAttribute",
                             {"RegionId": region, "SecurityGroupId": sg_id},
                             region=region, profile=profile)
            rules = _dig(body, ["Permissions", "Permission"]) or []
            for r in rules:
                r = dict(r)
                r["_sg"] = sg_id
                all_rules.append(r)
        except _cli.CliError as e:
            failed_sgs.append(sg_id)
            errors.append(f"describe sg {sg_id}: {e}")
            verdict["evidence"].append(f"rule query failed for {sg_id}: {e}")

    eval_direction = "egress" if direction == "egress" else "ingress"
    res = _eval_sg(all_rules, eval_direction, peer, proto, port)
    verdict["rule_count"] = len(all_rules)
    if failed_sgs and res["result"] != "allow":
        # A negative verdict built on partially unread rule sets is not evidence:
        # report the layer as UNKNOWN instead of blaming the security group.
        verdict["state"] = UNKNOWN
        verdict["evidence"].append(
            f"rule sets for {', '.join(failed_sgs)} were unreadable this run; L4 cannot "
            "be decided from partial data - retry, or manual console rule review requested")
        return verdict
    verdict["groups"] = {sg_id: types.get(sg_id, "unknown") for sg_id in sg_ids}

    ev = (f"direction={eval_direction} proto={proto} port={port if port is not None else 'n/a'} "
          f"peer={peer or 'UNSPECIFIED'}; groups: "
          + ", ".join(f"{k}({v})" for k, v in verdict["groups"].items()))
    verdict["evidence"].append(ev)

    if res["result"] == "allow":
        verdict["state"] = EXCLUDED
        rule = res["matched_rule"]
        verdict["evidence"].append(
            f"first-match allow: group {rule.get('_sg')} {rule.get('IpProtocol')} "
            f"{rule.get('PortRange')} prio {rule.get('Priority')} "
            f"src/dst {(rule.get('SourceCidrIp') or rule.get('DestCidrIp') or '0.0.0.0/0')!r}")
    elif res["result"] == "drop":
        verdict["state"] = HIT
        rule = res["matched_rule"]
        verdict["verdict_detail"] = (
            f"an explicit Drop rule blocks {proto}/{port} for peer {peer} "
            f"(group {rule.get('_sg')}, priority {rule.get('Priority')})")
        verdict["manual_steps"] = sg_manual_steps(eval_direction, proto, port, peer)
    elif res["result"] == "no-cover":
        enterprise_egress = (eval_direction == "egress"
                             and any(v == SG_TYPE_ENTERPRISE for v in types.values()))
        if eval_direction == "ingress":
            if peer is None:
                verdict["state"] = UNKNOWN
                verdict["evidence"].append(
                    "no covering allow rule for an ANY peer; provide the client egress IP "
                    "(lookups: " + ", ".join(EGRESS_IP_LOOKUP) + ") for a decisive verdict")
            else:
                verdict["state"] = HIT
                verdict["verdict_detail"] = (
                    f"no ingress allow rule covers {proto}/{port} from {peer}; unmatched "
                    "ingress traffic is denied by the security-group default policy")
                verdict["manual_steps"] = sg_manual_steps(eval_direction, proto, port, peer)
        elif enterprise_egress:
            verdict["state"] = HIT
            verdict["verdict_detail"] = (
                "enterprise security group: egress defaults to DENY and no allow rule "
                f"covers {proto}/{port} to {peer or 'the target'} - a classic cause of "
                "console-side functions and outbound calls failing")
            verdict["manual_steps"] = sg_manual_steps(eval_direction, proto, port, peer)
        else:
            verdict["state"] = EXCLUDED
            verdict["evidence"].append(
                "no rule matched, but normal security groups allow unmatched egress by default")
    else:
        verdict["state"] = UNKNOWN
        verdict["evidence"].append(
            "some rules authorize other security groups or prefix lists and cannot be "
            "expanded by this read path; manual review requested")
    return verdict


def sg_manual_steps(direction: str, proto: str, port: Optional[int],
                    peer: Optional[str]) -> list[str]:
    port_txt = str(port) if port is not None else "the target port"
    peer_txt = peer or "<client public egress CIDR>"
    dir_word = "Inbound" if direction == "ingress" else "Outbound"
    return [
        f"Manual step (not executed by this skill): ECS console -> Instances -> the target "
        f"instance -> Security Groups -> Manage Rules -> {dir_word} -> Add a rule allowing "
        f"{proto.upper()} port {port_txt} for peer {peer_txt} (policy Accept, priority high "
        "number = low precedence is NOT recommended; keep the smallest workable source range).",
        "Least privilege: never widen to 0.0.0.0/0 permanently. For remote-admin ports keep "
        f"the customer egress CIDR only; lookups to obtain it: {', '.join(EGRESS_IP_LOOKUP)}.",
        f"If the instance is inside an enterprise security group and the failing path is "
        f"OUTBOUND, also allow {proto.upper()} {port_txt} toward the destination "
        "(Alibaba service endpoints are commonly reachable via the "
        f"{ALIYUN_INTERNAL_RANGE} internal range check before widening).",
        "Before ANY change: create a snapshot of the data disks first (a customer-executed step: console or CreateSnapshot, "
        f"billing applies): {DOC_LINKS['create_snapshot']}.",
        f"Rule syntax reference: {DOC_LINKS['sg_manage_rules']} and {DOC_LINKS['sg_modify_rules']}.",
    ]


# ---------------------------------------------------------------------------
# L2 platform protection layer (cloud firewall policy + WAF presence)
# ---------------------------------------------------------------------------

def check_platform_policy(region: str, direction: str, peer: Optional[str],
                          proto: str, port: Optional[int], skip: bool,
                          profile: Optional[str], errors: list[str]) -> dict:
    verdict: dict[str, Any] = {
        "layer": "L2", "name": LAYER_NAMES["L2"], "state": UNKNOWN,
        "evidence": [], "manual_steps": [],
    }
    if skip:
        verdict["state"] = NOT_APPLICABLE
        verdict["evidence"].append("platform-policy read skipped by request")
        return verdict

    cfw_direction = CFW_DIRECTION_IN if direction != "egress" else "out"
    try:
        body = _cli.call("cloudfw", "DescribeControlPolicy",
                         {"Direction": cfw_direction, "CurrentPage": 1,
                          "PageSize": CFW_PAGE_SIZE, "IpVersion": "4"},
                         region=region, profile=profile)
        policies = _find_dicts(body, ("AclAction",))
        verdict["evidence"].append(
            f"cloud firewall internet-boundary policies read: {len(policies)} "
            f"record(s) for direction {cfw_direction}")
        blocking = []
        for p in policies:
            action = str(p.get("AclAction") or "").lower()
            release = str(p.get("Release") or "true").lower()
            if release in ("false", "draft") or action not in (CFW_ACTION_DROP, CFW_ACTION_LOG):
                continue
            dst_port = str(p.get("DestPort") or "").replace(",", " ").split()
            port_ok = any(_port_matches(rp if "/" in rp else f"{rp}/{rp}", port)
                          for rp in dst_port) or not dst_port
            proto_ok = str(p.get("Proto") or "ANY").upper() in ("ANY", proto.upper())
            src = str(p.get("Source") or "0.0.0.0/0")
            src_norm = src if "/" in src else (f"{src}/32" if _looks_like_ip(src) else "0.0.0.0/0")
            peer_ok = _cidr_covers(src_norm, peer)
            if port_ok and proto_ok and peer_ok:
                blocking.append(p)
        if blocking:
            verdict["state"] = HIT
            verdict["verdict_detail"] = (
                f"{len(blocking)} enabled Cloud Firewall drop/log rule(s) match the flow; "
                "note that configured match is NOT proof of an actual hit - hit logs are a "
                "known capability gap (see report notes)")
            verdict["manual_steps"] = [
                f"Manual review: Cloud Firewall console -> Prevention Configuration -> Access "
                f"Control -> Internet Border ({cfw_direction} policies). Reference: "
                f"{DOC_LINKS['cloud_firewall']}",
            ]
        else:
            verdict["state"] = EXCLUDED
            verdict["evidence"].append(
                "no enabled cloud firewall policy on the internet boundary matches this "
                "flow's direction/protocol/port/peer (policy-configuration view only; "
                "hit records are not queryable by this build)")
    except _cli.CliError as e:
        # plugin missing / not purchased / NoPermission all degrade honestly
        errors.append(f"cloudfw describe-control-policy: {e}")
        verdict["state"] = UNKNOWN
        verdict["evidence"].append(
            f"cloud firewall policy read unavailable ({e.code or 'error'}); if the CLI "
            "plugin for Cloud Firewall is not installed this check degrades - do not "
            "conclude 'no platform policy blocks you' from this layer")

    try:
        waf_body = _cli.call("waf-openapi", "DescribeInstance",
                             {"RegionId": region}, region=region, profile=profile)
        inst = _find_dicts(waf_body, ("InstanceId",))
        if inst:
            verdict["evidence"].append(
                f"a WAF instance is present in this region ({inst[0].get('InstanceId')}); "
                "WAF hit/interception records are NOT queryable by this build - when the "
                "customer blames WAF, ask for the request ID from the WAF block page and "
                "hand the rule question to the WAF product side")
        else:
            verdict["evidence"].append("no WAF instance id reported for this region")
    except _cli.CliError as e:
        errors.append(f"waf-openapi describe-instance: {e}")
        verdict["evidence"].append(
            f"WAF presence unknown (query failed: {e.code or 'error'}); treat as "
            "unverified, ask the customer whether their domain is CNAME-fronted by WAF")
    return verdict


# ---------------------------------------------------------------------------
# Gated guest inspection (single whitelisted, non-mutating command)
# ---------------------------------------------------------------------------

def run_guest_check(region: str, instance: dict, check_name: str,
                    profile: Optional[str], errors: list[str]) -> dict:
    check = GUEST_CHECKS[check_name]
    command = check["command"]
    for token in PROHIBITED_COMMAND_TOKENS:
        if token in command:
            return {"layer": "L5", "state": UNKNOWN,
                    "evidence": [f"whitelist integrity error: token {token!r} present"]}

    os_type = str(instance.get("OSType") or "").lower()
    if os_type and check["os"] not in os_type:
        return {"layer": check["layer"], "state": UNKNOWN,
                "evidence": [f"refused: check targets {check['os']} but instance OS is {os_type}"]}

    instance_id = str(instance.get("InstanceId") or "")
    verdict: dict[str, Any] = {
        "layer": check["layer"], "state": UNKNOWN, "evidence": [],
        "check": check_name, "command": command,
        "meaning": check["meaning"],
        "output_excerpt": "",
    }
    try:
        body = _cli.call("ecs", "RunCommand", {
            "RegionId": region,
            "Type": check["run_type"],
            "CommandContent": command,
            "InstanceId": [instance_id],
            "Name": "ecs-access-block-layered-guest-check",
            "Timeout": GUEST_RUN_TIMEOUT,
            "Description": "layered access-block diagnosis (single non-mutating read)",
        }, region=region, profile=profile)
        invoke_id = str(body.get("InvokeId") or "")
        if not invoke_id:
            verdict["evidence"].append("guest check submit returned no invoke id")
            errors.append("RunCommand returned no InvokeId")
            return verdict
    except _cli.CliError as e:
        errors.append(f"guest check submit: {e}")
        verdict["evidence"].append(
            f"guest command channel unavailable ({e.code or 'error'}): the Cloud Assistant "
            "agent may be offline or the instance has no working egress (known pattern). "
            "Fall back: ask the customer to run this exact command manually and paste output.")
        return verdict

    verdict["evidence"].append(
        "guest check executed under the operator confirmation gate (one command only)")

    deadline = time.monotonic() + GUEST_MAX_WAIT_SECONDS
    record: Optional[dict] = None
    while time.monotonic() < deadline:
        time.sleep(GUEST_POLL_INTERVAL_SECONDS)
        try:
            body = _cli.call("ecs", "DescribeInvocations", {
                "RegionId": region, "InvokeId": invoke_id,
                "IncludeOutput": "true",
            }, region=region, profile=profile)
            recs = _find_dicts(body, ("InvocationStatus", "Output"))
            # single-instance invokes report "Success" at both the Invocation and
            # InvokeInstance layers (verified live 2026-10-20); "Finished" appears
            # in multi-instance / legacy payloads - accept both as terminal.
            if recs and str(recs[0].get("InvocationStatus")) in (
                    "Finished", "Success", "Failed", "Stopped", "Timeout",
                    "PartialFailed"):
                record = recs[0]
                break
        except _cli.CliError as e:
            errors.append(f"guest result read: {e}")
            break

    if record is None:
        verdict["state"] = UNKNOWN
        verdict["evidence"].append(
            "no final result within the wait window; degrade to manual paste path")
        return verdict

    raw = str(record.get("Output") or "")
    try:
        decoded = base64.b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "replace")
    except (base64.binascii.Error, ValueError):
        decoded = raw
    verdict["output_excerpt"] = _cli._mask_credentials(decoded)[:4000]
    verdict["exit_status"] = str(record.get("InvocationStatus") or "")
    verdict["state"] = UNKNOWN
    if record.get("InvocationStatus") not in ("Finished", "Success"):
        verdict["evidence"].append(
            f"command did not finish cleanly ({record.get('InvocationStatus')}); "
            "treat this layer as not-judged and fall back to manual paste")
    else:
        verdict["evidence"].append("raw non-mutating read captured (interpretation below)")
    return verdict


def _iptables_anomaly_line(out: str, port: Optional[int]) -> Optional[str]:
    """Return the first DROP/REJECT line from `iptables -S` / `-L -n -v` output
    that gates the target port (or an unconditional INPUT drop), else None."""
    for raw in out.splitlines():
        ln = raw.strip()
        up = ln.upper()
        if not (up.endswith("DROP") or up.endswith("REJECT")
                or " -J DROP" in up or " -J REJECT" in up):
            continue
        if ln.startswith("-P"):
            chain = ln.split()[1] if len(ln.split()) > 1 else ""
            if chain in ("INPUT", "FORWARD") and port is None:
                return ln
            continue
        if port is not None:
            if f"--dport {port} " in ln or f"--dport {port}" == ln[-len(f"--dport {port}"):]:
                return ln
            # a range covering the port, e.g. --dport 20:23
            m = re.search(r"--dport (\d+):(\d+)", ln)
            if m and int(m.group(1)) <= port <= int(m.group(2)):
                return ln
            if "--dport" not in ln and "INPUT" in up:
                return ln  # blanket INPUT drop affects every port
        else:
            if "INPUT" in up:
                return ln
    return None


def interpret_guest_output(verdict: dict, port: Optional[int]) -> None:
    """Small deterministic probes over captured output; anything less certain
    is left to the agent with the excerpt attached.

    Hard guard: when the guest channel returned NOTHING (submit failed, agent
    offline, non-zero status) no probe may flip the verdict to HIT - an absent
    read is unknown, not evidence (2026-10-20 direct run: empty ss output under
    Forbidden.RAM produced a fabricated 'no listening socket' HIT)."""
    out = verdict.get("output_excerpt") or ""
    status = str(verdict.get("exit_status") or "")
    if not out.strip() or (status and status not in ("Finished", "Success")):
        return
    low = out.lower()
    name = verdict.get("check")
    if name in ("iptables-rules", "iptables-counters"):
        deny_line = _iptables_anomaly_line(out, port)
        if deny_line:
            verdict["state"] = HIT
            verdict["probe"] = (f"live read shows a deny rule gating the flow: "
                                f"`{deny_line[:160]}` — this in-guest DROP/REJECT is the "
                                "confirmed blocking layer for this port; it is readable "
                                "evidence and must be delivered as the primary cause")
        elif port is not None and re.search(
                rf"-A INPUT .*--dport {port}\b.*-j ACCEPT", out):
            verdict["probe"] = (f"iptables explicitly ACCEPTs port {port}; no deny rule "
                                "found in the guest — the guest firewall layer is excluded "
                                "for this flow")
    elif name == "ufw-status":
        if "status: inactive" in low or "status: disabled" in low:
            verdict["probe"] = ("UFW reports inactive: the guest firewall is NOT the blocker "
                                "(look at listeners / security group instead)")
        elif "status: active" in low:
            verdict["probe"] = ("UFW is active. Verify the target port appears in an ALLOW "
                                "line whose source covers the real client, else it REJECTs/DROPs "
                                "the flow.")
    elif name in ("firewalld-state", "firewalld-rules"):
        if "not running" in low:
            verdict["probe"] = "firewalld not running: L5 firewalld ruled out (check raw iptables)"
        elif "running" in low:
            verdict["probe"] = ("firewalld running: hand-added iptables rules may be overridden "
                                "by firewalld; confirm the port is "
                                "in the active zone's allowed services/ports")
    elif name in ("listeners", "listeners-netstat", "windows-listeners"):
        if port is not None:
            listening = any(f":{port}" in line for line in out.splitlines())
            if listening:
                verdict["probe"] = (f"port {port} IS listening (verify the bind address is not "
                                    "127.0.0.1-only - loopback binding explains 'Connection refused' "
                                    "or local-only service)")
            else:
                verdict["state"] = HIT
                verdict["probe"] = (f"no listening socket found on port {port}: the service "
                                    "itself is the blocker; "
                                    "'Connection refused' from outside is expected")
    elif name == "kernel-tcp-params":
        if "tcp_tw_recycle" in low and "= 1" in out:
            verdict["probe"] = ("tcp_tw_recycle=1 with timestamps enabled drops new connections "
                                "from NAT'd clients (ping OK while every TCP connection fails). "
                                "Fix is a MANUAL sysctl change with snapshot first.")
    elif name == "recent-logins":
        verdict["probe"] = ("compare the source IPs reaching the instance against the "
                            "security-group authorized IP - a mismatch means the client egress "
                            "IP assumption is wrong")


# ---------------------------------------------------------------------------
# Symptom prior + L0/L1/L7 narrative
# ---------------------------------------------------------------------------

def symptom_priors(symptom: str) -> list[dict]:
    low = symptom.lower()
    hits = []
    for entry in SYMPTOM_LAYER_MAP:
        if any(n in low for n in entry["needles"]):
            hits.append(entry)
    return hits


def knowledge_block(direction: str, symptom: str, domain: Optional[str],
                    peers_missing: bool) -> dict:
    kb: dict[str, Any] = {"layers": {}, "handoffs": []}
    priors = symptom_priors(symptom) if symptom else []
    for entry in priors:
        for lay in entry["layer_priors"]:
            kb["layers"].setdefault(lay, []).append(entry["note"])

    l0 = kb["layers"].setdefault("L0", [])
    l0.append("Client-side differential, run by the customer and reported back: try a second "
              "network (phone hotspot), a second device, a second browser / incognito, and "
              "IP-direct vs domain access. Confirm the egress IP used for authorization "
              f"matches the live one ({', '.join(EGRESS_IP_LOOKUP)}); VPN or corporate "
              "proxies change it silently.")
    if peers_missing:
        l0.append("The client egress IP was not provided, so source-coverage matching is a "
                  "guess - collect it before touching any rule; customers routinely mis-read "
                  "a modem or office NAT LAN address as their public egress IP.")
    l0.append("If the customer only says 'SSH' or 'remote desktop' without a port, evaluate the "
              f"well-known defaults ({WELL_KNOWN_PORTS['ssh']} for SSH, {WELL_KNOWN_PORTS['rdp']} "
              "for RDP) and DECLARE the substitution in the report.")

    l1 = kb["layers"].setdefault("L1", [])
    reset_prior = any("L1" in entry["layer_priors"] for entry in priors)
    if domain or reset_prior:
        l1.append("Domain path: verify the DNS answer points at the expected instance IP. If "
                  "the domain resolves to a Chinese-mainland IP, the symptoms are RST-style, "
                  "the server firewall and logs show nothing, compare direct-IP access: the "
                  "leading hypothesis is compliance interception of an unfiled domain. "
                  "This build has NO filing-status query API, so state "
                  "it as an assumption with self-check steps and the filing guide: "
                  + DOC_LINKS["icp_filing"])
    else:
        l1.append("No domain involved or symptom is not reset-style: DNS/filing path only "
                  "becomes relevant for domain-based access.")

    kb["handoffs"] = [
        {"target": "vpc_route_link",
         "when": ("all platform layers below are EXCLUDED but a specific path/ISP/region "
                  "fails, or the customer mentions custom routes / NAT / EIP quality")},
        {"target": "disk_io",
         "when": "network layer measures healthy but the OS is unresponsive / load is pegged"},
        {"target": "instance_state",
         "when": "TCP reaches the login screen or the fix requires a reboot"},
    ]
    return kb


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def ranking_directive(verdicts: list[dict]) -> list[str]:
    """Deterministic verdict line computed from this run's live reads, emitted so
    the final report cannot bury a confirmed in-guest anomaly behind a
    speculative security-group claim (Round6 evidence: legs ran the probes, read
    the DROP rule, still ranked SG first and fabricated SG readings)."""
    hits = [v for v in verdicts if v.get("state") == HIT]
    excluded = [v for v in verdicts if v.get("state") == EXCLUDED]
    lines: list[str] = []
    lines.append("RANKING DIRECTIVE (computed by this tool from live reads in THIS run — "
                 "obey verbatim in the delivered report)")
    lines.append("-" * 72)
    if hits:
        for i, v in enumerate(hits, 1):
            quote = str(v.get("probe") or v.get("verdict_detail") or "")[:240]
            lines.append(f"  PRIMARY CAUSE CANDIDATE #{i} [{v['layer']}] {v.get('name')}: {quote}")
        lines.append("  Hard rule: deliver the candidate(s) above as the confirmed primary "
                     "cause and quote their read lines in the Executed checks block. Naming "
                     "any other layer as root cause while a HIT read stands above contradicts "
                     "the evidence this tool collected and is a report defect.")
    else:
        lines.append("  No layer produced a HIT read in this run: every root-cause statement "
                     "must be labelled UNVERIFIED (no live evidence); prefer the exclusions "
                     "below as the deliverable.")
    for v in excluded:
        lines.append(f"  EXCLUDED by live read [{v['layer']}] {v.get('name')}: do NOT name "
                     "this layer as root cause in the report.")
    sg = next((v for v in verdicts if v.get("layer") == "L4"), None)
    if sg is not None and sg.get("state") == EXCLUDED:
        lines.append("  Security-group check was READ and allows this flow — the SG is "
                     "formally excluded; an in-guest or service-layer explanation must be "
                     "ranked first even if it still needs one more probe.")
    return lines


def render(verdicts: list[dict], kb: dict, status: str, instance: Optional[dict],
           args: argparse.Namespace, errors: list[str], next_action: str) -> str:
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("ECS ACCESS-BLOCK LAYERED DIAGNOSIS")
    lines.append("=" * 72)
    if instance:
        lines.append(f"Target      : {instance.get('InstanceId')}  region {args.region_id}  "
                     f"status {instance.get('Status')}  OS {instance.get('OSType')}")
        pub = _dig(instance, ["PublicIpAddress", "IpAddress"]) or []
        eip = _dig(instance, ["EipAddress", "IpAddress"]) or ""
        priv = _dig(instance, ["VpcAttributes", "PrivateIpAddress", "IpAddress"]) or []
        lines.append(f"Addresses   : public {pub or '-'} eip {eip or '-'} private {priv or '-'}")
    lines.append(f"Flow        : direction={args.direction} protocol={args.protocol} "
                 f"port={args.port if args.port is not None else 'n/a'} "
                 f"peer={args.source_ip or args.target_ip or 'UNSPECIFIED'}")
    if args.symptom:
        lines.append(f"Symptom     : {args.symptom}")
    lines.append("")
    lines.append("LAYER VERDICTS")
    lines.append("-" * 72)
    for v in verdicts:
        state = v.get("state", UNKNOWN)
        lines.append(f"[{v['layer']}] {v['name']}  ->  {state}")
        for e in v.get("evidence", []):
            lines.append(f"    evidence: {e}")
        if v.get("verdict_detail"):
            lines.append(f"    detail  : {v['verdict_detail']}")
        if v.get("probe"):
            lines.append(f"    probe   : {v['probe']}")
        if v.get("check"):
            lines.append(f"    command : {v['command']}")
        if v.get("output_excerpt"):
            excerpt = v["output_excerpt"]
            lines.append("    output  :")
            for ln in excerpt.splitlines():
                if ln.strip():
                    lines.append(f"      | {ln[:200]}")
        for step in v.get("manual_steps", []):
            lines.append(f"    MANUAL  : {step}")
    lines.append("")
    lines.extend(ranking_directive(verdicts))
    lines.append("")
    lines.append("KNOWLEDGE & NEXT LAYER ACTIONS")
    lines.append("-" * 72)
    for lay in ("L0", "L1", "L7"):
        for note in kb["layers"].get(lay, []):
            lines.append(f"[{lay}] {note}")
    if not kb["layers"].get("L7"):
        lines.append("[L7] If every layer above is EXCLUDED with evidence, the responsibility "
                     "leaves the platform: collect both-sides tests (customer: telnet/"
                     "Test-NetConnection from a second network; server-side manual capture as "
                     "a .cap file, never executed by this skill) and hand off to the ISP or "
                     "senior support with the evidence list.")
    lines.append("")
    lines.append("HANDOFF BOUNDARIES")
    lines.append("-" * 72)
    for h in kb["handoffs"]:
        lines.append(f"  {h['target']}: {h['when']}")
    if errors:
        lines.append("")
        lines.append("DEGRADED / FAILED STEPS (recorded honestly)")
        lines.append("-" * 72)
        for e in errors:
            lines.append(f"  [WARN] {e}")
    lines.append("")
    lines.append("Capability gaps of this build (never overstate conclusions that depend on them):")
    for g in CAPABILITY_GAPS:
        lines.append(f"  - {g}")
    lines.append("")
    lines.append("Snapshot-first reminder: any console/firewall/kernel change advised above "
                 f"should be preceded by a disk snapshot (manual step, {DOC_LINKS['create_snapshot']}).")
    lines.append("Credential safety: never paste instance passwords into the chat; use the "
                 "console reset-authorization flow, and rotate any password that was shared.")
    lines.append("")
    lines.append(f"STATUS: {status}")
    lines.append(f"NEXT_ACTION: {next_action}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Layered access-block diagnosis (security group / guest firewall / WAF)",
        epilog="All cloud access goes through the bundled scripts; never run raw product "
               "CLI commands by hand.",
    )
    p.add_argument("--region-id", default=DEFAULT_REGION,
                   help="Alibaba Cloud region id (default cn-hangzhou; declare auto-fills)")
    p.add_argument("--instance-id", help="target ECS instance id")
    p.add_argument("--ip", help="target public/private IP (resolved to an instance)")
    p.add_argument("--direction", choices=["ingress", "egress", "internal"],
                   help="ingress: outside->instance; egress: instance->outside; "
                        "internal: instance<->instance inside the VPC")
    p.add_argument("--protocol", choices=["tcp", "udp", "icmp", "all"], default="tcp")
    p.add_argument("--port", type=int, help="target port 1-65535")
    p.add_argument("--source-ip", help="client egress public IP (for ingress/internal)")
    p.add_argument("--target-ip", help="destination IP (for egress); for internal, the peer instance IP")
    p.add_argument("--symptom", default="", help="exact customer error string (timeout/refused/reset...)")
    p.add_argument("--domain", help="domain involved (enables DNS/filing branch)")
    p.add_argument("--skip-platform-policy", action="store_true",
                   help="skip Cloud Firewall / WAF reads (no such products in scope)")
    p.add_argument("--list-guest-checks", action="store_true",
                   help="print the guest inspection whitelist and exit")
    p.add_argument("--guest-check", choices=sorted(GUEST_CHECKS.keys()),
                   help="execute ONE whitelisted non-mutating guest inspection command")
    p.add_argument("--user-confirmed", action="store_true",
                   help="assert that the customer explicitly confirmed the exact command "
                        "after a restatement of scope and its non-mutating nature")
    p.add_argument("--profile", default=None, help="optional CLI credential profile name")
    p.add_argument("--json", action="store_true", help="machine-readable JSON output")
    return p


def _run_selftest() -> int:
    """Offline regression locks for the security-group match core that drives
    every L4 verdict: port/protocol/CIDR matching and the merged-rule first-match
    evaluation (ascending Priority, Drop before Accept). These decide whether a
    customer's block is attributed to the security group, so the boolean semantics
    are pinned here with no cloud call. Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    def ingress(**kw):
        rule = {"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "22/22",
                "SourceCidrIp": "0.0.0.0/0", "Policy": "Accept", "Priority": "1"}
        rule.update(kw)
        return rule

    # _port_matches: all-port sentinels match anything, ranges are inclusive,
    # junk is non-matching, a None port (ICMP/ALL) matches any range.
    expect("port: -1/-1, '', any, 0/0 all match port 22",
           all(_port_matches(x, 22) for x in ("-1/-1", "", "any", "0/0")))
    expect("port: 22/22 hits 22 not 80; 1/1024 hits 443; junk misses",
           _port_matches("22/22", 22) and not _port_matches("22/22", 80)
           and _port_matches("1/1024", 443) and not _port_matches("bad", 22))
    expect("port: None port matches a specific range (ICMP/ALL convention)",
           _port_matches("22/22", None) is True)

    # _protocol_matches: exact and ALL match, others reject, None rule is not ALL.
    expect("proto: TCP=TCP, ALL covers TCP, UDP!=TCP, None rule!=ALL",
           _protocol_matches("TCP", "TCP") and _protocol_matches("ALL", "TCP")
           and not _protocol_matches("UDP", "TCP")
           and not _protocol_matches(None, "TCP"))

    # _cidr_covers: 'any source' (peer None) only covered by the world rule;
    # a real peer is contained/excluded by the network; blank defaults to all.
    expect("cidr: peer None covered only by 0.0.0.0/0",
           _cidr_covers("0.0.0.0/0", None) and not _cidr_covers("1.2.3.4/32", None))
    expect("cidr: 10.0.0.0/8 covers 10.1.2.3 not 11.1.2.3; blank=all; junk=False",
           _cidr_covers("10.0.0.0/8", "10.1.2.3") and not _cidr_covers("10.0.0.0/8", "11.1.2.3")
           and _cidr_covers("", "8.8.8.8") and not _cidr_covers("garbage", "8.8.8.8"))

    # _eval_sg: single allow, Drop beats Accept at equal priority, lower priority
    # number wins regardless of policy, unmatched port/cidr -> no-cover,
    # group peer not expandable -> unevaluable, empty -> no-cover.
    expect("eval: single permissive ingress -> allow",
           _eval_sg([ingress()], "ingress", "1.2.3.4", "TCP", 22)["result"] == "allow")
    same = _eval_sg([ingress(Policy="Accept"), ingress(Policy="Drop")],
                    "ingress", "1.2.3.4", "TCP", 22)
    expect("eval: equal priority -> Drop wins",
           same["result"] == "drop" and same["matched_rule"]["Policy"] == "Drop")
    prio = _eval_sg([ingress(Policy="Drop", Priority="5"), ingress(Policy="Accept", Priority="1")],
                    "ingress", "1.2.3.4", "TCP", 22)
    expect("eval: priority 1 Accept beats priority 5 Drop",
           prio["result"] == "allow" and prio["matched_rule"]["Priority"] == "1")
    expect("eval: port 80 not covered by 22/22 -> no-cover",
           _eval_sg([ingress()], "ingress", "1.2.3.4", "TCP", 80)["result"] == "no-cover")
    expect("eval: peer outside rule cidr -> no-cover",
           _eval_sg([ingress(SourceCidrIp="10.0.0.0/8")], "ingress", "1.2.3.4", "TCP", 22)["result"] == "no-cover")
    expect("eval: group peer not expandable -> unevaluable",
           _eval_sg([ingress(SourceGroupId="sg-x")], "ingress", "1.2.3.4", "TCP", 22)["result"] == "unevaluable")
    expect("eval: empty rules -> no-cover; wrong direction filtered",
           _eval_sg([], "ingress", "1.2.3.4", "TCP", 22)["result"] == "no-cover"
           and _eval_sg([ingress(Direction="egress", DestCidrIp="0.0.0.0/0")],
                        "ingress", "1.2.3.4", "TCP", 22)["result"] == "no-cover")

    # _iptables_anomaly_line: exact dport, covered range, blanket INPUT drop,
    # clean accept-only sets and junk input.
    expect("iptables: exact deny dport 22 detected",
           _iptables_anomaly_line("-P INPUT ACCEPT\n-A INPUT -p tcp -m tcp "
                                  "--dport 22 -j DROP", 22)
           == "-A INPUT -p tcp -m tcp --dport 22 -j DROP")
    expect("iptables: range 20:23 covers 22; 80 vs 22 -> None",
           _iptables_anomaly_line("-A INPUT -p tcp --dport 20:23 -j REJECT", 22)
           and _iptables_anomaly_line("-A INPUT -p tcp --dport 80 -j DROP", 22) is None)
    expect("iptables: blanket INPUT drop hits any port; FORWARD-only ignored",
           _iptables_anomaly_line("-A INPUT -j DROP", 80)
           and _iptables_anomaly_line("-A FORWARD -j DROP", 80) is None)
    expect("iptables: accept-only / empty / policy-only -> None",
           _iptables_anomaly_line("-A INPUT -p tcp --dport 22 -j ACCEPT", 22) is None
           and _iptables_anomaly_line("", 22) is None
           and _iptables_anomaly_line("-P INPUT DROP", 22) is None
           and _iptables_anomaly_line("-P INPUT DROP", None) == "-P INPUT DROP")

    # ranking_directive: HIT leads, exclusions named, no-HIT honesty.
    hit_v = {"layer": "L5", "name": "iptables-rules", "state": HIT,
             "probe": "deny rule -A INPUT --dport 22 -j DROP"}
    sg_ex = {"layer": "L4", "name": "security group", "state": EXCLUDED}
    dd = "\n".join(ranking_directive([sg_ex, hit_v]))
    expect("directive: HIT becomes PRIMARY CAUSE CANDIDATE with hard rule",
           "PRIMARY CAUSE CANDIDATE #1 [L5] iptables-rules" in dd
           and "Hard rule" in dd
           and "formally excluded" in dd)
    dd2 = "\n".join(ranking_directive([sg_ex]))
    expect("directive: no HIT -> UNVERIFIED honesty + SG excluded still stated",
           "No layer produced a HIT" in dd2 and "formally excluded" in dd2)
    expect("directive: empty verdicts does not crash",
           any("No layer produced a HIT" in ln
               for ln in ranking_directive([])))

    # interpret guard: an unavailable channel (empty output / non-Finished) must
    # never fabricate a HIT on the listeners probe.
    gv_bad = {"check": "listeners", "layer": "L6", "state": UNKNOWN, "evidence": [],
              "output_excerpt": "", "exit_status": ""}
    interpret_guest_output(gv_bad, 8022)
    expect("interpret: empty output -> listeners stays UNKNOWN (no fabricated HIT)",
           gv_bad["state"] == UNKNOWN and "probe" not in gv_bad)
    gv_status = {"check": "listeners", "layer": "L6", "state": UNKNOWN, "evidence": [],
                 "output_excerpt": "LISTEN 0 128 0.0.0.0:22", "exit_status": "Failed"}
    interpret_guest_output(gv_status, 8022)
    expect("interpret: non-Finished status -> no judgement even with text",
           gv_status["state"] == UNKNOWN)
    gv_good = {"check": "listeners", "layer": "L6", "state": UNKNOWN, "evidence": [],
               "output_excerpt": "State Recv-Q Send-Q Local Address:Port\nLISTEN 0 128 0.0.0.0:22",
               "exit_status": "Finished"}
    interpret_guest_output(gv_good, 8022)
    expect("interpret: Finished + no socket -> legitimate HIT still fires",
           gv_good["state"] == HIT)
    return rc


GUEST_CONSENT_ENV = "ECS_GUEST_CONSENT"


def guest_consent_granted() -> bool:
    """True only when the caller obtained the customer's consent for in-guest reads.

    The dispatcher sets this after `--allow-guest-read`. A read-only whitelist lowers
    the *risk* of a command but does not make it consented: `iptables -S` and
    `ss -lntp` still reveal the customer's firewall and listening services, and
    dispatching them is a write against the instance's task history. Missing consent
    therefore means "report the layer as unverified and offer the command", never
    "run it quietly".
    """
    return str(os.environ.get(GUEST_CONSENT_ENV, "")).strip().lower() in (
        "1", "true", "yes", "on")


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(_run_selftest())
    parser = build_parser()
    args = parser.parse_args()

    if args.list_guest_checks:
        print("Guest inspection whitelist (single non-mutating commands, each needs explicit"
              " user confirmation):")
        for name, meta in sorted(GUEST_CHECKS.items()):
            print(f"\n  {name}  [layer {meta['layer']}, os {meta['os']}]\n"
                  f"    command: {meta['command']}\n"
                  f"    meaning: {meta['meaning']}\n"
                  f"    source : {meta['source']}")
        print("\nSTATUS: OK")
        print("NEXT_ACTION: pick one check, restate command+target+non-mutating nature to the user")
        sys.exit(0)

    errors: list[str] = []

    if not args.instance_id and not args.ip:
        print("STATUS: BLOCKED")
        print("NEXT_ACTION: ask the user for the instance id or the IP under test; "
              "no target can be guessed.")
        sys.exit(1)
    consent = guest_consent_granted()
    if args.guest_check and consent:
        # GUEST_CHECKS is a read-only whitelist (double-guarded by
        # PROHIBITED_COMMAND_TOKENS), but read-only is not the same as consented: the
        # dispatcher only sets ECS_GUEST_CONSENT after --allow-guest-read. Without it
        # the check is not dispatched and the layer stays unverified (see below).
        meta = GUEST_CHECKS[args.guest_check]
        print(f"NOTE: read-only whitelisted guest check, consent recorded: "
              f"{meta['command']} (layer {meta['layer']}, non-mutating)")
    elif args.guest_check:
        meta = GUEST_CHECKS[args.guest_check]
        print("CONSENT-REQUIRED: in-guest check not dispatched "
              f"({meta['command']}, layer {meta['layer']}).")
        print("  Tell the customer this exact command would run inside the instance "
              "and what it returns, then re-run with --allow-guest-read. "
              "Cloud-side (VPC/SG/platform) evidence below is unaffected.")

    if args.port is not None and not (1 <= args.port <= 65535):
        print("STATUS: BLOCKED")
        print("NEXT_ACTION: --port must be between 1 and 65535.")
        sys.exit(1)
    port = args.port
    direction = args.direction or "ingress"
    peer_raw = args.target_ip if direction == "egress" else (
        args.source_ip if direction == "ingress" else (args.source_ip or args.target_ip))
    peer = _normalize_peer(peer_raw)

    _cli.check_cli_available()

    # Identity pre-check (account ownership sanity, non-fatal on label failure)
    uid = _cli.resolve_account_id(region=args.region_id, profile=args.profile)
    if not uid:
        errors.append("identity check failed (NoPermission / InvalidAccessKeyId / "
                      "SignatureDoesNotMatch / chain unset): run `aliyun sts get-caller-identity`; "
                      "never paste credentials into chat")

    instance = resolve_instance(args.region_id, args.instance_id, args.ip,
                                args.profile, errors)
    if instance is None:
        print("STATUS: BLOCKED")
        print(f"NEXT_ACTION: target not resolvable in {args.region_id}: "
              f"{'; '.join(errors)}. Confirm the instance id/IP and region with the user.")
        sys.exit(1)

    verdicts: list[dict] = []
    need_input = False

    v4 = check_security_groups(args.region_id, instance, direction, peer,
                               args.protocol, port, args.profile, errors)
    verdicts.append(v4)
    if v4["state"] == UNKNOWN and peer is None:
        need_input = True

    v2 = check_platform_policy(args.region_id, direction, peer, args.protocol,
                               port, args.skip_platform_policy, args.profile, errors)
    verdicts.append(v2)

    v5: dict[str, Any] = {"layer": "L5", "name": LAYER_NAMES["L5"], "state": UNKNOWN,
                          "evidence": [], "manual_steps": []}
    v6: dict[str, Any] = {"layer": "L6", "name": LAYER_NAMES["L6"], "state": UNKNOWN,
                          "evidence": [], "manual_steps": []}
    if args.guest_check and consent:
        gv = run_guest_check(args.region_id, instance, args.guest_check,
                             args.profile, errors)
        interpret_guest_output(gv, port)
        if gv["layer"] == "L5":
            v5.update(gv)
        else:
            v6.update(gv)
    elif str(instance.get("OSType") or "linux").lower() != "windows" and consent:
        # Whitelisted single reads are query-only, but they are still commands inside
        # the customer's machine: run the two decisive checks only after consent.
        for auto_check in ("iptables-rules", "listeners"):
            gv = run_guest_check(args.region_id, instance, auto_check,
                                 args.profile, errors)
            interpret_guest_output(gv, port)
            if gv["layer"] == "L5":
                if v5.get("evidence") and v5.get("check"):
                    v5.setdefault("extra", []).append(gv)
                else:
                    v5.update(gv)
            else:
                v6.update(gv)
    elif str(instance.get("OSType") or "linux").lower() != "windows":
        # No consent: keep L5/L6 unverified and hand the customer the exact command,
        # instead of silently deciding the guest layers are clean.
        for layer, target in (("L5", v5), ("L6", v6)):
            target["manual_steps"].append(
                "In-guest read not executed (customer consent not given). Ask first; "
                "then re-run this area with --allow-guest-read. Candidate checks: "
                + "; ".join(f"{n} ({m['command']})" for n, m in sorted(GUEST_CHECKS.items())
                            if m["layer"] == layer))
    else:
        plan = [f"{name} ({m['command']})" for name, m in sorted(GUEST_CHECKS.items())
                if m["os"] == (str(instance.get("OSType") or "linux").lower() or "linux")
                and m["layer"] in ("L5", "L6", "L0")]
        v5["evidence"].append(
            "guest layer not inspected in this run. Confirmation-gated plan for the operator: "
            "propose ONE check from the whitelist, e.g.: " + "; ".join(plan[:6]))
        v5["manual_steps"].append(
            "If no confirmation channel exists, ask the customer to run the single command and "
            "paste output (ticket failure mode to avoid: chasing screenshots through chat).")
        v6["evidence"].append("listener state unverified until a guest listeners check runs")
    verdicts.append(v5)
    verdicts.append(v6)

    v0 = {"layer": "L0", "name": LAYER_NAMES["L0"],
          "state": UNKNOWN if peer is None else EXCLUDED if v4["state"] != HIT else UNKNOWN,
          "evidence": ["differential actions prepared in the knowledge block"],
          "manual_steps": []}
    v1 = {"layer": "L1", "name": LAYER_NAMES["L1"],
          "state": UNKNOWN,
          "evidence": ["DNS/filing branch prepared in the knowledge block; no filing-status API"],
          "manual_steps": []}
    v3 = {"layer": "L3", "name": LAYER_NAMES["L3"], "state": NOT_APPLICABLE,
          "evidence": ["VPC route/ACL ownership handed off per boundary rules "
                       "(references/access-block-layered__handoff-boundaries.md); not diagnosed here"],
          "manual_steps": []}
    v7 = {"layer": "L7", "name": LAYER_NAMES["L7"],
          "state": UNKNOWN,
          "evidence": ["reachable only after L0-L6 exclusions; see knowledge block"],
          "manual_steps": []}
    verdicts = [v0, v1, v2, v3, v4, v5, v6, v7]

    kb = knowledge_block(direction, args.symptom, args.domain, peer is None)

    # Status decision
    hit_layer = next((v for v in verdicts if v["state"] == HIT), None)
    if need_input:
        status = "DEGRADED"
        next_action = ("collect the missing client egress IP or target IP (offer "
                       + ", ".join(EGRESS_IP_LOOKUP) + "), then rerun for a decisive L4 verdict")
    elif hit_layer is not None:
        status = "OK"
        next_action = (f"root cause located at {hit_layer['layer']}: relay the evidence and the "
                       "MANUAL steps verbatim; recommend snapshot before the change; never "
                       "apply changes with this skill")
    elif errors:
        status = "DEGRADED"
        next_action = ("relay the per-layer verdicts, list which checks could not run, and "
                       "collect the customer-side evidence (references/access-block-layered__evidence-collection.md)")
    elif args.guest_check and v4["state"] == EXCLUDED and v2["state"] != HIT:
        status = "OK"
        next_action = ("every inspected layer EXCLUDED with evidence: conclude the block is "
                       "outside the platform for this path (L7) and deliver the "
                       "evidence-collection list plus the handoff wording "
                       "(references/access-block-layered__handoff-boundaries.md)")
    else:
        status = "DEGRADED"
        next_action = ("no platform-layer hit found from cloud evidence alone; either run a "
                       "confirmation-gated guest check (--guest-check ...) or proceed to the "
                       "evidence-collection list for L7 attribution")

    report = render(verdicts, kb, status, instance, args, errors, next_action)

    if args.json:
        payload = {
            "uid": uid,
            "instance": {k: instance.get(k) for k in
                         ("InstanceId", "Status", "OSType", "RegionId", "InstanceName")}
            if instance else None,
            "flow": {"direction": direction, "protocol": args.protocol, "port": port,
                     "peer": peer, "symptom": args.symptom, "domain": args.domain},
            "verdicts": verdicts,
            "knowledge": kb,
            "errors": errors,
            "capability_gaps": CAPABILITY_GAPS,
            "status": status,
            "next_action": next_action,
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(report)
    sys.exit(0 if status in ("OK", "DEGRADED") else 1)


if __name__ == "__main__":
    main()
