# 09 · Working-memory handoff across sessions

Scenario: a project session writes verified facts and progress into working notes. A later session reads those notes to continue the work without asking the user to repeat the project context.

**Test scope**: retested on 2026-10-09, cn-beijing, REST, `qwen3.8-max`, with the local environment-variable API key. Verified API memory creation → Session file-tool edits → API read-back → a new Session with a read-only mount. This recipe verifies explicit write-back; it does not test automatic post-session memory consolidation.

## Choose the right memory product

| Need | Product and isolation |
| --- | --- |
| MA project notes, progress, cross-session handoff | **MA Memory Store**: a separate file tree mounted through Session `resources` |
| Personal preferences and personalized memory supplied with UserId | **Bailian Memory Library**: a separate product with different APIs |

`metadata.user_id` does not automatically isolate Memory Store contents. Sessions sharing a Store share its contents. For isolation, the application must allocate separate Stores and verify each business user's access.

## Run the example

Use the [shared smoke-test setup](index.md#shared-smoke-test-setup), then run from the repository root:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py --scenarios memory
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute \
  --scenarios memory --output /tmp/ma-memory-check
```

Implementation: `setup` and `memory_test` in [cookbook_smoke.py](../../scripts/cookbook_smoke.py). The script verifies write-back and cross-session readback, then cleans up its temporary resources.

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
7. Check history through `GET /memory_stores/{store_id}/memory_versions`. For concurrent API edits, send `POST /memory_stores/{store_id}/memories/{memory_id}` with the hash returned by the preceding read in the conditional update body:

```json
{
  "content": "<updated notes>",
  "precondition": {
    "type": "content_sha256",
    "content_sha256": "<hash from the preceding read>"
  }
}
```

The `type` discriminator is required. In the 2026-10-09 additional check, the current hash allowed an update; reusing the old hash returned HTTP 409 with `memory_precondition_failed_error`, leaving the newer content intact. Re-read and merge after a conflict.

Observed: the first session appended `Verified total is 350.`; the second read `ORCHID-73` and `350`. History contained the creation and edit versions.

**Do not reuse the dynamic file-mounting workflow**: Memory Stores attach at Session creation. The 2026-09-18 negative test returned 400 when posting `type: memory_store` to an existing Session's `/resources`; that rejection was not retested on 2026-10-09. The latest run again found that `GET /sessions/{id}/resources` omitted an effective memory mount. Verify the creation configuration, file-tool output, and Memory API read-back together; an empty resource list alone does not prove failure.

## Configure file tools for working notes

Explicitly enable these tools in the same `builtin_toolkit`:

```json
{
  "type": "builtin_toolkit",
  "default_config": {"enabled": false},
  "configs": [
    {"name": "read", "enabled": true},
    {"name": "write", "enabled": true},
    {"name": "edit", "enabled": true},
    {"name": "glob", "enabled": true}
  ]
}
```

Keep the handoff instructions explicit: read the existing notes first, record verified facts and unfinished work after the task, and let the next Session consult the same Store. Configure the handoff consumer's mount as `read_only` even when its Agent has write tools.

In the 2026-10-09 additional write probe, the read-only consumer refused the request before issuing a write/edit call, and API read-back showed unchanged content. This verifies observed read-only behavior, but does not exercise a backend rejection of an attempted tool write; do not present it as that stronger access-control test.

## Sources and boundaries

- [Official Memory Store documentation](https://docs.agent.bailian.aliyun.com/zh/managed-agents/context/memory-store.md): mounting, access, versions, and the working-memory file tree.
- Archiving a Memory Store is irreversible; it can no longer be written or attached to new sessions. Cleanup archives only resources created by this test.
