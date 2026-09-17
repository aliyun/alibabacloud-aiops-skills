#!/usr/bin/env python3
"""
_oss_client.py -- Shared OSS control-plane client for multipart upload diagnosis
=================================================================================
SECURITY: This skill is strictly READ-ONLY. Credential resolution is delegated
end-to-end to the Alibaba Cloud default credential chain library
(alibabacloud-credentials), which owns where credentials come from -- standard
environment credentials, a CLI/credentials profile or an instance RAM role.
This module never reads, prints or passes an AccessKey pair itself, and never
prompts for one. Only the three metadata queries GetBucketInfo, ListBuckets and
ListMultipartUploads are ever issued against OSS; NO mutating call (no
AbortMultipartUpload, no PutObject, no Delete*) exists anywhere in this
skill -- fragment cleanup is documented guidance for the user only.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the diagnosis scripts so that every OSS control-plane call goes through ONE
place carrying timeout, degradation and observability guarantees.

Channels (measured, finalized):
  * OSS control-plane metadata -> Python oss2 SDK (>= 2.19.0, < 3). The
    aliyun CLI carries no OSS control-plane metadata and ossutil is not
    assumed to be installed, so the SDK is the only viable channel.
    ListMultipartUploads maps to oss2.Bucket.list_multipart_uploads()
    (measured on oss2 2.19.1: signature prefix/delimiter/key_marker/
    upload_id_marker/max_uploads; result exposes upload_list of
    MultipartUploadInfo{key, upload_id, initiation_date}, is_truncated,
    next_key_marker, next_upload_id_marker).
  * Caller identity / UID derivation -> `aliyun sts get-caller-identity`
    (plugin mode, CLI default credential chain), argument-list subprocess.

Observability:
  * User-Agent template: AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
  * session-id: 32-character hex string (uuid4().hex), generated once per
    run, attached to every OSS SDK request (User-Agent header) and every
    aliyun CLI call (--user-agent) of the same run.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import oss2
from oss2.credentials import Credentials

_SKILL_NAME = "alibabacloud-oss-multipart-upload-diagnosis"
_SKILL_VERSION: Optional[str] = None  # resolved at runtime; see resolve_skill_version()
_STS_ENDPOINT = "sts.aliyuncs.com"
_DEFAULT_TIMEOUT = 30   # seconds, applied to every single OSS SDK call
_CLI_TIMEOUT = 60       # seconds, applied to every single aliyun CLI call
_SESSION_ID: Optional[str] = None

# Pagination guard for ListMultipartUploads: never walk the whole key space;
# the report only needs enough evidence to attribute stuck/abandoned uploads.
_MAX_UPLOADS_SCAN = 1000   # hard cap on total uploads enumerated per run
_PAGE_SIZE = 1000          # server-side page size (API max is 1000)


class OssClientError(RuntimeError):
    """Structured, normalized error for every OSS control-plane call.

    category values (stable contract consumed by the diagnosis entry):
      credentials      -- env credential chain not configured
      not_found        -- NoSuchBucket (bucket name does not exist)
      permission       -- 403 AccessDenied / bucket not owned by caller
      endpoint         -- wrong-region / must-use-specified-endpoint errors
      network          -- DNS failure ("no such host"), timeout, reset
      server           -- 5xx / service-side failures
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


def _manifest_path() -> str:
    """Absolute path to references/manifest.json (the skill version source)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "references", "manifest.json")


def resolve_skill_version() -> str:
    """Resolve the skill version carried in every User-Agent (rule UA-SKILL-VERSION).

    Resolution order: the SKILL_VERSION environment variable (non-empty), then
    the top-level 'version' string of references/manifest.json. The version is
    never invented or guessed. This doubles as the FAILURE GATE required before
    the first cloud call: user_agent() sits on the path of every Alibaba Cloud
    call (SDK header and CLI --user-agent), so an unresolvable version raises
    here and the run stops BEFORE any network call -- an unversioned call must
    never reach the cloud.
    """
    global _SKILL_VERSION
    if _SKILL_VERSION is not None:
        return _SKILL_VERSION
    env_version = (os.environ.get("SKILL_VERSION") or "").strip()
    if env_version:
        _SKILL_VERSION = env_version
        return _SKILL_VERSION
    path = _manifest_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise RuntimeError(
            "skill version unresolved: references/manifest.json is missing or "
            f"not valid JSON ({e}). Every Alibaba Cloud call must carry a "
            "versioned User-Agent, so this run stops before any cloud call. "
            "Restore references/manifest.json or export SKILL_VERSION."
        )
    version = data.get("version") if isinstance(data, dict) else None
    if not (isinstance(version, str) and version.strip()):
        raise RuntimeError(
            "skill version unresolved: references/manifest.json has no "
            "non-empty top-level 'version' string. Restore it or export "
            "SKILL_VERSION before any cloud call."
        )
    _SKILL_VERSION = version.strip()
    return _SKILL_VERSION


def user_agent() -> str:
    """User-Agent attached to every API call of this run."""
    return f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{session_id()} skill-version/{resolve_skill_version()}"


# ---------------------------------------------------------------------------
# Credentials provider (delegates to the Alibaba Cloud default credential
# chain library -- SA-2.12 compliant)
# ---------------------------------------------------------------------------

_cred_chain_client: Optional[Any] = None


def _credential_chain_client():
    """Return the shared default credential chain client (built once per run).

    Credential resolution is fully delegated to the Alibaba Cloud credentials
    client: that library owns the chain and its order (environment credentials,
    CLI/credentials profile, instance RAM role), so it owns every AccessKey
    lookup. This module never reads, prints or passes an AccessKey pair itself
    and never asks the user for one (SA-2.12).
    """
    global _cred_chain_client
    if _cred_chain_client is None:
        try:
            from alibabacloud_credentials.client import Client as CredClient
        except ImportError as exc:
            raise OssClientError(
                "the default credential chain is unavailable because its "
                "client library is not installed; run "
                "`pip install -r scripts/requirements.txt` -- never pass "
                "AK/SK manually",
                category="credentials", code="NoCredentialChain",
            ) from exc
        # The chain library logs every probe of every provider on the shared
        # "credentials" logger; the diagnosis output owns stderr, so keep it
        # silent and surface resolution failures through OssClientError only.
        logging.getLogger("credentials").setLevel(logging.CRITICAL)
        _cred_chain_client = CredClient()
    return _cred_chain_client


class DefaultChainCredentialsProvider:
    """oss2 CredentialsProvider resolving through the default chain."""

    def get_credentials(self) -> Credentials:
        try:
            credential = _credential_chain_client().get_credential()
        except OssClientError:
            raise
        except Exception as exc:
            raise OssClientError(
                "the default credential chain resolved no usable credential; "
                "configure it first (run `aliyun configure`, or attach a RAM "
                "role to this host) -- never pass AK/SK manually",
                category="credentials", code="NoCredentials",
            ) from exc
        return Credentials(
            access_key_id=credential.access_key_id,
            access_key_secret=credential.access_key_secret,
            security_token=credential.security_token or "",
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
    auth = oss2.ProviderAuth(DefaultChainCredentialsProvider())
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


_ENDPOINT_HINT_RE = re.compile(r"(oss-[a-z0-9-]+\.aliyuncs\.com)")


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

    if isinstance(exc, oss2.exceptions.NoSuchBucket):
        return OssClientError(
            f"{operation}: the bucket does not exist ({msg})",
            category="not_found", code="NoSuchBucket", status=404,
            hint="Verify the bucket name spelling; bucket names are global "
                 "and case-sensitive lowercase.",
        )
    if isinstance(exc, oss2.exceptions.AccessDenied):
        category = "permission"
        hint = ("Check RAM permission for this caller (oss:GetBucketInfo / "
                "oss:ListMultipartUploads, see references/ram-policies.md), "
                "or confirm the bucket belongs to this account.")
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
        elif "specified endpoint" in low or _ENDPOINT_HINT_RE.search(msg):
            category = "endpoint"
            hint = ("The request hit the wrong region's endpoint; use the "
                    "endpoint of the region where the bucket was created.")
        return OssClientError(
            f"{operation}: access denied ({msg})",
            category=category, code="AccessDenied", status=403,
            hint=hint + (_action_hint_suffix(operation)
                         if category == "permission" else ""),
        )
    if isinstance(exc, oss2.exceptions.OssError):
        status = getattr(exc, "status", 0) or 0
        code = getattr(exc, "code", "") or ""
        # Measured: oss2 wraps transport-layer failures (DNS "no such host",
        # connect timeout, reset) into OssError/RequestError carrying status
        # -2 and an empty code. Classify them as network.
        if status <= 0 or "requesterror" in low:
            return OssClientError(
                f"{operation}: network/client failure: {msg}",
                category="network", code=code or "NetworkError",
                status=status,
                hint="Check DNS resolution of the endpoint host, local "
                     "network, and whether an internal endpoint is used "
                     "outside the Alibaba Cloud network of its region.",
            )
        hint = ""
        if status >= 500:
            category = "server"
        elif code in ("InvalidAccessKeyId", "SecurityTokenExpired",
                      "InvalidSecurityToken", "SignatureDoesNotMatch"):
            # Measured: bad/expired STS credentials surface as HTTP 403 with
            # these codes -- route to the credential-chain guidance.
            category = "credentials"
        elif code in ("InvalidBucketName", "InvalidArgument", "MalformedXML"):
            category = "invalid"
        else:
            category = "unknown"
        return OssClientError(
            f"{operation}: OSS error {code} (HTTP {status}): {msg}",
            category=category, code=code, status=status, hint=hint,
        )
    # Network-layer failures: DNS ("no such host" / "nodename nor servname"),
    # connect/read timeout, connection reset, TLS errors.
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
    """Call OSS GetBucketInfo (read-only) and return normalized fields.

    Returns dict keys (measured against oss2 2.19.x):
      name, location (e.g. "oss-cn-shanghai"), intranet_endpoint,
      extranet_endpoint, storage_class, acl, creation_date, owner_id.
    Raises OssClientError with a normalized category on any failure.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_info()
    except OssClientError:
        raise
    except Exception as exc:  # oss2/requests/socket errors -> normalized
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


def list_buckets(prefix: str = "", timeout: int = _DEFAULT_TIMEOUT,
                 endpoint: str = "oss-cn-hangzhou.aliyuncs.com",
                 max_buckets: int = 200) -> list:
    """Call OSS ListBuckets (read-only) to locate buckets of this account.

    Used as the fallback path when GetBucketInfo cannot resolve the region
    (wrong endpoint, permission gap): the returned `location` of each bucket
    reveals the region the bucket was created in. Raises OssClientError.
    """
    try:
        auth = oss2.ProviderAuth(DefaultChainCredentialsProvider())
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


def list_multipart_uploads(bucket_name: str, endpoint: str,
                           prefix: str = "",
                           timeout: int = _DEFAULT_TIMEOUT,
                           max_uploads: int = _MAX_UPLOADS_SCAN) -> dict:
    """Call OSS ListMultipartUploads (read-only) and normalize the result.

    Enumerates unfinished multipart upload events (fragments) of the bucket.
    Pagination is capped at `max_uploads` entries (hard guard against huge
    key spaces). Returns:
      {"uploads": [{"key", "upload_id", "initiated", "age_hours"}],
       "count": int, "truncated": bool, "scanned_limit": int}
    `initiated` is the ISO-8601 UTC string of InitiateMultipartUpload time;
    `age_hours` is rounded to one decimal against the current time.
    Raises OssClientError with a normalized category on any failure
    (403 permission gap, NoSuchBucket, wrong endpoint, network...).
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    uploads = []
    truncated = False
    key_marker = ""
    upload_id_marker = ""
    now_ts = datetime.now(timezone.utc).timestamp()
    try:
        while len(uploads) < max_uploads:
            page = min(_PAGE_SIZE, max_uploads - len(uploads))
            result = bucket.list_multipart_uploads(
                prefix=prefix, key_marker=key_marker,
                upload_id_marker=upload_id_marker, max_uploads=page)
            for info in result.upload_list:
                initiated_ts = getattr(info, "initiation_date", None) or 0
                iso = ""
                age_hours = None
                if initiated_ts:
                    try:
                        iso = datetime.fromtimestamp(
                            int(initiated_ts), tz=timezone.utc
                        ).strftime("%Y-%m-%dT%H:%M:%SZ")
                        age_hours = round(
                            max(0.0, (now_ts - int(initiated_ts)) / 3600.0), 1)
                    except (ValueError, OSError):
                        pass
                uploads.append({
                    "key": getattr(info, "key", "") or "",
                    "upload_id": getattr(info, "upload_id", "") or "",
                    "initiated": iso,
                    "age_hours": age_hours,
                })
            truncated = bool(result.is_truncated)
            if not truncated or len(uploads) >= max_uploads:
                break
            key_marker = result.next_key_marker or ""
            upload_id_marker = result.next_upload_id_marker or ""
            if not key_marker:  # defensive: cannot advance pagination
                break
        return {
            "uploads": uploads[:max_uploads],
            "count": len(uploads),
            "truncated": truncated,
            "scanned_limit": max_uploads,
        }
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(
            exc, f"ListMultipartUploads bucket={bucket_name} "
                 f"endpoint={endpoint}")


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
