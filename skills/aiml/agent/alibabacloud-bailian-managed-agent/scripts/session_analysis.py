#!/usr/bin/env python3
"""Offline evidence summaries for Managed Agent sessions; never makes cloud calls.

Analyze chronological, completed Event List results, not raw SSE fragments. The
caller must confirm pagination and filter coverage with --events-complete.
Outputs contain references and hashes rather than prompts, tool outputs or secrets.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import sys


SCHEMA = "managed-agent-session-analysis/v1"
STARTS = {"tool_call": "tool", "function_call": "function", "mcp_call": "mcp",
          "model_request_start": "model"}
ENDS = {"tool_call_output": "tool", "function_call_output": "function",
        "mcp_call_output": "mcp", "model_request_end": "model"}
METRICS = ("active_seconds", "duration_seconds", "input_tokens", "output_tokens",
           "cache_read_input_tokens", "cache_creation_input_tokens",
           "ordinary_input_tokens", "total_tokens", "cache_read_ratio")


def fingerprint(value):
    if value is None:
        return None
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def number(value):
    return value if (isinstance(value, (int, float)) and not isinstance(value, bool)
                     and math.isfinite(value) and value >= 0) else None


def version_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str) and value.strip():
        value = value.strip()
        return int(value) if value.isdecimal() else value
    return None


def blocks(event):
    content = event.get("content", [])
    return [b["data"] for b in content if isinstance(b, dict)
            and isinstance(b.get("data"), dict)] if isinstance(content, list) else []


def field(event, key):
    for source in [event, *blocks(event), event.get("metadata")]:
        if isinstance(source, dict) and source.get(key) is not None:
            return source[key]
    return None


def thread(event):
    values = linkage_values(event, ("session_thread_id", "thread_id"))
    return next(iter(values)) if len(values) == 1 else None


def linkage_values(event, keys):
    return {source[key] for source in [event, *blocks(event), event.get("metadata")]
            if isinstance(source, dict) for key in keys
            if isinstance(source.get(key), str) and source[key]}


def timestamp(value):
    # Numeric epochs have ambiguous units across exports; do not guess.
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.timestamp() if parsed.tzinfo else None
    except ValueError:
        return None


def event_pages(payload):
    """Accept arrays/envelopes; explicit truncated/has_more/coverage flags win."""
    if isinstance(payload, list):
        return payload, None, False
    if not isinstance(payload, dict):
        raise ValueError("Events must be an array or a data/items/pages object")
    coverage = payload.get("coverage")
    incomplete = (payload.get("truncated") is True or payload.get("has_more") is True
                  or (isinstance(coverage, dict) and coverage.get("events_complete") is False))
    if "pages" in payload:
        pages = payload["pages"]
        if not isinstance(pages, list) or not pages:
            raise ValueError("pages must be a nonempty ordered array of responses")
        rows = []
        for page in pages:
            batch, cursor, page_incomplete = event_pages(page)
            incomplete = incomplete or page_incomplete
            rows.extend(batch)
        return rows, cursor, incomplete
    for key in ("data", "items"):
        if isinstance(payload.get(key), list):
            return payload[key], payload.get("next_page"), incomplete
        if isinstance(payload.get(key), dict):
            rows, cursor, nested_incomplete = event_pages(payload[key])
            return rows, payload.get("next_page") or cursor, incomplete or nested_incomplete
    raise ValueError("No events array found; extract Event List output first")


def outcome(status, reason):
    kind = reason.get("type") if isinstance(reason, dict) else None
    if status == "terminated":
        return "terminated"
    if status == "idle" and kind == "requires_action":
        return "requires_action"
    if status == "idle" and kind == "end_turn":
        return "end_turn"
    if kind == "retries_exhausted":
        return "failed"
    if status in ("running", "rescheduling"):
        return "in_progress"
    return "unknown"


def analyze(session, payload, events_complete=False):
    if isinstance(session, dict) and isinstance(session.get("data"), dict):
        session = session["data"]
    if not isinstance(session, dict):
        raise ValueError("Session must be an object")
    rows, cursor, declared_incomplete = event_pages(payload)
    warnings = []
    events, positions = [], {}
    duplicates = partials = conflicts = 0
    for event in rows:
        if not isinstance(event, dict):
            raise ValueError("Each event must be an object")
        if (event.get("object") == "content" or event.get("status") == "in_progress"
                or event.get("type") in ("event_start", "event_delta")):
            partials += 1
            continue
        eid = event.get("id")
        if eid is not None and not isinstance(eid, str):
            raise ValueError("Event IDs must be strings")
        if eid and eid in positions:
            duplicates += 1
            position = positions[eid]
            conflicts += events[position] != event
            events[position] = event
        else:
            if eid:
                positions[eid] = len(events)
            events.append(event)
    complete = bool(events_complete and not cursor and not partials and not conflicts and not declared_incomplete)
    if not complete:
        warnings.append("History completeness is unverified; counts cover observed events only.")
    if cursor:
        warnings.append("The last page has next_page; more history remains even if data is empty.")
    if declared_incomplete:
        warnings.append("The export explicitly declares truncated/has_more/coverage.events_complete=false.")
    if conflicts:
        warnings.append("Duplicate event IDs have conflicting snapshots; latest supplied snapshot retained.")
    if partials:
        warnings.append("SSE partial frames were excluded; retrieve completed Event List history.")
    if any(not event.get("id") for event in events):
        warnings.append("Some events lack IDs and cannot be deduplicated; observed counts may include duplicates.")
    times = [timestamp(e.get("created_at")) for e in events]
    known_times = [t for t in times if t is not None]
    chronological = all(a <= b for a, b in zip(known_times, known_times[1:]))
    if not chronological:
        warnings.append("History is not chronological; order-sensitive outcome is unavailable.")

    stats = session.get("stats") or {}
    usage = session.get("usage") or {}
    if not isinstance(stats, dict) or not isinstance(usage, dict):
        raise ValueError("Session stats and usage must be objects when present")
    metrics = {key: number((stats if key.endswith("seconds") else usage).get(key))
               for key in METRICS[:6]}
    # Include both cache counters; cache is already part of total input tokens.
    metrics["cache_creation_input_tokens"] = number(usage.get("cache_creation_input_tokens"))
    inp, out = metrics["input_tokens"], metrics["output_tokens"]
    read, creation = metrics["cache_read_input_tokens"], metrics["cache_creation_input_tokens"]
    metrics["ordinary_input_tokens"] = (inp - read - creation
        if all(v is not None for v in (inp, read, creation)) else None)
    if metrics["ordinary_input_tokens"] is not None and metrics["ordinary_input_tokens"] < 0:
        warnings.append("Cache counters exceed input_tokens; token accounting is inconsistent.")
        metrics["ordinary_input_tokens"] = None
    metrics["total_tokens"] = inp + out if inp is not None and out is not None else None
    metrics["cache_read_ratio"] = read / inp if inp and read is not None and read <= inp else None

    scoped_statuses = [e for e in events if e.get("type") == "session_status"
                       and linkage_values(e, ("session_thread_id", "thread_id"))]
    if scoped_statuses:
        warnings.append("Thread-scoped status events cannot establish session-wide completion; use a Session snapshot.")
    status_events = [(index, e, data) for index, e in enumerate(events)
                     if e.get("type") == "session_status"
                     and not linkage_values(e, ("session_thread_id", "thread_id"))
                     for data in blocks(e) if "session_status" in data]
    latest_status = status_events[-1] if status_events and chronological else None
    new_work = bool(latest_status and any(
            e.get("type") in STARTS or (e.get("type") == "message" and e.get("role") in ("user", "system"))
            for e in events[latest_status[0] + 1:]))
    if new_work:
        warnings.append("New work follows the last history state; it cannot establish this turn's outcome.")
        latest_status = None
    history_state = latest_status[1:] if latest_status else None
    has_snapshot = session.get("status") is not None
    status = session.get("status") if has_snapshot else (
        history_state[1].get("session_status") if history_state else None)
    reason = session.get("stop_reason") if has_snapshot else (
        history_state[1].get("stop_reason") if history_state else None)
    state_conflict = bool((has_snapshot and history_state and (
            outcome(status, reason) != outcome(history_state[1].get("session_status"),
                                               history_state[1].get("stop_reason"))))
                          or (has_snapshot and new_work and outcome(status, reason) == "end_turn"))
    if state_conflict:
        warnings.append("Session snapshot and last history state disagree; reconcile capture times.")
    reason = reason if isinstance(reason, dict) else {}
    observed_outcome = outcome(status, reason)

    grouped = defaultdict(lambda: {"starts": [], "ends": []})
    unlinked, errors = [], []
    models = set()
    for event in events:
        kind = event.get("type")
        if kind in STARTS or kind in ENDS:
            call_ids = linkage_values(event, ("call_id",))
            tids = linkage_values(event, ("thread_id", "session_thread_id"))
            if len(call_ids) != 1 or len(tids) != 1:
                unlinked.append({"event_id": event.get("id"), "type": kind,
                                 "reason": "missing_or_conflicting_call_id_or_thread"})
            else:
                call_id = next(iter(call_ids))
                family = STARTS.get(kind) or ENDS[kind]
                grouped[(family, thread(event), call_id)]["starts" if kind in STARTS else "ends"].append(event)
        if kind in ("model_request_start", "model_request_end"):
            model = field(event, "model")
            if isinstance(model, str):
                models.add(model)
        if kind == "error" or event.get("is_error") is True or field(event, "is_error") is True:
            error = event.get("error") or field(event, "error") or {}
            errors.append({"event_id": event.get("id"), "type": kind,
                           "code": error.get("code") if isinstance(error, dict) else None})
    calls = []
    for (family, tid, call_id), pair in grouped.items():
        starts, ends = pair["starts"], pair["ends"]
        paired = len(starts) == len(ends) == 1
        start = timestamp(starts[0].get("created_at")) if paired else None
        end = timestamp(ends[0].get("created_at")) if paired else None
        calls.append({"family": family, "thread_id": tid, "call_id": call_id,
                      "start_event_ids": [e.get("id") for e in starts],
                      "end_event_ids": [e.get("id") for e in ends],
                      "pairing": "paired" if paired else "unmatched_or_ambiguous",
                      "observed_seconds": end - start if (start is not None and end is not None
                                                           and end >= start) else None})
    inputs = [{"role": e.get("role"), "content": e.get("content")}
              for e in events if e.get("type") == "message" and e.get("role") in ("user", "system")]
    agent = session.get("agent")
    snapshot_version = version_value(agent.get("version")) if isinstance(agent, dict) else None
    top_level_version = version_value(session.get("agent_version"))
    agent_version = snapshot_version if snapshot_version is not None else top_level_version
    version_conflict = (snapshot_version is not None and top_level_version is not None
                        and snapshot_version != top_level_version)
    if version_conflict:
        warnings.append("Embedded Agent snapshot version conflicts with top-level agent_version; snapshot takes precedence and comparison needs reconciliation.")
    if isinstance(agent, dict):
        agent = {k: agent[k] for k in ("id", "version") if isinstance(agent.get(k), (str, int))}
    return {
        "schema": SCHEMA,
        "session_id": session.get("id"),
        "coverage": {"events_complete": complete, "caller_confirmed_complete": events_complete,
                     "export_declared_incomplete": declared_incomplete,
                     "next_page_present": bool(cursor), "received_count": len(rows),
                     "observed_count": len(events), "duplicates_removed": duplicates,
                     "partial_frames_excluded": partials, "conflicting_duplicates": conflicts,
                     "chronological": chronological},
        "state": {"status": status, "stop_reason": reason.get("type"),
                  "outcome": observed_outcome, "source": "session" if has_snapshot else "history",
                  "consistent": not state_conflict,
                  "completion_verified": observed_outcome == "end_turn" and not state_conflict and complete and chronological,
                  "event_id": history_state[0].get("id") if not has_snapshot and history_state else None,
                  "pending_call_ids": reason.get("pending_call_ids"),
                  "pending_batch_id": reason.get("pending_batch_id")},
        "metrics": metrics,
        "events": {"by_type": dict(Counter(e.get("type") or "unknown" for e in events)),
                   "by_role": dict(Counter(e.get("role") or "unknown" for e in events)),
                   "by_thread": dict(Counter(str(thread(e) or "unknown") for e in events))},
        "errors": errors, "calls": calls, "unlinked_calls": unlinked,
        "agent_version_evidence": {
            "source": "agent.version" if snapshot_version is not None else (
                "agent_version" if top_level_version is not None else None),
            "snapshot_version": snapshot_version, "top_level_version": top_level_version,
            "conflict": version_conflict},
        "comparison_context": {
            "input_sha256": fingerprint(inputs) if inputs else None,
            "agent": agent, "agent_version": agent_version,
            "observed_models": sorted(models) or None,
            "environment_id": session.get("environment_id"),
            "resources_sha256": fingerprint(session.get("resources")),
            "environment_variables_sha256": fingerprint(session.get("environment_variables")),
            "vault_ids_sha256": fingerprint(session.get("vault_ids"))},
        "quality": {"verdict": "not_evaluated", "reason": "Requires task rubric and artifact verification."},
        "warnings": warnings + ["Call intervals may overlap; do not sum them as session wall time.",
                                "Stats/usage are cumulative session measures, not a selected turn."]}


def compare(baseline, candidate):
    if any(report.get("schema") != SCHEMA for report in (baseline, candidate)):
        raise ValueError("Compare requires two session_analysis analyze reports")
    changes = {}
    for key in METRICS:
        before = number(baseline.get("metrics", {}).get(key))
        after = number(candidate.get("metrics", {}).get(key))
        delta = after - before if before is not None and after is not None else None
        changes[key] = {"baseline": before, "candidate": after, "delta": delta,
                        "percent_change": 100 * delta / before if delta is not None and before else None}
    context = {}
    for key in sorted(set(baseline.get("comparison_context", {})) |
                      set(candidate.get("comparison_context", {}))):
        before = baseline.get("comparison_context", {}).get(key)
        after = candidate.get("comparison_context", {}).get(key)
        context[key] = "unverified" if before is None or after is None else (
            "same" if before == after else "different")
    issues = [f"{key}: {value}" for key, value in context.items() if value != "same"]
    if baseline.get("session_id") and baseline.get("session_id") == candidate.get("session_id"):
        issues.append("Same session ID: these are not independent fresh-session runs.")
    for label, report in (("baseline", baseline), ("candidate", candidate)):
        if report.get("agent_version_evidence", {}).get("conflict"):
            issues.append(f"{label}: embedded and top-level Agent versions conflict")
        if not report.get("coverage", {}).get("events_complete"):
            issues.append(f"{label}: incomplete history")
        if report.get("state", {}).get("outcome") != "end_turn":
            issues.append(f"{label}: turn did not demonstrably end normally")
        if report.get("state", {}).get("consistent") is not True:
            issues.append(f"{label}: session and history states conflict or consistency is unverified")
        if not report.get("coverage", {}).get("chronological"):
            issues.append(f"{label}: chronological history unverified")
    return {"schema": "managed-agent-session-comparison/v1",
            "baseline_session_id": baseline.get("session_id"),
            "candidate_session_id": candidate.get("session_id"),
            "metrics": changes, "context_checks": context,
            "comparability": {"status": "requires_review", "issues": issues,
                "note": "Confirm intended changes, equivalent inputs, environment versions, memory state, run scope and quality rubric."},
            "quality": "not_evaluated", "winner": None,
            "conclusion": "Observed differences only; elapsed time and tokens do not establish task quality or causation."}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    analyze_parser = commands.add_parser("analyze", help="Summarize local Session and Event List JSON")
    analyze_parser.add_argument("--session", required=True)
    analyze_parser.add_argument("--events", required=True)
    analyze_parser.add_argument("--events-complete", action="store_true",
                                help="Confirm all history pages and intended threads/turns were collected")
    compare_parser = commands.add_parser("compare", help="Compare two saved analyze reports")
    compare_parser.add_argument("--baseline", required=True)
    compare_parser.add_argument("--candidate", required=True)
    for command in (analyze_parser, compare_parser):
        command.add_argument("--output", help="New output file; omit to write JSON to stdout")
    args = parser.parse_args(argv)
    try:
        report = (analyze(read_json(args.session), read_json(args.events), args.events_complete)
                  if args.command == "analyze" else compare(read_json(args.baseline), read_json(args.candidate)))
        rendered = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        if args.output:
            with Path(args.output).open("x", encoding="utf-8") as handle:
                handle.write(rendered)
        else:
            sys.stdout.write(rendered)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"session_analysis: {exc}\n")


if __name__ == "__main__":
    main()
