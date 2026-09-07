# Scripts: safe_aliyun & safe_mutate

> The actual implementations live in [`tests/lib/safe-aliyun.sh`](../tests/lib/safe-aliyun.sh) and [`tests/lib/safe-mutate.sh`](../tests/lib/safe-mutate.sh). This document is the interface contract.

---

## `safe_aliyun` - the unified wrapper every CLI must go through (MANDATORY)

```bash
# Loading (must run once per session)
source ./tests/lib/safe-aliyun.sh

# Self-check
type safe_aliyun >/dev/null 2>&1 || { echo "❌ safe_aliyun not loaded; refusing to issue any CLI"; exit 2; }

# Invocation
safe_aliyun aliyun eflo-controller list-clusters --endpoint ... --region cn-hangzhou
```

**Contract**:

1. Every `aliyun ...` command (including read-only, polling, and parallel submissions) must be executed as `safe_aliyun aliyun ...`; a bare `aliyun ...` is a V1 violation.
2. Automatic exponential-backoff retry per the [edge-cases.md Section 4](edge-cases.md) whitelist (2s / 4s / 8s + jitter, up to 3 times).
3. Throttling (`Throttling*` / HTTP 429) waits a fixed 60s.
4. Blacklist errors (`InvalidAccessKeyId` / `NoPermission` / `InvalidParameter` / `NotFound` / `DiagnosticNotFound` / `OperationConflict` / `NodeNotInCluster`, etc.) return immediately, no retry.
5. Retry logs are written to the Agent's own execution log (not shown to the user), format: `retry #N after <err> sleeping <s>s`.

---

## Async diagnostic task polling interaction spec (MANDATORY, same pattern as node-ops)

```bash
# First round (executed automatically inside diagnose_submit; polls once and returns)
poll_diagnostic_burst <region> <did> 10 10

# Each subsequent round: an independent Bash call, until rc=0/1 terminal state
sleep 10 && poll_diagnostic_burst <region> <did> 10 10 <t0>
```

**Contract**:

1. After a successful submission, echo the submission receipt (DiagnosticId + RequestId + polling plan) first, then enter polling; writing it only into the thinking process or a collapsed terminal = V7 violation.
2. Foreground polling runs one round every 10s, and **each round is one independent Bash call**; the progress line on each round's stdout (`[WAIT] poll #N ... state=... elapsed ...`) must be relayed verbatim into the reply body.
3. rc=10 means still in progress (the `[burst-continue]` hint line on stderr carries t0 for the next round to reuse; not shown to the user); on rc=0/1 terminal states, stdout ends with the full JSON.
4. **Forbidden**: packing the polling loop into a single long command that blocks until terminal state (`poll_diagnostic` / `for i in $(seq ...)`) or running it silently in the background - the frontend would show zero progress; blocking `poll_diagnostic` is for tests / non-interactive orchestration only (MUTATE_AUTOCONFIRM=1).
5. Foreground cap of 20 minutes: on reaching the cap, report the latest state + DiagnosticId and run an HITL two-way pick (continue / stop with a self-check command).

---

## `safe_mutate` - two-phase commit (MANDATORY)

```bash
# Loading
source ./tests/lib/safe-mutate.sh

# Phase 1: dry-run + dump + hash generation
safe_mutate <action_label> aliyun eflo-controller create-diagnostic-task \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid> --diagnostic-type BasicCheck --node-ids <nid>

# Output: the hash is printed silently to stdout (for the Agent to capture, not shown to the user); the command is persisted to /tmp/lingjun-diag-mutate/<action>-<hash>.json

# Phase 2: after the user replies the confirmation word (zh 「确认」 / en "confirm"), the Agent commits internally (the user never copies the hash)
safe_mutate_confirm <hash>   # invoked internally by the Agent
```

**Contract**:

1. Phase 1 does **not** actually issue the request; it only persists the `cmd` text + prints the hash + renders the parameter confirmation table + validates that `forbidden_inference` fields are complete.
2. Phase 2 strictly matches the hash; missing or expired (30min) -> refuse to execute.
3. Phase 2 submission still goes through the `safe_aliyun` wrapper.
4. **Test mode**: when `MUTATE_AUTOCONFIRM=1`, Phase 2 is invoked automatically after Phase 1 for automated testing; this environment variable must never be enabled in interactive sessions.
5. For `reimage-nodes`, the Phase 1 confirmation table must prominently render the [WARN] system-disk-wiped, irreversible warning; the user's unified confirmation word (zh word per parameter-confirmation.md / en "confirm") acknowledges that impact, after which the Agent internally runs `safe_mutate_confirm <hash>` to enter Phase 2.

---

## Phase 1 dump mandatory fields (per action)

| Action | Mandatory fields |
|---|---|
| `create-diagnostic-task` | Region / ClusterId / DiagnosticType / Targets[] (NodeId+Hostname+MachineType) / Endpoint / full CLI |
| `reboot-nodes` | Region / ClusterId / Targets[] / IgnoreFailedNodeTasks / Endpoint / full CLI |
| `reimage-nodes` | Region / ClusterId / Targets[] / ImageId(forbidden_inference) / LoginPassword(`******`) / Hostname / Endpoint / full CLI |
| `stop-nodes` | Region / Targets[] / IgnoreFailedNodeTasks / Endpoint / full CLI (listing ClusterId is **strictly forbidden**) |
| `report-node-status` | Region / NodeId+Hostname / DiagnosisType / Description / Endpoint / full CLI |
| `stop-node-diagnostic` | Region / ReportId(forbidden_inference) / NodeId+Hostname (for display) / current fault status (translated name in zh sessions) / impact statement (termination is irreversible) / Endpoint / full CLI |

Any missing field (especially `forbidden_inference` fields) -> Phase 1 refuses to emit the hash and prompts the user to return to HITL to complete it.
