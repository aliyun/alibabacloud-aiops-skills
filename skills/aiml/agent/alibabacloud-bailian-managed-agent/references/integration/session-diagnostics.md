# Session diagnosis: evidence and execution contracts

Read this with the [session optimization workflow](../workflows/session-optimization.md). This reference covers evidence collection and interpretation; it does not authorize resource changes or replay of a customer's actions.

Checked against official operation pages on **2026-11-10**. CLI command shapes below come from the installed `bailian-managed-agent` command reference; inspect the actual installed leaf `--help` before execution. Follow [CLI/API routing](../workflows/cli-api-routing.md) and the [versioned User-Agent](../workflows/user-agent.md) rules for cloud calls.

## Read the baseline

| Evidence | Contract and diagnostic use |
| --- | --- |
| Session | `GET /sessions/{session_id}` supplies status, stop reason and the embedded Agent snapshot. Record the snapshot's ID/version and effective configuration, not just the current Agent fetched separately. |
| Recorded consumption | `POST /usage/summary` with only `dimension=session` and `session_id` supplies lifetime token/model/tool/runtime totals and grouped details. See [Usage API](usage-api.md); retain nulls and freshness, and do not treat it as a per-turn or live-progress counter. |
| Event history | `GET /sessions/{session_id}/events?order=asc&limit=100` supplies completed events. Follow every opaque `next_page` through `page`; omit `page` initially. Keep ordering and time filters unchanged while paging. |
| Current configuration | Read the current Agent/Environment separately when preparing a change. It can differ from the baseline snapshot. Preserve both versions in the experiment record. |
| Resources and inputs | Record file origins, mount paths, memory provider/entity/access, non-secret environment configuration and skill/member versions needed to reproduce the run. Resource metadata alone does not prove that input bytes or historical memory are recoverable. |

Event List returns `data`, `next_page` and a request ID. An absent/null next cursor means exhaustion. An empty page does **not** imply exhaustion when a next cursor remains, particularly with CLI client-side type filtering. Detect repeated cursors and record an incomplete collection instead of looping indefinitely. A filtered time window or a page/event limit must remain visible in the report. For an active Session, record the observation cutoff and status; a paginated read is not an atomic final snapshot.

Deduplicate completed events by their nonempty event IDs when merging history and streams; do not deduplicate anonymous records or equal message text. IDs are opaque: official examples include `msg_`, `out_` and `sevt_`, so avoid a single-prefix validator. Preserve unknown event types as evidence. Missing events, timestamps, usage or correlation IDs are unknown, not zero or proof of absence.

Sources: [Get Session](https://docs.bailian.console.aliyun.com/zh/model-studio/session-get), [Event List](https://docs.bailian.console.aliyun.com/zh/model-studio/event-list).

## Collect generated artifacts

After a turn ends, outputs under `/mnt/session/outputs` are collected as File resources. List with `GET /files?scope_type=session&scope_id={session_id}&limit=100`, follow opaque `next_page` via `page`, match the expected filename and scope, and check `downloadable`. Retrieve bytes with `GET /files/{file_id}/content`; choose the parser from the actual file type rather than assuming every download is JSON. The Session's mounted `resources` list is not its generated-output inventory. A short bounded retry may be needed for collection after `end_turn`; do not send another model message just to enumerate the files. Missing or non-downloadable output remains unverified.

Compare each answer against its own downloaded source when the task queries live data. Keep required rows, dates, prices, provenance and summary claims in the rubric; different per-query booking links alone are not evidence of a regression. Preserve original bytes locally with appropriate access restrictions, and do not publish credential-bearing artifacts.

Sources: [List Files](https://docs.bailian.console.aliyun.com/zh/model-studio/file-list), [Download File](https://docs.bailian.console.aliyun.com/zh/model-studio/file-download), [Data analysis and output files](https://docs.bailian.console.aliyun.com/zh/model-studio/managed-agents-data-analysis). The Session scope filter and download path were also exercised in the 2026-11-10 cloud trial.

## Interpret events without conflating signals

| Event | Where to look / interpretation |
| --- | --- |
| `message` | `role` and `content[]`; user echoes are inputs, assistant messages are outputs. A completed message does not by itself finish a turn. |
| `tool_call`, `mcp_call`, `function_call` | Data blocks under `content[].data` contain call identity and available name/arguments. Match outputs by call identity within the same thread, never by nearest timestamp alone. |
| `tool_call_output`, `mcp_call_output`, `function_call_output` | Output data carries `call_id` and `output`. Inspect event-level `is_error`; rejected or interrupted tools can also set it. Do not classify every tool failure as a service outage. |
| `error` | Error details are at the **event root**, `error.code` / `error.message`, not exclusively under `content[].data`. |
| `tool_approval_request` / response | Match the composite identity `(batch_id, call_id)`; approval delays are distinct from tool execution. Never replay an old approval into a new Session. |
| `session_status` | Read `content[].data.session_status` and `stop_reason`; Session GET also has root-level `status` / `stop_reason`. |

Resolve thread identity from supplied `session_thread_id`, `thread_id` or `metadata.thread_id`, retaining the source and marking conflicts/unknown ownership. Do not infer main-thread ownership merely from an absent field. A child thread ending does not finish the Session. No independent Thread CLI family is documented; do not fabricate `session thread …` commands. Archived thread REST observations in other references require current capability verification before use.

Inspect business results as well as the envelope. The 2026-11-10 FlyAI case returned `is_error=false` and outer bash `exit_code=0` while stdout contained the CLI's `exit:1` and `Trial limit reached`: commands after a failing command can hide its exit status. An empty top-level error list means no flagged event errors, not that every business operation succeeded. Do not classify quota exhaustion as local-signature or Vault incompatibility without evidence from the client/authentication mechanism.

For the Session's stop state:

- `idle` + `end_turn`: processing ended normally; business quality still needs separate evaluation.
- `idle` + `requires_action`: waiting for approval or an external result; inspect the pending calls. This is neither completed work nor automatically a fault.
- `idle` + `retries_exhausted`: failed processing.
- `running` (and an observed transient `rescheduling`): unfinished; use a bounded observation deadline.
- `terminated`: terminal lifecycle state; do not report successful task completion from this alone.
- A newly created `idle` Session with no stop reason has not necessarily processed any input. Associate completion evidence with the submitted user event and observation window, rather than accepting an earlier idle event.

Sources: [SSE event contract](https://docs.bailian.console.aliyun.com/zh/model-studio/event-sse-stream), [Send Event](https://docs.bailian.console.aliyun.com/zh/model-studio/event-post). Incremental frames require the additional rules in [event-stream.md](event-stream.md); an SSE fragment is not a completed historical event.

## Timing, usage and comparison limits

Use [Session timing and cumulative usage](session-stats-and-usage.md) for `stats`, cache accounting and cost definitions. These fields are supplemental product knowledge and are not enumerated in the current Get Session page; handle unavailable fields explicitly. Do not label Session-wide cumulative figures as one turn's usage or duration. A before/after delta is attributable to a turn only if the observed interval excludes other work and the counters are consistent.

A call/output timestamp difference is an **observed interval**, potentially including queuing or approval, not guaranteed model/server execution time. Concurrent calls overlap: their summed durations do not equal wall-clock latency. Unmatched calls and invalid/absent timestamps remain incomplete measurements. Historical completed-message timestamps do not reconstruct time to first token; measure that on a new live stream with a consistent clock and declared start point. Keep cold/warm starts and cache effects visible.

Check correlation-key uniqueness before pairing model events. In the 2026-11-10 FlyAI case, all model starts within a turn shared `request_id`, while only ends exposed unique `model_request_id`. Strictly alternating events on one thread support a labeled sequential observation window, not a verified unique-ID latency measurement. Time from `running` to the first model event can differ from user-message-to-model time; show the chosen clock and do not infer cold start or scheduling root cause from that gap alone.

Quality needs the original task, expected output or a stated rubric and the actual deliverable; `end_turn` alone is insufficient. A single before/after run is evidence for that sample, not a statistically reliable improvement. Price estimates require current model/tier prices and matching usage scope; token reductions alone are not measured currency savings.

## New Sessions and configuration changes

Session creation binds an Agent snapshot; changing the source Agent does not retune an existing Session. Create a new Session for every candidate run and read it back to verify the effective snapshot. String-form `agent` binds the latest version at creation; do not assume an old baseline can be reproduced by reusing that ID. If explicit historical-version binding is needed, verify the current creation contract/capability; otherwise construct an isolated candidate from the captured writable configuration and report any unrecoverable dependencies.

Agent update is full replacement with optimistic-lock `version`: read the latest configuration, preserve unrelated writable fields, apply the intended delta and handle version conflicts by re-reading. Do not submit the entire Session response as an Agent request. A baseline snapshot is evidence, not authority to overwrite newer shared configuration. Use the [provisioning workflow](../workflows/provision.md) for IaC plans and authorization. New environments/files may need readiness checks before running.

Sources: [Create Session](https://docs.bailian.console.aliyun.com/zh/model-studio/session-create), [Agent version semantics](https://docs.bailian.console.aliyun.com/zh/model-studio/agent-api), [Update Agent](https://docs.bailian.console.aliyun.com/zh/model-studio/agent-update).

## CLI capability map

| Need | Documented command family / limits |
| --- | --- |
| Session metadata | `bl managed-agent session get --session-id …` |
| Complete event history | `bl managed-agent session event list --session-id … --order asc --all --output json`; `session events` is a compatibility alias. `--types` is client-side in the installed reference. |
| Diagnostic convenience | `session debug`, `session export`; exports contain diagnostic metadata, not file bodies. Verify completeness separately; do not treat an aggregate as a substitute for events. |
| Resource discovery | `agent get`, `agent versions`, `environment get`, `state list/show`; flags depend on leaf help. |
| Create/update resources | Edit the intended `agents.yaml` declarations, then `validate → plan → apply` under the existing provisioning rules. There is no need for a Deployment just to test a Session. |
| Controlled run | `session create`, then `session event send` + `session event stream`; or `session run --agent <logical-name> --prompt …` when it can represent the experiment inputs. |

`session create/run --agent` selects a logical name from `agents.yaml`, not an arbitrary remote ID. `session run --output json` is documented as an envelope containing `session_id`, `provider`, `agent`, `events`; do not confuse this with a Session GET object. Raw `event send --event @file` takes an event object/array, while REST POST wraps it in `{"input": [...]}`. The acknowledgement only echoes submitted inputs; collect subsequent completion evidence.

The documented CLI `event stream --after-id` may implement recovery through paginated polling and ID deduplication when the provider lacks a native cursor. It does not prove native SSE delta replay support. For a CLI capability or header gap, use the bounded update/API fallback with the same workspace and authorization. Do not invent flags to make the experiment fit.
