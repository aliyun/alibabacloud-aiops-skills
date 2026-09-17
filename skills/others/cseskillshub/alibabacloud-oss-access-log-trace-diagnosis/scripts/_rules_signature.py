#!/usr/bin/env python3
"""

_rules_signature.py -- Signature, clock, form-upload and write-contention rules
==============================================================================
SECURITY: READ-ONLY. Pure logic over collected evidence; no cloud I/O. Never
recomputes a signature from a secret: the scripts hold no AccessKey pair, so a
mismatch is narrowed by request attributes, not reproduced.

Internal module (prefixed with `_`). Do NOT run directly.

Contents
--------
  * rule_signature_mismatch      SignatureDoesNotMatch, narrowed by sign type,
                                 credential shape and host used
  * rule_clock_skew              request date outside the allowed skew
  * rule_post_policy_expiry      expired form-upload policy, decoded locally
  * rule_concurrent_write_scan   overwrite race between parallel uploads
"""

from __future__ import annotations

import re

from _constants import (
    TEMPORARY_CREDENTIAL_PREFIXES,
    VERDICT_NEEDS_CONFIRMATION,
    VERDICT_SELF_DIAGNOSABLE,
)
from _rule_common import _request_attributes


def rule_signature_mismatch(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict B: narrow the candidates; the decisive evidence is server-side."""
    user_agent = str(row.get("user_agent") or "")
    access_id = str(row.get("access_id") or "")
    host = str(row.get("host") or "")
    sign_type = str(row.get("sign_type") or "")
    request_uri = str(row.get("request_uri") or "")

    sdk_markers = ("aliyun-sdk-", "aliyun-oss-", "oss-", "aws-sdk-", "aliyun-sdk")
    is_sdk = any(marker in user_agent.lower() for marker in sdk_markers)
    presigned_v1 = all(token in request_uri for token in
                       ("OSSAccessKeyId", "Expires", "Signature"))
    presigned_v4 = "x-oss-signature" in request_uri.lower()
    proxied = (".aliyuncs.com" not in host) or ("cdn" in host.lower())

    candidates = []
    if not access_id.startswith(TEMPORARY_CREDENTIAL_PREFIXES):
        candidates.append({
            "rank": 1,
            "cause": "The AccessKey Secret does not match the AccessKey ID",
            "why": ("The service recognised the AccessKey ID (otherwise the "
                    "error would be an invalid-key error) but the computed "
                    "signature differed. A rotated, deleted or mistyped secret "
                    "is the most common reason."),
            "verify": ("Confirm the secret currently configured for "
                       f"'{access_id or 'the logged AccessKey ID'}', and check "
                       "whether it was rotated recently."),
        })
    if proxied:
        candidates.append({
            "rank": len(candidates) + 1,
            "cause": "An intermediary rewrote a header that participates in signing",
            "why": (f"The request host '{host}' is not a plain OSS endpoint. "
                    "A proxy, gateway or CDN can add or rewrite the x-oss-* , "
                    "Content-Type or Content-MD5 headers, so the server "
                    "computes a signature over a different request than the "
                    "client signed."),
            "verify": ("Send the same request directly to the OSS endpoint, "
                       "bypassing the intermediary, and compare the outcome."),
        })
    if not is_sdk:
        candidates.append({
            "rank": len(candidates) + 1,
            "cause": "Hand-rolled signing omitted a header or re-encoded the URL",
            "why": (f"The User-Agent '{user_agent or '(empty)'}' is not an "
                    "official SDK, so the signature was constructed manually. "
                    "Omitting Content-Type, Content-MD5 or an x-oss-* header "
                    "from the string to sign, or re-encoding the path between "
                    "signing and sending, both break the match."),
            "verify": ("Print the client's own string to sign (V1) or canonical "
                       "request (V4) and compare it layer by layer with what "
                       "was actually sent. references/module3_error_codes.md "
                       "lists what to print for each signature version."),
        })
    else:
        candidates.append({
            "rank": len(candidates) + 1,
            "cause": "An SDK client configuration mismatch",
            "why": ("An official SDK builds the signature itself, so a mismatch "
                    "usually means the client configuration differs from the "
                    "endpoint actually reached: a path-style setting used "
                    "against a virtual-hosted endpoint, a region that does not "
                    "match the bucket, or a missing temporary security token."),
            "verify": ("Check the SDK's endpoint format, path-style flag, region "
                       "and, for temporary credentials, that the security token "
                       "is actually passed."),
        })
    if presigned_v1 or presigned_v4 or sign_type in ("UriSign", "URI_SIGN4"):
        candidates.append({
            "rank": len(candidates) + 1,
            "cause": "The presigned URL was altered or re-encoded after signing",
            "why": ("The request used a presigned URL. If the URL was copied "
                    "through a layer that re-encodes characters, or the object "
                    "path used at signing time differs from the path actually "
                    "requested, the signature no longer matches."),
            "verify": ("Generate the URL and issue the request from the same "
                       "program without any intermediate string processing, "
                       "then compare."),
        })

    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": ("The signature did not match. The candidates are ranked "
                       "below, but the decisive comparison cannot be made from "
                       "the customer side."),
        "root_cause": (
            "A signature mismatch means the client and the service computed "
            "different values over the request. The service-side string to sign "
            "is only present in the server-side internal log, which is not "
            "exposed through any customer-facing API, so the mismatch cannot be "
            "pinpointed from your log alone. What the access log does establish "
            f"is the request shape: signature type '{sign_type or '-'}', "
            f"User-Agent '{user_agent or '(empty)'}', AccessKey ID "
            f"'{access_id or '-'}', host '{host}'. Do not read the logged URL "
            f"encoding as proof of an encoding bug: an SDK handles encoding "
            f"itself and the log only shows how the request arrived. Note also "
            f"that a wrong region in a V4 signature produces a malformed "
            f"authorization error, not this one."),
        "recommendations": [
            f"{c['rank']}. {c['cause']} - {c['verify']}" for c in candidates
        ] if False else [
            f"{c['rank']}. {c['cause']} Verify: {c['verify']}"
            for c in candidates
        ] + [
            "If none of these resolves it, open a ticket with the escalation "
            "package below; the service-side signature detail has to be read by "
            "support.",
        ],
        "evidence": {
            "candidates": candidates,
            "request_attributes": _request_attributes(row),
            "presigned_v1": presigned_v1,
            "presigned_v4": presigned_v4,
            "looks_like_sdk": is_sdk,
            "host_is_plain_endpoint": not proxied,
        },
    }

def rule_clock_skew(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict B: device clock drift versus a request queued too long."""
    response_time = str(row.get("response_time") or "-")
    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": ("The request timestamp was more than 15 minutes away "
                       "from the service clock."),
        "root_cause": (
            "The allowed skew is 15 minutes for both header signatures and "
            "temporary credentials. Two causes remain and the log cannot "
            "separate them: the client device clock runs slow, which produces "
            "persistent failures, or the request was signed and then held in a "
            "client or network queue for a long time before being sent, which "
            f"produces sporadic failures. The logged total response time is "
            f"{response_time} ms; a small value means the link itself was fast "
            f"once the request arrived, so link latency is not the cause. A "
            f"skew that is an exact multiple of one hour points at a timezone "
            f"bug rather than clock drift."),
        "recommendations": [
            "1. Check whether the failure is persistent or sporadic on this "
            "client: persistent points at the device clock, sporadic points at "
            "queueing on a flaky network.",
            "2. Compare the device time with a reliable time source and enable "
            "automatic time synchronisation.",
            "3. Compute the exact skew; if it is a whole number of hours, look "
            "for a timezone conversion in the signing code instead.",
            "4. If requests can be held before sending, sign as late as "
            "possible or retry with a fresh signature.",
        ],
        "evidence": {"response_time": response_time,
                     "logged_time": row.get("time", "-"),
                     "user_agent": row.get("user_agent", "-"),
                     "access_id": row.get("access_id", "-")},
    }

def rule_post_policy_expiry(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A when the policy document is supplied, otherwise B."""
    decoded = ctx.get("post_policy") or {}
    if decoded.get("decoded"):
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": "The form-upload policy had expired when the request arrived.",
            "root_cause": (
                f"The decoded policy carries expiration "
                f"'{decoded.get('expiration')}'. All OSS time parameters are "
                f"UTC. Expired relative to now: "
                f"{decoded.get('expired_relative_to_now')}. A timezone mix-up "
                f"is not the cause: a Beijing-time value written into "
                f"expiration is parsed as UTC and therefore expires eight "
                f"hours LATER, not sooner."),
            "recommendations": [
                "Lengthen the validity window; at least 15 minutes beyond the "
                "expected send time is a practical floor.",
                "Stop reusing a cached policy - regenerate it per upload.",
                "Synchronise the clock of the server that signs the policy.",
            ],
            "evidence": {"decoded_policy": {
                k: v for k, v in decoded.items() if k != "document"},
                "request_attributes": _request_attributes(row)},
        }
    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": "The form-upload policy was rejected as expired.",
        "root_cause": (
            "A form upload carries the policy as a base64 JSON form field, and "
            "the service checks the request time against its expiration. The "
            "policy document was not supplied, so the actual expiration could "
            "not be compared. Note that all OSS time parameters are UTC: a "
            "Beijing-time value in expiration is parsed as UTC and expires "
            "eight hours later, so a timezone mix-up is not the cause. The "
            "real causes are a window that is too short, a stale policy being "
            "reused, or a signing server whose clock drifts."),
        "recommendations": [
            "Re-run with --post-policy <base64> to decode the actual policy and "
            "compare its expiration with the logged request time.",
            "Lengthen the validity window and regenerate the policy per upload.",
            "Check the clock of the host that generates the policy.",
        ],
        "evidence": {"request_attributes": _request_attributes(row)},
    }

def rule_concurrent_write_scan(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict B: a version conflict, service-side or customer-side."""
    sign_type = str(row.get("sign_type") or "")
    sync_request = str(row.get("sync_request") or "")
    concurrent = ctx.get("concurrent_writes") or []

    if sign_type == "AdminSign" or (sync_request and sync_request != "-"):
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": ("This conflict comes from an OSS service-side task, "
                           "not from your request."),
            "root_cause": (
                f"The logged signature type is '{sign_type}' and the sync "
                f"request field is '{sync_request}', which identifies a "
                f"service-side task such as last-access-time bookkeeping. Such "
                f"a task uses optimistic locking: it reads the current object "
                f"version and re-checks it before writing, so a concurrent "
                f"write makes it fail with a stale-file conflict. The service "
                f"retries on its own and your data is unaffected. The rate of "
                f"these conflicts grows with the write rate of the bucket, "
                f"which is expected on a busy bucket."),
            "recommendations": [
                "No action is required for this request.",
                "If these entries are noisy in your monitoring, filter them by "
                "signature type rather than treating them as failures.",
            ],
            "evidence": {"sign_type": sign_type,
                         "sync_request": sync_request,
                         "concurrent_writes": len(concurrent)},
        }

    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": ("The object metadata or tag write lost an optimistic "
                       "locking race."),
        "root_cause": (
            f"{len(concurrent)} write operation(s) touched the same object key "
            f"inside the queried window. A stale-file conflict means the object "
            f"version changed between the read and the write of the failing "
            f"request. Whether that is a bug depends on whether your "
            f"application intends to write this object concurrently."),
        "recommendations": [
            "Review the listed concurrent writes and decide whether the "
            "concurrency is intended.",
            "If it is not, serialize the writers or use a conditional write "
            "based on the object version.",
            "If it is intended, treat this failure as retryable in the client.",
        ],
        "evidence": {"concurrent_writes": concurrent[:20],
                     "sign_type": sign_type,
                     "sync_request": sync_request},
    }
