#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the access-block layered diagnosis
============================================================================
SECURITY: authentication is resolved exclusively by the aliyun CLI default
credential chain. This module NEVER reads, writes, caches or logs any
AccessKey / Secret. No credential handling lives in this file.

Per platform rule MUST 1.1.2, scripts/ may contain executable code only, so
every reference table this skill needs (layer model, symptom-to-layer map,
security-group semantics, guest inspection command whitelist) is embedded
here as Python constants. There are no data files.

Knowledge sources: real support-ticket dialogues distilled in
references/access-block-layered__ticket-patterns.md, the official help documents cited in
references/access-block-layered__layer-model.md, and API contracts verified with the aliyun CLI
metadata (see related_apis.yaml).
"""

# ---------------------------------------------------------------------------
# Skill identity & observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-access-block-layered"
UA_PREFIX = "AlibabaCloud-Agent-Skills"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
    "cloudfw": "2017-12-07",
    "waf-openapi": "2021-10-01",
}

# ---------------------------------------------------------------------------
# Query limits and timeouts
# ---------------------------------------------------------------------------

DEFAULT_REGION = "cn-hangzhou"
CLI_TIMEOUT_SECONDS = 60          # per aliyun CLI subprocess call
GUEST_POLL_INTERVAL_SECONDS = 5   # between DescribeInvocations polls
GUEST_MAX_WAIT_SECONDS = 90       # hard cap for one guest inspection run
GUEST_RUN_TIMEOUT = 40             # agent-side execution timeout for the command
MAX_PAGES = 20                    # pagination guardrail
PAGE_SIZE = 50                    # security-group rule page size

# ---------------------------------------------------------------------------
# CLI command styles
# ---------------------------------------------------------------------------
# Every product here is served in plugin mode: lowercase-hyphenated commands
# and flags (RegionId -> --biz-region-id, list parameters -> JSON arrays).
# Callers still speak in PascalCase API action names; the CLI layer translates.

PLUGIN_STYLE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

# ---------------------------------------------------------------------------
# The layer model (self-outside-in; see references/access-block-layered__layer-model.md)
# ---------------------------------------------------------------------------

LAYERS = [
    ("L0", "client_side", "Client side (local network, VPN, proxy, browser, egress IP)"),
    ("L1", "dns_compliance", "DNS resolution and domain compliance (ICP filing)"),
    ("L2", "platform_protection", "Platform protection (Cloud Firewall policy, WAF presence)"),
    ("L3", "vpc_network", "VPC network layer (route tables, network ACL) - identify and hand off only"),
    ("L4", "security_group", "ECS security group (ingress and egress, normal vs enterprise)"),
    ("L5", "guest_firewall", "Guest OS firewall / security software / kernel network parameters"),
    ("L6", "service_listener", "Service listener and application layer"),
    ("L7", "outside_platform", "Responsibility outside the platform (path, ISP, peer side)"),
]

LAYER_NAMES = {key: title for key, _, title in LAYERS}

# ---------------------------------------------------------------------------
# Symptom string -> prior layer hints
# ---------------------------------------------------------------------------
# Tier-quotable customer-facing error strings (authoritative list):
QUOTABLE_ERROR_STRINGS = [
    "Connection refused",
    "Connection reset",
    "timed out",
    "Connection timed out",
    "connection reset",
    "err_connection_timed_out",
]

# Symptom mapping. Keys are matched case-insensitively against the --symptom
# text. Entries marked tier=True carry the official quotable error strings;
# other keys are symptom wordings evidenced in real ticket dialogues (see
# references/access-block-layered__symptom-error-strings.md) and are reported as customer-reported
# wording, not as official error codes.
SYMPTOM_LAYER_MAP = [
    {
        "needles": ["timed out", "timeout", "err_connection_timed_out", "i/o timeout"],
        "layer_priors": ["L4", "L5", "L7"],
        "note": ("Drop-type loss: security group has no covering allow rule, guest firewall DROPs, "
                 "or a path/ISP element drops packets. A timeout alone never proves WHICH layer; "
                 "walk L4 -> L5 with evidence."),
        "tier": True,
    },
    {
        "needles": ["connection refused", "refused"],
        "layer_priors": ["L6", "L5"],
        "note": ("A refusal normally means the SYN reached the guest and nothing accepted it on "
                 "that port (no listener, listener bound to 127.0.0.1 only, container port not "
                 "published) or a local REJECT answered it. Check listeners before touching any rule."),
        "tier": True,
    },
    {
        "needles": ["connection reset", "reset by peer", "econnreset", "err_connection_reset"],
        "layer_priors": ["L1", "L7", "L5"],
        "note": ("An RST mid-handshake or mid-TLS often comes from a middlebox or a compliance "
                 "interceptor, and occasionally from the client side itself. Determine WHO sent "
                 "the RST before attributing. When a domain resolves to a Chinese-mainland IP, "
                 "is not ICP-filed, and the server sees no request log at all, unfiled-domain "
                 "interception is the leading hypothesis (assumption level: no filing-status API)."),
        "tier": True,
    },
    {
        "needles": ["no route to host", "no route"],
        "layer_priors": ["L5", "L4"],
        "note": ("Ticket-evidenced wording. 'No route to host' in an intra-VPC test is most often "
                 "a guest firewalld/iptables REJECT answering; it is a strong L5 prior."),
        "tier": False,
    },
    {
        "needles": ["unreachable", "could not connect", "cant connect", "cannot connect",
                    "unable to connect", "connect to the remote computer"],
        "layer_priors": ["L4", "L5", "L0"],
        "note": "Generic failure wording: run the full L4 -> L5 -> L6 sequence, no shortcuts.",
        "tier": False,
    },
    {
        "needles": ["authentication error", "credssp", "too many failed logons",
                    "security layer", "level of encryption"],
        "layer_priors": ["L6", "L5"],
        "note": ("Windows RDP wording. Once the TCP 3389 session establishes, credential-layer "
                 "errors belong to the system/RDP-service layer, not to the security group."),
        "tier": False,
    },
]

# ---------------------------------------------------------------------------
# Security-group evaluation constants
# ---------------------------------------------------------------------------
# Official rule semantics (references/access-block-layered__security-group-pitfalls.md):
#   * Rules are matched in ascending Priority numeric order (1 is highest).
#   * At equal priority an explicit Drop is evaluated before an Accept.
#   * The first matching rule decides. No match: INGRESS defaults to deny;
#     EGRESS defaults to allow for normal security groups, and to DENY for
#     enterprise security groups.

DEFAULT_PRIORITY = 1
MAX_PRIORITY = 100
ALL_PORT_RANGE = "-1/-1"
ALL_PROTOCOL = "ALL"
POLICY_ACCEPT = "Accept"
POLICY_DROP = "Drop"
DIRECTION_INGRESS = "ingress"
DIRECTION_EGRESS = "egress"
SG_TYPE_NORMAL = "normal"
SG_TYPE_ENTERPRISE = "enterprise"

# Well-known remote-access ports used when the customer only says "SSH" /
# "remote desktop".
WELL_KNOWN_PORTS = {
    "ssh": 22,
    "rdp": 3389,
    "http": 80,
    "https": 443,
    "mysql": 3306,
    "mssql": 1433,
    "pgsql": 5432,
}

# Alibaba Cloud service address ranges frequently required in the OUTBOUND
# direction (evidence: tickets where console file-upload failed because an
# enterprise group denied egress 443 to the OOS temporary OSS endpoint).
ALIYUN_INTERNAL_RANGE = "100.64.0.0/10"

# ---------------------------------------------------------------------------
# Guest inspection command whitelist (non-mutating reads only)
# ---------------------------------------------------------------------------
# Every command below is evidenced by a real ticket dialogue (sources noted)
# or explicitly approved in the confirmed requirements document as a new
# read-side check. Each entry: check name -> metadata.
#   os:        linux | windows
#   run_type:  aliyun assistant command type used with the RunCommand action
#              of the ecs product (RRun* values are Cloud Assistant types)
#   command:   the exact single command line, never edited at runtime
#   layer:     which layer this check inspects
#   source:    ticket IDs evidencing the check
# The engine refuses any check name not present here; no raw command text is
# ever accepted from callers, so no argument can be smuggled in.

GUEST_CHECKS = {
    "firewalld-state": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L5",
        "command": "firewall-cmd --state",
        "source": "T-E26080DA, T-45FF359B",
        "meaning": "Reports whether firewalld is running.",
    },
    "firewalld-rules": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L5",
        "command": "firewall-cmd --list-all",
        "source": "T-E26080DA, T-45FF359B, T-43258B49",
        "meaning": "Active zone, services and ports allowed by firewalld.",
    },
    "iptables-rules": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L5",
        "command": "iptables -S",
        "source": "T-42055B69, T-43258B49",
        "meaning": ("Raw iptables rule set in parsable form; reveals whether "
                    "firewalld has taken over rule management from hand-added iptables rules."),
    },
    "iptables-counters": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L5",
        "command": "iptables -L -n -v",
        "source": "T-E26080DA, T-42055B69",
        "meaning": "Chains with packet counters; a REJECT/DROP rule with growing counters is direct evidence.",
    },
    "ufw-status": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L5",
        "command": "ufw status verbose",
        "source": "T-45FF359B, T-0AC34CB9, T-9DE4F634",
        "meaning": "UFW enabled state, default policies and per-port allows (Ubuntu/Debian).",
    },
    "listeners": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L6",
        "command": "ss -lntp",
        "source": "T-E26080DA, T-024E447D",
        "meaning": "Listening sockets with process names; reveals 'bound to 127.0.0.1 only' cases.",
    },
    "listeners-netstat": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L6",
        "command": "netstat -ntulp",
        "source": "T-E26080DA (engineer-issued command in dialogue)",
        "meaning": "Legacy listener list, fallback when ss is unavailable.",
    },
    "kernel-tcp-params": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L5",
        "command": "sysctl net.ipv4.tcp_tw_recycle net.ipv4.tcp_timestamps",
        "source": "T-9CA9D2E9",
        "meaning": ("Reads two kernel network parameters; tcp_tw_recycle=1 plus timestamps drops "
                    "new connections behind NAT (ping OK, all TCP failing). Values are only "
                    "displayed; nothing is written."),
    },
    "recent-logins": {
        "os": "linux", "run_type": "RunShellScript", "layer": "L0",
        "command": "last -i",
        "source": "T-0AC34CB9 (engineer-issued command in dialogue)",
        "meaning": "Recent login records with source IPs; proves the real source address that reached the instance.",
    },
    "windows-listeners": {
        "os": "windows", "run_type": "RunPowerShellScript", "layer": "L6",
        "command": "Get-NetTCPConnection -State Listen | Select-Object LocalAddress,LocalPort,OwningProcess | Format-Table -AutoSize",
        "source": "newly proposed read-side check for Windows (requirements doc section 6.1)",
        "meaning": "Windows listening sockets with owning process.",
    },
    "windows-firewall-profiles": {
        "os": "windows", "run_type": "RunPowerShellScript", "layer": "L5",
        "command": "Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction | Format-Table -AutoSize",
        "source": "newly proposed read-side check for Windows (requirements doc section 6.1)",
        "meaning": "Per-profile Windows Firewall state and default inbound/outbound actions.",
    },
}

# Explicitly NOT whitelisted (ever): any rule change or state change, e.g.
# firewall-cmd --add-port / --reload, ufw allow / disable, iptables -I -A -D,
# sysctl -w, service/systemctl restart, reboot, tcpdump / pktmon captures,
# reading raw auth-log files, or any command with a redirect operator.
# Such steps are emitted as MANUAL guidance only.

# Tokens that must never appear inside a whitelisted command line (defense in
# depth; the whitelist already prevents caller-supplied text).
PROHIBITED_COMMAND_TOKENS = [
    "rm ", "mv ", "dd ", "kill", "reboot", "shutdown", "systemctl", "service ",
    "iptables -I", "iptables -A", "iptables -D", "iptables -F", "ip6tables",
    "firewall-cmd --add", "firewall-cmd --remove", "firewall-cmd --reload",
    "ufw allow", "ufw deny", "ufw disable", "ufw reset",
    "nft add", "nft delete", "sysctl -w", "tcpdump", "pktmon", "> ", ">>", "| ",
    "curl ", "wget ", "echo", "tee", "chmod", "chown", "reg add", "Set-NetFirewall",
    "New-NetFirewall", "Remove-NetFirewall", "netsh",
]

# ---------------------------------------------------------------------------
# Cloud Firewall (internet boundary) constants
# ---------------------------------------------------------------------------

CFW_DIRECTION_IN = "in"
CFW_DIRECTION_OUT = "out"
CFW_ACTION_DROP = "drop"
CFW_ACTION_ACCEPT = "accept"
CFW_ACTION_LOG = "log"
CFW_PAGE_SIZE = 50

# ---------------------------------------------------------------------------
# Handoff boundaries (see references/access-block-layered__handoff-boundaries.md)
# ---------------------------------------------------------------------------

HANDOFF_TARGETS = {
    "vpc_route_link": {
        "skill": "alibabacloud-ecs-vpc-publicnetwork-troubleshoot",
        "triggers": ["custom route table", "vswitch route", "third-party firewall diversion",
                     "EIP quality", "cross-border link", "ISP path", "SNAT", "NAT gateway"],
        "message": ("Symptoms sit in VPC routing / eip / public-link quality, which that skill owns; "
                    "this skill only performed the security-group, firewall and listener layers."),
    },
    "disk_io": {
        "skill": "area:resource-bottleneck",
        "triggers": ["disk IO", "iowait", "system frozen", "high load", "unresponsive but network fine"],
        "message": "Remote unresponsiveness with a healthy network layer and saturated disk IO belongs to disk-io diagnosis.",
    },
    "instance_state": {
        "skill": "area:instance-state-diagnosis",
        "triggers": ["cannot boot", "stuck starting", "restart to recover", "instance state"],
        "message": "Instance boot/state issues (or recovery by reboot) belong to instance-state diagnosis.",
    },
    "waf_product_side": {
        "skill": "WAF product console / support",
        "triggers": ["WAF rule tuning", "CC protection config", "bot management", "WAF back-to-origin ranges"],
        "message": "WAF/CC rule configuration itself is owned by the WAF product side.",
    },
    "security_incident": {
        "skill": "Security Center + manual incident response",
        "triggers": ["intrusion", "trojan", "miner", "defaced", "security agent offline"],
        "message": "Suspected compromise must go to incident response, not firewall diagnosis.",
    },
    "icp_filing": {
        "skill": "ICP filing process (manual guide)",
        "triggers": ["filing", "beian", "domain not registered with MIIT"],
        "message": "Filing application handling is a manual process; this skill only attributes the block.",
    },
    "commercial": {
        "skill": "Billing / commercial support",
        "triggers": ["refund", "billing dispute", "unsubscribe", "compensation"],
        "message": "Billing disputes are commercial processes outside technical diagnosis.",
    },
}

# ---------------------------------------------------------------------------
# Console / documentation links used in generated guidance (real URLs only)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "sg_overview": "https://help.aliyun.com/zh/ecs/user-guide/overview-44.md",
    "sg_quickstart": "https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md",
    "sg_manage_rules": "https://help.aliyun.com/zh/ecs/user-guide/manage-security-group-rules",
    "sg_modify_rules": "https://help.aliyun.com/document_detail/127161.html",
    "sg_start_using": "https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups",
    "linux_firewall": "https://help.aliyun.com/zh/ecs/use-cases/enable-or-disable-the-system-firewall-in-a-linux-instance",
    "cloud_firewall": "https://help.aliyun.com/zh/ecs/user-guide/use-cloud-firewall-to-defend-against-public-network-attacks.md",
    "security_overview": "https://help.aliyun.com/zh/ecs/user-guide/security-overview.md",
    "best_practices": "https://help.aliyun.com/zh/ecs/user-guide/best-security-practices.md",
    "ddos_cleaning": "https://help.aliyun.com/zh/ecs/user-guide/use-ddos-cleaning-service-to-resist-public-network-attacks.md",
    "workbench": "https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md",
    "workbench_windows": "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-windows-instance-through-workbench.md",
    "vnc_login": "https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc",
    "create_snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-of-a-disk",
    "icp_filing": "https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-application-overview",
    "waf_cname_access": "https://help.aliyun.com/zh/waf/web-application-firewall-3-0/user-guide/add-a-domain-name-to-waf-in-cname-record-mode",
    "waf_cc_rules": "https://help.aliyun.com/zh/waf/web-application-firewall-3-0/user-guide/configure-custom-rules-to-defend-against-specific-requests",
    "vpc_isolation": "https://help.aliyun.com/zh/ecs/user-guide/use-vpc-to-implement-network-isolation.md",
    "ecs_insight": "https://help.aliyun.com/zh/ecs/user-guide/ecs-insight-capabilities.md",
    "windows_telnet": "https://help.aliyun.com/zh/ecs/user-guide/enable-telnet-on-a-windows-instance",
}

# Customer self-service egress-IP lookup entry points (evidenced in tickets).
EGRESS_IP_LOOKUP = [
    "https://www.ip138.com/",
    "https://cip.cc",
]

# ---------------------------------------------------------------------------
# Honest capability gaps (requirements doc sections 3.3 / 5.1): whenever the
# verdict depends on one of these, the report must degrade to DEGRADED and
# state the gap instead of pretending the check happened.
# ---------------------------------------------------------------------------

CAPABILITY_GAPS = [
    "No platform-side connectivity dial-test API: 'reachability confirmed from the server side' is a human action this skill cannot reproduce; ask the customer for telnet / Test-NetConnection results from a second network.",
    "No WAF / Cloud Firewall hit-log (interception record) query: only policy configuration can be read, so 'no rule matched' is not proof of 'no interception'.",
    "No ICP filing status API: unfiled-domain interception stays an evidenced hypothesis with customer self-check steps, never a confirmed verdict.",
    "No one-click instance diagnostic report reader: conclusions are rebuilt from raw evidence layer by layer.",
    "No CMS metric reader wired in this build: bandwidth / connection-count side evidence must be checked by the customer in the console.",
]
