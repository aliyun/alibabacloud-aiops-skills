#!/usr/bin/env python3
"""
_oss_client.py -- Shared OSS control-plane client for CRR config check
======================================================================
SECURITY: This skill is strictly READ-ONLY. Credentials are resolved ONLY
from the standard Alibaba Cloud environment variables of the default
credential chain (ALIBABA_CLOUD_ACCESS_KEY_ID /
ALIBABA_CLOUD_ACCESS_KEY_SECRET / ALIBABA_CLOUD_SECURITY_TOKEN). This module
never hardcodes credentials, never prompts for them, and never prints their
values. Only the read-only metadata queries GetBucketReplication,
GetBucketInfo and ListBuckets are ever issued against OSS; no mutating call
exists anywhere in this skill.

Internal module (prefixed with `_`). Do NOT run directly -- it is imported by
the check scripts so that every OSS control-plane call goes through ONE place
carrying timeout, degradation and observability guarantees.

Channels (measured, finalized):
  * OSS control-plane metadata -> Python oss2 SDK (>= 2.19.0, < 3). The
    aliyun CLI carries no OSS control-plane replication metadata and ossutil
    is not assumed to be installed, so the SDK is the only viable channel.
  * Caller identity / UID derivation -> `aliyun sts get-caller-identity`
    (plugin mode, CLI default credential chain), argument-list subprocess.

Measured replication-channel facts (oss2 2.19.1 against the evaluation
bucket test-agentceping):
  * bucket.get_bucket_replication() returns GetBucketReplicationResult whose
    .rule_list holds ReplicationRule objects (currently at most one rule).
  * When the bucket has NO replication rule, the SDK raises
    oss2.exceptions.ServerError with status=404 and
    code="NoSuchReplicationConfiguration" -- this is NORMAL (not an error)
    and is surfaced here as OssClientError(category="no_replication") so the
    entry script reports "replication not configured" instead of a failure.

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

_SKILL_NAME = "alibabacloud-oss-crr-config-check"
_SKILL_VERSION: Optional[str] = None  # resolved at runtime; see resolve_skill_version()
_STS_ENDPOINT = "sts.aliyuncs.com"
_DEFAULT_TIMEOUT = 30   # seconds, applied to every single OSS SDK call
_CLI_TIMEOUT = 60       # seconds, applied to every single aliyun CLI call
_SESSION_ID: Optional[str] = None
# Measured: GetBucketReplication on a bucket without any replication rule.
_NO_REPLICATION_CODE = "NoSuchReplicationConfiguration"


class OssClientError(RuntimeError):
    """Structured, normalized error for every OSS control-plane call.

    category values (stable contract consumed by the check entry):
      credentials      -- env credential chain not configured
      not_found        -- NoSuchBucket (bucket name does not exist)
      no_replication   -- NoSuchReplicationConfiguration (404, NORMAL: the
                          bucket simply has no replication rule configured)
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

    # Measured: GetBucketReplication on a bucket with NO replication rule
    # raises ServerError(status=404, code=NoSuchReplicationConfiguration).
    # This is the expected "replication not configured" state, NOT a failure
    # and NOT a missing bucket -- classify it with its own dedicated category.
    exc_code = getattr(exc, "code", "") or ""
    if exc_code == _NO_REPLICATION_CODE:
        return OssClientError(
            f"{operation}: the bucket has no replication configuration "
            f"({msg})",
            category="no_replication", code=_NO_REPLICATION_CODE, status=404,
            hint="Replication is simply not configured on this bucket; this "
                 "is a valid finding, not an error. Configure a cross-region "
                 "replication rule if data replication is intended.",
        )
    if isinstance(exc, oss2.exceptions.NoSuchBucket):
        return OssClientError(
            f"{operation}: the bucket does not exist ({msg})",
            category="not_found", code="NoSuchBucket", status=404,
            hint="Verify the bucket name spelling; bucket names are global "
                 "and case-sensitive lowercase.",
        )
    if isinstance(exc, oss2.exceptions.AccessDenied):
        category = "permission"
        hint = ("Check RAM permission for this caller (see "
                "references/ram-policies.md), or confirm the bucket belongs "
                "to this account.")
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
    # Network-layer failures: DNS ("no such host"), connect/read timeout,
    # connection reset, TLS errors.
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
      name, location (e.g. "oss-cn-hangzhou"), intranet_endpoint,
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


def _rule_to_dict(rule) -> dict:
    """Normalize one oss2.models.ReplicationRule into a plain dict.

    Field semantics (measured against oss2 2.19.1 ReplicationRule):
      target_transfer_type  -- "oss_acc" when transfer acceleration is used,
                               otherwise a plain/empty data link label.
      action_list           -- "ALL" syncs PUT+ABORT+DELETE (delete linkage
                               ON); "PUT" syncs writes only (delete linkage
                               OFF); individual "DELETE"/"ABORT" may appear.
      is_enable_historical_object_replication -- bool, the historical-data
                               switch (False => only new objects replicate).
      prefix_list           -- object prefixes in scope (empty => whole
                               bucket).
      sync_role_name        -- the RAM role OSS assumes to perform the copy
                               (e.g. AliyunOSSRole); empty => no explicit
                               authorization role on the rule.
      status                -- starting | doing | closing (server-assigned).
    """
    return {
        "rule_id": getattr(rule, "rule_id", "") or "",
        "target_bucket_name": getattr(rule, "target_bucket_name", "") or "",
        "target_bucket_location": getattr(rule, "target_bucket_location", "") or "",
        "target_transfer_type": getattr(rule, "target_transfer_type", "") or "",
        "prefix_list": list(getattr(rule, "prefix_list", None) or []),
        "action_list": list(getattr(rule, "action_list", None) or []),
        "is_enable_historical_object_replication":
            getattr(rule, "is_enable_historical_object_replication", None),
        "sync_role_name": getattr(rule, "sync_role_name", "") or "",
        "replica_kms_keyid": getattr(rule, "replica_kms_keyid", "") or "",
        "sse_kms_encrypted_objects_status":
            getattr(rule, "sse_kms_encrypted_objects_status", "") or "",
        "status": getattr(rule, "status", "") or "",
    }


def get_bucket_replication(bucket_name: str, endpoint: str,
                           timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS GetBucketReplication (read-only) and return normalized rules.

    Returns {"configured": True, "rules": [rule dict, ...]} when one or more
    replication rules exist. When the bucket has NO replication rule the SDK
    raises 404 NoSuchReplicationConfiguration, which is converted to
    OssClientError(category="no_replication") -- the caller treats that as the
    legitimate "replication not configured" finding rather than a failure.
    Raises OssClientError with a normalized category on any other failure.
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_replication()
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(
            exc, f"GetBucketReplication bucket={bucket_name} "
                 f"endpoint={endpoint}")
    rules = [_rule_to_dict(r) for r in (getattr(result, "rule_list", None) or [])]
    return {"configured": bool(rules), "rules": rules}


def get_bucket_replication_progress(bucket_name: str, endpoint: str,
                                    rule_id: str,
                                    timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Call OSS GetBucketReplicationProgress (read-only) for one rule.

    This is the authoritative answer to "replication progress stuck at 0%" /
    "status is doing but no data landed" (tickets 0007KS78FF / 000EAR7WN7):
    it separates the HISTORICAL backlog percentage from the NEW-object
    watermark instead of guessing from the rule status alone.

    Returns normalized dict keys (measured against oss2 2.19.1
    models.BucketReplicationProgress):
      rule_id, status,
      historical_object_progress -- float percentage of the pre-existing
                                    backlog already copied (may be None when
                                    historical replication is disabled),
      new_object_progress        -- RFC1123 watermark; objects written to the
                                    source BEFORE this time are already
                                    replicated (empty until the historical
                                    phase completes),
      is_enable_historical_object_replication -- bool switch echoed back.
    Raises OssClientError with a normalized category on any failure (e.g. the
    rule_id does not match a configured rule); the caller degrades with
    [WARN] and never treats a progress-query failure as "replication broken".
    """
    rid = (rule_id or "").strip()
    if not rid:
        raise OssClientError(
            "GetBucketReplicationProgress requires a non-empty rule_id "
            "(read it from GetBucketReplication first)",
            category="invalid", code="MissingRuleId",
        )
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    try:
        result = bucket.get_bucket_replication_progress(rid)
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(
            exc, f"GetBucketReplicationProgress bucket={bucket_name} "
                 f"rule_id={rid} endpoint={endpoint}")
    prog = getattr(result, "progress", None)
    return {
        "rule_id": getattr(prog, "rule_id", "") or rid,
        "status": getattr(prog, "status", "") or "",
        "historical_object_progress":
            getattr(prog, "historical_object_progress", None),
        "new_object_progress": getattr(prog, "new_object_progress", "") or "",
        "is_enable_historical_object_replication":
            getattr(prog, "is_enable_historical_object_replication", None),
    }


def count_bucket_objects(bucket_name: str, endpoint: str, prefix: str = "",
                         max_scan: int = 5000, sample_size: int = 5,
                         timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Read-only ListObjectsV2 scan for post-replication data verification.

    Counts objects (and total size) under `prefix` on ONE bucket so the caller
    can compare the source and the target side. This never writes anything:
    ListObjectsV2 maps to the read-only oss:ListObjects action.

    The scan is BOUNDED: it stops after `max_scan` objects and reports
    `truncated=True` so a huge bucket cannot turn a verification into an
    unbounded listing. When truncated, the caller must fall back to the OSS
    Inventory (清单) rather than trusting the partial count.

    Returns dict keys:
      bucket, prefix, count, total_size, scanned, truncated,
      sample -- up to `sample_size` {key, etag, size} entries for ETag/Size
                spot-checking (never object content).
    Raises OssClientError with a normalized category on any failure (e.g. the
    cross-account target is not listable with this credential -- the common
    case, which the caller surfaces as a verification LIMIT, not an error).
    """
    bucket = _build_bucket(bucket_name, endpoint, timeout)
    count = 0
    total_size = 0
    scanned = 0
    sample = []
    truncated = False
    token = ""
    try:
        while True:
            page = min(1000, max(1, max_scan - scanned))
            result = bucket.list_objects_v2(
                prefix=prefix or "", continuation_token=token,
                max_keys=page)
            for obj in (getattr(result, "object_list", None) or []):
                count += 1
                scanned += 1
                total_size += int(getattr(obj, "size", 0) or 0)
                if len(sample) < sample_size:
                    sample.append({
                        "key": getattr(obj, "key", "") or "",
                        "etag": (getattr(obj, "etag", "") or "").strip('"'),
                        "size": int(getattr(obj, "size", 0) or 0),
                    })
                if scanned >= max_scan:
                    truncated = True
                    break
            if truncated or not getattr(result, "is_truncated", False):
                break
            token = getattr(result, "next_continuation_token", "") or ""
            if not token:
                break
    except OssClientError:
        raise
    except Exception as exc:
        raise _normalize_oss_error(
            exc, f"ListObjectsV2 bucket={bucket_name} "
                 f"prefix={prefix or '*'} endpoint={endpoint}")
    return {
        "bucket": bucket_name,
        "prefix": prefix or "",
        "count": count,
        "total_size": total_size,
        "scanned": scanned,
        "truncated": truncated,
        "sample": sample,
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
