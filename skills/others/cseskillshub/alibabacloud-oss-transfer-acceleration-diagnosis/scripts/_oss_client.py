#!/usr/bin/env python3
"""
_oss_client.py -- Shared OSS control-plane client for transfer acceleration
===========================================================================
SECURITY: This skill is strictly READ-ONLY. Credentials are resolved ONLY by
the standard Alibaba Cloud default credential chain: the environment variables
`ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` /
`ALIBABA_CLOUD_SECURITY_TOKEN` first, then the current profile of the aliyun
CLI config file (`~/.aliyun/config.json`) -- all inside this module, in memory.
This module never hardcodes credentials, never prompts for them, and never
prints their values, so a caller never has to (and must not) bridge or export
credentials by hand. Only the metadata queries GetBucketInfo,
GetBucketTransferAcceleration and ListBuckets are ever issued against OSS; no
mutating call exists anywhere in this skill (enabling transfer acceleration is
a console action executed by the user, never by this skill).

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the diagnosis scripts so that every OSS control-plane call goes through ONE
place carrying timeout, degradation and observability guarantees.

Channels (measured, finalized):
  * OSS control-plane metadata -> Python oss2 SDK (>= 2.19.0, < 3). The
    aliyun CLI carries no OSS control-plane metadata and ossutil is not
    assumed to be installed, so the SDK is the only viable channel.
    GetBucketTransferAcceleration support was measured on oss2 2.19.1:
    bucket.get_bucket_transfer_acceleration() returns a result object whose
    `enabled` attribute is True when the feature is on, and OSS answers
    HTTP 404 code NoSuchTransferAccelerationConfiguration when the bucket
    never enabled transfer acceleration (normalized below to category
    "not_configured").
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

_SKILL_NAME = "alibabacloud-oss-transfer-acceleration-diagnosis"
# UA-SKILL-VERSION: the skill version is declared ONLY in references/manifest.json
# and is read from there at runtime -- it is never hardcoded, guessed or reused
# in this module.
_MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "manifest.json")
_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
_SKILL_VERSION: Optional[str] = None
_STS_ENDPOINT = "sts.aliyuncs.com"
_DEFAULT_TIMEOUT = 30   # seconds, applied to every single OSS SDK call
_CLI_TIMEOUT = 60       # seconds, applied to every single aliyun CLI call
_SESSION_ID: Optional[str] = None


class OssClientError(RuntimeError):
    """Structured, normalized error for every OSS control-plane call.

    category values (stable contract consumed by the diagnosis entry):
      credentials      -- env credential chain not configured
      not_found        -- NoSuchBucket (bucket name does not exist)
      not_configured   -- transfer acceleration never enabled on the bucket
                          (404 NoSuchTransferAccelerationConfiguration;
                          measured on oss2 2.19.1)
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


class SkillVersionError(RuntimeError):
    """references/manifest.json is missing, unreadable or has no valid version.

    UA-SKILL-VERSION forbids inventing, guessing or reusing a version, so the
    run stops here instead of falling back to a placeholder value.
    """


def skill_version() -> str:
    """Return the UA skill-version, read from references/manifest.json.

    Resolved lazily on the first User-Agent build -- i.e. before the first cloud
    call of the run -- and cached for the rest of the run, the same way as the
    session-id. A missing/unreadable manifest or a malformed version raises
    SkillVersionError instead of substituting a guessed value.
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
# Credentials provider (default credential chain: env vars, then the aliyun
# CLI profile -- SA-2.12 compliant, values never printed or logged)
# ---------------------------------------------------------------------------

# Location of the aliyun CLI profile file; part of the platform's default
# credential chain, read silently below.
_CLI_CONFIG_PATH = os.path.expanduser("~/.aliyun/config.json")


class DefaultChainCredentialsProvider:
    """CredentialsProvider resolving the Alibaba Cloud default chain.

    The oss2 built-in EnvironmentVariableCredentialsProvider reads OSS_*
    prefixed variables, which do not match the platform's default credential
    chain, so this provider resolves, in order (first usable hit wins):
      1. ALIBABA_CLOUD_ACCESS_KEY_ID
         ALIBABA_CLOUD_ACCESS_KEY_SECRET
         ALIBABA_CLOUD_SECURITY_TOKEN   (optional, present for STS sessions)
      2. the `current` profile of the aliyun CLI config file
         (`~/.aliyun/config.json`) when its mode is `AK` or `StsToken`
    Profile-mode values are read into memory only: they are never printed,
    logged, echoed into a report, or exported to the environment, so no caller
    has a reason to extract them by hand.
    """

    @staticmethod
    def _from_cli_profile() -> tuple:
        """Return (access_key_id, access_key_secret, security_token) from the
        current aliyun CLI profile, or empty strings when the file, the
        profile, or a usable AK/StsToken mode is absent."""
        try:
            with open(_CLI_CONFIG_PATH, "r", encoding="utf-8") as fh:
                cfg = json.load(fh)
        except Exception:      # missing file / unreadable / malformed: degrade
            return "", "", ""
        current = str(cfg.get("current") or "").strip()
        for profile in cfg.get("profiles") or []:
            if str(profile.get("name") or "").strip() != current:
                continue
            mode = str(profile.get("mode") or "AK").strip()
            if mode not in ("AK", "StsToken"):
                return "", "", ""
            token = (str(profile.get("sts_token") or "").strip()
                     if mode == "StsToken" else "")
            return (str(profile.get("access_key_id") or "").strip(),
                    str(profile.get("access_key_secret") or "").strip(),
                    token)
        return "", "", ""

    def get_credentials(self) -> Credentials:
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
        access_key_secret = os.environ.get(
            "ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
        security_token = os.environ.get(
            "ALIBABA_CLOUD_SECURITY_TOKEN", "").strip()
        if not access_key_id or not access_key_secret:
            access_key_id, access_key_secret, token = self._from_cli_profile()
            security_token = security_token or token
        if not access_key_id or not access_key_secret:
            raise OssClientError(
                "no credentials found in the default credential chain "
                "(neither the ALIBABA_CLOUD_ACCESS_KEY_ID / "
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET environment variables nor a "
                "usable AK/StsToken profile in the aliyun CLI config); run "
                "`aliyun configure` to set the chain up -- this module already "
                "reads it, so never extract, print, or pass AK/SK by hand",
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
    name (uppercase / underscore / dot / special character / wrong length);
    it is converted here to the unified OssClientError(category="invalid")
    so the entry script degrades with [WARN] + STATUS: DEGRADED instead
    of a bare Traceback (measured: passing an endpoint-shaped string such
    as 'oss-cn-shenzhen.aliyuncs.com' as the bucket raises ClientError).
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
                 "problem and no API call was issued. If the value looks "
                 "like an endpoint host (contains dots), the bucket and "
                 "endpoint arguments were likely swapped.",
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
    if isinstance(exc, oss2.exceptions.OssError):
        code = getattr(exc, "code", "") or ""
        status = getattr(exc, "status", 0) or 0
        # Measured (oss2 2.19.1): a bucket that never enabled transfer
        # acceleration answers GetBucketTransferAcceleration with HTTP 404
        # code NoSuchTransferAccelerationConfiguration. This is a NORMAL
        # diagnostic finding ("feature not enabled"), not a failure, so it
        # gets its own category the entry script interprets as
        # transfer_acceleration.status = disabled.
        if code == "NoSuchTransferAccelerationConfiguration":
            return OssClientError(
                f"{operation}: transfer acceleration is not enabled on "
                f"this bucket ({msg})",
                category="not_configured", code=code, status=404,
                hint="Transfer acceleration was never enabled on this "
                     "bucket; enabling is a console action the user "
                     "performs (OSS console -> bucket -> Transfer "
                     "Acceleration -> Enable). This skill never enables "
                     "it (read-only).",
            )
    if isinstance(exc, oss2.exceptions.AccessDenied):
        category = "permission"
        hint = ("Check RAM permission oss:GetBucketInfo / "
                "oss:GetBucketTransferAcceleration for this caller, or "
                "confirm the bucket belongs to this account.")
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
        # connect timeout against an unreachable endpoint, reset) into
        # OssError/RequestError carrying status -2 and an empty code.
        # Classify them as network so the diagnosis entry can route to the
        # "no such host / unreachable endpoint" guidance.
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


def get_transfer_acceleration(bucket_name: str, endpoint: str,
                              timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS GetBucketTransferAcceleration (read-only).

    Returns {"enabled": True|False}:
      enabled=True   -- the feature is switched on for this bucket.
      enabled=False  -- OSS answered 404 NoSuchTransferAccelerationConfiguration
                        (measured 2026-08-27 on oss2 2.19.1 against bucket
                        test-agentceping: the feature is not enabled and OSS
                        reports a dedicated 404 code, NOT enabled=false).
    Any other failure raises OssClientError with a normalized category.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_transfer_acceleration()
    except OssClientError:
        raise
    except Exception as exc:  # oss2/requests/socket errors -> normalized
        err = _normalize_oss_error(
            exc, f"GetBucketTransferAcceleration bucket={bucket_name} "
                 f"endpoint={endpoint}")
        if err.category == "not_configured":
            # Normal diagnostic finding, not a failure.
            return {"enabled": False}
        raise err
    return {"enabled": bool(getattr(result, "enabled", False))}


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
