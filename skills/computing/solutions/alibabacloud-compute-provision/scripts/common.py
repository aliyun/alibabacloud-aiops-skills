#!/usr/bin/env python3
"""Shared utilities for Alibaba Cloud API calls."""

from __future__ import annotations

import json
import os
import time
import warnings
from typing import Any

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="urllib3")

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from darabonba.runtime import RuntimeOptions

USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-compute-provision"


def get_credential() -> CredentialClient:
    """Return a credential client using the default provider chain.

    The default chain automatically resolves credentials from environment
    variables, ~/.alibabacloud/credentials, ~/.aliyun/config.json, and
    instance RAM roles, in priority order.
    """
    return CredentialClient(None)


def get_default_region() -> str:
    """Return the default region (env override, otherwise cn-hangzhou)."""
    return os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")


def build_client(endpoint: str, region: str | None = None) -> OpenApiClient:
    """Build an OpenAPI client for the given endpoint."""
    config = open_api_models.Config(
        credential=get_credential(),
        endpoint=endpoint,
        region_id=region or get_default_region(),
        user_agent=USER_AGENT,
    )
    return OpenApiClient(config)


def call_rpc_api(
    product: str,
    version: str,
    action: str,
    params: dict[str, Any] | None = None,
    region: str | None = None,
    endpoint: str | None = None,
) -> dict:
    """Call an Alibaba Cloud RPC-style API.

    Args:
        product: Product code (e.g. 'ecs', 'vpc').
        version: API version (e.g. '2014-05-26').
        action: API action name.
        params: Query parameters.
        region: Region ID. Falls back to env default.
        endpoint: Override endpoint. Auto-resolved if not given.
    """
    r = region or get_default_region()
    ep = endpoint or f"{product}.{r}.aliyuncs.com"
    client = build_client(ep, r)

    query = dict(params or {})
    query.setdefault("RegionId", r)
    serialized = _serialize(query)

    api_params = open_api_models.Params(
        action=action,
        version=version,
        protocol="HTTPS",
        pathname="/",
        method="POST",
        auth_type="AK",
        style="RPC",
        body_type="json",
        req_body_type="json",
    )
    request = open_api_models.OpenApiRequest(query=serialized)
    result = client.call_api(api_params, request, RuntimeOptions())
    return result.get("body", result)


def call_roa_api(
    version: str,
    pathname: str,
    method: str = "GET",
    query: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None,
    region: str | None = None,
    endpoint: str | None = None,
    body_type: str = "json",
    action: str = "anonymous",
) -> dict | str:
    """Call an Alibaba Cloud ROA-style API.

    Args:
        version: API version.
        pathname: URL path (e.g. '/2023-03-30/functions').
        method: HTTP method.
        query: Query string parameters.
        body: Request body (for POST/PUT).
        region: Region ID.
        endpoint: API endpoint.
        body_type: Response body type — "json" (parse as JSON) or "none" (no parsing).
        action: API action name for gateway routing (some products like
            PAI-DLC require the real action name, not "anonymous").
    """
    if not endpoint:
        raise ValueError("endpoint is required for ROA API calls")

    r = region or get_default_region()
    client = build_client(endpoint, r)

    serialized_query = _serialize(query) if query else None

    api_params = open_api_models.Params(
        action=action,
        version=version,
        protocol="HTTPS",
        pathname=pathname,
        method=method,
        auth_type="AK",
        style="ROA",
        body_type=body_type,
        req_body_type="json",
    )
    request = open_api_models.OpenApiRequest(
        query=serialized_query,
        body=body,
    )
    result = client.call_api(api_params, request, RuntimeOptions())
    return result.get("body", result)


def wait_until(
    check_fn,
    target_statuses: set[str],
    fail_statuses: set[str] | None = None,
    interval: int = 10,
    timeout: int = 600,
    status_key: str = "Status",
) -> dict:
    """Poll check_fn until status reaches target or fails.

    Args:
        check_fn: Callable returning a dict with status info.
        target_statuses: Success statuses.
        fail_statuses: Failure statuses (raises on match).
        interval: Seconds between polls.
        timeout: Max wait seconds.
        status_key: Key to read status from check_fn result.

    Returns:
        The final check_fn result.
    """
    fail_statuses = fail_statuses or set()
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = check_fn()
        status = result.get(status_key, "")
        if status in target_statuses:
            return result
        if status in fail_statuses:
            raise RuntimeError(f"Resource entered failure state: {status}. Detail: {json.dumps(result, ensure_ascii=False)}")
        print(f"  Current status: {status}, waiting {interval}s...")
        time.sleep(interval)
    raise TimeoutError(f"Timed out after {timeout}s waiting for status in {target_statuses}")


def pp(data: Any) -> str:
    """Pretty-print a dict/list as JSON string and print it."""
    s = json.dumps(data, ensure_ascii=False, indent=2)
    print(s)
    return s


def _serialize(params: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, str):
            result[k] = v
        elif isinstance(v, bool):
            result[k] = "true" if v else "false"
        elif isinstance(v, (dict, list)):
            result[k] = json.dumps(v, ensure_ascii=False)
        else:
            result[k] = str(v)
    return result
