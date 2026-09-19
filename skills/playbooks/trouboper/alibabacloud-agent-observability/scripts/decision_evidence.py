#!/usr/bin/env python3
"""Extract decision evidence for one span / event (read-only).

Collects everything the analyzing agent needs for the three-perspective
judgment (why this call / chain position / result quality).

Dual-source combined (v3): with the default --mode both the evidence target
selects the source — --span-id extracts trace evidence, --event-id extracts
event evidence, both ids extract both (emitted side by side). --mode
loongsuit|ebpf restricts to one source.

- loongsuit mode: --span-id targets one CMS 2.0 trajectory span; evidence = the
  span's messages and attributes, its ancestor chain, sibling steps, the
  react rounds around it, and the trace's entry task.
- ebpf mode: --event-id (event.id) targets one ebpf-event runtime record;
  evidence = the row's HTTP/process/container/host facts, plus three context
  rings (same http.exchange.id, same pid within 60s, same trace_id). ebpf-event
  carries no message payloads, so messages/entry_task are null there.

Usage:
    python3 decision_evidence.py (--span-id <id> | --event-id <id>)
                                 [--from <ts> --to <ts>] [--detail-limit 2000]
                                 [--list-limit 200] [--format json]
"""

import json

import obs_core as c
import sls_event as e
import cms_trace as a

ROOT_MARKERS = ("", "0000000000000001")

def messages_of(attrs, key, limit):
    raw = attrs.get(key)
    if not raw:
        return None
    try:
        msgs = json.loads(raw)
    except json.JSONDecodeError:
        return c.truncate(raw, limit)
    out = []
    for m in msgs if isinstance(msgs, list) else []:
        if not isinstance(m, dict):
            continue
        parts = []
        for part in m.get("parts", []) or []:
            p = {}
            if isinstance(part, dict):
                if part.get("type"):
                    p["type"] = part["type"]
                p["content"] = c.truncate(part.get("content"), limit)
                # tool_call / tool_call_response carry name+arguments / response
                # in sibling keys, not in "content"
                for k, v in part.items():
                    if k in ("type", "content") or v is None:
                        continue
                    p[k] = c.truncate(v, limit) if isinstance(v, str) else v
            else:
                p["content"] = c.truncate(part, limit)
            parts.append(p)
        out.append({"role": m.get("role"), "parts": parts})
    return out

def tool_definitions(attrs, list_limit):
    raw = attrs.get("gen_ai.tool.definitions")
    if not raw:
        return None
    try:
        defs_ = json.loads(raw)
    except json.JSONDecodeError:
        return c.truncate(raw, list_limit)
    return [{"name": d.get("name"), "description": c.truncate(d.get("description"), list_limit)}
            for d in defs_ if isinstance(d, dict)]

REQUEST_PARAM_KEYS = ("max_tokens", "temperature", "top_p", "top_k",
                      "stop_sequences", "seed")

def request_params(attrs):
    out = {k: attrs[f"gen_ai.request.{k}"] for k in REQUEST_PARAM_KEYS
           if attrs.get(f"gen_ai.request.{k}") is not None}
    return out or None

def brief(item, list_limit):
    op = item.get("op")
    label = op or item.get("spanName") or "?"
    if op == "chat":
        label += f" {item.get('model') or ''}"
    elif op == "execute_tool":
        label += f" {item.get('tool') or ''}"
    return {"spanId": item["spanId"], "op": item.get("op"), "label": label.strip(),
            "error": item.get("error"), "tokens": item.get("tokens"),
            "duration_ms": item.get("duration_ms"),
            "arguments": c.truncate(item.get("arguments"), list_limit) if item.get("arguments") else None}

def build(args):
    cfg = c.Config.resolve(args)
    mode, narrowed = e.resolve_mode(cfg, args)
    f, t = c.resolve_window(args)
    if mode == "both":
        if not args.span_id and not args.event_id:
            raise c.ObsError(
                "both mode: pass --span-id (loongsuit evidence) and/or "
                "--event-id (ebpf evidence)")
        out = {"mode": "both", "window": {"from": f, "to": t}}
        if args.span_id:
            out["loongsuit"] = build_loongsuit(cfg, args, f, t)
        if args.event_id:
            out["ebpf"] = build_ebpf(cfg, args, f, t)
    elif mode == "ebpf":
        out = build_ebpf(cfg, args, f, t)
    else:
        out = build_loongsuit(cfg, args, f, t)
    # both auto-narrowing turns mode into loongsuit/ebpf, so these must sit
    # outside the dispatch or the narrowed case would never report them
    if narrowed:
        out["mode_narrowed"] = narrowed
    out["sources"] = c.source_availability(cfg, mode)
    out["gap_notes"] = c.gap_note(cfg)
    return out

# ---------------- loongsuit mode (CMS 2.0 workspace trajectory) ----------------

def _locate_span(cfg, args, f, t, span_pool):
    """Find the target span row: pool first, else enumerate + fetch.

    Primary enumeration is ENTRY-tagged (gen_ai.span.kind=ENTRY, falling
    back to kind=LLM when the window holds no ENTRY span). Spans of
    hung/incomplete chains can sit in traces whose entry span never landed;
    those are reached by passing --trace-id, which fetches that trace's spans
    directly instead of enumerating."""
    if span_pool:
        target = next((r for r in span_pool if r.get("spanId") == args.span_id), None)
        if target:
            return target, span_pool
    trace_id = getattr(args, "trace_id", None)
    if trace_id:
        rows = a.fetch_traces_spans(cfg, [trace_id], f, t)
    else:
        max_traces = getattr(args, "max_traces", a.DEFAULT_MAX_TRACES)
        traces, _, _ = a.search_agent_traces(cfg, f, t, max_traces=max_traces)
        rows = a.fetch_traces_spans(cfg, traces, f, t)
    target = next((r for r in rows if r.get("spanId") == args.span_id), None)
    if target is None:
        hint = ("check the id and the trace id" if trace_id else
                "shift --from/--to to the slice the span belongs to, or check the id "
                "(use trace_chain.py to list span ids); if the span belongs to a "
                "hung/incomplete chain whose trace has neither an ENTRY nor an LLM "
                "span, pass --trace-id to fetch that trace's spans directly")
        raise c.ObsError(f"span '{args.span_id}' not found in window; {hint}")
    return target, rows

def _runtime_calls(cfg, args, f, t, target_raw, event_pool=None):
    """Correlate the target loongsuit span to ebpf runtime facts via the W3C
    traceparent (trace_id + parent_span_id).

    The traceparent's third segment is the id of the span that made the
    outbound call, so an ebpf http.request captured inside span X should carry
    X's spanId. Whether that actually holds in this data is MEASURED here, not
    assumed: every exchange in the trace is classified as span-matched or
    trace-only and the counts are reported, so correlation quality stays
    observable instead of being asserted.

    The alternative join on an application-layer request id is not available:
    neither source carries `gen_ai.request.id`, so there is nothing to match
    `http.exchange.id` against."""
    if not cfg.has_ebpf:
        return {"present": False,
                "reason": "eBPF source not bound; pass --project to enable it"}
    import trace_chain as sc
    if event_pool:
        facets = e.link_by_exchange([e.runtime_facets(r) for r in event_pool])
    else:
        _, facets, _, _ = e.fetch_ebpf_rows(cfg, f, t)

    span_id = target_raw.get("spanId")
    trace_id = target_raw.get("traceId")
    grouped = {}
    for x in facets:
        if x["trace_id"] != trace_id:
            continue
        key = x["exchange_id"] or x["event_id"]
        cur = grouped.setdefault(key, {
            "exchange_id": x["exchange_id"], "event_ids": [], "ts": None,
            "method": None, "url_path": None, "server_address": None,
            "status_code": None, "parent_span_id": None, "error": None})
        cur["event_ids"].append(x["event_id"])
        cur["ts"] = cur["ts"] or sc.ns_iso(x["ts_ns"])
        cur["parent_span_id"] = cur["parent_span_id"] or x["parent_span_id"]
        cur["error"] = cur["error"] or x["error_type"]
        h = x["http"] or {}
        for k in ("method", "url_path", "server_address", "status_code"):
            cur[k] = cur[k] or h.get(k)

    span_hits = [g for g in grouped.values() if g["parent_span_id"] == span_id]
    trace_only = [g for g in grouped.values() if g["parent_span_id"] != span_id]
    total = len(span_hits) + len(trace_only)
    return {
        "present": True,
        "correlation": "w3c_traceparent",
        "join_keys": {"trace_id": trace_id, "span_id": span_id},
        "matched_by_span_id": span_hits[:20],
        "trace_only": trace_only[:20],
        "match": {
            "exchanges_in_trace": total,
            "by_span_id": len(span_hits),
            "trace_only": len(trace_only),
            "span_match_rate": round(len(span_hits) / total, 4) if total else None,
        },
        "notes": [
            "span-level join uses the traceparent third segment (parent_span_id) "
            "against the loongsuit spanId; the rate above is measured, so a low "
            "rate means the probe did not carry this span's id, not that the "
            "calls are missing",
            "the traceparent header only appears on http.request rows; response "
            "rows inherit trace_id and parent_span_id via http.exchange.id "
            "(link_by_exchange), which is why rows are grouped by exchange here",
            "no application-layer request id exists in either source "
            "(gen_ai.request.id is absent), so joining http.exchange.id to a "
            "gen_ai attribute is not possible",
        ],
    }


def build_loongsuit(cfg, args, f, t, span_pool=None, event_pool=None):
    """span_pool: optional raw span rows already fetched by trace_chain's
    collect dict; falls back to querying CMS 2.0."""
    if not args.span_id:
        raise c.ObsError("loongsuit mode: --span-id is required")
    target_raw, pool_rows = _locate_span(cfg, args, f, t, span_pool)

    trace_spans = [r for r in pool_rows if r.get("traceId") == target_raw["traceId"]] \
        if pool_rows else []
    if not trace_spans:
        trace_spans = a.fetch_traces_spans(cfg, [target_raw["traceId"]], f, t)

    import trace_chain as sc
    items = {s["spanId"]: s for s in (sc.summarize(r) for r in trace_spans)}
    target = items.get(args.span_id) or sc.summarize(target_raw)

    chain = []
    cur = target
    while cur and cur["parentSpanId"] not in ROOT_MARKERS and cur["parentSpanId"] in items:
        cur = items[cur["parentSpanId"]]
        chain.append(cur)
    chain.reverse()
    chain = [it for it in chain if it.get("op")]  # drop non-GenAI framework spans

    siblings = [it for it in items.values()
                if it["parentSpanId"] == target["parentSpanId"] and it["spanId"] != target["spanId"]
                and it.get("op")]
    siblings.sort(key=lambda x: x["start_ns"])

    react_rounds = sorted((it for it in items.values() if it["op"] == "react"),
                          key=lambda x: (x.get("round") or 0))
    enter = next((it for it in items.values() if it["op"] == "enter"), None)
    enter_task = None
    if enter:
        enter_attrs = c.parse_json_field(
            next(r for r in trace_spans if r["spanId"] == enter["spanId"]), "attributes")
        enter_task = messages_of(enter_attrs, "gen_ai.input.messages", args.detail_limit)

    attrs = c.parse_json_field(target_raw, "attributes")
    return {
        "mode": "loongsuit",
        "binding": {**c.binding_block(cfg),
                    "trace_set": {"domain": a.TRACE_SET_DOMAIN, "name": a.TRACE_SET_NAME},
                    "api_version": a.CMS_API_VERSION},
        "window": {"from": f, "to": t},
        "target": {
            **brief(target, args.list_limit),
            "spanName": target.get("spanName"),
            "service": target_raw.get("serviceName"),
            "agent": attrs.get("gen_ai.agent.name"),
            "span_kind": attrs.get("gen_ai.span.kind"),
            "round": target.get("round"),
            "finish_reason": target.get("finish_reason"),
            "finish_reasons": target.get("finish_reasons"),
            "ttft_ms": target.get("ttft_ms"),
            "request_params": request_params(attrs),
            "tool_type": attrs.get("gen_ai.tool.type"),
            "tool_call_id": attrs.get("gen_ai.tool.call.id"),
            "input_messages": messages_of(attrs, "gen_ai.input.messages", args.detail_limit),
            "output_messages": messages_of(attrs, "gen_ai.output.messages", args.detail_limit),
            "tool_arguments": c.truncate(attrs.get("gen_ai.tool.call.arguments"), args.detail_limit),
            "tool_result": c.truncate(attrs.get("gen_ai.tool.call.result"), args.detail_limit),
            "tool_definitions": tool_definitions(attrs, args.list_limit),
        },
        "ancestor_chain": [brief(it, args.list_limit) for it in chain],
        "siblings_around_target": [brief(it, args.list_limit) for it in siblings][:50],
        "react_rounds_in_trace": [
            {"spanId": it["spanId"], "round": it.get("round"),
             "finish_reason": it.get("finish_reason"), "error": it.get("error")}
            for it in react_rounds],
        "entry_task": enter_task,
        "runtime_calls": _runtime_calls(cfg, args, f, t, target_raw, event_pool),
        "session_id": attrs.get("gen_ai.session.id") or (
            next((it.get("session_id") for it in chain if it.get("session_id")), None)),
        "trace_id": target_raw["traceId"],
        "trace_span_count": len(items),
    }

# ---------------- ebpf mode (SLS ebpf-event runtime facts) ----------------

# seconds of process neighbourhood kept around the target row
PROCESS_NEIGHBOURHOOD_S = 60

def _locate_ebpf(cfg, args, f, t, event_pool):
    """Locate the target ebpf row and return the surrounding pool.

    event.id IS indexed in ebpf-event, so it can be pushed down server-side;
    every other locator would have to be filtered client-side."""
    if not args.event_id:
        raise c.ObsError("ebpf mode: --event-id is required (event.id)")
    if event_pool:
        for r in event_pool:
            if r.get("event.id") == args.event_id:
                return r, event_pool
    safe = args.event_id.replace("'", "").replace('"', "")
    rows, _ = e.run_ebpf_search(cfg, f'"event.id": "{safe}"', f, t, max_rows=10)
    if not rows:
        raise c.ObsError(
            f"no ebpf row matches event.id '{args.event_id}' in window; widen the "
            "window or check the id (use trace_overview.py --mode ebpf to list "
            "trace_ids, or trace_chain.py --mode ebpf --trace-id to list a trace's "
            "event ids)")
    return rows[0], None

def build_ebpf(cfg, args, f, t, event_pool=None):
    """Runtime-fact evidence for one ebpf row.

    event_pool: optional raw rows already fetched by trace_chain's collect
    dict; falls back to querying SLS. The context rings replace the old
    same-step/same-turn scoping, because ebpf-event has no Session/Turn/Step
    layer."""
    target_raw, pool_rows = _locate_ebpf(cfg, args, f, t, event_pool)
    import trace_chain as sc
    target = e.runtime_facets(target_raw)

    if pool_rows:
        facets = e.link_by_exchange([e.runtime_facets(r) for r in pool_rows])
    else:
        _, facets, _, _ = e.fetch_ebpf_rows(cfg, f, t)

    exchange_ring, process_ring, trace_ring = [], [], []
    pid = (target["process"] or {}).get("pid")
    for x in facets:
        if x["event_id"] == target["event_id"]:
            continue
        row = {"event_id": x["event_id"], "event_name": x["event_name"],
               "ts": sc.ns_iso(x["ts_ns"]), "trace_id": x["trace_id"],
               "exchange_id": x["exchange_id"],
               "method": x["http"].get("method"),
               "url_path": x["http"].get("url_path"),
               "status_code": x["http"].get("status_code"),
               "pid": (x["process"] or {}).get("pid"),
               "error": x["error_type"]}
        if x["exchange_id"] and x["exchange_id"] == target["exchange_id"]:
            exchange_ring.append(row)
        elif pid and (x["process"] or {}).get("pid") == pid and \
                abs(x["ts_ns"] - target["ts_ns"]) <= PROCESS_NEIGHBOURHOOD_S * 1e9:
            process_ring.append(row)
        elif x["trace_id"] and x["trace_id"] == target["trace_id"]:
            trace_ring.append(row)

    return {
        "mode": "ebpf",
        "binding": c.binding_block(cfg),
        "window": {"from": f, "to": t},
        "target": {
            "event_id": target["event_id"],
            "event_name": target["event_name"],
            "event_sequence": target["event_sequence"],
            "ts": sc.ns_iso(target["ts_ns"]),
            "trace_id": target["trace_id"],
            "trace_id_from": target["trace_id_from"],
            "parent_span_id": target["parent_span_id"],
            "exchange_id": target["exchange_id"],
            "agent_type": target["agent_type"],
            "http": target["http"],
            "process": target["process"],
            "container_id": target["container_id"],
            "host": target["host"],
            "k8s": target["k8s"],
            "error": {"type": target["error_type"],
                      "message": c.truncate(target["error_message"], args.detail_limit)}
                     if target["error_type"] else None,
            # ebpf-event carries no message payloads in this environment
            "messages": None,
        },
        "context": {
            "same_exchange": exchange_ring[:20],
            "same_process": process_ring[:50],
            "same_trace": trace_ring[:50],
            "process_neighbourhood_s": PROCESS_NEIGHBOURHOOD_S,
        },
        "entry_task": None,
        "session_id": None,
        "trace_id": target["trace_id"],
        "notes": [
            "ebpf-event carries no Session/Turn/Step layer and no message payloads, "
            "so entry_task and messages are null by construction — read the Agent "
            "decision on the loongsuit side via decision_evidence.py --span-id",
            "context rings replace the old same-step/same-turn scoping: the paired "
            "half of the same http.exchange.id, the same process (pid) within "
            f"{PROCESS_NEIGHBOURHOOD_S}s, and every runtime row of the same trace_id",
            "trace_id joins this evidence to the loongsuit source; trace_id_from says "
            "whether it came from the row's own traceparent or was propagated from "
            "the paired request via http.exchange.id",
        ],
    }

def main():
    p = c.base_parser("Extract decision evidence for one span / runtime event")
    p.add_argument("--span-id", dest="span_id",
                   help="loongsuit mode: target spanId")
    p.add_argument("--event-id", dest="event_id",
                   help="ebpf mode: target event.id")
    p.add_argument("--max-traces", dest="max_traces", type=int, default=a.DEFAULT_MAX_TRACES,
                   help=f"loongsuit mode standalone locate: max traces enumerated "
                        f"(default {a.DEFAULT_MAX_TRACES})")
    p.add_argument("--detail-limit", type=int, default=2000,
                   help="max chars per message/argument/result (default 2000)")
    p.add_argument("--list-limit", type=int, default=200,
                   help="max chars for list-level summaries (default 200)")
    args = p.parse_args()
    if not args.span_id and not args.event_id:
        raise c.ObsError("pass --span-id (loongsuit evidence) or --event-id (ebpf evidence)")
    result = build(args)
    c.emit(result, args.format)

if __name__ == "__main__":
    c.main_wrapper(main)
