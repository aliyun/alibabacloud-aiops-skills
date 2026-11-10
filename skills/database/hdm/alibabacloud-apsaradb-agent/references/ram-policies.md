# RAM Policy for ApsaraDB Agent

## Least-Privilege Permission

GetYaoChiAgent does not support resource-level authorization. The minimum API permission is:

| Product | RAM action | Access | Resource |
|---|---|---|---|
| DAS | `hdm:GetYaoChiAgent` | Get | `*` |

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "hdm:GetYaoChiAgent",
      "Resource": "*"
    }
  ]
}
```

Grant this policy to the RAM user or role represented by the selected aliyun CLI profile. Do not add AccessKey values to a policy, script, query, or troubleshooting message.

## Downstream Product Permissions

`hdm:GetYaoChiAgent` permits calling the Agent endpoint. Readonly requests may also need product-specific read permissions to inspect the user's resources. Grant only the read actions required for the intended product and scope them to resources where the product supports resource-level authorization.

## Optional, Separately Scoped Operation Permissions

Readonly callers do not need these actions. For an explicitly approved
operation, the existing CLI identity also needs `hdm:CreateYaoChiAgentConfirm`
on `*` and the specific product action for the target resource:

| Operation | Exact RAM action |
|---|---|
| Create a database on an existing RDS instance | `rds:CreateDatabase` |
| Edit the description of an RDS instance | `rds:ModifyDBInstanceDescription` |
| Edit the description of a PolarDB cluster | `polardb:ModifyDBClusterDescription` |
| Update a maintenance window | `rds:ModifyDBInstanceMaintainTime`, `polardb:ModifyDBClusterMaintainTime`, or `kvstore:ModifyInstanceMaintainTime` for the selected product |
| Request a PolarDB backup | `polardb:CreateBackup` |
| Enable cluster deletion protection | `polardb:ModifyDBClusterDeletion` (the helper only accepts enabling) |

Grant only the required action on the intended resource where supported.
The Skill never grants permissions. Keep deletion, purchase and broader write
permissions out of the operation role.

## Permission Failure

Follow the mandatory permission-failure workflow in [SKILL.md](../SKILL.md#ram-policy).

Report the returned action and request ID when available. Never ask the user to paste an AccessKey, secret, or STS token.

For `Forbidden.RAM` without an action, verify `hdm:GetYaoChiAgent` first, then check read permissions for the target database product.

## References

- [GetYaoChiAgent authorization](https://help.aliyun.com/zh/das/developer-reference/api-das-2020-01-16-getyaochiagent)
- [Alibaba Cloud RAM policy elements](https://help.aliyun.com/zh/ram/user-guide/policy-elements)
