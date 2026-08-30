# RAM permissions

## Required RAM actions

None.

This bootstrap Skill connects to Dgate through the managed MCP service or the
`dgate` CLI. It authenticates with a Region-bound Dgate Agent AccessToken and
uses Dgate's own Agent identity, instance ACL, security policy, and audit
controls. It does not call Alibaba Cloud OpenAPI directly and does not require
the user to grant Alibaba Cloud RAM actions, provide an AccessKey ID/Secret, or
attach a RAM policy.

Instance authorization is configured inside Dgate and must remain
least-privilege. Do not treat a Dgate platform role, MCP connectivity, or
metadata visibility as instance-level data permission.

If a future version calls Alibaba Cloud OpenAPI directly, declare the minimum
required RAM actions here and update `related_apis.yaml` before release.
