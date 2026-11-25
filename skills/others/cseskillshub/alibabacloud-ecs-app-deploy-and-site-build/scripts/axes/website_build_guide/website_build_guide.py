#!/usr/bin/env python3
"""Single entry point for the ECS website build and deployment guide skill.

Scope, stated precisely: this script performs two read-only Alibaba Cloud ECS
queries -- ``DescribeInstances`` and ``DescribeInstanceStatus`` -- for one
region, then renders the deployment mainline walkthrough, the customer
self-check templates, and the hand-off routing that the customer acts on.

It changes nothing and cannot enter an instance. Panel site lists, web-server
process state, file contents, local DNS views and the final browser result are
invisible to it by design; those become paste-back questions for the customer.

Exit contract: ``0`` when the run produced a report (``STATUS: OK`` or
``STATUS: DEGRADED``), ``1`` when no read could be completed
(``STATUS: FAIL``). Every degradation is announced on stderr as
``[WARN|DEGRADE]`` and recorded in the report's degradation log.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from . import _cli, _constants as C
except ImportError:  # pragma: no cover - direct execution
    import _cli
    import _constants as C

REGION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$")
INSTANCE_PATTERN = re.compile(r"^(i-|eci-)[A-Za-z0-9\-]{2,60}$")

# Where each list API hides its rows: {"OuterKey": {"InnerKey": [ ... ]}}.
LIST_SHAPES = {
    C.ACTION_DESCRIBE_INSTANCES: ("Instances", "Instance"),
    C.ACTION_DESCRIBE_INSTANCE_STATUS: ("InstanceStatuses", "InstanceStatus"),
}

SITE_TYPES = ("panel", "manual", "image", "docker", "unknown")
STAGE_COUNT = len(C.MAINLINE_STAGES)


# --------------------------------------------------------------------------
# read-only queries
# --------------------------------------------------------------------------
def _extract_rows(body, action):
    outer, inner = LIST_SHAPES[action]
    container = body.get(outer)
    if isinstance(container, dict):
        rows = container.get(inner) or []
    elif isinstance(container, list):
        rows = container
    else:
        rows = []
    return rows if isinstance(rows, list) else []


def paginate(action, base_params, timeout, profile, log):
    """Walk pages 1..n of one read-only list API and return the raw rows.

    Stops on an empty page, once ``TotalCount`` is covered, or at
    ``MAX_PAGES`` -- the last case is logged instead of silently truncating.
    A page that fails is logged and ends the walk; earlier pages are kept.
    """
    collected = []
    page = 1
    hit_page_limit = True
    while page <= C.MAX_PAGES:
        params = dict(base_params)
        params["PageNumber"] = page
        params["PageSize"] = C.PAGE_SIZE
        try:
            body = _cli.call_read_api(
                C.ECS_PRODUCT, action, params=params, timeout=timeout, profile=profile
            )
        except (_cli.CliError, OSError) as exc:
            log.append("{} {} page {}: {}".format(C.DEGRADE_PREFIX, action, page, exc))
            return collected

        rows = _extract_rows(body, action)
        collected.extend(rows)
        total = body.get("TotalCount")
        if not rows or (total is not None and len(collected) >= int(total)):
            hit_page_limit = False
            break
        page += 1

    if hit_page_limit:
        log.append("{} {} stopped at {} pages; the list may be incomplete".format(
            C.DEGRADE_PREFIX, action, C.MAX_PAGES))
    return collected


def describe_instances(region_id, instance_ids, timeout, profile, log):
    """Rows of ``DescribeInstances`` for one region (optionally id-filtered)."""
    base = {"RegionId": region_id}
    if instance_ids:
        base["InstanceIds"] = list(instance_ids)
    return paginate(C.ACTION_DESCRIBE_INSTANCES, base, timeout, profile, log)


def describe_instance_status(region_id, timeout, profile, log):
    """``{instance_id: status}`` map from ``DescribeInstanceStatus``."""
    rows = paginate(C.ACTION_DESCRIBE_INSTANCE_STATUS, {"RegionId": region_id},
                    timeout, profile, log)
    return {r.get("InstanceId"): r.get("Status") for r in rows if r.get("InstanceId")}


def account_label(timeout, profile, log):
    """Best-effort UID label; its failure only degrades the report header."""
    try:
        if __package__:
            from .sts_token import verify
        else:  # pragma: no cover - direct execution
            from sts_token import verify
        return verify(profile=profile, timeout=timeout).get("account_id", "")
    except (_cli.CliError, OSError) as exc:
        log.append("{} account label unavailable: {}".format(C.WARN_PREFIX, exc))
        return ""


# --------------------------------------------------------------------------
# interpretation
# --------------------------------------------------------------------------
def _sub_list(container, outer, inner):
    if not isinstance(container, dict):
        return []
    value = container.get(outer)
    if isinstance(value, dict):
        rows = value.get(inner)
        return rows if isinstance(rows, list) else []
    return value if isinstance(value, list) else []


def summarize_instance(row, status_map):
    """Reduce one ``DescribeInstances`` row to the fields this guide acts on."""
    instance_id = row.get("InstanceId", "")
    public_ips = list(_sub_list(row, "PublicIpAddress", "IpAddress"))
    eip = (row.get("EipAddress") or {}).get("IpAddress")
    if eip:
        public_ips.append(eip)
    status = row.get("Status", "")
    crosscheck = status_map.get(instance_id, "")
    return {
        "instance_id": instance_id,
        "name": row.get("InstanceName", ""),
        "status": status,
        "status_crosscheck": crosscheck,
        "region": row.get("RegionId", ""),
        "zone": row.get("ZoneId", ""),
        "os": row.get("OSName") or row.get("ImageId") or "",
        "instance_type": row.get("InstanceType", ""),
        "charge_type": row.get("InstanceChargeType", ""),
        "network_type": row.get("InstanceNetworkType", ""),
        "security_groups": _sub_list(row, "SecurityGroupIds", "SecurityGroupId"),
        "private_ips": _sub_list(row, "VpcAttributes", "PrivateIpAddress"),
        "public_ips": public_ips,
        "vpc_id": (row.get("VpcAttributes") or {}).get("VpcId", ""),
    }


def build_findings(instances, inventory_failed):
    """Deployment precheck findings, strictly from what was observed."""
    if inventory_failed:
        return [("blocked",
                 "The instance inventory could not be read, so no deployment "
                 "target is confirmed. Resolve the reported error and re-run "
                 "before starting the mainline.")]

    if not instances:
        return [("none",
                 "No instance is visible in the queried region under the current "
                 "credential's account. That is NOT proof of no server: ECS reads "
                 "are per region and per account. Ask which region the purchase "
                 "was made in, then re-run there.")]

    findings = []
    running = [i for i in instances if i["status"] == "Running"]
    for item in instances:
        label = "{} ({})".format(item["instance_id"], item["name"] or "unnamed")
        if item["status"] != "Running":
            findings.append(("not-running",
                             "Instance {} is in state '{}'. The customer starts it "
                             "themselves from the console instance list; a state "
                             "that will not change is a status symptom and leaves "
                             "this guide.".format(label, item["status"] or "unknown")))
        if item["status_crosscheck"] and item["status_crosscheck"] != item["status"]:
            findings.append(("status-mismatch",
                             "Instance {} shows '{}' in DescribeInstances and '{}' "
                             "in DescribeInstanceStatus; treat the state as in "
                             "transition.".format(label, item["status"],
                                                  item["status_crosscheck"])))
        if not item["public_ips"]:
            findings.append(("no-public-ip",
                             "Instance {} returned no public address. Stage 5 needs "
                             "one for a plain A record, or a fronting address the "
                             "customer confirms; never assume one.".format(label)))
        if not item["security_groups"]:
            findings.append(("no-sg",
                             "Instance {} shows no bound security group. Ask the "
                             "customer to check the console security-group page: "
                             "inbound 80/443 must be allowed for the site to be "
                             "reachable.".format(label)))

    if running:
        findings.append(("ready",
                         "{} of {} queried instance(s) are Running and usable as "
                         "the deployment target. Confirm the intended instance with "
                         "the customer before walking the mainline.".format(
                             len(running), len(instances))))
    return findings


def build_handoff_matches(wording):
    """Flag neighbour-skill symptoms present in the customer's own wording."""
    haystack = (wording or "").lower()
    if not haystack:
        return []
    matched = []
    for rule in C.HANDOFF_RULES:
        tokens = re.split(r"[/,]| and | or ", rule["signal"].lower())
        if any(len(t.strip()) > 5 and t.strip() in haystack for t in tokens):
            matched.append(rule)
    return matched


# --------------------------------------------------------------------------
# report rendering
# --------------------------------------------------------------------------
def render_inventory(rows, region_id, out):
    out.append("## Deployment Target Inventory (read-only)")
    out.append("")
    out.append("Source: `{}` `{}` + `{}` `{}`, region `{}`, API version `{}`.".format(
        C.ECS_PRODUCT, C.ACTION_DESCRIBE_INSTANCES,
        C.ECS_PRODUCT, C.ACTION_DESCRIBE_INSTANCE_STATUS,
        region_id, C.ECS_API_VERSION))
    out.append("")
    if not rows:
        out.append("- No instance returned for this region under this credential.")
        out.append("")
        out.append("> " + C.ENTITLEMENT_CAVEAT)
        return
    out.append("| Instance ID | Name | Status | Cross-check | Type | Public IP | Security groups |")
    out.append("|---|---|---|---|---|---|---|")
    for item in rows:
        out.append("| {} | {} | {} | {} | {} | {} | {} |".format(
            item["instance_id"] or "-",
            item["name"] or "-",
            item["status"] or "-",
            item["status_crosscheck"] or "-",
            item["instance_type"] or "-",
            ", ".join(item["public_ips"]) or "none returned",
            ", ".join(item["security_groups"]) or "none returned",
        ))
    out.append("")
    out.append("> " + C.ENTITLEMENT_CAVEAT)


def render_findings(findings, out):
    out.append("")
    out.append("## Deployment Precheck Findings")
    out.append("")
    if not findings:
        out.append("- Nothing to raise; the inventory is internally consistent.")
        return
    for kind, message in findings:
        out.append("- [{}] {}".format(kind, message))


def render_mainline(stage, domain, out):
    out.append("")
    out.append("## Deployment Mainline Walkthrough")
    out.append("")
    out.append(C.DISCLAIMER)
    out.append("")
    for item in C.MAINLINE_STAGES:
        if stage not in ("all", item["id"]):
            continue
        out.append("### " + item["title"])
        out.append("")
        out.append("- Entry point: {}".format(item["entry"]))
        out.append("- What you do: {}".format(item["action"]))
        out.append("- What to fill in: {}".format(item["fill"]))
        out.append("- Expected result: {}".format(item["expected"]))
        out.append("- If it fails: {}".format(item["fallback"]))
        out.append("- Hand-off target: {}".format(item["handoff"]))
        out.append("- Risk notice: {}".format(item["risk"]))
        if domain and item["id"] in ("site", "resolve", "verify"):
            out.append("- This customer's domain: `{}`".format(domain))
        out.append("")
    out.append("Expanded detail for each stage: `references/deploy-mainline.md`.")
    out.append("")


def render_selfcheck(stage, out):
    out.append("")
    out.append("## Customer Self-Check (paste-back) Items")
    out.append("")
    out.append("The cloud side cannot observe these. The customer runs the read-only "
               "commands or opens the console page themselves and pastes the result "
               "back; this skill never executes anything on the instance.")
    out.append("")
    items = [i for i in C.SELF_CHECK_ITEMS if stage in ("all", i["stage"])]
    for item in items or C.SELF_CHECK_ITEMS:
        out.append("### {}".format(item["question"]))
        out.append("")
        out.append("- Ask the customer to: {}".format(item["customer_action"]))
        out.append("- Why it matters: {}".format(item["why"]))
        out.append("")


def render_handoff(matched, out):
    out.append("")
    out.append("## Hand-off Routing")
    out.append("")
    if matched:
        out.append("Symptoms detected in the customer's own wording, which belong "
                   "to another flow:")
        out.append("")
        for rule in matched:
            out.append("- Detected [{}] -> route to **{}**".format(
                rule["signal"], rule["route"]))
            out.append("  - Why: {}".format(rule["reason"]))
            out.append("  - Say: \"{}\"".format(rule["sentence"]))
        out.append("")
    out.append("Full table: `references/handoff-rules.md`. Never diagnose any of "
               "these inside this guide.")


def render_degradations(log, out):
    out.append("")
    out.append("## Graceful Degradation Log")
    out.append("")
    if not log:
        out.append("- None. Every whitelisted read completed.")
        return
    for line in log:
        out.append("- {}".format(line))


def next_action(status, args):
    if status == C.STATUS_FAIL:
        return ("Resolve the reported read failure -- the CLI credential chain, or "
                "the missing read action in references/ram-policies.md, or an "
                "invalid region id -- then re-run this script. Do not substitute a "
                "hand-assembled CLI command.")
    if status == C.STATUS_DEGRADED:
        return ("Report the partial result together with its degradation log, then "
                "re-run to complete the missing read before drawing a conclusion.")
    if not args.instance_id:
        return ("Ask the customer which instance is the deployment target, then "
                "walk stages 1-{} with the mandatory disclaimer and collect the "
                "paste-back items in references/customer-selfcheck.md.".format(
                    STAGE_COUNT))
    return ("Walk stages 1-{} with the mandatory disclaimer, then re-run this "
            "script for the read-only re-check and combine it with the customer's "
            "pasted access result.".format(STAGE_COUNT))


def build_report(args):
    """Run the reads and return ``(lines, payload, status)``."""
    log = []
    raw_instances = describe_instances(
        args.region_id, args.instance_id, args.timeout, args.profile, log)
    status_map = describe_instance_status(
        args.region_id, args.timeout, args.profile, log)
    uid = account_label(args.timeout, args.profile, log)

    inventory_failed = not raw_instances and any(
        C.ACTION_DESCRIBE_INSTANCES in line and C.DEGRADE_PREFIX in line
        for line in log)
    reads_completed = sum(
        0 if any(action in line for line in log) else 1
        for action in (C.ACTION_DESCRIBE_INSTANCES, C.ACTION_DESCRIBE_INSTANCE_STATUS))
    rows = [summarize_instance(r, status_map) for r in raw_instances]
    findings = build_findings(rows, inventory_failed)
    matched = build_handoff_matches(args.stage_hint)

    if inventory_failed:
        status = C.STATUS_FAIL
    elif log:
        status = C.STATUS_DEGRADED
    else:
        status = C.STATUS_OK

    lines = [
        "# ECS Website Build & Deployment Guide - Read-only Report",
        "",
        "- Region queried: `{}` (per-region read)".format(args.region_id),
        "- Instance filter: {}".format(
            ", ".join(args.instance_id) if args.instance_id
            else "(none: every instance visible in the region)"),
        "- Expansion stage: `{}`".format(args.stage),
        "- Deployment flavour hint: `{}`".format(args.site_type),
        "- Domain supplied: {}".format(
            "`{}`".format(args.domain) if args.domain else "(none supplied)"),
        "- Account label: {}".format(uid or "(unavailable, see degradation log)"),
        "- Session id: `{}`".format(_cli.SESSION_ID),
        "- User-Agent sent on every call: `{}`".format(_cli.build_user_agent()),
        "- Read-only actions used: `{} {}` and `{} {}`; each call bounded by {}s.".format(
            C.ECS_PRODUCT, C.ACTION_DESCRIBE_INSTANCES,
            C.ECS_PRODUCT, C.ACTION_DESCRIBE_INSTANCE_STATUS, args.timeout),
        "",
        "## Summary",
        "",
    ]
    if inventory_failed:
        lines.append("- The instance inventory could not be read, so no deployment "
                     "target is confirmed and the walkthrough is unverified. "
                     "Resolve the error above and re-run.")
    elif not rows:
        lines.append("- No instance is visible in `{}` under the current "
                     "credential. Confirm the purchase region with the customer "
                     "before walking the mainline.".format(args.region_id))
    else:
        lines.append("- {} instance(s) visible in `{}`, of which {} Running. The "
                     "walkthrough below is guidance for the customer to execute; "
                     "nothing was changed.".format(
                         len(rows), args.region_id,
                         sum(1 for r in rows if r["status"] == "Running")))
    lines.append("- Cloud-side reads completed: {} of 2. Precheck findings: {}.".format(
        reads_completed, len(findings)))

    render_inventory(rows, args.region_id, lines)
    render_findings(findings, lines)
    render_mainline(args.stage, args.domain, lines)
    render_selfcheck(args.stage, lines)
    render_handoff(matched, lines)
    render_degradations(log, lines)

    payload = {
        "skill": C.SKILL_NAME,
        "session_id": _cli.SESSION_ID,
        "user_agent": _cli.build_user_agent(),
        "read_only": True,
        "region_id": args.region_id,
        "instance_filter": list(args.instance_id or []),
        "stage": args.stage,
        "site_type": args.site_type,
        "domain": args.domain or "",
        "account_label": uid,
        "read_only_actions": [C.ACTION_DESCRIBE_INSTANCES,
                              C.ACTION_DESCRIBE_INSTANCE_STATUS],
        "instances": rows,
        "findings": [{"kind": kind, "message": msg} for kind, msg in findings],
        "handoff_matches": [rule["route"] for rule in matched],
        "degradation_log": log,
        "STATUS": status,
        "NEXT_ACTION": next_action(status, args),
    }
    return lines, payload, status


def validate(args, parser):
    """Reject malformed inputs before any cloud call is attempted."""
    if not REGION_PATTERN.match(args.region_id or ""):
        parser.error("--region-id must be a region id such as cn-hangzhou; got "
                     "{!r}".format(args.region_id))
    for value in args.instance_id or []:
        if not INSTANCE_PATTERN.match(value):
            parser.error("--instance-id must look like i-xxxxxxxx; got {!r}".format(value))
    if args.site_type not in SITE_TYPES:
        parser.error("--site-type must be one of " + "/".join(SITE_TYPES))
    if args.timeout <= 0:
        parser.error("--timeout must be a positive number of seconds")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="website_build_guide.py",
        description="Read-only ECS deployment-target inventory plus the "
                    "website-build mainline walkthrough, for the customer to "
                    "execute themselves.",
    )
    parser.add_argument("--region-id", required=True,
                        help="Region to query, e.g. cn-hangzhou. Reads are per-region.")
    parser.add_argument("--instance-id", action="append", default=[],
                        help="Optional target instance id; repeatable.")
    parser.add_argument("--site-type", default="unknown",
                        help="|".join(SITE_TYPES) + " (default: unknown)")
    parser.add_argument("--domain", default="", help="Customer domain, if supplied.")
    parser.add_argument("--stage", default="all", choices=C.STAGE_IDS,
                        help="Mainline stage to expand (default: all).")
    parser.add_argument("--stage-hint", default="", dest="stage_hint",
                        help="Optional verbatim customer wording, used only to flag "
                             "neighbour-skill symptoms for hand-off.")
    parser.add_argument("--profile", default=None, help="Optional named CLI profile.")
    parser.add_argument("--timeout", type=int, default=C.DEFAULT_TIMEOUT,
                        help="Per-call timeout in seconds (default: %d)." % C.DEFAULT_TIMEOUT)
    parser.add_argument("--json", action="store_true", help="Structured output.")
    args = parser.parse_args(argv)
    validate(args, parser)

    lines, payload, status = build_report(args)

    for line in payload["degradation_log"]:
        print(line, file=sys.stderr)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        lines.extend(["", "STATUS: {}".format(status),
                      "NEXT_ACTION: {}".format(payload["NEXT_ACTION"])])
        print("\n".join(lines))
    return 1 if status == C.STATUS_FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
