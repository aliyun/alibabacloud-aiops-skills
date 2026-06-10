# RAM Policies — PAI Quota

## Read-only policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:GetQuota",
        "pai:ListQuotas",
        "pai:ListQuotaWorkloads",
        "pai:ListQuotaActiveUserUsages",
        "pai:GetResourceGroup",
        "pai:ListResourceGroups"
      ],
      "Resource": ["acs:pai:*:*:quota/*", "acs:pai:*:*:resourcegroup/*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "aiworkspace:GetWorkspace",
        "aiworkspace:ListWorkspaces",
        "aiworkspace:ListResources"
      ],
      "Resource": ["acs:aiworkspace:*:*:workspace/*"]
    }
  ]
}
```

## Full policy (read + write + workspace binding + VPC dependencies)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:GetQuota",
        "pai:ListQuotas",
        "pai:CreateQuota",
        "pai:UpdateQuota",
        "pai:ScaleQuota",
        "pai:DeleteQuota",
        "pai:ListQuotaWorkloads",
        "pai:ListQuotaActiveUserUsages",
        "pai:GetResourceGroup",
        "pai:ListResourceGroups",
        "pai:UpdateResourceGroup"
      ],
      "Resource": ["acs:pai:*:*:quota/*", "acs:pai:*:*:resourcegroup/*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "aiworkspace:GetWorkspace",
        "aiworkspace:ListWorkspaces",
        "aiworkspace:ListResources",
        "aiworkspace:CreateWorkspaceResource",
        "aiworkspace:UpdateWorkspaceResource",
        "aiworkspace:DeleteWorkspaceResource"
      ],
      "Resource": ["acs:aiworkspace:*:*:workspace/*"]
    },
    {
      "Effect": "Allow",
      "Action": ["vpc:DescribeVpcs", "vpc:DescribeVSwitches", "ecs:DescribeSecurityGroups"],
      "Resource": "*"
    }
  ]
}
```

## Per-API permission map

| API / CLI command | Action | Notes |
| --- | --- | --- |
| `list-quotas` | `pai:ListQuotas` | |
| `get-quota` | `pai:GetQuota` | |
| `create-quota` | `pai:CreateQuota` | + `pai:UpdateResourceGroup` if `--resource-group-ids` adjusts RG binding. + VPC describe perms if `--quota-config.UserVpc` supplied. |
| `update-quota` | `pai:UpdateQuota` | + VPC describe perms if `--quota-config.UserVpc` supplied. |
| `scale-quota` | `pai:ScaleQuota` | |
| `delete-quota` | `pai:DeleteQuota` | |
| `list-quota-workloads` | `pai:ListQuotaWorkloads` | |
| `list-quota-active-user-usages` | `pai:ListQuotaActiveUserUsages` | |
| `aiworkspace list-workspaces` | `aiworkspace:ListWorkspaces` | |
| `aiworkspace get-workspace` | `aiworkspace:GetWorkspace` | |
| `aiworkspace list-resources` | `aiworkspace:ListResources` | |
| `aiworkspace create-workspace-resource` | `aiworkspace:CreateWorkspaceResource` | |
| `aiworkspace update-workspace-resource` | `aiworkspace:UpdateWorkspaceResource` | |
| `aiworkspace delete-workspace-resource` | `aiworkspace:DeleteWorkspaceResource` | |

## Scoping examples

Restrict to specific Quotas and a single workspace:

```json
"Resource": [
  "acs:pai:cn-shanghai:123456789:quota/quota-aaa",
  "acs:pai:cn-shanghai:123456789:quota/quota-bbb",
  "acs:aiworkspace:cn-shanghai:123456789:workspace/ws-xxx"
]
```

## Permission Failure Handling

On `Forbidden.RAM` / `NoPermission`:

1. STOP immediately. Do NOT retry.
2. Print the failing `Action`, `Resource`, and request ID.
3. Direct the user to attach the missing action from the per-API map above.
4. Do NOT broaden the policy with wildcards (no `pai:*`, no `aiworkspace:*`).

## Source references

- https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy
- Public PAI OpenAPI portal: https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview
- Public AIWorkSpace OpenAPI portal: https://next.api.aliyun.com/document/AIWorkSpace/2021-02-04/overview
