#!/usr/bin/env python3
"""
_constants.py -- skill constants and embedded static knowledge
==============================================================
SECURITY: This skill is strictly READ-ONLY. This module holds only constants;
it never reads, prints, caches or transports any credential material.
Authentication is resolved exclusively by the aliyun CLI default credential
chain.

Platform rule MUST 1.1.2 keeps scripts/ executable-code-only, therefore every
static table this skill needs (API whitelist, versions, limits, the decision
knowledge emitted into reports) is embedded here as Python constants. There
are no data files in scripts/.
"""

SKILL_NAME = "alibabacloud-ecs-vpc-connectivity-check"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "vpc": "2016-04-28",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Hard API whitelist (deny-by-default guardrail, enforced in _cli.call)
# ---------------------------------------------------------------------------
# Only actions verified as read-only for this tier may be invoked, and only
# through the entry script. Any (product, action) pair outside this set is
# rejected before a subprocess is spawned.
ALLOWED_ACTIONS = frozenset({
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeInstanceStatus"),
    ("ecs", "DescribeAvailableResource"),
    # Inbound/outbound RULE CONTENT of a security group (direction, protocol,
    # port range, authorization object, policy, priority): read-only, no gate.
    ("ecs", "DescribeSecurityGroupAttribute"),
    ("vpc", "DescribeEipAddresses"),
    ("sts", "GetCallerIdentity"),
})

# ---------------------------------------------------------------------------
# Limits and timeouts
# ---------------------------------------------------------------------------
# MUST 7.6.1: every CLI subprocess call carries an explicit timeout.
DEFAULT_TIMEOUT = 60        # seconds per aliyun CLI invocation
PAGE_SIZE = 50              # PageSize used by the Describe* list queries
MAX_PAGES = 20              # hard pagination guardrail per query loop
RETRY_ATTEMPTS = 3          # total attempts on transient errors
BACKOFF_BASE_SECONDS = 2    # linear backoff: 2s, 4s

# Region fallback note: when the customer omits RegionId the caller may start
# from this region, but the entry script requires an explicit --region-id for
# every cloud-backed mode (no silent guessing).
DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Embedded decision knowledge (concise forms; full text lives in references/)
# ---------------------------------------------------------------------------

# Facts that are invisible to read-only cloud APIs and therefore always manual.
GUEST_BOUNDARY_ITEMS = [
    "Guest OS firewall (iptables / firewalld / Windows firewall rules)",
    "Docker bridge networks (br-*) whose CIDR may collide with the ECS "
    "private range",
    "Guest route table, NetworkManager connection names, NIC restart",
    "Application layer behaviour (IIS HTTPS binding, nginx reverse proxy, "
    "backend service state, DNS resolution inside the guest)",
]

# Fixed correction of the two most common customer misconceptions about
# security-group intranet whitelisting (observed root causes in tickets).
SG_MISCONCEPTION_FIXES = [
    "Inter-instance access is opened on the TARGET side only: an inbound "
    "rule on the target instance's security group that allows the source "
    "private IP and the target port. The source side needs no matching "
    "inbound rule for this traffic.",
    "Authorizing the whole large private range (for example 172.16.0.0/12) "
    "is NOT required: a /32 host route of the source private IP plus the "
    "target port is precise and safer.",
    "ping tests ICMP only. A denied ping does not prove the TCP port is "
    "blocked, and a reachable port does not imply ICMP is allowed; ICMP "
    "needs its own rule. Verify the port with telnet or curl.",
]

# The three consistency conditions a cross-account instance transfer target
# must satisfy, plus the reverse-authorization dependency.
TRANSFER_CONSISTENCY_CONDITIONS = [
    "Condition 1 (region): the transfer is not cross-region; the target "
    "account's resources must be created in the SAME region as the source "
    "instance.",
    "Condition 2 (VPC): the target vSwitch and the target security group "
    "must belong to the SAME VPC (the security group must be created under "
    "that VPC by the target account itself).",
    "Condition 3 (zone): the target vSwitch must be in the SAME availability "
    "zone as the source instance; a switch change also requires the same "
    "zone.",
]

TRANSFER_EXTRA_NOTES = [
    "Economy-type instance families may be assigned a random availability "
    "zone during transfer: pre-create a vSwitch in EVERY availability zone "
    "of the region on the target account.",
    "If the picker still reports InvalidDependence.GrantAccess, a grant / "
    "reverse-authorization dependency of the transfer is not cleared: the "
    "SOURCE account must cancel its reverse authorization, then the target "
    "account retries the selection.",
    "The transfer itself, target-resource creation and any cross-account "
    "backend operation are executed manually by the two account owners (or "
    "a human specialist for cross-account cases); this skill only produces "
    "the read-only pre-check.",
]

# Inbound rule dimensions the script reads back and compares one by one via
# DescribeSecurityGroupAttribute (direction / protocol / port range /
# authorization object / policy / priority). They are repeated in the manual
# block only as the fallback for a group whose rule read failed.
SG_RULE_VERIFY_DIMENSIONS = [
    "direction = inbound (ingress)",
    "authorization object = the source private IP written as <ip>/32, or a "
    "covering CIDR that really contains it",
    "ip protocol = tcp / udp / icmp as required by the traffic (ICMP is a "
    "separate protocol, not covered by a TCP rule)",
    "port range = the exact target port (for example 51711/51711, not "
    "'all' if a precise rule is wanted)",
    "policy = allow, and the rule priority must not be shadowed by a "
    "higher-priority deny",
]

# Recognize the security-group API vocabulary without reparsing it per call.
SG_ACCEPT_POLICIES = ("accept", "allow")
SG_DROP_POLICIES = ("drop", "deny", "refuse")
SG_PROTOCOL_ALL = ("all", "-1", "")

# Verdict templates for the security-group rule comparison (the rule content
# is read through DescribeSecurityGroupAttribute, so the verdict is computed
# from the returned rules, not from a console copy).
SG_RULE_VERDICTS = {
    "allowed": ("an inbound ALLOW rule matches the source address, the "
                "protocol and the port, and no higher-priority DENY shadows "
                "it: the cloud-side rule is NOT the block. Look at the guest "
                "firewall, the listening address and the application next"),
    "shadowed-by-deny": ("a matching DENY rule has a better (lower) priority "
                         "than the matching ALLOW rule: the security group "
                         "drops this traffic. Fixing it is a manual console "
                         "edit on the TARGET security group"),
    "no-matching-rule": ("no inbound rule matches the source address, the "
                         "protocol and the port: the security group has no "
                         "allow for this flow, which is a cloud-side root "
                         "cause. Adding it is a customer-executed step (console or the equivalent OpenAPI)"),
    "no-port-given": ("rules were read back and listed, but a port-level "
                      "verdict needs the target port: rerun with --port"),
    "unreadable": ("the rule content of this group could not be read this "
                   "run (see the [WARN] line): compare the listed dimensions "
                   "in the console before concluding anything"),
}

# Verdict templates for the same-VSwitch CIDR overlap check.
CIDR_VERDICTS = {
    "identical": "OVERLAP: the two CIDR blocks are identical.",
    "a-within-b": "OVERLAP: CIDR A is contained inside CIDR B.",
    "b-within-a": "OVERLAP: CIDR B is contained inside CIDR A.",
    "partial-overlap": "OVERLAP: the two CIDR blocks partially intersect.",
    "disjoint": "NO OVERLAP: the two CIDR blocks are disjoint.",
}

# Manual remediation step lists keyed by mode.
MANUAL_STEPS = {
    "pair": [
        "On the TARGET instance's security group, verify an inbound rule "
        "allowing the source private IP (/32) and the target port/protocol "
        "in use; add it in the ECS console if missing (console-only manual "
        "step).",
        "From the source instance, test the actual port with "
        "'telnet <target-private-ip> <port>' (or curl); do not judge the "
        "port by ping alone.",
        "If a ping is expected to work, verify a separate inbound ICMP "
        "allow rule exists.",
        "If cloud-side rules are confirmed correct, self-check the guest: "
        "OS firewall, listening address (0.0.0.0 vs 127.0.0.1), and whether "
        "a Docker bridge CIDR collides with the ECS private range.",
    ],
    "cidr": [
        "If the two vSwitch CIDRs overlap: on the side you control, create "
        "a new vSwitch with a non-conflicting CIDR inside the same VPC and "
        "move the instance's private IP onto it (switch change requires the "
        "same availability zone), then retest.",
        "Keep new vSwitch CIDRs out of ranges commonly taken by container "
        "bridges (172.17-172.31) when planning the VPC.",
    ],
    "transfer": [
        "Target account: confirm the region selector shows the SOURCE "
        "instance's region before creating resources (a transfer is never "
        "cross-region).",
        "Target account: create the vSwitch in the SOURCE instance's "
        "availability zone shown in the evidence (all zones for random-zone "
        "families). VPC IDs are account-local: the target account uses its "
        "own VPC, it cannot reuse the source account's VPC.",
        "Target account: create the security group UNDER THE SAME target VPC "
        "as the chosen vSwitch; a security group of any other VPC is never "
        "selectable.",
        "Same-account case (moving an instance to another vSwitch instead of "
        "a transfer): the destination vSwitch must be inside the instance's "
        "CURRENT VPC and in the instance's availability zone.",
        "Source account: cancel the reverse authorization / grant created "
        "for the transfer, then retry the selection.",
        "Execute the transfer itself in the console manually; this skill "
        "never performs it.",
    ],
    "ip-list": [
        "To assign additional private IPs, use the console ENI private-IP "
        "flow; inside the guest the IP must be configured per OS (Network-"
        "Manager based images use the connection name shown by 'nmcli -t "
        "-f NAME connection show', commonly 'System eth0', not 'eth0').",
    ],
    "eip-check": [
        "Intranet reachable but public unreachable, with the public path "
        "configured: verify HTTPS vs HTTP and the web/server application "
        "binding first (browser defaulting to HTTPS is a recurring root "
        "cause), then the security-group inbound rules for the public-side "
        "client addresses.",
        "No public IP / no EIP bound: the instance has no public ingress or "
        "egress path by design; egress needs NAT gateway or EIP - hand off "
        "to public-network diagnosis.",
    ],
}

# Cross-skill hand-off table (name -> situation).
HANDOFFS = {
    "alibabacloud-ecs-vpc-publicnetwork-troubleshoot":
        "public-internet reachability or VPC egress path (NAT / SNAT / "
        "route / EIP binding chain)",
    "alibabacloud-network-diagnose":
        "step-by-step path probing between two endpoints when the "
        "configuration itself is already confirmed correct",
    "area:disk-expand-diagnosis":
        "disk expansion not taking effect",
    "area:instance-state-diagnosis":
        "instance stuck in a start / stop / reboot state",
    "area:resource-bottleneck":
        "disk IO performance or capacity / inode pressure",
    "RAM / access-control support (human)":
        "policy conditions, AccessKey VPC access-control policies and any "
        "authorization denial that is not a security-group issue",
    "manual in-guest investigation":
        "guest firewall, Docker bridge collision, NIC configuration, "
        "application-layer faults",
}

# Recurring customer-side error strings and their disposition.
ERROR_DISPOSITIONS = {
    "InvalidDependence.GrantAccess":
        "transfer / cross-resource dependency not cleared: keep the "
        "read-only consistency findings, then source account cancels the "
        "reverse authorization (manual step)",
}
