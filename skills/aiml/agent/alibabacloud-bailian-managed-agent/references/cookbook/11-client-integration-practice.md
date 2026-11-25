# 11 · Building a conversation client: streaming and file interactions

Scenario: a developer embeds MA in an existing web or mobile product. After a user sends a question, the product shows progress and renders the answer incrementally. The user can add or withdraw files in the same conversation, and recover it after a connection drops.

**Test scope**: Delta/Thinking retested on **2026-10-23**, cn-beijing, REST, `qwen3.8-max` with `enable_thinking=true`, using the local bl profile's key and endpoint as a pair. **All 5 fresh Sessions received nonempty reasoning deltas**, matching their block snapshots, completed reasoning events, and Event List; see §4. This run observed `object=message/content` frames, while the [official SSE contract](https://help.aliyun.com/zh/model-studio/event-sse-stream) and [event-stream guide](https://docs.agent.bailian.aliyun.com/zh/managed-agents/sessions/event-stream), checked on the same date, still described `event_start/event_delta`. Treat this as dated workspace evidence, not proof of every deployment's schema.

**Earlier scope (2026-10-09)**: message delta assembly, reasoning start/final events, recovery after an intentional SSE disconnect without resubmitting input, and file add → read → remove → verify within an existing Session. File changes occurred between analysis turns. Recovery/files were not rerun on 2026-10-23. A complete browser application and file updates during an actively executing tool call were not tested.

## Run the protocol examples

Use the [shared smoke-test setup](index.md#shared-smoke-test-setup), then run from the repository root:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute \
  --scenarios delta recovery files --output /tmp/ma-client-check
```

For a focused Thinking-content check:

```bash
/tmp/ma-cookbook-env/bin/python scripts/cookbook_smoke.py \
  --execute --scenarios delta \
  --output /tmp/ma-thinking-check
```

Add `--bl-config "$HOME/.bailian/config.json"` to use that profile's key/endpoint pair, as in the 2026-10-23 retest. Use a fresh output directory for each run. Selecting only `delta` provisions a temporary no-tool Agent, a plain cloud Environment, and a Session; no Memory Store or files are needed.

`delta_test` establishes SSE before sending “Compute 17 * 19 and explain in three short sentences. No tools.” It recognizes both observed frame formats and compares **actual appended fragments** with completed content blocks, full events, and history, separately for answer and reasoning. Inspect `delta-frames.json`, `delta-history.json`, and `evidence.message` / `evidence.reasoning` in `live-results.jsonl`. The test requires nonempty reasoning deltas; start/completion alone cannot pass. A full snapshot must not hide a missing fragment. Fragment counts vary; nonempty text, content equality and `idle/end_turn` are the acceptance criteria.

`recovery_test` intentionally closes the first stream after a text delta, then subscribes again and reconciles history. It submits only once and verifies that all complete assistant messages are restored. Inspect `client_recovery_evidence`, `client-recovered-events.json`, `client-before-disconnect.json`, `client-reconnect-snapshot.json`, and `client-reconnected-stream.json`.

`resource_test` prepares a synthetic three-row input, verifies an initial result, then mounts the same data at a second path and removes that mount. Inspect `dynamic_mount`, `dynamic-read`, `dynamic_unmount`, and `dynamic-removed` for resource and tool evidence. The 2026-10-09 file rerun verified a downloaded result of `350`, resource-list removal, sandbox-path disappearance, and the source File remaining `available`. The upload endpoint rejected `.csv` in this workspace (HTTP 415); the same synthetic CSV text uploaded as `.txt` worked. This checks file access, not reconciliation of two different datasets. Select one scenario when validating a part independently.

## 1. Put the business backend between the UI and MA

```text
Web / mobile UI
  → authenticated business backend (conversation ownership, turn IDs)
    → MA Session + Event API
    ← MA SSE frames
  ← product events (answer updates, activity, turn state)
```

Keep the API key in the backend. Persist the business conversation's mapping to its `session_id`; reuse that Session for later turns. Agent and Environment provisioning belongs to application setup, as covered in [01](01-get-started-data-analysis-agent.md), rather than each send action.

Allocate a business `turn_id` when accepting a message. Keep separate records for the ordered assistant messages within that turn: an Agent may speak, call tools, and then speak again. One turn is not necessarily one message.

## 2. Subscribe before submitting the user input

The backend opens:

```text
GET /sessions/{id}/events/stream?event_deltas[]=message&event_deltas[]=reasoning
Accept: text/event-stream
```

Confirm the stream is established, then POST the user input through another connection. Sending first can miss a fast response or immediate error; SSE does not replay historical events. Do not let the stream occupy the only connection available for submission.

Locally echo the user's message immediately. The backend can report confirmed checkpoints such as connecting, submitted, and running while waiting for answer text. Flush the downstream stream and disable proxy response buffering. Keep connection, first-business-event, idle, and total-turn deadlines distinct; keepalive comments are not business progress.

Parse SSE by frames: ignore comment lines, accept both `data:` and `data: `, and combine multiple data lines before decoding JSON. For the 2026-10-23 format, dispatch on **`object` + `status` + `type`**: a content frame's `type=text` does not identify whether it belongs to an answer or reasoning. Resolve its `msg_id` against the parent message.

## 3. Assemble answer messages without duplicating them

| Observed 2026-10-23 frame | Backend handling | UI effect |
| --- | --- | --- |
| `object=message`, `status=in_progress`, `type=message/reasoning` | Register `id` → event type | Allocate a provisional answer or start Thinking |
| `object=content`, `type=text`, `delta=true` | Append `text` in arrival order to `(msg_id, index)` | Update the corresponding answer or Thinking block |
| `object=content`, `status=completed`, `delta=false` | Replace that block with the full `text` snapshot | Finalize the block without appending it again |
| `object=message`, `status=completed`, `type=message` | Replace that event's provisional content with full `content` | Settle the answer once; filter out user echoes |
| `object=message`, `status=completed`, `type=reasoning` | Replace the reasoning content if present and end the activity | Finish Thinking; the turn may still be running |

Minimal operation for the observed **content frames**, after registering the parent type and establishing ownership:

```python
buffers = {}

def apply_text_content(frame):
    if frame.get("object") != "content" or frame.get("type") != "text":
        return None
    key = (frame["msg_id"], frame["index"])
    if frame.get("delta") is True:
        buffers[key] = buffers.get(key, "") + frame.get("text", "")
    elif frame.get("delta") is False and frame.get("status") == "completed":
        buffers[key] = frame.get("text", "")
    return key
```

`index` identifies a **content block**, not a fragment sequence. Multiple fragments with the same pair must all be appended, even when their text is identical. For example, `"3"` and `"23"` at index 0 produce `"323"`; both the `delta=false` block snapshot and the completed Message replace provisional content instead of producing `"323323"`. A completed block alone does not end the reasoning activity or turn.

**Archived/documented envelope compatibility:** `event_start.event.id/type` registers the parent; `event_delta.event_id` + `delta.index` identifies the block, and `delta.content.text` is appended. The final full event still replaces the buffer. [normalize_delta_frame](../../scripts/cookbook_smoke.py) adapts the observed format to this envelope for verification; `content_completed` in that helper is a **local adapter label**, not an upstream event type. Do not assume the server always emits the archived envelope simply because current documentation shows it.

Route by the registered parent type so reasoning text never enters the answer buffer. Filter user-message echoes; only completed messages with `role: assistant` belong in the settled assistant transcript. Start frames may lack role or thread information: keep them provisional until ownership is established, and reconcile against the complete message. For MultiAgent output, use [04's thread separation](04-multi-agent-custom-proposals.md) before adding content to the primary answer.

The backend can expose its own small protocol, for example:

```json
{"type":"answer.updated","turn_id":"turn_1","event_id":"msg_1","block_index":0,"text":"323"}
```

This is an application-defined event, not a MA API field. Here `text` is the accumulated block snapshot, so the UI replaces that block on every update. Use stable event/block keys and a backend-assigned revision if downstream events may be replayed or reordered. A final message replacement must also remove any stale provisional blocks. Render model text safely; do not inject unsanitized HTML.

## 4. Separate thinking activity from turn completion

Thinking uses `reasoning` events and **provides actual text deltas**. The 2026-10-23 tests created Agents with `"model": {"id": "qwen3.8-max", "enable_thinking": true}`, verified that configuration by read-back, and created fresh Sessions. Subscribe to `event_deltas[]=reasoning` (and `message` for answers) before submitting input. If changing an existing Agent, create a new Session to use its updated snapshot.

Observed frame sequence below is schematic: IDs/text are illustrative, while field names match the live frames. `msg_id` ties the text to its reasoning parent; there was no `type=thinking_delta` frame.

```json
{"object":"message","status":"in_progress","role":"assistant","id":"msg_reasoning_example","type":"reasoning"}
{"object":"content","status":"in_progress","type":"text","msg_id":"msg_reasoning_example","index":0,"delta":true,"text":"…"}
{"object":"content","status":"completed","type":"text","msg_id":"msg_reasoning_example","index":0,"delta":false,"text":"…"}
{"object":"message","status":"completed","role":"assistant","id":"msg_reasoning_example","type":"reasoning","content":[{"type":"text","text":"…"}]}
```

Five consecutive verification Sessions used the same model, configuration, and arithmetic prompt:

| 2026-10-23 run | Nonempty reasoning fragments / characters | Answer fragments / characters | Result |
| --- | --- | --- | --- |
| 1 | 37 / 384 | 13 / 91 | All comparisons passed; `idle/end_turn` |
| 2 | 17 / 166 | 14 / 99 | All comparisons passed; `idle/end_turn` |
| 3 | 29 / 299 | 14 / 102 | All comparisons passed; `idle/end_turn` |
| 4 | 15 / 150 | 14 / 99 | All comparisons passed; `idle/end_turn` |
| 5 | 31 / 286 | 13 / 87 | All comparisons passed; `idle/end_turn` |

**5/5 passed**: both reasoning and answer fragments matched their block snapshots, completed events, and Event List exactly. Counts above are observed samples in one cn-beijing workspace. Keep Thinking separate from the answer and render the text actually received. For **capability verification**, require nonempty reasoning deltas plus content agreement; start/completion alone is insufficient. Test resources were cleaned up (Sessions/Environments deleted, Agents archived).

Read raw REST status from `content[].data`; the SDK may expose it as object properties. Map it to product state:

| Observed state | Product behavior |
| --- | --- |
| `running` | Keep the turn active; show answer or tool progress as events arrive |
| `idle` + `end_turn` | Mark this turn completed |
| `idle` + `requires_action` | Show an action-needed state; use [tutorial 06](../tutorials/06-tool-approval.md) for approvals |
| `idle` + `retries_exhausted` | Mark the turn failed and preserve the conversation |
| `terminated` | Stop loading and show the termination outcome |
| `error` | Read top-level `error.code` / `error.message`, retain diagnostic IDs, and reconcile Session state |

Neither HTTP 200, a complete assistant message, the end of a reasoning event, nor a closed SSE connection proves that the turn succeeded. Tool activity and multiple assistant messages can follow an earlier message. Keep any tool progress keyed by call ID and settle pending UI activities when the turn finishes or is interrupted.

## 5. Recover the conversation without submitting the task twice

For a page refresh, restore the backend's stored turn/messages first. If the backend still has its upstream connection, reattach the UI to that business stream instead of starting another MA turn.

If the upstream connection dropped, retain the Session ID and recover full messages through the paginated Event List. Establish a new live subscription and buffer incoming frames while reconciling history so completion during recovery is not lost. Upsert complete events by ID, scope them to the correct turn, and replace partial text with authoritative full messages. A resumed stream may contain only the suffix of an in-progress message; never assume it is a complete answer. Reconcile again after the turn reaches a terminal state.

Do not use `(event_id, index)` to deduplicate individual deltas, and do not resend the original user input merely because the connection closed. The upstream stream has no resumable delta cursor. If submission itself timed out, inspect history before deciding whether it is safe to submit again.

**Live recovery evidence (2026-10-09):** the test disconnected after the first answer delta and opened the replacement stream before fetching history. The single submitted user event produced two assistant messages separated by one bash call. Upserting full messages from the replacement stream and paginated history restored exactly the assistant messages in the final history, with no second user submission. This verifies protocol recovery; a browser refresh, downstream UI replay, and uncertain POST outcomes still need application-level tests.

## 6. Let users add files to the conversation

The attachment control needs a lifecycle independent of the answer stream:

```text
selected → uploading → checking → mounting → ready
                         └→ rejected       └→ timed out
ready → removing → removed
```

These are application UI states, not a list of platform status values. Associate each attachment with its owner, business conversation, uploaded `file_id`, returned resource ID, and full mount path. The backend checks ownership before acting on it.

Follow [01's upload flow](01-get-started-data-analysis-agent.md) and wait for the uploaded File to become `available`. The backend then adds it to the **existing** Session:

```text
POST /sessions/{id}/resources
{"type":"file","file_id":"<available_file_id>","mount_path":"/uploads/late.txt"}
```

Save the returned `sesrsc_...` resource ID separately from the uploaded File ID. The returned `mount_path` is already the full sandbox path; the returned `file_id` can identify a server-side copy. Resource mounting does not itself submit a user message or produce a Session event, so update the attachment UI from the backend's operation result and runtime checks. See the [resource API](https://help.aliyun.com/zh/model-studio/session-resource-create).

Do not label the attachment readable just because the resource list contains it. For the tested follow-up, after the previous turn ended the application sent:

```text
Use bash to wait up to 60 seconds for /mnt/session/uploads/late.txt
(test -f, sleep 2). Read it and report the sum of the amount column.
Do not use web tools.
```

The Agent read the file and reported `350`. Mark it ready only once the runtime confirms access; surface a timeout if it cannot. An earlier run took roughly 35 seconds, while the 2026-09-18 and 2026-10-09 checks found the path on their first tool attempt. Use a deadline instead of a fixed propagation delay.

In a business follow-up, also tell the Agent whether the new file adds rows, replaces an earlier input, or supplies reference material. Mounting alone does not ask it to revise its answer. If a turn is still running, the client can finish uploading and queue the follow-up for the next turn; do not promise that an in-flight tool automatically restarts with the new input. The tested sequence applies the change between turns in the same Session.

## 7. Remove an attachment without resetting the conversation

The user's remove action calls the backend, which uses the saved **resource ID**:

```text
DELETE /sessions/{id}/resources/{resource_id}
```

Show “removing” while reconciling both layers:

1. List `GET /sessions/{id}/resources`, following pagination, and confirm the ID is absent.
2. In a subsequent turn, have the Agent wait with a deadline for the full path to disappear. Instruct it **not to delete the file itself**, which could hide a failed unmount.

Both checks passed in the live test. On timeout, preserve the IDs and offer status recovery instead of showing a successful removal. Unmounting removes the Session's mounted copy, not the uploaded source File. Information already read into the conversation and derived outputs remain; “removed” means the attachment is no longer mounted, not that the Agent has forgotten it.

Memory Stores attach at Session creation and do not use this flow; see [09](09-working-memory-handoff.md). Upload and generated-output download details remain in [01](01-get-started-data-analysis-agent.md), and resource API basics in [tutorial 03](../tutorials/03-mount-files.md).

## Integration acceptance checks

- Short text answer: incremental content equals the final full message, with no repeated answer.
- Reasoning with text deltas: route content by its parent ID, append only `delta=true`, replace `delta=false` snapshots, and compare with the completed reasoning event and history.
- Multiple assistant messages with intervening tools: each message remains in order under the same turn.
- Approval pause or failure: `requires_action` and errors do not appear as successful completion.
- Page refresh and upstream disconnect: history is restored without duplicating messages or rerunning the business input.
- Add an attachment after a turn: the same Session reads it after runtime readiness is confirmed.
- Remove an attachment: its resource entry and sandbox path disappear, while prior messages remain intact.

Delta/Thinking, protocol recovery, and runtime file access have the separate live evidence described above; validate their combined UI and other application behaviors in the product being integrated. SDK 1.27.3 `events.stream()` had no `event_deltas` parameter in the recorded test. Use the documented REST SSE query for this example, and verify support before adopting an argument in another SDK version.

Related: [integration event contracts](../integration/api-quickstart.md), [integration patterns](../integration/patterns.md).
