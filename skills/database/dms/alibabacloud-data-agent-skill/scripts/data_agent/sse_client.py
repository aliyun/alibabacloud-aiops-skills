"""SSE (Server-Sent Events) streaming client for Data Agent.

Author: Tinker
Created: 2026-03-01
"""

from __future__ import annotations

import json
import hashlib
import hmac
import base64
import ssl
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode, quote
from typing import Iterator, Optional, Dict, Any, AsyncIterator
from dataclasses import dataclass

import requests
import aiohttp

from data_agent.config import DataAgentConfig


@dataclass
class SSEEvent:
    """Represents a single SSE event."""

    event_type: str
    data: Dict[str, Any]
    checkpoint: Optional[int] = None
    category: Optional[str] = None
    content: Optional[str] = None
    content_type: Optional[str] = None  # "json" or "str"


class AliyunSignerV3:
    """Signs requests for Alibaba Cloud OpenAPI using Signature Version 3."""

    # SHA256 hash of empty string
    EMPTY_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    @staticmethod
    def _sha256_hex(data: str) -> str:
        """Calculate SHA256 hash and return hex string."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def _hmac_sha256(key: bytes, data: str) -> bytes:
        """Calculate HMAC-SHA256."""
        return hmac.new(key, data.encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def sign(
        access_key_id: str,
        access_key_secret: str,
        method: str,
        host: str,
        action: str,
        params: Dict[str, str],
        body: str = "",
        security_token: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generate signed headers for Alibaba Cloud API V3.

        Args:
            access_key_id: Access Key ID.
            access_key_secret: Access Key Secret.
            method: HTTP method (GET/POST).
            host: API host.
            action: API action name.
            params: Request parameters.
            body: Request body (empty for GET requests).
            security_token: STS Security Token (optional).

        Returns:
            Headers dict with authorization.
        """
        # Timestamp in ISO 8601 format
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        nonce = str(uuid.uuid4())

        # Hash the request body (empty string hash for no body)
        hashed_payload = AliyunSignerV3._sha256_hex(body) if body else AliyunSignerV3.EMPTY_HASH

        # Build canonical request
        http_method = method.upper()
        canonical_uri = "/"

        # Query string (sorted)
        query_params = {"Action": action, "Version": "2025-04-14", **params}
        sorted_query = sorted(query_params.items())
        canonical_query_string = "&".join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}" for k, v in sorted_query
        )

        # Headers to sign
        headers_to_sign = {
            "host": host,
            "x-acs-action": action,
            "x-acs-content-sha256": hashed_payload,
            "x-acs-date": timestamp,
            "x-acs-signature-nonce": nonce,
            "x-acs-version": "2025-04-14",
        }

        # Add security token to headers if provided
        if security_token:
            headers_to_sign["x-acs-security-token"] = security_token

        # Canonical headers (sorted, lowercase)
        sorted_headers = sorted(headers_to_sign.items())
        canonical_headers = "\n".join(f"{k}:{v}" for k, v in sorted_headers) + "\n"
        signed_headers = ";".join(k for k, _ in sorted_headers)

        # Build canonical request string
        canonical_request = (
            f"{http_method}\n"
            f"{canonical_uri}\n"
            f"{canonical_query_string}\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_payload}"
        )

        # Hash the canonical request
        hashed_canonical_request = AliyunSignerV3._sha256_hex(canonical_request)

        # String to sign
        algorithm = "ACS3-HMAC-SHA256"
        string_to_sign = f"{algorithm}\n{hashed_canonical_request}"

        # Calculate signature
        signature = hmac.new(
            access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        # Build authorization header
        authorization = (
            f"{algorithm} Credential={access_key_id},"
            f"SignedHeaders={signed_headers},"
            f"Signature={signature}"
        )

        result = {
            "Authorization": authorization,
            "Host": host,
            "x-acs-action": action,
            "x-acs-content-sha256": hashed_payload,
            "x-acs-date": timestamp,
            "x-acs-signature-nonce": nonce,
            "x-acs-version": "2025-04-14",
            "Accept": "text/event-stream",
        }

        # Add security token to result headers if provided
        if security_token:
            result["x-acs-security-token"] = security_token

        return result


# Keep old signer for backward compatibility
AliyunSigner = AliyunSignerV3


class SSEClient:
    """Client for handling SSE streaming responses from Data Agent."""

    def __init__(self, config: DataAgentConfig):
        """Initialize SSE client.

        Args:
            config: Data Agent configuration.
        """
        self._config = config
        self._base_url = f"https://{config.endpoint}"

    def _do_stream(
        self,
        agent_id: str,
        session_id: str,
        timeout: int,
        checkpoint: Optional[int] = None,
    ) -> Iterator[SSEEvent]:
        """Single-connection streaming attempt."""
        # Check authentication type
        if hasattr(self._config, 'api_key') and self._config.api_key:
            # API_KEY authentication
            return self._do_stream_with_api_key(agent_id, session_id, timeout, checkpoint)
        else:
            # AK/SK authentication via default credential chain
            return self._do_stream_with_ak_sk(agent_id, session_id, timeout, checkpoint)

    def _do_stream_with_api_key(
        self,
        agent_id: str,
        session_id: str,
        timeout: int,
        checkpoint: Optional[int] = None,
    ) -> Iterator[SSEEvent]:
        """Stream with API_KEY authentication."""
        # Determine endpoint based on action type (GetChatContent is a data plane API)
        base_endpoint = f"dataagent-stream-{self._config.region}.aliyuncs.com/apikey"
        url = f"https://{base_endpoint}"

        # Build request body
        body = {
            'Action': 'GetChatContent',
            'Version': '2025-04-14',
            'RegionId': self._config.region,
            'AgentId': agent_id,
            'SessionId': session_id,
        }
        if checkpoint is not None:
            body['Checkpoint'] = str(checkpoint)

        # Set up headers with API_KEY
        headers = {
            'x-api-key': self._config.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'AlibabaCloud-Agent-Skills',
        }

        with requests.post(
            url,
            stream=True,
            timeout=timeout,
            headers=headers,
            json=body,
        ) as response:
            if not response.ok:
                request_id = response.headers.get("x-acs-request-id", "")
                body_preview = ""
                try:
                    body_preview = response.text[:500]
                except Exception:
                    pass
                raise requests.exceptions.HTTPError(
                    f"{response.status_code} {response.reason} for {response.url}"
                    f"\n  Request-Id: {request_id}"
                    + (f"\n  Body: {body_preview}" if body_preview else ""),
                    response=response,
                )

            buffer = ""
            event_type = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if not chunk:
                    continue
                buffer += chunk

                # Process complete lines from buffer
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith("event:"):
                        event_part = line[6:].strip()
                        if " at " in event_part:
                            event_type = event_part.split(" at ")[0]
                        else:
                            event_type = event_part.split()[0] if event_part else ""
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str and event_type:
                            event = self._parse_event(event_type, data_str)
                            yield event
                            if event.event_type == "SSE_FINISH":
                                return

    def _do_stream_with_ak_sk(
        self,
        agent_id: str,
        session_id: str,
        timeout: int,
        checkpoint: Optional[int] = None,
    ) -> Iterator[SSEEvent]:
        """Stream with AK/SK authentication via default credential chain."""
        from alibabacloud_credentials.client import Client as CredentialClient
        
        credential_client = CredentialClient()
        credential = credential_client.get_credential()
        access_key_id = credential.access_key_id
        access_key_secret = credential.access_key_secret
        security_token = credential.security_token
        
        params = {
            "AgentId": agent_id,
            "SessionId": session_id,
        }
        if checkpoint is not None:
            params["Checkpoint"] = str(checkpoint)

        host = self._config.endpoint
        headers = AliyunSignerV3.sign(
            access_key_id,
            access_key_secret,
            "POST",
            host,
            "GetChatContent",
            params,
            security_token=security_token if security_token else None,
        )
        headers["User-Agent"] = "AlibabaCloud-Agent-Skills"

        # Build query string for URL
        query_params = {"Action": "GetChatContent", "Version": "2025-04-14", **params}
        query_string = "&".join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}"
            for k, v in sorted(query_params.items())
        )
        url = f"{self._base_url}/?{query_string}"

        with requests.post(
            url,
            stream=True,
            timeout=timeout,
            headers=headers,
        ) as response:
            if not response.ok:
                request_id = response.headers.get("x-acs-request-id", "")
                body_preview = ""
                try:
                    body_preview = response.text[:500]
                except Exception:
                    pass
                raise requests.exceptions.HTTPError(
                    f"{response.status_code} {response.reason} for {response.url}"
                    f"\n  Request-Id: {request_id}"
                    + (f"\n  Body: {body_preview}" if body_preview else ""),
                    response=response,
                )

            buffer = ""
            event_type = ""
            for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
                if not chunk:
                    continue
                buffer += chunk

                # Process complete lines from buffer
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith("event:"):
                        # Extract event type (before " at " timestamp)
                        event_part = line[6:].strip()
                        if " at " in event_part:
                            event_type = event_part.split(" at ")[0]
                        else:
                            event_type = event_part.split()[0] if event_part else ""
                    elif line.startswith("data:"):
                        data_str = line[5:].strip()
                        if data_str and event_type:
                            event = self._parse_event(event_type, data_str)
                            yield event
                            if event.event_type == "SSE_FINISH":
                                return

    def stream_chat_content(
        self,
        agent_id: str,
        session_id: str,
        timeout: int = 120,
        checkpoint: Optional[int] = None,
        max_retries: int = 3,
    ) -> Iterator[SSEEvent]:
        """Stream chat content from Data Agent using SSE.

        Automatically reconnects from the last checkpoint on SSL/connection
        errors, enabling resilience during long-running ANALYSIS sessions.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            timeout: Request timeout in seconds.
            checkpoint: Optional starting checkpoint (0 to replay from beginning).
            max_retries: Maximum number of reconnection attempts on error.

        Yields:
            SSEEvent objects as they arrive.
        """
        # Retryable network/SSL exception types
        _retryable = (
            ssl.SSLError,
            requests.exceptions.SSLError,
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
        )

        current_checkpoint = checkpoint
        retry_count = 0

        while True:
            try:
                for event in self._do_stream(agent_id, session_id, timeout, current_checkpoint):
                    # Track latest checkpoint for potential reconnection
                    if event.checkpoint is not None:
                        current_checkpoint = event.checkpoint
                    yield event
                    if event.event_type == "SSE_FINISH":
                        return
                return  # Clean finish without SSE_FINISH
            except _retryable as exc:
                retry_count += 1
                if retry_count > max_retries:
                    raise
                wait = min(2 ** retry_count, 30)  # 2s, 4s, 8s … capped at 30s
                time.sleep(wait)
                # Loop continues with updated current_checkpoint

    def _parse_event(self, event_type: str, data_str: str) -> SSEEvent:
        """Parse an SSE event.

        Args:
            event_type: The event type.
            data_str: The data JSON string.

        Returns:
            Parsed SSEEvent.
        """
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            data = {"content": data_str}

        return SSEEvent(
            event_type=event_type,
            data=data,
            checkpoint=data.get("checkpoint"),
            category=data.get("category"),
            content=data.get("content", ""),
            content_type=data.get("content_type"),
        )

    # Categories to skip when collecting data events
    _SKIP_DATA_CATEGORIES = {"tool_call_choices", "metric_agent_config"}

    def get_full_response(
        self,
        agent_id: str,
        session_id: str,
        timeout: int = 120,
    ) -> str:
        """Get complete response by collecting all SSE events.

        Collects all `data` events (excluding tool_call_choices and
        metric_agent_config), which carry the primary analysis results.
        Also collects `delta/llm` events as supplementary streaming text.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            timeout: Request timeout in seconds.

        Returns:
            Complete response text.
        """
        content_parts = []

        for event in self.stream_chat_content(agent_id, session_id, timeout):
            # Collect all delta events (llm / tool_call_response / output_conclusion etc.)
            if event.event_type == "delta":
                if event.content:
                    content_parts.append(event.content)

            # Collect data events except filtered categories
            elif event.event_type == "data":
                if event.category not in self._SKIP_DATA_CATEGORIES:
                    if event.content:
                        content_parts.append(event.content)

            if event.event_type == "SSE_FINISH":
                break

        return "".join(content_parts)


class AsyncSSEClient:
    """Async client for handling SSE streaming responses."""

    def __init__(self, config: DataAgentConfig):
        """Initialize async SSE client.

        Args:
            config: Data Agent configuration.
        """
        self._config = config
        self._base_url = f"https://{config.endpoint}"

    async def _async_do_stream(
        self,
        agent_id: str,
        session_id: str,
        timeout: int,
        checkpoint: Optional[int] = None,
    ) -> AsyncIterator[SSEEvent]:
        """Single-connection async streaming attempt."""
        # Check authentication type
        if hasattr(self._config, 'api_key') and self._config.api_key:
            # API_KEY authentication
            async for event in self._async_do_stream_with_api_key(agent_id, session_id, timeout, checkpoint):
                yield event
        else:
            # AK/SK authentication via default credential chain
            async for event in self._async_do_stream_with_ak_sk(agent_id, session_id, timeout, checkpoint):
                yield event

    async def _async_do_stream_with_api_key(
        self,
        agent_id: str,
        session_id: str,
        timeout: int,
        checkpoint: Optional[int] = None,
    ) -> AsyncIterator[SSEEvent]:
        """Async stream with API_KEY authentication."""
        # Determine endpoint based on action type (GetChatContent is a data plane API)
        base_endpoint = f"dataagent-stream-{self._config.region}.aliyuncs.com/apikey"
        url = f"https://{base_endpoint}"

        # Build request body
        body = {
            'Action': 'GetChatContent',
            'Version': '2025-04-14',
            'RegionId': self._config.region,
            'AgentId': agent_id,
            'SessionId': session_id,
        }
        if checkpoint is not None:
            body['Checkpoint'] = str(checkpoint)

        # Set up headers with API_KEY
        headers = {
            'x-api-key': self._config.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'AlibabaCloud-Agent-Skills',
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers=headers,
                json=body,
            ) as response:
                response.raise_for_status()

                buffer = ""
                event_type = ""

                async for chunk in response.content.iter_chunked(1024):
                    if not chunk:
                        continue
                    buffer += chunk.decode("utf-8")

                    # Process complete lines from buffer
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line:
                            continue

                        if line.startswith("event:"):
                            event_part = line[6:].strip()
                            if " at " in event_part:
                                event_type = event_part.split(" at ")[0]
                            else:
                                event_type = event_part.split()[0] if event_part else ""
                        elif line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str and event_type:
                                event = self._parse_event(event_type, data_str)
                                yield event
                                if event.event_type == "SSE_FINISH":
                                    return

    async def _async_do_stream_with_ak_sk(
        self,
        agent_id: str,
        session_id: str,
        timeout: int,
        checkpoint: Optional[int] = None,
    ) -> AsyncIterator[SSEEvent]:
        """Async stream with AK/SK authentication via default credential chain."""
        from alibabacloud_credentials.client import Client as CredentialClient
        
        credential_client = CredentialClient()
        credential = credential_client.get_credential()
        access_key_id = credential.access_key_id
        access_key_secret = credential.access_key_secret
        security_token = credential.security_token
        
        params = {
            "AgentId": agent_id,
            "SessionId": session_id,
        }
        if checkpoint is not None:
            params["Checkpoint"] = str(checkpoint)

        host = self._config.endpoint
        headers = AliyunSignerV3.sign(
            access_key_id,
            access_key_secret,
            "POST",
            host,
            "GetChatContent",
            params,
            security_token=security_token if security_token else None,
        )
        headers["User-Agent"] = "AlibabaCloud-Agent-Skills"

        # Build query string for URL
        query_params = {"Action": "GetChatContent", "Version": "2025-04-14", **params}
        query_string = "&".join(
            f"{quote(k, safe='')}={quote(str(v), safe='')}"
            for k, v in sorted(query_params.items())
        )
        url = f"{self._base_url}/?{query_string}"

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers=headers,
            ) as response:
                response.raise_for_status()

                buffer = ""
                event_type = ""

                async for chunk in response.content.iter_chunked(1024):
                    if not chunk:
                        continue
                    buffer += chunk.decode("utf-8")

                    # Process complete lines from buffer
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        line = line.strip()

                        if not line:
                            continue

                        if line.startswith("event:"):
                            event_part = line[6:].strip()
                            if " at " in event_part:
                                event_type = event_part.split(" at ")[0]
                            else:
                                event_type = event_part.split()[0] if event_part else ""
                        elif line.startswith("data:"):
                            data_str = line[5:].strip()
                            if data_str and event_type:
                                event = self._parse_event(event_type, data_str)
                                yield event
                                if event.event_type == "SSE_FINISH":
                                    return

    async def stream_chat_content(
        self,
        agent_id: str,
        session_id: str,
        timeout: int = 120,
        checkpoint: Optional[int] = None,
        max_retries: int = 3,
    ) -> AsyncIterator[SSEEvent]:
        """Stream chat content asynchronously.

        Automatically reconnects from the last checkpoint on SSL/connection
        errors, enabling resilience during long-running ANALYSIS sessions.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            timeout: Request timeout in seconds.
            checkpoint: Optional starting checkpoint (0 to replay from beginning).
            max_retries: Maximum number of reconnection attempts on error.

        Yields:
            SSEEvent objects as they arrive.
        """
        import asyncio

        _retryable = (
            ssl.SSLError,
            aiohttp.ClientSSLError,
            aiohttp.ServerDisconnectedError,
            aiohttp.ClientConnectionError,
        )

        current_checkpoint = checkpoint
        retry_count = 0

        while True:
            try:
                async for event in self._async_do_stream(
                    agent_id, session_id, timeout, current_checkpoint
                ):
                    if event.checkpoint is not None:
                        current_checkpoint = event.checkpoint
                    yield event
                    if event.event_type == "SSE_FINISH":
                        return
                return  # Clean finish without SSE_FINISH
            except _retryable:
                retry_count += 1
                if retry_count > max_retries:
                    raise
                wait = min(2 ** retry_count, 30)
                await asyncio.sleep(wait)
                # Loop continues with updated current_checkpoint

    def _parse_event(self, event_type: str, data_str: str) -> SSEEvent:
        """Parse an SSE event."""
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            data = {"content": data_str}

        return SSEEvent(
            event_type=event_type,
            data=data,
            checkpoint=data.get("checkpoint"),
            category=data.get("category"),
            content=data.get("content", ""),
            content_type=data.get("content_type"),
        )

    # Categories to skip when collecting data events
    _SKIP_DATA_CATEGORIES = {"tool_call_choices", "metric_agent_config"}

    async def get_full_response(
        self,
        agent_id: str,
        session_id: str,
        timeout: int = 120,
    ) -> str:
        """Get complete response asynchronously.

        Collects all `data` events (excluding tool_call_choices and
        metric_agent_config), which carry the primary analysis results.
        Also collects `delta/llm` events as supplementary streaming text.

        Args:
            agent_id: The agent ID.
            session_id: The session ID.
            timeout: Request timeout in seconds.

        Returns:
            Complete response text.
        """
        content_parts = []

        async for event in self.stream_chat_content(agent_id, session_id, timeout):
            # Collect all delta events (llm / tool_call_response / output_conclusion etc.)
            if event.event_type == "delta":
                if event.content:
                    content_parts.append(event.content)

            # Collect data events except filtered categories
            elif event.event_type == "data":
                if event.category not in self._SKIP_DATA_CATEGORIES:
                    if event.content:
                        content_parts.append(event.content)

            if event.event_type == "SSE_FINISH":
                break

        return "".join(content_parts)