# Alert history

| Source | Project / Store | Evidence |
| --- | --- | --- |
| Project execution history | Rule's owning Project / `internal-alert-history` | Individual executions, including non-firing evaluations; condition/query results and execution errors |
| Global alert center history | `sls-alert-<primary-account-id>-<center-region>` / `internal-alert-center-log` | Alerts across all Projects and regions in the account: evaluation, receipt, routing, silence and notification |

Both are managed by alerting and independent of `logging get`.
The [managed Store safety rules](entry.md#safety-rules-for-managed-built-in-stores) apply.
Their initial provisioning requires the console, not manual Store creation.

## Project execution history

Filter by `AlertName` (stable rule ID); add `AlertID` for one execution:

```text
AlertName: "example-alert"
```

`Status: Success` means execution succeeded, not necessarily firing. Inspect
`Fired`, `AlertStatus`, `Condition` and `Results`; see
[execution fields](alert-execution-fields.md).

History is enabled on the first console visit to a rule's detail page:

```text
https://sls.console.aliyun.com/lognext/project/<projectName>/alert/<AlertName>
```

URL-encode the owning Project and stable rule ID. Older deployments may have
different activation timing and retention; do not assume a fixed history window.

## Global alert center history

The global center covers alerts from **all Projects and all regions under the
current Alibaba Cloud account**, not only those in the center's region. The
center region is the history storage location; caller permissions still govern
access to the history. Using the same profile,
obtain the primary account ID with
`aliyun sts GetCallerIdentity --cli-query AccountId`; this also works for RAM
users and assumed roles. Combine it with the center region using the Project
name above.

Resolve the center Project's actual region with a cross-region lookup:

```bash
aliyun sls project get --project CENTER_PROJECT \
  --cross-region true --region cn-zhangjiakou \
  --endpoint cn-zhangjiakou.log.aliyuncs.com --format json
```

Use the same profile and the returned `region` for history queries;
`cn-zhangjiakou` is only the discovery endpoint.

On first console use of alerting, the user selects a center region; SLS creates
the center Project and indexed Store automatically. See
[center setup](https://help.aliyun.com/zh/sls/alert-center-dashboards).

Filter by `alert.project` (owning Project), `alert.alert_id` (rule ID) and
`__topic__` (stage). Unlike Project history, `alert.alert_id` identifies the rule,
not one execution.

| `__topic__` | Evidence |
| --- | --- |
| `alert_state` | Rule evaluation; inspect state and condition to determine firing |
| `alert_received` | Alert management received the alert |
| `alert_routed` | Routing and merging |
| `alert_pre_filter`, `alert_silenced` | Entry into filtering, or suppression/silence |
| `alert_pre_notify`, `alert_notified` | Notification processing/send records; inspect outcome and errors |
| `system_config` | Configuration errors |

```text
__topic__: alert_state and alert.project: "example-project" and alert.alert_id: "example-alert"
```

Do not count lifecycle stages as separate triggers or receipt as delivery.
For analysis examples, see the [official guide](https://help.aliyun.com/zh/sls/use-custom-query-statements-to-analyze-alert-logs);
for cause investigation, see [event diagnosis](../alerting/diagnosis/diagnose.md).
