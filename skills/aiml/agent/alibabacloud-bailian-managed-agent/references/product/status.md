# Product status corrections

Source: explicit user-provided product correction on **2026-09-18**. This records launch status and positioning, not a live API test or a verified configuration schema. Consult current official MA documentation for execution details and applicable scope.

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

Live tests on 2026-09-18 covered built-in web tools, cross-session working memory, image file_id input, Delta/Thinking, dynamic files, main-Agent approval, MultiAgent, manual Deployment, and Vault placeholders. Reusable procedures are in cases 09–11 of the [cookbook index](../cookbook/index.md). Base64 image input is currently unsupported; the user confirmed the earlier documentation error and reproduction evidence was retained. This does not change the launch status of multimodal events. browser_use and current-run Webhook delivery still require an activated MCP service and a controlled receiver respectively; neither was verified in this run.

## Base64 image input: currently unsupported (user confirmation, 2026-09-18)

Source: after the live tests, the user explicitly confirmed that Base64 is currently unsupported and the documentation is incorrect. The user also noted that official documentation may be updated later.

- Do not currently use Base64 `image_data` plus `media_type` for MA image input. An accepted POST or an image block retained in history does not prove that the model received the image.
- Use the verified path: upload the image, wait for `available`, then send `type: image` with `file_id`.
- The earlier official send-event documentation incorrectly described Base64 support. This is a dated product correction, not an unresolved diagnosis.
- Check current official documentation for future implementations. Removing the Base64 claim is a documentation correction; an explicit future launch of support requires a successful retest before changing this record. Do not describe the present limitation as permanent.

See the [multimodal cookbook](../cookbook/10-multimodal-delta-and-thinking.md) for observations and the working alternative. Troubleshooting identifiers remain in local audit notes only.
