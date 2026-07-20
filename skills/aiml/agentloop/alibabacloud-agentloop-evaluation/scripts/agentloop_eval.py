#!/usr/bin/env python3
"""Safe orchestration for AgentLoop evaluator, task, and run CLI APIs.

Dependencies: Python 3.8+ standard library only (no external packages required).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


PLUGIN_NAME = "aliyun-cli-agentloop"
SKILL_NAME = "alibabacloud-agentloop-evaluation"
LOCAL_SUBCOMMANDS = {"version", "plugin", "configure"}
JSON_FLAGS = {
    "--config",
    "--data-filter",
    "--evaluators",
    "--run-strategies",
    "--tags",
    "--properties",
}
SUCCESS_STATES = {"completed", "complete", "succeeded", "success", "finished"}
FAILURE_STATES = {"failed", "failure", "cancelled", "canceled", "terminated", "error"}
CREATABLE_EVALUATOR_TYPES = {"LLM", "AGENT", "CODE"}
MAX_DISCOVERY_PAGES = 100


class WorkflowError(RuntimeError):
    """A user-actionable workflow failure."""


def compact_json(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def bool_text(value: bool) -> str:
    return "true" if value else "false"


def cli_value(value: Any) -> str:
    if isinstance(value, bool):
        return bool_text(value)
    return str(value)


def display_command(command: list[str]) -> str:
    rendered: list[str] = []
    hide_next = False
    for token in command:
        if hide_next:
            rendered.append("<json>")
            hide_next = False
            continue
        rendered.append(token)
        hide_next = token in JSON_FLAGS
    return shlex.join(rendered)


ALLOWED_BINARIES = {"aliyun"}


def _validate_command(command: list[str]) -> None:
    """Validate that the command is safe to execute.

    Security checks:
    - The binary (command[0]) must be in the allow-list (currently only "aliyun").
    - No argument may contain null bytes, which could truncate or alter the
      argument on certain platforms.
    - No argument may contain newline characters, which could obscure additional
      commands in log output.

    This function complements the list-based subprocess invocation (no shell=True)
    to provide defense-in-depth against command injection.
    """
    if not command:
        raise WorkflowError("refusing to execute an empty command")
    binary = command[0]
    if binary not in ALLOWED_BINARIES:
        raise WorkflowError(
            f"refusing to execute disallowed binary: {binary!r}; "
            f"only {sorted(ALLOWED_BINARIES)} are permitted"
        )
    for index, arg in enumerate(command):
        if "\x00" in arg:
            raise WorkflowError(f"command argument at position {index} contains a null byte")
        if "\n" in arg or "\r" in arg:
            raise WorkflowError(
                f"command argument at position {index} contains a newline character"
            )


def _is_cloud_api_command(command: list[str]) -> bool:
    """Return True if the command is an aliyun cloud API call that needs --user-agent."""
    if len(command) < 2 or command[0] != "aliyun":
        return False
    if command[1] in LOCAL_SUBCOMMANDS:
        return False
    if len(command) >= 3 and command[2] == "version":
        return False
    return True


def _ensure_user_agent(command: list[str]) -> list[str]:
    """Inject --user-agent into aliyun cloud API commands when SKILL_SESSION_ID is set."""
    if not _is_cloud_api_command(command):
        return command
    if "--user-agent" in command:
        return command
    session_id = os.environ.get("SKILL_SESSION_ID", "")
    if not session_id:
        print(
            "WARNING: SKILL_SESSION_ID is not set; --user-agent omitted from cloud API command. "
            "Set SKILL_SESSION_ID for observability compliance.",
            file=sys.stderr,
        )
        return command
    user_agent = f"AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session_id}"
    result = list(command)
    for i, token in enumerate(result):
        if token in ("--region", "--endpoint"):
            result.insert(i, user_agent)
            result.insert(i, "--user-agent")
            return result
    result.extend(["--user-agent", user_agent])
    return result


def run_cli(
    command: list[str],
    *,
    echo_output: bool = True,
    timeout: int = 300,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Execute a CLI command safely.

    Security: commands are passed as a list (not a string) to subprocess.run()
    without shell=True, which prevents shell metacharacter injection. The
    _validate_command() function additionally enforces an allow-list of
    binaries and rejects arguments containing null bytes or newlines.
    """
    command = _ensure_user_agent(command)
    _validate_command(command)
    print(f"+ {display_command(command)}", flush=True)
    try:
        proc = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise WorkflowError("aliyun CLI was not found in PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise WorkflowError(f"command timed out after {timeout}s") from exc

    if echo_output and proc.stdout.strip():
        print(proc.stdout.rstrip())
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    if check and proc.returncode != 0:
        detail = proc.stderr.strip() or proc.stdout.strip() or "no error detail"
        raise WorkflowError(f"command failed with exit code {proc.returncode}: {detail}")
    return proc


def parse_json_output(output: str) -> Any:
    text = output.strip()
    if not text:
        raise WorkflowError("the CLI returned an empty response")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError:
            continue
    raise WorkflowError(f"could not parse the CLI response as JSON: {text[:500]}")


def run_json(command: list[str], *, timeout: int = 300, echo_output: bool = False) -> Any:
    proc = run_cli(command, echo_output=echo_output, timeout=timeout)
    return parse_json_output(proc.stdout)


def add_connection_flags(command: list[str], region: str | None, endpoint: str | None) -> None:
    if region:
        command.extend(["--region", region])
    if endpoint:
        command.extend(["--endpoint", endpoint])


def require_fields(mapping: dict[str, Any], fields: Iterable[str], context: str) -> None:
    missing = [field for field in fields if mapping.get(field) in (None, "")]
    if missing:
        raise WorkflowError(f"{context} is missing required fields: {', '.join(missing)}")


def load_spec(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError as exc:
        raise WorkflowError(f"spec file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError("the workflow specification must be a JSON object")
    return value


def rename_keys(value: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, item in value.items():
        canonical = aliases.get(key, key)
        if canonical in result and canonical != key:
            raise WorkflowError(f"both {key!r} and its canonical alias {canonical!r} are present")
        result[canonical] = item
    return result


def parse_epoch_millis(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise WorkflowError(f"{field} must be ISO-8601 or epoch milliseconds")
    if isinstance(value, (int, float)):
        millis = int(value)
        if millis < 100_000_000_000:
            raise WorkflowError(f"{field} looks like seconds; pass epoch milliseconds")
        return millis
    if not isinstance(value, str):
        raise WorkflowError(f"{field} must be ISO-8601 or epoch milliseconds")
    text = value.strip()
    if text.isdigit():
        return parse_epoch_millis(int(text), field)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise WorkflowError(f"{field} is not valid ISO-8601: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WorkflowError(f"{field} must include a timezone offset")
    return int(parsed.timestamp() * 1000)


def normalize_evaluators(task: dict[str, Any]) -> list[dict[str, Any]]:
    raw = task.get("evaluators")
    refs = task.get("evaluator_refs")
    if raw is not None and refs is not None:
        raise WorkflowError("task must use either evaluators or evaluator_refs, not both")
    if raw is not None:
        if not isinstance(raw, list) or not raw:
            raise WorkflowError("task.evaluators must be a non-empty array")
        evaluators = copy.deepcopy(raw)
    else:
        if not isinstance(refs, list) or not refs:
            raise WorkflowError("task.evaluator_refs must be a non-empty array")
        evaluators = []
        aliases = {
            "result_name": "resultName",
            "result_type": "resultType",
            "variable_mapping": "variableMapping",
        }
        for index, reference in enumerate(refs):
            if not isinstance(reference, dict):
                raise WorkflowError(f"task.evaluator_refs[{index}] must be an object")
            ref = reference.get("ref") or reference.get("evaluatorRef")
            if not ref:
                raise WorkflowError(f"task.evaluator_refs[{index}] is missing ref")
            evaluator: dict[str, Any] = {"evaluatorRef": ref}
            for source, target in aliases.items():
                if source in reference:
                    evaluator[target] = copy.deepcopy(reference[source])
                elif target in reference:
                    evaluator[target] = copy.deepcopy(reference[target])
            for key in ("filters", "config"):
                if key in reference:
                    evaluator[key] = copy.deepcopy(reference[key])
            if reference.get("version"):
                config = evaluator.setdefault("config", {})
                if not isinstance(config, dict):
                    raise WorkflowError(f"task.evaluator_refs[{index}].config must be an object")
                config["version"] = reference["version"]
            evaluators.append(evaluator)

    identities: set[str] = set()
    for index, evaluator in enumerate(evaluators):
        if not isinstance(evaluator, dict):
            raise WorkflowError(f"task evaluator {index} must be an object")
        identity = evaluator.get("evaluatorRef") or evaluator.get("name")
        if not identity:
            raise WorkflowError(f"task evaluator {index} requires evaluatorRef or name")
        identity_text = str(identity)
        if identity_text in identities:
            raise WorkflowError(f"duplicate evaluator identity: {identity_text}")
        identities.add(identity_text)
    return evaluators


def normalize_task(
    spec: dict[str, Any],
    allow_unbounded: bool,
    allow_continuous: bool = False,
) -> dict[str, Any]:
    agent_space = spec.get("agent_space")
    if not isinstance(agent_space, str) or not agent_space.strip():
        raise WorkflowError("agent_space is required")
    raw_task = spec.get("task")
    if not isinstance(raw_task, dict):
        raise WorkflowError("task must be an object")
    task = copy.deepcopy(raw_task)

    data_filter = task.get("data_filter", task.get("dataFilter"))
    if not isinstance(data_filter, dict):
        raise WorkflowError("task.data_filter must be an object")
    data_filter = rename_keys(
        data_filter,
        {
            "max_records": "maxRecords",
            "sampling_rate": "samplingRate",
            "start_time": "startTime",
            "end_time": "endTime",
        },
    )

    mode = str(task.get("mode", task.get("taskMode", ""))).lower()
    if not mode:
        mode = "oneshot" if "provided" in data_filter else "batch"
    if mode not in {"oneshot", "batch"}:
        raise WorkflowError("task.mode must be oneshot or batch")
    if mode == "oneshot" and "provided" not in data_filter:
        raise WorkflowError("oneshot tasks require task.data_filter.provided")
    if mode == "batch" and "maxRecords" not in data_filter and not allow_unbounded:
        raise WorkflowError(
            "batch tasks require task.data_filter.max_records; use --allow-unbounded only after explicit approval"
        )
    if "maxRecords" in data_filter:
        max_records = data_filter["maxRecords"]
        if not isinstance(max_records, int) or isinstance(max_records, bool) or max_records <= 0:
            raise WorkflowError("task.data_filter.max_records must be a positive integer")

    run_strategies = task.get("run_strategies", task.get("runStrategies"))
    window = task.get("window")
    if mode == "batch" and window is None and run_strategies is None:
        raise WorkflowError(
            "batch tasks require task.window or task.run_strategies with a bounded backfill window; "
            "use task.window for simple start/end time ranges"
        )
    if window is not None and run_strategies is not None:
        raise WorkflowError("task.window and task.run_strategies are mutually exclusive")
    if window is not None:
        if not isinstance(window, dict):
            raise WorkflowError("task.window must be an object")
        require_fields(window, ("start", "end"), "task.window")
        start_ms = parse_epoch_millis(window["start"], "task.window.start")
        end_ms = parse_epoch_millis(window["end"], "task.window.end")
        if start_ms >= end_ms:
            raise WorkflowError("task.window.start must be earlier than task.window.end")
        run_strategies = {
            "backfill": {"enabled": True, "startTime": start_ms, "endTime": end_ms},
            "continuous": {
                "enabled": False,
                "intervalUnit": "MINUTE",
                "intervalValue": 1,
                "dataDelayMinutes": 1,
            },
        }
    if run_strategies is not None and not isinstance(run_strategies, dict):
        raise WorkflowError("task.run_strategies must be an object")
    if isinstance(run_strategies, dict):
        continuous = run_strategies.get("continuous")
        if continuous is not None:
            if not isinstance(continuous, dict):
                raise WorkflowError("task.run_strategies.continuous must be an object")
            continuous_enabled = continuous.get("enabled", False)
            if not isinstance(continuous_enabled, bool):
                raise WorkflowError("task.run_strategies.continuous.enabled must be a boolean")
            if continuous_enabled and not allow_continuous:
                raise WorkflowError(
                    "continuous evaluation requires --allow-continuous after explicit cost approval"
                )

    evaluators = normalize_evaluators(task)
    task_name = task.get("name") or task.get("task_name") or task.get("taskName")
    if not task_name:
        task_name = datetime.now().astimezone().strftime("eval-%Y%m%dT%H%M%S%z")

    data_type = str(task.get("data_type", task.get("dataType", "trace"))).lower()
    config = task.get("config")
    if mode == "batch" and data_type == "dataset":
        if not isinstance(config, dict):
            raise WorkflowError(
                "dataset tasks require task.config.datasetName or task.config.storeName"
            )
        dataset_name = config.get("datasetName") or config.get("storeName")
        if not isinstance(dataset_name, str) or not dataset_name.strip():
            raise WorkflowError(
                "dataset tasks require exact camelCase task.config.datasetName or task.config.storeName"
            )

    normalized: dict[str, Any] = {
        "name": str(task_name),
        "mode": mode,
        "data_type": data_type,
        "data_filter": data_filter,
        "evaluators": evaluators,
    }
    optional_aliases = {
        "channel": ("channel",),
        "client_token": ("client_token", "clientToken"),
        "config": ("config",),
        "description": ("description",),
        "tags": ("tags",),
    }
    for target, sources in optional_aliases.items():
        for source in sources:
            if source in task and task[source] is not None:
                normalized[target] = copy.deepcopy(task[source])
                break
    if run_strategies is not None:
        normalized["run_strategies"] = copy.deepcopy(run_strategies)
    return normalized


def evaluator_actions(spec: dict[str, Any]) -> list[dict[str, Any]]:
    value = spec.get("evaluator_actions", [])
    if "evaluator" in spec:
        if value:
            raise WorkflowError("use evaluator_actions or evaluator, not both")
        value = [spec["evaluator"]]
    if not isinstance(value, list):
        raise WorkflowError("evaluator_actions must be an array")
    for index, action in enumerate(value):
        if not isinstance(action, dict):
            raise WorkflowError(f"evaluator_actions[{index}] must be an object")
    return copy.deepcopy(value)


def custom_evaluator_references(evaluators: list[dict[str, Any]]) -> list[tuple[str, str | None]]:
    references: set[tuple[str, str | None]] = set()
    for evaluator in evaluators:
        reference_value = evaluator.get("evaluatorRef")
        if not reference_value or str(reference_value).lower().startswith("builtin."):
            continue
        config = evaluator.get("config")
        version_value = config.get("version") if isinstance(config, dict) else None
        version = str(version_value) if version_value not in (None, "") else None
        references.add((str(reference_value), version))
    return sorted(references, key=lambda item: item[0])


def append_optional(command: list[str], flag: str, value: Any, *, as_json: bool = False) -> None:
    if value is None:
        return
    command.extend([flag, compact_json(value) if as_json else cli_value(value)])


def build_evaluator_command(
    agent_space: str,
    definition: dict[str, Any],
    region: str | None,
    endpoint: str | None,
) -> list[str] | None:
    action = str(definition.get("action", "reuse")).lower()
    if action == "reuse":
        return None
    if action not in {"create", "update"}:
        raise WorkflowError(f"unsupported evaluator action: {action}")
    if action == "create":
        require_fields(
            definition,
            ("name", "type", "metric_name", "biz_version"),
            "create evaluator action",
        )
        evaluator_type = str(definition["type"]).strip()
        if evaluator_type not in CREATABLE_EVALUATOR_TYPES:
            raise WorkflowError(
                f"create evaluator action type must be one of {sorted(CREATABLE_EVALUATOR_TYPES)} "
                f"(exact uppercase); got {evaluator_type!r}"
            )
        command = [
            "aliyun",
            "agentloop",
            "create-evaluator",
            "--agent-space",
            agent_space,
            "--name",
            str(definition["name"]),
            "--type",
            evaluator_type,
            "--metric-name",
            str(definition["metric_name"]),
            "--biz-version",
            str(definition["biz_version"]),
        ]
    else:
        require_fields(definition, ("name",), "update evaluator action")
        command = [
            "aliyun",
            "agentloop",
            "update-evaluator",
            "--agent-space",
            agent_space,
            "--name",
            str(definition["name"]),
        ]

    mappings = (
        ("client_token", "--client-token", False),
        ("config", "--config", True),
        ("description", "--description", False),
        ("display_name", "--display-name", False),
        ("properties", "--properties", True),
        ("version_description", "--version-description", False),
    )
    if action == "update":
        mappings += (("biz_version", "--biz-version", False),)
    for key, flag, as_json in mappings:
        append_optional(command, flag, definition.get(key), as_json=as_json)
    annotations = definition.get("annotations")
    if annotations is not None:
        if not isinstance(annotations, list):
            raise WorkflowError("evaluator annotations must be an array")
        command.append("--annotations")
        command.extend(str(item) for item in annotations)
    add_connection_flags(command, region, endpoint)
    return command


def build_task_command(
    agent_space: str,
    task: dict[str, Any],
    region: str | None,
    endpoint: str | None,
) -> list[str]:
    command = [
        "aliyun",
        "agentloop",
        "create-evaluation-task",
        "--agent-space",
        agent_space,
        "--task-name",
        task["name"],
        "--task-mode",
        task["mode"],
        "--data-type",
        task["data_type"],
        "--data-filter",
        compact_json(task["data_filter"]),
        "--evaluators",
        compact_json(task["evaluators"]),
    ]
    simple = (
        ("channel", "--channel"),
        ("client_token", "--client-token"),
        ("description", "--description"),
    )
    for key, flag in simple:
        append_optional(command, flag, task.get(key))
    complex_values = (
        ("config", "--config"),
        ("run_strategies", "--run-strategies"),
        ("tags", "--tags"),
    )
    for key, flag in complex_values:
        append_optional(command, flag, task.get(key), as_json=True)
    add_connection_flags(command, region, endpoint)
    return command


def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def get_case_insensitive(mapping: dict[str, Any], key: str) -> Any:
    wanted = key.lower()
    for candidate, value in mapping.items():
        if candidate.lower() == wanted:
            return value
    return None


def find_first(value: Any, keys: Iterable[str]) -> Any:
    dictionaries = list(iter_dicts(value))
    for key in keys:
        for mapping in dictionaries:
            found = get_case_insensitive(mapping, key)
            if found not in (None, ""):
                return found
    return None


def extract_status(value: Any) -> str | None:
    status = find_first(value, ("lastRunStatus", "runStatus", "taskStatus", "status"))
    return str(status) if status not in (None, "") else None


def canonical_status(status: str | None) -> str:
    if not status:
        return ""
    return "".join(char for char in status.lower() if char.isalnum())


def extract_task_id(value: Any) -> str | None:
    task_id = find_first(value, ("taskId", "evaluationTaskId"))
    return str(task_id) if task_id not in (None, "") else None


def run_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for mapping in iter_dicts(value):
        run_id = get_case_insensitive(mapping, "runId")
        if run_id in (None, ""):
            continue
        key = str(run_id)
        if key not in seen:
            records.append(mapping)
            seen.add(key)
    return records


def latest_run(value: Any) -> dict[str, Any] | None:
    records = run_records(value)
    return records[0] if records else None


def get_agent_space_command(agent_space: str, region: str | None, endpoint: str | None) -> list[str]:
    command = ["aliyun", "agentloop", "get-agent-space", "--agent-space", agent_space]
    add_connection_flags(command, region, endpoint)
    return command


def get_evaluator_command(
    agent_space: str,
    name: str,
    region: str | None,
    endpoint: str | None,
    biz_version: str | None = None,
) -> list[str]:
    command = [
        "aliyun",
        "agentloop",
        "get-evaluator",
        "--agent-space",
        agent_space,
        "--name",
        name,
    ]
    if biz_version:
        command.extend(["--biz-version", biz_version])
    add_connection_flags(command, region, endpoint)
    return command


def get_task_command(
    agent_space: str,
    task_id: str,
    region: str | None,
    endpoint: str | None,
) -> list[str]:
    command = [
        "aliyun",
        "agentloop",
        "get-evaluation-task",
        "--agent-space",
        agent_space,
        "--task-id",
        task_id,
    ]
    add_connection_flags(command, region, endpoint)
    return command


def list_runs_command(
    agent_space: str,
    task_id: str,
    region: str | None,
    endpoint: str | None,
) -> list[str]:
    command = [
        "aliyun",
        "agentloop",
        "list-evaluation-runs",
        "--agent-space",
        agent_space,
        "--task-id",
        task_id,
        "--max-results",
        "20",
    ]
    add_connection_flags(command, region, endpoint)
    return command


def get_run_command(
    agent_space: str,
    task_id: str,
    run_id: str,
    region: str | None,
    endpoint: str | None,
) -> list[str]:
    command = [
        "aliyun",
        "agentloop",
        "get-evaluation-run",
        "--agent-space",
        agent_space,
        "--task-id",
        task_id,
        "--run-id",
        run_id,
    ]
    add_connection_flags(command, region, endpoint)
    return command


def poll_evaluation(
    agent_space: str,
    task_id: str,
    region: str | None,
    endpoint: str | None,
    timeout_seconds: int,
    poll_interval: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_status: str | None = None
    last_task: Any = None
    last_runs: Any = None
    selected: dict[str, Any] | None = None

    while True:
        last_task = run_json(
            get_task_command(agent_space, task_id, region, endpoint), timeout=120
        )
        try:
            last_runs = run_json(
                list_runs_command(agent_space, task_id, region, endpoint), timeout=120
            )
        except WorkflowError as exc:
            print(f"Run list is not available yet: {exc}", file=sys.stderr)
            last_runs = {}
        selected = latest_run(last_runs)
        run_status = extract_status(selected) if selected else None
        task_status = extract_status(last_task)
        effective_status = run_status or task_status or "Unknown"
        if effective_status != last_status:
            print(f"Evaluation status: {effective_status}", flush=True)
            last_status = effective_status

        canonical = canonical_status(effective_status)
        if canonical in SUCCESS_STATES or canonical in FAILURE_STATES:
            run_id_value = get_case_insensitive(selected, "runId") if selected else None
            run_id = str(run_id_value) if run_id_value not in (None, "") else None
            run_detail = None
            if run_id:
                run_detail = run_json(
                    get_run_command(agent_space, task_id, run_id, region, endpoint),
                    timeout=120,
                )
            return {
                "taskId": task_id,
                "runId": run_id,
                "status": effective_status,
                "task": last_task,
                "runs": last_runs,
                "run": run_detail,
            }

        if time.monotonic() >= deadline:
            raise WorkflowError(
                f"evaluation did not reach a terminal state within {timeout_seconds}s; "
                f"taskId={task_id}, lastStatus={effective_status}"
            )
        time.sleep(min(max(poll_interval, 0.5), 60.0))


def write_result(path: Path | None, value: Any) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote result: {path.resolve()}")


def fetch_discovery_pages(command: list[str], all_pages: bool) -> list[Any]:
    pages: list[Any] = []
    next_token: str | None = None
    seen_tokens: set[str] = set()
    while True:
        current = list(command)
        if next_token:
            current.extend(["--next-token", next_token])
        response = run_json(current)
        pages.append(response)
        if not all_pages:
            break
        token_value = find_first(response, ("nextToken",))
        if token_value in (None, ""):
            break
        token = str(token_value)
        if token in seen_tokens:
            raise WorkflowError("discovery pagination returned a repeated nextToken")
        if len(pages) >= MAX_DISCOVERY_PAGES:
            raise WorkflowError(
                f"discovery exceeded {MAX_DISCOVERY_PAGES} pages; narrow the query"
            )
        seen_tokens.add(token)
        next_token = token
    return pages


def print_discovery_result(title: str, pages: list[Any]) -> None:
    print(f"\n{title}")
    value: Any = pages[0] if len(pages) == 1 else {"pageCount": len(pages), "pages": pages}
    print(json.dumps(value, ensure_ascii=False, indent=2))


MIN_CLI_VERSION = (3, 3, 3)


def _parse_cli_version(text: str) -> tuple[int, ...]:
    """Extract a version tuple from aliyun CLI version output."""
    for token in text.split():
        parts = token.split(".")
        if len(parts) >= 3 and all(part.isdigit() for part in parts[:3]):
            return tuple(int(part) for part in parts[:3])
    raise WorkflowError(f"could not parse CLI version from output: {text.strip()}")


def command_doctor(args: argparse.Namespace) -> int:
    if not shutil.which("aliyun"):
        raise WorkflowError("aliyun CLI is not installed or not in PATH")
    version_proc = run_cli(["aliyun", "version"])
    cli_version = _parse_cli_version(version_proc.stdout)
    if cli_version < MIN_CLI_VERSION:
        raise WorkflowError(
            f"aliyun CLI version {'.'.join(map(str, cli_version))} is below the required minimum "
            f"{'.'.join(map(str, MIN_CLI_VERSION))}"
        )
    run_cli(["aliyun", "plugin", "show", "--name", PLUGIN_NAME])
    run_cli(["aliyun", "agentloop", "version"])
    if args.agent_space:
        run_json(
            get_agent_space_command(args.agent_space, args.region, args.endpoint),
            echo_output=True,
        )
    print("Doctor checks passed.")
    return 0


def command_discover(args: argparse.Namespace) -> int:
    if args.max_results <= 0 or args.max_results > 100:
        raise WorkflowError("--max-results must be between 1 and 100")
    saved_evaluators = [
        "aliyun",
        "agentloop",
        "list-evaluators",
        "--agent-space",
        args.agent_space,
        "--source",
        "custom",
        "--max-results",
        str(args.max_results),
    ]
    builtin_evaluators = [
        "aliyun",
        "agentloop",
        "list-evaluators",
        "--agent-space",
        args.agent_space,
        "--source",
        "builtin",
        "--max-results",
        str(args.max_results),
    ]
    tasks = [
        "aliyun",
        "agentloop",
        "list-evaluation-tasks",
        "--agent-space",
        args.agent_space,
        "--max-results",
        str(args.max_results),
    ]
    if args.channel:
        tasks.extend(["--channel", args.channel])
    add_connection_flags(saved_evaluators, args.region, args.endpoint)
    add_connection_flags(builtin_evaluators, args.region, args.endpoint)
    add_connection_flags(tasks, args.region, args.endpoint)
    print_discovery_result(
        "Saved evaluators", fetch_discovery_pages(saved_evaluators, args.all_pages)
    )
    print_discovery_result(
        "Built-in evaluators", fetch_discovery_pages(builtin_evaluators, args.all_pages)
    )
    print_discovery_result("Evaluation tasks", fetch_discovery_pages(tasks, args.all_pages))
    return 0


def command_run(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    agent_space = str(spec.get("agent_space", ""))
    region = spec.get("region")
    endpoint = spec.get("endpoint")
    task = normalize_task(spec, args.allow_unbounded, args.allow_continuous)
    actions = evaluator_actions(spec)
    evaluator_commands = [
        command
        for definition in actions
        if (command := build_evaluator_command(agent_space, definition, region, endpoint)) is not None
    ]
    task_command = build_task_command(agent_space, task, region, endpoint)

    if not args.execute:
        print(
            "Dry-run preview; no AgentLoop mutation request will be sent. "
            "The CLI may still resolve or refresh credentials."
        )
        for command in evaluator_commands:
            run_cli(command + ["--cli-dry-run"])
        run_cli(task_command + ["--cli-dry-run"])
        print("Preview completed. Re-run with --execute to apply it.")
        return 0

    print("Verifying AgentSpace before mutation...")
    run_json(get_agent_space_command(agent_space, region, endpoint))

    for command in evaluator_commands:
        run_json(command, echo_output=True)

    for reference, version in custom_evaluator_references(task["evaluators"]):
        version_suffix = f"@{version}" if version else ""
        print(f"Verifying evaluator reference: {reference}{version_suffix}")
        run_json(
            get_evaluator_command(
                agent_space,
                reference,
                region,
                endpoint,
                biz_version=version,
            )
        )

    create_response = run_json(task_command, echo_output=True, timeout=7200)
    task_id = extract_task_id(create_response)
    if not task_id:
        raise WorkflowError("task creation succeeded but the response did not contain taskId")
    print(f"Created evaluation task: {task_id}")

    if args.no_wait:
        result = {"taskId": task_id, "createResponse": create_response}
        write_result(args.output, result)
        return 0

    result = poll_evaluation(
        agent_space,
        task_id,
        region,
        endpoint,
        args.timeout,
        args.poll_interval,
    )
    result["createResponse"] = create_response
    write_result(args.output, result)
    print(f"Evaluation finished: taskId={task_id}, runId={result.get('runId')}, status={result['status']}")
    return 3 if canonical_status(result["status"]) in FAILURE_STATES else 0


def command_status(args: argparse.Namespace) -> int:
    if args.wait:
        result = poll_evaluation(
            args.agent_space,
            args.task_id,
            args.region,
            args.endpoint,
            args.timeout,
            args.poll_interval,
        )
    else:
        task = run_json(
            get_task_command(args.agent_space, args.task_id, args.region, args.endpoint)
        )
        runs = run_json(
            list_runs_command(args.agent_space, args.task_id, args.region, args.endpoint)
        )
        selected = latest_run(runs)
        run_id_value = get_case_insensitive(selected, "runId") if selected else None
        run_id = str(run_id_value) if run_id_value not in (None, "") else None
        detail = (
            run_json(
                get_run_command(args.agent_space, args.task_id, run_id, args.region, args.endpoint)
            )
            if run_id
            else None
        )
        result = {
            "taskId": args.task_id,
            "runId": run_id,
            "status": extract_status(selected) if selected else extract_status(task),
            "task": task,
            "runs": runs,
            "run": detail,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    write_result(args.output, result)
    return 0


def add_connection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--region", help="override endpoint-selection region")
    parser.add_argument("--endpoint", help="override AgentLoop service endpoint")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely orchestrate AgentLoop evaluation CLI workflows"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="check CLI/plugin and optionally cloud access")
    doctor.add_argument("--agent-space", help="verify one AgentSpace with a read-only call")
    add_connection_arguments(doctor)
    doctor.set_defaults(func=command_doctor)

    discover = subparsers.add_parser("discover", help="list evaluators and evaluation tasks")
    discover.add_argument("--agent-space", required=True)
    discover.add_argument("--max-results", type=int, default=100)
    discover.add_argument("--all-pages", action="store_true", help="follow nextToken pagination")
    discover.add_argument("--channel", help="query evaluation tasks in this channel")
    add_connection_arguments(discover)
    discover.set_defaults(func=command_discover)

    run_parser = subparsers.add_parser("run", help="preview or execute an evaluation spec")
    run_parser.add_argument("--spec", type=Path, required=True)
    run_parser.add_argument(
        "--execute",
        action="store_true",
        help="send cloud mutations; without this flag all mutations use --cli-dry-run",
    )
    run_parser.add_argument("--no-wait", action="store_true", help="return after task creation")
    run_parser.add_argument("--timeout", type=int, default=1800, help="poll timeout in seconds")
    run_parser.add_argument("--poll-interval", type=float, default=5.0, help="poll interval in seconds")
    run_parser.add_argument("--output", type=Path, help="write final JSON responses to this path")
    run_parser.add_argument(
        "--allow-unbounded",
        action="store_true",
        help="allow batch execution without dataFilter.maxRecords",
    )
    run_parser.add_argument(
        "--allow-continuous",
        action="store_true",
        help="allow continuous.enabled=true after explicit ongoing-cost approval",
    )
    run_parser.set_defaults(func=command_run)

    status = subparsers.add_parser("status", help="inspect or wait for an evaluation task")
    status.add_argument("--agent-space", required=True)
    status.add_argument("--task-id", required=True)
    status.add_argument("--wait", action="store_true")
    status.add_argument("--timeout", type=int, default=1800)
    status.add_argument("--poll-interval", type=float, default=5.0)
    status.add_argument("--output", type=Path)
    add_connection_arguments(status)
    status.set_defaults(func=command_status)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return int(args.func(args))
    except WorkflowError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
