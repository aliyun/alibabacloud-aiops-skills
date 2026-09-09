# RAM Permissions

This skill exposes the `alibabacloud.mcp-proxy` MCP tools as local commands. It does not
call a fixed set of OpenAPI actions itself: which resource APIs run (ECS, VPC, OSS, RDS,
SLS, ...) is decided at runtime by what the user asks for, and the documented example
commands are illustrative rather than a fixed surface. Their permissions are therefore
governed by the caller's own RAM policy and are not enumerated here.

The one permission this skill itself depends on is what the MCP service needs in order to
issue credentials on behalf of the caller.

## Required permission

| Permission | Why it is needed | Who configures it |
|---|---|---|
| `AliyunOpenAPIMCPServerStaticCredentialAccess` | The MCP service requires this permission point to mint credentials for the caller. Without it, `aliyun` CLI login can still succeed, yet the MCP handshake is rejected with `code: 403, You are not authorized to perform this action`. | Primary account / RAM administrator |

Attach it to the identity that runs `mcpx login`. A sub-account and the primary account are
distinct identities — granting the primary account does not grant the sub-account.

This is a single, specific permission point, not a wildcard. No `*`-scoped permission is
required or declared.
