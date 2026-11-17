#!/usr/bin/env python3
"""
_constants.py -- Embedded static knowledge for the SMTP / port-25 block skill
=============================================================================
SECURITY: This module is pure data (no I/O, no network, no credential access).
Per platform rule MUST 1.1.2 the scripts/ directory may only contain
executable code, so every lookup table this skill needs (port-policy matrix,
SMTP error signatures, unblock-application facts, guidance blocks, handoff
rules) is embedded here as Python constants instead of data files.

EVIDENCE DISCIPLINE (anti-hallucination):
  * Every policy statement below carries a `source` tag naming where it comes
    from: a real support-ticket id (e.g. "ticket T-BFFFC987"), an official
    help-document URL listed in DOC_LINKS, or "UNCONFIRMED" when ticket
    reports conflict (the entry script must then surface it as "verify
    before promising", never as a settled fact).
  * Do NOT "improve" a statement without such a source. Unknowns stay
    explicitly unknown.

PERMISSION MODEL (RO+G): the cloud side of this skill is non-mutating
Describe/Get queries plus exactly ONE state-changing-from-the-cloud-API call,
`ecs RunCommand`, which is used only to dispatch the fixed inspection-only
command templates in GUEST_PROBES below, and only after the caller passes the
PROBE_CONFIRMATION_TOKEN proving the user approved that single command (see
SKILL.md 'Guest Evidence Gate'). Because the dispatchable command surface is
exactly the strings in this module, it is finite, reviewable and immune to
free-form command injection: nothing outside GUEST_PROBES can ever be sent
into an instance by this skill.
"""

import re

# ---------------------------------------------------------------------------
# Skill identity / API metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-smtp-block-diagnosis"

# Informational: the aliyun CLI carries its own API metadata.
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# Per-call subprocess timeout in seconds (MUST 7.6.1: every CLI call carries
# an explicit timeout).
CLI_TIMEOUT = 60
MAX_ATTEMPTS = 3          # total attempts for one CLI invocation
BACKOFF_BASE_SECONDS = 2  # retry N waits N * 2s

# Guardrail for the optional invocation-record listing.
MAX_INVOCATIONS = 20

# ---------------------------------------------------------------------------
# API whitelist (machine-enforced)
# ---------------------------------------------------------------------------
# The ONLY (product, action) pairs this skill may ever send to the CLI.
# scripts/areas/smtp_block_diagnosis/_cli.py refuses anything else before a subprocess is spawned, so
# this set -- not prose -- is the privilege boundary. Everything here is a
# non-mutating Describe/Get query except `ecs RunCommand`, which exists
# solely to dispatch the fixed inspection-only templates in GUEST_PROBES
# behind the confirmation gate.
ALLOWED_ACTIONS = frozenset({
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeInstanceStatus"),
    ("ecs", "DescribeInvocations"),
    ("ecs", "DescribeSecurityGroupAttribute"),
    ("ecs", "RunCommand"),
    ("sts", "GetCallerIdentity"),
})

# ---------------------------------------------------------------------------
# Cloud Assistant probe timing (every bound is explicit; nothing waits
# forever, every underlying CLI call carries its own timeout too)
# ---------------------------------------------------------------------------
PROBE_CONNECT_TIMEOUT_SECONDS = 8    # per-port TCP guard inside the guest
PROBE_RUN_TIMEOUT_SECONDS = 60       # RunCommand Timeout parameter
PROBE_POLL_INTERVAL_SECONDS = 5      # gap between output polls
PROBE_MAX_WAIT_SECONDS = 120         # hard cap on polling one probe
PROBE_MAX_PORTS = 6                  # ports per port-probe dispatch
PROBE_OUTPUT_MAX_CHARS = 4000        # truncation ceiling for returned output

# The caller (agent) must pass this exact token to --user-confirmation to
# prove the user approved THIS single inspection-only command after the
# disclosure block was shown. Without it the script refuses to dispatch.
PROBE_CONFIRMATION_TOKEN = "I-APPROVE-INSPECTION-ONLY-COMMAND"

# Statuses that end the polling loop for one dispatched probe.
PROBE_TERMINAL_STATUSES = (
    "Success", "Finished", "Failed", "Error", "Timeout", "Stopped",
    "Cancelled", "Aborted", "PartialFailed", "Invalid", "InvalidNetwork",
)

# ---------------------------------------------------------------------------
# Port sets
# ---------------------------------------------------------------------------

MAIL_SEND_PORTS = (465, 587)
MAIL_PORTS = (25, 465, 587, 993, 995)     # ports customers call "email ports"
BASELINE_PORTS = (80, 443)                # control ports (proven unblocked)
BLOCKED_BY_DEFAULT_PORT = 25

# States accepted by --port-result PORT=STATE.
PORT_STATES = (
    "timeout",             # connect attempt gave up silently  (block symptom)
    "refused",             # RST back: reachable, nothing listening
    "connected",           # TCP established, session usable
    "connected-closed",    # TCP established then closed / session failed
    "banner-error",        # got an SMTP banner plus a rejection code
)

# ---------------------------------------------------------------------------
# Attribution layers (the verdict vocabulary of this skill)
# ---------------------------------------------------------------------------

LAYER_PLATFORM_BLOCK = "platform-outbound-port25-block"
LAYER_CUSTOMER_CONFIG = "customer-config-layer"        # security group / firewall
LAYER_PEER_APPLICATION = "peer-mail-server-application-layer"
LAYER_UNLISTENING = "guest-listener-or-container-mapping"
LAYER_APPLY_ELIGIBILITY = "unblock-application-eligibility"
LAYER_CROSS_BORDER = "cross-border-link-or-peer-overseas-policy"
LAYER_NOT_ATTRIBUTED = "not-attributed-insufficient-evidence"

# ---------------------------------------------------------------------------
# Unified policy statements (consistent wording for every customer -- one of
# the core values of this skill is that the answer no longer depends on which
# agent picks up the ticket; ticket evidence shows agents giving contradictory
# statements; see references/smtp-block-diagnosis__port-policy-matrix.md)
# ---------------------------------------------------------------------------

POLICY_STATEMENTS = {
    "outbound-25-default": {
        "text": ("By default new Alibaba Cloud ECS instances do not provide "
                 "outbound TCP port 25. This is a platform anti-spam policy; "
                 "it applies even when security-group egress rules allow the "
                 "traffic, and it is independent of the instance region or "
                 "age."),
        "source": "official ECS limits doc + ticket T-BFFFC987 (agent verbatim)",
    },
    "apply-flow": {
        "text": ("A port-25 unblock application can be submitted from the "
                 "console; a specialist reviews it. Review takes about 1 "
                 "business day and the result is sent by email. Approval is "
                 "NOT guaranteed -- do not promise an outcome."),
        "source": "ticket T-BFFFC987 (agent verbatim) + tickets T-ABCFCE6C / T-8D3AFDFB",
    },
    "agreement-scope": {
        "text": ("The Port-25 Usage Service Agreement restricts an unblocked "
                 "port 25 to CONNECTING TO THIRD-PARTY SMTP SERVERS. "
                 "Self-hosted MTA direct delivery to remote MX hosts is "
                 "outside the agreement scope and is rejected in review "
                 "(review note verbatim: use an external mail provider on "
                 "port 465 instead). Never misstate the use case to pass "
                 "review."),
        "source": "ticket T-0DC2E989 (reviewer note verbatim + agreement text)",
    },
    "secure-ports-open": {
        "text": ("Ports 465 (implicit TLS) and 587 (STARTTLS submission) are "
                 "NOT restricted by the platform and need no 'opening'; if "
                 "they are unreachable from an instance, the cause is on the "
                 "customer side (security group egress, guest firewall) or at "
                 "the receiving provider."),
        "source": "ticket T-8E8AD7A5 (agent verbatim) + ticket T-3E637B73",
    },
    "ipv6-25": {
        "text": ("Opening outbound port 25 over IPv6 is not supported on the "
                 "cloud network; use IPv4 connectivity, or an authenticated "
                 "submission port such as 465."),
        "source": "ticket T-F418FAF1 (agent verbatim)",
    },
    "ptr": {
        "text": ("Custom reverse DNS (PTR/rDNS) for an ECS public IP is not "
                 "self-service; providers that require a matching PTR cannot "
                 "be satisfied from an ECS IP -- plan an external mail "
                 "provider instead."),
        "source": "ticket T-043B7B7E (summary-level; verify against official docs)",
    },
    "inbound-25": {
        "text": ("Whether INBOUND TCP 25 (receiving mail) is platform-"
                 "restricted is reported inconsistently in past tickets: some "
                 "say inbound 25 needs no application, others were told to "
                 "apply for inbound too. Treat as UNCONFIRMED: verify against "
                 "the current official policy before promising anything, and "
                 "fix the customer-side layers (security group inbound rule, "
                 "listener, container port mapping) first -- those are the "
                 "proven causes."),
        "source": "UNCONFIRMED -- conflicting tickets T-5919F890 / T-398559AD vs T-DE88AA98 / T-62FDA757 / T-248E052C",
    },
    "overseas-25": {
        "text": ("Whether the outbound-25 policy and the unblock application "
                 "behave differently in regions outside the Chinese mainland "
                 "is reported inconsistently (one report says overseas "
                 "regions also refuse inbound-25 applications; another got a "
                 "successful unblock). Treat as UNCONFIRMED per region."),
        "source": "UNCONFIRMED -- conflicting tickets T-AFC2095D vs T-9F9BED3F / T-B6515F06",
    },
}

# ---------------------------------------------------------------------------
# Official documentation links (all taken from real ticket conversations or
# the injected help-search hits; console deep links change between versions,
# so the application entry is described by navigation path, with the
# last-customer-verified link given only as a hint plus a validity caveat)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "ecs-limits": {
        "title": "ECS usage limits (source of the outbound port-25 default)",
        "url": "https://help.aliyun.com/zh/ecs/product-overview/limits",
    },
    "unblock-application-doc": {
        "title": "How to apply to unblock port 25",
        "url": "https://help.aliyun.com/zh/document_detail/56130.html",
    },
    "ssl-465-example": {
        "title": "Sending mail over the SSL-encrypted port 465 (sample + demo)",
        "url": ("https://help.aliyun.com/zh/cloud-web-hosting/use-cases/"
                "encrypted-using-ssl-port-465-to-send-email"),
    },
    "cloud-security-rules": {
        "title": "Cloud platform security rules (anti-spam basis)",
        "url": "https://help.aliyun.com/knowledge_detail/37353.html",
    },
    "security-group-quickstart": {
        "title": "Five-minute security group guide (inbound/egress rules)",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "5-minute-guide-to-security-groups-secure-and-precise-"
                "network-access-control.md"),
    },
    "workbench-overview": {
        "title": "Connecting to an instance with Workbench (for running the "
                 "manual evidence commands)",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md",
    },
}

# The unblock-application console entry. Two generations of paths exist in
# ticket evidence; the old root link was VERIFIED DEAD by a real customer
# (it lands on an unrelated page). Give the navigation description first.
APPLICATION_ENTRY = {
    "description": ("Sign in to the console, open the security-control "
                    "section, and use the 'Port 25 unblock application' "
                    "tool page (in the console's more-tools area). Console "
                    "navigation changes between versions -- if the entry is "
                    "not found, search the console for '25' / 'port "
                    "unblock', or follow the official application document "
                    "listed above instead of an old bookmark."),
    "last_verified_hint_url": "https://yundun.console.aliyun.com/?p=scnew#/moreTools",
    "dead_old_url_warning": ("The older entry path (yundun console "
                             "'sc#/sc/port') was reported as no longer "
                             "working -- do not send customers there."),
    "source": "ticket T-0DC2E989 (customer confirmed the new path; old path verified broken)",
}

# ---------------------------------------------------------------------------
# SMTP error signatures: customer-visible report text -> attributed layer
# (extracted verbatim from real ticket dialogue; see also
# references/smtp-block-diagnosis__smtp-error-signatures.md)
# ---------------------------------------------------------------------------

ERROR_SIGNATURES = (
    {
        "id": "550-bad-helo",
        "regex": r"550\s+bad\s+helo|host\s+impersonating\s+domain",
        "layer": LAYER_PEER_APPLICATION,
        "headline": ("The receiving mail server rejected the session at the "
                     "application layer (Bad HELO: the HELO/EHLO name looks "
                     "like it impersonates a domain)."),
        "explanation": ("TCP connectivity is NOT the problem -- a 5xx reply "
                        "means the SMTP session was established. Common "
                        "causes: the client announces an HELO hostname that "
                        "does not resolve to the sending IP, or a webmail/"
                        "library default hostname colliding with a domain "
                        "the sender does not own."),
        "actions": (
            "Set the mail client/library HELO/EHLO identity to a fully "
            "qualified hostname that the sending IP legitimately owns "
            "(manual change in the customer's application).",
            "Align SPF/DNS records for the announced hostname, then retry.",
            "If it persists, ask the receiving mail provider which identity "
            "policy rejected the session -- this is the provider's side.",
        ),
        "not_this_skill": ("Do NOT route this through the port-25 unblock "
                           "path; a real ticket shows the 25-port answer here "
                           "was answering a different question."),
        "source": "ticket T-BFFFC987 (customer-quoted '550 Bad HELO - Host "
                  "impersonating domain name')",
    },
    {
        "id": "503-starttls-not-advertised",
        "regex": r"503\s+starttls\s+command\s+used\s+when\s+not\s+advertised",
        "layer": LAYER_PEER_APPLICATION,
        "headline": ("The client issued STARTTLS but the server did not "
                     "advertise it (TLS negotiation mismatch, application "
                     "layer)."),
        "explanation": ("The session reached the SMTP server, so the network "
                        "path is fine; the client and server disagree on how "
                        "to upgrade to TLS."),
        "actions": (
            "Match the client security mode to the port/provider: implicit "
            "TLS (SSL) on 465 vs STARTTLS on 587.",
            "Re-test after changing SMTPSecure/encryption settings "
            "(customer-side application configuration; manual).",
        ),
        "not_this_skill": "Not a platform port restriction.",
        "source": "ticket T-BFFFC987 (customer-quoted '503 STARTTLS command "
                  "used when not advertised')",
    },
    {
        "id": "451-timeout",
        "regex": r"451\s+timeout",
        "layer": LAYER_PEER_APPLICATION,
        "headline": ("The remote server accepted TCP but stalled the SMTP "
                     "session (451 Timeout from the peer)."),
        "explanation": ("Typical of provider-side greylisting / rate policy "
                        "or degraded paths (for example an overseas source "
                        "IP hitting a domestic provider). TCP reachability "
                        "does not prove mail acceptance."),
        "actions": (
            "Retry after a delay and capture the exact session transcript.",
            "Ask the receiving provider whether the source IP is throttled.",
            "If the instance region and the mail provider sit on opposite "
            "sides of a national border, consider the cross-border link "
            "handoff below before more network testing.",
        ),
        "not_this_skill": "Not a platform port restriction when 465/587 are "
                          "reachable.",
        "source": "ticket T-8E8AD7A5 (customer-quoted '451 Timeout.' after "
                  "'220 ... ESMTP')",
    },
    {
        "id": "illegal-address",
        "regex": r"illegal\s+address|addressexception",
        "layer": "customer-code-or-mail-product-layer",
        "headline": ("The failure is a malformed recipient/sender address in "
                     "the application (client-side exception), not a network "
                     "or port issue."),
        "explanation": ("An SMTP conversation never started (or is "
                        "irrelevant): the library rejected the address "
                        "string locally."),
        "actions": (
            "Validate the address format used by the sending code "
            "(manual, customer-side).",
            "If a managed mail product (for example a mail-push service) is "
            "involved, raise it with that product's support channel.",
        ),
        "not_this_skill": "Out of this skill's scope: product configuration "
                          "and application code.",
        "source": "ticket T-E561A8DF (javax.mail AddressException: Illegal "
                  "address)",
    },
    {
        "id": "ip-usage-permission",
        "regex": (r"permission\s+to\s+use\s+(this|the|your)\s+ip|"
                  r"ip\s+(address\s+)?(is\s+)?not\s+authorized|"
                  r"no\s+.{0,20}permission.{0,20}ip"),
        "layer": LAYER_APPLY_ELIGIBILITY,
        "headline": ("The unblock application rejected the IP: the address "
                     "used in the application is not an eligible "
                     "VPC-mode public IP."),
        "explanation": ("Real-ticket cause: the application must reference "
                        "the instance's VPC public IP; a non-VPC / legacy IP "
                        "form triggers the 'no permission to use this IP' "
                        "style error. The console message is localized; this "
                        "signature covers its English equivalent wording."),
        "actions": (
            "Run this script first: it pre-checks the instance's public-IP "
            "form (fixed public IP vs EIP) from DescribeInstances.",
            "Re-submit the application referencing the VPC-mode public IPv4 "
            "address shown by this skill.",
            "If the IP is an EIP, verify the EIP is associated with the "
            "instance at application time.",
        ),
        "not_this_skill": "Not a connectivity fault; nothing to fix in the "
                          "guest.",
        "source": "ticket T-384967AE (customer: 'no IP usage permission'; "
                  "agent: 'use the VPC public IP address' -> resolved)",
    },
    {
        "id": "smtp-550-generic",
        "regex": r"\b550\b.{0,60}(spam|blacklist|blocked|reject|denied)|"
                 r"blacklist|spamhaus",
        "layer": LAYER_PEER_APPLICATION,
        "headline": "The receiving server rejected the message at the "
                     "application layer (spam/identity policy).",
        "explanation": ("A 5xx reply proves the SMTP session was reached. "
                        "Provider-side identity/anti-spam policy, not the "
                        "cloud port policy."),
        "actions": (
            "Verify sending-domain identity: SPF record, matching HELO "
            "hostname, rDNS expectations (see the PTR note: custom PTR is "
            "not self-service).",
            "Ask the receiving provider for the rejection reason and "
            "delist procedure.",
        ),
        "not_this_skill": "Do not confuse with the platform port-25 block.",
        "source": "provider-side rejections in tickets T-BFFFC987 / "
                  "T-8E8AD7A5 (family)",
    },
)

# ---------------------------------------------------------------------------
# The three guest facts no cloud API can return. Preferred source is the
# confirmation-gated GUEST_PROBES dispatch above (one probe, after the user
# approves it). This checklist is the fallback: it is emitted verbatim when
# the guest channel is unavailable (Cloud Assistant agent offline, the
# `run-command` grant missing, Windows guest) or the customer declines the
# probe, and the pasted results feed the same attribution tree via
# --port-result / --listener-25. Every command listed prints state and
# changes nothing.
# ---------------------------------------------------------------------------

READINGS = (
    {
        "id": "port-matrix",
        "title": ("TCP reachability matrix from the instance to the mail "
                  "target: port 25 vs 465/587 vs 80/443"),
        "why": ("Separates the platform port-25 block (25 silently times out "
                "while 465/587/443 succeed) from a customer security-group / "
                "firewall problem (ALL mail ports fail, often 443 too)."),
        "commands": (
            "telnet <target-host> <port>      # one per port: 25 465 587 443",
            "or: nc -vz -w 8 <target-host> <port>",
            "or (no nc/telnet): timeout 8 bash -c \"</dev/tcp/<target-host>/<port>\" "
            "&& echo OPEN || echo UNREACHABLE",
            "Windows: Test-NetConnection <target-host> -Port <port>",
        ),
        "report_back": ("For EACH port say which of: instant banner/OK, "
                        "connected then closed, refused, or silent timeout "
                        "(and the wall time)."),
        "note": ("A successful TCP connect does NOT mean mail will be "
                 "accepted -- also capture the SMTP banner and any 4xx/5xx "
                 "reply (ticket T-8E8AD7A5 proved both states coexist)."),
    },
    {
        "id": "listener",
        "title": "What listens on 25/465/587 inside the instance (and whether "
                 "container ports are mapped to the host)",
        "why": ("Receiving-side failures in tickets came from the MTA not "
                "listening on the host or a container port never published "
                "to the host interface."),
        "commands": (
            "ss -lntp        # look for 0.0.0.0:25 / :465 / :587 listeners",
            "docker ps --format '{{.Names}} {{.Ports}}'   # if mail runs in a container",
        ),
        "report_back": "Paste the ss output lines mentioning mail ports, plus the docker port list if used.",
        "note": "Inspection only: these commands read state and change nothing.",
    },
    {
        "id": "local-firewall",
        "title": "Guest-local firewall ruleset in effect",
        "why": ("A local iptables/firewalld/nftables rule blocks mail ports "
                "regardless of cloud security groups."),
        "commands": (
            "iptables -S",
            "nft list ruleset        # if nftables is used",
            "firewall-cmd --list-all # if firewalld is used",
            "Windows: Get-NetFirewallRule -Direction Outbound -Enabled True | Select-Object -First 50",
        ),
        "report_back": "Paste the output (or say explicitly 'no local firewall rules').",
        "note": ("These are read/export commands; this skill never proposes "
                 "any iptables/firewalld change -- remediation guidance is "
                 "manual and risk-noted."),
    },
)

# ---------------------------------------------------------------------------
# GUEST PROBES -- the complete, closed set of commands this skill may execute
# inside an instance (RO+G path, Cloud Assistant `ecs RunCommand`).
#
# HARD RULES enforced by this table + the entry script:
#   * Only the templates below exist. Free-form command text can never be
#     submitted: the entry script accepts a probe ID, never a command.
#   * The only substitutions are the target host and port list, and both must
#     first pass the entry script's strict regex / integer validation.
#   * Every template is inspection-only: it prints state and changes nothing.
#     No file is written (all redirections target /dev/null), no package,
#     service, firewall, route, mount or process is touched, and no
#     `systemctl`/`service`/`reboot`/`kill` form appears anywhere below.
#   * Exactly ONE probe per run, and only with the confirmation token.
#   * Windows guests are not probed by this skill in this tier (no ticket
#     evidence); their checks stay on the manual READINGS checklist.
# ---------------------------------------------------------------------------

GUEST_PROBES = {
    "port-probe": {
        "command_type": "RunShellScript",
        "title": "TCP reachability matrix from the instance to the mail target",
        "requires": ("--probe-host and at least one --probe-port (default: "
                     "25, 465, 587, 443 when --target-port is not given)"),
        "reads": ("Whether each tested port silently times out (platform "
                  "block signature), refuses (reachable, nothing accepting) "
                  "or opens."),
        "why": ("The single most decisive fact in this tier and the one no "
                "cloud API exposes: 25 timeout + 465/587/443 open means the "
                "platform outbound-25 policy; 25 AND 465/587 timeout with 443 "
                "open means the customer's own egress path "
                "(ticket T-897D4DEA)."),
        "disclosure": ("Runs one short script in the instance that opens and "
                       "closes TCP test connections to the named mail target "
                       "and prints one line per port. It writes no files, "
                       "changes no configuration and needs no restart; a "
                       "blocked port costs the connect timeout (about 8 "
                       "seconds each, up to 6 ports)."),
        "reversible": "nothing to undo -- no state is written anywhere",
        "template": """#!/bin/sh
# ecs-smtp-block-diagnosis port probe: inspection only, changes nothing.
HOST="__HOST__"
PORTS="__PORTS__"
TMO=__TIMEOUT__
if ! command -v bash >/dev/null 2>&1; then
  echo "PROBE port-probe SKIPPED reason=bash-not-found"
  exit 0
fi
if command -v timeout >/dev/null 2>&1; then
  GUARD="timeout $TMO"
else
  GUARD=""
fi
for p in $PORTS; do
  $GUARD bash -c "exec 3<>/dev/tcp/$HOST/$p" </dev/null >/dev/null 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "PORT $p TCP-OPEN"
  elif [ "$rc" -eq 124 ]; then
    echo "PORT $p TCP-TIMEOUT"
  elif [ -z "$GUARD" ]; then
    echo "PORT $p TCP-FAIL-UNGUARDED rc=$rc"
  else
    echo "PORT $p TCP-REFUSED rc=$rc"
  fi
done
echo "PROBE port-probe COMPLETE"
""",
    },
    "listener": {
        "command_type": "RunShellScript",
        "title": "What listens on the mail ports, host-side, and what containers publish",
        "requires": "no target needed",
        "reads": ("Host listeners on 25/465/587/993/995, plus the port "
                  "mapping each running container publishes, plus which mail "
                  "daemons appear in the process table."),
        "why": ("Receive-side failures in this tier's evidence came from the "
                "MTA never bound on the host or a container port not "
                "published to it (ticket T-065FBFCF). Cloud APIs cannot see "
                "this."),
        "disclosure": ("Runs one short script in the instance that lists "
                       "open listening sockets, running container port "
                       "mappings and mail daemon process names. An "
                       "inspection-only listing: no socket is opened, closed "
                       "or rebound, no service is queried with control "
                       "verbs, no file is written, finishes in a couple of "
                       "seconds."),
        "reversible": "nothing to undo -- pure listing",
        "template": """#!/bin/sh
# ecs-smtp-block-diagnosis listener probe: inspection only, changes nothing.
if command -v ss >/dev/null 2>&1; then
  echo "== ss -lntp =="
  ss -lntp 2>/dev/null || echo "ss not readable (needs root)"
elif command -v netstat >/dev/null 2>&1; then
  echo "== netstat -lntp =="
  netstat -lntp 2>/dev/null || echo "netstat not readable (needs root)"
else
  echo "== no socket listing tool installed =="
fi
echo "== mail-port listeners =="
(ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null) \\
  | grep -E ':(25|465|587|993|995)[[:space:]]' || echo "NONE"
if command -v docker >/dev/null 2>&1; then
  echo "== container published ports =="
  docker ps --format '{{.Names}} {{.Ports}}' 2>/dev/null \\
    || echo "docker listing unavailable (daemon or permission)"
fi
if command -v ps >/dev/null 2>&1; then
  echo "== mail daemons in process table =="
  ps -eo comm 2>/dev/null \\
    | grep -E '^(master|sendmail|postfix|exim4|dovecot|dockerd)$' \\
    | sort -u || echo "NONE"
fi
echo "PROBE listener COMPLETE"
""",
    },
    "firewall": {
        "command_type": "RunShellScript",
        "title": "Local firewall ruleset actually in effect in the guest",
        "requires": "no target needed",
        "reads": ("The iptables/nftables/firewalld rule set as configured, "
                  "filtered to the parts that can swallow mail ports."),
        "why": ("A guest-local rule blocks mail independently of the cloud "
                "security group; it is the second half of the customer "
                "config layer and is invisible to every cloud API."),
        "disclosure": ("Runs one short script that PRINTS the current "
                       "firewall configuration (iptables -S, a filtered nft "
                       "ruleset listing, firewalld's configured state). It "
                       "adds, deletes, flushes or reloads nothing, writes no "
                       "file, and only needs root to read rules that were "
                       "installed with root."),
        "reversible": "nothing to undo -- rule listing only",
        "template": """#!/bin/sh
# ecs-smtp-block-diagnosis firewall probe: prints rules, changes nothing.
if command -v iptables >/dev/null 2>&1; then
  echo "== iptables -S =="
  iptables -S 2>/dev/null || echo "iptables listing not readable (needs root)"
else
  echo "== iptables not installed =="
fi
if command -v nft >/dev/null 2>&1; then
  echo "== nft ruleset (filtered) =="
  nft list ruleset 2>/dev/null | head -n 120 || echo "nft listing not readable"
fi
if command -v firewall-cmd >/dev/null 2>&1; then
  echo "== firewalld configured state =="
  firewall-cmd --state 2>/dev/null
  firewall-cmd --list-all 2>/dev/null || echo "firewalld not queryable"
fi
echo "== rules naming mail ports =="
(iptables -S 2>/dev/null; nft list ruleset 2>/dev/null) \\
  | grep -E '(25|465|587|993|995)' | grep -Ei 'drop|reject|accept|dport' \\
  | head -n 40 || echo "NONE"
echo "PROBE firewall COMPLETE"
""",
    },
    "path-info": {
        "command_type": "RunShellScript",
        "title": "Egress route, interface and name resolution for the mail target",
        "requires": "--probe-host (target hostname or IPv4)",
        "reads": ("Which interface and next hop carries traffic to the mail "
                  "target, the addresses bound on that interface, and how the "
                  "target name resolves (plus its MX records where dig "
                  "exists)."),
        "why": ("Separates 'no egress path at all' from a port-level policy, "
                "and exposes the IPv4/IPv6 resolution split that decides "
                "whether the 25 question is even answerable on this "
                "instance's addressing (ticket T-F418FAF1 pattern)."),
        "disclosure": ("Runs one short script that prints the routing table, "
                       "the route selected toward the named target, the "
                       "interface address summary and a name lookup. It adds "
                       "or deletes no route, brings no interface up or down, "
                       "writes no file; a few seconds."),
        "reversible": "nothing to undo -- pure listing",
        "template": """#!/bin/sh
# ecs-smtp-block-diagnosis path probe: inspection only, changes nothing.
HOST="__HOST__"
echo "== ip route =="
ip route 2>/dev/null || route -n 2>/dev/null || echo "no routing listing tool"
echo "== selected route toward target =="
ip route get "$HOST" 2>/dev/null || echo "ip route get unsupported"
echo "== interface address summary =="
ip -brief addr 2>/dev/null || ifconfig 2>/dev/null || echo "no addr tool"
echo "== name resolution =="
getent hosts "$HOST" 2>/dev/null || nslookup "$HOST" 2>/dev/null \\
  || echo "no resolver output"
if command -v dig >/dev/null 2>&1; then
  echo "== MX records for target =="
  dig +short MX "$HOST" 2>/dev/null || echo "dig query failed"
fi
echo "PROBE path-info COMPLETE"
""",
    },
}

# The ports probed when the caller names no target port.
PROBE_DEFAULT_PORTS = (25, 465, 587, 443)

# Things that must NEVER appear in a dispatched command. The entry script
# re-checks every rendered template against this list as defence-in-depth: a
# future edit adding a state-changing verb fails closed instead of shipping.
# Output redirection is policed separately by PROBE_REDIRECT_RE below, since
# "writes nothing" means "no redirect target outside /dev", not "no '>'".
PROBE_PROHIBITED_TOKENS = (
    "rm ", "rmdir", "mkfs", "dd ", "truncate", "tee ",
    "iptables -I", "iptables -A", "iptables -F", "iptables -P", "ip6tables -",
    "nft add", "nft create", "nft delete", "nft flush", "nft insert",
    "firewall-cmd --add", "firewall-cmd --remove", "firewall-cmd --reload",
    "systemctl", "service ", "reboot", "shutdown", "kill", "pkill",
    "mount", "umount", "fdisk", "parted", "useradd", "usermod", "passwd",
    "crontab", "sed -i", "chmod", "chown", "mv ", "cp ", "touch ",
    "ip route add", "ip route del", "ip link set", "ifconfig up",
    "docker run", "docker rm", "docker stop", "docker start", "docker restart",
    "yum ", "apt ", "apt-get", "pip install", "curl -o", "wget ",
)

# Every output redirect in a probe must land on /dev/null or on bash's
# /dev/tcp|/dev/udp pseudo-devices -- never on a real path. A "&" target is
# file-descriptor duplication (the "2>&1" idiom), not a write.
PROBE_REDIRECT_RE = re.compile(r">{1,2}\s*(\S+)")
PROBE_ALLOWED_REDIRECT_PREFIXES = ("/dev/null", "/dev/tcp", "/dev/udp", "&")


def _redirect_violations(text: str) -> list:
    """Output-redirect targets that would write somewhere real."""
    bad = []
    for target in PROBE_REDIRECT_RE.findall(text):
        if not target.startswith(PROBE_ALLOWED_REDIRECT_PREFIXES):
            bad.append(target)
    return bad


def render_probe_template(probe_id: str, host: str = "",
                          ports: tuple = ()) -> str:
    """Substitute the validated values into a whitelisted template.

    Placeholders are replaced (never str.format): the templates contain shell
    braces such as '{{.Names}}' that a format call would corrupt. The result
    is then re-checked against PROBE_PROHIBITED_TOKENS and the redirect rule,
    and any probe id outside GUEST_PROBES is refused -- so this function is
    the last gate between a validated request and the command string that
    reaches the instance.
    """
    probe = GUEST_PROBES.get(probe_id)
    if probe is None:
        raise ValueError(f"unknown probe id: {probe_id!r}")
    text = probe["template"]
    if "__HOST__" in text:
        text = text.replace("__HOST__", host)
    if "__PORTS__" in text:
        text = text.replace("__PORTS__", " ".join(str(p) for p in ports))
    if "__TIMEOUT__" in text:
        text = text.replace("__TIMEOUT__",
                            str(PROBE_CONNECT_TIMEOUT_SECONDS))
    lowered = text.lower()
    hits = [tok for tok in PROBE_PROHIBITED_TOKENS if tok.lower() in lowered]
    if hits:
        raise ValueError(
            f"probe {probe_id!r} contains prohibited token(s): {hits}")
    bad_redirects = _redirect_violations(text)
    if bad_redirects:
        raise ValueError(
            f"probe {probe_id!r} would write to: {bad_redirects}")
    return text


# Boundary tests: the shipped templates must pass their own guard, and the
# guard must be able to fail (a guard that cannot fail is not a guard).
assert render_probe_template("listener").rstrip().splitlines()[-1] == 'echo "PROBE listener COMPLETE"'
assert "ss -lntp" in render_probe_template("listener")
assert render_probe_template("port-probe", "smtp.example.com",
                             (25, 465)).splitlines()[0] == "#!/bin/sh"
assert 'PORTS="25"' in render_probe_template(
    "port-probe", "smtp.example.com", (25,))
assert "TCP-TIMEOUT" in render_probe_template(
    "port-probe", "smtp.example.com", (25,))
assert "__HOST__" not in render_probe_template("path-info", "smtp.example.com")
# The guard must catch both classes of escape: a state-changing verb and a
# redirect out of /dev. Only the redirect rule can see the second one.
try:
    render_probe_template("nope")
    raise AssertionError("unknown probe id accepted")
except ValueError:
    pass  # expected
try:
    render_probe_template("path-info", "x.example.com > /root/leak")
    raise AssertionError("redirect-to-file injection accepted")
except ValueError:
    pass  # expected
assert _redirect_violations("echo hi > /tmp/x") == ["/tmp/x"]
assert _redirect_violations("echo hi > /dev/null 2>&1") == []
# The four shipped probes must all clear both guards.
for _pid in GUEST_PROBES:
    render_probe_template(_pid, "smtp.example.com", (25, 465, 587))


# ---------------------------------------------------------------------------
# Verdict guidance blocks (manual steps plus confirmation-gated probes; the
# skill never applies a configuration change or submits an application)
# ---------------------------------------------------------------------------

GUIDANCE_BLOCKS = {
    "platform-block": (
        "State the unified policy wording (POLICY_STATEMENTS['outbound-25-default']).",
        "First fix = use an authenticated submission port: 465 (implicit TLS) "
        "or 587 (STARTTLS) with the mail provider -- no application needed "
        "from Alibaba Cloud (provider account credentials required instead).",
        "If the business truly needs direct outbound 25: run the eligibility "
        "pre-check (this script), then the customer applies via the console "
        "entry described in APPLICATION_ENTRY; review ~1 business day, result "
        "by email, approval not guaranteed.",
        "Agreement honesty rule (POLICY_STATEMENTS['agreement-scope']): if "
        "the use case is a self-hosted MTA delivering straight to remote MX "
        "hosts, set expectations: review typically refuses; recommend an "
        "external relay (third-party SMTP on 465 / corporate mail / a mail "
        "delivery service) instead of misdeclaring the purpose.",
        "Docs: DOC_LINKS['ecs-limits'], DOC_LINKS['ssl-465-example'], "
        "DOC_LINKS['unblock-application-doc'].",
    ),
    "customer-config": (
        "Do NOT claim the platform blocked the port: 465/587 failing means "
        "the customer path is broken (POLICY_STATEMENTS['secure-ports-open']).",
        "Customer-side checklist, in order: (1) security-group OUTBOUND "
        "rules -- a rule set that only allows a narrow egress list will "
        "swallow 465/587 even when 80/443 pass; (2) guest-local firewall "
        "ruleset from the READINGS; (3) provider-side reachability of the "
        "chosen host/port.",
        "Guide the security-group review with the quickstart doc "
        "(DOC_LINKS['security-group-quickstart']); this skill never edits "
        "rules for the customer -- state the risk note: egress rule changes "
        "widen the attack surface, minimal precise allowances only.",
        "After each customer-side change the customer re-runs the port "
        "matrix to verify (one change, one retest).",
    ),
    "peer-application": (
        "Explain the signature verdict from references/smtp-error-"
        "signatures.md and relay its actions.",
        "Keep the customer OUT of the port-25 unblock path: the SMTP session "
        "was reached (banner/replies prove it).",
        "Provider side: identity (HELO/FQDN), SPF alignment, throttling "
        "review -- the customer asks their mail provider.",
    ),
    "receive-inbound": (
        "Check in order: (1) MTA actually listening on 0.0.0.0:25 on the "
        "HOST (READINGS['listener']; container mail stacks must publish the "
        "port -- ticket T-065FBFCF root cause was an unmapped container); "
        "(2) security-group INBOUND rule allowing TCP 25 from 0.0.0.0/0 or "
        "specific senders; (3) guest firewall INPUT chain "
        "(READINGS['local-firewall']).",
        "Platform inbound-25 policy is UNCONFIRMED "
        "(POLICY_STATEMENTS['inbound-25']): verify with official documentation or "
        "human support before promising anything; do not tell the customer "
        "inbound needs no application OR that it definitely needs one.",
        "MX records must point at this instance's public IPv4.",
    ),
    "eligibility": (
        "Apply the pre-check output: VPC-mode public IPv4 required; IPv6 "
        "targets are not supported for 25 (POLICY_STATEMENTS['ipv6-25']); "
        "self-hosted MTA direct-MX use case is refused per agreement; "
        "custom PTR not self-service (POLICY_STATEMENTS['ptr']).",
        "Application material list for the customer: instance id, the VPC "
        "public IPv4, the REAL use case, agreement consent, a reachable "
        "contact email for the review result.",
        "Sub-accounts (RAM users) that cannot view application status or "
        "submit: identity self-check first (this script prints the caller "
        "identity), then hand off to the RAM policy diagnosis flow -- this "
        "skill never changes grants.",
        "Application history / review status has NO public query API: the "
        "customer checks their own console + the result email; state this "
        "limit plainly.",
    ),
    "cross-border": (
        "Evidence pattern: overseas-region instance to a domestic mail "
        "provider (or reverse): TCP reachable / banner OK but sessions slow "
        "or stalled (451 Timeout), while the same config works from a "
        "same-side region.",
        "Verdict: not a port policy; hand off to the cross-border link "
        "diagnosis flow and/or move sending to a same-side host or "
        "provider (ticket T-8E8AD7A5 resolved by switching to a domestic "
        "provider endpoint).",
    ),
    "degraded": (
        "State exactly which fact is missing, then prefer the confirmation-"
        "gated probe: name the probe (GUEST_PROBES id), relay its `disclosure`"
        " text, and only dispatch it once the user approves (guest-gate).",
        "Fall back to the manual READINGS checklist when the probe channel is"
        " unusable (Cloud Assistant agent offline, no `run-command` grant,"
        " Windows guest, or the customer declines): output it verbatim and"
        " re-run with --port-result / --listener-25 values when they answer.",
        "While degraded, only the cloud-side facts (instance, IP form, "
        "security-group ids, status) may be concluded on.",
    ),
    "guest-gate": (
        "Before ANY probe, show the user all four parts and wait for a clear"
        " yes: (1) WHICH command -- the probe title plus the exact script"
        " text that will run, printed in full;"
        " (2) SCOPE -- this one instance, this one command, inspection only;"
        " (3) REVERSIBILITY -- the probe's `reversible` line; there is"
        " nothing to undo, and no configuration, file, service, firewall or"
        " route is touched;"
        " (4) DURATION -- the Cloud Assistant Timeout plus the per-port"
        " connect guard.",
        "The script refuses to dispatch without --user-confirmation set to"
        " the exact token, so the gate cannot be skipped by accident, and one"
        " probe per run means no chaining without a fresh disclosure."
        "State-changing requests (open a port, restart a service, edit a"
        " security group, submit an application) are refused outright and"
        " answered with manual steps plus a risk note instead.",
    ),
    "unresolved": (
        "When every layer is eliminated and failures persist (intermittent "
        "resets, flapping), this skill's evidence ends: hand to human "
        "support with a material list -- failure time window, full session "
        "transcript, customer-side packet capture, the port matrix and "
        "listener/firewall readings already collected.",
        "Packet-level analysis is explicitly NOT performed here.",
    ),
}

# ---------------------------------------------------------------------------
# Handoff rules: out-of-scope signals recognized in the customer's own words
# or in the collected evidence (routing only -- no diagnosis happens here).
# ---------------------------------------------------------------------------

HANDOFF_RULES = (
    {
        "id": "non-mail-port",
        "match": r"\b(ssh|22|rdp|3389|http|https|80|443)\b.{0,40}(fail|reset|timeout|blocked|cannot|can't|unable)",
        "target": "area:ssh-connection (22), area:windows-rdp (3389), "
                  "area:web-inaccessible-slow (80/443), or "
                  "alibabacloud-ecs-vpc-publicnetwork-troubleshoot (general "
                  "public-network reachability)",
        "sentence": ("The failing port is not a mail port; this skill only "
                     "covers mail (25/465/587/993/995) semantics. Route to "
                     "the matching connectivity skill above."),
    },
    {
        "id": "mail-product",
        "match": (r"(directmail|mail\s*push|alibaba\s*mail|alimail|"
                  r"qiye\s*mail|qiye\.aliyun|enterprise\s*mail)"),
        "target": "the mail product's own console / support channel",
        "sentence": ("This concerns mail-product (Alibaba Mail / DirectMail) "
                     "configuration, not the ECS network path: hand off; "
                     "ECS-side diagnosis stops at SMTP reachability."),
    },
    {
        "id": "punishment-block",
        "match": r"(violation|breach|prohibited).{0,30}(block|shield|punish)|content.{0,20}block",
        "target": "area:punishment-appeal-guide",
        "sentence": ("The block stems from content/policy enforcement, not "
                     "the mail-port policy; appeal flow belongs to the "
                     "punishment-handoff skill."),
    },
    {
        "id": "ram-subaccount",
        "match": r"(sub\s*-?\s?account|ram\s*user|sub[- ]user).{0,50}(cannot|no permission|view|apply|submit)",
        "target": "area:ram-policy-diagnosis",
        "sentence": ("The gap is RAM authorization (viewing the block state "
                     "or submitting the application), not the mail path; the "
                     "identity self-check above shows which principal is in "
                     "use -- hand off for the grant review."),
    },
    {
        "id": "console-notification-mail",
        "match": r"(notification\s*email|console\s*email|resource\s*notice).{0,40}(not\s*found|cannot\s*see|missing)",
        "target": "area:console-resource-lookup",
        "sentence": ("This is a console-notification / resource-visibility "
                     "question, unrelated to SMTP sending (false-hit "
                     "pattern seen in ticket evidence)."),
    },
    {
        "id": "cross-border",
        "match": r"(cross[- ]?border|overseas).{0,40}(slow|loss|unstable|"
                 r"timeout|451|drop|fail)",
        "target": "area:cross-border-link-diagnosis, "
                  "area:network-quality-bandwidth",
        "sentence": ("TCP is established; the remaining symptoms point to "
                     "cross-border link quality or the peer's overseas-IP "
                     "policy -- that link diagnosis belongs to the "
                     "cross-border skill, not to the port-25 path."),
    },
    {
        "id": "refund-commerce",
        "match": r"(refund|unsubscribe|order|invoice|payment|renewal)",
        "target": "area:unsubscribe-refund / human "
                  "commercial support",
        "sentence": "Commercial/order processing is outside this skill.",
    },
)

# Domestic-provider mail hosts frequently used as relay examples in tickets;
# used ONLY as a hint table in guidance text, never as a promise.
RELAY_EXAMPLES = (
    "smtp.qiye.aliyun.com (Alibaba Mail)",
    "smtpdm.aliyun.com:465 (DirectMail)",
    "any external provider's 465/587 submission endpoint",
)

# ---------------------------------------------------------------------------
# Report framing helpers
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# Regions whose ids start with these prefixes are outside the Chinese
# mainland (used for the cross-border heuristic ONLY; never for policy
# claims -- see POLICY_STATEMENTS['overseas-25']).
OVERSEAS_REGION_PREFIXES = ("ap-", "us-", "eu-", "me-", "na-")
# 'cn-hongkong' is also treated as outside the mainland heuristic set.
EXTRA_OVERSEAS_REGIONS = ("cn-hongkong",)

# Domestic mail-provider host fragments for the cross-border heuristic
# (instance overseas + target domestic + session-level failure).
DOMESTIC_PROVIDER_HINTS = (
    "qq.com", "exmail.qq.com", "163.com", "126.com", "qiye.163.com",
    "sina.com", "sina.cn", "aliyun.com", "qiye.aliyun.com", "foxmail.com",
    "yeah.net", "tom.com", "21cn.com",
)
