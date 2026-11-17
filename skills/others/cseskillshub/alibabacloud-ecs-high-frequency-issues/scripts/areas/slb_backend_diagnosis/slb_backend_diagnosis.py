#!/usr/bin/env python3
"""
slb_backend_diagnosis.py -- single read-only entry point
=========================================================
SECURITY: This script issues READ-ONLY Alibaba Cloud API queries only
(Describe*/Get* actions on ecs / cms / vpc via the shared aliyun-CLI layer).
It NEVER creates, modifies, deletes or otherwise changes any resource, and it
NEVER executes any command inside a customer instance -- customer self-check
commands appear ONLY as guidance text for the customer to run and return.

What it does (RO_QUERY flow: fetch facts -> apply rules -> output verdict):
  1. verifies the caller identity (sts GetCallerIdentity, traceability label);
  2. collects backend-ECS facts that cloud APIs CAN see:
       - ecs  DescribeInstances     (status / zone / type / security groups / IPs)
       - ecs  DescribeInstanceTypes (spec ceilings; best-effort, degrades)
       - cms  DescribeMetricLast    (is the backend still producing load/traffic)
       - vpc  DescribeEipAddresses  (EIP binding & bandwidth facts)
  3. applies the embedded decision rules to the symptom + declared
     load-balancer-side facts (listeners/health checks are NOT cloud-readable
     by this skill -- they come from the customer's console self-checks);
  4. prints an evidence report ending in the STATUS / NEXT_ACTION contract.

Usage examples:
  python3 scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py --region-id cn-hangzhou \
      --symptom health-check --instance-ids i-bp1xxxx \
      --backend-port 8080 --ss-output "$(cat ss_returned_by_customer.txt)"

  python3 scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py --region-id cn-shenzhen \
      --symptom certificate --listener-protocol tcp --json

Exit codes: 0 = conclusion produced (OK or DEGRADED)  1 = FAIL (no usable
conclusion; NEXT_ACTION states what to ask for)  2 = argparse usage error.
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
import time
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import _cli  # noqa: E402
import _constants  # noqa: E402
from _constants import (  # noqa: E402
    CMS_METRICS, CMS_NAMESPACE, CMS_PERIOD_SECONDS, DEFAULT_TIMEOUT,
    FIXED_CALIBERS, HANDOFF, MAX_INSTANCES, MAX_METRIC_CALLS, MAX_TYPE_QUERY,
    RULES, SCENARIOS, SELF_CHECK_CONSOLES, SKILL_NAME, SYMPTOM_KEYWORDS,
)

_REGION_RE = re.compile(r"^[a-z0-9-]{4,32}$")
_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9-]{4,40}$")
_LB_ID_RE = re.compile(r"^(?:lb|alb|nlb)-[a-z0-9-]{4,64}$")


# ---------------------------------------------------------------------------
# Pure judgment functions (deterministic, unit-asserted at the bottom of
# this module; the agent must relay their output verbatim)
# ---------------------------------------------------------------------------

def classify_symptom(message: str) -> str:
    """Triage free-text customer wording to a scenario code (first hit wins)."""
    low = (message or "").lower()
    if not low:
        return "other"
    for code, needles in SYMPTOM_KEYWORDS:
        for needle in needles:
            if needle in low:
                return code
    return "other"


def match_error_strings(message: str) -> List[Tuple[str, str]]:
    """Return (quoted error string, rule id) pairs found in customer text."""
    low = (message or "").lower()
    hits: List[Tuple[str, str]] = []
    table = [
        ("empty reply from server", "HC-EMPTY-REPLY"),
        ("unexpected response code: 404", "E404-ROUTE-MISSING"),
        ("not in a normal listening", "HC-NOT-LISTENING"),
        ("bad gateway", "E502-BACKEND-UNHEALTHY"),
        ("nopermission", "HANDOFF-RAM"),
    ]
    for needle, rule_id in table:
        if needle in low:
            hits.append((needle, rule_id))
    if re.search(r"\b502\b", low):
        hits.append(("502", "E502-BACKEND-UNHEALTHY"))
    if re.search(r"\b404\b", low) and ("unexpected response code: 404", "E404-ROUTE-MISSING") not in hits:
        hits.append(("404", "E404-ROUTE-MISSING"))
    return hits


def listen_port_present(listening_text: Optional[str], port: Optional[int]) -> Optional[bool]:
    """True/False when the customer-returned `ss -ltnp` / `netstat -ano`
    output does/does not show a listening socket on `port`; None when either
    input is missing (no data -- never guess)."""
    if not listening_text or not port:
        return None
    port_s = str(int(port))
    for line in listening_text.splitlines():
        low = line.lower()
        if ("listen" not in low) and (" tcp" not in low) and not low.startswith("tcp"):
            continue
        # The service port is the digit run immediately after a colon (ss /
        # netstat always render `address:port`, e.g. `0.0.0.0:80`, `*:443`,
        # `[::]:9000`). Matching on a leading `.` too would let an IP's last
        # octet be mistaken for the port -- e.g. probing port 80 against
        # `10.0.0.80:8080` would wrongly report 80 as listening -- so anchor
        # on the colon and use `\b` so `:8080` does not match a query for 80.
        if re.search(r":" + re.escape(port_s) + r"\b", line):
            return True
    return False


def probe_verdict(probe_text: Optional[str]) -> Dict[str, Any]:
    """Classify a customer-returned local probe output (curl -v / telnet)."""
    out: Dict[str, Any] = {"class": "no-data", "rule": "", "detail": ""}
    if not probe_text:
        return out
    low = probe_text.lower()
    m = re.search(r"<\s*HTTP/[\d.]+\s+(\d{3})", probe_text, re.I)
    if "empty reply from server" in low:
        out.update({"class": "empty-reply", "rule": "HC-EMPTY-REPLY",
                    "detail": "connection accepted, closed without an HTTP response"})
    elif "connection refused" in low or "could not connect" in low:
        out.update({"class": "refused", "rule": "HC-NOT-LISTENING",
                    "detail": "nothing accepts connections on the probed port"})
    elif "timed out" in low or "timeout" in low:
        out.update({"class": "timeout", "rule": "HC-NOT-LISTENING",
                    "detail": "probe timed out (filtered path or dead service)"})
    elif m:
        code = int(m.group(1))
        if code == 404:
            out.update({"class": "http-404", "rule": "E404-ROUTE-MISSING",
                        "detail": "answered 404 on the probed path"})
        elif code == 101 or 200 <= code < 400:
            out.update({"class": "answered", "rule": "",
                        "detail": "service answered with HTTP {}".format(code)})
        else:
            out.update({"class": "http-error", "rule": "",
                        "detail": "service answered with HTTP {}".format(code)})
    return out


def zone_spread(instances: List[Dict]) -> Dict[str, Any]:
    """Distinct availability zones of the given backend instances."""
    zones = sorted({str(i.get("ZoneId")) for i in instances if i.get("ZoneId")})
    return {"zones": zones, "zone_count": len(zones), "multi_zone": len(zones) > 1}


def handoff_targets(message: str) -> List[Tuple[str, str]]:
    """Return (target skill, note) pairs whose signals appear in the text."""
    low = (message or "").lower()
    hits: List[Tuple[str, str]] = []
    for _name, spec in HANDOFF.items():
        if any(sig in low for sig in spec["signals"]):
            hits.append((spec["target"], spec["note"]))
    return hits


def epoch_ms(hours_back: int) -> str:
    """Current unix time (ms) minus hours_back, as the CMS APIs expect."""
    return str(int((time.time() - hours_back * 3600) * 1000))


# ---------------------------------------------------------------------------
# Read-only evidence collection (every failure degrades with a [WARN] line)
# ---------------------------------------------------------------------------

class Collector:
    """Runs the four whitelisted read-only APIs and records degradations."""

    def __init__(self, region: str, profile: Optional[str]):
        self.region = region
        self.profile = profile
        self.warnings: List[str] = []
        self.calls_ok = 0
        self.calls_failed = 0

    def warn(self, product: str, action: str, err: _cli.CliError) -> Dict[str, str]:
        line = "[WARN] {} {}: {}".format(product, action, err)
        print(line, file=sys.stderr)
        self.warnings.append(line)
        self.calls_failed += 1
        return {"code": err.code or "Unknown", "message": str(err)[:300]}

    def ok(self) -> None:
        self.calls_ok += 1

    def instances(self, instance_ids: List[str]) -> Tuple[List[Dict], Optional[Dict]]:
        params: Dict[str, Any] = {"RegionId": self.region}
        if instance_ids:
            params["InstanceIds"] = json.dumps(instance_ids)
        try:
            items = _cli.paginate_page_number(
                "ecs", "DescribeInstances", params,
                ["Instances", "Instance"],
                region=self.region, profile=self.profile,
                timeout=DEFAULT_TIMEOUT,
            )
            self.ok()
            return items, None
        except _cli.CliError as e:
            return [], self.warn("ecs", "DescribeInstances", e)

    def metric_last(self, instance_id: str, hours: int) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        dims = json.dumps([{"instanceId": instance_id}])
        for metric in CMS_METRICS:
            params = {
                "Namespace": CMS_NAMESPACE,
                "MetricName": metric,
                "Dimensions": dims,
                "Period": CMS_PERIOD_SECONDS,
                "StartTime": epoch_ms(hours),
                "EndTime": epoch_ms(0),
            }
            try:
                body = _cli.call("cms", "DescribeMetricLast", params,
                                 region=self.region, profile=self.profile,
                                 timeout=DEFAULT_TIMEOUT)
                self.ok()
                raw = body.get("Datapoints", "[]")
                points: List[Dict] = []
                if isinstance(raw, str) and raw.strip():
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            points = parsed
                    except (json.JSONDecodeError, ValueError):
                        points = []
                if points:
                    latest = points[-1]
                    result[metric] = {
                        "datapoints": len(points),
                        "latestAverage": latest.get("Average"),
                        "latestMaximum": latest.get("Maximum"),
                        "timestamp": latest.get("Timestamp"),
                    }
                else:
                    result[metric] = {"datapoints": 0,
                                      "note": "no datapoints in window "
                                              "(report honestly; absence of "
                                              "datapoints is NOT proof of "
                                              "zero traffic)"}
            except _cli.CliError as e:
                result[metric] = {"error": self.warn("cms", "DescribeMetricLast", e)}
        return result

    def type_ceilings(self, type_names: List[str]) -> Dict[str, Any]:
        """Best-effort spec ceiling lookup; the RAM action for this API is not
        yet verified for this tier, so any failure degrades to a [WARN] and
        the field is reported as unavailable (never guessed)."""
        out: Dict[str, Any] = {}
        uniq = sorted(set(type_names))[: MAX_TYPE_QUERY * 2]
        for i in range(0, len(uniq), MAX_TYPE_QUERY):
            chunk = uniq[i:i + MAX_TYPE_QUERY]
            params: Dict[str, Any] = {"RegionId": self.region}
            for n, tname in enumerate(chunk, 1):
                params["InstanceTypes.{}".format(n)] = tname
            try:
                body = _cli.call("ecs", "DescribeInstanceTypes", params,
                                 region=self.region, profile=self.profile,
                                 timeout=DEFAULT_TIMEOUT)
                self.ok()
                rows = (body.get("InstanceTypes") or {}).get("InstanceType") or []
                for row in rows:
                    tid = str(row.get("InstanceTypeId") or "")
                    if not tid:
                        continue
                    out[tid] = {
                        "CpuCoreCount": row.get("CpuCoreCount"),
                        "MemorySize": row.get("MemorySize"),
                        "InstanceTypeFamily": row.get("InstanceTypeFamily"),
                        # Raw fields, units per the official instance-type
                        # reference; no unit is asserted in the report.
                        "InstanceBandwidthRx": row.get("InstanceBandwidthRx"),
                        "InstanceBandwidthTx": row.get("InstanceBandwidthTx"),
                        "fieldsAbsent": [k for k in ("StorageIops", "VmIOPS")
                                         if k not in row],
                    }
            except _cli.CliError as e:
                self.warn("ecs", "DescribeInstanceTypes", e)
                for tname in chunk:
                    out.setdefault(tname, {"unavailable": True})
        return out

    def eips(self, lb_instance_id: Optional[str] = None) -> Tuple[List[Dict], Optional[Dict]]:
        params: Dict[str, Any] = {"RegionId": self.region}
        if lb_instance_id:
            # Narrow the listing to the EIP bound to the declared load
            # balancer (AssociatedInstanceId is a verified request parameter).
            params["AssociatedInstanceId"] = lb_instance_id
        try:
            items = _cli.paginate_page_number(
                "vpc", "DescribeEipAddresses", params,
                ["EipAddresses", "EipAddress"],
                region=self.region, profile=self.profile,
                max_pages=5,
                timeout=DEFAULT_TIMEOUT,
            )
            self.ok()
            return items, None
        except _cli.CliError as e:
            return [], self.warn("vpc", "DescribeEipAddresses", e)


# ---------------------------------------------------------------------------
# Small extraction helpers for DescribeInstances rows
# ---------------------------------------------------------------------------

def inst_public_ips(row: Dict) -> List[str]:
    pub = (row.get("PublicIpAddress") or {}).get("IpAddress") or []
    eip = str((row.get("EipAddress") or {}).get("IpAddress") or "")
    out = [str(x) for x in pub]
    if eip:
        out.append(eip)
    return out


def inst_security_groups(row: Dict) -> List[str]:
    return [str(x) for x in ((row.get("SecurityGroupIds") or {}).get("SecurityGroupId") or [])]


def fmt_rule(rule_id: str, prefix: str = "") -> List[str]:
    rule = RULES.get(rule_id)
    if not rule:
        return []
    lines = [
        "{}RULE {} [{}]".format(prefix, rule_id, rule.get("source", "caliber source noted")),
        "    verdict : {}".format(rule["verdict"]),
        "    next    : {}".format(rule["action"]),
    ]
    if rule.get("doc"):
        lines.append("    doc     : {}".format(rule["doc"]))
    else:
        lines.append("    doc     : (official doc reference pending -- caliber "
                     "source noted above; never cite a URL that is not listed)")
    return lines


# ---------------------------------------------------------------------------
# Scenario verdict builders -- each returns (verdict_lines, missing_facts[])
# ---------------------------------------------------------------------------

def verdict_certificate(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    missing: List[str] = []
    lp = facts.get("listener_protocol") or ""
    msg = (facts.get("customer_message") or "").lower()
    if lp in ("tcp", "udp"):
        lines += fmt_rule("CERT-L4")
        lines += fmt_rule("CERT-DEPLOY-VISIBILITY")
    elif lp == "https":
        lines += fmt_rule("CERT-L7")
    elif lp == "http":
        lines.append("The listener is plain HTTP (layer 7, no TLS): an HTTP "
                     "listener has no certificate field. To serve HTTPS, the "
                     "customer adds an HTTPS listener (console; done by the "
                     "customer) -- then rule CERT-L7 applies.")
        lines += fmt_rule("CERT-L7")
    else:
        missing.append("listener protocol (TCP / UDP / HTTP / HTTPS) and port "
                       "of the affected entry point -- see SELF_CHECK item 1")
        lines.append("BRANCH MODE (listener protocol not provided -- no "
                     "guessing):")
        lines.append("  IF the listener is TCP/UDP (layer 4) ->")
        lines += fmt_rule("CERT-L4", prefix="      ")
        lines += fmt_rule("CERT-DEPLOY-VISIBILITY", prefix="      ")
        lines.append("  IF the listener is HTTPS (layer 7) ->")
        lines += fmt_rule("CERT-L7", prefix="      ")
    if ("deploy" in msg or "cannot see" in msg or "not visible" in msg
            or "\u770b\u4e0d\u5230" in msg):  # CJK wording "cannot see it"
        lines += fmt_rule("CERT-DEPLOY-VISIBILITY")
    return lines, missing


def verdict_chain_service(facts: Dict[str, Any], seed_rules: List[str]) -> Tuple[List[str], List[str]]:
    """Shared decision tree for health-check and HTTP-status (502/404) cases:
    step 1 instance state -> step 2 security-group binding fact -> step 3
    listening socket (customer self-check) -> step 4 port mapping -> step 5
    local probe response shape -> step 6 LB-side capability constraints."""
    lines: List[str] = []
    missing: List[str] = []
    instances = facts.get("instances") or []

    for rule_id in seed_rules:
        lines += fmt_rule(rule_id)

    not_running = [str(r.get("InstanceId")) for r in instances
                   if str(r.get("Status") or "").lower() != "running"]
    if instances:
        if not_running:
            lines.append("Step 1 (instance state): NOT running: {}. A stopped "
                         "backend always fails health checks first.".format(", ".join(not_running)))
        else:
            lines.append("Step 1 (instance state): all {} given backend "
                         "instances are Running.".format(len(instances)))
    else:
        lines.append("Step 1 (instance state): unavailable (no instances "
                     "resolved) -- rely on customer self-check.")

    if instances:
        sgs = sorted({sg for r in instances for sg in inst_security_groups(r)})
        lines.append("Step 2 (security-group bindings, initial screen only): "
                     "{} -> {}. Whether these groups permit the load "
                     "balancer's health-check source ranges cannot be "
                     "concluded here (rule deep dive belongs to the "
                     "access-blocking tier); confirming the port is open on "
                     "the host and letting the customer re-check the LB "
                     "health status is the next evidence."
                     .format(len(sgs), ", ".join(sgs[:10])))

    hc_port = facts.get("health_check_port")
    be_port = facts.get("backend_port")
    target_port = hc_port or be_port
    lp_present = listen_port_present(facts.get("ss_output"), target_port)
    if lp_present is True:
        lines.append("Step 3 (listening socket, customer-returned): port {} "
                     "IS in the listening set -- continue down the tree."
                     .format(target_port))
    elif lp_present is False:
        lines += fmt_rule("HC-NOT-LISTENING")
        lines.append("  (evidence: customer-returned listener dump contains "
                     "no socket on port {})".format(target_port))
    else:
        missing.append("backend listener dump (`ss -ltnp` on Linux or "
                       "`netstat -ano` on Windows, customer-executed) plus "
                       "the health-check / backend port")

    if hc_port and be_port and int(hc_port) != int(be_port):
        lines += fmt_rule("HC-PORT-MISMATCH")
        lines.append("  (evidence: health-check port {} vs backend forward "
                     "port {})".format(hc_port, be_port))

    pv = probe_verdict(facts.get("probe_output"))
    if pv["class"] != "no-data":
        lines.append("Step 5 (local probe, customer-returned): {} -- {}."
                     .format(pv["class"], pv["detail"]))
        if pv["rule"]:
            lines += fmt_rule(pv["rule"])
    else:
        missing.append("local probe output (`curl -v http://127.0.0.1:"
                       "<port><uri>` and the same probe WITHOUT a Host "
                       "header, customer-executed)")

    if facts.get("lb_type") == "alb" and "https" in str(facts.get("listener_protocol") or ""):
        lines += fmt_rule("ALB-BASIC-HTTPS-BACKEND")

    lines.append("Step 6 (access control / whitelist branch): NOT verifiable "
                 "and NOT concluded by this skill -- no verified read API "
                 "exists for it yet; if everything above passes but health "
                 "checks still fail, have the customer check the listener's "
                 "access-control list in the console and note this as an "
                 "open item for a human follow-up.")
    return lines, missing


def verdict_real_ip(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    missing: List[str] = []
    lb = facts.get("lb_type") or ""
    lp = facts.get("listener_protocol") or ""
    msg = (facts.get("customer_message") or "").lower()
    if lb == "none" or "not using slb" in msg or "no load balancer" in msg or "127.0.0.1 in the log" in msg:
        lines += fmt_rule("RIP-NO-LB-LOCAL-PROXY")
    elif lb in ("alb",) or (lb == "clb" and lp in ("http", "https")):
        lines += fmt_rule("RIP-L7-XFF")
    elif lb == "clb" and lp in ("tcp", "udp"):
        lines.append("Layer-4 (TCP/UDP) listener: there is no HTTP header to "
                     "carry the client IP; the visible source address "
                     "depends on the LB's forwarding mode. The reliable "
                     "customer-side check is the backend packet capture "
                     "(customer-executed: `tcpdump -nn port <backend-port>`) "
                     "-- return one handshake line. (Official doc reference "
                     "pending; caliber from support tickets.)")
    elif lb == "nlb":
        lines.append("NLB is a layer-4 product: client-source-address "
                     "behavior depends on the instance-level client IP "
                     "preservation setting and any proxy-protocol handling "
                     "on the listener (console facts to be returned by the "
                     "customer). Official doc reference pending; do not "
                     "cite layer-7 XFF steps for NLB.")
    else:
        missing.append("the full link form: client -> (which LB product and "
                       "edition?) -> listener protocol/port -> backend port, "
                       "or 'no load balancer'")
        lines.append("BRANCH MODE (link form not stated -- the mechanism "
                     "differs per branch):")
        lines.append("  IF a layer-7 listener (CLB HTTP/HTTPS or ALB) sits in "
                     "the path ->")
        lines += fmt_rule("RIP-L7-XFF", prefix="      ")
        lines.append("  IF the chain is a local Nginx reverse proxy to IIS "
                     "with NO cloud load balancer ->")
        lines += fmt_rule("RIP-NO-LB-LOCAL-PROXY", prefix="      ")
        lines.append("  IF a layer-4 listener (CLB TCP/UDP or NLB) sits in "
                     "the path -> the HTTP-header methods above do NOT apply; "
                     "see the layer-4 notes in references/slb-backend-diagnosis__real-client-ip.md")
    return lines, missing


def verdict_selection(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    missing: List[str] = []
    msg = (facts.get("customer_message") or "").lower()
    if "ftp" in msg:
        lines += fmt_rule("SEL-FTP")
    if "zone" in msg or "cross-zone" in msg:
        lines += fmt_rule("SEL-MULTI-ZONE")
        inst = facts.get("instances") or []
        if inst:
            zs = zone_spread(inst)
            lines.append("Fact check (DescribeInstances): {} backend "
                         "instance(s) across {} zone(s): {}.".format(
                             len(inst), zs["zone_count"], ", ".join(zs["zones"])))
    if "alb" in msg and ("http" in msg or "https" in msg or "quic" in msg):
        lines += fmt_rule("ALB-BASIC-HTTPS-BACKEND")
    if not lines:
        missing.append("required protocol / port-range / edition "
                       "(see SELF_CHECK)")
    lines += fmt_rule("GAP-NO-LB-API")
    return lines, missing


def verdict_scaling(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    lines += fmt_rule("SCALING-MUST-ATTACH-LB")
    lines += fmt_rule("SCALING-SHARED-STATE")
    inst = facts.get("instances") or []
    if inst:
        zs = zone_spread(inst)
        lines.append("Fact check (DescribeInstances): {} instance(s), zones: "
                     "{}.".format(len(inst), ", ".join(zs["zones"])))
    lines += fmt_rule("SEL-MULTI-ZONE")
    return lines, []


def verdict_eip(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    lines += fmt_rule("EIP-ON-SLB-FEE")
    eips = facts.get("eips") or []
    given_ips = set()
    for row in facts.get("instances") or []:
        given_ips.update(inst_public_ips(row))
    shown = 0
    for e in eips:
        ip = str(e.get("IpAddress") or "")
        bound_type = str(e.get("InstanceType") or "")
        bound_id = str(e.get("InstanceId") or "")
        if given_ips and ip not in given_ips:
            continue
        shown += 1
        lines.append("EIP {} status={} bandwidth={}Mbps bound to {}{}".format(
            ip or "(unknown)", e.get("Status") or "?", e.get("Bandwidth") or "?",
            bound_id or "(nothing)", " (type {})".format(bound_type) if bound_type else ""))
        if bound_type == "SlbInstance":
            lines.append("  -> bound to a load balancer: the EIP configuration "
                         "fee is NOT waived (see the RULE above; the bill "
                         "itself -> billing-attribution tier or a human "
                         "ticket)")
    if shown == 0:
        lines.append("No matching EIP found among the {} visible in this "
                     "region/account (empty result stated honestly -- "
                     "cross-account or unlisted resources are invisible to "
                     "the current credential).".format("EIP list" if eips else "empty EIP list"))
    return lines, []


def verdict_handoff(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = []
    msg = facts.get("customer_message") or ""
    targets = handoff_targets(msg)
    if not targets:
        targets = [(HANDOFF[k]["target"], HANDOFF[k]["note"])
                   for k in ("performance", "billing", "access-block")]
    channels = {spec["target"] for spec in HANDOFF.values()
                if spec.get("kind") == "product-channel"}
    for target, note in targets:
        if target in channels:
            lines.append("MAIN DEMAND OUTSIDE THIS TIER -> product channel: {} "
                         "(another product, not an ECS skill; use that "
                         "product's own ticket entrance)".format(target))
        else:
            lines.append("MAIN DEMAND OUTSIDE THIS TIER -> candidate sibling tier "
                         "'{}' (name unconfirmed: confirm it exists here, "
                         "otherwise hand off to a human ticket)".format(target))
        lines.append("    reason: {}".format(note))
    lines.append("Carry the evidence sections above into the handoff; "
                 "the customer does not repeat the whole investigation.")
    for cal in FIXED_CALIBERS:
        lines.append("FIXED CALIBER: {}".format(cal))
    return lines, []


def verdict_other(facts: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    lines: List[str] = fmt_rule("GAP-NO-LB-API")
    missing = ["the exact symptom sentence / error string shown (browser, "
               "console, log or curl output)"]
    lines.append("Symptom not triaged to a known branch: re-state the "
                 "customer's own wording and match it against the Trigger "
                 "Conditions in SKILL.md before rerouting.")
    return lines, missing


SCENARIO_FUNCS = {
    "certificate": verdict_certificate,
    "health-check": lambda f: verdict_chain_service(f, []),
    "http-5xx": lambda f: verdict_chain_service(f, []),
    "real-client-ip": verdict_real_ip,
    "selection": verdict_selection,
    "scaling": verdict_scaling,
    "eip-slb": verdict_eip,
    "handoff": verdict_handoff,
    "other": verdict_other,
}

SCENARIO_REF = {
    "certificate": "references/slb-backend-diagnosis__listener-cert-placement.md",
    "health-check": "references/slb-backend-diagnosis__health-check-troubleshooting.md",
    "http-5xx": "references/slb-backend-diagnosis__health-check-troubleshooting.md",
    "real-client-ip": "references/slb-backend-diagnosis__real-client-ip.md",
    "selection": "references/slb-backend-diagnosis__lb-selection-matrix.md",
    "scaling": "references/slb-backend-diagnosis__ess-lb-integration.md",
    "eip-slb": "references/slb-backend-diagnosis__handoff-playbook.md",
    "handoff": "references/slb-backend-diagnosis__handoff-playbook.md",
    "other": "references/slb-backend-diagnosis__handoff-playbook.md",
}


# ---------------------------------------------------------------------------
# Argument parsing / validation
# ---------------------------------------------------------------------------

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="slb_backend_diagnosis.py",
        description="Read-only evidence collection + rule verdicts for the "
                    "load balancer (CLB/ALB/NLB) <-> backend ECS chain.",
    )
    p.add_argument("--region-id", required=True,
                   help="Alibaba Cloud region of the backend ECS instances, e.g. cn-hangzhou")
    p.add_argument("--instance-ids", default="",
                   help="Comma-separated backend ECS instance IDs (optional; "
                        "without them only rule calibers + checklists are produced)")
    p.add_argument("--symptom", default="auto", choices=["auto"] + SCENARIOS,
                   help="Symptom scenario; 'auto' classifies from --customer-message")
    p.add_argument("--customer-message", default="",
                   help="Customer's own symptom wording (English)")
    p.add_argument("--lb-type", default="unknown",
                   choices=["clb", "alb", "nlb", "none", "unknown"],
                   help="Load balancer product stated by the customer")
    p.add_argument("--lb-instance-id", default="",
                   help="Load-balancer instance ID stated by the customer "
                        "(lb-.../alb-.../nlb-...). This skill has NO verified "
                        "load-balancer read API, so the ID cannot be checked "
                        "for existence; it only narrows the EIP query and "
                        "labels the report.")
    p.add_argument("--listener-protocol", default="unknown",
                   choices=["tcp", "udp", "http", "https", "unknown"],
                   help="Affected listener protocol (from the customer's console self-check)")
    p.add_argument("--listener-port", type=int, default=None, help="Listener port")
    p.add_argument("--backend-port", type=int, default=None,
                   help="Backend forwarded-to port (console fact)")
    p.add_argument("--health-check-port", type=int, default=None,
                   help="Health-check port (console fact)")
    p.add_argument("--ss-output", default="",
                   help="Customer-returned `ss -ltnp` / `netstat -ano` output (verbatim text)")
    p.add_argument("--probe-output", default="",
                   help="Customer-returned local `curl -v ...` output (verbatim text)")
    p.add_argument("--hours", type=int, default=24,
                   help="CloudMonitor look-back window in hours (1-168, default 24)")
    p.add_argument("--profile", default=None, help="Optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON report")
    args = p.parse_args(argv)
    for name, value in (("listener-port", args.listener_port),
                        ("backend-port", args.backend_port),
                        ("health-check-port", args.health_check_port)):
        if value is not None and not (1 <= value <= 65535):
            p.error("{} must be between 1 and 65535".format(name))
    if not (1 <= args.hours <= 168):
        p.error("--hours must be between 1 and 168")
    if args.lb_instance_id and not _LB_ID_RE.match(args.lb_instance_id):
        p.error("--lb-instance-id must look like lb-xxx / alb-xxx / nlb-xxx")
    return args


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def build_sections(args: argparse.Namespace, facts: Dict[str, Any],
                   verdict_lines: List[str], missing: List[str]) -> List[Tuple[str, List[str]]]:
    sections: List[Tuple[str, List[str]]] = []
    scenario = facts["scenario"]

    sec1 = [
        "account UID (auto-derived via sts get-caller-identity): {}".format(facts.get("uid") or "unresolved"),
        "region: {}".format(args.region_id),
        "scenario: {}{}".format(scenario, " (auto-classified from the customer message)"
                                 if facts.get("auto_classified") else " (declared)"),
        "customer wording on record: {}".format(args.customer_message[:300] or "(none given)"),
        "declared link facts: lb-type={} lb-instance-id={} listener={} "
        "listener-port={} backend-port={} health-check-port={}".format(
            args.lb_type, args.lb_instance_id or "(not given)",
            args.listener_protocol, args.listener_port,
            args.backend_port, args.health_check_port),
        "note: load-balancer-side facts above are CUSTOMER-DECLARED; this "
        "skill has no verified load-balancer read API and cannot confirm "
        "the instance ID, listener or health-check configuration itself.",
    ]
    sections.append(("Identity and scope", sec1))

    sec2: List[str] = []
    instances = facts.get("instances") or []
    if facts.get("instances_error"):
        sec2.append("DescribeInstances unavailable ({}): recorded as a "
                    "degradation, resource-level checks skipped."
                    .format(facts["instances_error"].get("code")))
    elif not args.instance_ids and not instances:
        sec2.append("No backend instance IDs provided: no resource-level "
                    "cross-check was performed (stated honestly).")
    if instances:
        zs = zone_spread(instances)
        sec2.append("zone spread: {} zone(s) {} [{}]".format(
            zs["zone_count"], zs["zones"],
            "multi-zone" if zs["multi_zone"] else "SINGLE ZONE"))
        for row in instances[:MAX_INSTANCES]:
            sec2.append("- {} status={} zone={} type={} sg=[{}] public=[{}]".format(
                row.get("InstanceId"), row.get("Status"), row.get("ZoneId"),
                row.get("InstanceType"), ",".join(inst_security_groups(row)),
                ",".join(inst_public_ips(row))))
        if len(instances) > MAX_INSTANCES:
            sec2.append("- ... {} more instance(s) omitted from display "
                        "(cap {})".format(len(instances) - MAX_INSTANCES, MAX_INSTANCES))
    sections.append(("Backend ECS facts (ecs DescribeInstances)", sec2))

    sec3 = []
    types_ = facts.get("types") or {}
    if types_:
        for tid, info in sorted(types_.items()):
            if info.get("unavailable"):
                sec3.append("- {}: ceiling data unavailable (permission point "
                            "not yet verified for this tier; degraded)".format(tid))
            else:
                sec3.append("- {} cpu={} memGiB={} family={} bw-rx={} bw-tx={} "
                            "(raw values; storage-IOPS fields absent from the "
                            "response: {})".format(
                                tid, info.get("CpuCoreCount"), info.get("MemorySize"),
                                info.get("InstanceTypeFamily"),
                                info.get("InstanceBandwidthRx"),
                                info.get("InstanceBandwidthTx"),
                                info.get("fieldsAbsent")))
    else:
        sec3.append("No instance types resolved (no instances, or lookup skipped).")
    sections.append(("Instance-type ceilings (ecs DescribeInstanceTypes, best-effort)", sec3))

    sec4 = []
    metrics = facts.get("metrics") or {}
    if metrics:
        for iid, per in sorted(metrics.items()):
            for mname, info in sorted(per.items()):
                if "error" in info:
                    sec4.append("- {} {}: degraded ({})".format(iid, mname, info["error"].get("code")))
                elif info.get("datapoints"):
                    sec4.append("- {} {}: latest avg={} max={} over the last "
                                "{}h".format(iid, mname, info.get("latestAverage"),
                                             info.get("latestMaximum"), args.hours))
                else:
                    sec4.append("- {} {}: no datapoints in window".format(iid, mname))
    else:
        sec4.append("No metric queries issued (no resolved instances).")
    sections.append(("CloudMonitor last datapoints (cms DescribeMetricLast)", sec4))

    sec5 = []
    eips = facts.get("eips") or []
    if facts.get("eips_error"):
        sec5.append("DescribeEipAddresses unavailable ({})".format(facts["eips_error"].get("code")))
    elif eips:
        for e in eips[:MAX_INSTANCES]:
            sec5.append("- {} status={} bandwidth={}Mbps bound={}".format(
                e.get("IpAddress"), e.get("Status"), e.get("Bandwidth"),
                e.get("InstanceId") or "(none)"))
    else:
        sec5.append("No EIPs visible in this region/account.")
    sections.append(("EIP binding facts (vpc DescribeEipAddresses)", sec5))

    sections.append(("Scenario verdict -- {}".format(scenario),
                     verdict_lines or ["(no rule matched the provided facts)"]))

    checklist = SELF_CHECK_CONSOLES.get(scenario, SELF_CHECK_CONSOLES["other"])
    sec7 = []
    if missing:
        sec7.append("MISSING FACTS (needed before the tree can close):")
        sec7 += ["  ! {}".format(m) for m in missing]
    sec7.append("Console self-check items for the customer (this skill has no "
                "load-balancer-side read API -- GAP declared by rule "
                "GAP-NO-LB-API):")
    sec7 += ["  {}. {}".format(i, q) for i, q in enumerate(checklist, 1)]
    sections.append(("Customer self-check checklist", sec7))

    sec8 = ["Reference for the manual steps to relay: {}".format(SCENARIO_REF.get(scenario, "")),
            "All fixes are executed BY THE CUSTOMER in the console or on the "
            "backend host; this skill outputs step guidance + re-verification "
            "criteria only."]
    if scenario in ("eip-slb", "handoff", "other"):
        sec8.append("Handoff and boundary calibers: references/slb-backend-diagnosis__handoff-playbook.md")
    sections.append(("Next steps and boundary", sec8))
    return sections


def render_text(args: argparse.Namespace, facts: Dict[str, Any],
                sections: List[Tuple[str, List[str]]],
                status: str, next_action: str) -> str:
    bar = "=" * 66
    out = [
        bar,
        " ECS SLB BACKEND DIAGNOSIS -- read-only evidence + rule verdicts",
        " skill   : {}".format(SKILL_NAME),
        " session : {}".format(_cli.session_id()),
        bar,
    ]
    for title, lines in sections:
        out.append("")
        out.append("[{}]".format(title))
        out.extend(lines)
    out.append("")
    out.append("Graceful degradation log")
    out.extend(facts.get("warnings") or ["  (none)"])
    out.append("")
    out.append("Summary")
    out.append("-------")
    out.append("  what was checked : identity; {} read-only evidence call(s) "
               "ok, {} degraded/failed; {} scenario rule verdict(s)".format(
                   facts.get("calls_ok", 0), facts.get("calls_failed", 0),
                   sum(1 for _, ls in sections for l in ls if l.strip().startswith("RULE"))))
    out.append("  conclusion scope : cloud facts + customer-provided console "
               "facts only; load-balancer-side configuration was NOT read "
               "from the cloud (no verified API contract) -- conclusions "
               "depending on it are marked BRANCH MODE.")
    out.append("  this skill never executes commands inside instances and "
               "never changes any configuration.")
    out.append("")
    out.append("STATUS: {}".format(status))
    out.append("NEXT_ACTION: {}".format(next_action))
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Offline regression lock (no cloud, no files, no subprocess): run with
#   python3 scripts/areas/slb_backend_diagnosis/slb_backend_diagnosis.py --selftest
# The load-bearing core is `listen_port_present`, which previously matched the
# service port on a leading `.` as well and so mistook an IP's last octet for a
# listening port (e.g. reported port 80 as up when only 10.0.0.80:8080 was
# listening). Reverting that fix must fail `lpp_octet_*`.
# ---------------------------------------------------------------------------

def _run_selftest() -> int:
    rc = 0
    checked: List[str] = []

    def expect(name: str, cond: bool) -> None:
        nonlocal rc
        checked.append(name)
        if cond:
            print("PASS {}".format(name))
        else:
            print("FAIL {}".format(name))
            rc = 1

    # Real `ss -ltnp` output (whitespace-aligned, IP octets, IPv6, wildcard).
    ss = (
        "State  Recv-Q Send-Q Local Address:Port  Peer Address:Port Process\n"
        "LISTEN 0      128    10.0.0.80:8080    0.0.0.0:*    "
        "users:((\"nginx\",pid=1,fd=6))\n"
        "LISTEN 0      128    0.0.0.0:443       0.0.0.0:*    "
        "users:((\"nginx\",pid=1,fd=7))\n"
        "LISTEN 0      128    [::]:9000         [::]:*        "
        "users:((\"app\",pid=2,fd=3))\n"
    )
    # Real `netstat -ano` output (Windows column layout, LISTENING state).
    ns = (
        "  Proto  Local Address          Foreign Address        State        PID\n"
        "  TCP    10.0.0.80:8080         0.0.0.0:0              LISTENING    1234\n"
        "  TCP    0.0.0.0:443            0.0.0.0:0              LISTENING    1234\n"
    )
    # --- listen_port_present: the fixed octet false-positive (load-bearing) --
    expect("lpp_octet_ss_not_port", listen_port_present(ss, 80) is False)
    expect("lpp_octet_netstat_not_port", listen_port_present(ns, 80) is False)
    expect("lpp_octet_partial_808_absent", listen_port_present(ss, 808) is False)
    expect("lpp_octet_partial_900_absent", listen_port_present(ss, 900) is False)
    # --- listen_port_present: true positives on the colon-anchored port ------
    expect("lpp_v4_octet_real_port", listen_port_present(ss, 8080) is True)
    expect("lpp_wildcard_v4", listen_port_present(ss, 443) is True)
    expect("lpp_ipv6_bracket", listen_port_present(ss, 9000) is True)
    star = "LISTEN 0 128 *:80 0.0.0.0:* users:((\"caddy\",pid=3,fd=4))\n"
    expect("lpp_star_colon_true", listen_port_present(star, 80) is True)
    # --- listen_port_present: never guess on missing input --------------------
    expect("lpp_none_no_text", listen_port_present(None, 80) is None)
    expect("lpp_none_no_port", listen_port_present(ss, None) is None)

    # --- probe_verdict: real curl -v / telnet / nc output shapes -------------
    expect("pv_empty_reply",
           probe_verdict("curl: (52) Empty reply from server")["rule"] == "HC-EMPTY-REPLY")
    expect("pv_refused",
           probe_verdict("nc: connect to 10.0.0.80 port 80 (tcp) failed: Connection refused")["rule"]
           == "HC-NOT-LISTENING")
    expect("pv_timeout",
           probe_verdict("curl: (28) Connection timed out after 5000 milliseconds")["class"]
           == "timeout")
    pv404 = probe_verdict("< HTTP/1.1 404 Not Found\r\n")
    expect("pv_http404", pv404["rule"] == "E404-ROUTE-MISSING")
    expect("pv_http200_answered",
           probe_verdict("< HTTP/2 200 \r\n< content-type: text/html\r\n")["class"] == "answered")
    expect("pv_http502_error",
           probe_verdict("< HTTP/1.1 502 Bad Gateway\r\n")["class"] == "http-error")
    expect("pv_no_data", probe_verdict("")["class"] == "no-data")
    expect("pv_none", probe_verdict(None)["class"] == "no-data")

    # --- classify_symptom / match_error_strings / handoff_targets -----------
    expect("cs_eip", classify_symptom("our eip retention fee looks wrong") == "eip-slb")
    expect("cs_health", classify_symptom("the health check keeps failing") == "health-check")
    expect("cs_5xx", classify_symptom("getting random 502 errors") == "http-5xx")
    expect("cs_empty_other", classify_symptom("") == "other")
    expect("cs_unknown_other", classify_symptom("totally unrelated wording") == "other")
    ms = dict(match_error_strings("upstream returned empty reply from server"))
    expect("mes_empty_reply", ms.get("empty reply from server") == "HC-EMPTY-REPLY")
    mes_502 = [r for _s, r in match_error_strings("502 Bad Gateway")]
    expect("mes_502_maps", "E502-BACKEND-UNHEALTHY" in mes_502)
    mes_404 = [r for _s, r in match_error_strings("unexpected response code: 404")]
    expect("mes_404_dedup", mes_404.count("E404-ROUTE-MISSING") == 1)
    expect("mes_nopermission", "HANDOFF-RAM" in [r for _s, r in match_error_strings("NoPermission denied")])
    hops = [t for t, _n in handoff_targets("security group is blocking the port")]
    expect("ht_security_group", "area:access-block-layered" in hops)

    # --- zone_spread / instance row extractors ------------------------------
    zs = zone_spread([{"ZoneId": "cn-hangzhou-h"}, {"ZoneId": "cn-hangzhou-i"},
                      {"ZoneId": "cn-hangzhou-h"}])
    expect("zs_multi", zs["multi_zone"] is True and zs["zone_count"] == 2)
    zs1 = zone_spread([{"ZoneId": "cn-hangzhou-h"}, {"ZoneId": "cn-hangzhou-h"}])
    expect("zs_single", zs1["multi_zone"] is False and zs1["zone_count"] == 1)
    expect("zs_empty", zone_spread([])["zone_count"] == 0)
    row = {"PublicIpAddress": {"IpAddress": ["47.1.2.3"]},
           "EipAddress": {"IpAddress": "47.9.9.9"},
           "SecurityGroupIds": {"SecurityGroupId": ["sg-abc"]}}
    expect("ip_public_plus_eip", inst_public_ips(row) == ["47.1.2.3", "47.9.9.9"])
    expect("ip_only_eip", inst_public_ips({"EipAddress": {"IpAddress": "8.8.8.8"}}) == ["8.8.8.8"])
    expect("ip_none", inst_public_ips({}) == [])
    expect("sg_extract", inst_security_groups(row) == ["sg-abc"])
    expect("sg_empty", inst_security_groups({}) == [])

    # --- fmt_rule -----------------------------------------------------------
    expect("fmt_rule_unknown", fmt_rule("DOES-NOT-EXIST") == [])
    cert_l4 = fmt_rule("CERT-L4")
    expect("fmt_rule_header", cert_l4 and cert_l4[0].startswith("RULE CERT-L4 "))
    expect("fmt_rule_doc_pending", any("official doc reference pending" in ln for ln in cert_l4))
    expect("fmt_rule_prefix", fmt_rule("CERT-L4", prefix="    ")[0].startswith("    RULE CERT-L4"))

    print("SELFTEST: {} ({} checks)".format("PASS" if rc == 0 else "FAIL", len(checked)))
    return rc


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _run_selftest()
    args = parse_args(argv)

    if not _REGION_RE.match(args.region_id):
        print("[ERROR] --region-id must be a region ID like cn-hangzhou "
              "(letters, digits, hyphens).", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run with a valid --region-id.")
        return 1
    ids = [x.strip() for x in args.instance_ids.split(",") if x.strip()]
    for iid in ids:
        if not _INSTANCE_ID_RE.match(iid):
            print("[ERROR] invalid instance id: {!r} (expected i-...)".format(iid),
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: re-run with backend ECS instance IDs of the "
                  "form i-xxx (comma-separated).")
            return 1

    _cli.check_cli_available()

    # Identity pre-check (read-only; UID is only a traceability label).
    try:
        ident = _cli.call("sts", "GetCallerIdentity", {}, profile=args.profile,
                          timeout=DEFAULT_TIMEOUT)
        uid = str(ident.get("AccountId") or "")
    except _cli.CliError as e:
        print("[ERROR] credential check failed: {}".format(e), file=sys.stderr)
        print("[ERROR] Next step: configure the aliyun CLI default credential "
              "chain (`aliyun sts get-caller-identity`); never pass AK/SK to this script.",
              file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: fix credentials (aliyun sts get-caller-identity), then re-run.")
        return 1

    collector = Collector(args.region_id, args.profile)
    collector.calls_ok += 1  # identity call already succeeded

    # Scope discipline: DescribeInstances is queried ONLY for the instance IDs
    # the customer named -- this skill never enumerates whole regions.
    if ids:
        instances, instances_err = collector.instances(ids)
        if not instances and not instances_err:
            print("[WARN] DescribeInstances returned no rows for the given IDs "
                  "(not found in this region / not visible to this account)",
                  file=sys.stderr)
            collector.warnings.append("[WARN] DescribeInstances: no rows for the "
                                      "requested IDs")
    else:
        instances, instances_err = [], None

    metrics: Dict[str, Any] = {}
    if instances:
        budget = max(0, MAX_METRIC_CALLS // max(1, len(CMS_METRICS)))
        for row in instances[:budget]:
            iid = str(row.get("InstanceId") or "")
            if iid:
                metrics[iid] = collector.metric_last(iid, args.hours)

    types_info = collector.type_ceilings(
        [str(r.get("InstanceType")) for r in instances if r.get("InstanceType")])
    eips, eips_err = collector.eips(lb_instance_id=args.lb_instance_id or None)

    scenario = args.symptom
    auto = False
    if scenario == "auto":
        scenario = classify_symptom(args.customer_message)
        auto = scenario != "other"
    seed_rules: List[str] = []
    seen_rule_ids = {r for _s, r in match_error_strings(args.customer_message)}
    if scenario == "http-5xx":
        seed_rules = [r for r in ("E502-BACKEND-UNHEALTHY", "E404-ROUTE-MISSING")
                      if r in seen_rule_ids]
    elif scenario == "health-check":
        seed_rules = [r for r in ("HC-NOT-LISTENING", "HC-EMPTY-REPLY")
                      if r in seen_rule_ids]

    facts: Dict[str, Any] = {
        "uid": uid,
        "scenario": scenario,
        "auto_classified": auto,
        "instances": instances,
        "instances_error": instances_err,
        "metrics": metrics,
        "types": types_info,
        "eips": eips,
        "eips_error": eips_err,
        "warnings": collector.warnings,
        "calls_ok": collector.calls_ok,
        "calls_failed": collector.calls_failed,
        "customer_message": args.customer_message,
        "lb_type": args.lb_type,
        "lb_instance_id": args.lb_instance_id,
        "listener_protocol": args.listener_protocol if args.listener_protocol != "unknown" else "",
        "listener_port": args.listener_port,
        "backend_port": args.backend_port,
        "health_check_port": args.health_check_port,
        "ss_output": args.ss_output,
        "probe_output": args.probe_output,
    }

    if scenario in ("health-check", "http-5xx"):
        verdict_lines, missing = verdict_chain_service(facts, seed_rules)
    else:
        verdict_lines, missing = SCENARIO_FUNCS[scenario](facts)
    extra_hits = [r for _s, r in match_error_strings(args.customer_message)
                  if r not in seed_rules and r.startswith(("HC-", "E4", "E5"))
                  and scenario not in ("health-check", "http-5xx")]
    for rule_id in extra_hits:
        verdict_lines += fmt_rule(rule_id)
    if "HANDOFF-RAM" in [r for _s, r in match_error_strings(args.customer_message)]:
        verdict_lines.append("Quoted error NoPermission.RAM -> this is a "
                             "permission-channel matter (see "
                             "references/slb-backend-diagnosis__handoff-playbook.md); requestIDs may "
                             "not belong to the current account.")

    if scenario in ("certificate", "real-client-ip") and missing:
        next_action = ("Ask the customer for the missing facts listed under "
                       "MISSING FACTS, then re-run with the corresponding "
                       "flags (--listener-protocol, --lb-type) to close the "
                       "branch; do NOT guess load-balancer config.")
    elif scenario in ("health-check", "http-5xx") and missing:
        next_action = ("Have the customer run the SELF_CHECK commands and "
                       "re-run with --ss-output / --probe-output to close "
                       "the tree; if it still fails, hand off to a human "
                       "ticket with the evidence list.")
    elif scenario == "handoff":
        next_action = ("State the handoff direction (capability the next owner "
                       "provides); name a sibling tier only if it is confirmed "
                       "for this deployment, otherwise a human ticket -- either "
                       "way attach the evidence sections above.")
    else:
        next_action = ("Relay the verdicts and the customer-executed step "
                       "guidance from the referenced module; after the "
                       "customer applies changes, re-verify with the "
                       "re-check criteria in the module (read-only, this "
                       "skill never applies them).")

    if collector.calls_failed and not collector.calls_ok:
        status = "FAIL"
    elif collector.calls_failed or missing:
        status = "DEGRADED"
    else:
        status = "OK"

    sections = build_sections(args, facts, verdict_lines, missing)

    if args.json:
        payload = {
            "skill": SKILL_NAME,
            "session_id": _cli.session_id(),
            "uid": uid,
            "region": args.region_id,
            "scenario": scenario,
            "auto_classified": auto,
            "facts": {k: facts.get(k) for k in
                      ("instances", "metrics", "types", "eips",
                       "lb_type", "lb_instance_id", "listener_protocol",
                       "listener_port", "backend_port", "health_check_port")},
            "sections": [{"title": t, "lines": ls} for t, ls in sections],
            "missing_facts": missing,
            "warnings": collector.warnings,
            "calls_ok": collector.calls_ok,
            "calls_failed": collector.calls_failed,
            "status": status,
            "next_action": next_action,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        print("STATUS: {}".format(status))
        print("NEXT_ACTION: {}".format(next_action))
    else:
        print(render_text(args, facts, sections, status, next_action))
    return 1 if status == "FAIL" else 0


# ---------------------------------------------------------------------------
# Inline boundary assertions for the pure functions (normal / boundary /
# invalid), executed on every import -- a silent guard, no output on success.
# ---------------------------------------------------------------------------
assert classify_symptom("SLB health check failed on my backend") == "health-check"
assert classify_symptom("cannot get real client IP behind ALB") == "real-client-ip"
assert classify_symptom("") == "other"
assert classify_symptom("random words without any domain signal zzz") == "other"

assert listen_port_present("LISTEN 0 4096 0.0.0.0:80 0.0.0.0:* users:(\"nginx\")", 80) is True
assert listen_port_present("TCP    0.0.0.0:443    0.0.0.0:0    LISTENING   1234", 443) is True
assert listen_port_present("TCP    0.0.0.0:443    0.0.0.0:0    LISTENING   1234", 80) is False
assert listen_port_present("", 80) is None
assert listen_port_present("LISTEN 0 1 0.0.0.0:8080 0.0.0.0:*", None) is None
assert listen_port_present("not a socket table at all", 80) is False

assert probe_verdict(None)["class"] == "no-data"
assert probe_verdict("curl: (52) Empty reply from server")["rule"] == "HC-EMPTY-REPLY"
assert probe_verdict("< HTTP/1.1 404 Not Found")["class"] == "http-404"
assert probe_verdict("< HTTP/1.1 101 Switching Protocols")["class"] == "answered"

assert zone_spread([{"ZoneId": "cn-hangzhou-h"}, {"ZoneId": "cn-hangzhou-g"}])["multi_zone"] is True
assert zone_spread([])["zone_count"] == 0

assert match_error_strings("curl says Empty reply from server") == [("empty reply from server", "HC-EMPTY-REPLY")]
assert ("502", "E502-BACKEND-UNHEALTHY") in match_error_strings("clb returns 502 today")

assert handoff_targets("is my bill too high because of bandwidth")  # non-empty
assert handoff_targets("totally unrelated sentence about cooking") == []
assert epoch_ms(1).isdigit() and len(epoch_ms(1)) == 13

assert fmt_rule("CERT-L4") and "RULE CERT-L4" in fmt_rule("CERT-L4")[0]
assert fmt_rule("NO-SUCH-RULE") == []


if __name__ == "__main__":
    sys.exit(main())
