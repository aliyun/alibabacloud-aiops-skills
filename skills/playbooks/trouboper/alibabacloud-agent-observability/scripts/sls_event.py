#!/usr/bin/env python3
"""SLS read-only gateway and ebpf-event source adapter.

One of the two trajectory sources; the other is the CMS 2.0 workspace
trajectory read through UModel GetEntityStoreData (see cms_trace.py). This
module covers the eBPF runtime facts stored in an SLS project's `ebpf-event`
logstore, fetched via read-only `aliyun sls` commands.

Responsibilities:
- Read-only `aliyun sls get-logs` subprocess wrapper (raw search)
- ebpf-event logstore binding / probing
- Mode resolution (both | loongsuit | ebpf) with auto-narrowing
- Runtime-fact extraction: traceparent parsing, process/container/host/k8s
  facets, client-side aggregation

The ebpf-event index declares a full OTel GenAI field set, but the fields the
collector actually writes (agent.type, pid, comm, cmdline, url.*,
server.address, http.*) are NOT indexed — server-side SQL aggregation on them
is rejected. So this module fetches raw rows and aggregates client-side; there
is no SQL path here at all. Field dictionary: references/ebpf-event-fields.md.

Read-only guarantee: only SELECT queries are allowed; any write verb is rejected.
"""

import json
import re
import subprocess
import time

import obs_core as c

# GetLogs raw (non-SQL) search returns at most 100 rows per call; larger
# fetches paginate via --offset (see run_ebpf_search).
SEARCH_PAGE = 100
# Client-side aggregation samples at most this many rows per logstore; hitting
# the cap is surfaced as fetch_truncated so a sample is never mistaken for a
# census.
EBPF_FETCH_CAP = 2000

# The logstore the eBPF collector writes runtime facts into.
EBPF_LOGSTORE = "ebpf-event"

# Indexed gen_ai.* keys, used only to report coverage: they are declared in the
# logstore index but were never populated in the measured environment, so
# counting them turns that into a quantitative gap instead of a silent one.
GENAI_INDEXED_KEYS = (
    "gen_ai.session.id", "gen_ai.turn.id", "gen_ai.step.id",
    "gen_ai.agent.id", "gen_ai.agent.name", "gen_ai.agent.type",
    "gen_ai.provider.name", "gen_ai.request.model", "gen_ai.response.model",
    "gen_ai.response.id", "gen_ai.response.finish_reasons",
    "gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens",
    "gen_ai.usage.total_tokens", "gen_ai.usage.cache_read.input_tokens",
    "gen_ai.usage.cache_creation.input_tokens",
    "gen_ai.tool.name", "gen_ai.tool.call.id", "gen_ai.tool.call.exec.id",
    "gen_ai.skill.name",
)

_WRITE_VERBS = re.compile(
    r"\b(insert|update|delete|drop|create|alter|truncate|merge|replace)\b",
    re.IGNORECASE,
)

# W3C traceparent: version-traceid-parentid-flags
_TRACEPARENT = re.compile(
    r"^([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def run_get_logs(cfg, query, from_ts, to_ts, line=None, offset=None, reverse=None,
                 timeout=120, logstore=None):
    """Run one read-only GetLogs call via aliyun CLI; return parsed JSON dict.

    Responses are served from / written to the local result cache; windows
    ending more than CACHE_STABLE_AGE seconds ago are immutable and cached
    permanently, recent windows expire after AGENT_OBS_CACHE_TTL."""
    ls = logstore or cfg.logstore
    if not ls:
        raise c.ObsError("internal: no logstore bound for get-logs")
    if _WRITE_VERBS.search(query):
        raise c.ObsError("refused: only read-only SELECT queries are allowed")
    from_ts, to_ts = int(from_ts), int(to_ts)
    cache_key = {"api": "get-logs", "project": cfg.project, "logstore": ls,
                 "region": cfg.region, "query": query,
                 "from": from_ts, "to": to_ts, "line": line, "offset": offset,
                 "reverse": reverse}
    cached = c.cache_get(cache_key)
    if cached is not None:
        return cached
    cmd = [
        "aliyun", "sls", "get-logs",
        "--project", cfg.project,
        "--logstore", ls,
        "--from", str(from_ts),
        "--to", str(to_ts),
        "--query", query,
        "--region", cfg.region,
        "--user-agent", c.user_agent(),
    ]
    if line is not None:
        cmd += ["--line", str(line)]
    if offset is not None:
        cmd += ["--offset", str(offset)]
    if reverse is not None:
        cmd += ["--reverse", "true" if reverse else "false"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise c.ObsError("aliyun CLI not found on PATH; see references/cli-installation-guide.md")
    except subprocess.TimeoutExpired:
        raise c.ObsError(f"get-logs timed out after {timeout}s; narrow the time window or simplify the query")
    out = proc.stdout.strip()
    if proc.returncode != 0 or not out:
        err = (proc.stderr or out).strip()
        hint = c.cli_plugin_hint(err, "sls", "aliyun-cli-sls")
        if hint:
            raise hint
        if "Unauthorized" in err or "AccessDenied" in err or "Permission" in err:
            raise c.ObsError(
                "SLS permission denied. Read references/ram-policies.md for the required "
                "read-only permissions, grant them, then retry.\n" + err[:800]
            )
        if "ProjectNotExist" in err or "LogStoreNotExist" in err:
            raise c.ObsError(
                f"SLS project/logstore not found (project={cfg.project}, logstore={ls}, "
                f"region={cfg.region}). Ask the user to provide the correct SLS project "
                f"(and region) that stores the 'ebpf-event' logstore, then pass "
                f"--project / --region and re-run.\n" + err[:500]
            )
        raise c.ObsError(f"get-logs failed: {err[:1000]}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        raise c.ObsError(f"unexpected non-JSON response from get-logs: {out[:500]}")
    c.cache_put(cache_key, data, stable=(to_ts <= time.time() - c.CACHE_STABLE_AGE))
    return data


def list_logstores(cfg, timeout=60):
    """Read-only ListLogStores via aliyun CLI; returns the logstore name list.

    Cached with the normal TTL (logstore layout rarely changes)."""
    cache_key = {"api": "list-log-stores", "project": cfg.project, "region": cfg.region}
    cached = c.cache_get(cache_key)
    if cached is not None:
        return cached.get("logstores", [])
    cmd = [
        "aliyun", "sls", "list-log-stores",
        "--project", cfg.project,
        "--region", cfg.region,
        "--user-agent", c.user_agent(),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise c.ObsError("aliyun CLI not found on PATH; see references/cli-installation-guide.md")
    except subprocess.TimeoutExpired:
        raise c.ObsError(f"list-log-stores timed out after {timeout}s")
    out = proc.stdout.strip()
    if proc.returncode != 0 or not out:
        err = (proc.stderr or out).strip()
        hint = c.cli_plugin_hint(err, "sls", "aliyun-cli-sls")
        if hint:
            raise hint
        if "Unauthorized" in err or "AccessDenied" in err or "Permission" in err:
            raise c.ObsError(
                "SLS permission denied. Read references/ram-policies.md for the required "
                "read-only permissions, grant them, then retry.\n" + err[:800]
            )
        if "ProjectNotExist" in err:
            raise c.ObsError(
                f"SLS project not found (project={cfg.project}, region={cfg.region}). "
                "Ask the user to provide the correct SLS project (and region) that stores "
                "the 'ebpf-event' logstore, then pass --project / --region and re-run.\n"
                + err[:500]
            )
        raise c.ObsError(f"list-log-stores failed: {err[:1000]}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        raise c.ObsError(f"unexpected non-JSON response from list-log-stores: {out[:500]}")
    c.cache_put(cache_key, data, stable=False)
    return data.get("logstores", [])


def bind_ebpf_logstore(cfg, args):
    """Finalize cfg.event_logstores for ebpf mode.

    An explicit --logstore (comma-separated) wins; otherwise probe the project
    and require ebpf-event."""
    if not cfg.project:
        raise c.ObsError(
            "ebpf mode needs an SLS project: pass --project "
            "(the project that stores the 'ebpf-event' logstore)")
    if cfg.logstore:
        cfg.event_logstores = [s.strip() for s in cfg.logstore.split(",") if s.strip()]
        cfg.logstore = None
        return
    stores = list_logstores(cfg)
    if EBPF_LOGSTORE not in stores:
        raise c.ObsError(
            f"no '{EBPF_LOGSTORE}' logstore in project '{cfg.project}' "
            f"(found: {', '.join(stores[:20]) or 'none'}). The eBPF collector writes "
            "runtime facts into that logstore — ask the user to confirm the SLS "
            "project (--project) that holds it, check that the eBPF producer is "
            "installed, or override with --logstore")
    cfg.event_logstores = [EBPF_LOGSTORE]
    cfg.logstore = None


def resolve_mode(cfg, args):
    """Resolve the query scope: both | loongsuit | ebpf.

    Returns (mode, narrowed). both (default) auto-narrows to whichever sources
    are bound, so supplying only one binding is legal and the missing side is
    reported as an instrumentation gap rather than silently dropped. An
    explicit single-source mode without its binding is an error. 'trace',
    'event' and 'auto' were retired by the rename and produce an actionable
    error instead of being silently accepted."""
    explicit = (getattr(args, "mode", None) or "both").lower()
    if explicit not in ("both", "loongsuit", "ebpf"):
        raise c.ObsError(
            f"invalid mode '{explicit}': use both|loongsuit|ebpf. This skill renamed "
            "the modes — 'trace' -> 'loongsuit' (CMS 2.0 workspace via "
            "GetEntityStoreData, LoongSuit Session/Turn/Step), 'event' -> 'ebpf' "
            "(SLS 'ebpf-event' logstore, eBPF runtime facts); the legacy alias "
            "'auto' was removed because 'both' now auto-narrows to whichever "
            "sources are bound.")
    if explicit == "ebpf" and not cfg.has_ebpf:
        raise c.ObsError(
            "--mode ebpf needs the eBPF/SLS binding, but --project was not supplied. "
            "Either pass --project (the SLS project holding the 'ebpf-event' logstore), "
            "or drop --mode so the run auto-narrows to the bound source "
            "(--workspace only -> loongsuit). There is no silent single-source "
            "fallback: the missing side is always reported as an instrumentation gap.")
    if explicit == "loongsuit" and not cfg.has_loongsuit:
        raise c.ObsError(
            "--mode loongsuit needs the LoongSuit/CMS binding, but --workspace was not "
            "supplied. Either pass --workspace (the CMS 2.0 workspace name), or drop "
            "--mode so the run auto-narrows to the bound source (--project only -> "
            "ebpf). There is no silent single-source fallback: the missing side is "
            "always reported as an instrumentation gap.")
    mode, narrowed = explicit, None
    if explicit == "both":
        if cfg.has_ebpf and cfg.has_loongsuit:
            mode = "both"
        elif cfg.has_ebpf:
            mode = "ebpf"
            narrowed = {"from": "both", "to": "ebpf",
                        "reason": "--workspace not supplied"}
        else:
            mode = "loongsuit"
            narrowed = {"from": "both", "to": "loongsuit",
                        "reason": "--project not supplied"}
    if mode in ("both", "ebpf"):
        bind_ebpf_logstore(cfg, args)
    cfg.mode = mode
    return mode, narrowed


# --- ebpf source helpers (SLS ebpf-event runtime facts) ---

def parse_traceparent(row):
    """Read the W3C traceparent out of an ebpf row -> {trace_id, parent_span_id,
    flags}, or None. This is the only key joining the ebpf source to the
    loongsuit source."""
    raw = (row.get("http.request.header.traceparent") or "").strip()
    m = _TRACEPARENT.match(raw)
    if not m:
        return None
    return {"trace_id": m.group(2), "parent_span_id": m.group(3),
            "flags": m.group(4)}


def runtime_facets(row):
    """Extract the runtime-fact facets of one ebpf row (process / container /
    host / k8s / agent / http). Every field here is unindexed, so all of this
    happens client-side."""
    tp = parse_traceparent(row) or {}
    status = row.get("http.response.status_code")
    return {
        "event_id": row.get("event.id"),
        "event_name": row.get("event.name"),
        "event_sequence": c.to_int(row.get("event.sequence")),
        "ts_ns": c.to_int(row.get("time_unix_nano")),
        "trace_id": tp.get("trace_id"),
        "parent_span_id": tp.get("parent_span_id"),
        "trace_id_from": "traceparent" if tp.get("trace_id") else None,
        "exchange_id": row.get("http.exchange.id"),
        "agent_type": row.get("agent.type"),
        "process": {"pid": row.get("pid"), "comm": row.get("comm"),
                    "cmdline": row.get("cmdline")},
        "container_id": row.get("container.id"),
        "host": {"id": row.get("host.id"), "name": row.get("host.name"),
                 "ip": row.get("host.ip"),
                 "hostname": row.get("__tag__:__hostname__")},
        "k8s": {"cluster_id": row.get("__tag__:_cluster_id_"),
                "node_name": row.get("__tag__:_node_name_"),
                "node_ip": row.get("__tag__:_node_ip_")},
        "http": {"method": row.get("http.request.method"),
                 "url_path": row.get("url.path"),
                 "url_scheme": row.get("url.scheme"),
                 "server_address": row.get("server.address"),
                 "status_code": status,
                 "body_size": c.to_int(row.get("http.response.body.size")),
                 "is_sse": row.get("is_sse"),
                 "user_agent": row.get("user_agent.original")},
        "error_type": row.get("error.type"),
        "error_message": row.get("error.message"),
        "is_error": bool(row.get("error.type") or row.get("error.message")
                         or (status and c.to_int(status) >= 500)),
    }


def aggregate_rows(rows, key_field, limit=None):
    """Client-side group-by over extracted facets.

    key_field: a facet path ('agent_type', 'http.status_code', 'process.pid')
    or a callable taking one facet dict. Returns [{"key", "count"}] sorted by
    count desc then key, so output is deterministic across runs."""
    counts = {}
    for facets in rows:
        if callable(key_field):
            key = key_field(facets)
        else:
            key = facets
            for part in key_field.split("."):
                key = key.get(part) if isinstance(key, dict) else None
        if key in (None, ""):
            key = "unknown"
        key = str(key)
        counts[key] = counts.get(key, 0) + 1
    out = [{"key": k, "count": v} for k, v in counts.items()]
    out.sort(key=lambda d: (-d["count"], d["key"]))
    return out[:limit] if limit else out


def genai_index_coverage(rows):
    """Per-key count of raw rows carrying a value for each indexed gen_ai.* key.

    The ebpf-event index declares the full OTel GenAI set, but a collector that
    only emits runtime facts leaves every one of them empty; reporting the
    counts makes that an explicit, quantitative gap."""
    return {key: sum(1 for r in rows if r.get(key)) for key in GENAI_INDEXED_KEYS}


def _quote_term(value):
    return '"' + str(value).replace('"', '\\"') + '"'


def ebpf_query(cfg):
    """Build the raw-search query from the narrowing flags.

    Only indexed fields may be expressed server-side (container.id, host.*,
    event.name). A trace id is deliberately NOT pushed down: it lives in
    http.request.header.traceparent, which the ebpf-event index does not cover,
    so a bare full-text term returns zero rows (verified live) — trace ids are
    filtered client-side after the fetch instead."""
    terms = []
    if getattr(cfg, "container_id", None):
        terms.append(f'"container.id": {_quote_term(cfg.container_id)}')
    host = getattr(cfg, "host", None)
    if host:
        terms.append("(" + " or ".join(
            f'"{f}": {_quote_term(host)}'
            for f in ("host.id", "host.name", "host.ip")) + ")")
    if getattr(cfg, "event_name", None):
        terms.append(f'"event.name": {_quote_term(cfg.event_name)}')
    return " and ".join(terms) or "*"


def ebpf_client_filter(cfg, facets):
    """Apply the narrowing that cannot be expressed server-side.

    Returns (kept, matched_fields): matched_fields records which client-side
    filter removed rows, so the output can state the narrowing honestly."""
    kept, matched = [], set()
    agent_type = getattr(cfg, "agent_type", None)
    comm = getattr(cfg, "comm", None)
    trace_id = getattr(cfg, "trace_id", None)
    match = getattr(cfg, "match", None)
    for f in facets:
        if agent_type and f["agent_type"] != agent_type:
            matched.add("agent.type")
            continue
        if comm and comm not in (f["process"].get("comm") or ""):
            matched.add("comm")
            continue
        if trace_id and f["trace_id"] != trace_id:
            matched.add("trace_id")
            continue
        if match:
            hay = " ".join(str(v) for v in (f["http"].get("url_path"),
                                            f["process"].get("cmdline"),
                                            f["http"].get("user_agent")) if v)
            if match.lower() not in hay.lower():
                matched.add("match")
                continue
        kept.append(f)
    return kept, sorted(matched)


def link_by_exchange(facets):
    """Propagate the trace id from a request row to its response row.

    Only http.request carries the traceparent header, so without this every
    http.response row would look ungrouped even though it belongs to the same
    exchange; http.exchange.id is what pairs the two halves."""
    by_exchange = {}
    for x in facets:
        if x["exchange_id"] and x["trace_id"]:
            by_exchange[x["exchange_id"]] = (x["trace_id"], x["parent_span_id"])
    for x in facets:
        if not x["trace_id"] and x["exchange_id"]:
            pair = by_exchange.get(x["exchange_id"])
            if pair:
                x["trace_id"], x["parent_span_id"] = pair
                x["trace_id_from"] = "exchange"
    return facets


def merge_event_rows(rows):
    """Deduplicate raw rows by event.id (multiple logstores via --logstore)."""
    seen, out = set(), []
    for row in rows:
        eid = row.get("event.id")
        if eid:
            if eid in seen:
                continue
            seen.add(eid)
        out.append(row)
    return out


def run_ebpf_search(cfg, query, from_ts, to_ts, max_rows=EBPF_FETCH_CAP,
                    timeout=120):
    """Raw (non-SQL) search over every bound ebpf logstore; merged rows.

    GetLogs raw search returns at most 100 rows per call, so each logstore is
    paginated with --offset (oldest first) until it runs dry or max_rows is
    reached. Returns (rows, truncated): truncated is True when any store
    stopped at its cap instead of running dry — the caller must then treat
    every count as a sample, not a census."""
    rows, truncated = [], False
    for ls in cfg.event_logstores:
        got, offset = 0, 0
        while got < max_rows:
            page = min(SEARCH_PAGE, max_rows - got)
            data = run_get_logs(cfg, query, from_ts, to_ts, line=page,
                                offset=offset, reverse=False,
                                timeout=timeout, logstore=ls)
            batch = data.get("data", [])
            rows.extend(batch)
            got += len(batch)
            if len(batch) < page:
                break
            offset += len(batch)
        else:
            truncated = True
    return merge_event_rows(rows), truncated


def fetch_ebpf_rows(cfg, from_ts, to_ts, max_rows=EBPF_FETCH_CAP):
    """Fetch and narrow ebpf rows for a window.

    Returns (raw_rows, facets, truncated, narrowing); narrowing reports the
    service-name situation and which client-side filters removed rows."""
    raw, truncated = run_ebpf_search(cfg, ebpf_query(cfg), from_ts, to_ts,
                                     max_rows=max_rows)
    facets = [runtime_facets(r) for r in raw]
    # before the client-side filter: a --trace-id filter would otherwise drop
    # every response row, which never carries a traceparent of its own
    facets = link_by_exchange(facets)
    facets, matched = ebpf_client_filter(cfg, facets)
    service_name = getattr(cfg, "service_name", None)
    narrowing = {
        "service_name": service_name,
        # the ebpf-event index carries neither service.name nor
        # __tag__:__service_name__, so an application filter can never apply
        "service_filter_unavailable": bool(service_name),
        "applied": False,
        "client_side_filters": matched,
        "fetch_truncated": truncated,
        "rows_fetched": len(raw),
        "rows_after_filter": len(facets),
    }
    return raw, facets, truncated, narrowing


def service_filter_note(cfg, narrowing):
    """One note line stating the ebpf-side narrowing (None when nothing to say)."""
    if narrowing.get("service_filter_unavailable"):
        return (f"service_filter_unavailable: the ebpf-event index carries neither "
                f"service.name nor __tag__:__service_name__, so the service-name "
                f"filter '{narrowing['service_name']}' cannot apply to the ebpf "
                f"source (the loongsuit source is still narrowed); use "
                f"--agent-type / --comm / --container-id to narrow ebpf rows")
    if not getattr(cfg, "service_name", None):
        return ("queries are NOT narrowed to one agent application "
                "(--service-name omitted): rows may mix every application "
                "reporting into this workspace / project pair")
    return None
