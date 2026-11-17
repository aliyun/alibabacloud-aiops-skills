"""Shared constants for the ECS attack / blackhole diagnosis skill.

All reference data used by the diagnosis flow is embedded here as code
constants. No data files are shipped inside ``scripts/``.
"""

SKILL_NAME = "alibabacloud-ecs-attack-blackhole-diagnosis"

# Per-invocation session id is generated in _cli.py and appended to every
# OpenAPI call through the --user-agent flag (Observability requirement).
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"

# Verified API surface for this skill. product -> (version, [actions]).
# Only actions listed here may ever be called; every entry is read-only.
READ_ONLY_API_WHITELIST = {
    "ecs": (
        "2014-05-26",
        [
            "DescribeInstanceStatus",
            "DescribeInstances",
            "DescribeSecurityGroups",
            "DescribeSecurityGroupAttribute",
            "DescribeInvocations",
        ],
    ),
    "vpc": (
        "2016-04-28",
        [
            "DescribeEipAddresses",
        ],
    ),
    "sts": (
        "2015-04-01",
        [
            "GetCallerIdentity",
        ],
    ),
}

# Products whose action is invoked in plugin form (lowercase-hyphenated),
# e.g. `aliyun sts get-caller-identity`. Every product used here is listed.
PLUGIN_MODE_PRODUCTS = {"ecs", "sts", "vpc", "cms", "bssopenapi", "sas", "cloudfw", "cas", "waf-openapi"}

CLI_BINARY = "aliyun"

# Timeouts (seconds) for one subprocess call, including retries.
CALL_TIMEOUT_SECONDS = 60
STS_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0

DEFAULT_PAGE_SIZE = 50
MAX_PAGES = 10
MAX_SECURITY_GROUPS_PER_INSTANCE = 10
MAX_RECENT_INVOCATIONS = 20

# Ports that customers most often describe as "blocked" for a public site.
BUSINESS_PORTS = [80, 443]
# Administrative ports whose exposure to the whole internet is a hardening
# finding, and whose unreachability customers often report as an attack.
ADMIN_PORTS = [22, 3389]
# Well-known datastore/admin ports that appear in intrusion tickets; exposing
# them publicly is a hardening finding, not proof of an attack.
HIGH_RISK_PORTS = [6379, 13306, 3306, 1433, 445, 5985, 9200]

# Alibaba Cloud browser-based / Workbench SSH access must be allowed by the
# security group, otherwise console "connect" attempts fail even though the
# instance is healthy and no attack is in progress.
CONSOLE_SSH_WHITELIST_CIDR = "100.104.0.0/16"

FULL_COVERAGE_CIDRS = ("0.0.0.0/0", "::/0")

# ---------------------------------------------------------------------------
# Verdicts. The customer reports a symptom; the skill reports which area the
# evidence points at. Only two strings are customer-facing error signatures that
# this skill is allowed to quote, and neither is by itself proof of an attack.
# ---------------------------------------------------------------------------
QUOTABLE_ERROR_STRINGS = ["err_connection_reset", "Connection reset"]

VERDICT_REAL_DDOS = "REAL-DDOS-BLACKHOLE-UNCONFIRMED"
VERDICT_PLATFORM_BLOCKOUT = "PLATFORM-PENALTY-BLOCKOUT"
VERDICT_EXTERNAL_BLOCK = "EXTERNAL-PARTY-BLOCK"
VERDICT_NOT_ATTACK_CONFIG = "NOT-ATTACK-ACCESS-CONFIG"
VERDICT_NOT_ATTACK_RESOURCE = "NOT-ATTACK-INSTANCE-STATE"
VERDICT_UNDETERMINED = "UNDETERMINED"

# ---------------------------------------------------------------------------
# Console / documentation entry points. Kept here because the report must be
# able to cite them even when a query is degraded.
#
# Every console deep link that carries a region as a path segment keeps a
# ``{region_id}`` placeholder and is filled with the region actually queried
# (see ``console_link`` in the area script). A constant pinned to one region
# sent customers whose instance lived elsewhere to an empty page.
# ---------------------------------------------------------------------------
REGION_SWITCH_NOTE = "switch the region in the top-left corner of the console"
DDOS_CONSOLE_URL = "https://yundun.console.aliyun.com/?p=ddos#/asset/ecs/{region_id}"
SECURITY_CENTER_ALARMS_URL = "https://yundun.console.aliyun.com/?p=sas#/securityAlarm/{region_id}"
SECURITY_CENTER_VIRUS_KILL_URL = "https://yundun.console.aliyun.com/?p=sas#/virusKill/{region_id}"
SECURITY_CENTER_OVERVIEW_URL = "https://yundun.console.aliyun.com/?p=sas#/overview/home/{region_id}"
SECURITY_CENTER_LOGIN_URL = "https://yundun.console.aliyun.com/"
PENALTY_RELEASE_URL = "https://yundun.console.aliyun.com/?p=scnew#/sc/event/resources"
SECURITY_GROUP_CONSOLE_URL = "https://ecs.console.aliyun.com/securityGroup/region/{region_id}"

BILLING_DETAIL_URL = "https://billing-cost.console.aliyun.com/finance/expense-report/expense-detail-by-instance"

DOC_SNAPSHOT_CREATE = "https://help.aliyun.com/document_detail/25455.html"
DOC_SNAPSHOT_BILLING = "https://help.aliyun.com/document_detail/56159.html"
DOC_SNAPSHOT_DELETE = "https://help.aliyun.com/document_detail/128131.html"
DOC_SNAPSHOT_ROLLBACK = "https://help.aliyun.com/zh/ecs/user-guide/roll-back-a-disk-by-using-a-snapshot"
DOC_SNAPSHOT_SINGLE = "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot"
DOC_SNAPSHOT_OVERVIEW = "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1"
DOC_SG_START = "https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups"
DOC_SG_CASES = "https://help.aliyun.com/zh/ecs/user-guide/security-groups-for-different-use-cases"
DOC_WINDOWS_HIGH_BANDWIDTH = (
    "https://help.aliyun.com/zh/ecs/support/"
    "troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-in-windows-instances"
)
DOC_SWAP_PARTITION = (
    "https://help.aliyun.com/zh/ecs/support/how-do-i-configure-the-swap-partition-of-a-linux-instance"
)
DOC_HARDENING_SUMMARY = "https://help.aliyun.com/knowledge_list/60787.html"
DOC_TRIAL_ECS_GUIDE = "https://help.aliyun.com/document_detail/2839344.html#2738af3ab7x4e"
DOC_SAS_FREE_TRIAL = (
    "https://help.aliyun.com/zh/security-center/product-overview/apply-for-a-7-day-free-trial-of-security-center"
)
DOC_SAS_PAY_AS_YOU_GO = (
    "https://help.aliyun.com/zh/security-center/product-overview/pay-as-you-go#0ec8ae4c6bn06"
)
DOC_EIP_BANDWIDTH_CHANGE = "https://help.aliyun.com/document_detail/99059.html"
DOC_PUBLIC_IP_TO_EIP = "https://help.aliyun.com/document_detail/61290.html"
DOC_EIP_UNBIND = "https://help.aliyun.com/document_detail/65204.html"
DOC_EIP_BUY_BIND = "https://help.aliyun.com/document_detail/72125.html"
DOC_INSTANCE_METADATA = "https://help.aliyun.com/zh/ecs/user-guide/view-instance-metadata.md"

# Ordered 4-step manual path for replacing a fixed public IP after a
# blackhole; each entry is (step text, documentation URL).
EIP_CONVERSION_STEPS = [
    ("Change the fixed-bandwidth billing mode to pay-by-traffic first", DOC_EIP_BANDWIDTH_CHANGE),
    ("Convert the VPC fixed public IP into an Elastic IP Address (EIP)", DOC_PUBLIC_IP_TO_EIP),
    ("Unbind the current EIP from the instance", DOC_EIP_UNBIND),
    ("Purchase and bind a new EIP", DOC_EIP_BUY_BIND),
]

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
