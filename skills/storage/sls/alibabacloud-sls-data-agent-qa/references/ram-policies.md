# RAM Permissions

The Python scripts call SLS with the identity selected by the [Credentials SDK](python-runtime.md#endpoints-and-credentials). Grant that RAM user or role two independent kinds of access: **read the selected model** and **query the actual Logstores**. Reading model definitions or resolving storage locations does not grant access to the logs.

## Permissions by operation

| Skill command | RAM actions | Authorization scope |
| --- | --- | --- |
| `context-model list` | `log:ListContextModels` | Context Models in the account; optional when the model name is already known |
| `context-model catalog overview/get/search/resolve` | `log:QueryContextModel` | The specified Context Model |
| `source-model status` | `log:GetSourceModelStatus` | The selected Project |
| `source-model catalog overview/get/search` | `log:QuerySourceModel` | The selected Project |
| `source-model readiness` | `log:GetSourceModelStatus`, `log:QuerySourceModel` | The selected Project; checks generation status and the target Logstore's model node |
| `query` | `log:GetLogStoreLogs` | Each Logstore queried |
| `index get` | `log:GetIndex` | Each Logstore whose index is inspected |

Source Model permissions are scoped to a **Project**; Context Model permissions are scoped to a **model name**. These resource types follow the official [model permission policy](https://www.alibabacloud.com/help/en/sls/configure-sls-dataagent-permissions).

Use the RAM action names in this table when authorizing. The API `ListContextModel` maps to the plural action `log:ListContextModels`; `GetLogsV2` maps to `log:GetLogStoreLogs`. See [GetLogsV2 authorization](https://help.aliyun.com/en/sls/developer-reference/api-sls-2020-12-30-getlogsv2) and the [SLS RAM action/resource reference](https://help.aliyun.com/en/sls/developer-reference/api-sls-2020-12-30-ram).

## Custom policy example

This complete example supports both model workflows and one Logstore. Replace:

- `<account-id>` with the resource owner's Alibaba Cloud account ID, not a RAM user ID.
- `<model-name>` with the Context Model name/UUID used by `--name`, not a Schema name or source tag.
- `<source-project>` with the Project passed to `source-model --project`.
- `<log-region>`, `<log-project>` and `<logstore>` with the physical query location. For Context Models, use the location returned by `catalog resolve`; it may differ from the semantic source tag.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:ListContextModels"],
      "Resource": "acs:log:*:<account-id>:contextmodel/*"
    },
    {
      "Effect": "Allow",
      "Action": ["log:QueryContextModel"],
      "Resource": "acs:log:*:<account-id>:contextmodel/<model-name>"
    },
    {
      "Effect": "Allow",
      "Action": ["log:GetSourceModelStatus", "log:QuerySourceModel"],
      "Resource": "acs:log:*:<account-id>:project/<source-project>"
    },
    {
      "Effect": "Allow",
      "Action": ["log:GetLogStoreLogs", "log:GetIndex"],
      "Resource": "acs:log:<log-region>:<account-id>:project/<log-project>/logstore/<logstore>"
    }
  ]
}
```

Keep only the statements needed by the workflow:

- **Context Model only:** keep the Context Model and Logstore statements; remove the Source Model statement. Remove the listing statement too if `context-model list` will not be used.
- **Source Model only:** keep the Source Model and Logstore statements; remove both Context Model statements.
- **Both model types:** keep both model-read scopes and the required Logstores. For multiple resources, use explicit ARN arrays in the corresponding statements.

`log:GetIndex` is needed only for index inspection. Include every Logstore actually queried, including sources used by a JOIN. Source Model authorization covers model definitions in the selected Project; `--sources` narrows a catalog request but is not a Logstore-level RAM boundary.

This policy covers the skill's direct read APIs. Model generation, DataAgent/session management and role passing are separate operations; the skill does not call them or require their write actions or `ram:PassRole`.

## Check an access failure

Check the failing operation with the **same SDK identity and endpoint** used by the skill:

- Model reads fail: check the relevant Context Model or Source Model action and resource ARN above.
- Model reads succeed but `query` or `index get` fails: check permissions on the resolved physical Logstore, rather than its model or source tag.
- Credentials are invalid or expired: correct the credential configuration or refresh the session token.
- The service is not enabled, the endpoint is unsupported, or the resource is missing: verify service availability and coordinates. Adding RAM actions does not resolve these failures.

Policy examples are based on the official documentation. The functional tests use an existing test-account profile; they do not validate this reduced policy under a newly restricted RAM identity.
