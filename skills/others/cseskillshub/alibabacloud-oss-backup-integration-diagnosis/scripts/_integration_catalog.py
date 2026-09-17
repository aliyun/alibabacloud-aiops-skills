#!/usr/bin/env python3
# SECURITY: read-only knowledge module; only loaded by the entry script after
# SKILL.md confirmation; operates purely on user-supplied integration details.
"""Embedded knowledge catalog for OSS backup-tool integration diagnosis.

Tool x symptom -> attribution catalog (Python constant, no data files).

Knowledge sources (all verified 2026-08):
  - OSS S3 compatibility scope and limits (virtual-hosted style only,
    compatible API set, ETag/Restore differences):
    https://help.aliyun.com/zh/oss/developer-reference/compatibility-with-amazon-s3
  - Access OSS with AWS SDKs (S3-compatible endpoint forms):
    https://help.aliyun.com/zh/oss/developer-reference/use-aws-sdks-to-access-oss
  - V1 signature phase-out and V1->V4 upgrade guide:
    https://help.aliyun.com/zh/oss/developer-reference/guidelines-for-upgrading-v1-signatures-to-v4-signatures
  - Retrieval / data-processing fees (IA / Archive / ColdArchive /
    Deep ColdArchive retrieval billing):
    https://help.aliyun.com/zh/oss/product-overview/data-processing-fees
  - Storage fees and minimum storage durations (IA 30d / Archive 60d /
    ColdArchive & Deep ColdArchive 180d):
    https://help.aliyun.com/zh/oss/product-overview/storage-fees
  - Root-cause criteria distilled from 170 matched real support tickets
    (ticket/oss07.xlsx): Veeam compatibility whitelist 23, V1-signature
    adaptation 22, retrieval-fee attribution 23, S3-compat config 27,
    third-party backup tools 38, Synology/NAS 4, rclone 5.

Categories: signature / endpoint / style / permission / whitelist /
retrieval_fee / tool_usage.
side: 'client' = fix on the backup-tool side, 'server' = needs Alibaba
Cloud backend action (e.g. whitelist provisioning), 'both' = needs evidence.
"""

DOC_S3_COMPAT = "https://help.aliyun.com/zh/oss/developer-reference/compatibility-with-amazon-s3"
DOC_AWS_SDK = "https://help.aliyun.com/zh/oss/developer-reference/use-aws-sdks-to-access-oss"
DOC_V1_TO_V4 = "https://help.aliyun.com/zh/oss/developer-reference/guidelines-for-upgrading-v1-signatures-to-v4-signatures"
DOC_RETRIEVAL_FEES = "https://help.aliyun.com/zh/oss/product-overview/data-processing-fees"
DOC_STORAGE_FEES = "https://help.aliyun.com/zh/oss/product-overview/storage-fees"
DOC_V4_HEADER = "https://help.aliyun.com/zh/oss/developer-reference/recommend-to-use-signature-version-4"

CATEGORY_LABELS = {
    "signature": "signature version adaptation",
    "endpoint": "endpoint / URI form misconfiguration",
    "style": "request style (virtual-hosted vs path-style)",
    "permission": "permission mapping under S3 compatibility",
    "whitelist": "tool compatibility whitelist provisioning",
    "retrieval_fee": "retrieval / minimum-duration fee attribution",
    "tool_usage": "backup tool usage and restore behavior",
}

# Canonical S3-compatible endpoint forms (official AWS-SDK-access doc).
S3_ENDPOINT_FORMS = [
    "Public endpoint form: https://s3.oss-{region}.aliyuncs.com (replace {region} with the region ID, e.g. cn-hangzhou)",
    "Internal endpoint form: https://s3.oss-{region}-internal.aliyuncs.com (same-region ECS/VPC, no public traffic fee)",
    "Transfer-acceleration endpoint form: https://s3.oss-accelerate.aliyuncs.com",
    "OSS accepts only the virtual-hosted request style: the bucket name must be a subdomain (<bucket>.<endpoint>); path-style URLs (endpoint/<bucket>/...) are rejected",
]

# --- Error-code / error-message routing table -------------------------------
# Keys are canonical route IDs; 'aliases' enable case-insensitive fuzzy
# matching against whatever error text the customer pastes.

ERROR_ROUTES = {
    "V1SignatureRejected": {
        "aliases": [
            "v1 signature is forbidden",
            "v1 signature has been disabled",
            "v1 signature is deprecated",
            "the v1 signature",
            "v1签名被禁用",
            "v1签名下线",
            "v1 signature forbidden",
        ],
        "category": "signature",
        "side": "client",
        "root_cause_directions": [
            "OSS is phasing out the legacy V1 signature; requests still signed with V1 are rejected with 'V1 signature is forbidden'",
            "Upgrading the SDK/tool version alone is NOT enough: the client must explicitly enable the V4 signature (real ticket case: SDK upgraded but default signature stayed V1)",
            "V4 signature additionally requires the bucket region ID (e.g. cn-hangzhou) in client initialization; legacy configs that never set a region fail after the switch",
            "Very old backup tools/firmware without V4 support cannot be fixed client-side and need a tool upgrade or an explicit support-ticket exception",
        ],
        "configuration_advice": [
            "Upgrade the backup tool / SDK to a V4-capable version per the official table (OSS SDK Java >=3.17.4, Python V1 >=2.18.4, Go V1 >=3.0.2, PHP V1 >=2.7.0, C# V1 >=2.14.0, JavaScript >=6.20.0, C++ >=1.10.0, C >=3.11.0, ossutil1.0 >=1.7.12; ossutil2.0 / ossbrowser2.0 / ossfs2.0 support V4 in all versions; ossbrowser1.0 supports no V4 at all)",
            "Explicitly set the signature version to V4 in the client (e.g. Java SignVersion.V4, Python oss2.ProviderAuthV4, Go oss.AuthV4)",
            "Add the bucket region ID to the client configuration; V4 signing computes over the region",
            "If the tool cannot support V4 at all, open a support ticket instead of silently re-enabling anything; do NOT attempt to bypass the signature policy",
        ],
        "official_doc_ref": DOC_V1_TO_V4,
    },
    "PathStyleRejected": {
        "aliases": [
            "path style",
            "path-style",
            "pathstyle",
            "bucket name in the url path",
            "路径风格",
        ],
        "category": "style",
        "side": "client",
        "root_cause_directions": [
            "For security reasons OSS supports ONLY the virtual-hosted request style; S3-style path-style requests (https://endpoint/bucket/key) are rejected",
            "Backup tools defaulting to S3 path-style (older rclone/aws-cli settings, force_path_style=true) fail against OSS",
        ],
        "configuration_advice": [
            "Switch the tool to virtual-hosted style so the bucket name becomes a subdomain: https://<bucket>.s3.oss-{region}.aliyuncs.com/key",
            "In S3 SDK/CLI configs disable path-style explicitly (e.g. force_path_style=false / PathStyleAccess disabled)",
            "If a custom domain is bound to the bucket, use that domain directly as the endpoint without prepending the bucket name",
        ],
        "official_doc_ref": DOC_S3_COMPAT,
    },
    "S3HeadBucket403": {
        "aliases": [
            "headbucket 403",
            "headbucket",
            "headbucket forbidden",
        ],
        "category": "permission",
        "side": "client",
        "root_cause_directions": [
            "Under the S3 compatibility layer the HeadBucket operation maps to the OSS native API GetBucketInfo; granting oss:HeadBucket alone does not work",
            "RAM/Bucket Policy missing the oss:GetBucketInfo action, or an explicit deny, yields 403 AccessDenied on HeadBucket while ListObjectsV2/GetObject succeed (real ticket case)",
        ],
        "configuration_advice": [
            "Grant oss:GetBucketInfo on the bucket resource to the RAM identity used by the backup tool",
            "Re-test HeadBucket after the policy change; keep permissions least-privilege (only the actions the tool actually calls)",
        ],
        "official_doc_ref": DOC_S3_COMPAT,
    },
    "EndpointSchemeMissing": {
        "aliases": [
            "uri scheme of endpointoverride must not be null",
            "endpointoverride",
            "uri scheme",
        ],
        "category": "endpoint",
        "side": "client",
        "root_cause_directions": [
            "AWS S3-compatible SDK receives an endpoint string without a protocol scheme (missing https://), raising 'The URI scheme of endpointOverride must not be null' (real ticket case)",
            "When a custom domain is used, the bucket name was wrongly concatenated into the endpoint, producing unresolvable third-level subdomains",
        ],
        "configuration_advice": [
            "Always prefix the endpoint with https:// (e.g. https://s3.oss-cn-hangzhou.aliyuncs.com)",
            "Do not concatenate the bucket name into the endpoint; OSS uses virtual-hosted style and the SDK builds <bucket>.<endpoint> itself",
            "For custom domains, add the DNS record for the exact subdomain the client generates",
        ],
        "official_doc_ref": DOC_AWS_SDK,
    },
    "SignatureDoesNotMatch": {
        "aliases": [
            "signaturedoesnotmatch",
            "signature does not match",
            "签名不匹配",
        ],
        "category": "signature",
        "side": "client",
        "root_cause_directions": [
            "Wrong or rotated AccessKey Secret configured in the backup tool",
            "V4 signature region mismatch: the configured region does not match the bucket region / endpoint",
            "A proxy or gateway between the tool and OSS modifies headers that participate in signature computation",
            "Endpoint points at the wrong region or at a CDN/custom domain that does not forward signed headers",
        ],
        "configuration_advice": [
            "Re-enter the AccessKey pair in the tool; confirm the key still exists and is enabled in RAM",
            "Verify region, endpoint and bucket all belong to the same region (cn-hangzhou endpoint for a cn-hangzhou bucket)",
            "Bypass proxies for a control test; use the official S3-compatible endpoint https://s3.oss-{region}.aliyuncs.com",
            "For deep signature diffing, use the sibling skill alibabacloud-oss-transfer-error-code-diagnosis",
        ],
        "official_doc_ref": DOC_V4_HEADER,
    },
}

# --- Tool x configuration catalog -------------------------------------------

TOOL_CATALOG = {
    "veeam": {
        "aliases": ["veeam", "veeam backup", "veeam backup & replication", "veeam backup and replication"],
        "category": "whitelist",
        "side": "both",
        "summary": "Veeam Backup & Replication uses OSS as an S3-compatible backup repository; compatibility is gated by a backend whitelist and a fixed endpoint/signature configuration.",
        "config_checklist": [
            "Endpoint: use the S3-compatible form https://s3.oss-{region}.aliyuncs.com (public) or https://s3.oss-{region}-internal.aliyuncs.com (same-region VPC)",
            "Request style must be virtual-hosted; Veeam repository settings must not force path-style",
            "Signature version V4 must be enabled; V1-only builds are rejected since the V1 phase-out",
            "The target bucket must be registered in the Veeam compatibility whitelist before first use",
            "Use a dedicated RAM user with least-privilege OSS actions for the backup repository, never the account root AK",
        ],
        "known_issues": [
            "Whitelist not provisioned: the bucket is not open for Veeam by default; Alibaba Cloud backend must enable the compatibility whitelist manually - the customer cannot self-serve. File a support ticket providing bucket name(s), region(s) and account UID (real ticket cases: cn-shanghai and cn-beijing Veeam repositories)",
            "Backup files downloaded from OSS look unreadable: Veeam stores data in a proprietary chunked/encapsulated format, NOT the original file layout; direct download via ossbrowser/ossutil is not restorable. Restore must be performed through the Veeam console (real ticket case)",
            "'V1 signature is forbidden' from the repository validation step: enable V4 signing and set the bucket region in the repository configuration",
        ],
        "remediation_boundary": "This skill only explains the configuration and the whitelist request procedure; it never submits the whitelist request, never modifies the bucket, and never touches Veeam settings.",
        "official_doc_ref": DOC_AWS_SDK,
    },
    "synology": {
        "aliases": ["synology", "群晖", "qunhui", "synology nas", "dsm", "hyper backup", "cloud sync"],
        "category": "tool_usage",
        "side": "client",
        "summary": "Synology NAS (DSM Hyper Backup / Cloud Sync) reaches OSS through the S3-compatible interface; failures concentrate on endpoint form, credentials and legacy signature defaults on old firmware.",
        "config_checklist": [
            "Provider type: S3 storage / S3-compatible; endpoint https://s3.oss-{region}.aliyuncs.com (public) or the internal form when the NAS egresses through a same-region gateway",
            "Virtual-hosted style only: bucket name goes into the host, not the URL path",
            "AccessKey pair of a dedicated RAM user with least-privilege actions (PutObject/GetObject/ListObjects + multipart actions for large backups)",
            "Update DSM and the Hyper Backup / Cloud Sync package to the current version: legacy builds may default to the deprecated V1 signature and get 'V1 signature is forbidden'",
            "If the package exposes a signature-version or region option, set region to the bucket region ID (e.g. cn-hangzhou) and signature to V4",
        ],
        "known_issues": [
            "'V1 signature is forbidden' on old DSM/package versions: update firmware and package; if no update path exists the NAS backup must move to a V4-capable client",
            "Connection succeeds but large backups fail midway: enable multipart/resumable upload options and check NAS uplink bandwidth and MTU",
            "403 on HeadBucket during connection validation: the RAM policy needs oss:GetBucketInfo (S3 HeadBucket maps to GetBucketInfo on OSS)",
        ],
        "remediation_boundary": "This skill only gives configuration advice for the Synology side; it never changes DSM settings, bucket ACLs or RAM policies.",
        "official_doc_ref": DOC_S3_COMPAT,
    },
    "generic": {
        "aliases": ["generic", "s3 client", "s3-compatible", "s3兼容", "第三方工具", "第三方备份工具", "third-party", "rclone", "aws cli", "aws sdk", "s3cmd", "cyberduck", "s3browser"],
        "category": "tool_usage",
        "side": "client",
        "summary": "Generic S3-compatible clients (rclone, AWS CLI/SDK, s3cmd, etc.) talking to OSS; failures concentrate on endpoint form, request style, signature version and destructive sync semantics.",
        "config_checklist": [
            "Endpoint: https://s3.oss-{region}.aliyuncs.com (public), https://s3.oss-{region}-internal.aliyuncs.com (internal), https://s3.oss-accelerate.aliyuncs.com (transfer acceleration)",
            "rclone example: type=s3, provider=Alibaba, endpoint=oss-{region}.aliyuncs.com, access keys of a least-privilege RAM user",
            "AWS SDK/CLI: always prefix the endpoint with https://, set the region to the bucket region (or use endpointOverride with a valid URI)",
            "Virtual-hosted style only; disable force_path_style",
            "Signature V4: OSS is phasing out V1; tools signing with V1 are rejected",
        ],
        "known_issues": [
            "rclone sync can delete destination objects when sources are missing: sync mirrors the source onto OSS; without bucket versioning a mistaken sync is unrecoverable (real ticket case). Enable versioning before granting DeleteObject, or prefer copy over sync",
            "'The URI scheme of endpointOverride must not be null' (AWS SDK): the endpoint string misses the https:// prefix",
            "HeadBucket 403 via S3 compatibility: grant oss:GetBucketInfo",
            "ETag checks fail: OSS PUT ETags are uppercase while S3 clients may expect lowercase; multipart ETag computation also differs - make ETag comparison case-insensitive or skip it",
        ],
        "remediation_boundary": "This skill only advises on client configuration; it never runs rclone/AWS CLI against the user's bucket and never syncs, deletes or rewrites data.",
        "official_doc_ref": DOC_AWS_SDK,
    },
}

TOOL_KEYS = sorted(TOOL_CATALOG.keys())

# --- Retrieval / minimum-duration fee judgment table ------------------------
# Root cause criteria from official billing docs + ticket clustering.

RETRIEVAL_RULES = {
    "standard": {
        "label": "Standard",
        "retrieval_fee": False,
        "judgment": [
            "Standard storage has NO retrieval fee; any RetrievalData billing item means the accessed objects are not Standard",
            "Common cause: objects were converted to Infrequent Access / Archive by a lifecycle rule, or were uploaded with a per-object storage class by the backup tool",
            "Check the actual storage class of the billed objects (console object detail or billing usage line) before attributing the fee",
        ],
        "recommendations": [
            "Keep frequently restored backup data on Standard storage",
            "Audit lifecycle rules and per-object storage-class settings of the backup job",
        ],
    },
    "ia": {
        "label": "Infrequent Access (IA)",
        "retrieval_fee": True,
        "judgment": [
            "Every read of an IA object bills retrieval capacity (billing item RetrievalData): fee = retrieved GB x IA retrieval unit price",
            "Partial reads via HTTP Range or SelectObject bill only the retrieved byte range; full-object reads bill the whole object size",
            "IA objects have a 30-day minimum storage duration: backup tools that overwrite or delete objects earlier (incremental/rotating backups) trigger 'insufficient-duration' storage fees for the remaining days - a classic surprise bill for backup workloads (official docs + ticket cluster)",
            "Retrieval fees are pay-as-you-go only; no resource package covers data retrieval (real ticket case)",
        ],
        "recommendations": [
            "For backups restored or rotated more often than monthly, move the bucket/prefix back to Standard storage",
            "Keep lifecycle-driven IA conversion only for prefixes that are genuinely cold for 30+ days",
            "Size the retention window so objects live at least 30 days before overwrite/delete",
        ],
    },
    "archive": {
        "label": "Archive",
        "retrieval_fee": True,
        "judgment": [
            "Archive objects must be restored (unfrozen) before reading; the restore bills retrieval capacity: fee = restored file size x archive retrieval unit price",
            "Access between restore completion and re-freeze does NOT bill another restore - 'restore is free, only retrieval bills' is a misconception: restoring IS what triggers retrieval billing (real ticket case)",
            "Archive has a 60-day minimum storage duration; earlier conversion or deletion bills the remaining days",
            "Restore via the S3 API ignores S3 restore-days settings: the restored state lasts 1 day by default and can be extended to at most 7 days, then the object re-freezes",
        ],
        "recommendations": [
            "Plan restores in batches; avoid repeated single-object restores",
            "If backups need frequent test-restores, use ColdArchive with bulk tier or keep a Standard copy",
            "Do not delete/converse archive objects before 60 days of age",
        ],
    },
    "coldarchive": {
        "label": "Cold Archive",
        "retrieval_fee": True,
        "judgment": [
            "Cold Archive restore bills by retrieval tier: Standard (CAStdRetrievalData), High Priority (CAHighPriorRetrievalData, fastest and most expensive), Bulk (CABulkRetrievalData, slowest and cheapest)",
            "180-day minimum storage duration; earlier conversion/deletion bills the remaining days",
            "A backup job configured to 'verify by restoring' at high priority silently burns the most expensive tier",
        ],
        "recommendations": [
            "Default restore jobs to the Bulk or Standard tier; reserve High Priority for real incidents",
            "Disable routine restore-verification of cold backups or verify a sampled subset only",
        ],
    },
    "deepcoldarchive": {
        "label": "Deep Cold Archive",
        "retrieval_fee": True,
        "judgment": [
            "Deep Cold Archive restore bills by tier: Standard (DeepCAStdRetrievalData) or High Priority (DeepCAHighPriorRetrievalData)",
            "180-day minimum storage duration; earlier conversion/deletion bills the remaining days",
        ],
        "recommendations": [
            "Use Deep Cold Archive only for backups with restore frequency measured in years",
            "Prefer the Standard retrieval tier for planned restores",
        ],
    },
}

STORAGE_CLASS_ALIASES = {
    "standard": ["standard", "标准", "标准存储"],
    "ia": ["ia", "infrequent", "infrequent access", "低频", "低频访问", "低频存储"],
    "archive": ["archive", "归档", "归档存储"],
    "coldarchive": ["coldarchive", "cold archive", "冷归档", "冷归档存储"],
    "deepcoldarchive": ["deepcoldarchive", "deep cold archive", "深度冷归档"],
}

# Symptom routing: ordered list of (route_id, regex). First hit wins.
import re  # noqa: E402  (standard library, kept local to avoid import-order churn)

SYMPTOM_ROUTES = [
    ("retrieval_fee", re.compile(r"retriev|取回|解冻|数据取回|取回费|取回费用|restore fee", re.IGNORECASE)),
    ("whitelist", re.compile(r"加白|白名单|whitelist|white-list|compatibility whitelist", re.IGNORECASE)),
    ("path_style", re.compile(r"path[- ]?style|路径风格|path style", re.IGNORECASE)),
    ("v1_forbidden", re.compile(r"v1|签名.{0,6}(禁|下线)|signature.{0,20}forbidden|signature.{0,20}deprecat", re.IGNORECASE)),
    ("format_unreadable", re.compile(r"无法识别|格式.{0,4}(不一致|不对)|unrecognized|unreadable|proprietary format", re.IGNORECASE)),
]

WHITELIST_GUIDANCE = {
    "category": "whitelist",
    "side": "server",
    "root_cause_directions": [
        "Some backup tools (notably Veeam Backup & Replication) require a compatibility whitelist entry on the bucket before first use; OSS does not open this by default",
        "The whitelist is provisioned manually by the Alibaba Cloud backend; there is no self-service switch in the console (real ticket cluster: Veeam repositories in cn-shanghai / cn-beijing)",
    ],
    "configuration_advice": [
        "Submit a support ticket (工单) requesting whitelist provisioning, providing: account UID, bucket name(s), bucket region(s) and the backup tool name/version",
        "After provisioning, re-run the tool's repository validation/connection test",
        "This skill cannot submit the ticket or perform the provisioning; it only produces the request guidance",
    ],
    "official_doc_ref": DOC_AWS_SDK,
}

FORMAT_NOTE = {
    "category": "tool_usage",
    "side": "client",
    "root_cause_directions": [
        "Backup software (e.g. Veeam) stores data in a proprietary chunked/encapsulated format inside OSS; objects are not the original files (real ticket case)",
        "Downloading such objects directly (ossbrowser/ossutil/S3 client) yields data the backup software cannot recognize outside its own restore path",
    ],
    "configuration_advice": [
        "Restore through the backup software's own console/job (e.g. Veeam restore), never by direct object download",
        "Do not convert, rename or repack the downloaded objects - that destroys the backup chain",
    ],
    "official_doc_ref": DOC_S3_COMPAT,
}
