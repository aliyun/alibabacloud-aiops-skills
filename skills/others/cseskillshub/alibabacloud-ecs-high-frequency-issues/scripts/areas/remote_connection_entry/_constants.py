#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and read-only knowledge for the ECS
remote-connection entry triage skill.

SECURITY: This skill is strictly READ-ONLY. This module holds constants only:
no credentials, no network calls, no executable side effects. Credentials for
the actual queries are resolved exclusively by the aliyun CLI default
credential chain (see _cli.py); nothing here reads, prints or stores them.

Knowledge lives in code or in references/, never in ad-hoc data files: every
static table this skill needs (API whitelist, port mapping, error signature
catalog, handoff sentences, customer-run self-check commands, risk notices) is
embedded here as Python constants. The only non-code file under scripts/ is
requirements.txt, a manifest that declares no dependencies at all.
"""

# ---------------------------------------------------------------------------
# Skill identity & observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-remote-connection-entry"
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"

# ---------------------------------------------------------------------------
# API surface (all READ-ONLY). _cli.py enforces this whitelist on every call;
# any action not listed here can never leave this process.
# The set is identical to related_apis.yaml and references/ram-policies.md.
# ---------------------------------------------------------------------------

ECS_PRODUCT = "ecs"
STS_PRODUCT = "sts"
CMS_PRODUCT = "cms"

API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
    "cms": "2019-01-01",
}

API_WHITELIST = frozenset({
    (ECS_PRODUCT, "DescribeInstances"),
    (ECS_PRODUCT, "DescribeSecurityGroupAttribute"),
    (ECS_PRODUCT, "DescribeCloudAssistantStatus"),
    (ECS_PRODUCT, "DescribeInstanceVncUrl"),
    (STS_PRODUCT, "GetCallerIdentity"),
    (CMS_PRODUCT, "DescribeMetricLast"),
})

# ---------------------------------------------------------------------------
# Timeouts / retry / guardrails (every CLI call carries a timeout)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60          # seconds, per subprocess call
MAX_ATTEMPTS = 3              # total attempts for transient errors
BACKOFF_BASE_SECONDS = 2      # retry N waits N * this
MAX_SG_GROUPS = 10            # guardrail: security groups inspected per run
MAX_DATAPOINTS = 20           # guardrail: metric datapoints parsed per metric

# ---------------------------------------------------------------------------
# Protocol / port routing
# ---------------------------------------------------------------------------

SSH_DEFAULT_PORT = 22
RDP_DEFAULT_PORT = 3389

# OS type (from DescribeInstances OSType) -> protocol + default port.
OS_PROTOCOL = {
    "linux": ("SSH", SSH_DEFAULT_PORT),
    "windows": ("RDP", RDP_DEFAULT_PORT),
}

# Client tool (lowercased) -> the protocol the tool actually speaks on the
# default port. A mismatch against the instance OS is itself a finding
# (e.g. an SSH client pointed at a Windows instance: Windows ships without
# an SSH listener enabled, so "Could not connect to ... (port 22)" is the
# expected outcome, not a cloud fault).
TOOL_PROTOCOL_HINTS = {
    "xshell": "SSH",
    "finalshell": "SSH",
    "securecrt": "SSH",
    "putty": "SSH",
    "mobaxterm": "SSH",
    "termius": "SSH",
    "winscp": "SSH",   # SFTP rides the SSH port
    "xftp": "SSH",
    "bastion": "SSH",  # a bastion host typically brokers SSH
    "mstsc": "RDP",
    "remote-desktop": "RDP",
    "windows-app": "RDP",
}

SSH_PORTS_HINT = "SSH listens on 22 unless a custom port was configured (e.g. 10022)"

# ---------------------------------------------------------------------------
# CloudMonitor reading used for the saturation pre-screen.
# Only the well-documented standard ECS metric is queried by default;
# the metric set stays minimal until each metric name is separately
# verified -- never pass unverified names.
# ---------------------------------------------------------------------------

CMS_NAMESPACE = "acs_ecs_dashboard"
CMS_METRICS_DEFAULT = ("cpu_total",)     # MetricName values, verified set
CPU_SATURATION_PCT = 95.0                # >= this latest average -> hang signal

# ---------------------------------------------------------------------------
# Error / symptom signature catalog (customer-quotable strings -> branch).
# Branch ids resolve in references/remote-connection-entry__triage-tree.md and
# references/remote-connection-entry__error-signatures.md.
# ---------------------------------------------------------------------------

ERROR_SIGNATURES = (
    {
        "id": "credential",
        "patterns": ("permission denied", "authentication failed",
                     "incorrect password", "login failed",
                     "too many authentication failures",
                     "no supported authentication methods"),
        "branch": "S4 credential exit: authentication was REACHED but rejected",
        "guidance": ("Wrong password/key, or no acceptable authentication method "
                     "offered. Direct the customer to the console credential "
                     "reset flow (see references/remote-connection-entry__help-links.md): an online reset "
                     "needs no reboot but depends on the Cloud Assistant agent, "
                     "while an offline reset and a key-pair bind or unbind take "
                     "effect only after an instance restart. Editing sshd_config "
                     "needs a separate SSH service restart. Never collect or "
                     "test the customer password in this skill."),
    },
    {
        "id": "pam",
        "patterns": ("uid >= 1000", "user locked", "pam_", "pam authentication",
                     "account is disabled"),
        "branch": "S4 credential exit: in-guest PAM policy rejects the login",
        "guidance": ("A PAM policy inside the guest rejects the login even with "
                     "the correct password, so the credential only looks wrong. "
                     "Have the customer enter through VNC (that channel is not "
                     "gated by PAM) and follow the documented PAM adjustment or "
                     "account-unlock guidance; this skill changes nothing."),
    },
    {
        "id": "host-key",
        "patterns": ("host key verification failed",
                     "remote host identification has changed",
                     "man in the middle", "possible attack on your network"),
        "branch": "S4 tool exit: client-side stored host key no longer matches",
        "guidance": ("The instance was reinstalled or its host key changed, so "
                     "the client refuses to connect. After the customer confirms "
                     "the change was expected, they remove the stale entry from "
                     "their own known_hosts file on their own machine. This is a "
                     "client-side record mismatch, not a server fault."),
    },
    {
        "id": "sshd-config",
        "patterns": ("bad configuration options", "cannot bind any address",
                     "main process exited",
                     "error while loading shared libraries"),
        "branch": "S4 guest exit: sshd cannot start",
        "guidance": ("sshd itself cannot start: a syntax error in "
                     "/etc/ssh/sshd_config, an address that cannot be bound, or "
                     "damaged libraries. The customer validates the config and "
                     "restarts the SSH service from their own VNC session "
                     "(references/remote-connection-entry__guest-selfcheck-commands.md); this skill never "
                     "runs anything in the guest."),
    },
    {
        "id": "file-permission",
        "patterns": ("must be owned by root", "not group or world-writable",
                     "unprotected private key file",
                     "no supported key exchange algorithms"),
        "branch": "S4 guest exit: SSH file or directory ownership is wrong",
        "guidance": ("SSH refuses for ownership or permission reasons on "
                     "~/.ssh, authorized_keys or the host keys. Guide the "
                     "documented permission corrections, run by the customer "
                     "inside their own VNC session."),
    },
    {
        "id": "resource-limit",
        "patterns": ("connection reset by peer", "fork: cannot allocate memory",
                     "cannot allocate memory", "resource temporarily unavailable",
                     "ssh_exchange_identification", "mm_request_send",
                     "broken pipe"),
        "branch": "S4 guest exit: process/memory exhaustion at handshake time",
        "guidance": ("Classic guest-side process-slot exhaustion (fork "
                     "failure breaks the SSH handshake). Ask the customer to "
                     "check the login log and process limits inside the "
                     "instance via VNC (references/remote-connection-entry__guest-selfcheck-commands.md "
                     "step 5) and apply the documented limit-raising guide."),
    },
    {
        "id": "tool-local",
        "patterns": ("websocket", "could not negotiate", "handshake",
                     "unexpected disconnect", "closed unexpectedly"),
        "branch": "S4 tool/local exit: command line and VNC work, tool fails",
        "guidance": ("Tool-side WebSocket/proxy issue. Run the comparison "
                     "matrix: ssh from cmd/PowerShell vs the GUI tool vs VNC; "
                     "then disable local proxy/VPN, retry over a phone "
                     "hotspot, or swap the client. Not a server fault when "
                     "the plain command line connects."),
    },
    {
        "id": "protocol-mismatch",
        "patterns": ("could not connect to", "connection failed"),
        "branch": "S2/S3 split: SSH client against a Windows image, or a "
                  "custom port not reflected in the client",
        "guidance": ("Confirm OS type first: Windows instances have no SSH "
                     "listener by default (use RDP 3389), and a custom SSH "
                     "port must be used consistently in client and security "
                     "group (see references/remote-connection-entry__securitygroup-checklist.md)."),
    },
    {
        "id": "silent-drop",
        "patterns": ("timed out", "timeout", "operation timed out",
                     "no route to host", "network is unreachable",
                     "network unreachable", "destination host unreachable"),
        "branch": "S3 network-path exit: packets dropped silently",
        "guidance": ("Silent drop: security-group port or source CIDR, guest "
                     "firewall, or no public path (zero public bandwidth, or "
                     "bandwidth stopped by an overdue balance). Check the SG "
                     "evidence, then have the customer run telnet/ssh -v "
                     "locally. A failed ping proves little on its own: ICMP may "
                     "be blocked while TCP is fine, so test the port, not only "
                     "the host."),
    },
    {
        "id": "refused-or-service",
        "patterns": ("connection refused", "port unreachable"),
        "branch": "S4 guest-listener exit: path is open, nothing answers",
        "guidance": ("Refusal means the packet reached the host and no "
                     "listener answered: sshd/RDP service down or listening "
                     "on another port. Customer-run checks: systemctl status "
                     "sshd (the unit is named ssh on Ubuntu and Debian) and "
                     "ss -lnt, both inside the instance via VNC."),
    },
    {
        "id": "keepalive",
        "patterns": ("idle", "automatically exit", "drops after",
                     "disconnected after", "session closed"),
        "branch": "S4 tool/local exit: sessions die while idle",
        "guidance": ("Idle-disconnect: apply the three-way keepalive template "
                     "(server-side sshd ClientAliveInterval 60 / "
                     "ClientAliveCountMax 10, with an SSH service restart by the "
                     "customer or it does not take effect; client-side "
                     "ServerAliveInterval 60 / ServerAliveCountMax 10; and the "
                     "idle timeout of any intermediate NAT/firewall)."),
    },
    {
        # Non-English customer wording is not substring-matched here: the agent
        # routes it through the explicit flags (--intrusion-suspect,
        # --client-tool, --console-ok) instead.
        "id": "generic-entry",
        "patterns": ("cannot remote", "can't connect", "cannot connect",
                     "unable to connect", "remote connection failed",
                     "cannot log in"),
        "branch": "S0/S1 entry: protocol unknown, run the full split",
        "guidance": ("Generic symptom; rely on the collected evidence (state, "
                     "OS, SG, VNC, monitoring) rather than guessing. Note that "
                     "'the console connects but my own tool does not' is not a "
                     "contradiction: the console channel does not require the "
                     "customer's egress IP to be authorized, a local client "
                     "does."),
    },
)

# Intrusion-suspicion keywords -> security handoff (identify and transfer,
# never investigate here). Suspicions raised in another language are signalled
# by the agent with --intrusion-suspect rather than matched as text.
INTRUSION_PATTERNS = ("attacked", "hack", "unauthorized login", "stranger ip",
                      "unknown ip logged", "unfamiliar ip", "compromised",
                      "intrusion", "suspicious login")

INTRUSION_NOTE = "intrusion suspicion routes to the security handoff exit"

# ---------------------------------------------------------------------------
# Customer-run guest self-check (read-only, executed BY THE CUSTOMER inside
# their own VNC/Workbench session; this skill never runs anything in-guest).
# (command, what to look for)
# ---------------------------------------------------------------------------

GUEST_SELFCHECK_COMMANDS = (
    ("systemctl status sshd",
     "active (running) and the listen port in the last lines; failed or "
     "inactive means the service itself is down. On Ubuntu and Debian the unit "
     "is named ssh, so run 'systemctl status ssh' there - a 'not found' error "
     "is the wrong unit name, not a dead service. Windows instances have no "
     "sshd at all: check the Remote Desktop listener on 3389 instead."),
    ("ss -lnt",
     "a socket listening on 0.0.0.0:22 (or the custom SSH port); for Windows "
     "confirm the RDP listener on 3389 via the Remote Desktop settings page"),
    ("sshd -t",
     "silence means /etc/ssh/sshd_config parses correctly; any complaint names "
     "the offending line. This only validates the config, it changes nothing"),
    ("iptables -L -n",
     "any DROP/REJECT touching the SSH/RDP port, and rule order matters"),
    ("systemctl status firewalld",
     "firewalld active without the service/port allowed blocks logins even "
     "when the security group is open"),
    ("cat /var/log/secure",
     "authentication-stage failures, fork failures, or unknown source IPs; "
     "on Debian-family systems the equivalent log path is read the same way"),
    ("df -h",
     "a 100%-full system disk frequently breaks sshd/login silently; if "
     "disk or inode usage is the story, hand off to the capacity skill"),
)

LOCAL_SELFCHECK_COMMANDS = (
    ("curl cip.cc",
     "prints the local egress public IP - compare with the security-group "
     "authorized source CIDR"),
    ("telnet <public-ip> <port>",
     "connected = path open; timeout = silent drop (SG/guest firewall/no "
     "public path); refused = nothing listening"),
    ("ssh -v root@<public-ip> -p <port>",
     "-v shows exactly which stage fails (connect, handshake, auth)"),
)

# ---------------------------------------------------------------------------
# Fixed customer-facing notices (wording distilled from real ticket answers;
# relay these, do not rewrite the safety facts).
# ---------------------------------------------------------------------------

RISK_NOTICES = {
    "restart": ("Restart plan (customer performs it in the console during a "
                "business off-peak window): stop the application writes first "
                "so data is flushed, create a snapshot beforehand for safety "
                "(snapshots bill separately - see the snapshot pricing doc in "
                "references/remote-connection-entry__help-links.md), then restart from the console."),
    "stopping": ("A normal stop goes Running -> Stopping -> Starting -> "
                 "Running and takes up to 10-15 minutes without manual "
                 "intervention; in-guest processes that need to shut down "
                 "cleanly are the usual wait. Beyond that window it is the "
                 "instance-state area, not this skill."),
    "credential": ("Password/private-key problems are fixed through the "
                   "console credential flow by the customer. Some credential "
                   "changes (key-pair bind, offline password reset) take "
                   "effect only after an in-console restart. This skill never "
                   "asks for or tests your password."),
    "snapshot": ("Snapshots are billed by storage usage (a 100 GB snapshot is "
                 "roughly 0.016 CNY per hour as quoted in the support thread); "
                 "delete unneeded ones afterwards. Deleting snapshots is also "
                 "a manual console action."),
    "bandwidth": ("If the console channel works but the public address is "
                  "dead from outside, a pay-as-you-go bandwidth stopped for "
                  "an overdue balance is a known cause. This skill cannot "
                  "query account balance; check the Billing console yourself "
                  "and top up if needed: https://usercenter2.aliyun.com/"),
    "expansion": ("Disk expansion itself does not damage data, but resizing "
                  "partitions/filesystems is its own procedure; when the "
                  "question becomes 'expanded but not applied', hand off to "
                  "the disk-expand skill."),
}

# ---------------------------------------------------------------------------
# Handoff routing (this skill only identifies + transfers; it never
# deep-dives another area). Each entry names the receiving skill.
# ---------------------------------------------------------------------------

HANDOFFS = {
    "instance-state": ("area:instance-state-diagnosis",
                       "instance will not start / stuck in a transitional "
                       "state beyond the 10-15 minute window"),
    "disk-io": ("area:resource-bottleneck",
                "CPU/disk-IO saturation evidence: the connection failure is "
                "a symptom of the system being wedged"),
    "disk-capacity": ("the disk-capacity skill (disk full / inode exhausted)",
                      "guest check shows a full filesystem or inode pool"),
    "disk-expand": ("area:disk-expand-diagnosis",
                    "expansion completed but partition/filesystem not applied"),
    "security": ("the security channel: submit a support ticket and open "
                 "Security Center (https://yundun.console.aliyun.com/); "
                 "abuse reports via https://report.aliyun.com/#/reportCenter/home",
                 "suspected intrusion / unknown logins / abuse from the asset"),
}

HARDENING_CHECKLIST = (
    "change the instance password (and rotate key pairs) from the console",
    "restrict the SSH/RDP source CIDR in the security group to known egress IPs",
    "upgrade exposed software and patch via Security Center",
    "take regular snapshots",
    "report malicious outbound activity via the abuse-report page",
)

# ---------------------------------------------------------------------------
# Verdict catalogue: id -> (title, meaning, next-action line template).
# The entry script picks exactly one; see references/remote-connection-entry__triage-tree.md.
# ---------------------------------------------------------------------------

VERDICTS = {
    "OUT_OF_SCOPE_IP": (
        "not an instance of this account/region",
        "The address resolves to no ECS asset visible to the current "
        "credential in this region.",
        "Ask the customer to confirm the region and the owning account, or - "
        "if the IP belongs to another provider - contact that provider; "
        "diagnosis stops here."),
    "INSTANCE_NOT_RUNNING": (
        "instance state blocks connection",
        "The instance is not Running; connections cannot complete while it "
        "is stopped or transitioning.",
        "Guide a manual console start (state reading relayed from the "
        "report); if Stopping exceeds 10-15 minutes, hand off to "
        "area:instance-state-diagnosis."),
    "NO_PUBLIC_PATH": (
        "no public address on the instance",
        "The instance holds no public IP and no EIP, so a connection from "
        "the internet cannot reach it at all.",
        "Tell the customer to connect via the internal network / a jump "
        "host, or to associate an EIP through the console themselves "
        "(manual action; this skill never attaches addresses)."),
    "PROTOCOL_MISMATCH": (
        "client/protocol mismatch",
        "The client tool speaks a protocol the instance does not serve by "
        "default (e.g. SSH tools against a Windows image).",
        "Tell the customer which protocol/port this instance actually uses "
        "(relay from the routing section) and re-test; enabling OpenSSH on "
        "Windows is a manual in-console task."),
    "SG_PORT_CLOSED": (
        "security group does not allow the port",
        "No ingress rule accepts the target port on any bound security group.",
        "Show the evidence; the customer adds the rule manually in the "
        "console (this skill never writes SG rules)."),
    "SG_SOURCE_MISMATCH": (
        "security group source CIDR excludes the customer egress IP",
        "The port is open only to source CIDRs that do not include the "
        "customer's egress IP.",
        "Compare the listed source CIDRs with the egress IP from "
        "curl cip.cc; the customer fixes the authorized CIDR in the console."),
    "GUEST_LIKELY": (
        "cloud path open - guest service/firewall suspected",
        "Security group and state look normal; the failing layer is most "
        "likely inside the guest (service, listener, host firewall, logs).",
        "Give the VNC link and the customer-run self-check list from "
        "references/remote-connection-entry__guest-selfcheck-commands.md; interpret the pasted "
        "output, then conclude or hand off."),
    "TOOL_LOCAL": (
        "client tool / local network suspected",
        "Console/VNC and plain command-line channels behave differently "
        "from the failing GUI tool, pointing at the client environment.",
        "Relay the comparison matrix steps: proxy/VPN off, phone hotspot "
        "retry, alternate client, keepalive template."),
    "SATURATION_HANG": (
        "resource saturation wedged the system",
        "Monitoring/symptoms indicate CPU or IO saturation: the system "
        "cannot answer connections.",
        "Relay the snapshot-first restart notice (manual console action) "
        "and hand off to area:resource-bottleneck; suggest the "
        "atop tool afterwards (references/remote-connection-entry__help-links.md)."),
    "CREDENTIAL": (
        "authentication-stage failure",
        "The connection reached the authentication stage and was rejected.",
        "Relay the credential risk notice; direct the console credential "
        "flow. Never collect or test passwords here."),
    "SECURITY_SUSPECT": (
        "suspected intrusion - identify and hand off",
        "The request contains intrusion suspicion; it is out of this "
        "skill's read-only connection-triage scope.",
        "Output the hardening checklist and the security handoff sentence."),
    "OVERDUE_PATTERN": (
        "overdue-balance pattern suspected",
        "Console/VNC reachable, public ports dead - the known signature of "
        "public bandwidth stopped for an overdue balance (pay-as-you-go).",
        "Guide the customer to check the Billing console themselves; this "
        "skill has no balance/overdue API."),
    "INSUFFICIENT": (
        "no single cause pinned down yet",
        "The automated evidence left several layers unverifiable (typical: "
        "no egress IP, no error text, monitoring gap).",
        "List the concrete missing facts (egress IP, exact error text, "
        "console-vs-local result) and the next manual check; attach the "
        "already-collected evidence list if a human ticket is opened."),
}
