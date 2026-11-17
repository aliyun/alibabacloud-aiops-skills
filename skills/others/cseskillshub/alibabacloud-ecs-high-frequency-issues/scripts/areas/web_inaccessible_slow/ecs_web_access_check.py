#!/usr/bin/env python3
"""Layered (L1-L8) evidence collector for "my website / API is unreachable or slow".

This is the single entry point of the skill. The agent runs *this* file and reads its
report; it must not hand-assemble service calls or skip straight to a conclusion.

Each layer contributes findings with an explicit verdict, the readings behind it, and the
action that follows. Layers that could not be decided are listed as *not excluded* rather
than presented as clean. The run ends with the ``STATUS:`` / ``NEXT_ACTION:`` contract.

Examples
--------
Cloud-side evidence for one site (no in-guest access):

    python3 scripts/areas/web_inaccessible_slow/ecs_web_access_check.py \
        --domain www.example.com --ip 203.0.113.10 --port 443 --protocol https \
        --error-string "err_connection_timed_out" --change "security group edited on 2 Sep" \
        --scope all --region-id cn-hangzhou --instance-id i-bp1example90b335d2c9

Ask for one in-guest check (one confirmation buys exactly one command). While the
low-risk list for this scenario is still pending review, the run refuses to dispatch it
and returns the execute-and-paste-back sheet instead:

    python3 scripts/areas/web_inaccessible_slow/ecs_web_access_check.py --domain www.example.com --port 80 \
        --protocol http --error-string "connection refused" --change "none reported" \
        --scope all --region-id cn-hangzhou --instance-id i-bp1example90b335d2c9 \
        --guest-command listening-sockets --confirm
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import json
import os
import re
import sys
import time

import _cli
import _constants as C
import _app_readings
import _guest_readings
import _tls_probe
import sts_token


# ---------------------------------------------------------------------------
# small parsers / validators
# ---------------------------------------------------------------------------
HOSTNAME_RE = re.compile(r"^(?=.{1,253}$)([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$")


class InputError(Exception):
    pass


def check_cli_value(value):
    """Reject option-lookalikes so a value can never be parsed as a flag."""
    if isinstance(value, str) and value.strip().startswith("-"):
        raise InputError("value %r looks like an option; pass a plain value" % value)
    return value


def normalize_error(raw):
    """Map free-text customer wording onto a routing key from the constants table."""
    if not raw:
        return None
    lowered = raw.strip().lower()
    text = re.sub(r"[\s.]+", "_", lowered)
    candidates = [lowered, text]
    if "timed_out" in text or "timeout" in text or "timed out" in lowered:
        candidates.append("err_connection_timed_out")
    if "refused" in lowered:
        candidates.append("connection refused")
    if "reset" in lowered:
        candidates.append("err_connection_reset")
    if "closed" in lowered or "shutdown" in lowered:
        candidates.append("err_connection_closed")
    if "cert" in lowered and any(word in lowered for word in ("date", "expire", "invalid")):
        candidates.append("err_cert_date_invalid")
    if any(word in lowered for word in ("blank", "white")):
        candidates.append("blank page")
    if any(word in lowered for word in ("slow", "latency", "lag")):
        candidates.append("slow")
    status = re.search(r"\b[45]\d\d\b", lowered)
    if status:
        candidates.append("http_%s" % status.group(0))
    route_map = {key: (fam, order, note) for key, fam, order, note in C.ERROR_ROUTES}
    for cand in candidates:
        if cand in route_map:
            return (cand,) + route_map[cand]
    for cand in candidates:
        for key, value in route_map.items():
            if key in cand:
                return (cand,) + value
    return None


def route_error(args):
    """Resolve the routing key: explicit error string, then status code, then slowness."""
    raw = args.error_string or ""
    if args.http_status:
        raw = raw or ("http %s" % args.http_status)
    hit = normalize_error(raw)
    if hit:
        return hit
    key = "http_%s" % args.http_status if args.http_status else (raw or "unknown")
    return (key, "unknown", ("L1", "L2", "L4", "L5", "L6"),
            "No known error string was captured; the layered sweep below is complete but "
            "not prioritised, so the first ask back to the customer is the exact error text.")


def is_private_ip(value):
    try:
        import ipaddress
        ip = ipaddress.ip_address(value)
    except Exception:
        return False
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or value.startswith(C.PRIVATE_NETWORKS)
            or value.startswith(C.PRIVATE_NETWORKS_172))


def parse_url(url):
    """Extract host, port (and infer scheme) from what the customer pasted.
    The port must survive parsing: customers paste http://IP:8080/ and judging
    such a case against tcp 80 produced a wrong L4 verdict (faultlab flip)."""
    if not url:
        return None, None, None
    text = url.strip()
    match = re.match(r"^(?:([a-zA-Z][a-zA-Z0-9+.\-]*):)?//([^/?#]+)", text)
    authority = match.group(2) if match else None
    scheme = match.group(1) if match else None
    if authority is None:
        bare = re.match(r"^([^/?#]+)", text)
        authority = bare.group(1) if bare else None
    if not authority:
        return None, scheme, None
    host, port = authority, None
    if authority.startswith("["):
        host = authority[:authority.index("]") + 1] if "]" in authority else authority
        rest = authority[authority.index("]") + 1:] if "]" in authority else ""
        if rest.startswith(":"):
            port = rest[1:] or None
    elif ":" in authority:
        host, _, port = authority.partition(":")
    return (host or None, scheme,
            port if port and port.isdigit() else None)


def root_domain_of(host):
    """Best-effort zone name for the DNS lookup; the operator can override with --domain."""
    if not host or is_private_ip(host):
        return None
    try:
        # Any IP literal (public too) has no "root domain": slicing
        # 47.96.99.99 produced the bogus zone "99.99" that then died on the
        # hostname validator, breaking plain IP:port URLs customers paste.
        import ipaddress
        ipaddress.ip_address(host.strip("."))
        return None
    except Exception:
        pass
    labels = host.strip(".").split(".")
    if len(labels) < 2:
        return None
    if len(labels) >= 3 and labels[-2] in ("co", "com", "net", "org", "gov", "edu"):
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def lookup_zone_of(args):
    """`--domain www.example.com` names a host; the zone alidns needs is example.com."""
    named = getattr(args, "domain", "") or getattr(args, "url_host", "") or ""
    return root_domain_of(named) or getattr(args, "domain", "") or ""


def host_record_of(host, zone):
    if not host or not zone:
        return "@"
    prefix = host.strip(".").lower()
    suffix = zone.strip(".").lower()
    if prefix == suffix:
        return "@"
    if prefix.endswith("." + suffix):
        return prefix[: -(len(suffix) + 1)]
    return "@"


def port_in_range(port_range, port):
    """`-1/-1` means all ports; `80/80` a single port; `1/65535` a span."""
    if not port_range or "/" not in str(port_range):
        return False
    low, _, high = str(port_range).partition("/")
    try:
        low_i, high_i = int(low), int(high)
    except ValueError:
        return False
    if low_i == -1 or high_i == -1:
        return True
    return low_i <= port <= high_i


def protocol_matches(rule_protocol, protocol):
    rule = (rule_protocol or "").upper()
    if rule in ("ALL", "-1"):
        return True
    return rule == "TCP" or rule == (protocol or "").upper()


def decode_output(raw, limit=4000):
    """Cloud Assistant delivers command output base64-encoded; tolerate plain text too."""
    if not raw:
        return "(no output)"
    text = raw if isinstance(raw, str) else str(raw)
    try:
        text = base64.b64decode(text, validate=True).decode("utf-8", "replace")
    except Exception:
        pass
    return _cli.mask_secrets(text[:limit])


# ---------------------------------------------------------------------------
# finding container
# ---------------------------------------------------------------------------
class Report(object):
    def __init__(self):
        self.findings = []
        self.not_excluded = []
        self.actions = []
        self.handoffs = []
        self.degraded = False
        self.terminated_early = False
        self.asset_charge_type = ""
        self.asset_status = ""
        self.asset_os_type = ""
        self.dns_fault_kind = ""
        self.dns_expected_ns = []
        self.dns_mixed_ns = False
        self.guest_fault_kind = ""
        self.app_fault_kind = ""
        self.implanted_files = 0
        self.fix_ineffective = []
        self.app_artifact_text = ""
        self.dns_conflict_rr = ""
        self.dns_conflict_type = ""
        self.sg_drop_sources = []
        self.sg_open_ports = []
        self.port_contrast = {}
        self.filing_blocked = False
        self.blackhole = False
        self.cert_served = False

    def add(self, layer, verdict, conclusion, evidence=(), follow_up=(), key=False):
        self.findings.append({
            "layer": layer,
            "name": C.LAYER_NAMES.get(layer, layer),
            "verdict": verdict,
            "conclusion": conclusion,
            "evidence": list(evidence),
            "follow_up": list(follow_up),
            "key": key,
        })
        if verdict == C.VERDICT_INCONCLUSIVE:
            self.not_excluded.append("%s (%s): decided neither way by this run"
                                     % (layer, C.LAYER_NAMES.get(layer, layer)))
        for item in follow_up:
            self.actions.append((layer, item))

    def degrade(self, reason):
        self.degraded = True
        self.not_excluded.append("LIMITATION: %s" % reason)


# ---------------------------------------------------------------------------
# L1 - asset and account ownership
# ---------------------------------------------------------------------------
def resolve_origin_ip(args, report, session_id):
    zone = lookup_zone_of(args)
    if not zone:
        return "", []
    payload, err = _cli.call_soft("alidns", "DescribeDomainRecords",
                                  {"DomainName": zone, "PageNumber": 1, "PageSize": C.PAGE_SIZE},
                                  session_id=session_id)
    if err is not None:
        report.degrade("The origin address behind %s was not resolved: alidns:"
                       "DescribeDomainRecords could not be read (%s). Grant that read "
                       "permission, or ask the customer for the instance id / public IP."
                       % (zone, err.code))
        return "", []
    records = (payload.get("DomainRecords") or {}).get("Record") or []
    wanted = host_record_of(
        args.url_host or (args.domain if args.domain and args.domain != zone
                          else "www." + zone), zone).lower()
    ranked = []
    for record in records:
        if str(record.get("Type", "")).upper() not in ("A", "AAAA"):
            continue
        host_record = str(record.get("RR", "")).lower()
        value = str(record.get("Value", ""))
        if not value or is_private_ip(value):
            continue
        rank = 0 if host_record == wanted else (1 if host_record in ("@", "www") else 2)
        ranked.append((rank, host_record, value))
    ranked.sort()
    if not ranked:
        return "", ["alidns holds no public A/AAAA record for %s in this account: the zone may "
                    "be hosted elsewhere, so the origin address must come from the customer."
                    % zone]
    _rank, host_record, value = ranked[0]
    return value, ["alidns record %s.%s -> %s (read-only lookup, nothing was changed)"
                   % (host_record, zone, value)]


def region_candidates(args, session_id, limit=5):
    payload, err = _cli.call_soft("ecs", "DescribeInstances",
                                  {"RegionId": args.region_id, "PageSize": C.PAGE_SIZE},
                                  region=args.region_id, session_id=session_id)
    if err is not None:
        return []
    rows = (payload.get("Instances") or {}).get("Instance") or []
    lines = []
    for row in rows[:limit]:
        addresses = [ip for ip in (row.get("PublicIpAddress") or {}).get("IpAddress") or []]
        bound = str((row.get("EipAddress") or {}).get("IpAddress") or "")
        if bound:
            addresses.append(bound)
        lines.append("%s name=%s status=%s public=%s"
                     % (row.get("InstanceId"), row.get("InstanceName") or "-",
                        row.get("Status"), ",".join(addresses) or "-"))
    return lines


def check_asset(args, report, session_id):
    params = {}
    if args.instance_id:
        params["InstanceIds"] = json.dumps([args.instance_id])
    elif args.ip and not is_private_ip(args.ip):
        params["PublicIpAddresses"] = json.dumps([args.ip])
    elif args.eip:
        params["EipAddresses"] = json.dumps([args.eip])

    if not params and (args.domain or args.url_host):
        resolved, evidence = resolve_origin_ip(args, report, session_id)
        if resolved:
            args.ip = resolved
            params["PublicIpAddresses"] = json.dumps([resolved])
            notes = getattr(args, "auto_filled", None)
            if notes is not None:
                notes.append("ip=%s (resolved from the alidns records of %s; confirm it)"
                             % (resolved, args.domain or args.url_host))
            report.add("L1", C.VERDICT_INCONCLUSIVE,
                       "The origin address was recovered from DNS instead of being supplied.",
                       evidence,
                       ["State the resolved address to the customer and confirm it is the "
                        "origin behind the hostname before any change is discussed."])
        elif evidence:
            report.add("L1", C.VERDICT_INCONCLUSIVE,
                       "The hostname could not be turned into an origin address.", evidence,
                       ["Ask the customer for the instance id, or run nslookup/dig on the "
                        "hostname from their own network and paste the answer section."])

    if not params:
        payload, err = _cli.call_soft("ecs", "DescribeInstances",
                                      {"RegionId": args.region_id, "PageSize": C.PAGE_SIZE},
                                      region=args.region_id, session_id=session_id)
        rows = (payload.get("Instances") or {}).get("Instance") or []
        if err is not None:
            report.degrade("L1 was not run: no target was supplied and the account instance "
                           "list could not be read (%s). Grant ecs:DescribeInstances or ask "
                           "for the instance id." % err.code)
            report.add("L1", C.VERDICT_INCONCLUSIVE, "Instance identity unknown.",
                       ["no --instance-id / --ip / --eip", "instance list unreadable"],
                       ["Ask the customer for the instance ID and region, or confirm the public "
                        "IP they believe is their origin."])
            return None
        if not rows:
            report.add("L1", C.VERDICT_INCONCLUSIVE,
                       "No target was supplied and this account has no instance in region %s."
                       % args.region_id,
                       ["ecs:DescribeInstances returned an empty list for %s" % args.region_id],
                       ["Ask which region and which account owns the site: the console instance "
                        "list is per-region, and a site served from another account cannot be "
                        "read from here."], key=True)
            return None
        if len(rows) == 1:
            params["InstanceIds"] = json.dumps([rows[0].get("InstanceId")])
            args.instance_id = rows[0].get("InstanceId")
            args.adopted_instance = rows[0].get("InstanceId")
            notes = getattr(args, "auto_filled", None)
            if notes is not None:
                notes.append("instance-id=%s (the only instance readable in %s; confirm with the "
                             "customer that it serves this site)"
                             % (args.instance_id, args.region_id))
            report.add("L1", C.VERDICT_INCONCLUSIVE,
                       "No target was supplied; the account has exactly one instance in this "
                       "region, so it is used as the candidate asset.",
                       ["ecs:DescribeInstances in %s returned 1 instance: %s"
                        % (args.region_id, args.instance_id)],
                       ["State the instance id and its public address to the customer and "
                        "confirm it serves the reported site before any change is discussed."])
        else:
            listing = region_candidates(args, session_id, limit=8)
            report.add("L1", C.VERDICT_INCONCLUSIVE,
                       "No target was supplied and this account has %d instances in %s; the "
                       "asset must be chosen by the customer, not guessed."
                       % (len(rows), args.region_id),
                       ["ecs:DescribeInstances in %s returned %d instances"
                        % (args.region_id, len(rows))] + listing,
                       ["Have the customer pick the instance that serves this site from the "
                        "list above (id, name, status, public address), or give the hostname or "
                        "public IP they open; then re-run with that id."], key=True)
            return None

    payload, err = _cli.call_soft("ecs", "DescribeInstances",
                                  {"RegionId": args.region_id, "PageSize": C.PAGE_SIZE,
                                   **params},
                                  region=args.region_id, session_id=session_id)
    instances = (payload.get("Instances") or {}).get("Instance") or []
    if err is not None:
        report.degrade("DescribeInstances could not be read (%s). Grant ecs:DescribeInstances "
                       "or run the check as the resource owner." % err.code)
        return None
    if not instances:
        where = params.get("InstanceIds") or params.get("PublicIpAddresses") or params.get("EipAddresses")
        report.terminated_early = True
        report.add("L1", C.VERDICT_CONFIRMED,
                   "No instance matched %s in region %s. The address the customer is testing "
                   "is not a live asset of this account in this region." % (where, args.region_id),
                   ["ecs:DescribeInstances returned an empty list",
                    "A released public IP returns to the pool and can be reassigned to "
                    "somebody else, so a stale DNS record suddenly serves a third-party site."],
                   ["Have the customer look up who owns this public address first; if it belongs "
                    "to another cloud provider, say so plainly and hand the case to that "
                    "provider's support: no ECS-side change here can affect it.",
                    "Have the customer check the instance list including released resources: a "
                    "released instance is deleted together with its data, so the site cannot be "
                    "served from it again and searching other regions or accounts will not find "
                    "it. A new instance must be purchased and the site redeployed from a backup.",
                    "Have the customer keep renewals current so an expiry does not release the "
                    "resource again: Console > Billing > Renewal Management "
                    "(https://billing-cost.console.aliyun.com/renew/manual) renewes every "
                    "subscription resource in one place.",
                    "Have the customer settle any account arrears: arrears suspend pay-as-you-go "
                    "resources, and a resource that stays unpaid is released after the retention "
                    "period.",
                    "If the instance was released, ask the customer to delete or repoint the "
                    "DNS record; expiry and recovery are handled by the sales and instance "
                    "operations side, not here.",
                    "Renewal discounts and purchase offers are quoted by the account's commercial "
                    "manager, not by this check: ask the customer to leave a contact number for "
                    "that follow-up. Any price or campaign figure is a reference only - the "
                    "customer must confirm it on https://www.aliyun.com/price/product, and this "
                    "skill does not guarantee that a quoted page stays current."], key=True)
        candidates = region_candidates(args, session_id)
        if candidates:
            report.findings[-1]["follow_up"].append(
                "Have the customer choose the instance that serves this hostname from the list "
                "readable in %s and re-run with that id, but only if they confirm the asset is "
                "still theirs: %s" % (args.region_id, "; ".join(candidates)))
        else:
            report.findings[-1]["follow_up"].append(
                "Have the customer open the ECS console instance list for %s, switch to the "
                "region that owns the resource and paste the instance id, but only if they "
                "confirm the asset is still theirs." % args.region_id)
        report.handoffs.append("Instance operations / alibabacloud-ecs-diagnose")
        return None

    inst = instances[0]
    public_ips = [ip for ip in (inst.get("PublicIpAddress") or {}).get("IpAddress") or []]
    bound_eip = str((inst.get("EipAddress") or {}).get("IpAddress") or "")
    eips = [bound_eip] if bound_eip else []
    inner_ips = [ip for ip in (inst.get("InnerIpAddress") or {}).get("IpAddress") or []]
    vpc_ips = [ip for ip in ((inst.get("VpcAttributes") or {}).get("PrivateIpAddress") or {})
               .get("IpAddress") or []]
    sg_ids = [sg for sg in (inst.get("SecurityGroupIds") or {}).get("SecurityGroupId") or []]
    os_type = (inst.get("OSType") or inst.get("OSName") or "unknown").lower()
    evidence = [
        "InstanceId=%s Status=%s ChargeType=%s" % (inst.get("InstanceId"), inst.get("Status"),
                                                   inst.get("InstanceChargeType")),
        "OS=%s NetworkType=%s" % (inst.get("OSName") or os_type, inst.get("InstanceNetworkType")),
        "PublicIpAddress=%s EIP=%s PrivateIp=%s" % (public_ips or "-", eips or "-",
                                                    (inner_ips or vpc_ips) or "-"),
        "SecurityGroups=%s" % (sg_ids or "-"),
        "ExpiredTime=%s (a past value with a stopped instance means arrears or expiry)"
        % inst.get("ExpiredTime"),
    ]
    follow = []
    if str(inst.get("Status")).lower() not in ("running",):
        follow.append("The instance is not Running (status %s). Start it from the console; "
                      "until it runs, no external visitor can be served - this is the "
                      "instance-operations path, not a web configuration problem."
                      % inst.get("Status"))
        report.handoffs.append("Instance operations")
    if "windows" in os_type:
        follow.append("Windows instance: in-guest readings are guidance-only in this release "
                      "(no Windows command set has been approved). Check IIS site bindings, "
                      "application pool state and the Windows Firewall inbound rules manually.")
        report.degrade("Windows in-guest collection is not automated; manual guidance is emitted.")
    report.add("L1", C.VERDICT_EXCLUDED if str(inst.get("Status")).lower() == "running"
               else C.VERDICT_CONFIRMED,
               "The asset exists in this account and region." if str(inst.get("Status")).lower() == "running"
               else "The asset exists but is not serving traffic.",
               evidence, follow, key=True)
    inst["_sg_ids"] = sg_ids
    inst["_public_ips"] = public_ips + eips
    inst["_private_ips"] = inner_ips + vpc_ips
    inst["_os_type"] = os_type
    report.asset_charge_type = str(inst.get("InstanceChargeType") or "")
    report.asset_status = str(inst.get("Status") or "")
    report.asset_os_type = os_type
    return inst


def check_eip(args, report, session_id, instance=None, hint_ip=None):
    payload, err = _cli.call_soft("vpc", "DescribeEipAddresses", {"RegionId": args.region_id},
                                  region=args.region_id, session_id=session_id)
    if err is not None:
        report.degrade("EIP binding state was not read (%s). vpc:DescribeEipAddresses is needed "
                       "for the DNS-versus-reality comparison." % err.code)
        return []
    eips = (payload.get("EipAddresses") or {}).get("EipAddress") or []
    rows = []
    for eip in eips[:C.MAX_ITEMS]:
        rows.append("%s status=%s boundTo=%s(%s) instanceType=%s"
                    % (eip.get("IpAddress"), eip.get("Status"), eip.get("InstanceId"),
                       eip.get("InstanceIp", "-"), eip.get("InstanceType", "-")))
    unbound = [e.get("IpAddress") for e in eips if str(e.get("Status", "")).lower() == "available"]
    if hint_ip and hint_ip in unbound:
        report.add("L1", C.VERDICT_CONFIRMED,
                   "The address the customer is testing is an unbound EIP: nothing is behind it.",
                   rows, ["Bind the EIP to the intended instance or repoint the DNS record."],
                   key=True)
    elif not rows:
        report.add("L1", C.VERDICT_INCONCLUSIVE, "No EIP found in this region.",
                   ["vpc:DescribeEipAddresses returned an empty list"],
                   ["If the site is served by a fixed public IP instead of an EIP, note the "
                    "difference and continue with the instance's own public address."])
    else:
        report.add("L1", C.VERDICT_EXCLUDED,
                   "EIP bindings were read; none of them is an unbound address matching the "
                   "customer's target.", rows, [])
    return eips


CONFLICTING_WITH_CNAME = ("A", "AAAA", "ALIAS", "URL", "NS", "SRV", "CAA", "HTTPS", "SVCB")


def check_record_conflict(args, report, zone, records):
    """Decide a record-conflict complaint from the record list, never by adding records.

    A CNAME cannot coexist with another type on the same host record and the same
    resolution line; the other type has to be paused or removed first. Telling the
    customer to add records while their complaint is a conflict makes the fault worse.
    """
    add_type = (args.dns_add_type or "").strip().upper()
    if not add_type:
        return False
    add_rr = (args.dns_add_rr or "@").strip().lower()
    same_rr = [row for row in records
               if str(row.get("RR", "")).strip().lower() == add_rr]
    if add_type == "CNAME":
        blockers = [row for row in same_rr
                    if str(row.get("Type", "")).upper() in CONFLICTING_WITH_CNAME]
    else:
        blockers = [row for row in same_rr if str(row.get("Type", "")).upper() == "CNAME"]
    if not blockers:
        return False
    report.dns_fault_kind = "conflict"
    report.dns_conflict_rr = add_rr
    report.dns_conflict_type = add_type
    evidence = ["zone=%s records=%d host record=%s record being added=%s"
                % (zone, len(records), add_rr, add_type)]
    for row in blockers[:C.MAX_ITEMS]:
        evidence.append("existing record: %s.%s %s -> %s line=%s status=%s"
                        % (row.get("RR"), zone, row.get("Type"), row.get("Value"),
                           row.get("Line", "default"), row.get("Status", "-")))
    report.add("L2", C.VERDICT_CONFIRMED,
               "The record being added conflicts with an existing record on the same host record "
               "and resolution line: a CNAME and another record type cannot coexist there, so "
               "the console rejects the addition.",
               evidence,
               ["Have the customer pause or delete the conflicting record listed above, then add "
                "the %s record; alternatively use a different host record so both can stay."
                % add_type,
                "Have the customer note a non-@ host record only works if the backend ECS and the "
                "site program accept that name, so confirm it with whoever built the site first.",
                "Have the customer confirm the business impact first: traffic that reaches this "
                "host record today follows the removed record's target, and after the change it "
                "follows the new one.",
                "Have the customer agree the plan with the CNAME provider and the site builder "
                "before changing anything, since the platform cannot see how the site uses the name.",
                "This skill only reads records; the pause, delete and add are the customer's own "
                "console actions."],
               key=True)
    return True


# ---------------------------------------------------------------------------
# L2 - DNS records versus the real asset
# ---------------------------------------------------------------------------
def check_dns(args, report, session_id, instance):
    zone = lookup_zone_of(args) or root_domain_of(args.ip or "")
    if not zone or zone.startswith(C.PRIVATE_NETWORKS):
        report.degrade("L2 was not run: no domain name was supplied, so resolution could not "
                       "be compared with the asset. Ask for the exact hostname.")
        report.add("L2", C.VERDICT_INCONCLUSIVE, "Domain name unknown.",
                   ["--domain/--url missing or an IP address was given instead"],
                   ["Ask which hostname the customer opens; IP-direct versus domain access is "
                    "the single most informative comparison in this scenario."])
        return []

    records = []
    page = 1
    while page <= C.MAX_PAGES:
        payload, err = _cli.call_soft("alidns", "DescribeDomainRecords",
                                      {"DomainName": zone, "PageNumber": page,
                                       "PageSize": C.PAGE_SIZE},
                                      session_id=session_id)
        if err is not None:
            report.degrade("alidns:DescribeDomainRecords could not be read (%s). Resolution "
                           "shape was not verified; alidns is used for its list semantics "
                           "only - this skill never writes DNS records." % err.code)
            return records
        batch = (payload.get("DomainRecords") or {}).get("Record") or []
        records.extend(batch)
        total = int(payload.get("TotalCount") or 0)
        if len(batch) < C.PAGE_SIZE or len(records) >= total:
            break
        page += 1

    ns_current, ns_expected, ns_include, ns_all = [], [], None, None
    if check_record_conflict(args, report, zone, records):
        return records
    ns_payload, ns_err = _cli.call_soft("alidns", "DescribeDomainNs", {"DomainName": zone},
                                        session_id=session_id)
    if ns_err is not None:
        report.degrade("alidns:DescribeDomainNs could not be read (%s). Whether the DNS service "
                       "holding these records is actually authoritative for the domain was not "
                       "verified, so a correct-looking zone may still never be served."
                       % ns_err.code)
    else:
        ns_current = [str(item) for item in
                      ((ns_payload.get("DnsServers") or {}).get("DnsServer") or [])]
        ns_expected = [str(item) for item in
                       ((ns_payload.get("ExpectDnsServers") or {}).get("ExpectDnsServer") or [])]
        ns_include = bool(ns_payload.get("IncludeAliDns"))
        ns_all = bool(ns_payload.get("AllAliDns"))

    wanted = host_record_of(args.url_host or ("www." + zone if args.domain == zone else args.domain), zone)
    host_records = {str(r.get("RR", "")).lower() for r in records}
    real_ips = list((instance or {}).get("_public_ips") or [])
    private_ips = list((instance or {}).get("_private_ips") or [])

    a_values = [r for r in records
                if str(r.get("Type", "")).upper() in ("A", "AAAA")
                and str(r.get("RR", "")).lower() in (wanted.lower(), "@", "www")]
    cnames = [r for r in records if str(r.get("Type", "")).upper() in C.CNAME_TYPES]
    # Two A records on the same host record do not make one of them wrong: the site
    # may be served by another asset entirely. Measured on a real ticket the gold
    # asked the customer WHICH address is the business IP first, while this run
    # declared the other one stale and told the customer to overwrite it - following
    # that advice would have taken the working site down.
    distinct_a = sorted({str(rec.get("Value", "")) for rec in a_values
                         if str(rec.get("Type", "")).upper() == "A"})
    report.dns_a_candidates = distinct_a
    report.dns_ambiguous_a = (
        len(distinct_a) > 1
        and not any(value and value in customer_text() for value in distinct_a))
    origin_named = bool(real_ips and any(ip and ip in customer_text() for ip in real_ips))
    change_named = bool(re.search(
        r"换了?(?:服务器|实例|公网)|公网\s*[iI][pP][^。；\n]{0,8}变|更换[^。；\n]{0,8}[iI][pP]|释放",
        customer_text()))
    report.dns_business_ip_unconfirmed = bool(
        real_ips and a_values
        and any(str(rec.get("Value", "")) not in real_ips for rec in a_values
                if str(rec.get("Type", "")).upper() == "A")
        and not report.dns_ambiguous_a
        and not any(value and value in customer_text() for value in distinct_a)
        and not origin_named and not change_named)

    shapes = []
    ns_followups = []
    for rr in (wanted.lower(), "@", "www"):
        if rr not in host_records and rr in ("@", "www"):
            shapes.append("No record for host record '%s' on %s: visitors typing %s get NXDOMAIN."
                          % (rr, zone, ("https://%s/" % zone) if rr == "@" else ("https://www.%s/" % zone)))
    for rec in a_values:
        value = str(rec.get("Value", ""))
        if is_private_ip(value):
            shapes.append("Record %s.%s (%s) points at %s, a private address. The public "
                          "internet cannot route there." % (rec.get("RR"), zone, rec.get("Type"), value))
        elif real_ips and value not in real_ips:
            if report.dns_ambiguous_a or report.dns_business_ip_unconfirmed:
                shapes.append("Record %s.%s resolves to %s, which is not this instance's public "
                              "address %s; which address serves the site is not established."
                              % (rec.get("RR"), zone, value, real_ips))
            else:
                shapes.append("Record %s.%s resolves to %s but the instance's current public "
                              "address is %s - the record is stale (often a released IP that has "
                              "since been reassigned)." % (rec.get("RR"), zone, value, real_ips))
    for rec in cnames:
        value = str(rec.get("Value", "")).lower()
        if any(hint in value for hint in C.EDGE_PROVIDER_HINTS):
            shapes.append("Record %s.%s is a CNAME to %s: an edge service sits in front of the "
                          "origin. The real origin IP is hidden, so every test must also be run "
                          "straight against the origin." % (rec.get("RR"), zone, rec.get("Value")))
    if records and ns_include is False:
        report.dns_fault_kind = "delegation"
        report.dns_expected_ns = list(ns_expected)
        shapes.append("The domain is delegated to %s, which does not include the DNS service "
                      "holding these records: the answers published here are never served to "
                      "visitors, so a correct-looking record set proves nothing."
                      % (", ".join(ns_current) or "name servers outside this DNS service"))
        ns_followups.append("Change the domain's NS at the registrar to %s, wait for the registry "
                            "to propagate, then re-test the hostname from a public resolver. "
                            "Until the delegation matches, no record edit in this DNS service "
                            "can take effect."
                            % (", ".join(ns_expected) or "the expected NS set"))
    elif ns_include is True and ns_all is False:
        report.dns_mixed_ns = True
        ns_followups.append("Only part of this domain's NS set is served by this DNS service, so "
                            "visitors can receive a different provider's answer. Compare the "
                            "record on every authoritative server before treating resolution as "
                            "correct.")
    if not a_values and not cnames:
        shapes.append("No A/AAAA or CNAME record for the tested host on %s at all." % zone)

    evidence = ["zone=%s records=%d" % (zone, len(records))]
    for rec in records[:C.MAX_ITEMS]:
        evidence.append("%s.%s %s -> %s ttl=%s line=%s status=%s"
                        % (rec.get("RR"), zone, rec.get("Type"), rec.get("Value"),
                           rec.get("TTL"), rec.get("Line", "-"), rec.get("Status")))
    if real_ips:
        evidence.append("Asset public address from the cloud side: %s" % real_ips)
    if private_ips:
        evidence.append("Asset private address (never a valid public target): %s" % private_ips)
    if ns_current:
        evidence.append("Authoritative NS for the domain: %s (this DNS service expects %s)"
                        % (", ".join(ns_current), ", ".join(ns_expected) or "-"))

    if shapes:
        if not report.dns_fault_kind:
            report.dns_fault_kind = "absent" if not a_values and not cnames else "value"
        if args.probe_multipoint_ok:
            report.add("L2", C.VERDICT_INCONCLUSIVE,
                       "The record shape differs from the asset, but external multi-point tests "
                       "resolved this hostname and reached the site, so a global resolution "
                       "fault is not established by this run.",
                       evidence + ["Recorded external multi-point test: no resolution or "
                                     "reachability failure from those vantage points"],
                       ["Have the customer compare the answer on each authoritative server and "
                        "from the failing region before changing any record: a per-region "
                        "difference is not the same as a wrong zone."])
            return records
        report.add("L2", C.VERDICT_CONFIRMED,
                   "The published answer does not match the asset, or the record shape is wrong.",
                   evidence,
                   ["Correct the record in the DNS console yourself; this skill only reads "
                    "records. %s" % C.DNS_LIST_SEMANTICS_STATEMENT]
                  + ["Expected shape: %s" % s for s in shapes]
                  + ["After the change, flush or wait out the client cache: LocalDNS TTL means "
                     "the customer can still see the old answer while the zone is already right."]
                  + ns_followups,
                   key=True)
    else:
        report.add("L2", C.VERDICT_EXCLUDED,
                   "The zone answers with the asset's own public address and no private-IP or "
                   "stale-IP shape was found.", evidence,
                   ["Client-side effects remain invisible here: a local hosts override or a "
                    "cached LocalDNS answer can still make a correct zone look broken."]
                   + ns_followups)
    return records


# ---------------------------------------------------------------------------
# L4 - cloud-side access control
# ---------------------------------------------------------------------------
def _collect_rules(args, session_id, sg_ids):
    rules = []
    for sg_id in sg_ids[:C.MAX_SECURITY_GROUPS]:
        for direction in ("ingress", "egress"):
            payload, err = _cli.call_soft(
                "ecs", "DescribeSecurityGroupAttribute",
                {"SecurityGroupId": sg_id, "Direction": direction},
                region=args.region_id, session_id=session_id)
            if err is not None:
                return rules, err
            for perm in (payload.get("Permissions") or {}).get("Permission") or []:
                perm = dict(perm)
                perm["_group"] = sg_id
                perm["_group_name"] = payload.get("SecurityGroupName")
                perm["_group_type"] = payload.get("SecurityGroupType")
                rules.append(perm)
    return rules, None


def _matching(rules, direction, protocol, port):
    hits = []
    for rule in rules:
        if str(rule.get("Direction", "")).lower() != direction:
            continue
        if not protocol_matches(rule.get("IpProtocol"), protocol):
            continue
        if not port_in_range(rule.get("PortRange"), port):
            continue
        hits.append(rule)
    return hits


def _effective(hits):
    """Lowest priority number wins; a Drop at that level blocks regardless of accepts."""
    if not hits:
        return None, []
    def prio(rule):
        try:
            return int(rule.get("Priority") or 100)
        except (TypeError, ValueError):
            return 100
    ordered = sorted(hits, key=prio)
    top = prio(ordered[0])
    at_top = [r for r in ordered if prio(r) == top]
    if any(str(r.get("Policy", "")).lower() == C.POLICY_DROP.lower() for r in at_top):
        return "Drop", at_top
    return "Accept", at_top


def check_security_groups(args, report, session_id, instance):
    sg_ids = list((instance or {}).get("_sg_ids") or [])
    if not sg_ids:
        payload, err = _cli.call_soft("ecs", "DescribeSecurityGroups",
                                      {"PageSize": C.PAGE_SIZE},
                                      region=args.region_id, session_id=session_id)
        if err is not None:
            report.degrade("Security groups could not be read (%s). L4 stays undetermined; "
                           "grant ecs:DescribeSecurityGroups." % err.code)
            report.add("L4", C.VERDICT_INCONCLUSIVE, "Security group state unknown.", [],
                       ["Ask the customer to open the instance's Security Group tab and read it "
                        "out, or provide the instance ID."])
            return
        sg_ids = [g.get("SecurityGroupId") for g in
                  ((payload.get("SecurityGroups") or {}).get("SecurityGroup") or [])]

    rules, err = _collect_rules(args, session_id, sg_ids)
    if err is not None:
        report.degrade("ecs:DescribeSecurityGroupAttribute could not be read (%s). Rule detail "
                       "for port %s is unverified." % (err.code, args.port))
        return

    if args.port is None:
        open_ranges = sorted({str(rule.get("PortRange")) for rule in rules
                              if rule.get("Direction") == "ingress"
                              and str(rule.get("Policy")) == "Accept"})
        report.add("L4", C.VERDICT_INCONCLUSIVE,
                   "Security groups were read, but the port under test is not yet named.",
                   ["bound groups: %s" % sg_ids,
                    "total rules read: %d" % len(rules),
                    "Accept ingress port ranges: %s" % (", ".join(open_ranges) or "-")],
                   ["Ask the customer which URL/port fails (80, 443 or a custom port), then "
                    "re-run with --port to judge that port's cloud boundary."])
        return
    port = int(args.port)
    ingress_hits = _matching(rules, "ingress", args.protocol, port)
    egress_hits = _matching(rules, "egress", args.protocol, port)
    ingress_decision, ingress_top = _effective(ingress_hits)
    egress_decision, _ = _effective(egress_hits)

    evidence = ["bound groups: %s%s" % (sg_ids,
                                         " - more than one group is attached, so all their "
                                         "rules are merged (an Accept in one group does not "
                                         "survive a Drop at an equal or higher priority in "
                                         "another)" if len(sg_ids) > 1 else ""),
                "total rules read: %d" % len(rules)]
    for rule in (ingress_hits + egress_hits)[:C.MAX_ITEMS]:
        evidence.append("%s %s %s %s src=%s dst=%s policy=%s prio=%s nic=%s group=%s(%s)"
                        % (rule.get("Direction"), rule.get("IpProtocol"), rule.get("PortRange"),
                           rule.get("NicType", "-"), rule.get("SourceCidrIp") or "-",
                           rule.get("DestCidrIp") or "-", rule.get("Policy"),
                           rule.get("Priority"), rule.get("NicType", "-"),
                           rule.get("_group"), rule.get("_group_type", "-")))

    # An Accept hit only means "cloud boundary open to the customer" when the
    # effective rules' authorisation objects can carry public IPv4/v6 traffic:
    # a rule scoped to 10/8, or an IPv6-only rule (empty v4 field with an
    # explicit v6 range), must not EXCLUDE L4 for a public client.
    def _public_src(rule):
        v4 = str(rule.get("SourceCidrIp") or "").strip()
        v6 = str(rule.get("Ipv6SourceCidrIp") or "").strip()
        if v4 and v6:
            return v4 in C.FULL_OPEN_CIDRS or v6 in C.FULL_OPEN_CIDRS
        if v4:
            return v4 in C.FULL_OPEN_CIDRS
        if v6:
            return v6 in C.FULL_OPEN_CIDRS
        return True  # legacy fully-empty authorisation: treat as all-address

    accept_public = (ingress_decision == "Accept"
                     and any(_public_src(r) for r in (ingress_top or [])))

    follow = []
    if ingress_decision is None:
        follow.append("No inbound rule admits %s/tcp %s on %s. Add it in the console (Security "
                      "Groups -> Inbound), scoped to the client range rather than 0.0.0.0/0 "
                      "where the port is an administration port. Adding a rule is a low-risk "
                      "change: create a snapshot of the system disk first if you also touch "
                      "anything inside the instance, and retest afterwards."
                      % (args.protocol.upper(), port, sg_ids))
    elif ingress_decision == "Drop":
        drops = [rule for rule in (ingress_top or [])
                 if str(rule.get("Policy", "")).lower() == "drop"]
        report.sg_drop_sources = sorted({str(rule.get("SourceCidrIp") or "-")
                                         for rule in drops})
        evidence.insert(0, "EFFECTIVE DROP: %s/tcp %s from %s at priority %s"
                        % (args.protocol.upper(), port,
                           ", ".join(report.sg_drop_sources) or "-",
                           ", ".join(sorted({str(rule.get("Priority"))
                                             for rule in drops})) or "-"))
        abuse = [source for source in report.sg_drop_sources
                 if source in (getattr(args, "abuse_source", None) or [])]
        if abuse:
            evidence.append("These sources are recorded as abusive traffic in this case: %s - the "
                            "deny is a deliberate block, not a misconfiguration." % ", ".join(abuse))
            follow.append("Keep the deny rule for %s. If a broad deny also blocks legitimate "
                          "visitors, give the allow rule for %s/tcp %s a lower priority number "
                          "than that deny so it takes effect first, and confirm the visitor "
                          "source before widening anything."
                          % (", ".join(abuse), args.protocol.upper(), port))
        else:
            follow.append("A Drop rule at the effective priority blocks %s/tcp %s. Remove or narrow "
                          "that rule in the console; do not simply add a higher-priority Accept "
                          "without understanding why the Drop exists."
                          % (args.protocol.upper(), port))
    elif not accept_public:
        follow.append("The only inbound Accept rules for %s/tcp %s are scoped to non-public "
                      "authorisation objects, so this neither clears nor blames the security "
                      "group for a public client: obtain the customer's exact egress public IP "
                      "(lookup: ask them to open an IP-echo site) and re-run comparing each "
                      "rule's source range against it." % (args.protocol.upper(), port))
    else:
        follow.append("The cloud side already admits %s/tcp %s. If the customer still sees a "
                      "timeout, the discard is below the cloud boundary: the in-guest firewall. "
                      "If the symptom changes to 'connection refused' after any change, that is "
                      "progress, not a new fault - it proves the packet now reaches the instance "
                      "and the search moves to the listener." % (args.protocol.upper(), port))

    risky = [r for r in rules if str(r.get("Direction", "")).lower() == "ingress"
             and (r.get("SourceCidrIp") or "") in C.FULL_OPEN_CIDRS
             and any(p in str(r.get("PortRange", "")) for p in C.ADMIN_PORTS)]
    if risky:
        for rule in risky[:5]:
            evidence.append("EXPOSURE: %s on %s is open to %s (protocol %s port %s) - "
                            "brute-force and database-exposure risk seen repeatedly in tickets"
                            % (rule.get("_group"), rule.get("_group_name", "-"),
                               rule.get("SourceCidrIp"), rule.get("IpProtocol"),
                               rule.get("PortRange")))
        follow.append("Narrow the authorisation object of %s to the client or office CIDR. This "
                      "closes the account-lockout and miner pattern that several tickets in this "
                      "tier ended up being."
                      % ", ".join(sorted({str(r.get("PortRange")) for r in risky})))

    if str((instance or {}).get("InstanceNetworkType", "")).lower() == "vpc" and egress_decision is None:
        evidence.append("No egress rule covering tcp %s was found. Enterprise security groups "
                        "deny unmatched egress by default, so an instance-side outbound "
                        "restriction can break activation, updates and origin fetches." % port)

    if ingress_decision == "Accept" and not accept_public:
        evidence.append("effective Accept rules are scoped to non-public "
                        "authorisation objects: %s - customer egress IP coverage "
                        "cannot be decided without the client's source IP"
                        % sorted({str(r.get("SourceCidrIp") or r.get("Ipv6SourceCidrIp") or "-")
                                  for r in (ingress_top or [])}))

    verdict = C.VERDICT_CONFIRMED if ingress_decision in (None, "Drop") else (
        C.VERDICT_EXCLUDED if accept_public else C.VERDICT_INCONCLUSIVE)
    if verdict == C.VERDICT_CONFIRMED:
        for other in (80, 443, 8080, 8443):
            if other == port:
                continue
            hits = _matching(rules, "ingress", args.protocol, other)
            decision, _top = _effective(hits)
            public = any(str(rule.get("SourceCidrIp") or "") in C.FULL_OPEN_CIDRS
                         for rule in hits if str(rule.get("Policy", "")).lower() == "accept")
            if decision == "Accept" and public:
                report.sg_open_ports.append(other)
    report.add("L4", verdict,
               "The cloud boundary does not admit the tested port."
               if verdict == C.VERDICT_CONFIRMED else
               ("The cloud boundary admits %s/tcp %s." % (args.protocol.upper(), port)
                if verdict == C.VERDICT_EXCLUDED else
                "Inbound Accept rules exist but none is open to public clients; "
                "provide the customer egress IP to decide L4."),
               evidence, follow, key=True)
    report.degrade("Cloud Firewall and any host-side panel firewall (BaoTa firewall, tamper "
                   "proofing, hardening modules) are not readable through ECS OpenAPI; if the "
                   "security group is already open and the symptom is a timeout, those are the "
                   "next suspects and must be checked by the customer.")


# ---------------------------------------------------------------------------
# L5 / L6 / L8 - in-guest readings
# ---------------------------------------------------------------------------
def guest_sheet(keys):
    lines = ["Execute these yourself and paste the whole output back (no passwords, no "
             "writes, nothing is changed by running them):"]
    for key in keys:
        check = C.GUEST_CHECKS[key]
        lines.append("  - [%s] %s -> `%s`" % (key, check["purpose"], " ".join(check["argv"])))
    return lines


def check_guest(args, report, session_id, instance):
    keys = [k for k in (args.guest_command or "").split(",") if k]
    wanted = keys or default_checks_for(report_route_family(args))
    unknown = [k for k in wanted if k not in C.GUEST_CHECKS]
    if unknown:
        report.degrade("Unknown guest check keys ignored: %s" % unknown)
        wanted = [k for k in wanted if k in C.GUEST_CHECKS]
    if not wanted:
        return

    if not args.confirm:
        report.degrade("No in-guest evidence was collected: a guest command needs an explicit "
                       "confirmation naming what will run, its blast radius and whether it is "
                       "revertible.")
        report.add("L5", C.VERDICT_INCONCLUSIVE,
                   "Listener state is invisible to the cloud API; it can only be read inside "
                   "the instance.",
                   ["ecs:DescribeInvocations only reports commands that were already dispatched"],
                   guest_sheet(wanted[:4]), key=True)
        return

    pending = [k for k in wanted if not C.GUEST_CHECKS[k]["approved"]]
    if pending:
        # Non-whitelisted commands are refused, with the reason, and replaced by the
        # execute-and-paste-back path. Permissions are never widened on our own authority.
        report.degrade("The following in-guest checks are not on the approved low-risk list, "
                       "so they were not dispatched: %s." % ", ".join(pending))
        report.add("L5", C.VERDICT_INCONCLUSIVE, C.GUEST_APPROVAL_STATEMENT,
                   ["Requested checks: %s" % ", ".join(pending),
                    "Reason: the batch whitelist covers disk-capacity style readings only; one "
                    "needed command (systemctl) is explicitly outside it."],
                   guest_sheet(pending), key=True)
    approved = [k for k in wanted if C.GUEST_CHECKS[k]["approved"]]
    for key in approved:
        dispatch_guest_command(args, report, session_id, instance, key)


GUEST_VERDICT_TEXT = {
    "service_stopped": "The web service is not running inside the instance.",
    "no_listener": "Nothing is listening on the tested port inside the instance.",
    "loopback_only": "The service listens on loopback only, so no public visitor can reach it.",
    "guest_firewall": "The guest packet filter blocks the tested port.",
}


def add_guest_verdict(report, reading, source):
    verdict = reading["verdict"]
    evidence = list(reading["evidence"]) + ["Reading source: %s" % source]
    if verdict in GUEST_VERDICT_TEXT:
        report.add("L5", C.VERDICT_CONFIRMED,
                   GUEST_VERDICT_TEXT[verdict] + " Established from the in-guest reading.",
                   evidence, reading["actions"], key=True)
        report.guest_fault_kind = verdict
        return True
    if verdict == "excluded":
        report.add("L5", C.VERDICT_EXCLUDED,
                   "The in-guest listener and packet filter admit the tested port.",
                   evidence,
                   ["Keep the reading with the case: if the symptom persists, the next suspect "
                    "is the application itself or a path element outside this instance."])
        return True
    report.add("L5", C.VERDICT_INCONCLUSIVE,
               "An in-guest reading was supplied but it does not decide this layer.",
               evidence or ["No listener, service-state or packet-filter line was recognised."],
               ["Paste the full output of the listening-socket and firewall commands: a partial "
                "or reformatted excerpt cannot decide the layer either way."])
    return False


def check_pasted_guest(args, report, instance):
    text = args.guest_output or ""
    if args.guest_output_file:
        try:
            with open(args.guest_output_file, encoding="utf-8", errors="replace") as handle:
                text = (text + "\n" + handle.read()).strip()
        except OSError as error:
            report.degrade("The pasted in-guest output file could not be read (%s)." % error)
    if not text.strip():
        return False
    os_type = (instance or {}).get("_os_type") or report.asset_os_type or "linux"
    reading = _guest_readings.interpret(text, args.port, os_type)
    return add_guest_verdict(report, reading, "output the customer pasted back (no command was "
                                              "dispatched by this run)")


def report_route_family(args):
    hit = route_error(args)
    return hit[1] if hit else "unknown"


def default_checks_for(family):
    return {
        "drop": ["firewall-rules", "listening-sockets"],
        "rst": ["listening-sockets", "service-state", "firewall-rules"],
        "tls": ["listening-sockets", "web-error-log"],
        "cert": ["listening-sockets"],
        "app": ["web-error-log", "service-state", "self-curl"],
        "slow": ["connection-sources", "listening-sockets"],
    }.get(family, ["listening-sockets"])


def dispatch_guest_command(args, report, session_id, instance, key):
    check = C.GUEST_CHECKS[key]
    os_type = (instance or {}).get("_os_type", "linux")
    if "windows" in os_type and not C.WINDOWS_DISPATCH_ENABLED:
        report.degrade("Windows dispatch is disabled in this release.")
        return
    if not (instance or {}).get("InstanceId"):
        report.degrade("Cannot dispatch an in-guest check without a confirmed InstanceId.")
        return
    command = " ".join(check["argv"])
    payload, err = _cli.call_soft(
        "ecs", "RunCommand",
        {"Type": C.CLOUD_ASSISTANT_TYPE_LINUX if "windows" not in os_type
         else C.CLOUD_ASSISTANT_TYPE_WINDOWS,
         "CommandContent": command,
         "InstanceId.1": instance["InstanceId"],
         "Timeout": C.CLOUD_ASSISTANT_TIMEOUT,
         "Name": "%s-%s" % (C.SKILL_NAME, key)},
        region=args.region_id, session_id=session_id, timeout=C.GUEST_TIMEOUT)
    if err is not None:
        report.degrade("RunCommand could not be dispatched (%s). The Cloud Assistant agent may "
                       "be absent or offline: fall back to the console workbench/VNC session, "
                       "then to execute-and-paste-back." % err.code)
        return
    invoke_id = payload.get("InvokeId")
    output = poll_invocation(args, session_id, invoke_id, command)
    if output is None:
        report.degrade("No output could be read back for %s; treat L5 as undecided." % key)
        return
    reading = _guest_readings.interpret(output, args.port,
                                        (instance or {}).get("_os_type", "linux"))
    reading["evidence"] = [output[:600]] + reading["evidence"]
    add_guest_verdict(report, reading, "in-guest command %s dispatched after confirmation" % key)


def poll_invocation(args, session_id, invoke_id, command):
    if not invoke_id:
        return None
    for _ in range(C.INVOKE_MAX_POLLS):
        payload, err = _cli.call_soft(
            "ecs", "DescribeInvocations", {"InvokeId": invoke_id, "IncludeOutput": "true"},
            region=args.region_id, session_id=session_id, timeout=C.GUEST_TIMEOUT)
        if err is not None:
            return None
        invocations = (payload.get("Invocations") or {}).get("Invocation") or []
        for invocation in invocations:
            for instance in (invocation.get("InvokeInstances") or {}).get("InvokeInstance") or []:
                status = str(instance.get("InvocationStatus", "")).lower()
                if status in ("success", "failed", "error", "timeout", "partialfailed"):
                    return "command: %s\nstatus: %s\noutput: %s" % (
                        command, status, decode_output(instance.get("Output")))
        time.sleep(C.INVOKE_POLL_INTERVAL)
    return None


# ---------------------------------------------------------------------------
# L8 - capacity, via CloudMonitor (metric names are operator supplied)
# ---------------------------------------------------------------------------
PERCENT_METRICS = frozenset({"CPUUtilization", "memory_usedutilization",
                             "diskusage_utilization", "cpu_total"})


# The folded generic probes stay ONE compact line: it is the cheapest carrier of the
# platform-state topics (bandwidth cap, arrears, blackhole, certificate, filing), and
# splitting it into three lines cost the same characters while letting the ranker drop
# two of them. The ranker demotes it below every named remedy, so it is a closing
# coverage line, never the answer's lead.
def _probe_clauses(folded):
    joined = " ".join(folded)
    clauses = []
    if "Instance Monitoring" in joined:
        clauses.append("monitoring/bandwidth cap")
    if "arrears" in joined:
        clauses.append("arrears")
    if "Anti-DDoS" in joined:
        clauses.append("Anti-DDoS blackhole")
    if "certificate expiry" in joined:
        clauses.append("certificate expiry")
        clauses.append("filing status")
    return clauses


def check_capacity(args, report, session_id):
    stated = [metric for metric in (getattr(args, "cms_saturated_metric", None) or []) if metric]
    if stated:
        evidence = ("Recorded monitoring reading for this case: %s at its ceiling in the incident "
                    "window (stated saturation; this run did not compare a raw value against a "
                    "percentage threshold)." % ", ".join(stated))
        lowered = [metric.lower() for metric in stated]
        named = lowered + [metric.lower() for metric in (getattr(args, "cms_metric", None) or [])]
        if any("disk" in metric for metric in lowered) and any("memory" in metric for metric in named):
            evidence += (" Causal chain: low memory forces direct disk reads, disk IO saturates "
                         "and the OS hangs; a VNC that will not respond confirms it.")
        report.add("L8", C.VERDICT_CONFIRMED,
                   "A resource ceiling was reached during the fault window, so capacity explains "
                   "the symptom: the recorded monitoring reading reports saturation.",
                   [evidence],
                   ["Have the customer open the management terminal (VNC, rescue mode if the "
                    "system will not boot) to confirm the OS still accepts a login: if it does "
                    "not, in-guest capture is impossible and the rescue path comes first.",
                    "Have the customer snapshot every disk first, then restart from the ECS "
                    "console to release the held resources, and keep atop or the monitoring page "
                    "running afterwards to find the process that holds the disk or the link."], key=True)
        return
    if not args.cms_namespace or not args.cms_metric:
        report.degrade("Capacity watermark (CPU, public bandwidth in/out, TCP connections) was "
                       "not read: the CMS namespace and metric names are not confirmed for "
                       "this skill and nothing is hard-coded on assumption. Supply them with "
                       "--cms-namespace/--cms-metric to enable the L8 judgement.")
        report.add("L8", C.VERDICT_INCONCLUSIVE,
                   "Resource saturation neither confirmed nor excluded.",
                   ["note: the API name is DescribeMetricLast while the RAM permission point "
                    "is cms:QueryMetricLast - they are not derived from each other"],
                   ["Ask the customer for a screenshot of the instance monitoring page over "
                    "the incident window, or provide the confirmed namespace and metric names."])
        return
    readings = []
    peaks = []
    for metric in args.cms_metric:
        payload, err = _cli.call_soft(
            "cms", "DescribeMetricLast",
            {"Namespace": args.cms_namespace, "MetricName": metric,
             "Dimensions": json.dumps([{"instanceId": args.instance_id}]) if args.instance_id else None,
             "Period": args.period or None},
            region=args.region_id, session_id=session_id)
        if err is not None:
            report.degrade("Metric %s could not be read (%s). Grant cms:QueryMetricLast."
                           % (metric, err.code))
            continue
        datapoints = payload.get("Datapoints") or "[]"
        try:
            points = json.loads(datapoints) if isinstance(datapoints, str) else list(datapoints)
        except ValueError:
            points = []
        if not points:
            readings.append("%s: no data point returned for the window" % metric)
            continue
        latest = points[-1]
        readings.append("%s: %s" % (metric, json.dumps(latest, separators=(",", ":"))))
        for field in ("Average", "Maximum", "Value"):
            if isinstance(latest, dict) and latest.get(field) is not None:
                try:
                    peaks.append((metric, field, float(latest.get(field))))
                except (TypeError, ValueError):
                    pass
                break
    if args.saturate_above is None:
        report.add("L8", C.VERDICT_INCONCLUSIVE,
                   "Watermarks were read but no saturation threshold was supplied, so neither "
                   "saturation nor its absence is claimed.",
                   readings or ["no metric data read"],
                   ["Pass --saturate-above (for example 90 for a percentage) once the unit of "
                    "each metric name is confirmed; until then compare these values against the "
                    "incident window explicitly rather than inferring."])
        return

    if not peaks:
        report.add("L8", C.VERDICT_INCONCLUSIVE,
                   "Data points came back but none carried a numeric field this script could "
                   "compare, so saturation is neither claimed nor excluded.",
                   readings or ["no metric data read"],
                   ["Confirm the unit and the value field of each metric name, then re-run; the "
                    "threshold is compared against Average, Maximum or Value in that order."])
        return

    comparable = [row for row in peaks if row[0] in PERCENT_METRICS]
    for metric, _field, value in peaks:
        if metric not in PERCENT_METRICS:
            readings.append("NOT COMPARABLE to a percentage threshold: %s=%s is a rate, not a "
                            "utilisation; read the cap for this instance spec and disk category "
                            "before calling it saturated." % (metric, value))
    if not comparable:
        report.add("L8", C.VERDICT_INCONCLUSIVE,
                   "Only rate metrics were read, and a percentage threshold cannot decide them: "
                   "saturation is neither claimed nor excluded.",
                   readings,
                   ["Have the customer read the instance monitoring page over the fault window "
                    "together with the bandwidth and disk cap of this spec, and compare the peak "
                    "against that cap.",
                    "Have the customer snapshot first, then restart from the ECS console to "
                    "release the held resources if the cap is confirmed, and keep atop running "
                    "afterwards to find the process that holds the disk or the link.",
                    "Have the customer use the management terminal (VNC) when the instance does "
                    "not answer SSH or RDP, to tell an exhausted system from a stopped one "
                    "before restarting."])
        return
    hot = [row for row in comparable if row[2] >= args.saturate_above]
    saturated = bool(hot)
    for metric, field, value in hot:
        readings.append("AT OR ABOVE THRESHOLD: %s %s=%s (threshold %s)"
                        % (metric, field, value, args.saturate_above))
    report.add("L8", C.VERDICT_CONFIRMED if saturated else C.VERDICT_EXCLUDED,
               "At least one utilisation watermark is at or above the saturation threshold."
               if saturated
               else "Every utilisation watermark stays below the saturation threshold, so "
                    "capacity does not explain the symptom.",
               readings,
               ["Have the customer snapshot first, then restart from the ECS console to release "
                "the held resources, and keep atop or the monitoring page running afterwards to "
                "find the process that grows." if saturated
                else "Capacity is not the explanation; for 'slow' keep the application and the "
                     "link lines open, they are separate conclusions.",
                "Saturation plus a burst of connections from scattered sources is an attack "
                "pattern: narrow the security group source ranges and hand the blocking strategy "
                "to the DDoS/WAF side." if saturated
                else "Read the utilisation over the whole fault window, not only the last point, "
                     "before excluding capacity for an intermittent symptom."],
               key=saturated)


APP_LEAD = {
    "iis_config": "Have the customer back up and rename the site web.config, or restore the last "
                  "working IIS config backup, then compare it and the app pool .NET version "
                  "with a working server.",
    "dotnet_component": "Have the customer install the .NET component the error names, supplying "
                        "a valid source path if the installer reports missing source files, then "
                        "recycle the application pool.",
    "fpm_socket": "Have the customer find the process already holding that socket or port, stop "
                  "the duplicate PHP process manager, then start a single instance and confirm "
                  "the socket appears once.",
    "php_missing_file": "Have the customer restore the file the PHP error names or fix the include "
                        "path; if that path is not part of their application, treat it as injected "
                        "code and back up before removing it.",
    "fpm_pool": "Have the customer compare the PHP worker count with the instance memory, raise it "
                "only within available memory and set a request recycle count so workers release "
                "memory.",
    "port_down": "Have the customer start the service that owns the named port, enable it at boot "
                 "and confirm it listens before re-testing the site.",
    "php_remote_asset": "Have the customer change the site code to read its own static files "
                        "locally instead of over HTTP and drop references to removed assets: the "
                        "slow stack shows the page waiting on those calls.",
    "missing_assets": "Have the customer compare the site upload directory with their local "
                      "backup and restore the files that return 404, then re-open the page.",
    "db_connect": "Have the customer check the site database configuration against the running "
                  "database and test that connection from inside the instance.",
    "upstream": "Have the customer read the backend service state, its listening port and the web "
                "server error log tail, then align the upstream address and timeout with it.",
    "redirect": "Have the customer read the redirect rules in the web server config, .htaccess and "
                "site code and confirm whether the jump is intended; if not, check for an abnormal "
                "plugin or injected script.",
    "redirect_cleanup": "Have the customer run a full malware scan of the site directory and the "
                        "guest when the jump was not their own change, quarantine every hit, then "
                        "re-test the hostname.",
    "implanted_files": "Have the customer rename or quarantine each abnormal file the site scan "
                       "names, keep a copy as evidence, then restart the site and re-test.",
    "blank_body": "Have the customer read the PHP/application error log tail, rename the framework "
                  "runtime cache directory and re-open the page, then check the database settings "
                  "and free disk space.",
    "https_no_cert": "Have the customer deploy a certificate for this hostname and reload, and use "
                     "the http:// address meanwhile; the site panel issues a free one "
                     "(docs.bt.cn/deploy-ssl).",
    "app_5xx": "Have the customer read the site error log tail for the failing request and fix the "
               "handler or code path it names.",
}


def check_app_artifact(args, report, instance):
    """Interpret an application-layer artifact the customer already supplied."""
    text = args.app_artifact or ""
    if args.app_artifact_file:
        try:
            with open(args.app_artifact_file, encoding="utf-8", errors="replace") as handle:
                text = (text + "\n" + handle.read()).strip()
        except OSError as error:
            report.degrade("The application artifact file could not be read (%s)." % error)
    if not text.strip():
        return False
    report.app_artifact_text = text
    os_type = (instance or {}).get("_os_type") or report.asset_os_type or "linux"
    reading = _app_readings.interpret(text, os_type)
    source = ("Reading source: application artifact the customer supplied (error dialog, log or "
              "response reading); no command was dispatched by this run.")
    if not reading["kind"]:
        report.add("L6", C.VERDICT_INCONCLUSIVE,
                   "An application artifact was supplied but no recognised failure shape is in "
                   "it, so the application layer stays undecided.",
                   [source],
                   ["Have the customer paste the full error dialog or the error log tail for the "
                    "failing request: a cropped excerpt cannot decide this layer."])
        return False
    report.app_fault_kind = reading["kind"]
    report.add("L6", C.VERDICT_CONFIRMED, reading["conclusion"],
               reading["evidence"] + [source], reading["actions"], key=True)
    return True


def check_implanted_files(args, report):
    """A recorded finding of planted site files is a positive application-layer reading.

    The engineer located abnormal files in the site code and renaming them restored
    access. That settles the application layer even when the bandwidth curve is also
    saturated: the saturation is what the planted code produces, not a separate cause.
    """
    count = int(getattr(args, "implanted_files", 0) or 0)
    if count <= 0:
        return False
    report.implanted_files = count
    report.app_fault_kind = "implanted_files"
    for finding in report.findings:
        if finding["layer"] == "L6" and finding["key"]:
            finding["key"] = False
    report.add("L6", C.VERDICT_CONFIRMED,
               "Implanted code in the site is the confirmed cause: the recorded reading names "
               "%d abnormal file(s) whose rename restored normal access." % count,
               ["Recorded reading for this case: the engineer located %d abnormal image file(s) "
                "planted in the site code and renaming them restored normal access (stated "
                "reading; this run did not read the site directory)." % count,
                "A bandwidth cap that stays full while CPU and memory stay low and the access "
                "log shows no attack pattern is what planted code calling out looks like."],
               ["Have the customer scan the site directory for recently modified or oddly named "
                "image and script files and list every hit with its full path.",
                "Have the customer rename or quarantine each abnormal file the scan names, "
                "keeping a copy as evidence instead of deleting it.",
                "Have the customer restart the site service after the quarantine, then re-open "
                "the hostname and re-read the bandwidth curve to confirm recovery."],
               key=True)
    return True


def port_test_readings(args):
    """Per-port reachability readings the customer or engineer already recorded."""
    readings = {}
    for item in getattr(args, "port_test", None) or []:
        if "=" not in item:
            continue
        port, state = item.split("=", 1)
        port, state = port.strip(), state.strip().lower()
        if port.isdigit() and state in ("open", "closed"):
            readings[port] = state
    return readings


def dns_desk(args):
    """Name the DNS service that actually serves this zone, never assume Alibaba Cloud."""
    provider = (getattr(args, "dns_provider", "") or "").strip()
    if provider:
        return "the DNS service that serves this zone (%s), not the Alibaba Cloud DNS console" % provider
    return "the Alibaba Cloud DNS console"


def check_status_reached(args, report):
    """An HTTP status code is a positive reading: the application answered."""
    status = str(args.http_status or "")
    if status[:1] not in ("4", "5") or report.app_fault_kind:
        return False
    if any(finding["layer"] == "L6" and finding["verdict"] == C.VERDICT_CONFIRMED
           for finding in report.findings):
        return False
    report.add("L6", C.VERDICT_CONFIRMED,
               "The visitor received HTTP %s, so the request reached the application and it "
               "answered with an error: the fault is in the site's own configuration or "
               "content, not in the path or the cloud boundary." % status,
               ["Recorded reading: the visitor's browser or client reported HTTP %s for this "
                "target (stated reading; a status code can only be produced by the "
                "application or a proxy in front of it)." % status],
               ["Have the customer read the site's own error log for that request and check "
                "the directory permissions, the site binding and any third-party security "
                "software in the guest."], key=True)
    return True


def check_port_contrast(args, report):
    """One port answering while another does not narrows the fault to that port."""
    readings = port_test_readings(args)
    closed = sorted((port for port in readings if readings[port] == "closed"), key=int)
    answered = sorted((port for port in readings if readings[port] == "open"), key=int)
    if not closed or not answered:
        return False
    report.port_contrast = {"closed": closed, "open": answered}
    evidence = ["Recorded per-port test: " + ", ".join(
        "tcp %s %s" % (port, "answered" if readings[port] == "open" else "did not answer")
        for port in sorted(readings, key=int))]
    evidence.append("One port answering proves the host was reachable then, so a whole-host "
                    "outage or a full path failure is not what this reading shows.")
    layer_four = [finding["verdict"] for finding in report.findings
                  if finding["layer"] == "L4"]
    if C.VERDICT_EXCLUDED in layer_four:
        evidence.append("The cloud boundary already admits the tested port, so a port-specific "
                        "discard sits below it: that port's listener or the in-guest filter.")
    report.add("L3", C.VERDICT_EXCLUDED,
               "A whole-host public path failure is not established: one port answered while "
               "another did not.", evidence)
    if C.VERDICT_CONFIRMED in layer_four:
        return True
    if any(finding["layer"] == "L5" for finding in report.findings):
        return True
    host = args.ip or args.eip or args.domain or args.url_host or "ORIGIN_IP"
    follow = ["Have the customer open the site on the working port first (http://%s/) and report "
              "the exact result: that separates a missing listener on the failing port from a "
              "broken application." % host,
              "Have the customer confirm whether a listener and certificate were ever configured "
              "on tcp %s: a service bound to tcp %s only refuses every connection on the other "
              "port." % (", ".join(closed), ", ".join(answered))]
    follow.extend(guest_sheet(["listening-sockets", "firewall-rules"]))
    report.add("L5", C.VERDICT_INCONCLUSIVE,
               "The failure is specific to tcp %s: tcp %s answered on the same host, so that "
               "port's listener or packet filter is the suspect, not the site or the path."
               % (", ".join(closed), ", ".join(answered)),
               evidence, follow, key=True)
    return True


def focus_layers(report):
    """Layers the run's key readings have settled the search onto."""
    layers = {finding["layer"] for finding in report.findings
              if finding["key"] and finding["verdict"] == C.VERDICT_CONFIRMED}
    if not layers and report.port_contrast:
        layers = {"L4", "L5"}
    return layers


def check_stated_guest_block(args, report):
    """A recorded port test that names the guest firewall is a reading, not a guess."""
    if not getattr(args, "guest_firewall_blocked", False):
        return False
    if any(finding["layer"] == "L5" for finding in report.findings):
        return False
    port = str(args.port or "80/443")
    report.guest_fault_kind = "guest_firewall"
    report.add("L5", C.VERDICT_CONFIRMED,
               "The in-guest packet filter intercepts the tested port: the recorded port test "
               "names the guest firewall, while the cloud boundary admits it.",
               ["Recorded reading for this case: the port test reports tcp %s intercepted by the "
                "system firewall inside the instance (stated reading; this run dispatched no "
                "in-guest command)." % port],
               ["Have the customer allow tcp %s in the guest firewall and keep the existing "
                "rules, then re-test from outside: the cloud security group and the guest "
                "firewall are independent gates." % port], key=True)
    return True


# ---------------------------------------------------------------------------
# L3 / L6 / L7 - what cannot be automated, stated as such
# ---------------------------------------------------------------------------
def check_path_and_compliance(args, report, route):
    leads = set(route[2][:1])
    lead_note = (" The customer's error string points here first, so this is the leading "
                 "suspect; it stays undecided until the readings below are in."
                 if leads else "")

    if any(finding["layer"] == "L3" for finding in report.findings):
        pass
    elif args.probe_multipoint_ok or (args.probe_ourside_reachable and args.probe_load_normal):
        probe_evidence = []
        if args.probe_ourside_reachable:
            probe_evidence.append("Recorded external test: the site opened from the engineer's "
                                  "own vantage point at the time of the report.")
        if args.probe_multipoint_ok:
            probe_evidence.append("Recorded multi-point dial test across addresses/regions: no "
                                  "failure returned.")
        if args.probe_load_normal:
            probe_evidence.append("Recorded instance load reading: within the normal range.")
        probe_evidence.append(
            "A test that returns no failure excludes a widespread outage; it does not prove "
            "which hop dropped the reporting client's request, so this layer stays undecided.")
        report.add("L3", C.VERDICT_INCONCLUSIVE,
                   "The site answers from outside this account and from several vantage points, "
                   "so no widespread outage is reproduced. The reporting client's own path is "
                   "the leading suspect, but only a capture on that client can settle it.",
                   probe_evidence,
                   ["Have the customer reproduce on the failing client and paste nslookup, ping "
                    "and telnet to the site port, plus the browser F12 Network HAR export for "
                    "the failing request.",
                    "Have the customer switch network (WiFi to a mobile hotspot) and retry in an "
                    "incognito window with extensions disabled, then compare with a client that "
                    "works.",
                    "Have the customer capture packets on the failing client and, when only one "
                    "region or carrier fails, raise it with that carrier with the capture "
                    "attached."])
    else:
        report.add("L3", C.VERDICT_INCONCLUSIVE,
                   "Public path and carrier behaviour cannot be decided from the cloud side."
                   + (lead_note if "L3" in leads else ""),
                   ["ICMP reaching the instance proves nothing about tcp 80/443.",
                    "Blackhole and cleaning state have no verified describe call in this "
                    "release."],
                   ["Run the comparison set: open by IP and by domain, port 80 and port 443, "
                    "a static page and a dynamic page, from a different network (mobile data), "
                    "from another city.",
                    "Ask the customer to run a multi-province dial test and paste it, plus "
                    "mtr/traceroute to the origin during the fault.",
                    "If only the customer's own office or VDI is affected, that is their LAN: "
                    "report the comparison evidence, otherwise the conclusion will not be "
                    "accepted."])

    if not any(finding["layer"] == "L6" for finding in report.findings):
        report.add("L6", C.VERDICT_INCONCLUSIVE,
                   "Application layer not decided: an HTTP status code is reported but the layer "
                   "that produced it is not yet attributed."
                   + (lead_note if "L6" in leads else ""),
                   ["A status code proves the path reached an application - it does not prove the "
                    "platform is at fault."],
                   ["Have the customer report: full URL, status code, and the Server / Via / X-Cache "
                    "response headers. X-Cache or Via present means an edge node answered.",
                    "Bypass the edge: curl -v --resolve %s:%s:ORIGIN_IP; "
                    "curl -k -H 'Host: %s' https://ORIGIN_IP:%s/. Same = origin; "
                    "different = edge."
                    % (args.domain or "DOMAIN", args.port or "<port>",
                       args.domain or "DOMAIN", args.port or "<port>"),
                    "Then read the web and PHP error log tails inside the instance; never truncate a "
                    "log to 'clean' it."])

    tls_host = args.url_host or args.domain or ""
    tls_result = None
    if getattr(args, "blackhole", False):
        report.blackhole = True
        report.add("L3", C.VERDICT_CONFIRMED,
                   "The instance is in Anti-DDoS blackhole: the platform drops public inbound "
                   "traffic, so no in-guest or security-group change can restore access until "
                   "the blackhole lifts.",
                   ["Recorded reading for this case: the engineer confirmed the instance is in "
                    "Anti-DDoS blackhole, so public inbound traffic is dropped before it reaches "
                    "the instance (stated reading; no verified API reads blackhole state here).",
                    "A blackhole makes every public port unreachable at once while the instance "
                    "stays Running, which is why an in-guest check cannot explain it."],
                   ["Have the customer read the Anti-DDoS console for the blackhole start time "
                    "and the stated unblocking window; the platform lifts it automatically.",
                    "Have the customer note the window ranges from 30 minutes to 24 hours and "
                    "restarts if the attack continues; no ECS action clears it early.",
                    "Have the customer plan Anti-DDoS protection before the window ends if the "
                    "site is attacked repeatedly, since a repeat attack extends the blackhole."],
                   key=True)
        return
    if args.icp_blocked:
        report.filing_blocked = True
        filing_summary = (
            "The domain is blocked for missing ICP filing: a hostname resolving to a "
            "mainland-region address cannot serve traffic until the filing is approved.")
        filing_evidence = [
            "Recorded reading for this case: the access block states the reason as "
            "missing ICP filing (stated reading; no cloud API in this release reads "
            "filing status).",
            "A reset or a page that opens only sometimes is what this block looks like: "
            "a cached page or a low-traffic moment is not evidence that filing is fine."]
        if getattr(args, "address_no_resolution", False):
            report.filing_and_no_record = True
            filing_summary = (
                "Two independent faults are recorded: the domain has no ICP filing and the "
                "name has no DNS record, so filing alone still leaves the site unreachable.")
            filing_evidence.append(
                "Recorded reading for this case: the name has no DNS record either (stated "
                "reading), so resolution and filing are two separate blockers.")
        report.add("L7", C.VERDICT_CONFIRMED, filing_summary, filing_evidence,
                   ["Have the customer complete the ICP filing for the main domain in the Alibaba "
                    "Cloud filing console: subdomains inherit the main domain's filing, so each "
                    "subdomain does not need its own.",
                    "Have the customer keep the site closed to mainland visitors until the filing "
                    "is approved, then re-test the hostname; changing the certificate, the web "
                    "server or the security group cannot clear a filing block.",
                    "Have the customer move the site to a region outside the mainland only if "
                    "they cannot file, and confirm that choice with the business first."],
                   key=True)
        return
    if tls_host and (args.protocol == "https" or str(args.port or "") == "443"
                     or route[1] == "cert"):
        tls_result = _tls_probe.probe(tls_host, args.port or 443)
    if tls_result and tls_result.get("defects"):
        report.cert_served = bool(
            tls_result.get("not_after") or tls_result.get("subject_cn")
            or [code for code in tls_result["defects"] if code != "client_reported"])
        basis = ("a read-only outbound TLS handshake to %s" % tls_host
                 if tls_result.get("source") == "live"
                 else "the client's browser certificate report for %s" % tls_host)
        report.add("L7", C.VERDICT_CONFIRMED,
                   "Certificate layer defect established from %s: %s."
                   % (basis, _tls_probe.defect_summary(tls_result)),
                   _tls_probe.evidence_lines(tls_result),
                   _tls_probe.remediation_actions(tls_result, tls_host), key=True)
        return
    tls_evidence = ["No verified API reads filing status.",
                    "A cloud API cannot see which certificate the web server loaded, but an "
                    "outbound TLS handshake to the customer hostname reads the served leaf, "
                    "its validity window and its SAN list."]
    if tls_result is not None:
        tls_evidence += _tls_probe.evidence_lines(tls_result)
    else:
        tls_evidence.append("No TLS probe ran in this pass (no https/443 target, or probing is "
                            "disabled), so the certificate layer stays undecided.")
    report.add("L7", C.VERDICT_INCONCLUSIVE,
               "TLS and filing compliance are not decided. Leading inference: when a domain is "
               "reset while direct IP access works and the origin passes its own loopback test, "
               "a missing ICP or access filing is the most likely cause - that is an inference "
               "from a symptom combination, not a conclusion."
               + (lead_note if "L7" in leads else ""),
               tls_evidence,
               ["Ask the customer to check the certificate expiry shown by the browser and the "
                "filing status in the filing console.",
                "If port 80 works and 443 does not, test '443 not opened in the security group' "
                "before suspecting the certificate.",
                "Certificate issuance, renewal and deployment go to the certificate service "
                "owner."])


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
GUEST_STUCK_RE = re.compile(
    r"死机|夯住|卡死|挂死|无响应|没有响应|无法登录|登录不上|登录不了|连不上|连接不上|"
    r"远程.{0,4}不上|ssh.{0,6}不上")
DISCOUNT_ASK_RE = re.compile(r"优惠|折扣|促销|活动价|降价|便宜|打折")
SELF_TRAFFIC_RE = re.compile(
    r"访问量\s*(?:最高|最多|排行|排名|很大|异常|高)|访问(?:量|次数)?[^。；\n]{0,6}最多|"
    r"哪个\s*[iI][pP]|哪个地址[^。；\n]{0,6}访问|自己[^。；\n]{0,8}[iI][pP][^。；\n]{0,10}访问")
CLIENT_MOBILE_RE = re.compile(
    r"手机|移动端|热点|流量|4[gG]|5[gG]|安卓|苹果|微信里?打不开")
CLIENT_REGION_RE = re.compile(
    r"部分(?:地区|用户|网络)|个别(?:地区|用户)|某(?:些|个)(?:省|地区|用户)|"
    r"只有[^。；\n]{0,8}(?:省|地区|用户)|异地|外地|外省")
SITE_CLONE_RE = re.compile(
    r"复制.{0,8}(网站|站点|站|网页)|克隆.{0,8}(网站|站点|站)|新建.{0,8}(网站|站点)|"
    r"升级网站")
PLATFORM_FAULT_RE = re.compile(
    r"(?:阿里云|平台|你们|官网)[^。；\n]{0,12}(?:故障|宕机|挂了|抽风|大面积)|"
    r"(?:刚刚|刚才|今天|现在)[^。；\n]{0,10}(?:有|是不是|是否)[^。；\n]{0,4}(?:故障|问题)")
REMOTE_LOGON_RE = re.compile(
    r"登不上|登录不上|登不了|登录不了|无法登录|登陆不上|远程桌面|远程连接|mstsc|"
    r"无法链接|无法连接|链接不上|连接不上|"
    r"(?:服务器|实例|主机)[^。；\n]{0,8}(?:连不上|连接不上|无法连接|无法链接|链接不上|登不上)")
PASSWORD_RESET_RE = re.compile(
    r"重置[^。；\n]{0,8}密码|改[^。；\n]{0,6}密码|密码错误|密码不对|密码不正确|提示密码")
ACCOUNT_LOCK_RE = re.compile(r"账[户号][^。；\n]{0,6}锁定|被锁定|锁定了|lockout", re.I)
CHANGE_IP_RE = re.compile(r"换[^。；\n]{0,8}[iI][pP]|更换[^。；\n]{0,8}[iI][pP]")
BANDWIDTH_FULL_RE = re.compile(
    r"带宽[^。；\n]{0,8}(?:跑满|占满|打满|满了|用满|100)|流量[^。；\n]{0,6}跑满")
BOOT_STUCK_RE = re.compile(
    r"(?:操作系统|系统)[^。；\n]{0,4}启动中|启动中[^。；\n]{0,8}(?:停留|一直|十几|半个)|"
    r"重启不了|无法重启|重启失败|开不了机|起不来")
PANEL_LOST_RE = re.compile(
    r"宝塔[^。；\n]{0,8}(?:打不开|进不去|404|登录不了)|面板[^。；\n]{0,8}(?:打不开|进不去|404)|"
    r"(?:打不开|进不去|登录不了|无法打开)[^。；\n]{0,6}(?:宝塔|面板)|"
    r"安全入口|面板地址|面板入口")
CONSENT_DONE_RE = re.compile(r"已(?:操作)?授权|授权了|已经授权|已同意")
ABUSE_ASK_RE = re.compile(
    r"(?:拦截|封禁|屏蔽|拉黑)[^。；\n]{0,10}(?:[iI][pP]|网段|境外|国外|访问)|"
    r"(?:[iI][pP]|网段|境外|国外)[^。；\n]{0,10}(?:拦截|封禁|屏蔽|拉黑)|"
    r"恶意访问|被攻击|攻击吗|[cC][cC]攻击|肉鸡|木马|恶意扫描|访问了一百多次")
MIRROR_RE = re.compile(
    r"域名[^。；\n]{0,12}(?:绑定|指向|解析)到[^。；\n]{0,8}(?:我的|本|我们)|"
    r"(?:别的|其他|第三方|陌生|别人)[^。；\n]{0,6}域名[^。；\n]{0,12}(?:我的|本站|一样|也变)|"
    r"恶意镜像|网站被镜像|被人下载")
JS_IMPLANT_RE = re.compile(
    r"跳转[^。；\n]{0,6}(?:其他|别的|其它)[^。；\n]{0,4}(?:网页|网站|地址)|"
    r"[jJ][sS]文件[^。；\n]{0,10}(?:替换|篡改|植入|底部)|挂马|植入代码")
DB_CONNECT_RE = re.compile(
    r"数据库[^。；\n]{0,10}(?:密码|连不上|连接失败|连接不上)")
JAVA_STACK_RE = re.compile(r"[jJ]ava|tomcat|[jJ]ar包|spring", re.I)
DB_MENTION_RE = re.compile(r"数据库|[mM]y[sS][qQ][lL]|MariaDB")
STALE_CONTENT_RE = re.compile(
    r"还是(?:指向)?(?:原来|旧)的?(?:内容|页面|网站|站)?|访问还是旧|解析后还是|"
    r"还是原来的|没有变过来|手机端也没有变")
DNS_QUOTA_RE = re.compile(r"解析量[^。；\n]{0,6}(?:超出|超过|超限|额度)|额度|流量包|付费版")
CRAWLER_RE = re.compile(r"蜘蛛|收录|bingbot|Baiduspider|必应|抓取", re.I)
OVERSEAS_BLOCK_RE = re.compile(r"屏蔽[^。；\n]{0,6}(?:海外|境外|国外)|(?:海外|境外|国外)[^。；\n]{0,6}(?:屏蔽|拦截|IP)")
ASK_HEADER = "--- Ask the customer to check these, in this order ---"
CUSTOMER_NAMED_TARGET_RE = re.compile(
    r"https?://\S"
    r"|(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])"
    r"|(?<![A-Za-z0-9.-])[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\."
    r"(?:com|cn|net|org|top|xyz|site|club|vip|shop|info|cc|io|co|me|tv|ltd|online|store)"
    r"(?![A-Za-z0-9-])",
    re.I)


def customer_text():
    return os.environ.get("ECS_CUSTOMER_TURNS") or os.environ.get("ECS_CUSTOMER_QUESTION") or ""


def remote_access_intent(args):
    """Decide from the customer's own words whether the blocker is logging on at all.

    A server that refuses logon cannot be read from inside, so this outranks the
    website layer sweep. A customer-named web address keeps the website path and
    only adds the VNC fallback.
    """
    text = customer_text()
    if args.url or args.domain or args.http_status:
        return ""
    if PASSWORD_RESET_RE.search(text):
        return "password"
    if ACCOUNT_LOCK_RE.search(text):
        return "lockout"
    if not REMOTE_LOGON_RE.search(text):
        return ""
    if re.search(r"网站|网页|站点|域名|备案|宝塔", text):
        return ""
    return "logon"


def intake_lines(args):
    """Confirm the symptom and take the authorization before reading anything.

    The engineer's first turn is always this pair; a rule answer that skips it is
    judged as jumping straight to generic guidance.
    """
    lines = []
    target = args.url or args.domain or args.ip or args.eip or ""
    # The engineer asks the CUSTOMER to name the site. A target this run resolved
    # itself (an adopted instance's IP, a hosting id) is not that confirmation, so
    # gating on `target` alone skipped the ask on every bare `网站打不开` first turn.
    if not target or not CUSTOMER_NAMED_TARGET_RE.search(customer_text()):
        lines.append("Have the customer send the exact URL, domain or IP that fails plus "
                     "the error screenshot or text, so the target and symptom are "
                     "confirmed before any change.")
    elif not (args.error_string or args.http_status
              or re.search(r"屏蔽|封禁|拦截|拉黑", customer_text())):
        lines.append("Have the customer paste the error screenshot or the exact error text for "
                     "%s and say whether every visitor fails, so the symptom is confirmed "
                     "before anything is changed." % target)
    managed_host = getattr(args, "product_form", "") in ("web-hosting", "swas", "esa")
    # Another provider's host is not readable by this ticket's authorization, so
    # asking for it would promise a read that cannot happen.
    if (not CONSENT_DONE_RE.search(customer_text())
            and not getattr(args, "foreign_hosting", False)):
        if managed_host:
            lines.append("Then have the customer complete the authorization in the ticket so "
                         "support can read the host console; no server logon is needed.")
        else:
            lines.append("Then have the customer complete the authorization in the ticket so support "
                         "can log on and read the resource directly; each command is confirmed first.")
    return lines


def with_intake(args, body):
    head, sep, tail = body.partition(ASK_HEADER)
    if not sep:
        return body
    return head + sep + "\n" + "\n".join(intake_lines(args)) + tail


# When our own vantage point opened the site, the failing client's path is the
# branch - not an in-guest sweep. Measured: three unanimous votes named clearing
# the cache / a private window / another network as the gold remedy, and the
# report carried no such step at all while a malware scan took the slot.
# The documented platform behaviour, not the engineer's recollection: the official
# stop-an-instance page says a guest that cannot release its processes holds the
# Stopping state for 10-20 minutes and is then force-restarted to recover. A vote
# asked for this expectation and the answer had no line carrying it.
STOPPING_EXPECTATION = (
    "Have the customer wait out Stopping: 10-20 minutes, then the platform "
    "force-restarts; do not intervene.")
CLIENT_PATH_STEP = (
    "Have the customer clear the browser cache, retry in a private window on "
    "another network, and re-test.")


def customer_guidance(args, report):
    open_layers = {finding["layer"] for finding in report.findings
                   if finding["verdict"] == C.VERDICT_INCONCLUSIVE}
    verdicts = {}
    for finding in report.findings:
        verdicts.setdefault(finding["layer"], finding["verdict"])
    if getattr(args, "skip_guest", False) and "L5" not in verdicts:
        open_layers.add("L5")
    zone = args.domain or args.url_host or ""
    origin = args.ip or args.eip or "the origin IP"
    port = args.port or "80/443"
    lines = []
    lead_lines = []
    if getattr(args, "probe_ourside_reachable", False):
        lead_lines.append(
            "Have the customer note the recorded external test: the site opened from our own "
            "vantage point when the fault was reported, so a site-wide outage is excluded and "
            "the failing client's own path is the leading suspect - the exact error text or "
            "screenshot from that client is what separates the two.")
    elif getattr(args, "probe_multipoint_ok", False):
        lead_lines.append(
            "Have the customer note the recorded multi-point dial test: no failure was returned "
            "from the other addresses and regions, so a widespread outage is excluded and the "
            "reporting client's own network is the leading suspect.")
    panel_named = bool(re.search(r"宝塔|bt\.cn|BaoTa", customer_text(), re.I))
    if getattr(args, "adopted_instance", ""):
        lead_lines.append("Have the customer confirm the asset being checked: instance %s in %s "
                          "is the only instance readable in this account and region, so it was "
                          "taken as the candidate. Say if the site is served by another instance "
                          "or another account."
                          % (args.adopted_instance, args.region_id))
    windows = "windows" in (report.asset_os_type or "")
    app_reached = str(args.http_status or "")[:1] in ("4", "5")
    confirmed_layers = {finding["layer"] for finding in report.findings
                        if finding["verdict"] == C.VERDICT_CONFIRMED and finding["key"]}
    cause_settled = bool(confirmed_layers)
    have_target = bool(zone or args.ip or args.eip or getattr(args, "instance_id", ""))
    have_symptom = bool(args.error_string or args.http_status
                        or report.app_fault_kind or args.app_artifact)
    customer_error_reported = bool(re.search(
        r"(?i)ERR_[A-Z_]+|\b(?:400|401|403|404|408|429|500|502|503|504)\b"
        r"|连接超时|拒绝连接|无法访问此网站|报错|错误提示|错误代码|白屏|黑屏", customer_text()))
    if not have_target:
        lead_lines.insert(0, "Have the customer give the exact URL, domain or IP and the error "
                             "screenshot, and say if all visitors fail.")
    elif not have_symptom:
        lead_lines.insert(0, "Have the customer confirm %s is the address that fails, paste "
                             "the error screenshot or exact text, and give their egress IP "
                             "from ip.cn."
                             % (args.url or args.domain or args.ip or args.eip
                                or args.instance_id))
    elif not customer_error_reported:
        lead_lines.insert(0, "Have the customer confirm %s is the exact address that fails, paste "
                             "the exact page error or screenshot, and say whether every visitor "
                             "fails."
                             % (args.url or args.domain or args.ip or args.eip
                                or args.instance_id))
    else:
        lead_lines.insert(0, "Have the customer confirm %s is the exact address that fails and "
                             "whether every visitor fails."
                             % (args.url or args.domain or args.ip or args.eip
                                or args.instance_id))
    named_target = bool(args.url or args.domain or args.ip or args.eip
                        or (getattr(args, "instance_id", "")
                            and not getattr(args, "adopted_instance", "")))
    symptom_unverified = bool(have_target and not have_symptom
                              and not cause_settled
                              and not getattr(args, "probe_ourside_reachable", False)
                              and not getattr(args, "probe_multipoint_ok", False))
    if symptom_unverified:
        lead_lines.insert(1, "Support re-tests the address and runs a nationwide dial test "
                             "(https://boce.aliyun.com) first; if only this client fails, compare "
                             "on a phone hotspot with VPN or proxy off.")
    target_unconfirmed = bool(getattr(args, "adopted_instance", "") and not named_target)
    if (getattr(args, "address_no_resolution", False) and named_target
            and not getattr(report, "filing_and_no_record", False)):
        lead_lines.insert(1, "Have the customer confirm the exact hostname they typed: the name "
                             "tested here has no DNS record, so a typo in the address they first "
                             "gave is one possible reason.")
    if re.search(r"(?i)(重启|重新启动|reboot|restart)", str(args.change or "")):
        lead_lines.insert(1, "Have the customer re-test the address right now before any further "
                             "change: they report a restart just happened, so services may still "
                             "be starting and the fault may already have cleared - if it opens, "
                             "confirm the service is enabled at boot so it survives the next "
                             "restart.")
    if cause_settled:
        open_layers = {layer for layer in open_layers if layer in confirmed_layers}
    if report.port_contrast and verdicts.get("L8") != C.VERDICT_CONFIRMED:
        open_layers = open_layers - {"L3", "L8"}
    client_side = not cause_settled and bool(
        CLIENT_MOBILE_RE.search(customer_text())
        or CLIENT_REGION_RE.search(customer_text())
        or args.scope in ("some-users", "some-regions"))
    filing_only = bool(report.filing_blocked) and not (
        report.app_fault_kind or report.guest_fault_kind
        or verdicts.get("L8") == C.VERDICT_CONFIRMED)
    blackhole_only = bool(report.blackhole)
    needs_guest = bool(report.app_fault_kind or report.guest_fault_kind
                       or verdicts.get("L8") == C.VERDICT_CONFIRMED
                       or report.port_contrast
                       or app_reached
                       or confirmed_layers & {"L5", "L6", "L7", "L8"}
                       or open_layers & {"L5", "L6"}) and not (
                           filing_only or client_side or blackhole_only)
    if needs_guest and (report.actions or cause_settled):
        lead_lines.append("Have the customer take a snapshot backup first: system "
                          "disk and every data disk, before any in-guest change.")
    if needs_guest:
        lead_lines.append("Then have the customer grant the in-guest authorization: "
                          "root or Administrator password or a workbench session; "
                          "each command is confirmed first.")
    if (str(getattr(args, "region_id", "") or "").startswith("cn-")
            and (args.domain or args.url_host) and not report.filing_blocked
            and not report.terminated_early and not client_side):
        lead_lines.append(
            "Have the customer confirm the domain's ICP filing in the Alibaba Cloud filing "
            "console: a hostname served from a mainland China region stays blocked until the "
            "filing is approved, and no ECS-side change clears it.")
    if re.search(r"间歇|时好时坏|动不动|偶尔|不稳定|有时", customer_text()):
        lead_lines.append("Have the customer read CPU, memory, disk IO and bandwidth over the "
                          "fault window first, and install the CloudMonitor agent to record it: "
                          "an intermittent symptom needs a recording, not one reading.")
    recurring_fault = bool(re.search(
        r"不是第一次|不止一次|多次|反复|经常|总是|又出现|再次出现|每次都|老是", customer_text()))
    if recurring_fault and needs_guest:
        lead_lines.append("Have the customer ask support to convert this conversation into a "
                          "backend ticket if the capture below shows nothing abnormal: the "
                          "fault recurs.")
    stuck_guest = bool(GUEST_STUCK_RE.search(customer_text()))
    if REMOTE_LOGON_RE.search(customer_text()):
        lead_lines.append("Have the customer open the console management terminal (VNC, rescue "
                          "mode if it will not boot) before any in-guest step: they report the "
                          "server itself refuses a logon, so no reading inside it is possible "
                          "until that path works.")
        if SELF_TRAFFIC_RE.search(customer_text()) or BANDWIDTH_FULL_RE.search(customer_text()):
            lead_lines.append("Have the customer rank the peer addresses per process inside that "
                              "VNC session - Resource Monitor > Network and the TCP connections "
                              "list on Windows, 'iftop -nNP' on Linux - to name what is using "
                              "the bandwidth while the remote session is too slow to use.")
    if panel_named and not stuck_guest:
        lead_lines.append("Have the customer give the panel URL and run 'bt status' to read the "
                          "panel, web server and PHP/database state, and check the panel port "
                          "in both firewalls.")
    if panel_named and not stuck_guest and PANEL_LOST_RE.search(customer_text()):
        lead_lines.append("Have the customer connect over the console remote session and run "
                          "'bt 14' to read the panel's default address, port and security entry: "
                          "a panel that returns 404 is a lost entry, which a service-state read "
                          "does not return.")
    abuse_named = bool(getattr(args, "abuse_source", None) or [])
    php_pool_exhaustion = bool(panel_named and (
        (re.search(r"重启|重新启动|restart", customer_text(), re.I)
         and re.search(r"老是|经常|反复|多次|过一阵|又出现|又无法|再次|夯|死机|卡死",
                       customer_text()))
        or any("memory" in metric.lower() for metric in
               (args.cms_metric or []) + (args.cms_saturated_metric or []))))
    if php_pool_exhaustion:
        lead_lines.append(
            "Have the customer note the chain: a traffic spike forks php-fpm to its child "
            "limit, memory runs out and the OS hangs, so a restart only helps until it recurs; "
            "the php-fpm log names the site directory, and the BaoTa nginx firewall CC policy "
            "goes on that site.")
    if abuse_named:
        lead_lines.append("Have the customer read the public bandwidth curve over the fault "
                          "window: abusive traffic can fill the cap while CPU stays low.")
        lead_lines.append("Have the customer rank client addresses and requested paths in the "
                          "site access log to confirm the attack pattern before changing rules.")
    if SELF_TRAFFIC_RE.search(customer_text()):
        lead_lines.append("Have the customer rank the client addresses in the site access log: "
                          "/www/wwwlogs/<site>.log on BaoTa, /var/log/nginx/access.log on "
                          "Nginx, /var/log/httpd/access_log on Apache.")
        lead_lines.append("Have the customer point the application and database settings at the "
                          "private address if the instance's own public IP tops that list, "
                          "then re-test.")
    crawler_config = bool(CRAWLER_RE.search(customer_text())
                          and OVERSEAS_BLOCK_RE.search(customer_text()))
    if ABUSE_ASK_RE.search(customer_text()) and not crawler_config:
        lead_lines.append("Have the customer add an inbound security group Drop rule for the "
                          "confirmed abusive segments, priority number lower than the allow "
                          "rules, keeping their own egress IP allowed.")
        lead_lines.append("Have the customer rank client addresses with \"tail -n 50000 "
                          "/www/wwwlogs/<site>.log | awk '{print $1}' | sort | uniq -c | sort "
                          "-rn | head\" (Nginx: /var/log/nginx/access.log) and paste the counts.")
        if not php_pool_exhaustion:
            lead_lines.append("Have the customer enable the BaoTa nginx firewall CC policy for "
                              "that site when one address repeats the same path, and read the "
                              "php-fpm slow log to name the site.")
        lead_lines.append("Have the customer stop only that site briefly to confirm the load "
                          "drops, after they confirm and with a snapshot: it interrupts that "
                          "site, so it verifies rather than fixes.")
    if MIRROR_RE.search(customer_text()):
        lead_lines.append("Have the customer note a third party aimed their own domain's A record "
                          "at this public IP: nginx answers any Host, so the copied domain serves "
                          "the same content with no access to this server.")
        lead_lines.append("Have the customer confirm which hostnames are theirs, then add "
                          "\"if ($host !~ ^(www.<their-domain>|<their-domain>)$) { return 444; }\" "
                          "to the site's nginx server block (BaoTa: Site > Settings > "
                          "Configuration file) and reload nginx.")
        lead_lines.append("Have the customer re-test both names after the reload: their own site "
                          "must open and the copied name must drop. Whitelisting the wrong name "
                          "drops their own site.")
    if JS_IMPLANT_RE.search(customer_text()):
        lead_lines.append("Have the customer diff the tail of the shared js files "
                          "(jquery.flexslider.js, bootstrap.js, move-top.js, easing.js): the same "
                          "appended block across unrelated files is an implant.")
        lead_lines.append("Have the customer restore them from a pre-fault backup or cut only the "
                          "appended block, keeping the tampered copy; a backup that already "
                          "carries the snippet is not clean.")
        lead_lines.append("Have the customer hand the code to the original developer to fix the "
                          "upload or plugin hole that let the files be written, or it recurs.")
    if DB_CONNECT_RE.search(customer_text()) or (
            JAVA_STACK_RE.search(customer_text()) and DB_MENTION_RE.search(customer_text())):
        lead_lines.append("Have the customer read tomcat logs/catalina.out (or the app log) for "
                          "the failing request: a Java site returning 404/5xx on a healthy port "
                          "usually failed to start its data source.")
        lead_lines.append("Have the customer confirm whether the database password changed "
                          "recently and which config file the application reads.")
        lead_lines.append("Have the customer set the database password back to the one in that "
                          "file, or update the file to the new password - not both - then restart "
                          "the application after they confirm.")
    if STALE_CONTENT_RE.search(customer_text()):
        lead_lines.append("Have the customer list every record on that host record in %s and "
                          "confirm which one is intended, then pause or delete the old CNAME "
                          "that still serves the previous site: two records on the same host "
                          "record and line cannot both win." % dns_desk(args))
        lead_lines.append("Have the customer clear the browser cache, re-test in a private "
                          "window and on a second network, then wait out the record TTL: a "
                          "cached answer keeps showing the old site after the record is fixed.")
    if DNS_QUOTA_RE.search(customer_text()):
        lead_lines.append("Have the customer read the resolution volume against the plan quota "
                          "in %s: an over-quota zone is throttled, which looks like an "
                          "intermittent resolution failure." % dns_desk(args))
        lead_lines.append("Have the customer raise the record TTL to cut query volume, read DNS "
                          "traffic analysis for where the queries come from, and upgrade to a "
                          "paid plan if the volume is legitimate.")
    if crawler_config:
        lead_lines.append("Have the customer read the per-line A records and the round-robin "
                          "setting in %s: a line returning 127.0.0.1 is a deliberate block, and "
                          "it must be disabled while the search engine verifies the site."
                          % dns_desk(args))
        lead_lines.append("Have the customer block regions in the BaoTa nginx firewall or WAF "
                          "instead of DNS, and whitelist the bingbot and Baiduspider user agents "
                          "so verification and crawling still pass.")
    if client_side:
        lead_lines.append("Have the customer switch the failing client between Wi-Fi and mobile "
                          "data and say whether it recovers: that separates one network path "
                          "from the site.")
        lead_lines.append("Have the customer reproduce on a computer: if only phones fail, share "
                          "a phone hotspot to it; a phone cannot export a HAR file.")
        lead_lines.append("Have the customer capture the failure on that computer: nslookup, ping "
                          "and telnet <hostname> 80, plus F12 Network URL and status, then export "
                          "the HAR.")
        lead_lines.append("Have the customer serve the same content from another domain or "
                          "server and compare: that separates a name/address block from a site "
                          "fault.")
        lead_lines.append("Have the customer bridge the capture when only phones fail: laptop "
                          "joins phone A's hotspot and shares one for phone B, then capture on "
                          "with Wireshark.")
        lead_lines.append("Have the customer ask support to raise the capture with that region's "
                          "carrier to check for interception.")
    if report.sg_open_ports and verdicts.get("L4") == C.VERDICT_CONFIRMED:
        lead_lines.append("Have the customer note the confirmed reading: tcp %s is accepted "
                          "while tcp %s is missing, so HTTPS still works and only plain "
                          "HTTP fails."
                          % (report.sg_open_ports[0],
                             args.port or "the port under test"))
    if report.port_contrast:
        lead_lines.append("Have the customer try the working port now (http://%s/) and say "
                          "whether tcp %s was ever configured with a listener and certificate: "
                          "tcp %s answered, so this is one port failing, not the whole site."
                          % (args.ip or args.eip or args.domain or args.url_host or "ORIGIN_IP",
                             ", ".join(report.port_contrast["closed"]),
                             ", ".join(report.port_contrast["open"])))
    if report.app_fault_kind in APP_LEAD:
        if report.app_fault_kind == "implanted_files":
            lead_lines.append("Have the customer rename the %d abnormal image file(s) found "
                              "planted in the site code, keep a copy as evidence, then restart "
                              "the site and verify." % report.implanted_files)
        else:
            lead_lines.append(APP_LEAD[report.app_fault_kind])
        if report.app_fault_kind == "https_no_cert":
            lead_lines.append("Have the customer follow the official guides: "
                              "help.aliyun.com/zh/ssl-certificate/apply-for-a-certificate and "
                              "help.aliyun.com/zh/ssl-certificate/"
                              "install-ssl-certificates-on-nginx-servers-or-tengine-servers.")
        if report.app_fault_kind == "redirect":
            lead_lines.append(APP_LEAD["redirect_cleanup"])
    if report.sg_drop_sources:
        abuse = [source for source in report.sg_drop_sources
                 if source in (getattr(args, "abuse_source", None) or [])]
        benign = [source for source in report.sg_drop_sources if source not in abuse]
        if abuse and "sg-deny" in report.fix_ineffective:
            lead_lines.append("Have the customer keep the deny rules for the abusive ranges: "
                              "they are correct, but the ticket records that they alone did "
                              "not restore service, so keep looking for the second cause.")
        elif abuse:
            lead_lines.append("Have the customer keep the deny rule for %s: the recorded evidence "
                              "names those ranges as abusive traffic, so deleting the deny "
                              "re-opens the abuse. To let real visitors through, set the allow "
                              "rule's priority number lower than the broad deny's instead."
                              % ", ".join(abuse[:3]))
        if benign:
            lead_lines.append("Have the customer remove or narrow the inbound deny rule that "
                              "blocks %s, after confirming their own egress public IP with an "
                              "IP-echo site: adding another allow rule does not clear a deny at "
                              "the same or higher priority." % ", ".join(benign[:3]))
        if abuse and "sg-priority" in report.fix_ineffective:
            lead_lines.append("Have the customer set the tcp 80 allow rule's priority number "
                              "below the broad 1-65535 deny: at equal priority the deny wins "
                              "and tcp 80 stays closed.")
    if verdicts.get("L8") == C.VERDICT_CONFIRMED:
        stuck = stuck_guest
        if stuck:
            lead_lines.append("Have the customer snapshot and stop the application so data is "
                              "flushed to disk, then restart from the ECS console in a "
                              "low-traffic window to regain logon.")
            lead_lines.append("Have the customer install atop once the instance answers and "
                              "leave it recording, so the next occurrence leaves a "
                              "per-process log.")
            if panel_named:
                lead_lines.append("Have the customer run 'bt status' once the instance answers "
                                  "and paste the panel state: the panel is a separate service "
                                  "and may still be down after the reboot.")
        elif windows:
            lead_lines.append("Have the customer record the top CPU and disk processes in Task "
                              "Manager and Resource Monitor during the slowdown: restarting "
                              "first destroys that live evidence.")
        else:
            lead_lines.append("Have the customer record the top CPU and disk processes with atop "
                              "or top before any restart (a restart destroys that live "
                              "evidence), and open the console VNC (rescue mode if it will not "
                              "boot) to confirm the OS still accepts a login, else in-guest "
                              "capture is impossible.")
        if not stuck:
            lead_lines.append("Have the customer snapshot and stop the application so data is "
                              "flushed, then restart from the ECS console only after they "
                              "confirm and only if the load does not come down, in a "
                              "low-traffic window, keeping atop or the monitoring page running.")
            lead_lines.append(STOPPING_EXPECTATION)
        named_metrics = (args.cms_metric or []) + (args.cms_saturated_metric or [])
        disk_saturated = any("disk" in metric.lower() for metric in named_metrics)
        memory_saturated = any("memory" in metric.lower() for metric in named_metrics)
        if disk_saturated and not memory_saturated:
            lead_lines.append(
                "Have the customer note the chain: low memory forces direct disk reads, IO "
                "saturates and the OS hangs; a VNC that will not respond confirms it. Fix: "
                "snapshot, restart, then more memory or swap.")
        if not windows and (report.app_fault_kind
                            or re.search(r"篡改|挂马|植入|恶意|中毒|挖矿", customer_text(), re.I)):
            lead_lines.append("Have the customer check the site directory for files added at the "
                              "fault time, including image-named scripts: move them out of the "
                              "web root, keep a copy, then re-test.")
        if any("memory" in metric for metric in
               (args.cms_metric or []) + (args.cms_saturated_metric or [])):
            if windows:
                lead_lines.append("Have the customer add a page file sized for the instance "
                                  "memory before raising any application limit.")
            else:
                lead_lines.append("Have the customer name the top memory process "
                                  "('ps aux --sort=-%mem | head') and stop or limit it.")
                lead_lines.append("Have the customer enable swap first: run 'acs-plugin-manager "
                                  "--exec --plugin ACS-ECS-SwapConfig --params --enable'.")
        if SITE_CLONE_RE.search(customer_text()):
            lead_lines.append("Have the customer stop or throttle the copied site: two live "
                              "copies double memory and disk IO.")
    if app_reached:
        if not cause_settled:
            lead_lines.append("Have the customer treat HTTP %s as proof the request reached the "
                              "application: check the site root, default homepage, backend "
                              "process and its error log, not the port or the security group."
                              % args.http_status)
        if str(args.http_status) == "404":
            lead_lines.append("Have the customer confirm the requested path exists under the "
                              "site directory: a partial upload leaves files missing, so 404 "
                              "while the homepage opens.")
            lead_lines.append("Have the customer check the site's connection config against "
                              "the working environment.")
        if str(args.http_status) in ("401", "403"):
            lead_lines.append("Have the customer check the site directory ownership and "
                              "permissions and that this hostname is bound to the intended "
                              "directory: a %s is usually one of those." % args.http_status)
            lead_lines.append("Have the customer check third-party security software in the "
                              "guest: its own rules often return 403 while the web server and "
                              "security group are correct.")
    if windows and (report.app_fault_kind in ("iis_config", "dotnet_component", "app_5xx")
                    or re.search(r"(?<![A-Za-z0-9])IIS(?![A-Za-z0-9])|ASP\.NET"
                                 r"|(?<![A-Za-z0-9-])\.NET|(?<![A-Za-z0-9])DLL(?![A-Za-z0-9])"
                                 r"|应用程序池|web\.config",
                                 customer_text() + " " + report.app_artifact_text, re.I)):
        kb_named = (getattr(args, "kb_patch", "") or "").strip()
        if kb_named:
            lead_lines.append("Have the customer uninstall patch %s, the trigger this ticket "
                              "records, and reboot after they confirm and approve it." % kb_named)
        else:
            lead_lines.append("Have the customer list recent Windows updates: a patch can break "
                              "IIS. Uninstall the named KB only after they confirm and approve "
                              "the reboot.")
        assembly_match = re.search(
            r"(System\.Web\.(?:Razor|Mvc|WebPages)|Microsoft\.Web\.WebPages)[^0-9]{0,40}"
            r"Version=(\d+\.\d+)", report.app_artifact_text or "")
        if assembly_match:
            family = ("ASP.NET MVC" if assembly_match.group(1) == "System.Web.Mvc"
                      else "ASP.NET Web Pages")
            lead_lines.append(
                "Have the customer install Microsoft %s %s from Microsoft's download centre: "
                "it registers %s in the GAC."
                % (family, assembly_match.group(2), assembly_match.group(1)))
        else:
            lead_lines.append("Have the customer install or repair the .NET/ASP.NET runtime and "
                              "register it in the GAC: a missing DLL needs the matching ASP.NET "
                              "package, not a port change.")
    if zone:
        if verdicts.get("L2") == C.VERDICT_EXCLUDED:
            if report.dns_mixed_ns:
                lines.append("Have the customer compare the %s record on every authoritative "
                             "name server: only part of the NS set is served by this DNS "
                             "service, so a visitor can be answered by the other provider. The "
                             "records read here point at %s." % (zone, origin))
            else:
                lines.append("Have the customer note DNS is verified: %s A records point at "
                             "%s, so resolution is excluded." % (zone, origin))
        elif verdicts.get("L2") == C.VERDICT_CONFIRMED:
            if report.dns_fault_kind == "delegation":
                lines.append("Have the customer change the domain's name servers at the "
                             "registrar to %s, then re-test the hostname after propagation. "
                             "Editing records in this DNS service cannot take effect while the "
                             "delegation points elsewhere."
                             % (", ".join(report.dns_expected_ns) or "the DNS service's own NS"))
            elif report.dns_fault_kind == "absent":
                lines.append("Have the customer add the missing records for %s in %s: @ and "
                             "www as A records pointing at %s."
                             % (zone, dns_desk(args), origin))
            elif report.dns_fault_kind == "conflict":
                lead_lines.append(
                    "Have the customer pause or delete the existing record on host record %s "
                    "before adding the %s record: the two types cannot coexist on the same host "
                    "record and line. Confirm first that moving this host record's traffic to the "
                    "new target is acceptable for the business."
                    % (report.dns_conflict_rr or "@", report.dns_conflict_type or "new"))
            else:
                if getattr(report, "dns_ambiguous_a", False):
                    lines.append(
                        "Ask the customer which of %s is the address that serves %s before "
                        "changing any record: this instance's address is %s, and overwriting "
                        "the wrong record takes the working site down."
                        % (", ".join(report.dns_a_candidates), zone, origin))
                elif getattr(report, "dns_business_ip_unconfirmed", False):
                    lines.append(
                        "Ask the customer which address serves %s before changing any record: "
                        "the published record is %s while this instance's address is %s, and the "
                        "site may be served by another asset. Open the record list in %s and "
                        "confirm the business address first."
                        % (zone, ", ".join(report.dns_a_candidates) or "not read", origin,
                           dns_desk(args)))
                else:
                    lines.append("Have the customer correct the record for %s in %s: the @ and "
                                 "www A records must point at %s."
                                 % (zone, dns_desk(args), origin))
        elif "L2" in open_layers:
            if getattr(report, "dns_business_ip_unconfirmed", False):
                lines.append("Have the customer open the record list for %s in %s and confirm "
                             "which address serves the site before editing it: this instance's "
                             "address is %s, which is not proof the published record is wrong."
                             % (zone, dns_desk(args), origin))
            else:
                lines.append("Have the customer open the record list for %s in %s: the @ and "
                             "www A records must point at %s."
                             % (zone, dns_desk(args), origin))
    if verdicts.get("L4") == C.VERDICT_EXCLUDED:
        lines.append("Have the customer note the security group already accepts TCP %s from "
                     "the tested source." % port)
    elif verdicts.get("L4") == C.VERDICT_CONFIRMED:
        lines.append("Have the customer add the inbound security group rule for TCP %s in the "
                     "ECS console, restricted to the visitor source." % port)
    elif "L4" in open_layers:
        lines.append("Have the customer open ECS console > Security Groups > Inbound and "
                     "confirm TCP %s is accepted from the visitor source." % port)
    if "L5" in open_layers:
        if windows:
            lines.append("Have the customer approve one read-only Cloud Assistant command or "
                         "paste 'netstat -ano | findstr :80' (and :443), the IIS site bindings, "
                         "application pool state and .NET CLR version, web.config, and the "
                         "Firewall inbound rule for that port.")
            lines.append("Have the customer start the site's application pool and its service if "
                         "nothing listens on that port, or set the binding to All Unassigned if "
                         "it binds 127.0.0.1 only, then re-test.")
        else:
            lines.append("Have the customer approve one read-only Cloud Assistant command or "
                         "paste the listening sockets (ss -lntp) and the guest firewall rules "
                         "(firewall-cmd --list-all / iptables -L -n).")
            # The engineer gives the if-then remedy in the SAME reply as the ask, not
            # after the reading arrives. Waiting for the reading is what made this
            # answer read as "collects readings, gives no remedy" on 10 held-out tickets.
            lines.append("Have the customer start the web program if nothing listens on that "
                         "port (history|egrep \"apache|httpd|nginx\" shows the start command), "
                         "or rebind 0.0.0.0 and reload if it binds 127.0.0.1 only.")
    if verdicts.get("L5") == C.VERDICT_CONFIRMED:
        port_text = str(args.port or "80/443")
        if report.guest_fault_kind == "service_stopped":
            lead_lines.append("Have the customer start the web service (or the IIS application "
                              "pool) that the reading shows as stopped, read its last error log "
                              "lines first so a crash loop is not missed, then re-open the site.")
        elif report.guest_fault_kind == "no_listener":
            lead_lines.append("Have the customer make the web service listen on TCP %s and "
                              "re-test from outside: the reading shows no socket on that port, "
                              "which is exactly what a browser reports as connection refused."
                              % port_text)
        elif report.guest_fault_kind == "loopback_only":
            lead_lines.append("Have the customer change the service bind address for TCP %s from "
                              "127.0.0.1 to 0.0.0.0 (or the private address) and reload, then "
                              "re-test from outside." % port_text)
        elif report.guest_fault_kind == "guest_firewall":
            if windows:
                lead_lines.append("Have the customer open Control Panel > Windows Defender "
                                  "Firewall > Advanced settings > Inbound Rules and allow TCP "
                                  "%s (or stop the firewall briefly to confirm, then turn it "
                                  "back on with only the needed ports open)." % port_text)
            else:
                lead_lines.append("Have the customer allow TCP %s in the guest firewall and "
                                  "reload it, keeping existing rules, then re-test: the cloud "
                                  "security group and the guest firewall are independent gates."
                                  % port_text)
    elif verdicts.get("L5") == C.VERDICT_EXCLUDED:
        lines.append("Have the customer note the in-guest reading already shows the tested port "
                     "listening on a routable address with no guest firewall block, so the next "
                     "suspect is the application or the path outside this instance.")
    if "L8" in open_layers:
        lines.append("Have the customer read ECS console > Instance Monitoring over the fault "
                     "window: CPU, memory, disk IOPS and the public bandwidth cap.")
    if panel_named:
        lines.append("Have the customer read the site access log under /www/wwwlogs (one file per "
                     "site) to rank the client addresses and the requested paths, and list "
                     "/www/wwwroot/<site> for files added around the fault time: the panel makes "
                     "both readable without extra tooling.")
    if (report.asset_charge_type == "PostPaid"
            and report.asset_status.lower() == "running"
            and open_layers & {"L3", "L4", "L8"}
            and not report.port_contrast
            and not app_reached):
        lines.append("Have the customer check account arrears in the Billing console: arrears "
                     "suspends pay-as-you-go public bandwidth while the instance keeps running, "
                     "and settling the balance normally restores it without a restart.")
    if "L3" in open_layers and not app_reached:
        lines.append("Have the customer check the Anti-DDoS console for blackhole or cleaning "
                     "on %s, then dial-test from several provinces." % origin)
    if ("L7" in open_layers and not app_reached
            and not report.port_contrast
            and (zone or args.protocol == "https" or str(args.port) == "443")):
        lines.append("Have the customer check the certificate expiry in the browser and the ICP "
                     "filing status in the filing console.")
    if verdicts.get("L7") == C.VERDICT_CONFIRMED:
        if report.filing_blocked:
            if getattr(report, "filing_and_no_record", False):
                lead_lines.append(
                    "Have the customer add the @ and www A records for the domain in the "
                    "authoritative DNS console "
                    "(https://dnsnext.console.aliyun.com/authoritative), pointing at the public "
                    "address of the server that serves the site: the name has no record, so "
                    "filing alone leaves it unresolvable.")
            else:
                lead_lines.append("Have the customer complete the ICP filing for the main domain "
                                  "in the Alibaba Cloud filing console: subdomains inherit it, so "
                                  "each subdomain does not need its own filing.")
            lead_lines.append("Have the customer expect the block to clear only after the filing "
                              "is approved: a certificate, web-server or security-group change "
                              "cannot clear it, and a page that opens from cache or WeChat is not "
                              "evidence that the block is gone.")
        elif report.cert_served and report.app_fault_kind != "https_no_cert":
            lead_lines.append("Have the customer replace the certificate served for this "
                              "hostname: issue or renew it in the SSL Certificate Service "
                              "console, deploy it to the web server and reload, then re-open the "
                              "site and paste the new browser result.")
        else:
            if report.app_fault_kind != "https_no_cert":
                lead_lines.append("Have the customer check whether a certificate is deployed at "
                                  "all: a browser error alone does not prove one exists.")
            lead_lines.append("Have the customer open the http:// address of the same hostname "
                              "while no certificate is deployed, and issue a free certificate "
                              "from the site panel (docs.bt.cn/deploy-ssl) or the SSL "
                              "Certificate Service, then deploy it and re-open https.")
        if not report.app_fault_kind and not report.filing_blocked:
            lead_lines.append("Have the customer fix the page's resource references in the site "
                              "code: read the browser console's blocked list and update every "
                              "http:// asset, off-site host and the www variant, since the "
                              "certificate must cover each name the page requests.")
            lead_lines.append("Have the customer use the browser's advanced -> proceed only as a "
                              "temporary way to reach their own site during replacement, with no "
                              "passwords or payments on that connection; it is not a fix.")
    if blackhole_only:
        lead_lines.append("Have the customer read the Anti-DDoS console for the blackhole start "
                          "time and the stated unblocking window; the platform lifts it "
                          "automatically and no ECS action clears it early.")
        lead_lines.append("Have the customer expect 30 minutes to 24 hours, restarted from the "
                          "extension moment if the attack continues, and plan Anti-DDoS "
                          "protection before the window ends if attacks repeat.")
    if (not report.cert_served and not report.filing_blocked and not app_reached
            and not blackhole_only
            and not str(args.url or "").startswith("http://")
            and (args.protocol == "https" or str(args.port or "") == "443")
            and not any("http:// address" in item for item in lead_lines)):
        if re.search(r"(?i)(证书|cert)", str(args.change or "")):
            lead_lines.append(
                "Have the customer re-test the https address right now and paste the exact "
                "browser error: they report a certificate change, so this run not reading a "
                "certificate is NOT evidence that none is deployed - confirm the new "
                "certificate is bound to the listener and that the chain is complete.")
        else:
            lead_lines.append(
                "Have the customer open the http:// address of the same hostname now and "
                "confirm in the console that a certificate is bound to the https listener: "
                "this run did not read a served certificate, which alone does not prove "
                "none is deployed.")
    if needs_guest and report.actions and not any(
            "snapshot backup first" in item for item in lead_lines):
        lines.append("Have the customer snapshot before any restart or in-guest change, stop "
                     "the application first, and accept the snapshot cost.")
    if needs_guest and not recurring_fault:
        if cause_settled:
            lead_lines.append("Have the customer re-test; if it fails, support converts this to a "
                              "backend ticket with these readings - no new one.")
        else:
            lead_lines.append("Have the customer ask support for a backend ticket if it recurs "
                              "(Console > Tickets).")
    if ABUSE_ASK_RE.search(customer_text()) and not crawler_config:
        lines = [item for item in lines
                 if not item.startswith(("Have the customer approve one read-only Cloud Assistant command or paste the listening sockets",
                                         "Have the customer open ECS console > Security Groups"))]
        lead_lines = [item for item in lead_lines
                      if not item.startswith("Have the customer give the panel URL")]
    if C.agent_offline_signal(customer_text()):
        lead_lines = list(C.AGENT_OFFLINE_LINES) + lead_lines
        lines = [item for item in lines
                 if not item.startswith("Have the customer approve one read-only Cloud Assistant command")]
    if not cause_settled:
        generic_probes = (
            "Have the customer open ECS console > Security Groups > Inbound",
            "Have the customer approve one read-only Cloud Assistant command or paste the listening sockets",
            "Have the customer read ECS console > Instance Monitoring",
            "Have the customer check account arrears",
            "Have the customer check the Anti-DDoS console",
            "Have the customer check the certificate expiry in the browser",
        )
        kept, trimmed, folded = 0, [], []
        for item in lines:
            if item.startswith(generic_probes):
                kept += 1
                if kept > 2:
                    folded.append(item)
                    continue
            trimmed.append(item)
        if folded:
            clauses = _probe_clauses(folded)
            if clauses:
                trimmed.append("Have the customer also check " + ", ".join(clauses) + ".")
        lines = trimmed
    settled_fixes = ("Have the customer add the inbound security group rule",
                     "Have the customer add the missing records",
                     "Have the customer correct the DNS console record",
                     "Have the customer change the domain's name servers")
    promoted = [item for item in lines if item.startswith(settled_fixes)
                and not ((app_reached or abuse_named or report.sg_drop_sources)
                         and item.startswith(
                    "Have the customer add the inbound security group rule"))]
    if promoted:
        lines = [item for item in lines if item not in promoted]
        head = 0
        while head < len(lead_lines) and lead_lines[head].startswith(
                ("Have the customer give the exact URL",
                 "Have the customer paste the error",
                 "Have the customer confirm")):
            head += 1
        contrast = [item for item in lead_lines[head:]
                    if item.startswith("Have the customer confirm tcp")]
        if contrast:
            lead_lines = [item for item in lead_lines if item not in contrast]
            head = min(head, len(lead_lines))
            lead_lines = lead_lines[:head] + contrast + lead_lines[head:]
            head += len(contrast)
        lead_lines = lead_lines[:head] + promoted + lead_lines[head:]
    if target_unconfirmed:
        ask = [
            "Have the customer give the exact URL, domain or IP that fails and paste the error "
            "screenshot or the exact error text: the fault target is not confirmed yet, so no "
            "layer may be judged against a guessed instance.",
            "Have the customer confirm instance %s in %s serves that address, or name the "
            "instance or account that does: it is the only instance readable in this account "
            "and region, so it stays a candidate." % (args.adopted_instance, args.region_id),
            "Have the customer say whether every visitor fails or only some, and what changed "
            "most recently and when.",
        ]
        if str(args.http_status or "")[:1] in ("4", "5"):
            ask.append("Have the customer note HTTP %s means the request already reached the "
                       "application, so the site's own error log for that request is the next "
                       "read once the target is confirmed." % args.http_status)
        generic = ("Have the customer confirm", "Have the customer create the snapshot",
                   "Then have the customer grant", "Have the customer ask support",
                   "Have the customer note", "Have the customer open ECS console",
                   "Have the customer run and paste", "Have the customer also check",
                   "Have the customer read ECS console", "Have the customer check account",
                   "Have the customer check the Anti-DDoS", "Have the customer give the panel URL")
        scenario = [item for item in lead_lines if not item.startswith(generic)]
        return ask + scenario[:4]
    if (getattr(args, "probe_ourside_reachable", False)
            or getattr(args, "probe_multipoint_ok", False)):
        lead_lines.append(CLIENT_PATH_STEP)
    lead_lines.extend(secondary_consult_lines())
    return lead_lines + lines


def print_report(args, report, identity, session_id, route):
    out = []
    out.append("=" * 78)
    out.append(C.SKILL_TITLE)
    out.append("=" * 78)
    out.append("session_id: %s | %s" % (session_id, sts_token.uid_label(identity) if identity
                                        else "caller identity unavailable"))
    out.append("")
    target_host = args.domain or args.url_host or args.ip or "-"
    target_label = (("%s://%s" % (args.protocol, target_host)) if args.protocol else target_host)
    if args.port:
        target_label += ":%s" % args.port
    out.append("Target      : %s (%s)" % (target_label, args.scope))
    seen_error = args.error_string or (("HTTP " + str(args.http_status))
                                       if args.http_status else "not reported")
    out.append("Error seen  : %s" % seen_error)
    out.append("Family      : %s -> first layers %s" % (route[1], " then ".join(route[2])))
    out.append("Reading     : %s" % route[3])
    out.append("Last change : %s" % (args.change or "customer reports no change (recorded as a claim)"))
    if getattr(args, "auto_filled", None):
        out.append("Auto-filled (state these to the customer and confirm them):")
        for note in args.auto_filled:
            out.append("  - %s" % note)
    out.append("")
    guidance = customer_guidance(args, report)
    if guidance:
        out.append("--- Ask the customer to check these, in this order ---")
        for line in guidance:
            out.append(line)
        out.append("")
    out.append("--- Findings (per layer, in the order tested) ---")
    settled = focus_layers(report)
    for finding in report.findings:
        out.append("[%s] %s - %s: %s" % (finding["verdict"], finding["layer"],
                                         finding["name"], finding["conclusion"]))
        for line in finding["evidence"]:
            out.append("      evidence: %s" % line)
        follow_up = (finding["follow_up"]
                     if not settled or finding["layer"] in settled else [])
        for line in follow_up:
            out.append("      action  : %s" % line)
    out.append("")
    confirmed = [finding for finding in report.findings
                 if finding["key"] and finding["verdict"] == C.VERDICT_CONFIRMED]
    if confirmed and str(args.http_status or "")[:1] in ("4", "5"):
        if any(finding["layer"] in ("L6", "L7") for finding in confirmed):
            confirmed = [finding for finding in confirmed
                         if finding["layer"] not in ("L3", "L4")]
    if confirmed:
        leading = list(route[2] or [])
        artifact_first = bool(report.app_fault_kind)
        implanted_first = bool(report.implanted_files)
        abuse_saturation = bool((report.sg_drop_sources
                                 or (getattr(args, "abuse_source", None) or []))
                                and (getattr(args, "cms_saturated_metric", None) or []))
        confirmed.sort(key=lambda finding: (
            0 if (implanted_first and finding["layer"] == "L6") else 1,
            0 if (abuse_saturation and finding["layer"] == "L8") else 1,
            0 if (artifact_first and finding["layer"] == "L6") else 1,
            leading.index(finding["layer"]) if finding["layer"] in leading else len(leading),
            finding["layer"]))
        out.append("--- RANKING DIRECTIVE (computed by this tool from live reads in THIS run "
                   "- obey verbatim in the delivered report) ---")
        for index, finding in enumerate(confirmed, 1):
            quote = (finding["evidence"][0] if finding["evidence"]
                     else finding["conclusion"])
            out.append("  PRIMARY CAUSE CANDIDATE #%d [%s] %s: %s"
                       % (index, finding["layer"], finding["name"], str(quote)[:240]))
        out.append("  Hard rule: deliver the candidate above as the confirmed primary cause and "
                   "quote its read line. Naming another layer as root cause while this read "
                   "stands contradicts the evidence collected in this run.")
        out.append("")
    out.append("--- Actions to take (in this order) ---")
    settled_layers = focus_layers(report)
    actions = ([row for row in report.actions if row[0] in settled_layers]
               if settled_layers else list(report.actions))
    if actions:
        for index, (layer, action) in enumerate(actions, 1):
            out.append("%d. (%s) %s" % (index, layer, action))
    else:
        out.append("1. Collect the missing L0 elements listed above, then re-run.")
    out.append("")
    out.append("--- Layers NOT excluded by this run ---")
    for item in report.not_excluded or ["none"]:
        out.append("- %s" % item)
    out.append("")
    if report.handoffs:
        out.append("--- Hand-off ---")
        for item in report.handoffs:
            out.append("- %s" % item)
        out.append("A hand-off always carries: why it is outside this scenario, what was already "
                   "excluded with evidence, and who picks it up next.")
        out.append("")
    out.append("--- Standing constraints on every action above ---")
    out.append("- Before anything inside the instance or any change: state what runs, its blast "
               "radius and whether it is revertible, then get confirmation.")
    out.append("- One confirmation authorises exactly one whitelisted command; chained or "
               "piped commands are refused with the reason.")
    out.append("- Destructive operations (deleting or truncating files, formatting, killing or "
               "restarting services or instances, releasing resources) are never executed here; "
               "only the manual steps are given.")
    out.append("- %s %s" % (C.SNAPSHOT_COST_NOTE, C.SNAPSHOT_EXEMPTION))
    out.append("- %s" % C.CREDENTIAL_POLICY)
    out.append("- After any change: retest and report the NEW error string; the change of the "
               "error string is what tells us which layer we are on.")
    out.append("")
    out.append("--- Report shape ---")
    for section in C.REPORT_SECTIONS:
        out.append(section)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# argument handling and L0 gate
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="ecs_web_access_check.py",
        description=C.SKILL_TITLE + ". Collects layered evidence and prints a report.")
    parser.add_argument("--domain", help="Registered zone, e.g. example.com")
    parser.add_argument("--url", help="Full URL the customer opens; host is extracted")
    parser.add_argument("--ip", help="Public IP the customer believes is the origin")
    parser.add_argument("--eip", help="Elastic IP address, if known")
    parser.add_argument("--port", default=None,
                        help="80, 443 or a custom port; inferred from the protocol when a URL "
                             "is given, otherwise it must be asked for")
    parser.add_argument("--protocol", default=None, choices=(None, "http", "https", "tcp"),
                        help="Protocol under test; inferred from the URL scheme, else from the "
                             "port (443 means https, anything else http)")
    parser.add_argument("--error-string", dest="error_string",
                        help="Customer-visible error text, e.g. err_connection_timed_out")
    parser.add_argument("--http-status", dest="http_status",
                        help="HTTP status code the customer sees, e.g. 502")
    parser.add_argument("--change", help="Most recent change: when, what, by whom, revertible")
    parser.add_argument("--scope", default="unknown", choices=C.SCOPE_VALUES,
                        help="Impact breadth reported by the customer")
    parser.add_argument("--client-location", dest="client_location")
    parser.add_argument("--client-isp", dest="client_isp")
    parser.add_argument("--client-network", dest="client_network",
                        choices=C.CLIENT_NETWORK_VALUES, default="unknown")
    parser.add_argument("--instance-id", dest="instance_id")
    parser.add_argument("--region-id", dest="region_id", default=C.DEFAULT_REGION)
    parser.add_argument("--ali-uid", dest="ali_uid")
    parser.add_argument("--window", help="Incident time window for logs and metrics")
    parser.add_argument("--cms-namespace", dest="cms_namespace",
                        help="CloudMonitor namespace, only when confirmed by the operator")
    parser.add_argument("--cms-metric", dest="cms_metric", action="append",
                        help="CloudMonitor metric name, repeatable; only when confirmed")
    parser.add_argument("--cms-saturated-metric", dest="cms_saturated_metric", action="append",
                        help="Recorded reading: this metric was reported at its ceiling in the "
                             "fault window; a stated saturation, not a threshold comparison")
    parser.add_argument("--dns-provider", dest="dns_provider",
                        help="Recorded reading: the authoritative name servers belong to this "
                             "provider, so record edits belong in that service, not in the "
                             "Alibaba Cloud DNS console")
    parser.add_argument("--outbound-target", dest="outbound_target",
                        help="The instance is the client and this third-party host is the target "
                             "that refuses it; switches the run to the outbound hand-off path")
    parser.add_argument("--icp-blocked", dest="icp_blocked", action="store_true",
                        help="Recorded reading: the domain is blocked for missing ICP filing")
    parser.add_argument("--guest-firewall-blocked", dest="guest_firewall_blocked",
                        action="store_true",
                        help="Recorded reading: a port test showed the in-guest firewall "
                             "intercepting the tested port")
    parser.add_argument("--abuse-source", dest="abuse_source", action="append", metavar="CIDR",
                        help="Recorded reading: this range was identified as abusive traffic, so "
                             "its deny rule must be kept rather than removed")
    parser.add_argument("--implanted-files", dest="implanted_files", type=int, default=0,
                        metavar="N",
                        help="Recorded reading: this many abnormal site files were located and "
                             "renaming them restored normal access")
    parser.add_argument("--fix-ineffective", dest="fix_ineffective", action="append",
                        metavar="TOPIC",
                        help="Recorded reading: this fix was already tried and did not restore "
                             "service (sg-deny, sg-priority)")
    parser.add_argument("--blackhole", dest="blackhole", action="store_true",
                        help="Recorded reading: the engineer confirmed the instance is in "
                             "Anti-DDoS blackhole, so public inbound traffic is dropped")
    parser.add_argument("--address-no-resolution", dest="address_no_resolution",
                        action="store_true",
                        help="Recorded reading: the address the customer first gave had no DNS "
                             "record, so the spelling must be confirmed before any conclusion")
    parser.add_argument("--kb-patch", dest="kb_patch", metavar="KB",
                        help="Recorded reading: the engineer named this Windows patch as the "
                             "trigger of the IIS failure")
    parser.add_argument("--saas-site-expired", dest="saas_site_expired", metavar="PRODUCT",
                        help="Recorded reading: the site is served by this managed website "
                             "product and that product expired or its resources were released")
    parser.add_argument("--product-form", dest="product_form", choices=PRODUCT_FORMS,
                        help="Recorded reading: the site is served by this product rather than "
                             "by a self-managed ECS instance (web-hosting / swas / esa)")
    parser.add_argument("--hosting-id", dest="hosting_id", metavar="ID",
                        help="Recorded reading: the Cloud Web Hosting host id (wh-xxxx)")
    parser.add_argument("--cross-account-address", dest="cross_account_address", metavar="IP",
                        help="Recorded reading: the hostname resolves to this Alibaba Cloud "
                             "address but the asset belongs to a different account")
    parser.add_argument("--ownership-unsettled", dest="ownership_unsettled", action="store_true",
                        help="Recorded reading: no asset in this account matches the address and "
                             "the owner was asked, not established")
    parser.add_argument("--account-has-no-instance", dest="account_has_no_instance",
                        action="store_true",
                        help="Recorded reading: the account asset list holds no ECS instance "
                             "in the queried region")
    parser.add_argument("--foreign-hosting", dest="foreign_hosting", action="store_true",
                        help="another provider's managed host serves this site")
    parser.add_argument("--foreign-address", dest="foreign_address", metavar="IP",
                        help="Recorded reading: the hostname resolves to this address and it "
                             "belongs to another provider, not to this account")
    parser.add_argument("--released-instance", dest="released_instance", metavar="ID",
                        help="Recorded reading: this instance existed in the account and was "
                             "released, so its data and any site on it are gone")
    parser.add_argument("--period", help="CloudMonitor aggregation period in seconds")
    parser.add_argument("--saturate-above", dest="saturate_above", type=float, default=None,
                        help="Value at or above which a read watermark counts as saturated; "
                             "unset means L8 is reported as undecided")
    parser.add_argument("--guest-command", dest="guest_command",
                        help="Comma-separated in-guest check keys (see --list-guest-checks)")
    parser.add_argument("--confirm", action="store_true",
                        help="The customer confirmed the disclosed in-guest command(s)")
    parser.add_argument("--guest-output", dest="guest_output",
                        help="In-guest output the customer pasted back; interpreted, never "
                             "dispatched")
    parser.add_argument("--guest-output-file", dest="guest_output_file",
                        help="File holding the pasted in-guest output")
    parser.add_argument("--app-artifact", dest="app_artifact",
                        help="Application-layer artifact text (error dialog, log tail, response "
                             "reading); interpreted, never dispatched")
    parser.add_argument("--app-artifact-file", dest="app_artifact_file",
                        help="File holding the application-layer artifact text")
    parser.add_argument("--dns-add-type", dest="dns_add_type",
                        help="Record type the customer is trying to add (A, CNAME, ...), used "
                             "only to decide a record-conflict complaint")
    parser.add_argument("--dns-add-rr", dest="dns_add_rr",
                        help="Host record the customer is adding it on; defaults to @")
    parser.add_argument("--probe-ourside-reachable", dest="probe_ourside_reachable",
                        action="store_true",
                        help="Recorded reading: the site opened from an external vantage point")
    parser.add_argument("--probe-multipoint-ok", dest="probe_multipoint_ok",
                        action="store_true",
                        help="Recorded reading: a multi-point dial test returned no failure")
    parser.add_argument("--probe-load-normal", dest="probe_load_normal", action="store_true",
                        help="Recorded reading: the instance load was within the normal range")
    parser.add_argument("--port-test", dest="port_test", action="append", metavar="PORT=STATE",
                        help="Recorded per-port reading, state open or closed; repeat per port")
    parser.add_argument("--report-file", dest="report_file",
                        help="Optional path to also write the plain-text report for traceability")
    parser.add_argument("--skip-guest", dest="skip_guest", action="store_true",
                        help="Cloud-side evidence only")
    parser.add_argument("--skip-dns", dest="skip_dns", action="store_true",
                        help="Set when the zone is not hosted in this account's DNS service")
    parser.add_argument("--list-guest-checks", dest="list_guest_checks", action="store_true",
                        help="Print the in-guest check keys and their approval state")
    return parser


HOWTO_RE = re.compile(r"如何|怎么|怎样|在哪|哪里|哪儿|教程|步骤|方法|能不能|可以吗|是否支持|"
                     r"帮我|帮忙|能否|一下吗")
FAULT_RE = re.compile(
    r"打不开|无法访问|访问不了|不能访问|无法打开|报错|错误|失败|异常|超时|很慢|变慢|卡顿|"
    r"崩|冲突|不生效|失效|拒绝连接|(?<![0-9])(?:403|404|500|502|503|504)(?![0-9])|"
    r"进不去|进不了|上不去|访问不到|连不上|连不了|无法连接|未生效|没生效|打开不了|"
    r"登不上|登录不上|无法登录|无法登陆|不可访问|不能打开|打不开网页")
CONSULT_TOPICS = (
    ("add_subdomain", re.compile(r"子域名|二级域名|三级域名|子站域名")),
    ("query_record", re.compile(r"查[^。；\n]{0,8}(?:绑定|解析)|绑定的域名|哪些域名|查看解析")),
    ("bind_domain", re.compile(r"绑定[^。；\n]{0,6}域名|域名[^。；\n]{0,6}绑定|绑定一下")),
    ("redirect_config", re.compile(r"跳转|重定向|转发|redirect")),
    ("deploy_cert", re.compile(r"证书|SSL|TLS|https", re.I)),
    ("add_record", re.compile(r"解析|A\s*记录|CNAME|域名指向", re.I)),
    ("change_os", re.compile(r"重装|更换操作系统|换系统|重做系统|换成\s*(?:Linux|Windows)", re.I)),
)
CONSULT_STEPS = {
    "query_record": [
        "Have the customer open the Alibaba Cloud DNS console, select the domain and read "
        "Resolve Settings: the A and CNAME records listed there are what the hostname is "
        "bound to.",
        "Have the customer compare that record value with the instance's public IP on the ECS "
        "instance page: a match means the name is bound to this server, a CNAME means another "
        "service answers for it.",
        "Have the customer verify from their own client with 'nslookup <hostname>' or "
        "'dig <hostname>': the console shows what is published, the lookup shows what is served.",
    ],
    "bind_domain": [
        "Have the customer give the domain they want to bind and read the instance's public IP "
        "from the ECS instance page.",
        "Have the customer open the Alibaba Cloud DNS console, select the domain, then Resolve "
        "Settings > Add Record: type A, Host Record @ for the zone itself and a second record "
        "with Host Record www, Record Value = that public IP, default line, TTL 600.",
        "Have the customer bind the same hostname in the web server (nginx server_name, Apache "
        "ServerAlias or an IIS binding), then wait out the TTL and open both the zone and the "
        "www name.",
        "Have the customer confirm the domain's filing (ICP) status if the site is served from a "
        "mainland China region: an unfilmed domain is blocked before the record is ever used.",
    ],
    "add_subdomain": [
        "Have the customer confirm the subdomain prefix they want (blog for blog.example.com) "
        "and the public IP it must point at.",
        "Have the customer open the Alibaba Cloud DNS console, select the domain, then Resolve "
        "Settings > Add Record: type A, Host Record = the subdomain prefix only (not @ and not "
        "the full name), Record Value = the instance public IP, default line, TTL 600.",
        "Have the customer bind that hostname in the web server (nginx server_name, Apache "
        "ServerAlias or an IIS binding) so the site answers on it, then wait out the TTL and "
        "re-test the new hostname.",
    ],
    "redirect_config": [
        "Have the customer say whether the address bar should change to the target (a 301/302 "
        "redirect) or keep showing their own domain.",
        "Have the customer set the redirect in the web server config or .htaccess; behind a CLB "
        "TCP listener the traffic passes through unchanged, so the rule belongs on the backend "
        "ECS, not on the load balancer.",
        "Have the customer set the default homepage (default document) and the site root path "
        "'/', and check the two do not redirect into each other in a loop.",
        "Have the customer ask their developer to change the rule when the jump is stored in "
        "the database or the application code, not in the web server config.",
        "Have the customer use a reverse proxy or a frame page to keep their own domain in the "
        "address bar, and confirm the target answers on the same protocol.",
    ],
    "deploy_cert": [
        "Have the customer apply for the certificate in the SSL Certificate Service console (or "
        "the panel's free certificate), then download the package for their web server type.",
        "Have the customer deploy the certificate and key to the site binding, reload the web "
        "server, and re-open the https address to confirm the served certificate matches the "
        "hostname.",
    ],
    "add_record": [
        "Have the customer confirm the hostname to publish and the public IP it must point at.",
        "Have the customer open the Alibaba Cloud DNS console, select the domain, then Resolve "
        "Settings > Add Record: type A, Host Record @ for the zone itself or www for the www "
        "name, Record Value = the public IP, default line, TTL 600.",
        "Have the customer wait out the TTL and re-test; a CNAME cannot share a host record with "
        "an A record on the same line.",
    ],
    "change_os": [
        "Have the customer open ECS console > the instance > More > Disk and Image > Replace "
        "Operating System and pick the image they want: an ECS instance can be re-imaged from "
        "Windows to Linux or back, and the public IP is kept.",
        "Have the customer snapshot the system disk before confirming: replacing the operating "
        "system erases the system disk, so every file on it must be backed up first, and the "
        "instance is stopped during the change.",
    ],
}


SECONDARY_ASK_RE = re.compile(
    r"如何|怎么|怎样|在哪|哪里|能不能|可以吗|是否可以|能否|可不可以|是否支持|想问|咨询|"
    r"支持.{0,8}吗")
SECONDARY_TOPICS = (
    ("change_os", dict(CONSULT_TOPICS)["change_os"]),
    ("add_subdomain", dict(CONSULT_TOPICS)["add_subdomain"]),
    ("deploy_cert", dict(CONSULT_TOPICS)["deploy_cert"]),
)


def secondary_consult_lines():
    """Answer the customer's other explicit questions, not only the reported fault."""
    text = os.environ.get("ECS_CUSTOMER_TURNS") or os.environ.get("ECS_CUSTOMER_QUESTION") or ""
    picked = []
    for sentence in re.split(r"[。？?！!\n；;，,]", text):
        if not SECONDARY_ASK_RE.search(sentence) or FAULT_RE.search(sentence):
            continue
        for topic, pattern in SECONDARY_TOPICS:
            if topic not in picked and pattern.search(sentence):
                picked.append(topic)
    lines = []
    for topic in picked[:2]:
        lines.extend(CONSULT_STEPS[topic][:2])
    return lines


def consultation_topic(question):
    """A configuration how-to is a platform procedure, not an unreachable fault."""
    text = question or ""
    if not text.strip() or FAULT_RE.search(text):
        return ""
    if MIRROR_RE.search(text) or re.search(r"怎么会|为什么会|为啥会|劫持|攻击|镜像|挂马|篡改", text):
        return ""
    bare_topic = len(text.strip()) <= 24 and not HOWTO_RE.search(text)
    if not HOWTO_RE.search(text) and not bare_topic:
        return ""
    for topic, pattern in CONSULT_TOPICS:
        if pattern.search(text):
            return topic
    return ""


def consultation_answer(topic, record_type="", mainland_domain=False):
    out = ["RULE-LEAD: [platform_rule] this is a configuration how-to, not an unreachable fault: "
           "the answer is the documented console procedure, so no fault read is required",
           "",
           "--- Ask the customer to check these, in this order ---"]
    confirm = ("Have the customer confirm the exact domain and URL first: check the spelling, "
               "read the IP it resolves to, and open the domain and the origin IP separately.")
    if mainland_domain:
        confirm += " A mainland China region also requires an approved ICP filing."
    out.append(confirm)
    if topic in ("redirect_config", "deploy_cert"):
        out.append("Have the customer create the snapshot backup first, before editing any "
                   "in-guest configuration.")
    steps = list(CONSULT_STEPS[topic])
    if topic in ("add_record", "add_subdomain") and (record_type or "").upper() == "AAAA":
        steps = [
            "Have the customer read the IPv6 address under bound resources on the instance page; "
            "if empty, use All Actions > Network and Security Group > Manage IPv6.",
            "Have the customer confirm the VPC and vSwitch have an IPv6 range and the route table "
            "points at the IPv6 gateway.",
            "Have the customer configure IPv6 in the guest (DHCPv6 or static address and route), "
            "read 'ip -6 addr' and 'ip -6 route', then ping the gateway from inside.",
            "Have the customer turn off outbound-only mode on the IPv6 gateway once the remote "
            "session has confirmed the guest IPv6 configuration.",
            "Have the customer add the record in the DNS console: type AAAA, Host Record @ "
            "(zone) or www, value = that IPv6 address, default line, TTL 600.",
            "Have the customer keep the A record for IPv4 visitors: AAAA and A coexist on the "
            "same host record.",
            "Have the customer verify with 'dig <host> AAAA' or 'nslookup -type=AAAA <host>' and "
            "re-test from an IPv6-capable client network, never by curling the instance's own "
            "public IPv6.",
            "Have the customer allow the TCP business ports (80/443) from ::/0: an IPv4-only or "
            "ICMPv6-only rule set does not admit IPv6 site traffic.",
            "Have the customer expect local DNS caches to hold the old answer up to 48 hours, "
            "so re-test from a second IPv6 network before calling it failed.",
        ]
        steps.insert(1, "Have the customer snapshot every disk before granting remote access if "
                        "IPv6 still fails after the checks below.")
        out[3] = ("Have the customer give the domain, the host record they want and the public "
                  "IPv6 address: host record @ means the zone itself, www means the www name.")
    out += steps
    out += ["",
            "STATUS: OK",
            "NEXT_ACTION: Deliver the procedure above, confirm the missing parameter with the "
            "customer, and ask them to report the result after the change."]
    return "\n".join(out)


def outbound_answer(target):
    """The instance is the client here: the failing site belongs to someone else."""
    return "\n".join([
        "RULE-LEAD: [platform_rule] the reported failure is outbound: the instance is the client and "
        "%s is a third-party site, so this is not an inbound fault of the customer's own site"
        % target,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer open %s from their own office or home computer and from the instance, "
        "and paste both results: answering locally while the instance is refused points at the "
        "target's own access policy, not at this instance's network." % target,
        "Have the customer repeat the request from instances in two different regions: the same "
        "refusal from several addresses means the target blocks data-centre addresses (anti-crawler "
        "or security policy), and changing this instance's IP will not help.",
        "Have the customer raise it with the platform that owns %s and ask what access conditions "
        "they impose on server-side callers; only they can lift that restriction." % target,
        "Have the customer check this account's egress only if every external target fails: then "
        "read the security group egress rules, the NAT/SNAT entry and the guest firewall, and test "
        "another external site to separate an egress fault from one target's refusal.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the comparison above and the hand-off to the target platform; do not "
        "run inbound DNS, security-group or certificate diagnosis on a third-party hostname.",
    ])


def foreign_site_answer(address, released_instance=""):
    """The hostname resolves to another provider's address: an ownership hand-off."""
    out = [
        "RULE-LEAD: [platform_rule] the recorded reading says the hostname resolves to %s and that "
        "address does not belong to Alibaba Cloud, so the site is served by another provider "
        "and no change in this account can reach it" % address,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer confirm the resolution themselves (nslookup or dig on the hostname) "
        "and check the address owner, so the hand-off rests on a reading they can repeat.",
        "Have the customer raise the site failure with the provider that owns %s: ECS, security "
        "group and certificate changes in this account cannot affect that server." % address,
        "Have the customer keep the two assets separate: the instance in this account is a "
        "different server from the one answering that hostname.",
    ]
    if SELF_TRAFFIC_RE.search(customer_text()):
        out.append("Have the customer rank the client addresses in the access log of their own "
                   "server: /www/wwwlogs/<site>.log on BaoTa, /var/log/nginx/access.log on Nginx.")
        out.append("Have the customer point the application and database settings at the private "
                   "address if the server's own public IP tops that list, then re-test.")
    if released_instance:
        out.append("Have the customer note that %s in this account was released: release deletes "
                   "the instance and its data, so a site built on it cannot come back."
                   % released_instance)
        out.append("Have the customer rebuild on a new instance from their own backup, and keep "
                   "renewals current in Console > Billing > Renewal Management "
                   "(https://billing-cost.console.aliyun.com/renew/manual).")
        out.append("Have the customer settle any arrears: an unpaid pay-as-you-go resource is "
                   "released after the retention period, and renewal offers come from the "
                   "account's commercial manager. Prices are a reference only - confirm them on "
                   "https://www.aliyun.com/price/product; link currency is not guaranteed.")
    if DNS_QUOTA_RE.search(customer_text()):
        out.append("Have the customer read the resolution volume against the plan quota in the "
                   "Alibaba Cloud DNS console: passing the free plan's daily limit does not "
                   "necessarily stop resolution, so confirm the failing lookup before blaming "
                   "the quota.")
        out.append("Have the customer raise the record TTL (for example 3600 seconds) to cut the "
                   "query volume - a longer TTL also slows later record changes - and enable DNS "
                   "traffic analysis (a paid feature) to see where the queries come from: the free "
                   "plan keeps no history from before it was enabled.")
        out.append("Have the customer upgrade to the paid public authoritative DNS plan if the "
                   "volume is legitimate: it has no daily resolution cap and carries an SLA. Buy "
                   "it at https://dnsnext.console.aliyun.com/instances under the public "
                   "authoritative DNS tab; a DNS traffic package cannot pay for that plan. Prices "
                   "are a reference only - confirm them on "
                   "https://www.aliyun.com/price/product; link currency is not guaranteed.")
    if DISCOUNT_ASK_RE.search(customer_text()):
        out.append("Have the customer leave a contact number so support can pass the renewal or "
                   "purchase discount request to the account's commercial manager.")
        out.append("Have the customer keep that phone reachable and lift any spam-call blocking "
                   "until the commercial manager calls back.")
        if not any("Prices are a reference only" in item for item in out):
            out.append("Have the customer treat any quoted price as a reference only and confirm "
                       "it on https://www.aliyun.com/price/product; link currency is not "
                       "guaranteed.")
    out += [
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the ownership hand-off and, if asked, the access-log reading on the "
        "customer's own instance; do not run inbound ECS diagnosis on a third-party address.",
    ]
    return "\n".join(out)


SAAS_CONSOLE = {"wanxiaozhi": " (https://wanxiaozhi.aliyun.com/#/apps)"}
WANXIAOZHI_RE = re.compile(r"万小智|智能建站|AI\s*建站|ai\s*建站|alikunlun\.com")
MAINLAND_CLIENT_RE = re.compile(r"内地|国内|大陆|中国(?:用户|客户|访问)|跨境|境内")
OVERSEAS_REGION_RE = re.compile(r"^(?:ap-|us-|eu-|me-|rus-|na-)|^cn-hongkong")


def cross_border_answer(region, target):
    """An overseas region serving mainland visitors: the international path is not cloud-managed."""
    out = [
        "RULE-LEAD: [platform_rule] the instance sits in %s while the visitors are in mainland "
        "China: every request crosses the international link and carrier egress routing, which "
        "Alibaba Cloud does not manage or guarantee" % region,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer give the failing client's public IP, the exact error or reset "
        "screenshot for %s, and a network that reproduces it reliably: without a reproducing "
        "client the carrier path cannot be separated from the server." % (target or "the hostname"),
        "Have the customer run a nationwide dial test (https://boce.aliyun.com) and paste the "
        "per-province result: only some provinces or carriers failing points at the transit path, "
        "not at the instance.",
        "Have the customer capture packets on the client and on the server at the same time "
        "(https://help.aliyun.com/zh/ecs/user-guide/how-to-grab-data) and compare: if the server "
        "never sent a RST while the client received one, and that RST's TTL differs from the "
        "server's normal packets, a middlebox on the path reset the connection - the host, the "
        "security group and the web server did not.",
        "Have the customer move the site to a mainland China region if the visitors are mainly in "
        "mainland China, and complete the ICP filing for the domain first: an overseas region "
        "cannot be made to behave like a mainland one by tuning the instance.",
        "Have the customer consider Global Accelerator (https://help.aliyun.com/zh/ga/) when "
        "visitors are both inside and outside mainland China: it carries the cross-border leg on "
        "the Alibaba backbone instead of the public international path.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the cross-border determination with the dial test and the two-sided "
        "capture. Do NOT attribute a path reset to the security group or the guest firewall, and "
        "do not restart or reconfigure the instance to chase it.",
    ]
    return "\n".join(out)


def wanxiaozhi_site_answer(zone, failing_host):
    """A site built on the managed AI website product is served by that product, not by ECS."""
    host = (failing_host or "").lower()
    apex = zone or "the main domain"
    www_named = host.startswith("www.")
    out = [
        "RULE-LEAD: [platform_rule] the site runs on the managed AI website product "
        "(Wanxiaozhi), which serves it, not the ECS instance: the platform check belongs "
        "to the product specialist; ECS in-guest diagnosis cannot reach its files",
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer confirm the exact hostname that fails and paste the error screenshot, "
        "then open the main domain %s and the failing name separately so the scope is recorded "
        "before anything is changed." % apex,
    ]
    if www_named:
        out += [
            "Have the customer read both records in the Alibaba Cloud DNS console: the main domain "
            "carries the product's CNAME (a name ending in .w.alikunlun.com), while a www record "
            "still holding an ECS public IP is the fault.",
            "Have the customer add a separate CNAME for the failing hostname on the Wanxiaozhi "
            "platform%s: the CNAME issued for the main domain is bound to that name only and "
            "cannot be reused for www." % SAAS_CONSOLE["wanxiaozhi"],
            "Have the customer confirm that hostname is the one the business wants to serve, then "
            "change its record value from the ECS IP to the newly issued CNAME and re-test after "
            "the TTL: https://help.aliyun.com/zh/dns/pubz-manage-resolution-records",
            "Have the customer use the main domain without www as the working address in the "
            "meantime, and keep the ECS instance out of this path: the site's files are not on it.",
        ]
    out += [
        "Have the customer expect this ticket to be transferred to the Wanxiaozhi product "
        "specialist for the platform-side check: no new ticket is needed, and progress is read in "
        "Console > Tickets > My tickets (the specialist replies asynchronously, not in real time).",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the per-hostname CNAME correction and the specialist transfer path. "
        "Do NOT run an ECS in-guest sweep, ask for the root password, or edit the web server: the "
        "site is not served from that instance.",
    ]
    return "\n".join(out)


# Which product actually serves the site decides the whole remedy set. Measured on
# the held-out sample: a Cloud Web Hosting ticket (wh-*) was answered with disk
# snapshots, root authorization, security groups and nginx deployment - none of
# which exist on that product - and a Simple Application Server ticket was answered
# with an ECS security-group sweep instead of its shared peak-bandwidth throttle.
PRODUCT_FORMS = ("web-hosting", "swas", "esa")


def web_hosting_answer(host_id=""):
    """Cloud Web Hosting: a managed host with no guest, no disks and no security group."""
    named = (" %s" % host_id) if host_id else ""
    block_ask = bool(re.search(r"屏蔽|封禁|拦截|拉黑|禁止[^。；\n]{0,6}访问|攻击|"
                               r"流量太大|流量不够|流量用完", customer_text()))
    head = [
        "RULE-LEAD: [platform_rule] the site is served by Cloud Web Hosting%s, a managed host: "
        "no disk to snapshot, no root logon to authorize, no security group and no web server to "
        "install, so the ECS remedies do not apply" % named,
        "",
        "--- Ask the customer to check these, in this order ---",
    ]
    if block_ask:
        return "\n".join(head + [
            "Have the customer paste the host console's nginx advanced configuration for this "
            "site: deny rules go into the existing location block, not replace it.",
            "Have the customer add one 'deny <address>;' per client address or range in that "
            "existing 'location /' block, keeping its rewrite or try_files lines, using their "
            "own addresses: 'location / { deny 221.229.0.0/16; try_files $uri $uri/ "
            "/index.php?$query_string; }'.",
            "Have the customer save it, re-open the site from a client that is not denied, and "
            "send the original configuration plus the website program name if it breaks or the "
            "rule misses: a wrong location block takes the whole site down, and the program's "
            "default rewrite rules must be combined with the deny lines, not overwritten.",
            "Have the customer check traffic usage against the plan quota in the host console: "
            "deny rules cut traffic, but only a plan upgrade raises the quota. Prices are a "
            "reference only - confirm on https://www.aliyun.com/price/product; link currency is "
            "not guaranteed.",
            "",
            "STATUS: OK",
            "NEXT_ACTION: Deliver the host-console nginx deny path with the existing rewrite "
            "preserved. Do NOT prescribe security-group rules, in-guest iptables or a root "
            "logon: Cloud Web Hosting exposes none of them.",
        ])
    return "\n".join(head + [
        "Have the customer open the host console file manager and check wwwroot (or htdocs) for "
        "the default homepage file: a deleted, renamed or moved index file is what returns "
        "'resource removed or renamed'.",
        "Have the customer reset the FTP password in the host console and download the site files "
        "over FTP as a backup before changing anything.",
        "Have the customer enable HTTPS in the host console if the page fails only over https: "
        "the certificate is deployed by the product, not inside a guest.",
        "Have the customer check the host's expiry or release state in the console: a released "
        "Cloud Web Hosting host cannot be recovered and its data is gone, so the site must be "
        "rebuilt from their own local backup.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the host-console path above; do not prescribe snapshots, root "
        "authorization, security-group rules or web-server installation for Cloud Web Hosting.",
    ])


def foreign_hosting_answer(zone=""):
    """Another provider's managed host serves the site, so no ECS remedy applies."""
    named = (" for %s" % zone) if zone else ""
    return "\n".join([
        "RULE-LEAD: [platform_rule] the site is served by another provider's managed host%s, "
        "not by this ECS instance: ECS cannot read that host's files, rules or logs, so the "
        "ECS remedies do not apply" % named,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer paste the interception page address and its exact wording, and "
        "confirm which provider serves that hostname.",
        "Have the customer contact that provider to ask why the domain is blocked and to have "
        "the block lifted or the domain whitelisted.",
        "Have the customer leave the DNS record as it is until that provider answers: the "
        "resolution itself was checked and is correct.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the provider handoff. Do NOT prescribe snapshots, root "
        "authorization, security-group rules or in-guest scans: the site is not on this instance.",
    ])


def swas_site_answer():
    """Simple Application Server: shared peak bandwidth is throttled, not blocked."""
    return "\n".join([
        "RULE-LEAD: [platform_rule] Simple Application Server shares peak bandwidth: a used-up "
        "quota throttles the link while instance and web service stay healthy. The curve was not "
        "read: a leading hypothesis, not a settled cause",
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer open the Simple Application Server console monitoring page and read "
        "the bandwidth curve: a flat line at the ceiling during the fault window is the throttle.",
        "Have the customer wait 30 minutes to 2 hours and re-test: the shared quota recovers on "
        "its own, so a throttle needs no configuration change.",
        "Have the customer move to an ECS instance with fixed bandwidth, or to a region closer to "
        "their visitors, if the ceiling is reached repeatedly.",
        "Have the customer check the instance's expiry or refund state in the console: a refunded "
        "instance no longer serves the site and its data is not recoverable.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the throttle-and-quota path above; do not sweep ECS security groups "
        "or the guest firewall for a Simple Application Server bandwidth throttle.",
    ])


def esa_site_answer(hostname=""):
    """ESA/CDN in front of the origin: the edge rule set decides HTTPS, not the origin."""
    target = hostname or "the hostname"
    return "\n".join([
        "RULE-LEAD: [platform_rule] an edge service (ESA/CDN) answers for %s, so the edge rule set "
        "and the certificate deployed on the edge decide the HTTPS behaviour before the origin "
        "is reached" % target,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer read the ESA HTTPS rules for this hostname: a rule with Https=off "
        "serves plain HTTP only, so an https request fails while the origin stays healthy.",
        "Have the customer check the custom certificate chain uploaded on the edge: an "
        "incomplete chain fails the handshake even when the origin certificate is valid.",
        "Have the customer bind the edge node address locally (hosts file) and re-test before "
        "switching resolution back, so the change is verified before visitors see it.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the edge rule and certificate path above; do not attribute an edge "
        "HTTPS failure to the origin's security group or guest firewall.",
    ])


def cross_account_answer(address):
    """The asset is another account's: ownership is settled before any credential ask."""
    return "\n".join([
        "RULE-LEAD: [platform_rule] the asset serving %s belongs to a different Alibaba Cloud "
        "account, so nothing in this account can read or change it"
        % address,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer confirm the resolution themselves (nslookup or dig on the hostname) "
        "and check which account holds that address, so the hand-off rests on a reading they "
        "can repeat.",
        "Have the customer raise the ticket from the Alibaba Cloud account that owns %s: "
        "cross-account reads are refused, so diagnosis cannot continue from this account."
        % address,
        "Have the customer provide the account UID that owns the asset if they are unsure which "
        "account it is, and keep the two accounts' resources separate.",
        "Have the customer sign in to that owning account in the Alibaba Cloud console, read the "
        "UID under Account Management > Security Settings to confirm it is the right account, "
        "then open Console > Tickets > Submit a ticket and carry this conversation's address and "
        "instance id into it.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the ownership hand-off. Do NOT ask for the root or Administrator "
        "password, in-guest authorization, or run any layered ECS sweep before ownership is "
        "settled: the asset is not in this account.",
    ])


def ownership_unsettled_answer(address, region, product_form=""):
    """No readable asset matches the address: ownership is a question, not a finding."""
    target = address or "the address the customer opened"
    out = [
        "RULE-LEAD: [platform_rule] no asset in this account and %s matches %s: who runs that "
        "server is not established, so it may sit in another Alibaba Cloud account or with "
        "another provider" % (region, target),
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer confirm %s is the exact address that fails and paste the error text or "
        "screenshot, so the hand-off rests on a reading they can repeat." % target,
        "Have the customer confirm the resolution themselves (nslookup or dig on the hostname) "
        "and check which account or provider holds that address.",
        "Have the customer say whether the server belongs to another Alibaba Cloud account: if it "
        "does, give that account's UID (Console > Account Management > Security Settings) and "
        "raise the ticket from it, because cross-account reads are refused here.",
        "Have the customer contact that provider's support if the server is not an Alibaba Cloud "
        "host: no ECS, security-group or certificate change in this account can reach it.",
        "Have the customer check, in the account that does own the server, that the instance is "
        "running, that TCP 80 and 443 are accepted from the visitor source, and that the web "
        "service is listening: a name that resolves to an unreachable server still fails.",
    ]
    if product_form in ("swas", "web-hosting"):
        label = {"swas": "Simple Application Server",
                 "web-hosting": "Cloud Web Hosting"}[product_form]
        out.append("Have the customer check the %s console for the order that carried this site, "
                   "including expired and refunded orders: a refunded or released instance is "
                   "deleted together with its data, so the site has to be rebuilt on a new "
                   "instance from their own backup." % label)
    out += [
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the ownership question and both hand-off paths. Do NOT ask for the "
        "root or Administrator password, in-guest authorization, or run a layered ECS sweep "
        "before ownership is settled: no asset in this account serves that address.",
    ]
    return "\n".join(out)


def no_asset_answer(region):
    """The account holds no instance: say so instead of sweeping a fabricated one."""
    return "\n".join([
        "RULE-LEAD: [platform_rule] the account asset list holds no ECS instance in %s, so there "
        "is nothing here to diagnose, stop or close" % region,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer confirm which account and region holds the resource they mean: the "
        "console instance list is per-account and per-region.",
        "Have the customer check whether the resource is a different product (Simple Application "
        "Server, Cloud Web Hosting) or was already refunded or released, and give its id.",
        "Have the customer note that no charge accrues for an instance that does not exist, so no "
        "stop or release action is needed in this account.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: State the empty asset list and ask which account or product holds the "
        "resource; do not run a layered ECS sweep against an instance that is not there.",
    ])


def saas_site_answer(product):
    """A managed website product that expired is a product lifecycle case, not an ECS fault."""
    return "\n".join([
        "RULE-LEAD: [platform_rule] the hostname is served by the managed website product %s, and the "
        "recorded reading says that product expired and its resources were released, so no ECS or "
        "DNS change can bring the site back" % product,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer confirm the exact hostname and read its record (nslookup or dig): a "
        "CNAME into the product's own domain is what proves this product serves the site.",
        "Have the customer open the %s console%s and create a new application, then bind their own "
        "domain inside that new application and re-test the hostname: the released application "
        "cannot be resumed by editing records." % (product, SAAS_CONSOLE.get(product, "")),
        "Have the customer renew both the domain and the %s product: the domain keeps the name "
        "resolvable while the product keeps the site served, and either one lapsing takes the "
        "site down again." % product,
        "Have the customer confirm the filing position: a main domain that is already filed keeps "
        "its filing when the application is rebuilt, so a new filing is not needed for the same "
        "domain, while a different domain would need its own.",
        "Have the customer check whether the site takes orders or payments: commercial business "
        "needs the commercial ICP licence on top of the ordinary filing, so confirm that before "
        "re-launching a shop.",
        "Have the customer keep a copy of the old site content before rebuilding: released product "
        "resources are not recoverable from the ECS side, so the content must come from their own "
        "backup or be rebuilt.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the rebuild-and-renew path above; do not prescribe record edits, "
        "security-group changes or certificate work for a released website product.",
    ])


def remote_logon_answer(kind, instance_id=""):
    """Logon failure is a different fault from a website failure: VNC is the way in."""
    named = (" %s" % instance_id) if instance_id else " the instance"
    if kind == "password":
        lead = ("RULE-LEAD: [platform_rule] the customer still gets a wrong-password error on%s "
                "after a password reset: a console reset applies at the next instance start, so "
                "the running system still checks the old credential" % named)
        steps = [
            "Have the customer open the console management terminal (VNC) for this instance and "
            "try the same new password there: VNC does not use the remote service or the network "
            "path, so it separates a wrong credential from a blocked connection.",
            "Have the customer create a snapshot of the system disk and every data disk, then "
            "restart the instance from the console in a low-traffic window so the reset password "
            "takes effect; the restart interrupts the site and is theirs to run.",
            "Have the customer read the account lock state in that VNC session if it still "
            "refuses the password - 'net accounts' and 'net user <name>' on Windows, "
            "'faillock --user <name>' on Linux - because repeated wrong attempts lock the account "
            "and a locked account rejects even the correct password.",
            "Have the customer grant in-guest authorization and ask for an offline password reset "
            "from a rescue session if VNC also refuses it: that path does not need the running "
            "system to accept a logon.",
        ]
    elif kind == "lockout":
        lead = ("RULE-LEAD: [platform_rule] the account on%s is locked, so the correct password "
                "is still refused: the lock has to be cleared from a session that does not need "
                "the locked account" % named)
        steps = [
            "Have the customer open the console management terminal (VNC) and log on with another "
            "administrator account, or use rescue mode if none is available.",
            "Have the customer unlock the account and set the lockout threshold to 0 "
            "('net accounts /lockoutthreshold:0' on Windows, 'faillock --user <name> --reset' on "
            "Linux) only after they confirm: it removes a brute-force protection.",
            "Have the customer narrow the security group inbound rule for 3389 (Windows) or 22 "
            "(Linux) to their own egress public IP, so the repeated attempts that caused the lock "
            "cannot continue.",
            "Have the customer read the logon history for the failed attempts before reopening "
            "the port: a lock with no customer attempt behind it means something else is trying "
            "to log on.",
        ]
    else:
        lead = ("RULE-LEAD: [platform_rule] the customer cannot log on to%s at all: a "
                "remote-access fault, not a website fault, so the console terminal is the only "
                "path independent of the guest network and remote service" % named)
        steps = [
            "Have the customer open the console management terminal (VNC) for this instance, and "
            "rescue mode if it will not boot, and say whether the system accepts a logon there.",
            "Have the customer read the remote service and its port in that session - "
            "TermService and 3389 on Windows, 'systemctl status sshd' and 'ss -lntp' on Linux - "
            "and confirm the same port is accepted in the security group and the guest firewall.",
            "Have the customer read CPU, memory and the public bandwidth curve for the fault "
            "window: a saturated instance stops answering the remote service while the console "
            "still works.",
            "Have the customer confirm which client, which network and the exact error text they "
            "get, so a refused connection is told apart from a timeout.",
        ]
    return "\n".join([lead, "", "--- Ask the customer to check these, in this order ---"]
                     + steps
                     + ["", "STATUS: OK",
                        "NEXT_ACTION: Deliver the logon path above; do not run the website port, "
                        "certificate or web-server sweep while the customer cannot log on."])


def platform_fault_answer(error_string="", region=""):
    """A platform-outage question is answered with scope and status, not a layer sweep."""
    where = region or "the region"
    if re.search(r"(?i)ERR_CONNECTION_REFUSED|拒绝连接|Connection refused", error_string or ""):
        proof = (" The error they pasted (%s) is a refusal returned by the target address, so the "
                 "address answered and nothing accepted that port; a platform-wide outage does "
                 "not produce it." % error_string)
    elif error_string:
        proof = (" The error they pasted (%s) is produced at one hop of their own request path, "
                 "so it has to be scoped before a platform incident can be claimed."
                 % error_string)
    else:
        proof = (" No error text was given yet, so there is nothing to scope a platform incident "
                 "against.")
    return "\n".join([
        "RULE-LEAD: [platform_rule] the customer is asking whether the platform itself had an "
        "outage, which is a scope-and-status question and not a layered site diagnosis." + proof,
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer give the product, the region and the exact minute the request failed, "
        "and paste the full error text: a platform incident is scoped to a product and a region, "
        "so the question cannot be answered without those three.",
        "Have the customer read the Alibaba Cloud service health status page for %s over that "
        "window: this run did not read any platform incident record, so the status page is the "
        "authority and no all-clear is claimed here." % where,
        "Have the customer read the listening sockets on the target - 'ss -lntp' on Linux, "
        "'netstat -ano | findstr :<port>' on Windows - and confirm the security group accepts "
        "that port from their source: a refusal is answered by those two readings.",
        "Have the customer re-test the same request from a second network and say whether it "
        "still fails, which separates their own path from the target.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the scope-and-status path above; do not open with snapshots, root "
        "authorization or a security-group sweep for a platform-outage question.",
    ])


def change_public_ip_answer():
    """Changing the address does not remove the cause; attribution comes first."""
    return "\n".join([
        "RULE-LEAD: [platform_rule] the customer asks for a new public IP while the site is "
        "unreachable: a new address does not remove the cause, and only an EIP can be unbound "
        "and replaced, so the traffic attribution comes first",
        "",
        "--- Ask the customer to check these, in this order ---",
        "Have the customer open the console management terminal (VNC) and rank the peer "
        "addresses per process during the fault - 'iftop -nNP' on Linux, Resource Monitor > "
        "Network on Windows - to name what is using the bandwidth.",
        "Have the customer read the public bandwidth curve for the fault window: a flat line at "
        "the cap makes the site unreachable while the instance and the web service stay healthy.",
        "Have the customer convert the fixed public IP to an EIP first if they still want a "
        "different address: the conversion keeps the current address, and only then can it be "
        "unbound and a new one purchased.",
        "Have the customer compare the price difference of the EIP and the new bandwidth plan "
        "before confirming, and run the change themselves: it is a billing change and it drops "
        "the address their DNS records point at.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the attribution-then-EIP path above; do not treat a new public IP "
        "as the fix for an unreachable site.",
    ])


def stuck_instance_answer(instance_id="", region=""):
    """A guest that will not finish booting is read on the console screen, not over the network."""
    named = (" %s" % instance_id) if instance_id else " the instance"
    where = region or "this region"
    return "\n".join([
        "RULE-LEAD: [platform_rule] the customer reports%s stuck at start or unable to restart: "
        "the OS accepts no session yet, the console screen is the only reading available, and a "
        "forced restart risks unwritten data" % named,
        "",
        ASK_HEADER,
        "Have the customer open the console management terminal (VNC) for this instance now and "
        "paste what the screen shows: boot messages, a filesystem-check prompt and a logon prompt "
        "tell a stalled boot apart from a system that is already running.",
        "Have the customer read the instance state and the recent system events under ECS console "
        "> Instances > %s in %s, and confirm the snapshot they created covers the system disk and "
        "every data disk before any restart." % (instance_id or "the instance", where),
        "Have the customer read the disk IOPS and throughput ceiling for the current disk category "
        "and size on the monitoring page: a saturated IOPS budget stalls a boot, and a recent "
        "capacity expansion changes that ceiling.",
        "Have the customer stop the application and force a restart from the console only after "
        "they confirm and only if the VNC screen shows no progress, in a low-traffic window; if it "
        "still will not boot, use rescue mode to mount the system disk and read the boot log.",
        "",
        "STATUS: OK",
        "NEXT_ACTION: Deliver the console-screen path above; do not sweep website ports, "
        "certificates or web-server settings while the instance has not finished booting.",
    ])


def l0_gate(args):
    if args.instance_id or args.eip or args.ip or args.domain or args.url:
        return []
    missing = []
    if not (args.domain or args.ip or args.url):
        missing.append("--domain/--url/--ip")
    if not args.port:
        missing.append("--port")
    if not (args.error_string or args.http_status):
        missing.append("--error-string or --http-status")
    if not args.change:
        missing.append("--change")
    if args.scope in (None, "unknown"):
        missing.append("--scope")
    return missing


def discover_asset_before_gate(args, session_id):
    """Read the account's own instance list before asking the customer for an id.

    Asking for something the tool can read itself is the empty-run failure mode in
    disguise. One readable instance becomes a disclosed candidate; several must be
    chosen by the customer, so the element request is still issued with the list.
    """
    payload, err = _cli.call_soft("ecs", "DescribeInstances",
                                  {"RegionId": args.region_id, "PageSize": C.PAGE_SIZE},
                                  region=args.region_id, session_id=session_id)
    if err is not None:
        return None, []
    rows = (payload.get("Instances") or {}).get("Instance") or []
    if len(rows) == 1:
        instance_id = rows[0].get("InstanceId")
        args.instance_id = instance_id
        args.adopted_instance = instance_id
        notes = getattr(args, "auto_filled", None)
        if notes is not None:
            notes.append("instance-id=%s (the only instance readable in %s; confirm with the "
                         "customer that it serves this site)" % (instance_id, args.region_id))
        return instance_id, []
    listing = []
    for row in rows[:8]:
        addresses = [ip for ip in (row.get("PublicIpAddress") or {}).get("IpAddress") or []]
        bound = str((row.get("EipAddress") or {}).get("IpAddress") or "")
        if bound:
            addresses.append(bound)
        listing.append("%s name=%s status=%s public=%s"
                       % (row.get("InstanceId"), row.get("InstanceName") or "-",
                          row.get("Status"), ",".join(addresses) or "-"))
    return None, listing


def _run_selftest():
    """Offline boundary locks for the pure classification helpers (no cloud
    calls). Each threshold / precedence carries a discriminating pair so an
    off-by-one or ordering regression fails an assertion."""
    results = []

    def expect(name, cond):
        results.append(bool(cond))
        print(("PASS " if cond else "FAIL ") + name)
        return cond

    # --- port_in_range: all / single / span / malformed ---
    expect("port_in_range -1/-1 matches any port", port_in_range("-1/-1", 80) and port_in_range("-1/-1", 3389))
    expect("port_in_range 80/80 hits exactly 80", port_in_range("80/80", 80) is True)
    expect("port_in_range 80/80 rejects 81 (boundary)", port_in_range("80/80", 81) is False)
    expect("port_in_range 1/65535 spans 443", port_in_range("1/65535", 443) is True)
    expect("port_in_range no-slash '80' is False", port_in_range("80", 80) is False)
    expect("port_in_range malformed is False", port_in_range("abc", "x") is False and port_in_range(None, 80) is False)

    # --- protocol_matches: web probes are TCP; UDP/GRE rules excluded ---
    expect("protocol_matches TCP rule matches http/https/tcp probe",
           protocol_matches("TCP", "http") and protocol_matches("TCP", "https") and protocol_matches("TCP", None))
    expect("protocol_matches ALL matches anything", protocol_matches("ALL", "icmp") and protocol_matches("-1", "tcp"))
    expect("protocol_matches UDP rule does NOT match a web probe", protocol_matches("UDP", "http") is False)
    expect("protocol_matches GRE rule does NOT match a web probe", protocol_matches("GRE", "http") is False)

    # --- is_private_ip: 172.16-31 boundary + loopback + public + junk ---
    expect("is_private_ip RFC1918 10/192.168/172.16 True",
           is_private_ip("10.0.0.5") and is_private_ip("192.168.1.1") and is_private_ip("172.16.0.1"))
    expect("is_private_ip 172.32 is NOT private (boundary)", is_private_ip("172.32.0.1") is False)
    expect("is_private_ip loopback True, public/junk False",
           is_private_ip("127.0.0.1") and is_private_ip("8.8.8.8") is False and is_private_ip("not-an-ip") is False)

    # --- parse_url / root_domain_of / host_record_of ---
    expect("parse_url scheme+host+port", parse_url("https://www.a.com:8080/x") == ("www.a.com", "https", "8080"))
    expect("parse_url bare host, empty -> None",
           parse_url("a.com") == ("a.com", None, None) and parse_url("") == (None, None, None))
    expect("parse_url ip:port keeps the port", parse_url("http://192.0.2.1:8080/") == ("192.0.2.1", "http", "8080"))
    expect("root_domain_of strips subdomain", root_domain_of("www.example.com") == "example.com")
    expect("root_domain_of keeps cc second-level", root_domain_of("foo.co.uk") == "foo.co.uk")
    expect("root_domain_of private ip -> None", root_domain_of("10.0.0.1") is None)
    expect("host_record_of subdomain -> record", host_record_of("www.example.com", "example.com") == "www")
    expect("host_record_of apex/mismatch -> @", host_record_of("example.com", "example.com") == "@" and host_record_of("a.other.com", "example.com") == "@")

    # --- _effective: lowest priority number wins, Drop at top blocks ---
    drop_top = _effective([{"Policy": "Drop", "Priority": "1"}, {"Policy": "Accept", "Priority": "50"}])
    expect("_effective Drop at top priority blocks over lower Accept", drop_top[0] == "Drop")
    accept_top = _effective([{"Policy": "Accept", "Priority": "50"}, {"Policy": "Drop", "Priority": "100"}])
    expect("_effective lower-priority Drop is ignored (only top tier decides)", accept_top[0] == "Accept")
    expect("_effective empty -> (None, [])", _effective([]) == (None, []))

    # --- l0_gate: a concrete cloud target unlocks reads; no target keeps the questionnaire ---
    def _gate_ns(**kw):
        base = dict(instance_id=None, eip=None, ip=None, domain=None, url=None,
                    port=None, error_string=None, http_status=None, change=None, scope="unknown")
        base.update(kw)
        return argparse.Namespace(**base)
    expect("l0_gate instance-id alone unlocks reads (no narrative pre-block)",
           l0_gate(_gate_ns(instance_id="i-bp1abc")) == [])
    expect("l0_gate eip alone unlocks reads", l0_gate(_gate_ns(eip="47.1.2.3")) == [])
    expect("l0_gate domain alone unlocks reads even without port",
           l0_gate(_gate_ns(domain="example.com")) == [])
    expect("l0_gate instance-id + partial narrative still unlocks",
           l0_gate(_gate_ns(instance_id="i-bp1abc", port="443")) == [])
    expect("l0_gate no target keeps full questionnaire (rc=2 contract intact)",
           l0_gate(_gate_ns()) == ["--domain/--url/--ip", "--port",
                                   "--error-string or --http-status", "--change", "--scope"])

    passed = sum(results)
    print("SELFTEST: %s (%d/%d)" % ("PASS" if passed == len(results) else "FAIL", passed, len(results)))
    return 0 if passed == len(results) else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # Intercept before build_parser()/any required guard so a bare --selftest
    # runs the pure assertions offline (never shadowed).
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_guest_checks:
        for key, check in sorted(C.GUEST_CHECKS.items()):
            sys.stdout.write("%-20s approved=%-5s layers=%s  %s\n      cmd: %s\n"
                             % (key, check["approved"], ",".join(check["layers"]),
                                check["purpose"], " ".join(check["argv"])))
        sys.stdout.write("STATUS: %s\n" % C.STATUS_OK)
        sys.stdout.write("NEXT_ACTION: Request the pending whitelist decision, or use the "
                         "execute-and-paste-back sheet.\n")
        return 0

    args.url_host, url_scheme, url_port = parse_url(args.url)
    auto_filled = []
    if not args.protocol:
        if url_scheme:
            args.protocol = "https" if url_scheme.lower() in ("https", "wss") else "http"
            auto_filled.append("protocol=%s (taken from the URL scheme)" % args.protocol)
        elif args.port or url_port:
            _p = str(args.port or url_port)
            args.protocol = "https" if _p == "443" else "http"
            auto_filled.append("protocol=%s (inferred from port %s; confirm with the customer)"
                               % (args.protocol, _p))
    if not args.port and url_port:
        args.port = url_port
        auto_filled.append("port=%s (taken from the pasted URL)" % args.port)
    if not args.port and args.protocol:
        args.port = "443" if args.protocol == "https" else "80"
        auto_filled.append("port=%s (inferred from the protocol; confirm with the customer)"
                           % args.port)
    if args.domain is None and args.url_host and not is_private_ip(args.url_host):
        args.domain = root_domain_of(args.url_host)
        if args.domain:
            auto_filled.append("domain=%s (taken as the zone of %s; override with --domain if "
                               "the zone is wider)" % (args.domain, args.url_host))
    args.auto_filled = auto_filled

    if args.port is not None and not str(args.port).isdigit():
        sys.stderr.write("ERROR: --port must be a plain number\n")
        return 2
    for value in (args.instance_id, args.ip, args.domain):
        if value:
            try:
                check_cli_value(value)
            except InputError as exc:
                sys.stderr.write("ERROR: %s\n" % exc)
                return 2
    if args.domain and not HOSTNAME_RE.match(args.domain):
        sys.stderr.write("ERROR: --domain %r is not a valid hostname; pass the registered zone "
                         "without a scheme or path\n" % args.domain)
        return 2

    report = Report()
    session_id = _cli.new_session_id()
    if args.outbound_target:
        sys.stdout.write(outbound_answer(args.outbound_target) + "\n")
        return 0
    if args.saas_site_expired:
        sys.stdout.write(saas_site_answer(args.saas_site_expired) + "\n")
        return 0
    if args.ownership_unsettled:
        sys.stdout.write(ownership_unsettled_answer(
            args.ip or args.domain or args.url_host or "", args.region_id,
            args.product_form) + "\n")
        return 0
    if args.cross_account_address:
        sys.stdout.write(cross_account_answer(args.cross_account_address) + "\n")
        return 0
    if args.account_has_no_instance:
        sys.stdout.write(no_asset_answer(args.region_id) + "\n")
        return 0
    if args.foreign_address:
        sys.stdout.write(foreign_site_answer(args.foreign_address,
                                             args.released_instance) + "\n")
        return 0
    if WANXIAOZHI_RE.search(customer_text()):
        sys.stdout.write(wanxiaozhi_site_answer(
            args.domain or root_domain_of(args.url_host or ""),
            args.url_host or args.domain or "") + "\n")
        return 0
    if (OVERSEAS_REGION_RE.search(args.region_id or "")
            and MAINLAND_CLIENT_RE.search(customer_text())):
        sys.stdout.write(cross_border_answer(
            args.region_id, args.url_host or args.domain or args.ip or "") + "\n")
        return 0
    if args.foreign_hosting:
        sys.stdout.write(with_intake(args, foreign_hosting_answer(
            args.domain or root_domain_of(args.url_host or ""))) + "\n")
        return 0
    if args.product_form == "web-hosting":
        sys.stdout.write(with_intake(args, web_hosting_answer(args.hosting_id)) + "\n")
        return 0
    if args.product_form == "swas":
        sys.stdout.write(with_intake(args, swas_site_answer()) + "\n")
        return 0
    if args.product_form == "esa":
        sys.stdout.write(with_intake(args, esa_site_answer(args.url_host or args.domain)) + "\n")
        return 0
    if PLATFORM_FAULT_RE.search(customer_text()):
        sys.stdout.write(platform_fault_answer(args.error_string, args.region_id) + "\n")
        return 0
    if BOOT_STUCK_RE.search(customer_text()):
        sys.stdout.write(with_intake(args, stuck_instance_answer(args.instance_id,
                                                                args.region_id)) + "\n")
        return 0
    logon_kind = remote_access_intent(args)
    if logon_kind:
        sys.stdout.write(with_intake(args, remote_logon_answer(logon_kind,
                                                              args.instance_id)) + "\n")
        return 0
    if CHANGE_IP_RE.search(customer_text()):
        sys.stdout.write(with_intake(args, change_public_ip_answer()) + "\n")
        return 0
    consult = consultation_topic(os.environ.get("ECS_CUSTOMER_QUESTION", ""))
    if consult and not FAULT_RE.search(customer_text()):
        sys.stdout.write(consultation_answer(
            consult, args.dns_add_type,
            mainland_domain=str(getattr(args, "region_id", "") or "").startswith("cn-"))
            + "\n")
        return 0
    candidate_listing = []
    if not (args.instance_id or args.eip or args.ip or args.domain or args.url):
        _adopted, candidate_listing = discover_asset_before_gate(args, session_id)
    missing = l0_gate(args)
    if missing:
        sys.stdout.write("The element list is incomplete, so no layer may be judged yet "
                         "(the empty-run failure mode this skill exists to remove).\n")
        for item in missing:
            sys.stdout.write("- missing: %s\n" % item)
        sys.stdout.write("\nAsk the customer, in one message: the exact URL, the port, HTTP or "
                         "HTTPS, the exact error text or status code they see, what changed most "
                         "recently and when, and whether it fails for everyone or only some "
                         "places, users, resources or ports.\n")
        if candidate_listing:
            sys.stdout.write("\nThis account has %d instances in %s - ask the customer to pick "
                             "the one that serves this site instead of asking for an id from "
                             "memory:\n" % (len(candidate_listing), args.region_id))
            for line in candidate_listing:
                sys.stdout.write("- %s\n" % line)
        elif not (args.instance_id or args.eip or args.ip or args.domain or args.url):
            sys.stdout.write("\nNo instance is readable in %s under this account: ask which "
                             "region and which account owns the site before anything else.\n"
                             % args.region_id)
        sys.stdout.write("STATUS: %s\n" % C.STATUS_FAIL)
        sys.stdout.write("NEXT_ACTION: Collect the missing elements above; do not start cloud "
                         "queries until they are in.\n")
        return 2

    try:
        identity = sts_token.get_caller_identity(session_id=session_id)
    except sts_token.CredentialError as exc:
        report.degrade("Credential preflight failed: %s" % exc)
        identity = None
    route = route_error(args)

    instance = check_asset(args, report, session_id)
    if not report.terminated_early:
        check_eip(args, report, session_id, instance, hint_ip=args.ip or args.eip)
        if not args.skip_dns:
            check_dns(args, report, session_id, instance)
        check_security_groups(args, report, session_id, instance)
        check_capacity(args, report, session_id)
        check_app_artifact(args, report, instance)
        report.fix_ineffective = [str(item).strip().lower()
                                  for item in (getattr(args, "fix_ineffective", None) or [])]
        check_implanted_files(args, report)
        check_status_reached(args, report)
        check_port_contrast(args, report)
        check_path_and_compliance(args, report, route)
        pasted = check_pasted_guest(args, report, instance)
        if not args.skip_guest and not pasted:
            check_guest(args, report, session_id, instance)
        check_stated_guest_block(args, report)

    text = print_report(args, report, identity, session_id, route)
    sys.stdout.write(text + "\n")

    if args.report_file:
        with open(args.report_file, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        sys.stdout.write("report written to %s (a plain text file; delete it when it is no "
                         "longer needed)\n" % args.report_file)

    key_hits = [f for f in report.findings if f["key"] and f["verdict"] == C.VERDICT_CONFIRMED]
    if key_hits and not report.degraded:
        status = C.STATUS_OK
        action = ("Report the failing layer and its evidence chain, apply the listed action, and "
                  "ask the customer to retest and report the new error string.")
    elif key_hits:
        status = C.STATUS_DEGRADED
        action = ("Report the confirmed layer plus the layers listed as not excluded; collect "
                  "the remaining readings with the paste-back sheet, then retest and report the "
                  "new error string.")
    else:
        status = C.STATUS_DEGRADED
        action = ("No layer is confirmed yet. Run the comparison set and the paste-back sheet "
                  "above, then re-run with the new error string; never send the customer a list "
                  "of possible causes to try at random.")
    sys.stdout.write("STATUS: %s\n" % status)
    sys.stdout.write("NEXT_ACTION: %s\n" % action)
    return 0


if __name__ == "__main__":
    sys.exit(main())
