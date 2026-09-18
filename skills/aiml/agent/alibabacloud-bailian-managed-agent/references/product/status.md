# Product status corrections

Source: explicit user-provided product correction on **2026-09-18**. This records launch status and positioning, not a live API test or a verified configuration schema. Consult current official MA documentation for execution details and applicable scope.

The following capabilities are launched, superseding the archived whitepaper's `coming soon` labels:

| Capability | Current positioning |
| --- | --- |
| MultiAgent | Multi-agent collaboration |
| Memory Store | MA built-in memory, primarily working memory |
| websearch / webfetch | Built-in web tools |
| browser_use | Available through MCP; do not describe it as a built-in tool |
| Events multimodal | Multimodal event content |
| Events Delta and Thinking | Incremental output and Thinking events |
| Resource add/remove | Dynamic resource mounting/unmounting |
| Webhook | Event notifications |

## Two distinct memory products

- **MA Memory Store**: built into Managed Agents, primarily for working memory and task context.
- **Bailian Memory Library (百炼记忆库)**: a separate memory service, primarily for personalized memory with a supplied **UserId** dimension.

Do not infer MA Memory Store native binding, APIs, identifiers or isolation semantics from Bailian Memory Library documentation. Select the product by task-context versus user-personalization needs, then verify that product's current contract.

The local [whitepaper edition](whitepaper-source.md) was also updated on 2026-09-18 at the user's request, with a visible revision note; it is no longer an unchanged historical snapshot. GitHub/Gitee repository mounting and built-in aliyun-cli were not covered by this launch correction; their old labels alone do not establish current availability.
