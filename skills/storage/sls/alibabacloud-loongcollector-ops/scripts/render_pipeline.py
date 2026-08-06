#!/usr/bin/env python3
"""render_pipeline.py — render a Logtail pipeline config from task inputs.

Builds the canonical pipeline skeleton (exactly 1 input, optional processors,
exactly 1 flusher_sls) so it can be handed to `aliyun sls create/update-logtail-
pipeline-config`. This only renders; validation lives in validate_pipeline.py.

Input : a task JSON (via --input FILE or stdin) shaped like:
  {
    "config_name": "nginx-access",
    "logstore": "nginx-log",
    "log_sample": "...",                       # optional
    "scenario": "host|docker_stdio|k8s_stdio|docker_file|k8s_file",
    "input": { ... }        or "file_paths": ["/var/log/app/*.log"],
    "processors": [ ... ],                       # optional, native-first
    "global": { "TopicType": "machine_group_topic" },   # optional
    "container_filters": { ... }                 # optional (container scenarios)
  }

Protocol: stdout = single JSON object {tool,status,config,cli_hint};
          stderr = diagnostics; exit 0 ok, 2 usage/parse error.

Usage:
  python3 scripts/render_pipeline.py --input task.json [--format json|yaml]
  cat task.json | python3 scripts/render_pipeline.py
"""
import argparse
import json
import os
import sys

SCENARIO_INPUT = {
    "host": "input_file",
    "docker_file": "input_file",
    "k8s_file": "input_file",
    "docker_stdio": "input_container_stdio",
    "k8s_stdio": "input_container_stdio",
}


def die(msg, code=2):
    sys.stderr.write("[render_pipeline] %s\n" % msg)
    sys.exit(code)


def build_input(task):
    if isinstance(task.get("input"), dict) and task["input"].get("Type"):
        return dict(task["input"])
    scenario = task.get("scenario", "host")
    itype = SCENARIO_INPUT.get(scenario, "input_file")
    inp = {"Type": itype}
    if itype == "input_file":
        paths = task.get("file_paths") or task.get("log_path")
        if isinstance(paths, str):
            paths = [paths]
        if not paths:
            die("input_file scenario requires file_paths/log_path")
        inp["FilePaths"] = paths
    else:  # input_container_stdio
        inp["IgnoringStdout"] = False
        inp["IgnoringStderr"] = False
        cf = task.get("container_filters")
        if isinstance(cf, dict) and cf:
            inp["ContainerFilters"] = cf
    return inp


def build_flusher(task):
    logstore = task.get("logstore")
    if not logstore:
        die("logstore is required for flusher_sls")
    return {"Type": "flusher_sls", "Logstore": logstore}


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--input", help="task JSON file; omit to read stdin")
    ap.add_argument("--format", choices=["json", "yaml"], default="json")
    args = ap.parse_args()

    raw = ""
    if args.input:
        if not os.path.isfile(args.input):
            die("input file not found: %s" % args.input)
        with open(args.input, "r", encoding="utf-8") as fh:
            raw = fh.read()
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        die("empty input")
    try:
        task = json.loads(raw)
    except json.JSONDecodeError as e:
        die("input is not valid JSON: %s" % e)

    if not task.get("config_name"):
        die("config_name is required")

    config = {
        "configName": task["config_name"],
        "inputs": [build_input(task)],
        "flushers": [build_flusher(task)],
    }
    if task.get("log_sample"):
        config["logSample"] = task["log_sample"]
    if isinstance(task.get("global"), dict) and task["global"]:
        config["global"] = task["global"]
    else:
        config["global"] = {"TopicType": "machine_group_topic"}
    procs = task.get("processors")
    if isinstance(procs, list) and procs:
        config["processors"] = procs

    inputs_json = json.dumps(config["inputs"], ensure_ascii=False)
    flushers_json = json.dumps(config["flushers"], ensure_ascii=False)
    cli_hint = (
        "aliyun sls create-logtail-pipeline-config --project <p> "
        "--config-name %s --inputs '%s' --flushers '%s' "
        "--region <r> --user-agent AlibabaCloud-Agent-Skills/"
        "alibabacloud-loongcollector-ops/%s  # add --processors/--global; run --cli-dry-run first"
        % (config["configName"], inputs_json, flushers_json,
           os.environ.get("SKILL_SESSION_ID", "<session-id>"))
    )

    if args.format == "yaml":
        rendered = _to_yaml(config)
    else:
        rendered = json.dumps(config, ensure_ascii=False, indent=2)

    out = {
        "tool": "render_pipeline",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        "status": "ok",
        "format": args.format,
        "config": config,
        "rendered": rendered,
        "cli_hint": cli_hint,
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


def _to_yaml(obj, indent=0):
    """Minimal YAML emitter (no external deps) for dict/list/scalar."""
    pad = "  " * indent
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)) and v:
                lines.append("%s%s:" % (pad, k))
                lines.append(_to_yaml(v, indent + 1))
            else:
                lines.append("%s%s: %s" % (pad, k, _scalar(v)))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                block = _to_yaml(item, indent + 1)
                block = block[len(pad) + 2:] if block.startswith(pad + "  ") else block.lstrip()
                lines.append("%s- %s" % (pad, block.lstrip()))
            else:
                lines.append("%s- %s" % (pad, _scalar(item)))
    else:
        lines.append("%s%s" % (pad, _scalar(obj)))
    return "\n".join(lines)


def _scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return json.dumps(v, ensure_ascii=False) if isinstance(v, str) else str(v)


if __name__ == "__main__":
    sys.exit(main())
