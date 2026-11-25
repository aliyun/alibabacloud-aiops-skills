"""Constants for the ECS disk encryption and KMS key guide skill (read-only).

Everything the scripts need as data is embedded here or in the module that uses it;
this directory holds executable code only.
"""

SKILL_NAME = "alibabacloud-ecs-disk-encryption-kms-guide"
# Observability: one session id per run, appended to this template on every call.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/" + SKILL_NAME + "/{session-id} skill-version/{skill-version}"

ALIYUN_BIN = "aliyun"

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"
# Plugin mode: the product and the action name are lowercase-hyphenated.
STS_CALLER_IDENTITY = "GetCallerIdentity"

ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_DISKS = "DescribeDisks"
ACTION_DESCRIBE_SNAPSHOTS = "DescribeSnapshots"

# The only cloud actions this skill may invoke.
READ_ONLY_WHITELIST = (
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_DISKS,
    ACTION_DESCRIBE_SNAPSHOTS,
)

DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 300
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = (1, 2, 4)

PAGE_SIZE = 50
MAX_PAGES = 20
# Snapshot reads are scoped per disk; this caps the number of disks expanded that way.
MAX_SNAPSHOT_LOOKUPS = 10

REGION_ENDPOINT_PATTERN = "ecs.{region_id}.aliyuncs.com"

# Facts a read-only cloud query cannot produce; reported with every answer.
READ_BOUNDARIES = (
    "Guest OS layer: volume encryption such as BitLocker or LUKS, filesystem layout, and "
    "whether a newly provisioned disk was initialised - not visible to any ECS read; ask "
    "the customer to run the read-only commands in references/query-recipes.md and paste back.",
    "Account and region scope: each read covers one account in one RegionId; other regions "
    "need one run per region.",
    "KMS objects inside the account (key metadata, aliases, authorisation policies) and the "
    "order or billing records behind a failed purchase are outside this skill's action list.",
    "Other product lines, for example a simple application server whose resource id is not "
    "i- / d- / s- shaped, cannot be answered by these ECS reads.",
    "No command is run inside a customer instance by this skill.",
)

# Console-side checks used whenever a field is not exposed by the read.
CONSOLE_CHECK_HINTS = (
    "ECS console -> Storage & Snapshots -> Disks -> the disk's Detail pane, the encryption row.",
    "ECS console -> Storage & Snapshots -> Snapshots -> the snapshot's Detail pane, the "
    "encryption row.",
    "KMS console -> the key list and the key's alias, to tell a service key apart from a "
    "customer-managed key.",
)


def region_endpoint_hint(region_id):
    """Return the regional endpoint shown in the report header for traceability."""
    return REGION_ENDPOINT_PATTERN.format(region_id=region_id)
