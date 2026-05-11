"""Shared credential helper for Alibaba Cloud OSS Media Processing Skill.

Provides a unified interface for obtaining Alibaba Cloud credentials via the
alibabacloud-credentials SDK default chain (~/.aliyun/config.json set by
`aliyun configure`, ECS instance metadata).

The credential client is cached and passed through provider-aware SDK hooks so
callers do not need to manually extract or manage raw AK/SK values.
"""

import json
import os
import sys

from errors import die as _die

_CRED_CLIENT = None
USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-oss-media-process"


def _credential_has_material(cred_client) -> bool:
    """Return True when a credential client yields usable access key material."""
    try:
        cred = cred_client.get_credential()
    except Exception:
        return False

    if cred is None:
        return False

    access_key_id = getattr(cred, "access_key_id", None)
    if access_key_id is None and hasattr(cred, "get_access_key_id"):
        access_key_id = cred.get_access_key_id()

    access_key_secret = getattr(cred, "access_key_secret", None)
    if access_key_secret is None and hasattr(cred, "get_access_key_secret"):
        access_key_secret = cred.get_access_key_secret()

    return bool(access_key_id and access_key_secret)


def _try_credentials_sdk():
    """Try to get credentials from alibabacloud-credentials SDK.

    Returns the credential client object or None.
    """
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
    except ImportError:
        return None

    try:
        cred = CredentialClient()
        if _credential_has_material(cred):
            return cred
    except Exception:
        pass

    return None


def ensure_credentials(required: bool = True) -> bool:
    """Load credentials via alibabacloud-credentials SDK and cache the client.

    The SDK follows its default credential chain:
      ~/.aliyun/config.json (set by `aliyun configure`) →
      ECS instance metadata

    When required=True, prints error and exits if credentials cannot be obtained.
    When required=False, returns False silently on failure.

    Returns True if credentials were loaded successfully.
    """
    global _CRED_CLIENT

    # Already cached
    if _CRED_CLIENT is not None:
        return True

    cred = _try_credentials_sdk()
    if cred:
        _CRED_CLIENT = cred
        return True

    # No credentials found
    if required:
        _die(
            "Alibaba Cloud credentials not found.",
            "Configure credentials with Aliyun CLI:\n"
            "  aliyun configure",
        )
    return False


def get_credential_client(required: bool = True):
    """Return the cached credential client from the default chain.

    Returns None only when required=False and credentials are unavailable.
    """
    if ensure_credentials(required=required):
        return _CRED_CLIENT
    return None


def get_oss_credentials_provider(required: bool = True):
    """Create an oss2 credentials provider backed by the default chain."""
    client = get_credential_client(required=required)
    if client is None:
        return None

    try:
        import oss2.credentials as oss2_credentials
    except ImportError:
        if required:
            _die("oss2 SDK not installed.", "Install with: pip install oss2==2.19.1")
        return None

    class _AliyunCredentialProvider(oss2_credentials.CredentialsProvider):
        def __init__(self, cred_client):
            self._cred_client = cred_client

        def get_credentials(self):
            cred = self._cred_client.get_credential()
            return oss2_credentials.Credentials(
                access_key_id=cred.get_access_key_id(),
                access_key_secret=cred.get_access_key_secret(),
                security_token=cred.get_security_token() or "",
            )

    return _AliyunCredentialProvider(client)


def has_credential_material() -> bool:
    """Return True when the default credential chain yields usable material."""
    client = get_credential_client(required=False)
    if client is None:
        return False

    return _credential_has_material(client)


def get_bucket(default: str = "") -> str:
    """Return bucket name from env var, or the given default."""
    return os.environ.get("ALIBABA_CLOUD_OSS_BUCKET", default)


def get_region(default: str = "") -> str:
    """Return region from env var, or the given default."""
    return os.environ.get("ALIBABA_CLOUD_OSS_REGION", default)


def get_imm_project(default: str = "") -> str:
    """Return IMM project name from env var, or the given default."""
    return os.environ.get("ALIBABA_CLOUD_IMM_PROJECT", default)
