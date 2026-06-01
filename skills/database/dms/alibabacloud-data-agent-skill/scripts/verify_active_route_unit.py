#!/usr/bin/env python3
"""Standalone verifier for the GetActiveRouteUnit API.

Purpose:
    Independently verify that the dms-enterprise OpenAPI
    ``GetActiveRouteUnit`` (2018-11-01) can be called and returns a usable
    DMSUnit value. Does not touch ``DataAgentClient`` or business code.

Usage:
    cd alibabacloud-data-agent-skill
    python3 scripts/verify_active_route_unit.py
    python3 scripts/verify_active_route_unit.py --region cn-hangzhou
    DATA_AGENT_DEBUG_API=1 python3 scripts/verify_active_route_unit.py

Exit codes:
    0 - API call succeeded and a DMSUnit-like field was parsed.
    1 - API call failed (TeaException / network / missing field).

Author: Tinker
Created: 2026-04-28
"""

from __future__ import annotations

import argparse
import json
import os
import pprint
import sys
from pathlib import Path
from typing import Any, Optional

# Ensure local packages (data_agent) are importable, mirroring data_agent_cli.py
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_util import models as util_models
from Tea.exceptions import TeaException

from data_agent.config import DataAgentConfig


API_VERSION = "2018-11-01"
API_ACTION = "GetActiveRouteUnit"

# Per the OpenAPI spec:
#   - Route object on the frontend maps to backend field name "data"
#   - Route.RegionId (backend: regionId) is the real DMSUnit value
# So we search both the frontend (PascalCase) and backend (camelCase) naming.
ROUTE_CONTAINER_KEYS = ("Route", "data", "Data")
UNIT_FIELD_CANDIDATES = ("RegionId", "regionId")


def _debug_enabled() -> bool:
    return os.getenv("DATA_AGENT_DEBUG_API", "").lower() in ("true", "1", "yes")


def _build_client(region: str) -> OpenApiClient:
    """Build an OpenApiClient for dms-enterprise using the default credential chain."""
    endpoint = f"dms-enterprise.{region}.aliyuncs.com"
    cred = CredentialClient()
    cfg = open_api_models.Config()
    cfg.endpoint = endpoint
    cfg.credential = cred
    cfg.user_agent = "AlibabaCloud-Agent-Skills/alibabacloud-data-agent-skill/verify-route-unit"
    return OpenApiClient(cfg)


def _call(client: OpenApiClient, params: dict[str, Any], timeout: int) -> dict[str, Any]:
    """Invoke GetActiveRouteUnit with the given params. Returns the response body dict."""
    api_params = open_api_models.Params(
        action=API_ACTION,
        version=API_VERSION,
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="json",
        body_type="json",
    )
    request = open_api_models.OpenApiRequest(
        query=OpenApiUtilClient.query(params),
    )
    runtime = util_models.RuntimeOptions(
        read_timeout=timeout * 1000,
        connect_timeout=30000,
    )
    response = client.call_api(api_params, request, runtime)
    return response.get("body", {}) if isinstance(response, dict) else {}


def _extract_unit(body: dict[str, Any]) -> Optional[tuple[str, str]]:
    """Search for Route.RegionId in the response body.

    Per OpenAPI spec, the Route object (backend: "data") may contain
    {Uid, RegionId, Status}. Only present when the tenant has been
    scheduled to a non-default DMS unit.

    Returns (field_path, value) on hit, or None otherwise.
    """
    for container_key in ROUTE_CONTAINER_KEYS:
        route = body.get(container_key)
        if not isinstance(route, dict):
            continue
        for unit_key in UNIT_FIELD_CANDIDATES:
            val = route.get(unit_key)
            if isinstance(val, str) and val:
                return f"{container_key}.{unit_key}", val
    return None


def _print_request(region: str, params: dict[str, Any]) -> None:
    print("=" * 70)
    print(f"Endpoint : dms-enterprise.{region}.aliyuncs.com")
    print(f"Action   : {API_ACTION}")
    print(f"Version  : {API_VERSION}")
    print(f"Region   : {region}")
    print(f"Params   : {params if params else '(none)'}")
    print("-" * 70)


def _print_response(body: dict[str, Any]) -> None:
    print(f"RequestId: {body.get('RequestId', '(missing)')}")
    if _debug_enabled():
        print("Body (full):")
        pprint.pprint(body, indent=2, width=100)
    else:
        print("Body:")
        try:
            print(json.dumps(body, ensure_ascii=False, indent=2))
        except (TypeError, ValueError):
            pprint.pprint(body, indent=2, width=100)
    print("=" * 70)


def verify(region: str, timeout: int) -> int:
    """Run the verification. Returns process exit code.

    Interpretation of responses (based on confirmed OpenAPI spec):
      - body has Route/data object with RegionId -> tenant was scheduled to
        a non-default unit; that RegionId IS the DMSUnit. Exit 0.
      - body is {RequestId, Success: true} only -> tenant belongs to the
        default unit; DMSUnit should fall back to current region. Exit 0.
      - any ErrorCode / non-200 -> failure. Exit 1.
    """
    try:
        client = _build_client(region)
    except Exception as e:  # noqa: BLE001
        print(f"[ERROR] Failed to build OpenApiClient: {e}", file=sys.stderr)
        print(
            "Hint: configure AK/SK via ~/.aliyun/config.json, environment variables, "
            "or instance role (default credential chain).",
            file=sys.stderr,
        )
        return 1

    params: dict[str, Any] = {}  # No business params required; identity is injected by POP gateway
    _print_request(region, params)
    try:
        body = _call(client, params, timeout)
    except TeaException as e:
        code = getattr(e, "code", "Unknown")
        message = getattr(e, "message", str(e))
        req_id = None
        if hasattr(e, "data") and isinstance(e.data, dict):
            req_id = e.data.get("RequestId")
        print(
            f"[FAIL] TeaException: code={code}, message={message}, requestId={req_id}",
            file=sys.stderr,
        )
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    _print_response(body)

    # Business-level error in body (ErrorCode / ErrorMessage)
    err_code = body.get("ErrorCode") or body.get("errorCode")
    if err_code:
        err_msg = body.get("ErrorMessage") or body.get("message") or ""
        print(f"\n[FAIL] Server reported business error: {err_code} - {err_msg}", file=sys.stderr)
        return 1

    hit = _extract_unit(body)
    if hit:
        field, value = hit
        print(f"\n[OK] DMSUnit resolved from Route: {field} = {value!r}")
        print(f"      (tenant was scheduled to a non-default unit)")
        return 0

    # Success:true but no Route -> default unit
    if body.get("Success") is True or body.get("success") is True:
        print(
            f"\n[OK] No Route object in response -> tenant belongs to the DEFAULT unit.\n"
            f"      DMSUnit should fall back to the current region: {region!r}"
        )
        return 0

    print(
        "\n[FAIL] Response neither carries Route/data nor Success=true; cannot resolve DMSUnit.",
        file=sys.stderr,
    )
    return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify dms-enterprise GetActiveRouteUnit API and print DMSUnit.",
    )
    parser.add_argument(
        "--region",
        default=None,
        help="Alibaba Cloud region ID; defaults to DataAgentConfig.from_env() (DATA_AGENT_REGION).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    cfg = DataAgentConfig.from_env()
    region = args.region or cfg.region
    print(f"Using region: {region} (override with --region)")
    return verify(region=region, timeout=args.timeout)


if __name__ == "__main__":
    sys.exit(main())
