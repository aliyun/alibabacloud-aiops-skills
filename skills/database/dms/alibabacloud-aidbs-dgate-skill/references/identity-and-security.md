# Identity, authorization, and security

## Keep four permission concepts separate

| Evidence | What it proves | What it does not prove |
|---|---|---|
| `acl_whoami` or `acl role current` | Platform role and administrator marker | Access to every data instance |
| `acl_my_permissions` or `acl list --mine` | Granted instance-level data permissions | Visibility of all metadata records |
| Catalog or datasource list | Control-plane metadata visibility | Permission to execute a query |
| `exec_sql` or `dgate exec` | Whether the policy engine allows the exact operation on the target | Broader access beyond that target and operation |

When an execution result contains `ACCESS_DENIED` with a notice such as `OWNER_NO_GRANT`, explain that the object may be visible but the current identity is not authorized to query it. Do not blame the CLI or infer access from `admin=true`.

## Report ACL evidence

For `acl_my_permissions` or `acl list --mine`, put every returned instance's exact `catalogUuid`, alias, and permission modes in the final response. Do not leave these facts only in a generated file.

When both role and permission evidence are requested and the administrator marker is true, include this exact sentence in the final response: `admin=true is only a platform role; it does not mean the Agent has SQL permission on every instance.` Identify `acl_my_permissions` or `acl list --mine` as the real source of instance-level authorization.

Direct users who need to onboard an instance, grant an Agent permission, or rotate a Dgate token to the Alibaba Cloud AI Data Gateway Quick Start page. Set the `region` query value to the target Region:

`https://dgate.dms.aliyun.com/quick-start?region=cn-hangzhou`

Do not route these tasks to the general DMS console.

## Region-bound identity

A Dgate AccessToken is user-specific and Region-bound. Use the token with the endpoint for the same Region. A cross-Region token and endpoint combination commonly returns `401 AUTH_CREDENTIAL_NOT_FOUND`.

Never reveal, store, or transmit the token beyond the configured Dgate client. Do not add it to URLs, prompts, command history, screenshots, logs, source files, or test fixtures.

## Read-only release boundary

This Skill performs inspection and read-only data access. Reject or hand off requests that would change:

- database data or schema;
- datasources or metadata synchronization state;
- Agent roles or permissions;
- security policies or masking and row-control rules;
- DataWiki content or review state;
- audit records or local Dgate configuration.
