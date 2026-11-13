# SysAgent CLI Reference

Use the official SysOM plugin through `aliyun sysom sysagent`. Follow [Environment Setup](setup.md) before use. The plugin handles cloud requests, streaming, and checkpoints; do not call raw OpenAPI or read or edit private checkpoints. Check the exact command's `--help` if the installed release differs from this reference.

The tables use subcommands relative to `aliyun sysom sysagent`. Examples are complete command lines. Replace uppercase placeholders with real values and resolve `USER_AGENT` per [Observability](../SKILL.md#observability). Append the Host's `--profile PROFILE` when using a named Profile, consistently for the whole task. Describe the resource region in the user's message; the service control plane is fixed in Hangzhou. SysAgent has no separate authentication, endpoint, region, update, or state-directory options.

## Quick Start

1. **Submit a new task.** Put the user's goal, confirmed scope, and constraints in `request.txt`. Use one request ID for the submission.

   ```bash
   aliyun sysom sysagent ask --message-file request.txt --request-id REQUEST_ID --wait 5s --user-agent USER_AGENT
   ```

2. **Continue from the receipt.** Use the returned `sessionId`, `runId`, and the last consumed `observation.cursor`. Choose the command that matches the next action:

   | User intent | Command | Effect |
   | --- | --- | --- |
   | Check current execution status | `run get` | Reads the state of the same run. |
   | “Keep following the check” | `run watch` | Resumes observation of the same run. Use the consumed cursor when available. |
   | “Check whether that CPU spike matches a deploy” (a new question) | `ask --session SESSION` | Starts a new turn in the same cloud conversation. |
   | Answer a question or decide on a proposed action | `input get`, then `input submit` | Reads the pending form. Sends only the user's decision to the exact run and input. |
   | Read results or files | `result get`, then the relevant evidence or artifact command | Reads the output already synchronized for this run. |

## Commands and parameters

| Command | Purpose | Parameters |
| --- | --- | --- |
| `ask` | Submit a new turn; creates a session if omitted | `--message TEXT` or `--message-file FILE`, `--request-id ID`; optional `--session SESSION`, `--agent-id ID`, `--wait DURATION` |
| `session create` | Create an empty cloud conversation | Optional `--name NAME` (default `Local Agent`) |
| `session get` | Read cloud session metadata | `--session SESSION` |
| `session list` | List accessible cloud sessions | Optional pagination |
| `run start` | Submit a new turn in a specified session | Same as `ask`, with `--session SESSION` required |
| `run get` | Inspect an execution's state | `--session SESSION --run RUN` |
| `run watch` | Observe an existing execution | `--session SESSION --run RUN`; optional `--cursor CURSOR`, `--wait DURATION`, `--stream-events BOOL` |
| `run cancel` | Request cancellation of an identified execution | `--session SESSION --run RUN` |
| `input get` | Read the current pending form | `--session SESSION --run RUN` |
| `input submit` | Answer a specific pending form | `--session SESSION --run RUN --input-id INPUT --file ANSWERS.json --request-id ID`; optional `--wait DURATION` |
| `result get` | Read the locally synchronized public result | `--session SESSION --run RUN` |
| `plan list`, `evidence list`, `artifact list` | List plans, evidence, or artifact references | `--session SESSION --run RUN`; optional pagination |
| `activity list` | List diagnostic tool activities | `--session SESSION --run RUN`; optional `--cursor CURSOR` and pagination |
| `plan get`, `evidence get`, `artifact get`, `activity get` | Expand an object from the selected run | `--session SESSION --run RUN --ref REF` |
| `artifact download` | Save a file artifact | `--session SESSION --run RUN --ref REF --destination FILE` |

- **Pagination:** list commands accept `--limit` (1–100, default 20) and `--next-token`. Use the returned token with the same list query. A local list can change as more events are synchronized; on `PAGE_CHANGED`, restart the list if still needed.
- **Message:** supply exactly one of `--message` and `--message-file`. A message file is UTF-8 request text, at most 1 MiB; `-` reads standard input. It does not upload a local diagnostic attachment.
- **Agent ID:** `ask` and `run start` default to `sysagent`; omit the flag for normal use. Pass `--agent-id` only when the user explicitly supplies a valid Agent ID. Never map expert names to IDs locally.
- **Observation window:** `ask`, `run start`, and `input submit` accept 0–60s (default 5s); zero still waits for the receipt. `run watch` accepts 1–60s (default 10s). The window limits local observation, not the lifetime of the cloud task.

## Submit or identify a run

Use `ask` for new work. A new follow-up in a confirmed conversation uses `ask --session SESSION`; asking for existing progress or results does not require a new turn. Save a logical request ID before submitting. An accepted receipt identifies the `sessionId` and top-level `runId`; do not use a child activity's ID as the run. If a submission is unconfirmed, inspect the known execution, or follow the CLI's same-request retry guidance with the original inputs and identity. Do not replace an uncertain submission with a new request ID.

```bash
aliyun sysom sysagent session list --limit 20 --user-agent USER_AGENT
aliyun sysom sysagent session get --session SESSION --user-agent USER_AGENT
aliyun sysom sysagent run get --session SESSION --run RUN --user-agent USER_AGENT
```

Use `session list` and `session get` only to help identify the intended task if its receipt is unavailable. A returned active or last turn is usable only when it matches the user's intended run. Ask when there are ambiguous candidates. Session metadata is not a full conversation transcript or a guarantee that older execution status is available.

## Observe an execution

```bash
aliyun sysom sysagent run watch --session SESSION --run RUN --cursor CURSOR --wait 10s --user-agent USER_AGENT
```

- **Which cursor:** Use the last consumed `observation.cursor` and update it after processing the batch. `projection.cursor` is the plugin's checkpoint, not a receipt that the local Agent saw the events. With no cursor, omitting the flag starts from the plugin's checkpoint. If earlier output is needed but the consumed cursor is unknown, or the CLI reports `CURSOR_AHEAD_OF_CHECKPOINT`, use `--cursor 0` on the same run. Do not re-announce known progress when replaying.
- **More results:** When `observation.hasMore=true`, continue with the returned consumer cursor. In either output mode, preserve the last consumed cursor if the command is interrupted.

### Choose an output mode

| Mode | CLI output | When to use it |
| --- | --- | --- |
| Default | One JSON response per watch call, with a `progress` array and observation state. | Use short watch windows, especially when the host buffers command output until exit. |
| `--stream-events true` | JSONL records: `observation.started`, individual progress records, and `observation.result` when available. | Use only if the host can read and act on records as they arrive. |

Both modes are for machine consumption. Show the user a short explanation of the new finding, scope, or limitation that the records support.

### Read progress records

| Record | How to interpret it |
| --- | --- |
| `activity` | Use `payload.facts`, `payload.status`, and `payload.isError` when present. A returned tool can still have failed or covered only part of the requested scope. |
| `public_message`, `plan` | Report a meaningful change in the work; a message or plan alone is not a measurement. |
| `evidence_ready`, `artifact_ready`, `input_required` | Use the reference or signal to inspect the actual evidence, artifact metadata, or pending form. |

Use progress `id` to deduplicate replays. Read detailed objects by `ref` only when they help explain a material finding, decision, or limitation.

### Interpret execution and observation state

| Field | Meaning |
| --- | --- |
| `submissionStatus` | Whether the submitted request is confirmed; `accepted` does not mean the execution is complete. |
| `runStatus` | The state of the cloud execution. Before reporting completion, call `run get` for the original session and run to verify its current terminal status. If it is still running, continue observing the same execution. After the terminal-state query, read `result get`; do not report a partial result as complete. |
| `projection.status` | State of the local view. `degraded` indicates projection issues; `incomplete` indicates an observation error. |
| `caughtUp`, `partial` | A null value does not prove all output arrived. Neither a terminal execution state nor `projection.status=current` establishes complete local evidence. |

A successful status read after a parse failure updates the execution state, but does not restore missing evidence.

`run cancel` sends a cloud cancellation request. Use it only on explicit instruction for that execution, then inspect it with `run get`. A cancellation receipt does not mean the cloud run is already cancelled. Ctrl-C, an expired watch window, or a closed terminal stops only the local observation.

## Answer pending input

```bash
aliyun sysom sysagent input get --session SESSION --run RUN --user-agent USER_AGENT
aliyun sysom sysagent input submit --session SESSION --run RUN --input-id INPUT --file answers.json --request-id ANSWER_REQUEST_ID --wait 5s --user-agent USER_AGENT
```

Use the actual returned `inputId` and form fields, not a guessed schema. The answer file contains one JSON object, at most 1 MiB; `--file -` reads it from standard input. Use a new logical request ID for each new answer and the same request ID and exact answer if the CLI directs a retry of that same submission. If the input changed or is no longer pending, re-read the current form; a decision for an older form does not authorize a different one.

## Read results, evidence, and artifacts

```bash
aliyun sysom sysagent result get --session SESSION --run RUN --user-agent USER_AGENT
aliyun sysom sysagent evidence get --session SESSION --run RUN --ref EVIDENCE_REF --user-agent USER_AGENT
aliyun sysom sysagent artifact list --session SESSION --run RUN --user-agent USER_AGENT
aliyun sysom sysagent artifact get --session SESSION --run RUN --ref ARTIFACT_REF --user-agent USER_AGENT
aliyun sysom sysagent artifact download --session SESSION --run RUN --ref ARTIFACT_REF --destination REPORT_FILE --user-agent USER_AGENT
```

- `result get` and the object commands read synchronized local output. Use the actual resource scope and time window reported by the evidence. A missing observation is not a normal reading.
- Use the object's real `ref` from the same execution. An evidence entry can explain a conclusion without pointing to a downloadable file. An artifact can be listed but unavailable for download.
- Download to a new local path. The plugin requires a usable HTTPS URL, does not overwrite an existing file, and validates the artifact's SHA256 if supplied. Keep expiring or signed URLs out of chat and logs. If the file is unavailable, exceeds the CLI's limits, or has no published checksum, state which delivery or verification step could not be completed.

## Troubleshooting

| Symptom | Next action |
| --- | --- |
| Unconfirmed submission | Inspect the original run if known. Use the same request ID and input only if the CLI directs a same-request retry. |
| `CURSOR_AHEAD_OF_CHECKPOINT` | Replay from `--cursor 0` on the same run and avoid re-announcing known progress. |
| `CACHE_MISS` | Observe the same run to synchronize output before reading its result or objects again. |
| Repeatable stream parse error | Keep the error and last consumed cursor, check status with `run get`, and report any usable evidence and remaining gaps. Do not loop on the same error. |
| Artifact unavailable or checksum mismatch | Report the delivery or verification failure. Do not bypass the plugin's download checks. |
