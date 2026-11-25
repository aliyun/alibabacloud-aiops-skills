#!/usr/bin/env python3
"""ECS BT (Baota) panel use and access diagnosis - single entry point.

Subcommands
    check-env   resolve the account behind the default credential chain
    triage      read-only cloud sweep + five-layer panel-access decision tree
    probe       ONE whitelisted side-effect-free guest command, consent-gated
    readback    print customer self-check templates (commands the CUSTOMER runs)
    handoff     adjacent-area routing wording with the evidence summary
    explain     embedded knowledge for a topic

Everything here is read-only against the cloud and, inside the guest, against
the low-risk command whitelist. The skill never creates snapshots, never
restarts anything, never changes configuration and never resets credentials:
fixes are printed as manual steps and re-verified read-only afterwards.

Usage
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py check-env
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py triage --region-id cn-hangzhou \
        --instance-id i-bp1sample --error-text "panel won't open, ERR_CONNECTION_RESET"
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py triage --region-id cn-hangzhou \
        --public-ip 203.0.113.10 --panel-url "http://203.0.113.10:8888" \
        --used-port 8888 --actual-port 39575 --domain www.example.com
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py probe --region-id cn-hangzhou \
        --instance-id i-bp1sample --command ls_dir --target /www/server/panel/vhost/cert
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py probe ... --confirm <token>   # after consent
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py readback --template panel_entry_default
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py handoff --list
    python3 scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py explain --topic decision-tree

A failing cloud query degrades the report with a [WARN] line; it never aborts
the whole diagnosis and never substitutes a guessed value.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import binascii
import json
import sys
import time

from _cli import (
    call_soft,
    mask_secrets,
    paginate_page_number,
    session_id,
    user_agent,
)
from _constants import (
    ALL_CATEGORIES,
    API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS,
    API_ECS_DESCRIBE_INSTANCES,
    API_ECS_DESCRIBE_INSTANCES_FULL_STATUS,
    API_ECS_DESCRIBE_INVOCATIONS,
    API_ECS_RUN_COMMAND,
    AUTH_ERROR_TOKENS,
    CATEGORY_ARREARS,
    CATEGORY_BLACKHOLE,
    CATEGORY_ENTRY_UNKNOWN,
    CATEGORY_ICP,
    CATEGORY_NOT_INSTALLED,
    CATEGORY_PANEL_BAN,
    CATEGORY_PANEL_BROKEN,
    CATEGORY_SG_BLOCKED,
    CATEGORY_UNREACHABLE_RESET,
    CATEGORY_UNKNOWN,
    CANDIDATES,
    CLI_TIMEOUT_SECONDS,
    CUSTOMER_SELFCHECK,
    DEFAULT_PAGE_SIZE,
    ECS_API_VERSION,
    ERROR_CODE_ALIASES,
    ERROR_CODE_CONNECTION_RESET,
    EXPLAIN_TOPICS,
    FAILED_STATES,
    FINISHED_STATES,
    GUEST_COMMANDS,
    GUEST_POLL_INTERVAL_SECONDS,
    GUEST_POLL_MAX_ATTEMPTS,
    GUEST_COMMAND_TIMEOUT_SECONDS,
    HANDOFF_RULES,
    INSTANCE_SCAN_MAX_PAGES,
    NON_RUNNING_STATES,
    PANEL_FACTS,
    PRODUCT_ECS,
    REJECTED_COMMAND_TOKENS,
    SHELL_METACHARACTERS,
    SKILL_NAME,
    STS_API_VERSION,
    SYMPTOM_PATTERNS,
    TRIAGE_LAYERS,
    WINDOWS_SHELL_METACHARACTERS,
)

_REJECTED_TOKENS = frozenset(token.lower() for token in REJECTED_COMMAND_TOKENS)

_STDIN_NOTE = (
    "Every value below came from the customer or from a numbered cloud query; "
    "nothing was assumed."
)


class CommandPolicyError(RuntimeError):
    """Raised when the guest command whitelist rejects a request."""


# ---------------------------------------------------------------------------
# report scaffolding
# ---------------------------------------------------------------------------
class Evidence:
    def __init__(self, title):
        self.title = title
        self.rows = []
        self.findings = []
        self.manual_steps = []
        self.candidates = []
        self.notes = []
        self.layers = []
        self.status = "OK"
        self.show_handoff = True

    def record(self, action, params, outcome, summary):
        self.rows.append({
            "action": action,
            "params": _fmt_params(params),
            "outcome": outcome,
            "summary": mask_secrets(summary),
        })

    def finding(self, text):
        self.findings.append(text)

    def manual(self, text):
        self.manual_steps.append(text)

    def note(self, text):
        self.notes.append(text)

    def candidate(self, candidate):
        self.candidates.append(candidate)

    def layer(self, layer_id, state, detail):
        self.layers.append((layer_id, state, detail))

    def degrade(self):
        if self.status == "OK":
            self.status = "DEGRADED"

    def fail(self):
        self.status = "FAIL"

    def render(self, identity_tag, inputs, next_action):
        out = []
        out.append("=" * 72)
        out.append(self.title)
        out.append("=" * 72)
        out.append("Skill      : {0}".format(SKILL_NAME))
        out.append("Session-Id : {0}".format(session_id()))
        out.append("User-Agent : {0}".format(user_agent()))
        out.append("Identity   : {0}".format(identity_tag))
        out.append("API surface: ecs/{0} sts/{1}".format(ECS_API_VERSION, STS_API_VERSION))
        out.append("")
        out.append("-- Inputs (flag any value this skill assumed rather than was told) ------")
        for key in sorted(inputs):
            out.append("  {0:<18}: {1}".format(key, mask_secrets(str(inputs[key]))))
        out.append("")
        if self.layers:
            out.append("-- Panel-access layers (tri-state: excluded / hit / no-evidence) ----")
            for layer_id, state, detail in self.layers:
                spec = next((l for l in TRIAGE_LAYERS if l["id"] == layer_id), None)
                name = spec["name"] if spec else layer_id
                out.append("  [{0:<14}] {1}".format(layer_id, state.upper()))
                for line in _wrap(detail, 66):
                    out.append("      {0}".format(line))
            out.append("")
        out.append("-- Evidence -----------------------------------------------------------")
        if not self.rows:
            out.append("  (no cloud query was needed for this question)")
        for index, row in enumerate(self.rows, 1):
            out.append("  [{0}] {1}  params: {2}".format(index, row["action"], row["params"]))
            out.append("      -> {0}: {1}".format(row["outcome"], row["summary"]))
        out.append("")
        out.append("-- Findings -----------------------------------------------------------")
        for text in self.findings or ["Nothing was confirmed from returned data."]:
            out.append("  - {0}".format(text))

        if self.candidates:
            out.append("")
            out.append("-- Root-cause candidates (case history, not measured here) ----------")
            for candidate in self.candidates:
                out.append("  * [{0} | confidence: {1}]".format(
                    candidate["id"], candidate["confidence"]))
                for line in _wrap(candidate["summary"], 68):
                    out.append("      {0}".format(line))
                for check in candidate["self_checks"]:
                    tmpl = CUSTOMER_SELFCHECK.get(check)
                    if tmpl:
                        out.append("      customer self-check : {0}  ({1})".format(
                            tmpl["command"], check))
                for key in candidate["probe_keys"]:
                    out.append("      whitelisted probe   : {0} ({1})".format(
                        key, GUEST_COMMANDS[key]["purpose"]))
                out.append("      case refs           : {0}".format(
                    ", ".join(candidate["case_refs"]) or "n/a"))

        if self.manual_steps:
            out.append("")
            out.append("-- Manual-only actions (never executed by this skill) --------------")
            for step in self.manual_steps:
                for i, line in enumerate(_wrap(step, 66)):
                    out.append("  {0} {1}".format("!" if i == 0 else " ", line))

        if self.notes:
            out.append("")
            out.append("-- Notes -----------------------------------------------------------")
            for text in self.notes:
                out.append("  i {0}".format(text))

        if self.show_handoff:
            out.append("")
            out.append("-- Hand-off rules (adjacent areas) ----------------------------------")
            for rule in HANDOFF_RULES:
                out.append("  if {0}".format(rule["when"]))
                out.append("     -> {0}".format(rule["target"]))

        out.append("")
        out.append("STATUS: {0}".format(self.status))
        out.append("NEXT_ACTION: {0}".format(next_action))
        return "\n".join(out)


def _wrap(text, width):
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        if current and len(current) + len(word) + 1 > width:
            lines.append(current)
            current = word
        else:
            current = word if not current else current + " " + word
    if current:
        lines.append(current)
    return lines or [""]


def _fmt_params(params):
    try:
        text = json.dumps(params, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(params)
    return mask_secrets(text[:160])


def _resolve_identity():
    import sts_token
    record, error = sts_token.resolve_identity()
    if error is not None:
        sys.stderr.write("[WARN] identity could not be resolved: {0}\n".format(
            mask_secrets(str(error))))
        return "account=unverified", error
    return sts_token.uid_tag(record), None


# ---------------------------------------------------------------------------
# classification
# ---------------------------------------------------------------------------
def classify(error_text):
    """Return (category, matched_tokens, normalized_error_code).

    Never guesses: no match -> (UNKNOWN, [], None). Multiple matches keep
    every token; the category is the first in ALL_CATEGORIES order that hit.
    """
    haystack = (error_text or "").lower()
    matched, hits = {}, []
    for category, patterns in SYMPTOM_PATTERNS.items():
        tokens = [p for p in patterns if p and p in haystack]
        if tokens:
            matched[category] = tokens
    code = None
    for canonical, aliases in ERROR_CODE_ALIASES.items():
        if any(a in haystack for a in aliases):
            code = canonical
    if not matched:
        return CATEGORY_UNKNOWN, hits, code
    for category in ALL_CATEGORIES:
        if category in matched:
            hits = matched[category]
            if category == CATEGORY_UNREACHABLE_RESET and code is None:
                code = ERROR_CODE_CONNECTION_RESET
            return category, hits, code
    return CATEGORY_UNKNOWN, hits, code


# ---------------------------------------------------------------------------
# defensive response digging: only echo fields that are actually present
# ---------------------------------------------------------------------------
def _dig_list(payload, container_key, item_key):
    node = (payload or {}).get(container_key)
    if isinstance(node, dict):
        node = node.get(item_key)
    if isinstance(node, dict):
        node = [node]
    return node if isinstance(node, list) else []


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _instance_ips(inst):
    ips = []
    # DescribeInstances nests every address group as {"<Group>": {"IpAddress": [...]}}
    # (verified against a live STS response); the inner key is always "IpAddress",
    # not a repeat of the outer group name -- reading the outer name again yields None
    # and silently drops the instance's real public / inner / VPC-private addresses.
    for group in ("PublicIpAddress", "InnerIpAddress"):
        raw = inst.get(group)
        if isinstance(raw, dict):
            raw = raw.get("IpAddress")
        ips.extend(_as_list(raw))
    vpc = inst.get("VpcAttributes") or {}
    if isinstance(vpc, dict):
        priv = vpc.get("PrivateIpAddress")
        if isinstance(priv, dict):
            priv = priv.get("IpAddress")
        ips.extend(_as_list(priv))
    eip = inst.get("EipAddress")
    if isinstance(eip, dict) and eip.get("IpAddress"):
        ips.append(eip["IpAddress"])
    elif isinstance(eip, str) and eip:
        ips.append(eip)
    return [ip for ip in ips if isinstance(ip, str) and ip]


def _instance_sg_ids(inst):
    sg = inst.get("SecurityGroupIds")
    if isinstance(sg, dict):
        return _as_list(sg.get("SecurityGroupId")) or []
    return _as_list(sg)


def _instance_os(inst):
    return (inst.get("OSType") or "").lower() or None


def summarize_instance(inst):
    fields = []
    for key in ("InstanceId", "InstanceName", "Status", "OSType",
                "InstanceChargeType", "InstanceNetworkType", "ZoneId",
                "ExpiredTime", "ImageId"):
        if inst.get(key):
            fields.append("{0}={1}".format(key, inst[key]))
    ips = _instance_ips(inst)
    if ips:
        fields.append("ips={0}".format(",".join(sorted(set(ips)))))
    sg = _instance_sg_ids(inst)
    if sg:
        fields.append("security-groups={0}".format(",".join(sg)))
    locks = inst.get("OperationLocks")
    if isinstance(locks, dict):
        lock_list = _as_list(locks.get("LockReason")) or []
        if lock_list:
            fields.append("operation-locks={0}".format(json.dumps(lock_list)))
    return "; ".join(fields) or "no recognized fields returned"


# ---------------------------------------------------------------------------
# cloud-side read-only queries
# ---------------------------------------------------------------------------
def locate_instance(ev, region_id, instance_id, public_ip, private_ip):
    """Resolve exactly one instance. Returns (instance|None, matched_by).

    0 matches -> caller FAILs with the account/region boundary note (cases in
    this scenario show customers naming an address belonging to another
    account, e.g. T-4B98459C). Several matches -> list candidates and ask.
    """
    if instance_id:
        params = {"RegionId": region_id,
                  "InstanceIds": json.dumps([instance_id])}
    elif public_ip:
        params = {"RegionId": region_id, "PublicIpAddresses": public_ip}
    else:
        params = {"RegionId": region_id, "PrivateIpAddresses": private_ip}
    payload, error = call_soft(API_ECS_DESCRIBE_INSTANCES, params,
                               product=PRODUCT_ECS,
                               timeout=CLI_TIMEOUT_SECONDS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_INSTANCES, params, "WARN", str(error))
        _permission_or_generic(ev, error, API_ECS_DESCRIBE_INSTANCES)
        ev.degrade()
        return None, None
    rows = _dig_list(payload, "Instances", "Instance")
    ev.record(API_ECS_DESCRIBE_INSTANCES, params, "OK",
              "{0} row(s) matched the filter".format(len(rows)))

    if not rows and (public_ip or private_ip):
        # The filtered search can miss an EIP-bound or classic-network case:
        # one bounded scan over the region, matching any address field.
        wanted = public_ip or private_ip
        scanned, note = paginate_page_number(
            API_ECS_DESCRIBE_INSTANCES, {"RegionId": region_id},
            ["Instances", "Instance"], product=PRODUCT_ECS,
            page_size=DEFAULT_PAGE_SIZE, max_pages=INSTANCE_SCAN_MAX_PAGES)
        if note:
            ev.note("region scan: {0}".format(note))
        rows = [i for i in scanned if wanted in _instance_ips(i)]
        ev.record(API_ECS_DESCRIBE_INSTANCES, {"RegionId": region_id,
                                               "scan": "bounded page scan for {0}".format(wanted)},
                  "OK", "{0} row(s) matched the address across the scanned "
                        "pages".format(len(rows)))

    if not rows:
        return None, None
    if len(rows) > 1:
        ev.finding("More than one instance matched; the diagnosis needs one. "
                   "Candidates: " + " | ".join(
                       "{0} ({1})".format(r.get("InstanceId", "?"),
                                          r.get("InstanceName", ""))
                       for r in rows[:10]))
        return None, "ambiguous"
    return rows[0], ("instance-id" if instance_id else
                     "public-ip" if public_ip else "private-ip")


def query_full_status(ev, region_id, instance_id):
    params = {"RegionId": region_id, "InstanceId.1": instance_id,
              "PageSize": DEFAULT_PAGE_SIZE}
    payload, error = call_soft(API_ECS_DESCRIBE_INSTANCES_FULL_STATUS, params,
                               product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_INSTANCES_FULL_STATUS, params, "WARN",
                  str(error))
        _permission_or_generic(ev, error, API_ECS_DESCRIBE_INSTANCES_FULL_STATUS)
        ev.degrade()
        return None
    rows = _dig_list(payload, "InstanceFullStatusSets", "InstanceFullStatusSet")
    events = []
    for row in rows:
        status = (row.get("Status") or {}).get("Name")
        health = (row.get("HealthStatus") or {}).get("Name")
        for event in _as_list(((row.get("Events") or {}).get("Event")) or []):
            if isinstance(event, dict):
                event_type = event.get("InstanceEventType") or event.get("EventType")
                name = (event_type.get("Name") if isinstance(event_type, dict)
                        else event_type)
                if name:
                    events.append(str(name))
        ev.record(API_ECS_DESCRIBE_INSTANCES_FULL_STATUS,
                  {"InstanceId.1": instance_id}, "OK",
                  "Status={0} HealthStatus={1} events={2}".format(
                      status or "?", health or "?",
                      ",".join(events) if events else "none listed"))
    if not rows:
        ev.record(API_ECS_DESCRIBE_INSTANCES_FULL_STATUS,
                  {"InstanceId.1": instance_id}, "OK",
                  "no full-status records returned for this instance")
    return {"rows": rows, "events": events}


def query_agent_status(ev, region_id, instance_id):
    params = {"RegionId": region_id, "InstanceId.1": instance_id}
    payload, error = call_soft(API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS, params,
                               product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS, params, "WARN",
                  str(error))
        _permission_or_generic(ev, error, API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS)
        ev.degrade()
        return None
    rows = _dig_list(payload, "InstanceCloudAssistantStatusSet",
                     "InstanceCloudAssistantStatus")
    if not rows:
        ev.record(API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS,
                  {"InstanceId.1": instance_id}, "OK",
                  "no agent record returned: treat the agent as NOT reachable "
                  "and degrade to customer-pasted readings")
        return False
    online = str(rows[0].get("CloudAssistantStatus", "")).lower() == "true"
    version = rows[0].get("CloudAssistantVersion") or rows[0].get("Version") or "?"
    ev.record(API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS,
              {"InstanceId.1": instance_id}, "OK",
              "CloudAssistantStatus={0} version={1} lastInvoked={2}".format(
                  "online" if online else "offline", version,
                  rows[0].get("LastInvokedTime") or "never recorded"))
    return online


def _permission_or_generic(ev, error, action_name):
    text = str(error)
    if any(token in text for token in AUTH_ERROR_TOKENS):
        ev.finding(
            "The identity in use is not permitted to call {0} (NoPermission / "
            "ImplicitDeny). Report the missing action and hand the customer the "
            "statement from references/ram-policies.md; do not widen permissions "
            "or substitute a broader policy.".format(action_name))
    else:
        ev.finding("Query {0} failed: {1}".format(action_name,
                                                  mask_secrets(text)))


# ---------------------------------------------------------------------------
# triage
# ---------------------------------------------------------------------------
def cmd_triage(args):
    ev = Evidence("BT PANEL TRIAGE (read-only cloud sweep + layer triage)")
    identity, _ = _resolve_identity()
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id or "-",
        "public-ip": args.public_ip or "-",
        "private-ip": args.private_ip or "-",
        "panel-url": args.panel_url or "-",
        "used-port": args.used_port or "-",
        "actual-port": args.actual_port or "-",
        "domain": args.domain or "-",
        "error-text": args.error_text or "-",
        "region source": "given by the customer, never guessed",
    }
    if not (args.instance_id or args.public_ip or args.private_ip):
        ev.fail()
        ev.finding("No resource located: the customer must give an instance id "
                   "or an IP address, and the region must be named.")
        return (ev, inputs, identity,
                "Ask the customer for the instance id (or public IP) and the "
                "region shown in the console region selector; do not guess.")

    category, tokens, code = classify(args.error_text)
    if category != CATEGORY_UNKNOWN:
        ev.finding("Symptom classification: {0} (matched: {1})".format(
            category, ", ".join(tokens)))
    else:
        ev.finding("Symptom classification: no pattern matched; the report "
                   "continues on the five access layers, on readings only.")
    if code:
        ev.finding("Customer-side error wording normalizes to the panel "
                   "unreachable signature ({0}); it is a symptom label, not a "
                   "cause.".format(code))

    instance, matched_by = locate_instance(ev, args.region_id,
                                           args.instance_id, args.public_ip,
                                           args.private_ip)
    if instance is None:
        if matched_by == "ambiguous":
            return (ev, inputs, identity,
                    "Ask the customer which candidate instance hosts the panel, "
                    "then re-run triage with that --instance-id.")
        ev.fail()
        ev.finding("The instance was not found in {0} under the current "
                   "account. This skill's queries only ever see the account "
                   "the credentials belong to and the named region (cases like "
                   "T-4B98459C had front and back end in two accounts): "
                   "confirm the region and the paying account before "
                   "concluding 'the instance does not exist'.".format(args.region_id))
        return (ev, inputs, identity,
                "Re-ask the region and account with the customer, then re-run.")

    ev.finding("Located {0} via {1}: {2}".format(
        instance.get("InstanceId", "?"), matched_by, summarize_instance(instance)))
    status = instance.get("Status")
    is_win = _instance_os(instance) == "windows"

    full = query_full_status(ev, args.region_id, instance.get("InstanceId"))
    agent_online = query_agent_status(ev, args.region_id,
                                      instance.get("InstanceId"))

    # ---------------- layer states ----------------
    lifecycle_hit = status in NON_RUNNING_STATES
    ev.layer("platform",
             "hit" if lifecycle_hit else
             ("no-evidence" if full is None else
              ("hit" if (full or {}).get("events") else "excluded")),
             "instance Status={0}{1}. Arrears, DDoS blackhole and ICP filing "
             "have NO verified query in this skill: where their signatures "
             "fit (all ports dead while Running -> blackhole-like; overdue "
             "bandwidth -> arrears-like; interception page -> filing), the "
             "report recognizes and hands off, proving nothing.".format(
                 status,
                 "; scheduled events: " + ", ".join(full["events"])
                 if (full or {}).get("events") else ""))

    sg_ids = _instance_sg_ids(instance)
    if category == CATEGORY_SG_BLOCKED:
        admission_state = "hit"
    else:
        admission_state = "no-evidence"
    ev.layer("admission", admission_state,
             "Bound security groups: {0}. Rule DETAIL has no verified query "
             "here, so the reading comes from the customer's console: list the "
             "inbound rules for the panel's ACTUAL port (never assume 8888). "
             "OS firewalld/iptables and the panel's own ban list are outside "
             "the low-risk whitelist -> customer self-checks "
             "'os_firewall_state' and 'panel_ban_list'.".format(
                 ", ".join(sg_ids) or "none returned"))

    if args.actual_port and args.used_port:
        port_state = ("hit" if str(args.used_port) != str(args.actual_port)
                      else "excluded")
        port_detail = ("Customer dialled port {0}; the guest reading says the "
                       "panel listens on {1}.".format(args.used_port,
                                                      args.actual_port))
    elif category == CATEGORY_ENTRY_UNKNOWN:
        port_state = "hit"
        port_detail = ("Entry address/port unknown to the customer: recover it "
                       "inside the instance with bt default or bt 14 "
                       "(self-check templates below) before anything else.")
    else:
        port_state = "no-evidence"
        port_detail = ("No cloud API can see the panel's listening port. "
                       "Until the customer pastes the bt default / bt 14 "
                       "address line (credentials stripped), comparing '8888 "
                       "allowed' against the customer's URL proves nothing - "
                       "cases T-952279A8/T-38543E1F/T-43233650 ran on 51973/"
                       "39575/19356.")
    ev.layer("address-port", port_state, port_detail)

    candidate = CANDIDATES.get(category, CANDIDATES[CATEGORY_UNKNOWN])
    if agent_online is False:
        ev.layer("service-file", "no-evidence",
                 "Cloud Assistant agent is offline: whitelisted file probes "
                 "cannot be dispatched and the report must not claim guest "
                 "readings. Degrade: customer runs the self-checks in "
                 "Workbench/SSH and pastes results.")
    elif agent_online is None:
        ev.layer("service-file", "no-evidence",
                 "Agent status could not be read; probes are possible but may "
                 "fail - the dispatch result decides.")
    else:
        probe_hint = ("whitelisted probes available: {0}".format(
            ", ".join(candidate["probe_keys"]))
            if candidate["probe_keys"] else
            "file layer can be probed read-only after per-command consent")
        ev.layer("service-file", "no-evidence",
                 "Service state (panel/web units) and dependency versions are "
                 "outside the low-risk whitelist -> customer self-checks "
                 "'service_status' and 'dependency_versions'. {0}".format(
                     probe_hint))

    earlier_hit = any(state == "hit" for _, state, _ in ev.layers)
    ev.layer("local-client",
             "not-reached" if earlier_hit else "no-evidence",
             "Default last resort once everything server-side is excluded: "
             "incognito window, another network, curl -v from the customer's "
             "machine (self-check 'local_retest'). Cases T-13C89CBC and "
             "T-8BC236C5 recovered here.")

    ev.candidate(dict(candidate, id=category))

    fact_for_category = {
        CATEGORY_ENTRY_UNKNOWN: "entry",
        CATEGORY_UNREACHABLE_RESET: "entry",
        CATEGORY_PANEL_BAN: "local_bans",
        CATEGORY_PANEL_BROKEN: "dependencies",
    }.get(category)
    if fact_for_category:
        ev.note("fact ({0}): {1}".format(fact_for_category,
                                         PANEL_FACTS[fact_for_category]))

    if category == CATEGORY_NOT_INSTALLED:
        ev.manual("The customer's echo 'bt: command not found' (or equivalent) "
                  "means the panel is absent or broken at install level: that "
                  "is the installation area - hand off with this report.")
    for step in candidate["manual_steps"]:
        ev.manual(step)
    if sg_ids:
        ev.manual("Security-group check path (customer console): ECS -> "
                  "instance {0} -> Security Groups -> Inbound rules; ensure "
                  "TCP allow on the panel's actual port with the narrowest "
                  "source that fits the customer's exit IP.".format(
                      instance.get("InstanceId")))

    ev.note("Cloud-side visibility boundary: Describe* only sees this "
            "account's resources in the named region; security-group rule "
            "detail, CloudMonitor metrics, billing and DDoS records are not "
            "verified for this scenario and are never queried - they are "
            "customer-console readings or hand-offs.")
    ev.note(_STDIN_NOTE)

    next_action = _triage_next(category, candidate, agent_online, args, ev)
    if ev.status == "OK" and any(r["outcome"] == "WARN" for r in ev.rows):
        ev.degrade()
    return (ev, inputs, identity, next_action)


def _triage_next(category, candidate, agent_online, args, ev):
    if category == CATEGORY_NOT_INSTALLED:
        return ("handoff --area 1: the panel itself is not installed; "
                "installation questions are a different area.")
    signature_area = {
        CATEGORY_ARREARS: 5,     # billing overview: no verified query exists
        CATEGORY_BLACKHOLE: 4,   # anti-DDoS records area
        CATEGORY_ICP: 6,         # filing console area
    }
    if category in signature_area:
        return ("handoff --area {0}: this is a platform-side state this skill "
                "only recognizes, never proves; attach this report.".format(
                    signature_area[category]))
    if candidate.get("handoff"):
        target = candidate["handoff"][0]
        return ("Recognized adjacent area ({0}): summarize this evidence and "
                "route there (see 'handoff --list'); do not re-run prechecks "
                "there.".format(target))
    if agent_online and candidate["probe_keys"]:
        key = candidate["probe_keys"][0]
        target_hint = " --target <path>" if GUEST_COMMANDS[key][
            "target_required"] else ""
        return ("Guest evidence available read-only: run 'probe --region-id {0} "
                "--instance-id {1} --command {2}{3}' first to print the "
                "disclosure, get the customer's consent, then re-run with the "
                "token.".format(args.region_id, args.instance_id or
                                "<instance-id>", key, target_hint))
    if candidate["self_checks"]:
        key = candidate["self_checks"][0]
        return ("Readback mode: 'readback --template {0}' and ask the customer "
                "to paste the reading (address/port line only, never "
                "credentials); the tree continues on it.".format(key))
    return "Collect the customer's browser error wording verbatim and re-run triage."


# ---------------------------------------------------------------------------
# command whitelist policy + probe (class B, consent-gated)
# ---------------------------------------------------------------------------
def _validate_target(target, os_name):
    if not target:
        raise CommandPolicyError("--target is required for this probe")
    if len(target) > 512:
        raise CommandPolicyError("--target is too long")
    meta = (WINDOWS_SHELL_METACHARACTERS if os_name == "windows"
            else SHELL_METACHARACTERS)
    if any(ch in target for ch in meta):
        raise CommandPolicyError("--target contains a rejected character")
    if " " in target:
        raise CommandPolicyError("--target must not contain whitespace")
    if ".." in target:
        raise CommandPolicyError("--target must not contain '..'")
    if os_name == "windows":
        ok_drive = len(target) == 2 and target[0].isalpha() and target[1] == ":"
        ok_path = (len(target) >= 3 and target[0].isalpha()
                   and target[1] == ":" and target[2] == "\\")
        if not (ok_drive or ok_path):
            raise CommandPolicyError("--target must be a drive letter like C: "
                                     "or a drive-rooted path like C:\\dir")
    elif not target.startswith("/"):
        raise CommandPolicyError("--target must be a POSIX absolute path")
    return target


def _validate_command_string(command_string):
    """A whitelist match is necessary but not sufficient: the assembled
    string is re-checked so no side effect can ride in on a parameter."""
    for token in command_string.split():
        if token.lstrip("-").lower() in _REJECTED_TOKENS:
            raise CommandPolicyError("the assembled command contains the "
                                     "rejected token '{0}'".format(token))
    return command_string


def build_guest_command(key, target=None):
    """Return (guest_os, command_type, command_string) for one whitelisted
    read-only probe."""
    spec = GUEST_COMMANDS.get(key)
    if spec is None:
        raise CommandPolicyError("'{0}' is not a whitelisted probe".format(key))
    argv = list(spec["argv"])
    if spec["target_required"]:
        argv.append(_validate_target(target, spec["os"]))
    elif target:
        raise CommandPolicyError("--target is not accepted for probe '{0}'".format(key))
    command_string = " ".join(argv)
    if any(ch in command_string for ch in
           (WINDOWS_SHELL_METACHARACTERS if spec["os"] == "windows"
            else SHELL_METACHARACTERS)):
        raise CommandPolicyError("the assembled command contains a shell "
                                 "metacharacter")
    return spec["os"], spec["type"], _validate_command_string(command_string)


def probe_ack(region_id, instance_id, key, target):
    rendered = "{0}:{1}".format(key, target) if target else key
    return "PANELPROBE:{0}:{1}:{2}".format(region_id, instance_id, rendered)


def _decode_output(value):
    """The CLI may honour or ignore the requested encoding, so decode when
    the body is base64 and fall back to the raw text otherwise."""
    if not value:
        return ""
    text = value if isinstance(value, str) else str(value)
    try:
        return base64.b64decode(text.strip(), validate=True).decode("utf-8", "strict")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return text


def _invocation_rows(payload_list):
    rows = []
    for invocation in payload_list or []:
        nested = invocation.get("InvokeInstances")
        if isinstance(nested, dict):
            nested = _as_list(nested.get("InvokeInstance"))
        for row in nested or []:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def poll_invocation(ev, region_id, invoke_id):
    deadline_rows = []
    for attempt in range(GUEST_POLL_MAX_ATTEMPTS):
        rows, note = paginate_page_number(
            API_ECS_DESCRIBE_INVOCATIONS,
            {"RegionId": region_id, "InvokeId": invoke_id,
             "IncludeOutput": True, "ContentEncoding": "PlainText"},
            ["Invocations", "Invocation"], product=PRODUCT_ECS,
            page_size=DEFAULT_PAGE_SIZE, max_pages=2)
        if note is not None:
            return None, "the result could not be read back: {0}".format(note)
        deadline_rows = _invocation_rows(rows)
        for row in deadline_rows:
            if (row.get("InvocationStatus") or "") in FINISHED_STATES:
                return row, None
        if attempt < GUEST_POLL_MAX_ATTEMPTS - 1:
            time.sleep(GUEST_POLL_INTERVAL_SECONDS)
    return None, ("no final state within the polling budget: the agent may "
                  "itself be the broken thing - switch to degraded mode")


def cmd_probe(args):
    ev = Evidence("BT PANEL GUEST READ-ONLY PROBE (consent-gated)")
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    ack = probe_ack(args.region_id, args.instance_id, args.command, args.target)
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id,
        "probe": args.command,
        "target": args.target or "n/a",
        "consent": "given" if args.confirm else "NOT GIVEN",
    }
    spec = GUEST_COMMANDS.get(args.command)

    try:
        guest_os, command_type, command_string = build_guest_command(
            args.command, args.target)
    except CommandPolicyError as exc:
        ev.fail()
        ev.finding("Rejected by the command policy: {0}".format(exc))
        ev.note("Whitelisted probes: {0}".format(", ".join(sorted(GUEST_COMMANDS))))
        ev.note("The readings this scenario's support threads also used - bt "
                "menu commands, ss/netstat, systemctl/service, top/free/ps, "
                "iptables/firewall-cmd, openssl/pip, any log reader - are "
                "deliberately NOT whitelisted: they are printed by 'readback' "
                "as customer-run steps and never dispatched here.")
        return (ev, inputs, identity,
                "Pick a whitelisted --command and re-run; the mapping to case "
                "evidence is in references/bt-panel-diagnosis__bt-readonly-evidence.md.")

    ev.record("command-policy", {"probe": args.command}, "OK",
              "single assembled read-only command accepted by the whitelist")

    if not args.confirm:
        for line in [
            "WHAT WILL RUN     : {0}".format(command_string),
            "GUEST OS          : {0}".format(guest_os),
            "DELIVERY          : one Cloud Assistant command of Type={0} to "
            "exactly one instance".format(command_type),
            "AFFECTS           : instance {0} alone; it reads state/metadata "
            "and modifies nothing".format(args.instance_id),
            "READ-ONLY         : the command lists, stats or counts; it "
            "writes nothing, kills nothing, restarts nothing",
            "REVERSIBLE        : n/a - nothing is modified",
            "COST              : the probe itself is not billed",
            "PRECONDITION      : the Cloud Assistant agent must be reachable; "
            "panel threads often have exactly that broken - then this degrades "
            "to a customer-pasted reading instead of failing the diagnosis",
            "PURPOSE           : {0}".format(spec["purpose"]),
            "REPORTS           : {0}".format(spec["reports"]),
            "SCOPE OF CONSENT  : the token below authorizes exactly this "
            "region/instance/probe/target; a second command needs a second "
            "consent",
        ]:
            ev.manual(line)
        ev.finding("Nothing has been executed yet; this is the pre-execution "
                   "disclosure the customer must see before agreeing.")
        return (ev, inputs, identity,
                "Read the lines above to the customer and get their agreement, "
                "then re-run with --confirm {0}".format(ack))

    if args.confirm != ack:
        ev.fail()
        ev.finding("The supplied --confirm is not the consent token for this "
                   "exact operation. Consent is single-use and bound to "
                   "region, instance, probe and target.")
        return (ev, inputs, identity, "Re-run with --confirm {0}".format(ack))

    # Fresh preconditions: instance OS must match the probe family, agent must
    # answer, and nothing is retried by dispatching twice.
    instance, matched_by = locate_instance(ev, args.region_id,
                                           args.instance_id, None, None)
    if instance is None:
        ev.fail()
        return (ev, inputs, identity,
                "The instance could not be located under these credentials; "
                "fix the region/account before probing.")
    os_name = _instance_os(instance) or guest_os
    if os_name != guest_os:
        ev.fail()
        ev.finding("The instance runs {0}; probe '{1}' belongs to the {2} "
                   "whitelist family. Cross-OS dispatch is refused.".format(
                       os_name, args.command, guest_os))
        return (ev, inputs, identity,
                "Pick a probe matching the instance OS and re-disclose.")

    online = query_agent_status(ev, args.region_id, instance.get("InstanceId"))
    if online is False:
        ev.degrade()
        ev.finding("Cloud Assistant agent is offline: the probe was NOT "
                   "dispatched (no blind retries against a downed agent).")
        ev.manual("Degraded mode: have the customer run `{0}` in Workbench/SSH "
                  "and paste the raw output (masked here); then continue the "
                  "same layer.".format(command_string))
        return (ev, inputs, identity,
                "readback --template listen_ports (or run the exact command "
                "above in the customer's session); do not re-dispatch.")

    params = {
        "RegionId": args.region_id,
        "Type": command_type,
        "CommandContent": command_string,
        "ContentEncoding": "PlainText",
        "Name": "bt-panel-diag-{0}".format(args.command),
        "Timeout": str(GUEST_COMMAND_TIMEOUT_SECONDS),
        "InstanceId.1": args.instance_id,
    }
    payload, error = call_soft(API_ECS_RUN_COMMAND, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_RUN_COMMAND,
                  {"RegionId": args.region_id, "Type": command_type,
                   "CommandContent": command_string}, "WARN", str(error))
        ev.degrade()
        if any(t in str(error) for t in AUTH_ERROR_TOKENS):
            ev.finding("The dispatch needs ecs RunCommand permission under "
                       "the customer's own credentials (NoPermission / "
                       "ImplicitDeny): see references/ram-policies.md for the "
                       "exact statement.")
        else:
            ev.finding("The probe could not be delivered: the commonest reason "
                       "in this scenario is that the Cloud Assistant agent is "
                       "unreachable - which is itself a finding, not noise.")
        ev.manual("Degraded mode: give the customer `{0}` to run and paste; "
                  "continue the tree on that reading.".format(command_string))
        return (ev, inputs, identity,
                "Degrade to customer-pasted output for `{0}`; do not retry the "
                "dispatch blind.".format(command_string))

    invoke_id = payload.get("InvokeId")
    if not invoke_id:
        ev.record(API_ECS_RUN_COMMAND,
                  {"RegionId": args.region_id}, "WARN",
                  "the dispatch returned no invoke id; the result cannot be "
                  "read back for this exact probe")
        ev.degrade()
        return (ev, inputs, identity,
                "Read the task result in the console command list, or have "
                "the customer run `{0}` and paste it; do not re-dispatch "
                "blind.".format(command_string))
    ev.record(API_ECS_RUN_COMMAND,
              {"RegionId": args.region_id, "InstanceId.1": args.instance_id},
              "OK", "dispatched, InvokeId={0}".format(invoke_id))

    row, poll_error = poll_invocation(ev, args.region_id, invoke_id)
    if poll_error is not None:
        ev.record("read-back", {"InvokeId": invoke_id}, "WARN", poll_error)
        ev.degrade()
        return (ev, inputs, identity,
                "Re-read the result later (DescribeInvocations history); a "
                "fresh dispatch needs fresh consent.")

    state = row.get("InvocationStatus") or "?"
    output = mask_secrets(_decode_output(row.get("Output") or ""))
    ev.record("guest-output", {"InvokeId": invoke_id}, state,
              "ExitCode={0}, output lines={1}".format(row.get("ExitCode"),
                                                      len(output.splitlines())))
    if state in FAILED_STATES:
        ev.degrade()
        ev.finding("The read-only probe did not complete cleanly (status {0}); "
                   "a failing inspection command is itself evidence about the "
                   "guest.".format(state))
    else:
        ev.finding("Guest reading collected; nothing was modified.")

    print("=" * 72)
    print("GUEST OUTPUT :: {0}".format(command_string))
    print("=" * 72)
    print(output.rstrip() or "(empty output)")
    print("")
    return (ev, inputs, identity,
            "Interpret the output against the layer table; every repair that "
            "follows is a manual customer step (this skill writes nothing), "
            "then re-probe here to verify.")


# ---------------------------------------------------------------------------
# readback: customer self-check templates (never dispatched by this skill)
# ---------------------------------------------------------------------------
def cmd_readback(args):
    ev = Evidence("BT PANEL CUSTOMER SELF-CHECK TEMPLATES")
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    keys = ([args.template] if args.template else sorted(CUSTOMER_SELFCHECK))
    inputs = {"templates": ",".join(keys)}
    bad = [k for k in keys if k not in CUSTOMER_SELFCHECK]
    if bad:
        ev.fail()
        ev.finding("Unknown template(s): {0}".format(", ".join(bad)))
        return (ev, inputs, identity,
                "Available: {0}".format(", ".join(sorted(CUSTOMER_SELFCHECK))))
    for key in keys:
        tmpl = CUSTOMER_SELFCHECK[key]
        ev.finding("[{0}] run: {1}".format(key, tmpl["command"]))
        ev.manual("where: {0}".format(tmpl["run_where"]))
        ev.manual("read: {0}".format(tmpl["read"]))
        if tmpl.get("privacy"):
            ev.note("privacy: {0}".format(tmpl["privacy"]))
        if tmpl.get("case_refs"):
            ev.note("why it matters: cases {0}".format(", ".join(tmpl["case_refs"])))
    ev.note("These commands are OUTSIDE the low-risk whitelist: the customer "
            "runs them in their own session and pastes back the reading; "
            "this skill never dispatches them.")
    ev.note(_STDIN_NOTE)
    return (ev, inputs, identity,
            "Paste the readings back (strip credentials), then re-run triage "
            "with --used-port/--actual-port filled in from the echo.")


# ---------------------------------------------------------------------------
# handoff
# ---------------------------------------------------------------------------
def cmd_handoff(args):
    ev = Evidence("BT PANEL HAND-OFF (adjacent areas)")
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    inputs = {"area": str(args.area) if args.area is not None else "list"}
    if args.area is not None:
        if not (0 <= args.area < len(HANDOFF_RULES)):
            ev.fail()
            return (ev, inputs, identity,
                    "area index outside 0..{0}".format(len(HANDOFF_RULES) - 1))
        rule = HANDOFF_RULES[args.area]
        ev.finding("when: {0}".format(rule["when"]))
        ev.finding("target: {0}".format(rule["target"]))
        ev.manual("Attach this session's evidence summary, state which layers "
                  "were already excluded, and stop: the receiving area owns "
                  "any change. This skill never performs the change on the "
                  "way out.")
    else:
        for i, rule in enumerate(HANDOFF_RULES):
            ev.finding("[{0}] when: {1}".format(i, rule["when"]))
            ev.manual("     -> {0}".format(rule["target"]))
    ev.note("The neighbour list of this batch was not finalised: a named skill "
            "below is a candidate destination to confirm against the live "
            "catalogue before quoting it, and where none is known the console "
            "path is the destination and the wording says so honestly.")
    return (ev, inputs, identity,
            "Run handoff --area <n> for the single destination this case "
            "needs; do not re-run this skill's prechecks there.")


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------
def cmd_explain(args):
    ev = Evidence("BT PANEL KNOWLEDGE ({0})".format(args.topic))
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    inputs = {"topic": args.topic}
    if args.topic == "facts":
        for key in sorted(PANEL_FACTS):
            ev.finding("{0}: {1}".format(key, PANEL_FACTS[key]))
        return (ev, inputs, identity,
                "Apply the facts against live readings; never assume a port.")
    text = EXPLAIN_TOPICS.get(args.topic)
    if text is None:
        ev.fail()
        return (ev, inputs, identity,
                "Topics: {0}, facts".format(", ".join(sorted(EXPLAIN_TOPICS))))
    ev.finding(text)
    return (ev, inputs, identity,
            "Continue the tree; the long form of every topic lives in "
            "references/.")


# ---------------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="bt_panel_diagnosis.py",
        description="Read-only BT panel diagnosis for ECS: cloud sweep, "
                    "five-layer access triage, consent-gated read-only guest "
                    "probes, customer self-check templates, hand-offs.")
    sub = parser.add_subparsers(dest="subcommand")

    env = sub.add_parser("check-env", help="resolve account via the default "
                                           "credential chain (never asks for "
                                           "keys)")

    triage = sub.add_parser("triage", help="read-only cloud sweep + layer "
                                           "triage")
    triage.add_argument("--region-id", required=True,
                        help="region the customer names; never guessed")
    triage.add_argument("--instance-id")
    triage.add_argument("--public-ip")
    triage.add_argument("--private-ip")
    triage.add_argument("--panel-url", help="the address the customer opens "
                                            "in the browser, verbatim")
    triage.add_argument("--used-port", help="port the customer is dialling")
    triage.add_argument("--actual-port", help="panel listening port from the "
                                              "customer's bt reading, once "
                                              "pasted back")
    triage.add_argument("--domain", help="site domain, for certificate paths")
    triage.add_argument("--error-text", help="browser/console wording, "
                                             "verbatim")

    probe = sub.add_parser("probe", help="one whitelisted read-only guest "
                                         "command, consent-gated")
    probe.add_argument("--region-id", required=True)
    probe.add_argument("--instance-id", required=True)
    probe.add_argument("--command", required=True,
                       choices=sorted(GUEST_COMMANDS),
                       help="whitelist key from references/bt-panel-diagnosis__bt-readonly-evidence.md")
    probe.add_argument("--target", help="path argument for keys that take one")
    probe.add_argument("--confirm", help="exact consent token printed by the "
                                         "disclosure run")

    readback = sub.add_parser("readback", help="customer self-check templates")
    readback.add_argument("--template", choices=sorted(CUSTOMER_SELFCHECK))

    handoff = sub.add_parser("handoff", help="adjacent-area routing")
    handoff.add_argument("--area", type=int, help="rule index; omit to list")

    explain = sub.add_parser("explain", help="embedded knowledge topics")
    explain.add_argument("--topic", required=True)

    return parser


def _run_selftest():
    """Offline regression locks for the pure cores that build the triage report:
    address extraction (a real bug lived here -- reading the outer group key
    again dropped every public/inner/VPC-private IP), the defensive list dig, and
    symptom classification. Expected shapes are the live DescribeInstances
    structure (verified via STS). Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # _instance_ips must descend the nested {"IpAddress": [...]} under each group;
    # reading the group name again returns None (the historical bug) and yields []
    # even though the API carried a real address.
    expect("instance_ips: VPC-private nested under PrivateIpAddress.IpAddress",
           _instance_ips({"VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["10.111.214.109"]}}})
           == ["10.111.214.109"])
    expect("instance_ips: public and inner nested under <Group>.IpAddress",
           _instance_ips({"PublicIpAddress": {"IpAddress": ["47.1.2.3"]},
                          "InnerIpAddress": {"IpAddress": ["192.168.1.5"]}})
           == ["47.1.2.3", "192.168.1.5"])
    expect("instance_ips: EipAddress.IpAddress and blank fields dropped",
           _instance_ips({"EipAddress": {"IpAddress": "8.8.8.8"},
                          "PublicIpAddress": {"IpAddress": []}}) == ["8.8.8.8"])
    expect("instance_ips: empty record -> []", _instance_ips({}) == [])

    # _dig_list: two-level descent, single-dict wrap, and no crash on absent keys.
    expect("dig_list: list passthrough, single-dict wrap, absent -> []",
           _dig_list({"Instances": {"Instance": [{"a": 1}]}}, "Instances", "Instance") == [{"a": 1}]
           and _dig_list({"Instances": {"Instance": {"a": 1}}}, "Instances", "Instance") == [{"a": 1}]
           and _dig_list({}, "Instances", "Instance") == []
           and _dig_list(None, "Instances", "Instance") == [])

    # classify: resolves a symptom to its category and never guesses on no-match.
    cat, _hits, code = classify("connection reset by peer")
    expect("classify: connection-reset wording maps to its category with a code",
           cat == CATEGORY_UNREACHABLE_RESET and code is not None)
    expect("classify: unrelated and empty text -> UNKNOWN (no guess)",
           classify("totally unrelated xyz")[0] == CATEGORY_UNKNOWN
           and classify("")[0] == CATEGORY_UNKNOWN)
    return rc


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.subcommand:
        parser.print_help()
        return 2

    if args.subcommand == "check-env":
        import sts_token
        return sts_token.main()

    handlers = {
        "triage": cmd_triage,
        "probe": cmd_probe,
        "readback": cmd_readback,
        "handoff": cmd_handoff,
        "explain": cmd_explain,
    }
    ev, inputs, identity, next_action = handlers[args.subcommand](args)
    print(ev.render(identity, inputs, next_action))
    return 1 if ev.status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
