#!/usr/bin/env python3
"""Content search over trajectory spans (loongsuit source only, read-only).

Locates WHERE a piece of text (a user request, an injected instruction, a
tool result) appears in the agent trajectory, anchored to spans and traces —
the entry point for security/hijack-style localization when the caller knows
the content but not the trace id.

The search is case-insensitive substring over every message role of each
span's gen_ai.input.messages AND gen_ai.output.messages. All roles matter:
an injected instruction typically enters the context as role="tool" (a tool
result), not as a user turn, so restricting the search to the user turn would
hide it. Hits carry locator ids (trace_id / span_id / op) plus the role-based
field label and a context snippet, sorted by time and capped by --limit.

ebpf-event carries no message payloads, so content search is meaningful on
the loongsuit source only; binding a CMS 2.0 workspace (--workspace) is
required.

Cost grows linearly with the window span and the enumerated trace count:
run this only inside the slice confirmed in Step 0 (SKILL.md section 8).

Usage:
    python3 span_search.py --match TEXT --workspace <ws> --region <region>
                           [--from <ts> --to <ts>] [--limit 50] [--format json]
"""

import json
import sys

import obs_core as c
import cms_trace as a

MATCH_CONTEXT_RADIUS = 100   # chars kept around a match in the snippet

# ---------------- match helpers (any-role, case-insensitive) ----------------

def _match_context(content, needle, radius=MATCH_CONTEXT_RADIUS):
    """Snippet around the first occurrence of needle (needle pre-lowercased)."""
    i = content.lower().find(needle)
    if i < 0:
        return None
    lo = max(0, i - radius)
    return c.truncate(content[lo:i + len(needle) + radius],
                      2 * radius + len(needle) + 40)

def _message_texts(raw):
    """Yield (role, content) of a gen_ai.*.messages JSON payload, one pair per
    message part carrying string content. Every role is yielded: an injected
    instruction enters the context through a tool result (role="tool"), not
    through the user turn."""
    if not raw:
        return
    try:
        msgs = json.loads(raw)
    except json.JSONDecodeError:
        yield None, raw
        return
    for m in msgs if isinstance(msgs, list) else []:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        for part in m.get("parts", []) or []:
            if not isinstance(part, dict):
                continue
            content = part.get("content")
            if isinstance(content, str) and content:
                yield role, content

# ---------------- search ----------------

def build(args):
    cfg = c.Config.resolve(args)
    if not cfg.has_loongsuit:
        raise c.ObsError(
            "span_search needs the loongsuit source: pass --workspace (CMS 2.0 "
            "workspace name). ebpf-event carries no message payloads, so there "
            "is no message content to search on the ebpf side")
    f, t = c.resolve_window(args)
    needle = (args.match or "").strip().lower()

    traces, truncated, enum_fallback = a.search_agent_traces(
        cfg, f, t, max_traces=getattr(args, "max_traces", a.DEFAULT_MAX_TRACES))
    if truncated:
        cap = getattr(args, "max_traces", a.DEFAULT_MAX_TRACES)
        print(f"note: loongsuit enumeration hit the --max-traces cap ({cap}); the "
              f"search covers the first {cap} enumerated traces only. Narrow the "
              "window, add --service-name filters, or raise --max-traces for full "
              "coverage.", file=sys.stderr)
    trace_ids = [tr["trace_id"] for tr in traces]
    rows = a.fetch_traces_spans(cfg, traces, f, t) if trace_ids else []

    hits = []
    for r in rows:
        attrs = c.parse_json_field(r, "attributes")
        op = attrs.get("gen_ai.operation.name")
        if not op:
            continue
        for msg_key, side in (("gen_ai.input.messages", "input"),
                              ("gen_ai.output.messages", "output")):
            for role, content in _message_texts(attrs.get(msg_key)):
                sn = _match_context(content, needle)
                if sn:
                    hits.append({
                        "trace_id": r["traceId"],
                        "span_id": r.get("spanId"),
                        "op": op,
                        "agent": attrs.get("gen_ai.agent.name"),
                        "service": r.get("serviceName"),
                        "field": f"{side}.{role or 'messages'}",
                        "start_ns": int(r.get("startTime") or 0),
                        "snippet": sn,
                    })
                    break  # one hit per span per side is enough to locate it

    hits.sort(key=lambda h: h["start_ns"])
    for h in hits:
        ns = h.pop("start_ns")
        h["start"] = ns // 1_000_000_000 if ns else None

    result = {
        "mode": "loongsuit",
        "binding": {**c.binding_block(cfg),
                    "trace_set": {"domain": a.TRACE_SET_DOMAIN, "name": a.TRACE_SET_NAME},
                    "api_version": a.CMS_API_VERSION},
        "window": {"from": f, "to": t, "hours": round((t - f) / 3600, 2)},
        "match": args.match,
        "count": len(hits[:args.limit]),
        "hits": hits[:args.limit],
        "traces_enumerated": len(trace_ids),
        "enumeration_truncated": truncated,
        "enumeration_fallback": enum_fallback,
        "sources": c.source_availability(cfg, "loongsuit"),
        "notes": [
            "content search over span gen_ai.input.messages AND gen_ai.output.messages, "
            "every message role (case-insensitive substring); hits are anchored to "
            "trace_id/span_id — feed the trace_id into trace_chain.py and the span_id "
            "into decision_evidence.py",
            "an injected instruction typically enters the context as role=\"tool\" "
            "(a tool result), so hits labelled input.tool are the usual hijack "
            "signature",
            "spans are scanned client-side after enumeration by gen_ai.span.kind=ENTRY "
            "(falling back to kind=LLM when the window holds no ENTRY span), capped by "
            "--max-traces; traces beyond the cap are not searched",
            "ebpf-event carries no message payloads, so this search is loongsuit-only",
        ],
    }
    result["notes"].extend(c.gap_note(cfg))
    return result

def main():
    p = c.base_parser("Content search over trajectory spans (loongsuit source)")
    p.add_argument("--match", required=True,
                   help="text to locate (case-insensitive substring), scanned across "
                        "every message role of each span's input AND output messages; "
                        "a payload injected via a tool result shows up as input.tool")
    p.add_argument("--limit", type=int, default=50,
                   help="max hits to emit, earliest first (default 50)")
    p.add_argument("--max-traces", dest="max_traces", type=int,
                   default=a.DEFAULT_MAX_TRACES,
                   help=f"max traces enumerated (default {a.DEFAULT_MAX_TRACES})")
    args = p.parse_args()
    result = build(args)
    c.emit(result, args.format)

if __name__ == "__main__":
    c.main_wrapper(main)
