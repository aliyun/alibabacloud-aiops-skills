# Verification Method

This document provides verification commands and expected outputs for each Step in the execution flow, used for self-validation. All commands output JSON to stdout. On error, the JSON includes an `error` field and the exit code is 1. In the commands, `$PWD` is the project root directory and `<skill-root>` is the skill base directory.

Execution flow: `env-check -> list-accounts -> init -> create-thread -> chat (diagnose) -> plan -> self-validate -> report -> cleanup`

## Mandatory Command Sequence Quick Reference

The first 5 steps are **MUST** -- they are verified by eval expectations and must not be skipped or substituted.

| Step | Command | Script | MUST | Eval Expectation ID | Description |
|------|---------|--------|------|---------------------|-------------|
| 1 | `env-check` | `session_manager.py` | **YES** | `env-check` (fallback scenario) | Check all environment prerequisites. Required in all scenarios. |
| 2 | `list-accounts` | `session_manager.py` | **YES** | `list-accounts` | List all configured UIDs and their profile/employeeId mapping. Never skip even if only one account. |
| 3 | `init` | `session_manager.py` | **YES** | `init-session` | Initialize a new session bound to a UID. Never skip even if "no session tracking needed". |
| 4 | `create-thread` | `starops_manager.py` | **YES\*** | `create-starops-thread` | Create STAROps diagnostic Thread. `*` = required when STAROps is available; fallback to `aliyun` CLI when unavailable. |
| 5 | `chat` | `starops_manager.py` | **YES\*** | `send-*-query` | Send diagnostic query via STAROps SSE stream. `*` = required when STAROps is available. |

> **Forbidden alternatives**: Do NOT substitute with `aliyun ecs describe-instances`, `aliyun cs describe-cluster-*`, `curl`/`wget` API calls, or any other direct CLI/API approach. Run `python3 scripts/session_manager.py workflow` for a machine-readable JSON of the mandatory sequence.

## Execution Trace Verification

Every `session_manager.py` and `starops_manager.py` invocation automatically appends a JSONL record to `.aliyun-sre/execution-trace.jsonl`. After running the mandatory command sequence, verify the trace log contains records for each step:

```bash
cat .aliyun-sre/execution-trace.jsonl | python3 -m json.tool --json-lines
```

Expected: at least 5 trace records (env-check, list-accounts, init, create-thread, chat), each with `"success": true`.

## Step 1 - env-check

Verify all environment prerequisites pass.

```bash
python3 scripts/session_manager.py env-check --cwd "$PWD"
```

Expected output: top-level `"status": "pass"`, `"critical_failures": 0`, and each check item (`aliyun_cli` / `starops` / `python_deps` / `accounts`) is `pass`.

> If `status` is `fail` (exit code 1), stop subsequent steps and handle each failed item's `remediation`.

## Step 2 - list-accounts (MUST)

List registered accounts. In single-account mode, auto-select without user confirmation. In multi-account mode, user must confirm selection. This step is mandatory in every session.

```bash
python3 scripts/session_manager.py list-accounts --cwd "$PWD"
```

Expected output: `accounts` list, each item containing `uid` / `profile` / `effective_profile` / `profile_source` / `employeeId` / `workspace`.

## Step 3 - init

Verify new session creation and correct UID->profile->digital employee binding.

```bash
python3 scripts/session_manager.py init --uid <uid> --cwd "$PWD"
```

Expected output: returned JSON contains `session` ID. The `.aliyun-sre/<session>/tasks/status.json` contains `uid` / `profile` / `employeeId` / `workspace` / `threadId` (initially `null`) fields, with `status` as `pending`.

## Step 4 - starops-cap-cache-get

Verify capability cache hit status (determines whether capability rediscovery is needed).

```bash
python3 scripts/session_manager.py starops-cap-cache-get \
  --uid <uid> --employee-id <id> --workspace <ws> --cwd "$PWD"
```

Expected output: `"hit": true` (cache hit, returns cached capabilities) or `"hit": false` (miss/expired, requires rediscovery and `starops-cap-cache-set` to write).

## Step 5 - create-thread

Verify STAROps Thread creation returns a valid threadId.

```bash
python3 scripts/starops_manager.py create-thread --employee-id <id> --config "<config.json path>" --uid <uid>
```

Expected output: stdout outputs a `threadId` string. This threadId is written to status.json's `threadId` field and reused for all subsequent `chat` queries.

## Step 6 - starops_manager

Verify diagnostic query via STAROps returns diagnostic text.

```bash
python3 scripts/starops_manager.py chat <thread-id> "<question>" --uid <uid>
```

Expected output: stdout outputs the complete diagnostic conclusion text returned by STAROps (`role=assistant` content).

> The `<thread-id>` must first be obtained via `starops_manager.py create-thread` subcommand and written to status.json's `threadId`. Follow-up queries reuse the same threadId. For multi-account, `--uid` is required.

## Step 9 - Report Existence Check

Verify report file has been generated.

```bash
ls .aliyun-sre/<session>/diagnostic-report.md
# or (inspection-governance scenario)
ls .aliyun-sre/<session>/inspection-report.md
```

Expected output: `diagnostic-report.md` (diagnostic scenario) or `inspection-report.md` (inspection governance scenario) exists. Report conclusions must be based on actual diagnostic data. Fabrication is prohibited.

## Step 10 - cleanup

Verify expired sessions are cleaned up.

```bash
python3 scripts/session_manager.py cleanup --cwd "$PWD"
```

Expected output: returned JSON reports removed sessions (`removed` list / count). TTL defaults to 300 seconds.

---

> For state machine and status.json structure, see [session-management.md](session-management.md). For STAROps API and idempotency keys, see [starops-api.md](starops-api.md). For command list, see [related-commands.md](related-commands.md).
