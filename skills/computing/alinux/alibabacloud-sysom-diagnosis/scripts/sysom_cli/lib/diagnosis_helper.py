"""诊断 Helper：参数模型、调用 InvokeDiagnosis / 轮询 GetDiagnosisResult。

仅依赖 ``openapi_client.SysomOpenAPIClient``，无额外 Helper 基类。
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field
from Tea.model import TeaModel

from .openapi_client import SysomOpenAPIClient, sysom_openapi_client

__all__ = [
    "DiagnoseResultCode",
    "DiagnosisRequest",
    "DiagnosisResponse",
]

class DiagnoseResultCode:
    """诊断结果状态码常量"""

    SUCCESS = "Success"
    TASK_CREATE_FAILED = "TaskCreateFailed"
    TASK_EXECUTE_FAILED = "TaskExecuteFailed"
    TASK_TIMEOUT = "TaskTimeout"
    RESULT_PARSE_FAILED = "ResultParseFailed"
    GET_RESULT_FAILED = "GetResultFailed"


class DiagnosisRequest(BaseModel):
    """诊断请求参数。"""

    service_name: str = Field(..., description="诊断服务名称")
    channel: str = Field(..., description="诊断通道")
    region: str = Field(..., description="地域")
    params: Dict[str, Any] = Field(default_factory=dict, description="诊断参数")


class DiagnosisResponse(BaseModel):
    """诊断响应（含通用 code / message，等价于原 OpenAPIResponse + 诊断字段）。"""

    code: str = Field(..., description="业务状态码")
    message: str = Field(default="", description="说明")
    task_id: str = Field(default="", description="任务ID")
    result: Dict[str, Any] = Field(default_factory=dict, description="诊断结果")
    # InvokeDiagnosis 失败时由客户端填入，便于 JSON 透传服务端原始信息
    api_business_code: str = Field(default="", description="InvokeDiagnosis 响应体中的业务 code")
    api_request_id: str = Field(default="", description="InvokeDiagnosis 响应体中的 request_id")


def _normalize_map(obj: Any) -> Any:
    """递归将 TeaModel / 嵌套结构转为可序列化 dict。"""
    if obj is None:
        return None
    if isinstance(obj, TeaModel):
        return _normalize_map(obj.to_map())
    if isinstance(obj, dict):
        return {k: _normalize_map(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize_map(x) for x in obj]
    return obj


def _extract_invoke_failure_message(norm: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    从 InvokeDiagnosis 响应体提取可读错误与原始 code / request_id。

    Returns:
        (message, api_business_code, request_id)
    """
    if not norm:
        return ("", "", "")

    req_id = str(
        norm.get("request_id")
        or norm.get("RequestId")
        or norm.get("requestId")
        or ""
    ).strip()

    biz = str(norm.get("code") or norm.get("Code") or "").strip()
    msg = str(norm.get("message") or norm.get("Message") or "").strip()

    data = norm.get("data")
    if isinstance(data, dict):
        msg = msg or str(data.get("message") or data.get("Message") or "").strip()
        biz = biz or str(data.get("code") or data.get("Code") or "").strip()

    recommend = norm.get("Recommend") or norm.get("recommend")
    if not msg and recommend:
        msg = str(recommend).strip()

    parts: list[str] = []
    if biz and msg:
        parts.append(f"{biz}: {msg}")
    elif msg:
        parts.append(msg)
    elif biz:
        parts.append(f"业务错误（code={biz}），服务端未返回 message 字段")

    if not parts:
        try:
            parts.append(json.dumps(norm, ensure_ascii=False)[:2000])
        except (TypeError, ValueError):
            parts.append(str(norm)[:2000])

    return ("; ".join(parts), biz, req_id)


_GET_DIAGNOSIS_META_KEYS = frozenset(
    {
        "task_id",
        "TaskId",
        "status",
        "Status",
        "err_msg",
        "ErrMsg",
        "message",
        "Message",
        "request_id",
        "RequestId",
        "code",
        "Code",
    }
)


def _extract_get_diagnosis_result_payload(data: Dict[str, Any]) -> Any:
    """
    从 GetDiagnosisResult 返回的 data 中提取业务载荷。
    兼容 result/Result、以及载荷落在兄弟字段（无标准 result）的情况。
    """
    if not isinstance(data, dict):
        return None

    def _nonempty(x: Any) -> bool:
        if x is None or x == "":
            return False
        if isinstance(x, dict) and not x:
            return False
        if isinstance(x, list) and not x:
            return False
        return True

    r = data.get("result")
    if _nonempty(r):
        return r
    R = data.get("Result")
    if _nonempty(R):
        return R
    for k in (
        "diagnosis_result",
        "DiagnosisResult",
        "output",
        "Output",
        "report",
        "Report",
        "diagnosis_data",
        "DiagnosisData",
    ):
        v = data.get(k)
        if _nonempty(v):
            return v

    rest = {k: v for k, v in data.items() if k not in _GET_DIAGNOSIS_META_KEYS}
    if len(rest) == 1:
        only = next(iter(rest.values()))
        if _nonempty(only):
            return only
    if len(rest) > 1:
        return rest
    return None


def _response_data_to_dict(response_data: Any) -> Dict[str, Any]:
    """将 ``call_api`` 返回值统一为 dict（TeaModel / dict）。"""
    if response_data is None:
        return {}
    if isinstance(response_data, dict):
        return response_data
    if isinstance(response_data, TeaModel):
        return response_data.to_map()
    return {}


class DiagnosisMCPHelper:
    """诊断流程封装：发起任务并轮询结果。"""

    def __init__(
        self,
        client: Optional[SysomOpenAPIClient] = None,
        *,
        timeout: int = 150,
        poll_interval: int = 1,
    ) -> None:
        self.client: SysomOpenAPIClient = client or sysom_openapi_client
        self.timeout = timeout
        self.poll_interval = poll_interval

    async def execute(self, request: DiagnosisRequest) -> DiagnosisResponse:
        params_json = json.dumps(request.params, ensure_ascii=False)
        invoke_request: Dict[str, Any] = {
            "service_name": request.service_name,
            "channel": request.channel,
            "params": params_json,
        }

        success, response_data, error_msg = await self.client.call_api(
            "InvokeDiagnosis",
            invoke_request,
            return_as="dict",
        )

        if not success:
            raw = _normalize_map(_response_data_to_dict(response_data))
            detail, biz, rid = _extract_invoke_failure_message(raw if isinstance(raw, dict) else {})
            combined = (error_msg or "").strip()
            if detail:
                if combined and detail not in combined and combined not in detail:
                    combined = f"{combined}; {detail}"
                elif not combined:
                    combined = detail
            if not combined:
                combined = "发起诊断失败（未收到服务端错误详情，请检查网络与 endpoint）"
            return DiagnosisResponse(
                code=DiagnoseResultCode.TASK_CREATE_FAILED,
                message=combined,
                task_id="",
                api_business_code=biz,
                api_request_id=rid,
                result={},
            )

        data_map = _normalize_map(_response_data_to_dict(response_data))
        if not isinstance(data_map, dict):
            data_map = {}

        data_inner = data_map.get("data") or {}
        if isinstance(data_inner, TeaModel):
            data_inner = data_inner.to_map()
        if not isinstance(data_inner, dict):
            data_inner = {}
        task_id = str(data_inner.get("task_id") or "").strip()

        biz_code = str(data_map.get("code") or "").strip()
        ok_invoke = biz_code.lower() == "success" or (not biz_code and bool(task_id))
        if not ok_invoke:
            detail, biz, rid = _extract_invoke_failure_message(data_map)
            if not detail:
                detail = "发起诊断失败（服务端未返回可解析的错误信息）"
            return DiagnosisResponse(
                code=DiagnoseResultCode.TASK_CREATE_FAILED,
                message=detail,
                task_id="",
                api_business_code=biz or biz_code,
                api_request_id=rid,
                result={},
            )

        if not task_id:
            detail, biz, rid = _extract_invoke_failure_message(data_map)
            return DiagnosisResponse(
                code=DiagnoseResultCode.TASK_CREATE_FAILED,
                message=detail or "InvokeDiagnosis 未返回 task_id",
                task_id="",
                api_business_code=biz or biz_code,
                api_request_id=rid,
                result={},
            )

        code, message, result = await self._wait_for_result(task_id)

        if code == DiagnoseResultCode.SUCCESS:
            if isinstance(result, str):
                try:
                    result_dict = json.loads(result)
                except (json.JSONDecodeError, TypeError) as e:
                    return DiagnosisResponse(
                        task_id=task_id,
                        code=DiagnoseResultCode.RESULT_PARSE_FAILED,
                        message=f"结果解析失败：{str(e)}，原始结果：{result[:200]}",
                        result={"raw": result},
                    )
            elif isinstance(result, dict):
                result_dict = result
            else:
                return DiagnosisResponse(
                    task_id=task_id,
                    code=DiagnoseResultCode.RESULT_PARSE_FAILED,
                    message=f"结果类型异常：{type(result)}，期望字符串或字典",
                    result={"raw": str(result)},
                )

            return DiagnosisResponse(
                task_id=task_id,
                code=DiagnoseResultCode.SUCCESS,
                result=result_dict,
            )

        return DiagnosisResponse(task_id=task_id, code=code, message=message)

    async def _wait_for_result(self, task_id: str) -> Tuple[str, str, Any]:
        loop = asyncio.get_running_loop()
        start_time = loop.time()

        while (loop.time() - start_time) < self.timeout:
            success, response_data, error_msg = await self.client.call_api(
                "GetDiagnosisResult",
                {"task_id": task_id},
                return_as="dict",
            )

            if not success:
                return DiagnoseResultCode.GET_RESULT_FAILED, error_msg or "获取结果失败", None

            response_data = _response_data_to_dict(response_data)

            if str(response_data.get("code") or "").strip().lower() == "success":
                data = response_data.get("data") or {}
                task_status = str(data.get("status") or "").strip().lower()
                if task_status == "fail":
                    return (
                        DiagnoseResultCode.TASK_EXECUTE_FAILED,
                        data.get("err_msg", "任务执行失败"),
                        None,
                    )
                if task_status == "success":
                    payload = _extract_get_diagnosis_result_payload(data)
                    if payload is None:
                        payload = {
                            "_sysom_cli_note_zh": (
                                "GetDiagnosisResult 标记成功但未解析到业务 result；"
                                "请对照控制台或原始 API。以下为 data 中非元数据字段。"
                            ),
                            "task_id": task_id,
                            "_raw_data_keys": sorted(data.keys()),
                        }
                    return DiagnoseResultCode.SUCCESS, "", payload
                await asyncio.sleep(self.poll_interval)
            else:
                return (
                    DiagnoseResultCode.GET_RESULT_FAILED,
                    response_data.get("message", "获取结果失败"),
                    None,
                )

        return (
            DiagnoseResultCode.TASK_TIMEOUT,
            f"诊断执行超时（{self.timeout}秒），task_id: {task_id}",
            None,
        )
