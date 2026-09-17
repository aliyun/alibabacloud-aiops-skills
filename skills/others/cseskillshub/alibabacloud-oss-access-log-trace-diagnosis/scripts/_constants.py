#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for OSS Access-Log Trace Diagnosis
========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads, writes, caches or
prints any credentials; authentication is resolved exclusively by the aliyun
CLI default credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (log field catalog, EC error-code knowledge base,
bucket-policy grammar whitelist, operation aliases, magic-byte table) is
embedded here as Python constants. There are NO data files in this skill.

Field semantics and error-code meanings in this module follow the public
Alibaba Cloud documentation for OSS realtime access logs and OSS EC codes.
"""

# ---------------------------------------------------------------------------
# Service endpoints and API versions
# ---------------------------------------------------------------------------

# Region-less central endpoints (the CLI is given an explicit endpoint so calls
# never depend on the caller's default region).
STS_ENDPOINT = "sts.aliyuncs.com"

# API versions, informational; the aliyun CLI carries its own metadata.
API_VERSIONS = {
    "sts": "2015-04-01",
    "oss": "2019-05-17",
    "sls": "2020-12-30",
    "ram": "2015-05-01",
}

# ---------------------------------------------------------------------------
# Timeouts and query limits (platform rule 7.6.1: every network call carries
# an explicit timeout sourced from here)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60

# Longer budget for log queries that scan a wide window server-side.
LOG_QUERY_TIMEOUT = 120

# Hard guardrail on pagination loops.
MAX_PAGES = 20

# Maximum rows requested per log query. Kept deliberately small: aggregated
# SQL returns a small result table, and raw-row pulls are capped to protect
# the conversation from log floods.
MAX_LOG_LINES = 100

# Default look-back window (seconds) when the user does not give one.
DEFAULT_WINDOW_SECONDS = 24 * 3600

# Widest window accepted for a single query (7 days). OSS realtime access logs
# are retained per the customer's own SLS logstore configuration; a wider
# window mostly costs scan time without adding evidence.
MAX_WINDOW_SECONDS = 7 * 24 * 3600

# ---------------------------------------------------------------------------
# OSS realtime access log -- source addressing
# ---------------------------------------------------------------------------

# The realtime access-log project is created per account per region when the
# customer enables realtime log query for OSS. Logstore name is fixed.
LOG_PROJECT_TEMPLATE = "oss-log-{uid}-{region}"
LOG_LOGSTORE = "oss-log-store"

# One logstore carries THREE log kinds, distinguished by __topic__. Every query
# MUST pin the topic: without it, hourly metering rows pollute any aggregation,
# and batch-deletion detail rows are missed entirely.
TOPIC_ACCESS_LOG = "oss_access_log"
TOPIC_BATCH_DELETE_LOG = "oss_batch_delete_log"
TOPIC_METERING_LOG = "oss_metering_log"

TOPIC_MEANINGS = {
    TOPIC_ACCESS_LOG: "One row per request - the evidence this skill needs.",
    TOPIC_BATCH_DELETE_LOG: (
        "One row per key removed by a batch delete call. A batch delete logs "
        "only ONE request row in the access topic; the individual keys live "
        "here and join back through request_id."),
    TOPIC_METERING_LOG: "One row per bucket per hour - usage counters, not requests.",
}

# ---------------------------------------------------------------------------
# OSS realtime access log -- field catalog (public documented schema)
# ---------------------------------------------------------------------------
# Field names below are the customer-facing realtime log schema. They differ
# from the server-side log schema used by support tooling; never mix the two.

ACCESS_LOG_FIELDS = {
    # -- identity --
    "bucket": "Bucket name.",
    "owner_id": "Alibaba Cloud account ID that owns the bucket.",
    "access_id": "AccessKey ID used by the requester; '-' when anonymous.",
    "requester_id": "Requester ID; '-' for anonymous access.",
    "extend_information": (
        "Populated for RAM-role requests as "
        "requesterParentId,roleName,roleSessionName,roleOwnerId "
        "(comma separated; further fields may be appended). "
        "Compare roleOwnerId with owner_id to decide cross-account access."
    ),
    "sign_type": (
        "Signature type: NotSign (unsigned), NormalSign (V1 header), "
        "UriSign (V1 presigned URL), AdminSign (administrator account), "
        "NORMAL_SIGN4 (V4 header), URI_SIGN4 (V4 presigned URL)."
    ),
    # -- network --
    "client_ip": "Client IP: the caller itself, or its firewall / proxy IP.",
    "host": "Request host, e.g. bucketname.oss-cn-beijing.aliyuncs.com.",
    "http_type": "HTTP or HTTPS.",
    "vpc_id": "ID of the VPC where OSS is reached; empty/'-' for public access.",
    "vpc_addr": (
        "Integer form of the VPC address. Convert with "
        "int_to_ip(cast(vpc_addr as bigint)) and REVERSE the octets."
    ),
    # -- request --
    "http_method": "HTTP method.",
    "operation": "OSS operation name (see OPERATION_ALIASES for traps).",
    "request_uri": "Request URI including query string, URL ENCODED.",
    "object": "Object key, URL ENCODED. Decode with url_decode(object).",
    "object_size": "Object size in bytes.",
    "referer": "HTTP Referer header.",
    "user_agent": "HTTP User-Agent header.",
    "request_length": "Request size including headers, in bytes.",
    "content_length_in": "Request Content-Length in bytes.",
    "sync_request": (
        "Sync request type: '-' normal request, 'cdn' CDN back-to-origin, "
        "'lifecycle' lifecycle rule execution."
    ),
    # -- response --
    "http_status": "HTTP status code returned.",
    "error_code": "OSS error code; '-' on success.",
    "ec": "Detailed EC error code (the primary diagnosis key of this skill).",
    "response_time": "Total HTTP response time in milliseconds.",
    "server_cost_time": "Server-side processing time in milliseconds.",
    "response_body_length": "Response body size in bytes, excluding headers.",
    "content_length_out": "Response Content-Length in bytes.",
    # -- storage / misc --
    "bucket_storage_type": "Storage class: standard / archive / IA ...",
    "bucket_location": "Data center of the bucket, usually oss-<regionId>.",
    "delta_data_size": "Object size change; 0 if unchanged, '-' if not an upload.",
    "restore_priority": "Restore priority for archive retrieval.",
    "archive_direct_read_size": "Bytes billed as archive direct read.",
    "acc_access_region": "Transfer-acceleration access point region, else '-'.",
    "logging_flag": "true when periodic log shipping to a bucket is enabled.",
    "user_defined_log_fields": "Base64 of a JSON object with configured custom headers/params.",
    "time": "Request end time, e.g. 27/Feb/2018:13:58:45. Use __time__ for a timestamp.",
}

# Fields that carry an index in a default realtime-log logstore and can be used
# as a pre-filter before the '|' pipe. Non-indexed fields must be filtered in
# the SQL part instead. Index configuration is customer-editable, so the scripts
# verify empirically rather than trusting this list.
USUALLY_INDEXED_FIELDS = (
    "bucket", "owner_id", "access_id", "client_ip", "host", "http_method",
    "operation", "http_status", "error_code", "ec", "sign_type",
    "sync_request", "request_id", "bucket_storage_type", "vpc_id",
)

# Fields usually NOT indexed: filtering them before the '|' pipe returns an
# error or zero rows; put them in the SQL WHERE clause instead.
USUALLY_NON_INDEXED_FIELDS = (
    "object", "request_uri", "referer", "user_agent", "object_size",
    "response_time", "server_cost_time", "response_body_length",
    "content_length_in", "content_length_out", "requester_id",
    "extend_information",
)

# The dedicated logstore's index CANNOT be modified by the customer, so the two
# lists above are stable rather than per-account. Do not tell the customer to
# add an index to make a filter work; move the predicate into the SQL part.
LOGSTORE_INDEX_IMMUTABLE = True

# ---------------------------------------------------------------------------
# Logstore, enablement, retention and billing facts
# ---------------------------------------------------------------------------

LOGSTORE_FACTS = (
    "The dedicated logstore accepts no other data and its index cannot be "
    "modified, but query, statistics and alerting are unrestricted.",
    "A bucket without a region attribute cannot enable realtime log query.",
    "Do not delete the OSS-related log project or logstore: log push breaks.",
    "Realtime data becomes queryable in roughly three seconds; rows arriving "
    "later than that are backfilled data rather than ordinary lag.",
)

RETENTION_FACTS = (
    "Log files shipped into a destination bucket are NEVER auto-deleted; a "
    "lifecycle rule on the destination bucket is required to clean them up.",
    "The dedicated logstore keeps logs 7 days by default; retention can be "
    "changed in the log service, and beyond the free tier its billing applies.",
)

LOG_BILLING_FACTS = (
    "Free tier under the feature-based billing mode: retention of 7 days or "
    "less AND daily write (compressed) plus index traffic of 900 GB or less "
    "(about 900 million records at 1 KB each) incurs no log-service charge.",
    "Free shard quota: 16 x 31 shard*days per month; excess is billed.",
    "Read traffic, internet traffic, data transformation and delivery of the "
    "dedicated logstore are billed at standard log-service rates.",
    "Quote these figures only from this table; never invent numbers.",
)

MANAGEMENT_PLANE_NOTE = (
    "Realtime access logs cover the DATA plane only. Management-plane events - "
    "who changed a RAM policy, a bucket ACL or any bucket configuration - are "
    "recorded in ActionTrail, not in this log. A question about who changed a "
    "configuration must be answered from ActionTrail, not from here."
)

# Official attribution list for an expected request row that is MISSING from the
# log. Log absence never proves the request did not happen; one of these four
# must be quoted instead of concluding "no such request occurred".
LOG_ABSENCE_CAUSES = (
    {
        "cause": "CDN cache hit",
        "detail": "The request was served by a CDN edge and never reached OSS.",
        "check": "Look at CDN offline logs for cache-served requests.",
    },
    {
        "cause": "Client-side interruption",
        "detail": "The request died before reaching OSS (client network or "
                  "client configuration).",
        "check": "Inspect the client SDK error logs around the same timestamp.",
    },
    {
        "cause": "Log push failure",
        "detail": "OSS does not guarantee 100 percent log delivery; a small "
                  "loss rate is documented expected behaviour.",
        "check": "Treat a single missing row as inconclusive, not as proof.",
    },
    {
        "cause": "Cross-region endpoint usage",
        "detail": "The request hit another region's endpoint for this bucket, "
                  "so it landed in that region's log project.",
        "check": "Query the project of the region whose endpoint was used.",
    },
)

# Custom log fields: the standard schema is fixed, but a bucket may additionally
# record up to 6 chosen request headers and/or query parameters.
USER_DEFINED_LOG_FIELDS_FACTS = (
    "Up to 6 request headers and/or query parameters per bucket can be "
    "recorded in addition to the fixed schema.",
    "Values land in the single field user_defined_log_fields as Base64-encoded "
    "JSON with the keys headers, querys and truncated; key and value combined "
    "are capped at 1024 bytes and keys are lowercased.",
    "Requires realtime log query to be enabled and takes effect within roughly "
    "15 minutes, so it cannot recover anything for a past window.",
    "Typical use: record x-forwarded-for to identify the real client IP behind "
    "a CDN or proxy chain. Header names must use hyphens, not underscores.",
    "When a trace needs the behind-proxy client IP and this field was not "
    "configured for that window, state that it cannot be recovered - it can "
    "only be enabled going forward.",
)

# Mirror back-to-origin rules are NOT exposed by the SDK: the website read
# returns only the static-website index and error documents (verified against
# oss2 2.19.1, whose website parser sets exactly index_file and error_file).
MIRROR_RULES_NOT_EXPOSED = (
    "The origin address of a mirror back-to-origin rule is not readable "
    "through the SDK; only the static-website index and error documents are. "
    "Read the rule in the console under the bucket's static-website settings, "
    "then request the origin URL directly to see the status it returns."
)

# ---------------------------------------------------------------------------
# Official documentation sources
# ---------------------------------------------------------------------------
# Cite these instead of restating a rule from memory. Per-EC pages are resolved
# at runtime by _doc_lookup.py against the help-center index, so an EC link is
# quoted only when that lookup actually returned it.

DOC_INDEX_URL = "https://help.aliyun.com/zh/oss/llms.txt"

DOC_SOURCES = {
    "log_fields": "https://help.aliyun.com/zh/sls/log-fields-13",
    "realtime_log_assets_and_billing":
        "https://help.aliyun.com/zh/sls/usage-notes-of-oss-access-log/",
    "log_delivery_console_path":
        "https://help.aliyun.com/zh/oss/user-guide/logging",
    "missing_log_attribution":
        "https://help.aliyun.com/zh/oss/user-guide/"
        "why-can-t-i-query-the-desired-log-in-the-oss-access-log",
    "custom_log_fields":
        "https://help.aliyun.com/zh/oss/user-guide/"
        "set-logging-request-headers-or-url-parameters",
    "log_retention_cleanup":
        "https://help.aliyun.com/zh/oss/user-guide/"
        "will-oss-access-logs-be-cleared-regularly",
    "error_response_and_ec":
        "https://help.aliyun.com/zh/oss/user-guide/overview-14",
}

# ---------------------------------------------------------------------------
# Operation aliases and traps
# ---------------------------------------------------------------------------

OPERATION_ALIASES = {
    # The log operation name for listing objects is GetBucket, not ListObjects.
    "GetBucket": "ListObjects (list objects in the bucket)",
    # Multipart completion is logged as CompleteUploadPart, NOT CompleteMultipart.
    "CompleteUploadPart": "Complete a multipart upload (final assembly)",
    "InitiateMultipartUpload": "Initialize a multipart upload (no payload)",
    "UploadPart": "Upload one part (the actual data transfer)",
    # The abort operation is spelled inconsistently across documentation
    # sources (AbortMultipartUpload vs AbortMultiPartUpload). Neither spelling
    # could be confirmed against a live log on the build host, so queries that
    # filter on it MUST include both forms rather than pick one.
    "AbortMultipartUpload": "Abort a multipart upload (spelling variant A)",
    "AbortMultiPartUpload": "Abort a multipart upload (spelling variant B)",
    "PostObject": "Form-based upload (policy + signature in the form body)",
    "ProcessImage": "Image processing request (x-oss-process)",
    "DeleteObjects": (
        "Batch delete: logs ONE request row here, while the individual removed "
        "keys are recorded under the batch-delete topic and join back through "
        "request_id"
    ),
    "ExpireObject": "Removal performed by a lifecycle rule",
}

# Both documented spellings, for queries that must not miss either form.
ABORT_OPERATION_SPELLINGS = ("AbortMultipartUpload", "AbortMultiPartUpload")

# Operations that carry the actual upload payload when measuring upload speed.
UPLOAD_DATA_OPERATIONS = ("PutObject", "PostObject", "UploadPart", "AppendObject")

# ---------------------------------------------------------------------------
# Bucket naming rules (public documented constraints)
# ---------------------------------------------------------------------------

# 3-63 characters, lowercase letters / digits / hyphens, must start and end
# with a lowercase letter or digit. A dot or underscore makes the name invalid,
# so such a bucket can never exist.
BUCKET_NAME_PATTERN = r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$"

# ---------------------------------------------------------------------------
# Bucket Policy grammar whitelist (syntax guardrail)
# ---------------------------------------------------------------------------
# Only condition keys documented for OSS bucket policies are allowed. Anything
# outside this list must be reported as unsupported rather than invented.

POLICY_CONDITION_KEYS = {
    "acs:SourceIp": "Source IP. In a bucket policy it must be paired with acs:SourceVpc.",
    "acs:SourceVpc": "VPC ID. Use StringLike with [\"*\"] to mean 'any or no VPC'.",
    "acs:UserAgent": "User-Agent header.",
    "acs:AccessId": "AccessKey ID of the caller; TMP.*/STS.* match temporary credentials.",
    "oss:Prefix": "Object prefix. ONLY effective for APIs carrying a prefix parameter (listing).",
    "oss:Delimiter": "Delimiter, listing APIs only.",
    "oss:ExistingObjectTag/<key>": "Existing object tag.",
    "oss:BucketTag/<key>": "Bucket tag.",
    "oss:x-oss-acl": "Bucket ACL.",
    "oss:x-oss-object-acl": "Object ACL.",
    "oss:object-remaining-retention-days": "WORM remaining retention days.",
    "oss:ClassicIntranet": "Classic network access flag.",
}

# Frequently requested but NOT supported as a bucket-policy condition key.
POLICY_UNSUPPORTED_CONDITIONS = {
    "acs:Referer": (
        "Not a supported condition key. Hotlink protection is configured with "
        "the bucket referer whitelist instead of a policy condition."
    ),
    "oss:Referer": (
        "Not listed among supported OSS bucket-policy condition keys. Use the "
        "bucket referer whitelist for hotlink protection."
    ),
    "oss:content-type": (
        "Not supported by bucket policies or RAM policies. To constrain the "
        "upload content type, use a form-upload policy or a presigned URL that "
        "fixes Content-Type."
    ),
}

# Principal forms valid in a BUCKET policy. RAM policy syntax must not be mixed in.
POLICY_PRINCIPAL_FORMS = {
    "account_or_ram_user": 'Plain UID string in an array, e.g. ["1234567890"]',
    "assumed_role": '["arn:sts::<ownerUid>:assumed-role/<roleName>/*"] (wildcard the session name)',
    "anonymous": '["*"]',
}

# Principal forms that are INVALID in a bucket policy and must be rejected.
POLICY_PRINCIPAL_ANTIPATTERNS = (
    'Object form {"RAM": [...]} is RAM-policy syntax and is not valid here.',
    'Using role/<name> instead of assumed-role/<name> never matches a role session.',
    'Hardcoding a session name instead of the /* wildcard breaks dynamic sessions.',
)

# ---------------------------------------------------------------------------
# Verdict classes -- the honesty contract of this skill
# ---------------------------------------------------------------------------
# A: provable from the customer's own logs plus the customer's own
#    configuration. The script concludes with evidence.
# B: evidence narrows the cause to a few candidates, but confirmation needs
#    something the customer must supply or run. The script lists candidates
#    plus a concrete verification step for each.
# C: the decisive evidence is not reachable through public customer-facing
#    APIs. The script MUST escalate and state plainly what it could not
#    verify. Guessing is forbidden.

VERDICT_SELF_DIAGNOSABLE = "A"
VERDICT_NEEDS_CONFIRMATION = "B"
VERDICT_ESCALATE = "C"

VERDICT_LABELS = {
    VERDICT_SELF_DIAGNOSABLE: "Provable from your own logs and configuration",
    VERDICT_NEEDS_CONFIRMATION: "Narrowed to candidates; confirmation needed",
    VERDICT_ESCALATE: "Requires a support ticket; not verifiable by you",
}

# Error codes whose decisive evidence is server-side only. Listed separately so
# the escalation path can be triggered even when no EC code is present.
ESCALATION_ERROR_CODES = {
    "InternalError": "Server-side failure; escalate with the request ID.",
    "ServiceUnavailable": "Server-side overload; escalate with the request ID.",
    "OperationTimeout": "Server-side timeout; escalate with the request ID.",
    "MirrorFailed": (
        "Mirror back-to-origin failed because the origin did not return 200. "
        "The root cause sits at the origin: verify the origin URL directly."
    ),
}

# HTTP status classes that always escalate when no EC code explains them.
ESCALATION_STATUS_FLOOR = 500

# ---------------------------------------------------------------------------
# Image handling reference data
# ---------------------------------------------------------------------------

IMAGE_PROCESSING_SUPPORTED_TYPES = (
    "image/jpeg", "image/png", "image/webp", "image/gif",
    "image/bmp", "image/tiff", "image/avif",
)

# Magic bytes used to prove what a file really contains.
IMAGE_MAGIC_BYTES = {
    "PNG": "89 50 4E 47 0D 0A 1A 0A",
    "JPEG": "FF D8 FF",
    "GIF": "47 49 46 38",
    "WebP": "52 49 46 46 .. .. .. .. 57 45 42 50",
    "BMP": "42 4D",
}

# An object this small cannot be a real image; treat it as a placeholder or a
# truncated upload until proven otherwise.
SUSPICIOUS_OBJECT_SIZE_BYTES = 50

# ---------------------------------------------------------------------------
# Bucket-policy hit analysis -- condition key to log field mapping
# ---------------------------------------------------------------------------

POLICY_CONDITION_LOG_FIELDS = {
    "acs:SourceIp": "client_ip",
    "acs:SourceVpc": "vpc_id",
    "acs:AccessId": "access_id",
    "acs:UserAgent": "user_agent",
    "oss:Prefix": "request_uri",
}

# Operators and whether they honour wildcards. Using StringEquals with a
# wildcard is a silent no-match and must be reported as a configuration bug.
POLICY_OPERATOR_WILDCARD = {
    "StringLike": True,
    "StringNotLike": True,
    "StringEquals": False,
    "StringNotEquals": False,
    "IpAddress": False,
    "NotIpAddress": False,
    "Bool": False,
}

# Temporary-credential AccessKey ID prefixes.
TEMPORARY_CREDENTIAL_PREFIXES = ("STS.", "TMP.")
