# Event streaming: answer and Thinking text

Use this reference when implementing SSE consumption in any language. [Cookbook 11](../cookbook/11-client-integration-practice.md#4-separate-thinking-activity-from-turn-completion) contains the reproducible test and measurements: **5/5 fresh Sessions** returned nonempty reasoning deltas on 2026-10-23, cn-beijing, `qwen3.8-max`, `enable_thinking=true`.

## Subscribe and choose the output mode

Set `model.enable_thinking=true` on a supported Agent and create a fresh Session after changing the Agent. Establish the SSE connection before sending the user event through another connection. Use the same [versioned User-Agent](../workflows/user-agent.md) on both requests.

```bash
curl --user-agent "$BAILIAN_MANAGED_AGENT_SKILL_UA" --max-time 180 \
  -N --no-buffer --get "$CMA_BASE/sessions/$SESSION_ID/events/stream" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -H 'Accept: text/event-stream' \
  --data-urlencode 'event_deltas[]=message' \
  --data-urlencode 'event_deltas[]=reasoning'
```

- Without `event_deltas[]`, receive completed events. An SSE connection alone does not enable token-level text output.
- With the repeated parameters above, receive both answer and reasoning content incrementally. A plain string/append-only frontend transport is insufficient: it must distinguish message type, event ID, block index, and append versus replacement.
- The Python SDK 1.27.3 snapshot did not expose an `event_deltas` stream argument. Verify the installed SDK's signature and actual frame handling before using it for Delta; otherwise use REST. Do not infer present SDK support from the old snapshot or invent an SDK keyword.

HTTPX query parameters: `params=[("event_deltas[]", "message"), ("event_deltas[]", "reasoning")]`. OkHttp: call `.addQueryParameter("event_deltas[]", "message")` and `.addQueryParameter("event_deltas[]", "reasoning")` on the stream URL builder. Enabling these parameters also requires the content-frame adapter below; adding them to a completed-message-only dispatcher will drop fragments.

## Parse frames, then route by the parent event

Ignore SSE comments, accept `data:` with or without a space, and join multiple data lines before JSON decoding. Dispatch using the JSON fields, not the outer SSE `event:` name.

The following format was observed in all five live tests. The official SSE pages checked on the same date still described `event_start/event_delta`; that envelope is covered below as a compatibility path.

| JSON frame | Key and action |
| --- | --- |
| `object=message`, `status=in_progress`, `type=message/reasoning` | Register parent `id` → event type and available role/thread metadata. This is a start frame, not a complete message. |
| `object=content`, `type=text`, `delta=true` | Append `text` in arrival order to the block keyed by `(msg_id, index)`. Look up `msg_id` to decide answer versus reasoning. |
| `object=content`, `type=text`, `delta=false`, `status=completed` | Replace that block with the full `text` snapshot. Do not append it again. |
| `object=message`, `status=completed`, `type=message/reasoning` | Upsert the complete parent event by `id`; replace all its provisional blocks with `content` and remove stale blocks. Only assistant messages belong in the assistant transcript. |
| `type=session_status` | Read `content[].data.session_status` and `stop_reason`; this determines turn outcome. |

`index` is a content-block index, not a fragment sequence. Repeated equal fragments at the same key must each be appended. For example `"3"`, `"23"`, followed by a `delta=false` snapshot `"323"` still produces `"323"`.

Content frames do not carry the parent's business event type or necessarily its `thread_id`. Keep an ID-to-parent map. If ownership or thread is not established, buffer provisionally until the completed parent supplies it; **missing thread metadata on a partial frame does not mean main-thread output**. Separate reasoning from answer text, and member-thread content from the coordinator's answer.

For the documented `event_start/event_delta` envelope, register `event_start.event.id/type`, append `event_delta.delta.content.text` to `(event_id, delta.index)`, then replace with the completed event. [normalize_delta_frame and delta_evidence](../../scripts/cookbook_smoke.py) exercise both formats. Their `content_completed` label is local to the adapter, not an upstream event type.

## Ordering, completion, and recovery

Consume live fragments in arrival order. Do not sort or deduplicate them by `sequence_number`, SSE `id:`, message ID, block index, or text. In the tested payloads `sequence_number` was null, and content frames need not contain a timestamp or an SSE cursor. Deduplicate **completed events** by event ID when merging stream and history.

End of reasoning, a completed content block, or a completed answer does not end the turn. Continue until `session_status` reports `idle/end_turn`, `idle/requires_action`, failure, or termination; handle each outcome separately. Keep total deadlines and cancel the transport when the waiting operation ends.

After disconnect, establish a replacement stream, buffer live events, and reconcile paginated Event List by completed-event ID. A new stream may deliver only the suffix of an unfinished block; replace provisional content with full history instead of assuming the suffix is complete. Do not resubmit the input or assume `Last-Event-ID` can resume deltas.

## Validate the integration

Require nonempty reasoning deltas when testing Thinking delivery. Compare the appended fragments independently against the block snapshot, completed reasoning event, and history; replacing a buffer with a final snapshot must not conceal lost fragments. Check answers separately, then require `idle/end_turn`. [The delta smoke scenario](../../scripts/cookbook_smoke.py) performs these checks; [Cookbook 11](../cookbook/11-client-integration-practice.md) gives its setup and command.

For application adapters, test that reasoning cannot enter the answer stream, snapshots cannot duplicate text, user echoes cannot become assistant output, and unknown types cannot terminate the parser. The live evidence above covers the REST protocol; SDK transports, UI rendering and MultiAgent Delta ownership need their own application validation.
