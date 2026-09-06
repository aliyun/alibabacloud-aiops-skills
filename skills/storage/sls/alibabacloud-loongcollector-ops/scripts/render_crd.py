#!/usr/bin/env python3
"""render_crd.py — render a ClusterAliyunPipelineConfig from task JSON.

Reuses render_pipeline.build_* so spec.config stays isomorphic with the API
pipeline. Does not apply. stdout = one JSON object + YAML in `rendered`.

Usage:
  python3 scripts/render_crd.py --input task.json
  cat task.json | python3 scripts/render_crd.py
"""
import argparse
import json
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from render_pipeline import (  # noqa: E402
    build_flusher,
    build_input,
    die,
    AGENTSIGHT_SCENARIOS,
    AGENTSIGHT_CONFIG_NAME,
    AGENTSIGHT_LOGSTORE,
    agentsight_mask_processor,
)

NAME_RE = re.compile(r"^[a-z0-9]([a-z0-9_-]{0,126}[a-z0-9])?$")
FORBIDDEN_KINDS = ("AliyunLogConfig", "NamespaceAliyunPipelineConfig", "AliyunPipelineConfig")


def yaml_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    return json.dumps(v, ensure_ascii=False)


def to_yaml(obj, indent=0):
    pad = "  " * indent
    lines = []
    if isinstance(obj, dict):
        if not obj:
            return pad + "{}"
        for k, v in obj.items():
            if isinstance(v, dict):
                lines.append("%s%s:" % (pad, k))
                lines.append(to_yaml(v, indent + 1) if v else pad + "  {}")
            elif isinstance(v, list):
                lines.append("%s%s:" % (pad, k))
                lines.append(to_yaml(v, indent + 1) if v else pad + "  []")
            else:
                lines.append("%s%s: %s" % (pad, k, yaml_scalar(v)))
    elif isinstance(obj, list):
        if not obj:
            return pad + "[]"
        for item in obj:
            if isinstance(item, dict):
                keys = list(item.keys())
                first = keys[0]
                rest = {k: item[k] for k in keys[1:]}
                if isinstance(item[first], (dict, list)):
                    lines.append("%s- %s:" % (pad, first))
                    lines.append(to_yaml(item[first], indent + 2))
                    if rest:
                        lines.append(to_yaml(rest, indent + 1))
                else:
                    lines.append("%s- %s: %s" % (pad, first, yaml_scalar(item[first])))
                    if rest:
                        lines.append(to_yaml(rest, indent + 1))
            elif isinstance(item, list):
                lines.append("%s-" % pad)
                lines.append(to_yaml(item, indent + 1))
            else:
                lines.append("%s- %s" % (pad, yaml_scalar(item)))
    else:
        lines.append("%s%s" % (pad, yaml_scalar(obj)))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", help="task JSON file; omit to read stdin")
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

    kind = task.get("kind") or "ClusterAliyunPipelineConfig"
    if kind in FORBIDDEN_KINDS:
        die("refusing to render %s; write target is ClusterAliyunPipelineConfig" % kind)

    scenario = task.get("scenario", "k8s_stdio")
    if scenario in AGENTSIGHT_SCENARIOS:
        task.setdefault("config_name", AGENTSIGHT_CONFIG_NAME)
        task.setdefault("logstore", AGENTSIGHT_LOGSTORE)

    name = task.get("config_name") or task.get("name")
    if not name:
        die("config_name is required")
    if not NAME_RE.match(name):
        die("config_name must be 2-128 lowercase [a-z0-9_-] and match metadata.name")

    project = task.get("project") or (task.get("spec") or {}).get("project") or {}
    if isinstance(project, str):
        project = {"name": project}
    if not project.get("name"):
        die("project.name is required")

    cluster_id = task.get("cluster_id") or task.get("clusterID") or ""
    groups = task.get("machine_groups") or task.get("machineGroups")
    if not groups:
        if cluster_id:
            groups = ["k8s-group-%s" % cluster_id]
        elif task.get("machine_group"):
            groups = [task["machine_group"]]
        else:
            die("machine_groups or cluster_id is required")
    if isinstance(groups, str):
        groups = [groups]
    machine_groups = [{"name": g} if isinstance(g, str) else g for g in groups]

    config = {
        "inputs": [build_input(task)],
        "flushers": [build_flusher(task)],
        "global": task.get("global") if isinstance(task.get("global"), dict)
        else {"TopicType": "machine_group_topic"},
    }
    if task.get("log_sample"):
        config["sample"] = task["log_sample"]
    procs = task.get("processors")
    if procs is None and task.get("desensitize"):
        procs = [agentsight_mask_processor()]
    if isinstance(procs, list) and procs:
        config["processors"] = procs

    logstore_name = task.get("logstore")
    logstores = task.get("logstores")
    if not logstores and logstore_name:
        entry = {
            "name": logstore_name,
            "ttl": int(task.get("ttl") or 30),
            "shardCount": int(task.get("shard_count") or 2),
            "autoSplit": True,
            "maxSplitShard": 64,
            "appendMeta": True,
            "queryMode": "standard",
        }
        if isinstance(task.get("index"), dict) and task["index"]:
            entry["index"] = task["index"]
        logstores = [entry]

    spec = {
        "project": {k: v for k, v in project.items() if v not in (None, "")},
        "config": config,
        "machineGroups": machine_groups,
        "enableUpgradeOverride": bool(task.get("enable_upgrade_override", False)),
    }
    if logstores:
        spec["logstores"] = logstores

    cr = {
        "apiVersion": "telemetry.alibabacloud.com/v1alpha1",
        "kind": "ClusterAliyunPipelineConfig",
        "metadata": {"name": name},
        "spec": spec,
    }
    rendered = to_yaml(cr) + "\n"
    out = {
        "tool": "render_crd",
        "session_id": os.environ.get("SKILL_SESSION_ID", ""),
        "status": "ok",
        "kind": cr["kind"],
        "name": name,
        "project": project.get("name"),
        "machine_groups": [g.get("name") for g in machine_groups],
        "cr": cr,
        "rendered": rendered,
        "apply_hint": "kubectl apply --dry-run=server -f <cr.yaml>  # after approval: kubectl apply -f <cr.yaml>",
    }
    sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
