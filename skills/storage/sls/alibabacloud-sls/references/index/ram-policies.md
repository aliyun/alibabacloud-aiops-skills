# RAM permissions for SLS index configuration

These permissions apply to the CLI caller. Grant the actions needed for the
requested operation and its required reads.

## Required permissions

For Logstore indexes:

| CLI command | RAM action |
| -------------- | ----------------- |
| `index get`    | `log:GetIndex`    |
| `index create` | `log:CreateIndex` |
| `index update` | `log:UpdateIndex` |
| `index delete` | `log:DeleteIndex` |

Resource: `acs:log:<region-id>:<account-id>:project/<project-name>/logstore/<logstore-name>`

ARN placeholders: `<region-id>` (e.g. `cn-hangzhou`, or `*`), `<account-id>` (UID or `*`), `<project-name>` (or `*`), `<logstore-name>` (or `*`).

## Minimum RAM policy (read-only)

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

## Complete RAM policy

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

Cross-region Project discovery additionally requires `log:GetProject` on
`acs:log:<region-id>:<account-id>:project/<project-name>`. Add it only when discovery is needed.

## StoreView inspection

`store-view get-index` requires `log:GetStoreViewIndex` with `Resource: "*"`.
The Logstore policies above do not cover this separate read operation.

## Permission errors

Authorization failures concern the caller's identity and permitted actions or resources;
they do not establish that an index is absent. See [access troubleshooting](../troubleshooting.md#environment-and-access)
and [Profile configuration](../profile-configuration.md) for relevant checks.
