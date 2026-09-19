#!/usr/bin/env python3
"""Application-level observability overview over a time window (read-only).

Dual-source combined: loongsuit and ebpf are complementary views of the same
Agent trajectory. Default --mode both aggregates both sources over the same
window and emits them side by side (never cross-compared: span-level vs
runtime-fact calibers). --mode loongsuit|ebpf restricts to one source, and a
binding that supplies only one side makes both auto-narrow to it.

- loongsuit mode: aggregates GenAI spans (enter/invoke_agent/react/chat/
  execute_tool) from the CMS 2.0 workspace via UModel GetEntityStoreData,
  including cross-Agent call chains (per-span serviceName).
- ebpf mode: aggregates eBPF runtime facts from the bound SLS project's
  ebpf-event logstore (process / container / host / network / HTTP), fetched
  as raw rows and aggregated client-side because those fields are unindexed.

Usage:
    python3 trace_overview.py [--from <ts> --to <ts>] [--agent NAME] [--mode both]
                              [--max-traces 200] [--compare-hours N] [--format json]

Drift check: --compare-hours N builds the same loongsuit overview over the
preceding N-hour window and emits a `drift` section with per-metric
base/current/delta_pct. Quantitative only — whether a delta matters is a
qualitative judgment for the analyzing agent.
"""

import json
import sys
import time

import obs_core as c
import sls_event as e
import cms_trace as a

def _p95(values):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, int(0.95 * (len(values) - 1)))]

def build_both(cfg, args, f, t, mode="both"):
    """Dual-source combined: both overviews over the same window, emitted side
    by side. Counters are NOT cross-comparable (span vs runtime-fact caliber)."""
    return {
        "mode": mode,
        "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)},
        "loongsuit": build_loongsuit(cfg, args, f, t),
        "ebpf": build_ebpf(cfg, args, f, t),
        "note": ("dual-source combined overview: the loongsuit and ebpf sections "
                 "share only the time window; do not cross-compare their counters "
                 "(span-level vs runtime-fact calibers); a section reporting zero "
                 "data is a coverage finding, not an error"),
    }

def build(args):
    cfg = c.Config.resolve(args)
    mode, narrowed = e.resolve_mode(cfg, args)
    f, t = c.resolve_window(args)
    if mode == "ebpf":
        result = build_ebpf(cfg, args, f, t)
        if getattr(args, "compare_hours", None):
            result["notes"].append(
                "--compare-hours drift is loongsuit-side only; run with "
                "--mode loongsuit (or the default both) to get it")
    elif mode == "loongsuit":
        result = build_loongsuit(cfg, args, f, t)
        result["notes"] = list(result.get("notes") or [])
    else:
        result = build_both(cfg, args, f, t)
    if narrowed:
        result["mode_narrowed"] = narrowed
    result["sources"] = c.source_availability(cfg, mode)
    result["notes"] = list(result.get("notes") or []) + c.gap_note(cfg)
    return result

# ---------------- loongsuit mode (CMS 2.0 workspace trajectory) ----------------

def _extract_user_input_summary(attrs, limit=120):
    """Extract a short summary of the user's input from an entry/enter span.

    Looks at gen_ai.input.messages, finds the first user-role message, and
    returns a truncated plain-text excerpt. Returns None when no user content
    is found."""
    raw = attrs.get("gen_ai.input.messages")
    if not raw:
        return None
    try:
        msgs = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return c.truncate(raw, limit) if isinstance(raw, str) else None
    if not isinstance(msgs, list):
        return None
    for m in msgs:
        if not isinstance(m, dict):
            continue
        role = (m.get("role") or "").lower()
        if role != "user":
            continue
        content = m.get("content") or m.get("text") or ""
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict):
                    parts.append(p.get("text") or "")
                else:
                    parts.append(str(p))
            content = " ".join(parts)
        if not isinstance(content, str):
            content = str(content)
        content = content.strip()
        if content:
            return c.truncate(content, limit)
    return None


def _build_trace_candidates(rows, traces, limit=120):
    """Build a user-friendly trace candidate list from already-fetched rows.

    Each entry has trace_id, input_summary (the user's original query excerpt),
    start_ms, span_count, and has_error. The input_summary comes from the
    entry/enter span's gen_ai.input.messages user-role content, so users can
    identify traces by what was asked rather than by opaque hex IDs."""
    trace_meta = {}
    for tr in traces:
        trace_meta[tr["trace_id"]] = {
            "trace_id": tr["trace_id"],
            "start_ms": tr.get("start_ms"),
            "span_count": 0,
            "has_error": False,
            "input_summary": None,
        }
    entry_ops = {"enter", "invoke_agent"}
    entry_kinds = {"ENTRY"}
    for r in rows:
        tid = r.get("traceId")
        if tid not in trace_meta:
            continue
        trace_meta[tid]["span_count"] += 1
        if r.get("statusCode") == "2":
            trace_meta[tid]["has_error"] = True
        if trace_meta[tid]["input_summary"] is not None:
            continue
        attrs = c.parse_json_field(r, "attributes")
        op = attrs.get("gen_ai.operation.name")
        kind = attrs.get("gen_ai.span.kind")
        if op in entry_ops or kind in entry_kinds:
            summary = _extract_user_input_summary(attrs, limit)
            if summary:
                trace_meta[tid]["input_summary"] = summary
    ordered = sorted(trace_meta.values(),
                     key=lambda x: x["start_ms"] or 0)
    return ordered


def _overview_loongsuit(cfg, args, f, t):
    traces, truncated, enum_fallback = a.search_agent_traces(
        cfg, f, t, max_traces=getattr(args, "max_traces", a.DEFAULT_MAX_TRACES))
    if truncated:
        cap = getattr(args, "max_traces", a.DEFAULT_MAX_TRACES)
        print(f"note: loongsuit enumeration hit the --max-traces cap ({cap}); "
              f"aggregates cover the first {cap} enumerated traces only. Narrow the "
              "window, add --agent/--service-name filters, or raise --max-traces "
              "for full coverage.", file=sys.stderr)
    trace_ids = [tr["trace_id"] for tr in traces]
    rows = a.fetch_traces_spans(cfg, traces, f, t) if trace_ids else []

    agent = getattr(args, "agent", None)
    if agent:
        kept_traces = set()
        kept_rows = []
        for r in rows:
            attrs = c.parse_json_field(r, "attributes")
            if attrs.get("gen_ai.agent.name") == agent:
                kept_traces.add(r["traceId"])
                kept_rows.append(r)
        rows = [r for r in kept_rows if r["traceId"] in kept_traces]
        trace_ids = sorted(kept_traces)

    by_op, by_model, by_tool, by_day = {}, {}, {}, {}
    react_rounds, sessions, users, services = [], set(), set(), set()
    repeated, chat_tokens, agent_tokens, cache_tokens = {}, 0, 0, 0
    errors = 0
    steps_from_kind = 0
    # window-level token split (scenario 4: consumption analysis, token-only —
    # neither source carries a price field, so money is never computed here)
    chat_in, chat_out = 0, 0
    tok_sum = {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
               "total_tokens": 0}
    tok_spans, tok_covered = 0, 0

    for r in rows:
        attrs = c.parse_json_field(r, "attributes")
        op = attrs.get("gen_ai.operation.name")
        if attrs.get("gen_ai.span.kind") == "STEP":
            steps_from_kind += 1
        if not op:
            continue
        dur_ms = round(int(r.get("duration") or 0) / 1e6, 1)
        tokens = c.to_int(attrs.get("gen_ai.usage.total_tokens"))
        in_tok = c.to_int(attrs.get("gen_ai.usage.input_tokens"))
        out_tok = c.to_int(attrs.get("gen_ai.usage.output_tokens"))
        cache_tok = c.to_int(attrs.get("gen_ai.usage.cache_read.input_tokens"))
        error = r.get("error") or r.get("statusCode") == "2"
        errors += 1 if error else 0
        day = time.strftime("%Y-%m-%d", time.localtime(int(r.get("startTime") or 0) / 1e9))

        tok_spans += 1
        if tokens or in_tok or out_tok or cache_tok:
            tok_covered += 1
        tok_sum["input_tokens"] += in_tok
        tok_sum["output_tokens"] += out_tok
        tok_sum["cache_read_tokens"] += cache_tok
        tok_sum["total_tokens"] += tokens

        d = by_op.setdefault(op, {"op": op, "spans": 0, "errors": 0, "tokens": 0,
                                  "input_tokens": 0, "output_tokens": 0,
                                  "cache_read_tokens": 0, "_durs": []})
        d["spans"] += 1
        d["errors"] += 1 if error else 0
        d["tokens"] += tokens
        d["input_tokens"] += in_tok
        d["output_tokens"] += out_tok
        d["cache_read_tokens"] += cache_tok
        d["_durs"].append(dur_ms)

        day_d = by_day.setdefault(day, {"day": day, "spans": 0, "errors": 0, "tokens": 0})
        day_d["spans"] += 1
        day_d["errors"] += 1 if error else 0
        day_d["tokens"] += tokens

        if r.get("serviceName"):
            services.add(r["serviceName"])
        sid = attrs.get("gen_ai.session.id")
        if sid:
            sessions.add(sid)
        uid = attrs.get("gen_ai.user.id")
        if uid:
            users.add(uid)

        if op == "chat":
            model = attrs.get("gen_ai.request.model") or "?"
            m = by_model.setdefault(model, {"model": model, "calls": 0, "errors": 0,
                                            "tokens": 0, "input_tokens": 0,
                                            "output_tokens": 0, "_ttfts": []})
            m["calls"] += 1
            m["errors"] += 1 if error else 0
            m["tokens"] += tokens
            m["input_tokens"] += in_tok
            m["output_tokens"] += out_tok
            chat_tokens += tokens
            chat_in += in_tok
            chat_out += out_tok
            ttft = attrs.get("gen_ai.response.time_to_first_token")
            if ttft:
                m["_ttfts"].append(round(int(ttft) / 1e6, 1))
        elif op == "execute_tool":
            tool = attrs.get("gen_ai.tool.name") or "?"
            td = by_tool.setdefault(tool, {"tool": tool, "calls": 0, "errors": 0, "_durs": []})
            td["calls"] += 1
            td["errors"] += 1 if error else 0
            td["_durs"].append(dur_ms)
            key = (tool, attrs.get("gen_ai.tool.call.arguments"))
            repeated[key] = repeated.get(key, 0) + 1
        elif op == "react":
            rnd = c.to_int(attrs.get("gen_ai.react.round"), default=None)
            if rnd:
                react_rounds.append(rnd)
        elif op == "invoke_agent":
            agent_tokens += tokens
            cache_tokens += c.to_int(attrs.get("gen_ai.usage.cache_read.input_tokens"))

    by_operation = []
    for d in sorted(by_op.values(), key=lambda x: -x["spans"]):
        durs = d.pop("_durs")
        d["avg_ms"] = round(sum(durs) / len(durs), 1) if durs else None
        d["p95_ms"] = _p95(durs)
        by_operation.append(d)

    trace_candidates = _build_trace_candidates(rows, traces)

    by_model_out = []
    for m in sorted(by_model.values(), key=lambda x: -x["calls"]):
        ttfts = m.pop("_ttfts")
        m["avg_ttft_ms"] = round(sum(ttfts) / len(ttfts), 0) if ttfts else None
        by_model_out.append(m)
    by_tool_out = []
    for td in sorted(by_tool.values(), key=lambda x: -x["calls"]):
        durs = td.pop("_durs")
        td["avg_ms"] = round(sum(durs) / len(durs), 1) if durs else None
        td["p95_ms"] = _p95(durs)
        td["error_rate"] = round(td["errors"] / td["calls"], 4) if td["calls"] else 0.0
        by_tool_out.append(td)
    repeated_out = [{"tool": k[0], "arguments": c.truncate(k[1], 200), "times": n}
                    for k, n in sorted(repeated.items(), key=lambda x: -x[1]) if n > 1][:20]

    genai_spans = sum(d["spans"] for d in by_operation)
    return {
        "mode": "loongsuit",
        "binding": {**c.binding_block(cfg),
                    "trace_set": {"domain": a.TRACE_SET_DOMAIN, "name": a.TRACE_SET_NAME},
                    "api_version": a.CMS_API_VERSION},
        "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)},
        "agent_filter": getattr(args, "agent", None),
        "traces_analyzed": len(trace_ids),
        "trace_ids": trace_ids[:50],
        "trace_candidates": trace_candidates[:50],
        "enumeration_truncated": truncated,
        "enumeration_fallback": enum_fallback,
        "by_operation": by_operation,
        "by_model": by_model_out,
        "by_tool": by_tool_out[:50],
        "by_day": sorted(by_day.values(), key=lambda x: x["day"]),
        "sessions": [{"sessions": len(sessions), "users": len(users), "traces": len(trace_ids)}],
        "react_stats": [{"steps": len(react_rounds),
                         "max_round": max(react_rounds) if react_rounds else 0,
                         "avg_round": round(sum(react_rounds) / len(react_rounds), 1)
                         if react_rounds else 0}],
        # gen_ai.step.id is never populated in the measured data, so the step
        # layer is counted from span.kind instead of being invented
        "step_id_source": "span.kind+lineage",
        "steps_from_span_kind": steps_from_kind,
        "repeated_tool_calls": repeated_out,
        "services": sorted(services),
        "totals": {
            "genai_spans": genai_spans,
            "errors": errors,
            "error_rate": round(errors / genai_spans, 4) if genai_spans else 0.0,
            "model_tokens_from_chat_spans": chat_tokens,
            "agent_tokens_from_invoke_spans": agent_tokens,
            "cache_read_tokens": cache_tokens,
        },
        "token_composition": {
            "by_source_field": dict(tok_sum),
            "by_span_role": {
                "chat": {"total_tokens": chat_tokens, "input_tokens": chat_in,
                         "output_tokens": chat_out},
                "invoke_agent": {"total_tokens": agent_tokens},
            },
            "coverage": {"spans_total": tok_spans, "spans_with_usage": tok_covered,
                         "coverage": f"{tok_covered}/{tok_spans}"},
            "pricing": {
                "available": False,
                "reason": "neither source carries a price/cost/billing attribute and "
                          "this skill calls no billing API, so money is never computed",
                "money_label": "缺失",
            },
            "notes": [
                "token-only scope: consumption is reported in tokens, never in money; "
                "no unit price is bundled and no billing API is called",
                "tokens land only on chat and invoke_agent spans — tool calls and "
                "retrieval steps carry no token count, so a three-way "
                "model/tool/retrieval split cannot be drawn from this data",
                "cache_read_tokens may be under-reported (observed 0 despite warm "
                "prefix reuse); judge prefix-cache effects from TTFT spread, not "
                "from this attribute",
            ],
        },
        "notes": [
            "loongsuit mode: spans fetched from the CMS 2.0 workspace via UModel "
            "GetEntityStoreData (.trace_set with domain=apm, name=apm.trace.common)",
            "enumeration starts from entry spans (gen_ai.span.kind=ENTRY); with no ENTRY "
            "span in the window it falls back to kind=LLM and reports enumeration_fallback; "
            f"traces_analyzed is capped by --max-traces ({getattr(args, 'max_traces', a.DEFAULT_MAX_TRACES)})",
            "under ENTRY enumeration, hung/incomplete chains whose trace lacks an entry span "
            "are NOT enumerated here; if you know such a trace id (from the application's "
            "logs or the ebpf traceparent), use trace_chain.py --trace-id or "
            "decision_evidence.py --trace-id to reach it directly",
            "gen_ai.step.id is absent from the data, so the step layer is derived from "
            "gen_ai.span.kind=STEP plus the parent-child lineage (steps_from_span_kind), "
            "never from an invented step id",
            "tokens: model_tokens sums chat spans; agent_tokens sums invoke_agent spans "
            "(includes cached input; may differ from chat sum due to caching/rollups)",
            "repeated_tool_calls: identical (tool, arguments) pairs executed >1x — loop/retry candidates",
            "services: distinct serviceName across spans — cross-Agent call chains appear as >1 service",
            "trace_candidates: user-friendly trace list with input_summary (the user's original "
            "query excerpt from the entry span) for human selection; prefer this over trace_ids "
            "when presenting candidates to the user",
        ],
    }

def _delta(base, cur):
    """{base, current, delta_pct}; delta_pct is None when undefined."""
    out = {"base": base, "current": cur}
    if base in (None, 0) or cur is None:
        out["delta_pct"] = None
    else:
        out["delta_pct"] = round((cur - base) / base * 100, 1)
    return out

def _op_row(overview, op):
    return next((d for d in overview["by_operation"] if d["op"] == op), {})

def _drift_section(base, cur):
    """Cross-window metric deltas (base = preceding window, cur = current).
    Quantitative only; significance is the analyzing agent's judgment."""
    b_tot, c_tot = base["totals"], cur["totals"]
    b_sess = base["sessions"][0] if base["sessions"] else {}
    c_sess = cur["sessions"][0] if cur["sessions"] else {}
    b_react = base["react_stats"][0] if base["react_stats"] else {}
    c_react = cur["react_stats"][0] if cur["react_stats"] else {}
    b_chat, c_chat = _op_row(base, "chat"), _op_row(cur, "chat")

    models = sorted({m["model"] for m in base["by_model"]} |
                    {m["model"] for m in cur["by_model"]})
    b_models = {m["model"]: m for m in base["by_model"]}
    c_models = {m["model"]: m for m in cur["by_model"]}
    by_model = []
    for name in models:
        bm, cm = b_models.get(name, {}), c_models.get(name, {})
        by_model.append({
            "model": name,
            "calls": _delta(bm.get("calls", 0), cm.get("calls", 0)),
            "tokens": _delta(bm.get("tokens", 0), cm.get("tokens", 0)),
            "avg_ttft_ms": _delta(bm.get("avg_ttft_ms"), cm.get("avg_ttft_ms")),
        })

    tools = sorted({t["tool"] for t in base["by_tool"]} |
                   {t["tool"] for t in cur["by_tool"]})
    b_tools = {t["tool"]: t for t in base["by_tool"]}
    c_tools = {t["tool"]: t for t in cur["by_tool"]}
    by_tool = []
    for name in tools:
        bt, ct = b_tools.get(name, {}), c_tools.get(name, {})
        by_tool.append({
            "tool": name,
            "calls": _delta(bt.get("calls", 0), ct.get("calls", 0)),
            "errors": _delta(bt.get("errors", 0), ct.get("errors", 0)),
        })
    by_tool.sort(key=lambda x: -(x["calls"]["current"] or 0))

    return {
        "base_window": base["window"],
        "current_window": cur["window"],
        "totals": {
            "genai_spans": _delta(b_tot["genai_spans"], c_tot["genai_spans"]),
            "errors": _delta(b_tot["errors"], c_tot["errors"]),
            "error_rate": _delta(b_tot["error_rate"], c_tot["error_rate"]),
            "model_tokens": _delta(b_tot["model_tokens_from_chat_spans"],
                                   c_tot["model_tokens_from_chat_spans"]),
            "sessions": _delta(b_sess.get("sessions", 0), c_sess.get("sessions", 0)),
            "traces": _delta(b_sess.get("traces", 0), c_sess.get("traces", 0)),
        },
        "chat_latency": {
            "avg_ms": _delta(b_chat.get("avg_ms"), c_chat.get("avg_ms")),
            "p95_ms": _delta(b_chat.get("p95_ms"), c_chat.get("p95_ms")),
        },
        "react_stats": {
            "avg_round": _delta(b_react.get("avg_round"), c_react.get("avg_round")),
            "max_round": _delta(b_react.get("max_round"), c_react.get("max_round")),
        },
        "by_model": by_model,
        "by_tool": by_tool[:50],
        "notes": [
            "drift = same overview metrics over two adjacent windows "
            "(base immediately precedes current); delta_pct is None when the "
            "base value is 0/absent",
            "quantitative deltas only: whether a change is degradation "
            "(vs traffic mix / workload change) is a qualitative judgment — "
            "corroborate with by_day trends and per-trace drill-down",
            "both windows honor the same --agent / --service-name filters",
        ],
    }

def build_loongsuit(cfg, args, f, t):
    """LoongSuit overview; with --compare-hours also the preceding-window drift
    section (drift is loongsuit-side only)."""
    cur = _overview_loongsuit(cfg, args, f, t)
    compare_h = getattr(args, "compare_hours", None)
    if compare_h:
        base = _overview_loongsuit(cfg, args, f - int(compare_h * 3600), f)
        cur["drift"] = _drift_section(base, cur)
    return cur

# ---------------- ebpf mode (SLS ebpf-event runtime facts) ----------------

def _pair_exchanges(facets):
    """Pair http.request with http.response by http.exchange.id -> latency stats.

    Unpaired halves are counted, not dropped: a request without a response is
    an in-flight or lost call, and reporting it is the point."""
    pairs = {}
    unpaired_req, unpaired_resp = 0, 0
    for f in facets:
        xid = f["exchange_id"]
        if not xid:
            continue
        d = pairs.setdefault(xid, {})
        if f["http"].get("method"):
            d["request"] = f
        if f["http"].get("status_code"):
            d["response"] = f
    latencies = []
    exchanges = []
    for xid, d in pairs.items():
        req, resp = d.get("request"), d.get("response")
        latency_ms = None
        if req and resp:
            latency_ms = round((resp["ts_ns"] - req["ts_ns"]) / 1e6, 1)
            latencies.append(latency_ms)
        elif req:
            unpaired_req += 1
        elif resp:
            unpaired_resp += 1
        src = req or resp
        exchanges.append({
            "exchange_id": xid,
            "trace_id": src["trace_id"],
            "method": (req or {}).get("http", {}).get("method"),
            "url_path": (req or {}).get("http", {}).get("url_path"),
            "server_address": src["http"].get("server_address"),
            "status_code": (resp or {}).get("http", {}).get("status_code"),
            "latency_ms": latency_ms,
            "is_error": bool((resp or src)["is_error"]),
            "process": src["process"],
            "agent_type": src["agent_type"],
        })
    exchanges.sort(key=lambda x: -(x["latency_ms"] or 0))
    return {
        "pairs": len(latencies),
        "avg_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "p95_ms": _p95(latencies),
        "unpaired_requests": unpaired_req,
        "unpaired_responses": unpaired_resp,
    }, exchanges

def build_ebpf(cfg, args, f, t):
    """eBPF runtime-fact overview.

    Every dimension here is aggregated client-side: the ebpf-event index does
    not cover the fields the collector writes, so server-side SQL is impossible.
    Counts are therefore a sample whenever fetch_truncated is true."""
    raw, facets, truncated, narrowing = e.fetch_ebpf_rows(cfg, f, t)
    latency, exchanges = _pair_exchanges(facets)

    errors = sum(1 for x in facets if x["is_error"])
    trace_ids = sorted({x["trace_id"] for x in facets if x["trace_id"]})
    processes = {x["process"].get("pid") for x in facets if x["process"].get("pid")}
    containers = {x["container_id"] for x in facets if x["container_id"]}
    hosts = {x["host"].get("id") or x["host"].get("name") or x["host"].get("ip")
             for x in facets}
    hosts.discard(None)
    agent_types = {x["agent_type"] for x in facets if x["agent_type"]}

    by_process = [{"pid": d["key"], "count": d["count"]}
                  for d in e.aggregate_rows(facets, "process.pid", limit=50)]
    comm_by_pid = {}
    for x in facets:
        pid = x["process"].get("pid")
        if pid and x["process"].get("comm"):
            comm_by_pid.setdefault(pid, x["process"]["comm"])
    for row in by_process:
        row["comm"] = comm_by_pid.get(row["pid"])

    by_day = e.aggregate_rows(
        facets,
        lambda x: time.strftime("%Y-%m-%d", time.localtime(x["ts_ns"] / 1e9))
        if x["ts_ns"] else "unknown")
    by_day = [{"day": d["key"], "count": d["count"]}
              for d in sorted(by_day, key=lambda d: d["key"])]

    notes = [
        "ebpf mode: runtime facts fetched from the ebpf-event logstore as raw rows "
        "and aggregated client-side — the logstore index does not cover agent.type / "
        "pid / comm / url.* / http.*, so server-side SQL aggregation is rejected",
        "ebpf-event carries no Session/Turn/Step layer; those come from the "
        "loongsuit source (--workspace). This section reports runtime behaviour only",
        "ebpf rows join the loongsuit source through trace_id parsed out of "
        "http.request.header.traceparent; rows without a traceparent land in no group",
        "a zero token count on this side means UNMEASURABLE, not measured-zero: "
        "gen_ai.usage.* is declared in the ebpf-event index but never populated, so "
        "token totals must be read from the loongsuit side (see genai_index_coverage)",
    ]
    if truncated:
        notes.append(
            f"fetch_truncated: only the first {e.EBPF_FETCH_CAP} rows per logstore "
            "were sampled, so every count here is a sample, not a census — narrow "
            "the window or add --container-id / --agent-type filters")
    svc_note = e.service_filter_note(cfg, narrowing)
    if svc_note:
        notes.append(svc_note)

    return {
        "mode": "ebpf",
        "binding": {**c.binding_block(cfg), **narrowing},
        "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)},
        "totals": {
            "rows": len(facets),
            "exchanges": len(exchanges),
            "errors": errors,
            "error_rate": round(errors / len(facets), 4) if facets else 0.0,
            "hosts": len(hosts),
            "containers": len(containers),
            "processes": len(processes),
            "agent_types": len(agent_types),
            "trace_ids": len(trace_ids),
        },
        "by_event": [{"event": d["key"], "count": d["count"]}
                     for d in e.aggregate_rows(facets, "event_name")],
        "by_http_status": [{"status_code": d["key"], "count": d["count"]}
                           for d in e.aggregate_rows(facets, "http.status_code")],
        "by_url_path": [{"url_path": d["key"], "count": d["count"]}
                        for d in e.aggregate_rows(facets, "http.url_path", limit=50)],
        "by_method": [{"method": d["key"], "count": d["count"]}
                      for d in e.aggregate_rows(facets, "http.method")],
        "by_server": [{"server_address": d["key"], "count": d["count"]}
                      for d in e.aggregate_rows(facets, "http.server_address", limit=50)],
        "by_process": by_process,
        "by_container": [{"container_id": d["key"], "count": d["count"]}
                         for d in e.aggregate_rows(facets, "container_id", limit=50)],
        "by_host": [{"host": d["key"], "count": d["count"]}
                    for d in e.aggregate_rows(
                        facets, lambda x: x["host"].get("id") or x["host"].get("name")
                        or x["host"].get("ip"), limit=50)],
        "by_agent_type": [{"agent_type": d["key"], "count": d["count"]}
                          for d in e.aggregate_rows(facets, "agent_type")],
        "by_cluster": [{"cluster_id": d["key"], "count": d["count"]}
                       for d in e.aggregate_rows(facets, "k8s.cluster_id")],
        "by_node": [{"node_name": d["key"], "count": d["count"]}
                    for d in e.aggregate_rows(facets, "k8s.node_name", limit=50)],
        "by_day": by_day,
        "errors_by_type": [{"error_type": d["key"], "count": d["count"]}
                           for d in e.aggregate_rows(
                               [x for x in facets if x["is_error"]], "error_type")],
        "latency": latency,
        "exchanges": exchanges[:50],
        "trace_ids": trace_ids[:50],
        "genai_index_coverage": e.genai_index_coverage(raw),
        "notes": notes,
    }

def _fmt_delta(d):
    pct = "n/a" if d["delta_pct"] is None else f"{d['delta_pct']:+.1f}%"
    return f"{d['base']} -> {d['current']} ({pct})"

def main():
    p = c.base_parser("Application-level GenAI observability overview")
    p.add_argument("--agent", help="filter by gen_ai.agent.name (loongsuit side)")
    p.add_argument("--max-traces", dest="max_traces", type=int, default=a.DEFAULT_MAX_TRACES,
                   help=f"loongsuit mode: max traces enumerated (default {a.DEFAULT_MAX_TRACES})")
    p.add_argument("--compare-hours", dest="compare_hours", type=float, default=None,
                   help="loongsuit side: also overview the preceding N-hour window and emit a "
                        "drift section with per-metric base/current/delta_pct")
    args = p.parse_args()
    result = build(args)
    c.emit(result, args.format)

if __name__ == "__main__":
    c.main_wrapper(main)
