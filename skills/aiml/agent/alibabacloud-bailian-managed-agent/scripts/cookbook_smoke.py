#!/usr/bin/env python3
"""Opt-in live cookbook smoke tests. Creates only temporary synthetic resources.

Requires httpx. No credentials are loaded until --execute is provided.
The output ledger contains IDs, not credentials. Automatic cleanup only touches
IDs created in this run; archive-only resources retain historical records.
"""
import argparse
import os, json, time, uuid, collections, struct, zlib
from pathlib import Path
import httpx
from user_agent import create_user_agent

OUT = BASE = http = ledger_path = None
ledger = {}


def save_ledger():
    ledger_path.write_text(json.dumps(ledger, indent=2))


def assistant_text(events):
    return "\n".join(
        b.get("text", "")
        for e in events
        if e.get("type") == "message"
        and e.get("role") == "assistant"
        and not (e.get("thread_id") or "").startswith("sthr_")
        for b in e.get("content", [])
        if b.get("type") == "text"
    )


def log(label, **kw):
    rec = {"label": label, **kw}
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    with (OUT / "live-results.jsonl").open("a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def req(method, path, body=None, files=None, allowed=()):
    r = http.request(method, BASE + path, json=body, files=files)
    with (OUT / "requests.jsonl").open("a") as f:
        f.write(
            json.dumps(
                {
                    "method": method,
                    "path": path,
                    "status": r.status_code,
                    "request_id": r.headers.get("x-request-id"),
                }
            )
            + "\n"
        )
    try:
        d = r.json()
    except ValueError:
        d = {}
    if r.is_error:
        er = d.get("error", d)
        log(
            "http_error",
            method=method,
            path=path,
            status=r.status_code,
            error=er,
            request_id=r.headers.get("x-request-id"),
        )
        if r.status_code not in allowed:
            r.raise_for_status()
    return d


def create(kind, body, key=None):
    d = req("POST", "/" + kind, body)
    rid = d["id"]
    ledger.setdefault(kind, []).append(rid)
    if key:
        ledger[key] = rid
    ledger_path.write_text(json.dumps(ledger, indent=2))
    log("created", kind=kind, id=rid)
    return d


def message(text):
    return {
        "role": "user",
        "type": "message",
        "content": [{"type": "text", "text": text}],
    }


def history(sid):
    events = []
    page = None
    seen = set()
    while True:
        url = f"/sessions/{sid}/events?" + str(
            httpx.QueryParams(
                {"limit": 100, "order": "asc", **({"page": page} if page else {})}
            )
        )
        d = req("GET", url)
        events += d.get("data", [])
        page = d.get("next_page")
        if not page:
            break
        if page in seen:
            raise RuntimeError("repeated cursor")
        seen.add(page)
    return events


def list_items(path, **params):
    """Read every page without dropping a resource scope/filter."""
    items, page, seen = [], None, set()
    while True:
        query = httpx.QueryParams(
            {"limit": 100, **params, **({"page": page} if page else {})}
        )
        data = req("GET", path + "?" + str(query))
        items.extend(data.get("data", []))
        page = data.get("next_page")
        if not page:
            return items
        if page in seen:
            raise RuntimeError("repeated resource cursor")
        seen.add(page)


def terminal_state(events):
    """Only a new terminal status can settle the submitted turn."""
    for event in reversed(events):
        if event.get("type") != "session_status":
            continue
        for block in event.get("content", []):
            state = block.get("data", {})
            status = state.get("session_status")
            reason = (state.get("stop_reason") or {}).get("type")
            if status == "terminated" or (status == "idle" and reason):
                return state
            if status:
                return None
    return None


def assert_end_turn(events):
    state = terminal_state(events)
    assert state and state.get("session_status") == "idle", state
    assert (state.get("stop_reason") or {}).get("type") == "end_turn", state


def tool_outputs(events):
    return [
        event for event in events
        if event.get("type") in ("tool_call_output", "mcp_call_output")
    ]


def assert_tool_success(events, output_contains=None):
    outputs = tool_outputs(events)
    assert outputs, "No tool output; an assistant claim alone is insufficient"
    assert not any(event.get("is_error") for event in outputs), "Tool failed"
    if output_contains:
        assert output_contains in json.dumps(outputs, ensure_ascii=False), outputs


def inspect_run(label, sid, events=None):
    evs = history(sid) if events is None else events
    (OUT / (label + "-events.json")).write_text(
        json.dumps(evs, ensure_ascii=False, indent=2)
    )
    texts = [
        b.get("text", "")
        for e in evs
        if e.get("type") == "message" and e.get("role") == "assistant"
        for b in e.get("content", [])
        if b.get("type") == "text"
    ]
    tools = [
        b.get("data", {})
        for e in evs
        if e.get("type") in ("tool_call", "mcp_call", "tool_approval_request", "error")
        for b in e.get("content", [])
        if b.get("type") == "data"
    ]
    log(
        label,
        session=sid,
        types=dict(collections.Counter(e.get("type") for e in evs)),
        text="\n".join(texts)[-2500:],
        tools=tools[:12],
    )
    return evs


def run(sid, text=None, inputs=None, timeout=210):
    old_ids = {e.get("id") for e in history(sid)}
    req("POST", f"/sessions/{sid}/events", {"input": inputs or [message(text)]})
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        info = req("GET", f"/sessions/{sid}")
        if info.get("status") in ("idle", "terminated"):
            evs = history(sid)
            fresh = [e for e in evs if e.get("id") not in old_ids]
            state = terminal_state(fresh)
            # A fresh running event does not make an old cached end_turn current.
            if state:
                reason = state.get("stop_reason") or {}
                if state.get("session_status") == "terminated" or reason.get("type") not in ("end_turn", "requires_action"):
                    raise RuntimeError("abnormal turn: " + str(state))
                return info, fresh
        time.sleep(2)
    raise TimeoutError(sid)


def session(label, agent=None, **kw):
    return create(
        "sessions",
        {
            "agent": agent or ledger["main_agent"],
            "environment_id": ledger["environment"],
            "title": "skill-audit-" + label,
            **kw,
        },
    )["id"]


def setup():
    env = create(
        "environments",
        {
            "name": "skill-audit-" + uuid.uuid4().hex[:8],
            "config": {
                "type": "cloud",
                "packages": {"pip": ["humanize"]},
                "networking": {"type": "unrestricted"},
            },
        },
        "environment",
    )
    agent = create(
        "agents",
        {
            "name": "skill-audit-" + uuid.uuid4().hex[:8],
            "model": {"id": "qwen3.8-max", "enable_thinking": True},
            "system": "You are a concise test assistant. Follow exact tool-use instructions. Never inspect or output credentials. For web tasks prefer built-in web_search and web_fetch. Do only the requested small task.",
            "tools": [
                {
                    "type": "builtin_toolkit",
                    "default_config": {"enabled": False},
                    "configs": [
                        {"name": n, "enabled": True}
                        for n in [
                            "bash",
                            "read",
                            "write",
                            "edit",
                            "glob",
                            "grep",
                            "web_search",
                            "web_fetch",
                        ]
                    ],
                }
            ],
        },
        "main_agent",
    )
    log("agent_readback", tools=req("GET", "/agents/" + agent["id"]).get("tools"))
    store = create(
        "memory_stores",
        {
            "name": "skill-audit-" + uuid.uuid4().hex[:8],
            "description": "Temporary synthetic audit notes",
        },
        "memory",
    )
    mem = req(
        "POST",
        f"/memory_stores/{store['id']}/memories",
        {
            "path": "/notes/handoff.md",
            "content": "Project code is ORCHID-73. Next task: verify exports.",
        },
    )
    ledger["memory_item"] = mem["id"]
    ledger_path.write_text(json.dumps(ledger, indent=2))
    log("memory_created", id=mem["id"], keys=list(mem))


def resource_test():
    for ext in ["csv", "txt"]:
        r = http.post(
            BASE + "/files",
            files={
                "file": (
                    "audit." + ext,
                    b"region,amount\nEast,100\nEast,50\nWest,200\n",
                    "text/plain",
                )
            },
        )
        d = r.json()
        log("upload_" + ext, status=r.status_code, id=d.get("id"), error=d.get("error"))
        if r.is_success:
            ledger.setdefault("files", []).append(d["id"])
            ledger_path.write_text(json.dumps(ledger, indent=2))
            if ext == "txt":
                fid = d["id"]
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        f = req("GET", "/files/" + fid)
        if f["status"] == "available":
            break
        if f["status"] in ("rejected", "type_rejected"):
            raise RuntimeError(f["status"])
        time.sleep(2)
    else:
        raise TimeoutError("file review")
    sid = session(
        "files",
        resources=[
            {"type": "file", "file_id": fid, "mount_path": "/uploads/audit.txt"}
        ],
    )
    ledger["resource_session"] = sid
    ledger_path.write_text(json.dumps(ledger, indent=2))
    info, evs = run(
        sid,
        "Use bash to import humanize, read /mnt/session/uploads/audit.txt and sum the amount column. Write exactly the total to /mnt/session/outputs/total.txt. Report total and humanize version. Do not use web tools.",
    )
    inspect_run("file-analysis", sid, evs)
    assert_end_turn(evs)
    assert_tool_success(evs)
    artifact_deadline = time.monotonic() + 60
    while True:
        arts = list_items("/files", scope_type="session", scope_id=sid)
        matches = [x for x in arts if x.get("filename") == "total.txt" and x.get("downloadable")]
        if matches or time.monotonic() >= artifact_deadline:
            break
        time.sleep(2)
    log(
        "artifacts",
        files=[
            {k: x.get(k) for k in ("id", "filename", "downloadable", "status")}
            for x in arts
        ],
    )
    assert len(matches) == 1, "Expected exactly one downloadable total.txt"
    r = http.get(BASE + "/files/" + matches[0]["id"] + "/content")
    log("artifact_download", status=r.status_code, body=r.text[:200])
    r.raise_for_status()
    assert r.text.strip() == "350"
    # Dynamic add/read/remove. Metadata visibility alone isn't runtime readiness.
    mount = req(
        "POST",
        f"/sessions/{sid}/resources",
        {"type": "file", "file_id": fid, "mount_path": "/uploads/late.txt"},
    )
    log("dynamic_mount", resource=mount)
    info, evs = run(
        sid,
        "Use bash to wait up to 60 seconds for /mnt/session/uploads/late.txt (test -f, sleep 2). Read it and report the sum. Do not use web tools.",
    )
    inspect_run("dynamic-read", sid, evs)
    assert_end_turn(evs)
    assert_tool_success(evs)
    # read may return the source rows for the model to sum; bash may return 350.
    evidence = json.dumps(tool_outputs(evs), ensure_ascii=False)
    assert "350" in evidence or all(row in evidence for row in ("East,100", "East,50", "West,200"))
    assert "350" in assistant_text(evs)
    req("DELETE", f"/sessions/{sid}/resources/{mount['id']}")
    remaining_ids = [x["id"] for x in list_items(f"/sessions/{sid}/resources")]
    log("dynamic_unmount", remaining_ids=remaining_ids)
    assert mount["id"] not in remaining_ids
    info, evs = run(
        sid,
        "Use bash to wait up to 60 seconds for /mnt/session/uploads/late.txt to disappear. Print MOUNT_REMOVED only if test ! -e succeeds, otherwise print STILL_PRESENT. Do not delete the file yourself. Report the tool result.",
    )
    inspect_run("dynamic-removed", sid, evs)
    assert_end_turn(evs)
    assert_tool_success(evs, "MOUNT_REMOVED")
    assert "MOUNT_REMOVED" in assistant_text(evs)
    assert req("GET", "/files/" + fid)["status"] == "available"


def memory_test():
    resource = {
        "type": "memory_store",
        "memory_store_id": ledger["memory"],
        "access": "read_write",
        "instructions": "Read and update /notes/handoff.md using file tools, never bash. This is synthetic work memory.",
    }
    sid = session("memory-writer", resources=[resource])
    log("memory_mount", resources=req("GET", f"/sessions/{sid}/resources"))
    info, evs = run(
        sid,
        "Read the mounted memory note /notes/handoff.md using read. Report project code, then use edit or write to append a new line: Verified total is 350. Use the actual memory mount path from your instructions. Do not use bash or web.",
    )
    inspect_run("memory-write", sid, evs)
    assert_end_turn(evs)
    assert_tool_success(evs)
    memory = req("GET", f"/memory_stores/{ledger['memory']}/memories/{ledger['memory_item']}")
    assert "ORCHID-73" in memory.get("content", "") and "350" in memory.get("content", "")
    log(
        "memory_readback",
        memory=memory,
    )
    resource["access"] = "read_only"
    sid2 = session("memory-reader", resources=[resource])
    info, evs = run(
        sid2,
        "Use read to read /notes/handoff.md in the mounted memory store. State the project code and verified total recorded by the previous session. Do not guess, do not write, do not use bash or web.",
    )
    inspect_run("memory-cross-session", sid2, evs)
    assert_end_turn(evs)
    assert_tool_success(evs)
    text = assistant_text(evs)
    assert "ORCHID-73" in text and "350" in text
    versions = list_items(f"/memory_stores/{ledger['memory']}/memory_versions")
    log("memory_versions", count=len(versions))
    assert len(versions) >= 2, "Memory creation and edit should produce versions"


def web_test():
    sid = session("builtin-web")
    info, evs = run(
        sid,
        "Call built-in web_search once for Alibaba Cloud Managed Agents Memory Store documentation. Then call built-in web_fetch once for https://docs.agent.bailian.aliyun.com/zh/managed-agents/context/memory-store . State one documented mounting constraint and its source URL. No bash or MCP. Maximum two web tool calls.",
    )
    inspect_run("builtin-web", sid, evs)
    assert_end_turn(evs)
    assert_tool_success(evs)
    names = {
        b.get("data", {}).get("name")
        for e in evs
        if e.get("type") == "tool_call"
        for b in e.get("content", [])
    }
    assert {"web_search", "web_fetch"} <= names
    assert not any(
        e.get("is_error") for e in evs if e.get("type") == "tool_call_output"
    )


def web_team_test():
    """Exercise recipe 05's actual built-in worker/coordinator configuration."""
    worker = create(
        "agents",
        {
            "name": "skill-audit-web-worker-" + uuid.uuid4().hex[:6],
            "model": {"id": "qwen3.7-plus"},
            "tools": [{
                "type": "builtin_toolkit",
                "default_config": {"enabled": False},
                "configs": [{"name": name, "enabled": True} for name in ("web_search", "web_fetch")],
            }],
            "system": "You research one focused question. Use web_search once and web_fetch once, then return concise findings with source URLs, not full page text. No other web calls or tasks. Never inspect credentials.",
        },
    )
    coordinator = create(
        "agents",
        {
            "name": "skill-audit-web-coordinator-" + uuid.uuid4().hex[:6],
            "model": {"id": "qwen3.8-max"},
            "multiagent": {
                "type": "coordinator",
                "agents": [{"type": "agent", "id": worker["id"], "version": worker["version"]}],
            },
            "system": "Delegate the user's research to exactly one instance of your search worker using create_agent, then wait_for_agents. The worker has built-in web_search and web_fetch; you have no web tools. Do not research or answer from your own knowledge. After the worker finishes, summarize its finding and source URL. Do not spawn further workers.",
        },
    )
    sid = session("web-team", agent=coordinator["id"])
    _, events = run(
        sid,
        "Have your worker call web_search once for Alibaba Cloud Managed Agents Memory Store documentation, then web_fetch once for https://help.aliyun.com/zh/model-studio/managed-agents-memory-store . Determine when a Memory Store must be attached to a Session. Cite the source URL. One worker, at most two web tool calls in total.",
        timeout=300,
    )
    inspect_run("builtin-web-team", sid, events)
    assert_end_turn(events)
    assert_tool_success(events)
    assert any(e.get("type") == "thread_created" for e in events), "No delegation evidence"
    calls = [
        {"thread_id": e.get("thread_id"), "name": b.get("data", {}).get("name")}
        for e in events if e.get("type") == "tool_call"
        for b in e.get("content", []) if b.get("type") == "data"
    ]
    web_calls = [x for x in calls if x["name"] in ("web_search", "web_fetch")]
    assert {x["name"] for x in web_calls} == {"web_search", "web_fetch"}
    assert all((x["thread_id"] or "").startswith("sthr_") for x in web_calls), web_calls
    assert not any(e.get("type") == "mcp_call" for e in events)
    model_calls = [
        {"thread_id": e.get("thread_id"), **b.get("data", {})}
        for e in events if e.get("type") == "model_request_end"
        for b in e.get("content", []) if b.get("type") == "data"
    ]
    log("web_team_evidence", web_calls=web_calls, model_calls=model_calls,
        threads=list_items(f"/sessions/{sid}/threads"))
    assert "http" in assistant_text(events), "Missing cited source"


def delta_test():
    sid = session("delta")
    frames = []
    pending = {}
    complete = {}
    started = {}
    seen_status = []
    with http.stream(
        "GET",
        BASE + f"/sessions/{sid}/events/stream",
        params=[("event_deltas[]", "message"), ("event_deltas[]", "reasoning")],
        headers={"Accept": "text/event-stream"},
        timeout=httpx.Timeout(210, read=45),
    ) as r:
        r.raise_for_status()
        req(
            "POST",
            f"/sessions/{sid}/events",
            {
                "input": [
                    message(
                        "Compute 17 * 19 and explain in three short sentences. No tools."
                    )
                ]
            },
        )
        data = []
        deadline = time.monotonic() + 180
        for line in r.iter_lines():
            if time.monotonic() > deadline:
                raise TimeoutError("delta business deadline")
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
            elif line == "" and data:
                raw = "\n".join(data)
                data = []
                if raw == "[DONE]":
                    break
                ev = json.loads(raw)
                frames.append(ev)
                typ = ev.get("type")
                if typ == "event_start":
                    started[ev["event"]["id"]] = ev["event"].get("type")
                if typ == "event_delta":
                    d = ev.get("delta", {})
                    content = d.get("content", {})
                    key = (ev["event_id"], d.get("index", 0))
                    if content.get("type") == "text":
                        pending[key] = pending.get(key, "") + content.get("text", "")
                if typ == "message" and ev.get("role") == "assistant":
                    complete[ev["id"]] = "".join(
                        b.get("text", "")
                        for b in ev.get("content", [])
                        if b.get("type") == "text"
                    )
                if typ == "session_status":
                    for b in ev.get("content", []):
                        state = b.get("data", {})
                        seen_status.append(state)
                        if state.get("session_status") == "terminated" or (
                            state.get("session_status") == "idle" and
                            (state.get("stop_reason") or {}).get("type")
                        ):
                            break
                    else:
                        continue
                    break
    (OUT / "delta-frames.json").write_text(
        json.dumps(frames, ensure_ascii=False, indent=2)
    )
    comparisons = {
        eid: "".join(v for (i, n), v in sorted(pending.items()) if i == eid) == text
        for eid, text in complete.items()
    }
    log(
        "delta",
        session=sid,
        types=dict(collections.Counter(x.get("type") for x in frames)),
        start_types=list(started.values()),
        delta_matches_completed=comparisons,
        statuses=seen_status,
    )
    assert complete and all(comparisons.values())
    assert_end_turn(frames)
    assert any(e.get("type") == "event_delta" for e in frames)
    assert "reasoning" in started.values()
    assert any(e.get("type") == "reasoning" for e in frames)
    assert "323" in assistant_text(frames)


def iter_sse_events(response, deadline):
    data = []
    for line in response.iter_lines():
        if time.monotonic() > deadline:
            raise TimeoutError("SSE total deadline")
        if line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
        elif line == "" and data:
            raw = "\n".join(data)
            data = []
            if raw == "[DONE]":
                return
            yield json.loads(raw)


def session_stream(sid):
    return http.stream(
        "GET", BASE + f"/sessions/{sid}/events/stream",
        params=[("event_deltas[]", "message"), ("event_deltas[]", "reasoning")],
        headers={"Accept": "text/event-stream"},
        timeout=httpx.Timeout(180, read=30),
    )


def recovery_test():
    """Drop SSE after a delta; reconnect and restore without resubmission."""
    sid = session("client-recovery")
    deadline = time.monotonic() + 180
    first = []
    with session_stream(sid) as response:
        response.raise_for_status()
        req("POST", f"/sessions/{sid}/events", {"input": [message(
            "First say CLIENT_STARTED. Then call bash exactly once to run: sleep 3; printf CLIENT_TOOL_OK. Finally explain 17 times 19 in three sentences and finish with CLIENT_DONE_323. No web calls."
        )]})
        for event in iter_sse_events(response, deadline):
            first.append(event)
            if event.get("type") == "event_delta":
                break
    assert any(e.get("type") == "event_delta" for e in first), "No partial answer before disconnect"
    live = []
    with session_stream(sid) as response:
        response.raise_for_status()
        snapshot = history(sid)
        if not terminal_state(snapshot):
            for event in iter_sse_events(response, deadline):
                live.append(event)
                if terminal_state([event]):
                    break
    final = history(sid)
    inspect_run("client-recovered", sid, final)
    assert_end_turn(final)
    assert_tool_success(final, "CLIENT_TOOL_OK")
    assert "CLIENT_DONE_323" in assistant_text(final)
    user_messages = [e for e in final if e.get("type") == "message" and e.get("role") == "user"]
    assert len(user_messages) == 1, "Business input was duplicated"
    recovered = {}
    for event in first + snapshot + live + final:
        if event.get("id") and event.get("type") == "message" and event.get("role") == "assistant":
            recovered[event["id"]] = event
    expected = {e["id"]: e for e in final if e.get("type") == "message" and e.get("role") == "assistant"}
    assert recovered == expected
    for name, payload in [("client-before-disconnect", first), ("client-reconnect-snapshot", snapshot), ("client-reconnected-stream", live)]:
        (OUT / (name + ".json")).write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    log("client_recovery_evidence", submissions=1, user_messages=len(user_messages), answer_messages=len(expected),
        before_disconnect=dict(collections.Counter(e.get("type") for e in first)),
        after_reconnect=dict(collections.Counter(e.get("type") for e in live)), restored_equal_to_history=True)


def image_test():
    def chunk(t, d):
        return (
            struct.pack("!I", len(d))
            + t
            + d
            + struct.pack("!I", zlib.crc32(t + d) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack("!2I5B", 64, 64, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\0" + b"\xff\0\0" * 64) * 64))
        + chunk(b"IEND", b"")
    )
    f = req("POST", "/files", files={"file": ("audit-image.png", png, "image/png")})
    ledger.setdefault("files", []).append(f["id"])
    save_ledger()
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        status = req("GET", "/files/" + f["id"])["status"]
        if status == "available":
            break
        if status in ("rejected", "type_rejected"):
            raise RuntimeError(status)
        time.sleep(2)
    else:
        raise TimeoutError("image review")
    sid = session("image-file")
    info, evs = run(
        sid,
        inputs=[
            {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Identify the dominant color in the attached image. Answer just the color name. No tools.",
                    },
                    {"type": "image", "file_id": f["id"]},
                ],
            }
        ],
    )
    inspect_run("image-file", sid, evs)
    assert_end_turn(evs)
    assert assistant_text(evs).strip().lower().rstrip(".") == "red"


def approval_test():
    agent = create(
        "agents",
        {
            "name": "skill-audit-approval-" + uuid.uuid4().hex[:6],
            "model": {"id": "qwen3.8-max"},
            "system": "Follow the user exactly. Use bash when asked. Do not use web.",
            "tools": [
                {
                    "type": "builtin_toolkit",
                    "default_config": {"enabled": False},
                    "configs": [
                        {
                            "name": "bash",
                            "enabled": True,
                            "permission_policy": {"type": "always_ask"},
                        }
                    ],
                }
            ],
        },
    )
    sid = session("approval", agent=agent["id"])
    info, evs = run(
        sid,
        "Use bash once to run exactly: printf AUDIT_APPROVED. Then report its stdout.",
    )
    inspect_run("approval-pending", sid, evs)
    reason = info.get("stop_reason") or {}
    assert reason.get("type") == "requires_action"
    # Approve only the exact synthetic printf command requested by this test.
    calls = [
        b.get("data", {})
        for e in evs
        if e.get("type") == "tool_approval_request"
        for b in e.get("content", [])
    ]
    assert calls and all(
        c.get("name") == "bash"
        and json.loads(c["arguments"]).get("command") == "printf AUDIT_APPROVED"
        for c in calls
    )
    replies = [
        {
            "type": "tool_approval_response",
            "role": "user",
            "content": [
                {
                    "type": "data",
                    "data": {
                        "batch_id": reason["pending_batch_id"],
                        "call_id": cid,
                        "result": "allow",
                    },
                }
            ],
        }
        for cid in reason["pending_call_ids"]
    ]
    info, evs = run(sid, inputs=replies)
    inspect_run("approval-completed", sid, evs)
    assert (info.get("stop_reason") or {}).get("type") == "end_turn"


def multiagent_test():
    member = create(
        "agents",
        {
            "name": "skill-audit-math-" + uuid.uuid4().hex[:6],
            "description": "A calculator member. Returns the integer result of simple arithmetic.",
            "model": {"id": "qwen3.7-plus"},
            "system": "Compute the requested simple arithmetic and return just the integer. No tools needed.",
        },
    )
    leader = create(
        "agents",
        {
            "name": "skill-audit-coordinator-" + uuid.uuid4().hex[:6],
            "model": {"id": "qwen3.8-max"},
            "system": "You are a coordinator. Always delegate arithmetic to your math member using the available orchestration tools. Do not calculate it yourself. After its reply, answer COORDINATOR_RESULT=<value>.",
            "multiagent": {
                "type": "coordinator",
                "agents": [
                    {"type": "self"},
                    {"type": "agent", "id": member["id"], "version": member["version"]},
                ],
            },
        },
    )
    sid = session("multiagent", agent=leader["id"])
    info, evs = run(
        sid,
        "Delegate computing 17 times 19 to the math member and summarize its answer.",
    )
    inspect_run("multiagent", sid, evs)
    log("multiagent_threads", threads=req("GET", f"/sessions/{sid}/threads"))
    assert any(e.get("type") == "thread_created" for e in evs)
    assert "323" in assistant_text(evs)


def deployment_test():
    dep = create(
        "deployments",
        {
            "name": "skill-audit-manual-" + uuid.uuid4().hex[:6],
            "agent": {
                "id": ledger["main_agent"],
                "version": req("GET", "/agents/" + ledger["main_agent"])["version"],
            },
            "environment_id": ledger["environment"],
            "initial_events": [message("Reply with AUDIT_DEPLOYMENT_OK. No tools.")],
        },
    )
    info = req("POST", f"/deployments/{dep['id']}/run", {})
    log("deployment_trigger", response=info)
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        runs = req("GET", f"/deployments/{dep['id']}/runs").get("data", [])
        for r in runs:
            sid = r.get("session_id")
            if sid and sid not in ledger.get("sessions", []):
                ledger.setdefault("sessions", []).append(sid)
                ledger_path.write_text(json.dumps(ledger, indent=2))
            if r.get("status") in ("succeeded", "failed"):
                log("deployment_result", run=req("GET", "/deployment_runs/" + r["id"]))
                if sid:
                    inspect_run("deployment-session", sid)
                assert r["status"] == "succeeded"
                return
        time.sleep(2)
    raise TimeoutError("deployment")


def vault_test():
    v = create("vaults", {"display_name": "skill-audit-" + uuid.uuid4().hex[:6]})
    d = req(
        "POST",
        f"/vaults/{v['id']}/credentials",
        {
            "display_name": "Synthetic test value",
            "auth": {
                "type": "environment_variable",
                "secret_name": "AUDIT_SYNTHETIC_TOKEN",
                "secret_value": "not-a-real-secret",
                "networking": {"allowed_hosts": ["docs.agent.bailian.aliyun.com"]},
            },
        },
    )
    log("vault_credential", id=d.get("id"), keys=list(d))
    sid = session("vault", vault_ids=[v["id"]])
    info, evs = run(
        sid,
        "Use bash to check whether os.environ.get('AUDIT_SYNTHETIC_TOKEN','').startswith('BMA_SECRET_PLACEHOLDER_') in Python. Print only True or False. Never print the variable value or make a network request.",
    )
    inspect_run("vault-placeholder", sid, evs)
    assert assistant_text(evs).strip() == "True"


def cleanup():
    failures = []
    # No workspace-wide deletes. Every ID comes from this run's create responses.
    for kind in (
        "deployments",
        "sessions",
        "vaults",
        "agents",
        "environments",
        "files",
        "memory_stores",
    ):
        for rid in reversed(ledger.get(kind, [])):
            try:
                if kind == "vaults":
                    page = None
                    while True:
                        query = "?" + str(
                            httpx.QueryParams(
                                {"limit": 100, **({"page": page} if page else {})}
                            )
                        )
                        data = req("GET", f"/vaults/{rid}/credentials" + query)
                        for item in data.get("data", []):
                            req("DELETE", f"/vaults/{rid}/credentials/{item['id']}")
                        page = data.get("next_page")
                        if not page:
                            break
                archive = kind in ("agents", "deployments", "memory_stores")
                path = f"/{kind}/{rid}" + ("/archive" if archive else "")
                req(
                    "POST" if archive else "DELETE",
                    path,
                    {} if archive else None,
                    allowed=(404,),
                )
                log(
                    "cleanup",
                    kind=kind,
                    id=rid,
                    action="archive" if archive else "delete",
                )
            except Exception as exc:
                failures.append({"kind": kind, "id": rid, "error": type(exc).__name__})
    ledger["cleanup_failures"] = failures
    save_ledger()
    return failures


SCENARIOS = {
    "files": resource_test,
    "memory": memory_test,
    "web": web_test,
    "web_team": web_team_test,
    "delta": delta_test,
    "recovery": recovery_test,
    "image": image_test,
    "approval": approval_test,
    "multiagent": multiagent_test,
    "deployment": deployment_test,
    "vault": vault_test,
}


def main():
    global OUT, BASE, http, ledger_path, ledger
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS)
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run live mutations and model/tool calls; charges may apply",
    )
    parser.add_argument(
        "--bl-config",
        type=Path,
        help="Explicitly use this bl JSON profile's api_key/base_url as a pair",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp") / ("ma-cookbook-" + uuid.uuid4().hex[:10]),
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Retry cleanup from the output ledger",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            {
                "scenarios": args.scenarios,
                "resources": "temporary agents, environment, memory store, sessions, files; optional vault/deployment",
                "schedule": "none; manual run only",
                "cleanup": "automatic; archive-only resources retain history",
                "output": str(args.output),
            },
            ensure_ascii=False,
        )
    )
    if not args.execute:
        return 0
    if args.bl_config:
        cfg = json.loads(args.bl_config.expanduser().read_text())
        key, endpoint = cfg["api_key"], cfg["base_url"]
    else:
        key = os.environ["DASHSCOPE_API_KEY"]
        endpoint = os.environ.get("CMA_BASE") or (
            "https://"
            + os.environ["BAILIAN_WORKSPACE_ID"]
            + ".cn-beijing.maas.aliyuncs.com"
        )
    BASE = endpoint.rstrip("/")
    if not BASE.endswith("/api/v1/agentstudio"):
        BASE += "/api/v1/agentstudio"
    parsed = httpx.URL(BASE)
    if parsed.scheme != "https" or not parsed.host.endswith(".maas.aliyuncs.com"):
        raise ValueError("Use the authorized Alibaba Cloud workspace endpoint")
    OUT = args.output.expanduser().resolve()
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    ledger_path = OUT / "ledger.json"
    if args.cleanup_only:
        ledger = json.loads(ledger_path.read_text())
        if ledger.get("base_url") != BASE:
            raise ValueError("Cleanup endpoint must match the original run")
    else:
        if ledger_path.exists():
            raise ValueError(
                "Use a fresh output directory; existing ledger must not be overwritten"
            )
        ledger = {"base_url": BASE}
        save_ledger()
    http = httpx.Client(
        headers={"Authorization": "Bearer " + key, "User-Agent": create_user_agent()},
        timeout=30,
    )
    failures = []
    try:
        req(
            "GET", "/agents?limit=1"
        )  # Validate the exact key/endpoint pair before any mutation.
        if not args.cleanup_only:
            setup()
            for name in args.scenarios:
                try:
                    SCENARIOS[name]()
                    log("scenario_pass", scenario=name)
                except Exception as exc:
                    failures.append(name)
                    log(
                        "scenario_failed",
                        scenario=name,
                        error=type(exc).__name__ + ": " + str(exc),
                    )
    finally:
        failures.extend(x["id"] for x in cleanup())
        http.close()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
