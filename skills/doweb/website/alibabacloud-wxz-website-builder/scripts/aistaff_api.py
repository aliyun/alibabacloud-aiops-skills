#!/usr/bin/env python3
"""
AI Staff (零号员工) Website Builder — Alibaba Cloud OpenAPI CLI Client

Calls zero2staff OpenAPI (RPC style) via alibabacloud_tea_openapi.
Supports conversation creation, async chat, SSE event polling, and retry.

Usage:
    python aistaff_api.py <command> [options]

Environment variables:
    ALIBABACLOUD_ACCESS_KEY_ID      - AccessKey ID (optional, credential chain used)
    ALIBABACLOUD_ACCESS_KEY_SECRET  - AccessKey Secret (optional, credential chain used)
    ALIBABACLOUD_REGION_ID          - Region (default: cn-hangzhou)
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_credentials.client import Client as CredentialClient

VERSION = "1.0.0"
DEFAULT_REGION = "cn-hangzhou"
PRODUCT = "websitebuild"
API_VERSION = "2025-04-29"


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def create_client(region_id: str | None = None) -> OpenApiClient:
    """Create an OpenAPI client using the Alibaba Cloud default credential chain.

    Credential resolution order (handled automatically by alibabacloud_credentials):
    1. Environment variables (ALIBABACLOUD_ACCESS_KEY_ID / ALIBABACLOUD_ACCESS_KEY_SECRET)
    2. Shared config file (~/.alibabacloud/credentials)
    3. ECS RAM role / instance metadata service
    """
    region = region_id or os.getenv("ALIBABACLOUD_REGION_ID") or DEFAULT_REGION

    credential = CredentialClient()
    config = open_api_models.Config(
        credential=credential,
        region_id=region,
        endpoint=f"{PRODUCT}.aliyuncs.com",
        user_agent="AlibabaCloud-Agent-Skills/alibabacloud-wxz-website-builder",
    )

    return OpenApiClient(config)


def call_api(client: OpenApiClient, action: str, params: dict) -> dict:
    """Call a zero2staff RPC-style OpenAPI action.

    Returns the parsed response body dict.
    """
    api_params = open_api_models.Params(
        action=action,
        version=API_VERSION,
        protocol="HTTPS",
        method="POST",
        auth_type="AK",
        style="RPC",
        pathname="/",
        req_body_type="formData",
        body_type="json",
    )
    runtime = util_models.RuntimeOptions(
        connect_timeout=10000,   # 10s
        read_timeout=60000,      # 60s
    )
    request = open_api_models.OpenApiRequest(body=params)
    resp = client.call_api(api_params, request, runtime)
    body = resp.get("body", {})
    return body


# ---------------------------------------------------------------------------
# API wrappers
# ---------------------------------------------------------------------------

def create_conversation(client: OpenApiClient, text: str) -> dict:
    """CreateAIStaffConversation — create conversation with site instance."""
    params = {"Text": text}
    body = call_api(client, "CreateAIStaffConversation", params)
    return body


def create_chat(client: OpenApiClient, conversation_id: str, messages: list,
                biz_id: str | None = None,
                chat_id: str | None = None,
                meta_data: dict | None = None) -> dict:
    """CreateAIStaffChat — fire async chat."""
    params: dict = {
        "ConversationId": conversation_id,
        "Messages": messages,
    }
    if biz_id:
        params["BizId"] = biz_id
    if chat_id:
        params["ChatId"] = chat_id
    if meta_data:
        params["MetaData"] = meta_data
    body = call_api(client, "CreateAIStaffChat", params)
    return body


def fetch_chat_events(client: OpenApiClient, conversation_id: str,
                      chat_id: str | None = None,
                      last_event_id: int = 0,
                      biz_id: str | None = None) -> dict:
    """ListAIStaffChatEvents — fetch incremental SSE events."""
    params: dict = {
        "ConversationId": conversation_id,
        "LastEventId": last_event_id,
    }
    if chat_id:
        params["ChatId"] = chat_id
    if biz_id:
        params["BizId"] = biz_id
    body = call_api(client, "ListAIStaffChatEvents", params)
    # Normalize to {conversationId, chatId, lastEventId, hasMore, events}
    data = body['Module']
    return {
        "conversationId": data.get("ConversationId", conversation_id),
        "chatId": data.get("ChatId", chat_id),
        "lastEventId": data.get("LastEventId", last_event_id),
        "hasMore": data.get("HasMore", False),
        "events": data.get("Events", []),
    }


def list_chat_messages(client: OpenApiClient, conversation_id: str,
                       page_size: int = 50,
                       start_create_time: str | None = None) -> list:
    """ListAIStaffChatMessages — query message page by cursor.

    Args:
        conversation_id: conversation to query
        page_size: number of messages (10-100, default 20)
        start_create_time: cursor (ISO datetime string), None for first page

    Returns:
        List of message dicts.
    """
    params: dict = {
        "ConversationId": conversation_id,
        "PageSize": page_size,
    }
    if start_create_time:
        params["StartCreateTime"] = start_create_time
    body = call_api(client, "ListAIStaffChatMessages", params)
    data = body.get("Module", {})
    return data.get("Messages", [])


# ---------------------------------------------------------------------------
# Event summary extraction
# ---------------------------------------------------------------------------

def extract_chat_summary(events: list) -> dict:
    """Extract status summary from SSE events.

    Returns a dict with status info and detailed progress tracking:
    - chatStatus, hasError, errorMsg, hasPrd, toolsCalled (as before)
    - filesWritten: list of {path, semantic, status} for Write tool calls
    - toolDetails: list of {name, status, semantic} for all tool calls
    - lastAssistantMessage: latest assistant text message content
    - activeTools: list of tool names currently in 'wait' status
    """
    chat_status = "unknown"
    has_error = False
    error_msg = ""
    tools_called: set = set()
    files_written: list = []
    tool_details: list = []
    last_assistant_msg = ""
    active_tools: list = []
    # Track tool status by id to deduplicate (wait → done)
    tool_status_map: dict = {}

    for ev in events:
        name = ev.get("name", "") or ev.get("Name", "")

        if name in ("chat.completed", "chat.failed"):
            try:
                d = json.loads(ev.get("data", ev.get("Data", "{}")))
                chat_status = d.get("status", chat_status)
            except (json.JSONDecodeError, KeyError):
                pass

        if name == "message.error":
            has_error = True
            try:
                d = json.loads(ev.get("data", ev.get("Data", "{}")))
                error_msg = d.get("content", "") if isinstance(d, dict) else str(d)
            except (json.JSONDecodeError, KeyError):
                pass

        if name in ("message.completed",):
            try:
                d = json.loads(ev.get("data", ev.get("Data", "{}")))
                if isinstance(d, dict) and d.get("role") == "assistant":
                    content = d.get("content", "")
                    if content:
                        last_assistant_msg = content
            except (json.JSONDecodeError, KeyError):
                pass

        if name in ("message.tool", "message.tool.delta"):
            try:
                d = json.loads(ev.get("data", ev.get("Data", "{}")))
                md = d.get("metaData", {}) if isinstance(d, dict) else {}
                tool_name = md.get("name", "")
                tool_id = md.get("id", "")
                tool_status = md.get("status", "")
                if tool_name:
                    tools_called.add(tool_name)

                    # Parse arguments for detail extraction
                    args_str = md.get("arguments", "{}")
                    try:
                        tool_args = json.loads(args_str) if isinstance(args_str, str) else args_str
                    except (json.JSONDecodeError, ValueError):
                        tool_args = {}

                    semantic = tool_args.get("semantic", "") if isinstance(tool_args, dict) else ""

                    # Track tool by id for dedup
                    detail = {
                        "name": tool_name,
                        "status": tool_status,
                        "semantic": semantic,
                    }

                    # Extract file info from Write tool
                    if tool_name == "Write" and isinstance(tool_args, dict):
                        file_path = tool_args.get("file_path", "")
                        if file_path:
                            detail["filePath"] = file_path
                            # Deduplicate by file path
                            existing = [f for f in files_written if f.get("path") == file_path]
                            if existing:
                                existing[0]["status"] = tool_status
                            else:
                                files_written.append({
                                    "path": file_path,
                                    "semantic": semantic,
                                    "status": tool_status,
                                })

                    if tool_id:
                        tool_status_map[tool_id] = detail
                    else:
                        tool_details.append(detail)
            except (json.JSONDecodeError, KeyError):
                pass

    # Build final tool_details from the dedup map
    tool_details = list(tool_status_map.values()) + tool_details
    # Active tools = those still in 'wait' status
    active_tools = [t["name"] for t in tool_details if t.get("status") == "wait"]

    return {
        "chatStatus": chat_status,
        "hasError": has_error,
        "errorMsg": error_msg,
        "hasPrd": bool({"WritePrd", "GeneratePrd"} & tools_called),
        "toolsCalled": sorted(tools_called),
        "filesWritten": files_written,
        "toolDetails": tool_details,
        "lastAssistantMessage": last_assistant_msg,
        "activeTools": active_tools,
    }


# ---------------------------------------------------------------------------
# Drain old events (advance cursor)
# ---------------------------------------------------------------------------

def drain_events(client: OpenApiClient, conversation_id: str,
                 biz_id: str | None = None,
                 verbose: bool = False) -> int:
    """Advance the SSE event cursor to the end of the current stream.

    Fetches events in a loop until HasMore is False, discarding the content.
    Returns the lastEventId at the end of the stream so that a subsequent
    poll can start from this point and only see new events.
    """
    cursor = 0
    total_drained = 0
    while True:
        try:
            result = fetch_chat_events(client, conversation_id,
                                       last_event_id=cursor, biz_id=biz_id)
        except Exception as e:
            if verbose:
                print(f"[Drain] Error fetching events: {e}", file=sys.stderr)
            break
        events = result.get("events", [])
        total_drained += len(events)
        new_cursor = result.get("lastEventId", cursor)
        if new_cursor == cursor and not events:
            break
        cursor = new_cursor
        if not result.get("hasMore", False):
            break
    if verbose:
        print(f"[Drain] Skipped {total_drained} old events, cursor at {cursor}",
              file=sys.stderr)
    return cursor


# ---------------------------------------------------------------------------
# Message builder
# ---------------------------------------------------------------------------

def build_messages(text: str, chat_id: str | None = None,
                   chat_status: str | None = None,
                   phase: str | None = None,
                   user_navigation: str | None = None,
                   hidden: bool = False,
                   without_refer: bool = False,
                   model: str = "qwen3.5") -> list:
    """Build the messages list for CreateAIStaffChat."""
    msg: dict = {
        "ContentType": "text",
        "Content": text,
        "MetaData": {"model": model},
        "Role": "user",
        "Type": "question",
    }
    if phase:
        msg["MetaData"]["phase"] = phase
    if user_navigation:
        msg["MetaData"]["user_navigation"] = user_navigation
    if chat_status:
        msg["chatStatus"] = chat_status
    if hidden:
        msg["MetaData"]["__hidden__"] = True
    if without_refer:
        msg["withoutRefer"] = True
    return [msg]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Staff Website Builder — Alibaba Cloud OpenAPI CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--region", default=None, help=f"Region ID (default: {DEFAULT_REGION})")

    sub = parser.add_subparsers(dest="command", required=True)

    # create-conversation
    p = sub.add_parser("create-conversation", help="Create a new conversation with site instance")
    p.add_argument("--text", required=True, help="User question text (first 100 chars used as title)")
    p.add_argument("--output", help="Write output to file")

    # chat (async fire, always returns immediately; use `poll` to track progress)
    p = sub.add_parser("chat", help="Fire an async chat message (returns immediately, use poll to track)")
    p.add_argument("--text", required=True, help="Message text or form answers JSON")
    p.add_argument("--conversation-id", required=True, help="Conversation ID")
    p.add_argument("--biz-id", required=True, help="Site/biz ID from create-conversation")
    p.add_argument("--chat-id", default=None, help="Chat ID (for HITL resume)")
    p.add_argument("--chat-status", default=None, choices=["interrupt"])
    p.add_argument("--phase", default=None, choices=["requirement_collect", "generate_prd", "generate_code"])
    p.add_argument("--user-navigation", default=None)
    p.add_argument("--hidden", action="store_true")
    p.add_argument("--without-refer", action="store_true")
    p.add_argument("--model", default="qwen3.5")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--output", help="Write output to file")

    # fetch-events
    p = sub.add_parser("fetch-events", help="Fetch incremental SSE events (single call)")
    p.add_argument("--conversation-id", required=True)
    p.add_argument("--biz-id", required=True, help="Site/biz ID from create-conversation")
    p.add_argument("--chat-id", default=None)
    p.add_argument("--last-event-id", type=int, default=0)
    p.add_argument("--output", help="Write output to file")

    # poll (single-shot status check for agent-driven polling)
    p = sub.add_parser("poll", help="Single-shot status check: fetch new events + check message status (no looping)")
    p.add_argument("--conversation-id", required=True)
    p.add_argument("--biz-id", required=True, help="Site/biz ID from create-conversation")
    p.add_argument("--last-event-id", type=int, default=0,
                   help="Cursor from previous poll (default: 0)")
    p.add_argument("--max-output-events", type=int, default=10,
                   help="Max events in output (default: 10, 0=unlimited)")
    p.add_argument("--output", help="Write output to file")

    # list-messages
    p = sub.add_parser("list-messages", help="Query chat messages (cursor-based pagination)")
    p.add_argument("--conversation-id", required=True)
    p.add_argument("--tail", type=int, default=10,
                   help="Only output the last N messages (default: 10, 0=all)")
    p.add_argument("--output", help="Write output to file")

    return parser


def write_output(data: str, output_path: str | None):
    """Print output and optionally write to file."""
    if output_path:
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(data + "\n")
        print(f"Output written to {output_path}")
    else:
        print(data)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        client = create_client(args.region)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output_path = getattr(args, "output", None)

    try:
        if args.command == "create-conversation":
            body = create_conversation(client, text=args.text)
            # Flatten: extract Module fields to top level for easy parsing
            module = body.get("Module", {})
            flat = {
                "ConversationId": module.get("ConversationId", ""),
                "SiteId": module.get("SiteId", ""),
                "ChatId": module.get("ChatId", ""),
                "SectionId": module.get("SectionId", ""),
                "BotId": module.get("BotId", ""),
                "Title": module.get("Title", ""),
            }
            result = json.dumps(flat, indent=2, ensure_ascii=False, default=str)
            write_output(result, output_path)

        elif args.command == "chat":
            if args.verbose:
                print("[Chat] Firing async chat...", file=sys.stderr)

            # Drain old SSE events BEFORE firing, so that subsequent poll
            # only sees events from the new chat round.
            drain_events(
                client, args.conversation_id,
                biz_id=args.biz_id, verbose=args.verbose,
            )

            messages = build_messages(
                args.text,
                chat_id=args.chat_id,
                chat_status=args.chat_status,
                phase=args.phase,
                user_navigation=args.user_navigation,
                hidden=args.hidden,
                without_refer=args.without_refer,
                model=args.model,
            )

            fire_result = create_chat(
                client,
                conversation_id=args.conversation_id,
                messages=messages,
                biz_id=args.biz_id,
                chat_id=args.chat_id,
            )

            success = fire_result.get("Success", fire_result.get("success",
                      fire_result.get("Module") is not None))
            if not success:
                error_msg = f"[{fire_result.get('Code', 'UNKNOWN')}] {fire_result.get('Message', 'Async chat failed')}"
                result = json.dumps({
                    "conversationId": args.conversation_id,
                    "chatId": None,
                    "error": error_msg,
                }, ensure_ascii=False)
                write_output(result, output_path)
                return 1

            if args.verbose:
                print(f"[Chat] Fired for conversation {args.conversation_id}", file=sys.stderr)
            result = json.dumps({
                "conversationId": args.conversation_id,
                "chatId": fire_result.get("ChatId"),
                "status": "fired",
                "error": None,
            }, ensure_ascii=False)
            write_output(result, output_path)

        elif args.command == "fetch-events":
            events = fetch_chat_events(client, args.conversation_id,
                                       chat_id=args.chat_id,
                                       last_event_id=args.last_event_id,
                                       biz_id=args.biz_id)
            result = json.dumps(events, ensure_ascii=False, indent=2)
            write_output(result, output_path)

        elif args.command == "poll":
            # Single-shot: fetch new events + check message status
            all_new_events: list = []
            cursor = args.last_event_id
            # Drain all available events in one pass
            while True:
                try:
                    ev_result = fetch_chat_events(
                        client, args.conversation_id,
                        last_event_id=cursor, biz_id=args.biz_id,
                    )
                except Exception as e:
                    break
                events = ev_result.get("events", [])
                all_new_events.extend(events)
                new_cursor = ev_result.get("lastEventId", cursor)
                if new_cursor == cursor and not events:
                    break
                cursor = new_cursor
                if not ev_result.get("hasMore", False):
                    break

            # Extract summary from events
            summary = extract_chat_summary(all_new_events)

            # Also check message status for more reliable status detection
            msg_status = None
            try:
                messages = list_chat_messages(client, args.conversation_id)
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    msg_status = (last_msg.get("ChatStatus")
                                  or last_msg.get("chatStatus") or None)
            except Exception:
                pass

            # Merge: prefer event-based status, fall back to message status
            if summary["chatStatus"] == "unknown" and msg_status:
                summary["chatStatus"] = msg_status
            if msg_status == "fail" and not summary["hasError"]:
                summary["hasError"] = True

            # Determine a human-readable phase hint
            phase_hint = "processing"
            tools = summary.get("toolsCalled", [])
            if summary["chatStatus"] == "interrupt":
                phase_hint = "waiting_for_input"
            elif summary["chatStatus"] in ("success", "fail"):
                phase_hint = summary["chatStatus"]
            elif "GeneratePrd" in tools or "WritePrd" in tools:
                phase_hint = "generating_prd"
            elif "FetchWebsiteInfo" in tools:
                phase_hint = "fetching_reference"
            elif "AskUserQuestion" in tools:
                phase_hint = "waiting_for_input"

            # Build progressDetail for agent-facing progress reporting
            files_written = summary.get("filesWritten", [])
            active_tools = summary.get("activeTools", [])
            tool_details = summary.get("toolDetails", [])
            last_msg = summary.get("lastAssistantMessage", "")

            progress_detail: dict = {
                "filesWrittenCount": len(files_written),
                "activeTools": active_tools,
            }
            # Latest file being written (most recent Write call)
            if files_written:
                latest = files_written[-1]
                progress_detail["latestFile"] = {
                    "path": latest.get("path", ""),
                    "semantic": latest.get("semantic", ""),
                    "status": latest.get("status", ""),
                }
            # All files written so far (compact: path + semantic only)
            if files_written:
                progress_detail["allFiles"] = [
                    {"path": f["path"], "semantic": f.get("semantic", "")}
                    for f in files_written
                ]
            # Latest assistant message (useful for understanding what the bot said)
            if last_msg:
                # Truncate to 200 chars to keep output compact
                progress_detail["lastMessage"] = last_msg[:200]
            # Tool-level progress (compact: name + status + semantic)
            if tool_details:
                progress_detail["toolProgress"] = [
                    {k: v for k, v in t.items() if v}
                    for t in tool_details
                ]

            # Remove verbose detail fields from summary to keep top-level clean
            compact_summary = {
                k: v for k, v in summary.items()
                if k not in ("filesWritten", "toolDetails", "lastAssistantMessage", "activeTools")
            }

            max_ev = args.max_output_events
            output_events = all_new_events[-max_ev:] if max_ev else all_new_events
            poll_output = {
                "conversationId": args.conversation_id,
                "lastEventId": cursor,
                "newEvents": len(all_new_events),
                "phase": phase_hint,
                "summary": compact_summary,
                "progressDetail": progress_detail,
                "events": output_events,
            }
            result = json.dumps(poll_output, ensure_ascii=False)
            write_output(result, output_path)

        elif args.command == "list-messages":
            messages = list_chat_messages(client, args.conversation_id)
            if args.tail and isinstance(messages, list):
                messages = messages[-args.tail:]
            result = json.dumps(messages, ensure_ascii=False, indent=2, default=str)
            write_output(result, output_path)

    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
