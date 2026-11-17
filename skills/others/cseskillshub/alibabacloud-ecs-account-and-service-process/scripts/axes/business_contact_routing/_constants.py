"""Constants and embedded lexicon data for the read-only contact-routing skill."""

SKILL_NAME = "alibabacloud-ecs-business-contact-routing"

ALIYUN_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 30
STS_TIMEOUT_SECONDS = 20
HELP_TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.5

UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

ECS_PRODUCT = "ecs"
STS_PRODUCT = "sts"

READ_ONLY_ALLOWLIST = (
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeInstanceStatus"),
    ("ecs", "DescribeAvailableResource"),
    ("sts", "GetCallerIdentity"),
)

PAGE_SIZE = 50
PAGE_NUMBER = 1
MAX_INSTANCE_IDS = 20

RETRYABLE_CODES = (
    "Throttling",
    "Throttling.User",
    "ServiceUnavailable",
    "InternalError",
    "CliTimeout",
    "CliTransport",
)

AUTH_FAILURE_CODES = ("NoPermission", "ImplicitDeny", "AuthFailure")

INTENT_BUSINESS = "S1_business_contact"
INTENT_HUMAN_PHONE = "S2_human_phone"
INTENT_COMMERCIAL_ACTION = "S3_commercial_action"
INTENT_UNCLASSIFIED = "unclassified"

INTENT_LABELS = {
    INTENT_BUSINESS: "Requests a business or sales contact",
    INTENT_HUMAN_PHONE: "Requests a human agent or a phone call-back",
    INTENT_COMMERCIAL_ACTION: "Substantive ask is a billing or account action",
    INTENT_UNCLASSIFIED: "Routing intent not recognised from the text",
}

BUSINESS_TERMS = (
    "商务经理", "商务人员", "商务", "客户经理", "销售", "报价", "折扣", "合同",
    "框架", "批量采购", "专属顾问", "对接", "沟通",
    "account manager", "business manager", "sales manager", "ask sales",
    "for a quote", "discount", "contract", "procurement", "dedicated consultant",
)

HUMAN_PHONE_TERMS = (
    "回电", "客服电话", "人工服务", "专员", "打电话", "拨打", "来电", "电话",
    "联系", "人工", "客服", "转人工", "服务热线",
    "call me back", "phone me", "give me a call", "customer service number",
    "hotline", "human agent", "talk to a person", "manual support", "real person",
)

COMMERCIAL_ACTION_TERMS = (
    "退款", "退订", "降配", "账务", "发票", "开票", "账户主体", "主体变更", "对公",
    "refund", "unsubscribe", "downgrade", "invoice", "billing adjustment",
    "account entity", "bank transfer", "purchase order",
)

HANDOFF_TERMS = (
    ("disk-capacity", "alibabacloud-ecs-disk-capacity",
     ("磁盘满", "空间不足", "容量不足", "inode", "磁盘占用", "清理磁盘",
      "disk full", "no space left", "used space", "inode usage")),
    ("disk-expand", "alibabacloud-ecs-disk-expand-diagnosis",
     ("扩容不生效", "扩容后", "分区未生效", "扩展卷", "磁盘大小不变",
      "expand not effective", "partition not resized", "extend volume")),
    ("instance-state", "alibabacloud-ecs-instance-state-diagnosis",
     ("起不来", "无法开机", "开机失败", "重启中", "卡住", "中间状态",
      "will not come up", "stuck in a transitional state", "power state stuck")),
    ("disk-io", "alibabacloud-ecs-disk-io-diagnosis",
     ("io慢", "磁盘慢", "读写慢", "延迟高", "iostat", "io wait",
      "slow disk", "high latency", "iops below")),
)

CONSOLE_SERVICE_ENTRY = (
    "Alibaba Cloud console, Support and Services area: open a ticket and request "
    "human handling; the ticket can then be escalated to a business contact."
)

SUPPLEMENTARY_NOTIFICATION_CHANNEL = {
    "name": "ECS message notification overview (self-service alternative to phone follow-up)",
    "doc": "help.aliyun.com/zh/ecs/user-guide/overview-35.md",
    "evidence": "single hit from the injected help-document search for this tier",
}

CHANNEL_DIRECTORY_STATUS = (
    "PENDING_HUMAN_CONFIRMATION: this package asserts no phone number, no call-back "
    "time window and no unverified entry link. The official channel directory must be "
    "confirmed by a human owner before it is quoted to a customer."
)

CONFIDENCE_THRESHOLD = 0.34

CLARIFYING_QUESTION = (
    "Do you want a business or sales contact for commercial terms, or a human support "
    "agent for technical handling?"
)
