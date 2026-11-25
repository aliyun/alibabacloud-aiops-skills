"""Constants for the ECS game and application server deployment guide skill.

Everything this skill knows (the action whitelist, the frozen guest inspection
list, deployment-path document anchors, the handoff table, symptom signatures)
is embedded here as code constants: standalone data files are not allowed
under ``scripts/``.

SECURITY AND BOUNDARY
  * The transport layer in ``_cli.py`` only ever issues the actions listed in
    ``API_WHITELIST`` and refuses anything outside it before a process is
    spawned, so a mistake upstream cannot reach the cloud.
  * Three classes live inside that whitelist. The evidence group is a Describe
    or Get call: it mutates nothing, so it runs on its own. The class B group is
    one Cloud Assistant dispatch of ONE command taken verbatim from
    ``GUEST_PROBES``; class C is one snapshot of one named disk. B and C change
    state and are refused unless the caller repeats the exact command string or
    disk id as that single call's confirmation.
  * A confirmation is good for one call. It is never cached, never inferred
    from an earlier answer, and never reused for the next command.
  * Everything else in this tier -- installing software, opening security
    group ports, starting services, deleting or cleaning files, restarting
    instances -- is guidance with a console or in-guest path a human runs. This
    package never performs those steps and never scripts them.
  * Credentials are never read, printed, or passed by this package: the aliyun
    CLI resolves them from its own default credential chain.
"""

SKILL_NAME = "alibabacloud-ecs-app-server-deploy-guide"

# --- Observability -----------------------------------------------------------
# One 32-character session id per run, attached to every single CLI invocation
# so one deployment-preparation session is traceable end to end. Rendered by
# _cli.build_user_agent().
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"
SESSION_ID_LENGTH = 32

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0

# RPC-style products keep the PascalCase action name; plugin-style products use
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
ACTION_DESCRIBE_INSTANCE_STATUS = "DescribeInstanceStatus"
ACTION_DESCRIBE_AVAILABLE_RESOURCE = "DescribeAvailableResource"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_RUN_COMMAND = "RunCommand"
ACTION_CREATE_SNAPSHOT = "CreateSnapshot"

# Class A: evidence calls that mutate nothing, so they run without a prompt.
# All five names and their key parameters were verified for this tier
# (DescribeInstances / DescribeInstanceStatus / DescribeAvailableResource
# against the ECS 2014-05-26 metadata; GetCallerIdentity and
# DescribeInvocations against the shipped batch contract).
EVIDENCE_ACTIONS = (
    ("sts", ACTION_GET_CALLER_IDENTITY),
    ("ecs", ACTION_DESCRIBE_INSTANCES),
    ("ecs", ACTION_DESCRIBE_INSTANCE_STATUS),
    ("ecs", ACTION_DESCRIBE_AVAILABLE_RESOURCE),
    ("ecs", ACTION_DESCRIBE_INVOCATIONS),
)

# Classes B and C: the only state-changing calls this package can make, each
# one reachable only with a confirmation that repeats the command or disk it
# covers. RunCommand exists solely to carry a class-B probe string from
# GUEST_PROBES below; CreateSnapshot exists solely as the snapshot-first safety
# net a human needs BEFORE any cleanup or space-releasing step.
GATED_WRITE_ACTIONS = (
    ("ecs", ACTION_RUN_COMMAND),
    ("ecs", ACTION_CREATE_SNAPSHOT),
)

# The complete set of actions this skill may ever put on the wire, and the only
# set declared in related_apis.yaml and references/ram-policies.md.
API_WHITELIST = EVIDENCE_ACTIONS + GATED_WRITE_ACTIONS

# Granted RAM action identifiers, kept in one place so references/ram-policies.md,
# this whitelist, and the calls in the entry script stay aligned by construction.
# The two gated ones are named in the CLI plugin-mode form (lowercase
# hyphenated); the same calls carry their API names in related_apis.yaml.
RAM_POLICY_ACTIONS = (
    "sts:GetCallerIdentity",
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus",
    "ecs:DescribeAvailableResource",
    "ecs:DescribeInvocations",
    "ecs:run-command",
    "ecs:create-snapshot",
)

# Which parameter each gated action's confirmation has to repeat verbatim. The
# confirmation is therefore always about one concrete target: this command,
# this disk. It cannot be a generic flag, so it cannot cover a second call by
# accident.
CONFIRMATION_SUBJECT_PARAM = {
    ("ecs", ACTION_RUN_COMMAND): "CommandContent",
    ("ecs", ACTION_CREATE_SNAPSHOT): "DiskId",
}

# --- Gated guest inspection (class B) ----------------------------------------
# The frozen whitelist. Each entry is ONE complete shell command string; the
# dispatch only ever carries one of these, one command per confirmed call.
# They cover exactly the three uses this tier is scoped to: the pre-deploy
# space and inode checks, the mount-layout check behind "the files did not
# land where I expected", and the deleted-but-open-holder check behind
# "cannot create new file" when the block usage looks fine.
GUEST_PROBES = {
    "space": {
        "command": "df -h",
        "proves": ("Free space per mounted file system, human units. A full "
                   "target file system explains most install failures."),
        "when": "before any fresh install, and for every disk-full symptom",
    },
    "inodes": {
        "command": "df -i",
        "proves": ("Free inodes per mounted file system. Space can look fine "
                   "while the inode table is exhausted, which surfaces as "
                   "'cannot create new file'."),
        "when": "install fails with a cannot-create-file symptom but df -h is "
                "not full",
    },
    "mounts": {
        "command": "findmnt",
        "proves": ("The live mount table: which device backs which directory. "
                   "Explains installs that 'disappeared' onto the wrong disk."),
        "when": "the deploy target path is on a data disk, or files land in "
                "an unexpected place",
    },
    "root-usage": {
        "command": "du -x --max-depth=1 /",
        "proves": ("One-level usage of the root file system, staying on a "
                   "single device, so the biggest top-level directories show "
                   "where the space went."),
        "when": "a space check came back full and the operator needs to see "
                "which top-level directory holds it",
    },
    "deleted-open": {
        "command": "lsof +L1",
        "proves": ("Files still held open after deletion: space that a "
                   "cleanup removed but the kernel has not released yet."),
        "when": "df says full but du does not add up, right after a cleanup",
    },
}
GUEST_PROBE_COMMANDS = tuple(sorted(e["command"] for e in GUEST_PROBES.values()))

# Commands deliberately NOT executable from this package: service, port,
# process, and package-manager queries are outside the approved low-risk
# command whitelist for this tier, so the report prints them as steps for a
# human and asks for the pasted output instead.
HUMAN_ONLY_CHECKS = (
    "Listening sockets and service state (ss -tlnp / systemctl status): "
    "human step, output pasted back.",
    "Java / Node / runtime versions (java -version, node -v): human step.",
    "Any install, config edit, service start, deletion, or cleanup: human "
    "step only, never dispatched from here.",
)

INSPECTION_COMMAND_NAME = "ecs-app-server-deploy-probe"
INSPECTION_DESCRIPTION = "One confirmed pre-deployment inspection reading."
# Linux only this release. Windows server guests are guided through the
# console path; the batch rule is to add Windows readings only when ticket
# evidence for them arrives.
SCRIPT_TYPE_LINUX = "RunShellScript"
GUEST_POLL_INTERVAL_SECONDS = 5
GUEST_WAIT_DEFAULT_SECONDS = 60
GUEST_WAIT_MAX_SECONDS = 240
# Guest output is the customer's own data and is still masked before display,
# then truncated, because a raw block listing is not what a report should
# carry whole. Unfinished invocation states are owned by the entry script.
GUEST_OUTPUT_MAX_CHARS = 2000

# --- Snapshot gate (class C) --------------------------------------------------
SNAPSHOT_NAME_PREFIX = "ecs-app-server-deploy-"
SNAPSHOT_DESCRIPTION = ("Pre-cleanup snapshot taken under the deploy-guide "
                        "snapshot-first rule. Billable storage: note the id "
                        "and delete it via the console when done.")
SNAPSHOT_BILLING_NOTE = (
    "Snapshots are billable storage that keeps charging until a human deletes "
    "the snapshot in the console. This skill never deletes anything.")

# --- Query caps and shapes -----------------------------------------------------
PAGE_SIZE = 50
REGION_RE = r"^[a-z][a-z0-9-]{2,29}$"
INSTANCE_ID_RE = r"^i-[a-z0-9][a-z0-9-]{2,62}$"
DISK_ID_RE = r"^d-[a-z0-9][a-z0-9-]{2,62}$"
INSTANCE_TYPE_RE = r"^[A-Za-z][A-Za-z0-9.-]{1,60}$"
ZONE_ID_RE = r"^[a-z][a-z0-9-]{2,29}$"

# --- Error vocabulary -----------------------------------------------------------
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_CONFIRMATION_REQUIRED = "ConfirmationRequired"
CODE_POLICY_REFUSED = "RefusedBySkillPolicy"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_API_ERROR = "ApiError"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_PARSE_ERROR = "ParseError"

CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid", "accesskeyidnotfound", "signaturedoesnotmatch",
    "invalidsecuritytoken", "securitytokenexpired", "sdk.invalidcredential",
    "defaultchainfailed", "invalidsts",
)
RETRYABLE_MARKERS = (
    "throttling", "serviceunavailable", "internalerror", "server busy",
    "temporarily unavailable", "connection reset", "timed out", "timeout",
    "http 500", "http 502", "http 503", "http 504", "statuscode: 5",
)
NON_RETRYABLE_MARKERS = (
    "invalidparameter", "missingparameter", "nosuchinstance",
    "invalidinstanceid", "instanceidnotfound", "regionnotfound",
    "operationdenied", "instancelock", "idempotentparameter",
)

# Field-name shapes whose VALUE is scrubbed from every line that leaves the
# transport layer, including guest readings and CLI error envelopes.
SENSITIVE_KEY_PATTERNS = (
    r"access[-_]?key[-_]?(id|secret)",
    r"security[-_]?token",
    r"session[-_]?token",
    r"signature(nonce)?",
    r"password",
    r"passwd",
    r"private[-_]?key",
)
MASKED_VALUE = "***"

# --- Customer symptom signatures ------------------------------------------------
# Matched against --error-text / free wording, in order. Every key below is a
# string a customer can actually see (console message, OS error line), not an
# internal analysis term. A capacity match never means this skill fixes it: it
# means take the confirmed space/inode readings, then hand off per the table.
SYMPTOM_SIGNATURES = (
    ("capacity-blocks", (
        "no space left on device", "disk is full", "disk full",
        "not enough space", "insufficient space"),
     "Space exhausted on the target file system.",
     "disk-capacity"),
    ("capacity-inodes", (
        "cannot create new file", "file count limit", "inode exhausted",
        "no space left on device but df looks fine"),
     "Inode or file-count exhaustion, not raw bytes.",
     "disk-capacity"),
    ("sold-out", (
        "operationdenied.nostock", "sold out", "no stock",
        "insufficient stock", "resource unavailable"),
     "The wanted instance type has no stock in that zone right now.",
     "stock"),
    ("resize-not-effective", (
        "resized but still", "expanded disk not", "partition not grown",
        "new size not visible"),
     "A completed resize whose guest still shows the old size.",
     "disk-expand"),
    ("boot-or-state", (
        "instance will not start", "stuck in starting", "stuck in stopping",
        "cannot boot the server"),
     "The instance itself is not usable, before any deploy question.",
     "instance-state"),
    ("io-slow", (
        "disk io is slow", "iops limit reached", "disk latency",
        "server laggy since"),
     "Performance of the disk, not the deployment path.",
     "disk-io"),
    ("panel", (
        "bt panel", "aaPanel", "baota", "web hosting panel"),
     "Panel operation, a different tier.",
     "panel"),
    ("website", (
        "site not accessible", "domain not resolving", "website down"),
     "Site accessibility, a different tier.",
     "website"),
    ("runtime", (
        "nginx failed", "php error", "java exception", "port already in use",
        "service failed to start"),
     "Runtime/service configuration, a different tier.",
     "web-runtime"),
    ("database", (
        "mysql won't start", "database migration failed", "redis connect"),
     "Database engine work on ECS, a different tier.",
     "database"),
    ("mail-port", (
        "port 25", "cannot send mail", "smtp blocked"),
     "Mail sending restriction, a different tier.",
     "smtp-port"),
    ("not-listening", (
        "game server not reachable", "server not listening",
        "cannot join the server"),
     "Deployed but the port is not reachable: process and firewall checks "
     "are human steps for this release.",
     "post-deploy-check"),
)

# --- Handoff targets --------------------------------------------------------------
# Neighbouring tiers this skill recognises and hands off to. Names mirror the
# ECS skill family layout for those tiers; the full table with wording is in
# references/handoff-boundaries.md.
HANDOFF_TARGETS = {
    "disk-capacity": "alibabacloud-ecs-disk-capacity-cleanup",
    "disk-expand": "alibabacloud-ecs-disk-expand-diagnosis",
    "instance-state": "alibabacloud-ecs-instance-state-diagnosis",
    "disk-io": "alibabacloud-ecs-disk-io-diagnosis",
    "panel": "alibabacloud-ecs-bt-panel-diagnosis",
    "website": "alibabacloud-ecs-web-inaccessible-slow",
    "web-runtime": "alibabacloud-ecs-web-service-runtime-config",
    "database": "alibabacloud-ecs-db-on-ecs-diagnosis",
    "site-migration": "alibabacloud-ecs-site-migration-guide",
    "smtp-port": "alibabacloud-ecs-smtp-block-diagnosis",
}

# --- Deployment paths and their verified document anchors -------------------------
# Only URLs retrieved for this tier are listed; nothing here is a remembered or
# guessed link. Game-specific install tutorials and the security-group port
# guide are NOT part of the verified set: the report says so instead of
# inventing links.
DEPLOY_PATH_DOCS = {
    "instance-selection": {
        "title": "ECS instance type selection best practices",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "best-practices-for-instance-type-selection.md"),
        "use": "right-sizing CPU, memory and disk for a server workload",
    },
    "high-clock": {
        "title": "ECS instance families with high clock speeds (hf series)",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "instance-families-with-high-clock-speeds.md"),
        "use": ("game servers and other single-thread-sensitive backends; "
                "the document describes the hf families themselves"),
    },
    "gpu-families": {
        "title": "GPU-accelerated and vGPU instance families",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "gpu-accelerated-compute-optimized-and-vgpu-accelerated-"
                "instance-families-1.md"),
        "use": "GPU-backed application servers",
    },
    "free-trial": {
        "title": "Usage scenarios for the ECS free trial",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "usage-scenarios-for-the-ecs-free-trial.md"),
        "use": "individual and small-team customers trying a server out",
    },
    "custom-image": {
        "title": "Share a custom image",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image.md",
        "use": "replicating a built environment to more instances or accounts",
    },
    "server-migration": {
        "title": "Server migration guide",
        "url": "https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md",
        "use": "moving an existing server workload onto ECS",
    },
    "simple-app-servers": {
        "title": "Manage Simple Application Servers with the Alibaba Cloud client",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "use-alibaba-cloud-client-to-manage-simple-application-"
                "servers.md"),
        "use": ("telling a Simple Application Server apart from an ECS "
                "instance when DescribeInstances matches nothing"),
    },
}

# --- Guidance blocks rendered by the entry script -----------------------------------
PATH_LABELS = {
    "fresh-install": "Path 1, purchase or reuse an instance and install on it",
    "image-copy": "Path 2, replicate the built environment from a custom image",
    "migration": "Path 3, migrate an existing server onto ECS",
    "selection": "Path 4, size and buy the right instance type first",
}

MANUAL_PREREQUISITES = (
    "Security group: open ONLY the ports the server actually serves, inbound, "
    "on the bound security group (ECS console -> Instances -> the instance -> "
    "Security Groups -> Add Rule). This skill never edits rules.",
    "Install location: pick the data disk mount point if one exists (confirm "
    "with the 'mounts' probe) so game or app files never sit on the system "
    "disk by accident.",
    "Runtime prerequisites (JDK, Node, screen, steamcmd or similar): the "
    "customer installs these themselves; this package never installs "
    "software.",
    "Disk space and inodes: check with the confirmed 'space' and 'inodes' "
    "probes, or ask the customer to paste df -h and df -i output.",
)

POST_DEPLOY_HUMAN_CHECKS = (
    "1. Inside the guest, the customer runs a listener check (for example "
    "'ss -tlnp') and confirms the game port is listening.",
    "2. From outside, the customer connects to <public-ip>:<port>; a timeout "
    "means security group or firewall review next.",
    "3. Process and service verification is a human step this release: no "
    "port or process command is on the dispatch whitelist.",
)

LIMITATIONS = (
    "Cloud queries cannot see a process, a port, or a file inside the guest; "
    "only the five published probe strings reach the guest, one per "
    "confirmation, and everything else stays a human step.",
    "Inventory results are a snapshot of the query moment, not a purchase "
    "promise.",
    "Ticket-derived deployment playbooks for this tier were not available to "
    "this build: the guidance is document-anchored, and handoff boundaries "
    "were fixed from the tier plan, not from conversations.",
)

# --- Report tail contract -----------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

EXIT_FOR_STATUS = {STATUS_OK: 0, STATUS_DEGRADED: 1, STATUS_FAIL: 2}
