"""Constants for the ECS encrypted-image cross-account read-only skill.

Everything the skill "knows" that is not code lives here as in-code constants;
no data files are shipped inside scripts/.
"""

SKILL_NAME = "alibabacloud-ecs-image-encryption-cross-account"
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"
# {session_id} is a 32-char hex token generated once per script run.
USER_AGENT_TEMPLATE = USER_AGENT_PREFIX + "/" + SKILL_NAME + "/{session_id}"

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"
# Plugin mode: product and command are lowercase-hyphenated.
STS_IDENTITY_COMMAND = "GetCallerIdentity"

# ABSOLUTE PROHIBITION whitelist. Any action not listed here must never be
# invoked, printed as a command line, or suggested as "run this to fix it".
READ_ONLY_ACTIONS = (
    "DescribeImages",
    "DescribeInstances",
    "DescribeInstanceStatus",
)

CLI_TIMEOUT_SECONDS = 90
IDENTITY_TIMEOUT_SECONDS = 45
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.5
RETRYABLE_MARKERS = (
    "Throttling",
    "ServiceUnavailable",
    "ServiceUnavailableException",
    "InternalError",
    "SDK.ServerUnreachable",
    "connection reset",
    "timed out",
    "timeout",
)
RETRYABLE_HTTP_STATUS = ("500", "502", "503", "504")

# Limits taken from the DescribeImages / DescribeInstanceStatus API contract.
IMAGE_PAGE_SIZE = 100          # DescribeImages PageSize max is 100
INSTANCE_STATUS_PAGE_SIZE = 50  # DescribeInstanceStatus PageSize range is 1..50
MAX_PAGES = 20                  # hard stop so a large account cannot loop forever

# DescribeImages.Status values. The API defaults to Available, which hides
# images that are still being produced; "ALL" is therefore used unless the
# caller asks for the default filter.
IMAGE_STATUS_DEFAULT_FILTER = "Available"
IMAGE_STATUS_FILTER_ALL = "ALL"
IMAGE_STATUSES = (
    "Creating",
    "Waiting",
    "Available",
    "UnAvailable",
    "CreateFailed",
    "Deprecated",
)
# Image sources: self = own custom image, others = shared/community image.
IMAGE_OWNER_ALIASES = ("self", "system", "others", "marketplace")

AUTH_DENIED_MARKERS = ("NoPermission", "ImplicitDeny", "AccessDenied", "not authorized")

# Customer-facing entry points (console) used by the guidance output.
CONSOLE_IMAGE_PAGE = "https://ecs.console.aliyun.com/image"
CONSOLE_TASK_PAGE = "https://ecs.console.aliyun.com/task/region"
CONSOLE_QUOTA_PAGE = "https://quotas.console.aliyun.com/products/ecs/quotas"
CONSOLE_RAM_PAGE = "https://ram.console.aliyun.com/roles"

# Authoritative documentation used for every factual claim in this skill.
# Each entry was read on the verification date below; details not covered by
# these documents are reported as "unverified", never guessed.
DOC_VERIFIED_ON = "2026-09-18"
DOC_ENCRYPT_CUSTOM_IMAGES = (
    "https://help.aliyun.com/zh/ecs/user-guide/encrypt-custom-images-1.md"
)
DOC_SHARE_CUSTOM_IMAGE = "https://help.aliyun.com/document_detail/25463.html"
DOC_CROSS_ACCOUNT_ENCRYPTED_SHARE = "https://help.aliyun.com/document_detail/2838993.html"
DOC_COPY_CUSTOM_IMAGE = "https://help.aliyun.com/document_detail/25462.html"
DOC_EXPORT_CUSTOM_IMAGE = (
    "https://help.aliyun.com/zh/ecs/user-guide/export-a-custom-image.md"
)
DOC_ECS_LIMITATIONS = "https://help.aliyun.com/zh/ecs/user-guide/limitations.md"
DOC_ECS_QUOTA_DETAIL = "https://help.aliyun.com/document_detail/184116.html"
DOC_DATA_ENCRYPTION_PRACTICE = (
    "https://help.aliyun.com/zh/ecs/user-guide/encrypt-data-stored-on-ecs-resources.md"
)
DOC_DESCRIBE_IMAGES = (
    "https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-describeimages.md"
)

# Roles required before an encrypted image or snapshot can be shared.
ROLE_SHARE_ENCRYPTED_IMAGE = "AliyunECSShareEncryptImageDefaultRole"
ROLE_SHARE_ENCRYPTED_SNAPSHOT = "AliyunECSShareEncryptSnapshotDefaultRole"
ROLE_DISK_ENCRYPT_DEFAULT = "AliyunECSDiskEncryptDefaultRole"
KMS_SERVICE_KEY_ALIAS = "alias/acs/ecs"
KMS_POLICY_SERVICE_KEY = "AliyunKMSFullAccess"

# Quota identifiers relevant to this symptom axis.
QUOTA_CUSTOM_IMAGE_COUNT = "q_user-image-count"
QUOTA_SHARE_USER_COUNT = "q_user-per-image-shared-user-count"

# Error literals that this skill can legitimately quote: each was read from the
# official error table of the operation that returns it (DescribeImages error
# table, and the export FAQ for IMAGE_ALREADY_EXIST).
ERROR_IMAGE_ALREADY_EXIST = "IMAGE_ALREADY_EXIST"
ERROR_IMAGE_OWNER_ID_UNSUPPORTED = "InvalidOperation.ImageOwnerIdUnsupported"
ERROR_PUBLIC_IMAGE_ALIAS = "InvalidImageOwnerAlias.PublicImageUnsupported"
ERROR_FILTER_KEY_NOT_FOUND = "InvalidFilterKey.NotFound"

TRUSTED_PRINCIPAL_SUFFIX = "@ecs.aliyuncs.com"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"
