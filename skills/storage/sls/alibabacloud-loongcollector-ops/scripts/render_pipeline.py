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
    "scenario": "host|docker_stdio|k8s_stdio|docker_file|k8s_file|host_agentsight|agentloop",
    "input": { ... }        or "file_paths": ["/var/log/app/*.log"],
    "probe": { ... },                          # optional (host_agentsight form)
    "desensitize": false,                      # optional (host_agentsight mask)
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
import re
import sys

SCENARIO_INPUT = {
    "host": "input_file",
    "docker_file": "input_file",
    "k8s_file": "input_file",
    "docker_stdio": "input_container_stdio",
    "k8s_stdio": "input_container_stdio",
    "host_agentsight": "input_agentsight",
    "agentloop": "input_agentsight",
}
AGENTSIGHT_SCENARIOS = {"host_agentsight", "agentloop"}
AGENTSIGHT_CONFIG_NAME = "runtime-ebpf-agentsight-config"
AGENTSIGHT_LOGSTORE = "ebpf-event"
# Frontend mask mode is the literal "buildin" (not "builtin"). Do not "fix" it.
AGENTSIGHT_MASK_RULES = (
    '[{"mode":"buildin","types":["IP_ADDRESS","EMAIL","LANDLINE_PHONE",'
    '"CREDIT_CARD","PHONE","IDCARD"],"maskType":"placeholder"}]'
)
AGENTSIGHT_MASK_SCRIPT = (
    '* | extend "gen_ai.input.messages" = mask("gen_ai.input.messages",\'%s\')'
    ' | extend "gen_ai.output.messages" = mask("gen_ai.output.messages",\'%s\')'
    % (AGENTSIGHT_MASK_RULES, AGENTSIGHT_MASK_RULES)
)
HTTP_DOMAIN_RE = re.compile(r":\d+$")


def die(msg, code=2):
    sys.stderr.write("[render_pipeline] %s\n" % msg)
    sys.exit(code)


def is_http_domain(value):
    text = str(value).strip()
    if not text:
        return False
    if text.startswith(":") or text[0].isdigit() or HTTP_DOMAIN_RE.search(text):
        return True
    return False


def normalize_whitelist(items):
    out = []
    skipped = 0
    if not isinstance(items, list):
        die("CmdlineWhitelist must be an array")
    for item in items:
        if not isinstance(item, dict):
            skipped += 1
            continue
        agent_type = item.get("AgentType")
        args = item.get("Args")
        if isinstance(args, str):
            args = [args]
        if not agent_type or not isinstance(args, list) or not args:
            skipped += 1
            continue
        if not all(isinstance(arg, str) and arg for arg in args):
            skipped += 1
            continue
        out.append({"AgentType": agent_type, "Args": args})
    if items and not out:
        die("CmdlineWhitelist items missing AgentType or Args; empty list is illegal")
    if skipped:
        sys.stderr.write(
            "[render_pipeline] dropped %d incomplete CmdlineWhitelist row(s)\n" % skipped
        )
    return out


def normalize_blacklist(items):
    if not isinstance(items, list):
        die("CmdlineBlacklist must be an array")
    if items and all(isinstance(item, str) for item in items):
        items = [items]
    out = []
    for item in items:
        if not isinstance(item, list) or not item:
            die("CmdlineBlacklist entries must be non-empty string arrays")
        if not all(isinstance(arg, str) and arg for arg in item):
            die("CmdlineBlacklist entries must be non-empty string arrays")
        out.append(list(item))
    return out


def split_domains(domains):
    https, http = [], []
    if not isinstance(domains, list):
        die("domains must be an array of strings")
    for item in domains:
        if not isinstance(item, str) or not item.strip():
            continue
        target = item.strip()
        if is_http_domain(target):
            http.append(target)
        else:
            https.append(target)
    return https, http


def build_probe_config(task):
    raw_input = task.get("input")
    if isinstance(raw_input, dict) and isinstance(raw_input.get("ProbeConfig"), dict):
        source = dict(raw_input["ProbeConfig"])
    elif isinstance(task.get("ProbeConfig"), dict):
        source = dict(task["ProbeConfig"])
    elif isinstance(task.get("probe"), dict):
        source = dict(task["probe"])
    else:
        source = {}

    probe = {}
    whitelist = source.get("CmdlineWhitelist") or source.get("cmdline_whitelist")
    if whitelist:
        probe["CmdlineWhitelist"] = normalize_whitelist(whitelist)
    blacklist = source.get("CmdlineBlacklist") or source.get("cmdline_blacklist")
    if blacklist:
        probe["CmdlineBlacklist"] = normalize_blacklist(blacklist)

    https = source.get("Https") or source.get("https")
    http = source.get("Http") or source.get("http")
    domains = source.get("domains") or source.get("domain_whitelist")
    if domains:
        split_https, split_http = split_domains(domains)
        https = list(https or []) + split_https
        http = list(http or []) + split_http
    if https:
        if not isinstance(https, list) or not all(isinstance(item, str) and item for item in https):
            die("Https must be a non-empty string array")
        probe["Https"] = https
    if http:
        if not isinstance(http, list) or not all(isinstance(item, str) and item for item in http):
            die("Http must be a non-empty string array")
        probe["Http"] = http

    verbose = source.get("Verbose") if "Verbose" in source else source.get("verbose")
    if verbose == 1 or verbose is True:
        probe["Verbose"] = 1
    log_path = source.get("LogPath") if "LogPath" in source else source.get("log_path")
    if isinstance(log_path, str) and log_path:
        probe["LogPath"] = log_path
    if "EventStreamFormat" in source:
        probe["EventStreamFormat"] = bool(source["EventStreamFormat"])
    if "MessageDeltaOnly" in source:
        probe["MessageDeltaOnly"] = bool(source["MessageDeltaOnly"])
    raw_fb = source.get("RawHttpsFallback")
    if raw_fb is None:
        raw_fb = source.get("raw_https_fallback")
    if raw_fb is True:
        probe["RawHttpsFallback"] = True
    return probe


def agentsight_mask_processor():
    return {
        "Type": "processor_spl",
        "TimeoutMilliSeconds": 1000,
        "Script": AGENTSIGHT_MASK_SCRIPT,
    }


def build_input(task):
    if isinstance(task.get("input"), dict) and task["input"].get("Type"):
        inp = dict(task["input"])
        if inp.get("Type") == "input_agentsight" and "ProbeConfig" not in inp:
            inp["ProbeConfig"] = build_probe_config(task)
        return inp
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
    elif itype == "input_agentsight":
        inp["ProbeConfig"] = build_probe_config(task)
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

    scenario = task.get("scenario", "host")
    if scenario in AGENTSIGHT_SCENARIOS:
        task.setdefault("config_name", AGENTSIGHT_CONFIG_NAME)
        task.setdefault("logstore", AGENTSIGHT_LOGSTORE)

    if not task.get("config_name"):
        die("config_name is required")

    config = {
        "configName": task["config_name"],
        "inputs": [build_input(task)],
        "flushers": [build_flusher(task)],
    }
    if task.get("log_sample"):
        config["logSample"] = task["log_sample"]
    if "global" in task:
        if not isinstance(task["global"], dict):
            die("global must be an object")
        config["global"] = task["global"]
    elif scenario in AGENTSIGHT_SCENARIOS:
        config["global"] = {}
    else:
        config["global"] = {"TopicType": "machine_group_topic"}
    procs = task.get("processors")
    probe = task.get("probe") if isinstance(task.get("probe"), dict) else {}
    desensitize = task.get("desensitize")
    if desensitize is None:
        desensitize = probe.get("desensitize")
    if procs is None and desensitize:
        procs = [agentsight_mask_processor()]
    if isinstance(procs, list) and procs:
        config["processors"] = procs

    inputs_json = json.dumps(config["inputs"], ensure_ascii=False)
    flushers_json = json.dumps(config["flushers"], ensure_ascii=False)
    extra = " --global '%s'" % json.dumps(config.get("global", {}), ensure_ascii=False)
    if config.get("processors"):
        extra += " --processors '%s'" % json.dumps(config["processors"], ensure_ascii=False)
    cli_hint = (
        "aliyun sls create-logtail-pipeline-config --project <p> "
        "--config-name %s --inputs '%s' --flushers '%s'%s "
        "--region <r> --user-agent AlibabaCloud-Agent-Skills/"
        "alibabacloud-loongcollector-ops/%s  # run --cli-dry-run first"
        % (config["configName"], inputs_json, flushers_json, extra,
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
