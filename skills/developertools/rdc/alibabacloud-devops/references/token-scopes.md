# Yunxiao Personal Access Token Authorization Scopes

All MCP calls in this Skill authenticate using `YUNXIAO_ACCESS_TOKEN`. Different toolsets correspond to different authorization scopes. If the Token's authorization is insufficient, you will receive a `401` (unauthenticated) or `403` (insufficient permissions) error.

## Obtaining / Managing Tokens

- Yunxiao platform -> Personal Settings -> Personal Access Tokens -> Create / Edit
- Official documentation: [Obtain Personal Access Token](https://help.aliyun.com/zh/yunxiao/developer-reference/obtain-personal-access-token)

## Toolset <-> Authorization Scope

| Toolset | Recommended Authorization Scope (select read/write as needed) |
|---------|--------------------------------------------------------------|
| `base` | Organization management (read) |
| `organization-management` | Organization management (read/write) |
| `code-management` | Code management (read/write) |
| `pipeline-management` | Pipeline (read/write) |
| `packages-management` | Packages (read/write) |
| `project-management` | Project collaboration (read/write) |
| `test-management` | Test management (read/write) |
| `application-delivery` | Application delivery (read/write) |

> Principle of least privilege: If you only need to query, select "read"; only check "write" when you need to modify or delete.

## Failure Handling Workflow

1. **401 Unauthenticated**
   - Possible causes: Token expired / manually revoked / environment variable not configured
   - Resolution: Guide the user to regenerate the Token and update the `YUNXIAO_ACCESS_TOKEN` environment variable in the MCP Server
2. **403 Insufficient Permissions**
   - Check the table above to confirm the required authorization scope for the current tool's toolset
   - Guide the user to edit the Token under "Personal Access Tokens" and add the corresponding authorization scope
   - Some operations also require **resource-level permissions**:
     - Code management: Repository Reporter/Developer/Master/Owner
     - Pipeline: Pipeline/group read/write
     - Project collaboration: Project member + role (Owner/Admin/Member)
     - Application delivery: Application Owner/Operator/Member
3. **Prompt the user** to regenerate the Token or adjust resource membership, then **pause** execution and wait for the user to confirm that permissions have been restored before continuing.

## Follow-up Template (Insufficient Permissions)

```
This operation requires the Token to have {authorization scope for the toolset}. The current call failed (HTTP {errCode}): {errMsg}.
Please:
1. Go to "Personal Settings -> Personal Access Tokens", edit the Token, and check {required scope} (read/write)
2. If operating on a specific resource, ensure you have a sufficient member role in the corresponding {project/repository/application}
3. After completing the above, regenerate/save the Token and update the YUNXIAO_ACCESS_TOKEN environment variable in the MCP Server
Please reply "updated" when done, and I will retry.
```
