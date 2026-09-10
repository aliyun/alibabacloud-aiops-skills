# Alert center history

Query `internal-alert-center-log` in `sls-alert-<account-id>-<region>` for rule
evaluations and triggered alerts. The region is selected during initial
console setup and can differ from the rule's region.

## Locate the center

Use `aliyun sts GetCallerIdentity --cli-query AccountId` with the same profile
to obtain the primary account ID. [`AccountId`](https://help.aliyun.com/document_detail/43767.html)
also identifies the primary account for RAM users and assumed roles.
Combine it with the center's region to form the Project name above.

If the region is unknown, find accessible Projects using
`list-project --project-name "sls-alert-<account-id>-"` and resolve their actual
regions through [region configuration](../../regions.md). A regional listing
alone does not establish whether a center exists in another region.

## Event types and filters

Filter by `alert.project` (owning Project), `alert.alert_id` (rule), and
`__topic__` (stage). These differ from Project execution-history fields.

| Topic | Evidence |
| --- | --- |
| `alert_state` | Rule evaluation |
| `alert_received` | Management received the alert |

For example, select rule evaluations with:

```text
__topic__: alert_state and alert.project: "example-project" and alert.alert_id: "example-alert"
```

Inspect the recorded status and condition to determine whether an evaluation
fired. For query examples, see the
[official alert-log analysis guide](https://help.aliyun.com/zh/sls/use-custom-query-statements-to-analyze-alert-logs).

## First-time center setup

On first use of SLS alerting in the **SLS console**, the user selects a region.
SLS automatically creates the center Project and `internal-alert-center-log`,
which is **free to use** and indexed by default. The CLI cannot perform this setup.
