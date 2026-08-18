#!/usr/bin/env python3
"""Safe V1 wrapper for Alibaba Cloud AgentLoop Pipeline preview and creation."""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


SKILL_NAME = "alibabacloud-agentloop-management"
ALLOWED_BINARIES = {"aliyun"}
PIPELINE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
DATASET_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
SUPPORTED_NODES = {
    "project",
    "extend",
    "where",
    "limit",
    "make-instance",
    "dedup-exact",
    "dedup-fuzzy",
    "dedup-semantic",
    "embedding",
    "doc-stats",
    "semantic-cluster",
    "sample",
    "llm-call",
    "agentic-call",
}
DEPRECATED_NODES = {"ai-gen"}
EXPERIMENTAL_NODES = {"make-conversation"}
AI_NODES = {"llm-call", "agentic-call"}
DEDUP_NODES = {"dedup-exact", "dedup-fuzzy", "dedup-semantic"}
SECRET_KEY_RE = re.compile(
    r"(access.?key|secret|token|authorization|credential|password)",
    re.IGNORECASE,
)

# Strong credential terms in a field name are always treated as secret.
_SECRET_STRONG_RE = re.compile(
    r"(access.?key|secret|authorization|credential|password)",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"token", re.IGNORECASE)
# LLM token-usage counters (e.g. llm_input_tokens, total_output_tokens,
# token_count) are legitimate OT-AI trace fields, not credentials.
_TOKEN_USAGE_RE = re.compile(
    r"(input|output|total|prompt|completion|cache|cached|reasoning|thinking|"
    r"max|min|avg|mean|num|n|used|remaining|per|count)[_\-]?tokens?"
    r"|tokens?[_\-]?(count|used|total|in|out|sum|usage)"
    r"|^tokens?$",
    re.IGNORECASE,
)


def _is_secret_key(key: Any) -> bool:
    """Return True when a field name looks like a credential.

    Strong terms (access key, secret, authorization, credential, password) are
    always secret. A ``token`` field is secret only when it is not a token-usage
    counter such as ``llm_input_tokens`` or ``total_output_tokens``.
    """
    text = str(key)
    if _SECRET_STRONG_RE.search(text):
        return True
    if _TOKEN_RE.search(text) and not _TOKEN_USAGE_RE.search(text):
        return True
    return False



class PipelineError(Exception):
    """User-facing validation or execution error."""


@dataclass
class Plan:
    spec: dict[str, Any]
    source: dict[str, Any]
    pipeline: dict[str, Any]
    sink: dict[str, Any]
    execute_policy: dict[str, Any]
    client_token: str
    warnings: list[str]


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


_CACHED_SESSION_ID: str | None = None


def _session_id() -> str:
    global _CACHED_SESSION_ID
    if _CACHED_SESSION_ID is not None:
        return _CACHED_SESSION_ID
    existing = os.environ.get("SKILL_SESSION_ID", "")
    if re.fullmatch(r"[a-f0-9]{32}", existing):
        _CACHED_SESSION_ID = existing
    else:
        _CACHED_SESSION_ID = secrets.token_hex(16)
    return _CACHED_SESSION_ID


def _user_agent() -> str:
    return f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{_session_id()}"


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, inner in value.items():
            if _is_secret_key(key):
                result[key] = "<redacted>"
            else:
                result[key] = _redact(inner)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _reject_secrets(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, inner in value.items():
            child_path = f"{path}.{key}"
            if _is_secret_key(key):
                raise PipelineError(f"secret-like field is not allowed in spec: {child_path}")
            _reject_secrets(inner, child_path)
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            _reject_secrets(inner, f"{path}[{index}]")


def _parse_time(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise PipelineError(f"{field} must be an ISO-8601 timestamp or Unix seconds")
    if isinstance(value, int):
        if value >= 100_000_000_000:
            raise PipelineError(f"{field} looks like milliseconds; use Unix seconds")
        if value <= 0:
            raise PipelineError(f"{field} must be positive Unix seconds")
        return value
    if isinstance(value, float):
        raise PipelineError(f"{field} must not be a floating-point timestamp")
    if not isinstance(value, str) or not value.strip():
        raise PipelineError(f"{field} must be an ISO-8601 timestamp or Unix seconds")
    text = value.strip()
    if text.isdigit():
        return _parse_time(int(text), field)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise PipelineError(f"{field} is not valid ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None:
        raise PipelineError(f"{field} must include a timezone offset")
    return int(parsed.timestamp())


def _require_object(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PipelineError(f"{path} must be an object")
    return value


def _require_string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PipelineError(f"{path} must be a non-empty string")
    if "\x00" in value or "\n" in value or "\r" in value:
        raise PipelineError(f"{path} must not contain null bytes or newlines")
    return value.strip()


def load_spec(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise PipelineError(f"spec file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PipelineError(f"spec is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PipelineError("spec root must be a JSON object")
    return data


def build_plan(spec: dict[str, Any], *, allow_scheduled: bool = False) -> Plan:
    _reject_secrets(spec)
    operation = spec.get("operation")
    if operation not in (None, "create"):
        raise PipelineError("V1 wrapper only supports create specs")

    agent_space = _require_string(spec.get("agent_space"), "agent_space")
    region = _require_string(spec.get("region"), "region")
    pipeline_name = _require_string(spec.get("pipeline_name"), "pipeline_name")
    if not PIPELINE_NAME_RE.fullmatch(pipeline_name):
        raise PipelineError(
            "pipeline_name must be 3-63 lowercase letters, digits, or hyphens"
        )

    description = spec.get("description")
    if description is not None:
        description = _require_string(description, "description")
        if len(description) > 256:
            raise PipelineError("description must be at most 256 characters")

    source_spec = _require_object(spec.get("source"), "source")
    source_type = _require_string(source_spec.get("type"), "source.type")
    if source_type.lower() != "logstore":
        raise PipelineError("V1 supports only source.type=logstore")
    logstore = _require_object(source_spec.get("logstore"), "source.logstore")
    source = {
        "type": "logstore",
        "logstore": {
            "project": _require_string(logstore.get("project"), "source.logstore.project"),
            "logstore": _require_string(logstore.get("logstore"), "source.logstore.logstore"),
            "query": _require_string(logstore.get("query"), "source.logstore.query"),
        },
    }

    nodes_spec = spec.get("nodes")
    if not isinstance(nodes_spec, list) or not nodes_spec:
        raise PipelineError("nodes must be a non-empty array")
    seen_ids: set[str] = set()
    nodes: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, node_value in enumerate(nodes_spec):
        node = _require_object(node_value, f"nodes[{index}]")
        node_id = _require_string(node.get("id"), f"nodes[{index}].id")
        if node_id in seen_ids:
            raise PipelineError(f"duplicate node id: {node_id}")
        seen_ids.add(node_id)
        node_type = _require_string(node.get("type"), f"nodes[{index}].type")
        if node_type in DEPRECATED_NODES:
            raise PipelineError("ai-gen is deprecated for new specs; use llm-call")
        if node_type in EXPERIMENTAL_NODES:
            raise PipelineError("make-conversation is experimental and rejected in V1")
        if node_type not in SUPPORTED_NODES:
            raise PipelineError(f"unsupported node type: {node_type}")
        parameters = _require_object(node.get("parameters", {}), f"nodes[{index}].parameters")
        _validate_node_parameters(node_type, parameters, f"nodes[{index}].parameters")
        if node_type in AI_NODES:
            warnings.append(f"AI node {node_id} ({node_type}) may incur model/agent cost")
        if node_type in DEDUP_NODES and parameters.get("global") is True:
            warnings.append(f"node {node_id} uses global deduplication state")
        nodes.append({"id": node_id, "type": node_type, "parameters": parameters})

    sink_spec = _require_object(spec.get("sink"), "sink")
    if sink_spec.get("type") != "dataset":
        raise PipelineError("V1 supports only sink.type=dataset")
    dataset = _require_object(sink_spec.get("dataset"), "sink.dataset")
    sink_agent_space = _require_string(dataset.get("agent_space"), "sink.dataset.agent_space")
    if sink_agent_space != agent_space:
        raise PipelineError("cross-AgentSpace dataset sink is not supported in V1")
    dataset_name = _require_string(dataset.get("name"), "sink.dataset.name")
    if not 4 <= len(dataset_name) <= 63 or not DATASET_NAME_RE.fullmatch(dataset_name):
        raise PipelineError(
            "sink.dataset.name must be 4-63 lowercase letters, digits, or underscore-separated words"
        )
    sink = {
        "type": "dataset",
        "dataset": {
            "agentSpace": sink_agent_space,
            "dataset": dataset_name,
        },
    }

    execute_spec = _require_object(spec.get("execute_policy"), "execute_policy")
    mode = _require_string(execute_spec.get("mode"), "execute_policy.mode").lower()
    if mode == "run_once":
        window = _require_object(execute_spec.get("window"), "execute_policy.window")
        from_time = _parse_time(window.get("start"), "execute_policy.window.start")
        to_time = _parse_time(window.get("end"), "execute_policy.window.end")
        if from_time >= to_time:
            raise PipelineError("execute_policy.window.start must be earlier than end")
        execute_policy = {
            "mode": "runOnce",
            "runOnce": {"fromTime": from_time, "toTime": to_time},
        }
    elif mode == "scheduled":
        if not allow_scheduled:
            raise PipelineError("Scheduled pipelines require --allow-scheduled")
        from_time = _parse_time(execute_spec.get("start"), "execute_policy.start")
        interval = _require_string(execute_spec.get("interval"), "execute_policy.interval")
        execute_policy = {
            "mode": "scheduled",
            "scheduled": {"fromTime": from_time, "interval": interval},
        }
        warnings.append("Scheduled Pipeline can continue running and accumulating cost")
    else:
        raise PipelineError("execute_policy.mode must be run_once or scheduled")

    normalized = {
        "agent_space": agent_space,
        "region": region,
        "pipeline_name": pipeline_name,
        "source": source,
        "nodes": nodes,
        "sink": sink,
        "execute_policy": execute_policy,
    }
    if description is not None:
        normalized["description"] = description

    return Plan(
        spec=normalized,
        source=source,
        pipeline={"nodes": nodes},
        sink=sink,
        execute_policy=execute_policy,
        client_token=secrets.token_hex(16),
        warnings=warnings,
    )


def _validate_node_parameters(node_type: str, parameters: dict[str, Any], path: str) -> None:
    if node_type in DEDUP_NODES | {"embedding", "doc-stats", "semantic-cluster"}:
        _require_string(parameters.get("field"), f"{path}.field")
    if node_type == "sample":
        has_ratio = "ratio" in parameters
        has_n = "n" in parameters
        if has_ratio == has_n:
            raise PipelineError(f"{path} must contain exactly one of ratio or n")
    if node_type == "llm-call":
        _require_string(parameters.get("prompt"), f"{path}.prompt")
        fields = parameters.get("fields")
        _require_string(fields, f"{path}.fields")
    if node_type == "agentic-call":
        _require_string(parameters.get("prompt"), f"{path}.prompt")
        _require_string(parameters.get("fields"), f"{path}.fields")
        _require_string(parameters.get("employee"), f"{path}.employee")


def build_preview_command(
    plan: Plan, *, from_time: int, to_time: int, dry_run: bool
) -> list[str]:
    """Build the preview-pipeline call from the same spec used for create.

    ``source`` and ``pipeline`` are taken straight off the Plan, so the operator
    never has to split the spec by hand. Each JSON blob is one argv element and
    never reaches a shell, which removes the quoting failures that inline
    command-line JSON causes.
    """
    command = [
        "aliyun",
        "agentloop",
        "preview-pipeline",
        "--agent-space",
        plan.spec["agent_space"],
        "--source",
        _json_dumps(plan.source),
        "--pipeline",
        _json_dumps(plan.pipeline),
        "--from-time",
        str(from_time),
        "--to-time",
        str(to_time),
        "--region",
        plan.spec["region"],
        "--user-agent",
        _user_agent(),
    ]
    if dry_run:
        command.extend(["--cli-dry-run", "true"])
    return command


def build_create_command(plan: Plan, *, dry_run: bool) -> list[str]:
    spec = plan.spec
    command = [
        "aliyun",
        "agentloop",
        "create-pipeline",
        "--agent-space",
        spec["agent_space"],
        "--pipeline-name",
        spec["pipeline_name"],
        "--source",
        _json_dumps(plan.source),
        "--pipeline",
        _json_dumps(plan.pipeline),
        "--sink",
        _json_dumps(plan.sink),
        "--execute-policy",
        _json_dumps(plan.execute_policy),
        "--region",
        spec["region"],
        "--client-token",
        plan.client_token,
        "--user-agent",
        _user_agent(),
    ]
    if "description" in spec:
        command.extend(["--description", spec["description"]])
    if dry_run:
        command.extend(["--cli-dry-run", "true"])
    return command


def _validate_command(command: list[str]) -> None:
    if not command:
        raise PipelineError("refusing to execute an empty command")
    if command[0] not in ALLOWED_BINARIES:
        raise PipelineError(f"refusing to execute disallowed binary: {command[0]!r}")
    for index, arg in enumerate(command):
        if "\x00" in arg or "\n" in arg or "\r" in arg:
            raise PipelineError(f"command argument at position {index} is unsafe")


def run_cli(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    _validate_command(command)
    redacted = [_redact_arg(arg) for arg in command]
    print("+ " + " ".join(redacted), file=sys.stderr)
    return subprocess.run(command, check=check, text=True, capture_output=True)


def _redact_arg(arg: str) -> str:
    if SECRET_KEY_RE.search(arg):
        return "<redacted>"
    return arg


def print_plan(plan: Plan) -> None:
    summary = {
        "agent_space": plan.spec["agent_space"],
        "region": plan.spec["region"],
        "pipeline_name": plan.spec["pipeline_name"],
        "source": plan.source,
        "nodes": [
            {"id": node["id"], "type": node["type"], "parameters": _redact(node["parameters"])}
            for node in plan.pipeline["nodes"]
        ],
        "sink": plan.sink,
        "execute_policy": plan.execute_policy,
        "warnings": plan.warnings,
    }
    if "description" in plan.spec:
        summary["description"] = plan.spec["description"]
    print(_json_dumps(_redact(summary)))


def cmd_doctor(args: argparse.Namespace) -> int:
    aliyun = shutil.which("aliyun")
    checks: list[dict[str, Any]] = [{"name": "aliyun binary", "ok": bool(aliyun), "value": aliyun}]
    if not aliyun:
        print(_json_dumps({"ok": False, "checks": checks}))
        return 1

    for name, command in [
        ("aliyun version", ["aliyun", "version"]),
        ("agentloop help", ["aliyun", "agentloop", "--help"]),
        ("create-pipeline help", ["aliyun", "agentloop", "create-pipeline", "--help"]),
        ("preview-pipeline help", ["aliyun", "agentloop", "preview-pipeline", "--help"]),
    ]:
        result = run_cli(command, check=False)
        checks.append(
            {
                "name": name,
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip().splitlines()[:5],
                "stderr": _redact(result.stderr.strip().splitlines()[:5]),
            }
        )

    if args.agent_space:
        command = [
            "aliyun",
            "agentloop",
            "get-agent-space",
            "--agent-space",
            args.agent_space,
            "--user-agent",
            _user_agent(),
        ]
        if args.region:
            command.extend(["--region", args.region])
        result = run_cli(command, check=False)
        checks.append(
            {
                "name": "agent space access",
                "ok": result.returncode == 0,
                "stdout": _redact(result.stdout.strip().splitlines()[:10]),
                "stderr": _redact(result.stderr.strip().splitlines()[:10]),
            }
        )

    ok = all(item["ok"] for item in checks)
    print(_json_dumps({"ok": ok, "checks": checks}))
    return 0 if ok else 1


def cmd_create(args: argparse.Namespace) -> int:
    plan = build_plan(load_spec(Path(args.spec)), allow_scheduled=args.allow_scheduled)
    print_plan(plan)
    dry_run = build_create_command(plan, dry_run=True)
    dry_result = run_cli(dry_run, check=False)
    print(dry_result.stdout, end="")
    if dry_result.returncode != 0:
        print(dry_result.stderr, file=sys.stderr, end="")
        return dry_result.returncode
    if not args.execute:
        return 0

    expected = plan.spec["pipeline_name"]
    print(
        f"Type the Pipeline name to confirm creation ({expected}): ",
        file=sys.stderr,
        end="",
        flush=True,
    )
    confirmation = sys.stdin.readline().strip()
    if confirmation != expected:
        raise PipelineError("confirmation did not match Pipeline name; creation aborted")

    command = build_create_command(plan, dry_run=False)
    result = run_cli(command, check=False)
    print(result.stdout, end="")
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr, end="")
    return result.returncode


MAX_PREVIEW_WINDOW_SECONDS = 900


def declared_output_columns(plan: Plan) -> list[str] | None:
    """Return the columns declared by the last project node, if there is one."""
    for node in reversed(plan.pipeline["nodes"]):
        if node["type"] == "project":
            return sorted(node["parameters"].keys())
    return None


def check_preview_columns(plan: Plan, payload: Any) -> dict[str, Any] | None:
    """Compare the previewed meta.keys against the declared output columns.

    This is the manual comparison the documented workflow asks for. It is
    advisory: a mismatch usually means a misspelled aggregator, a WHERE that
    dropped every row, or a NULL upstream extraction.
    """
    declared = declared_output_columns(plan)
    if declared is None or not isinstance(payload, dict):
        return None
    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return None
    keys = meta.get("keys")
    if not isinstance(keys, list) or not all(isinstance(key, str) for key in keys):
        return None
    returned = sorted(keys)
    missing = [column for column in declared if column not in returned]
    extra = [column for column in returned if column not in declared]
    rows = payload.get("data")
    return {
        "ok": not missing,
        "declared": declared,
        "returned": returned,
        "missing": missing,
        "extra": extra,
        "rows": len(rows) if isinstance(rows, list) else None,
    }


def cmd_preview(args: argparse.Namespace) -> int:
    plan = build_plan(load_spec(Path(args.spec)), allow_scheduled=args.allow_scheduled)
    from_time = _parse_time(args.from_time, "--from-time")
    to_time = _parse_time(args.to_time, "--to-time")
    if from_time >= to_time:
        raise PipelineError("--from-time must be earlier than --to-time")

    warnings = list(plan.warnings)
    window_seconds = to_time - from_time
    if window_seconds > MAX_PREVIEW_WINDOW_SECONDS:
        warnings.append(
            f"preview window is {window_seconds}s; a few minutes is usually enough "
            "and a wider window scans more SLS bytes"
        )
    ai_nodes = [
        node["id"] for node in plan.pipeline["nodes"] if node["type"] in AI_NODES
    ]
    if ai_nodes:
        warnings.append(
            "preview executes AI nodes against real data and bills per row: "
            + ", ".join(ai_nodes)
        )
    print(_json_dumps({"preview": {"from_time": from_time, "to_time": to_time}}))
    print_plan(plan)
    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    dry_result = run_cli(
        build_preview_command(plan, from_time=from_time, to_time=to_time, dry_run=True),
        check=False,
    )
    print(dry_result.stdout, end="")
    if dry_result.returncode != 0:
        print(dry_result.stderr, file=sys.stderr, end="")
        return dry_result.returncode
    if not args.execute:
        return 0

    if ai_nodes:
        expected = plan.spec["pipeline_name"]
        print(
            f"Preview runs AI nodes and incurs cost. Type the Pipeline name to "
            f"confirm ({expected}): ",
            file=sys.stderr,
            end="",
            flush=True,
        )
        if sys.stdin.readline().strip() != expected:
            raise PipelineError("confirmation did not match Pipeline name; preview aborted")

    result = run_cli(
        build_preview_command(plan, from_time=from_time, to_time=to_time, dry_run=False),
        check=False,
    )
    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, file=sys.stderr, end="")
        return result.returncode

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stdout, end="")
        return 0

    print(
        "NOTE: previewed rows can contain real user content from the source LogStore",
        file=sys.stderr,
    )
    print(_json_dumps(_redact(payload)))
    verdict = check_preview_columns(plan, payload)
    if verdict is not None:
        print(_json_dumps({"column_check": verdict}))
        if not verdict["ok"]:
            print(
                "WARNING: previewed columns do not cover the declared output columns; "
                "fix the spec and preview again before creating",
                file=sys.stderr,
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="check local CLI and optional access")
    doctor.add_argument("--agent-space")
    doctor.add_argument("--region")
    doctor.set_defaults(func=cmd_doctor)

    preview = subparsers.add_parser(
        "preview",
        help="trial-run one spec's nodes over a bounded window without creating it",
    )
    preview.add_argument("--spec", required=True)
    preview.add_argument(
        "--from-time",
        required=True,
        help="window start as Unix seconds or ISO-8601 with a timezone offset",
    )
    preview.add_argument(
        "--to-time",
        required=True,
        help="window end as Unix seconds or ISO-8601 with a timezone offset",
    )
    preview.add_argument("--execute", action="store_true")
    preview.add_argument("--allow-scheduled", action="store_true")
    preview.set_defaults(func=cmd_preview)

    create = subparsers.add_parser("create", help="validate and create one Pipeline")
    create.add_argument("--spec", required=True)
    create.add_argument("--execute", action="store_true")
    create.add_argument("--allow-scheduled", action="store_true")
    create.set_defaults(func=cmd_create)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except PipelineError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
