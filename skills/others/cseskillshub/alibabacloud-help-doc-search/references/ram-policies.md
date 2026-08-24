# RAM Permission Requirements

This skill requires **no RAM permissions at all**.

All data sources are public and anonymous:

| Endpoint | Purpose | Authentication |
|---|---|---|
| `https://help.aliyun.com/zh/**` (llms.txt / .md) | Document indexes and bodies | None |
| `https://t.aliyun.com/abs/search/doSearch` | Full-text help-document search | None |
| `https://api.aliyun.com/meta/v1/**` | OpenAPI metadata contracts | None |

The skill never invokes the aliyun CLI, never calls credentialed OpenAPI actions, and
never reads or transmits credentials, AccessKeys, or account data. No RAM policy needs
to be attached to any role or user for this skill to function.
