"""Constants for the ECS bandwidth change and billing-mode guide skill.

Everything the entry script needs is a module-level constant here. The scripts
directory intentionally holds no data file of any kind, so tables that would
otherwise live in JSON or YAML are expressed as Python literals.
"""

SKILL_NAME = "alibabacloud-ecs-bandwidth-modify-guide"

# Full literal form of the user agent prefix; the session id is appended to this.
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues"

CLI_BINARY = "aliyun"

PRODUCT_ECS = "ecs"
PRODUCT_VPC = "vpc"

# Plugin-mode command form, lower-case hyphenated, as the CLI expects it. The API
# versions live in related_apis.yaml; the CLI resolves them, so nothing here repeats
# them and risks drifting.
STS_CALLER_IDENTITY_CMD = ["sts", "get-caller-identity"]

# Actions this skill may send, in authorisation-name form. Mirrored by
# ACTION_WHITELIST in _cli.py, related_apis.yaml and references/ram-policies.md.
RAM_ACTIONS = [
    "sts:GetCallerIdentity",
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus",
    "ecs:DescribeAvailableResource",
    "vpc:DescribeEipAddresses",
]

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300
DEFAULT_RETRIES = 3
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRY_BACKOFF_CAP_SECONDS = 20.0

DEFAULT_PAGE_SIZE = 50
MAX_PAGES = 20
INSTANCE_IDS_BATCH = 20

INTENTS = [
    "survey",
    "resize",
    "not-effective",
    "billing-convert",
    "ip-swap",
    "temp-upgrade",
    "cost-rule",
    "triage",
]

# Enumerated values as documented for the two describe calls. They are matched
# exactly; anything else is reported verbatim as an unrecognised value rather than
# rounded into one of these buckets.
CHARGE_PREPAID = "PrePaid"
CHARGE_POSTPAID = "PostPaid"
BANDWIDTH_BY_BANDWIDTH = "PayByBandwidth"
BANDWIDTH_BY_TRAFFIC = "PayByTraffic"

# Published inbound rule: below 10 Mbit/s purchased outbound the inbound ceiling
# is 10 Mbit/s, at or above it the inbound value tracks the outbound value.
INBOUND_TRACKING_THRESHOLD_MBITPS = 10

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# Failures worth retrying with backoff. Anything else surfaces immediately.
TRANSIENT_ERROR_TOKENS = [
    "Throttling",
    "SystemBusy",
    "ServiceUnavailable",
    "InternalError",
    "SDK.ServerUnreachable",
    "timed out",
    "timeout",
    "connection reset",
    "500",
    "503",
    "504",
]

# The only denial literals this skill ever quotes back to a user.
PERMISSION_ERROR_TOKENS = ["NoPermission", "ImplicitDeny"]

REDACT_KEYS = ["AccessKeyId", "SecurityToken", "Signature"]

UID_TAG_PREFIX = "uid="
