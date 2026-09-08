# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_util import models as tea_util_models

try:
    from alibabacloud_tea_openapi import utils_models as open_api_util_models
except ImportError:
    try:
        from alibabacloud_tea_openapi import util_models as open_api_util_models
    except ImportError:
        open_api_util_models = open_api_models


class SysomAuthError(RuntimeError):
    pass


def _check_env_credentials() -> Optional[Dict[str, str]]:
    ak_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID") or os.getenv(
        "ALICLOUD_ACCESS_KEY_ID")
    ak_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or os.getenv(
        "ALICLOUD_ACCESS_KEY_SECRET")
    security_token = (
        os.getenv("ALIBABA_CLOUD_SECURITY_TOKEN")
        or os.getenv("ALICLOUD_SECURITY_TOKEN")
        or os.getenv("SECURITY_TOKEN")
    )
    if not ak_id or not ak_secret:
        return None
    creds: Dict[str, str] = {"ak_id": ak_id, "ak_secret": ak_secret}
    if security_token:
        creds["security_token"] = security_token
    return creds


def _load_aliyun_profile() -> Dict[str, Any]:
    config_path = Path.home() / ".aliyun" / "config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _fetch_ram_role_credentials(role_name: str) -> Optional[Dict[str, str]]:
    url = f"http://100.100.100.200/latest/meta-data/ram/security-credentials/{role_name}"
    try:
        response = requests.get(url, timeout=3)
        if response.status_code != 200:
            return None
        data = response.json()
        return {
            "ak_id": data["AccessKeyId"],
            "ak_secret": data["AccessKeySecret"],
            "security_token": data["SecurityToken"],
        }
    except Exception:
        return None


def _load_ecs_ram_role_credentials() -> Optional[Dict[str, str]]:
    base = "http://100.100.100.200/latest/meta-data/ram/security-credentials/"
    try:
        role_resp = requests.get(base, timeout=3)
        if role_resp.status_code != 200 or not role_resp.text.strip():
            return None
        return _fetch_ram_role_credentials(role_resp.text.strip())
    except Exception:
        return None


def _assume_role(
    ak_id: str,
    ak_secret: str,
    role_arn: str,
    role_session_name: str = "sysom-inspection",
    duration_seconds: int = 3600,
    external_id: Optional[str] = None,
    sts_endpoint: str = "sts.aliyuncs.com",
) -> Dict[str, str]:
    """Call STS AssumeRole to exchange temporary credentials."""
    try:
        cfg = open_api_models.Config(
            access_key_id=ak_id,
            access_key_secret=ak_secret,
            endpoint=sts_endpoint,
        )
        client = OpenApiClient(cfg)
        runtime = tea_util_models.RuntimeOptions()

        query: Dict[str, str] = {
            "Action": "AssumeRole",
            "Version": "2015-04-01",
            "Format": "JSON",
            "RoleArn": role_arn,
            "RoleSessionName": role_session_name,
            "DurationSeconds": str(duration_seconds),
        }
        if external_id:
            query["ExternalId"] = external_id

        req = open_api_util_models.OpenApiRequest(query=query)
        params = open_api_util_models.Params(
            action="AssumeRole",
            version="2015-04-01",
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="AK",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )

        response = client.call_api(params, req, runtime)
        body = response.get("body", {}) if isinstance(response, dict) else {}
        creds = body.get("Credentials")
        if not creds:
            code = body.get("Code", "")
            message = body.get("Message", "no credentials in response")
            raise SysomAuthError(f"STS AssumeRole failed: {code} - {message}")

        return {
            "ak_id": creds["AccessKeyId"],
            "ak_secret": creds["AccessKeySecret"],
            "security_token": creds["SecurityToken"],
        }
    except SysomAuthError:
        raise
    except Exception as e:
        raise SysomAuthError(
            f"Failed to assume role '{role_arn}': {e}"
        ) from e


def _load_aliyun_config_credentials() -> Optional[Dict[str, str]]:
    config = _load_aliyun_profile()
    if not config:
        return None

    profile_name = config.get("current_profile") or config.get(
        "current") or "default"
    profiles = config.get("profiles") or []
    profile = next(
        (p for p in profiles if p.get("name") == profile_name), None)
    if not profile:
        return None

    mode = str(profile.get("mode", "AK")).strip().lower()
    if mode == "ak":
        if profile.get("access_key_id") and profile.get("access_key_secret"):
            return {
                "ak_id": profile["access_key_id"],
                "ak_secret": profile["access_key_secret"],
            }
        return None

    if mode == "ststoken":
        token = profile.get("sts_token") or profile.get(
            "security_token") or profile.get("access_key_sts_token")
        if profile.get("access_key_id") and profile.get("access_key_secret") and token:
            return {
                "ak_id": profile["access_key_id"],
                "ak_secret": profile["access_key_secret"],
                "security_token": token,
            }
        return None

    if mode == "ecsramrole":
        return _load_ecs_ram_role_credentials()

    if mode == "ramrolearn":
        ak_id = profile.get("access_key_id")
        ak_secret = profile.get("access_key_secret")
        role_arn = profile.get("ram_role_arn")
        if not ak_id or not ak_secret or not role_arn:
            return None
        session_name = profile.get("ram_session_name") or "sysom-inspection"
        external_id = profile.get("external_id") or None
        sts_region = profile.get("sts_region") or None
        sts_endpoint = f"sts.{sts_region}.aliyuncs.com" if sts_region else "sts.aliyuncs.com"
        return _assume_role(
            ak_id, ak_secret, role_arn, session_name,
            external_id=external_id, sts_endpoint=sts_endpoint,
        )

    if profile.get("ram_role_name"):
        return _fetch_ram_role_credentials(profile["ram_role_name"])
    return None


def resolve_sysom_credentials() -> Dict[str, str]:
    creds = _check_env_credentials()
    if creds:
        return creds
    creds = _load_aliyun_config_credentials()
    if creds:
        return creds
    raise SysomAuthError(
        "No valid credentials found. Configure AK/SK environment variables "
        "or ~/.aliyun/config.json (AK/StsToken/EcsRamRole/RamRoleArn)."
    )
