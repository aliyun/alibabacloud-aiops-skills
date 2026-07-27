from pathlib import Path

try:
    from scripts.a2a_proxy.references.http_security import (
        normalize_official_agenthub_endpoint as normalize_agenthub_endpoint,
        expected_agenthub_host,
        validate_agent_id,
    )
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.references.http_security import (
        normalize_official_agenthub_endpoint as normalize_agenthub_endpoint,
        expected_agenthub_host,
        validate_agent_id,
    )


DEFAULT_AGENTHUB_HOST_SUFFIX = "cn-beijing.agenthub.aliyuncs.com"
ALIYUN_AGENTHUB_OAUTH_PROFILE = "aliyun_agenthub_oauth"
ALIYUN_AGENTHUB_LEGACY_AK_PROFILE = "aliyun_agenthub"
PROFILE_AUTO_SELECTOR = "__auto__"
AGENTHUB_PRIVATE_PROFILE_CANDIDATES = (
    ALIYUN_AGENTHUB_LEGACY_AK_PROFILE,
    ALIYUN_AGENTHUB_OAUTH_PROFILE,
)


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_vendor_proxy_script() -> Path:
    return skill_root() / "scripts" / "a2a_proxy" / "a2a_operations.py"


def endpoint_for_agent_id(agent_id: str) -> str:
    normalized = validate_agent_id(agent_id)
    return f"https://{expected_agenthub_host(normalized)}"
