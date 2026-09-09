# Minimal Read-Only RAM Policy

This skill performs strictly read-only billing diagnosis and cost auditing.
It requires nine RAM action strings (listed in the policy JSON below)
covering seven distinct read-only APIs. No wildcards (`*`) are used in any
action name.

## Required actions

| # | RAM Action | API Version | Endpoint | Purpose |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | Verify the caller identity and derive the account UID (`sts_token.py`) |
| 2 | `bssopenapi:DescribeInstanceBill` | 2017-12-14 | `business.aliyuncs.com` | Instance-level bills by billing cycle / product (`query_instance_bill.py`, `query_cost_trend.py`, `audit_paid_features.py`, `audit_idle_instances.py`, EOS-hint fallback of `audit_renewal_orders.py`) |
| 3 | `bssopenapi:DescribeSplitItemBill` | 2017-12-14 | `business.aliyuncs.com` | Per-billing-item / split-item drill-down (`query_instance_bill.py --split-item`, `audit_paid_features.py`) |
| 4 | `bssopenapi:QueryOrders` and `bss:QueryOrders` | 2017-12-14 | `business.aliyuncs.com` | Order history for renewal / refund anomalies (`audit_renewal_orders.py`) |
| 5 | `bssopenapi:QueryAvailableInstances` and `bss:QueryAvailableInstances` | 2017-12-14 | `business.aliyuncs.com` | Instance inventory with EndTime / RenewStatus for the expiry audit (`audit_renewal_orders.py`) |
| 6 | `cms:DescribeMetricList` | 2019-01-01 | `metrics.aliyuncs.com` | RDS load sampling for the idle audit (`audit_idle_instances.py`) |
| 7 | `cms:QueryMetricList` | 2019-01-01 | `metrics.aliyuncs.com` | Alternative metric-list action name observed during authorization; the two CMS actions are the only monitored ones granted |

All actions are read-only Describe/Get/Query-class APIs. They never modify
any resource, order, or configuration.

### Why both `bssopenapi:` and `bss:` prefixes

`QueryOrders` and `QueryAvailableInstances` are authorized under two RAM
action prefixes: the canonical OpenAPI prefix `bssopenapi:` and the legacy
expense-center prefix `bss:`. Depending on account configuration, the
authorization check for these two order/inventory actions can resolve under
either prefix, so granting only one of them can yield a false `NoPermission`
while the identical bill-query actions (rows 2-3) work. Grant both prefixes
for rows 4-5; there is no privilege escalation because both resolve to the
same read-only operations.

## Full policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyBillingQuery",
      "Effect": "Allow",
      "Action": [
        "bssopenapi:DescribeInstanceBill",
        "bssopenapi:DescribeSplitItemBill",
        "bssopenapi:QueryOrders",
        "bss:QueryOrders",
        "bssopenapi:QueryAvailableInstances",
        "bss:QueryAvailableInstances"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyCloudMonitorQuery",
      "Effect": "Allow",
      "Action": [
        "cms:DescribeMetricList",
        "cms:QueryMetricList"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are forbidden for this skill.
- `Resource: "*"` is the minimum possible scope here: STS, BSS billing and
  CloudMonitor metric reads are account-level, region-less APIs that do not
  support resource-level authorization (they cannot be narrowed to specific
  resource ARNs). Read-only effect is guaranteed by the action list itself.
- No `Deny` statements are required; anything not listed above is denied by
  default.

## Relation to `related_apis.yaml`

The declared API set of `related_apis.yaml` covers exactly the unconditional
calls of the scripts; `cms:DescribeMetricList` is deliberately absent there
(it is only called when billed RDS instances exist) while it IS granted
here: RAM authorization is action-level and must cover conditional calls as
well, so the two files differ by design, not by mistake.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | None -- STS, BSS billing and CloudMonitor metric reads are central, region-less services (`sts.aliyuncs.com`, `business.aliyuncs.com`, `metrics.aliyuncs.com`) |
| Resources | Account-level billing, order, instance-inventory and monitoring data of the account (or assumed-role target account) whose credential runs the query; no per-resource ARN granularity exists for these APIs |
| Data exposed | Bill amounts, billing items, instance IDs, product codes, subscription/renewal status, order history, CPU/connection utilization samples -- read data only |
| Mutations | None possible; only Describe/Get/Query-class actions are granted |

## How to grant

Option A -- RAM user (same-account use, recommended for daily operation):

1. RAM console -> Identities -> Users: create or select a RAM user.
2. Create a custom policy from the JSON above (Permissions -> Policies ->
   Create Policy -> Script mode).
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential
   (`aliyun configure`). The scripts resolve credentials exclusively through
   the aliyun CLI default credential chain; they never take AK/SK arguments.

Option B -- RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: create a RAM role trusted by the
   calling account.
2. Attach the policy above to the role.
3. Assume the role (`aliyun sts assume-role`) and configure the temporary
   credential as a named CLI profile; pass it to the scripts with
   `--profile <name>`.

Least-privilege checklist:

- Grant only the actions above; do not attach `AliyunBSSFullAccess`,
  `AliyunCloudMonitorFullAccess` or any administrator policy.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
