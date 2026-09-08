# Edge Cases

## 1. Exception classification and retries

### 1.1 Whitelist (safe_aliyun silently retries <=3 times)

| Type | Trigger | Backoff |
|---|---|---|
| network layer | `connection refused` / `i/o timeout` / `TLS handshake` / `dns lookup` / `unexpected EOF` | `2s/4s/8s` exponential backoff + jitter |
| HTTP 5xx | `502` / `503` / `504` | `2s/4s/8s` |
| server transient | `ServiceUnavailable` / `InternalError` / `RequestTimeout` / `SystemBusy` | `2s/4s/8s` |
| throttling | `Throttling` / `Throttling.User` / HTTP 429 | fixed 60s |

### 1.2 Blacklist (fail immediately, no retry)

- authentication: `InvalidAccessKeyId` / `SignatureDoesNotMatch`
- authorization: `NoPermission` / `Forbidden` / HTTP 403
- business 4xx: `InvalidParameter*` / `*.NotFound` / `OperationConflict` / `MissingParameter` / `InvalidNodeStatus` / `Failure to check order`
- task terminal failure: `TaskState=execution_fail`

### 1.3 Mutating retry preconditions

- `renew-instance` must use a stable `ClientToken`, unchanged across retries
- once a `TaskId` / `InvokeId` / `OrderId` is obtained -> switch to async polling; **never retry the submit**
- task terminal business failure -> report the error directly; stop polling

---

## 2. Idempotency (Reentrancy)

| API | Idempotency mechanism |
|---|---|
| `stop-nodes` / `reboot-nodes` | server decides based on `OperatingState`; pre-check node state |
| `reimage-nodes` | same `NodeId` + same `Hostname` + same `ImageId` within 60s is treated as the same request |
| `change-node-types` | server dedupes by `(NodeId, NodeType)` |
| `renew-instance` | `ClientToken` UUID strong idempotency |
| `run-command` | `ClientToken` strong idempotency |
| `update-node-group` | no explicit idempotency key; must `describe-node-group` to confirm state before retry |
| `tag-resources` | re-tagging the same K-V silently OK |
| `untag-resources` | removing a nonexistent Key silently OK |
| `change-resource-group` | no explicit idempotency key; `describe-node` to confirm `ResourceGroupId` before retry |

---

## 3. Skill self-violations (non-retryable)

| Code | Description | Remedy |
|---|---|---|
| **V1** | bare `aliyun` call (not via safe_aliyun) | abort immediately; discard the response; restart from the Pre-Execution Self-Check |
| **V2** | submitting a change without the user replying the confirmation word (see `render.confirm_word` in `lib/core/i18n.sh`) - skipping the single-step confirmation gate | abort immediately; run Sec.2 Reentrancy to check for residual resources |
| **V3** | auto-filling a `forbidden_inference` field | abort immediately; discard collected parameters; HITL redo the list-* picker |
| **V4** | defaulting / reusing a Region | abort immediately; HITL have the user explicitly pick a Region |
| **V5** | treating a vague / unrelated reply as the confirmation word (e.g. silence, "probably fine", yes/OK, a new question, the other language's word) | abort immediately; run Sec.2 Reentrancy + Sec.4 Orphan Scan |
| **V5(c)** | confirmation table impersonates `NodeId` / `Hostname` with aggregate fields such as `MachineType` / `NodeGroupName` | abort immediately; handle as V5 |
| **V6** | default-value hallucination (HITL "skip" != "use default X") | abort immediately; HITL three-way pick (skip / explicit default / customize) and re-collect |
| **V7** | after async submit, failing to echo the submission receipt (TaskId/RequestId) in the reply body, or failing to poll in a single foreground poll_task rolling loop (background silent polling / splitting commands across turns and burying progress in thinking blocks) | resend the receipt immediately; switch to a single foreground poll_task to continue polling |

Unified disclosure format for all violations:

```text
[WARN] Skill violation (V<code>): <concrete facts>; <results already obtained> have been discarded; restarting from <recovery point>.
```

---

## 4. Orphan Resource Scan

Executed only after V2 / V5 triggers; the goal is to determine whether any **unaccounted** cloud-side change has already happened:

1. F1/F2/F3 -> `describe-node --node-id <ids>`, compare `OperatingState` / `ImageId` / boot time
2. F4 -> `bssopenapi query-orders --product-code bccluster --order-type Renew` to pull orders from the last 60 minutes, matching `InstanceId == NodeId`; also `describe-node` to check whether `ExpiredTime` moved forward
3. F5 -> `describe-node` to compare `MachineType`
4. F8.2 -> `describe-node` to compare `NodeGroupId`
5. F9.1/F9.2 -> `list-tag-resources` to compare `Tags[]`
6. F9.4 -> `describe-node` to compare `ResourceGroupId`

If any effective change is found:
- rewrite the [paused] Not Executed report as "[WARN] Partially changed (violation triggered)"
- list the changed `NodeId`s with before/after field comparison
- let the user decide whether to roll back (many changes are irreversible, e.g. reimage / renew)

---

## 5. Unified failure report format

```text
[FAIL] Execution Failed
- Stage: <Phase 1/2/Polling/Verify>
- API: <namespace> <action>
- HTTP: <code> Code: <ErrCode>
- RequestId: <id> (if any)
- Cause: <verbatim server-side Message>
- Recovery: <next-step suggestion, citing the matching row in error-codes.md>
```

---

## 6. Pagination exhaustion

- every `list-*` must exhaust pagination until `NextToken=""` or accumulated count >= `TotalCount`
- `--max-results` stays unchanged; `--next-token` is passed back verbatim - encoding / truncating is forbidden
- safety threshold: a single run >=50 pages or >=1000 items -> HITL two-way pick (continue / accept partial and explicitly mark "not exhausted")
- multi-Region enumeration: each Region must be exhausted independently; concatenating only the first page is forbidden

---

## 7. Concurrent mutating operations

- between two mutating operations on the same node / same group, the server may return `OperationConflict`
- the Agent **must** HITL let the user pick: a) submit in parallel (user accepts the rejection risk) / b) wait for the previous task's terminal state
- silently serializing/waiting is forbidden; silently retrying `OperationConflict` is forbidden

---

## 8. F4 renewal special handling

- `Failure to check order` -> re-check `ProductCode=bccluster` + `ProductType=bccluster_eflocomputing_public_cn` + `RenewPeriod  in  [1..9, 12, 24, 36]`
- gateway returned `OrderId` but `query-orders` cannot find it -> wait 30s and query again (async sync window)
- insufficient balance: `NotApplicable.AccountBalance` -> abort immediately; HITL have the user top up then manually retry (**no** auto-retry)

---

## 9. F7 run-command special handling

- `InvocationStatus=Timeout` -> report a warning, but do not treat as failure (the user script itself timed out)
- `InvocationStatus=PartialFailed` -> mandatory `describe-invocations --include-output true` to fetch per-node detailed output
- commands containing secrets: must use `--enable-parameter` + `--parameters '{"k":"v"}'` instead of embedding them in `--command-content`
