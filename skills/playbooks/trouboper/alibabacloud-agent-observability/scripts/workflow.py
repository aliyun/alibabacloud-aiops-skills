#!/usr/bin/env python3
"""Deterministic end-to-end workflow for alibabacloud-agent-observability.

The canonical entry point for a complete user-facing analysis. Orchestrates
the component scripts in the mandatory order and persists every intermediate
JSON plus a final manifest, so downstream verification can prove that each
step actually ran, succeeded, and fed the next one — instead of trusting
that the shell history "looks about right".

Two subcommands cover the two supported user intents:

  search   preflight -> span_search -> (select hit) -> trace_chain ->
                    decision_evidence -> report_render
  trace    preflight -> trace_chain -> decision_evidence -> report_render

Child scripts are invoked via subprocess.run([...], shell=False) with the
current interpreter (sys.executable), so shell metacharacters in --match /
--trace-id / paths are passed through safely. Each child's JSON stdout is
captured, validated, and written under <run-dir>/facts/; the final HTML
artifact lands under <run-dir>/reports/html/. A manifest at
<run-dir>/workflow.json records every step's exit status, timing, output
path, and SHA-256, plus the selection policy and chosen trace/span ids.

Fail-fast: a non-zero child exit, invalid JSON, empty search hits, invalid
selection, or a missing/invalid report abort the workflow and are recorded
in the manifest. Credentials, environment dumps, and raw command output
are never written to the manifest.

The component scripts remain available for direct use as diagnostic /
building-block commands; workflow.py is the public workflow for complete
analyses (SKILL.md section 8).

Usage:
    python3 workflow.py search --region R --workspace W --match TEXT
                               (--select first | --select unique)
                               [--limit N] [--from TS --to TS]
                               [--run-dir PATH]

    python3 workflow.py trace --region R --workspace W --trace-id TID
                              [--from TS --to TS] [--run-dir PATH]
"""

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obs_core as c  # noqa: E402

WORKFLOW_SCHEMA = "agent-obs-workflow-v1"
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPTS_DIR)

# Structural secret patterns that must never appear in the manifest.
# Applied to every string value before write; matches are replaced with
# "<redacted>". This is regex-shape matching (same discipline as
# report_render.redact), not semantic PII detection.
_MANIFEST_REDACT = [
    re.compile(r"\bLTAI[A-Za-z0-9]{12,24}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[Z0-9]{16}\b"),
    re.compile(r"(?i)\b(?:bearer|token)\s+[A-Za-z0-9\-_.]{16,}"),
]

CHILD_SCRIPTS = {
    "preflight": "preflight.py",
    "span_search": "span_search.py",
    "trace_chain": "trace_chain.py",
    "decision_evidence": "decision_evidence.py",
    "report_render": "report_render.py",
}


# ---------------- manifest helpers ----------------

def _sha256_path(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _new_run_id():
    return secrets.token_hex(16)


def _atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(_redact(obj), fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _redact(obj):
    """Walk obj and replace any string matching _MANIFEST_REDACT with
    '<redacted>'. Applied to the manifest before write so a child payload
    that accidentally echoes a credential-shaped token never lands on disk
    via the workflow's own artifact."""
    if isinstance(obj, str):
        s = obj
        for pat in _MANIFEST_REDACT:
            s = pat.sub("<redacted>", s)
        return s
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items()}
    return obj


def mark_workflow_complete(run_dir, report_path):
    """Generate completion marker file when workflow succeeds."""
    marker = {
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "report_path": report_path,
        "status": "success",
        "workflow_version": "1.0",
        "run_dir": run_dir
    }
    marker_path = os.path.join(run_dir, "workflow-complete.json")
    with open(marker_path, "w", encoding="utf-8") as f:
        json.dump(marker, f, ensure_ascii=False, indent=2)
    return marker_path


def mark_workflow_failed(run_dir, error_message, failed_stage=None):
    """Generate failure marker file when workflow fails."""
    marker = {
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
        "status": "failed",
        "error": error_message,
        "failed_stage": failed_stage,
        "workflow_version": "1.0",
        "run_dir": run_dir
    }
    marker_path = os.path.join(run_dir, "workflow-complete.json")
    with open(marker_path, "w", encoding="utf-8") as f:
        json.dump(marker, f, ensure_ascii=False, indent=2)
    return marker_path


def _resolve_run_dir(explicit, subcommand):
    if explicit:
        os.makedirs(explicit, exist_ok=True)
        return explicit
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    base = os.path.join(REPO_ROOT, "reports", "workflows",
                        f"{subcommand}-{ts}-{_new_run_id()[:8]}")
    os.makedirs(base, exist_ok=True)
    return base


# ---------------- child invocation ----------------

def _run_child(name, argv, env_extra=None, timeout=None):
    """Run a child script with shell=False. Return (stdout_text, stderr_text,
    exit_code, duration_s). Never raises on child failure — the caller
    decides."""
    script = os.path.join(SCRIPTS_DIR, CHILD_SCRIPTS[name])
    cmd = [sys.executable, script, *argv]
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    start = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              shell=False, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, None, -1, time.time() - start
    except FileNotFoundError:
        return None, None, -2, time.time() - start
    return proc.stdout, proc.stderr, proc.returncode, time.time() - start


def _parse_child_json(stdout):
    """Parse child stdout as JSON; raise ObsError on any failure."""
    if not stdout:
        raise c.ObsError("child produced no stdout (expected JSON)")
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as ex:
        raise c.ObsError(f"child stdout is not valid JSON: {ex}\n"
                         f"--- first 400 chars ---\n{stdout[:400]}")


# ---------------- step runner ----------------

class _Step:
    def __init__(self, name):
        self.name = name
        self.start = None
        self.end = None
        self.exit_code = None
        self.output_path = None
        self.output_hash = None
        self.output_size = None
        self.error = None

    def as_dict(self):
        return {k: getattr(self, k) for k in
                ("name", "exit_code", "start", "end",
                 "output_path", "output_hash", "output_size", "error")}


def _record_step(step, argv, facts_dir, env_extra=None, timeout=None,
                 write_json=True):
    step.start = time.time()
    stdout, stderr, rc, _ = _run_child(step.name, argv, env_extra=env_extra,
                                       timeout=timeout)
    step.end = time.time()
    step.exit_code = rc
    if rc != 0:
        snippet = (stdout or "")[:400]
        err_snippet = (stderr or "")[:400]
        parts = [f"child exited with code {rc}"]
        if snippet:
            parts.append(f"stdout head: {snippet}")
        if err_snippet:
            parts.append(f"stderr head: {err_snippet}")
        step.error = "; ".join(parts)
        return None
    if not write_json:
        return stdout
    try:
        data = _parse_child_json(stdout)
    except c.ObsError as ex:
        step.error = str(ex)
        step.exit_code = -3
        return None
    path = os.path.join(facts_dir, f"{step.name}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    step.output_path = path
    step.output_size = os.path.getsize(path)
    step.output_hash = _sha256_path(path)
    return data


# ---------------- selection ----------------

def _select_hit(search_result, policy):
    hits = search_result.get("hits") or []
    if not hits:
        raise c.ObsError("span_search returned no hits; nothing to analyse")
    if policy == "first":
        return hits[0], 0
    if policy == "unique":
        trace_ids = {h.get("trace_id") for h in hits if h.get("trace_id")}
        if len(trace_ids) != 1:
            raise c.ObsError(
                f"--select unique requires all hits to resolve to one trace_id; "
                f"got {len(trace_ids)} distinct traces across {len(hits)} hits. "
                "Re-run with --select first, narrow the window, or ask the user "
                "to pick a trace_id from span_search output")
        return hits[0], 0
    raise c.ObsError(f"unknown --select policy: {policy}")


# ---------------- common arg plumbing ----------------

def _common_argv(args):
    """Build the argv tail shared by every child that takes the data-source
    binding + window. Each flag is added only when the user actually supplied
    a value, so children fall back to their own defaults / env vars."""
    argv = []
    if args.region:
        argv += ["--region", args.region]
    if args.project:
        argv += ["--project", args.project]
    if args.workspace:
        argv += ["--workspace", args.workspace]
    if getattr(args, "logstore", None):
        argv += ["--logstore", args.logstore]
    if getattr(args, "service_name", None):
        argv += ["--service-name", args.service_name]
    if getattr(args, "mode", None):
        argv += ["--mode", args.mode]
    if getattr(args, "from_ts", None) is not None:
        argv += ["--from", str(args.from_ts)]
    if getattr(args, "to_ts", None) is not None:
        argv += ["--to", str(args.to_ts)]
    if getattr(args, "hours", None) is not None and \
            getattr(args, "from_ts", None) is None:
        argv += ["--hours", str(args.hours)]
    if getattr(args, "no_cache", False):
        argv += ["--no-cache"]
    return argv


def _preflight_argv(args):
    """Build the argv tail for preflight.py, which only accepts binding args
    (--region / --project / --workspace / --logstore) and --no-cache.
    preflight does NOT accept --from / --to / --hours / --service-name / --mode."""
    argv = []
    if args.region:
        argv += ["--region", args.region]
    if args.project:
        argv += ["--project", args.project]
    if args.workspace:
        argv += ["--workspace", args.workspace]
    if getattr(args, "logstore", None):
        argv += ["--logstore", args.logstore]
    if getattr(args, "no_cache", False):
        argv += ["--no-cache"]
    return argv


def _add_common(p):
    p.add_argument("--region", required=True)
    p.add_argument("--project")
    p.add_argument("--workspace")
    p.add_argument("--logstore")
    p.add_argument("--service-name", dest="service_name")
    p.add_argument("--mode")
    p.add_argument("--hours", type=float)
    p.add_argument("--from", dest="from_ts", type=int)
    p.add_argument("--to", dest="to_ts", type=int)
    p.add_argument("--no-cache", dest="no_cache", action="store_true")
    p.add_argument("--run-dir", dest="run_dir",
                   help="directory to persist facts/manifest/report under; "
                        "default reports/workflows/<sub>-<ts>-<id>")
    p.add_argument("--format", choices=["json", "yaml"], default="json")


# ---------------- search subcommand ----------------

SEARCH_STEPS_ORDER = ("preflight", "span_search", "trace_chain",
                      "decision_evidence", "report_render")


def _cmd_search(args):
    if not args.workspace:
        raise c.ObsError(
            "workflow search requires the loongsuit source: pass --workspace "
            "(span_search reads message payloads, which ebpf-event does not carry)")
    if args.select not in ("first", "unique"):
        raise c.ObsError("--select must be 'first' or 'unique'")

    run_dir = _resolve_run_dir(args.run_dir, "search")
    facts_dir = os.path.join(run_dir, "facts")
    reports_dir = os.path.join(run_dir, "reports", "html")
    os.makedirs(facts_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    manifest = {
        "schema": WORKFLOW_SCHEMA,
        "subcommand": "search",
        "run_id": _new_run_id(),
        "run_dir": run_dir,
        "started_at": time.time(),
        "args": _safe_args(args),
        "steps": [],
        "selection": {"policy": args.select, "hit_index": None,
                      "trace_id": None, "span_id": None},
        "report": None,
        "status": "running",
    }

    common = _common_argv(args)
    steps_run = {}

    # 1. preflight --strict
    pf = _Step("preflight")
    pf_data = _record_step(pf, ["--strict", *_preflight_argv(args), "--format", "json"],
                           facts_dir)
    manifest["steps"].append(pf.as_dict())
    if pf_data is None:
        return _fail(manifest, "preflight", pf.error, run_dir)
    if pf_data.get("overall") == "fail":
        pf.error = "preflight reported overall=fail"
        manifest["steps"][-1] = pf.as_dict()
        return _fail(manifest, "preflight", pf.error, run_dir)
    steps_run["preflight"] = pf_data

    # 2. span_search
    ss = _Step("span_search")
    ss_argv = ["--match", args.match, "--limit", str(args.limit),
               "--max-traces", str(args.max_traces),
               *common, "--format", "json"]
    ss_data = _record_step(ss, ss_argv, facts_dir)
    manifest["steps"].append(ss.as_dict())
    if ss_data is None:
        return _fail(manifest, "span_search", ss.error, run_dir)
    steps_run["span_search"] = ss_data

    # 3. selection
    try:
        hit, idx = _select_hit(ss_data, args.select)
    except c.ObsError as ex:
        return _fail(manifest, "selection", str(ex), run_dir)
    manifest["selection"]["hit_index"] = idx
    manifest["selection"]["trace_id"] = hit.get("trace_id")
    manifest["selection"]["span_id"] = hit.get("span_id")
    if not manifest["selection"]["trace_id"]:
        return _fail(manifest, "selection",
                     "selected hit has no trace_id", run_dir)

    # 4. trace_chain
    tc = _Step("trace_chain")
    tc_argv = ["--trace-id", manifest["selection"]["trace_id"], *common,
               "--format", "json"]
    tc_data = _record_step(tc, tc_argv, facts_dir)
    manifest["steps"].append(tc.as_dict())
    if tc_data is None:
        return _fail(manifest, "trace_chain", tc.error, run_dir)
    steps_run["trace_chain"] = tc_data

    # 5. decision_evidence (span_id when present, else trace anchor)
    de = _Step("decision_evidence")
    de_argv = [*common, "--format", "json"]
    if manifest["selection"]["span_id"]:
        de_argv += ["--span-id", manifest["selection"]["span_id"]]
    else:
        de_argv += ["--trace-id", manifest["selection"]["trace_id"]]
    de_data = _record_step(de, de_argv, facts_dir)
    manifest["steps"].append(de.as_dict())
    if de_data is None:
        return _fail(manifest, "decision_evidence", de.error, run_dir)
    steps_run["decision_evidence"] = de_data

    # 6. report_render
    rr = _Step("report_render")
    report_name = (manifest["selection"]["trace_id"] or "report") + ".html"
    report_path = os.path.join(reports_dir, report_name)
    chain_path = manifest["steps"][2]["output_path"]
    rr_argv = ["--facts", f"chain={chain_path}",
               "--out", report_path, "--format", "json"]
    rr_stdout, _rr_stderr, rr_rc, _ = _run_child("report_render", rr_argv)
    rr.end = time.time()
    rr.exit_code = rr_rc
    if rr_rc != 0:
        rr.error = (f"report_render exited {rr_rc}; stdout head: "
                    f"{(rr_stdout or '')[:400]}")
        manifest["steps"].append(rr.as_dict())
        return _fail(manifest, "report_render", rr.error, run_dir)
    if not os.path.isfile(report_path) or os.path.getsize(report_path) == 0:
        rr.error = f"report artifact missing or empty at {report_path}"
        manifest["steps"].append(rr.as_dict())
        return _fail(manifest, "report_render", rr.error, run_dir)
    rr.output_path = report_path
    rr.output_size = os.path.getsize(report_path)
    rr.output_hash = _sha256_path(report_path)
    manifest["steps"].append(rr.as_dict())

    manifest["report"] = {
        "path": report_path,
        "sha256": rr.output_hash,
        "size": rr.output_size,
    }
    # extract self-containment from the render summary if parseable
    try:
        summary = json.loads(rr_stdout or "{}")
        manifest["report"]["self_containment"] = summary.get("self_containment")
    except (json.JSONDecodeError, AttributeError):
        manifest["report"]["self_containment"] = None

    manifest["status"] = "ok"
    manifest["finished_at"] = time.time()
    _atomic_write_json(os.path.join(run_dir, "workflow.json"), manifest)
    mark_workflow_complete(run_dir, report_path)
    c.emit(_summary(manifest), args.format)
    return 0


def _fail(manifest, stage, error, run_dir):
    manifest["status"] = "failed"
    manifest["failed_stage"] = stage
    manifest["error"] = error
    manifest["finished_at"] = time.time()
    _atomic_write_json(os.path.join(run_dir, "workflow.json"), manifest)
    mark_workflow_failed(run_dir, error, stage)
    raise c.ObsError(f"workflow failed at {stage}: {error}")


def _safe_args(args):
    """Echo effective arguments without credentials or env dumps."""
    safe = {}
    for key in ("region", "project", "workspace", "logstore", "service_name",
                "mode", "match", "limit", "select", "max_traces",
                "from_ts", "to_ts", "hours"):
        v = getattr(args, key, None)
        if v is not None:
            safe[key] = v
    if getattr(args, "no_cache", False):
        safe["no_cache"] = True
    return safe


def _summary(manifest):
    return {
        "workflow": manifest["schema"],
        "subcommand": manifest["subcommand"],
        "status": manifest["status"],
        "run_id": manifest["run_id"],
        "run_dir": manifest["run_dir"],
        "selection": manifest.get("selection"),
        "steps": [
            {"name": s["name"], "exit_code": s["exit_code"],
             "output_path": s.get("output_path")}
            for s in manifest["steps"]
        ],
        "report": manifest.get("report"),
        "error": manifest.get("error"),
    }


# ---------------- trace subcommand ----------------

TRACE_STEPS_ORDER = ("preflight", "trace_chain",
                     "decision_evidence", "report_render")


def _cmd_trace(args):
    if not args.trace_id:
        raise c.ObsError("--trace-id is required for the trace subcommand")
    run_dir = _resolve_run_dir(args.run_dir, "trace")
    facts_dir = os.path.join(run_dir, "facts")
    reports_dir = os.path.join(run_dir, "reports", "html")
    os.makedirs(facts_dir, exist_ok=True)
    os.makedirs(reports_dir, exist_ok=True)

    manifest = {
        "schema": WORKFLOW_SCHEMA,
        "subcommand": "trace",
        "run_id": _new_run_id(),
        "run_dir": run_dir,
        "started_at": time.time(),
        "args": _safe_args(args),
        "selection": {"trace_id": args.trace_id, "span_id": None},
        "steps": [],
        "report": None,
        "status": "running",
    }

    common = _common_argv(args)

    pf = _Step("preflight")
    pf_data = _record_step(pf, ["--strict", *_preflight_argv(args), "--format", "json"],
                           facts_dir)
    manifest["steps"].append(pf.as_dict())
    if pf_data is None or pf_data.get("overall") == "fail":
        return _fail(manifest, "preflight",
                     pf.error or "preflight reported overall=fail", run_dir)

    tc = _Step("trace_chain")
    tc_data = _record_step(tc, ["--trace-id", args.trace_id, *common,
                                "--format", "json"], facts_dir)
    manifest["steps"].append(tc.as_dict())
    if tc_data is None:
        return _fail(manifest, "trace_chain", tc.error, run_dir)

    root_span = next(
        (s for s in (tc_data.get("steps") or []) if s.get("depth") == 0),
        None)
    root_span_id = root_span["spanId"] if root_span else None
    if not root_span_id:
        return _fail(manifest, "decision_evidence",
                     "trace_chain output has no root span (depth=0); "
                     "cannot derive --span-id for decision_evidence", run_dir)
    manifest["selection"]["span_id"] = root_span_id

    de = _Step("decision_evidence")
    de_data = _record_step(de, ["--span-id", root_span_id,
                                "--trace-id", args.trace_id, *common,
                                "--format", "json"], facts_dir)
    manifest["steps"].append(de.as_dict())
    if de_data is None:
        return _fail(manifest, "decision_evidence", de.error, run_dir)

    rr = _Step("report_render")
    report_name = args.trace_id + ".html"
    report_path = os.path.join(reports_dir, report_name)
    chain_path = manifest["steps"][1]["output_path"]
    rr_stdout, _rr_stderr, rr_rc, _ = _run_child(
        "report_render",
        ["--facts", f"chain={chain_path}",
         "--out", report_path, "--format", "json"])
    rr.exit_code = rr_rc
    if rr_rc != 0 or not os.path.isfile(report_path) or \
            os.path.getsize(report_path) == 0:
        rr.error = (f"report_render exited {rr_rc} or produced no artifact; "
                    f"stdout head: {(rr_stdout or '')[:400]}")
        manifest["steps"].append(rr.as_dict())
        return _fail(manifest, "report_render", rr.error, run_dir)
    rr.output_path = report_path
    rr.output_size = os.path.getsize(report_path)
    rr.output_hash = _sha256_path(report_path)
    manifest["steps"].append(rr.as_dict())

    manifest["report"] = {
        "path": report_path,
        "sha256": rr.output_hash,
        "size": rr.output_size,
    }
    try:
        summary = json.loads(rr_stdout or "{}")
        manifest["report"]["self_containment"] = summary.get("self_containment")
    except (json.JSONDecodeError, AttributeError):
        manifest["report"]["self_containment"] = None

    manifest["status"] = "ok"
    manifest["finished_at"] = time.time()
    _atomic_write_json(os.path.join(run_dir, "workflow.json"), manifest)
    mark_workflow_complete(run_dir, report_path)
    c.emit(_summary(manifest), args.format)
    return 0


# ---------------- entry ----------------

def main():
    p = argparse.ArgumentParser(
        description="Deterministic end-to-end workflow for the agent "
                    "observability skill. Use this for complete user-facing "
                    "analyses; the component scripts remain available for "
                    "diagnostics.")
    sub = p.add_subparsers(dest="subcommand", required=True)

    sp_search = sub.add_parser(
        "search",
        help="preflight -> span_search -> select hit -> trace_chain -> "
             "decision_evidence -> report_render")
    _add_common(sp_search)
    sp_search.add_argument("--match", required=True,
                           help="text to locate (case-insensitive substring)")
    sp_search.add_argument("--limit", type=int, default=50,
                           help="max hits from span_search (default 50)")
    sp_search.add_argument("--max-traces", dest="max_traces", type=int,
                           default=200,
                           help="max traces enumerated by span_search "
                                "(default 200)")
    sp_search.add_argument("--select", required=True,
                           choices=["first", "unique"],
                           help="hit selection policy: 'first' = hits[0] "
                                "(only when the user asked for the first); "
                                "'unique' = continue only when all hits share "
                                "one trace_id")

    sp_trace = sub.add_parser(
        "trace",
        help="preflight -> trace_chain -> decision_evidence -> report_render "
             "for a user-provided trace id")
    _add_common(sp_trace)
    sp_trace.add_argument("--trace-id", dest="trace_id", required=True,
                          help="trace id to analyse (user-provided)")

    args = p.parse_args()
    if args.subcommand == "search":
        rc = _cmd_search(args)
    else:
        rc = _cmd_trace(args)
    sys.exit(rc or 0)


if __name__ == "__main__":
    c.main_wrapper(main)
