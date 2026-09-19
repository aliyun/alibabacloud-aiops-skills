#!/usr/bin/env python3
"""Render the Agent trace observation report (read-only, zero cloud calls).

The artifact is a self-contained HTML report produced by injecting ONE
TRACE_DATA object into the page template shipped with the skill
(references/report-template.html). The template is fully offline and
data-driven: every section (Trace Info / Trace Analysis / Performance / LLM Calls /
TOOL Calls / Execution Trace Tree / Gantt Timeline / Node Details) renders client-side from
window.TRACE_DATA = {meta, summary, spans}; missing data shows as "No data available"
rather than being invented.

Pipeline: facts (trace_chain.py output as --facts chain=...) -> TRACE_DATA
mapping -> structural redaction -> script-safe JSON encoding -> template
injection -> self-containment guard -> artifact.

Optional annotations (--spec) carry the analyzing agent's qualitative notes,
keyed by spanId: {schema_version, title?, notes?{spanId: text}}. Numbers in
the report are ALWAYS derived from the chain facts — the spec carries text
only, and money is refused outright (neither source has price/cost/billing
data; declare it 缺失, never quantify it).

Security discipline (the report is a distributable artifact):
- every free-text string entering TRACE_DATA passes redact() (structural
  secret patterns) before encoding;
- the TRACE_DATA literal is JSON-encoded with <, >, & escaped to \\uXXXX so
  no string can break out of the template's <script> block;
- the final artifact is scanned: external asset references must be 0 and the
  script block count exactly 1 (the template's own renderer) — a polluted
  template is refused, not shipped.

Output contract:
  --out PATH   HTML artifact -> file,   render summary -> stdout (--format)
  --out -      HTML artifact -> stdout, render summary -> stderr

Usage:
    python3 report_render.py --facts chain=chain.json [--spec notes.json]
                             [--template PATH] [--out report.html]
"""

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import obs_core as c  # noqa: E402

REPORT_SCHEMA_VERSION = "obs-trace-report-v1"
CHECK_RULE_COUNT = 4
DATA_MARKER = "window.TRACE_DATA"
DEFAULT_TEMPLATE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "references", "report-template.html")

# span op -> template node kind (react|llm|tool|skill|agent)
KIND_BY_OP = {"enter": "agent", "invoke_agent": "agent", "react": "react",
              "chat": "llm", "execute_tool": "tool"}
ROOT_MARKERS = ("", "0000000000000001")

# Structural redaction. Boundary: this is regex shape-matching, NOT semantic
# PII detection — what the agent chooses to quote stays the agent's call.
REDACT_PATTERNS = [
    ("private_key_block", re.compile(
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----(?:.*?-----END [A-Z ]*PRIVATE KEY-----"
        r"|[^\n]*)", re.S)),
    ("bearer_token", re.compile(r"(?i)\b(?:bearer|token)\s+[A-Za-z0-9\-_.]{16,}")),
    ("aliyun_access_key", re.compile(r"\bLTAI[A-Za-z0-9]{12,24}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("secret_assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?key)\b"
        r"\s*[=:]\s*\S{6,}")),
]

# Decision: consumption is token-only. No price data exists in either source,
# so any money-bearing text in the agent-authored layer is refused rather than
# silently invented.
MONEY_PATTERN = re.compile(
    r"(?i)\b(price|pricing|cost|fee|billing|currency)\b|金额|费用|价格|账单|成本")

_redact_hits = {}

def redact(text):
    """Structural secret redaction; records hits for the render summary."""
    if not isinstance(text, str) or not text:
        return text
    for name, rx in REDACT_PATTERNS:
        text, n = rx.subn(f"[redacted:{name}]", text)
        if n:
            _redact_hits[name] = _redact_hits.get(name, 0) + n
    return text

def redact_tree(obj):
    """Apply redact() to every string in a nested structure."""
    if isinstance(obj, str):
        return redact(obj)
    if isinstance(obj, dict):
        return {k: redact_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_tree(v) for v in obj]
    return obj

# ---------------- facts -> TRACE_DATA mapping ----------------

def chain_root(chain):
    """The loongsuit chain section the report renders. both-mode facts descend
    into the loongsuit side; ebpf-only facts cannot drive the template."""
    if chain.get("mode") == "both":
        ls = chain.get("loongsuit")
        if not isinstance(ls, dict) or ls.get("present") is False:
            raise c.ObsError(
                "both-mode chain facts carry no loongsuit section — the report "
                "template renders a loongsuit span tree, and the ebpf side alone "
                "has no GenAI spans to render")
        return ls
    if chain.get("mode") == "ebpf":
        raise c.ObsError(
            "ebpf-only chain facts cannot drive the report template: it renders "
            "a GenAI span tree (enter/react/chat/execute_tool), which only the "
            "loongsuit source provides. Bind --workspace and rebuild the chain")
    return chain

def _fmt_ms(ns):
    """'YYYY-MM-DD HH:MM:SS.mmm' from nanoseconds (template meta format)."""
    if not ns:
        return None
    secs, ms = divmod(int(ns), 1000)
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(secs)) + f".{ms:03d}"

def _round_of(step, by_id):
    """Nearest react ancestor's round (the template labels every node of a
    react round with it)."""
    cur = step
    seen = set()
    while cur is not None and cur["spanId"] not in seen:
        seen.add(cur["spanId"])
        if cur.get("op") == "react" and cur.get("round"):
            return cur["round"]
        pid = cur.get("parentSpanId")
        cur = by_id.get(pid) if pid else None
    return None

def _span_name(s):
    op = s.get("op")
    if op == "chat":
        return f"LLM · {s.get('model') or 'unknown'}"
    if op == "execute_tool":
        return f"execute_tool · {s.get('tool') or s.get('spanName') or 'unknown'}"
    if op == "react":
        return f"react · round {s['round']}" if s.get("round") else "react"
    return s.get("spanName") or op or "unknown"

def build_trace_data(chain, notes_map):
    """Map trace_chain loongsuit facts + agent notes into window.TRACE_DATA."""
    steps = chain["steps"]
    t0 = min(s["start_ns"] for s in steps)
    ids = {s["spanId"] for s in steps}
    by_id = {s["spanId"]: s for s in steps}

    spans = []
    notes_applied = 0
    for s in steps:
        pid = s.get("parentSpanId") or ""
        op = s.get("op")
        span = {
            "id": s["spanId"],
            "parentId": pid if (pid and pid not in ROOT_MARKERS and pid in ids) else None,
            "kind": KIND_BY_OP.get(op, "agent"),
            "name": _span_name(s),
            "startMs": round((s["start_ns"] - t0) / 1e6),
            "durationMs": s.get("duration_ms") or 0,
            "round": s.get("round") if op == "react" else _round_of(s, by_id),
            "status": "error" if s.get("error") else "ok",
        }
        if s.get("model"):
            span["model"] = s["model"]
        for src, dst in (("tokens", "totalTokens"),
                         ("input_tokens", "promptTokens"),
                         ("output_tokens", "completionTokens"),
                         ("cache_read_tokens", "cachedTokens"),
                         ("ttft_ms", "ttftMs")):
            if s.get(src) is not None:
                span[dst] = s[src]
        if s.get("tool"):
            span["tool"] = s["tool"]
        if s.get("input_text"):
            span["input"] = s["input_text"]
        if s.get("output_text"):
            span["output"] = s["output_text"]
        if s.get("input_chars"):
            span["inputChars"] = s["input_chars"]
        if s.get("output_chars"):
            span["outputChars"] = s["output_chars"]
        note = notes_map.get(s["spanId"])
        if note:
            notes_applied += 1
        elif s.get("error"):
            note = s.get("statusMessage")  # factual fallback for failed spans
        if note:
            span["note"] = note
        spans.append(span)

    enter = next((s for s in steps if s.get("op") == "enter"), None)
    invoke = next((s for s in steps if s.get("op") == "invoke_agent"), None)
    first_chat = next((s for s in steps if s.get("op") == "chat"), None)
    entry = enter or invoke
    failed = (chain.get("patterns") or {}).get("failed_spans") or []
    binding = chain.get("binding") or {}
    env = binding.get("region")
    ws_or_proj = binding.get("workspace") or binding.get("project")
    if env and ws_or_proj:
        env = f"{env} · {ws_or_proj}"
    hi = max(s["start_ns"] + int((s.get("duration_ms") or 0) * 1e6) for s in steps)

    meta = {
        "traceId": chain.get("trace_id"),
        "sessionId": (entry or {}).get("session_id")
                     or next((s.get("session_id") for s in steps if s.get("session_id")), None),
        "agent": (entry or {}).get("agent")
                 or next((s.get("agent") for s in steps if s.get("agent")), None)
                 or (chain.get("services") or [None])[0],
        "model": (first_chat or {}).get("model"),
        "query": (entry or {}).get("input_text"),
        "startTime": _fmt_ms(t0),
        "endTime": _fmt_ms(hi),
        "status": "error" if failed else "ok",
        "env": env,
        "user": (entry or {}).get("user_id"),
    }
    # summary stays {} — every aggregate is derived from spans by the template,
    # never typed in
    return {"meta": meta, "summary": {}, "spans": spans}, notes_applied

# ---------------- report_check (spec/structural guards) ----------------

def check_report(chain, spec, notes_map, args):
    errs = []
    steps = chain.get("steps")
    if not isinstance(steps, list) or not steps:
        errs.append("R1: chain facts carry no steps array — pass the output of "
                    "trace_chain.py as --facts chain=...")
        return errs
    if spec.get("schema_version") not in (None, REPORT_SCHEMA_VERSION):
        errs.append(f"R2: schema_version must be {REPORT_SCHEMA_VERSION!r}")
    span_ids = {s.get("spanId") for s in steps}
    for sid in sorted(notes_map):
        if sid not in span_ids:
            errs.append(f"R2: spec.notes key '{sid}' is not a span in the chain facts")
    title = spec.get("title")
    if title is not None and len(str(title)) > args.text_limit:
        errs.append(f"R3: title exceeds --text-limit ({args.text_limit})")
    for sid, text in sorted(notes_map.items()):
        if len(str(text)) > args.text_limit:
            errs.append(f"R3: note for span '{sid}' exceeds --text-limit "
                        f"({args.text_limit}); keep report notes short")
    blob = json.dumps(spec, ensure_ascii=False)
    if MONEY_PATTERN.search(blob):
        errs.append("R4: the spec implies a money amount — neither source carries "
                    "price/cost/billing data; report money as 缺失 (absent), never "
                    "quantify it")
    return errs

# ---------------- template injection ----------------

def js_data_literal(obj):
    """JSON-encode for embedding inside the template's <script> block: <, >, &
    and the JS line separators are escaped so no string can break out."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return (s.replace("<", "\\u003c").replace(">", "\\u003e")
             .replace("&", "\\u0026")
             .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))

def load_template(path):
    try:
        with open(path, encoding="utf-8") as fh:
            tpl = fh.read()
    except OSError as ex:
        raise c.ObsError(f"cannot read the report template '{path}': {ex}")
    if DATA_MARKER not in tpl or "<title>" not in tpl:
        raise c.ObsError(
            f"template '{path}' is not a valid report template: it must contain "
            f"the {DATA_MARKER} assignment and a <title> element")
    return tpl

def inject(tpl, literal, title):
    """Replace the sample TRACE_DATA object and the title."""
    # anchor on the ASSIGNMENT, not the bare name: the template header comment
    # also mentions window.TRACE_DATA
    m = re.search(r"window\.TRACE_DATA\s*=", tpl)
    if not m:
        raise c.ObsError("template contract broken: no window.TRACE_DATA assignment")
    start = m.start()
    try:
        end = tpl.index("\n};", start) + len("\n};")
    except ValueError:
        raise c.ObsError("template contract broken: the window.TRACE_DATA object "
                         "literal does not end with '\\n};'")
    out = tpl[:start] + DATA_MARKER + " = " + literal + ";" + tpl[end:]
    mt = re.search(r"<title>.*?</title>", out, re.S)
    if mt:
        out = (out[:mt.start()]
               + f"<title>{html.escape(str(title), quote=True)}</title>"
               + out[mt.end():])
    return out

def self_containment_scan(html_text):
    """Measure, don't assert: external asset references and script blocks in
    the final artifact."""
    external = re.findall(r"(?:src|href)\s*=\s*[\"']\s*(?:https?:)?//",
                          html_text, re.I)
    scripts = len(re.findall(r"<script\b", html_text, re.I))
    return {"external_assets": len(external), "script_blocks": scripts,
            "inline_js": scripts}

# ---------------- entry point ----------------

def _load_facts(pairs):
    pool = {}
    for item in pairs or []:
        if "=" not in item:
            raise c.ObsError(f"--facts expects NAME=PATH, got {item!r}")
        name, path = item.split("=", 1)
        name = name.strip()
        if not name or not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise c.ObsError(f"--facts name must be an identifier, got {name!r}")
        if not os.path.isfile(path):
            raise c.ObsError(f"--facts file not found: {path}")
        with open(path, encoding="utf-8") as fh:
            try:
                pool[name] = json.load(fh)
            except json.JSONDecodeError as ex:
                raise c.ObsError(f"--facts file is not valid JSON: {path} ({ex})")
    return pool

def render_summary(trace_id, title, args, html_text, pool, notes_applied, scan):
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "trace_id": trace_id,
        "title": title,
        "out": args.out,
        "bytes": len(html_text.encode("utf-8")),
        "sha256": hashlib.sha256(html_text.encode("utf-8")).hexdigest(),
        "facts": {"pool": sorted(pool)},
        "redaction": {"applied": bool(_redact_hits),
                      "hits": [{"class": k, "count": v}
                               for k, v in sorted(_redact_hits.items())],
                      "boundary": "structural regex only, not semantic PII detection"},
        "notes_applied": notes_applied,
        "self_contained": scan,
        "template": args.template or DEFAULT_TEMPLATE,
        "self_check": {"rules_evaluated": CHECK_RULE_COUNT, "errors": 0},
    }

def main():
    p = argparse.ArgumentParser(
        description="Render the Agent trace observation report from trace_chain "
                    "facts (template-based, self-contained HTML, zero cloud calls)")
    p.add_argument("--facts", action="append", metavar="NAME=PATH", required=True,
                   help="saved script JSON output (NAME=PATH); chain=trace_chain.py "
                        "output is required")
    p.add_argument("--spec",
                   help="optional annotations JSON: {schema_version, title?, "
                        "notes?{spanId: text}} — text only, never numbers")
    p.add_argument("--template", default=None,
                   help=f"page template (default {DEFAULT_TEMPLATE})")
    p.add_argument("--text-limit", dest="text_limit", type=int, default=4000,
                   help="max chars for spec text fields (default 4000)")
    p.add_argument("--out", required=True,
                   help="output HTML path ('-' writes stdout)")
    p.add_argument("--format", choices=["json", "yaml"], default="json",
                   help="render summary format (default json)")
    args = p.parse_args()

    _redact_hits.clear()
    pool = _load_facts(args.facts)
    if "chain" not in pool:
        raise c.ObsError("report needs the chain facts: --facts chain=<trace_chain.py "
                         "output>")
    chain = chain_root(pool["chain"])

    spec = {}
    if args.spec:
        if not os.path.isfile(args.spec):
            raise c.ObsError(f"spec file not found: {args.spec}")
        with open(args.spec, encoding="utf-8") as fh:
            try:
                spec = json.load(fh)
            except json.JSONDecodeError as ex:
                raise c.ObsError(f"spec is not valid JSON: {args.spec} ({ex})")
        if not isinstance(spec, dict):
            raise c.ObsError("spec must be a JSON object")
    notes_map = spec.get("notes") or {}
    if not isinstance(notes_map, dict):
        raise c.ObsError("spec.notes must be an object keyed by spanId")

    errs = check_report(chain, spec, notes_map, args)
    if errs:
        raise c.ObsError("report self-check failed:\n" + "\n".join(f"- {e}" for e in errs))

    trace_data, notes_applied = build_trace_data(chain, notes_map)
    trace_data = redact_tree(trace_data)
    trace_id = (trace_data["meta"] or {}).get("traceId")
    # the title is agent-authored free text and lands in the artifact twice
    # (the <title> element and meta.title), so it passes redact() as well
    title = redact(spec.get("title") or f"Agent链路观测报告 · {trace_id}")
    trace_data["meta"]["title"] = title

    tpl = load_template(args.template or DEFAULT_TEMPLATE)
    html_text = inject(tpl, js_data_literal(trace_data), title)

    scan = self_containment_scan(html_text)
    if scan["external_assets"] > 0 or scan["script_blocks"] != 1:
        raise c.ObsError(
            f"refused: the artifact is not self-contained "
            f"(external_assets={scan['external_assets']}, "
            f"script_blocks={scan['script_blocks']}); the template must be fully "
            "offline with exactly one script block — check the template file")

    summary = render_summary(trace_id, title, args, html_text, pool,
                             notes_applied, scan)
    if args.out == "-":
        sys.stdout.write(html_text)
        print(json.dumps(summary, ensure_ascii=False, indent=2), file=sys.stderr)
    else:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(html_text)
        print(f"report written to {args.out}", file=sys.stderr)
        c.emit(summary, args.format)

if __name__ == "__main__":
    c.main_wrapper(main)
