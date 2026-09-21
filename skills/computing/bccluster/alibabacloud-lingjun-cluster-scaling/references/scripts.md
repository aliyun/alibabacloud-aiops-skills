# Reusable Scripts for Lingjun Cluster Management

This document provides reusable bash scripts for common Lingjun cluster management tasks.

> **📁 Path note (important)**: historical examples in this file use `~/lingjun-scripts/lib/` as the script deployment location; **the current deployment location is unified to the repo's `./lib/`** (or `~/.qoder/skills/alibabacloud-lingjun-cluster-scaling/lib/`, auto-loaded by Qoder). Any `~/lingjun-scripts/lib/...` appearing below should be treated as an equivalent placeholder of `./lib/...` — **no manual file copying needed**. In the Agent's self-check / error recovery, use `./lib/` (or the absolute deployment path).

> **⚠️ Region Required (MANDATORY)** ｜ Every `aliyun eflo-controller` command example in this file **must** explicitly carry the `--region <region>` parameter (`<region>` given explicitly by the user via HITL; defaulting / reusing / persisting via environment variable is **strictly forbidden**). The endpoint is auto-derived by the aliyun CLI from `--region`; an explicit `--endpoint` is **neither needed nor desired** (see [SKILL.md §B-6 Region Required](../SKILL.md)). This rule does **not** apply to `aliyun bssopenapi` and `aliyun ecs` commands.

> **⚠️ Transient Failure Retry (MANDATORY)** ｜ All CLI calls inside script examples in this file uniformly use the `safe_aliyun aliyun ...` form, per [SKILL.md → Transient Failure Retry (MANDATORY)](../SKILL.md). Before running a script you **must** first `source` or inline-define the `safe_aliyun` function; the implementation skeleton is in [edge-cases.md → Appendix B.4](./edge-cases.md) (depends on §B.1 `retry_with_jitter` + §B.2 `retry_on_throttle` + the retry blacklist). Bare `aliyun ...` calls are treated as a hard-rule violation.

### Prerequisites — load `safe_aliyun` before running any script

```bash
# Drop the three function definitions from edge-cases.md §B.1/B.2/B.4 into ~/lingjun-scripts/lib/safe-aliyun.sh
# then source it once at the top of every script:
source ~/lingjun-scripts/lib/safe-aliyun.sh
```

## Table of Contents

1. [`safe_mutate` Two-Phase Commit (MANDATORY)](#safe_mutate-two-phase-commit-mandatory)
2. [Task Monitoring Script](#task-monitoring-script)
3. [Cluster Health Check](#cluster-health-check)
4. [Retry with Backoff](#retry-with-backoff)
5. [Batch Cluster Operations](#batch-cluster-operations)
6. [Automated Verification](#automated-verification)

---

## `safe_mutate` Two-Phase Commit (MANDATORY)

> 🛑 **Scope**: all mutating CLIs — `extend-cluster` / `shrink-cluster` / `delete-node` / `delete-hyper-node` / `change-node-group` / `create-node-group` / `update-node-group` / `bssopenapi create-instance`. **Going through the two-phase Gate is a Skill hard rule** ([SKILL.md → Parameter Confirmation](../SKILL.md#parameter-confirmation)): Phase 1 must dump the parameters, generate a token, and **send no request**; Phase 2 may call `safe_aliyun` to submit only after receiving the user's confirm word. Bare mutating CLI calls, self-filling a value and retrying after `MissingParameter`, and inferring VPC/VSwitch/SecurityGroup from `describe-cluster` on your own — all are serious violations.
>
> ⚠ **User-surface control**: terms such as `Phase 1` / `Phase 2` / `APPROVE_TOKEN` / `hash` / `safe_mutate_confirm` must never appear in any user-visible output (including the Agent's thinking chain / chat reply / terminal command descriptions). The user only sees the parameter confirmation table → replies with the confirm word → gets the result.

> 🚨 **Honesty constraint declaration (READ FIRST)**: `lib/safe-mutate.sh` only does the minimal two-phase flow (parameter dump + hash + submitting via safe_aliyun); it performs **no intent comparison, writes no HITL state file, and never ABORTs on keyword conflict**. There is **no shell-level physical gate anywhere** in the Skill system — all responsibility for intent-drift detection, HITL state file writing, and self-checking rests on the Agent. **The Agent must not rely on any "the script will block it anyway" assumption**. See [SKILL.md §Honesty Constraint Declaration](../SKILL.md#parameter-confirmation) and [detailed-rules.md §Intent → Action Extended](detailed-rules.md#intent-action-extended).

### Why two-phase

When an LLM sees a `MissingParameter VpcId` / `InvalidParameter` error, its default behavior is "retry with the parameter filled in". A textually described Parameter Confirmation cannot stop this impulse; the two-phase function-call decoupling forces the LLM to dump first and wait for the user's confirm word before submitting — **but this is only a structural constraint; whether the rules are really followed ultimately depends on the Agent's own discipline**. The `forbidden_inference` schema (see [../workflows/](../workflows/README.md)) is actively compared by the Agent before generating the parameter table — **there is no automatic interception in the dry-run phase**.

### Function definitions

> The following is the minimal version of `lib/safe-mutate.sh` actually deployed: mutating whitelist validation → `--intent` parsing and persistence (for audit traceability) → parameter hash dump → calling `safe_aliyun` to submit in the confirm phase. It performs **no intent comparison**, **writes no HITL state file**, and **never ABORTs on keyword conflict**. All responsibility for intent recognition, self-check, and HITL state file writing rests on the Agent — see [detailed-rules.md §Intent → Action Extended](detailed-rules.md#intent-action-extended) and [§HITL State File Check](detailed-rules.md#hitl-state-file-check).

```bash
# ~/lingjun-scripts/lib/safe-mutate.sh
# Dependencies: safe_aliyun (edge-cases.md §B.4) + jq + sha256sum
# Usage:
#   safe_mutate <action> --intent "<user's original words>" aliyun eflo-controller <action> --region ... --cluster-id ...
#   safe_mutate_confirm <hash>

SAFE_MUTATE_DIR="${SAFE_MUTATE_DIR:-/tmp/lingjun-mutate}"
mkdir -p "$SAFE_MUTATE_DIR"

safe_mutate() {
  local action="${1:?action name required, e.g. extend-cluster}"
  shift

  # Parse --intent "<user's original words>" (must immediately follow the action).
  # This field takes no part in the wrapper's internal logic; it is only written into audit.log
  # for post-hoc accountability, and serves as the Agent's formal trace of "I did perform the self-check".
  local intent=""
  if [ "${1:-}" = "--intent" ]; then
    intent="${2:?--intent value required, e.g. --intent \"extend my cluster\"}"
    shift 2
  fi

  # Identify the mutating whitelist (bare `aliyun list-* / describe-* / get-*` does not go through this wrapper)
  case "$action" in
    extend-cluster|shrink-cluster|delete-node|delete-hyper-node|\
    change-node-group|create-node-group|update-node-group|delete-node-group|\
    create-instance) ;;
    *) echo "❌ safe_mutate applies only to mutating actions; got: $action" >&2; return 2 ;;
  esac

  # 1) Serialize input parameters into a stable hash
  local args_json hash
  args_json=$(printf '%s\n' "$@" | jq -R . | jq -s .)
  hash=$(printf '%s|%s' "$action" "$args_json" | sha256sum | cut -c1-12)

  # 2) Persist all parameters to disk, redacting the password
  local dump="$SAFE_MUTATE_DIR/${action}-${hash}.json"
  printf '%s' "$args_json" | \
    jq --arg action "$action" --arg hash "$hash" --arg intent "$intent" \
       '{action:$action, hash:$hash, intent:$intent, args:., redacted:false}' \
    | sed -E 's/(LoginPassword"[^"]*")[^,}]*"[^"]*"/\1"******"/g; s/(--login-password"[^,}]*")[^,}]*"[^"]*"/\1"******"/g' \
    > "$dump"

  # 3) Silently print the hash to stdout (captured programmatically by the Agent); emit no internal-mechanism terms
  echo "$hash"

  # Detailed banner is emitted to stderr only in test mode (MUTATE_AUTOCONFIRM=1)
  if [ "${MUTATE_AUTOCONFIRM:-0}" = "1" ]; then
    cat <<BANNER >&2
[test-harness] action=${action} hash=${hash} dump=${dump}
[AUTOCONFIRM] executing confirm...
BANNER
    safe_mutate_confirm "$hash"
    return $?
  fi
  return 0
}

safe_mutate_confirm() {
  local hash="${1:?hash required}"
  local dump
  dump=$(ls -1 "$SAFE_MUTATE_DIR"/*-"$hash".json 2>/dev/null | head -1)
  if [ -z "$dump" ] || [ ! -f "$dump" ]; then
    echo "❌ confirm submission failed: token invalid or expired" >&2
    return 2
  fi
  local action
  action=$(jq -r .action "$dump")
  # Execute silently, emitting no internal-phase information
  local -a argv
  while IFS= read -r line; do argv+=("$line"); done < <(jq -r '.args[]' "$dump")
  safe_aliyun "${argv[@]}"
  local rc=$?
  # Release the dump after submission to prevent replay
  rm -f "$dump"
  return $rc
}
```

> ⚠ **Writing the HITL state file is entirely the Agent's responsibility**: this function family does **not** automatically write `$HOME/.lingjun/hitl-required.json`. When the Agent detects any V1-V7 self-violation / self-check failure / async task in a non-terminal state, it **must proactively** run `jq -n '{...}' > $HOME/.lingjun/hitl-required.json` (schema in [detailed-rules.md §HITL State File Check](detailed-rules.md#hitl-state-file-check)).

### Usage example — Feature 2 extend-cluster

```bash
source ~/lingjun-scripts/lib/safe-aliyun.sh
source ~/lingjun-scripts/lib/safe-mutate.sh

# Phase 1: dry-run dump; no request is sent
# 🎯 Key: --intent must immediately follow the action, carrying the user's original words that triggered this operation.
#   This field is only written into the dump / audit.log for post-hoc accountability; the wrapper performs no intent comparison —
#   intent→action consistency is guaranteed by the Agent's self-check block (see detailed-rules.md)
safe_mutate extend-cluster --intent "extend my cluster to 8 nodes" aliyun eflo-controller extend-cluster \
  --region cn-wulanchabu \
  --cluster-id i116913051663373010974 \
  --node-groups '[{"NodeGroupId":"ng-xxx","Nodes":[{"NodeId":"e01-cn-yyy","Hostname":"node-006","LoginPassword":"<RealPwd>","VpcId":"vpc-xxx","VSwitchId":"vsw-xxx","SecurityGroupId":"sg-xxx"}]}]'
# → Internally the Agent generates a redacted parameter confirmation table (the token is held internally by the Agent, never exposed to the user)

# Agent internal: after the user replies with the confirm word, the Agent validates and executes
safe_mutate_confirm a1b2c3d4e5f6
# → Internally submits extend-cluster through the safe_aliyun retry system (silent execution, no user-visible output)
```

### Standard production path (MANDATORY): `safe_mutate_oneshot` (single call, zero script)

> 🛑 **Strongly recommended**: the actual submission after the user's confirm word should **use `safe_mutate_oneshot`** — a single inline command completes Phase 1 + Phase 2, with **no need** for the Agent to pass the hash between Bash tool calls, and the Agent is **strictly forbidden** from authoring temporary `.sh` scripts (the latter makes the IDE display "file created/deleted" metadata that pollutes the user surface, violating the spirit of [SKILL.md §A.3-15 tool-call step exposure](../SKILL.md)).

**Preconditions for calling** (**the Agent is responsible for guaranteeing them**; the function cannot validate them — a violation is a [SKILL.md §B-8 V2](../SKILL.md) violation):
- ✅ The user has explicitly replied with the strict confirm word on the parameter confirmation table ("yes"/"OK"/"submit"/"go" are all **not** accepted)
- ✅ The Agent has passed the [intent self-check (B-9 V7 gate)](../SKILL.md)
- ✅ The Agent has `read_file`d the corresponding [`../workflows/{action}/schema.yaml`](../workflows/README.md) (A.2-4 Pre-Form Mechanical Gate)

```bash
# After the user replies with the confirm word, complete the submission with one inline line (no script writing, no hash passing across Bash calls)
safe_mutate_oneshot extend-cluster --intent "extend my cluster to 8 nodes" aliyun eflo-controller extend-cluster \
  --region cn-wulanchabu \
  --cluster-id i116913051663373010974 \
  --node-groups '[{"NodeGroupId":"ng-xxx","Nodes":[{"NodeId":"e01-cn-yyy","Hostname":"node-006","LoginPassword":"<RealPwd>"}]}]'
# → Internally equivalent to: hash=$(safe_mutate ...); safe_mutate_confirm "$hash"
# → Goes through the same safe_aliyun retry system, same dump + audit trail, silent execution
```

### Two-phase vs one-shot: when to use which

| Scenario | Recommended | Reason |
|---|---|---|
| User has confirmed; submit the real request immediately | **`safe_mutate_oneshot`** | Single inline command; no hash passing across Bash calls; no temporary script needed |
| Test / debug mode | `MUTATE_AUTOCONFIRM=1 safe_mutate ...` | Emits the test-harness banner to stderr for auditing |
| Submission spans multiple turns (rare) | `safe_mutate` (Phase 1) → ... → `safe_mutate_confirm <hash>` (Phase 2) | Other work needed while the dump persists |
| Explicit staged auditing (rare) | same as above | A hash verification / sidecar tool can be inserted between the two phases |

**Default preference**: unless there is a special auditing need, after the user's confirm word you **MUST** use `safe_mutate_oneshot`.

**Anti-incident example — the Agent self-check must detect and ABORT**:

```bash
# ❌ The user said "shrink" but change-node-group is about to be issued (reproduction path of incident TaskId i156268331779185240034)
# Before generating the command below, the Agent must emit the self-check block; skipping it is equivalent to a V7 violation:
#
# [intent self-check · internal]
# user original words : shrink node-002 for me
# matched keywords    : shrink
# action to map       : shrink-cluster
# action about to run : change-node-group
# consistency verdict : ❌ inconsistent → ABORT
#
# The Agent must immediately:
#   1) not generate the safe_mutate call
#   2) jq -n '...' > $HOME/.lingjun/hitl-required.json
#   3) disclose to the user: ① the original intent maps to shrink-cluster ② why change-node-group is not equivalent ③ candidate actions are for the user to choose

# Counter-example (if the Agent skips the self-check and issues it directly):
safe_mutate change-node-group --intent "shrink node-002 for me" aliyun eflo-controller change-node-group \
  --region cn-wulanchabu --node-id e01-cn-xxx --target-node-group-id ng-idle
# → lib/safe-mutate.sh will actually NOT block this (it only dumps + emits the hash); the command will really be submitted after confirmation
# → This is the physical path of a V7 drift incident; the Agent self-check must block it before generating the command
```

### Behavioural contract

- For **any** mutating action the Agent must call `safe_mutate <action> --intent "<user's original words>" aliyun ...`. A bare `safe_aliyun aliyun extend-cluster ...` call is treated as a Skill hard-rule violation.
- **`--intent` is mandatory** (immediately after the action): the current `lib/safe-mutate.sh` does **not** enforce-validate `--intent` (omitting it only produces an ordinary error, not a physical block), but the Agent **MUST** pass it itself. Missing it or using placeholder phrasing (`--intent "execute operation"` / `--intent "user has confirmed"`) = a V7 self-violation, handled per [edge-cases.md §4.5 V7](./edge-cases.md#45-skill-self-violation-not-retryable) as non-retryable and non-pardonable. The field's actual purposes: ① written into `audit.log` for post-hoc accountability; ② the Agent's formal trace of "I did perform the self-check".
- **Intent mapping table (single source of truth for keywords)**: the `user_intent_keywords:` at the top of [`../workflows/<biz>/schema.yaml`](../workflows/README.md). The Agent **MUST** `read_file` the corresponding yaml before every mutating operation to fetch the list, and **must not** reuse it from memory. This script maintains no shadow copy, to avoid drifting from the yaml.
- After the parameter confirmation table is shown, only two follow-up paths are allowed: ① the user replies with the confirm word (the Agent **recommends** submitting via one inline `safe_mutate_oneshot` line; the legacy path `safe_mutate_confirm <hash>` remains usable); ② the user explicitly says "cancel". Any other phrasing (including "yes / OK / submit") does **not** constitute consent.
- The Agent is **strictly forbidden** from authoring temporary `.sh` scripts to execute mutating operations — even to "bind source + Phase 1 + Phase 2", it **MUST** switch to `safe_mutate_oneshot`. Temporary scripts trigger the IDE's file-created/deleted metadata display, polluting the user surface (same tier as [SKILL.md §A.3-15](../SKILL.md) tool-call step exposure V1).
- `MissingParameter` error → the Agent is **not allowed** to self-fill parameters and retry; it must re-ask via HITL and then issue a new `safe_mutate` call to obtain a new hash; the original dump is voided.
- Sensitive fields (`LoginPassword` / `--login-password`) are redacted as `******` in the dump; the dump is released after submission to prevent the plaintext from being read a second time.
- **User-surface shielding**: `--intent` / `audit.log` / "self-check block" are internal constraint terms; the [detailed-rules.md §Agent Output Surface Control](detailed-rules.md#agent-output-surface-control) hard rule forbids them from appearing on the user surface. When a self-check failure ABORTs, what the Agent presents to the user is "per the rules, your requested 'shrink' cannot be mapped to a node-group migration; the current operation has been cancelled — please choose from the following candidates…", not internal diagnostic information.
- **HITL State File**: when the Agent's self-check fails / any V1-V7 self-violation is detected, it **must proactively** run `jq -n '{...}' > $HOME/.lingjun/hitl-required.json` (schema in [detailed-rules.md §HITL State File Check](detailed-rules.md#hitl-state-file-check)). The script layer does **not** write it on the Agent's behalf. The Agent checks this file at the entry of every turn; if it exists, HITL disclosure is mandatory; after disclosure completes, clean it up with `rm -f`.

---

## Standalone Localized Command Functions (zh-cli)

> 🛡️ **Scope**: `lib/zh-cli/commands-zh.sh` provides a set of standalone shell functions whose names are localized Chinese action verbs (no prefix), designed for scenarios where beginner-friendly action words should be shown in the `run_in_terminal` progress panel. Since the literal function names are non-English, this document refers to them by their **English semantic aliases** below; the exact localized verb for each alias is defined in the source file — see [Source location](#source-location-zh).

### Command quick reference <a id="command-quickref-zh"></a>

| English alias (= function semantics) | Arguments | Description | Progress-panel display |
|---|---|---|---|
| `prepare` | — | Initialize the execution environment | the localized verb for "prepare" |
| `check` | — | HITL state check | the localized verb for "check" |
| `verify-credentials` | — | Verify CLI credentials are usable | the localized verb for "verify credentials" |
| `list-clusters` | — | Cluster list | the localized verb for "list clusters" |
| `describe-cluster` | `<cluster-id>` | Cluster details | verb + `i116...` |
| `list-cluster-nodes` | `<cluster-id>` | Cluster node list | verb + `i116...` |
| `list-node-groups` | `<cluster-id>` | Node group list | verb + `i116...` |
| `describe-node-group` | `<node-group-id>` | Node group details | verb + `ng-...` |
| `describe-node` | `<node-id>` | Single node details | verb + `e01-cn-...` |
| `list-free-nodes` | — | Free node list | verb only |
| `list-free-hyper-nodes` | — | Free hyper node list | verb only |
| `list-machine-types` | — | Available machine types | verb only |
| `list-images` | — | Available images | verb only |
| `list-hyper-nodes` | — | Hyper node list | verb only |
| `describe-hyper-node` | `<hyper-node-id>` | Hyper node details | verb + `hn-...` |
| `describe-task` | `<task-id>` | Task status | verb + `i159...` |
| `extend-cluster` | `--intent "..." aliyun ...` | Cluster expansion | verb + `--intent "..." aliyun ...` |
| `shrink-cluster` | `--intent "..." aliyun ...` | Cluster shrink | verb + `--intent "..." aliyun ...` |
| `delete-node` | `--intent "..." aliyun ...` | Release a node | verb + `--intent "..." aliyun ...` |
| `delete-hyper-node` | `--intent "..." aliyun ...` | Release a hyper node | verb + `--intent "..." aliyun ...` |
| `change-node-group` | `--intent "..." aliyun ...` | Node migration | verb + `--intent "..." aliyun ...` |
| `create-node-group` | `--intent "..." aliyun ...` | Create a node group | verb + `--intent "..." aliyun ...` |
| `update-node-group` | `--intent "..." aliyun ...` | Update a node group | verb + `--intent "..." aliyun ...` |
| `create-instance` | `--intent "..." aliyun ...` | Purchase a node | verb + `--intent "..." aliyun ...` |
| `confirm-submit` | `<hash>` | Confirm a mutating operation | verb + `a1b2c3` |
| `monitor-task` | `<task-id>` | Async task polling | verb + `t-xxx` |
| `run` | `<command...>` | Pass-through execution | verb + `aliyun ...` |

### Typical execution flow

```bash
# First command of the session (Pre-Execution Self-Check)
<localized verb for "prepare">
# → progress panel shows: the "prepare" verb

# HITL state check
<localized verb for "check">
# → progress panel shows: the "check" verb

# List clusters (query commands may carry arguments directly)
<localized verb for "list clusters">
# → progress panel shows: the "list clusters" verb

# List nodes
<localized verb for "list nodes"> i116913051663373010974
# → progress panel shows: verb + "i116913051663373010974"

# Mutating operation (verb + arguments, passed through directly)
<localized verb for "extend"> --intent "extend my cluster to 8 nodes" aliyun eflo-controller extend-cluster --region ...
# → progress panel shows: verb + --intent "..." aliyun eflo-controller ...

# Confirm submission (hash passed directly)
<localized verb for "confirm submit"> a1b2c3d4e5f6
# → progress panel shows: verb + "a1b2c3d4e5f6"

# Async polling (task-id passed directly)
<localized verb for "monitor task"> i159809891662373011020
# → progress panel shows: verb + "i159809891662373011020"
```

### Source location <a id="source-location-zh"></a>

[`lib/zh-cli/commands-zh.sh`](../lib/zh-cli/commands-zh.sh) — each function definition there starts with the localized Chinese verb; invoke them directly per the table above.

---

## `query` Chinese Rendering Wrapper (MANDATORY for read-only queries)

> 🛡️ **Scope**: all `eflo-controller list-*` / `describe-*` style queries. When presenting query results to the user, the Agent **must** use `query` instead of the bare `safe_aliyun aliyun eflo-controller ...` command. Dumping raw JSON to the user = an information-leak violation of the localized-display hard rule in [detailed-rules.md §Agent Output Surface Control](detailed-rules.md#agent-output-surface-control) (handled jointly with SKILL.md B-10 HITL display localization).

### Environment preparation

```bash
# Sourced once during the Pre-Execution Self-Check (invisible to the user)
source lib/core/aliyun-call.sh
source lib/query/query.sh
# Region is no longer persisted via an environment variable; it is passed explicitly as the first argument on every query call
```

### Subcommand quick reference

> Invocation signature: `query <region> <subcmd> [args...]` — region is required and passed explicitly as the first argument

| Subcommand | Arguments (after `<region>`) | Description |
|---|---|---|
| `cluster-list` | — | Cluster list (localized table) |
| `cluster-describe` | `<cluster-id>` | Cluster details (localized KV) |
| `cluster-nodes` | `<cluster-id>` | Cluster node list |
| `node-group-list` | `<cluster-id>` | Node group list |
| `node-group-describe` | `<group-id>` | Node group details |
| `node-describe` | `<node-id>` | Single node details |
| `free-nodes` | — | Free node list |
| `free-hyper-nodes` | — | Free hyper node list |
| `machine-types` | — | Machine type list |
| `images` | — | Image list |
| `hyper-node-list` | — | Hyper node list |
| `hyper-node-describe` | `<hyper-node-id>` | Hyper node details |
| `task` | `<task-id>` | Task status (localized summary) |

### User-facing example (the Agent executes in the terminal + presents the result)

```bash
# The command the user sees (short, no internal details; region passed explicitly)
query cn-wulanchabu cluster-list

# The output the user sees (localized table per session language, no raw JSON);
# English header equivalents: Cluster Name / Cluster ID / Cluster Type / State / Node Count / Created At
# cluster_test_1  i11877...48838359  Lite  Running  4  2026-05-06
```

### Extension guide

To support a new `eflo-controller` subcommand, add the corresponding `_lj_render_*` function and `case` branch in [`lib/query/query.sh`](../lib/query/query.sh). Render functions must ensure:
- Field labels are rendered with the localized display label only; appending the English KEY in parentheses is forbidden (per [detailed-rules.md §HITL Chinese Display](detailed-rules.md#hitl-chinese-display); canonical label strings live in `lib/core/i18n.sh`)
- Enum values are rendered with the localized translation only, without appending the raw English value (e.g. `Running` → the localized "running" display word)
- Boolean fields are rendered with the localized label + enabled/disabled display words only

---

## Task Monitoring Script

Monitor asynchronous task progress with timeout and notifications.

### monitor-task.sh

```bash
#!/bin/bash
#
# Monitor Lingjun task progress
# Usage: ./monitor-task.sh <region> <task-id> [timeout-seconds]
#

set -euo pipefail

REGION="${1:-cn-wulanchabu}"
TASK_ID="${2:?Task ID required}"
TIMEOUT="${3:-1800}"  # 30 minutes default
CHECK_INTERVAL=30

if [ -z "$TASK_ID" ]; then
  echo "Usage: $0 <region> <task-id> [timeout-seconds]"
  exit 1
fi

echo "=== Monitoring Task ==="
echo "Region: $REGION"
echo "Task ID: $TASK_ID"
echo "Timeout: ${TIMEOUT}s"
echo "Check interval: ${CHECK_INTERVAL}s"
echo ""

START_TIME=$(date +%s)
LAST_PROGRESS=0
STALL_COUNT=0

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))

  # Check timeout
  if [ $ELAPSED -ge $TIMEOUT ]; then
    echo "❌ Task timeout after ${ELAPSED}s"
    exit 1
  fi

  # Query task status (polling is naturally idempotent; safe_aliyun swallows transient failures and never misjudges network jitter as TaskState=Failed)
  RESPONSE=$(safe_aliyun aliyun eflo-controller describe-task \
    --region "$REGION" \
    --task-id "$TASK_ID" 2>&1)

  if [ $? -ne 0 ]; then
    echo "⚠️  Failed to query task: $RESPONSE"
    sleep $CHECK_INTERVAL
    continue
  fi

  # Parse response
  STATE=$(echo "$RESPONSE" | jq -r '.TaskState')
  PROGRESS=$(echo "$RESPONSE" | jq -r '.TaskProgress // 0')
  UPDATE_TIME=$(echo "$RESPONSE" | jq -r '.UpdateTime')

  # Display progress
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] State: $STATE | Progress: $PROGRESS% | Elapsed: ${ELAPSED}s | Updated: $UPDATE_TIME"

  # Check for completion
  if [ "$STATE" = "Success" ]; then
    echo ""
    echo "✅ Task completed successfully!"
    echo "Total time: ${ELAPSED}s"
    exit 0
  elif [ "$STATE" = "Failed" ]; then
    echo ""
    echo "❌ Task failed!"
    echo "Task result:"
    echo "$RESPONSE" | jq '.TaskResult'
    exit 1
  fi

  # Check for stalled progress
  if [ "$PROGRESS" = "$LAST_PROGRESS" ]; then
    STALL_COUNT=$((STALL_COUNT + 1))
    if [ $STALL_COUNT -ge 5 ]; then
      echo "⚠️  WARNING: Progress hasn't changed in $((STALL_COUNT * CHECK_INTERVAL))s"
    fi
  else
    STALL_COUNT=0
  fi
  LAST_PROGRESS=$PROGRESS

  sleep $CHECK_INTERVAL
done
```

**Usage**:
```bash
chmod +x monitor-task.sh

# Monitor task with default 30min timeout
./monitor-task.sh cn-wulanchabu i159809891662373011020

# Monitor with custom timeout (1 hour)
./monitor-task.sh cn-wulanchabu i159809891662373011020 3600
```

---

## Cluster Health Check

Comprehensive cluster health check script.

### cluster-health-check.sh

```bash
#!/bin/bash
#
# Lingjun Cluster Health Check
# Usage: ./cluster-health-check.sh <region> <cluster-id>
#

set -euo pipefail

REGION="${1:?Region required}"
CLUSTER_ID="${2:?Cluster ID required}"

echo "======================================"
echo "   Lingjun Cluster Health Check"
echo "======================================"
echo "Region: $REGION"
echo "Cluster ID: $CLUSTER_ID"
echo "Timestamp: $(date)"
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES_FOUND=0

# Function to print status
print_status() {
  local status=$1
  local message=$2

  case $status in
    "ok")
      echo -e "${GREEN}✓${NC} $message"
      ;;
    "warn")
      echo -e "${YELLOW}⚠${NC} $message"
      ;;
    "error")
      echo -e "${RED}✗${NC} $message"
      ISSUES_FOUND=$((ISSUES_FOUND + 1))
      ;;
  esac
}

# 1. Check cluster exists and state
echo "=== 1. Cluster Status ==="
CLUSTER_INFO=$(safe_aliyun aliyun eflo-controller describe-cluster \
  --region "$REGION" \
  --cluster-id "$CLUSTER_ID" 2>&1)

if [ $? -ne 0 ]; then
  print_status "error" "Failed to retrieve cluster information"
  echo "$CLUSTER_INFO"
  exit 1
fi

CLUSTER_NAME=$(echo "$CLUSTER_INFO" | jq -r '.ClusterName')
OPERATING_STATE=$(echo "$CLUSTER_INFO" | jq -r '.OperatingState')
NODE_COUNT=$(echo "$CLUSTER_INFO" | jq -r '.NodeCount')
NODE_GROUP_COUNT=$(echo "$CLUSTER_INFO" | jq -r '.NodeGroupCount')
ACTIVE_TASK=$(echo "$CLUSTER_INFO" | jq -r '.TaskId')

echo "Cluster Name: $CLUSTER_NAME"
echo "Operating State: $OPERATING_STATE"
echo "Node Count: $NODE_COUNT"
echo "Node Group Count: $NODE_GROUP_COUNT"

if [ "$OPERATING_STATE" = "Running" ] || [ "$OPERATING_STATE" = "Stable" ]; then
  print_status "ok" "Cluster state is healthy"
elif [ "$OPERATING_STATE" = "Creating" ] || [ "$OPERATING_STATE" = "Deleting" ]; then
  print_status "warn" "Cluster is in transitional state"
else
  print_status "error" "Cluster state is abnormal: $OPERATING_STATE"
fi

# 2. Check active tasks
echo ""
echo "=== 2. Active Tasks ==="
if [ -n "$ACTIVE_TASK" ] && [ "$ACTIVE_TASK" != "" ] && [ "$ACTIVE_TASK" != "null" ]; then
  print_status "warn" "Active task detected: $ACTIVE_TASK"

  TASK_INFO=$(safe_aliyun aliyun eflo-controller describe-task \
    --region "$REGION" \
    --task-id "$ACTIVE_TASK")

  TASK_STATE=$(echo "$TASK_INFO" | jq -r '.TaskState')
  TASK_PROGRESS=$(echo "$TASK_INFO" | jq -r '.TaskProgress')

  echo "  Task State: $TASK_STATE"
  echo "  Task Progress: $TASK_PROGRESS%"

  if [ "$TASK_STATE" = "Failed" ]; then
    print_status "error" "Active task has failed"
    echo "$TASK_INFO" | jq '.TaskResult'
  fi
else
  print_status "ok" "No active tasks"
fi

# 3. Check node health
echo ""
echo "=== 3. Node Health ==="
NODE_LIST=$(safe_aliyun aliyun eflo-controller list-cluster-nodes \
  --region "$REGION" \
  --cluster-id "$CLUSTER_ID")

TOTAL_NODES=$(echo "$NODE_LIST" | jq '.TotalCount')
RUNNING_NODES=$(echo "$NODE_LIST" | jq '[.Nodes[] | select(.OperatingState=="Running")] | length')
STOPPED_NODES=$(echo "$NODE_LIST" | jq '[.Nodes[] | select(.OperatingState=="Stopped")] | length')
FAILED_NODES=$(echo "$NODE_LIST" | jq '[.Nodes[] | select(.OperatingState=="Failed")] | length')

echo "Total Nodes: $TOTAL_NODES"
echo "Running: $RUNNING_NODES"
echo "Stopped: $STOPPED_NODES"
echo "Failed: $FAILED_NODES"

if [ "$RUNNING_NODES" = "$TOTAL_NODES" ]; then
  print_status "ok" "All nodes are running"
elif [ "$FAILED_NODES" -gt 0 ]; then
  print_status "error" "$FAILED_NODES nodes in failed state"
  echo "$NODE_LIST" | jq -r '.Nodes[] | select(.OperatingState=="Failed") | "  - \(.NodeId) (\(.Hostname))"'
elif [ "$STOPPED_NODES" -gt 0 ]; then
  print_status "warn" "$STOPPED_NODES nodes are stopped"
  echo "$NODE_LIST" | jq -r '.Nodes[] | select(.OperatingState=="Stopped") | "  - \(.NodeId) (\(.Hostname))"'
fi

# 4. Check node groups
echo ""
echo "=== 4. Node Groups ==="
NODE_GROUPS=$(safe_aliyun aliyun eflo-controller list-node-groups \
  --region "$REGION" \
  --cluster-id "$CLUSTER_ID" 2>&1)

if [ $? -eq 0 ]; then
  GROUP_COUNT=$(echo "$NODE_GROUPS" | jq '.TotalCount')
  echo "Node Groups: $GROUP_COUNT"

  echo "$NODE_GROUPS" | jq -r '.NodeGroups[] | "  - \(.NodeGroupName) (\(.NodeGroupId)): \(.NodeCount) nodes"'

  print_status "ok" "Node groups healthy"
else
  print_status "warn" "Could not retrieve node groups"
fi

# 5. Summary
echo ""
echo "======================================"
echo "           Health Check Summary"
echo "======================================"

if [ $ISSUES_FOUND -eq 0 ]; then
  echo -e "${GREEN}✓ Cluster is healthy${NC}"
  echo "No issues detected"
  exit 0
else
  echo -e "${RED}✗ Issues found: $ISSUES_FOUND${NC}"
  echo "Please review the findings above"
  exit 1
fi
```

**Usage**:
```bash
chmod +x cluster-health-check.sh

# Run health check
./cluster-health-check.sh cn-wulanchabu i116913051663373010974
```

---

## Retry with Backoff

> **⚠️ Deprecated for Alibaba Cloud CLI calls** ｜ The `retry_with_backoff` in this subsection is a **generic** command-level retry sample and does **not** include the **blacklist short-circuit** required by [SKILL.md → Transient Failure Retry (MANDATORY)](../SKILL.md) (auth / permission / 4xx business errors return immediately); it would swallow `InvalidAccessKeyId` / `NoPermission` / `InvalidParameter` / `NotFound` / `OperationConflict` into retries alike. **For all `aliyun ...` calls, always use [edge-cases.md → Appendix B.4 `safe_aliyun`](./edge-cases.md)**; `retry_with_backoff` is retained only for non-aliyun shell commands (e.g. `curl` / `scp` / in-house tools).

Exponential backoff retry logic for CLI commands.

### retry-command.sh

```bash
#!/bin/bash
#
# Retry command with exponential backoff and jitter
# Usage: ./retry-command.sh <max-attempts> <base-delay> <command> [args...]
#

retry_with_backoff() {
  local max_attempts="${1:?Max attempts required}"
  local base_delay="${2:?Base delay required}"
  shift 2
  local attempt=1

  while [ $attempt -le $max_attempts ]; do
    echo "[Attempt $attempt/$max_attempts] Executing: $*"

    # Execute command
    if "$@"; then
      echo "✓ Command succeeded on attempt $attempt"
      return 0
    fi

    local exit_code=$?
    echo "✗ Command failed with exit code $exit_code"

    if [ $attempt -lt $max_attempts ]; then
      # Calculate exponential backoff with jitter
      local backoff=$((base_delay * (2 ** (attempt - 1))))
      local jitter=$((RANDOM % backoff))
      local sleep_time=$((backoff + jitter))

      echo "Retrying in ${sleep_time}s..."
      sleep $sleep_time
    fi

    attempt=$((attempt + 1))
  done

  echo "✗ Command failed after $max_attempts attempts"
  return 1
}

# Example usage in script
if [ "$#" -lt 3 ]; then
  echo "Usage: $0 <max-attempts> <base-delay> <command> [args...]"
  echo "Example: $0 3 2 aliyun eflo-controller list-clusters --region cn-wulanchabu"
  exit 1
fi

retry_with_backoff "$@"
```

**Usage**:
```bash
# Retry up to 5 times with 2s base delay
./retry-command.sh 5 2 aliyun eflo-controller list-clusters --region cn-wulanchabu

# Retry extend cluster operation
./retry-command.sh 3 5 aliyun eflo-controller extend-cluster \
  --region cn-wulanchabu \
  --cluster-id i116913051663373010974 \
  --node-groups '...'
```

---

## Batch Cluster Operations

Perform operations across multiple clusters.

### batch-cluster-operation.sh

```bash
#!/bin/bash
#
# Perform batch operations on multiple clusters
# Usage: ./batch-cluster-operation.sh <region> <operation> [cluster-ids...]
#

set -euo pipefail

REGION="${1:?Region required}"
OPERATION="${2:?Operation required}"
shift 2
CLUSTER_IDS=("$@")

if [ ${#CLUSTER_IDS[@]} -eq 0 ]; then
  echo "No cluster IDs provided, querying all clusters..."
  CLUSTER_IDS=($(safe_aliyun aliyun eflo-controller list-clusters \
    --region "$REGION" \
    --cli-query "Clusters[*].ClusterId" | jq -r '.[]'))
fi

echo "=== Batch Cluster Operation ==="
echo "Region: $REGION"
echo "Operation: $OPERATION"
echo "Clusters: ${#CLUSTER_IDS[@]}"
echo ""

SUCCESS_COUNT=0
FAILED_COUNT=0

for CLUSTER_ID in "${CLUSTER_IDS[@]}"; do
  echo "----------------------------------------"
  echo "Processing: $CLUSTER_ID"

  # Get cluster name
  CLUSTER_NAME=$(safe_aliyun aliyun eflo-controller describe-cluster \
    --region "$REGION" \
    --cluster-id "$CLUSTER_ID" \
    --cli-query "ClusterName" 2>/dev/null | jq -r '.')

  echo "Name: $CLUSTER_NAME"

  case "$OPERATION" in
    "health-check")
      if ./cluster-health-check.sh "$REGION" "$CLUSTER_ID"; then
        echo "✓ Health check passed"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
      else
        echo "✗ Health check failed"
        FAILED_COUNT=$((FAILED_COUNT + 1))
      fi
      ;;

    "list-nodes")
      NODE_COUNT=$(safe_aliyun aliyun eflo-controller list-cluster-nodes \
        --region "$REGION" \
        --cluster-id "$CLUSTER_ID" \
        --cli-query "TotalCount" | jq -r '.')
      echo "Total nodes: $NODE_COUNT"
      SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
      ;;

    "describe")
      safe_aliyun aliyun eflo-controller describe-cluster \
        --region "$REGION" \
        --cluster-id "$CLUSTER_ID"
      SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
      ;;

    *)
      echo "Unknown operation: $OPERATION"
      FAILED_COUNT=$((FAILED_COUNT + 1))
      ;;
  esac

  echo ""
done

echo "========================================"
echo "           Batch Summary"
echo "========================================"
echo "Total clusters: ${#CLUSTER_IDS[@]}"
echo "Successful: $SUCCESS_COUNT"
echo "Failed: $FAILED_COUNT"

if [ $FAILED_COUNT -eq 0 ]; then
  exit 0
else
  exit 1
fi
```

**Usage**:
```bash
chmod +x batch-cluster-operation.sh

# Health check all clusters in region
./batch-cluster-operation.sh cn-wulanchabu health-check

# List nodes in specific clusters
./batch-cluster-operation.sh cn-wulanchabu list-nodes \
  i116913051663373010974 \
  i116913051663373010975

# Describe specific clusters
./batch-cluster-operation.sh cn-wulanchabu describe \
  i116913051663373010974
```

---

## Automated Verification

Automated verification script for cluster operations.

### verify-operation.sh

```bash
#!/bin/bash
#
# Verify cluster operation completion
# Usage: ./verify-operation.sh <operation> <region> <cluster-id> <task-id> [expected-node-count]
#

set -euo pipefail

OPERATION="${1:?Operation required (extend|shrink|delete)}"
REGION="${2:?Region required}"
CLUSTER_ID="${3:?Cluster ID required}"
TASK_ID="${4:?Task ID required}"
EXPECTED_COUNT="${5:-}"

echo "=== Verification: $OPERATION ==="
echo "Region: $REGION"
echo "Cluster: $CLUSTER_ID"
echo "Task: $TASK_ID"
[ -n "$EXPECTED_COUNT" ] && echo "Expected Node Count: $EXPECTED_COUNT"
echo ""

PASSED=0
FAILED=0

# 1. Verify task completion
echo "1. Verifying task completion..."
TASK_STATE=$(safe_aliyun aliyun eflo-controller describe-task \
  --region "$REGION" \
  --task-id "$TASK_ID" \
  --cli-query "TaskState" | jq -r '.')

if [ "$TASK_STATE" = "Success" ]; then
  echo "   ✓ Task completed successfully"
  PASSED=$((PASSED + 1))
else
  echo "   ✗ Task state: $TASK_STATE"
  FAILED=$((FAILED + 1))
fi

# 2. Verify cluster state
echo "2. Verifying cluster state..."

if [ "$OPERATION" = "delete" ]; then
  # For delete, cluster should not exist (safe_aliyun hits the NotFound blacklist and returns non-zero immediately without retrying — exactly the expected behavior here)
  if safe_aliyun aliyun eflo-controller describe-cluster \
    --region "$REGION" \
    --cluster-id "$CLUSTER_ID" 2>&1 | grep -q "ClusterNotFound\|not found"; then
    echo "   ✓ Cluster successfully deleted"
    PASSED=$((PASSED + 1))
  else
    echo "   ✗ Cluster still exists"
    FAILED=$((FAILED + 1))
  fi
else
  # For extend/shrink, verify node count
  CURRENT_COUNT=$(safe_aliyun aliyun eflo-controller describe-cluster \
    --region "$REGION" \
    --cluster-id "$CLUSTER_ID" \
    --cli-query "NodeCount" | jq -r '.')

  if [ -n "$EXPECTED_COUNT" ] && [ "$CURRENT_COUNT" = "$EXPECTED_COUNT" ]; then
    echo "   ✓ Node count matches expected: $CURRENT_COUNT"
    PASSED=$((PASSED + 1))
  elif [ -z "$EXPECTED_COUNT" ]; then
    echo "   ✓ Cluster exists with $CURRENT_COUNT nodes"
    PASSED=$((PASSED + 1))
  else
    echo "   ✗ Node count mismatch. Expected: $EXPECTED_COUNT, Actual: $CURRENT_COUNT"
    FAILED=$((FAILED + 1))
  fi
fi

# 3. Verify node states (skip for delete)
if [ "$OPERATION" != "delete" ]; then
  echo "3. Verifying node states..."
  RUNNING_NODES=$(safe_aliyun aliyun eflo-controller list-cluster-nodes \
    --region "$REGION" \
    --cluster-id "$CLUSTER_ID" \
    --cli-query "Nodes[?OperatingState=='Running'] | length(@)" | jq -r '.')

  TOTAL_NODES=$(safe_aliyun aliyun eflo-controller list-cluster-nodes \
    --region "$REGION" \
    --cluster-id "$CLUSTER_ID" \
    --cli-query "TotalCount" | jq -r '.')

  if [ "$RUNNING_NODES" = "$TOTAL_NODES" ]; then
    echo "   ✓ All $TOTAL_NODES nodes are running"
    PASSED=$((PASSED + 1))
  else
    echo "   ⚠  Only $RUNNING_NODES of $TOTAL_NODES nodes are running"
    FAILED=$((FAILED + 1))
  fi
fi

# Summary
echo ""
echo "=== Verification Summary ==="
echo "Passed: $PASSED"
echo "Failed: $FAILED"

if [ $FAILED -eq 0 ]; then
  echo "✅ All verifications passed!"
  exit 0
else
  echo "❌ Some verifications failed"
  exit 1
fi
```

**Usage**:
```bash
# Verify extend operation (expect 7 nodes)
./verify-operation.sh extend cn-wulanchabu \
  i116913051663373010974 \
  i159809891662373011020 \
  7

# Verify shrink operation (expect 5 nodes)
./verify-operation.sh shrink cn-wulanchabu \
  i116913051663373010974 \
  i159809891662373011025 \
  5

# Verify delete operation
./verify-operation.sh delete cn-wulanchabu \
  i116913051663373010974 \
  i159809891662373011030
```

---

## Script Installation

To install all scripts:

```bash
# Create scripts directory
mkdir -p ~/lingjun-scripts
cd ~/lingjun-scripts

# Download or copy scripts
# (Copy the script contents from above into individual files)

# Make all scripts executable
chmod +x *.sh

# Add to PATH (optional)
echo 'export PATH="$HOME/lingjun-scripts:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

## Script Best Practices

1. **Always use `set -euo pipefail`** for error handling
2. **Validate input parameters** before executing
3. **Use meaningful variable names** for clarity
4. **Add comments** to explain complex logic
5. **Log operations** with timestamps
6. **Exit with appropriate codes** (0 for success, non-zero for errors)
7. **Use colors** for better readability (but check if terminal supports it)
8. **Implement timeout handling** for long-running operations
9. **Clean up temporary files** on exit
10. **Test scripts** in dev environment before production use
