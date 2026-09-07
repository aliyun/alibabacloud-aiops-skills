# Edge Cases and Error Handling

> This file defines 7 exception-handling categories + the retry algorithm + the unified failure report format. In every exception branch the Agent must treat this file as the single source of truth.

---

## 1. Timeout (polling timeout)

### 1.1 Polling cadence

`describe-diagnostic-result` foreground polling runs one round every 10s (unified across the three DiagnosticTypes, same pattern as node-ops): each round is an independent Bash call (`sleep 10 && poll_diagnostic_burst <region> <did> 10 10 <t0>`), and at the end of every round the Agent must report one progress line to the user in the reply body (poll index + status + elapsed time); **forbidden** to cram the polling loop into a single long command blocking until terminal state or running silently in the background (the frontend would show zero progress); the blocking `poll_diagnostic` is reserved for tests / non-interactive orchestration.

### 1.2 Decision tree

| Diagnostic Type | Normal cap | Hard cap | Behavior after cap is hit |
|---|---|---|---|
| `BasicCheck` | 15 min | 30 min | HITL three-way choice: keep waiting / resubmit / open a ticket |
| `NodeHardwareCheck` | 45 min | 60 min | Same as above |
| `CheckByAiJobLogs` | 30 min | 60 min | Same as above |

> The enums were calibrated against the write endpoint `create-diagnostic-task` server-side measurements (first test 2026-08-16, retest 2026-08-19): the current write enums are `BasicCheck`/`NodeHardwareCheck`/`CheckByAiJobLogs`; `NetConfigCheck`/`NetRuntimeCheck` were deprecated product-side on 2026-08-19 (the API enum validation may still accept the strings, but nothing is dispatched); the old values `NetDiag`/`ServerDiag` are no longer usable on the write endpoint. Note the **enum split**: the read endpoint `list-diagnostic-results` only accepts the old enums (see api-parameters.md #9).

Repair CLI polling: `reboot/reimage/stop` poll via `describe-node` every 30s, hard cap 30min.

### 1.5 Long-task UX (Foreground vs Background)

- **Submission receipt first (MANDATORY, V7)**: after Phase 2 succeeds and **before** the first `describe-diagnostic-result` poll, the submission receipt must be echoed to the user: `DiagnosticId` + `RequestId` + Region + DiagnosticType + NodeIds + polling mode (Background additionally gets a `resume_command`). **Forbidden** to enter polling silently - the user must always be able to take the DiagnosticId/RequestId to the console or a ticket for reconciliation.
- **Foreground (default for all three DiagnosticTypes)**: burst polling one round every 10s, each round an independent Bash call reporting the language-matched poll progress line (poll number / status / elapsed) in the reply body until terminal state; single-long-command blocking polling is forbidden. If the user says they won't wait, or 20min is exceeded -> switch to Background.
- **Background (only when the user explicitly chooses not to wait / foreground downgrade)**: return immediately with the `DiagnosticId` + write it to `$HOME/.lingjun/diag-pending-tasks.json`, and hand the user a `resume_command`.

`last_state_snapshot` is only a resume input / display fallback and must **never** be presented as live state.

---

## 2. Error-Code lookup

Look up [error-codes.md](error-codes.md) first; if not found, pass `ErrorCode + Message` through to the user verbatim and classify per the table below:

> **Known exception**: `create-diagnostic-task` returns `InternalError` + "These nodes do not exist" but the nodes are confirmed to exist via `describe-node` -> server-side node registry out of sync (KI-1, see error-codes.md); **no retry** - produce the failure report directly + suggest opening a ticket with the RequestId attached.

| Class | Handling |
|---|---|
| Network layer / 5xx / throttling | safe_aliyun retries automatically |
| Auth / Permission | blacklist, fail immediately |
| Business 4xx | blacklist, fail immediately, hand back to HITL to re-pick parameters |
| Terminal-state task business failure | no retry, report Section 6 |

---

## 3. Reentrancy (re-entry idempotence)

| Operation | Re-entry check |
|---|---|
| `create-diagnostic-task` | `list-diagnostic-results` checks whether the same node already has an InProgress task; if so, HITL two-way choice (reuse / force-create) |
| `reboot-nodes` | If `describe-node.OperatingState` is already `Rebooting` -> wait, do not resubmit |
| `reimage-nodes` | Same as above, plus check whether `ImageId` is already the target |
| `stop-nodes` | If `describe-node.OperatingState=Stopped`, return [PASS] Already Stopped directly |
| `report-node-status` | Pre-check via `describe-node`: node must be in `Using` state and have no unresolved duplicate report |

---

## 4. Exception Classification & Retry

### 4.1 Whitelist (safe_aliyun retries automatically)

- Network: connection refused / timeout / TLS / DNS / EOF
- HTTP 5xx: 502 / 503 / 504
- Transient business: `ServiceUnavailable` / `InternalError` / `RequestTimeout` / `SystemBusy`
- Throttling: `Throttling*` / HTTP 429 (fixed 60s wait)

Backoff: `2s / 4s / 8s + jitter`, at most 3 attempts.

### 4.2 Blacklist (fail immediately)

- Authentication: `InvalidAccessKeyId` / `SignatureDoesNotMatch`
- Authorization: `NoPermission` / `Forbidden` / 403
- Business 4xx: `InvalidParameter` / `NotFound` / `DiagnosticNotFound` / `OperationConflict` / `NodeNotInCluster` / `NodeStateNotMatch`
- Terminal-state business failure: diagnostic terminal state `Failed`, repair CLI returning non-2xx

### 4.5 Skill self-violations (non-retryable, non-pardonable)

| ID | Description |
|---|---|
| V1 | Bare `aliyun ...` (bypassing the `safe_aliyun` wrapper) |
| V2 | Skipping the `safe_mutate` two-phase commit |
| V3 | LLM auto-filling a `forbidden_inference` field (e.g. ImageId / LoginPassword) |
| V4 | Defaulting / reusing a Region |
| V5 | Accepting a near-miss reply as confirmation (e.g. treating `OK` / `yes` / near-miss spellings / the confirmation word of the other language as a valid confirmation), or executing Phase 2 without the user replying the current session language's confirmation word (zh word per parameter-confirmation.md / en "confirm") |
| V5(c) | Impersonating node identity in the resource list with aggregate fields like `MachineType` / `NodeGroupName` |
| V5(d) | After emitting the [PAUSE] Not Executed interception report for a non-matching reply, continuing within the same turn by simulating or fabricating a subsequent user reply (e.g. self-authoring a "the user replied confirm" message), or issuing any Phase 1 / Phase 2 / mutating command after the report; the turn must end at the interception report, and only a genuine new user message arriving in a later turn may resume the flow |
| V6 | Default-value hallucination (e.g. claiming "skipped optional field" as "using default value X") |
| V7 | Entering polling silently after submitting a diagnostic task without echoing the receipt (DiagnosticId/RequestId) first |

Violation detected -> stop immediately, discard all results obtained so far, disclose to the user and reset using the `[WARN] Skill violation (Vx): <fact>, <results obtained> discarded; re-entering ...` template.

---

## 5. Rollback

Diagnosis itself only reads node state; no rollback is needed. Repair CLIs:

| Action | Rollback |
|---|---|
| `reboot-nodes` | Considered successful once the node returns to Using; stuck -> open a ticket |
| `reimage-nodes` | **Irreversible**; the system disk has been wiped |
| `stop-nodes` | Restart via console `start-nodes` (out of scope for this skill) |
| `report-node-status` | Cannot be revoked; terminate the spawned deep diagnosis via `stop-node-diagnostic` |

---

## 6. Unified Error Output Template

```
❌ <Action> failed
  Region          : cn-hangzhou
  ClusterId       : <cid>
  DiagnosticId/   : <did>
    NodeId
  ErrorCode       : <code>
  ErrorMessage    : <msg>
  RequestId       : <reqid>
  Impact          : <one-sentence description>
  Suggestion      : <one-sentence suggestion>
```

---

## 7. Pagination Exhaustion

- Every `list-*` must paginate to exhaustion: non-empty `NextToken` -> continue with `--next-token <prev_value>`; **never** splice / truncate / re-encode the token.
- `--max-results` always keeps the value passed on the first page; **never** change it across pages.
- Soft cap: 50 pages / 1000 items; when hit, HITL two-way choice (continue / stop) - silent truncation is **forbidden**.
- When traversing multiple Regions, **each** Region completes its exhaustion independently.
