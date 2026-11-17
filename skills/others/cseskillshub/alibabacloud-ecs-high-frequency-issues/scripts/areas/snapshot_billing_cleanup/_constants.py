"""Constants for the ECS snapshot billing attribution and cleanup skill.

All reference data (billing vocabulary, capacity lenses, the guest diagnostics
whitelist, deduction facts and handoff targets) lives here as in-script
constants: standalone data files are not allowed under ``scripts/``.

The two confirmation-gated non-destructive actions (the snapshot backup action
and the guest command dispatch) are whitelisted explicitly; every other
mutating operation is out of scope for this skill by design.
"""

SKILL_NAME = "alibabacloud-ecs-snapshot-billing-cleanup"

# --- Observability -----------------------------------------------------------
# Attached to every single CLI invocation so a run is traceable end to end.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0
POLL_INTERVAL_SECONDS = 5
POLL_DEADLINE_SECONDS = 120

# Every product runs in plugin mode: the lowercase-hyphenated command form
# (sts GetCallerIdentity -> get-caller-identity). Callers pass PascalCase API
# action names; the CLI layer translates them.
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
PLUGIN_MODE_COMMANDS = {
("sts", "GetCallerIdentity"): "get-caller-identity",
}

ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_DISKS = "DescribeDisks"
ACTION_DESCRIBE_SNAPSHOTS = "DescribeSnapshots"
ACTION_DESCRIBE_IMAGES = "DescribeImages"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"
# Confirmation-gated, low-risk, non-destructive-by-default actions. They are
# dispatched ONLY by an explicit operator command line that carries the
# user-confirmation flags; see scripts/areas/snapshot_billing_cleanup/snapshot_billing_report.py.
ACTION_CREATE_SNAPSHOT = "CreateSnapshot"
ACTION_RUN_COMMAND = "RunCommand"

# The complete set of actions this skill may ever call, as (product, action)
# pairs so the RAM-console rendering is always derived, never hardcoded.
# Anything outside this set is prohibited by design; destructive operations
# (snapshot, image or policy removal included) are never called and only
# appear as manual guidance.
API_WHITELIST = (
    ("ecs", ACTION_DESCRIBE_INSTANCES),
    ("ecs", ACTION_DESCRIBE_DISKS),
    ("ecs", ACTION_DESCRIBE_SNAPSHOTS),
    ("ecs", ACTION_DESCRIBE_IMAGES),
    ("ecs", ACTION_DESCRIBE_INVOCATIONS),
    ("ecs", ACTION_CREATE_SNAPSHOT),  # gated pre-cleanup backup
    ("ecs", ACTION_RUN_COMMAND),      # gated dispatch, whitelisted readings
    ("sts", ACTION_GET_CALLER_IDENTITY),
)
GATED_WRITE_PAIRS = (
    ("ecs", ACTION_CREATE_SNAPSHOT),
    ("ecs", ACTION_RUN_COMMAND),
)


def ram_action_name(pair):
    """Render one (product, action) pair as its RAM action string."""
    product, action = pair
    return product + ":" + action

# Cloud Assistant script kinds (guest is Linux) and (guest is Windows).
CLOUD_ASSISTANT_KIND_LINUX = "RunShellScript"
CLOUD_ASSISTANT_KIND_WINDOWS = "RunPowerShellScript"

# --- Paging ------------------------------------------------------------------
PAGE_SIZE = 50
IMAGE_PROBE_PAGE_SIZE = 10
MAX_PAGES = 10

# --- Billing vocabulary ------------------------------------------------------
# The literal billing-item label seen on bills for this tier. The report and
# the references quote this label verbatim so the customer can match the
# invoice line to the evidence table.
BILLING_ITEM_LABEL = "SnapshotLink Capacity (Size)"
BILLING_ITEM_CN_HINT = "snapshot chain capacity"

# The three capacity lenses. Mixing them up is the single largest source of
# misunderstanding in this tier; every report row states which lens it uses.
CAPACITY_LENSES = (
    ("billing", "Snapshot chain capacity: the billed figure per region and disk "
     "snapshot chain; incremental chains share blocks, so the chain total is not "
     "the sum of the individual snapshot entries."),
    ("cloud", "Cloud disk capacity: the provisioned size of the disk reported by "
     "the disk listing; it is the size AT SNAPSHOT CREATION TIME, not usage."),
    ("guest", "File-system visible usage: what df or du inside the guest shows; "
     "it differs from both other lenses because snapshots back data blocks, a "
     "deleted file is only marked free, and metadata and formatting overhead are "
     "included."),
)

# Facts about snapshot storage the report may state (documented in
# references/snapshot-billing-cleanup__snapshot-billing-decision-tree.md with the source anchors).
SNAPSHOT_STORAGE_FACTS = {
    "storage_location": "Snapshots are stored in an OSS space managed by the "
    "snapshot service that the customer cannot browse; they never occupy the "
    "used space of the cloud disk itself.",
    "point_in_time": "A snapshot captures the state at the moment it was "
    "created; it is not real-time replication.",
    "incremental": "The first snapshot of a chain is a full block-level backup; "
    "later snapshots store only changed blocks, but the console still shows the "
    "total needed to restore from that snapshot.",
    "region_scoped": "Snapshots are billed per region; deleting in one region "
    "changes only that region's charges.",
    "existence_billing": "While snapshots exist they are billed by capacity and "
    "duration; releasing or stopping the instance does not delete them.",
    "no_service_switch": "There is no service switch to close: once every "
    "snapshot is removed the snapshot charge stops on its own.",
    "restore_window": "Deleting the last snapshot of an instance removes the "
    "rollback and system-disk reset path built on it.",
}

# --- Deletion-blocker model ----------------------------------------------------
# Values of the Usage field returned per snapshot entry, plus how each maps to
# the manual unblocking order (human console steps; this skill never deletes).
USAGE_KEY_NONE = "none"
USAGE_BLOCKING_STATES = ("image", "disk", "image_disk")
BLOCKER_ORDER = (
    "1. If the snapshot is shared with other accounts, cancel the image share "
    "first (a customer-executed step: console or the equivalent OpenAPI).",
    "2. Delete the custom image(s) that reference the snapshot (manual console "
    "step; note that afterwards a system-disk reset from that image is no "
    "longer possible, and skipping the linked snapshot option when deleting "
    "the image leaves the snapshot billing).",
    "3. Delete data disks that were created from the snapshot first (manual "
    "console step).",
    "4. Only then delete the source snapshot itself, in the console, region by "
    "region.",
)

# --- Regrowth-source model ("deleted but charging again") ----------------------
REGROWTH_SOURCES = (
    "other_region", "auto_policy", "external_job", "settlement_lag",
)

# --- Guest diagnostics whitelist (class B of the low-risk operation list) ----
# Exactly one command is dispatched per gated call. Anything not spelled out
# here, or carrying any blocked token, is refused before the CLI is touched.
GUEST_READINGS_LINUX = (
    "df -h",
    "df -i",
    "lsof +L1",
    "findmnt",
    "du -x --max-depth=1",   # takes a validated absolute path argument
    "du -sh --inodes",       # takes a validated absolute path argument
    "stat",                  # takes a validated absolute path argument
    "ls -l",                 # takes a validated absolute path argument
    "wc -l",                 # takes a validated absolute path argument
)
GUEST_READINGS_WINDOWS = (
    "Get-Volume",
    "Get-PSDrive",
    "Get-ChildItem",         # takes a validated drive path argument
    "fsutil volume diskfree",  # takes a validated drive letter argument
)
# Commands that need an explicit path argument appended.
GUEST_PATH_COMMANDS = (
    "du -x --max-depth=1", "du -sh --inodes", "stat", "ls -l", "wc -l",
    "Get-ChildItem", "fsutil volume diskfree",
)
LINUX_PATH_RE = r"^/[A-Za-z0-9][A-Za-z0-9._/-]{0,63}$"
WINDOWS_PATH_RE = r"^[A-Za-z]:(\\[A-Za-z0-9 ._@%+-]{0,63})?$"
# A single-quote, redirection, chaining or destructive verb anywhere in the
# requested reading means the request is refused outright.
GUEST_BLOCKED_TOKENS = (
    ";", "|", "&", ">", "<", "`", "$", "*", "?", "\n", "\\", "'", "\"",
    "&&", "||", "$(", "${",
)
GUEST_BLOCKED_WORDS = (
    "rm", "rmdir", "mv", "cp", "dd", "kill", "killall", "shutdown", "reboot",
    "halt", "mkfs", "fdisk", "parted", "wipefs", "truncate", "mount", "umount",
    "systemctl", "service", "crontab", "chown", "chmod", "passwd", "useradd",
    "userdel", "init", "format", "cipher", "del", "erase", "sdelete", "set",
    "out-file", "new-item", "remove-item", "move-item", "rename-item",
    "clear-recyclebin", "invoke", "start-process", "stop-process", "iwr",
    "curl", "wget", "nc", "ssh", "scp", "eval", "iex", "iwr",
)

# --- Snapshot backup gate (pre-cleanup "snapshot first") -----------------------
# Two semantics, per the confirmed requirements document:
#  * Before any IN-DISK file cleanup intended to shrink future snapshot or disk
#    usage, a manual-confirmation-gated snapshot backup of that disk MUST be
#    taken first (the gated CreateSnapshot dispatch below).
#  * Before DELETING SNAPSHOTS themselves, no snapshot is taken (the object of
#    the removal is the snapshot data); instead a delete/keep candidate list
#    plus a human double-check is produced.
SNAPSHOT_FIRST_RULE = (
    "Before any in-disk cleanup that shrinks future usage, back the target disk "
    "up first: run the entry script in prepare-snapshot mode (it creates ONE "
    "snapshot on the named disk after explicit user "
    "confirmation). For snapshot deletion itself, output the delete/keep list "
    "and require the human double-check instead - never 'create a snapshot in "
    "order to delete snapshots'."
)

# --- Candidate list file (optional artifact of the report mode) ----------------
CANDIDATE_FILE_PREFIX = "/tmp/snapshot-cleanup-candidates-"
CANDIDATE_FILE_RE = r"^/tmp/snapshot-cleanup-candidates-[A-Za-z0-9_-]{1,64}\.json$"

# --- Deduction and quota vocabulary (facts only; see references) --------------
DEDUCTION_FACTS = (
    "Deduction order for standard snapshot storage: an OSS storage package "
    "(standard locally redundant storage plan) first, then a storage capacity "
    "unit (SCU), then pay-as-you-go.",
    "Only STANDARD snapshot storage in the SAME region as the package is "
    "deductible; a package covers only usage generated after it was purchased.",
    "An ECS savings plan covers instance and system-disk fees only; it never "
    "deducts snapshot fees.",
    "The 100 GiB long-term free quota belongs to the ECS file backup essential "
    "edition (a different product), not to snapshots.",
)

# --- Out-of-scope routing (mirrors references/snapshot-billing-cleanup__handoffs.md) ---------------------
HANDOFFS = (
    ("resize applied but capacity did not merge, growpart, resize2fs, "
     "Windows extend volume", "area:disk-expand-diagnosis"),
    ("instance stuck in a transitional state, force stop or restart refused, "
     "snapshot writes locked by instance state",
     "area:instance-state-diagnosis"),
    ("snapshot creation hurting IO or throughput, disk performance ceiling",
     "area:resource-bottleneck"),
    ("in-guest file or inode cleanup execution and capacity governance",
     "area:disk-expand-diagnosis"),
    ("snapshot rollback, system disk restoration, build instance from image, "
     "cross-account migration",
     "alibabacloud-ecs-disaster-recovery-snapshot (rollback) / image and "
     "migration tiers"),
    ("automatic snapshot policy creation, enable, modify, delete, cross-region "
     "copy, archive or download of snapshots",
     "alibabacloud-ebs-disk-snapshot-management"),
    ("custom image removal, image share management, image fee cleanup",
     "image lifecycle and image billing tiers (area:image-billing-cleanup /"
     "area:custom-image-lifecycle)"),
    ("bill totals across products, arrears, renewal price, coupons, "
     "cancellation or waiver", "commercial and account billing paths (human)"),
    ("quota raise for the per-disk snapshot count",
     "quota center manual application (this skill reports counts only)"),
)

# --- Quota branch vocabulary ---------------------------------------------------
QUOTA_NOTES = (
    "Snapshot fees follow capacity, not entry count: every snapshot that "
    "exists carries capacity, and capacity is billed. Removing the newest "
    "entries is not automatically cheaper than removing the oldest ones.",
    "There is no per-account snapshot capacity ceiling or overage blocker: "
    "usage keeps accruing and a spending alert is the only guard.",
    "The console removes snapshots page by page with a per-page limit; batch "
    "removal stays a human action following the console prompts.",
)

# --- Failure vocabulary ----------------------------------------------------------
# Permission failures are reported with these literals only.
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"
# Snapshot writes refused while the instance is in a transitional state surface
# this customer-quoted string; the skill reports it and stops (handoff per
# references/snapshot-billing-cleanup__handoffs.md).
ERROR_STRING_INSTANCE_STATE = "IncorrectInstanceStatus"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
NOT_RETURNED = "not returned"

# Transient conditions worth retrying.
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
    "500",
    "502",
    "503",
    "429",
)

# Conditions that must never be retried.
NON_RETRYABLE_MARKERS = (
    "noparameter",
    "missingparameter",
    "invalidparameter",
    "signaturedoesnotmatch",
    "invalidaccesskeyid",
    "no permission",
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "notfound",
    "invalidinstanceidnotfound",
    "incorrectinstancestatus",
)

# Credential-chain failures, classified apart from a generic API error because
# the recovery is to refresh the local CLI configuration rather than to retry
# or to request a permission.
CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid",
    "signaturedoesnotmatch",
    "invalidsecuritytoken",
    "securitytokenexpired",
    "invalidcredential",
)

# Credential material that must never reach the terminal or a log line.
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

# --- Report banners ------------------------------------------------------------
BANNER = "ECS Snapshot Billing Attribution and Cleanup"
FINAL_ANSWER_BANNER = (
    "+==============================================================+\n"
    "|  Alibaba Cloud ECS Skill: {skill}\n"
    "|  Session: {session_id}\n"
    "+==============================================================+"
)
