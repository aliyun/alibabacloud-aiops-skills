# 09 · Working-memory handoff and built-in web research

Scenario: a research session writes verified project facts into working notes. A later session reads those notes to continue the work. Prefer built-in `web_search` / `web_fetch` when external information is needed.

**Test scope**: 2026-09-18, cn-beijing test workspace, REST, `qwen3.8-max`. Verified API memory creation → Session file-tool edits → API read-back → a new Session with a read-only mount, plus real calls to both web tools. Handoff and web research were tested separately; automatic saving of search results is not a platform guarantee.

## Choose the right memory product

| Need | Product and isolation |
| --- | --- |
| MA project notes, progress, cross-session handoff | **MA Memory Store**: a separate file tree mounted through Session `resources` |
| Personal preferences and personalized memory supplied with UserId | **Bailian Memory Library**: a separate product with different APIs |

`metadata.user_id` does not automatically isolate Memory Store contents. Sessions sharing a Store share its contents. For isolation, the application must allocate separate Stores and verify each business user's access.

## Run the example

Run from the repository root. The script previews its scope by default. `--execute` creates temporary resources, calls models/tools, then cleans up its own resources. Agent and Memory Store archival retains history.

```bash
python3 -m venv /tmp/ma-cookbook-env
/tmp/ma-cookbook-env/bin/pip install httpx
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py --scenarios memory web
# Use authorized local bl configuration; keys are not passed as arguments, printed, or saved in output.
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute --bl-config "$HOME/.bailian/config.json" \
  --scenarios memory web --output /tmp/ma-memory-web-check
```

Alternatively, omit `--bl-config` and inject `DASHSCOPE_API_KEY` with `BAILIAN_WORKSPACE_ID`, or a complete `CMA_BASE`. Configured `base_url` and `workspace_id` can be stale or inconsistent: the script pairs the selected configuration's API key with its `base_url` and performs a read-only authentication check first. Do not mix in a key from another environment.

Implementation: `setup`, `memory_test`, and `web_test` in [cookbook_smoke.py](../../scripts/cookbook_smoke.py). No SDK is required. Requests carry this skill's freshly generated per-invocation User-Agent; mutations are not automatically retried.

## Request sequence

1. `POST /memory_stores` with `{"name":"project-notes","description":"Work handoff"}`.
2. `POST /memory_stores/{id}/memories` with `{"path":"/notes/handoff.md","content":"Project code is ORCHID-73."}`. Save the returned Memory ID.
3. At Session creation, pass:

```json
{
  "agent": "<agent_id>",
  "environment_id": "<environment_id>",
  "resources": [{
    "type": "memory_store",
    "memory_store_id": "<memory_store_id>",
    "access": "read_write",
    "instructions": "Read the working notes and write back verified facts after completing the task. Use file tools, not bash."
  }]
}
```

4. Use `read` / `edit` / `write` at the platform-provided `/mnt/memory/<name>/notes/handoff.md`. Do not construct an arbitrary local directory; **bash cannot access the memory file tree**.
5. Read back `GET /memory_stores/{store_id}/memories/{memory_id}` to verify persistence.
6. Create another Session with the same Store and `access: "read_only"`, and ask it to read the updated notes.
7. Check history through `GET /memory_stores/{store_id}/memory_versions`. For concurrent edits, use the documented `precondition.content_sha256` conditional update; re-read and merge after a conflict.

Observed: the first session appended `Verified total is 350.`; the second read `ORCHID-73` and `350`. History contained the creation and edit versions.

**Do not reuse the dynamic file-mounting workflow**: Memory Stores attach at Session creation. Posting `type: memory_store` to an existing Session's `/resources` returned 400. In the tested workspace, `GET /sessions/{id}/resources` also omitted an effective memory mount. Verify the creation configuration, file-tool output, and Memory API read-back together; an empty resource list alone does not prove failure.

## Web configuration

Explicitly enable these tools in the same `builtin_toolkit`:

```json
{
  "type": "builtin_toolkit",
  "default_config": {"enabled": false},
  "configs": [
    {"name": "read", "enabled": true},
    {"name": "write", "enabled": true},
    {"name": "edit", "enabled": true},
    {"name": "glob", "enabled": true},
    {"name": "web_search", "enabled": true},
    {"name": "web_fetch", "enabled": true}
  ]
}
```

The test requested a search for Memory Store documentation and then retrieval of a specified official page. Events contained successful `web_search` and `web_fetch` tool calls; the final answer cited the creation-time mounting constraint and its source.

`websearch` / `webfetch` are informal names; configuration keys require underscores. Ordinary search and page retrieval do not need a search MCP. For browser clicks or forms, connect `browser_use` through an activated MCP service. Obtain service and tool names from the account's catalog; do not guess that `browser_use` is a built-in name or an MCP service code.

No browser MCP service code was available in this test workspace. **browser_use execution was not verified**; this routing guidance is not a tested browser cookbook.

## Sources and boundaries

- [Official Memory Store documentation](https://docs.agent.bailian.aliyun.com/zh/managed-agents/context/memory-store.md): mounting, access, versions, and the working-memory file tree.
- [Official built-in tool documentation](https://docs.agent.bailian.aliyun.com/zh/managed-agents/build-agent/tools.md): `web_search` / `web_fetch` and approval scope.
- Archiving a Memory Store is irreversible; it can no longer be written or attached to new sessions. Cleanup archives only resources created by this test.
