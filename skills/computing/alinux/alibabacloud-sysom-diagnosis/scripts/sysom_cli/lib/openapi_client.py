# -*- coding: utf-8 -*-
"""
SysOM OpenAPI（阿里云 SDK）封装：凭证解析、按 Action 名异步调用。

约定::

    ``ListDiagnosis`` -> ``models.ListDiagnosisRequest`` + ``await client.list_diagnosis_async(request)``

鉴权：``sysom_cli.lib.auth.resolve_sysom_auth`` / ``test_sysom_api``。

用法::

    import asyncio
    from sysom_cli.lib.sysom_openapi_client import sysom_openapi_client

    async def main():
        ok, data, err = await sysom_openapi_client.call_api("ListDiagnosis", {})

    asyncio.run(main())

``sysom_openapi_client`` 为**惰性单例**：首次调用方法时才构造 ``SysomOpenAPIClient``，
避免在仅导入模块（如注册子命令）时就必须已有凭证。需换 endpoint / 凭证时可赋值替换::

    import sysom_cli.lib.openapi_client as m
    m.sysom_openapi_client = SysomOpenAPIClient(verify_auth=False, endpoint="...")
"""
from __future__ import annotations

import json
import re
from typing import Any, Awaitable, Callable, Dict, Literal, Optional, Tuple, Type, Union

from Tea.model import TeaModel
from alibabacloud_sysom20231230.client import Client as SysOM20231230Client
from alibabacloud_tea_openapi import models as open_api_models

from sysom_cli.lib.auth import resolve_sysom_auth, test_sysom_api

__all__ = [
    "DEFAULT_SYSOM_ENDPOINT",
    "ReturnAs",
    "SysomOpenAPIClient",
    "sysom_openapi_client",
    "api_action_to_snake",
    "resolve_sysom_async_api",
    "pack_result",
    "build_sdk_request",
    "normalize_sysom_roa_body",
]

ReturnAs = Literal["body", "response", "dict"]

DEFAULT_SYSOM_ENDPOINT = "sysom.cn-hangzhou.aliyuncs.com"
_CONNECT_TIMEOUT_MS = 10_000


def api_action_to_snake(api_action: str) -> str:
    """``ListDiagnosis`` -> ``list_diagnosis``。"""
    name = api_action.strip()
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1)
    return s2.lower()


def resolve_sysom_async_api(
    api_name: str,
    sdk_client: SysOM20231230Client,
) -> Tuple[Type[TeaModel], Callable[..., Awaitable[Any]]]:
    """由 OpenAPI Action 名解析 ``Request`` 类与 SDK 上的 ``{snake}_async`` 方法。"""
    from alibabacloud_sysom20231230 import models as sysom_models

    action = api_name.strip()
    if not action:
        raise ValueError("api_name 不能为空")

    request_cls_name = f"{action}Request"
    if not hasattr(sysom_models, request_cls_name):
        raise LookupError(
            f"未找到模型 alibabacloud_sysom20231230.models.{request_cls_name}，"
            "请确认 Action 为 PascalCase 且与 SDK 一致"
        )
    request_cls = getattr(sysom_models, request_cls_name)

    async_name = api_action_to_snake(action) + "_async"
    method = getattr(sdk_client, async_name, None)
    if method is None or not callable(method):
        raise LookupError(
            f"SDK 上不存在异步方法 {async_name!r}（来自 Action {action!r}），"
            "请核对名称或使用 raw_sdk_client()"
        )
    return request_cls, method


def pack_result(response: Any, body: Any, return_as: ReturnAs) -> Any:
    """按 ``return_as`` 从 ``response`` / ``body`` 取出返回值。"""
    if return_as == "response":
        return response
    if return_as == "body":
        return body
    if return_as == "dict":
        target = body if body is not None else response
        if target is None:
            return None
        if isinstance(target, dict):
            return target
        to_map = getattr(target, "to_map", None)
        if callable(to_map):
            return to_map()
        return str(target)
    raise ValueError(f"不支持的 return_as: {return_as!r}，应为 body / response / dict")


def normalize_sysom_roa_body(inner: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    将 ROA JSON 中常见的 PascalCase 字段映射为 SDK 模型使用的小写键，便于下游判断标准错误码。

    网关可能返回 ``Code`` / ``Message`` / ``RequestId``，而 alibabacloud 部分模型 ``from_map`` 只读小写，
    导致 ``body.to_map()`` 为空；此处与原始 ``call_api_async`` 的 ``body`` 字典对齐。
    """
    if not inner:
        return {}
    out: Dict[str, Any] = dict(inner)
    if out.get("code") is None and "Code" in inner:
        out["code"] = inner["Code"]
    if out.get("message") is None and "Message" in inner:
        out["message"] = inner["Message"]
    if out.get("request_id") is None and "RequestId" in inner:
        out["request_id"] = inner["RequestId"]
    if out.get("recommend") is None and "Recommend" in inner:
        out["recommend"] = inner["Recommend"]
    if out.get("host_id") is None and "HostId" in inner:
        out["host_id"] = inner["HostId"]

    data = inner.get("data") if isinstance(inner.get("data"), dict) else inner.get("Data")
    if isinstance(data, dict):
        nd = dict(data)
        if "task_id" not in nd and "TaskId" in nd:
            nd["task_id"] = nd["TaskId"]
        # GetDiagnosisResult 轮询数据
        if "status" not in nd and "Status" in nd:
            nd["status"] = nd["Status"]
        if "err_msg" not in nd and "ErrMsg" in nd:
            nd["err_msg"] = nd["ErrMsg"]
        # result / Result：部分专项在 result 为 null/{} 时把载荷放在 Result，或仅有大写键
        rlow = nd.get("result")
        rhigh = nd.get("Result")
        if rhigh is not None and (
            rlow is None
            or rlow == ""
            or (isinstance(rlow, dict) and not rlow)
        ):
            nd["result"] = rhigh
        elif "result" not in nd and rhigh is not None:
            nd["result"] = rhigh
        out["data"] = nd
    return out


def _biz_code_success(code: Optional[str]) -> bool:
    return str(code or "").strip().lower() == "success"


def _format_roa_biz_error(norm: Dict[str, Any]) -> str:
    c = norm.get("code")
    m = (norm.get("message") or "").strip()
    if c and m:
        return f"{c}: {m}"
    if m:
        return m
    if c:
        return str(c)
    try:
        return json.dumps(norm, ensure_ascii=False)[:2000]
    except (TypeError, ValueError):
        return str(norm)[:2000]


def build_sdk_request(
    request_cls: Type[TeaModel],
    request: Optional[Union[TeaModel, Dict[str, Any]]],
) -> Tuple[Optional[TeaModel], Optional[str]]:
    """
    将 ``call_api`` 的 ``request`` 参数规范化为 SDK 的 ``*Request`` 实例。

    Returns:
        ``(req, None)`` 成功；``(None, err_msg)`` 类型不匹配等失败。
    """
    if request is None:
        return request_cls(), None
    if isinstance(request, dict):
        req = request_cls()
        req.from_map(request)
        return req, None
    if isinstance(request, request_cls):
        return request, None
    return (
        None,
        f"请求类型错误：需要 {request_cls.__name__} 或 dict，实际为 {type(request).__name__}",
    )


class SysomOpenAPIClient:
    """
    - ``verify_auth=True``：解析凭证并调用 InitialSysom 校验（与 precheck 一致）。
    - ``verify_auth=False``：仅解析凭证。
    """

    def __init__(
        self,
        *,
        verify_auth: bool = True,
        credentials: Optional[Dict[str, str]] = None,
        endpoint: str = DEFAULT_SYSOM_ENDPOINT,
    ) -> None:
        self._endpoint = endpoint

        if credentials is not None:
            self._credentials = dict(credentials)
            self._auth_method = "显式传入 credentials"
            if verify_auth:
                api_result = test_sysom_api(self._credentials)
                if not api_result["success"]:
                    raise RuntimeError(
                        api_result.get("error", "SysOM API 校验失败")
                        + (
                            f" — {api_result.get('detail', '')}"
                            if api_result.get("detail")
                            else ""
                        )
                    )
        else:
            resolved = resolve_sysom_auth(verify_api=verify_auth)
            if not resolved.get("ok"):
                raise RuntimeError(resolved.get("error", "无法解析 SysOM 凭证"))
            self._credentials = resolved["credentials"]
            self._auth_method = resolved.get("method", "unknown")

        cfg = open_api_models.Config(
            access_key_id=self._credentials["ak_id"],
            access_key_secret=self._credentials["ak_secret"],
            endpoint=self._endpoint,
            user_agent="AlibabaCloud-Agent-Skills/alibabacloud-sysom-diagnosis",
        )
        if self._credentials.get("security_token"):
            cfg.security_token = self._credentials["security_token"]
        cfg.connect_timeout = _CONNECT_TIMEOUT_MS
        self._sdk_client = SysOM20231230Client(cfg)

    @property
    def auth_method(self) -> str:
        return self._auth_method

    async def _call_invoke_diagnosis_roa_raw(
        self,
        request: Union[TeaModel, Dict[str, Any]],
        *,
        return_as: ReturnAs,
    ) -> Tuple[bool, Any, Optional[str]]:
        """经 ``call_api_async`` 取原始 body，避免 PascalCase 导致高层 ``body.to_map()`` 为空。"""
        from alibabacloud_sysom20231230 import models as sysom_models
        from alibabacloud_tea_openapi import utils_models as open_api_util_models
        from alibabacloud_tea_openapi.utils import Utils
        from alibabacloud_tea_util import models as tea_util_models

        if return_as != "dict":
            return False, None, "InvokeDiagnosis 当前仅支持 return_as=dict"

        req, build_err = build_sdk_request(sysom_models.InvokeDiagnosisRequest, request)
        if build_err is not None:
            return False, None, build_err

        body = req.to_map()
        open_req = open_api_util_models.OpenApiRequest(
            headers={},
            body=Utils.parse_to_map(body),
        )
        params = open_api_util_models.Params(
            action="InvokeDiagnosis",
            version="2023-12-30",
            protocol="HTTPS",
            pathname="/api/v1/openapi/diagnosis/invoke_diagnosis",
            method="POST",
            auth_type="AK",
            style="ROA",
            req_body_type="json",
            body_type="json",
        )
        runtime = tea_util_models.RuntimeOptions()
        raw = await self._sdk_client.call_api_async(params, open_req, runtime)
        if not isinstance(raw, dict):
            return False, None, f"invoke_diagnosis 非预期响应类型: {type(raw)!r}"

        status = raw.get("statusCode") or raw.get("status_code")
        inner = raw.get("body") if isinstance(raw.get("body"), dict) else {}
        norm = normalize_sysom_roa_body(inner)

        if status != 200:
            return False, norm, _format_roa_biz_error(norm) if norm else f"HTTP {status}"

        if not _biz_code_success(norm.get("code")):
            return False, norm, _format_roa_biz_error(norm)

        return True, norm, None

    async def _call_get_diagnosis_result_roa_raw(
        self,
        request: Union[TeaModel, Dict[str, Any]],
        *,
        return_as: ReturnAs,
    ) -> Tuple[bool, Any, Optional[str]]:
        from alibabacloud_sysom20231230 import models as sysom_models
        from alibabacloud_tea_openapi import utils_models as open_api_util_models
        from alibabacloud_tea_openapi.utils import Utils
        from alibabacloud_tea_util import models as tea_util_models

        if return_as != "dict":
            return False, None, "GetDiagnosisResult 当前仅支持 return_as=dict"

        req, build_err = build_sdk_request(sysom_models.GetDiagnosisResultRequest, request)
        if build_err is not None:
            return False, None, build_err

        query: Dict[str, str] = {}
        if getattr(req, "task_id", None):
            query["task_id"] = req.task_id
        open_req = open_api_util_models.OpenApiRequest(
            headers={},
            query=Utils.query(query),
        )
        params = open_api_util_models.Params(
            action="GetDiagnosisResult",
            version="2023-12-30",
            protocol="HTTPS",
            pathname="/api/v1/openapi/diagnosis/get_diagnosis_results",
            method="GET",
            auth_type="AK",
            style="ROA",
            req_body_type="json",
            body_type="json",
        )
        runtime = tea_util_models.RuntimeOptions()
        raw = await self._sdk_client.call_api_async(params, open_req, runtime)
        if not isinstance(raw, dict):
            return False, None, f"get_diagnosis_result 非预期响应类型: {type(raw)!r}"

        status = raw.get("statusCode") or raw.get("status_code")
        inner = raw.get("body") if isinstance(raw.get("body"), dict) else {}
        norm = normalize_sysom_roa_body(inner)

        if status != 200:
            return False, norm, _format_roa_biz_error(norm) if norm else f"HTTP {status}"

        if not _biz_code_success(norm.get("code")):
            return False, norm, _format_roa_biz_error(norm)

        return True, norm, None

    async def call_api(
        self,
        api_name: str,
        request: Optional[Union[TeaModel, Dict[str, Any]]] = None,
        *,
        return_as: ReturnAs = "body",
    ) -> Tuple[bool, Any, Optional[str]]:
        action = api_name.strip()
        if action == "InvokeDiagnosis":
            return await self._call_invoke_diagnosis_roa_raw(request, return_as=return_as)
        if action == "GetDiagnosisResult":
            return await self._call_get_diagnosis_result_roa_raw(request, return_as=return_as)

        try:
            request_cls, method = resolve_sysom_async_api(api_name, self._sdk_client)
        except (LookupError, ValueError) as e:
            return False, None, str(e)

        req, build_err = build_sdk_request(request_cls, request)
        if build_err is not None:
            return False, None, build_err

        try:
            response = await method(req)
        except Exception as exc:  # noqa: BLE001
            msg = getattr(exc, "message", None) or str(exc)
            data = getattr(exc, "data", None)
            if isinstance(data, dict) and data.get("Recommend"):
                msg = f"{msg} | 诊断/建议: {data['Recommend']}"
            return False, None, msg

        status_code = getattr(response, "status_code", None)
        body = getattr(response, "body", None)

        if status_code == 200:
            return True, pack_result(response, body, return_as), None

        if body is None:
            err = "未知错误（响应 body 为空）"
        else:
            code, message = getattr(body, "code", None), getattr(body, "message", None)
            # 避免仅缺 message 时退化成 str(body) 不易读；与 diagnosis_helper 抽取逻辑一致
            if code is not None and message is not None:
                err = f"{code}: {message}"
            elif code is not None:
                m = (message or "").strip()
                err = f"{code}: {m}" if m else str(code)
            elif message is not None:
                err = str(message)
            else:
                err = str(body)
        return False, pack_result(response, body, return_as), err


class _LazySysomOpenAPIClient:
    """
    惰性包装：首次访问属性/方法时才构造 ``SysomOpenAPIClient``。
    解决在 Agent/IDE 中多段 Bash 未设置凭证时，导入 diagnosis 子命令即失败的问题。
    """

    __slots__ = ("_inner",)

    def __init__(self) -> None:
        self._inner: Optional[SysomOpenAPIClient] = None

    def _get(self) -> SysomOpenAPIClient:
        if self._inner is None:
            self._inner = SysomOpenAPIClient()
        return self._inner

    def __getattr__(self, name: str) -> Any:
        return getattr(self._get(), name)


sysom_openapi_client = _LazySysomOpenAPIClient()
