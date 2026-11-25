"""Constants for the ECS key pair and passwordless logon configuration skill.

Everything this skill knows (symptom taxonomy, quotable error signatures, guest
inspection readings, console paths, handoff table) is embedded here as code
constants: standalone data files are not allowed under ``scripts/``.

SECURITY AND BOUNDARY
  * The transport layer in ``_cli.py`` only ever issues the actions listed in
    ``API_WHITELIST``, and refuses anything outside it before a process is
    spawned, so a mistake upstream cannot reach the cloud.
  * Two classes live inside that whitelist. The evidence group is a Describe or
    Get call and mutates nothing, so it runs on its own. The gated group is
    ``RunCommand`` (one inspection command, inside the guest) and
    ``CreateSnapshot`` (one disk, before a restart window); both change state and
    both are refused unless the caller repeats the exact command or disk id as
    that call's confirmation.
  * A confirmation is good for one call. It is never cached, never inferred from
    an earlier answer, and never reused for the next command.
  * ``NEVER_GRANTED_ACTION_NAMES`` names the D-class changes this skill explains
    but never performs: power state changes, key pair and password edits,
    security group rule edits, deletions, and any in-guest edit. Those are
    console steps a human approves.
  * Credentials are never read, printed, or passed by this package: the aliyun
    CLI resolves them from its own default credential chain.
"""

SKILL_NAME = "alibabacloud-ecs-keypair-login-config"

# --- Observability -----------------------------------------------------------
# One 32-character session id per run, attached to every single CLI invocation
# so one diagnosis is traceable end to end. Rendered by _cli.build_user_agent().
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}"
SESSION_ID_LENGTH = 32

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0

# RPC style products keep the PascalCase action name; plugin style products use
# the lowercase-hyphenated command form (the identity lookup below is one).
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
PLUGIN_MODE_COMMANDS = {
    ("sts", "GetCallerIdentity"): "GetCallerIdentity",
}

ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"
ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_FULL_STATUS = "DescribeInstancesFullStatus"
ACTION_DESCRIBE_ASSISTANT_STATUS = "DescribeCloudAssistantStatus"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_RUN_COMMAND = "RunCommand"
ACTION_CREATE_SNAPSHOT = "CreateSnapshot"

# Class A: evidence calls that mutate nothing, so they run without a prompt.
EVIDENCE_ACTIONS = (
    ("sts", ACTION_GET_CALLER_IDENTITY),
    ("ecs", ACTION_DESCRIBE_INSTANCES),
    ("ecs", ACTION_DESCRIBE_FULL_STATUS),
    ("ecs", ACTION_DESCRIBE_ASSISTANT_STATUS),
    ("ecs", ACTION_DESCRIBE_INVOCATIONS),
)

# Classes B and C: the only state-changing calls this package can make, each one
# reachable only with a confirmation that repeats the command or disk it covers.
GATED_WRITE_ACTIONS = (
    ("ecs", ACTION_RUN_COMMAND),
    ("ecs", ACTION_CREATE_SNAPSHOT),
)

# The complete set of actions this skill may ever put on the wire, and the only
# set declared in related_apis.yaml and references/ram-policies.md.
API_WHITELIST = EVIDENCE_ACTIONS + GATED_WRITE_ACTIONS

# Granted RAM action identifiers, kept in one place so ram-policies.md, this
# whitelist and the calls in the entry script stay aligned by construction.
# The two gated ones are named in the CLI plugin-mode form (lowercase
# hyphenated); the same calls carry their API names in related_apis.yaml.
RAM_POLICY_ACTIONS = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstancesFullStatus",
    "ecs:DescribeCloudAssistantStatus",
    "ecs:DescribeInvocations",
    "sts:GetCallerIdentity",
    "ecs:run-command",
    "ecs:create-snapshot",
)

# Report and query caps, kept here so the scripts carry no tuning numbers.
PAGE_SIZE = 50
INVOCATION_HISTORY_ROWS = 10
MAX_FIELD_PREVIEW_CHARS = 160

# --- Gated guest inspection (class B) ---------------------------------------
# RunCommand takes a script type, not a shell guess: it follows the reported
# operating system unless the caller states it. Values are the Cloud Assistant
# script types, and nothing here is assembled from path fragments.
INSPECTION_SHELL_TYPES = {
    "shell": "RunShellScript",
    "bat": "RunBatScript",
    "powershell": "RunPowerShellScript",
}
INSPECTION_DEFAULT_SHELL = {
    "linux": "RunShellScript",
    "windows": "RunBatScript",
}
# How long a confirmed reading may take before the report says it did not come
# back. Bounded so a hung agent cannot sit on an instance indefinitely.
GUEST_POLL_INTERVAL_SECONDS = 5
GUEST_WAIT_DEFAULT_SECONDS = 60
GUEST_WAIT_MAX_SECONDS = 240
# Guest output is the customer's own data and is still masked before display, then
# truncated, because a journalctl tail is not what a report should carry whole.
GUEST_OUTPUT_MAX_CHARS = 2000
INSPECTION_COMMAND_NAME = "ecs-keypair-login-inspection"
# Statuses that still mean the reading has not come back, so the read-back keeps
# polling until one of them clears or the wait budget runs out.
GUEST_IN_PROGRESS_STATUSES = (
    "running", "pending", "invoking", "scheduled", "waiting", "stopping",
)

# --- Gated pre-change snapshot (class C) ------------------------------------
SNAPSHOT_NAME_PREFIX = "agent-keypair-login-"
SNAPSHOT_DESCRIPTION = (
    "Pre-change snapshot taken by skill %s before a restart-dependent logon "
    "credential step; delete it when the change window closes." % SKILL_NAME)

# Named to be refused. Key pair lifecycle, password reset, instance power,
# security group rule and deletion actions have no verified parameter or RAM
# contract for this tier and are D-class changes, so this skill never calls any
# of them; it guides a human through the console instead.
# InvokeCommand is refused for a different reason: RunCommand creates and
# dispatches in one call, so a second invocation path would need its own
# parameter and confirmation contract, and nothing is declared that no call uses.
NEVER_GRANTED_ACTION_NAMES = (
    "CreateKeyPair", "ImportKeyPair", "AttachKeyPair", "DetachKeyPair",
    "DeleteKeyPair", "ModifyInstanceAttribute", "ResetPassword",
    "DeleteSnapshot", "RebootInstance", "StopInstance", "StartInstance",
    "AuthorizeSecurityGroup", "RevokeSecurityGroup", "InvokeCommand",
)

# --- Reporting ---------------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# Permission failures are reported with these two literals only.
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_POLICY_REFUSED = "RefusedBySkillPolicy"
# A class B or class C call that arrived without its per-call confirmation.
CODE_CONFIRMATION_REQUIRED = "ConfirmationRequired"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"

RETRYABLE_MARKERS = (
    "throttling",
    "throttlingexception",
    "systembusy",
    "serviceunavailable",
    "internalerror",
    "internal failure",
    "temporar",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
    "429",
    "500",
    "502",
    "503",
)

NON_RETRYABLE_MARKERS = (
    "missingparameter",
    "noparameter",
    "invalidparameter",
    "signaturedoesnotmatch",
    "invalidaccesskeyid",
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "notfound",
    "invalidinstancenotfound",
    "nosuchinstance",
)

CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid",
    "signaturedoesnotmatch",
    "invalidsecuritytoken",
    "securitytokenexpired",
    "invalidcredential",
)

# Credential and key material that must never reach a terminal or a log line.
SENSITIVE_KEY_PATTERNS = (
    r"accesskeyid",
    r"access[-_]key[-_]id",
    r"accesskeysecret",
    r"access[-_]key[-_]secret",
    r"securitytoken",
    r"security[-_]token",
    r"bearer token",
    r"signature",
    r"password",
    r"passwd",
    r"private key",
)
MASKED_VALUE = "***"

# --- Intake (C1 routing inputs) ---------------------------------------------
# The customer always supplies a symptom, never a root cause. These four
# elements are collected before any query runs.
INTAKE_ELEMENTS = (
    ("instance-id+region", "Which instance, in which region"),
    ("os-type", "Which operating system: Linux or Windows"),
    ("connection-entry", "Which logon path was used: Workbench passwordless, "
     "Workbench with a key, local ssh, Remote Desktop, or VNC"),
    ("error-text", "The exact error text as shown, copied verbatim"),
)

CONNECTION_ENTRIES = (
    "workbench-passwordless", "workbench-key", "local-ssh", "rdp", "vnc",
    "unknown",
)

SYMPTOM_TAXONOMY = (
    ("passwordless-workbench", "console passwordless logon fails, message mentions "
     "a temporary SSH key", "references/login-decision-tree.md"),
    ("keypair-not-effective", "key pair created, imported or bound but logon still "
     "fails", "references/keypair-and-credential-guidance.md"),
    ("client-key-error", "the local SSH client refuses the private key file",
     "references/error-signatures.md"),
    ("credential-lost", "the private key or the password is lost and cannot be "
     "queried back", "references/faq.md"),
    ("password-reset-failed", "an online password reset stops at the key pair step",
     "references/login-decision-tree.md"),
    ("windows-rdp-lockout", "Windows logon is refused after repeated failed attempts",
     "references/login-decision-tree.md"),
    ("windows-multi-user", "several users need to log on to Windows at the same time",
     "references/faq.md"),
    ("authorized-keys-drift", "authorized_keys content changes on its own",
     "references/guest-evidence-commands.md"),
    ("os-change-or-image", "credentials stopped working after the operating system or "
     "the image was changed", "references/keypair-and-credential-guidance.md"),
    ("passkey-third-party", "a passkey, fingerprint or face logon to a third-party "
     "website", "references/handoff-boundaries.md"),
    ("unknown", "not classified yet, collect evidence first",
     "references/login-decision-tree.md"),
)

# --- Quotable error signatures ----------------------------------------------
# Every wording below is something a customer can actually see: SSH client
# output, a console message, or a Windows error code. Match tokens are
# lower-cased before comparison. Tuple shape:
# (match tokens, where it comes from, verdict, recommended action, fix side).
ERROR_SIGNATURES = (
    (
        ("unprotected private key file", "bad permissions", "permissions 0644",
         "permissions 0664"),
        "Local SSH client",
        "The private key file permissions are too open, so the client refuses to "
        "use the key at all.",
        "Have the customer tighten the file on their own workstation: chmod 600 on "
        "the pem file, or the icacls equivalent on Windows, then retry.",
        "customer-local",
    ),
    (
        ("permission denied (publickey)",),
        "sshd on the instance",
        "Public key authentication was rejected: wrong log-on user name, the key "
        "was never offered, the public key is absent from authorized_keys, or the "
        "binding never took effect.",
        "Confirm the user name, then which key the client actually offers, then the "
        "console binding and its effect condition, then the in-guest inspection "
        "readings.",
        "cloud-and-guest",
    ),
    (
        ("too many authentication failures", "ssh_msg_disconnect: 2"),
        "Local SSH client or sshd",
        "The client offered several stored keys in a row and the server closed the "
        "connection before the intended key was reached.",
        "Pin one identity: pass the intended key explicitly and enable the "
        "single-identity option; clear cached agent identities; wait out any lockout "
        "window before retrying.",
        "customer-local",
    ),
    (
        ("temporary ssh key", "passwordless logon", "password-free login",
         "cannot connect using a temporary ssh key"),
        "ECS console message",
        "The passwordless path is a temporary SSH key pair delivered inside the "
        "guest by Cloud Assistant, so the failure belongs to that channel and not to "
        "the instance password.",
        "Report the Cloud Assistant status first. Offline or stale means the agent "
        "path; online means look for a wedged guest instead.",
        "cloud-side",
    ),
    (
        ("create key pair failed", "failed to create the key pair",
         "key pair creation failed"),
        "ECS console message",
        "An online password reset builds a temporary key pair through Cloud "
        "Assistant, so the reset failed wherever the in-guest execution failed.",
        "Report the agent status and the recent execution history, then propose the "
        "offline reset path, which needs a restart and therefore a snapshot first.",
        "cloud-and-guest",
    ),
    (
        ("0xd07", "account is currently locked out", "locked out"),
        "Windows logon prompt",
        "Windows locked the account after repeated failed logon attempts, usually "
        "public brute-force traffic against 3389.",
        "Explain the lockout, guide one successful VNC logon or the console send-"
        "command path to release it, and point at tightening 3389 to the customer's "
        "own source address.",
        "guest-and-console",
    ),
    (
        ("no such file or directory", "/bin/bash", "/bin/ls"),
        "sshd output or Cloud Assistant failure",
        "Basic operating system files are missing. This is not a credential problem "
        "and more credential work is wasted effort.",
        "Stop the credential branch, take a snapshot first, then hand off to the "
        "operating system troubleshooting skill or an offline disk-repair engineer.",
        "handoff",
    ),
    (
        ("connection timed out", "connection refused", "operation timed out",
         "network error"),
        "Local SSH client",
        "The network path or the listening service failed before any credential was "
        "exchanged.",
        "Confirm the instance is Running, then have the customer test reachability of "
        "port 22 and their own egress network; security group rule content is read in "
        "the console, not by this skill.",
        "customer-local-and-console",
    ),
)

# --- Key pair lifecycle facts ------------------------------------------------
KEY_PAIR_NAMING_RULES = (
    "2 to 128 characters, starting with a letter or a Chinese character, using "
    "letters, digits, periods, underscores or hyphens",
    "the private key file is offered for download exactly once, at create or import "
    "time",
    "the platform keeps no copy of a private key, so a lost private key cannot be "
    "recovered",
    "one instance carries one key pair binding at a time",
)

# The ticket corpus contains two contradictory statements about when a binding
# takes effect: a console restart is required, versus a replacement taking effect
# immediately. Both cannot be unconditional, so this skill uses one operative
# wording and marks it pending the requirements sign-off item instead of copying
# either ticket sentence.
KEY_PAIR_EFFECT_RULE = (
    "Treat a key pair bound or replaced on a running instance as effective only "
    "after the instance has been restarted from the ECS console. Ask whether that "
    "restart happened before concluding anything else, and offer the documented "
    "no-restart alternative. This single wording replaces the two contradictory "
    "sentences in the ticket corpus and is pending sign-off."
)

NO_RESTART_ALTERNATIVE = (
    "If the workload cannot be restarted now: log on by another working path, "
    "generate a key pair locally, and append the public key line to the log-on "
    "account's authorized_keys file. That gives key logon without waiting for the "
    "platform injection step."
)

CREDENTIAL_FACTS = (
    "Private keys are downloadable only at create or import time, never stored by "
    "the platform and never queryable afterwards; the recovery path is a new key "
    "pair.",
    "Instance passwords are never recorded and never queryable; the recovery path is "
    "a reset.",
    "An online password reset runs inside the guest through Cloud Assistant and needs "
    "no restart. An offline reset needs a console restart, so it needs a snapshot "
    "first.",
    "When a key pair is bound to the instance, password logon may stay refused even "
    "after a successful reset; the key path or the unbind path is then the one to "
    "use.",
    "Public images support console credential management. Community images flagged as "
    "Others Linux generally do not, after an image swap on an existing instance.",
)

WINDOWS_LOGON_FACTS = (
    "Windows Server allows two concurrent Remote Desktop sessions by default, and "
    "the same user name reconnects into one session instead of opening a second one.",
    "More concurrent sessions need the Remote Desktop Session Host role plus RDS "
    "client access licences; a 120-day trial is the only vendor-supported path.",
    "The account lockout policy fires after repeated failed logon attempts, so public "
    "traffic against 3389 can lock an account the customer believes is passwordless.",
    "Passwordless logon types no password, which is why a lockout can look impossible "
    "to the customer while somebody else was guessing one.",
)

CLOUD_ASSISTANT_FACTS = (
    "Console passwordless logon uses a temporary SSH key pair delivered inside the "
    "guest by the Cloud Assistant agent, so an offline or unhealthy agent breaks the "
    "passwordless path only.",
    "That temporary key path does not depend on the root password or on "
    "PermitRootLogin, which is why a locked-down instance can still be reachable "
    "through it.",
    "A RAM sub-account needs ECS view and manage permission plus Cloud Assistant "
    "permission to use the passwordless path a colleague can already use.",
    "When the guest is wedged by memory pressure and disk IO saturation, the agent "
    "stops reporting, and the passwordless symptom is only the visible end of that "
    "cause.",
)

AUTHORIZED_KEYS_FACTS = (
    "The public key of a key pair bound in the console is written into the log-on "
    "account's authorized_keys file when the binding takes effect.",
    "The platform neither pre-installs third-party keys nor edits that file on its "
    "own; unexpected content came from inside the guest or from another tool.",
    "If an unexpected key appears: remove it, change the instance password, and "
    "temporarily fall back to password logon while reviewing how it got there.",
    "Content drift needs evidence before a conclusion: pull the execution history "
    "first, never answer from a guess.",
)

# --- Console navigation labels (not URLs) -----------------------------------
CONSOLE_ENTRIES = {
    "key_pair": "ECS console > Storage & Images > Key Pairs (select the region first)",
    "instance_list": "ECS console > Instances & Images > Instances (select the region "
                     "first)",
    "instance_credential": "ECS console > Instances > target instance > More > "
                           "Password/Key Pair",
    "restart": "ECS console > Instances > target instance > Restart (a customer-"
               "executed change, after a snapshot)",
    "vnc": "ECS console > Instances > Remote & Connect > VNC (fallback logon path)",
    "send_command": "ECS console > Instances > Remote & Connect > Send Command "
                    "(customer-executed)",
    "snapshot": "ECS console > Storage & Images > Snapshots",
    "security_group": "ECS console > Network & Security > Security Groups > rules for "
                      "22 and 3389",
    "cloud_assistant": "ECS console > Instances > Cloud Assistant > agent status and "
                       "command history",
}

# --- Snapshot-first gate -----------------------------------------------------
# A restart-dependent step never comes before a snapshot. Class C can take one on
# an explicit confirmation naming that disk; without one, the guidance names the
# console path and the owner decides.
SNAPSHOT_FIRST_GATE = (
    "Before any step that needs a restart, an offline reset, or a detached repair "
    "disk: snapshot the system disk first and wait for it to complete. A pure "
    "evidence review needs none. This skill takes one only when the operator "
    "confirms that exact disk, and otherwise prints the console path instead.",
)
SNAPSHOT_RISK_NOTES = (
    "Snapshots are billable storage: note the snapshot id and delete it once the "
    "change window is closed.",
    "A snapshot is not a substitute for a verified backup on data-critical volumes.",
    "The restart itself is a customer-executed change with a service-interruption "
    "window.",
)

# --- In-guest inspection readings -------------------------------------------
# Each entry: (command, what the reading proves). A listed command can be run by a
# human or, on its own confirmation, as one class B call; the strings are given in
# full so nothing is assembled from path fragments.
GUEST_READINGS_LINUX = (
    ("sshd -T", "the effective configuration the daemon is actually using"),
    ("cat /etc/ssh/sshd_config", "the file behind that configuration, includes and all"),
    ("sshd -T | grep -i -E "
     "'pubkeyauthentication|passwordauthentication|permitrootlogin|authorizedkeysfile'",
     "the four options that decide key logon, password logon and where keys are read"),
    ("stat -c '%n %a %U:%G' ~ ~/.ssh ~/.ssh/authorized_keys",
     "the home directory and .ssh permission chain, the classic refusal cause"),
    ("systemctl status sshd --no-pager",
     "whether the service runs and when it last started"),
    ("iptables -L -n", "host firewall rules that block 22 even when the cloud rule is "
                       "open"),
    ("firewall-cmd --list-all", "the firewalld equivalent of the same check"),
    ("last -n 20", "successful logons around the incident"),
    ("lastb -n 20", "failed logon attempts around the incident, and their source"),
    ("journalctl -u sshd --no-pager -n 100",
     "the server-side reason for each rejected attempt"),
)

GUEST_READINGS_WINDOWS = (
    ("query user", "current sessions and their state, in practice against the "
                   "two-session ceiling"),
    ("net accounts", "the lockout threshold, its duration and the observation window"),
    ("net localgroup administrators", "which accounts may log on as administrators"),
    ("Get-Volume | Format-Table", "free space per volume, a prerequisite for any "
                                  "agent work"),
)

# The exact-match set a confirmed class B call is allowed to run, derived from the
# two lists above so the published readings, the gate and the code cannot drift
# apart. Comparison is on the whole string: no prefix, no glob, no shell reuse.
EXECUTABLE_INSPECTION_COMMANDS = (
    tuple(command for command, _ in GUEST_READINGS_LINUX)
    + tuple(command for command, _ in GUEST_READINGS_WINDOWS)
)

GUEST_READING_RULES = (
    "Announce the command before it runs: what it reads, its scope, that it changes "
    "nothing, and how to recover if anything is unexpected.",
    "One command per confirmation. Approval for one command never covers the next, "
    "and is never carried over from an earlier run.",
    "Anything outside EXECUTABLE_INSPECTION_COMMANDS is refused and degraded to a "
    "plain suggestion for the customer to weigh.",
    "No in-guest edit is ever accepted here, under any confirmation: not an sshd "
    "configuration change, not a service restart, not a cleared authorized_keys "
    "file, not a lockout policy change, not a power action. Those are human, "
    "approved changes with their own snapshot gate.",
    "Pasted output from the customer's own session is accepted as evidence; a "
    "private key in that output is never requested and never reproduced.",
)

# --- Handoff table (identify, name the boundary, hand off) ------------------
HANDOFF_TABLE = (
    ("disk full, inode exhaustion, a resize that never shows inside the guest",
     "a capacity problem, not a credential problem",
     "alibabacloud-ecs-disk-capacity-cleanup"),
    ("disk IO or IOPS saturated, the system wedged, several symptoms at once",
     "the logon failure is the visible end of an IO hang",
     "alibabacloud-ecs-disk-io-diagnosis"),
    ("the instance will not boot, or is stuck between states",
     "an instance lifecycle problem", "alibabacloud-ecs-instance-state-diagnosis"),
    ("base files such as the default shell are missing and every command fails",
     "operating system damage that needs an offline disk repair",
     "alibabacloud-ecs-linux-os-troubleshooting"),
    ("a passkey, security key, fingerprint or face logon to a third-party website",
     "WebAuthn on a third-party platform; an ECS instance has no biometric hardware "
     "or matching operating system framework for it",
     "the third party's own documentation"),
    ("overdue balance, a released instance, resources invisible in this account",
     "account or commercial scope, not guest credentials",
     "account and billing support"),
    ("adding, deleting or re-scoping a security group rule",
     "a network access policy change", "the security group documentation and console"),
    ("a third-party terminal-services activation script or cracked licensing",
     "an unlicensed path", "the vendor-licensed Remote Desktop path only"),
    ("the Workbench file upload experience",
     "console product experience", "Workbench support"),
    ("the aftermath of a brute-force campaign, deeper incident response",
     "security incident handling", "the security incident skills"),
)

# --- Documentation anchors (official help pages) ----------------------------
OFFICIAL_DOCS = (
    ("Choose a connection method for an instance",
     "https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md"),
    ("Log on to a Linux instance with a password or a key pair",
     "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-or-key.md"),
    ("How Workbench passwordless logon works, temporary SSH key pair",
     "https://help.aliyun.com/zh/ecs/user-guide/workbench-password-free-login-principle-temporary-ssh-key-pair.md"),
    ("Instance logon credential management",
     "https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management"),
    ("Connect to a Linux instance with an SSH key pair",
     "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-an-ssh-key-pair"),
    ("Security group quick start",
     "https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md"),
    ("Account locked after too many logon or password attempts",
     "https://help.aliyun.com/zh/ecs/for-safety-consideration-have-lock-the-user-account-the-reason-is-that-login-attempt-or-password-change-try-too-much"),
    ("Configure multiple concurrent Remote Desktop users on Windows",
     "https://help.aliyun.com/zh/ecs/user-guide/configure-windows-multi-user-remote-desktop-connection"),
)

# Anchors captured from support replies rather than from a documentation search.
# They carry a verification warning on purpose: open each one before quoting it.
TICKET_QUOTED_LINKS_NOTE = (
    "Captured from support-agent replies, not from a documentation search. Each one "
    "still has to be opened and verified before it is pasted to a customer."
)
TICKET_QUOTED_LINKS = (
    ("Reset an instance password", "https://help.aliyun.com/document_detail/25439.html"),
    ("Bind or replace a key pair",
     "https://help.aliyun.com/document_detail/2936588.html"),
    ("Key pair product documentation entry",
     "https://help.aliyun.com/product/25365.html"),
    ("Create a snapshot", "https://help.aliyun.com/document_detail/25455.html"),
    ("Snapshot billing", "https://help.aliyun.com/document_detail/56159.html"),
    ("Delete a snapshot", "https://help.aliyun.com/document_detail/128131.html"),
    ("Use atop to review Linux resource history",
     "https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools"),
)
