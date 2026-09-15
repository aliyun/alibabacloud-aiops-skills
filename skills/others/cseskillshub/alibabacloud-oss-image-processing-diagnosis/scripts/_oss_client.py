#!/usr/bin/env python3
"""
_oss_client.py -- Shared OSS client for image-processing diagnosis
====================================================================
SECURITY: This skill is strictly READ-ONLY. Credentials are resolved ONLY
from the standard Alibaba Cloud environment variables of the default
credential chain (ALIBABA_CLOUD_ACCESS_KEY_ID /
ALIBABA_CLOUD_ACCESS_KEY_SECRET / ALIBABA_CLOUD_SECURITY_TOKEN). This module
never hardcodes credentials, never prompts for them, and never prints their
values. Only read-class queries are ever issued against OSS: GetBucketInfo
(bucket metadata), HeadObject (object metadata), and GET probes of an object
(optionally with the read-only x-oss-process rendering query). No mutating
call exists anywhere in this skill; style creation/changes are guidance only.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the diagnosis scripts so that every OSS call goes through ONE place carrying
timeout, degradation and observability guarantees.

Channels (measured, finalized):
  * OSS data-plane / metadata probes -> Python oss2 SDK (>= 2.19.0, < 3).
    Measured method signature for a rendering probe:
        bucket.get_object(key, params={'x-oss-process': <process-string>})
    (oss2 also exposes the equivalent native keyword form
    bucket.get_object(key, process=<process-string>); both measured OK.)
  * Caller identity / UID derivation -> `aliyun sts get-caller-identity`
    (plugin mode, CLI default credential chain), argument-list subprocess.

Observability:
  * User-Agent template: AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
  * skill-version: read at runtime from references/manifest.json (the single
    declaration place), never hardcoded in this module.
  * session-id: 32-character hex string (uuid4().hex), generated once per
    run, attached to every OSS SDK request (User-Agent header) and every
    aliyun CLI call (--user-agent) of the same run.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from typing import Any, Optional

import oss2
from oss2.credentials import Credentials

_SKILL_NAME = "alibabacloud-oss-image-processing-diagnosis"
# The UA skill-version is declared ONLY in references/manifest.json and read
# at runtime, so bumping the version never touches the code.
_MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "manifest.json")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_SKILL_VERSION: Optional[str] = None
_STS_ENDPOINT = "sts.aliyuncs.com"
_DEFAULT_TIMEOUT = 30   # seconds, applied to every single OSS SDK call
_CLI_TIMEOUT = 60       # seconds, applied to every single aliyun CLI call
_PROBE_MAX_BYTES = 4096  # cap for GET probe bodies (never streams full objects)
_SESSION_ID: Optional[str] = None


class OssClientError(RuntimeError):
    """Structured, normalized error for every OSS call.

    category values (stable contract consumed by the diagnosis entry):
      credentials      -- env credential chain not configured
      not_found        -- NoSuchBucket / NoSuchKey / NoSuchStyle (bucket,
                          object or image style missing; measured: 404
                          NoSuchStyle from probing ?x-oss-process=style/xxx)
      permission       -- 403 AccessDenied (incl. original-image protection)
      process          -- image processing rejected (400 BadRequest, e.g.
                          "This image format is not supported."), an
                          out-of-range processing parameter (400
                          InvalidArgument, EC 0040-* family), or an
                          IMG-specific 400 code without an EC prefix
                          (CutEdgeExceedRange / ImageTooLarge /
                          WatermarkError / MissingArgument / NotImplemented /
                          BadWebPImage / MemLimitExceeded)
      endpoint         -- wrong-region / must-use-specified-endpoint errors
                          (403 AccessDenied + "specified endpoint" wording
                          ONLY -- the HostId inside an error body is NOT an
                          endpoint signal)
      network          -- DNS failure ("no such host"), timeout, reset
      server           -- 5xx / service-side failures / account disabled by
                          OSS risk control (403 UserDisable)
      credentials        -- invalid/expired AK or STS token, signature mismatch
      invalid          -- invalid bucket name or request parameter
      unknown          -- anything else
    """

    def __init__(self, message: str, category: str = "unknown",
                 code: str = "", status: int = 0, hint: str = ""):
        super().__init__(message)
        self.category = category
        self.code = code
        self.status = status
        self.hint = hint

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "code": self.code,
            "status": self.status,
            "message": str(self),
            "hint": self.hint,
        }


class CliError(RuntimeError):
    """Raised when the aliyun CLI identity call fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Session-ID & User-Agent (observability)
# ---------------------------------------------------------------------------

def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_oss_client] session-id: {_SESSION_ID}", file=sys.stderr)
    return _SESSION_ID


class SkillVersionError(RuntimeError):
    """references/manifest.json is missing, unreadable or has no valid version.

    UA-SKILL-VERSION forbids inventing, guessing or reusing a version, so the
    run stops here instead of falling back to a placeholder value.
    """


def skill_version() -> str:
    """Return the UA skill-version read from references/manifest.json.

    Resolved lazily on the first User-Agent build -- i.e. before the first cloud
    call of the run -- and cached for the rest of the run, the same way as the
    session-id. A missing/unreadable manifest or a malformed version raises
    SkillVersionError instead of substituting a placeholder such as `unknown`.
    """
    global _SKILL_VERSION
    if _SKILL_VERSION is None:
        try:
            with open(_MANIFEST_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh).get("version")
        except (OSError, ValueError, AttributeError) as exc:
            raise SkillVersionError(
                f"cannot read the skill version from {_MANIFEST_PATH}: {exc}"
            ) from exc
        version = str(raw or "").strip()
        if not _VERSION_RE.match(version):
            raise SkillVersionError(
                f"references/manifest.json carries no valid version "
                f"(got {raw!r}); refusing to guess the UA skill-version")
        _SKILL_VERSION = version
    return _SKILL_VERSION


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return (f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{session_id()} "
            f"skill-version/{skill_version()}")


# ---------------------------------------------------------------------------
# Credentials provider (env-var default chain only -- SA-2.12 compliant)
# ---------------------------------------------------------------------------

class EnvCredentialsProvider:
    """CredentialsProvider reading the ALIBABA_CLOUD_* environment variables.

    The oss2 built-in EnvironmentVariableCredentialsProvider reads OSS_*
    prefixed variables, which do not match the platform's default credential
    chain, so this provider reads:
      ALIBABA_CLOUD_ACCESS_KEY_ID
      ALIBABA_CLOUD_ACCESS_KEY_SECRET
      ALIBABA_CLOUD_SECURITY_TOKEN   (optional, present for STS sessions)
    Values are never printed or logged anywhere.
    """

    def get_credentials(self) -> Credentials:
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
        access_key_secret = os.environ.get(
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
        security_token = os.environ.get(
            "ALIBABA_CLOUD_SECURITY_TOKEN", "").strip()
        if not access_key_id or not access_key_secret:
            raise OssClientError(
                "no credentials found in the environment credential chain "
                "(ALIBABA_CLOUD_ACCESS_KEY_ID / "
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET are not set); configure the "
                "default credential chain first, never pass AK/SK manually",
                category="credentials", code="NoCredentials",
            )
        return Credentials(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
        )


# ---------------------------------------------------------------------------
# Transient-failure retry (bounded, read-only, observable)
# ---------------------------------------------------------------------------

# Only service-side transient failures are retried: credential, permission,
# endpoint, not-found and invalid-input errors are deterministic, so retrying
# them would only add latency to an answer that is already final. The fixed
# delay list bounds the added latency to 4s on top of the per-call timeout.
_RETRY_DELAYS = (1.0, 3.0)
_RETRYABLE_CODES = frozenset({
    "InternalError", "ServiceUnavailable", "SlowDown", "RequestTimeout",
    "OperationTimeout", "TooManyRequests", "Throttling",
})


def _is_retryable(err: OssClientError) -> bool:
    """True when a normalized error looks transient (5xx or throttling)."""
    return err.category == "server" or err.code in _RETRYABLE_CODES


def _operation_label(method: str, bucket_name: str, endpoint: str) -> str:
    """Render an oss2 method name as the OSS operation name for [WARN] traces.

    SDK method names map 1:1 onto the CamelCase operation names
    (get_bucket_info -> GetBucketInfo), so a retry trace names the operation
    the customer would have to quote in a follow-up ticket.
    """
    op = "".join(part.capitalize() for part in str(method).split("_"))
    if bucket_name:
        return f"{op} bucket={bucket_name} endpoint={endpoint}"
    return f"{op} endpoint={endpoint}"


def _call_with_retry(operation: str, fn, *args, **kwargs):
    """Run one read-only OSS call, re-issuing it on transient 5xx/throttling.

    Classification goes through _normalize_oss_error, but the ORIGINAL
    exception is re-raised once the retries are used up, so every caller keeps
    producing its own operation-specific error message unchanged. Each retry
    leaves a [WARN] trace on stderr, keeping the degradation visible.
    """
    attempt = 0
    while True:
        try:
            return fn(*args, **kwargs)
        except OssClientError:
            raise
        except Exception as exc:
            err = _normalize_oss_error(exc, operation)
            if attempt >= len(_RETRY_DELAYS) or not _is_retryable(err):
                raise
            delay = _RETRY_DELAYS[attempt]
            attempt += 1
            print(f"[WARN] {operation}: transient {err.category} "
                  f"({err.code or 'HTTP ' + str(err.status)}) -- retry "
                  f"{attempt}/{len(_RETRY_DELAYS)} in {delay:.0f}s",
                  file=sys.stderr)
            time.sleep(delay)


class _RetryingHandle:
    """Read-only proxy around an oss2 handle, adding the bounded retry above.

    Every SDK call of this module goes through a handle built here, so
    wrapping the handle once keeps the transient-error policy in ONE place
    instead of duplicating a retry loop per operation. Non-callable attributes
    are forwarded untouched; callables are intercepted only to re-issue the
    very same read-only request.
    """

    def __init__(self, handle, bucket_name: str = "", endpoint: str = ""):
        self._handle = handle
        self._bucket_name = bucket_name
        self._endpoint = endpoint

    def __getattr__(self, name):
        handle = object.__getattribute__(self, "_handle")
        attr = getattr(handle, name)
        if name.startswith("_") or not callable(attr):
            return attr

        def _call(*args, **kwargs):
            label = _operation_label(
                name, object.__getattribute__(self, "_bucket_name"),
                object.__getattribute__(self, "_endpoint"))
            return _call_with_retry(label, attr, *args, **kwargs)

        return _call


def _build_bucket(bucket_name: str, endpoint: str,
                  timeout: int = _DEFAULT_TIMEOUT) -> "_RetryingHandle":
    """Build an oss2.Bucket handle carrying UA + per-call timeout.

    oss2.Bucket raises oss2.exceptions.ClientError for an illegal bucket
    name (uppercase / underscore / special character / wrong length); it
    is converted here to the unified OssClientError(category="invalid")
    so the entry script degrades with [WARN] + STATUS: DEGRADED instead
    of a bare Traceback.
    """
    auth = oss2.ProviderAuth(EnvCredentialsProvider())
    session = oss2.Session()
    # Inject the observability User-Agent into every SDK request of this run.
    session.session.headers["User-Agent"] = user_agent()
    try:
        return _RetryingHandle(
            oss2.Bucket(auth, endpoint, bucket_name, session=session,
                        connect_timeout=timeout),
            bucket_name, endpoint)
    except oss2.exceptions.ClientError as exc:
        raise OssClientError(
            f"the bucket name '{bucket_name}' is invalid: bucket names must "
            "be 3-63 characters of lowercase letters, digits and hyphens, "
            "starting and ending with a lowercase letter or digit",
            category="invalid", code="InvalidBucketName",
            hint="Fix the bucket name spelling; this is a client-side input "
                 "problem and no API call was issued.",
        ) from exc


def _action_hint_suffix(operation: str) -> str:
    """Name the RAM action the failing call most likely needs.

    OSS action names track the control-plane operation name, so pointing at
    the concrete action beats a generic "check your RAM policy" line -- the
    403 class is the single most common dead end for customer-run diagnosis.
    """
    m = re.match(r"([A-Z][A-Za-z0-9]+)", operation or "")
    if not m:
        return ""
    op = m.group(1)
    return (f" The failing call is {op}: the RAM action that must be granted "
            f"for this caller is oss:{op} (see references/ram-policies.md).")


# IMG-specific 400 error codes WITHOUT the 0040-* EC prefix (official IMG
# error-response doc + FAQ + live measurements): they all belong to the
# image-processing parameter/source family. Their XML bodies carry the
# endpoint HostId, which must never be read as an endpoint signal.
_IMG_400_ERROR_CODES = frozenset({
    "CutEdgeExceedRange",   # crop region beyond source bounds (measured, B04)
    "ImageTooLarge",        # source beyond size/pixel limits (official doc)
    "WatermarkError",       # watermark parameter/object problem (official doc)
    "NotImplemented",       # action not implemented (official doc)
    "MissingArgument",      # required parameter missing (measured, B01)
    "BadWebPImage",         # animated WebP needs a whitelist (official FAQ)
    "MemLimitExceeded",     # source beyond pixel limits (ticket-bound)
})


def _normalize_oss_error(exc: Exception, operation: str) -> OssClientError:
    """Map any oss2/requests/socket failure to a structured OssClientError."""
    msg = str(exc).strip() or exc.__class__.__name__
    low = msg.lower()
    # Carry the OSS RequestId into every normalized error so the customer can
    # cite it in a follow-up ticket instead of re-describing the failure.
    _rid = str(getattr(exc, "request_id", "") or "").strip()
    if _rid and _rid not in msg:
        msg = f"{msg} [request-id: {_rid}]"
        low = msg.lower()

    if isinstance(exc, oss2.exceptions.NoSuchKey):
        return OssClientError(
            f"{operation}: the object does not exist ({msg})",
            category="not_found", code="NoSuchKey", status=404,
            hint="The requested object key does not exist in the bucket; "
                 "verify the key spelling, case and path prefix.",
        )
    if isinstance(exc, oss2.exceptions.NoSuchBucket):
        return OssClientError(
            f"{operation}: the bucket does not exist ({msg})",
            category="not_found", code="NoSuchBucket", status=404,
            hint="Verify the bucket name spelling; bucket names are global "
                 "and case-sensitive lowercase.",
        )
    if isinstance(exc, oss2.exceptions.AccessDenied):
        hint = ("Check RAM permission for this caller (see "
                "references/ram-policies.md), whether the bucket belongs to "
                "this account, and whether original-image protection is "
                "enabled on the bucket -- with protection enabled, direct "
                "anonymous GET of the original returns 403 while style-based "
                "access keeps working.")
        # G3-11: per the official doc, "does not belong to you" is a
        # client-side pre-check permission failure (the tool calls
        # ListObjects/GetBucketInfo before the real operation), NOT a bucket
        # ownership problem. Keep the error category as permission, but make
        # the hint lead with the missing bucket-level pre-check action.
        if "does not belong to you" in low:
            hint = ("Access denied (403) on a client-side pre-check: per the "
                    "official doc this message does NOT indicate a bucket-"
                    "ownership problem. The credential usually lacks "
                    "oss:ListObjects on the bucket-level resource "
                    "acs:oss:*:*:<bucket> (or oss:GetBucketInfo when the tool "
                    "pre-checks it) while holding only object-level actions. "
                    "Grant those bucket-level actions first; a wrong-account "
                    "credential or a wrong-region endpoint are secondary "
                    "hypotheses only.")
        return OssClientError(
            f"{operation}: access denied ({msg})",
            category="permission", code="AccessDenied", status=403,
            hint=hint + _action_hint_suffix(operation),
        )
    if isinstance(exc, oss2.exceptions.OssError):
        status = getattr(exc, "status", 0) or 0
        code = getattr(exc, "code", "") or ""
        # Measured: a rendering probe against a non-image (e.g. a PDF)
        # returns 400 BadRequest with message "This image format is not
        # supported." -- classify as the image-processing rejection path.
        if status == 400 and ("image format is not supported" in low
                              or "invalidimageformat" in low.replace(" ", "")
                              or code == "BadRequest"):
            return OssClientError(
                f"{operation}: image processing rejected ({msg})",
                category="process", code=code or "BadRequest", status=400,
                hint="The source object is not processable as an image: its "
                     "declared type or actual byte content (magic number) is "
                     "not a supported image format, or it exceeds the source "
                     "limits. Verify Content-Type, object size and magic "
                     "bytes per references/image-processing-playbook.md.",
            )
        # Measured: oss2 wraps transport-layer failures (DNS "no such host",
        # connect timeout, reset) into OssError/RequestError carrying status
        # -2 and an empty code; classify them as network.
        if status <= 0 or "requesterror" in low:
            return OssClientError(
                f"{operation}: network/client failure: {msg}",
                category="network", code=code or "NetworkError",
                status=status,
                hint="Check DNS resolution of the endpoint host, local "
                     "network, and whether an internal endpoint is used "
                     "outside the Alibaba Cloud network of its region.",
            )
        # Measured: probing a non-existent image style
        # (?x-oss-process=style/xxx) returns 404 NoSuchStyle whose error
        # body carries the endpoint HostId -- that HostId would falsely
        # trigger the endpoint-hint branch below, so classify 404
        # NoSuch*-style codes FIRST as not_found.
        if status == 404 and code.startswith("NoSuch"):
            if code == "NoSuchStyle":
                hint = ("The referenced image style does not exist on this "
                        "bucket; verify the style name in OSS console -> "
                        "bucket -> Data Processing -> Image Processing -> "
                        "Image Styles (this skill never creates styles).")
            elif code == "NoSuchKey":
                hint = ("The requested object key does not exist in the "
                        "bucket; verify the key spelling, case and path "
                        "prefix.")
            else:
                hint = ("The requested resource does not exist; verify the "
                        "bucket name / object key / style name spelling.")
            return OssClientError(
                f"{operation}: resource not found ({msg})",
                category="not_found", code=code, status=404, hint=hint,
            )
        # Measured (live ticket M-I1, EC=0040-00000312): probing an
        # out-of-range processing parameter (e.g. image/resize,w_99999999)
        # returns 400 InvalidArgument, Message 'The value: 99999999 of
        # parameter: w is invalid.', whose HostId carries the endpoint host
        # -- that used to falsely trigger the endpoint-hint branch below and
        # suggest switching endpoints. The 400 + 0040-* family is the image
        # processing parameter-error family (see references/params-limits.md,
        # common-errors table) and must classify as process, consistent with
        # the local process_validation verdict.
        ec = (getattr(exc, "ec", "") or "").strip()
        _param_reject = (
            "parameter" in low and "invalid" in low) or ec.startswith("0040")
        if status == 400 and (ec.startswith("0040") or (
                code == "InvalidArgument" and _param_reject)):
            return OssClientError(
                f"{operation}: image processing parameter rejected ({msg})",
                category="process", code=code or "InvalidArgument",
                status=400,
                hint="An x-oss-process parameter value is outside its legal "
                     "range (e.g. resize w must be 1-16384). Correct the "
                     "parameter per references/params-limits.md. This is a "
                     "parameter problem, NOT an endpoint problem -- do not "
                     "switch endpoints because of it.",
            )
        # IPM-1 (live ticket B04): probing image/crop,x_10,y_10,w_100,h_100
        # against a 1x1 source returns 400 CutEdgeExceedRange with NO
        # 0040-* EC field and no "parameter ... is invalid" wording -- but
        # the error body carries the bucket HostId, which used to falsely
        # trigger the endpoint-hint branch below and suggest switching
        # endpoints. The whole IMG-specific 400 code family is a
        # processing parameter/source problem and must classify as process
        # BEFORE any HostId-based guess.
        if status == 400 and (code in _IMG_400_ERROR_CODES
                              or "exceed the maximum allowable rotation"
                              in low):
            return OssClientError(
                f"{operation}: image processing request rejected ({msg})",
                category="process", code=code or "BadRequest", status=400,
                hint="The x-oss-process request was rejected by image "
                     "processing: e.g. the crop/circle region lies beyond "
                     "the source image bounds (CutEdgeExceedRange), the "
                     "source exceeds the pixel limits (MemLimitExceeded/"
                     "ImageTooLarge), or a watermark/action problem "
                     "(WatermarkError/MissingArgument/NotImplemented). "
                     "Correct the parameters per references/params-limits."
                     "md. This is NOT an endpoint problem -- do not switch "
                     "endpoints because of it.",
            )
        # IPM-1: only the explicit "must use specified endpoint" wording on
        # a 403 AccessDenied marks a genuine wrong-region/endpoint problem.
        # The endpoint HostId that every OSS error XML body carries is NOT
        # an endpoint signal (it used to misroute 400 IMG parameter errors
        # and 403 UserDisable to the endpoint category).
        if (status == 403 and code == "AccessDenied"
                and "specified endpoint" in low):
            return OssClientError(
                f"{operation}: wrong-region endpoint ({msg})",
                category="endpoint", code=code, status=status,
                hint="Use the endpoint of the region where the bucket was "
                     "created ('must use specified endpoint').",
            )
        # IPM-1 (B14, same root cause): 403 UserDisable (EC 0003-00000801
        # family) carries the endpoint HostId in its body and used to fall
        # into the endpoint category via the HostId regex. It actually
        # means the ACCOUNT owning the resource has been disabled by OSS
        # risk control -- switching endpoints or granting RAM permissions
        # will not fix it.
        if status == 403 and code == "UserDisable":
            return OssClientError(
                f"{operation}: account disabled ({msg})",
                category="server", code="UserDisable", status=403,
                hint="The account that owns this resource has been "
                     "disabled by OSS risk control (UserDisable, EC "
                     "0003-00000801 family). Switching endpoints or "
                     "granting RAM permissions will not fix it; the "
                     "resource owner must resolve the account-level block "
                     "with Alibaba Cloud support.",
            )
        hint = ""
        if status >= 500:
            category = "server"
        elif code in ("InvalidAccessKeyId", "SecurityTokenExpired",
                      "InvalidSecurityToken", "InvalidSecurityTokenVersion",
                      "SignatureDoesNotMatch"):
            # Measured: bad/expired STS credentials surface as HTTP 403 with
            # these codes, not as a RAM permission gap -- route to the
            # credential-chain guidance.
            category = "credentials"
            hint = ("The credential itself is invalid, expired or mismatched: "
                    "refresh the STS credential / re-export the "
                    "ALIBABA_CLOUD_* environment variables and retry. This is "
                    "NOT a missing RAM action, so granting more permissions "
                    "will not fix it.")
        elif code in ("InvalidBucketName", "InvalidArgument", "MalformedXML"):
            category = "invalid"
        else:
            category = "unknown"
        return OssClientError(
            f"{operation}: OSS error {code} (HTTP {status}): {msg}",
            category=category, code=code, status=status, hint=hint,
        )
    # Network-layer failures: DNS ("no such host"), timeout, reset, TLS.
    if isinstance(exc, oss2.exceptions.ClientError) or not isinstance(
            exc, oss2.exceptions.OssError):
        return OssClientError(
            f"{operation}: network/client failure: {msg}",
            category="network", code=getattr(exc, "code", "") or "NetworkError",
            hint="Check DNS resolution of the endpoint host, local network, "
                 "and whether an internal endpoint is used outside the "
                 "Alibaba Cloud network.",
        )
    return OssClientError(f"{operation}: {msg}", category="unknown")


# ---------------------------------------------------------------------------
# Read-only queries
# ---------------------------------------------------------------------------

# --- G3-11 inline assertions for _normalize_oss_error hint correctness ---
def _make_access_denied(message_text: str):
    """Helper: create an oss2 AccessDenied with a given message."""
    details = {"Code": "AccessDenied", "Message": message_text}
    return oss2.exceptions.AccessDenied(403, {"x-oss-request-id": "assert-test"}, b"", details)

_assert_exc = _make_access_denied("The bucket you access does not belong to you")
_assert_result = _normalize_oss_error(_assert_exc, "test_op")
assert _assert_result.category == "permission", f"G3-11: category must stay 'permission', got {_assert_result.category}"
assert "pre-check" in _assert_result.hint, f"G3-11: hint must mention 'pre-check', got: {_assert_result.hint[:80]}"
assert "ownership" not in _assert_result.hint.lower() or "NOT indicate a bucket-ownership" in _assert_result.hint,     f"G3-11 regression: hint must not lead with ownership, got: {_assert_result.hint[:80]}"
assert "oss:ListObjects" in _assert_result.hint, f"G3-11: hint must mention oss:ListObjects"

# Boundary: Chinese variant
_assert_exc_cn = _make_access_denied("\u60a8\u8bbf\u95ee\u7684Bucket\u4e0d\u5c5e\u4e8e\u60a8")  # not matched by EN pattern
_assert_result_cn = _normalize_oss_error(_assert_exc_cn, "test_op")
# CN variant falls through to the generic permission hint (not the EN-specific one)
assert _assert_result_cn.category == "permission"

# Boundary: other 403 (not belong-to-you) -- should get generic permission hint
_assert_exc_other = _make_access_denied("You have no right to access this object because of bucket acl.")
_assert_result_other = _normalize_oss_error(_assert_exc_other, "test_op")
assert _assert_result_other.category == "permission"
assert "pre-check" not in _assert_result_other.hint, "G3-11: non-belong-to-you 403 must NOT get pre-check hint"
# --- end G3-11 inline assertions ---

def get_bucket_info(bucket_name: str, endpoint: str,
                    timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS GetBucketInfo (read-only) and return normalized fields."""
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_info()
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(
            exc, f"GetBucketInfo bucket={bucket_name} endpoint={endpoint}")
    info = result
    acl = getattr(info, "acl", None)
    owner = getattr(info, "owner", None)
    return {
        "name": getattr(info, "name", "") or bucket_name,
        "location": getattr(info, "location", "") or "",
        "intranet_endpoint": getattr(info, "intranet_endpoint", "") or "",
        "extranet_endpoint": getattr(info, "extranet_endpoint", "") or "",
        "storage_class": getattr(info, "storage_class", "") or "",
        "acl": getattr(acl, "grant", "") if acl is not None else "",
        "creation_date": getattr(info, "creation_date", "") or "",
        "owner_id": getattr(owner, "id", "") if owner is not None else "",
    }


def head_object_meta(bucket_name: str, endpoint: str, key: str,
                     timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS HeadObject (read-only) for the object's declared metadata.

    SOP step 1+2 inputs: the declared Content-Type (mime_type) and the
    object size. Returns dict keys: content_type, content_length, etag.
    Raises OssClientError with a normalized category on any failure.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.head_object(key)
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(
            exc, f"HeadObject bucket={bucket_name} key={key}")
    return {
        "content_type": (getattr(result, "content_type", "") or "").strip(),
        "content_length": int(getattr(result, "content_length", 0) or 0),
        "etag": (getattr(result, "etag", "") or "").strip(),
    }


def probe_object(bucket_name: str, endpoint: str, key: str,
                 process: str = "", byte_range: Optional[tuple] = None,
                 max_bytes: int = _PROBE_MAX_BYTES,
                 timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Read-only GET probe of an object, optionally with x-oss-process.

    Measured invocation form (oss2 >= 2.19.0):
        bucket.get_object(key, params={'x-oss-process': <process>})
    Only the first `max_bytes` bytes are read (probe cap). With byte_range
    set (e.g. (0, 15)) it fetches the leading bytes of the ORIGINAL object
    for magic-number verification (SOP step 3) -- no process parameter is
    combined with a range request.

    Returns dict keys: status, content_type, content_disposition,
    x_oss_hash_crc64, body (bytes, capped), body_size.
    Raises OssClientError with a normalized category on any failure.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    params: dict = {}
    if process:
        params["x-oss-process"] = process
    try:
        result = bucket.get_object(
            key,
            byte_range=byte_range,
            params=params if params else None,
        )
        body = result.read(max_bytes) if max_bytes else result.read()
        headers = result.headers
        return {
            "status": int(getattr(result, "status", 0) or 0),
            "content_type": (headers.get("Content-Type") or "").strip(),
            "content_disposition": (
                headers.get("Content-Disposition") or "").strip(),
            "body": body,
            "body_size": len(body),
        }
    except OssClientError:
        raise
    except Exception as exc:
        op = (f"GetObject bucket={bucket_name} key={key}"
              + (f" x-oss-process={process}" if process else ""))
        raise _normalize_oss_error(exc, op)


def list_buckets(prefix: str = "", timeout: int = _DEFAULT_TIMEOUT,
                 endpoint: str = "oss-cn-hangzhou.aliyuncs.com",
                 max_buckets: int = 200) -> list:
    """Call OSS ListBuckets (read-only) to locate buckets of this account.

    Fallback path when GetBucketInfo cannot resolve the region: the returned
    `location` of each bucket reveals the region it was created in.
    Raises OssClientError.
    """
    try:
        auth = oss2.ProviderAuth(EnvCredentialsProvider())
        session = oss2.Session()
        session.session.headers["User-Agent"] = user_agent()
        service = _RetryingHandle(
            oss2.Service(auth, endpoint, session=session,
                         connect_timeout=timeout),
            "", endpoint)
        buckets = []
        marker = ""
        while len(buckets) < max_buckets:
            result = service.list_buckets(prefix=prefix, marker=marker,
                                          max_keys=100)
            for b in result.buckets:
                buckets.append({"name": b.name, "location": b.location,
                                "creation_date": b.creation_date})
            if not result.is_truncated:
                break
            marker = result.next_marker
        return buckets
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(exc, f"ListBuckets prefix={prefix or '*'}")


# ---------------------------------------------------------------------------
# Caller identity via aliyun CLI (argument-list subprocess, never shell=True)
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def get_caller_identity(timeout: int = _CLI_TIMEOUT) -> dict:
    """Run `aliyun sts get-caller-identity` and return the parsed response.

    Credentials come exclusively from the aliyun CLI default credential
    chain; the UA template and the per-run session-id are attached via
    --user-agent. Raises CliError on any failure.
    """
    if shutil.which("aliyun") is None:
        raise CliError(
            "aliyun CLI not found on PATH; install/configure it "
            "(`aliyun configure`) -- never pass AK/SK manually",
            code="CliMissing",
        )
    cmd = ["aliyun", "sts", "get-caller-identity",
           "--endpoint", _STS_ENDPOINT,
           "--user-agent", user_agent()]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise CliError(f"aliyun sts get-caller-identity timed out after "
                       f"{timeout}s", code="Timeout")
    stderr = _ANSI_ESCAPE_RE.sub("", result.stderr or "").strip()
    if result.returncode != 0:
        raise CliError(
            f"aliyun sts get-caller-identity failed: {stderr[:300]}",
            stderr=stderr,
        )
    stdout = (result.stdout or "").strip()
    if not stdout:
        return {}
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as e:
        raise CliError(f"aliyun sts get-caller-identity returned non-JSON "
                       f"output: {e}")


def resolve_uid() -> str:
    """Derive the caller UID (AccountId) via STS; return '' on failure.

    Callers degrade gracefully (log [WARN]) instead of aborting: UID is only
    a traceability label for this read-only skill.
    """
    try:
        identity = get_caller_identity()
    except CliError as e:
        print(f"[WARN] identity pre-check failed: {e}", file=sys.stderr)
        return ""
    return str(identity.get("AccountId") or "").strip()


# ---------------------------------------------------------------------------
# Inline boundary assertions for skill_version(): normal / boundary / illegal.
# They run at import time, touch no network and no cloud API, and pin the
# UA-SKILL-VERSION contract -- the version comes from references/manifest.json,
# and a missing or malformed manifest STOPS the run instead of being guessed.
# ---------------------------------------------------------------------------

def _selfcheck_skill_version() -> None:
    global _MANIFEST_PATH, _SKILL_VERSION
    real_path, real_cached = _MANIFEST_PATH, _SKILL_VERSION
    try:
        _SKILL_VERSION = None                     # normal: this repo's manifest
        assert _VERSION_RE.match(skill_version()), \
            "UA-SKILL-VERSION: manifest version must be a valid version string"
        assert _VERSION_RE.match("1.0.0-rc.1") and _VERSION_RE.match("1.2.3+b.5"), \
            "UA-SKILL-VERSION: pre-release/build suffixes must stay valid"
        assert not _VERSION_RE.match("1.0") and not _VERSION_RE.match(""), \
            "UA-SKILL-VERSION: malformed versions must be rejected"
        _MANIFEST_PATH = os.path.join(os.path.dirname(real_path),
                                      "no-such-manifest.json")
        _SKILL_VERSION = None                     # illegal: manifest missing
        try:
            skill_version()
            raise AssertionError(
                "UA-SKILL-VERSION: a missing manifest must raise, never guess")
        except SkillVersionError:
            pass
    finally:
        _MANIFEST_PATH, _SKILL_VERSION = real_path, real_cached


_selfcheck_skill_version()
