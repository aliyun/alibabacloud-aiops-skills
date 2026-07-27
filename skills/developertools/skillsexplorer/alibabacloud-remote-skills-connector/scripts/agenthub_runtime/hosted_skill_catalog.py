from __future__ import annotations

import http.client
import json
import math
import ssl
from dataclasses import dataclass
from email.utils import formatdate
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request

try:
    from scripts.a2a_proxy.references.http_security import secure_urlopen
    from scripts.a2a_proxy.references.observability import (
        ObservabilitySessionError,
        build_user_agent,
    )
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.references.http_security import secure_urlopen
    from a2a_proxy.references.observability import (
        ObservabilitySessionError,
        build_user_agent,
    )


HOSTED_SKILLS_API_URL = "https://skills.aliyun.com/openapi/skills"
DEFAULT_TIMEOUT_SEC = 10.0
MAX_RESULTS = 100
MAX_PAGES = 100
MAX_RESPONSE_BYTES = 1024 * 1024

FetchJson = Callable[[str, dict[str, str], dict[str, str], float], dict[str, Any]]


class HostedSkillCatalogError(RuntimeError):
    pass


@dataclass(frozen=True)
class HostedSkill:
    skill_name: str
    display_name: str
    description: str
    category_name: str
    sub_category_name: str
    name_en: str
    description_en: str

    def to_dict(self) -> dict[str, str]:
        return {
            "skillName": self.skill_name,
            "displayName": self.display_name,
            "description": self.description,
            "categoryName": self.category_name,
            "subCategoryName": self.sub_category_name,
            "nameEn": self.name_en,
            "descriptionEn": self.description_en,
        }


@dataclass(frozen=True)
class HostedSkillCatalog:
    total_catalog_count: int
    skills: tuple[HostedSkill, ...]

    @property
    def hosted_count(self) -> int:
        return len(self.skills)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostedOnly": True,
            "totalCatalogCount": self.total_catalog_count,
            "hostedCount": self.hosted_count,
            "skills": [skill.to_dict() for skill in self.skills],
        }


HostedSkillCatalogResponse = HostedSkillCatalog


def list_hosted_skills(
    *,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    fetch_json: FetchJson | None = None,
) -> HostedSkillCatalog:
    timeout = _positive_timeout(timeout_sec)
    try:
        user_agent = build_user_agent()
    except ObservabilitySessionError as exc:
        raise HostedSkillCatalogError(str(exc)) from exc

    headers = {
        "Date": formatdate(usegmt=True),
        "User-Agent": user_agent,
        "Accept": "application/json",
    }
    fetch = fetch_json or _fetch_json
    next_token: str | None = None
    seen_tokens: set[str] = set()
    total_catalog_count = 0
    skills_by_name: dict[str, HostedSkill] = {}

    for page_number in range(1, MAX_PAGES + 1):
        params = {"maxResults": str(MAX_RESULTS)}
        if next_token is not None:
            params["nextToken"] = next_token
        payload = fetch(HOSTED_SKILLS_API_URL, params, headers, timeout)
        if not isinstance(payload, dict):
            raise HostedSkillCatalogError("托管技能目录返回的 JSON 必须是对象。")
        if payload.get("success") is not True:
            raise HostedSkillCatalogError("托管技能目录请求未返回 success=true。")
        data = payload.get("data")
        if not isinstance(data, list):
            raise HostedSkillCatalogError("托管技能目录返回的 data 必须是列表。")

        if "totalCount" not in payload:
            raise HostedSkillCatalogError("托管技能目录返回内容缺少 totalCount。")
        page_total = payload["totalCount"]
        if type(page_total) is not int or page_total < 0:
            raise HostedSkillCatalogError(
                "托管技能目录返回的 totalCount 必须是非负整数。"
            )
        total_catalog_count = max(total_catalog_count, page_total)

        for item in data:
            if not isinstance(item, dict) or item.get("hosted") is not True:
                continue
            skill = _normalize_skill(item)
            existing = skills_by_name.get(skill.skill_name)
            if existing is None:
                skills_by_name[skill.skill_name] = skill
            elif existing != skill:
                raise HostedSkillCatalogError(
                    "托管技能目录包含互相冲突的重复 skillName。"
                )

        raw_next_token = payload.get("nextToken")
        if raw_next_token is None or raw_next_token == "":
            break
        if not isinstance(raw_next_token, str):
            raise HostedSkillCatalogError("托管技能目录返回的 nextToken 必须是字符串。")
        if raw_next_token in seen_tokens:
            raise HostedSkillCatalogError("托管技能目录返回了重复的 nextToken。")
        if page_number == MAX_PAGES:
            raise HostedSkillCatalogError("托管技能目录分页超过本地 100 页上限。")
        seen_tokens.add(raw_next_token)
        next_token = raw_next_token

    skills = tuple(
        sorted(
            skills_by_name.values(),
            key=lambda skill: (
                skill.category_name,
                skill.sub_category_name,
                skill.display_name,
                skill.skill_name,
            ),
        )
    )
    return HostedSkillCatalog(
        total_catalog_count=total_catalog_count,
        skills=skills,
    )


def _normalize_skill(item: dict[str, Any]) -> HostedSkill:
    skill_name = _text(item.get("skillName"))
    if not skill_name:
        raise HostedSkillCatalogError("托管技能记录缺少必需的 skillName。")
    name_en = _text(item.get("nameEn"))
    description_en = _text(item.get("descriptionEn"))
    display_name = _text(item.get("displayName")) or name_en or skill_name
    description = _text(item.get("description")) or description_en
    return HostedSkill(
        skill_name=skill_name,
        display_name=display_name,
        description=description,
        category_name=_text(item.get("categoryName")),
        sub_category_name=_text(item.get("subCategoryName")),
        name_en=name_en,
        description_en=description_en,
    )


def _positive_timeout(value: Any) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value <= 0
    ):
        raise HostedSkillCatalogError("timeout_sec 必须是大于 0 的有限数字。")
    return float(value)


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
            if not isinstance(body_bytes, (bytes, bytearray)):
                raise HostedSkillCatalogError("托管技能目录返回的 HTTP 内容不是字节数据。")
            if len(body_bytes) > MAX_RESPONSE_BYTES:
                raise HostedSkillCatalogError("托管技能目录响应超过本地 1 MiB 上限。")
            body = bytes(body_bytes).decode("utf-8")
    except HTTPError as exc:
        raise HostedSkillCatalogError(f"托管技能目录 HTTP 请求失败: {exc.code}。") from exc
    except URLError as exc:
        raise HostedSkillCatalogError(
            "托管技能目录网络请求失败；请检查网络连接后重试。"
        ) from exc
    except TimeoutError as exc:
        raise HostedSkillCatalogError("托管技能目录请求超时；请稍后重试。") from exc
    except UnicodeDecodeError as exc:
        raise HostedSkillCatalogError("托管技能目录返回内容不是合法 UTF-8。") from exc
    except ssl.SSLError as exc:
        raise HostedSkillCatalogError(
            "托管技能目录 TLS 连接失败；请检查本地 TLS 配置后重试。"
        ) from exc
    except http.client.HTTPException as exc:
        raise HostedSkillCatalogError(
            "托管技能目录 HTTP 协议响应无效；请稍后重试。"
        ) from exc
    except OSError as exc:
        raise HostedSkillCatalogError(
            "托管技能目录网络 I/O 失败；请检查本地网络环境后重试。"
        ) from exc

    try:
        decoded = json.loads(body, parse_constant=_reject_json_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise HostedSkillCatalogError("托管技能目录返回内容不是合法 JSON。") from exc
    if not isinstance(decoded, dict):
        raise HostedSkillCatalogError("托管技能目录返回的 JSON 必须是对象。")
    return decoded


def _text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")
