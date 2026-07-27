from __future__ import annotations

import os
import re
from collections.abc import Mapping


SKILL_NAME = "alibabacloud-remote-skills-connector"
SESSION_ENV = "SKILL_SESSION_ID"
SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")
USER_AGENT_TEMPLATE = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{{session-id}}"


class ObservabilitySessionError(RuntimeError):
    """Raised before a cloud request when its observability session is unusable."""


def validate_session_id(value: str | None) -> str:
    session_id = (value or "").strip()
    if not SESSION_ID_RE.fullmatch(session_id):
        raise ObservabilitySessionError(
            "SKILL_SESSION_ID must be one 32-character lowercase hexadecimal value "
            "generated once and reused for the current conversation"
        )
    return session_id


def skill_session_id(*, env: Mapping[str, str] | None = None) -> str:
    source = os.environ if env is None else env
    return validate_session_id(source.get(SESSION_ENV))


def build_user_agent(
    client_component: str | None = None,
    *,
    env: Mapping[str, str] | None = None,
) -> str:
    user_agent = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{skill_session_id(env=env)}"
    component = (client_component or "").strip()
    return f"{user_agent} {component}" if component else user_agent
