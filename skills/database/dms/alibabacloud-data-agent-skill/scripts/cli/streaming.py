"""SSE event routing and streaming response handling.

Uses a stateful StreamState + event_type->category dispatch architecture,
modelled after the TypeScript transform-chat-message-chunk.ts reference.

Output modes:
  "summary" (default) -- minimal: only conclusion, query result, confirmations,
                        suggestions, reports. Process details suppressed.
  "detail"            -- full: plan progress, status changes, step titles,
                        jupyter cell results, plus everything in summary.
  "raw"               -- every SSE event printed verbatim.

Author: Tinker
Created: 2026-03-03
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from datetime import datetime
import sys
import threading

from cli.log_handler import StructuredLogHandler

# ---------------------------------------------------------------------------
# StreamState — shared mutable state across events within one stream
# ---------------------------------------------------------------------------


@dataclass
class StreamState:
    """Mutable state shared across events within a single SSE stream."""

    # Output mode: "summary" (minimal) | "detail" (full) | "raw"
    output_mode: str = "summary"

    # Accumulated textual output for capturing the final result
    full_output: list[str] = field(default_factory=list)

    # Output directory for saving extracted images etc.
    output_dir: Optional[Path] = None

    # Log handler for process logs (if provided)
    process_log_handler: Optional[StructuredLogHandler] = None

    # Session metadata for structured logging
    session_id: Optional[str] = None
    session_status: Optional[str] = None

    # Last received checkpoint (for checkpoint.txt generation)
    last_checkpoint: Optional[int] = None

    # Cross-event accumulators for content groups
    content_category: Optional[str] = None
    pending_step_label: Optional[str] = None
    output_conclusion_chunks: Optional[list[str]] = None
    tool_call_response_content: Optional[str] = None
    ask_report_render_payload: Optional[dict] = None

    # Stream completion state
    got_content: bool = False
    need_user_confirm: bool = False
    is_attach: bool = False  # True when called from attach command


from cli.formatters import (
    _SKIP_DATA_CATEGORIES,
    _extract_json_objects,
    _fmt_insights,
    _fmt_jupyter_cell,
    _fmt_output_conclusion,
    _fmt_plan_progress,
    _fmt_recommended_questions,
    _fmt_status_change,
    _fmt_task_finish,
    _fmt_ask_report_render,
)
from data_agent import SSEEvent, MessageHandler, DataSource


# Global variables for structured logging
_progress_jsonl_file = None
_progress_log_file = None  # New variable for plain text log
_jsonl_lock = threading.Lock()


def init_structured_logging(output_dir: Optional[Path] = None):
    """Initialize structured logging to plain text format only (progress.jsonl disabled).

    Args:
        output_dir: Directory where progress.log should be created
    """
    global _progress_jsonl_file, _progress_log_file

    if output_dir:
        # Disabled JSONL logging - progress.jsonl creation is skipped
        _progress_jsonl_file = None

        # Only open progress.log if not already set
        if not _progress_log_file:
            log_path = output_dir / "progress.log"
            # In worker processes, stdout is redirected to progress.log,
            # so check if that's the case and reuse that fd
            if hasattr(sys.stdout, 'name') and sys.stdout.name == str(log_path):
                # stdout is already redirected to progress.log, reuse that fd
                _progress_log_file = sys.stdout
            else:
                # In sync mode, open the log file directly
                _progress_log_file = open(log_path, "w", encoding="utf-8")


def close_structured_logging():
    """Close the structured logging files."""
    global _progress_jsonl_file, _progress_log_file

    if _progress_jsonl_file:
        _progress_jsonl_file.close()
        _progress_jsonl_file = None

    # Only close _progress_log_file if it's not sys.stdout (which happens
    # when stdout is redirected to progress.log in worker processes)
    if _progress_log_file and _progress_log_file is not sys.stdout:
        _progress_log_file.close()
        _progress_log_file = None


def write_to_jsonl(data: dict):
    """Write structured data to JSONL file.

    Args:
        data: Dictionary containing structured log data
    """
    # JSONL logging is disabled - do nothing
    pass


def write_to_progress_log(text: str):
    """Write text to progress log file.

    Args:
        text: Text to write to the plain text log
    """
    global _progress_log_file

    # Skip writing if in worker process where stdout is redirected to progress.log
    # This prevents duplication since print() calls already go to the same file
    import os
    if os.environ.get("DATA_AGENT_ASYNC_WORKER") == "1":
        return

    if _progress_log_file:
        _progress_log_file.write(text)
        _progress_log_file.flush()
    else:
        # Debug: log to file if _progress_log_file is None
        debug_file = Path("/tmp/data_agent_debug.log")
        with open(debug_file, "a") as f:
            f.write(f"DEBUG: _progress_log_file is None, cannot write: {text[:50]}...\n")


def _out(state: StreamState, text: str = "", **kwargs) -> None:
    """Print text to console and record it as result output.

    Use for actual Data Agent results that should appear in output.md:
    conclusions, plans, SQL, reports, insights, recommendations, etc.
    """
    # In worker process, force flush after each print for real-time logging
    import os
    if os.environ.get("DATA_AGENT_ASYNC_WORKER") == "1":
        kwargs['flush'] = True

    print(text, **kwargs)
    state.full_output.append(text)

    # Write to progress.log (for both sync and async modes)
    # Skip if in worker process where stdout is redirected to progress.log
    # to prevent duplication
    if os.environ.get("DATA_AGENT_ASYNC_WORKER") != "1" and text.strip():
        progress_text = text + ("\n" if kwargs.get('end', '\n') == '\n' else "")
        write_to_progress_log(progress_text)

    # Write structured log entry to JSONL
    if text.strip():  # Only log non-empty text
        write_to_jsonl({
            'type': 'output',
            'content': text,
            'category': 'result'
        })

    # Also write to process logs if handler is available
    if state.process_log_handler and text.strip():
        state.process_log_handler.write_both(text + ("\n" if kwargs.get('end', '\n') == '\n' else ""))


def _log(state: StreamState, text: str = "", **kwargs) -> None:
    """Print text to console only (progress.log) without recording to output.md.

    Use for diagnostic / process information: user query echo, plan step
    progress, status changes, intermediate code execution results, etc.
    """
    # In worker process, force flush after each print for real-time logging
    import os
    if os.environ.get("DATA_AGENT_ASYNC_WORKER") == "1":
        kwargs['flush'] = True

    print(text, **kwargs)

    # Write to progress.log (for both sync and async modes)
    # Skip if in worker process where stdout is redirected to progress.log
    # to prevent duplication
    if os.environ.get("DATA_AGENT_ASYNC_WORKER") != "1" and text.strip():
        progress_text = text + ("\n" if kwargs.get('end', '\n') == '\n' else "")
        write_to_progress_log(progress_text)

    # Write structured log entry to JSONL
    if text.strip():  # Only log non-empty text
        write_to_jsonl({
            'type': 'log',
            'content': text,
            'category': 'diagnostic'
        })

    # Also write to process logs if handler is available
    if state.process_log_handler and text.strip():
        state.process_log_handler.write_both(text + ("\n" if kwargs.get('end', '\n') == '\n' else ""))


# ---------------------------------------------------------------------------
# StreamState — shared mutable state across events within one stream
# ---------------------------------------------------------------------------

@dataclass
class StreamState:
    """Mutable state shared across events within a single SSE stream."""

    # Output mode: "summary" (minimal) | "detail" (full) | "raw"
    output_mode: str = "summary"

    # Accumulated textual output for capturing the final result
    full_output: list[str] = field(default_factory=list)

    # Output directory for saving extracted images etc.
    output_dir: Optional[Path] = None

    # Log handler for process logs (if provided)
    process_log_handler: Optional[StructuredLogHandler] = None

    # Session ID for user prompts
    session_id: Optional[str] = None
    session_status: Optional[str] = None
    is_attach: bool = False

    # Task / Plan tracking
    current_task: Optional[str] = None
    current_step: Optional[int] = None
    current_plan_status: Optional[str] = None
    total_steps: int = 0
    step_names: dict = field(default_factory=dict)  # {order: name}

    # Pending step label — consumed by next conclusion output (summary mode)
    pending_step_label: Optional[str] = None

    # Current user question (extracted from chat_start)
    current_question: Optional[str] = None

    # content_start / content_finish lifecycle
    content_category: Optional[str] = None

    # Accumulators (between content_start and content_finish)
    output_conclusion_chunks: Optional[list] = None
    tool_call_response_content: str = ""

    # Result flags
    got_content: bool = False
    need_user_confirm: bool = False

    # Turn counter for multi-turn display
    turn_count: int = 0

    # Store current checkpoint for resumption
    last_checkpoint: Optional[int] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------



def _print_event(
    event: SSEEvent,
    output_mode: str = "summary",
    state: Optional[StreamState] = None,
) -> tuple:
    """Route a single SSE event to the appropriate output handler.

    Args:
        event: The SSE event to handle.
        output_mode: "summary" (minimal), "detail" (full), or "raw".
        state: Optional shared StreamState for cross-event tracking.
               When None a temporary state is created (backward compat).

    Returns:
        (got_content: bool, need_user_confirm: bool)
    """
    content = event.content or ""

    if state is not None and event.checkpoint is not None:
        state.last_checkpoint = event.checkpoint
        if state.output_dir:
            try:
                with open(state.output_dir / "checkpoint.txt", "w") as f:
                    f.write(str(event.checkpoint))
            except Exception:
                pass

    # -- raw mode -- (diagnostic, not recorded to output.md)
    if output_mode == "raw":
        cat = f" cat={event.category}" if event.category else ""
        cp = f" cp={event.checkpoint}" if event.checkpoint is not None else ""
        ct = f" ct={event.content_type}" if getattr(event, "content_type", None) else ""
        msg1 = f"[{event.event_type}]{cat}{cp}{ct}"
        if state is not None:
            _log(state, msg1)
        else:
            print(msg1)
        if content:
            preview = content[:600] + ("...(truncated)" if len(content) > 600 else "")
            msg2 = f"  {preview}"
            if state is not None:
                _log(state, msg2)
            else:
                print(msg2)
        return bool(content), False

    # -- summary / detail: delegate to stateful dispatch --
    if state is None:
        state = StreamState(output_mode=output_mode)
    _dispatch_event(state, event)
    return state.got_content, state.need_user_confirm


def _stream_response(
    message_handler: MessageHandler,
    session,
    query: str,
    data_source: Optional[DataSource] = None,
    output_mode: str = "summary",
    output_dir: Optional[Path] = None,
    process_log_handler: Optional[StructuredLogHandler] = None,
    is_attach: bool = False,
) -> tuple[bool, bool, str]:
    """Stream response tokens to stdout in real-time.

    Uses StreamState to track cross-event context (plan progress,
    output_conclusion accumulation, tool_call_response lifecycle).

    Returns (got_content: bool, need_user_confirm: bool, output_text: str).
    """
    state = StreamState(output_mode=output_mode)
    state.output_dir = output_dir
    state.process_log_handler = process_log_handler  # Set the process log handler
    state.session_id = getattr(session, 'session_id', None)
    state.session_status = getattr(session, 'status', None)
    if hasattr(state.session_status, 'value'):
        state.session_status = state.session_status.value
    # IMPORTANT: Set is_attach to True for attach mode
    state.is_attach = is_attach

    # Initialize structured logging if output directory provided
    init_structured_logging(output_dir)

    try:
        for event in message_handler.stream_events(session, query, data_source=data_source):
            # Log SSE event to JSONL (disabled per user request to disable progress.jsonl)
            # write_to_jsonl({
            #     'type': 'sse_event',
            #     'event_type': event.event_type,
            #     'category': event.category,
            #     'content': event.content,
            #     'data': event.data,
            #     'raw_event': asdict(event)
            # })

            if event.event_type == "SSE_FINISH":
                break
            _print_event(event, output_mode, state=state)
    finally:
        # Close structured logging
        close_structured_logging()

    _finalize_stream(state)

    if state.got_content and not state.need_user_confirm:
        _out(state, "")  # final newline after streaming

    full_text = "\n".join(state.full_output)
    return state.got_content, state.need_user_confirm, full_text


def _finalize_stream(state: StreamState) -> None:
    """Flush any pending accumulators when the stream ends."""
    # Flush accumulated output_conclusion that never got a content_finish
    if state.output_conclusion_chunks:
        text = "".join(state.output_conclusion_chunks)
        if text.strip():
            header = _consume_step_label(state)
            _out(state, _fmt_output_conclusion(text, output_dir=state.output_dir, header=header))
            state.got_content = True
        state.output_conclusion_chunks = None

    # Flush accumulated tool_call_response that never got a content_finish
    if state.tool_call_response_content:
        _flush_tool_call_response(state)

    state.content_category = None


def _consume_step_label(state: StreamState) -> Optional[str]:
    """Return and clear the pending step label for use as conclusion header."""
    label = state.pending_step_label
    state.pending_step_label = None
    return label


def _is_user_confirmation_event(event: SSEEvent) -> bool:
    """Check if an SSE event requires user confirmation."""
    if event.event_type == "data":
        data = event.data or {}
        if data.get("need_confirm") or data.get("requires_confirmation"):
            return True
        category = event.category or ""
        if "confirm" in category.lower() or "approval" in category.lower():
            return True
        content = event.content or ""
        confirm_keywords = ["确认", "confirm", "approve", "approval", "需要确认"]
        if any(keyword in content.lower() for keyword in confirm_keywords):
            return True
    return False


# ---------------------------------------------------------------------------
# Dispatch — event_type first-level switch
# ---------------------------------------------------------------------------

def _dispatch_event(state: StreamState, event: SSEEvent) -> None:
    """Main dispatcher: routes by event_type to specialised handlers."""
    et = event.event_type

    if et == "chat_start":
        _handle_chat_start(state, event)
    elif et == "content_start":
        _handle_content_start(state, event)
    elif et == "delta":
        _handle_delta(state, event)
    elif et == "data":
        _handle_data(state, event)
    elif et == "content_finish":
        _handle_content_finish(state, event)
    elif et == "status_change":
        _handle_status_change(state, event)
    elif et == "chat_finish":
        _handle_chat_finish(state, event)
    elif et == "chat_canceled":
        _out(state, "\n[Canceled] 任务已取消")
        state.got_content = True
    elif et == "SSE_FAILURE":
        _handle_sse_failure(state, event)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _handle_chat_start(state: StreamState, event: SSEEvent) -> None:
    """Handle chat_start events — mark the beginning of a new turn."""
    state.turn_count += 1
    # Reset per-turn plan state
    state.current_step = None
    state.current_plan_status = None
    state.pending_step_label = None

    content = event.content or ""
    # Extract user question from JSON payload
    question = ""
    try:
        data = json.loads(content) if isinstance(content, str) else content
        if isinstance(data, dict):
            question = data.get("message", "")
    except (json.JSONDecodeError, TypeError):
        pass

    if question:
        state.current_question = question

    if question:
        _log(state, f"\n> User Query: {question}\n")


def _handle_content_start(state: StreamState, event: SSEEvent) -> None:
    """Set content_category and initialise accumulators."""
    # If previous content never finished, flush it
    if state.content_category == "tool_call_response" and state.tool_call_response_content:
        _flush_tool_call_response(state)
    if state.content_category == "output_conclusion" and state.output_conclusion_chunks:
        text = "".join(state.output_conclusion_chunks)
        if text.strip():
            header = _consume_step_label(state)
            _out(state, _fmt_output_conclusion(text, output_dir=state.output_dir, header=header))
            state.got_content = True
        state.output_conclusion_chunks = None

    state.content_category = event.category

    if event.category == "tool_call_response":
        state.tool_call_response_content = ""
    elif event.category == "output_conclusion":
        state.output_conclusion_chunks = []


def _handle_delta(state: StreamState, event: SSEEvent) -> None:
    """Accumulate delta content based on category."""
    content = event.content or ""
    if not content:
        return

    cat = event.category or ""

    if cat == "tool_call_response":
        state.tool_call_response_content += content
    elif cat == "output_conclusion":
        if state.output_conclusion_chunks is not None:
            state.output_conclusion_chunks.append(content)
    # llm / think / llm_reasoning deltas: silent in summary mode
    # (they are internal reasoning, not shown in CLI)


def _handle_data(state: StreamState, event: SSEEvent) -> None:
    """Second-level dispatch by category for data events."""
    content = event.content or ""
    cat = event.category or ""

    if cat in _SKIP_DATA_CATEGORIES or not content:
        return

    if cat == "ask_plan":
        _handle_ask_plan(state, content)
    elif cat == "plan":
        _handle_data_plan(state, event)
    elif cat == "task_finish":
        _handle_data_task_finish(state, content)
    elif cat == "jsx_report":
        _handle_data_jsx_report(state, content)
    elif cat == "mission_report":
        _handle_data_mission_report(state, content)
    elif cat == "recommended_question":
        out = _fmt_recommended_questions(content)
        if out:
            _out(state, out)
    elif cat == "ask_report_render":
        out = _fmt_ask_report_render(content, getattr(state, "session_id", None))
        if out:
            _out(state, out)
        state.got_content = True
        state.need_user_confirm = True
        return
    elif cat == "output_conclusion":
        # Dual-path: if content_start was received, accumulate; otherwise direct
        if state.output_conclusion_chunks is not None:
            state.output_conclusion_chunks.append(content)
        else:
            # Old format without content_start/content_finish lifecycle
            header = _consume_step_label(state)
            _out(state, _fmt_output_conclusion(content, output_dir=state.output_dir, header=header))
            state.got_content = True
    elif cat == "tool_call_response":
        # data event inside content lifecycle — handled at content_finish
        pass
    else:
        # Fallback: extract title/step from JSON for [Step] display
        _handle_data_fallback(state, content)


def _handle_data_plan(state: StreamState, event: SSEEvent) -> None:
    """Handle data/plan events — show step progress.

    detail mode: full "[Plan] Step n/N: name" with description.
    summary mode: compact progress dot on step change.
    """
    content = event.content or ""
    ct = getattr(event, "content_type", None)
    if ct and ct != "json":
        return

    try:
        data = json.loads(content) if isinstance(content, str) else content
    except (json.JSONDecodeError, TypeError):
        return

    new_step = data.get("current_step")
    new_status = data.get("plan_status")

    # Count total steps from plan data and update step_names
    plans = data.get("plans", [])
    if plans and isinstance(plans[0], dict):
        inner_plan = plans[0].get("plan", {})
        if isinstance(inner_plan, dict):
            steps = inner_plan.get("steps", [])
            if steps:
                state.total_steps = len(steps)
                for idx, s in enumerate(steps, 1):
                    order = s.get("order", idx)
                    name = s.get("name", "")
                    if name:
                        state.step_names[order] = name

    # Only react when step changes
    if new_step is not None and (new_step != state.current_step or new_status != state.current_plan_status):
        state.current_step = new_step
        state.current_plan_status = new_status
        if state.output_mode == "detail":
            out = _fmt_plan_progress(data, new_step, state.total_steps)
            if out:
                _log(state, out, flush=True)
                state.got_content = True
        else:
            # summary: build step label for next conclusion header
            step_name = state.step_names.get(new_step, "")
            total = state.total_steps
            progress = f"Step {new_step}/{total}" if total else f"Step {new_step}"
            if step_name:
                state.pending_step_label = f"{progress}: {step_name}"
            else:
                state.pending_step_label = progress


def _handle_data_task_finish(state: StreamState, content: str) -> None:
    """Handle data/task_finish — structured query result."""
    json_parts = _extract_json_objects(content)
    for _, _, parsed in json_parts:
        if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict) and "title" in parsed[0]:
            out = _fmt_insights(parsed)
            if out:
                _out(state, out)
                state.got_content = True
                return
        elif isinstance(parsed, dict):
            out = _fmt_task_finish(parsed)
            if out:
                _out(state, out)
                state.got_content = True
                return


def _handle_data_jsx_report(state: StreamState, content: str) -> None:
    """Handle data/jsx_report events. Shown in all modes."""
    try:
        data = json.loads(content) if isinstance(content, str) else content
        report_type = data.get("type", "") if isinstance(data, dict) else ""
        _out(state, f"\n### Report Generated" + (f" ({report_type})" if report_type else ""))
    except (json.JSONDecodeError, TypeError):
        _out(state, "\n### Report Generated")


def _handle_data_mission_report(state: StreamState, content: str) -> None:
    """Handle data/mission_report events. Shown in all modes."""
    try:
        data = json.loads(content) if isinstance(content, str) else content
        title = data.get("title", "") if isinstance(data, dict) else ""
        _out(state, f"\n### Task Report Generated" + (f": {title}" if title else ""))
    except (json.JSONDecodeError, TypeError):
        _out(state, "\n### Task Report Generated")


def _handle_data_fallback(state: StreamState, content: str) -> None:
    """Fallback for unrecognised data categories — extract title/step.

    Only shown in detail mode.
    """
    if state.output_mode != "detail":
        return

    json_parts = _extract_json_objects(content)
    for _, _, parsed in json_parts:
        if isinstance(parsed, dict):
            if parsed.get("result_type") == "jupyter_cell":
                out = _fmt_jupyter_cell(parsed)
                if out:
                    _log(state, out, flush=True)
                    state.got_content = True
            elif parsed.get("title"):
                _log(state, f"  [Step] {parsed['title']}", flush=True)
                state.got_content = True
            elif parsed.get("step"):
                _log(state, f"  [Step] {parsed['step']}", flush=True)
                state.got_content = True
            elif parsed.get("status") and parsed.get("message"):
                _log(state, f"  [{parsed['status']}] {parsed['message']}", flush=True)
                state.got_content = True


def _handle_content_finish(state: StreamState, event: SSEEvent) -> None:
    """Flush accumulators when content lifecycle ends."""
    last_category = state.content_category
    state.content_category = None

    if last_category == "tool_call_response" and state.tool_call_response_content:
        _flush_tool_call_response(state)
    elif last_category == "output_conclusion" and state.output_conclusion_chunks is not None:
        text = "".join(state.output_conclusion_chunks)
        if text.strip():
            header = _consume_step_label(state)
            _out(state, _fmt_output_conclusion(text, output_dir=state.output_dir, header=header))
            state.got_content = True
        state.output_conclusion_chunks = None


def _flush_tool_call_response(state: StreamState) -> None:
    """Parse accumulated tool_call_response and format output.

    jupyter_cell results only shown in detail mode.
    """
    raw = state.tool_call_response_content
    state.tool_call_response_content = ""

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return

    result_type = data.get("result_type", "")

    if result_type == "jupyter_cell":
        if state.output_mode != "detail":
            return
        # Re-parse the nested result field for jupyter cell formatting
        result_raw = data.get("result", "")
        try:
            inner = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
        except (json.JSONDecodeError, TypeError):
            inner = result_raw
        if isinstance(inner, dict):
            out = _fmt_jupyter_cell({"result": json.dumps(inner) if not isinstance(result_raw, str) else result_raw, **{k: v for k, v in data.items() if k != "result"}})
            if out:
                _log(state, out, flush=True)
                state.got_content = True
    elif result_type == "plan":
        # Plan results from tool_call_response — parse and display
        result_raw = data.get("result", "")
        try:
            plan_data = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
        except (json.JSONDecodeError, TypeError):
            return
        if isinstance(plan_data, dict):
            _handle_data_plan(state, SSEEvent(
                event_type="data", data={}, category="plan",
                content=json.dumps(plan_data), content_type="json",
            ))
            # Plan generation in tool call needs user confirmation
            if not state.is_attach:
                _out(state, f"\n> ⚠️  Please review the execution plan above. To confirm, DO NOT create a new session, use the existing session:")
                session_id = state.session_id or "<SESSION_ID>"
                _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '确认执行'")
                _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q 'confirm'")
                state.got_content = True
                state.need_user_confirm = True
            else:
                # When in attach mode (plan confirmed), continue processing without setting need_user_confirm
                _out(state, f"\n> ⚠️  Plan confirmed, continuing analysis...")
                state.got_content = True
    elif result_type == "empty":
        pass  # ignore
    # Other result types: silent (no useful CLI output)


def _handle_status_change(state: StreamState, event: SSEEvent) -> None:
    """Handle status_change events. Only visible in detail mode."""
    content = event.content or ""
    ct = getattr(event, "content_type", None)
    if ct and ct != "json":
        return

    # Always track state internally
    try:
        data = json.loads(content) if isinstance(content, str) else content
        if isinstance(data, dict):
            state.current_task = data.get("current_task")
    except (json.JSONDecodeError, TypeError):
        pass

    # Only print in detail mode
    if state.output_mode == "detail":
        out = _fmt_status_change(content)
        if out:
            _log(state, out, flush=True)


def _handle_chat_finish(state: StreamState, event: SSEEvent) -> None:
    """Handle chat_finish events — completions and user confirmations."""
    content = event.content or ""
    cat = event.category or ""

    if cat == "chat":
        q = state.current_question
        is_confirmation = False
        if q:
            q_lower = q.strip().lower()
            exact_confirms = {
                "确认", "confirm", "execute", "同意", "approve", "yes", "y",
                "确认执行", "确认执行当前sql", "同意后续所有sql执行"
            }
            if q_lower in exact_confirms:
                is_confirmation = True

        if q and not is_confirmation:
            # Truncate long questions
            label = q if len(q) <= 40 else q[:37] + "..."
            _out(state, f"\n✅ 「{label}」已完成分析，正在获取生成的报告和中间文件...")
        else:
            _out(state, "\n✅ 分析已完成，正在获取生成的报告和中间文件...")
        state.got_content = True
        return

    if cat == "ask_sql" and content:
        _handle_ask_sql(state, content)
        return

    if cat == "ask_plan" and content:
        _handle_ask_plan(state, content)
        # If in attach mode, ensure need_user_confirm is set to False after plan confirmation
        if state.is_attach:
            state.need_user_confirm = False
        return

    if cat == "ask_human" and content:
        if state.is_attach:
            # When in attach mode, we should continue processing further events
            _out(state, f"\n[Processing human input response]")
            _out(state, f"{content}")
            _out(state, f"\n\u26a0\ufe0f  Continuing analysis after user input...")
            state.got_content = True
            # Do not set need_user_confirm to True as user has responded
            # Explicitly reset need_user_confirm since user has responded
            state.need_user_confirm = False
            return
        _out(state, f"\n[Human Input Required]")
        _out(state, f"{content}")
        _out(state, f"\n\u26a0\ufe0f  Please respond using the existing session (DO NOT create a new session):")
        session_id = state.session_id or "<SESSION_ID>"
        _out(state, f"   python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '<your response>'")
        state.got_content = True
        state.need_user_confirm = True
        return

    if cat == "ask_report_render" and content:
        # Avoid printing ask_report_render again if session status is already WAIT_INPUT, which is handled in attach code
        if state.is_attach:
            # When in attach mode, process the report render request
            out = _fmt_ask_report_render(content, getattr(state, "session_id", None))
            if out:
                _out(state, out)
            _out(state, f"\n\u26a0\ufe0f  Report render confirmed, continuing...")
            state.got_content = True
            # Do not set need_user_confirm to True as user has already responded
            # Explicitly reset need_user_confirm since user has responded
            state.need_user_confirm = False
            return
        out = _fmt_ask_report_render(content, getattr(state, "session_id", None))
        if out:
            _out(state, out)
        state.got_content = True
        state.need_user_confirm = True
        return


def _handle_ask_sql(state: StreamState, content: str) -> None:
    """Format ask_sql confirmation prompt."""
    try:
        data = json.loads(content) if isinstance(content, str) else content
        if isinstance(data, dict):
            sql = data.get("sql", data.get("query", ""))
            question = data.get("question", "")
            explain_result = data.get("explain_result", "")

            if sql:
                _out(state, f"\n### Generated SQL")
                _out(state, f"```sql\n{sql}\n```")
                if question:
                    _out(state, f"\n> **Warning**: {question}")
                if explain_result:
                    _out(state, f"\n#### Explain Result\n{explain_result}")
                if not state.is_attach:
                    session_id = state.session_id or "<SESSION_ID>"
                    _out(state, f"\n> ⚠️  Please review the SQL above.")
                    _out(state, f"> To confirm and execute ONLY this SQL, DO NOT create a new session, use the existing session:")
                    _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '确认执行当前SQL'")
                    _out(state, f"> To agree to execute all subsequent SQL automatically:")
                    _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '同意后续所有SQL执行'")
                    state.got_content = True
                    state.need_user_confirm = True
                return
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback: raw display
    _out(state, f"\n### Generated SQL")
    _out(state, f"```sql\n{content}\n```")
    if not state.is_attach:
        session_id = state.session_id or "<SESSION_ID>"
        _out(state, f"\n> ⚠️  Please review the SQL above.")
        _out(state, f"> To confirm and execute ONLY this SQL, DO NOT create a new session, use the existing session:")
        _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '确认执行当前SQL'")
        _out(state, f"> To agree to execute all subsequent SQL automatically:")
        _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '同意后续所有SQL执行'")
        state.got_content = True
        state.need_user_confirm = True


def _handle_ask_plan(state: StreamState, content: str) -> None:
    """Format ask_plan confirmation prompt."""
    try:
        data = json.loads(content) if isinstance(content, str) else content
        if isinstance(data, dict):
            plans_data = data.get("plans", [])
            plan_id = data.get("plan_id", "")

            _out(state, f"\n### Execution Plan (ID: {plan_id[:16]}...)")

            for plan_item in plans_data:
                plan = plan_item.get("plan", {})
                steps = plan.get("steps", [])
                if steps:
                    state.total_steps = len(steps)
                    for idx, step in enumerate(steps, 1):
                        order = step.get("order", idx)
                        name = step.get("name", "")
                        if name:
                            state.step_names[order] = name
                for step in steps:
                    order = step.get("order", "?")
                    name = step.get("name", "")
                    desc = step.get("description", "")
                    step_type = step.get("type", "")
                    status = step.get("status", "")
                    _out(state, f"\n#### Step {order}: {name}")
                    if step_type:
                        _out(state, f"  Type: {step_type}")
                    if desc:
                        _out(state, f"  Description: {desc}")
                    if status:
                        _out(state, f"  Status: {status}")

            if not state.is_attach:
                _out(state, f"\n> \u26a0\ufe0f  Please review the execution plan above. To confirm, DO NOT create a new session, use the existing session:")
                session_id = state.session_id or "<SESSION_ID>"
                _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '\u786e\u8ba4\u6267\u884c'")
                _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q 'confirm'")
                state.got_content = True
                state.need_user_confirm = True
            else:
                # When in attach mode (plan confirmed), reset the need_user_confirm flag
                # so subsequent steps and results are processed normally
                _out(state, f"\n> \u26a0\ufe0f  Plan confirmed, continuing analysis...")
                state.got_content = True
                # In attach mode, explicitly reset need_user_confirm since user has confirmed
                state.need_user_confirm = False
            return
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback
    _out(state, f"\n### Execution Plan")
    _out(state, f"{content[:1000]}...")
    if not state.is_attach:
        _out(state, f"\n> \u26a0\ufe0f  Please review the plan above. To confirm, DO NOT create a new session, use the existing session:")
        session_id = state.session_id or "<SESSION_ID>"
        _out(state, f">    python3 scripts/data_agent_cli.py attach --session-id {session_id} -q '\u786e\u8ba4\u6267\u884c'")
        state.got_content = True
        state.need_user_confirm = True
    else:
        # In attach mode, indicate that plan was confirmed and continue
        _out(state, f"\n> \u26a0\ufe0f  Plan confirmed, continuing...")
        state.got_content = True
        # In attach mode, explicitly reset need_user_confirm since user has confirmed
        state.need_user_confirm = False


def _handle_sse_failure(state: StreamState, event: SSEEvent) -> None:
    """Handle SSE_FAILURE events."""
    content = event.content or ""
    ct = getattr(event, "content_type", None)

    error_msg = content
    if ct == "json":
        try:
            data = json.loads(content)
            error_msg = data.get("message", data.get("error", content))
        except (json.JSONDecodeError, TypeError):
            pass

    _out(state, f"\n[Error] {error_msg}")
    state.got_content = True
