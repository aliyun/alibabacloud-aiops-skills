from __future__ import annotations

from dataclasses import dataclass

from .config import normalize_agenthub_endpoint


@dataclass(frozen=True)
class ParsedAgentCard:
    interface_url: str
    protocol_version: str
    supports_streaming: bool
    rpc_path: str = "/rpc"


def _trusted_interface_url(url: object, agent_id: str) -> tuple[str, str] | None:
    if not isinstance(url, str):
        return None
    try:
        normalized = normalize_agenthub_endpoint(url, agent_id=agent_id)
    except ValueError:
        return None
    return normalized, "/rpc"


def parse_agent_card(card: object, *, agent_id: str) -> ParsedAgentCard:
    if not isinstance(card, dict):
        raise ValueError("Agent Card must be a JSON object")
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list) or not interfaces:
        raise ValueError("Agent Card has no supported interfaces")
    selected_url = None
    selected_rpc_path = None
    selected_protocol_version = ""
    for interface in interfaces:
        if not isinstance(interface, dict):
            continue
        if interface.get("protocolBinding") != "JSONRPC":
            continue
        trusted = _trusted_interface_url(interface.get("url"), agent_id)
        if trusted is None:
            continue
        selected_url, selected_rpc_path = trusted
        advertised_version = interface.get("protocolVersion")
        if isinstance(advertised_version, str):
            selected_protocol_version = advertised_version
        break
    if selected_url is None:
        raise ValueError("Agent Card has no trusted JSONRPC interface")
    capabilities = card.get("capabilities")
    streaming = (
        isinstance(capabilities, dict)
        and type(capabilities.get("streaming")) is bool
        and capabilities.get("streaming") is True
    )
    return ParsedAgentCard(
        interface_url=selected_url,
        protocol_version=selected_protocol_version,
        supports_streaming=streaming,
        rpc_path=selected_rpc_path or "/rpc",
    )
