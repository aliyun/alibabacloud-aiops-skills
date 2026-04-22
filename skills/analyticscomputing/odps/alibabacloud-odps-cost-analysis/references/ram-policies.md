# RAM Policies

Required RAM (Resource Access Management) permissions for MaxCompute Cost Analysis operations.

## Required Permissions

This Skill execution requires the following RAM permissions in `{Product}:{Action}` format:

- `odps:ListInstances` — List instances for cost analysis
- `odps:SumBills` — Summarize billing data
- `odps:SumBillsByDate` — Daily billing trends
- `odps:SumDailyBillsByItem` — Daily billing details
- `odps:SumStorageMetricsByType` — Storage metrics by type
- `odps:SumStorageMetricsByDate` — Storage metrics by date
- `odps:ListComputeMetricsByInstance` — Compute metrics by instance
- `odps:ListComputeMetricsBySignature` — Compute metrics by SQL signature
- `odps:SumComputeMetricsByUsage` — Compute usage trends
- `odps:SumComputeMetricsByRecord` — Compute record counts

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| MaxCompute | `odps:ListInstances` | `*` | List instances for cost analysis |
| MaxCompute | `odps:SumBills` | `*` | Summarize billing data |
| MaxCompute | `odps:SumBillsByDate` | `*` | Daily billing trends |
| MaxCompute | `odps:SumDailyBillsByItem` | `*` | Daily billing details |
| MaxCompute | `odps:SumStorageMetricsByType` | `*` | Storage metrics by type |
| MaxCompute | `odps:SumStorageMetricsByDate` | `*` | Storage metrics by date |
| MaxCompute | `odps:ListComputeMetricsByInstance` | `*` | Compute metrics by instance |
| MaxCompute | `odps:ListComputeMetricsBySignature` | `*` | Compute metrics by SQL signature |
| MaxCompute | `odps:SumComputeMetricsByUsage` | `*` | Compute usage trends |
| MaxCompute | `odps:SumComputeMetricsByRecord` | `*` | Compute record counts |

---

## RAM Policy Document

### Full Access Policy

Use this policy for users who need complete cost analysis capabilities:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListInstances",
        "odps:SumBills",
        "odps:SumBillsByDate",
        "odps:SumDailyBillsByItem",
        "odps:SumStorageMetricsByType",
        "odps:SumStorageMetricsByDate",
        "odps:ListComputeMetricsByInstance",
        "odps:ListComputeMetricsBySignature",
        "odps:SumComputeMetricsByUsage",
        "odps:SumComputeMetricsByRecord"
      ],
      "Resource": "*"
    }
  ]
}
```

### Billing Only Policy

For users who only need to view billing information:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListInstances",
        "odps:SumBills",
        "odps:SumBillsByDate",
        "odps:SumDailyBillsByItem"
      ],
      "Resource": "*"
    }
  ]
}
```

### Storage Analysis Only Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListInstances",
        "odps:SumStorageMetricsByType",
        "odps:SumStorageMetricsByDate"
      ],
      "Resource": "*"
    }
  ]
}
```

### Compute Analysis Only Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListInstances",
        "odps:ListComputeMetricsByInstance",
        "odps:ListComputeMetricsBySignature",
        "odps:SumComputeMetricsByUsage",
        "odps:SumComputeMetricsByRecord"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Pre-configured System Policies

| Policy Name | Description |
|-------------|-------------|
| `AliyunODPSFullAccess` | Full access to MaxCompute resources |
| `AliyunODPSReadOnlyAccess` | Read-only access to MaxCompute resources |

---

## Best Practices

1. **Least Privilege**: Grant only the minimum permissions required for the analysis task
2. **Role Separation**: Use billing-only policy for finance teams, compute-only for DevOps
3. **Audit Regularly**: Review and audit RAM policies periodically
4. **Use Roles**: For cross-account access, use RAM roles instead of long-term credentials
