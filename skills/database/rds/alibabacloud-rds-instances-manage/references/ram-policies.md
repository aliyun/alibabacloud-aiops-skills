# RAM Policies - RDS Instances Manage

Grant read-only permissions by default. Add mutating permissions only for operations the user actually needs.

## Read-only policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:DescribeDBInstances",
        "rds:DescribeDBInstanceAttribute",
        "rds:DescribeRegions",
        "rds:DescribeAvailableZones",
        "rds:DescribeAvailableClasses",
        "rds:DescribePrice",
        "rds:DescribeDBInstancePerformance",
        "rds:DescribeSlowLogRecords",
        "rds:DescribeErrorLogs",
        "rds:DescribeParameters",
        "rds:DescribeDatabases",
        "rds:DescribeAccounts",
        "rds:DescribeDBInstanceNetInfo",
        "rds:DescribeDBInstanceIPArrayList",
        "rds:DescribeAllWhitelistTemplate",
        "rds:DescribeInstanceLinkedWhitelistTemplate",
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "bssapi:DescribeInstanceBill",
        "hdm:GetPfsMetricTrends",
        "hdm:GetPfsSqlSummaries"
      ],
      "Resource": "*"
    }
  ]
}
```

Billing and DAS permissions can expose sensitive financial or SQL-workload metadata. Remove `bssapi:DescribeInstanceBill` and the `hdm:*` actions when those capabilities are not required.

## Mutating policy

Add only the actions needed by the approved operating scope:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rds:CreateDBInstance",
        "rds:ModifyParameter",
        "rds:ModifyDBInstanceSpec",
        "rds:ModifyDBInstanceDescription",
        "rds:CreateAccount",
        "rds:ModifySecurityIps",
        "rds:AllocateInstancePublicConnection",
        "rds:AttachWhitelistTemplateToInstance",
        "rds:TagResources",
        "rds:RestartDBInstance",
        "rds:DeleteDBInstance"
      ],
      "Resource": "*"
    }
  ]
}
```

RAM authorization does not replace the skill's explicit confirmation gate. Even a profile with these permissions must not execute a mutation until the user confirms the exact target and parameters.

## Least-privilege guidance

1. Use a dedicated RAM user or role instead of a root-account AccessKey.
2. Separate read-only and mutating profiles when practical.
3. Restrict resources with supported RDS RAM resource ARNs and conditions when the account's governance model permits it.
4. Grant billing permissions only to users who are allowed to see financial data.
5. Grant DAS permissions only to users who are allowed to see SQL and workload metadata.
6. Rotate long-lived AccessKeys and prefer temporary credentials or role-based credentials for automation.
7. Configure credentials with `aliyun configure`; do not commit or export secrets as the normal workflow.

## Permission error handling

When an API returns `Forbidden`, `NoPermission`, or an equivalent authorization error:

- Report the exact missing Action when the response identifies it.
- Do not recommend broad administrator access.
- Propose the smallest policy addition required for the requested capability.
- Do not retry a mutating call automatically after permissions are changed; re-run current-state checks and request mutation confirmation again.
