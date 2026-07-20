#!/usr/bin/env python3
"""Read AgentLoop evaluation results from SLS and structure low-score cases.

Dependencies: Python 3.8+ standard library only; imports the local agentloop_eval module (no external packages required).
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from agentloop_eval import (
    WorkflowError,
    add_connection_flags,
    display_command,
    find_first,
    get_agent_space_command,
    run_cli,
    run_json,
    write_result,
)


EVALUATION_LOGSTORE = "evaluation_detail"
DEFAULT_LOW_SCORE_THRESHOLD = 0.5
DEFAULT_MAX_CASES = 50
MAX_CASES_LIMIT = 200


def parse_epoch_seconds(value: Any, field: str) -> int:
    """Accept timezone-bearing ISO-8601, epoch seconds, or epoch milliseconds."""
    if isinstance(value, bool):
        raise WorkflowError(f"{field} must be ISO-8601, epoch seconds, or epoch milliseconds")
    if isinstance(value, (int, float)):
        number = int(value)
        if number >= 100_000_000_000:
            return number // 1000
        if number >= 1_000_000_000:
            return number
        raise WorkflowError(f"{field} is not a plausible epoch timestamp")
    if not isinstance(value, str):
        raise WorkflowError(f"{field} must be ISO-8601, epoch seconds, or epoch milliseconds")
    text = value.strip()
    if text.isdigit():
        return parse_epoch_seconds(int(text), field)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise WorkflowError(f"{field} is not valid ISO-8601: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowError(f"{field} must include a timezone offset")
    return int(parsed.timestamp())


def sql_quote(value: str) -> str:
    return value.replace("'", "''")


def where_clause(conditions: list[str]) -> str:
    if not conditions:
        return ""
    return "WHERE " + " AND ".join(conditions)


def build_queries(
    *,
    channel: str,
    task_id: str | None,
    run_id: str | None,
    evaluator_name: str | None,
    threshold: float,
    max_cases: int,
    include_unknown: bool,
) -> dict[str, str]:
    base_conditions: list[str] = []
    if task_id:
        base_conditions.append(f"task_id = '{sql_quote(task_id)}'")
    if run_id:
        base_conditions.append(f"run_id = '{sql_quote(run_id)}'")
    if evaluator_name:
        base_conditions.append(f"evaluator_name = '{sql_quote(evaluator_name)}'")

    accepted_status = "status = 'success'"
    if include_unknown:
        accepted_status = "(status = 'success' OR status = 'unknown')"

    score_present = "normalized_score_value IS NOT NULL AND normalized_score_value != ''"
    score_cast = "CAST(normalized_score_value AS DOUBLE)"
    low_score = f"{score_cast} < {threshold:g}"
    search = f"channel = '{sql_quote(channel)}'"
    base_where = where_clause(base_conditions)

    overview = (
        f"{search} | SELECT "
        "count(1) AS total_count, "
        "count_if(status = 'success') AS success_count, "
        "count_if(status = 'unknown') AS unknown_count, "
        "count_if(status = 'failed') AS failed_count, "
        f"count_if({accepted_status} AND {score_present}) AS scored_count, "
        f"avg(CAST(CASE WHEN {accepted_status} THEN normalized_score_value ELSE NULL END AS DOUBLE)) "
        "AS avg_normalized_score, "
        f"count_if({accepted_status} AND {score_present} AND {low_score}) AS low_score_count, "
        f"avg(CAST(CASE WHEN {accepted_status} THEN eval_latency ELSE NULL END AS DOUBLE)) "
        "AS avg_latency, "
        f"approx_percentile(CAST(CASE WHEN {accepted_status} THEN eval_latency ELSE NULL END "
        "AS DOUBLE), 0.95) "
        f"AS p95_latency FROM log {base_where}"
    )

    evaluator_breakdown = (
        f"{search} | SELECT evaluator_name, "
        "max(evaluator_display_name) AS evaluator_display_name, "
        "count(1) AS total_count, "
        "count_if(status = 'success') AS success_count, "
        "count_if(status = 'unknown') AS unknown_count, "
        "count_if(status = 'failed') AS failed_count, "
        f"count_if({accepted_status} AND {score_present}) AS scored_count, "
        f"avg(CAST(CASE WHEN {accepted_status} THEN normalized_score_value ELSE NULL END AS DOUBLE)) "
        "AS avg_normalized_score, "
        f"count_if({accepted_status} AND {score_present} AND {low_score}) AS low_score_count "
        f"FROM log {base_where} GROUP BY evaluator_name "
        "ORDER BY low_score_count DESC, total_count DESC LIMIT 100"
    )

    case_conditions = list(base_conditions)
    case_conditions.extend((accepted_status, score_present, low_score))
    case_where = where_clause(case_conditions)
    low_score_cases = (
        f"{search} | SELECT eval_id, task_id, task_name, run_id, evaluator_name, "
        "evaluator_display_name, score_value, score_range, normalized_score_value, status, "
        "timestamp, explanation, evaluation_process, custom_outputs, eval_metrics, eval_info, "
        f"data_link, eval_latency FROM log {case_where} "
        f"ORDER BY {score_cast} ASC, timestamp DESC LIMIT {max_cases}"
    )
    return {
        "overview": overview,
        "evaluatorBreakdown": evaluator_breakdown,
        "lowScoreCases": low_score_cases,
    }


def build_sls_command(
    *,
    project: str,
    start: int,
    end: int,
    query: str,
    region: str | None,
    line: int = 100,
) -> list[str]:
    command = [
        "aliyun",
        "sls",
        "get-logs-v2",
        "--project",
        project,
        "--logstore",
        EVALUATION_LOGSTORE,
        "--from",
        str(start),
        "--to",
        str(end),
        "--accept-encoding",
        "lz4",
        "--query",
        query,
        "--line",
        str(line),
    ]
    add_connection_flags(command, region, None)
    return command


def extract_logs(response: Any) -> list[dict[str, Any]]:
    if isinstance(response, list):
        return [item for item in response if isinstance(item, dict)]
    if not isinstance(response, dict):
        return []
    for key in ("logs", "data", "results", "items"):
        value = response.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_logs(value)
            if nested:
                return nested
    body = response.get("body")
    if isinstance(body, str):
        try:
            return extract_logs(json.loads(body))
        except json.JSONDecodeError:
            return []
    return []


def finite_float(value: Any) -> float | None:
    if value in (None, "", "null"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def integer(value: Any) -> int:
    number = finite_float(value)
    return int(number) if number is not None else 0


def json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def score_bucket(value: float | None) -> str | None:
    if value is None:
        return None
    if value < 0.3:
        return "very_poor"
    if value < 0.5:
        return "poor"
    if value < 0.7:
        return "medium"
    if value < 0.9:
        return "good"
    return "excellent"


def normalize_overview(row: dict[str, Any], threshold: float) -> dict[str, Any]:
    scored_count = integer(row.get("scored_count"))
    low_score_count = integer(row.get("low_score_count"))
    low_score_rate = 0.0
    if scored_count > 0:
        low_score_rate = low_score_count / scored_count
    return {
        "totalCount": integer(row.get("total_count")),
        "successCount": integer(row.get("success_count")),
        "unknownCount": integer(row.get("unknown_count")),
        "failedCount": integer(row.get("failed_count")),
        "scoredCount": scored_count,
        "averageNormalizedScore": finite_float(row.get("avg_normalized_score")),
        "lowScoreThreshold": threshold,
        "lowScoreCount": low_score_count,
        "lowScoreRate": low_score_rate,
        "averageLatency": finite_float(row.get("avg_latency")),
        "p95Latency": finite_float(row.get("p95_latency")),
    }


def normalize_evaluator(row: dict[str, Any]) -> dict[str, Any]:
    scored_count = integer(row.get("scored_count"))
    low_score_count = integer(row.get("low_score_count"))
    low_score_rate = 0.0
    if scored_count > 0:
        low_score_rate = low_score_count / scored_count
    return {
        "evaluatorName": row.get("evaluator_name"),
        "evaluatorDisplayName": row.get("evaluator_display_name") or row.get("evaluator_name"),
        "totalCount": integer(row.get("total_count")),
        "successCount": integer(row.get("success_count")),
        "unknownCount": integer(row.get("unknown_count")),
        "failedCount": integer(row.get("failed_count")),
        "scoredCount": scored_count,
        "averageNormalizedScore": finite_float(row.get("avg_normalized_score")),
        "lowScoreCount": low_score_count,
        "lowScoreRate": low_score_rate,
    }


def normalize_case(row: dict[str, Any], include_content: bool = False) -> dict[str, Any]:
    eval_info = json_object(row.get("eval_info"))
    data_link = json_object(row.get("data_link"))
    eval_metrics = json_object(row.get("eval_metrics"))
    custom_outputs = json_object(row.get("custom_outputs"))
    if not custom_outputs:
        custom_outputs = json_object(eval_info.get("custom_outputs"))
    normalized_score = finite_float(row.get("normalized_score_value"))
    result = {
        "evalId": row.get("eval_id"),
        "taskId": row.get("task_id"),
        "taskName": row.get("task_name"),
        "runId": row.get("run_id"),
        "evaluatorName": row.get("evaluator_name"),
        "evaluatorDisplayName": row.get("evaluator_display_name") or row.get("evaluator_name"),
        "status": row.get("status"),
        "timestamp": row.get("timestamp"),
        "score": finite_float(row.get("score_value")),
        "scoreRange": row.get("score_range"),
        "normalizedScore": normalized_score,
        "scoreBucket": score_bucket(normalized_score),
        "explanation": row.get("explanation"),
        "evaluationLatency": finite_float(row.get("eval_latency")),
        "dataLink": data_link,
        "evalMetrics": eval_metrics,
    }
    if include_content:
        result.update(
            {
                "evaluationProcess": row.get("evaluation_process"),
                "input": eval_info.get("input"),
                "output": eval_info.get("output"),
                "expectedOutput": eval_info.get("expected_output")
                or eval_info.get("ground_truth"),
                "evalInfo": eval_info,
                "customOutputs": custom_outputs,
            }
        )
    else:
        result.update(
            {
                "contentOmitted": True,
                "evalInfoFields": sorted(str(key) for key in eval_info),
                "customOutputFields": sorted(str(key) for key in custom_outputs),
            }
        )
    return result


def build_analysis(
    *,
    source: dict[str, Any],
    queries: dict[str, str],
    overview_rows: list[dict[str, Any]],
    evaluator_rows: list[dict[str, Any]],
    case_rows: list[dict[str, Any]],
    threshold: float,
    include_content: bool = False,
) -> dict[str, Any]:
    overview_row = overview_rows[0] if overview_rows else {}
    evaluators = [normalize_evaluator(row) for row in evaluator_rows]
    evaluators.sort(key=lambda item: (-item["lowScoreCount"], -item["totalCount"]))
    cases = [normalize_case(row, include_content=include_content) for row in case_rows]
    cases.sort(
        key=lambda item: (
            item["normalizedScore"] is None,
            item["normalizedScore"] if item["normalizedScore"] is not None else 0.0,
        )
    )
    return {
        "source": source,
        "queries": queries,
        "overview": normalize_overview(overview_row, threshold),
        "evaluatorBreakdown": evaluators,
        "lowScoreCases": cases,
    }


def resolve_project(args: argparse.Namespace) -> str:
    if args.project:
        return args.project
    if not args.agent_space:
        raise WorkflowError("pass --project or --agent-space so the SLS project can be resolved")
    response = run_json(get_agent_space_command(args.agent_space, args.region, None))
    project = find_first(response, ("slsProject", "sls_project"))
    if project in (None, ""):
        raise WorkflowError(
            "AgentSpace response did not contain slsProject; pass --project explicitly"
        )
    return str(project)


def verify_sls_plugin() -> None:
    if not shutil.which("aliyun"):
        raise WorkflowError("aliyun CLI is not installed or not in PATH")
    try:
        run_cli(
            ["aliyun", "plugin", "show", "--name", "aliyun-cli-sls"],
            echo_output=False,
        )
    except WorkflowError as exc:
        raise WorkflowError(
            "aliyun-cli-sls is required for result analysis; install it only after user approval"
        ) from exc


def command_analyze(args: argparse.Namespace) -> int:
    start = parse_epoch_seconds(args.start, "--from")
    end = parse_epoch_seconds(args.end, "--to")
    if start >= end:
        raise WorkflowError("--from must be earlier than --to")
    if not math.isfinite(args.threshold) or args.threshold < 0 or args.threshold > 1:
        raise WorkflowError("--threshold must be between 0 and 1")
    if args.max_cases <= 0 or args.max_cases > MAX_CASES_LIMIT:
        raise WorkflowError(f"--max-cases must be between 1 and {MAX_CASES_LIMIT}")

    project = resolve_project(args)
    queries = build_queries(
        channel=args.channel,
        task_id=args.task_id,
        run_id=args.run_id,
        evaluator_name=args.evaluator_name,
        threshold=args.threshold,
        max_cases=args.max_cases,
        include_unknown=args.include_unknown,
    )
    line_limits = {
        "overview": 1,
        "evaluatorBreakdown": 100,
        "lowScoreCases": args.max_cases,
    }
    commands = {
        name: build_sls_command(
            project=project,
            start=start,
            end=end,
            query=query,
            region=args.region,
            line=line_limits[name],
        )
        for name, query in queries.items()
    }
    source = {
        "agentSpace": args.agent_space,
        "project": project,
        "logstore": EVALUATION_LOGSTORE,
        "region": args.region,
        "from": start,
        "to": end,
        "channel": args.channel,
        "taskId": args.task_id,
        "runId": args.run_id,
        "evaluatorName": args.evaluator_name,
        "lowScoreThreshold": args.threshold,
        "maxCases": args.max_cases,
        "includeUnknown": args.include_unknown,
        "includeContent": args.include_content,
    }

    if args.preview:
        preview = {
            "source": source,
            "queries": queries,
            "commands": {name: display_command(command) for name, command in commands.items()},
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        write_result(args.output, preview)
        return 0

    verify_sls_plugin()
    overview_response = run_json(commands["overview"], timeout=300)
    evaluator_response = run_json(commands["evaluatorBreakdown"], timeout=300)
    cases_response = run_json(commands["lowScoreCases"], timeout=300)
    analysis = build_analysis(
        source=source,
        queries=queries,
        overview_rows=extract_logs(overview_response),
        evaluator_rows=extract_logs(evaluator_response),
        case_rows=extract_logs(cases_response),
        threshold=args.threshold,
        include_content=args.include_content,
    )
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    write_result(args.output, analysis)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze low-score AgentLoop evaluation cases from SLS"
    )
    parser.add_argument("--agent-space", help="resolve the SLS project from this AgentSpace")
    parser.add_argument("--project", help="explicit SLS project; skips AgentSpace resolution")
    parser.add_argument("--region", help="Aliyun endpoint-selection region")
    parser.add_argument("--from", dest="start", required=True, help="timezone ISO-8601 or epoch")
    parser.add_argument("--to", dest="end", required=True, help="timezone ISO-8601 or epoch")
    parser.add_argument("--task-id")
    parser.add_argument("--run-id")
    parser.add_argument("--evaluator-name")
    parser.add_argument("--channel", default="default")
    parser.add_argument("--threshold", type=float, default=DEFAULT_LOW_SCORE_THRESHOLD)
    parser.add_argument("--max-cases", type=int, default=DEFAULT_MAX_CASES)
    parser.add_argument(
        "--include-unknown",
        action="store_true",
        help="include status=unknown records when they have scores",
    )
    parser.add_argument(
        "--include-content",
        action="store_true",
        help="include raw eval_info, evaluation process, and custom outputs after authorization",
    )
    parser.add_argument("--preview", action="store_true", help="render queries without SLS calls")
    parser.add_argument("--output", type=Path, help="write preview or analysis JSON")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return command_analyze(args)
    except WorkflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
