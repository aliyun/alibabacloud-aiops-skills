# RAM Policies

## required_permissions

RAM permission points for the Alibaba Cloud API operations explicitly invoked by
this Skill. Each operation maps to one `{Product}:{Action}` value.

| API Operation | Usage | Permission Required |
| ------------- | ----- | ------------------- |
| `GetCallerIdentity` | Verify the current CLI identity | `sts:GetCallerIdentity` |
| `ListApiMcpServerCores` | Check whether an API MCP Server Core already exists | `openapiexplorer:ListApiMcpServerCores` |
| `CreateApiMcpServerCore` | Create an API MCP Server Core after user confirmation | `openapiexplorer:CreateApiMcpServerCore` |
| `GenerateAccessToken` | Exchange the bearer token through the RamOAuth endpoint | `ram:GenerateAccessToken` |

For MCP Server Core permission errors, the Skill directs the user to the managed
system policy `AliyunOpenAPIMCPServerStaticCredentialAccess`.

`ram:GenerateAccessToken` uses deny-only authorization and does not require an
explicit `Allow` by default. If it returns `NoPermission`, check for an applicable
explicit `Deny` instead of adding a broader policy.

Local CLI operations such as `aliyun configure`, `aliyun plugin`, and `aliyun version`
do not call account-scoped cloud APIs and therefore require no RAM Action here.
