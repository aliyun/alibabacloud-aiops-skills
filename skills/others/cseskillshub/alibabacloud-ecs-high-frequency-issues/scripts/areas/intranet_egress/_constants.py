#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and static data for
area:intranet-egress (ECS intranet / egress connectivity diagnosis)
================================================================================
SECURITY: Cloud queries performed by this skill are non-mutating Describe/Get
calls. The single gated exception is the inspection dispatch in
guest_command_gate.py, which is closed by default (see APPROVED_COMMAND_CLASSES)
and requires explicit per-command operator confirmation. Credential material
(access keys, secrets, session tokens) is never read, printed, accepted as an
argument, cached or passed by this module: authentication is resolved
exclusively by the aliyun CLI default credential chain.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so all
static reference data (inspection checklists, target hints, thresholds) lives
here as Python constants. There are no data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-intranet-egress"

# Central STS endpoint (region-less identity service).
STS_ENDPOINT = "sts.aliyuncs.com"

# API versions, aligned with related_apis.yaml. The aliyun CLI carries its own
# metadata; these values document the version each action is invoked against.
API_VERSIONS = {
    "ecs": "2014-05-26",
    "vpc": "2016-04-28",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Timeouts / limits (MUST 7.6.1: every invocation carries a timeout)
# ---------------------------------------------------------------------------

# Per-CLI-invocation subprocess timeout, in seconds.
DEFAULT_TIMEOUT = 60
# Hard guardrail on pagination pages fetched per query loop.
MAX_PAGES = 10
# Page size used for Describe* list queries (every action used here accepts 50).
PAGE_SIZE = 50

# Inspection dispatch (guest_command_gate.py): guest-side execution timeout in
# seconds, plus the read-back poll budget of polls x interval seconds.
GUEST_EXEC_TIMEOUT = 60
GUEST_POLL_INTERVAL = 3
GUEST_MAX_POLLS = 20

# ---------------------------------------------------------------------------
# Mainland-China region classifier
# ---------------------------------------------------------------------------
# Every "cn-" region id is a Chinese-mainland region EXCEPT cn-hongkong.
# Anything not starting with "cn-" is treated as an overseas region.
MAINLAND_PREFIX = "cn-"
NON_MAINLAND_CN_REGIONS = {"cn-hongkong"}


def is_mainland_region(region_id: str) -> bool:
    """True when region_id is a Chinese-mainland ECS region."""
    r = (region_id or "").strip().lower()
    return r.startswith(MAINLAND_PREFIX) and r not in NON_MAINLAND_CN_REGIONS


# ---------------------------------------------------------------------------
# Overseas / cross-border target hints (observed in real support tickets)
# ---------------------------------------------------------------------------
# Domain fragments whose resolution target typically sits OUTSIDE the Chinese
# mainland, so a mainland instance reaching them crosses carrier international
# exits. Used only to ROUTE the diagnosis into the cross-border branch -- the
# script never claims a live link measurement.
OVERSEAS_TARGET_HINTS = (
    "github.com",
    "githubusercontent.com",
    "githubassets.com",
    "gitlab.com",
    "gitlabcdn.com",
    "google.com",
    "googleapis.com",
    "gstatic.com",
    "google-analytics.com",
    "bing.com",
    "youtube.com",
    "acme-v02.api.letsencrypt.org",
    "acme-staging-v02.api.letsencrypt.org",
    "letsencrypt.org",
    "ifconfig.me",
    "ipinfo.io",
    "cloudflare.com",
    "cdn.jsdelivr.net",
    "pypi.org",
    "files.pythonhosted.org",
    "registry.npmjs.org",
    "registry-1.docker.io",
    "docker.io",
    "auth.docker.io",
    "quay.io",
    "raw.githubusercontent.com",
)

# Domestic mirror / alternative endpoints for the well-known egress pain points
# above. Guidance strings only -- this skill never probes or configures them.
DOMESTIC_ALTERNATIVES = [
    "Point package repositories at a domestic mirror (for example the "
    "Aliyun mirrors site for apt/pip/npm: https://mirrors.aliyun.com/).",
    "For GitHub/GitLab fetches, use a domestic code-hosting mirror, or relay "
    "the fetch through an instance that is itself outside the Chinese "
    "mainland. This is a customer architecture decision.",
    "For TLS certificate issuance, prefer a CA endpoint inside mainland China "
    "instead of an overseas ACME endpoint.",
]

# ---------------------------------------------------------------------------
# Error-string normalization (symptom -> evidence class, never a root cause)
# ---------------------------------------------------------------------------
# Each entry: (evidence_class, [lowercase substrings]). Order matters: the
# first matching class wins, so the more specific shapes are listed first.
ERROR_STRING_CLASSES = [
    ("proxy-path", [
        "err_proxy_connection_failed", "proxy",
    ]),
    ("reset", [
        "err_connection_reset", "err_timed_out", "connection reset",
        "reset by peer", "was reset", "forced to close",
    ]),
    ("refused", [
        "connection refused", "actively refused", "err_connection_refused",
    ]),
    ("timeout", [
        "timed out", "timeout", "i/o timeout", "could not connect to server",
        "failed to connect", "couldn't connect", "100% loss", "100% packet loss",
        "no response", "unreachable",
    ]),
    ("filtered", ["filtered"]),
]

# ---------------------------------------------------------------------------
# In-guest state-inspection check lists (printed for the customer to run)
# ---------------------------------------------------------------------------
# Default behavior: the skill PRINTS these commands for the customer to run
# inside the instance and paste back as plain text. Automatic dispatch of a
# single command stays closed until the low-risk command list formally covers
# network inspection (see APPROVED_COMMAND_CLASSES below).

# Resolver-state files the customer prints inside the instance, named relative
# to the guest filesystem root: they belong to the customer's guest, and nothing
# in this skill ever opens them.
GUEST_RESOLVER_FILES = ("etc/resolv.conf", "etc/hosts", "etc/nsswitch.conf")
DNS_STATE_COMMANDS = tuple(f"cat /{name}" for name in GUEST_RESOLVER_FILES)

GUEST_CHECKS_LINUX = {
    "listeners": [
        "ss -antlp            # full listener table: confirm the port is "
        "listed AND bound to 0.0.0.0, not to 127.0.0.1 only",
        "ss -s                # socket summary",
    ],
    "guest-firewall": [
        "iptables -nL -v --line-numbers",
        "ip6tables -nL -v",
        "nft list ruleset",
        "firewall-cmd --state",
        "firewall-cmd --list-all",
        "systemctl is-active firewalld nftables ufw",
        "ls -l /etc/ufw /etc/firewalld   # also look for third-party host "
        "security agents (cloud-lock / safety-dog style)",
    ],
    "routes-dns-proxy": [
        "ip route show",
        "ip rule show",
        *DNS_STATE_COMMANDS,
        "env        # look for http_proxy, https_proxy, all_proxy, no_proxy",
    ],
    "live-probes-egress": [
        "curl -v --connect-timeout 8 <TARGET_URL>",
        "curl -s --connect-timeout 8 http://cip.cc   # egress public IP and "
        "carrier info as seen from the instance",
        "ping -c 4 <TARGET_IP>",
        "telnet <TARGET_IP> <PORT>",
        "traceroute -T -p <PORT> <TARGET_IP>",
    ],
    "reach-arrival": [
        "Grep the web/service access log (nginx/apache application log) for "
        "the customer request: if the request appears in the log, the packet "
        "reached the instance and the fault sits ABOVE the network layer "
        "(application behavior), not in the network path.",
    ],
}

GUEST_CHECKS_WINDOWS = {
    "listeners": [
        "netstat -ano         # confirm the port is listening and note the "
        "owning PID; check for a 127.0.0.1-only bind",
        "Get-NetTCPConnection -State Listen",
    ],
    "guest-firewall": [
        "Get-NetFirewallProfile",
        "Get-NetFirewallRule -Direction Inbound -Action Block",
    ],
    "routes-dns-proxy": [
        "route print",
        "ipconfig /all",
        "netsh winhttp show proxy",
    ],
    "live-probes-egress": [
        "Test-NetConnection <TARGET_IP> -Port <PORT>",
        "curl.exe -v --connect-timeout 8 <TARGET_URL>",
        "curl.exe -s --connect-timeout 8 http://cip.cc",
    ],
    "reach-arrival": [
        "Check the IIS / application log for the customer request (same "
        "reach-arrival logic as the Linux path).",
    ],
}

# ---------------------------------------------------------------------------
# Gated inspection dispatch (guest_command_gate.py)
# ---------------------------------------------------------------------------
# The gate dispatches EXACTLY ONE command per invocation, and only when ALL of:
#   1. the command's check group is listed in APPROVED_COMMAND_CLASSES below;
#   2. the operator passed --acknowledge-approval, declaring item 1 is met by
#      the deployment's own written low-risk command list;
#   3. --confirm echoes the exact command text (per-command informed consent);
#   4. the command fully matches one of the inspection-only patterns;
#   5. the command contains none of the side-effect veto fragments.
# Any unmet condition makes the gate REFUSE and print the manual customer path.

# Command classes the program's low-risk list currently covers. LEFT EMPTY on
# purpose: the network inspection commands this tier needs are not yet part of
# the formally approved list (open item in the requirements document), so the
# automatic path is closed and the skill falls back to printed guidance. A
# deployment that owns a written approval may add class names here; every
# remaining guard still applies.
APPROVED_COMMAND_CLASSES: tuple = ()

# Leading binaries accepted for a dispatched inspection command.
INSPECTION_COMMAND_TOKENS = {
    "ip", "cat", "ss", "netstat", "iptables", "ip6tables", "nft",
    "firewall-cmd", "systemctl", "curl", "ping", "telnet", "traceroute",
    "route", "ifconfig", "nslookup", "dig", "host", "env", "printenv",
    "hostname", "id", "date", "get-netfirewallprofile",
    "get-netfirewallrule", "get-nettcpconnection", "get-netipconfiguration",
    "get-dnsclientserversaddress", "test-netconnection", "netstat.exe",
    "curl.exe", "ipconfig", "nslookup.exe", "netsh", "tracert", "ls",
}

# Substrings that veto the dispatch because they either mutate state or chain
# a second command. Any occurrence refuses the dispatch regardless of flags.
SIDE_EFFECT_FRAGMENTS = [
    " rm ", " mv ", " dd ", " kill ", " pkill ", " truncate ", " mkfs ",
    " chmod ", " chown ", " reboot ", " shutdown ", " halt ", " parted ",
    " mkswap ", " systemctl start", " systemctl stop", " systemctl restart",
    " systemctl enable", " systemctl disable", " service ",
    " iptables -a", " iptables -d", " iptables -i", " iptables -p",
    " iptables -f", " iptables -x", " ip6tables -a", " ip6tables -d",
    " nft add", " nft delete", " nft flush", " nft insert",
    " ufw allow", " ufw deny", " ufw delete", " ufw disable", " ufw reset",
    " ip route add", " ip route del", " ip rule add", " ip rule del",
    " ifdown", " ifup", " setnetsh", " new-netfirewallrule",
    " remove-item", " set-item", " new-item", " invoke-command",
    " invoke-expression", " invoke-webrequest", " start-process",
    " stop-process", " > ", ">>", " >>", " >> ", " < ", " && ", " ||",
    ";", "`", "$(", "|", "&", "\n", "invoke-expression", "iex ",
    "curl -o", "curl.exe -o", "wget ",
]

# Accepted argument forms for the leading binary. Two policies are used, chosen
# by veto_mode(): POSITIONAL commands are interpreted positionally, so EVERY
# remaining token must appear in POSITIONAL_ALLOWLIST (an unlisted token such as
# "-F" therefore refuses the dispatch); FLAG commands only ever report state,
# whatever their flag order, so their flags are checked by the text guards
# alone. Any leading binary outside both maps is refused.
POSITIONAL_ALLOWLIST = {
    "ip": {"route", "rule", "addr", "address", "link", "neigh", "show",
           "list", "-4", "-6", "-s"},
    "nft": {"list", "ruleset", "table", "tables", "chain", "chains"},
    "route": {"print", "-n"},
    "netsh": {"winhttp", "show", "proxy"},
    "systemctl": {"is-active", "is-enabled", "status", "list-units", "show",
                  "-l", "--no-pager", "--full", "-a", "--all", "--plain",
                  "firewalld", "nftables", "ufw"},
    "cat": frozenset(f"/{name}" for name in GUEST_RESOLVER_FILES),
    "iptables": {"-n", "-nl", "-n-l", "-nv", "-l", "-L", "-s", "-v", "-x",
                 "--line-numbers", "--line-number", "--numeric", "--exact",
                 "-t", "filter", "security", "nat", "mangle", "raw"},
    "ip6tables": {"-n", "-nl", "-n-l", "-nv", "-l", "-L", "-s", "-v", "-x",
                  "--line-numbers", "--line-number", "--numeric", "--exact",
                  "-t", "filter", "security", "nat", "mangle", "raw"},
    "firewall-cmd": {"--state", "--list-all", "--list-ports",
                     "--list-services", "--list-protocols",
                     "--list-rich-rules", "--get-active-zones",
                     "--get-default-zone", "--get-zones", "--zone",
                     "--all-zones"},
}

# Accepted with any flag combination, because every flag of these commands is
# informational; the veto fragments above still apply to the whole text.
FLAG_ALLOWLIST = {
    "ss", "netstat", "netstat.exe", "curl", "curl.exe", "ping", "telnet",
    "traceroute", "tracert", "nslookup", "nslookup.exe", "dig", "host",
    "ifconfig", "env", "printenv", "hostname", "id", "date", "ipconfig",
    "get-netfirewallprofile", "get-netfirewallrule", "get-nettcpconnection",
    "get-netipconfiguration", "get-dnsclientserversaddress",
    "test-netconnection", "ls",
}


def veto_mode(lead: str) -> str:
    """Return the argument policy for one leading binary.

    "positional" -- every remaining token must be allowlisted;
    "flags"      -- flags are informational, text guards alone apply;
    "none"       -- binary not accepted, the dispatch is refused.
    """
    name = (lead or "").strip().lower()
    if name in POSITIONAL_ALLOWLIST:
        return "positional"
    if name in FLAG_ALLOWLIST:
        return "flags"
    return "none"


# Flag-policied commands accept arbitrary arguments, so a few traffic-shaping
# or file-writing flags are rejected token by token: they are not state
# mutations inside the guest, but they are not state INSPECTION either.
HIGH_RISK_ARGUMENT_FLAGS = frozenset({
    "-f", "--flood", "-F", "--file",
    "-o", "--output", "-O", "--remote-name", "--config", "-K",
    "--data", "--data-binary", "--data-urlencode",
})

# Bundling a letter into a short-flag cluster must not smuggle a denied flag
# past the exact-token check, so these binaries have their clusters decomposed
# and every letter checked. Only binaries whose short letters carry write
# semantics need an entry.
SHORT_FLAG_CLUSTER_DENY = {
    "curl": set("oOdFTbKG"),
    "curl.exe": set("oOdFTbKG"),
    "ping": set("f"),
}

# ---------------------------------------------------------------------------
# Handoff targets (skill names for the boundary matrix)
# ---------------------------------------------------------------------------
HANDOFF_SKILLS = {
    "general-network": "alibabacloud-network-diagnose",
    "disk-expand": "area:disk-expand-diagnosis",
    "disk-io": "area:resource-bottleneck",
    "instance-state": "area:instance-state-diagnosis",
}

# ---------------------------------------------------------------------------
# Inline boundary assertions (run on every import)
# ---------------------------------------------------------------------------
# normal case
assert is_mainland_region("cn-hangzhou") is True
assert is_mainland_region("ap-southeast-1") is False
# boundary: Hong Kong is not part of the Chinese mainland
assert is_mainland_region("cn-hongkong") is False
# invalid input degrades to False and never raises
assert is_mainland_region("") is False
assert is_mainland_region(None) is False
# every error class resolves to a known name, first match wins
assert ERROR_STRING_CLASSES[0][0] == "proxy-path"
assert ERROR_STRING_CLASSES[1][0] == "reset"
# the automatic dispatch is closed by default
assert APPROVED_COMMAND_CLASSES == ()
# veto fragments must cover the canonical mutation shapes
assert " rm " in SIDE_EFFECT_FRAGMENTS
assert ">>" in SIDE_EFFECT_FRAGMENTS
assert ";" in SIDE_EFFECT_FRAGMENTS
# both argument policies only name accepted binaries
assert set(POSITIONAL_ALLOWLIST) <= INSPECTION_COMMAND_TOKENS
assert set(FLAG_ALLOWLIST) <= INSPECTION_COMMAND_TOKENS
# policy selection: positional binaries are token-checked, probes are not
assert veto_mode("iptables") == "positional"
assert veto_mode("curl") == "flags"
assert veto_mode("id") == "flags"
assert veto_mode("rm") == "none"
assert veto_mode("") == "none"
assert set(SHORT_FLAG_CLUSTER_DENY) <= FLAG_ALLOWLIST
# a status query must NOT be vetoed: the service manager name is legitimate
assert not any(f in "systemctl is-active firewalld"
               for f in SIDE_EFFECT_FRAGMENTS)
assert not any(f in "iptables -nL -v --line-numbers"
               for f in SIDE_EFFECT_FRAGMENTS)
# every command this skill prints must survive the argument policies, so the
# approved-list day does not silently break the shipped checklist
assert veto_mode("traceroute") == "flags"
assert "-t" not in HIGH_RISK_ARGUMENT_FLAGS
assert "-l" not in HIGH_RISK_ARGUMENT_FLAGS
assert "-o" in HIGH_RISK_ARGUMENT_FLAGS
# handoff targets are the sibling skills named in the boundary matrix
assert HANDOFF_SKILLS["general-network"] == "alibabacloud-network-diagnose"
