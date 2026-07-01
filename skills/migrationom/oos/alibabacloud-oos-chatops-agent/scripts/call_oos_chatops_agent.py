#!/usr/bin/env python3
"""
Alibaba Cloud OOS ChatOps Agent - SSE Streaming Chat Client.

Calls the OOS Chat API via alibabacloud-tea-openapi-sse SDK and streams
the response back in real-time.

SSE Response Structure:
    {"ConversationId": "xxx", "Message": "增量文本", "RequestId": "xxx"}

Environment Variables:
    ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET
    OOS_CHATOPS_ENDPOINT (optional, default: oos.cn-hangzhou.aliyuncs.com)
    OOS_CHATOPS_REGION (optional, default: cn-hangzhou)
    OOS_CHATOPS_TIMEOUT (optional, read timeout in seconds, default: 300)

Usage:
    python3 call_oos_chatops_agent.py -q "帮我查看ECS实例列表"
    python3 call_oos_chatops_agent.py -q "帮我重启实例 i-xxx" --region cn-hangzhou --pipe
    python3 call_oos_chatops_agent.py -q "查看cn-beijing的" --session "<conversation_id>" --pipe
    python3 call_oos_chatops_agent.py -q "查看实例" --timeout 600 --pipe
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from enum import Enum
from typing import Any, Optional

from alibabacloud_tea_openapi_sse.client import Client as OpenApiClient
from alibabacloud_tea_openapi_sse import models as open_api_models
from alibabacloud_tea_util_sse import models as util_models

try:
    from alibabacloud_credentials.client import Client as CredentialClient
except ImportError:
    CredentialClient = None


# =============================================================================
# Constants
# =============================================================================

DEFAULT_REGION = "cn-hangzhou"
DEFAULT_ENDPOINT = "oos.cn-hangzhou.aliyuncs.com"  # Fixed, ChatOps API is only in Hangzhou
DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 2
SKILL_NAME = "alibabacloud-oos-chatops-agent"
SESSION_ID_ENV = "SKILL_SESSION_ID"


def resolve_session_id() -> str:
    """Resolve or generate a 32-char hex session ID for observability."""
    env_val = os.environ.get(SESSION_ID_ENV, "").strip()
    if env_val and len(env_val) == 32 and all(c in '0123456789abcdef' for c in env_val.lower()):
        return env_val.lower()
    import uuid
    new_id = uuid.uuid4().hex
    os.environ[SESSION_ID_ENV] = new_id
    return new_id


def build_user_agent(session_id: str) -> str:
    """Build User-Agent string with session-id for tracing."""
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id}"


class OutputMode(str, Enum):
    CLI = "cli"    # Interactive streaming output
    JSON = "json"  # JSONL structured output
    PIPE = "pipe"  # Agent-friendly: answer wrapped in delimiters


class OOSChatError(RuntimeError):
    """OOS Chat API returned an error or failed."""


class OOSChatTimeoutError(OOSChatError):
    """OOS Chat API streaming timed out."""


class CredentialError(RuntimeError):
    """Alibaba Cloud credentials could not be loaded."""


# =============================================================================
# OOS ChatOps Agent Client
# =============================================================================

class OOSChatOpsClient:
    """OOS ChatOps Agent SSE Client."""

    def __init__(
        self,
        region: str = DEFAULT_REGION,
        mode: OutputMode = OutputMode.CLI,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        self.region = region
        self.endpoint = DEFAULT_ENDPOINT
        self.mode = mode
        self.timeout_seconds = timeout_seconds
        self.session_id = resolve_session_id()
        self.user_agent = build_user_agent(self.session_id)
        self._client = self._create_client()
        self._api_info = self._create_api_info()
        self._runtime = util_models.RuntimeOptions(
            read_timeout=int(timeout_seconds * 1000)
        )

    def _create_client(self) -> OpenApiClient:
        """Create OpenAPI client with credentials."""
        access_key_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID")
        access_key_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET")
        security_token = os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")

        if access_key_id and access_key_secret:
            config = open_api_models.Config(
                access_key_id=access_key_id,
                access_key_secret=access_key_secret,
                security_token=security_token,
                user_agent=self.user_agent,
            )
        elif CredentialClient is not None:
            try:
                credential = CredentialClient()
                cred = credential.get_credential()
                config = open_api_models.Config(
                    access_key_id=cred.get_access_key_id(),
                    access_key_secret=cred.get_access_key_secret(),
                    security_token=cred.get_security_token(),
                    user_agent=self.user_agent,
                )
            except Exception as exc:
                raise CredentialError(
                    f"Failed to resolve credentials from default chain: {exc}\n"
                    "Set ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET, "
                    "or configure ~/.aliyun/config.json."
                ) from exc
        else:
            raise CredentialError(
                "No credentials found. Set ALIBABA_CLOUD_ACCESS_KEY_ID and "
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET, or install alibabacloud-credentials."
            )

        config.endpoint = self.endpoint
        return OpenApiClient(config)

    def _create_api_info(self) -> open_api_models.Params:
        """Define OOS Chat API parameters."""
        return open_api_models.Params(
            action="Chat",
            version="2020-01-01",
            protocol="HTTPS",
            method="POST",
            auth_type="AK",
            style="RPC",
            pathname="/",
            req_body_type="json",
            body_type="sse",
        )

    async def chat(
        self,
        question: str,
        conversation_id: Optional[str] = None,
        retries: int = MAX_RETRIES,
    ) -> None:
        """Send a question and stream the SSE response with retry support."""
        last_error: Optional[Exception] = None

        for attempt in range(retries + 1):
            try:
                await self._do_chat(question, conversation_id)
                return
            except OOSChatTimeoutError:
                # Timeout: don't retry
                raise
            except OOSChatError as e:
                last_error = e
                if attempt < retries:
                    self._progress(f"[retry] Attempt {attempt + 1} failed, retrying in {RETRY_DELAY_SECONDS}s...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    raise
            except Exception as e:
                last_error = e
                if attempt < retries:
                    self._progress(f"[retry] Unexpected error, retrying in {RETRY_DELAY_SECONDS}s...")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                else:
                    raise

    async def _do_chat(self, question: str, conversation_id: Optional[str] = None) -> None:
        """Execute a single chat request."""
        body: dict[str, Any] = {
            "RegionId": self.region,
            "Messages": [{"Role": "user", "Content": question}],
        }

        # Multi-turn: reuse conversation
        if conversation_id:
            body["ConversationId"] = conversation_id

        request = open_api_models.OpenApiRequest(body=body)

        try:
            sse_receiver = self._client.call_sse_api_async(
                params=self._api_info,
                request=request,
                runtime=self._runtime,
            )
        except Exception as e:
            raise OOSChatError(f"Failed to initiate SSE request: {e}") from e

        accumulated_answer = ""
        resolved_conversation_id = conversation_id or ""
        request_id = ""
        start_time = time.monotonic()

        try:
            async for res in sse_receiver:
                # Check timeout
                elapsed = time.monotonic() - start_time
                if elapsed > self.timeout_seconds:
                    raise OOSChatTimeoutError(
                        f"SSE stream timed out after {int(elapsed)}s "
                        f"(limit: {int(self.timeout_seconds)}s). "
                        "Increase --timeout if the query is expected to be long-running."
                    )

                event = res.get("event") if isinstance(res, dict) else None
                if event is None:
                    continue

                raw_data = event.data if hasattr(event, "data") else str(event)

                try:
                    payload = json.loads(raw_data)
                except (json.JSONDecodeError, TypeError):
                    continue

                # Extract fields
                message = payload.get("Message", "")
                conv_id = payload.get("ConversationId", "")
                req_id = payload.get("RequestId", "")

                if conv_id and not resolved_conversation_id:
                    resolved_conversation_id = conv_id
                if req_id:
                    request_id = req_id

                # Accumulate text
                if message:
                    accumulated_answer += message
                    if self.mode == OutputMode.CLI:
                        self._emit(message, end="")
                    elif self.mode == OutputMode.JSON:
                        self._emit_json({
                            "type": "message",
                            "delta": message,
                            "conversation_id": conv_id,
                        })

        except OOSChatTimeoutError:
            raise
        except Exception as e:
            raise OOSChatError(f"Error during SSE streaming: {e}") from e

        # === Stream ended ===
        self._emit_conversation(resolved_conversation_id, request_id)
        self._emit_done(accumulated_answer)

    # =========================================================================
    # Output helpers
    # =========================================================================

    def _emit(self, text: str, end: str = "\n") -> None:
        print(text, end=end, flush=True)

    def _emit_json(self, obj: dict) -> None:
        print(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), flush=True)

    def _progress(self, text: str) -> None:
        if self.mode == OutputMode.JSON:
            self._emit_json({"type": "progress", "message": text})
        elif self.mode == OutputMode.PIPE:
            print(text, file=sys.stderr, flush=True)
        else:
            print(text, file=sys.stderr, flush=True)

    def _emit_conversation(self, conversation_id: str, request_id: str) -> None:
        """Emit conversation metadata for session reuse."""
        if self.mode == OutputMode.JSON:
            self._emit_json({
                "type": "conversation",
                "conversation_id": conversation_id,
                "request_id": request_id,
            })
        elif self.mode == OutputMode.PIPE:
            self._emit(f"CONVERSATION: {conversation_id}")
        else:
            self._emit(f"\n[Conversation: {conversation_id}]")

    def _emit_done(self, answer: str) -> None:
        if self.mode == OutputMode.JSON:
            self._emit_json({"type": "done", "status": "completed"})
        elif self.mode == OutputMode.PIPE:
            self._emit("=== OOS CHATOPS ANSWER BEGIN ===")
            self._emit(answer.strip() or "(No answer was returned.)")
            self._emit("=== OOS CHATOPS ANSWER END ===")
        # CLI: already streamed

    def _emit_error(self, error: str) -> None:
        if self.mode == OutputMode.JSON:
            self._emit_json({"type": "error", "message": error})
        else:
            print(f"ERROR: {error}", file=sys.stderr, flush=True)


# =============================================================================
# CLI Entry Point
# =============================================================================

def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Call Alibaba Cloud OOS ChatOps Agent Chat API (SSE streaming)"
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="The question or command to send to OOS ChatOps Agent",
    )
    parser.add_argument(
        "--region",
        default=os.environ.get("OOS_CHATOPS_REGION", DEFAULT_REGION),
        help=f"Target region for resource queries (default: {DEFAULT_REGION})",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="ConversationId for multi-turn conversation (from previous response)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("OOS_CHATOPS_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)),
        help=f"Total timeout in seconds for SSE streaming (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable automatic retry on transient errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSONL output: one JSON object per line, machine-readable",
    )
    parser.add_argument(
        "--pipe",
        action="store_true",
        help="Agent-friendly mode: answer wrapped in delimiters on stdout",
    )
    return parser


async def async_main(args: argparse.Namespace) -> int:
    if args.json and args.pipe:
        print("ERROR: Use only one output mode: --json or --pipe.", file=sys.stderr)
        return 1
    if args.json:
        mode = OutputMode.JSON
    elif args.pipe:
        mode = OutputMode.PIPE
    else:
        mode = OutputMode.CLI

    try:
        client = OOSChatOpsClient(
            region=args.region,
            mode=mode,
            timeout_seconds=args.timeout,
        )
        await client.chat(
            question=args.question,
            conversation_id=args.session,
            retries=0 if args.no_retry else MAX_RETRIES,
        )
        return 0
    except (CredentialError, OOSChatError) as e:
        if mode == OutputMode.JSON:
            print(json.dumps({"type": "error", "message": str(e)}, ensure_ascii=False), flush=True)
        else:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
