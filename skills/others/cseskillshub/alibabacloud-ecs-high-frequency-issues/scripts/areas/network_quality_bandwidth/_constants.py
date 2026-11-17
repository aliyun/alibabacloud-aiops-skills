"""Static configuration for the network quality and bandwidth diagnosis skill.

All reference data used by the scripts lives in this module as constants; no data files are
shipped next to the code. Numeric limits that are not verifiable from the cloud side are marked
with a confidence note instead of being asserted.
"""

SKILL_NAME = "alibabacloud-ecs-network-quality-bandwidth"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

ECS_PRODUCT = "ecs"
VPC_PRODUCT = "vpc"
CMS_PRODUCT = "cms"
STS_PRODUCT = "sts"

ECS_API_VERSION = "2014-05-26"
VPC_API_VERSION = "2016-04-28"
CMS_API_VERSION = "2019-01-01"

CLI_TIMEOUT_SECONDS = 30
STS_TIMEOUT_SECONDS = 20
QUERY_TIMEOUT_SECONDS = 45

MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2

RETRYABLE_ERROR_TOKENS = (
    "throttling",
    "throttled",
    "serviceunavailable",
    "internalerror",
    "unavailable",
    "timeout",
    "timed out",
    "connectionreset",
    "500",
    "502",
    "503",
    "504",
)

PERMISSION_ERROR_TOKENS = (
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "denied",
    "unauthorizedoperation",
    "notauthorized",
)

SUCCESS_CODES = ("200", "ok", "success")

KBPS_PER_MBPS = 128
SATURATION_RATIO = 0.95
NEAR_LIMIT_RATIO = 0.80
SATURATION_CONSECUTIVE_POINTS = 2

# Bounds for the measurement command text that `guide` prints for the customer to run themselves.
# This skill is read-only and never executes any of it.
PROBE_TOOLS = ("ping", "mtr")
PROBE_TARGET_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9.\-:_]{0,62}$"
PING_DEFAULT_COUNT = 20
PING_MAX_COUNT = 50
PING_MIN_PACKET_SIZE = 56
PING_MAX_PACKET_SIZE = 1472
PING_MAX_PACKET_SAMPLES = 4
MTR_DEFAULT_COUNT = 30
MTR_MAX_COUNT = 100
PROBE_MIN_PORT = 1
PROBE_MAX_PORT = 65535

MAX_INSTANCES_DESCRIBED = 100

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

VERDICT_SATURATED = "SATURATED"
VERDICT_NEAR_LIMIT = "NEAR_LIMIT"
VERDICT_NOT_SATURATED = "NOT_SATURATED"
VERDICT_UNKNOWN = "UNKNOWN"

UNIT_TO_MBPS = {
    "mbps": 1.0,
    "mb/s": 8.0,
    "kbps": 1.0 / 1000.0,
    "kb/s": 8.0 / 1000.0,
    "bps": 1.0 / 1000000.0,
    "b/s": 8.0 / 1000000.0,
    "gibps": 1000.0,
    "bits_per_sec": 1.0 / 1000000.0,
}

BILLING_MODE_FACTS = (
    "PayByTraffic charges outbound traffic only; the peak of one instance is capped at 100 Mbps and",
    "no total traffic quota can be configured.",
)

HOSTNAME_SHAPED_VALUES = ("iZ",)

HANDOFF_RULES = (
    {
        "code": "disk-io",
        "target": "area:resource-bottleneck",
        "keywords": ("iops", "disk bandwidth", "io hang", "disk io", "read/write latency"),
        "note": "Disk bandwidth or IOPS at the specification limit is a storage performance issue.",
    },
    {
        "code": "instance-state",
        "target": "area:instance-state-diagnosis",
        "keywords": ("cannot start", "cannot boot", "will not start", "stuck starting",
                     "ssh fails", "vnc", "connection refused", "frozen",
                     "hung", "unresponsive"),
        "note": "Instance unreachable or hung is an instance state issue, not a bandwidth issue.",
    },
    {
        "code": "compute",
        "target": "ECS compute resource diagnosis (same family)",
        "keywords": ("cpu 100", "cpu full", "load high", "memory", "swap"),
        "note": "CPU or memory saturation reported as slow network belongs to the compute area.",
    },
    {
        "code": "application",
        "target": "application operations (customer side)",
        "keywords": ("499", "502", "504", "timeout config", "nginx", "tls certificate",
                     "control panel", "web panel", "openvpn", "rustdesk"),
        "note": "Error codes produced by the web or app layer with normal cloud resources.",
    },
    {
        "code": "security",
        "target": "security handling (no verified skill name for this batch)",
        "keywords": ("ddos", "cc attack", "blocked by alibaba cloud", "unblock", "waf", "attack"),
        "note": "Attack traffic and platform security blocking: evidence only, no unblocking.",
    },
    {
        "code": "billing",
        "target": "billing or presales",
        "keywords": ("coupon", "voucher", "refund", "price", "quote", "invoice", "renew"),
        "note": "Commercial questions are answered by billing or presales staff.",
    },
    {
        "code": "mtr-link",
        "target": "alibabacloud-mtr-network-diagnosis-customer",
        "keywords": ("hop", "mtr", "traceroute", "which router", "path analysis"),
        "note": "Hop-by-hop link analysis is owned by the MTR diagnosis skill.",
    },
)

CONCLUSIONS = {
    "spec_limit": (
        "Outbound bandwidth reached the purchased peak, so the transfer rate is capped by the "
        "specification rather than by link quality."
    ),
    "near_limit": (
        "Outbound bandwidth is close to the purchased peak, which can explain intermittent "
        "slowdown under bursts."
    ),
    "not_limit": (
        "Outbound bandwidth stayed well below the purchased peak during the stated window, so the "
        "purchased capacity is not the bottleneck."
    ),
    "overdue_candidate": (
        "With pay-by-traffic billing, an overdue account throttles outbound bandwidth. This skill "
        "cannot read the account balance, so the customer must check it in the billing center."
    ),
    "mtu_candidate": (
        "Larger packets failing while small packets succeed can also come from an interface MTU "
        "inside the guest, for example a tun interface of a self-hosted VPN."
    ),
}
