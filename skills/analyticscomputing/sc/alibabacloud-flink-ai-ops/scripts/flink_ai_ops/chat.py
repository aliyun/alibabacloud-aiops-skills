"""Validate assistant requests and collect one non-replayed SSE conversation."""

import asyncio
from copy import deepcopy

from .common import (
    OpsError, add_body_arguments, positive_number, positive_seconds,
    validate_object, validate_string,
)
from .sse import finish_stream


def _invalid(message):
    raise OpsError("INVALID_ARGUMENT", message)


def validate_chat_body(body, confirm=False):
    """Return a validated copy, rejecting unknown fields rather than dropping them."""
    validate_object(body, "body", {"userMessage", "sessionId", "refs", "hitlDecisions"}, code="INVALID_ARGUMENT")
    if not isinstance(confirm, bool):
        _invalid("confirm must be a boolean.")

    if "userMessage" in body:
        message = body["userMessage"]
        if not isinstance(message, str) or not 1 <= len(message) <= 64000:
            _invalid("userMessage must be a string of 1 to 64000 characters.")
    if "sessionId" in body:
        validate_string(body["sessionId"], "sessionId", code="INVALID_ARGUMENT")

    if "refs" in body:
        refs = body["refs"]
        validate_object(refs, "refs", {"jobs", "skills"}, code="INVALID_ARGUMENT")
        if "jobs" in refs:
            if not isinstance(refs["jobs"], list):
                _invalid("refs.jobs must be an array.")
            for index, job in enumerate(refs["jobs"]):
                name = f"refs.jobs[{index}]"
                validate_object(job, name, {"deploymentId", "jobId"}, code="INVALID_ARGUMENT")
                if not job:
                    _invalid(f"{name} must provide deploymentId or jobId.")
                for field, value in job.items():
                    validate_string(value, f"{name}.{field}", code="INVALID_ARGUMENT")
        if "skills" in refs:
            if not isinstance(refs["skills"], list):
                _invalid("refs.skills must be an array.")
            for index, skill in enumerate(refs["skills"]):
                validate_string(skill, f"refs.skills[{index}]", code="INVALID_ARGUMENT")

    decisions = body.get("hitlDecisions", [])
    if not isinstance(decisions, list):
        _invalid("hitlDecisions must be an array.")
    seen_ids = set()
    has_approval = False
    for index, decision in enumerate(decisions):
        name = f"hitlDecisions[{index}]"
        validate_object(decision, name, {"hitlId", "decision"}, code="INVALID_ARGUMENT")
        validate_string(decision.get("hitlId"), f"{name}.hitlId", code="INVALID_ARGUMENT")
        if decision.get("decision") not in ("approve", "deny"):
            _invalid(f"{name}.decision must be approve or deny.")
        if decision["hitlId"] in seen_ids:
            _invalid(f"{name}.hitlId is duplicated; the approval decision is not unique.")
        seen_ids.add(decision["hitlId"])
        has_approval = has_approval or decision["decision"] == "approve"

    if decisions and "sessionId" not in body:
        _invalid("Continuing HITL approvals requires sessionId.")
    if "userMessage" not in body and not decisions:
        _invalid("A first conversation requires userMessage; HITL continuation requires a non-empty hitlDecisions.")
    if has_approval and not confirm:
        raise OpsError("CONFIRMATION_REQUIRED", "Approving HITL operations requires an explicit --confirm.")
    return deepcopy(body)


class _KeyboardInterrupted(Exception):
    """Keep KeyboardInterrupt inside the collector task until its caller handles it."""


async def run_chat(api, body, confirm=False, timeout=300):
    """Collect a single stream and carry partial results in every streaming error."""
    request_body = validate_chat_body(body, confirm=confirm)
    positive_number(timeout, "timeout", code="INVALID_ARGUMENT")

    data = {
        "sessionId": request_body.get("sessionId"),
        "events": [],
        "text": "",
        "pendingApprovals": [],
        "usage": {},
        "streamComplete": False,
        "status": "streaming",
        "operationVerified": False,
    }
    failures = []
    tool_calls = {}
    tool_results = {}

    async def collect():
        stream = None
        primary = None
        try:
            stream = api.chat(request_body)
            async for envelope in stream:
                data["events"].append(deepcopy(envelope))
                if not isinstance(envelope, dict) or not isinstance(envelope.get("body"), dict):
                    raise OpsError("INVALID_RESPONSE", "The assistant stream event or body is not a JSON object.")
                event_body = envelope["body"]
                event_types = (envelope.get("event"), event_body.get("event"))
                event_session = event_body.get("sessionId")
                if isinstance(event_session, str) and event_session.strip():
                    if data["sessionId"] is not None and event_session != data["sessionId"]:
                        raise OpsError("INVALID_RESPONSE", "The assistant stream changed the sessionId mid-conversation.")
                    data["sessionId"] = event_session
                if isinstance(event_body.get("text"), str):
                    data["text"] += event_body["text"]
                if "usage" in event_body:
                    data["usage"] = deepcopy(event_body["usage"])

                # The JSON event identifies the tool event. Older streams can use the SSE name.
                tool_event = next((event for event in reversed(event_types)
                                   if event in ("toolCall", "toolResult")), None)
                if tool_event is not None:
                    tool_id = event_body.get("toolCallId")
                    validate_string(tool_id, f"{tool_event}.toolCallId", code="INVALID_RESPONSE")
                    tracked = tool_calls if tool_event == "toolCall" else tool_results
                    tracked[tool_id] = None

                tool_failed = event_body.get("success") is False or (
                    isinstance(event_body.get("success"), str)
                    and event_body["success"].strip().lower() == "false"
                )
                if "error" in event_types or tool_failed:
                    failures.append(
                        {
                            "eventIndex": len(data["events"]) - 1,
                            "event": event_body.get("event", envelope.get("event")),
                            **{
                                key: deepcopy(event_body[key])
                                for key in ("toolCallId", "toolName", "errorType", "errorMessage", "message")
                                if key in event_body
                            },
                        }
                    )
                if "hitlPending" in event_types:
                    items = event_body.get("items")
                    if not isinstance(items, list) or not items:
                        raise OpsError("INVALID_RESPONSE", "hitlPending.items must be a non-empty array.")
                    if data["sessionId"] is None:
                        raise OpsError("INVALID_RESPONSE", "hitlPending requires a known sessionId.")
                    pending_ids = set()
                    for index, item in enumerate(items):
                        name = f"hitlPending.items[{index}]"
                        if not isinstance(item, dict):
                            raise OpsError("INVALID_RESPONSE", f"{name} must be a JSON object.")
                        validate_string(item.get("hitlId"), f"{name}.hitlId", code="INVALID_RESPONSE")
                        if item["hitlId"] in pending_ids:
                            raise OpsError("INVALID_RESPONSE", f"{name}.hitlId is duplicated in hitlPending.items.")
                        pending_ids.add(item["hitlId"])
                    data["pendingApprovals"] = deepcopy(items)
                    data["status"] = "failed" if failures else "pending"
                    return
            data["streamComplete"] = True
            data["status"] = "completed"
        except BaseException as exc:
            primary = exc
            if isinstance(exc, KeyboardInterrupt):
                primary = _KeyboardInterrupted()
                primary.cleanup_errors = getattr(exc, "cleanup_errors", [])
                raise primary from exc
            raise
        finally:
            unpaired_calls = [tool_id for tool_id in tool_calls if tool_id not in tool_results]
            if unpaired_calls:
                data["unpairedToolCallIds"] = unpaired_calls
            # A continuation can report results for calls made in a previous stream.
            if "sessionId" not in request_body:
                unpaired_results = [tool_id for tool_id in tool_results if tool_id not in tool_calls]
                if unpaired_results:
                    data["unpairedToolResultIds"] = unpaired_results
            if failures:
                data["failures"] = failures
            await finish_stream(stream, primary=primary,
                                request_id=getattr(api, "last_request_id", ""))
            if primary is not None and getattr(primary, "cleanup_errors", None):
                data["cleanupErrors"] = deepcopy(primary.cleanup_errors)

    try:
        await asyncio.wait_for(collect(), timeout=timeout)
    except asyncio.TimeoutError as exc:
        data["status"] = "interrupted"
        data["interruptionReason"] = "timeout"
        raise OpsError("CHAT_TIMEOUT", "Assistant stream read timed out; the current session and events are kept. Do not automatically replay the request.", data=data) from exc
    except (asyncio.CancelledError, KeyboardInterrupt, _KeyboardInterrupted) as exc:
        data["status"] = "interrupted"
        data["interruptionReason"] = "cancelled" if isinstance(exc, asyncio.CancelledError) else "keyboardInterrupt"
        raise OpsError("CHAT_INTERRUPTED", "Assistant stream read was interrupted; the current session and events are kept. Do not automatically replay the request.", data=data) from exc
    except OpsError as exc:
        data["status"] = "failed"
        if exc.data is not None:
            data["streamError"] = deepcopy(exc.data)
        raise OpsError(exc.code, getattr(exc, "message", str(exc)), request_id=getattr(exc, "request_id", ""), data=data) from exc
    except Exception as exc:
        data["status"] = "failed"
        raise OpsError("CHAT_STREAM_ERROR", f"Assistant stream read failed: {exc}; the current session and events are kept. Do not automatically replay the request.", data=data) from exc

    if not data["events"]:
        data["status"] = "failed"
        raise OpsError("CHAT_EMPTY_STREAM", "The assistant returned an empty event stream; the conversation cannot be confirmed complete.", data=data)
    if failures:
        data["status"] = "failed"
        raise OpsError("CHAT_FAILED", "The assistant returned an error event or a tool execution failed; inspect the full event record.", data=data)
    if data["streamComplete"] and (data.get("unpairedToolCallIds") or data.get("unpairedToolResultIds")):
        data["status"] = "failed"
        raise OpsError("CHAT_INCOMPLETE_STREAM", "The stream ended with unpaired tool events; inspect the saved evidence before continuing.", data=data)
    return data


def _prepare_cli(args, body):
    """Validate approvals before the CLI constructs credentials or a client."""
    return {"body": validate_chat_body(body, confirm=args.confirm),
            "confirm": args.confirm, "timeout": args.timeout}


def compact_chat_output(data):
    """Copy redacted evidence, removing only provably duplicated plain text."""
    result = deepcopy(data)
    if not isinstance(result, dict) or not isinstance(result.get("events"), list):
        return result
    if not isinstance(result.get("text"), str):
        return result

    transcript = "".join(
        envelope["body"]["text"] for envelope in result["events"]
        if isinstance(envelope, dict) and isinstance(envelope.get("body"), dict)
        and isinstance(envelope["body"].get("text"), str)
    )
    if transcript != result["text"]:
        return result

    for envelope in result["events"]:
        if not isinstance(envelope, dict) or set(envelope) - {"id", "event", "body"}:
            continue
        body = envelope.get("body")
        if not isinstance(body, dict) or set(body) - {"event", "text", "sessionId", "completed"}:
            continue
        if envelope.get("event") not in ("message", "text"):
            continue
        if body.get("event", envelope.get("event")) == "text" and isinstance(body.get("text"), str):
            del body["text"]
    return result


def register(subparsers, common_parser):
    """Register the assistant workflow without coupling CLI dispatch to its name."""
    command = subparsers.add_parser(
        "chat_ai_agent", parents=[common_parser],
        help="AI assistant conversation, multi-turn continuation, and per-item HITL approvals.",
        description="AI assistant conversation, multi-turn continuation, and per-item HITL approvals.",
    )
    add_body_arguments(command)
    command.add_argument("--timeout", type=positive_seconds, default=300,
                         help="Total SSE collection time limit for this round in seconds, default 300.")
    command.add_argument("--compact", action="store_true",
                         help="Trim plain-text event fragments duplicated by the aggregated text in the output, keeping event order and full business evidence.")
    command.set_defaults(prepare=_prepare_cli, execute=run_chat)
