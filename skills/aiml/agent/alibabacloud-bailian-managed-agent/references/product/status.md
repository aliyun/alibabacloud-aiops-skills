# Product status corrections

Sources: explicit user-provided product corrections on **2026-09-18** and **2026-10-09**, with separately dated live checks below. Launch status and positioning do not by themselves verify a configuration schema. Consult current official MA documentation for execution details and applicable scope.

The following capabilities are launched, superseding the archived whitepaper's `coming soon` labels:

| Capability | Current positioning |
| --- | --- |
| MultiAgent | Multi-agent collaboration |
| Memory Store | MA built-in memory, primarily working memory |
| `web_search` / `web_fetch` | Built-in web tools; preferred for search and webpage reading |
| browser_use | Available through MCP; do not describe it as a built-in tool |
| Events multimodal | Multimodal event content |
| Events Delta and Thinking | Incremental output and Thinking events |
| Resource add/remove | Dynamic resource mounting/unmounting |
| Webhook | Event notifications |

## Two distinct memory products

- **MA Memory Store**: built into Managed Agents, primarily for working memory and task context.
- **Bailian Memory Library**: a separate memory service, primarily for personalized memory with a supplied **UserId** dimension.

Do not infer MA Memory Store native binding, APIs, identifiers or isolation semantics from Bailian Memory Library documentation. Select the product by task-context versus user-personalization needs, then verify that product's current contract.

The local [whitepaper edition](whitepaper-source.md) was also updated on 2026-09-18 at the user's request, with a visible revision note; it is no longer an unchanged historical snapshot. GitHub/Gitee repository mounting and built-in aliyun-cli were not covered by this launch correction; their old labels alone do not establish current availability.

## Asynchronous readiness (user correction, 2026-09-18)

- Environments with preinstalled packages may have a short preparation period after creation. Creating a Session during preparation can fail; wait until the Environment is ready. This correction does not specify API status names, error codes or a guaranteed duration.
- Uploaded files have a short detection/security-review period. Wait for review to pass before attaching or mounting them. The existing [file tutorial](../tutorials/03-mount-files.md) documents polling for `available` and stopping on rejection.

Both are prerequisites for a Session using a newly prepared Environment and newly uploaded files; a successful create/upload response alone is insufficient.

## Web tool naming and routing (2026-09-18)

User correction and current [official tool documentation](https://docs.agent.bailian.aliyun.com/zh/managed-agents/build-agent/tools.md) agree: the API names are **`web_search` and `web_fetch`** (underscores). Prefer them for internet access. `websearch` / `webfetch` in earlier notes were informal names, not configuration keys. The historical claim that these tools do not exist is superseded. Browser interaction uses an activated MCP service, not a built-in `browser_use` entry.

## Live practice and known discrepancies

Live tests on 2026-09-18 covered built-in web tools, cross-session working memory, image file_id input, Delta/Thinking, dynamic files, main-Agent approval, MultiAgent, manual Deployment, and Vault placeholders. The [cookbook index](../cookbook/index.md) routes these to their scenario recipes: web research in 05, memory in 09, images in 10, and streaming/file interactions in 11; approval, Deployment, MultiAgent, and Vault remain in 02 / 04 / 08. The 2026-10-09 online retest verified 05's built-in worker/coordinator path, 09's explicit memory handoff and conditional API updates, 10's supported image routes, and 11's Delta assembly, protocol-level reconnection, and file add/remove between turns. A complete browser application and file updates during active tool execution were not tested; no matched cost benchmark was run. Base64 image input is currently unsupported; the user confirmed the earlier documentation error and reproduction evidence was retained. browser_use and current-run Webhook delivery still require an activated MCP service and a controlled receiver respectively; neither was verified in this run.

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
