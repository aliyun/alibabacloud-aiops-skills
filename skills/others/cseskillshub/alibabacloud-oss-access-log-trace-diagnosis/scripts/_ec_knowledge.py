#!/usr/bin/env python3
"""
_ec_knowledge.py -- EC error-code knowledge base
=================================================
SECURITY: READ-ONLY reference data. No cloud I/O, no credential handling.

Internal module (prefixed with `_`). Do NOT run directly.

Keys are EC codes as they appear in the realtime access log 'ec' field and in
the OSS error response body. Every entry states the verdict class, the
evidence to collect, and the public documentation link.

PROVENANCE: meanings are the publicly documented ones. No customer
identifiers, bucket names, AccessKey values, account IDs or request IDs are
embedded here; documentation links point at the public help centre only. A
code that is not listed is reported as unknown by lookup_knowledge() rather
than mapped onto the nearest neighbour.

This table lives in its own module because it is reference data rather than
configuration: it is the largest table in the skill and it grows independently
of the constants in _constants.py. The verdict classes it uses are imported
from there, so importing this module can never form a cycle.
"""

from _constants import (
    VERDICT_ESCALATE,
    VERDICT_NEEDS_CONFIRMATION,
    VERDICT_SELF_DIAGNOSABLE,
)

# ---------------------------------------------------------------------------
# EC error-code knowledge base
# ---------------------------------------------------------------------------
# Keys are EC codes as they appear in the realtime access log 'ec' field and in
# the OSS error response body. Every entry states the verdict class, the
# evidence to collect, and the public documentation link.
#
# NOTE ON PROVENANCE: meanings are the publicly documented ones. No customer
# identifiers, bucket names, AccessKey values, account IDs or request IDs are
# embedded here; all examples in references use synthetic values.

EC_KNOWLEDGE = {
    # ---- authorization: bucket policy ----
    "0003-00000101": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "The request was denied by a bucket policy statement.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "policy_hit_analysis",
        "evidence_apis": ["oss:GetBucketPolicy"],
        "log_fields": ["vpc_id", "client_ip", "access_id", "requester_id",
                       "extend_information", "sign_type", "operation", "object"],
        "doc": "https://help.aliyun.com/zh/oss/user-guide/0003-00000101",
        "note": (
            "A presigned URL does NOT bypass a bucket policy: the policy is "
            "evaluated before signature acceptance."
        ),
    },
    "0003-00000201": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "The request was denied by a RAM policy attached to the caller identity.",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "ram_deny_scan",
        "evidence_apis": ["ram:ListPoliciesForUser", "ram:GetPolicy"],
        "log_fields": ["access_id", "requester_id", "extend_information", "operation"],
        "doc": "https://help.aliyun.com/zh/oss/user-guide/0003-00000201",
        "note": (
            "An explicit Deny outranks every Allow, so adding an Allow in a "
            "bucket policy cannot fix this. Both a RAM identity policy Deny "
            "and a resource-directory control policy produce this code and the "
            "two cannot be told apart from the log alone."
        ),
    },
    "0003-00000905": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "An anonymous request was denied.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "anonymous_denied",
        "evidence_apis": ["oss:GetBucketAcl", "oss:GetBucketPolicy",
                          "oss:GetPublicAccessBlock"],
        "log_fields": ["sign_type", "operation", "access_id", "host"],
        "note": (
            "Neither public-read nor public-read-write grants anonymous "
            "listing. Anonymous ListObjects requires a bucket policy "
            'statement with Principal ["*"]. Also note the logged operation '
            "for listing is GetBucket."
        ),
    },
    "0003-00000005": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "No read permission on the requested object.",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "object_read_denied",
        "evidence_apis": ["oss:GetBucketAcl", "oss:GetObjectAcl"],
        "log_fields": ["object", "sign_type", "access_id", "operation"],
        "note": (
            "Two causes only. First: the bucket is public-read but this object "
            "carries its own private ACL - verifiable with the object ACL and "
            "fixable by setting the object ACL back to default. Second: the "
            "object is blocked at platform level, which is NOT verifiable "
            "through customer-facing APIs and must be escalated. Never invent "
            "a third cause such as a content-security interception."
        ),
        "escalate_if": "object ACL is not private, or object ACL cannot be read",
    },
    "0003-00000001": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "The request was denied by a platform-level security policy.",
        "verdict": VERDICT_ESCALATE,
        "diagnosis": "escalate",
        "evidence_apis": [],
        "log_fields": ["client_ip", "host", "operation"],
        "note": (
            "The policy content is not readable through customer-facing APIs. "
            "Retrying or re-issuing credentials does not help, because the "
            "denial happens before credential evaluation."
        ),
    },
    "0003-00000801": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "The account is disabled (UserDisable).",
        "verdict": VERDICT_ESCALATE,
        "diagnosis": "escalate",
        "evidence_apis": [],
        "log_fields": ["owner_id", "requester_id"],
        "note": (
            "Whether the disablement comes from a compliance action or from an "
            "overdue balance is not distinguishable through customer-facing "
            "APIs. Check the billing console for an overdue balance first, "
            "then escalate with the request ID."
        ),
    },

    # ---- naming and existence ----
    "0015-00000101": {
        "error_code": "NoSuchBucket",
        "http_status": 404,
        "meaning": "The bucket does not exist.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "bucket_existence",
        "evidence_apis": ["oss:GetBucketInfo"],
        "log_fields": ["host", "bucket", "sign_type", "response_time"],
        "note": (
            "The name is valid but no such bucket exists: it was deleted, or "
            "the name or the region in the endpoint is wrong. When the bucket "
            "does not exist, sign_type / access_id / owner_id stay empty "
            "because the request failed during routing."
        ),
    },
    "0015-00000001": {
        "error_code": "InvalidBucketName",
        "http_status": 400,
        "meaning": "The bucket name does not follow the naming rules.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "bucket_name_validation",
        "evidence_apis": [],
        "log_fields": ["host"],
        "note": (
            "Decided locally from the host header: strip the endpoint suffix "
            "and validate the remainder. A dot or an underscore makes the name "
            "invalid, so such a bucket can never exist - typically a domain "
            "name was used where a bucket name was expected. Distinct from "
            "0015-00000101, where the name is valid but absent."
        ),
    },
    "0026-00000001": {
        "error_code": "NoSuchKey",
        "http_status": 404,
        "meaning": "The requested object does not exist.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "object_existence",
        "evidence_apis": ["oss:GetBucketInfo"],
        "log_fields": ["object", "operation", "http_status"],
        "note": (
            "Trace the object's own history in the access log to tell whether "
            "it was deleted, removed by a lifecycle rule, or never uploaded. "
            "Object keys are URL encoded in the log; decode before comparing. "
            "With versioning enabled, look for a delete marker."
        ),
    },

    # ---- request-level semantics ----
    "0026-00000002": {
        "error_code": "FileAlreadyExists",
        "http_status": 409,
        "meaning": "The object exists and the request asked not to overwrite it.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "knowledge_rule",
        "evidence_apis": [],
        "log_fields": ["operation", "object"],
        "note": (
            "This is a REQUEST-level control: the caller sent the "
            "x-oss-forbid-overwrite header. It is not a bucket-level "
            "'forbid overwrite' setting. In a versioning-enabled bucket the "
            "header has no effect - every write creates a new version."
        ),
    },
    "0026-00000004": {
        "error_code": "StaleFile",
        "http_status": 409,
        "meaning": "Concurrent modification of object metadata or tags.",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "concurrent_write_scan",
        "evidence_apis": [],
        "log_fields": ["operation", "object", "sign_type", "sync_request", "client_ip"],
        "note": (
            "Optimistic-locking conflict. When sign_type is AdminSign or "
            "sync_request points at a service-side task, this is OSS's own "
            "bookkeeping (for example last-access-time tracking), it is "
            "retried automatically and needs no action. Otherwise scan the "
            "same window for concurrent writes to the same object key."
        ),
    },
    "0048-00000105": {
        "error_code": "-",
        "http_status": 200,
        "meaning": "The response was forced to download instead of previewing inline.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "forced_download",
        "evidence_apis": ["oss:GetBucketInfo"],
        "log_fields": ["host", "operation", "http_status", "object"],
        "note": (
            "For buckets created after 2019-09-30 15:00, image access through "
            "the default OSS domain gets Content-Disposition: attachment. This "
            "is expected security behaviour, not a failure - status is 200. "
            "Fixes: bind a custom domain, front the bucket with a CDN, or add "
            "response-content-disposition=inline to the request."
        ),
    },
    "0040-00000005": {
        "error_code": "BadRequest",
        "http_status": 400,
        "meaning": "Image processing rejected the source object format.",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "image_source_validation",
        "evidence_apis": [],
        "log_fields": ["operation", "object", "object_size", "request_uri"],
        "note": (
            "Step 1: if the content type is a video or otherwise non-image "
            "type, image processing does not apply - close the case. Step 2: "
            "if it is an image type, inspect object_size; a value of 1 byte "
            "strongly suggests a placeholder was uploaded instead of image "
            "bytes. Step 3: download the object and check the magic bytes. "
            "Step 3 needs object read permission, which this skill does not "
            "request by default - hand the customer the exact command instead."
        ),
    },
    "0006-00000213": {
        "error_code": "InvalidPolicyDocument",
        "http_status": 403,
        "meaning": "The policy field of a form upload had expired.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "post_policy_expiry",
        "evidence_apis": [],
        "log_fields": ["operation", "sign_type", "request_length", "time"],
        "note": (
            "All OSS time parameters are UTC. A Beijing-time value written "
            "into expiration is parsed as UTC and therefore expires 8 hours "
            "LATER, not sooner - so a timezone mix-up is not the cause. Real "
            "causes: the validity window is too short, the client reuses a "
            "stale policy, or the signing server's clock drifts. Decode the "
            "policy form field (base64 JSON) and compare expiration with the "
            "logged request time."
        ),
    },

    # ---- signature family ----
    "0002-00000201": {
        "error_code": "SignatureDoesNotMatch",
        "http_status": 403,
        "meaning": "Header signature mismatch (V1 or V4).",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "signature_mismatch",
        "evidence_apis": [],
        "log_fields": ["access_id", "sign_type", "user_agent", "host",
                      "client_ip", "request_uri", "content_length_in"],
        "note": (
            "The server-side string-to-sign is not exposed through "
            "customer-facing APIs, so the mismatch cannot be pinpointed from "
            "the log alone. Narrow it instead: compare the access_id of "
            "failing and succeeding requests from the same client (mixed "
            "credentials), check whether the host indicates a proxy or CDN "
            "that could rewrite signed headers, and branch on user_agent - an "
            "official SDK signs correctly by itself, so a wrong secret or a "
            "misconfigured client is far more likely than an encoding issue. "
            "For hand-rolled signing, the customer must print their own "
            "string-to-sign for a layer-by-layer comparison."
        ),
    },
    "0002-00000040": {
        "error_code": "SignatureDoesNotMatch",
        "http_status": 403,
        "meaning": "Presigned-URL signature mismatch (V1 URL signature).",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "signature_mismatch",
        "evidence_apis": [],
        "log_fields": ["access_id", "sign_type", "user_agent", "request_uri", "host"],
        "note": (
            "Identified by OSSAccessKeyId + Expires + Signature in the query "
            "string. Same evidence limits as 0002-00000201. When user_agent "
            "is empty or non-SDK, the URL was signed by hand: ask for the "
            "client's own string-to-sign and check whether the URL was "
            "re-encoded between signing and sending."
        ),
    },
    "0002-00000504": {
        "error_code": "RequestTimeTooSkewed",
        "http_status": 403,
        "meaning": "The request timestamp is more than 15 minutes off the server clock.",
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "diagnosis": "clock_skew",
        "evidence_apis": [],
        "log_fields": ["access_id", "user_agent", "response_time", "time", "sign_type"],
        "note": (
            "The allowed skew is 15 minutes for both header signatures and "
            "temporary credentials. Two candidates: the client device clock "
            "runs slow (persistent failures), or the request sat in a client "
            "queue and was sent long after signing (sporadic failures, common "
            "on flaky mobile networks). A normal response_time rules out link "
            "latency. A whole-hour multiple such as 8 hours points at a "
            "timezone bug rather than clock drift."
        ),
    },

    # ---- back-to-origin ----
    "0024-00000008": {
        "error_code": "AccessDenied",
        "http_status": 403,
        "meaning": "The requested feature is gated and not enabled for this access path.",
        "verdict": VERDICT_ESCALATE,
        "diagnosis": "escalate",
        "evidence_apis": [],
        "log_fields": ["operation", "host", "vpc_id"],
        "note": (
            "Feature gating is not readable through customer-facing APIs. "
            "Record the operation and the access path, then escalate."
        ),
    },
    "0030-00000006": {
        "error_code": "NoSuchBucketPolicy",
        "http_status": 404,
        "meaning": "The bucket has no policy configured.",
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "diagnosis": "knowledge_rule",
        "evidence_apis": ["oss:GetBucketPolicy"],
        "log_fields": ["operation", "http_status"],
        "note": (
            "This is NOT an authorization failure. A 404 on a policy read "
            "simply means no policy exists. Reporting it as 'permission "
            "denied' is a misdiagnosis."
        ),
    },
}
