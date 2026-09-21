# Edge Cases and Error Handling

Detailed edge-case / error-handling reference for Lingjun cluster scaling. The structure here mirrors section **3.2** of the design document and the six-category model in [SKILL.md](../SKILL.md#edge-cases-and-error-handling).

> **⚠️ Region Required (MANDATORY)** ｜ Every `aliyun eflo-controller` command example in this file **must** explicitly carry `--region <region>` (`<region>` given explicitly by the user via HITL; defaulting / reusing / persisting via environment variable is **strictly forbidden**). The endpoint is auto-derived by the aliyun CLI from `--region`; an explicit `--endpoint` is **neither needed nor desired** (see [SKILL.md §B-6 Region Required](../SKILL.md)). This rule does **not** apply to `aliyun bssopenapi` and `aliyun ecs` commands.

## Table of Contents

1. [Operation Timeouts (3.2.1)](#1-operation-timeouts-321)
   - [§1.5 Long-Running Async Task UX (client experience)](#15-long-running-async-task-ux-client-experience)
2. [Error-Code Lookup (3.2.2)](#2-error-code-lookup-322)
3. [Reentrancy (3.2.3)](#3-reentrancy-323)
4. [Exception Classification & Retry (3.2.4)](#4-exception-classification--retry-324)
5. [Rollback Capability (3.2.5)](#5-rollback-capability-325)
6. [Unified Error Output (3.2.6)](#6-unified-error-output-326)
7. [Pagination Exhaustion (3.2.7)](#7-pagination-exhaustion-327)
8. [Appendix A — Network Resource Cleanup](#appendix-a--network-resource-cleanup)
9. [Appendix B — Retry Code Snippets](#appendix-b--retry-code-snippets)

---

## 1. Operation Timeouts (3.2.1)

### 1.1 Timeout Matrix

| Operation | Normal | Hard timeout |
| --- | --- | --- |
| Cluster expand (cloud disk) | 10–20 min | 60 min |
| Cluster expand (local disk) | ~120 min | 240 min |
| Cluster shrink (cloud disk) | 10–20 min | 60 min |
| Cluster shrink (local disk) | *to be confirmed* | *to be confirmed* |
| Node create (BssOpenApi) | 1–5 min | 40 min |
| Change node group | 2–5 min | 20 min |

Poll `describe-task` every **30 s** while the task is `running` / `waiting_to_run`. The Agent should also surface a visible "elapsed Xmin" progress line to the user.

### 1.2 Decision Tree

```plain
Poll describe-task (every 30s)
    │
    ├─ TaskState=execution_success → normal exit (verify result)
    ├─ TaskState=execution_fail    → extract ErrorCode + Message → report (see §6)
    └─ TaskState=running/waiting_to_run AND elapsed > hard timeout
        │
        └─ STOP polling and ask the user:
             1. Keep waiting in background (the task may still make progress)
             2. Open a support ticket with RegionId + TaskId
                (for CreateInstance also include OrderId + InstanceId)
```

### 1.3 Detection — is the task actually stuck?

```bash
# Compare UpdateTime across consecutive queries; if frozen for > 15min
# inside the normal window, treat as "likely stuck"
for i in 1 2 3; do
  safe_aliyun aliyun eflo-controller describe-task \
    --region "$REGION" \
    --task-id "$TASK_ID" \
    --cli-query '{State:TaskState, Progress:TaskProgress, UpdateTime:UpdateTime}'
  sleep 60
done
```

### 1.4 Partial escalation ladder (guidance, not policy)

| Elapsed | Action |
| --- | --- |
| < normal upper bound | silent wait |
| normal → hard timeout | surface "elapsed Xmin" to user, keep polling |
| ≥ hard timeout | stop polling, present the two-choice dialog (§1.2) |

### 1.5 Long-Running Async Task UX (client experience)

To solve the session-blocking and "close the window, lose the tracking" problems caused by **multi-hour** tasks such as expansion (up to 240min) / shrink (up to 60min) / node purchase (up to 40min), the Agent makes a **dual-mode decision** based on each task's Normal upper bound; whichever mode is chosen, the server-side task progress is unaffected.

#### 1.5.1 Mode thresholds (decided by the Normal upper bound, NOT the Hard Timeout)

| Task | Normal upper bound | Default mode |
| --- | --- | --- |
| `change-node-group` | 5 min | **A foreground polling** |
| `delete-node` / `delete-hyper-node` (synchronous fire-and-forget) | 5–10 min (the real reclamation runs in the cloud background; the agent does not poll) | **Synchronous RequestId return**; the agent only outputs the summary per `completion_summary_template` |
| `extend-cluster` (cloud disk) / `shrink-cluster` (cloud disk) | 20 min | **B immediate return + suspend** (> 20 min threshold) |
| `create-instance` (Feature 4) | 5–40 min | **B immediate return + suspend** |
| `extend-cluster` (local disk) | 120 min | **B immediate return + suspend** |

Hard rule: **tasks whose Normal upper bound > 20 min always default to mode B**; downgrading back to A is allowed only when the user explicitly says "I'll wait", but it must automatically bounce back to B when the Normal upper bound is reached (no indefinite continuation).

#### 1.5.2 Mode A: foreground polling (short duration)

- Per the §1.1 matrix, `describe-task` every 30 s until a terminal state.
- The caller uses `poll_task`, which automatically emits standardized progress cards to stderr (see [detailed-rules.md §Receipt + On-Demand Query](detailed-rules.md#silent-polling)). `LJ_TASK_LABEL` must be exported before the call, e.g.:
  ```bash
  export LJ_TASK_LABEL="Shrink task host-prod-001"
  poll_task cn-wulanchabu "$tid" 1500 15
  ```
- The user-facing terminal is throttled in layers: "first full card → refresh the card on state change → one heartbeat line every 60s in between → one terminal-state summary line"; the state fields come from real `describe-task` responses and **must not** be fabricated (see SKILL.md Anti-Fabrication §3: fabricating polling logs is forbidden).
- Elapsed ≥ Normal upper bound, or the user explicitly says "don't wait for now" → downgrade to B immediately: write the current `last_state_snapshot` into `pending-tasks.json`, output the resume instructions, and end this session round.

#### 1.5.3 Mode B: immediate return + suspend (long duration, default)

1. The moment `safe_aliyun` obtains HTTP 2xx + a non-empty `TaskId` (not when polling ends), suspend this task immediately.
2. Register into `$HOME/.lingjun/pending-tasks.json` (the client-side single source of truth; its role runs in parallel with `tests/reports/pending-tasks.json` without conflict); append one entry to `pending[]` via `jq`:
   ```json
   {
     "task_id": "i15xxxxxxxxxxxxx",
     "action": "extend-cluster",        // or shrink-cluster / change-node-group / create-instance / delete-node ...
     "region": "cn-wulanchabu",
     "endpoint": "eflo-controller.cn-wulanchabu.aliyuncs.com",
     "cluster_id": "...",                 // write null when Feature 4 has no cluster_id
     "node_group_id": "...",              // optional
     "order_id": "...",                    // Feature 4 only
     "submitted_at_local": "ISO8601",
     "normal_window_min": 20,              // from the §1.5.1 matrix
     "hard_timeout_min": 60,               // from the §1.1 matrix
     "last_state_snapshot": { "task_state": "running", "update_time": "...", "steps_done": 0 },
     "resume_command": "safe_aliyun aliyun eflo-controller describe-task --region <region> --task-id <tid>"
   }
   ```
3. Emit the unified "Mode B suspend template" (customer-facing; localized per session language):
   ```
   ⏳ Submitted; the task is still progressing server-side
       TaskId: <tid>
       Operation: <action>
       Region:    <region>
       ETA: ~<normal_window_min> min (hard cap <hard_timeout_min> min)

   ⏺️ Closing this session does not affect the task. To check, just say "check my last task", or run:
       <resume_command>
   ```
4. This session round ends, with the state annotated ⏳ (submitted, pending poll). Giving a ✅ success / ❌ failure conclusion **without** calling `describe-task` again is forbidden.

#### 1.5.4 Resume query

When the user next says "check my last task", the Agent executes:

1. `jq -r '.pending[].resume_command' $HOME/.lingjun/pending-tasks.json` — enumerate pending entries; if more than one, HITL selection is required.
2. Execute the `resume_command` to get the latest `TaskState`:
   - `execution_success` → run the corresponding Feature's "terminal-state verification" (e.g. `describe-node` confirms `NodeGroupId` has switched) → output the ✅ completion report → move the entry from `pending[]` to `completed[]` via `jq`.
   - `execution_fail` → output details per §6 Unified Error Output → move to `failed[]`.
   - `running` / `waiting_to_run` → update `last_state_snapshot.update_time`; judge against the hard timeout by elapsed time and apply the §1.2 two-way choice (keep waiting / file a ticket).
3. In all resume outputs, `TaskId` / `RequestId` / `update_time` / `steps_done` **must still come from the real `describe-task` response**; the snapshot in `pending-tasks.json` must not impersonate real-time state.

Reference interaction script (directly runnable; depends on `jq` and `safe_aliyun`):

```bash
PENDING="$HOME/.lingjun/pending-tasks.json"

# Step 1 — enumerate: select directly if only 1 entry; HITL if more than 1
 mapfile -t RESUMES < <(jq -r '.pending[] | [.task_id, .action, .region, .submitted_at_local, .resume_command] | @tsv' "$PENDING")
[ "${#RESUMES[@]}" -eq 0 ] && echo "⚠️ no pending tasks" && exit 0
if [ "${#RESUMES[@]}" -gt 1 ]; then
  printf '%s\n' "Pending tasks (enter index 1..N):"
  for i in "${!RESUMES[@]}"; do
    IFS=$'\t' read -r TID ACT REG TS _ <<<"${RESUMES[$i]}"
    printf '  [%d] %s  %s  %s  (submitted %s)\n' $((i+1)) "$TID" "$ACT" "$REG" "$TS"
  done
  # The Agent binds the index chosen by the user to $SEL (0-based)
else SEL=0; fi
IFS=$'\t' read -r TID ACT REG TS CMD <<<"${RESUMES[$SEL]}"

# Step 2 — echo the resume_command to be executed (run only after HITL confirmation)
printf '→ about to run: %s\n' "$CMD"

# Step 3 — execute the real describe-task ($CMD already contains safe_aliyun / --region / --task-id)
RESP=$(eval "$CMD") || { echo "❌ resume call failed; classify per §4"; exit 1; }
STATE=$(jq -r '.TaskInfo.TaskState // .TaskState' <<<"$RESP")

# Step 4 — terminal-state migration (or snapshot write-back)
case "$STATE" in
  execution_success)
    jq --arg tid "$TID" '.completed += [.pending[] | select(.task_id==$tid)] | .pending |= map(select(.task_id!=$tid))' "$PENDING" > "$PENDING.tmp" && mv "$PENDING.tmp" "$PENDING"
    echo "✅ $ACT completed (TaskId=$TID); verify the terminal object per the Feature verification method" ;;
  execution_fail)
    jq --arg tid "$TID" '.failed += [.pending[] | select(.task_id==$tid)] | .pending |= map(select(.task_id!=$tid))' "$PENDING" > "$PENDING.tmp" && mv "$PENDING.tmp" "$PENDING"
    echo "❌ $ACT failed; output details per §6 Unified Error Output" ;;
  running|waiting_to_run)
    NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    jq --arg tid "$TID" --arg t "$NOW" --argjson resp "$RESP" '(.pending[] | select(.task_id==$tid) | .last_state_snapshot) |= {task_state:($resp.TaskInfo.TaskState // $resp.TaskState),update_time:$t,steps_done:($resp.TaskInfo.Steps|length? // 0)}' "$PENDING" > "$PENDING.tmp" && mv "$PENDING.tmp" "$PENDING"
    echo "⏳ $ACT still progressing (TaskId=$TID); judge hard-timeout per §1.2" ;;
esac
```

Constraint: `eval "$CMD"` is valid only for `resume_command` entries in the local `pending-tasks.json` written by the Agent itself (trusted field source); this script must **not** be run against externally supplied JSON files.

#### 1.5.5 Optional proactive reminders (opt-in, off by default)

The Agent itself has no background-push capability. If the user asks for a timed reminder, offer two documented client-side options; the SKILL only provides example scripts and does **not** enable them by default:

- **Option B: local `nohup` daemon + macOS `osascript` popup** (visible on the local machine only): embed `resume_command` in a loop script, `nohup bash lj-watch.sh <tid> &`.
- **Option C: script + Webhook** (reachable across devices): on terminal state, `curl`-push to the user's existing DingTalk / WeCom bot webhook.

Both options reuse the existing `resume_command` / `TaskId` / `endpoint` fields of `pending-tasks.json` and introduce no extra configuration surface.

---

## 2. Error-Code Lookup (3.2.2)

### 2.1 Lookup order

1. **First** consult [error-codes.md](error-codes.md) — it carries HTTP/SDK code → cause → remediation rows for every known code.
2. **Fallback** when the code is not listed: compose a best-effort suggestion from `ErrorCode + Message` (never hallucinate a "known" fix that isn't documented).

### 2.2 Parameter-error recovery pattern

```plain
CLI returns an error
    │
    ├─ Parse ErrorCode + Message
    │
    ├─ Auto-fixable? (derivable from conversation context)
    │   ├─ Yes  (e.g. missing RegionId → infer from previous turns) → auto-fill → retry
    │   └─ No   (e.g. wrong ClusterId)                              → interactive fix
    │           ├─ Run the discovery API (list-clusters / list-node-groups / ...)
    │           ├─ Show the valid options
    │           └─ User picks → retry
    │
    └─ Non-fixable? (e.g. quota exceeded, commodity unavailable)
        → State the cause plainly + provide the escalation path
          (quota increase, choose another region, file a ticket...)
```

### 2.3 BssOpenApi CreateInstance specifics

| ErrorCode | HTTP | Trigger | Agent action |
| --- | --- | --- | --- |
| `InvalidProductType` | 400 | `ProductCode` / `ProductType` does not match the region's commodity | Enforce `ProductCode=bccluster` + `ProductType=bccluster_eflocomputing_public_cn` (China sites); do **not** fall back to legacy placeholder `lingjun` |
| `Failure to check order` | 400 | Installment / discount / period combination is inconsistent | Re-collect `Period` + `StageNum` + `PaymentRatio` + `discountlevel` and re-confirm |

See [`../workflows/create-instance/schema.yaml`](../workflows/create-instance/schema.yaml) for the authoritative parameter contract.

---

## 3. Reentrancy (3.2.3)

Retries must never produce side effects or data inconsistency. Before retrying each function, the Agent must run the pre-check below.

| Feature | Pre-check before retry |
| --- | --- |
| **Expand cluster** `ExtendCluster` | `list-cluster-nodes --cluster-id` → if the NodeId is already present, skip it (don't re-expand) |
| **Shrink cluster** `ShrinkCluster` | `list-cluster-nodes --cluster-id` → if the NodeId is already absent, skip it (don't re-shrink) |
| **Release node** `DeleteNode` | Tolerate already-released nodes — return backend status directly without error |
| **Change node group** `ChangeNodeGroup` | `describe-node` → if `NodeGroupId == target`, no-op |
| **Create node** `CreateInstance` | Query free nodes under `(Region + HpnZone + Zone + computingserver)` and offer the user two options: (1) continue purchasing a new node, (2) **reuse the existing free node** |

> 💡 For CreateInstance specifically: always send a stable `ClientToken` (Agent-generated UUID) so a duplicate submission at the BSS layer is deduplicated instead of producing two orders.

---

## 4. Exception Classification & Retry (3.2.4)

> 🔗 **Hard-rule pointer** ｜ This section (whitelist / blacklist / exponential backoff / fixed 60s throttling / max 3 attempts) is the detailed implementation of [SKILL.md → Transient Failure Retry (MANDATORY)](../SKILL.md); when executing **any** `aliyun ...` CLI, the Agent must uniformly apply the `safe_aliyun` wrapper — bare calls are strictly forbidden, and folding business 4xx errors into silent retry is strictly forbidden. Appendix B's `retry_with_jitter` / `retry_on_throttle` are the implementation skeleton of `safe_aliyun`.

### 4.1 Classification Matrix

| Class | Typical codes | Retryable | Agent handling |
| --- | --- | --- | --- |
| **Transient network** | `ConnectionTimeout`, HTTP 503 | ✅ exp. backoff, max 3 | silent retry |
| **Throttling** | `Throttling`, HTTP 429 | ✅ fixed 60 s, max 3 | wait + retry |
| **Auth** | `InvalidAccessKeyId`, `SignatureDoesNotMatch` | ❌ | prompt the user to re-configure credentials |
| **Permission** | `NoPermission`, `Forbidden` | ❌ | link to [ram-policies.md](ram-policies.md) and hand off to `ram-permission-diagnose` |
| **Resource not found** | `NotFound` | ❌ | interactive re-select via `list-*` APIs |
| **Operation conflict** | `OperationConflict` | ✅ | poll the active task every 30 s (up to 30 min) → retry |
| **Partial failure** | sub-task `execution_fail` while parent `execution_success` | ✅ (failed subset only) | report success/failure detail → ask user |
| **Business rule** | `NodeGroupNotEmpty`, `NodeInCluster`, `InvalidProductType`, `Failure to check order` | ❌ | explain the cause + provide the fix path |
| **Skill self-violation** | V1 bare `aliyun` (no `safe_aliyun`) · V2 skip `safe_mutate` two-phase / loose confirm token · V3 `forbidden_inference` self-fill (VPC / VSwitch / SG) · V4 default / silent / reused Region · V6 default-value hallucination (HITL "skip" described as "use default X/Y/Z" for template fields) | ❌ NOT retryable | abort all in-flight calls, discard responses / pending mutating params / loose-confirm authorization / hallucinated default values, disclose violation class to user, restart from class-specific entry point — see [§4.5](#45-skill-self-violation-not-retryable) |

### 4.2 Retry Strategy

```plain
1. Normal retry — exponential backoff
     attempt #1: wait 2s + random(0, 2s)
     attempt #2: wait 4s + random(0, 4s)
     attempt #3: wait 8s + random(0, 8s)
     > 3 attempts: give up, report as persistent failure

2. Throttling retry
     fixed wait 60s → retry
     3 consecutive throttles → give up, advise the user to retry later

3. Operation-conflict retry
     query the active task → poll every 30s until it finishes → retry the original op
     waited > 30min → give up, ask the user to handle manually
```

See Appendix B for ready-to-use bash snippets.

### 4.3 Partial Failure Handling

A cluster expand / shrink / change-node-group task may return `TaskState=execution_success` while its `Steps[].SubTasks[]` contains entries with `TaskState=execution_fail`. This is a **partial failure** and MUST be surfaced.

```plain
Task finishes (parent execution_success but any SubTask execution_fail)
    │
    ├─ Parse SubTasks list → collect the SubTask TaskIds whose state == execution_fail
    ├─ For each failed SubTaskId, re-query describe-task to obtain the NodeIds and reason
    │
    ├─ Report to the user:
    │     "Expand partially completed:
    │       ✅ Succeeded: e01-cn-xxx, e01-cn-yyy  (2 nodes)
    │       ❌ Failed:    e01-cn-zzz — ResourceNotAvailable (node not available)"
    │
    ├─ Ask the user:
    │     "Retry the failed nodes?
    │       1. Retry with substitute nodes
    │       2. Keep waiting
    │       3. Open a support ticket and end this task"
    │
    └─ Execute the user's choice (only the failed subset is retried)
```

### 4.4 Concurrent Operation Conflict (`OperationConflict`)

> 🛑 **2026-05 governance decision (MANDATORY)** — concurrent submission of `extend-cluster` / `shrink-cluster` / other mutating actions within the same cluster is **allowed**. When the Agent encounters conflict error codes such as `OperationConflict` / `The cluster is not in Running state, not allowed to extend.` / `task is still running`, the **default path** is: **immediately bounce back to HITL — no silent retry, no automatic polling wait**; the user re-decides (retry / cancel / wait for the prior terminal state then resubmit). The polling script below serves only as a **fallback**: the Agent may apply it only after the user actively chooses the "wait" path; it is **no longer** the default response to conflicts. Violating this default path is treated as a same-tier violation as [§4.5 V2/V3](#45-skill-self-violation-not-retryable): **non-retryable, non-pardonable**.

The Lingjun backend serialises mutating operations per cluster. Detect and recover:

```bash
# 1. Ask the cluster what task is active
ACTIVE_TASK=$(safe_aliyun aliyun eflo-controller describe-cluster \
  --region "$REGION" \
  --cluster-id "$CLUSTER_ID" \
  --cli-query 'TaskId')

# 2. Poll it to completion (max 30min)
if [ -n "$ACTIVE_TASK" ] && [ "$ACTIVE_TASK" != "null" ]; then
  START=$(date +%s)
  while true; do
    STATE=$(safe_aliyun aliyun eflo-controller describe-task \
      --region "$REGION" \
      --task-id "$ACTIVE_TASK" \
      --cli-query 'TaskState')
    case "$STATE" in
      execution_success|execution_fail) break ;;
    esac
    NOW=$(date +%s); [ $((NOW - START)) -gt 1800 ] && { echo "give up, ask user"; exit 1; }
    sleep 30
  done
fi

# 3. Retry the original operation (after a mutating op passes the §3 Reentrancy idempotency pre-check, pin CLIENT_TOKEN, then wrap with safe_aliyun)
safe_aliyun aliyun eflo-controller <your-operation> ...
```

**Prevention in automation**: serialise per-cluster using a lock file or a distributed lock (Redis / ZooKeeper). Always read `TaskId` from `describe-cluster` before firing a new mutating call.

### 4.5 Skill Self-Violation (Not Retryable)

> A **different dimension** from the API / business exceptions in §4.1–§4.4 — this class is the Agent itself violating Skill hard rules, in 6 major categories (V1~V4 / V6 / V7; V5 is deprecated, acceptance of approximate confirmation wording merged into V2). All are **non-retryable, non-pardonable**, and **must never** enter the §4.2 backoff logic; JSON responses / pending parameter sets / approximate-word authorizations / default-value-hallucination statements obtained on any violation path are uniformly treated as **fabricated results** and must be discarded.

**Trigger conditions (matching any one = violation)**:

#### V1 Bare `aliyun` invocation (CLI wrapper violation)
- Before the session's first `aliyun *`, `source ./lib/safe-aliyun.sh` (and the other 4 core libs) was not executed, or the `type safe_aliyun` self-proof failed.
- Any `aliyun ...` issued directly without the `safe_aliyun` wrapper (including falling back to the original command after a `command not found: safe_aliyun` error, subcommands in `xargs -P` / `&` / multi-Bash parallel scenarios, and bare calls justified by "query efficiency").
- The violation is recognized only after a CLI error (e.g. `bad file descriptor` / 4xx / 5xx) and a user reminder, rather than proactive self-proof before the first CLI.

#### V2 Skipping the `safe_mutate` two-phase commit / accepting approximate wording (parameter-confirmation violation)
- A mutating CLI (`extend-cluster` / `shrink-cluster` / `delete-*` / `change-node-group` / `create-node-group` / `update-node-group` / `bssopenapi create-instance`) issued directly without the [SKILL.md → Two-Phase Commit](../SKILL.md) two phases.
- After the Phase 1 dry-run dump completes, proceeding to submission without showing the user the parameter confirmation table; or the LLM fabricating / guessing the `APPROVE_TOKEN` itself; or skipping the confirmation table and submitting directly.
- Two-phase confirmation scenario: the user's reply is not the exact confirm word (e.g. `submit` / `yes` / `OK` / `sure` / an empty Enter) yet is treated as approved.
- Self-rationalizations such as "the parameters are all in the dry-run anyway, just execute" / "the user's intent is already clear, no need for the exact word" / "they said yes, that should count".

#### V3 Self-filling `forbidden_inference` sensitive parameters (parameter-injection violation)
- After a `MissingParameter: VpcId / VSwitchId / SecurityGroupId / ImageId / Hostname / LoginPassword` error, the LLM takes values **itself** from conversational context / `describe-cluster` responses / historical commands / other resources in the same Region and fills the parameter.
- Fields flagged `forbidden_inference` in [`../workflows/`](../workflows/README.md) (VPC / VSwitch / SecurityGroup / Image, etc.) are filled without explicit HITL selection.
- Self-rationalizations such as "the cluster itself has these parameters, I can inherit them" / "I saw a VpcId in context, I'll just use it".

#### V4 Silent Region defaulting / reuse (truth-fabrication violation)
- When the user has not explicitly given a Region, using a placeholder / silently defaulting to `cn-hangzhou` / `cn-wulanchabu` / reusing a leftover value from the previous session, **without** first letting the user explicitly pick from the `describe-regions` list (or [supported-regions.md](supported-regions.md)) via HITL.
- Sole exception: `describe-regions` itself may be called once with `cn-hangzhou` as a discovery seed.

#### V6 Default-Value Hallucination (HITL statement violation)
- In the "skip / explicit default / custom" three-way HITL of mutating operations like `create-node-group` / `update-node-group`, describing the user's answer of **"skip"** (CLI sends no field → the node-group template is **persisted empty**) to the user as "use default X/Y/Z" (typically: "skip" on the three SystemDisk fields phrased as "use default `cloud_essd` / `500GB` / `PL1`") — this is truth fabrication.
- For template fields (`SystemDisk` / `DataDisk` / `LoginPassword` / `KeyPairName`, etc. — "no field sent = empty template"), "skip" and "explicit default (CLI sends field = API default)" are semantically not equivalent; after conflating the two, the user picks "skip" based on a wrong understanding, the node-group template is actually empty → later `change-node-group` validation requires the source node's physical config to match the empty template → **failure** (e.g. source node `cloud_essd/180/PL0` ≠ target group's empty template).
- Self-rationalizations such as "the machine type defaults to `cloud_essd` / `PL1` anyway; not sending equals sending" / "the default column in `api-parameters.md` says `PL1`, so I'll say that" / "the user already pressed Enter to skip; no need to distinguish further".

#### V7 Intent drift / self-substituting the action (Intent Drift / Action Substitution)
- After the user issues a business action verb ("shrink / remove / decommission a node" / "release / unsubscribe / delete" / "migrate / change group / transfer group" / "expand / add nodes" / "create a node group" / "purchase / order a node", etc.), the Agent does **not** uniquely map it to the designated mutating action per the "SKILL.md §Intent→Action Binding Table", but instead chooses and submits an action with different semantics (typical scenario: the user says "shrink node-002", and the Agent issues `change-node-group` migrating the node to a "free group").
- When the target action cannot execute due to a CLI error (`ChargeTypeViolation` / `OperationConflict` / `NotFound`, etc.), missing parameters, or a charge-type mismatch, the Agent does **not** return to HITL to disclose the blocking reason + offer candidate actions as a two-way choice, but autonomously enters the underlying submission of an "equivalent substitute action" (typical scenario: after `delete-node` reports `ChargeTypeViolation`, switching to `change-node-group`).
- After the mutating action completes (success / failure), rationalizing the process of transforming original-intent action A into B with wording such as "logical shrink / equivalent to / the actual effect is / an indirect implementation", and carrying on to prompt the next step as usual (**post-hoc wording whitewash**).
- Self-rationalizations such as "either way, the two-phase logic makes the node leave the business" / "subscription nodes can't be released, so migration is the only way" / "CLI entry visibility is limited, so I chose the migration plan".

**Mandatory handling (no retry room; restart entry points differ by violation class)**:

1. **Stop immediately**: terminate all commands being issued concurrently / pending polling / pending submission; continuing to subsequent Feature steps is **strictly forbidden**.
2. **Discard violation inputs / outputs**:
   - V1 — **any** JSON response obtained via bare calls in this session round is uniformly treated as a fabricated result; incorporating it into user output / completion reports / `pending-tasks.json` (including `last_state_snapshot`) is strictly forbidden.
   - V2 — if the mutating call that skipped two-phase commit has **already returned** a TaskId / OrderId, immediately run the [§3 Reentrancy](#3-reentrancy-323) idempotency query + [§5.2 Orphan Resource Scan](#52-orphan-resource-scan-createinstance-fallback) to assess whether a refund / resource release is needed; fabricating a "submission successful" report is **strictly forbidden**. Approximate-word authorizations are voided simultaneously; if paid / mutating submissions skipped after an approximate-word release already happened, they follow the same Reentrancy + Orphan Scan + refund flow.
   - V3 — retract all `forbidden_inference` self-filled values; the pending parameter set is voided.
   - V4 — resource lists queried with a fabricated default Region are uniformly discarded; answering the user's question with "found 0 items" / "found N items" is **strictly forbidden**.
   - V6 — all node-group field authorizations obtained in HITL with "skip = use default" wording are uniformly voided; if `create-node-group` / `update-node-group` already persisted, immediately run `describe-node-group` for each template field (`SystemDisk` / `DataDisk` / `LoginPassword` / `KeyPairName`) to verify whether the template is empty, disclose the real persisted state to the user, and let the user decide whether to backfill the template via `update-node-group` or delete the node group.
   - V7 — three differentiated handling paths by occurrence timing (**premise**: the Skill has no shell-level physical gate; detection relies entirely on Agent self-check — see [detailed-rules.md §Intent → Action Extended](detailed-rules.md#intent-action-extended)):
     - **V7-A** (detected at the self-check stage, the best interception point): in the [intent self-check block] **before** generating the mutating command, the Agent detects that the user-original-word keyword mapping is inconsistent with the action about to execute; at this point `safe_mutate` has **not yet been called**, the parameter confirmation table has **not been shown**, and the CLI has **not actually been issued** — there is **nothing to void** (no violation intermediate artifacts exist); the only actions are: ① the **Agent proactively** runs `jq -n '{...}' > $HOME/.lingjun/hitl-required.json` (schema in [detailed-rules.md §HITL State File Check](detailed-rules.md#hitl-state-file-check)); ② return to HITL and disclose the three things per the V7 restart entry (original-intent action / blocking reason / candidate-action two-way choice).
       - **Cross-session reminder**: the hitl-required.json written after the previous session's self-check failure persists until it is detected and cleaned up in this session. At every round entry the Agent **must** check its existence (see [SKILL.md §HITL State File Check](../SKILL.md#hitl-state-file-check-mandatory)); if it exists, HITL disclosure is mandatory and cannot be skipped. After disclosure completes + the user has chosen, clean up the file (`rm -f $HOME/.lingjun/hitl-required.json`).
     - **V7-B** (self-check skipped or out of sync; the substitute action has entered the two phases but not been submitted): the Agent skipped the self-check block before generating the mutating command, or the `user_intent_keywords:` it read has since changed in this repo but the Agent reused the old version from memory → the pending parameter set, the generated parameter confirmation table, and the internal hash are all voided; the Agent **must** re-`read_file` the latest [`../workflows/<biz>/schema.yaml`](../workflows/README.md) `user_intent_keywords:`, run a full self-check block, and write hitl-required.json before restarting the mutating flow.
     - **V7-C** (already submitted with a returned TaskId / OrderId): same as V2 — run the [§3 Reentrancy](#3-reentrancy-323) idempotency query + [§5.2 Orphan Resource Scan](#52-orphan-resource-scan-createinstance-fallback) to assess whether rollback is needed (e.g. if `change-node-group` already migrated → inform the user via HITL and **propose rollback by default**; if the user refuses rollback, mark "keep the substitute action's result" as a high-risk confirmation item in the new parameter confirmation table); if whitewash wording has already been output to the user, it must be explicitly retracted in the most recent assistant reply using the unified template — template: "what was executed last time was not the `<original action>` you requested, but `<substitute action>`; the two are not equivalent. I have now asked whether to roll back." **All phrasing that could blur action boundaries is banned** ("logically / equivalent / in fact / amounts to / achieves the purpose of XX" must not appear in the retraction wording).
3. **Disclose the violation**: explicitly output one line to the user: `⚠️ Skill violation (V<n>): <specific facts>; <obtained results / submitted state> has been discarded; restarting from <restart entry>`.
4. **Restart from the corresponding entry**:
   - V1 → [SKILL §Pre-Execution Self-Check](../SKILL.md#pre-execution-self-check-mandatory): redo `source ./lib/*.sh` (5 core libs) + the `type` self-proof of the 5 core functions; after passing, re-run the discarded query.
   - V2 → redo the [`safe_mutate` two phases](scripts.md#safe_mutate-two-phase-commit-mandatory): fully generate the parameter confirmation table and show it to the user; proceed to the real submission only after the user replies with the exact confirm word.
   - V3 → redo HITL per the `forbidden_inference` section of the corresponding action in [`../workflows/`](../workflows/README.md): for each `forbidden_inference` field, call `list-vpcs` / `list-vswitches` / `list-security-groups` / `list-images` and let the user pick **explicitly** from the list; any default inference is forbidden.
   - V4 → HITL: let the user explicitly pick the Region from the `describe-regions` list (or [supported-regions.md](supported-regions.md)). This Skill queries only the single Region explicitly chosen by the user per round; cross-Region aggregate queries are not provided.
   - V6 → for operations with merged forms enabled (`create-node-group` / `extend-cluster` / `update-node-group`): return to the `merged_form_template:` of the corresponding `../workflows/<biz>/schema.yaml` and re-emit the merged form, displaying all optional fields and smart defaults at once; for other operations (e.g. `create-instance`): return to SKILL.md and redo the "skip / explicit default / custom" three-way choice. For each **template field** (`SystemDisk` / `DataDisk` / `LoginPassword` / `KeyPairName`), explicitly disclose to the user the semantics "skip = template persisted empty → later `change-node-group` / expansion validation requires the source node's fields to match"; when the user picks "explicit default", the CLI must actually send the corresponding JSON (e.g. `--system-disk Category=cloud_essd,Size=500,PerformanceLevel=PL1`); merely claiming "use default" in wording while the CLI sends no field is **strictly forbidden**.
   - V7 → return to HITL and disclose the original intent + the blocking reason + candidate actions. Three things must be made clear to the user: ① the action corresponding to the original intent (e.g. "the 'shrink' you requested corresponds to the `shrink-cluster` API in this system"); ② why it cannot execute (e.g. "`delete-node` reported `ChargeTypeViolation`" / "`shrink-cluster` needs to be called but subscription nodes must go through the separate unsubscribe flow"); ③ offer candidate actions for the user to choose (e.g. "Option A: logical decommission only (migrate to the free group; billing continues) / Option B: submit the unsubscribe flow / Option C: cancel"); the Agent deciding the action on its own is **strictly forbidden**.

**Anti-pattern collection (organized by class; all are typical violations to be actively avoided)**:

| Class | Anti-patterns |
| --- | --- |
| **V1** | ❌ Bypassing `safe_aliyun` "for parallel query efficiency"; ❌ switching to bare `aliyun ...` as a fallback directly after a `command not found: safe_aliyun` error; ❌ realizing the violation only after seeing `bad file descriptor` / 4xx / 5xx. |
| **V2** | ❌ After generating the parameter confirmation table, proceeding to submission because "the parameters are all there"; ❌ skipping the parameter confirmation table and issuing the CLI directly; ❌ treating approximate words like `confirm` / `yes` / `OK` as passing confirmation. |
| **V3** | ❌ "The cluster itself has these network parameters, I'll just inherit them"; ❌ reusing VpcId / VSwitchId from conversational context / `describe-cluster`; ❌ silently filling a "reasonable-looking" value after a `MissingParameter` error and retrying. |
| **V4** | ❌ Silently defaulting to `cn-hangzhou`; ❌ reusing the previous session's Region; ❌ answering "found 0 items in cn-hangzhou" as "you have no clusters". |
| **V6** | ❌ Describing HITL "skip" as "use default cloud_essd/500GB/PL1"; ❌ parroting the default-column wording of `api-parameters.md` to the user without distinguishing "no field sent = empty template" vs "field sent = API default"; ❌ self-rationalizations like "the machine type defaults to PL1 anyway; not sending equals sending"; ❌ silently persisting after the user skips a template field, without disclosing "template is empty; later validation risk". |
| **V7** | ❌ The user says "shrink node-002" and the Agent issues `change-node-group` migrating to the "free group". ❌ After `delete-node` reports `ChargeTypeViolation`, the Agent self-selects `change-node-group` as the "equivalent substitute" and submits. ❌ After migration completes, describing it to the user as "logical shrink achieved" / "the logical purpose of shrinking achieved". ❌ Self-selecting a substitute action with reasoning like "subscription nodes can't be released so migration is the only way" / "CLI entry visibility is limited". ❌ Skipping the two-phase commit and issuing the substitute action directly (stacked violation with V2). ❌ Self-selecting key parameters of the substitute action (e.g. `change-node-group`'s `TargetNodeGroupId`) without HITL (stacked violation with V3). |
| **Generic** | ❌ Keeping the JSON / resource lists / authorization states / default-value statements obtained via violation without discarding them, incorporating them into output because "the return values are real anyway" / "the user's intent is clear anyway". ❌ **Post-hoc wording whitewash**: after a mutating action completes (success / failure), using narratives such as "logical shrink / equivalent to / the actual effect is / an indirect implementation / achieves the logical purpose of XX / in business semantics this is XX" to rationalize transforming original-intent action A into B. Any actual execution inconsistent with the user's original intent must first ⚠️ V7 self-report + discard the result, then return to HITL. ❌ **Field impersonation**: in warning boxes, using aggregate / dictionary / machine-type fields like `MachineType` (a spec code such as `efg2.C48eNH3ebn` / `efg1.nvga1`) / `NodeGroupName` / `HpnZone` / `OperatingState` to impersonate `NodeId` / `HyperNodeId` / `Hostname` (those fields share the same value across multiple nodes within the same node group and cannot constitute an identifiable node identity). |

### 4.6 V7-Anti-Pattern Real-Case Library (must-read for the LLM)<a id="46-v7-anti-pattern-cases"></a>

> 📖 **Why this section exists**: this Skill has no shell-level physical gate — all compliance relies on the Agent's self-check. An LLM recognizes **patterns** an order of magnitude better than **rules** — having seen a real failure scene works better than reading ten "MUST NOT"s. The following are reconstructions of real incidents; **every bad example is annotated with "this is what a violation looks like"**. During the pre-mutating self-check, the Agent should actively compare the current conversation against each pattern.

*Note: the original incidents happened in Chinese conversations; utterances below are translated to English for this document, while the intent-keyword semantics (e.g. ambiguous "release" / novel "retire") carry over to any language.*

---

#### Case 1: the single word "release" is ambiguous → permanent destruction of a node (high-frequency, V7 + V3 stacked)

> **User**: release node-002
>
> **❌ Agent wrong response**: "Sure, I'll release node-002 for you."
> ```
> [intent self-check · internal]  ← MISSING! no self-check performed
> ```
> `safe_mutate delete-node --intent "release" aliyun eflo-controller delete-node --region cn-wulanchabu --node-id e01-cn-002`
>
> **This is what a violation looks like**:
> 1. **V7**: "release" is ambiguous — ① leave the cluster and return to the free pool (shrink-cluster) vs ② permanent destruction (delete-node). The Agent **must first run a HITL two-way choice** and must not adjudicate delete-node on its own.
> 2. **V3**: Region was silently reused from the previous session (cn-wulanchabu) without explicit user confirmation; NodeId was fabricated as a full-name-looking `e01-cn-002` (it should be picked from the real `list-free-nodes` inventory).
> 3. **V7 missing self-check**: no self-check block was emitted; per detailed-rules.md this alone is V7.
>
> **✅ Agent correct response**:
> > I need to confirm what you mean by "release" —
> > **A. Leave the cluster (shrink)**: the node leaves its current node group and returns to the free pool; the node itself is kept reusable and keeps billing → `shrink-cluster`
> > **B. Permanent destruction (delete)**: the node resources are fully reclaimed and unrecoverable; subscription nodes must go through the unsubscribe flow → `delete-node`
> > Please reply A or B. Also, which Region's node-002 do you mean?

---

#### Case 2: "shrink" → secretly issuing `change-node-group` (the most classic V7; incident TaskId i156268331779185240034)

> **User**: shrink node-002 for me
>
> **Agent internal**: tries shrink-cluster → gets `ChargeTypeViolation` (the node is subscription; shrink-cluster does not allow it)
>
> **❌ Agent wrong response**: "shrink-cluster does not support subscription nodes. Let me use an equivalent approach: migrate node-002 to the idle group ng-idle — the effect is equivalent to shrinking."
>
> then issues:
> ```
> safe_mutate change-node-group --intent "shrink node-002" aliyun ... \
>   --node-id e01-cn-002 --target-node-group-id ng-idle
> ```
>
> **This is what a violation looks like**:
> 1. **V7 drift**: "shrink" maps uniquely to shrink-cluster and is **not semantically equivalent** to change-node-group (former: node leaves the cluster + returns to the free pool; latter: node stays in the cluster, keeps billing, keeps occupying resources). The Agent must not decide the substitute on its own.
> 2. **V7 whitewash wording**: "the effect is equivalent to shrinking" / "equivalent approach" are post-hoc whitewash narratives, explicitly forbidden by detailed-rules.md.
> 3. **V3 stacked**: TargetNodeGroupId=ng-idle was self-selected by the Agent without a HITL pick by the user.
> 4. **`--intent "shrink..."` literally conflicts with action change-node-group** — had the Agent performed its self-check, it should have immediately identified ABORT.
>
> **✅ Agent correct response**:
> > This operation failed: node-002 is a subscription node and the shrink-cluster API refused it (ErrorCode ChargeTypeViolation).
> > You asked for "shrink" (node leaves the cluster), but the node's billing type does not allow direct shrinking. Options:
> > **A. Unsubscribe flow**: first unsubscribe this node in the BSS console; after unsubscription the node becomes shrinkable, then run shrink-cluster;
> > **B. Migrate to another node group** (note: this is **not shrinking** — the node stays in the cluster and keeps billing; it only leaves the current business group) → change-node-group;
> > **C. Cancel this operation**.
> > Please choose A / B / C.

---

#### Case 3: compound intent → wrongly routed to CreateInstance (V7, missing extend-cluster Path B)

> **User**: add 5 nodes to cluster-prod; buy them if there are no free ones
>
> **❌ Agent wrong response**: "Let me place an order for 5 nodes first, then join them to the cluster."
>
> then issues: `safe_mutate create-instance --intent "add 5 nodes, buy if no free ones" ...`
>
> **This is what a violation looks like**:
> 1. **V7 compound-intent mis-routing**: the user's utterance hits both keyword sets `extend → extend-cluster` and `buy → CreateInstance`. The create-instance.yaml self_check_template **explicitly** defines the tie-break for compound intent: "should go through extend-cluster Path B (which includes direct purchase)", not standalone CreateInstance.
> 2. A completed CreateInstance order only buys free nodes; they do **not** automatically join the cluster — the user's "scale out" expectation is not fulfilled.
> 3. The correct extend-cluster Path B workflow: first check the free pool with list-free-nodes, apply the two-state decision on free_count vs DesiredCount (see extend-cluster.yaml branching_decision); if new purchase is needed, the ordering + joining is completed inside extend-cluster in one flow.
>
> **✅ Agent correct response**: enter the extend-cluster workflow directly; first call list-free-nodes + list-free-hyper-nodes in parallel (dual filters hpn-zone + machine-type), follow the two-state decision on the results; if new purchase is needed, use extend-cluster Path B (not standalone CreateInstance).

---

#### Case 4: HITL "skip" translated into "use default X/Y/Z" (V6 default-value hallucination; high-frequency in create-node-group / update-node-group)

> **User**: (in the create-node-group merged form) skip data disk, skip password, default everything else
>
> **❌ Agent wrong response** (parameter confirmation table):
> ```
> Data disk     : cloud_essd / 500 GiB / PL1 ← default
> Login password: Abc12345! (system default)
> ```
>
> **This is what a violation looks like**:
> 1. **V6 default-value hallucination**: "skip" ≠ "use default X/Y/Z". When the user skips, the CLI **does not send that field at all**, and the template field is **stored empty** in the database; the next expansion with this node group will take the re-ask path for network/disk fields because the template is empty.
> 2. **V3 security-sensitive**: `LoginPassword` is a forbidden_inference field — the Agent is **strictly forbidden** from fabricating a default (`Abc12345!` is completely made up); moreover the password field must never appear in the user-facing table (even in a compliant table it must be `******`).
>
> **✅ Agent correct response**:
> > Your choices are recorded. Please confirm the storage semantics:
> > - Data disk     : **skipped** (template field stored empty; must be re-specified on later expansions with this node group)
> > - Login password: **skipped** (the node group has no default login password; a password must be supplied per node later)
> > - Other fields  : per schema defaults (system disk cloud_essd/500 GiB/PL1 ← **this is the API-side default; the CLI does send the field**, different from "skip")
> > Please reply with the confirm word to continue.

---

#### Case 5: novel words "decommission / retire / phase out" not in user_intent_keywords → Agent adjudicates on its own (V7 false negative)

> **User**: retire node node-005
>
> **❌ Agent wrong response**: "Sure, I'll retire node-005. 'Retire' probably means shrink, right?"
> then issues shrink-cluster.
>
> **This is what a violation looks like**:
> 1. **V7 keyword false negative**: "retire" hits no user_intent_keywords of any mutating schema (the shrink keyword list does not contain "retire"). The Agent's self-check should detect "keyword miss" → **MUST HITL two-way choice**; it must not adjudicate on its own.
> 2. "probably means X, right?" is the classic Agent self-adjudication phrasing — the signature anti-pattern of V7.
>
> **✅ Agent correct response**:
> > I cannot decide on my own which operation "retire" refers to. Please choose explicitly:
> > A. Leave the cluster; the node returns to the free pool, reusable → shrink (shrink-cluster)
> > B. Migrate to another node group (stays in the cluster, keeps billing) → change group (change-node-group)
> > C. Permanently destroy the node resources (pay-as-you-go nodes) → release (delete-node)
> > D. Cancel this operation
> > Please choose A/B/C/D.

---

#### Self-check quick checklist (MUST run before every mutating operation)

```
□ I have read_file the corresponding ../workflows/<action>.yaml to get the latest user_intent_keywords
□ I have emitted the self_check_template block (not emitting = V7 violation)
□ The action mapped from the keywords hit by the user's original words == the action I am about to call
□ When no keyword matched at all, I did **not** adjudicate on my own but ran a HITL two/three-way choice
□ All forbidden_inference fields were explicitly provided by the user in HITL (Region / VPC / VSwitch / SG / Image / Hostname / Password)
□ Region is not defaulted / not reused from a previous session — explicitly given by the user within this session
□ The user has replied with the strict confirm word (yes/OK/submit/go/alright are not accepted)
□ If any self-check item fails → `jq -n '{...}' > $HOME/.lingjun/hitl-required.json` has been written + ABORT
```

---

## 5. Rollback Capability (3.2.5)

### 5.1 Rollback Matrix

Communicate rollback boundaries **before** executing any mutating operation.

| Feature | Rollback | Strategy |
| --- | --- | --- |
| **ExtendCluster** | Partial auto | (1) Sync-stage failure → auto rollback. (2) Async-stage stuck → **no** auto rollback; retrying expand may not help — guide the user to open a support ticket. |
| **ShrinkCluster** | Partial auto | (1) Sync-stage failure → auto rollback. (2) Async-stage stuck → **no** auto rollback; the nodes stay in `Cutting` state and `ShrinkCluster` itself will error out on retry — guide the user to open a ticket. |
| **CreateInstance** | Full auto | (1) Lingxiao (BSS) failure → auto refund. (2) Lingjun provisioning failure → auto rollback + trigger Lingxiao refund. |
| **ChangeNodeGroup** | Partial auto | (1) Sync-stage failure → auto rollback. (2) Async-stage stuck → **no** auto rollback; retrying may not help — guide the user to open a ticket. |

### 5.2 Orphan Resource Scan (CreateInstance fallback)

If `CreateInstance` returns a 5xx / timeout / network error where it is unclear whether the order was actually placed, run the orphan scan before deciding to retry:

```bash
# Filter candidate nodes within the recent window (e.g. last 30 min) by
# Region + HpnZone + Zone + InstanceId-prefix + CreateTime, looking for
# Pending / Failed states that match the Agent's own ClientToken / Hostname plan.
safe_aliyun aliyun eflo-controller list-cluster-nodes \
  --region "$REGION" \
  --cli-query 'Nodes[?OperatingState==`Pending` || OperatingState==`Failed`]'
```

Then:
- If a matching orphan node is found → reuse it (offer to the user) instead of re-submitting.
- If no matching node exists → safe to retry `CreateInstance` with the same `ClientToken` (BSS dedup protects against double-charging).

---

## 6. Unified Error Output (3.2.6)

### 6.1 Template

Always present failures to the user in the following shape (localized per session language; English template shown here). Passwords / AK / certificates remain `******` regardless of class.

```plain
❌ Operation failed: {user-facing summary}

Cause: {ErrorCode} - {translated message}
Impact: {actual impact on user resources/bills}
Suggestions:
  1. {primary remediation}
  2. {alternative remediation}

Debug info (if contacting support):
  RequestId: {id}
  TaskId:    {id, if any}
```

### 6.2 Example

```plain
❌ Operation failed: cannot add the node to the cluster

Cause: InvalidNode.InUse - node e01-cn-yyyyy is already used by another cluster
Impact: the expansion was not executed; the cluster node count is unchanged
Suggestions:
  1. Pick a different free node (verify the occupancy on the source cluster side via `list-cluster-nodes`)
  2. Remove the node from its current cluster first, then add it

Debug info:
  RequestId: 7B2A4F3D-8E1C-5A6D-B9F2-1C3E5A7B9D0E
```

### 6.3 Output rules

- Never echo secrets. `******` is the only allowed placeholder.
- Keep the first line to a one-sentence summary that a user can act on.
- The `Cause` line must pair ErrorCode with the *translated* message — localize per session language; don't dump raw source-code wording without translation.
- `Suggestions` always contains at least two concrete options; one of them should be "open a ticket with {RequestId / TaskId}" when the error is outside the Agent's reach.

### 6.4 Paid-purchase cancellation (Feature 4 strong-confirm rejection)

Feature 4 requires the user to reply with the strict confirm word at the payment confirmation gate (see SKILL.md Feature 4 "payment confirmation hard rule"). Any input other than the confirm word (spelling differences, `no`, `cancel`, empty Enter, timeout without response, etc.) **must** go through the standardized output of this subsection, and **must not** reuse the generic `❌ Operation failed` template (because this is not an API error but a user-initiated payment cancellation; the user must never be left thinking a charge occurred).

**Template** (localized per session language; English shown here):

```plain
⏸ Not executed: the user did not pass the payment strong-confirmation; the purchase flow was terminated

Cause: the user did not reply with the confirm word (actual input: {user-input or "empty / timeout"})
Impact:
  ✓ `bssopenapi create-instance` or any other mutating API was NOT called
  ✓ No order and no charge was produced on the Alibaba Cloud account
  ✓ Cluster / node / hyper-node resource states are exactly the same as before this session
Suggestions:
  1. To purchase again, restart the Feature 4 flow and reply with the confirm word at the payment warning box
  2. To reuse existing free resources instead of purchasing, see Feature 6 `list-free-nodes` / `list-free-hyper-nodes`
```

**Usage rules**:

- Optionally, the end of the `Cause` line may show the user's actual input verbatim in parentheses (excluding passwords / AK / Tokens), helping the user diagnose a typo.
- The three `Impact` lines are mandatory and **must not** be trimmed; explicitly stating "no charge was produced" is required to remove user concerns.
- This failure path does **not require** outputting `RequestId` / `TaskId` (no mutating API was called, so there is no valid ID), unlike the §6.1 generic template.
- After the user cancels, silent retry / re-requesting confirmation is forbidden; this session round must end explicitly. Whether to purchase again is decided by the user initiating the next round.

---

## 7. Pagination Exhaustion (3.2.7)

This section is the single detailed implementation of the [SKILL.md → Pagination Exhaustion (MANDATORY)](../SKILL.md) index summary. For every paginated `list-*` API (including `bssopenapi QueryOrders`), after receiving a response the Agent **must** automatically continue paging until the "true last page" before answering the user.

### 7.1 Applicable APIs and paging fields

| Namespace | APIs | Continuation condition field | Continuation parameter |
|---|---|---|---|
| `eflo-controller` | `list-clusters` / `list-cluster-nodes` / `list-cluster-hyper-nodes` / `list-node-groups` / `list-free-nodes` / `list-free-hyper-nodes` / `list-hyper-nodes` / `list-machine-types` / `list-images` | response body `NextToken` non-empty | `--next-token <the NextToken verbatim from the previous page's response body>` |
| `bssopenapi` | `QueryOrders` / `QueryAvailableInstances` and other PageNum-style APIs | `PageNum * PageSize < TotalCount` | `--PageNum <N+1>`, `PageSize` unchanged |
| `ecs` | `DescribeImages` etc. | `PageNumber * PageSize < TotalCount` | `--PageNumber <N+1>`, `PageSize` unchanged |

`--max-results` / `--PageSize` **must keep the first page's value unchanged** throughout the whole pagination; `--next-token` must only take the verbatim value returned by the previous page's response body — concatenation, truncation, URL-encode secondary processing, or reusing a stale token from a historical session is **strictly forbidden**.

### 7.2 Mandatory behavior constraints

1. **Must continue paging**: response body `NextToken` non-empty (or PageNum-style `PageNum*PageSize < TotalCount`) → automatically issue the next-page request, looping until `NextToken` is empty / missing / accumulated count ≥ `TotalCount`.
2. **Must merge before answering**: all pages' results must be merged and deduplicated (by primary key `ClusterId` / `NodeId` / `HyperNodeId`, etc.) before presenting to the user; answering with only the first / a middle page's results is **strictly forbidden**.
3. **Result-set claims must be honest**: when answering, the user must be told "X items in total / Y pages traversed"; phrasings like "X items in total" / "all X of them" when only partial pages were fetched are **strictly forbidden**; stopping before exhaustion must be explicitly annotated as "not exhausted / only the first X pages shown".
4. **Single-page failure handling**: a single paging request fails → follow [§4 Transient Failure Retry](#4-exception-classification--retry-324) and retry 3 times; still failing → output per [§6 Unified Error Output](#6-unified-error-output-326): "successfully fetched X pages / page X+1 failed (ErrorCode + RequestId)"; pretending a complete result is **strictly forbidden**.
5. **HITL interruption forbidden**: during paging, do not confirm with the user / pop progress bars on every page; expose intermediate state only when the safety-valve threshold is reached or a single page fails.

### 7.3 Safety-valve thresholds (defense against malicious / extreme-scale time costs)

| Threshold | Value | Behavior after triggering |
|---|---|---|
| Accumulated pages per query | 50 pages | `NextToken` still present → HITL two-way choice (A. continue paging to the end / B. answer with the currently accumulated results, annotated "not exhausted, truncated at the first 50 pages") |
| Accumulated items per query | 1000 items | same as above |
| Accumulated elapsed time per query | 60 s | same as above, additionally showing the elapsed time |

When the user picks B, the result set **must** state explicitly in the title or footnote: "⚠ Pagination not exhausted; the first N items / first X pages are shown; to get the true total, narrow down with finer filter parameters (`--operating-states` / `--machine-type` / `--hpn-zone`, etc.) and query again". Truncating silently by default without telling the user is **strictly forbidden**.

### 7.4 Continuation pseudocode (reference implementation)

```bash
# eflo-controller NextToken-style continuation skeleton
fetch_all_clusters() {
  local region="$1"
  local page=0 token="" total=0
  local results="[]"
  while :; do
    page=$((page + 1))
    local resp
    if [ -z "$token" ]; then
      resp=$(safe_aliyun aliyun eflo-controller list-clusters \
 --region "$region" \
        --max-results 50)
    else
      resp=$(safe_aliyun aliyun eflo-controller list-clusters \
 --region "$region" \
        --max-results 50 --next-token "$token")
    fi
    results=$(jq -s '.[0] + (.[1].Clusters // [])' <(echo "$results") <(echo "$resp"))
    total=$(echo "$results" | jq 'length')
    token=$(echo "$resp" | jq -r '.NextToken // empty')
    # Safety valve
    if [ "$page" -ge 50 ] || [ "$total" -ge 1000 ]; then
      [ -n "$token" ] && hitl_ask_continue_or_truncate "$page" "$total"
      break
    fi
    [ -z "$token" ] && break  # NextToken empty → true last page
  done
  echo "$results"
}
```

### 7.5 Anti-examples (strictly forbidden)

- ❌ Page 3's response body has non-empty `NextToken="abc..."`, yet the Agent stops and answers the user "you have N clusters in total".
- ❌ Changing `--max-results` from 50 to 10 / 100 during continuation (the first page's value must be kept).
- ❌ Passing the previous page's `NextToken` through URL-encode / base64 secondary processing before feeding it to `--next-token`.
- ❌ After hitting the 50-page threshold, silently answering with the accumulated results without telling the user "not exhausted".

---

## Appendix A — Network Resource Cleanup

After a cluster is deleted, the surrounding VPC / VSwitch / Lingjun Connection resources may remain, because they are often shared. Do **not** auto-delete them.

### A.1 Decision matrix

| Scenario | Action |
| --- | --- |
| VPC created exclusively for this cluster | Safe to delete (confirm with user first) |
| VPC shared with other clusters / ECS / databases | **Do not delete** |
| Not sure | Leave it — ask the account admin |

### A.2 Manual cleanup (exclusive VPC only)

```bash
# Delete all VSwitches first (VPC must be empty)
safe_aliyun aliyun vpc describe-vswitches --vpc-id "$VPC_ID" \
  --cli-query 'VSwitches[*].VSwitchId' | jq -r '.[]' | while read vsw; do
    safe_aliyun aliyun vpc delete-vswitch --vswitch-id "$vsw"
    sleep 5
done

# Then delete the VPC
safe_aliyun aliyun vpc delete-vpc --vpc-id "$VPC_ID"
```

### A.3 Best practices

- Tag cluster-owned VPC/VSwitch with `ClusterId = <id>` for traceability.
- Snapshot `safe_aliyun aliyun vpc describe-vpcs --vpc-id "$VPC_ID" > vpc-${VPC_ID}.json` before deletion.
- Prefer IaC (Terraform) for reproducible teardown.

---

## Appendix B — Retry Code Snippets

### B.1 Exponential backoff with jitter

```bash
retry_with_jitter() {
  local max_attempts=${MAX_ATTEMPTS:-3}
  local base=${BASE_SECONDS:-2}
  local attempt=1
  while [ $attempt -le $max_attempts ]; do
    "$@" && return 0
    if [ $attempt -lt $max_attempts ]; then
      local backoff=$((base * (2 ** (attempt - 1))))
      local jitter=$((RANDOM % backoff + 1))
      sleep $((backoff + jitter))
    fi
    attempt=$((attempt + 1))
  done
  return 1
}

# Example: retry a transient-error-prone list call
# ⚠️ In business code, always use §B.4 `safe_aliyun` for aliyun calls (including the blacklist short-circuit); do not use retry_with_jitter bare.
# This example only shows the standalone invocation form of retry_with_jitter.
retry_with_jitter aliyun eflo-controller list-clusters --region "$REGION"
```

### B.2 Fixed 60 s throttle retry

```bash
retry_on_throttle() {
  local max_attempts=3
  local attempt=1
  while [ $attempt -le $max_attempts ]; do
    OUTPUT=$("$@" 2>&1) && { echo "$OUTPUT"; return 0; }
    if echo "$OUTPUT" | grep -qE 'Throttling|429'; then
      sleep 60
      attempt=$((attempt + 1))
      continue
    fi
    echo "$OUTPUT" >&2
    return 1
  done
  return 1
}
```

### B.4 `safe_aliyun` unified wrapper (the implementation skeleton of SKILL.md Transient Failure Retry)

`safe_aliyun` = outer `retry_on_throttle` + inner `retry_with_jitter`; it is the unified CLI wrapper required by [SKILL.md → Transient Failure Retry (MANDATORY)](../SKILL.md). Whenever the Agent executes **any** `aliyun ...` command, it must be issued in the form `safe_aliyun aliyun ...`.

```bash
# Combine the two layers retry_with_jitter (§B.1) and retry_on_throttle (§B.2):
#   inner layer handles network jitter / 5xx / transient API errors (exponential backoff + jitter, max 3 attempts)
#   outer layer handles Throttling / HTTP 429 (fixed 60s, max 3 attempts)
safe_aliyun() {
  # When a retry blacklist entry is hit, return the original error immediately without further retries
  # Blacklist: InvalidAccessKeyId / SignatureDoesNotMatch / NoPermission / Forbidden /
  #            InvalidParameter / MissingParameter / NotFound / OperationConflict / 403
  local out rc
  out=$(retry_on_throttle retry_with_jitter "$@" 2>&1); rc=$?
  if [ $rc -ne 0 ] && echo "$out" | grep -qE \
    'InvalidAccessKeyId|SignatureDoesNotMatch|NoPermission|Forbidden|AccessDenied|InvalidParameter|MissingParameter|NotFound|OperationConflict|HTTP 403'; then
    echo "$out" >&2
    return $rc
  fi
  echo "$out"
  return $rc
}

# Usage: all read-only / mutating / polling CLIs go through the same entry point
safe_aliyun aliyun eflo-controller list-clusters \
 --region "$REGION"

safe_aliyun aliyun eflo-controller describe-task \
 --region "$REGION" --task-id "$TASK_ID"

# Mutating scenarios must first run the §3 Reentrancy pre-check, and fix ClientToken for CreateInstance
CLIENT_TOKEN=${CLIENT_TOKEN:-$(uuidgen)}
safe_aliyun aliyun bssopenapi create-instance \
  --client-token "$CLIENT_TOKEN" \
  --product-code bccluster --product-type bccluster_eflocomputing_public_cn \
  ...
```

> ⚠️ When 3 retries still fail, `safe_aliyun` throws the last attempt's stderr as-is; the caller must output the complete failure report to the user in the §6 "Unified Error Output" format (including `ErrorCode` + `RequestId`). Continuing to retry silently or fabricating a successful return value is strictly forbidden.

### B.3 Idempotent expand helper

```bash
# Only add nodes that are not already in the cluster
CURRENT=$(safe_aliyun aliyun eflo-controller list-cluster-nodes \
  --region "$REGION" --cluster-id "$CLUSTER_ID")
for nid in $NODES_TO_ADD; do
  if echo "$CURRENT" | jq -e ".Nodes[] | select(.NodeId==\"$nid\")" > /dev/null; then
    echo "skip: $nid already in cluster"
  else
    echo "add:  $nid"
  fi
done
```

---

## Summary — Quick Reference

| Situation | How to detect | Primary action |
| --- | --- | --- |
| Task beyond hard-timeout | elapsed > table in §1.1 | stop polling → ask user (wait / ticket) |
| Unknown ErrorCode | not in [error-codes.md](error-codes.md) | derive advice from `ErrorCode + Message`, never fabricate |
| Retry could double-act | mutating op + no dedup guarantee | run reentrancy pre-check (§3) |
| Sub-tasks partial fail | parent success + SubTask fail | split report + ask "retry failed subset?" |
| Conflict with active task | `OperationConflict` | poll active TaskId ≤ 30 min → retry |
| Async stuck, no rollback | expand/shrink/change-node-group hung | guide user to file a support ticket |
| CreateInstance unclear | 5xx / timeout during BSS call | orphan-scan (§5.2) → reuse or resend with same ClientToken |
| Reporting failure to user | any error path | use the §6 template verbatim |
