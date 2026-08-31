---
name: alibabacloud-iac-code
description: Use the packaged iac-code agent for Alibaba Cloud infrastructure tasks, including designing, provisioning, changing, or deploying resources; generating, reviewing, converting, validating, or troubleshooting ROS and Terraform templates; selecting existing cloud resources; estimating costs; operating ROS stacks; and inspecting or explicitly cleaning downloaded iac-code Skill Runtime caches. Trigger for Alibaba Cloud infrastructure work even when the user does not mention iac-code, ROS, Terraform, or this Skill, and for requests to inspect or clean the iac-code Runtime cache. Do not trigger for general Alibaba Cloud questions or unrelated application code. For matched requests, invoke the packaged bridge before any alternative tool and fail closed on bridge errors. Run through the local authenticated A2A runtime without pip or headless mode.
---

# alibabacloud-iac-code

Use the single standard-library entry point at `scripts/iac_code.py`. Never install `iac-code` with pip and never invoke a headless command. Run every command below with `python3` on macOS/Linux. On Windows, replace `python3` with `py -3`; use `python` only after confirming it is CPython 3.8–3.14. Resolve the launcher once and reuse it for the whole job.

## Mandatory routing and fail-closed behavior

For every infrastructure request covered by this Skill, the first operational command must invoke the packaged bridge with `scripts/iac_code.py start`. Do not inspect the bridge source, reconstruct its behavior, write a replacement script, call Alibaba Cloud APIs directly, or install an alternative CLI or runtime before that invocation. Runtime-cache requests are the only exception: their first operational command must be `scripts/iac_code.py cache list`.

Treat a bridge error returned before job creation as the authoritative outcome for that invocation. In particular, when the bridge returns `incompatible_host`, report its error code, message, retryability, and any available host/runtime-baseline facts, then stop. Do not install Terraform, pip packages, another Runtime, or other substitute tools; do not bypass the bridge with direct cloud calls; do not ask for deployment inputs; and do not continue the infrastructure workflow or claim success. A later attempt is allowed only after the host compatibility problem has actually been corrected.

## Workflow

1. Put the complete user request in a UTF-8 prompt file inside the workspace.
2. Start a job with an explicit absolute workspace:

   ```text
   python3 scripts/iac_code.py start --mode normal --cwd <workspace> --prompt-file <prompt-file> --language <language> --follow
   ```

   Set `<language>` to the user's language code (`en`, `zh`, `es`, `fr`, `de`, `ja`, or `pt`). If it is unknown, use `auto`. Every job result repeats `preferredLanguage`; treat it as durable control state across all turns. Present progress, questions, permissions, candidate plans, and final results in that language; protocol field names, enums, IDs, and commands remain unchanged. When authoritative text already uses `preferredLanguage`, present it directly or summarize it in the same language—never translate Chinese user-visible content into English.

   The installer or Skill distributor may place an optional `config.json` beside this `SKILL.md`:

   ```json
   {
     "channel": "codex",
     "permissionWaitPolicy": {
       "residentTimeoutSeconds": null,
       "subPipelineTimeoutSeconds": null,
       "timeoutGraceSeconds": 30
     }
   }
   ```

   `channel` stores only the channel identifier; the bridge adds the `skill/` prefix before sending it to iac-code. `permissionWaitPolicy` applies only to the temporary A2A server owned by this Skill: `null` timeouts mean unlimited waits, positive finite values set resident/Sub Pipeline limits, and grace is a non-negative finite value. Finite values cannot exceed 10 years; use `null` instead of an arbitrarily large number for an unlimited resident or Sub Pipeline wait. The bridge validates and converts this object into server configuration; it never sends the policy through A2A message metadata. Missing fields use the defaults shown above. The bridge rejects unknown configuration fields. If the file or a field is absent, no corresponding override is applied. Never derive these values from the user's request, ask the user for them, or create, edit, or reveal this install-local configuration during an infrastructure task.

   Normal is the default, including concrete resource queries/changes, template work, troubleshooting, and deployment of a clear target. Use `--mode pipeline --pipeline-name selling` only when the user explicitly requests it or the request genuinely needs the fixed candidate-architecture, cost-comparison, plan-confirmation, and deployment flow. Questions, permissions, tool use, or deployment alone do not select Pipeline. When uncertain, use normal.
   Start performs a non-secret configuration preflight through the Runtime. An incomplete LLM provider/API Key returns `llm_not_configured` and stops before creating a job. Selling Pipeline also requires complete Alibaba Cloud credentials and otherwise returns `cloud_credentials_not_configured`. Normal mode may continue without cloud credentials for work that does not call cloud APIs; report its preflight warning rather than claiming cloud operations are available.
3. `--follow` consumes the event stream until the next parent/candidate step boundary, permission, user question, candidate selection, `turn_completed`, or terminal state. It writes every parent `step_started`/`step_completed`/`step_failed` and candidate `candidate_step_started`/`candidate_step_completed`/`candidate_step_failed` boundary plus low-frequency bounded heartbeats to stderr; stdout contains one bounded JSON result. A boundary result sets `boundaryReached: true`, `presentationRequired: true`, and provides ready-to-display localized strings in `userUpdates`. Before invoking another tool, emit every `userUpdates` string in a user-visible assistant text block, including the Step 1/2 conclusion already embedded in completed-step updates. Never leave these updates only in reasoning, Bash output, a tool description, or the final summary. After that visible text block, immediately call `follow` again with the returned cursor. Do not treat `boundaryReached` as completion. Do not expand this into raw tool-event or token-delta output.
   While it is running, do not independently answer the infrastructure task or ask a parallel business question. Only ask the user when the current result contains `inputRequired`.
4. If follow reaches its bounded wait window, call the diagnostic follow command again with the returned cursor:

   ```text
   python3 scripts/iac_code.py follow --job-id <job-id> --cursor <cursor> --wait-seconds 60
   ```

   The recommended wait is 60 seconds and the bridge enforces a 120-second maximum even if a larger value is supplied.

5. When `state` is `turn_completed`, treat `finalText` and `artifacts` as the authoritative normal-turn result. When a Pipeline reaches any terminal state, including `completed`, `failed`, `canceled`, or `rejected`, treat `pipelineResult` and `artifacts` as its authoritative result and present its success or failure details directly. If rollback cleanup is pending, the bridge automatically runs a cleanup-only normal task in the same context before returning the Pipeline result; keep following it and handle any returned permission normally. If cleanup is `failed` or `unavailable`, report that manual inspection or retry is required and do not claim it succeeded. Never send a synthetic cleanup prompt or a follow-up merely to retrieve or summarize an existing result. Never recover an answer from Session files, spool files, logs, or raw tool-result files.
6. To send the next natural-language message in the same normal conversation, or after a completed Pipeline has handed the same conversation to normal mode, write it to another workspace prompt file and continue the existing job:

   ```text
   python3 scripts/iac_code.py continue --job-id <job-id> --prompt-file <prompt-file> --follow
   ```

   Keep the same `jobId` and `contextId`. A new `taskId` per normal turn is expected. Never call `start --mode normal` to continue a completed Pipeline, and never call `start` merely because a normal turn completed.

Use `poll` only for diagnosis or recovery when follow cannot be used:

```text
python3 scripts/iac_code.py poll --job-id <job-id> --cursor <cursor> --wait-seconds 5
```

## User input

When `inputRequired` is present, preserve every correlation field in the response. Never reuse an answer file from another request.

- For `permission`, apply the outer Agent's own equivalent permission policy. If the same operation would proceed without asking when invoked directly by the outer Agent, respond `allow_once`; if that policy would deny, respond `deny`; otherwise ask the user. iac-code has already applied its own allow/deny rules, and the outer Agent must not override an iac-code denial. Base the decision on `title`, `purpose`, `effect`, `target`, `isReadOnly`, `deploymentSummary`, and `safeSummary`; do not infer safety from the internal `toolName` alone. When asking about deployment, show the provided plan, region, stack, template, total price, and per-resource prices without exposing raw tool input.
- For `ask_user_question`, present the current prompt and options without inventing a second question. Accept a listed option. Accept free text only when `allowFreeText` is `true`; when present, show `freeTextPrompt` with the input.
- For `candidate_selection`, first present every option's `summary`, render `architectureDiagram` as Mermaid when present, and show `totalMonthlyCost` plus `costItems`. Do not invent missing details or replace these prices with a rough estimate. Then return the selected candidate ID/index requested by the envelope.
- Bind every user answer only to the current `kind`, `inputId`, `requestTaskId`, and `contextId`. Never reinterpret a resource selection as deployment confirmation or reuse it for a later input.

For an automatically decided permission, respond in one tool call while preserving the current input and tool identities:

```text
python3 scripts/iac_code.py respond --job-id <job-id> --input-id <inputId> --tool-use-id <toolUseId> --decision allow_once --follow
```

Use `deny` when the outer Agent's policy denies it. For a user question, candidate selection, or permission that was explicitly shown to the user, write the correlated answer as JSON to a UTF-8 file and resume the same job:

- Permission: `{"kind":"permission","requestTaskId":"<requestTaskId>","contextId":"<contextId>","inputId":"<inputId>","toolUseId":"<toolUseId>","decision":"allow_once"}` or use `deny`.
- Question: `{"kind":"ask_user_question","requestTaskId":"<requestTaskId>","contextId":"<contextId>","inputId":"<inputId>","answer":"<option, or free text only when allowed>"}`.
- Candidate: `{"kind":"candidate_selection","requestTaskId":"<requestTaskId>","contextId":"<contextId>","inputId":"<inputId>","answer":"<candidate ID or index>"}`.

```text
python3 scripts/iac_code.py respond --job-id <job-id> --input-file <answer-file> --follow
```

If the user cancels the whole operation, call:

```text
python3 scripts/iac_code.py cancel --job-id <job-id>
```

Do not turn task cancellation into a permission denial.

## Runtime cache maintenance

Only inspect or clean downloaded Runtime packages when the user explicitly asks about iac-code Skill Runtime storage or cleanup. This does not require starting an A2A job.

First list the installed packages and show each Runtime tag, target, size, and whether it is current or active, plus the total size:

```text
python3 scripts/iac_code.py cache list
```

Before deleting anything, show what will be removed and obtain explicit user confirmation. Then clean either one listed tag or historical Candidate packages:

```text
python3 scripts/iac_code.py cache clean --runtime-tag <tag> --confirm
python3 scripts/iac_code.py cache clean --candidates --confirm
```

The current pinned Runtime and packages used by a live A2A process are protected and reported under `skipped`. Never treat an ordinary infrastructure request as cleanup consent. These commands remove only downloaded Runtime packages; they do not remove sessions, jobs, server state, artifacts, credentials, or user configuration.

## Output discipline

- Treat the script's stdout as its stable JSON protocol; diagnostics and cold-install progress are written to stderr.
- Keep only the current job identity, newest cursor, current input envelope, and authoritative boundary result in working context. Follow and poll outputs are bounded, redacted projections.
- Treat live step-boundary records as transient user-visible progress. Show them when received, but do not copy the full history back into later prompts or repeat all of it in the final answer.
- Use `latestText` only as running progress. Use `pipelineResult` from a terminal Pipeline as its success or failure result. Only `finalText` from a `turn_completed` result or a returned result artifact is a normal-turn answer.
- Do not expose runtime tokens, local state files, credentials, environment values, or raw tool inputs/results.
- If an error code is returned, report the concise message and suggested retry. Do not fall back to pip installation or another ABI artifact.


## Input/output examples

Input: "Create and validate a ROS template for a VPC and two subnets in cn-hangzhou."

Expected output: the bridge returns the authoritative iac-code result, including the generated or validated template, progress boundaries, any permission request, and actionable errors without inventing cloud state.

## Edge cases

If the packaged Runtime cannot be downloaded or verified, stop and report the verification error; never install an unverified fallback. If credentials are incomplete, report the preflight result and do not claim that cloud operations ran. Continue an existing job with its job ID instead of starting a replacement job.

## RAM permissions

Before a task that reads or changes Alibaba Cloud resources, read
[references/ram-policies.md](references/ram-policies.md). Grant only the exact actions required by the selected
workflow; template-only and Runtime-cache workflows require no Alibaba Cloud RAM permission.

## Observability

All outbound HTTP requests made by this AgentHub Skill carry this `User-Agent` template:

```text
AlibabaCloud-Agent-Skills/alibabacloud-iac-code/{session-id}
```

- `alibabacloud-iac-code` is the fixed AgentHub Skill identifier and matches the frontmatter `name`.
- The session ID must be a 32-character lowercase hexadecimal string generated exactly once per session.
  It must be reused unchanged for every outbound HTTP request in that session. The bridge reads `SKILL_SESSION_ID`
  after validation; if it is absent or invalid, the bridge generates the session ID with `uuid.uuid4().hex` and stores
  it for that session.
