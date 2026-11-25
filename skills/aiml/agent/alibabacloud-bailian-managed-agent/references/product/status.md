# Product status corrections

Sources: explicit user-provided product corrections on **2026-09-18**, **2026-10-09**, **2026-10-23**, **2026-10-29**, **2026-11-02**, **2026-11-09**, **2026-11-10**, **2026-11-11**, and **2026-11-17**, with separately dated live checks below. Launch status and positioning do not by themselves verify a configuration schema. Consult current official MA documentation for execution details and applicable scope.

The following capabilities are launched, superseding the archived whitepaper's `coming soon` labels:

| Capability | Current positioning |
| --- | --- |
| MultiAgent | Multi-agent collaboration |
| Memory Store | MA built-in memory, primarily working memory |
| Bailian Memory Library binding | Session `resources[].provider=agentstudio_memory`; facts, skills and profiles scoped by library/entity |
| Knowledge retrieval | Built-in `search_knowledgebases` configured with a published retrieval service ID |
| `web_search` / `web_fetch` | Built-in web tools; preferred for search and webpage reading |
| browser_use | Available through MCP; do not describe it as a built-in tool |
| Events multimodal | Multimodal event content |
| Events Delta and Thinking | Incremental answers and Thinking text; nonempty reasoning verified in 5/5 fresh Sessions on 2026-10-23 |
| Resource add/remove | Dynamic resource mounting/unmounting |
| Webhook | Event notifications |
| Usage queries | Workspace/Agent/Session summaries and workspace/Agent hourly/daily/monthly trends, with model/tool details; [contract and live scope](../integration/usage-api.md) |
| Sandbox snapshot persistence | Opt-in retention of working files and environment modifications; automatic refresh on successful new snapshots; [lifecycle and recovery rules](../integration/sandbox-persistence.md) |

## Sandbox persistence (user clarification and official docs, 2026-11-17)

The user confirmed launch and supplied the resource recovery matrix and **CNY 0.003 per snapshot-hour** price. The [official Session operations guide](https://help.aliyun.com/zh/model-studio/managed-agents-session-operations), checked that day, resolves the previously uncertain retention start: **new snapshot creation time**, after sandbox use and eligibility for recycling. Recovery alone does not refresh retention. See [sandbox persistence](../integration/sandbox-persistence.md) for the API fields, lifecycle, external-data precedence and the three-day renewal example. This update did not run cloud recovery or billing tests.

## Usage queries (user contract and live probes, 2026-11-11)

The supplied contract adds read-only `POST /usage/summary` and `POST /usage/trend`. Existing-record probes in one cn-beijing workspace verified scope selection, time alignment, pagination and historical summary/trend reconciliation, empty/unknown semantics and parameter errors. Usage is asynchronously updated consumption, not a bill or real-time progress feed. Session summaries cover the lifetime and have no time/granularity filter; Session trends are unsupported. Use [Usage API](../integration/usage-api.md) for metric definitions, reproducible probes and explicitly untested limits. These observations do not establish SDK/CLI coverage or rollout in other workspaces.

## Two distinct memory products

- **MA Memory Store**: built-in working files, attached with omitted/`default` provider and read through the returned mount path.
- **Bailian Memory Library**: memory service for facts, skills and profiles; MA supports native Session binding with **`provider=agentstudio_memory`** and required **`entity_id`**. No filesystem path is returned.

Both use `resources[].type=memory_store`, but their resource IDs, service APIs and isolation semantics remain different. A Session cannot mix providers. This binding contract is documented in the [current Create Session API](https://docs.bailian.console.aliyun.com/zh/model-studio/session-create), checked **2026-11-09**, and supersedes earlier guidance that only described the two products separately. Configuration and boundaries: [knowledge and memory integration](../integration/knowledge-and-memory.md).

The local [whitepaper edition](whitepaper-source.md) was also updated on 2026-09-18 at the user's request, with a visible revision note; it is no longer an unchanged historical snapshot. GitHub/Gitee repository mounting and built-in aliyun-cli were not covered by this launch correction; their old labels alone do not establish current availability.

## Asynchronous readiness (user correction, 2026-09-18)

- Environments with preinstalled packages may have a short preparation period after creation. Creating a Session during preparation can fail; wait until the Environment is ready. This correction does not specify API status names, error codes or a guaranteed duration.
- Uploaded files have a short detection/security-review period. Wait for review to pass before attaching or mounting them. The existing [file tutorial](../tutorials/03-mount-files.md) documents polling for `available` and stopping on rejection.

Both are prerequisites for a Session using a newly prepared Environment and newly uploaded files; a successful create/upload response alone is insufficient.

## Web tool naming and routing (2026-09-18)

User correction and current [official tool documentation](https://docs.agent.bailian.aliyun.com/zh/managed-agents/build-agent/tools.md) agree: the API names are **`web_search` and `web_fetch`** (underscores). Prefer them for internet access. `websearch` / `webfetch` in earlier notes were informal names, not configuration keys. The historical claim that these tools do not exist is superseded. Browser interaction uses an activated MCP service, not a built-in `browser_use` entry.

## Tool configuration priority (user clarification, 2026-10-29)

Within each tool group, explicit `configs[]` entries take precedence; tools absent from `configs[]` use `default_config`. Prefer a disabled default and explicitly enable only required tools so newly added tools do not change the enabled inventory. An enabled default is appropriate when automatic adoption of toolkit additions is desired. This supersedes the older claim that `default_config.enabled: true` is ineffective without per-tool entries. Details and example: [tool configuration](../integration/tool-configuration.md). This is a user-provided clarification, not a new cloud test result.

## Task planning tool (user clarification, 2026-11-02)

`todo_write` maintains a structured to-do list recording task steps and their status. Use it to break down long tasks and track the execution progress of multi-step tasks. This capability description comes from the user's clarification; no cloud test was run for this update. Tool-call parameters, status enum values, and persistence semantics were not supplied and must not be inferred from the tool name.

## Vault header replacement scope (2026-11-02)

Source: user correction and the [official credential documentation](https://docs.agent.bailian.aliyun.com/zh/managed-agents/sessions/credentials), checked 2026-11-02. For a destination matching the credential's `allowed_hosts`, the gateway replaces matching credential placeholders in **all HTTP request headers**, including `Authorization`, `X-API-Key`, and custom headers. Request-body and query-parameter placeholders remain unchanged; destinations outside the allowlist receive placeholders.

This supersedes the archived Authorization-only restriction and advice to move every credential into that header. The 2026-09-03 host-only selection and same-host ambiguity observations remain historical evidence, not current implementation guarantees. This update verifies documentation, not a new live cloud test. Configuration and examples: [Vault cookbook](../cookbook/08-vault-secret-injection-and-egress-gateway.md).

## Local signing requires real key material (user clarification, 2026-11-10)

The user clarified that SDKs/CLIs performing local signing or HMAC cannot use a Vault placeholder as the signing secret: they sign the placeholder bytes before the request reaches the gateway, and header substitution cannot repair the derived signature. The [current official credential guide](https://docs.bailian.console.aliyun.com/zh/model-studio/managed-agents-credential), checked **2026-11-10**, confirms placeholder replacement in HTTP headers and the distinct runtime exposure of plaintext Session environment variables; the local-signing conclusion is the user's clarification, not a new live signing test.

Choose by authentication mechanism: direct header API keys/tokens fit Vault; verified local-signing clients can receive real credentials through Session-start `environment_variables` within the authorized scope, or use a trusted external signer when keys must stay outside the sandbox. Plaintext injection exposes the value to runtime code and Session readers; build requests in-process, use variable names rather than values in prompts, and omit secret-bearing request/response/debug data from logs and reports. This is a compatibility trade-off, not an equally isolated replacement for Vault.

Do not infer this failure from an SDK/CLI name, a timeout or unrelated errors. Apply it to a specific Session only when the authentication path and evidence support it. Selection and verification: [Vault cookbook signing branch](../cookbook/08-vault-secret-injection-and-egress-gateway.md#sdkcli-local-signing-and-hmac-user-clarification-2026-11-10).

## Live practice and known discrepancies

Live tests on 2026-09-18 covered built-in web tools, cross-session working memory, image file_id input, Delta/Thinking, dynamic files, main-Agent approval, MultiAgent, manual Deployment, and Vault placeholders. The [cookbook index](../cookbook/index.md) routes these to their scenario recipes: web research in 05, memory in 09, images in 10, and streaming/file interactions in 11; approval, Deployment, MultiAgent, and Vault remain in 02 / 04 / 08. The 2026-10-09 online retest verified 05's built-in worker/coordinator path, 09's explicit memory handoff and conditional API updates, 10's supported image routes, and 11's Delta assembly, protocol-level reconnection, and file add/remove between turns. A complete browser application and file updates during active tool execution were not tested; no matched cost benchmark was run. Base64 image input is currently unsupported; the user confirmed the earlier documentation error and reproduction evidence was retained. browser_use and current-run Webhook delivery still require an activated MCP service and a controlled receiver respectively; neither was verified in this run.

## Thinking text and current SSE frames (2026-10-23)

Thinking delta supports subscribing to the actual reasoning text. Live cn-beijing REST tests with `qwen3.8-max` and `enable_thinking=true` verified **5/5 fresh Sessions** on 2026-10-23. They received 37 / 17 / 29 / 15 / 31 nonempty reasoning fragments respectively; every run matched the completed content block, reasoning event, and Event List, and reached `idle/end_turn`.

The live payload used `object=message,status=in_progress` to identify the parent, then `object=content,type=text,msg_id,index,delta,text` for content. Append `delta=true`; replace `delta=false` snapshots and completed messages. The official SSE pages checked that day still showed `event_start/event_delta`; do not mistake that older envelope for the only live format. Keep reasoning separate from the answer. Configuration, frame examples, reproducible verification and scope: [cookbook 11](../cookbook/11-client-integration-practice.md#4-separate-thinking-activity-from-turn-completion). This retest did not cover other models/regions, SDK delta support, reconnection, or browser rendering.

## Base64 image input: currently unsupported (user confirmation, 2026-09-18)

Source: after the live tests, the user explicitly confirmed that Base64 is currently unsupported and the documentation is incorrect. The user also noted that official documentation may be updated later.

- Do not currently use Base64 `image_data` plus `media_type` for MA image input. An accepted POST or an image block retained in history does not prove that the model received the image.
- Use the verified path: upload the image, wait for `available`, then send `type: image` with `file_id`.
- The earlier official send-event documentation incorrectly described Base64 support. This is a dated product correction, not an unresolved diagnosis.
- Check current official documentation for future implementations. Removing the Base64 claim is a documentation correction; an explicit future launch of support requires a successful retest before changing this record. Do not describe the present limitation as permanent.

See the [multimodal cookbook](../cookbook/10-multimodal-input.md) for observations and the working alternative. Troubleshooting identifiers remain in local audit notes only.

## Auto-model image follow-up (2026-09-19)

A live cn-beijing test with `model.id=auto` successfully identified a synthetic red PNG sent through an uploaded, available `file_id`, answering `Red` without tool calls. The Agent configuration was read back as `auto`; no claim is made about the underlying routed model. See the [multimodal cookbook](../cookbook/10-multimodal-input.md). This test did not repeat Base64 input.

The 2026-10-09 retest also passed with `auto`, `qwen3.8-max`, and `qwen3.7-plus` using available image file IDs; it did not repeat Base64 input.

## Performance does not support multimodal input (user confirmation, 2026-10-09)

The user explicitly confirmed that **`performance` does not support multimodal input**. Its inability to view the uploaded image in the 2026-09-19 and 2026-10-09 tests is consistent with that limitation, not an unresolved route failure. For image input, use `auto` or an explicitly supported model and a new Session. See the [multimodal cookbook](../cookbook/10-multimodal-input.md) for the verified flow.
