#!/usr/bin/env python3
"""
Alibaba Cloud DAS Agent Chat API Client.

This is a PAID SERVICE with a FREE TIER for trial usage.
- Free Tier: When ALIBABA_CLOUD_DAS_AGENT_ID is not set, the AgentId parameter is omitted
  and the API will use a default Agent ID with limited free quota for trial purposes.
- Paid Usage: After purchasing DAS Agent service, set your own ALIBABA_CLOUD_DAS_AGENT_ID
  to bind your dedicated agent and quota.

Environment Variables:
    Credentials are resolved by Alibaba Cloud Credentials default provider chain.
    ALIBABA_CLOUD_DAS_AGENT_ID: DAS Agent ID (optional, uses default Agent ID if not set)

Command-line Arguments:
    --question: The question to send to the Agent

Usage:
    uv run call_das_agent.py --question "Please check the performance of instance rm-12345"
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import uuid
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, quote_plus, urlencode

import pytz
import requests

try:
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_credentials.exceptions import CredentialException
except ImportError:
    CredentialClient = None
    CredentialException = None


class SignatureRequest:
    def __init__(
            self,
            http_method: str,
            canonical_uri: str,
            host: str,
            x_acs_action: str,
            x_acs_version: str
    ):
        self.http_method = http_method
        self.canonical_uri = canonical_uri
        self.host = host
        self.x_acs_action = x_acs_action
        self.x_acs_version = x_acs_version
        self.headers = self._init_headers()
        self.query_param = OrderedDict()
        self.body = None

    def _init_headers(self) -> Dict[str, str]:
        current_time = datetime.now(pytz.timezone('Etc/GMT'))
        headers = OrderedDict([
            ('host', self.host),
            ('x-acs-action', self.x_acs_action),
            ('x-acs-version', self.x_acs_version),
            ('x-acs-date', current_time.strftime('%Y-%m-%dT%H:%M:%SZ')),
            ('x-acs-signature-nonce', str(uuid.uuid4())),
            ('x-acs-web-code', 'hdm'),
            ('x-accel-buffering', 'no'),
            ('accept', 'text/event-stream'),
            ('cache-control', 'no-cache'),
            ('connection', 'keep-alive'),
            ('User-Agent', 'AlibabaCloud-Agent-Skills/alibabacloud-das-agent'),
        ])
        return headers

    def sorted_query_params(self) -> None:
        self.query_param = dict(sorted(self.query_param.items()))

    def sorted_headers(self) -> None:
        self.headers = dict(sorted(self.headers.items()))


class DasAgentChatClient:
    # Output mode constants
    MODE_CLI = "cli"            # CLI chat UI: real-time streaming with tool details
    MODE_JSON = "json"          # JSONL structured output, all events to stdout
    MODE_PIPE = "pipe"          # Agent-friendly: progress to stderr, answer delimited on stdout

    def __init__(self, mode="cli"):
        if CredentialClient is None:
            raise ImportError("No module named 'alibabacloud_credentials'")

        # Support both environment variable names; if not set, AgentId param will be omitted (uses default Agent ID with free quota)
        self.agent_id = os.environ.get("ALIBABA_CLOUD_DAS_AGENT_ID") or os.environ.get("AGENT_ID") or None
        self.credentials_client = CredentialClient()
        self.algorithm = "ACS3-HMAC-SHA256"
        self.host = "das.cn-shanghai.aliyuncs.com"
        self.action = "Chat"
        self.version = "2020-01-16"

        # Output mode
        self.mode = mode

        # Dictionary for accumulating streaming tool call data
        self.tool_call_data = {}  # tool_call_id -> {"args": "", "result": "", "name": ""}

        # Dictionary for tracking message roles
        self.message_roles = {}  # message_id -> role

        # Accumulate current assistant message text
        self.accumulated_text = ""
        self.current_message_id = None

        # Accumulate current tool call result
        self.accumulated_tool_result = ""
        self.current_tool_id = None
        
        # Track last tool name for fallback (SSE may send TOOL_CALL_RESULT after TOOL_CALL_END)
        self.last_tool_name = None

    # --- Output helpers ---
    # All output goes to stdout for easy Agent consumption.
    # In JSON mode, everything is JSONL. In text modes, plain text.
    # In PIPE mode, everything goes to stdout in order; answer is wrapped in clear delimiters.

    def _emit(self, text, end="\n"):
        """Write content to stdout."""
        print(text, end=end, flush=True)

    def _progress(self, text, end="\n"):
        """Write progress/status info.
        - JSON mode  → structured progress event on stdout
        - PIPE mode  → plain text on stdout (in order with everything else)
        - CLI mode   → plain text on stdout
        """
        if self.mode == self.MODE_JSON:
            # In JSON mode, emit progress as structured event
            if text.strip():  # Skip empty progress
                self._emit_json({"type": "progress", "message": text.strip()})
        else:
            # CLI and PIPE: print directly to stdout
            print(text, end=end, flush=True)

    def _emit_json(self, obj):
        """Write a single JSON object as one line to stdout (JSONL)."""
        print(json.dumps(obj, ensure_ascii=False), flush=True)

    def _percent_encode(self, encoded_str: str) -> str:
        """Percent-encode according to ACS spec."""
        return encoded_str.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    def _sha256_hex(self, s: bytes) -> str:
        return hashlib.sha256(s).hexdigest()

    def _format_credential_error(self, error: Exception) -> str:
        """Translate SDK credential-chain failures into actionable guidance."""
        hints = [
            "Failed to resolve Alibaba Cloud credentials from the default provider chain.",
            "Configure credentials using one of the supported methods:",
            "  - See: https://www.alibabacloud.com/help/en/sdk/developer-reference/v2-manage-python-access-credentials",
            "  - Alibaba Cloud CLI/profile files: ~/.aliyun/config.json or ~/.alibabacloud/credentials.ini",
            "  - ECS RAM Role when the script runs on an Alibaba Cloud ECS instance",
        ]

        error_text = str(error)

        if "100.100.100.200" in error_text:
            hints.append(
                "The SDK also tried the ECS metadata service (100.100.100.200). "
                "If this is not running on ECS, set ALIBABA_CLOUD_ECS_METADATA_DISABLED=true to skip metadata lookup."
            )

        if "CLIProfileCredentialsProvider" in error_text or "ProfileCredentialsProvider" in error_text:
            hints.append(
                "If you expect credentials from a local profile, make sure the profile files exist and contain a valid default profile."
            )

        return "\n".join(hints)

    def _silence_credentials_sdk_logs(self):
        """Suppress noisy SDK logging while resolving credentials."""
        logger = logging.getLogger("credentials")
        return logger

    def _get_current_credential(self):
        """Fetch the latest credential from the default provider chain."""
        credentials_logger = self._silence_credentials_sdk_logs()
        original_disabled = credentials_logger.disabled
        credentials_logger.disabled = True
        try:
            credential = self.credentials_client.get_credential()
        except Exception as error:
            if CredentialException is not None and isinstance(error, CredentialException):
                raise ValueError(self._format_credential_error(error)) from error
            raise
        finally:
            credentials_logger.disabled = original_disabled

        access_key_id = credential.get_access_key_id()
        access_key_secret = credential.get_access_key_secret()
        security_token = credential.get_security_token()

        if not access_key_id or not access_key_secret:
            raise ValueError(
                "Failed to resolve access credentials from the Alibaba Cloud default credentials chain"
            )

        return access_key_id, access_key_secret, security_token

    def _get_authorization(self, request: SignatureRequest) -> None:
        """Generate authorization signature (based on documentation logic, adapted for Chat API)"""
        access_key_id, access_key_secret, security_token = self._get_current_credential()
        new_query_param = OrderedDict()
        self._process_object(new_query_param, '', request.query_param)
        request.query_param = new_query_param
        request.sorted_query_params()

        canonical_query_string = "&".join(
            f"{self._percent_encode(quote_plus(k))}={self._percent_encode(quote_plus(str(v)))}"
            for k, v in request.query_param.items()
        )

        hashed_request_payload = self._sha256_hex(request.body or b'')
        request.headers['x-acs-content-sha256'] = hashed_request_payload
        if security_token:
            request.headers['x-acs-security-token'] = security_token
        request.sorted_headers()

        filtered_headers = OrderedDict()
        for k, v in request.headers.items():
            if k.lower().startswith("x-acs-") or k.lower() in ["host", "content-type"]:
                filtered_headers[k.lower()] = v

        canonical_headers = "\n".join(f"{k}:{v}" for k, v in filtered_headers.items()) + "\n"
        signed_headers = ";".join(filtered_headers.keys())

        canonical_request = (
            f"{request.http_method}\n{request.canonical_uri}\n{canonical_query_string}\n"
            f"{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
        )

        hashed_canonical_request = self._sha256_hex(canonical_request.encode("utf-8"))
        string_to_sign = f"{self.algorithm}\n{hashed_canonical_request}"

        # Calculate signature
        signature = hmac.new(
            access_key_secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        ).hexdigest().lower()

        authorization = f'{self.algorithm} Credential={access_key_id},SignedHeaders={signed_headers},Signature={signature}'
        request.headers["Authorization"] = authorization

    def _process_object(self, result_map: Dict[str, str], key: str, value: Any) -> None:
        """Recursively process objects, flattening nested structures (for query parameters)."""
        if value is None:
            return

        if isinstance(value, (list, tuple)):
            for i, item in enumerate(value):
                self._process_object(result_map, f"{key}.{i + 1}", item)
        elif isinstance(value, dict):
            for sub_key, sub_value in value.items():
                self._process_object(result_map, f"{key}.{sub_key}", sub_value)
        else:
            key = key.lstrip(".")
            result_map[key] = value.decode("utf-8") if isinstance(value, bytes) else str(value)

    def _form_data_to_string(self, form_data: Dict[str, Any]) -> str:
        """Convert form data to URL-encoded string (for request body)"""
        tile_map = OrderedDict()
        self._process_object(tile_map, "", form_data)
        return urlencode(tile_map)

    # Input validation constants
    MAX_MESSAGE_LENGTH = 32000  # Max characters for user message
    MAX_SESSION_ID_LENGTH = 128  # Max characters for session ID

    def _validate_message(self, message: str) -> str:
        """Validate and sanitize user message input.
        
        Args:
            message: The user input message to validate
            
        Returns:
            The validated message (stripped of leading/trailing whitespace)
            
        Raises:
            ValueError: If the message fails validation
        """
        # Type check
        if not isinstance(message, str):
            raise ValueError(f"Message must be a string, got {type(message).__name__}")
        
        # Strip and check for empty content
        message = message.strip()
        if not message:
            raise ValueError("Message cannot be empty or contain only whitespace")
        
        # Length boundary check
        if len(message) > self.MAX_MESSAGE_LENGTH:
            raise ValueError(
                f"Message exceeds maximum length of {self.MAX_MESSAGE_LENGTH} characters "
                f"(got {len(message)} characters)"
            )
        
        return message

    def _validate_session_id(self, session_id: Optional[str]) -> Optional[str]:
        """Validate session ID format.
        
        Args:
            session_id: Optional session ID to validate
            
        Returns:
            The validated session ID or None
            
        Raises:
            ValueError: If the session ID fails validation
        """
        if session_id is None:
            return None
        
        # Type check
        if not isinstance(session_id, str):
            raise ValueError(f"Session ID must be a string, got {type(session_id).__name__}")
        
        # Strip and check
        session_id = session_id.strip()
        if not session_id:
            return None  # Treat empty string as None
        
        # Length check
        if len(session_id) > self.MAX_SESSION_ID_LENGTH:
            raise ValueError(
                f"Session ID exceeds maximum length of {self.MAX_SESSION_ID_LENGTH} characters"
            )
        
        # Format validation: allow only UUID-like characters (alphanumeric and hyphens)
        if not re.match(r'^[a-zA-Z0-9\-]+$', session_id):
            raise ValueError(
                "Session ID contains invalid characters. "
                "Only alphanumeric characters and hyphens are allowed."
            )
        
        return session_id

    def chat(self, message: str, session_id: str = None) -> None:
        """Send a message and receive streaming response."""
        # Validate inputs
        message = self._validate_message(message)
        session_id = self._validate_session_id(session_id)

        # Reset state
        self.message_roles.clear()
        self.accumulated_text = ""
        self.accumulated_tool_result = ""
        self.current_message_id = None
        self.current_tool_id = None

        # Use provided session_id, or generate a new one
        if session_id is None:
            session_id = str(uuid.uuid4())

        request = SignatureRequest("POST", "/", self.host, self.action, self.version)

        # Build Message JSON (using compact format, no spaces)
        message_json = {
            "id": str(uuid.uuid4()),
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": message
                }
            ]
        }

        # Build form data (reference: curl invocation)
        form_data = OrderedDict()
        form_data["Format"] = "JSON"
        form_data["SecureTransport"] = "true"
        # Use compact JSON format, no spaces
        form_data["Message"] = json.dumps(message_json, ensure_ascii=False, separators=(',', ':'))
        form_data["SourceTlsVersion"] = "TLSv1.2"
        form_data["AcceptLanguage"] = "zh-CN"
        # Only include AgentId if provided; omitting it uses the default Agent ID with free quota
        if self.agent_id:
            form_data["AgentId"] = self.agent_id
        form_data["SessionId"] = session_id

        # Manually build URL-encoded string to ensure correct encoding
        body_parts = []
        for key, value in form_data.items():
            # URL-encode the value using quote's safe parameter
            encoded_value = quote(str(value), safe='')
            body_parts.append(f"{key}={encoded_value}")
        request.body = "&".join(body_parts).encode('utf-8')
        request.headers["content-type"] = "application/x-www-form-urlencoded"

        self._get_authorization(request)

        # Output session ID only after credential resolution succeeds.
        if self.mode == self.MODE_JSON:
            self._emit_json({"type": "session", "session_id": session_id})
        elif self.mode == self.MODE_PIPE:
            self._emit(f"SESSION: {session_id}")
        else:
            self._emit(f"[Session: {session_id}]")

        self._call_api(request)

    def _call_api(self, request: SignatureRequest) -> None:
        """Call the API and handle streaming response."""
        url = f"https://{request.host}{request.canonical_uri}"
        if request.query_param:
            url += "?" + urlencode(request.query_param, doseq=True, safe="*")

        headers = dict(request.headers)
        data = request.body

        try:
            response = requests.request(
                method=request.http_method,
                url=url,
                headers=headers,
                data=data,
                stream=True,
                timeout=300
            )

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                self._progress(f"HTTP error: {response.status_code}")
                self._progress(f"Response content: {response.text}")
                if self.mode == self.MODE_JSON:
                    self._emit_json({"type": "error", "code": response.status_code, "message": error_msg})
                return

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    self._process_sse_line(line)

        except requests.exceptions.Timeout:
            self._progress("Request timed out")
            if self.mode == self.MODE_JSON:
                self._emit_json({"type": "error", "code": "TIMEOUT", "message": "Request timed out"})
        except requests.exceptions.ConnectionError:
            self._progress("Connection failed")
            if self.mode == self.MODE_JSON:
                self._emit_json({"type": "error", "code": "CONNECTION_ERROR", "message": "Connection failed"})
        except requests.exceptions.HTTPError as e:
            self._progress(f"HTTP error: {e}")
            if hasattr(e.response, 'text'):
                self._progress(f"Error details: {e.response.text}")
            if self.mode == self.MODE_JSON:
                self._emit_json({"type": "error", "code": "HTTP_ERROR", "message": str(e)})
        except Exception as e:
            self._progress(f"Unknown error: {e}")
            import traceback
            traceback.print_exc(file=sys.stderr)
            if self.mode == self.MODE_JSON:
                self._emit_json({"type": "error", "code": "UNKNOWN", "message": str(e)})

    def _process_sse_line(self, line: str) -> None:
        """Process a single SSE data line."""
        if not line.startswith('data:'):
            return

        data_content = line[5:]
        if data_content == '[DONE]':
            return

        try:
            json_data = json.loads(data_content)
        except json.JSONDecodeError:
            self._progress(f"[JSON parse error] Raw data: {data_content[:100]}...")
            if self.mode == self.MODE_JSON:
                self._emit_json({"type": "error", "code": "JSON_PARSE", "message": f"Failed to parse SSE data: {data_content[:200]}"})
            return

        event_type = json_data.get('Type')
        handler = {
            'TEXT_MESSAGE_START': self._on_text_message_start,
            'TEXT_MESSAGE_CONTENT': self._on_text_message_content,
            'TEXT_MESSAGE_END': self._on_text_message_end,
            'TOOL_CALL_START': self._on_tool_call_start,
            'TOOL_CALL_ARGS': self._on_tool_call_args,
            'TOOL_CALL_RESULT': self._on_tool_call_result,
            'TOOL_CALL_CHUNK': self._on_tool_call_chunk,
            'TOOL_CALL_END': self._on_tool_call_end,
            'ACTIVITY_DELTA': self._on_activity_delta,
            'CUSTOM': self._on_custom,
            'RUN_STARTED': lambda d: None,
            'RUN_FINISHED': lambda d: None,
        }.get(event_type)

        if handler:
            handler(json_data)
        elif 'Answer' in json_data:
            # Legacy format compatibility
            self._on_legacy_answer(json_data)

    # --- SSE Event Handlers ---

    def _on_text_message_start(self, data):
        message_id = data.get('MessageId')
        role = data.get('Role', '')
        if message_id and role:
            self.message_roles[message_id] = role
            if role == 'assistant':
                self.current_message_id = message_id
                self.accumulated_text = ""

    def _on_text_message_content(self, data):
        delta = data.get('Delta', '')
        message_id = data.get('MessageId')
        if not delta:
            return

        # Determine if this is an assistant message
        role = self.message_roles.get(message_id, '') if message_id else 'assistant'
        if role != 'assistant':
            return

        # Accumulate text (all modes need this)
        if message_id == self.current_message_id or not message_id:
            self.accumulated_text += delta

        # CLI mode: stream to stdout in real-time
        # PIPE mode: accumulate only; we print with delimiters at message end
        if self.mode == self.MODE_CLI:
            self._emit(delta, end='')

    def _on_text_message_end(self, data):
        message_id = data.get('MessageId')
        if not message_id or message_id not in self.message_roles:
            return

        role = self.message_roles[message_id]
        del self.message_roles[message_id]

        if role != 'assistant' or message_id != self.current_message_id:
            return

        text = self.accumulated_text.strip()
        self.current_message_id = None
        self.accumulated_text = ""

        if not text:
            return

        # Output the complete assistant message
        if self.mode == self.MODE_JSON:
            self._emit_json({"type": "message", "role": "assistant", "content": text})
        elif self.mode == self.MODE_PIPE:
            # PIPE mode: wrap the answer in clear delimiters on stdout so the host agent
            # can identify and relay the real DAS response without ambiguity.
            self._emit("\n=== DAS AGENT RESPONSE ===")
            self._emit(text)
            self._emit("=== END RESPONSE ===")
        else:
            # CLI mode: already streamed, just add a newline separator
            self._emit("\n")

    def _on_tool_call_start(self, data):
        tool_id = data.get('ToolCallId')
        # Extract tool name from SSE event - the field is "ToolCallName" based on actual API response
        tool_name = data.get('ToolCallName') or data.get('Name') or data.get('tool_name') or 'unknown_tool'

        self.tool_call_data[tool_id] = {
            'name': tool_name,
            'args': '',
            'result': '',
        }
        self.current_tool_id = tool_id
        self.last_tool_name = tool_name  # Save for fallback in TOOL_CALL_RESULT
        self.accumulated_tool_result = ""

        if self.mode == self.MODE_JSON:
            self._emit_json({"type": "tool_call", "tool": tool_name, "status": "started"})
        elif self.mode == self.MODE_PIPE:
            self._emit(f"[tool] {tool_name} started")
        else:
            # CLI mode: show tool call with newline
            self._emit(f"\nCalling tool [{tool_name}]...")

    def _on_tool_call_args(self, data):
        tool_id = data.get('ToolCallId')
        delta = data.get('Delta', '')
        if tool_id in self.tool_call_data:
            self.tool_call_data[tool_id]['args'] += delta

    def _on_tool_call_result(self, data):
        tool_id = data.get('ToolCallId')
        delta = data.get('Delta', '')
        direct_result = data.get('Result')
        content = data.get('Content', '')

        # Determine result content and source
        result_content = ''
        result_source = ''
        if delta:
            result_content = delta
            result_source = 'Delta'
        elif direct_result is not None:
            result_content = json.dumps(direct_result, ensure_ascii=False)
            result_source = 'Result'
        elif content:
            result_content = content
            result_source = 'Content'

        if not result_content:
            return

        # Accumulate into tool data
        if tool_id and tool_id in self.tool_call_data:
            self.tool_call_data[tool_id]['result'] += result_content

        # Accumulate for current tool
        if tool_id == self.current_tool_id:
            self.accumulated_tool_result += result_content

        # Get tool name for output
        # Note: SSE may send TOOL_CALL_RESULT after TOOL_CALL_END, so tool_call_data may be deleted
        # Use last_tool_name as fallback
        tool_name = 'unknown_tool'
        if tool_id and tool_id in self.tool_call_data:
            tool_name = self.tool_call_data[tool_id]['name']
        elif self.current_tool_id and self.current_tool_id in self.tool_call_data:
            tool_name = self.tool_call_data[self.current_tool_id]['name']
        elif self.last_tool_name:
            # Fallback to last known tool name (handles RESULT after END scenario)
            tool_name = self.last_tool_name

        # Output result content (Content-type results contain actual API responses)
        if result_source == 'Content':
            if self.mode == self.MODE_CLI:
                self._emit(f"\n[Result]")
                preview = result_content[:500] + "..." if len(result_content) > 500 else result_content
                self._emit(preview)
            elif self.mode == self.MODE_PIPE:
                # PIPE mode: print tool output inline on stdout
                preview = result_content[:300] + "..." if len(result_content) > 300 else result_content
                self._emit(f"[tool_output] {preview}")
            elif self.mode == self.MODE_JSON:
                # Emit tool output immediately for JSON mode
                if len(result_content) > 5000:
                    self._emit_json({"type": "tool_output", "tool": tool_name, "content": result_content[:5000] + "...(truncated)"})
                else:
                    self._emit_json({"type": "tool_output", "tool": tool_name, "content": result_content})

    def _on_tool_call_chunk(self, data):
        tool_id = data.get('ToolCallId')
        chunk = data.get('Chunk', '')
        if tool_id in self.tool_call_data:
            self.tool_call_data[tool_id]['result'] += str(chunk)

    def _on_tool_call_end(self, data):
        tool_id = data.get('ToolCallId')
        direct_result = data.get('Result')

        # Get tool info before deletion
        tool_name = 'unknown_tool'
        tool_args = ''
        if tool_id and tool_id in self.tool_call_data:
            tool_name = self.tool_call_data[tool_id]['name']
            tool_args = self.tool_call_data[tool_id]['args']
            # Also check if result was accumulated in tool_call_data
            if not self.accumulated_tool_result:
                self.accumulated_tool_result = self.tool_call_data[tool_id].get('result', '')
            del self.tool_call_data[tool_id]

        # Determine final result text
        result_text = ""
        if direct_result is not None:
            result_text = json.dumps(direct_result, ensure_ascii=False)
        elif self.accumulated_tool_result:
            result_text = self.accumulated_tool_result

        # Output tool result in JSON mode (always emit, even if result is empty)
        if self.mode == self.MODE_JSON:
            event = {"type": "tool_result", "tool": tool_name}
            if tool_args:
                event["args"] = tool_args
            if result_text:
                # Truncate very long results to avoid overwhelming output
                if len(result_text) > 5000:
                    event["content"] = result_text[:5000] + "...(truncated)"
                else:
                    event["content"] = result_text
            self._emit_json(event)

        # Reset
        if tool_id == self.current_tool_id:
            self.current_tool_id = None
            self.accumulated_tool_result = ""

        # Progress indicator
        if self.mode == self.MODE_CLI:
            print(" done", flush=True)
        elif self.mode == self.MODE_PIPE:
            self._emit(f"[tool] {tool_name} done")

    def _on_activity_delta(self, data):
        # Show progress dots in CLI/PIPE modes; skip in JSON mode
        if self.mode in (self.MODE_CLI, self.MODE_PIPE):
            print(".", end="", flush=True)

    def _on_custom(self, data):
        event_name = data.get('Name', '')
        value = data.get('Value', {})
        if event_name == 'error' and isinstance(value, dict):
            error_code = value.get('Code', 'unknown')
            error_msg = value.get('Message', 'Unknown error')
            self._progress(f"\n[Error {error_code}] {error_msg}")
            if self.mode == self.MODE_JSON:
                self._emit_json({"type": "error", "code": error_code, "message": error_msg})

    def _on_legacy_answer(self, data):
        answer = data.get('Answer', '')
        if not answer:
            return
        if self.mode == self.MODE_JSON:
            self._emit_json({"type": "message", "role": "assistant", "content": answer})
        else:
            self._emit(answer, end='')


def main():
    parser = argparse.ArgumentParser(description="Call Alibaba Cloud DAS Agent Chat API")
    parser.add_argument("--question", required=True, help="The question to send to the Agent")
    parser.add_argument("--session", help="Session ID for maintaining conversation context")
    parser.add_argument("--json", action="store_true", help="JSONL output: one JSON object per line, machine-readable")
    parser.add_argument("--pipe", action="store_true",
                        help="Agent-friendly mode: progress/tool noise to stderr, answer delimited on stdout")
    args = parser.parse_args()

    if args.json:
        mode = DasAgentChatClient.MODE_JSON
    elif args.pipe:
        mode = DasAgentChatClient.MODE_PIPE
    else:
        mode = DasAgentChatClient.MODE_CLI

    try:
        client = DasAgentChatClient(mode=mode)
        client.chat(args.question, session_id=args.session)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except ImportError as e:
        print(
            "Dependency error: install project dependencies first (missing Alibaba Cloud Credentials SDK).",
            file=sys.stderr,
        )
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Runtime error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
