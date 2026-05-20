# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_util import models as tea_util_models

try:
    from alibabacloud_tea_openapi.utils import Utils
except ImportError:  # 兼容不导出 utils 模块的 tea-openapi 版本
    Utils = None

try:
    # tea-openapi 新版本
    from alibabacloud_tea_openapi import utils_models as open_api_util_models
except ImportError:
    try:
        # 部分旧版本命名
        from alibabacloud_tea_openapi import util_models as open_api_util_models
    except ImportError:
        # 再兜底到 models，避免因模块导出差异导致启动失败
        open_api_util_models = open_api_models

SYSOM_ENDPOINT = "sysom.cn-hangzhou.aliyuncs.com"
SYSOM_API_VERSION = "2023-12-30"


def _build_query(data: Dict[str, Any]) -> Dict[str, Any]:
    if Utils is not None:
        return Utils.query(data)
    return dict(data)


def _build_map(data: Dict[str, Any]) -> Dict[str, Any]:
    if Utils is not None:
        return Utils.parse_to_map(data)
    return dict(data)


class SysomOpenApiCaller:
    def __init__(self, credentials: Dict[str, str], endpoint: str = SYSOM_ENDPOINT) -> None:
        cfg = open_api_models.Config(
            access_key_id=credentials["ak_id"],
            access_key_secret=credentials["ak_secret"],
            endpoint=endpoint,
            user_agent="AlibabaCloud-Agent-Skills/alibabacloud-alinux-sysom-inspection",
        )
        if credentials.get("security_token"):
            cfg.security_token = credentials["security_token"]
        cfg.connect_timeout = 10_000
        self._client = OpenApiClient(cfg)
        self._runtime = tea_util_models.RuntimeOptions()

    async def call_rpc(self, action: str, query: Dict[str, Any]) -> Dict[str, Any]:
        req = open_api_util_models.OpenApiRequest(query=_build_query(query), headers={})
        params = open_api_util_models.Params(
            action=action,
            version=SYSOM_API_VERSION,
            protocol="HTTPS",
            pathname="/",
            method="POST",
            auth_type="AK",
            style="RPC",
            req_body_type="formData",
            body_type="json",
        )
        out = await self._client.call_api_async(params, req, self._runtime)
        if not isinstance(out, dict):
            raise RuntimeError(f"{action} 返回类型异常: {type(out)}")
        return out

    async def call_roa(
        self,
        action: str,
        pathname: str,
        method: str,
        body: Optional[Dict[str, Any]] = None,
        query: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        req = open_api_util_models.OpenApiRequest(
            headers={},
            body=_build_map(body or {}),
            query=_build_query(query or {}),
        )
        params = open_api_util_models.Params(
            action=action,
            version=SYSOM_API_VERSION,
            protocol="HTTPS",
            pathname=pathname,
            method=method,
            auth_type="AK",
            style="ROA",
            req_body_type="json",
            body_type="json",
        )
        out = await self._client.call_api_async(params, req, self._runtime)
        if not isinstance(out, dict):
            raise RuntimeError(f"{action} 返回类型异常: {type(out)}")
        return out


def normalize_sysom_body(raw: Dict[str, Any]) -> Dict[str, Any]:
    body = raw.get("body")
    if not isinstance(body, dict):
        return {}
    out = dict(body)
    if out.get("code") is None and body.get("Code") is not None:
        out["code"] = body["Code"]
    if out.get("message") is None and body.get("Message") is not None:
        out["message"] = body["Message"]
    if out.get("request_id") is None and body.get("RequestId") is not None:
        out["request_id"] = body["RequestId"]
    return out


def extract_data_points(metric_body: Dict[str, Any]) -> List[Tuple[int, float]]:
    data = metric_body.get("data") or metric_body.get("Data") or {}
    candidates: Sequence[Any] = (
        data.get("datapoints"),
        data.get("Datapoints"),
        data.get("points"),
        metric_body.get("datapoints"),
        metric_body.get("Datapoints"),
    )

    points_raw: Any = None
    for x in candidates:
        if x is not None:
            points_raw = x
            break
    if points_raw is None:
        return []

    if isinstance(points_raw, str):
        try:
            points_raw = json.loads(points_raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(points_raw, list):
        return []

    points: List[Tuple[int, float]] = []
    for p in points_raw:
        if not isinstance(p, dict):
            continue
        ts = p.get("timestamp") or p.get("Timestamp") or p.get("time") or p.get("Time")
        val = p.get("value") or p.get("Value") or p.get("avg") or p.get("Avg")
        try:
            points.append((int(float(ts)), float(val)))
        except (TypeError, ValueError):
            continue
    points.sort(key=lambda x: x[0])
    return points


def is_continuous_over_threshold(
    points: Sequence[Tuple[int, float]],
    *,
    now_ts: int,
    window_seconds: int,
    threshold_percent: float,
    period_seconds: int,
) -> bool:
    if not points:
        return False

    begin = now_ts - window_seconds
    in_window = [(ts, val) for ts, val in points if begin <= ts <= now_ts]
    if not in_window:
        return False

    max_gap = int(period_seconds * 1.5)
    first_ts = in_window[0][0]
    last_ts = in_window[-1][0]
    if first_ts > begin + max_gap:
        return False
    if now_ts - last_ts > max_gap:
        return False

    prev: Optional[int] = None
    for ts, val in in_window:
        if val <= threshold_percent:
            return False
        if prev is not None and ts - prev > max_gap:
            return False
        prev = ts

    return (last_ts - first_ts) >= (window_seconds - max_gap)
