"""Shared IMM client factory used by process.py and imm_admin.py."""

import json
import os
import sys

from errors import die as _die


def get_imm_client(region: str):
    """Create and return an IMM client. Lazy-loads the IMM SDK."""
    try:
        from alibabacloud_imm20200930.client import Client as ImmClient
        from alibabacloud_tea_openapi import models as openapi_models
    except ImportError:
        _die(
            "Missing dependencies for IMM operations: "
            "alibabacloud_imm20200930, alibabacloud_tea_openapi.",
            "Install with: pip install -r scripts/requirements.txt"
        )

    from credential import USER_AGENT, get_credential_client

    credential_client = get_credential_client()

    # IMM region: strip 'oss-' prefix if present
    imm_region = region.replace("oss-", "")
    config = openapi_models.Config(
        credential=credential_client,
        endpoint=f"imm.{imm_region}.aliyuncs.com",
        region_id=imm_region,
        connect_timeout=30000,  # 30s in milliseconds
        read_timeout=60000,     # 60s in milliseconds
        user_agent=USER_AGENT,
    )
    return ImmClient(config)
