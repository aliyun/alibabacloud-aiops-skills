---
name: alibabacloud-ros-agent
description: Use Alibaba Cloud ROS Agent through its StartChat API for remote infrastructure conversations. Trigger when the user explicitly asks for the ROS Agent, its StartChat API, or a remote iac-code conversation through Alibaba Cloud. Supports normal and selling Pipeline conversations, questions, candidate selection, correlated permission approval or denial, and explicit StopChat cancellation. Do not trigger for ordinary Alibaba Cloud infrastructure work that can use the local iac-code Skill, or for unrelated ROS API operations.
---

# Alibaba Cloud ROS Agent

Use the bridge at `scripts/ros_agent.py`. Its default code transport uses the Alibaba Cloud Credentials SDK default credential chain and Tea OpenAPI V3 signing to send ROS RPCs directly and consume StartChat SSE incrementally. The bridge never reads credential environment variables or credential values from Profile files itself. A Profile explicitly pinned by local policy is delegated to the Credentials SDK Profile provider and is exclusive: it never falls back to the default chain or another Profile. Credentials exist only inside the SDK-backed request path and are never accepted as bridge arguments, persisted in job state, or returned. An optional dependency-free transport invokes the ROS CLI plugin's `start-chat` and `stop-chat` commands. Run the bridge with `python3` on macOS/Linux or `py -3` on Windows.

## Required interaction contract

Visible narration is part of completing this workflow, not optional styling. Internal reasoning/thinking, a tool description, raw tool output, and the wording of a user question are not substitutes for a user-visible assistant text block. Keep each update concise—normally one to three sentences in the user's language. An update and the following tool call may be in the same assistant response, so do not pause merely to narrate.

Use these stage gates:

- After loading this Skill and before the first operational tool call, acknowledge the infrastructure task, identify Normal or Pipeline mode, and state the immediate next phase.
- After `check` succeeds and before local prompt preparation or `start`, report that readiness passed and what ROS Agent will work on next. Do not expose commands, Profile details, or opaque IDs.
- Whenever bridge JSON has `presentationRequired: true`, the next assistant response must begin with a user-visible text block before any further tool call. For every `boundaryReached` result, emit every ready-to-display `userUpdates` string—even after earlier Pipeline updates; skipping a repeated stage gate and going directly to Bash is a protocol violation. For `followTimedOut`, show the `heartbeat` without claiming completion. For `turn-completed`, present the authoritative `finalText` and relevant artifacts before starting another action or asking a follow-up question.
- Before asking the user to confirm a deployment, present the proposed architecture as a fenced Mermaid diagram after the deployment summary. The confirmation question must come after the diagram; tool output or an unrendered diagram field does not satisfy this gate. Follow the architecture rules below.
- When input is required, first explain in a separate visible update what has completed, what ROS Agent is waiting for, and why the answer is needed; then ask the question with every returned option intact using an interaction method appropriate to the host. For permissions, include the safe action, target, and `permissionClass`; for `pendingPermissions`, state how many independent Sub Pipeline steps are waiting. End the agent turn without choosing for the user.
- After the user answers a question, selects a candidate, or allows/denies a permission, begin the next assistant response by acknowledging the choice and saying that ROS Agent is resuming, then call `continue` or `respond`. Before sending any later natural-language request such as a change or cleanup through `continue`, similarly state what the same ROS Agent session will do next.
- On completion or failure, present the authoritative result or concise sanitized error immediately. Do not dump raw JSON, event counts, correlation IDs, or the full prior milestone history, and do not repeat already presented progress.

Do not call `TodoWrite`, `Task`, or another planning tool merely to track this managed workflow. The preserved `jobId` and `cursor` are its state; report progress directly to the user instead.

While a Pipeline has `wireState: TASK_STATE_WORKING`, `follow` is the only observation operation. This remains true after `permission-responded` and when a cursor has not advanced. Never invoke or offer `continue` as a retry, poll, nudge, or way to unstick a Pipeline: it sends a real natural-language interrupt. Present a returned heartbeat and keep following; if the bridge reports `state: failed`, present that error rather than inventing a recovery message.

## Prerequisites

The selected credential must be allowed to call `ros:StartChat`. Explicit cancellation additionally requires `ros:StopChat`; it is not required for an ordinary completed conversation. The default code transport requires the packages pinned in `scripts/requirements.txt` to be installed for the Python interpreter that runs the bridge. The Credentials SDK default chain or explicitly pinned Profile provider resolves the effective identity without bridge-level credential parsing. The `aliyun_cli` transport has no Python package dependency. Its local execution mode requires the installed CLI and a ROS plugin that provides `start-chat` and `stop-chat`; its remote execution mode expects the host's same-name `aliyun` command to forward those API invocations to a cloud CLI sandbox. Run the bridge check once before the first StartChat call:

```text
python3 <absolute-bridge-path>/ros_agent.py check
```

The bounded JSON result includes the effective `transport`, `aliyunCLIExecutionMode`, endpoint, Agent modes, Thinking policy, configured Profile policy, effective region when locally available, and only non-secret credential metadata. `cli` and `version` are null when the code transport does not need the CLI. In unpinned code mode, `mode: DefaultCredentialChain` means the Credentials SDK resolved the identity without bridge-level credential parsing. In local CLI mode, `rosPluginReady`, `pluginAutoInstallEnabled`, and `pluginInstallRequired` describe plugin readiness. If and only if `pluginInstallRequired` is true, visibly report that the required ROS CLI plugin is being installed, run exactly `aliyun plugin install --name ros`, and then rerun `check`; never add a version, package URL, mirror, or source override. If the plugin is absent but CLI automatic plugin installation is enabled, `pluginInstallRequired` is false and the first `start-chat` invocation may install it. In remote CLI mode, `check` deliberately does not run CLI management commands or inspect local Profiles/plugins.

Use the check result as the sole readiness source. Except for the one local-mode plugin install command directed by `pluginInstallRequired`, never run `aliyun configure`, `aliyun plugin`, or other discovery/management commands, enumerate profiles, or read Alibaba Cloud CLI configuration files yourself. The check deliberately excludes credential values and does not prove that a token is still accepted by ROS; the StartChat response is authoritative for authentication and authorization failures.

The returned `transport` is installation policy, not an Agent choice. In an AgentHub-managed ephemeral runtime, if `check` returns `sdk_not_installed`, use the same Python interpreter to install only the exact bundled dependencies from `scripts/requirements.txt` into that ephemeral runtime, without `sudo` or system changes, and then rerun `check` once. This readiness repair does not authorize a transport change, alternative tooling, or credential access. If installation, the repeated `check`, or any other readiness check fails, report the exact error and stop. Never edit `config.json`, propose or attempt another transport, pass a transport override, or fall back to `aliyun_cli` to bypass the failure. Only the user or installation administrator may change this policy outside the infrastructure task, after which a new `check` is required.

Add `--aliyun-path <path>` to `check` or `start` only when the effective credential path requires native aliyun CLI and it is not on `PATH`; the managed job preserves it for later requests. Use the returned credential source and region without asking the user to choose a Profile. Omit `--profile` unless the user explicitly supplied a Profile and local policy did not pin one; never try to override `aliyunCLIProfile`. Never pass credentials on the command line, put them in prompt files, or expose CLI configuration.

## Optional local policy

The bridge reads an optional `config.json` beside this `SKILL.md`. If it is absent, the transport defaults to `code`, the endpoint defaults to `ros.aliyuncs.com`, both Agent modes are allowed, Thinking is enabled, the Credentials SDK default chain selects the effective identity, and the temporary loopback manager exits 60 seconds after the last SSE worker and manager request become idle. The file accepts these settings:

```json
{
  "transport": "code",
  "endpoint": "127.0.0.1:56124",
  "allowedAgentModes": ["normal", "pipeline"],
  "managerIdleSeconds": 60,
  "enableThinking": true,
  "aliyunCLIProfile": ""
}
```

When `transport` is `aliyun_cli`, add `"aliyunCLIExecutionMode": "local"` or `"remote"`; do not add that field to a `code` transport configuration.

- `transport` accepts exactly `code` or `aliyun_cli`. `code` is the default: it delegates identity resolution to the Credentials SDK default chain unless a Profile is explicitly pinned, in which case the SDK Profile provider owns resolution and refresh. It signs and sends StartChat or StopChat to the configured endpoint while exposing SSE events as they arrive. `aliyun_cli` is the dependency-free path and invokes only the ROS plugin's validated `start-chat` and `stop-chat` operations. SDK imports are lazy and never occur in `aliyun_cli` mode. There is no silent fallback between transports or from a pinned Profile to the default chain.
- `aliyunCLIExecutionMode` accepts exactly `local` or `remote`, defaults to `local`, and is valid only with `transport: "aliyun_cli"`. `local` uses the native local CLI, Profile, and plugin installation. `remote` treats the same-name `aliyun` executable as a cloud-sandbox forwarder: the bridge may invoke only `aliyun ros start-chat` and `aliyun ros stop-chat`, never CLI management or another API operation. Remote mode does not read or pass a local Profile, does not infer a local region, rejects `aliyunCLIProfile`, and requires a public `*.aliyuncs.com` endpoint. All prompt and response payloads are passed inline; never pass a file-backed CLI parameter to the remote command.
- `endpoint` fixes the ROS endpoint for every StartChat and StopChat request in a managed job. A conflicting `--endpoint` is rejected, so do not try to override this local policy. Public endpoints must be `*.aliyuncs.com` hostnames. For local integration tests only, `localhost:<port>` and `127.0.0.1:<port>` are accepted; both transports use HTTPS and skip certificate verification only for those loopback addresses.
- `allowedAgentModes` is a non-empty allowlist containing `normal`, `pipeline`, or both. Do not invoke or suggest a mode excluded by this list.
- `managerIdleSeconds` is an integer from 1 through 86400. It defaults to 60. The countdown starts only when no StartChat SSE worker is running—including a concurrent Sub Pipeline permission-response worker—and is refreshed by each manager request; after exit, any managed command starts a new manager automatically while preserving job state.
- `enableThinking` is a boolean and defaults to `true`. It fixes `EnableThinking` for the whole managed job; do not pass `--no-thinking` or try to override it per request.
- `aliyunCLIProfile` is an empty or exact CLI Profile name and defaults to empty. In code mode, empty uses the Credentials SDK default chain. A non-empty value pins that Profile for code transport or local CLI execution and fails instead of falling back when the Profile is unavailable. It is invalid in remote CLI execution. Do not pass a conflicting `--profile`.

Unknown fields, invalid values, and duplicate modes fail closed. Never edit `config.json` during an infrastructure task or store credentials in it; it is an administrator/user installation policy.

## Managed StartChat workflow

1. Put the complete user request in a UTF-8 prompt file inside the target workspace. Run `start` with the shell process working directory set to that target workspace while invoking the resolved bridge script by its absolute path. Never change into the Skill directory or copy prompt, answer, or permission files there merely to satisfy workspace validation.
2. Start a normal managed job from the target workspace. The bridge uses its process working directory only for local prompt-file isolation; it never sends a workspace or `cwd` field to StartChat:

   ```text
   python3 <absolute-bridge-path>/ros_agent.py start --prompt-file <prompt-file> --mode normal --follow
   ```

   Pass `--region-id` only when the user explicitly supplied a region. Otherwise the bridge uses the first supported region environment variable, then an explicitly pinned Profile region, then `cn-hangzhou`; do not query CLI configuration to fill it. Use `--mode pipeline` only when the user explicitly wants the candidate-architecture, cost-comparison, confirmation, and deployment Pipeline. Thinking is installation policy from `config.json`, not an Agent choice. Forward underspecified infrastructure requirements to ROS Agent as written so its own `ask_user_question` can gather them.
3. Preserve the returned `jobId` and newest `cursor`. A temporary authenticated loopback manager owns the job, and a detached worker keeps the selected StartChat transport open after the outer tool call returns. In the default code transport, each SSE event is projected as it arrives. `--follow` returns at every step start, step completion/failure, input boundary, completed turn, terminal state, or its bounded wait window so the user can see the Pipeline progressing. A result can contain multiple ordered `userUpdates` when events were already queued, and can also contain `inputRequired` or a terminal result; present all updates first, then handle that result without an extra drain-only `follow`.
4. When the result has `boundaryReached: true`, present every `userUpdates` string to the user, then immediately follow from the returned cursor:

   ```text
   python3 <absolute-bridge-path>/ros_agent.py follow --job-id <jobId> --cursor <cursor> --wait-seconds 60
   ```

   Follow waits at most 120 seconds even if a larger value is requested. If it returns `followTimedOut: true`, present its `heartbeat` as a visible status update and call `follow` again with the newest cursor. A timeout never stops the background worker or sends a new StartChat query.
5. For every natural-language follow-up, answer to `ask_user_question`, or `candidate_selection`, write a new prompt file and continue the same job:

   ```text
   python3 <absolute-bridge-path>/ros_agent.py continue --job-id <jobId> --prompt-file <prompt-file> --follow
   ```

   Do not invent a `SessionId`; the job binds the remote session, mode, endpoint, region, Profile, and workspace. When a completed Pipeline returns `normalHandoffReady: true` or `conversationMode: normal`, its next user message is a Normal chat turn reached through this same `continue` command and `jobId`; the bridge intentionally keeps the StartChat mode while the remote A2A context performs the handoff. Never replace that handoff with `start --mode normal`. Do not start a new job merely to continue the same task.
6. Only when the user explicitly asks to stop or cancel the active ROS Agent operation, cancel that same managed job:

   ```text
   python3 <absolute-bridge-path>/ros_agent.py cancel --job-id <jobId>
   ```

   This invokes the ROS `StopChat` OpenAPI through the job's selected transport; it does not send a StartChat query or a natural-language cancellation message. Present the returned status immediately. `Stopped` means cancellation completed, `Stopping` means it was accepted and the existing job should be observed with `follow` from its current cursor, and `NoActiveStream` means there was no active remote stream to stop. Never call `cancel` merely because `follow` timed out, a local tool call was interrupted, or the outer Agent turn ended.

Without a configured endpoint, the bridge defaults to `ros.aliyuncs.com`. Use `--endpoint <ROS endpoint>` only when the user's ROS region or network requires a different endpoint and `config.json` does not fix one. The code transport sends a generic ROS RPC with API version `2019-09-10` and `ACS3-HMAC-SHA256` signing, so it does not depend on generated StartChat metadata. The `aliyun_cli` transport uses the installed/remote ROS plugin's published `start-chat` and `stop-chat` commands and does not bypass plugin validation. Both transports identify every StartChat and StopChat request with the user-agent segment `AlibabaCloud-Agent-Skills/alibabacloud-ros-agent`.

## Architecture before deployment confirmation

Immediately before any create/update deployment confirmation, render one compact `mermaid` `flowchart` showing the resources that would be deployed and their material relationships. This is presentation work by the outer Agent and does not require another StartChat query.

Use only authoritative data already returned for the current plan, in this order:

1. A non-empty `architectureDiagram` returned by ROS Agent.
2. The current ROS/Terraform template artifact. If the result exposes a local artifact `sourcePath` and the returned summary is insufficient, read only that artifact; do not inspect manager state, worker logs, or unrelated files.
3. `finalText`, `deploymentSummary`, candidate details, and other bounded result fields.

For Normal mode, derive the diagram from declared resources and explicit template references or dependencies. For Pipeline mode, render the selected candidate's returned diagram and ensure it still matches the plan being confirmed. Label nodes with user-meaningful resource types or names, group network containment when explicit, and show only relationships supported by the source. Use distinct Mermaid IDs for containers and resource nodes. Keep cloud scopes accurate: an Alibaba Cloud VPC is regional, while a VSwitch belongs to a zone, so put the VSwitch inside the VPC and include its zone in the VSwitch label rather than placing the VPC inside a zone. Collapse large repeated groups to keep the diagram readable. Never invent resources, connections, public exposure, zones, or dependencies. If relationships are unavailable, show a resource inventory diagram without speculative edges and briefly state that the returned plan did not describe the missing relationships.

Present the deployment summary, fenced Mermaid block, and confirmation question in that order. Do not ask for confirmation first and add the diagram afterward. A later permission prompt may summarize the same plan without regenerating the diagram if the proposed architecture has not changed; if it has changed, render the updated diagram before seeking confirmation again.

## Optional context and images

With the `code` transport only, use `--client-context-file <json-file>` for a JSON object accepted by StartChat. Keep this file inside the workspace and exclude secrets. The bridge rejects common credential-bearing keys at any nesting depth; if rejected, remove the sensitive fields and never retry with copied Profile or credential data. The ROS CLI plugin does not expose ClientContext, so the bridge rejects this option for both local and remote `aliyun_cli` execution.

Use `--attachments-file <json-file>` for up to five OSS-backed images. The file must be a JSON array such as:

```json
[
  {
    "Type": "image",
    "MimeType": "image/png",
    "Name": "architecture.png",
    "OssObjectKey": "user/workspace/architecture.png"
  }
]
```

The bridge also accepts lower camel case and snake case field names. Do not use local paths, inline image bytes, or secret-bearing URLs. StartChat V2 currently supports `image/png`, `image/jpeg`, `image/webp`, and `image/gif` OSS objects.

## Interpret the result

Stdout is one bounded JSON object; diagnostics belong to stderr.

- `state: turn-completed`: present `finalText` and `artifacts` as the authoritative normal-turn result.
- `state: input-required`: present the prompt, safe action details, and every option from `inputRequired`. Treat correlation fields as bridge-owned opaque data; do not copy or rewrite them. For `ask_user_question` or `candidate_selection`, send the user's answer with `continue` on the same `jobId`.
- For `candidate_selection`, show every option's label, summary, `totalMonthlyCost`, and `costItems`. Render each non-empty `architectureDiagram` as its own fenced `mermaid` block before asking the user to choose; never leave the diagram as escaped JSON or only inside tool output.
- A permission in `inputRequired` includes `permissionClass`: `normal` for a Normal conversation or `pipeline` for a top-level Pipeline permission. A permission in `pendingPermissions` uses `sub_pipeline`.
- `pendingPermissions` contains every currently visible Sub Pipeline step permission. Present them separately; multiple candidate steps may wait for permission at the same time.
- For a terminal Pipeline, present `pipelineResult` and `artifacts` as the authoritative deployment conclusion. `normalHandoffReady: true` or `conversationMode: normal` means later operations must continue this job as Normal chat. Do not claim success from milestones alone.
- `state: failed`: report the sanitized `error`; preserve `requestId` when present for support.
- `milestones` contains bounded Pipeline progress. Show useful step boundaries without treating them as final output.
- `boundaryReached: true` means the result contains transient progress at a step start, completion, or failure. Present every `userUpdates` entry in order. If the same result also contains `inputRequired`, `turn-completed`, or a terminal state, handle it immediately; otherwise call `follow` again with the returned cursor.
- `wireState` preserves the last A2A task state for diagnosis. A normal turn may end with wire state `TASK_STATE_INPUT_REQUIRED` without an input envelope; the bridge reports that case as `turn-completed`, matching the remote agent's conversational boundary.

The event classes have different execution behavior:

- `ask_user_question` and `candidate_selection` are business input. The selling Pipeline's top-level scheme confirmation is `candidate_selection`, not a tool permission. Answer both with `continue` on the same `jobId`. For `candidate_selection`, the prompt file must contain only the exact chosen `options[].id` returned by the current envelope (for example `1`), with no label, explanation, deployment request, or surrounding sentence; this avoids the Pipeline interpreting the answer as an unrecognized selection and asking again.
- Never call `respond` for `ask_user_question` or `candidate_selection`, even if their envelope contains `inputId`, `requestTaskId`, or other correlation fields. Put the user's selected option and any parameter choices in a natural-language prompt file and call `continue`.
- A Normal conversation permission has `permissionClass: normal`. It serially pauses the task with `TASK_STATE_INPUT_REQUIRED`.
- A top-level Pipeline tool permission has `permissionClass: pipeline`. It serially pauses the parent Pipeline and its agent loops with `TASK_STATE_INPUT_REQUIRED`. This is distinct from `candidate_selection`.
- A Sub Pipeline step permission has `permissionClass: sub_pipeline`. It is sideband: the parent task remains `TASK_STATE_WORKING`, and multiple candidate steps may have independent pending permissions.

## Approve or deny a permission

Do not answer a permission with natural language or create a permission JSON file. The managed job already owns the exact correlation identifiers. When exactly one permission is waiting, call `respond` with only the job and the user's decision:

```text
python3 <absolute-bridge-path>/ros_agent.py respond --job-id <jobId> --decision <allow_once|deny> --follow
```

If multiple `pendingPermissions` are waiting, keep each returned `permissionRef` associated with the action shown to the user and include only the selected short reference:

```text
python3 <absolute-bridge-path>/ros_agent.py respond --job-id <jobId> --permission-ref <permissionRef> --decision <allow_once|deny> --follow
```

Never type, copy, reconstruct, transform, or save `requestTaskId`, `contextId`, `inputId`, or `toolUseId`. Do not use a shell or another script to extract `inputRequired`; `respond` resolves those fields atomically from the current job. Without `--permission-ref`, it fails closed if more than one permission is waiting. A supplied reference must match exactly one still-pending permission.

The job preserves its original mode and validates the permission class. When the user has already made an explicit `allow_once` or `deny` decision, execute `respond` in that same agent turn. Do not stop after merely announcing that you will run it.

The bridge selects the pending permission under the job lock, retrieves its original correlation identifiers, and sends the same fixed marker and compact payload as the complete StartChat `Query`:

```text
IAC_CODE_PERMISSION: {"schemaVersion":1,"kind":"permission","requestTaskId":"<requestTaskId>","contextId":"<contextId>","inputId":"<inputId>","toolUseId":"<toolUseId>","decision":"<allow_once|deny>"}
```

The JSON portion has this schema:

```json
{
  "schemaVersion": 1,
  "kind": "permission",
  "requestTaskId": "<requestTaskId>",
  "contextId": "<contextId>",
  "inputId": "<inputId>",
  "toolUseId": "<toolUseId>",
  "decision": "<allow_once|deny>"
}
```

`permissionRef` is a short local selector and is never sent to StartChat. Do not add client context or attachments to a permission response. The iac-code A2A server checks the exact `IAC_CODE_PERMISSION:` prefix before decoding JSON, then validates the full payload against an active pending permission. Missing or altered prefixes, extra fields, surrounding text, mismatched context, stale identifiers, and conflicting replies fail closed.

The three permission classes share this one StartChat `respond` command, but resume differently:

- `normal`: serial. The StartChat stream that exposed the permission ends naturally. `respond` uses the same correlated ROS Agent session and returns the resumed output on its new stream.
- `pipeline`: while resident, the original parent Pipeline StartChat stream stays alive. `respond` uses ROS active Pipeline reentry only to deliver the correlated decision; resumed progress remains on the parent stream. If `permissionWait.status` is `suspended`, the parent stream has ended and `respond` recovers the same task from its durable boundary on the new stream.
- `sub_pipeline`: sideband. Correlation identifies the waiting candidate step while the parent task remains `TASK_STATE_WORKING`; multiple pending step permissions must be answered separately. The bridge keeps the original parent StartChat SSE worker alive and starts a separate concurrent StartChat worker for each response. That response stream ends after its acknowledgement; it never takes ownership of, drains, or replaces the parent stream. After acknowledgement, another pending permission can become `inputRequired`; otherwise `follow` continues observing the original parent worker until its next Pipeline boundary.

`permissionResponse` records the bounded correlation payload sent by the bridge. For a live Pipeline reentry, require `permissionAck.accepted: true` before reporting acceptance. For a serial or recovered permission, interpret the resumed stream normally and surface any next `inputRequired` event. Treat `permissionWait.status=suspended` with `resumable=true` as a recoverable pause: ask for the decision against the original `inputRequired` and call `respond` on the same job. Treat `permissionRecovered` as continuation of that same job; never start a replacement session.

Never use `continue` to poll a working Pipeline after `respond`. StartChat has no status-query operation, and a new natural-language message is a real Pipeline interrupt. Use only `follow` to observe the original parent SSE. If `respond` returns `input-required`, present and answer that newly visible permission. If it returns only `permission-responded` because other already-presented `pendingPermissions` remain, answer those permissions separately; otherwise keep following the current job. Do not ask the user to choose between `follow` and `continue`.

## Safety and output discipline

- Never print, persist, or pass AccessKey IDs, secrets, security tokens, signatures, or authorization headers.
- Unit tests and validation must remain offline. Run a live StartChat or cloud deployment test only when the user explicitly authorizes that external action and its cleanup scope.
- Treat `latestText` as progress only. Use `finalText` only when `state` is `turn-completed`.
- Keep `sessionId`, `taskId`, and `iacCodeSessionId` as opaque identifiers.
- Interrupting a `follow` command does not cancel the background StartChat worker. Report the interruption and resume `follow` with the last confirmed cursor. Use `cancel` only after an explicit user cancellation request. If the worker itself fails, report its sanitized error; do not claim the remote task was canceled.
- Treat the bridge JSON as the only job-state interface. Do not inspect `~/.cache/alicloud-ros-agent`, manager records, worker logs, the bridge source, or Alibaba Cloud CLI configuration to diagnose a failed job; present the returned sanitized `error` and let the operator inspect the server side.


## Input/output examples

Input: "Review this ROS template, explain validation errors, and propose a corrected version."

Expected output: the bridge returns the authoritative ROS Agent response and preserves the same session for follow-up questions, permissions, and final artifacts.

## Edge cases

If credentials, endpoint metadata, or permissions are unavailable, stop with the returned actionable error. Reuse the returned session ID for follow-ups and StopChat. If a stream is interrupted, resume the frozen job instead of silently creating a second cloud session.

## RAM permissions

Before the first ROS API request, read [references/ram-policies.md](references/ram-policies.md) and verify that
the selected credential has only the exact ROS actions required for the requested conversation and cancellation path.

## Observability

All outbound HTTP requests made by this AgentHub Skill carry this `User-Agent` template:

```text
AlibabaCloud-Agent-Skills/alibabacloud-ros-agent/{session-id}
```

- `alibabacloud-ros-agent` is the fixed AgentHub Skill identifier and matches the frontmatter `name`.
- The session ID must be a 32-character lowercase hexadecimal string generated exactly once per session.
  It must be reused unchanged for every outbound HTTP request in that session. The bridge reads `SKILL_SESSION_ID`
  after validation; if it is absent or invalid, the bridge generates the session ID with `uuid.uuid4().hex` and stores
  it for that session.
