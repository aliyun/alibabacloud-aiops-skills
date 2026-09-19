#!/usr/bin/env python3
"""Rebuild one trace's agent call chain (loongsuit) and/or runtime timeline (ebpf).

The analysis unit is ONE trace, anchored on --trace-id in every mode. The
trace id is user-supplied (from the application's own logs/console, or from
trace_overview.py's trace_ids listing); this script never picks a trace on
the user's behalf.

Dual-source combined: loongsuit and ebpf are complementary views of the same
Agent trajectory. Default --mode both rebuilds both views anchored on the SAME
trace_id; a side with no data is reported present=false (coverage-gap
finding). --mode loongsuit|ebpf restricts to one source.

- loongsuit mode: fetches the trace's spans from the CMS 2.0 workspace
  (GetEntityStoreData filtered on traceId), rebuilds the parent-child span
  tree and annotates behavioral patterns: tool loops, retries, failed spans,
  react depth, latency decomposition, context growth. Cross-Agent chains
  surface via per-span serviceName.
- ebpf mode: rebuilds the trace's HTTP exchange timeline with request ->
  response latency pairing plus process/container/host facts, and flags
  failed exchanges, 5xx responses, repeated calls and unpaired halves.

Usage:
    python3 trace_chain.py --trace-id <32hex> [--from <ts> --to <ts>]
                           [--margin 300] [--event-limit 200] [--format json]

Window auto-narrowing: the loongsuit detail fetch runs against
[trace bounds +/- --margin seconds] instead of the full window. The ebpf
side cannot narrow this way — its anchor fields are unindexed, so no
server-side bounds probe is possible and window_narrowed stays null.
"""

import json
import time

import obs_core as c
import sls_event as e
import cms_trace as a

ROOT_MARKERS = ("", "0000000000000001")

def narrow_window(f, t, bounds, margin):
    """Clamp the outer window around trace bounds +/- margin seconds."""
    if not bounds:
        return f, t, None
    nf, nt = max(f, bounds[0] - margin), min(t, bounds[1] + margin)
    return nf, nt, {"from": nf, "to": nt, "margin_s": margin,
                    "bounds": {"from": bounds[0], "to": bounds[1]}}

def ns_iso(value):
    ts = c.to_int(value, default=None)
    if not ts:
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts / 1e9))

# ---------------- loongsuit mode (CMS 2.0 workspace trajectory) ----------------

def probe_trace_bounds(cfg, trace_id, f, t):
    """Cheap bounds probe for one trace: light-project span rows and fold
    their startTime/duration into (lo, hi) unix seconds. Returns None when
    the window holds no span of this trace."""
    safe = trace_id.replace("'", "").replace('"', "")
    rows, _ = a.search_spans(cfg, f, t,
                             where=f"traceId in ({a.spl_literal(safe)})",
                             project=("traceId", "startTime", "duration"))
    if not rows:
        return None
    lo = min(c.to_int(r.get("startTime")) for r in rows) // 1000
    hi = max((c.to_int(r.get("startTime")) + c.to_int(r.get("duration")))
             for r in rows) // 1000 + 1
    return lo, hi

def fetch_trace_spans(cfg, trace_id, f, t, margin=300, bounds=None):
    """Fetch one trace's spans via CMS 2.0 GetEntityStoreData, auto-narrowing
    the window around the trace bounds.

    Bounds come from a light bounds probe (no full-attribute scan). Safety
    net: if the trace returns no spans in the narrowed window (a span longer
    than the margin), the fetch falls back to the full window."""
    if bounds is None:
        bounds = probe_trace_bounds(cfg, trace_id, f, t)
    if bounds is None:
        raise c.ObsError(
            f"no spans found for trace '{trace_id}' in window; widen --hours or "
            "check --trace-id (trace_overview.py lists the trace_ids present in "
            "the window)")
    nf, nt, narrowed = narrow_window(f, t, bounds, margin)
    spans = a.fetch_traces_spans(cfg, [trace_id], nf, nt)
    if narrowed and not spans:
        spans = a.fetch_traces_spans(cfg, [trace_id], f, t)
        narrowed["fallback_full_window"] = True
    return spans, narrowed

def _messages_text(raw, limit=200):
    """Flatten a gen_ai.*.messages JSON payload into 'role: content' lines,
    truncated. Returns (text, full_chars): text is the truncated flattening
    (None when the payload is empty), full_chars the pre-truncation length."""
    if not raw:
        return None, None
    try:
        msgs = json.loads(raw)
    except json.JSONDecodeError:
        return c.truncate(raw, limit), len(raw)
    lines = []
    for m in msgs if isinstance(msgs, list) else []:
        if not isinstance(m, dict):
            continue
        role = m.get("role") or "?"
        parts = []
        for part in m.get("parts", []) or []:
            content = part.get("content") if isinstance(part, dict) else part
            if isinstance(content, str) and content:
                parts.append(content)
        if parts:
            lines.append(f"{role}: " + " ".join(parts))
    if not lines:
        return None, None
    full = "\n".join(lines)
    return c.truncate(full, limit), len(full)

def summarize(span):
    attrs = c.parse_json_field(span, "attributes")
    op = attrs.get("gen_ai.operation.name")
    item = {
        "spanId": span["spanId"],
        "traceId": span["traceId"],
        "parentSpanId": span.get("parentSpanId") or "",
        "op": op,
        "span_kind": attrs.get("gen_ai.span.kind"),
        "spanName": span.get("spanName"),
        "service": span.get("serviceName"),
        "agent": attrs.get("gen_ai.agent.name"),
        "start_ns": int(span.get("startTime") or 0),
        "duration_ms": round(int(span.get("duration") or 0) / 1e6, 1),
        "error": span.get("statusCode") == "2",
        "statusMessage": span.get("statusMessage") or None,
        "tokens": int(attrs.get("gen_ai.usage.total_tokens") or 0) or None,
    }
    if op == "react":
        item["round"] = int(attrs.get("gen_ai.react.round") or 0) or None
        item["finish_reason"] = attrs.get("gen_ai.react.finish_reason")
    elif op == "chat":
        item["model"] = attrs.get("gen_ai.request.model")
        fr = attrs.get("gen_ai.response.finish_reasons")
        try:
            item["finish_reasons"] = json.loads(fr) if fr else None
        except json.JSONDecodeError:
            item["finish_reasons"] = fr
        ttft = attrs.get("gen_ai.response.time_to_first_token")
        item["ttft_ms"] = round(int(ttft) / 1e6, 0) if ttft else None
        item["input_tokens"] = c.to_int(attrs.get("gen_ai.usage.input_tokens"), default=None)
        item["output_tokens"] = c.to_int(attrs.get("gen_ai.usage.output_tokens"), default=None)
        item["cache_read_tokens"] = c.to_int(
            attrs.get("gen_ai.usage.cache_read.input_tokens"), default=None)
        item["input_text"], item["input_chars"] = _messages_text(
            attrs.get("gen_ai.input.messages"))
        item["output_text"], item["output_chars"] = _messages_text(
            attrs.get("gen_ai.output.messages"))
        # latency decomposition: decode = duration - TTFT (both ms)
        if item["ttft_ms"] is not None and item["duration_ms"] > item["ttft_ms"]:
            item["decode_ms"] = round(item["duration_ms"] - item["ttft_ms"], 1)
            if item["output_tokens"]:
                item["decode_tps"] = round(item["output_tokens"] / (item["decode_ms"] / 1000), 1)
    elif op == "execute_tool":
        item["tool"] = attrs.get("gen_ai.tool.name")
        item["tool_type"] = attrs.get("gen_ai.tool.type")
        item["arguments"] = c.truncate(attrs.get("gen_ai.tool.call.arguments"), 200)
        args_raw = attrs.get("gen_ai.tool.call.arguments")
        item["input_text"] = item["arguments"]
        item["input_chars"] = len(args_raw) if args_raw else None
        item["output_text"], item["output_chars"] = _messages_text(
            attrs.get("gen_ai.tool.call.result"))
        if item["output_text"] is None and attrs.get("gen_ai.tool.call.result"):
            # tool results are usually a plain string, not a messages payload
            res = attrs.get("gen_ai.tool.call.result")
            item["output_text"] = c.truncate(res, 200)
            item["output_chars"] = len(res)
    elif op in ("enter", "invoke_agent"):
        item["session_id"] = attrs.get("gen_ai.session.id")
        item["user_id"] = attrs.get("gen_ai.user.id")
        item["model"] = attrs.get("gen_ai.request.model")
        item["input_text"], item["input_chars"] = _messages_text(
            attrs.get("gen_ai.input.messages"))
        item["output_text"], item["output_chars"] = _messages_text(
            attrs.get("gen_ai.output.messages"))
    return item

def build_tree(spans):
    items = [summarize(s) for s in spans]
    items.sort(key=lambda x: x["start_ns"])
    by_id = {it["spanId"]: it for it in items}
    children = {}
    roots = []
    for it in items:
        pid = it["parentSpanId"]
        # missing parents (occasional upstream detail gaps) become roots
        if pid in ROOT_MARKERS or pid not in by_id:
            roots.append(it)
        else:
            children.setdefault(pid, []).append(it)

    steps = []

    def walk(node, depth):
        if node.get("op"):
            out = dict(node)
            out["depth"] = depth
            steps.append(out)
            child_depth = depth + 1
        else:
            # collapse non-GenAI spans (the detail response includes framework
            # internals without gen_ai.operation.name): children inherit
            # the current depth
            child_depth = depth
        for child in children.get(node["spanId"], []):
            walk(child, child_depth)

    for root in roots:
        walk(root, 0)
    return steps

def detect_patterns(steps):
    patterns = {"failed_spans": [], "tool_loops": [], "max_react_round": 0}
    for st in steps:
        if st["error"]:
            patterns["failed_spans"].append(
                {"spanId": st["spanId"], "spanName": st["spanName"],
                 "statusMessage": st.get("statusMessage")})
        if st["op"] == "react" and st.get("round"):
            patterns["max_react_round"] = max(patterns["max_react_round"], st["round"])
    seen = {}
    for st in steps:
        if st["op"] == "execute_tool":
            k = (st.get("tool"), st.get("arguments"))
            seen.setdefault(k, []).append(st["spanId"])
    for (tool, args), ids in seen.items():
        if len(ids) > 1:
            patterns["tool_loops"].append(
                {"tool": tool, "arguments": args, "times": len(ids), "spanIds": ids})
    patterns["tool_loops"].sort(key=lambda x: x["times"], reverse=True)
    return patterns

def _percentile(values, pct):
    if not values:
        return None
    vs = sorted(values)
    idx = min(len(vs) - 1, int(round(pct / 100 * (len(vs) - 1))))
    return vs[idx]

def latency_profile(steps):
    """Latency decomposition over the chain's chat spans plus the chain
    self-baseline (TTFT / decode throughput / context-size quantiles)."""
    chats = [s for s in steps if s.get("op") == "chat"]
    if not chats:
        return {"present": False, "reason": "no chat spans in the chain"}
    rows = []
    for s in chats:
        rows.append({
            "spanId": s["spanId"],
            "traceId": s["traceId"],
            "start": time.strftime("%Y-%m-%d %H:%M:%S",
                                   time.localtime(s["start_ns"] / 1e9)),
            "model": s.get("model"),
            "duration_ms": s["duration_ms"],
            "ttft_ms": s.get("ttft_ms"),
            "decode_ms": s.get("decode_ms"),
            "decode_tps": s.get("decode_tps"),
            "input_tokens": s.get("input_tokens"),
            "output_tokens": s.get("output_tokens"),
            "cache_read_tokens": s.get("cache_read_tokens"),
        })
    ttfts = [r["ttft_ms"] for r in rows if r["ttft_ms"] is not None]
    tps = [r["decode_tps"] for r in rows if r["decode_tps"] is not None]
    ins = [r["input_tokens"] for r in rows if r["input_tokens"]]
    baseline = {
        "chats": len(rows),
        "ttft_ms": {"coverage": f"{len(ttfts)}/{len(rows)}",
                    "median": _percentile(ttfts, 50),
                    "p95": _percentile(ttfts, 95),
                    "max": max(ttfts) if ttfts else None},
        "decode_tps": {"median": _percentile(tps, 50),
                       "min": min(tps) if tps else None},
        "input_tokens": {"median": _percentile(ins, 50),
                         "max": max(ins) if ins else None},
    }
    notes = []
    if len(ttfts) < len(rows):
        notes.append("TTFT coverage incomplete: some models do not report "
                     "gen_ai.response.time_to_first_token")
    notes.append("cache_read_tokens may be under-reported (observed 0 despite "
                 "warm prefix reuse); judge prefix-cache effects from TTFT "
                 "spread, not from this attribute")
    return {"chats": rows, "baseline": baseline, "notes": notes}

# context_growth flag thresholds (see notes in the output)
GROWTH_PCT_FLAG = 100.0
MONOTONIC_FRAC_FLAG = 0.8

def context_growth(steps):
    """Context growth over the chain's chat spans in chronological order.

    Answers the recurring long-horizon question 'is this chain's context
    ballooning': per-chat input_tokens series plus growth summary. Within one
    trace the series runs across the react rounds. The threshold-derived flag
    only marks ballooning candidates; cost/quality impact is the analyzing
    agent's judgment."""
    chats = sorted((s for s in steps if s.get("op") == "chat"),
                   key=lambda s: s["start_ns"])
    if len(chats) < 2:
        return {"present": False, "reason": "fewer than 2 chat spans in the chain"}
    series = [{"spanId": s["spanId"], "input_tokens": s.get("input_tokens"),
               "ttft_ms": s.get("ttft_ms")} for s in chats]
    ins = [x["input_tokens"] for x in series if x["input_tokens"]]
    pairs = list(zip(ins, ins[1:]))
    monotonic_frac = (round(sum(1 for a, b in pairs if b > a) / len(pairs), 2)
                      if pairs else None)
    first, last = (ins[0], ins[-1]) if ins else (None, None)
    growth_pct = (round((last - first) / first * 100, 1)
                  if first and last is not None else None)
    ttfts = [x["ttft_ms"] for x in series if x["ttft_ms"] is not None]
    return {
        "chats": len(series),
        "input_tokens_coverage": f"{len(ins)}/{len(series)}",
        "series": series,
        "input_tokens": {
            "first": first, "last": last,
            "max": max(ins) if ins else None,
            "growth_pct": growth_pct,
            "monotonic_frac": monotonic_frac,
        },
        "total": {
            "input_tokens": sum(ins),
            "output_tokens": sum(s.get("output_tokens") or 0 for s in chats),
        },
        "ttft_ms": {"first": ttfts[0] if ttfts else None,
                    "last": ttfts[-1] if ttfts else None},
        "ballooning_candidate": bool(
            growth_pct is not None and growth_pct >= GROWTH_PCT_FLAG
            and monotonic_frac is not None and monotonic_frac >= MONOTONIC_FRAC_FLAG
            and len(ins) >= 5),
        "notes": [
            "input_tokens across successive chats approximates context growth; "
            "a flat series suggests context compression or independent calls",
            f"ballooning_candidate = growth_pct >= {GROWTH_PCT_FLAG:.0f} and "
            f"monotonic_frac >= {MONOTONIC_FRAC_FLAG} over >= 5 chats with "
            "input_tokens; judge cost/quality impact from total tokens and the "
            "TTFT trend (first vs last)",
            "the event side has no per-call context series; this view is trace-only",
        ],
    }

def op_duration_split(steps):
    """Per-operation roll-up of span count and duration.

    Feeds the report's "LLM vs tool" time-share donut. Pure sums over the
    already-fetched tree -- which op matters is the analyzing agent's call.

    Container ops are derived from the parent/child links rather than a
    hard-coded protocol list: an op is a container when a span of that op
    carries a child, which means its duration_ms already includes its
    children's. A donut must therefore take its shares from leaf_ops, or it
    double-counts.
    """
    by_id = {s["spanId"] for s in steps}
    has_child = set()
    counts, durations = {}, {}
    for s in steps:
        op = s.get("op") or "unknown"
        counts[op] = counts.get(op, 0) + 1
        durations[op] = round(durations.get(op, 0.0) + (s.get("duration_ms") or 0.0), 1)
        parent = s.get("parentSpanId")
        if parent and parent in by_id:
            has_child.add(parent)
    container_ops = sorted({s.get("op") or "unknown" for s in steps
                            if s["spanId"] in has_child})
    leaf_ops = sorted(set(counts) - set(container_ops))
    return {
        "count": counts,
        "duration_ms": durations,
        "container_ops": container_ops,
        "leaf_ops": leaf_ops,
        "total_duration_ms": round(sum(durations.values()), 1),
        "notes": [
            "container ops (their spans carry children) already include their "
            "children's duration_ms: take donut shares from leaf_ops only, "
            "otherwise nested react/chat/tool time is double-counted",
            "duration_ms is span-level; wall-clock trace elapsed time is the "
            "sum of depth-0 spans, not total_duration_ms",
        ],
    }

def llm_analysis(steps):
    """Per-model roll-up of chat spans for the LLM调用分析 table."""
    chats = [s for s in steps if s.get("op") == "chat"]
    by_model = {}
    for s in chats:
        m = s.get("model") or "unknown"
        by_model.setdefault(m, []).append(s)
    rows = []
    for model, group in sorted(by_model.items(), key=lambda kv: -len(kv[1])):
        n = len(group)
        dur = [s["duration_ms"] for s in group if s.get("duration_ms")]
        ttft = [s["ttft_ms"] for s in group if s.get("ttft_ms")]
        tps = [s["decode_tps"] for s in group if s.get("decode_tps")]
        rows.append({
            "model": model,
            "count": n,
            "total_tokens": sum(s.get("tokens") or 0 for s in group),
            "input_tokens": sum(s.get("input_tokens") or 0 for s in group),
            "output_tokens": sum(s.get("output_tokens") or 0 for s in group),
            "avg_duration_ms": round(sum(dur) / len(dur), 1) if dur else None,
            "avg_ttft_ms": round(sum(ttft) / len(ttft), 1) if ttft else None,
            "avg_output_tps": round(sum(tps) / len(tps), 1) if tps else None,
        })
    return {"rows": rows, "total_chats": len(chats)}


def tool_analysis(steps):
    """Per-tool roll-up of execute_tool spans for the Tool调用分析 table."""
    tools = [s for s in steps if s.get("op") == "execute_tool"]
    by_tool = {}
    for s in tools:
        t = s.get("tool") or s.get("spanName") or "unknown"
        by_tool.setdefault(t, []).append(s)
    rows = []
    for tool, group in sorted(by_tool.items(), key=lambda kv: -len(kv[1])):
        n = len(group)
        dur = [s["duration_ms"] for s in group if s.get("duration_ms") is not None]
        errs = sum(1 for s in group if s.get("error"))
        rows.append({
            "tool": tool,
            "count": n,
            "avg_duration_ms": round(sum(dur) / len(dur), 2) if dur else None,
            "total_duration_ms": round(sum(dur), 2) if dur else None,
            "error_count": errs,
            "error_rate": round(errs / n * 100, 1) if n else None,
        })
    return {"rows": rows, "total_tools": len(tools)}


def build_loongsuit(cfg, args, f, t, bounds=None, collect=None):
    margin = getattr(args, "margin", 300)
    spans, narrowed = fetch_trace_spans(
        cfg, args.trace_id, f, t, margin=margin, bounds=bounds)
    if collect is not None:
        collect["spans"] = spans
    steps = build_tree(spans)
    services = sorted({s["service"] for s in steps if s.get("service")})
    result = {
        "mode": "loongsuit",
        "binding": {**c.binding_block(cfg),
                    "trace_set": {"domain": a.TRACE_SET_DOMAIN, "name": a.TRACE_SET_NAME},
                    "api_version": a.CMS_API_VERSION},
        "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)},
        "window_narrowed": narrowed,
        "trace_id": args.trace_id,
        "span_count": len(steps),
        "services": services,
        "total_tokens": sum(s["tokens"] or 0 for s in steps if s["op"] == "chat"),
        "total_input_tokens": sum(s.get("input_tokens") or 0 for s in steps if s["op"] == "chat"),
        "total_output_tokens": sum(s.get("output_tokens") or 0 for s in steps if s["op"] == "chat"),
        "total_duration_ms": sum(s["duration_ms"] for s in steps if s["depth"] == 0),
        "avg_ttft_ms": (round(sum(s["ttft_ms"] for s in steps
                                  if s["op"] == "chat" and s.get("ttft_ms"))
                             / max(1, sum(1 for s in steps
                                          if s["op"] == "chat" and s.get("ttft_ms"))), 1)
                        if any(s.get("ttft_ms") for s in steps if s["op"] == "chat") else None),
        "chat_count": sum(1 for s in steps if s["op"] == "chat"),
        "tool_count": sum(1 for s in steps if s["op"] == "execute_tool"),
        "patterns": detect_patterns(steps),
        "latency": latency_profile(steps),
        "context_growth": context_growth(steps),
        "op_duration_split": op_duration_split(steps),
        "llm_analysis": llm_analysis(steps),
        "tool_analysis": tool_analysis(steps),
        "steps": steps,
    }
    if len(services) > 1:
        result["note"] = ("spans span multiple service.name values: this trace "
                          "crosses Agent runtimes (cross-Agent call chain)")
    return result

# ---------------- ebpf mode (SLS ebpf-event runtime facts) ----------------

def build_ebpf(cfg, args, f, t, bounds=None, collect=None):
    """Rebuild one trace's runtime timeline from ebpf-event.

    ebpf-event carries no Session/Turn/Step layer, so the anchor is --trace-id
    (the value parsed out of http.request.header.traceparent, which also joins
    the loongsuit source). The window cannot be auto-narrowed: the fields a
    bounds probe would need are unindexed, so no server-side min/max query is
    possible and the full outer window is scanned."""
    if not getattr(args, "trace_id", None):
        raise c.ObsError(
            "ebpf mode needs --trace-id: ebpf-event carries no Session/Turn/Step "
            "layer, so a trace id is the anchor. Take one from "
            "trace_overview.py --mode ebpf (trace_ids)")
    raw, facets, truncated, narrowing = e.fetch_ebpf_rows(cfg, f, t)
    if collect is not None:
        # raw rows, not facets: decision_evidence locates its target by event.id
        collect["ebpf_rows"] = raw
    # filter explicitly on the anchor rather than relying on cfg.trace_id
    # client-side filtering alone: the anchor is the chain's identity and must
    # hold even if the cfg-level filter changes
    anchor = getattr(args, "trace_id", None)
    facets = [x for x in facets if x["trace_id"] == anchor]
    if not facets:
        raise c.ObsError(
            f"no ebpf rows found for trace '{args.trace_id}' in window; widen the "
            "window or check --trace-id")

    exchanges = {}
    for x in facets:
        xid = x["exchange_id"] or f"(no-exchange){x['event_id']}"
        d = exchanges.setdefault(xid, {
            "exchange_id": x["exchange_id"], "trace_id": x["trace_id"],
            "ts": None, "method": None, "url_path": None, "url_scheme": None,
            "server_address": None, "status_code": None, "latency_ms": None,
            "is_sse": None, "body_size": None, "error": None,
            "process": None, "container_id": None, "host": None, "k8s": None,
            "agent_type": None, "event_ids": []})
        d["event_ids"].append(x["event_id"])
        if d["ts"] is None or x["ts_ns"] < d["ts"]:
            d["ts"] = x["ts_ns"]
        for key, src in (("process", "process"), ("container_id", "container_id"),
                         ("host", "host"), ("k8s", "k8s"), ("agent_type", "agent_type")):
            if d[key] is None and x[src]:
                d[key] = x[src]
        if x["http"].get("method"):
            d["method"] = x["http"]["method"]
            d["url_path"] = x["http"].get("url_path")
            d["url_scheme"] = x["http"].get("url_scheme")
            d["server_address"] = x["http"].get("server_address")
            d["user_agent"] = x["http"].get("user_agent")
        if x["http"].get("status_code"):
            d["status_code"] = x["http"]["status_code"]
            d["is_sse"] = x["http"].get("is_sse")
            d["body_size"] = x["http"].get("body_size")
        if x["is_error"]:
            d["error"] = x["error_type"] or f"status {x['http'].get('status_code')}"

    timeline = []
    latencies = []
    for xid, d in exchanges.items():
        req_ts = next((x["ts_ns"] for x in facets
                       if (x["exchange_id"] or f"(no-exchange){x['event_id']}") == xid
                       and x["http"].get("method")), None)
        resp_ts = next((x["ts_ns"] for x in facets
                        if (x["exchange_id"] or f"(no-exchange){x['event_id']}") == xid
                        and x["http"].get("status_code")), None)
        if req_ts and resp_ts:
            d["latency_ms"] = round((resp_ts - req_ts) / 1e6, 1)
            latencies.append(d["latency_ms"])
        elif req_ts or resp_ts:
            d["unpaired"] = "request" if req_ts else "response"
        d["ts"] = ns_iso(d["ts"])
        timeline.append(d)
    timeline.sort(key=lambda d: d["ts"] or "")

    seen_calls = {}
    for d in timeline:
        if d["method"]:
            key = (d["method"], d["url_path"], d["server_address"])
            seen_calls.setdefault(key, []).append(d["exchange_id"])
    repeated = [{"method": k[0], "url_path": k[1], "server_address": k[2],
                 "times": len(v), "exchange_ids": v}
                for k, v in seen_calls.items() if len(v) > 1]
    repeated.sort(key=lambda x: -x["times"])

    limit = getattr(args, "event_limit", 200)
    notes = [
        "ebpf-event carries no Session/Turn/Step layer: this timeline is anchored "
        "on --trace-id and pairs http.request with http.response by "
        "http.exchange.id to derive per-exchange latency",
        "window_narrowed is null by construction: the fields a bounds probe would "
        "need are unindexed in ebpf-event, so the full outer window is scanned and "
        "no server-side narrowing is possible",
        "trace_id joins this timeline to the loongsuit source; use "
        "decision_evidence.py --mode loongsuit --span-id to reach the Agent "
        "decision behind an exchange",
    ]
    if truncated:
        notes.append(f"fetch truncated: more than {e.EBPF_FETCH_CAP} rows per "
                     "logstore exist in the window; only the earliest were pulled, "
                     "so the timeline may be incomplete")
    svc_note = e.service_filter_note(cfg, narrowing)
    if svc_note:
        notes.append(svc_note)
    return {
        "mode": "ebpf",
        "binding": {**c.binding_block(cfg), **narrowing},
        "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)},
        "window_narrowed": None,
        "window_narrowed_note": "ebpf anchor fields are unindexed; no server-side "
                                "bounds probe is possible, so no narrowing happened",
        "trace_id": args.trace_id,
        "row_count": len(facets),
        "exchange_count": len(timeline),
        "fetch_truncated": truncated,
        "exchanges_truncated": len(timeline) > limit,
        "totals": {
            "rows": len(facets),
            "exchanges": len(timeline),
            "requests": sum(1 for d in timeline if d["method"]),
            "responses": sum(1 for d in timeline if d["status_code"]),
            "errors": sum(1 for d in timeline if d["error"]),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1)
            if latencies else None,
            "latency_pairs": len(latencies),
        },
        "patterns": {
            "failed_exchanges": [{"exchange_id": d["exchange_id"],
                                  "url_path": d["url_path"], "error": d["error"]}
                                 for d in timeline if d["error"]],
            "status_5xx": [{"exchange_id": d["exchange_id"],
                            "status_code": d["status_code"], "url_path": d["url_path"]}
                           for d in timeline
                           if c.to_int(d["status_code"]) >= 500],
            "repeated_calls": repeated[:20],
            "unpaired": [{"exchange_id": d["exchange_id"], "half": d.get("unpaired")}
                         for d in timeline if d.get("unpaired")],
        },
        "processes": e.aggregate_rows(facets, "process.pid"),
        "exchanges": timeline[:limit],
        "notes": notes,
    }

# ---------------- dispatch ----------------

def build_both(cfg, args, f, t, bounds=None, collect=None):
    """Dual-source combined: rebuild the chain from each source, both anchored
    on the SAME --trace-id. A source with no data is reported as present=false
    (a coverage-gap finding), not an error; only when BOTH sources are absent
    is the trace considered not found."""
    out = {"mode": "both", "trace_id": args.trace_id,
           "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)}}
    narrowed_by_source = {}
    try:
        out["loongsuit"] = build_loongsuit(cfg, args, f, t, bounds=bounds,
                                           collect=collect)
        narrowed_by_source["loongsuit"] = out["loongsuit"].get("window_narrowed")
    except c.ObsError as ex:
        msg = str(ex)
        if "no spans found" in msg:
            out["loongsuit"] = {"present": False, "reason": msg}
        else:
            raise

    try:
        out["ebpf"] = build_ebpf(cfg, args, f, t, bounds=bounds, collect=collect)
        narrowed_by_source["ebpf"] = out["ebpf"].get("window_narrowed")
    except c.ObsError as ex:
        msg = str(ex)
        if "no ebpf rows found" in msg:
            out["ebpf"] = {"present": False, "reason": msg}
        else:
            raise

    union = None
    for nwd in narrowed_by_source.values():
        if not nwd:
            continue
        union = ({"from": min(union["from"], nwd["from"]),
                  "to": max(union["to"], nwd["to"])} if union
                 else {"from": nwd["from"], "to": nwd["to"]})
    out["window_narrowed"] = union
    out["window_narrowed_by_source"] = narrowed_by_source
    if all(isinstance(out.get(s), dict) and out[s].get("present") is False
           for s in ("loongsuit", "ebpf")):
        raise c.ObsError(
            f"trace '{args.trace_id}' not found in either data source within "
            "window; widen the window or check --trace-id")
    out["note"] = ("dual-source combined chain: 'loongsuit' and 'ebpf' are aligned "
                   "views of the same run anchored on the same trace_id — the span "
                   "tree from the CMS workspace and the runtime timeline from "
                   "ebpf-event; a side with present=false is a coverage gap "
                   "(onboarding finding), not proof of absence")
    return out

def build(args):
    cfg = c.Config.resolve(args)
    mode, narrowed = e.resolve_mode(cfg, args)
    f, t = c.resolve_window(args)
    if mode == "ebpf":
        result = build_ebpf(cfg, args, f, t)
    elif mode == "loongsuit":
        result = build_loongsuit(cfg, args, f, t)
    else:
        result = build_both(cfg, args, f, t)
    # both auto-narrowing turns mode into loongsuit/ebpf, so this must sit
    # outside the dispatch or the narrowed case would never report it
    if narrowed:
        result["mode_narrowed"] = narrowed
    result["sources"] = c.source_availability(cfg, mode)
    result.setdefault("notes", [])
    if isinstance(result.get("notes"), list):
        result["notes"].extend(c.gap_note(cfg))
    else:
        result["gap_notes"] = c.gap_note(cfg)
    return result

def _summary_only(result):
    """Strip the heavy per-span tree and per-chat detail rows, keeping only
    aggregated analysis. Reduces output from ~100KB+ to ~3-5KB so the agent
    can consume the key findings without flooding the context window.

    The full output (with steps[]) is still available via report_render.py
    reading the chain JSON file directly."""
    def _strip_mode(d):
        if not isinstance(d, dict):
            return d
        out = {k: v for k, v in d.items()
               if k not in ("steps", "chats", "series")}
        if "latency" in out and isinstance(out["latency"], dict):
            lat = dict(out["latency"])
            lat.pop("chats", None)
            out["latency"] = lat
        if "context_growth" in out and isinstance(out["context_growth"], dict):
            cg = dict(out["context_growth"])
            cg.pop("series", None)
            out["context_growth"] = cg
        return out

    out = dict(result)
    out.pop("steps", None)
    if "latency" in out and isinstance(out["latency"], dict):
        lat = dict(out["latency"])
        lat.pop("chats", None)
        if "baseline" in lat and isinstance(lat["baseline"], dict):
            lat["baseline"] = dict(lat["baseline"])
        out["latency"] = lat
    if "context_growth" in out and isinstance(out["context_growth"], dict):
        cg = dict(out["context_growth"])
        cg.pop("series", None)
        out["context_growth"] = cg
    for key in ("loongsuit", "ebpf"):
        if key in out and isinstance(out[key], dict):
            out[key] = _strip_mode(out[key])
    out["summary_only"] = True
    out.setdefault("notes", [])
    if isinstance(out["notes"], list):
        out["notes"].append(
            "summary_only: steps[] and per-chat latency/context series "
            "stripped to reduce context footprint; re-run without "
            "--summary-only or read the chain JSON file for full detail")
    return out


def main():
    p = c.base_parser("Rebuild one trace's agent call chain, and/or its runtime "
                      "timeline")
    p.add_argument("--margin", type=int, default=300,
                   help="seconds added around the trace bounds when auto-narrowing "
                        "the loongsuit fetch window (default 300)")
    p.add_argument("--event-limit", dest="event_limit", type=int, default=200,
                   help="ebpf mode: max exchanges to emit (default 200)")
    p.add_argument("--detail-limit", dest="detail_limit", type=int, default=200,
                   help="per-field text truncation (default 200)")
    p.add_argument("--summary-only", dest="summary_only", action="store_true",
                   default=False,
                   help="strip steps[] and per-chat detail rows from output; "
                        "keeps aggregated analysis (latency baseline, context "
                        "growth summary, op split, patterns) for agent consumption "
                        "without flooding the context window")
    args = p.parse_args()
    if not args.trace_id:
        p.error("--trace-id is required: the analysis unit is one user-specified "
                "trace (take a trace id from trace_overview.py's trace_ids or from "
                "the application's own logs)")
    result = build(args)
    if args.summary_only:
        result = _summary_only(result)
    c.emit(result, args.format)

if __name__ == "__main__":
    c.main_wrapper(main)
