"""Constants for the read-only ECS stop-mode billing guide skill.

All reference data (rules, documents, matrices) lives in this module or in
``references/*.md``. No data files are allowed inside ``scripts/``.
"""

SKILL_NAME = "alibabacloud-ecs-stop-mode-billing-guide"

# Observability: one User-Agent template, one session id per script run,
# attached to every single CLI invocation.
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

CLI_BIN = "aliyun"
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# Per-call timeouts (never rely on an unbounded CLI wait).
CLI_TIMEOUT_SECONDS = 30
STS_TIMEOUT_SECONDS = 20
CLI_RETRIES = 2
RETRY_BACKOFF_BASE_SECONDS = 1.5
RETRY_BACKOFF_CAP_SECONDS = 8.0

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
MAX_INSTANCE_IDS = 50

# ---------------------------------------------------------------------------
# API whitelist. Only these read-only actions may ever reach the CLI layer.
# ---------------------------------------------------------------------------
ALLOWED_ACTIONS = (
    "DescribeInstances",
    "DescribeInstanceStatus",
    "DescribeAvailableResource",
)

# STS runs in plugin mode like every other product here: the CLI command token
# is the lowercase-hyphenated form of the API action name
# (GetCallerIdentity -> get-caller-identity), verified against aliyun CLI 3.4.5.
# The whitelist below keys on the PascalCase API action name.
ALLOWED_STS_ACTIONS = ("GetCallerIdentity",)

RAM_READ_ONLY_ACTIONS = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus",
    "ecs:DescribeAvailableResource",
)

# Action-name prefixes that this skill must never call, and never tell the
# customer to run on their behalf. Enforced by _cli.run_readonly().
DISALLOWED_ACTION_PREFIXES = (
    "Start",
    "Stop",
    "Reboot",
    "RebootInstances",
    "Create",
    "Delete",
    "Modify",
    "Release",
    "Reset",
    "Replace",
    "Attach",
    "Detach",
    "Assign",
    "Unassign",
    "Allocate",
    "Convert",
    "Renew",
    "Authorize",
    "Revoke",
    "Join",
    "Leave",
    "Import",
    "Export",
    "Copy",
    "Cancel",
    "Remove",
    "Add",
    "Run",
    "Invoke",
    "Send",
    "Install",
    "Redeploy",
    "Rollback",
    "Terminate",
    "Dissociate",
    "Associate",
    "Tag",
    "Untag",
)

MINIMAL_RAM_POLICY = """\
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource"
      ],
      "Resource": "*"
    }
  ]
}
"""

# Transient failures worth a bounded backoff retry. Anything else is raised.
TRANSIENT_CODES = (
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "ServiceUnavailable",
    "InternalError",
    "SystemBusy",
    "SDK.ServerUnreachable",
    "SDK.HttpError",
    "RequestTimeout",
)

# Authentication / authorization codes. Platform wording: NoPermission and
# ImplicitDeny only.
AUTH_CODES = (
    "NoPermission",
    "ImplicitDeny",
    "Unauthorized",
    "InvalidSecurityToken",
    "MissingSecurityToken",
    "SecurityTokenExpired",
)

# ---------------------------------------------------------------------------
# Rule knowledge (mirrors references/; keep both in sync).
# ---------------------------------------------------------------------------
DOC_SOURCES = {
    "economical_mode": "https://help.aliyun.com/zh/ecs/user-guide/use-of-economical-mode.md",
    "stop_an_instance": "https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance",
    "release_an_instance": "https://help.aliyun.com/zh/ecs/user-guide/release-an-instance",
    "impacts_and_risks": "https://help.aliyun.com/document_detail/63353.html",
    "ecs_overview": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
    "spot_overview": "https://help.aliyun.com/zh/ecs/user-guide/what-is-a-spot-instance.md",
    "burstable_performance_mode": (
        "https://help.aliyun.com/zh/ecs/user-guide/switch-the-performance-mode-of-a-burstable-instance.md"
    ),
    "bill_detail_console": "https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance",
    "coupon_faq": "https://help.aliyun.com/zh/user-center/user-guide/faq-about-coupons",
}

# Billing matrix. ``UNRESOLVED`` rows are questions where the source material
# still conflicts; the agent must not assert a value for those.
BILLING_MATRIX = [
    ("vCPU / memory / GPU (compute)", "Charged", "Billing suspended", "No charge (instance gone)"),
    ("System disk", "Charged", "Still charged", "No charge (disk destroyed)"),
    ("Data disks", "Charged", "Still charged", "No charge (disk destroyed)"),
    ("Public IP address (system assigned)", "Kept", "Released and reassigned at random",
     "No charge (instance gone)"),
    ("Public bandwidth charging", "Charged", "UNRESOLVED (see references)",
     "No charge (instance gone)"),
    ("Snapshots", "Charged on usage", "Charged on usage", "Charged on usage until deleted"),
    ("Elastic IP (bound separately)", "Charged per EIP rules", "Charged per EIP rules", "Released with the EIP"),
]

STOP_MODE_TRISTATE = [
    ("Normal stop (keep charging)", "Computes stay allocated to the instance",
     "Everything keeps charging; restart is immediate and stock is not a factor"),
    ("Economical stop mode", "Compute resources and the public IP are released",
     "Compute billing suspended, disks keep charging, restart needs fresh stock "
     "and the public IP may change"),
    ("Release", "Instance and its disks are destroyed",
     "All instance charging stops, data is unrecoverable, backups must exist beforehand"),
]

# The only verbatim error sentence proven by customer-reported console output.
# Quote it as-is.
SOLD_OUT_ERROR_TEXT = (
    "The requested resource is sold out in the specified zone; "
    "try other types of resources or other regions and zones."
)
SOLD_OUT_ERROR_PATTERN = "sold out in the specified zone"
SOLD_OUT_READING = (
    "Zone stock is insufficient: economical stop released the compute resources and the restart "
    "has to re-acquire them. This is not a billing fault and not data loss."
)

# Customer paraphrases, not official error codes. Never present these as quotes.
SYMPTOM_PHRASES = [
    ("still charged", "check which stop mode was used; disks keep charging"),
    ("ip changed", "the system-assigned public IP was released with the compute resources"),
    ("cannot find the option", "the stop mode is chosen inside the stop dialog, not on the list page"),
    ("start fails after stopping", "compute must be re-acquired, so the zone may be out of stock"),
    ("how to stop charging completely", "only release ends all instance charging"),
]

# Fixed clarification paragraphs for the recurring customer misunderstandings.
MISCONCEPTION_CLARIFICATIONS = [
    "'Stopped' is not the same as 'released': only release ends all instance charging.",
    "'Economical stop mode' is not free: disks keep charging.",
    "Economical stop mode is available on pay-as-you-go instances only, not on subscription ones.",
    "Choosing a stop mode is a console action the customer performs; this skill only reads state back.",
    "Data on the disks survives economical stop mode, but the public IP address may not.",
    "Being able to read a value is not the same as being able to change it.",
]

HANDOFF_TOPICS = [
    ("EIP / fixed public IP / ICP filing", "Explain the release rule, then hand off to the EIP and filing topics."),
    ("Snapshots and custom images", "Hand off the backup or restore work; keep the data-retention clarification here."),
    ("VPC or network reconfiguration", "Hand off; this skill covers only billing consequences of stopping."),
    ("Spot / pre-emptive instance interruption", "Hand off; only the data-retention rule is answered here."),
    ("Refunds, coupons, arrears, invoice or account issues", "Hand off to billing and human support; no money action here."),
    ("Scheduled or automatic start and stop", "Clarify that the mode has no scheduler, then hand off to OOS or CloudMonitor."),
    ("In-guest commands (processes, files, services)", "Not available here; guide the customer to run read-only checks themselves."),
]
