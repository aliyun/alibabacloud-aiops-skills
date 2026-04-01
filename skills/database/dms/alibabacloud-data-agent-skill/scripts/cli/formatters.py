"""SSE data event formatting helpers for CLI display.

Author: Tinker
Created: 2026-03-04
"""

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any, Optional


# Categories to skip (mirrors SSEClient._SKIP_DATA_CATEGORIES)
_SKIP_DATA_CATEGORIES = {"tool_call_choices", "metric_agent_config"}


def _fmt_jupyter_cell(outer: dict) -> Optional[str]:
    """Format a jupyter_cell data event into human-readable text.

    Decision logic:
    - Parse nb_file_outputs for real content
    - Skip cells whose only outputs are dms/executing placeholders
    - SQL cells: show query + result table
    - Code cells: show stdout only (not the code itself)
    """
    result_raw = outer.get("result", "")
    try:
        inner = json.loads(result_raw) if isinstance(result_raw, str) else result_raw
    except (json.JSONDecodeError, TypeError):
        return None

    title        = inner.get("title", "")
    content_type = inner.get("content_type", "")
    cell_content = inner.get("content", "").strip()

    # Collect real output blocks first; skip this cell entirely if empty
    output_lines = []
    for output in inner.get("nb_file_outputs", []):
        otype    = output.get("output_type", "")
        metadata = output.get("metadata", {})

        # Skip dms/executing placeholders ("正在执行中...")
        if otype == "display_data" and metadata.get("content_type") == "dms/executing":
            continue

        if otype == "display_data":
            app_json = (
                output.get("data", {})
                      .get("application/json", {})
                      .get("data", {})
            )
            columns = app_json.get("columns", [])
            rows    = app_json.get("result", [])
            if columns and rows:
                headers = [c.get("title", c.get("field", "?")) for c in columns]
                output_lines.append("Result:")
                output_lines.append("  " + " | ".join(headers))
                output_lines.append("  " + "-" * max(len(" | ".join(headers)), 30))
                for row in rows:
                    vals = [str(row.get(c["field"], "")) for c in columns]
                    output_lines.append("  " + " | ".join(vals))

        elif otype == "stream":
            text = output.get("text", "").strip()
            if text:
                output_lines.append(f"Output:\n{text}")

    # Nothing real to show -> suppress this cell
    if not output_lines:
        return None

    lines = []
    sep = "-" * 50
    if title:
        lines.append(f"\n{sep}")
        lines.append(f"  {title}")
        lines.append(sep)

    # SQL cells: show the query
    if content_type == "sql" and cell_content:
        lines.append(f"SQL:\n{cell_content}")
    # Code cells: suppress code text, show output only

    lines.extend(output_lines)
    return "\n".join(lines)


def _fmt_task_finish(payload: dict) -> Optional[str]:
    """Format a task_finish data event for structured CLI display (ASK_DATA mode).

    Handles common field layouts returned by the Data Agent:
      - status / taskStatus / state
      - conclusion / summaryResult / summary / answer  (natural language result)
      - sql / sqlList                                   (executed SQL)
      - result / resultData / data                     (table with columns+rows)
    """
    lines: list[str] = []
    lines.append(f"\n### Query Result\n")

    # Status line
    status = (
        payload.get("status")
        or payload.get("taskStatus")
        or payload.get("state")
        or payload.get("taskState")
    )
    if status:
        lines.append(f"  Status : {status}")

    # Natural language conclusion
    conclusion = (
        payload.get("conclusion")
        or payload.get("summaryResult")
        or payload.get("summary")
        or payload.get("answer")
        or payload.get("content")
        or ""
    )
    if conclusion and isinstance(conclusion, str) and conclusion.strip():
        lines.append(f"\n{conclusion.strip()}")

    # SQL
    sql = payload.get("sql")
    if not sql:
        sql_list = payload.get("sqlList") or []
        sql = sql_list[0] if sql_list else None
    if sql and isinstance(sql, str) and sql.strip():
        lines.append(f"\nSQL:\n  {sql.strip()}")

    # Result table
    result = (
        payload.get("result")
        or payload.get("resultData")
        or payload.get("data")
    )
    if isinstance(result, dict):
        raw_cols = result.get("columns", [])
        raw_rows = (
            result.get("data")
            or result.get("rows")
            or result.get("result")
            or []
        )
        if raw_cols and raw_rows:
            # Normalize column spec: may be dicts with title/field or plain strings
            if raw_cols and isinstance(raw_cols[0], dict):
                headers  = [c.get("title", c.get("field", "?")) for c in raw_cols]
                col_keys = [c.get("field", "") for c in raw_cols]
            else:
                headers  = [str(c) for c in raw_cols]
                col_keys = headers

            col_widths = [max(len(h), 6) for h in headers]
            # Calculate widths from data
            for row in raw_rows[:20]:
                if isinstance(row, dict):
                    vals = [str(row.get(k, "")) for k in col_keys]
                elif isinstance(row, (list, tuple)):
                    vals = [str(v) for v in row]
                else:
                    vals = [str(row)]
                for i, v in enumerate(vals[:len(col_widths)]):
                    col_widths[i] = max(col_widths[i], len(v))

            def _row_str(vals: list) -> str:
                padded = [str(v).ljust(col_widths[i]) for i, v in enumerate(vals[:len(col_widths)])]
                return "  " + " | ".join(padded)

            lines.append("")
            lines.append(_row_str(headers))
            lines.append("  " + "-" * (sum(col_widths) + 3 * (len(col_widths) - 1)))
            for row in raw_rows[:20]:  # cap at 20 rows
                if isinstance(row, dict):
                    vals = [str(row.get(k, "")) for k in col_keys]
                elif isinstance(row, (list, tuple)):
                    vals = [str(v) for v in row]
                else:
                    vals = [str(row)]
                lines.append(_row_str(vals))
            if len(raw_rows) > 20:
                lines.append(f"  ... ({len(raw_rows) - 20} more rows)")

    # If we only produced the header/sep with no real content, suppress
    content_lines = [l for l in lines if l.strip() and l.strip() != "### Query Result"]
    return "\n".join(lines) if content_lines else None


def _fmt_insights(items: list) -> Optional[str]:
    """Format a list of insight objects (final conclusion)."""
    lines = ["\n## Analysis Result\n"]
    for item in items:
        title   = item.get("title", "")
        summary = item.get("summary", "")
        if title:
            lines.append(f"\n{title}")
        if summary:
            lines.append(f"  {summary}")
        # Inline data table if present
        data_payload = item.get("data")
        if isinstance(data_payload, str):
            try:
                data_payload = json.loads(data_payload)
            except (json.JSONDecodeError, TypeError):
                data_payload = None
        if isinstance(data_payload, dict):
            columns = data_payload.get("columns", [])
            rows    = data_payload.get("data", [])
            if columns and rows:
                lines.append("  " + " | ".join(str(c) for c in columns))
                lines.append("  " + "-" * 40)
                for row in rows[:10]:  # cap at 10 rows
                    lines.append("  " + " | ".join(str(v) for v in row))
    return "\n".join(lines)


def _extract_json_objects(content: str) -> list:
    """Extract all JSON objects/arrays from a mixed content string.

    Handles cases like:
    - Plain text before JSON: "some text {...}"
    - Multiple JSONs concatenated: '{"a":1}{"b":2}'
    - Text between JSONs: '{...} text {...}'

    Returns list of (start, end, parsed_json) tuples.
    """
    results = []
    i = 0
    while i < len(content):
        # Find start of JSON object or array
        if content[i] in ('{', '['):
            start = i
            try:
                parsed, end = json.JSONDecoder().raw_decode(content, i)
                results.append((start, end, parsed))
                i = end
            except json.JSONDecodeError:
                i += 1
        else:
            i += 1
    return results


def _format_data_event(content: str) -> Optional[str]:
    """Parse and format a data event's content for CLI display.

    Returns a formatted string to print, or None to suppress the event.
    """
    content = content.strip()
    if not content:
        return None

    # Try to extract all JSON objects/arrays from content
    json_parts = _extract_json_objects(content)

    if not json_parts:
        # No JSON found, return as plain text
        return content

    # If entire content is a single JSON, format it
    if len(json_parts) == 1 and json_parts[0][0] == 0 and json_parts[0][1] == len(content):
        parsed = json_parts[0][2]
        return _format_parsed_json(parsed)

    # Multiple JSONs or mixed text+JSON
    # Format each JSON part and collect results
    formatted_parts = []
    prev_end = 0
    for start, end, parsed in json_parts:
        # Text before this JSON (if any)
        if start > prev_end:
            text_before = content[prev_end:start].strip()
            if text_before:
                formatted_parts.append(text_before)
        # Format the JSON
        formatted = _format_parsed_json(parsed)
        if formatted:
            formatted_parts.append(formatted)
        prev_end = end

    # Text after last JSON (if any)
    if prev_end < len(content):
        text_after = content[prev_end:].strip()
        if text_after:
            formatted_parts.append(text_after)

    return "\n".join(formatted_parts) if formatted_parts else None


def _format_parsed_json(parsed) -> Optional[str]:
    """Format a parsed JSON value (dict or list) for display."""
    # List -> final insights / conclusion
    if isinstance(parsed, list):
        if parsed and isinstance(parsed[0], dict) and "title" in parsed[0]:
            return _fmt_insights(parsed)
        # Unknown list type - check if it's table summaries
        if parsed and isinstance(parsed[0], dict) and "table_name" in parsed[0]:
            return _fmt_table_summaries(parsed)
        return None  # suppress other lists

    # Dict
    if isinstance(parsed, dict):
        result_type = parsed.get("result_type")
        if result_type == "jupyter_cell":
            return _fmt_jupyter_cell(parsed)
        return None  # other tool metadata, suppress

    return None


def _fmt_table_summaries(items: list) -> Optional[str]:
    """Format table summary list for display."""
    lines = ["\n### Table Summaries\n"]
    for item in items:
        table_name = item.get("table_name", "?")
        summary = item.get("table_summary", "")
        lines.append(f"\n{table_name}:")
        if summary:
            # Wrap long summaries
            words = summary.split()
            line = "  "
            for word in words:
                if len(line) + len(word) + 1 > 70:
                    lines.append(line)
                    line = "  " + word
                else:
                    line += (" " if line != "  " else "") + word
            if line.strip():
                lines.append(line)
    lines.append(sep)
    return "\n".join(lines)


def _fmt_plan_progress(plan_data: dict, current_step: int, total_steps: int) -> Optional[str]:
    """Format a plan data event showing step progress.

    Expected plan_data structure (from API):
      {"current_step": 2, "plan_status": "...", "plans": [{"plan": {"steps": [...]}}]}

    Each step has "name" and optionally "description".
    """
    steps = []
    plans = plan_data.get("plans", [])
    if plans and isinstance(plans[0], dict):
        inner_plan = plans[0].get("plan", {})
        if isinstance(inner_plan, dict):
            steps = inner_plan.get("steps", [])

    step_name = ""
    step_desc = ""
    # current_step is 1-based from API
    if steps and 0 < current_step <= len(steps):
        step = steps[current_step - 1]
        step_name = step.get("name", "")
        step_desc = step.get("description", "")

    label = f"[Plan] Step {current_step}/{total_steps}"
    if step_name:
        label += f": {step_name}"
    lines = [label]
    if step_desc:
        lines.append(f"  {step_desc}")
    return "\n".join(lines)


def _fmt_status_change(content: str) -> Optional[str]:
    """Format a status_change event's JSON content.

    Expected JSON: {"previous": "PLANNING", "current": "STEP_EXECUTION", "current_task": "..."}
    """
    try:
        data = json.loads(content) if isinstance(content, str) else content
    except (json.JSONDecodeError, TypeError):
        return None

    previous = data.get("previous", "none")
    current = data.get("current", "none")
    current_task = data.get("current_task", "")

    line = f"[Task] {previous} \u2192 {current}"
    if current_task and current_task != current:
        line += f" ({current_task})"
    return line


def _fmt_output_conclusion(text: str, output_dir: Optional[Path] = None, header: Optional[str] = None) -> str:
    """Wrap analysis conclusion text with visual borders.

    If output_dir is provided, extracts inline base64 images from the text,
    saves them to output_dir/images/, and replaces inline data with file paths.
    If header is provided, use it instead of the default "Analysis Conclusion".
    """
    if output_dir is not None:
        text = _extract_and_save_images(text, output_dir)
    title = header or "Analysis Conclusion"
    return f"\n## {title}\n\n{text}\n"


# Regex for markdown inline images with base64 data URIs:
#   ![alt](data:image/png;base64,AAAA...)
_BASE64_IMG_RE = re.compile(
    r"!\[([^\]]*)\]"                       # ![alt text]
    r"\("                                  # (
    r"data:image/([a-zA-Z0-9.+-]+)"        # data:image/png
    r";base64,"                            # ;base64,
    r"([A-Za-z0-9+/=\s]+)"                # base64 payload (may contain whitespace)
    r"\s*\)"                               # )
)


def _extract_and_save_images(text: str, output_dir: Path, prefix: str = "conclusion") -> str:
    """Extract inline base64 images from text and save to disk.

    Returns cleaned text with images replaced by file-path references.
    """
    img_dir = output_dir / "images"
    counter = 0

    def _replace(match: re.Match) -> str:
        nonlocal counter
        counter += 1
        alt = match.group(1) or f"image_{counter}"
        mime_subtype = match.group(2).lower()  # png, jpeg, svg+xml, etc.
        b64_data = match.group(3).strip()

        # Determine file extension
        ext = _mime_subtype_to_ext(mime_subtype)
        filename = f"{prefix}_{counter}{ext}"
        save_path = img_dir / filename

        try:
            img_dir.mkdir(parents=True, exist_ok=True)
            raw = base64.b64decode(b64_data)
            save_path.write_bytes(raw)
            return f"![{alt}]({save_path.resolve()})"
        except Exception:
            return f"![{alt}](save_failed)"

    return _BASE64_IMG_RE.sub(_replace, text)


def _mime_subtype_to_ext(subtype: str) -> str:
    """Map image MIME subtype to file extension."""
    mapping = {
        "png": ".png",
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "gif": ".gif",
        "svg+xml": ".svg",
        "webp": ".webp",
        "bmp": ".bmp",
        "tiff": ".tiff",
    }
    return mapping.get(subtype, f".{subtype.split('+')[0]}")


def _fmt_recommended_questions(content: str) -> Optional[str]:
    """Format recommended follow-up questions.

    Expected JSON: {"questions": ["q1", "q2", ...]} or a list of strings.
    """
    try:
        data = json.loads(content) if isinstance(content, str) else content
    except (json.JSONDecodeError, TypeError):
        return None

    questions = []
    if isinstance(data, dict):
        questions = data.get("questions", [])
        if not questions:
            questions = data.get("recommendQuestions", [])
    elif isinstance(data, list):
        questions = data

    if not questions:
        return None

    lines = ["\n### Suggestions"]
    for i, q in enumerate(questions[:5], 1):
        text = q.get("question", q) if isinstance(q, dict) else str(q)
        lines.append(f"  {i}. {text}")
    return "\n".join(lines)


def _fmt_ask_report_render(content: str, session_id: Optional[str] = None) -> Optional[str]:
    """Format ask_report_render confirmation prompt."""
    lines = ["\n### Report Render"]

    # Try to parse as JSON first in case it has a 'message' field
    display_text = content
    try:
        data = json.loads(content) if isinstance(content, str) else content
        if isinstance(data, dict) and "message" in data:
            display_text = data["message"]
    except (json.JSONDecodeError, TypeError):
        pass

    preview = display_text[:500] + ("..." if len(display_text) > 500 else "")
    lines.append(f"  {preview}")

    sid = session_id or "<SESSION_ID>"
    lines.append(f"\n> ⚠️  Please review the report rendering request.")
    lines.append(f"> To confirm you want to render the report, DO NOT create a new session, use the existing session and explicitly say yes:")
    lines.append(f">    python3 scripts/data_agent_cli.py attach --session-id {sid} -q '确认绘制网页报告'")
    lines.append(f">    python3 scripts/data_agent_cli.py attach --session-id {sid} -q 'yes, render the report'")
    lines.append(f"> To decline, simply respond with no:")
    lines.append(f">    python3 scripts/data_agent_cli.py attach --session-id {sid} -q '不绘制'")

    return "\n".join(lines)
