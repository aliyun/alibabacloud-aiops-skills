#!/usr/bin/env python3
"""
_oss_client.py -- Shared OSS control-plane client (oss2 SDK channel)
====================================================================
SECURITY: This skill is strictly READ-ONLY. Credentials are resolved ONLY from
the standard Alibaba Cloud environment variables of the default credential
chain (ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET /
ALIBABA_CLOUD_SECURITY_TOKEN). This module never hardcodes credentials, never
prompts for them, and never prints their values. Only Get/List-class metadata
queries are ever issued against OSS; no mutating call exists anywhere in this
skill.

Internal module (prefixed with `_`). Do NOT run directly.

Channels (aligned with the measured conclusion of this skill family)
-------------------------------------------------------------------
  * OSS control-plane metadata -> Python oss2 SDK (>= 2.19.0, < 3). The aliyun
    CLI carries no OSS control-plane metadata and ossutil is not assumed to be
    installed, so the SDK is the only viable channel. Because SDK calls do not
    go through the aliyun CLI, they cannot be intercepted by CLI Mock and
    cannot be attributed to a POP gateway; they are therefore covered by evals
    `cloud_interaction.skill_script` assertions and stay OUT of
    related_apis.yaml.
  * Caller identity / UID derivation, and SLS log reads -> aliyun CLI
    (see _cli.py), which is a POP-gateway channel and can be mocked.

Observability:
  * User-Agent template (rule UA-SKILL-VERSION):
    AlibabaCloud-Agent-Skills/{skill-name}/{session-id}/skill-version/{version}
  * session-id: 32-character hex string (uuid4().hex), generated once per run,
    attached to every OSS SDK request (User-Agent header) and every aliyun CLI
    call (--user-agent) of the same run.
  * skill-version: resolved from the SKILL_VERSION env var, else from the
    top-level 'version' of references/manifest.json; unresolvable version is a
    hard gate that stops the run before any cloud call.

SDK attribute names below were verified against oss2 2.19.1 by inspecting
oss2.xml_utils parse_* functions and oss2.models classes, not guessed:
  GetBucketInfoResult   -> RequestResult + BucketInfo (name, location, region,
                           extranet_endpoint, intranet_endpoint, storage_class,
                           creation_date, owner, acl, versioning_status,
                           data_redundancy_type, cross_region_replication,
                           transfer_acceleration, access_monitor, comment,
                           bucket_encryption_rule, resource_group_id)
  GetBucketAclResult    -> acl
  GetBucketPolicyResult -> policy
  GetBucketRefererResult-> allow_empty_referer, referers, black_referers,
                           allow_truncate_query_string
  GetObjectAclResult    -> acl
  GetBucketPublicAccessBlockResult -> block_public_access
  GetBucketWebsiteResult-> index_file, error_file   (NO mirror rules: the SDK
                           does not expose back-to-origin configuration)
  GetBucketLoggingResult-> target_bucket, target_prefix
  ListBucketsResult     -> buckets, is_truncated, next_marker, owner
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from typing import Any, Optional

try:
    import oss2
    from oss2.credentials import Credentials
    _OSS2_AVAILABLE = True
    _OSS2_IMPORT_ERROR = ""
except ImportError as exc:  # pragma: no cover - environment dependent
    oss2 = None
    Credentials = object
    _OSS2_AVAILABLE = False
    _OSS2_IMPORT_ERROR = str(exc)

_SKILL_NAME = "alibabacloud-oss-access-log-trace-diagnosis"
_STS_ENDPOINT = "sts.aliyuncs.com"
_DEFAULT_TIMEOUT = 30   # seconds, applied to every single OSS SDK call
_CLI_TIMEOUT = 60       # seconds, applied to every single aliyun CLI call
_DEFAULT_REGION = "cn-hangzhou"
_MAX_LIST_BUCKETS = 200

_SESSION_ID: Optional[str] = None

# Error codes that mean "this configuration is simply not present", which is a
# valid finding rather than a failure.
NOT_CONFIGURED_CODES = frozenset({
    "NoSuchBucketPolicy",
    "NoSuchWebsiteConfiguration",
    "NoSuchCORSConfiguration",
    "NoSuchLifecycleConfiguration",
    "NoSuchReplicationConfiguration",
    "NoSuchPublicAccessBlockConfiguration",
})

# Error codes meaning the caller's own credential is invalid or expired (a
# lapsed STS session, a rotated/deleted key). These are CREDENTIAL problems,
# not permission or resource findings: the correct response is to refresh the
# credential and degrade honestly -- never to inspect/print a credential file
# and never to state a configuration value that could not be read.
CREDENTIAL_ERROR_CODES = frozenset({
    "InvalidSecurityToken",
    "SecurityTokenExpired",
    "InvalidAccessKeyId",
    "InvalidToken",
    "SecurityTokenException",
})


class OssClientError(RuntimeError):
    """Structured, normalized error for every OSS control-plane call.

    category values (stable contract consumed by the diagnosis entry):
      credentials      -- env credential chain not configured
      dependency       -- the oss2 SDK is not installed
      not_found        -- NoSuchBucket / NoSuchKey
      permission       -- 403 AccessDenied, or bucket owned by another account
      endpoint         -- wrong-region / must-use-specified-endpoint errors
      network          -- DNS failure, timeout, connection reset
      server           -- 5xx / service-side failures
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
    """Raised when an aliyun CLI call fails."""

    def __init__(self, message: str, code: str = "", stderr: str = ""):
        super().__init__(message)
        self.code = code
        self.stderr = stderr


# ---------------------------------------------------------------------------
# Session-ID and User-Agent (observability)
# ---------------------------------------------------------------------------

def session_id() -> str:
    """Return the per-run 32-char hex session-id (generated lazily, cached)."""
    global _SESSION_ID
    if _SESSION_ID is None:
        _SESSION_ID = uuid.uuid4().hex
        print(f"[_oss_client] session-id: {_SESSION_ID}", file=sys.stderr)
    return _SESSION_ID


_SKILL_VERSION: Optional[str] = None


def _manifest_path() -> str:
    """Absolute path to references/manifest.json (the skill version source)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(here), "references", "manifest.json")


def resolve_skill_version() -> str:
    """Resolve the skill version carried in every User-Agent (rule UA-SKILL-VERSION).

    Resolution order: the SKILL_VERSION environment variable (non-empty), then
    the top-level 'version' string of references/manifest.json. This doubles as
    the FAILURE GATE required before the first cloud call: user_agent() sits on
    the path of every Alibaba Cloud call (SDK header and CLI --user-agent), so
    an unresolvable version raises here and the run stops BEFORE any network
    call -- an unversioned call must never reach the cloud.
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
    """User-Agent attached to every API call of this run.

    Template (rule UA-SKILL-VERSION):
      AlibabaCloud-Agent-Skills/{skill-name}/{session-id}/skill-version/{version}
    """
    return (f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{session_id()}"
            f"/skill-version/{resolve_skill_version()}")


def sdk_available() -> tuple[bool, str]:
    """Report whether the oss2 SDK is importable, and why not."""
    return _OSS2_AVAILABLE, _OSS2_IMPORT_ERROR


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

    def get_credentials(self):
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
                hint="Run `aliyun configure` or export the ALIBABA_CLOUD_* "
                     "variables of an assumed role session.",
            )
        return Credentials(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            security_token=security_token,
        )


# ---------------------------------------------------------------------------
# Endpoint helpers
# ---------------------------------------------------------------------------

def endpoint_for_region(region: str) -> str:
    """Build the public OSS endpoint of a region.

    Accepts either a bare region id (cn-hangzhou) or a location string as
    returned by GetBucketInfo (oss-cn-hangzhou).
    """
    region = (region or _DEFAULT_REGION).strip()
    if region.startswith("oss-"):
        region = region[4:]
    return f"oss-{region}.aliyuncs.com"


def region_from_location(location: str) -> str:
    """Normalize a GetBucketInfo location (oss-cn-hangzhou) to a region id."""
    location = (location or "").strip()
    return location[4:] if location.startswith("oss-") else location


# ---------------------------------------------------------------------------
# Bucket handle and error normalization
# ---------------------------------------------------------------------------

def _build_bucket(bucket_name: str, endpoint: str,
                  timeout: int = _DEFAULT_TIMEOUT):
    """Build an oss2.Bucket handle carrying the UA and a per-call timeout.

    oss2.Bucket raises oss2.exceptions.ClientError for an illegal bucket name
    (uppercase / underscore / dot / wrong length); it is converted here to the
    unified OssClientError(category="invalid") so the entry script degrades
    with [WARN] instead of a bare traceback. Measured: passing an
    endpoint-shaped string such as 'oss-cn-shenzhen.aliyuncs.com' as the bucket
    name raises ClientError.
    """
    if not _OSS2_AVAILABLE:
        raise OssClientError(
            f"the oss2 SDK is not installed ({_OSS2_IMPORT_ERROR}); install it "
            f"with: pip install 'oss2>=2.19.0,<3'",
            category="dependency", code="SdkMissing",
        )
    auth = oss2.ProviderAuth(EnvCredentialsProvider())
    session = oss2.Session()
    # Inject the observability User-Agent into every SDK request of this run.
    session.session.headers["User-Agent"] = user_agent()
    try:
        return oss2.Bucket(auth, endpoint, bucket_name, session=session,
                           connect_timeout=timeout)
    except oss2.exceptions.ClientError as exc:
        raise OssClientError(
            f"the bucket name '{bucket_name}' is invalid: bucket names must "
            "be 3-63 characters of lowercase letters, digits and hyphens, "
            "starting and ending with a lowercase letter or digit",
            category="invalid", code="InvalidBucketName",
            hint="Fix the bucket name spelling; this is a client-side input "
                 "problem and no API call was issued. If the value looks like "
                 "an endpoint host (contains dots), the bucket and endpoint "
                 "arguments were likely swapped.",
        ) from exc


_ENDPOINT_HINT_RE = re.compile(r"(oss-[a-z0-9-]+\.aliyuncs\.com)")


def _normalize_oss_error(exc: Exception, operation: str) -> OssClientError:
    """Map any oss2 / requests / socket failure to a structured OssClientError."""
    msg = str(exc).strip() or exc.__class__.__name__
    low = msg.lower()
    code = str(getattr(exc, "code", "") or "")

    if code in NOT_CONFIGURED_CODES:
        # "Not configured" is a finding, surfaced as its own category so the
        # caller can report it positively instead of as a failure.
        return OssClientError(
            f"{operation}: configuration not present ({code})",
            category="not_configured", code=code,
            status=int(getattr(exc, "status", 0) or 0),
            hint="This resource has no such configuration; that is a valid "
                 "finding, not an error.",
        )
    if code in CREDENTIAL_ERROR_CODES:
        return OssClientError(
            f"{operation}: the caller credential is invalid or expired ({code})",
            category="credentials", code=code,
            status=int(getattr(exc, "status", 0) or 0),
            hint="The STS session credential is invalid or expired, so no "
                 "configuration could be read. Refresh it (re-assume the role, "
                 "or re-export a valid session's ALIBABA_CLOUD_* variables, or "
                 "re-run `aliyun configure`). This is an environment credential "
                 "problem, NOT a permission or resource finding. NEVER read, "
                 "open, cat or print a credential or CLI config file "
                 "(~/.aliyun/config.json, ~/.alibabacloud/credentials, or an "
                 "env dump) to debug it, and never state a configuration value "
                 "that could not be read.",
        )
    if isinstance(exc, oss2.exceptions.NoSuchBucket):
        return OssClientError(
            f"{operation}: the bucket does not exist ({msg})",
            category="not_found", code="NoSuchBucket", status=404,
            hint="Verify the bucket name spelling; bucket names are global "
                 "and case-sensitive lowercase.",
        )
    if isinstance(exc, oss2.exceptions.NoSuchKey):
        return OssClientError(
            f"{operation}: the object does not exist ({msg})",
            category="not_found", code="NoSuchKey", status=404,
            hint="Verify the object key, including case and URL encoding.",
        )
    if isinstance(exc, oss2.exceptions.AccessDenied):
        category = "permission"
        hint = ("Check the RAM permission for this action, or confirm the "
                "bucket belongs to this account.")
        # Measured: hitting the wrong region's endpoint of an existing bucket
        # owned by the caller ALSO surfaces as AccessDenied "does not belong
        # to you", so keep the attribution broad and surface the
        # region-mismatch hypothesis through the hint.
        if "does not belong to you" in low:
            hint = ("Access denied (403): the caller lacks permission, the "
                    "bucket belongs to another account, or the endpoint's "
                    "region differs from the bucket's region (wrong-region "
                    "access also reports 'does not belong to you'). Verify "
                    "ownership, RAM permission and endpoint region.")
        elif "specified endpoint" in low or _ENDPOINT_HINT_RE.search(msg):
            category = "endpoint"
            hint = ("The request hit the wrong region's endpoint; use the "
                    "endpoint of the region where the bucket was created.")
        return OssClientError(
            f"{operation}: access denied ({msg})",
            category=category, code=code or "AccessDenied", status=403,
            hint=hint,
        )
    if isinstance(exc, oss2.exceptions.OssError):
        status = int(getattr(exc, "status", 0) or 0)
        # Measured: oss2 wraps transport-layer failures (DNS "no such host",
        # connect timeout, reset) into OssError/RequestError carrying a
        # non-positive status and an empty code.
        if status <= 0 or "requesterror" in low:
            return OssClientError(
                f"{operation}: network/client failure: {msg}",
                category="network", code=code or "NetworkError", status=status,
                hint="Check DNS resolution of the endpoint host, the local "
                     "network, and whether an internal endpoint is used "
                     "outside the Alibaba Cloud network of its region.",
            )
        if status >= 500:
            category = "server"
        elif code in ("InvalidBucketName", "InvalidArgument", "MalformedXML"):
            category = "invalid"
        else:
            category = "unknown"
        return OssClientError(
            f"{operation}: OSS error {code} (HTTP {status}): {msg}",
            category=category, code=code, status=status,
        )
    if isinstance(exc, oss2.exceptions.ClientError):
        return OssClientError(
            f"{operation}: client failure: {msg}",
            category="network", code=getattr(exc, "code", "") or "ClientError",
            hint="Check the bucket name spelling and local network.",
        )
    return OssClientError(f"{operation}: {msg}", category="unknown")


# ---------------------------------------------------------------------------
# Result extraction (attribute names verified against oss2 2.19.1)
# ---------------------------------------------------------------------------

def _acl_grant(result: Any) -> str:
    acl = getattr(result, "acl", None)
    if isinstance(acl, str):
        return acl
    return str(getattr(acl, "grant", "") or "")


def _extract_bucket_info(result: Any) -> dict:
    owner = getattr(result, "owner", None)
    acl = getattr(result, "acl", None)
    return {
        "name": getattr(result, "name", "") or "",
        "location": getattr(result, "location", "") or "",
        "region": region_from_location(getattr(result, "location", "") or ""),
        "extranet_endpoint": getattr(result, "extranet_endpoint", "") or "",
        "intranet_endpoint": getattr(result, "intranet_endpoint", "") or "",
        "storage_class": getattr(result, "storage_class", "") or "",
        "creation_date": getattr(result, "creation_date", "") or "",
        "owner_id": getattr(owner, "id", "") if owner is not None else "",
        "owner_display_name": getattr(owner, "display_name", "") if owner is not None else "",
        "acl": getattr(acl, "grant", "") if acl is not None else "",
        "versioning_status": getattr(result, "versioning_status", "") or "",
        "data_redundancy_type": getattr(result, "data_redundancy_type", "") or "",
        "cross_region_replication": getattr(result, "cross_region_replication", "") or "",
        "transfer_acceleration": getattr(result, "transfer_acceleration", "") or "",
        "access_monitor": getattr(result, "access_monitor", "") or "",
        "resource_group_id": getattr(result, "resource_group_id", "") or "",
    }


def _extract_referer(result: Any) -> dict:
    referers = list(getattr(result, "referers", None) or [])
    black = list(getattr(result, "black_referers", None) or [])
    return {
        "allow_empty_referer": bool(getattr(result, "allow_empty_referer", False)),
        "allow_truncate_query_string": getattr(
            result, "allow_truncate_query_string", None),
        "whitelist_count": len(referers),
        "whitelist": [str(r) for r in referers][:100],
        "blacklist_count": len(black),
        "blacklist": [str(r) for r in black][:100],
    }


def _extract_logging(result: Any) -> dict:
    target_bucket = str(getattr(result, "target_bucket", "") or "")
    return {
        "enabled": bool(target_bucket),
        "target_bucket": target_bucket,
        "target_prefix": str(getattr(result, "target_prefix", "") or ""),
    }


def _extract_website(result: Any) -> dict:
    # The SDK exposes only the static-website index/error documents. Mirror
    # back-to-origin rules are NOT exposed, so a mirror-related failure cannot
    # be resolved from here and must be handed to the customer as console
    # guidance.
    return {
        "index_file": str(getattr(result, "index_file", "") or ""),
        "error_file": str(getattr(result, "error_file", "") or ""),
        "mirror_rules_exposed": False,
        "note": ("The SDK exposes only index/error documents. Mirror "
                 "back-to-origin rules are not readable here; check them in "
                 "the console under the bucket's static-website settings."),
    }


def _extract_policy(result: Any) -> dict:
    raw = str(getattr(result, "policy", "") or "")
    document: dict = {}
    if raw.strip():
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                document = parsed
        except json.JSONDecodeError:
            document = {"_raw": raw[:4000]}
    statements = document.get("Statement") or []
    if not isinstance(statements, list):
        statements = []
    return {
        "configured": bool(raw.strip()),
        "raw": raw[:8000],
        "document": document,
        "statement_count": len(statements),
        "deny_count": sum(
            1 for s in statements
            if isinstance(s, dict) and str(s.get("Effect", "")).lower() == "deny"),
    }


# action -> (oss2 Bucket method name, extractor, tolerate-not-configured)
CONFIG_READERS = {
    "GetBucketInfo": ("get_bucket_info", _extract_bucket_info, False),
    "GetBucketAcl": ("get_bucket_acl",
                     lambda r: {"acl": _acl_grant(r)}, False),
    "GetBucketPolicy": ("get_bucket_policy", _extract_policy, True),
    "GetBucketReferer": ("get_bucket_referer", _extract_referer, True),
    "GetBucketLogging": ("get_bucket_logging", _extract_logging, True),
    "GetBucketWebsite": ("get_bucket_website", _extract_website, True),
    "GetPublicAccessBlock": (
        "get_bucket_public_access_block",
        lambda r: {"block_public_access":
                   str(getattr(r, "block_public_access", "")).lower()
                   in ("true", "1", "yes")},
        True),
    "GetObjectAcl": ("get_object_acl",
                     lambda r: {"acl": _acl_grant(r)}, False),
}


def read_config(action: str, bucket_name: str, region: str,
                endpoint: str = "", key: str = "",
                timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Read one bucket- or object-level configuration, normalized.

    Returns a stable dict regardless of outcome:
      available  bool   -- the read produced an answer (including "not configured")
      configured bool   -- the configuration exists
      action     str
      data       dict   -- extracted fields (empty when unavailable)
      error      dict   -- OssClientError.to_dict() when unavailable
    Never raises: every failure is captured so one denied read does not abort
    the whole evidence collection.
    """
    reader = CONFIG_READERS.get(action)
    if reader is None:
        return {"available": False, "configured": False, "action": action,
                "data": {}, "error": {"category": "invalid",
                                      "code": "UnsupportedAction",
                                      "message": f"no reader for {action}",
                                      "hint": "", "status": 0}}
    method_name, extractor, tolerate = reader
    endpoint = endpoint or endpoint_for_region(region)
    label = f"{action} bucket={bucket_name}" + (f" key={key}" if key else "")

    if not _OSS2_AVAILABLE:
        return {"available": False, "configured": False, "action": action,
                "data": {},
                "error": OssClientError(
                    f"the oss2 SDK is not installed ({_OSS2_IMPORT_ERROR})",
                    category="dependency", code="SdkMissing").to_dict()}

    try:
        bucket = _build_bucket(bucket_name, endpoint, timeout)
        method = getattr(bucket, method_name, None)
        if method is None:
            raise OssClientError(
                f"oss2 {method_name} is unavailable in this SDK version",
                category="dependency", code="MethodMissing",
                hint="Upgrade oss2 within the pinned range.")
        result = method(key) if key else method()
    except OssClientError as exc:
        if exc.category == "not_configured" or exc.code in NOT_CONFIGURED_CODES:
            return {"available": True, "configured": False, "action": action,
                    "data": extractor(None) if extractor is _extract_referer
                    else {}, "error": {}}
        return {"available": False, "configured": False, "action": action,
                "data": {}, "error": exc.to_dict()}
    except Exception as exc:  # noqa: BLE001 -- normalized below, never raised
        normalized = _normalize_oss_error(exc, label)
        if tolerate and (normalized.category == "not_configured"
                         or normalized.code in NOT_CONFIGURED_CODES):
            return {"available": True, "configured": False, "action": action,
                    "data": {}, "error": {}}
        return {"available": False, "configured": False, "action": action,
                "data": {}, "error": normalized.to_dict()}

    try:
        data = extractor(result)
    except Exception as exc:  # noqa: BLE001 -- extraction must not abort
        return {"available": False, "configured": False, "action": action,
                "data": {},
                "error": OssClientError(
                    f"{label}: could not parse the response ({exc})",
                    category="unknown", code="ParseError").to_dict()}

    configured = bool(data) and data.get("configured", True) is not False
    if action == "GetBucketPolicy":
        configured = bool(data.get("configured"))
    elif action == "GetBucketLogging":
        configured = bool(data.get("enabled"))
    return {"available": True, "configured": configured, "action": action,
            "data": data, "error": {}}


def list_buckets(prefix: str = "", region: str = _DEFAULT_REGION,
                 timeout: int = _DEFAULT_TIMEOUT,
                 max_buckets: int = _MAX_LIST_BUCKETS) -> list:
    """List buckets of this account (read-only), used as the region fallback.

    The `location` of each bucket reveals the region it was created in, which
    is how a wrong-region guess is corrected.
    """
    if not _OSS2_AVAILABLE:
        raise OssClientError(
            f"the oss2 SDK is not installed ({_OSS2_IMPORT_ERROR})",
            category="dependency", code="SdkMissing")
    endpoint = endpoint_for_region(region)
    try:
        auth = oss2.ProviderAuth(EnvCredentialsProvider())
        session = oss2.Session()
        session.session.headers["User-Agent"] = user_agent()
        service = oss2.Service(auth, endpoint, session=session,
                               connect_timeout=timeout)
        buckets: list = []
        marker = ""
        while len(buckets) < max_buckets:
            result = service.list_buckets(prefix=prefix, marker=marker,
                                          max_keys=100)
            for b in result.buckets:
                buckets.append({
                    "name": getattr(b, "name", ""),
                    "location": getattr(b, "location", ""),
                    "region": region_from_location(getattr(b, "location", "")),
                    "storage_class": getattr(b, "storage_class", ""),
                    "creation_date": getattr(b, "creation_date", ""),
                })
            if not getattr(result, "is_truncated", False):
                break
            marker = getattr(result, "next_marker", "") or ""
            if not marker:
                break
        return buckets
    except OssClientError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _normalize_oss_error(exc, f"ListBuckets prefix={prefix or '*'}")


def resolve_bucket_region(bucket_name: str, region: str,
                          timeout: int = _DEFAULT_TIMEOUT) -> dict:
    """Resolve the bucket's real region, with the ListBuckets fallback.

    Returns {region, location, source, info, buckets_scanned, warnings}.
    `source` is one of: get_bucket_info | list_buckets | user_provided |
    unresolved -- the caller must declare it, because a region taken from the
    user without verification is an assumption, not a finding.
    """
    warnings: list[str] = []
    info = read_config("GetBucketInfo", bucket_name, region, timeout=timeout)
    if info.get("available") and info.get("data", {}).get("location"):
        data = info["data"]
        return {"region": data.get("region") or region,
                "location": data.get("location", ""),
                "source": "get_bucket_info", "info": info,
                "buckets_scanned": 0, "warnings": warnings}

    warnings.append(
        f"GetBucketInfo did not resolve the region "
        f"({(info.get('error') or {}).get('code') or 'no location'}); "
        f"falling back to ListBuckets")
    try:
        buckets = list_buckets(prefix=bucket_name, region=region,
                               timeout=timeout)
    except OssClientError as exc:
        warnings.append(f"ListBuckets fallback failed: {exc.code or exc}")
        return {"region": region, "location": "", "source": "user_provided",
                "info": info, "buckets_scanned": 0, "warnings": warnings}

    for b in buckets:
        if b.get("name") == bucket_name and b.get("location"):
            return {"region": b["region"], "location": b["location"],
                    "source": "list_buckets", "info": info,
                    "buckets_scanned": len(buckets), "warnings": warnings}

    warnings.append(
        f"the bucket was not found among {len(buckets)} listed bucket(s); "
        f"using the caller-supplied region as an unverified assumption")
    return {"region": region, "location": "", "source": "user_provided",
            "info": info, "buckets_scanned": len(buckets),
            "warnings": warnings}


# ---------------------------------------------------------------------------
# Caller identity via aliyun CLI (argument-list subprocess, never shell=True)
# ---------------------------------------------------------------------------

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def get_caller_identity(timeout: int = _CLI_TIMEOUT) -> dict:
    """Run `aliyun sts get-caller-identity` and return the parsed response."""
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
            stderr=stderr)
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

    Callers degrade gracefully (log [WARN]) instead of aborting. The UID is a
    component of the real-time log project name oss-log-<uid>-<region>; the
    bucket OWNER uid from GetBucketInfo is preferred when available, because
    the identity chain and the data plane may belong to different accounts.
    """
    try:
        identity = get_caller_identity()
    except CliError as e:
        print(f"[WARN] identity pre-check failed: {e}", file=sys.stderr)
        return ""
    return str(identity.get("AccountId") or "").strip()


# ---------------------------------------------------------------------------
# Inline boundary assertions for the pure helpers above
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Normal / boundary / invalid assertions; run with --self-test."""
    assert endpoint_for_region("cn-hangzhou") == "oss-cn-hangzhou.aliyuncs.com"
    assert endpoint_for_region("oss-cn-beijing") == "oss-cn-beijing.aliyuncs.com"
    assert endpoint_for_region("") == f"oss-{_DEFAULT_REGION}.aliyuncs.com"
    assert region_from_location("oss-cn-shanghai") == "cn-shanghai"
    assert region_from_location("cn-shanghai") == "cn-shanghai"
    assert region_from_location("") == ""

    # error normalization: not-configured is a finding, not a failure
    assert "NoSuchBucketPolicy" in NOT_CONFIGURED_CODES
    err = OssClientError("x", category="not_configured",
                         code="NoSuchBucketPolicy")
    assert err.to_dict()["category"] == "not_configured"

    # extractors must survive an empty/None result
    assert _extract_referer(None) == {
        "allow_empty_referer": False, "allow_truncate_query_string": None,
        "whitelist_count": 0, "whitelist": [],
        "blacklist_count": 0, "blacklist": []}
    assert _extract_logging(None) == {"enabled": False, "target_bucket": "",
                                      "target_prefix": ""}
    assert _extract_website(None)["mirror_rules_exposed"] is False
    assert _extract_policy(None)["configured"] is False
    assert _extract_bucket_info(None)["owner_id"] == ""

    # policy extraction: valid JSON, invalid JSON, empty
    class _R:
        policy = '{"Version":"1","Statement":[{"Effect":"Deny"},{"Effect":"Allow"}]}'
    out = _extract_policy(_R())
    assert out["configured"] is True and out["statement_count"] == 2
    assert out["deny_count"] == 1

    class _Bad:
        policy = "not-json"
    assert _extract_policy(_Bad())["document"] == {"_raw": "not-json"}

    class _Empty:
        policy = ""
    assert _extract_policy(_Empty())["configured"] is False

    # read_config on an unknown action degrades instead of raising
    out = read_config("NoSuchAction", "b", "cn-hangzhou")
    assert out["available"] is False and out["error"]["code"] == "UnsupportedAction"

    # every declared reader names a method that exists in the pinned SDK range
    if _OSS2_AVAILABLE:
        for action, (method_name, _ext, _tol) in CONFIG_READERS.items():
            assert hasattr(oss2.Bucket, method_name), f"{action}: {method_name}"

    print("self-test passed")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _self_test()
        sys.exit(0)
    print("internal module; run with --self-test", file=sys.stderr)
    sys.exit(2)
