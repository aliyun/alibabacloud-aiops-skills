# Independent group evaluation

Use group evaluation when the requested outcome needs independent alerts per
host, service, or another entity. Derive the grouping fields from that outcome;
otherwise keep `groupConfiguration.type = no_group`. Define the field in
[query and statistics](queries/define-alert-queries.md) first; this setting controls how
the resulting rows are evaluated.

```json
{
  "type": "custom",
  "fields": ["host"]
}
```

Place this object in `configuration.groupConfiguration`. Every grouping field
must be present in the final query results. The same severity conditions apply
within each group; row counts are group-local. Grouping fields also become
alert labels, influencing notification grouping and identity.

SQL `GROUP BY host` aggregates query rows; it does not by itself request one
alert per host. Without alert group evaluation, qualifying query rows still
belong to one evaluation group. Also check `LIMIT` and query filtering: a host
excluded from the query results cannot be evaluated as a group.

Keep groups bounded and stable. Do not select request IDs or other rapidly
changing fields as grouping keys without discussing the resulting number of
alerts. One evaluation forwards at most 100 alert groups to the alert policy;
if more than 100 groups are produced, SLS randomly selects 100. Filter, aggregate,
or otherwise bound high-cardinality results so relevant groups are not omitted.
This feature is separate from action/alert-policy notification grouping.

See the
[rule-creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs)
for grouping semantics and the
[rule schema](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-an-alert-monitoring-rule)
for `groupConfiguration`. The hard limit is documented in the
[official group-evaluation guide](https://help.aliyun.com/zh/sls/use-the-group-evaluation-feature).
