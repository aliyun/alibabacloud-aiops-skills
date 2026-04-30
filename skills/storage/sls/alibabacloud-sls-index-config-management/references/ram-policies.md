# RAM Policies - SLS Index Configuration Manager

## Required Permissions

| CLI Command    | API Action        |
| -------------- | ----------------- |
| `get-index`    | `log:GetIndex`    |
| `create-index` | `log:CreateIndex` |
| `update-index` | `log:UpdateIndex` |
| `delete-index` | `log:DeleteIndex` |

Resource: `acs:log:{regionId}:{accountId}:project/{ProjectName}/logstore/{LogstoreName}`

ARN placeholders: `{regionId}` (e.g. `cn-hangzhou`, or `*`), `{accountId}` (UID or `*`), `{ProjectName}` (or `*`), `{LogstoreName}` (or `*`).

## Minimum RAM Policy (read-only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["log:GetIndex"],
      "Resource": "acs:log:*:*:project/<project-name>/logstore/<logstore-name>"
    }
  ]
}
```

## Complete RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "log:GetIndex",
        "log:CreateIndex",
        "log:UpdateIndex",
        "log:DeleteIndex"
      ],
      "Resource": "acs:log:*:*:project/<project-name>/logstore/<logstore-name>"
    }
  ]
}
```

Use `logstore/*` to match all Logstores under a project, or `project/*` to match all projects.

Grant only the actions needed: start with `GetIndex` for inspection, add write actions when needed, add `DeleteIndex` only when the user explicitly requests deletion.
