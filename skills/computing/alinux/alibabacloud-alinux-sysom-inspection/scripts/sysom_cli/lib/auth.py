# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class SysomAuthError(RuntimeError):
    pass


def _check_env_credentials() -> Optional[Dict[str, str]]:
    ak_id = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_ID") or os.getenv("ALICLOUD_ACCESS_KEY_ID")
    ak_secret = os.getenv("ALIBABA_CLOUD_ACCESS_KEY_SECRET") or os.getenv("ALICLOUD_ACCESS_KEY_SECRET")
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


def _load_aliyun_config_credentials() -> Optional[Dict[str, str]]:
    config = _load_aliyun_profile()
    if not config:
        return None

    profile_name = config.get("current_profile") or config.get("current") or "default"
    profiles = config.get("profiles") or []
    profile = next((p for p in profiles if p.get("name") == profile_name), None)
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
        token = profile.get("sts_token") or profile.get("security_token") or profile.get("access_key_sts_token")
        if profile.get("access_key_id") and profile.get("access_key_secret") and token:
            return {
                "ak_id": profile["access_key_id"],
                "ak_secret": profile["access_key_secret"],
                "security_token": token,
            }
        return None

    if mode == "ecsramrole":
        return _load_ecs_ram_role_credentials()

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
        "未找到可用凭证，请配置环境变量 AK/SK 或 ~/.aliyun/config.json（AK/StsToken/EcsRamRole）。"
    )
