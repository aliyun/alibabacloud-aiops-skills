#!/usr/bin/env python3
"""

_rules_resource.py -- Resource existence, naming and serving-behaviour rules
============================================================================
SECURITY: READ-ONLY. Pure logic over collected evidence; no cloud I/O.

Internal module (prefixed with `_`). Do NOT run directly.

Contents
--------
  * rule_bucket_name_validation    the name itself is not addressable
  * rule_bucket_existence          404 on the bucket
  * rule_object_existence          404 on the object, with deletion evidence
  * rule_knowledge_rule            documented meaning, no deeper local cause
  * rule_forced_download           served as a download instead of a preview
  * rule_image_source_validation   image processing refused by a bad source
"""

from __future__ import annotations

import re

from _constants import (
    SUSPICIOUS_OBJECT_SIZE_BYTES,
    VERDICT_NEEDS_CONFIRMATION,
    VERDICT_SELF_DIAGNOSABLE,
)
from _policy_hit import validate_bucket_name_from_host
from _rule_common import _request_attributes


def rule_bucket_name_validation(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A, decided locally from the host header."""
    check = validate_bucket_name_from_host(str(row.get("host") or ""),
                                           ctx["bucket"])
    if not check["extracted_name"]:
        # No host value means no evidence. Asserting an invalid name here would
        # be a guess, so the verdict is downgraded.
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The bucket name could not be extracted, so the "
                           "invalid-name error cannot be confirmed."),
            "root_cause": (
                "This rule is decided entirely from the host header of the "
                "failing request, and no host value was available: either no "
                "logged row matched, or the row carries no host. Declaring the "
                "name invalid without that value would be a guess."),
            "recommendations": [
                "Trace the failing request by its request ID so the host header "
                "becomes available, then re-run.",
                "Or supply the exact host or bucket name the client used.",
            ],
            "evidence": check,
        }
    if check["name_source"] != "host":
        # The name came from the caller, not from the logged host header, so it
        # cannot prove what the failing request actually used. Word the finding
        # according to whether the supplied name itself is valid.
        if check["name_valid"]:
            return {
                "verdict": VERDICT_NEEDS_CONFIRMATION,
                "conclusion": ("The bucket name supplied for this diagnosis "
                               "satisfies the naming rules, so an invalid-name "
                               "error cannot be explained by it."),
                "root_cause": (
                    f"The name '{check['extracted_name']}' was provided by the "
                    f"caller and is valid. No logged host header was available "
                    f"(host value: '{check['host'] or 'unavailable'}'), so the "
                    f"host the failing request actually used is unknown and no "
                    f"cause is asserted."),
                "recommendations": [
                    "Trace the failing request by its request ID so the real "
                    "host header becomes available, then re-run.",
                ],
                "evidence": check,
            }
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The bucket name supplied for this diagnosis does "
                           "not satisfy the naming rules, but the failing "
                           "request's host header was not available."),
            "root_cause": (
                f"The name '{check['extracted_name']}' was provided by the "
                f"caller rather than read from a logged host header "
                f"(host value: '{check['host'] or 'unavailable'}'). "
                f"{' '.join(check['reasons'])} Because the logged request was "
                f"not available, this skill cannot confirm that the failing "
                f"request used this name, so the finding is reported as a "
                f"strong hint rather than a proven cause."),
            "recommendations": [
                "Trace the failing request by its request ID so the real host "
                "header becomes available, then re-run for a definitive "
                "answer.",
                "Meanwhile correct the bucket name in the client "
                "configuration: lowercase letters, digits and hyphens only, "
                "3 to 63 characters, no dot and no domain suffix.",
            ],
            "evidence": check,
        }
    if check["name_valid"]:
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The reported invalid-name error does not reproduce "
                           "from the logged host header."),
            "root_cause": (f"The name extracted from host '{check['host']}' is "
                           f"'{check['extracted_name']}', which satisfies the "
                           f"naming rules. The failing request may have used a "
                           f"different host than the one logged here."),
            "recommendations": [
                "Trace the exact failing request by its request ID and re-check "
                "its host header.",
            ],
            "evidence": check,
        }
    reason_text = " ".join(check["reasons"])
    return {
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "conclusion": ("The bucket name in the request is invalid, so such a "
                       "bucket can never exist."),
        "root_cause": (
            f"The host header '{check['host']}' yields the bucket name "
            f"'{check['extracted_name']}'. {reason_text} Bucket names may only "
            f"contain lowercase letters, digits and hyphens, be 3 to 63 "
            f"characters long, and start and end with a letter or digit. This "
            f"is different from a valid name that does not exist: here the name "
            f"itself is not allowed."
            + (" The value looks like a domain name, so a domain was probably "
               "used where a bucket name was expected."
               if check["looks_like_domain"] else "")),
        "recommendations": [
            "Correct the bucket name in the client configuration; do not "
            "include a domain suffix or a dot.",
            "If the intent was to reach a custom domain, use the custom domain "
            "as the host and keep the bucket name separate.",
        ],
        "evidence": check,
    }

def rule_bucket_existence(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A: the bucket does not exist, or the region/name is wrong."""
    facts = ctx["facts"]
    info = ctx["evidence"].get("bucket_info", {}) or {}
    if not info.get("available"):
        # The read never produced an answer, so existence is undetermined.
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("Whether this bucket exists could not be "
                           "determined."),
            "root_cause": (
                f"The bucket information read did not return an answer "
                f"({info.get('error_code') or 'not attempted'}). Existence can "
                f"be neither confirmed nor ruled out, and claiming the bucket "
                f"does not exist without a successful read would be a guess. "
                f"A permission gap on the bucket information read produces this "
                f"same outcome."),
            "recommendations": [
                "Check the degradation log for the exact error of the bucket "
                "information read and resolve it first (usually a missing read "
                "permission or a wrong region).",
                "Confirm the bucket name and its region in the console.",
                "Re-run once the read succeeds.",
            ],
            "evidence": {"bucket_info_error": info.get("error_code", ""),
                         "bucket_info_message": info.get("error_message", ""),
                         "request_attributes": _request_attributes(row)},
        }
    if info.get("configured"):
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The bucket does exist and is readable with the "
                           "current credential."),
            "root_cause": (
                f"The bucket information read succeeded (location "
                f"{facts.get('region') or '-'}), so the logged "
                f"'no such bucket' failure was not caused by a missing bucket. "
                f"The failing request most likely used a different endpoint "
                f"region than the bucket's real one, which produces a "
                f"misleading not-found style error."),
            "recommendations": [
                f"Point the client at the bucket's real region "
                f"({facts.get('region') or 'see the bucket info output'}).",
                "Trace the failing request by ID and compare its host header "
                "with the correct endpoint.",
            ],
            "evidence": {"facts": facts},
        }
    return {
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "conclusion": "The bucket does not exist.",
        "root_cause": (
            f"No bucket information could be read for '{ctx['bucket']}' "
            f"({info.get('error_code') or 'read failed'}). A request against a "
            f"non-existent bucket fails during routing, which is why the logged "
            f"identity fields stay empty. Either the name is misspelled or the "
            f"bucket was deleted."),
        "recommendations": [
            "Verify the bucket name character by character against the console.",
            "Confirm the endpoint region matches the bucket's region.",
            "If the bucket was deleted, its name may not be reusable.",
        ],
        "evidence": {"bucket_info_error": info.get("error_code", ""),
                     "request_attributes": _request_attributes(row)},
    }

def rule_object_existence(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A: the object is not there; the log shows its history."""
    history = ctx.get("object_history") or []
    removals = [h for h in history
                if str(h.get("operation") or "") in
                ("DeleteObject", "DeleteObjects", "ExpireObject")]
    if removals:
        lines = [f"The object was removed by a logged operation:"]
        for item in removals[:10]:
            lines.append(
                f"  {item.get('time', '-')}  {item.get('operation', '-')}  "
                f"status={item.get('http_status', '-')}  "
                f"requester={item.get('requester_id', '-')}  "
                f"ip={item.get('client_ip', '-')}  "
                f"sign_type={item.get('sign_type', '-')}")
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": "The object does not exist because it was deleted.",
            "root_cause": "\n".join(lines),
            "recommendations": [
                "Confirm whether that deletion was intended; the logged "
                "requester and client IP identify who issued it.",
                "If deletions must be recoverable, enable versioning so a "
                "delete marker is written instead of removing the data.",
                "Check whether a lifecycle rule is expiring this prefix.",
            ],
            "evidence": {"removal_events": removals[:20],
                         "history_rows": len(history)},
        }
    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": "The object does not exist and no removal was logged.",
        "root_cause": (
            f"No logged operation touched this object key inside the queried "
            f"window ({len(history)} row(s)). It may never have been uploaded, "
            f"it may have been removed before realtime logging was enabled or "
            f"outside the window, or the key may be spelled differently - keys "
            f"are URL encoded in the log."),
        "recommendations": [
            "Widen the window with --hours and re-run.",
            "Confirm the exact key, including case and any URL encoding.",
            "If versioning is enabled, list object versions to see whether a "
            "delete marker exists.",
        ],
        "evidence": {"history_rows": len(history)},
    }

def rule_knowledge_rule(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A for error codes whose cause is a documented behaviour."""
    ec = entry.get("ec", "")
    if ec == "0030-00000006":
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": "This is not an authorization failure.",
            "root_cause": (
                "A 404 on a bucket-policy read simply means the bucket has no "
                "policy configured. Reporting it as 'permission denied' is a "
                "misdiagnosis: the request was answered normally, there is "
                "nothing to fix."),
            "recommendations": [
                "No action is required unless a policy was expected; in that "
                "case the policy was removed or never saved.",
            ],
            "evidence": {"policy_statement_count":
                         ctx["facts"].get("policy_statement_count", 0)},
        }
    return {
        "verdict": (VERDICT_SELF_DIAGNOSABLE if (entry.get("meaning")
                                                 or entry.get("note"))
                    else VERDICT_NEEDS_CONFIRMATION),
        "conclusion": entry.get("meaning") or (
            "This error code is documented behaviour rather than a "
            "misconfiguration, but no specific detail is recorded for it here."),
        "root_cause": entry.get("note") or (
            "No further detail is recorded for this code in the knowledge base "
            "of this skill. Look the EC value up in the public OSS error-code "
            "documentation, where each code has its own page explaining the "
            "cause and the fix."),
        "recommendations": [
            "Adjust the caller so it no longer sends the conflicting request "
            "header, or drop the expectation that the bucket enforces it.",
            "Consult the public OSS error-code documentation for this EC value.",
        ],
        "evidence": {"request_attributes": _request_attributes(row),
                     "ec": entry.get("ec", ""),
                     "doc": entry.get("doc", "")},
    }

def rule_forced_download(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict A: a 200 response that forces a download instead of previewing."""
    facts = ctx["facts"]
    if not row:
        return {
            "verdict": VERDICT_NEEDS_CONFIRMATION,
            "conclusion": ("The forced-download code was reported, but no "
                           "logged request row was available to confirm it."),
            "root_cause": (
                "This conclusion depends on the request host and the response "
                "status of the actual request. Without a logged row neither is "
                "known, so the behaviour is explained in general terms only "
                "and not asserted for your request."),
            "recommendations": [
                "Re-run with --request-id so the failing request can be traced.",
                "Or confirm yourself whether the URL uses the default OSS "
                "domain; that is the condition this code depends on.",
            ],
            "evidence": {"host": "-", "default_domain_used": None,
                         "creation_date": facts.get("creation_date", "")},
        }
    host = str(row.get("host") or "")
    default_domain = ".aliyuncs.com" in host and "internal" not in host
    created = str(facts.get("creation_date") or "")
    after_cutoff = created[:10] > "2019-09-30" if created else None

    return {
        "verdict": VERDICT_SELF_DIAGNOSABLE,
        "conclusion": ("The request succeeded; the response was forced to "
                       "download rather than preview inline."),
        "root_cause": (
            f"The status is {row.get('http_status', '200')} with this "
            f"informational code, so this is expected behaviour rather than a "
            f"failure. For buckets created after 2019-09-30 15:00, image access "
            f"through the default OSS domain gets a Content-Disposition "
            f"attachment header. Request host '{host}' "
            f"{'is' if default_domain else 'is not'} a default OSS domain; "
            f"bucket creation date reads '{created or 'unavailable'}'"
            f"{'' if after_cutoff is None else (' and is after the cutoff' if after_cutoff else ' and is before the cutoff')}."),
        "recommendations": [
            "Bind a custom domain and serve the image through it; the forced "
            "download does not apply to custom domains.",
            "Or front the bucket with a CDN using the custom domain.",
            "Or append response-content-disposition=inline to the request URL "
            "for a single override.",
        ],
        "evidence": {"host": host, "default_domain_used": default_domain,
                     "creation_date": created,
                     "http_status": row.get("http_status", "-")},
    }

def rule_image_source_validation(row: dict, entry: dict, ctx: dict) -> dict:
    """Verdict B: object read permission is not requested by default."""
    mime = str(row.get("mime_type") or ctx.get("mime_hint") or "")
    size_raw = str(row.get("object_size") or "")
    try:
        size = int(float(size_raw))
    except ValueError:
        size = None

    from _constants import IMAGE_PROCESSING_SUPPORTED_TYPES
    if mime and not mime.startswith("image/"):
        return {
            "verdict": VERDICT_SELF_DIAGNOSABLE,
            "conclusion": "Image processing does not apply to this content type.",
            "root_cause": (
                f"The logged content type is '{mime}', which is not an image "
                f"type. Image processing supports "
                f"{', '.join(IMAGE_PROCESSING_SUPPORTED_TYPES)} only. Applying "
                f"it to a video or other binary is rejected before any image "
                f"decoding happens."),
            "recommendations": [
                "Remove the image-processing parameter for this object.",
                "For video, use a media processing service instead.",
            ],
            "evidence": {"mime_type": mime, "object_size": size_raw},
        }

    suspicious = size is not None and size < SUSPICIOUS_OBJECT_SIZE_BYTES
    return {
        "verdict": VERDICT_NEEDS_CONFIRMATION,
        "conclusion": ("Image processing rejected the source object; the "
                       "object content must be inspected to close this."),
        "root_cause": (
            f"The logged content type is '{mime or 'unavailable'}' and the "
            f"object size is {size_raw or 'unavailable'} bytes."
            + (f" A size below {SUSPICIOUS_OBJECT_SIZE_BYTES} bytes cannot be a "
               f"real image, which strongly suggests the upload wrote a "
               f"placeholder string instead of image bytes."
               if suspicious else
               " The size is plausible for an image, so the content itself is "
               "likely corrupt, truncated, or named with a content type that "
               "does not match its real format.")
            + " Proving which requires downloading the object and checking its "
              "magic bytes. This skill does not hold object read permission by "
              "default, so it hands you the command instead of running it."),
        "recommendations": [
            "Download the object without any processing parameter and inspect "
            "the first bytes; references/module3_error_codes.md lists the magic "
            "byte signature of each supported image format.",
            "If the content is a single ASCII character or all zeros, the "
            "upload path wrote a placeholder - fix the upload code and "
            "re-upload.",
            "If the magic bytes disagree with the content type, re-upload with "
            "the correct content type.",
        ],
        "evidence": {"mime_type": mime, "object_size": size_raw,
                     "size_suspicious": suspicious,
                     "request_attributes": _request_attributes(row)},
    }
