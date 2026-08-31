# RAM Policies

**This skill requires NO Alibaba Cloud RAM permissions.**

The skill manages QianWen support tickets exclusively through:
- The `qianwen` CLI (browser device-flow session), or
- The QianWen platform HTTP API (`https://cli.qianwenai.com/data/v2/api.json`)
  authenticated with a device-flow Bearer token.

Neither path invokes Alibaba Cloud OpenAPI, so no RAM actions
(`*:Get*`, `*:List*`, `*:Create*`, etc.) are required and none are declared.

Alibaba Cloud main/sub-account AccessKeys and STS tokens are NOT used and
CANNOT authenticate these endpoints (see SKILL.md Credentials section).
