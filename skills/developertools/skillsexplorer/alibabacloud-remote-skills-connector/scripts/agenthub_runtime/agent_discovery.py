from __future__ import annotations

import json
from dataclasses import dataclass
from email.utils import formatdate
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

try:
    from scripts.a2a_proxy.references.http_security import secure_urlopen, validate_agent_id
    from scripts.a2a_proxy.references.observability import (
        ObservabilitySessionError,
        build_user_agent,
    )
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.references.http_security import secure_urlopen, validate_agent_id
    from a2a_proxy.references.observability import ObservabilitySessionError, build_user_agent


AGENT_EXPLORER_API_URL = "https://agentexplorer.aliyuncs.com/openapi/for-agent/agents"
DEFAULT_MAX_RESULTS = 5
DEFAULT_TIMEOUT_SEC = 10.0
MAX_RESPONSE_BYTES = 1024 * 1024

FetchJson = Callable[[str, dict[str, str], dict[str, str], float], dict[str, Any]]

class AgentDiscoveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiscoveredSkill:
    name: str
    version: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }


@dataclass(frozen=True)
class DiscoveredAgent:
    agent_id: str
    agent_name: str
    description: str
    keywords: list[str]
    skills: list[DiscoveredSkill]

    def to_dict(self) -> dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "agentName": self.agent_name,
            "description": self.description,
            "keywords": self.keywords,
            "skills": [skill.to_dict() for skill in self.skills],
        }


@dataclass(frozen=True)
class AgentDiscoveryResponse:
    request_id: str
    total_count: int
    max_results: int
    http_status_code: int
    success: bool
    candidates: list[DiscoveredAgent]

    def to_dict(self) -> dict[str, Any]:
        return {
            "requestId": self.request_id,
            "totalCount": self.total_count,
            "maxResults": self.max_results,
            "httpStatusCode": self.http_status_code,
            "success": self.success,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
        }


def discover_agents(
    keyword: str,
    *,
    max_results: int | None = DEFAULT_MAX_RESULTS,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    fetch_json: FetchJson | None = None,
) -> AgentDiscoveryResponse:
    if not isinstance(keyword, str) or not keyword.strip():
        raise AgentDiscoveryError("keyword 不能为空。")
    if "\x00" in keyword:
        raise AgentDiscoveryError("keyword 不能包含 NUL 字符。")
    params = {
        # The managed-input boundary has already validated the UTF-8 payload.
        # Preserve it byte-for-byte rather than silently rewriting user intent.
        "keyword": keyword,
    }
    if max_results is not None:
        if type(max_results) is not int or max_results <= 0:
            raise AgentDiscoveryError("maxResults 必须大于 0。")
        if max_results > DEFAULT_MAX_RESULTS:
            raise AgentDiscoveryError(f"maxResults 不能超过 {DEFAULT_MAX_RESULTS}。")
        params["maxResults"] = str(max_results)
    try:
        user_agent = build_user_agent()
    except ObservabilitySessionError as exc:
        raise AgentDiscoveryError(str(exc)) from exc
    headers = {
        "Date": formatdate(usegmt=True),
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    fetch = fetch_json or _fetch_json
    payload = fetch(AGENT_EXPLORER_API_URL, params, headers, timeout_sec)
    response = parse_agent_discovery_response(
        payload,
        max_candidates=max_results or DEFAULT_MAX_RESULTS,
    )
    if not response.success or response.http_status_code >= 400:
        raise AgentDiscoveryError(
            f"AgentExplorer 查询失败: requestId={response.request_id or '-'} "
            f"httpStatusCode={response.http_status_code}"
        )
    return response


def parse_agent_discovery_response(
    payload: dict[str, Any],
    *,
    max_candidates: int = DEFAULT_MAX_RESULTS,
) -> AgentDiscoveryResponse:
    if type(max_candidates) is not int or not 0 < max_candidates <= DEFAULT_MAX_RESULTS:
        raise AgentDiscoveryError(
            f"本地候选数量上限必须在 1 到 {DEFAULT_MAX_RESULTS} 之间。"
        )
    data = payload.get("data")
    candidates = []
    if isinstance(data, list):
        for item in data:
            if len(candidates) >= max_candidates:
                break
            if isinstance(item, dict):
                candidate = _candidate_from_item(item)
                if candidate:
                    candidates.append(candidate)
    success_value = payload.get("success")
    return AgentDiscoveryResponse(
        request_id=_string(payload.get("requestId")),
        total_count=_int(payload.get("totalCount")),
        max_results=_int(payload.get("maxResults")),
        http_status_code=_int(payload.get("httpStatusCode")),
        success=success_value if type(success_value) is bool else False,
        candidates=candidates,
    )


def _candidate_from_item(item: dict[str, Any]) -> DiscoveredAgent | None:
    agent_id = _string(item.get("agentCode"))
    if not agent_id:
        return None
    try:
        agent_id = validate_agent_id(agent_id)
    except ValueError:
        return None
    return DiscoveredAgent(
        agent_id=agent_id,
        agent_name=_string(item.get("agentName")),
        description=_string(item.get("description")),
        keywords=_keywords(item.get("keywords")),
        skills=_skills(item.get("skills")),
    )


def _skills(raw: Any) -> list[DiscoveredSkill]:
    if not isinstance(raw, list):
        return []
    skills = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = _string(item.get("name"))
        if not name:
            continue
        skills.append(
            DiscoveredSkill(
                name=name,
                version=_string(item.get("version")),
                description=_string(item.get("description")),
            )
        )
    return skills


def _keywords(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [_string(value) for value in raw if _string(value)]
    text = _string(raw)
    if not text:
        return []
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        return [text]
    if isinstance(decoded, list):
        return [_string(value) for value in decoded if _string(value)]
    return [text]


def _fetch_json(
    url: str,
    params: dict[str, str],
    headers: dict[str, str],
    timeout_sec: float,
) -> dict[str, Any]:
    separator = "&" if "?" in url else "?"
    request_url = f"{url}{separator}{urlencode(params)}"
    request = Request(request_url, headers=headers, method="GET")
    try:
        with secure_urlopen(request, timeout=timeout_sec) as response:
            body_bytes = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body_bytes) > MAX_RESPONSE_BYTES:
                raise AgentDiscoveryError("AgentExplorer 响应超过本地 1 MiB 上限。")
            body = body_bytes.decode("utf-8")
    except HTTPError as exc:
        raise AgentDiscoveryError(f"AgentExplorer HTTP 错误: {exc.code}") from exc
    except URLError as exc:
        raise AgentDiscoveryError(f"AgentExplorer 网络错误: {exc.reason}") from exc
    except TimeoutError as exc:
        raise AgentDiscoveryError("AgentExplorer 查询超时。") from exc
    except UnicodeDecodeError as exc:
        raise AgentDiscoveryError("AgentExplorer 返回内容不是合法 UTF-8。") from exc
    try:
        decoded = json.loads(body)
    except json.JSONDecodeError as exc:
        raise AgentDiscoveryError("AgentExplorer 返回内容不是合法 JSON。") from exc
    if not isinstance(decoded, dict):
        raise AgentDiscoveryError("AgentExplorer 返回 JSON 不是对象。")
    return decoded


def _string(value: Any) -> str:
    return str(value or "").strip()


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
