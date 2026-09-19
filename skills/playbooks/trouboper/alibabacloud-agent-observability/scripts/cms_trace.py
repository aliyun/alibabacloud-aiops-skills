#!/usr/bin/env python3
"""CMS 2.0 UModel read-only client for loongsuit mode.

Data source: the LoongSuit agent trajectory (Session / Turn / Step and
framework state) of a CMS 2.0 workspace, read through the unified data model
(UModel) `GetEntityStoreData` API rather than any ARMS endpoint. Field
contract: references/otel-genai-attributes.md; query-language cheatsheet:
references/cms-umodel-query.md.

Access is via `aliyun cms` with `--api-version 2024-03-30`; only whitelisted
read-only actions may run, and every SPL query is screened against SPL_DENY
before it leaves the process (some SPL pipeline commands such as http-call /
llm-call perform outbound or model calls, which are not read-only observation).

Span rows come back already in the shared shape used downstream
(traceId/spanId/parentSpanId/spanName/serviceName/startTime ns/duration ns/
statusCode/statusMessage/attributes JSON/resources JSON), so the tree, pattern
and evidence logic is unchanged.

SPL facts verified live against workspace
default-cms-1543428740671114-cn-hangzhou on 2026-09-13 — the grammar is narrow
and undocumented, so these are asserted by tests rather than assumed:
- a statement must start with a directive (.trace_set / .entity / .umodel ...);
  a bare index query is rejected ("index query is not supported in umodel mode")
- attribute keys contain dots, so JSONPath needs bracket notation
  $["gen_ai.session.id"]; the dotted form parses as a nested path and returns null
- aggregation only accepts the alias-equals form: stats c = count(*) by field
- statusCode has no consistent type: `= 2` fails with eq(VARCHAR, INTEGER) and
  `= '2'` fails with "'=' cannot be applied to bigint, varchar(1)"; the working
  form is cast(statusCode as bigint) = 2
- offset paging is `limit <offset>, <count>`
"""

import json
import re
import subprocess
import time

import obs_core as c

CMS_ACTION_WHITELIST = ("get-entity-store-data", "list-workspaces")
CMS_API_VERSION = "2024-03-30"

# Trace data set, discovered via `.umodel | where kind = 'trace_set'`:
# domain apm, protocol otel, common_schema apm-common.
TRACE_SET_DOMAIN = "apm"
TRACE_SET_NAME = "apm.trace.common"

SPAN_PAGE = 1000            # spans per SPL page (offset paging)
TRACE_BATCH = 50            # trace ids per `traceId in (...)` detail query
DEFAULT_MAX_TRACES = 200    # enumeration cap for overview/listing stages

# SPL pipeline commands that perform an outbound HTTP or model call. They are
# legal SPL but are not read-only observation, so they are refused here — the
# same boundary that sls_event._WRITE_VERBS draws for SQL write verbs.
SPL_DENY = re.compile(
    r"\b(http-call|llm-call|agentic-call|embedding|entity-call|"
    r"prom-call|graph-call)\b",
    re.IGNORECASE,
)

# gen_ai.span.kind markers. ENTRY is the application entry point; apps that
# instrument only the LLM/STEP/TOOL layers emit no ENTRY span at all, so the
# discovery path falls back to LLM (see search_agent_traces).
ENTRY_KIND = "ENTRY"
LLM_KIND = "LLM"

# statusCode follows OTel: 0 UNSET, 1 OK, 2 ERROR.
STATUS_ERROR = 2

SPAN_FIELDS = ("traceId", "spanId", "parentSpanId", "spanName", "serviceName",
               "startTime", "duration", "statusCode", "statusMessage",
               "attributes", "resources")


def spl_literal(value):
    """SPL single-quoted string literal (embedded quotes doubled)."""
    return "'" + str(value).replace("'", "''") + "'"


def trace_set_prelude():
    """The directive every trace query must start with."""
    return (f".trace_set with (domain={spl_literal(TRACE_SET_DOMAIN)}, "
            f"name={spl_literal(TRACE_SET_NAME)})")


def attr(key):
    """SPL expression reading one dotted attribute key out of the attributes
    JSON object. Bracket notation is mandatory: the key itself contains dots."""
    safe = str(key).replace('"', '\\"')
    return f'json_extract_scalar(attributes, \'$["{safe}"]\')'


def status_error_pred():
    """SPL predicate matching error spans (statusCode has no consistent type)."""
    return f"cast(statusCode as bigint) = {STATUS_ERROR}"


def stats(alias, agg="count", by=None):
    """SPL aggregation clause. Only the alias-equals form parses;
    `count(*) as c` / `count(*) by f` / `count() by f` are all rejected."""
    clause = f"| stats {alias} = {agg}(*)"
    if by:
        clause += f" by {by}"
    return clause


def build_query(where="", project=(), sort=None, offset=0, count=SPAN_PAGE):
    """Assemble one read-only trace query."""
    q = trace_set_prelude()
    if where:
        q += f" | where {where}"
    if project:
        q += " | project " + ", ".join(project)
    if sort:
        q += f" | sort {sort}"
    q += f" | limit {int(offset)}, {int(count)}"
    return q


def guard_spl(query):
    """Refuse any SPL query containing a pipeline command that makes an
    outbound or model call."""
    hit = SPL_DENY.search(query)
    if hit:
        raise c.ObsError(
            f"refused: only read-only SPL pipeline commands are allowed; "
            f"'{hit.group(0)}' performs an outbound/model call")
    return query


def rows_from_response(data):
    """Turn a GetEntityStoreData response (header + array rows) into dicts."""
    header = data.get("header") or []
    out = []
    for row in data.get("data") or []:
        if isinstance(row, dict):
            out.append(row)
        elif isinstance(row, list):
            out.append(dict(zip(header, row)))
    return out


def run_cms(cfg, action, params, timeout=120, stable=None):
    """Run one whitelisted read-only CMS 2.0 action; return the parsed response.

    params: {flag: value} (kebab-case flags, no leading --). Responses go
    through the shared local cache; stable=None derives immutability from the
    window end, exactly like the other gateways."""
    if action not in CMS_ACTION_WHITELIST:
        raise c.ObsError(f"refused: CMS action '{action}' is not in the read-only "
                         f"whitelist {CMS_ACTION_WHITELIST}")
    cache_key = {"api": f"cms {action}", "region": cfg.region,
                 "workspace": getattr(cfg, "workspace", None), "params": params}
    cached = c.cache_get(cache_key)
    if cached is not None:
        return cached
    cmd = ["aliyun", "cms", action, "--api-version", CMS_API_VERSION]
    for flag, value in params.items():
        cmd.append(f"--{flag}")
        if isinstance(value, (list, tuple)):
            cmd.extend(str(v) for v in value)
        else:
            cmd.append(str(value))
    cmd += ["--region", cfg.region, "--user-agent", c.user_agent()]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise c.ObsError("aliyun CLI not found on PATH; see references/cli-installation-guide.md")
    except subprocess.TimeoutExpired:
        raise c.ObsError(f"cms {action} timed out after {timeout}s; narrow the time window")
    out = proc.stdout.strip()
    if proc.returncode != 0 or not out:
        err = (proc.stderr or out).strip()
        hint = c.cli_plugin_hint(err, "cms", "aliyun-cli-cms")
        if hint:
            raise hint
        if any(k in err for k in ("Forbidden", "NoPermission", "AccessDenied",
                                  "Unauthorized", "not authorized")):
            raise c.ObsError(
                "CMS 2.0 permission denied. Read references/ram-policies.md for the "
                "required read-only permissions (cms:ListWorkspaces / "
                "cms:GetEntityStoreData), grant them, then retry.\n" + err[:800]
            )
        if "InvalidSPLFormat" in err:
            # Surface the server's own diagnosis verbatim — the SPL grammar is
            # narrow and the message names the offending token position.
            raise c.ObsError(
                f"CMS 2.0 rejected the SPL query: {err[:1200]}\n"
                "hint: see references/cms-umodel-query.md for the verified query "
                "shapes (directive prelude, bracket JSONPath, alias-equals stats)")
        raise c.ObsError(
            f"cms {action} failed: {err[:1000]}\n"
            "hint: confirm the loongsuit-source bindings — --workspace (CMS 2.0 "
            "workspace name, a real GetEntityStoreData query parameter) and "
            "--region — and that the RAM identity has the read-only permissions "
            "in references/ram-policies.md")
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        raise c.ObsError(f"unexpected non-JSON response from cms {action}: {out[:500]}")
    if stable is None:
        stable = int(params.get("to") or 0) <= time.time() - c.CACHE_STABLE_AGE
    c.cache_put(cache_key, data, stable=stable)
    return data


def run_query(cfg, query, from_ts, to_ts, timeout=120):
    """Run one read-only SPL query against the bound workspace."""
    if not getattr(cfg, "workspace", None):
        raise c.ObsError(
            "loongsuit mode needs a CMS 2.0 workspace: pass --workspace "
            "(the workspace name GetEntityStoreData queries)")
    return run_cms(cfg, "get-entity-store-data", {
        "workspace": cfg.workspace,
        "query": guard_spl(query),
        "from": int(from_ts),
        "to": int(to_ts),
    }, timeout=timeout)


def list_workspaces(cfg, workspace_names=None, timeout=60):
    """Read-only workspace listing; used by preflight to verify that a bound
    --workspace actually exists in the region."""
    params = {"biz-region": cfg.region, "max-results": 50}
    if workspace_names:
        params["workspace-name-list"] = list(workspace_names)
    data = run_cms(cfg, "list-workspaces", params, timeout=timeout)
    return data.get("workspaces") or []


def search_spans(cfg, f, t, where="", project=SPAN_FIELDS, sort=None,
                 max_rows=None, timeout=120):
    """Page through one filtered span query; returns (rows, truncated)."""
    cap = max_rows or SPAN_PAGE * 20
    rows, offset, truncated = [], 0, False
    while offset < cap:
        count = min(SPAN_PAGE, cap - offset)
        data = run_query(cfg, build_query(where=where, project=project, sort=sort,
                                          offset=offset, count=count), f, t,
                         timeout=timeout)
        batch = rows_from_response(data)
        rows.extend(batch)
        if len(batch) < count:
            break
        offset += len(batch)
    else:
        truncated = True
    return rows, truncated


def _span_error(row):
    """Best-effort span error verdict: OTel statusCode first, then the
    attributes (error.type/message, finish_reasons, otel.status_code)."""
    if c.to_int(row.get("statusCode")) == STATUS_ERROR:
        return True, row.get("statusMessage") or None
    tags = c.parse_json_field(row, "attributes")
    if tags.get("error.type") or tags.get("error.message"):
        return True, tags.get("error.message") or tags.get("error.type")
    if '"error"' in (tags.get("gen_ai.response.finish_reasons") or ""):
        return True, "finish_reasons contains error"
    if (tags.get("otel.status_code") or "").upper() == "ERROR":
        return True, tags.get("otel.status_description") or None
    return False, None


def cms_span_to_row(row, trace_id=None):
    """Normalize one CMS span into the shared span-row shape.

    GetEntityStoreData already returns these field names, so this is mostly a
    pass-through; it only guarantees the ns string forms downstream expects and
    derives the error verdict."""
    error, status_message = _span_error(row)
    # downstream (trace_chain / decision_evidence) decides errors solely from
    # statusCode == "2", so the three-tier verdict has to be folded into it;
    # the raw OTel value stays available as status_raw for transparency
    return {
        "traceId": trace_id or row.get("traceId"),
        "spanId": row.get("spanId"),
        "parentSpanId": row.get("parentSpanId") or "",
        "spanName": row.get("spanName"),
        "serviceName": row.get("serviceName"),
        "startTime": str(c.to_int(row.get("startTime"))),
        "duration": str(c.to_int(row.get("duration"))),
        "statusCode": "2" if error else "0",
        "status_raw": str(c.to_int(row.get("statusCode"))),
        "statusMessage": status_message or row.get("statusMessage"),
        "attributes": row.get("attributes") or "{}",
        "resources": row.get("resources") or "{}",
        "error": error,
    }


def _where_from_filters(tags=None, service_name=None, is_error=None):
    """Combine the narrowing filters into one SPL where clause."""
    preds = []
    for key, value in tags or []:
        preds.append(f"{attr(key)} = {spl_literal(value)}")
    if service_name:
        preds.append(f"serviceName = {spl_literal(service_name)}")
    if is_error:
        preds.append(status_error_pred())
    return " and ".join(preds)


def _aggregate_span(traces, row):
    """Fold one span row into the per-trace aggregate."""
    tid = row.get("traceId")
    if not tid:
        return
    start_ns = c.to_int(row.get("startTime"))
    dur_ns = c.to_int(row.get("duration"))
    start_ms, end_ms = start_ns // 1_000_000, (start_ns + dur_ns) // 1_000_000
    d = traces.get(tid)
    if d is None:
        traces[tid] = {"trace_id": tid, "start_ms": start_ms, "end_ms": end_ms,
                       "spans_seen": 1,
                       "ops": {row.get("spanName") or ""},
                       "services": {row.get("serviceName") or ""}}
        traces[tid]["ops"].discard("")
        traces[tid]["services"].discard("")
        return
    d["start_ms"] = min(d["start_ms"], start_ms)
    d["end_ms"] = max(d["end_ms"], end_ms)
    d["spans_seen"] += 1
    if row.get("spanName"):
        d["ops"].add(row["spanName"])
    if row.get("serviceName"):
        d["services"].add(row["serviceName"])


def search_traces(cfg, f, t, tags=None, service_name=None, is_error=None,
                  max_traces=DEFAULT_MAX_TRACES):
    """Enumerate traces, aggregated per traceId.

    f/t: unix seconds. tags: [(attribute key, value)] filters. Returns
    (traces, truncated); each trace = {trace_id, start_ms, end_ms, spans_seen,
    ops[], services[]} sorted by start_ms."""
    service_name = service_name if service_name is not None else cfg.service_name
    where = _where_from_filters(tags, service_name, is_error)
    project = ("traceId", "spanId", "spanName", "serviceName", "startTime",
               "duration")
    traces = {}
    truncated = False
    offset = 0
    while True:
        data = run_query(cfg, build_query(where=where, project=project,
                                          sort="startTime", offset=offset,
                                          count=SPAN_PAGE), f, t)
        batch = rows_from_response(data)
        for row in batch:
            _aggregate_span(traces, row)
        if len(traces) >= max_traces:
            truncated = True
            break
        if len(batch) < SPAN_PAGE:
            break
        offset += len(batch)
    out = sorted(traces.values(), key=lambda d: d["start_ms"])[:max_traces]
    for d in out:
        d["ops"] = sorted(d["ops"])
        d["services"] = sorted(d["services"])
    return out, truncated


def search_agent_traces(cfg, f, t, max_traces=DEFAULT_MAX_TRACES):
    """Enumerate GenAI traces for the discovery stages.

    ENTRY is the entry-point marker, but an app that instruments only the
    LLM/STEP/TOOL layers emits no ENTRY span and would be invisible to every
    discovery path while still being reachable by session id. So an empty ENTRY
    result retries on LLM spans, which every GenAI app emits.

    Returns (traces, truncated, fallback); fallback is None or "no-entry-span"."""
    traces, truncated = search_traces(cfg, f, t,
                                      tags=[("gen_ai.span.kind", ENTRY_KIND)],
                                      max_traces=max_traces)
    if traces:
        return traces, truncated, None
    traces, truncated = search_traces(cfg, f, t,
                                      tags=[("gen_ai.span.kind", LLM_KIND)],
                                      max_traces=max_traces)
    return traces, truncated, "no-entry-span" if traces else None


def fetch_traces_spans(cfg, traces, f, t):
    """Fetch full span details for the given traces.

    traces: search_traces() result dicts or plain trace-id strings. Returns
    span rows in the shared shape (see cms_span_to_row). Ids are queried in
    TRACE_BATCH-sized `traceId in (...)` groups; rows are deduplicated by
    (traceId, spanId)."""
    if not traces:
        return []
    if isinstance(traces[0], dict):
        trace_ids = [tr["trace_id"] for tr in traces]
    else:
        trace_ids = list(traces)
    rows, seen = [], set()
    for i in range(0, len(trace_ids), TRACE_BATCH):
        batch = trace_ids[i:i + TRACE_BATCH]
        ids = ", ".join(spl_literal(x) for x in batch)
        where = f"traceId in ({ids})"
        got, _ = search_spans(cfg, f, t, where=where, project=SPAN_FIELDS,
                              sort="startTime")
        for row in got:
            out = cms_span_to_row(row)
            key = (out["traceId"], out["spanId"])
            if key not in seen:
                seen.add(key)
                rows.append(out)
    return rows
