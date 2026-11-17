# RAM permissions

Grant only the permissions needed by the selected workflow. `<account-id>` is the resource owner's account UID, not a RAM user ID.

## DataAgent Chat

| Entry point | API | RAM action | Resource scope |
| --- | --- | --- | --- |
| `aliyun sls list-data-agents` | [ListDataAgents](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-listdataagents) | `log:ListDataAgents` | `*` |
| `chat.py send` when creating a thread | [CreateThread](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createthread) | `log:CreateThread` | `*` |
| `aliyun sls get-thread-data` | [GetThreadData](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getthreaddata) | `log:GetThreadData` | Thread ARN |
| `chat.py send/respond/reconnect`, `aliyun sls create-chat --action stop` | [CreateChat](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createchat) | Not published separately | See conversation policy below |

Thread ARN: `acs:log:<chat-region>:<account-id>:dataagent/<agent-name>/thread/<thread-id>`. Use `*` for `<thread-id>` when access to multiple threads under the selected DataAgent is required.

For CreateChat, follow the ordinary-user policy in [Configure SLS DataAgent permissions](https://help.aliyun.com/zh/sls/configure-sls-dataagent-permissions); do not infer `log:CreateChat` from the API name. The scenario policy and individual API references use different resource scopes, so the table is not a validated complete least-privilege Chat policy.

The caller's conversation permissions and the DataAgent's bound role authorize conversation access and underlying data access separately.

## Model QA

### Model and log reads

| Entry point | API | RAM action | Resource scope |
| --- | --- | --- | --- |
| `model_qa.py context-model list` | [ListContextModels](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-listcontextmodels) | `log:ListContextModels` | `*` |
| `model_qa.py context-model catalog overview/get/resolve` | [QueryContextModel](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-querycontextmodel) | `log:QueryContextModel` | Context Model ARN |
| `model_qa.py source-model status` | [GetSourceModelStatus](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getsourcemodelstatus) | `log:GetSourceModelStatus` | Project ARN |
| `model_qa.py source-model query`, `catalog overview/get` | [QuerySourceModel](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-querysourcemodel) | `log:QuerySourceModel` | Project ARN |
| `model_qa.py query` | [GetLogsV2](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getlogsv2) | `log:GetLogStoreLogs` | Each queried Logstore ARN |
| `aliyun sls get-index` | [GetIndex](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-getindex) | `log:GetIndex` | Each inspected Logstore ARN |

Resource ARNs:

- Context Model: `acs:log:<model-region>:<account-id>:contextmodel/<model-name>`.
- Project: `acs:log:<source-region>:<account-id>:project/<source-project>`.
- Logstore: `acs:log:<log-region>:<account-id>:project/<log-project>/logstore/<logstore>`.

`<model-name>` is the Context Model name/UUID, not a Schema name or source tag. Use physical query locations and include every Logstore queried, including JOIN sources.

Reading model definitions does not grant log access. Source Model authorization is Project-scoped; `--sources` narrows the returned catalog, not the RAM authorization boundary.

### Policy example

Replace the placeholders and remove unused statements. Keep only the model type being used; omit listing when unnecessary and remove `log:GetIndex` when no index inspection is needed. Use ARN arrays for multiple models, Projects or Logstores.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:ListContextModels"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["log:QueryContextModel"],
      "Resource": "acs:log:<model-region>:<account-id>:contextmodel/<model-name>"
    },
    {
      "Effect": "Allow",
      "Action": ["log:GetSourceModelStatus", "log:QuerySourceModel"],
      "Resource": "acs:log:<source-region>:<account-id>:project/<source-project>"
    },
    {
      "Effect": "Allow",
      "Action": ["log:GetLogStoreLogs", "log:GetIndex"],
      "Resource": "acs:log:<log-region>:<account-id>:project/<log-project>/logstore/<logstore>"
    }
  ]
}
```

### Optional Source Model writes

Grant these separately, only for explicitly requested writes through the existing management/HIL flow:

| CLI | RAM action | Resource |
| --- | --- | --- |
| `aliyun sls create-source-model` | [`log:CreateSourceModel`](https://help.aliyun.com/zh/sls/developer-reference/api-sls-2020-12-30-createsourcemodel) | Project ARN above |
| `aliyun sls regenerate-source-model` | [`log:RegenerateSourceModel`](https://help.aliyun.com/zh/sls/configure-sls-dataagent-permissions) | Project ARN above |

`--logstores` limits the modeling request, not the Project-level RAM authorization scope.

## Permission errors

Use the failing operation and reported action, resource and requestId, when available, to check the actual caller identity and grants. The SDK and CLI may use different identities; see the [installation guide](cli-installation-guide.md).

- Model reads succeed but log queries fail: check the physical Logstore permissions.
- Chat data access fails: check the DataAgent's bound role.
- Distinguish invalid or expired credentials, unavailable services and missing resources from authorization failures. Do not switch identities or broaden grants to bypass an error.
