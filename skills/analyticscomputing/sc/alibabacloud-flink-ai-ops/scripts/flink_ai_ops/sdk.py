"""Official SDK adapter with explicit deadlines and non-replaying writes."""

import asyncio
import json
import math
import re
import time

from .client import DEFAULT_CONNECT_TIMEOUT, create_client, runtime_options
from .common import OpsError, positive_number
from .sse import SDKStreamResources, finish_stream


_OPERATIONS = {
    "ChatAiAgent": ("POST", "advisor", "ai-agent/stream/agent/v2/chat"),
    "GetPatrolConfig": ("GET", "autopilot", "patrol-config"),
    "ListPatrolReports": ("GET", "autopilot", "patrol-reports"),
    "GetPatrolReportDetail": ("GET", "autopilot", "patrol-reports/details"),
    "TriggerPatrol": ("POST", "autopilot", "patrol-reports/trigger"),
    "UpdatePatrolConfig": ("PATCH", "autopilot", "patrol-config"),
}


def _exception_chain(error):
    pending = [error]
    seen = set()
    chain = []
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        chain.append(current)
        pending.extend(e for e in (getattr(current, "inner_exception", None), current.__cause__) if isinstance(e, Exception))
    return chain


def _failure(error):
    chain = _exception_chain(error)
    for current in chain:
        if isinstance(current, OpsError):
            return current
    if any(type(current).__name__ == "CredentialException" for current in chain):
        return OpsError(
            "MissingCredentials",
            "Cannot obtain credentials from the Alibaba Cloud default credential chain. Configure them"
            " in the terminal that starts the execution process:\n"
            "export ALIBABA_CLOUD_ACCESS_KEY_ID='***REDACTED***'\n"
            "export ALIBABA_CLOUD_ACCESS_KEY_SECRET='***REDACTED***'\n"
            "Required only for STS temporary credentials:\n"
            "export ALIBABA_CLOUD_SECURITY_TOKEN='***REDACTED***'\n"
            "The values above are redacted placeholders to be replaced locally by the user. A local"
            " credential file, a RAM role, or an OIDC role also works. Make sure the process inherits"
            " the configuration, and never provide secrets in chat or in the repository."
            " Reference: https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials ."
            f" Original error: {error}",
        )
    source = next((current for current in reversed(chain) if getattr(current, "code", None)), chain[-1])
    code = getattr(source, "code", None) or type(source).__name__
    request_id = getattr(source, "request_id", "") or ""
    data = getattr(source, "data", None)
    if isinstance(data, dict):
        request_id = request_id or data.get("RequestId", data.get("requestId", ""))
    return OpsError(str(code), str(source), request_id, data)


def _transient(error):
    chain = _exception_chain(error)
    if any(type(current).__name__ == "CredentialException" for current in chain):
        return False
    for current in chain:
        code = str(getattr(current, "code", "")).lower()
        status = getattr(current, "status_code", getattr(current, "statusCode", None))
        if isinstance(current, (TimeoutError, ConnectionError, OSError)) or any(
            marker in (code + type(current).__name__.lower())
            for marker in ("timeout", "throttl", "serviceunavailable", "internalerror", "internalservererror", "connectionerror", "retryerror")
        ) or status in (429, 500, 502, 503, 504):
            return True
    return False


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("SSE data contains a non-finite number.")
    return number


class ApiClient:
    """Bind every request to one explicit workspace, namespace and region."""

    def __init__(self, region, workspace, namespace, connect_timeout=DEFAULT_CONNECT_TIMEOUT,
                 read_timeout=None):
        if not isinstance(region, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", region):
            raise OpsError("ValidationError", "region_id must be a real Alibaba Cloud region identifier.")
        for name, value in (("workspace", workspace), ("namespace", namespace)):
            if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 for c in value):
                raise OpsError("ValidationError", f"{name} must be a non-empty real value.")
        self.connect_timeout = positive_number(connect_timeout, "connect_timeout")
        self.read_timeout = None if read_timeout is None else positive_number(read_timeout, "read_timeout")
        self.workspace = workspace
        self.namespace = namespace
        self.last_request_id = ""
        try:
            self.client = create_client(region)
        except ImportError as error:
            raise OpsError("DependencyError", "Install assets/requirements.txt in the virtual environment." + str(error)) from error
        except Exception as error:
            raise _failure(error) from error

    def _prepare_request(self, action, parameters=None, body=None):
        """Build JSON and SSE requests with the same SDK models and context."""
        from alibabacloud_tea_openapi import utils_models
        from alibabacloud_tea_openapi.utils import Utils
        from alibabacloud_ververica20220718 import models
        from darabonba.url import Url

        method, area, resource = _OPERATIONS[action]
        values = parameters if method == "GET" else body
        model = getattr(models, action + "Request")().from_map(values or {})
        model.validate()
        serialized = model.to_map()
        params = utils_models.Params(
            action=action, version="2022-07-18", protocol="HTTPS",
            pathname=f"/{area}/v2/namespaces/{Url.percent_encode(self.namespace)}/{resource}",
            method=method, auth_type="AK", style="ROA", req_body_type="json", body_type="json",
        )
        request = utils_models.OpenApiRequest(
            headers={"workspace": self.workspace},
            query=Utils.query(serialized) if method == "GET" else None,
            body=serialized if method != "GET" else None,
        )
        return params, request

    def request(self, action, parameters=None, body=None, timeout=None):
        """Return a validated business response; retry temporary read errors once."""
        self.last_request_id = ""
        if action not in _OPERATIONS or action == "ChatAiAgent":
            raise OpsError("ValidationError", "Unsupported API: " + action)
        if timeout is not None:
            positive_number(timeout, "timeout")
        deadline = time.monotonic() + timeout if timeout is not None else None
        params, request = self._prepare_request(action, parameters, body)
        attempts = 2 if params.method == "GET" else 1
        for attempt in range(attempts):
            remaining = deadline - time.monotonic() if deadline is not None else None
            if remaining is not None and remaining <= 0:
                raise OpsError("Timeout", "Request exceeded the total time limit.", self.last_request_id)
            try:
                async def invoke():
                    runtime = runtime_options(self.connect_timeout, self.read_timeout, remaining)
                    call = self.client.call_api_async(params, request, runtime)
                    return await asyncio.wait_for(call, timeout=remaining) if remaining is not None else await call

                response = asyncio.run(invoke())
                response_headers = response.get("headers") or {}
                payload = response.get("body")
                if not isinstance(payload, dict):
                    raise OpsError("InvalidResponse", "The API response body must be a JSON object.",
                                   response_headers.get("x-acs-request-id", ""), response)
                self.last_request_id = payload.get("requestId") or response_headers.get("x-acs-request-id", "")
                if payload.get("success") is not True:
                    raise OpsError(
                        payload.get("errorCode") or "BusinessError",
                        payload.get("errorMessage") or "The API did not return an explicit business success result.",
                        self.last_request_id, payload,
                    )
                return payload
            except Exception as error:
                if attempt + 1 == attempts or isinstance(error, OpsError) or not _transient(error):
                    if isinstance(error, OpsError):
                        raise
                    raise _failure(error) from error
                remaining = deadline - time.monotonic() if deadline is not None else 1
                if remaining > 0:
                    time.sleep(min(1, remaining))
        raise AssertionError("unreachable")

    async def chat(self, body):
        """Use SDK signing and raw SSE data to retain future response fields."""
        self.last_request_id = ""
        params, wire_request = self._prepare_request("ChatAiAgent", body=body)
        resources = SDKStreamResources()
        runtime = runtime_options(self.connect_timeout, self.read_timeout, for_chat=True)
        stream = resources.open(self.client, params, wire_request, runtime)
        primary = None
        try:
            async for response in stream:
                response_headers = response.headers or {}
                self.last_request_id = response_headers.get("x-acs-request-id", self.last_request_id)
                event = response.event
                if event is None or event.data is None:
                    continue
                try:
                    event_body = json.loads(event.data, parse_float=_finite_float, parse_constant=_finite_float)
                    if not isinstance(event_body, dict):
                        raise ValueError("SSE data must be a JSON object.")
                except ValueError as error:
                    raise OpsError("InvalidResponse", "Invalid assistant SSE data: " + str(error), self.last_request_id,
                                   {"id": event.id, "event": event.event, "rawData": event.data}) from error
                yield {
                    "id": event.id, "event": event.event, "body": event_body,
                }
        except BaseException as error:
            primary = error
            if isinstance(error, Exception) and not isinstance(error, OpsError):
                primary = _failure(error)
            if isinstance(primary, OpsError) and not primary.request_id:
                primary.request_id = resources.request_id
            if primary is not error:
                raise primary from error
            raise
        finally:
            self.last_request_id = resources.request_id or self.last_request_id
            await finish_stream(stream, resources, primary=primary,
                                request_id=self.last_request_id)
