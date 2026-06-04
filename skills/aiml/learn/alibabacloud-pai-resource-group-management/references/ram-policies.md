# RAM Policies — PAI ResourceGroup

## Read-only policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:GetResourceGroup",
        "pai:ListResourceGroups",
        "pai:ListResourceGroupMachineGroups"
      ],
      "Resource": ["acs:pai:*:*:resourcegroup/*"]
    }
  ]
}
```

## Full policy (read + write + VPC dependencies)

> Note: `pai:DeleteResourceGroupMachineGroup` and `pai:DeleteMachineGroup` are intentionally **omitted** — this skill refuses MachineGroup deletion / release (see `not-implementable.md` and `SKILL.md` Section 7). Do not grant these actions for skill execution; if a user has them attached for other reasons, the skill will still refuse to invoke the corresponding CLI commands.
>
> Note: `pai:GetResourceGroupMachineGroup` and `pai:GetMachineGroup` are **not required** — this skill uses `list-resource-group-machine-groups --machine-group-ids` instead of `get-resource-group-machine-group` / `get-machine-group`.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:GetResourceGroup",
        "pai:ListResourceGroups",
        "pai:CreateResourceGroup",
        "pai:UpdateResourceGroup",
        "pai:DeleteResourceGroup",
        "pai:ListResourceGroupMachineGroups"
      ],
      "Resource": ["acs:pai:*:*:resourcegroup/*"]
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
| `list-resource-groups` | `pai:ListResourceGroups` | |
| `get-resource-group` | `pai:GetResourceGroup` | |
| `create-resource-group` | `pai:CreateResourceGroup` | + VPC describe perms if `--user-vpc` is supplied. |
| `update-resource-group` | `pai:UpdateResourceGroup` | + VPC describe perms if updating UserVpc. |
| `delete-resource-group` | `pai:DeleteResourceGroup` | |
| `list-resource-group-machine-groups` | `pai:ListResourceGroupMachineGroups` | Use `--machine-group-ids` for specific MG lookup. |
| ~~`get-resource-group-machine-group` / `get-machine-group`~~ | ~~`pai:GetResourceGroupMachineGroup` / `pai:GetMachineGroup`~~ | **Not used by this skill** — use `list-resource-group-machine-groups --machine-group-ids` instead. |
| ~~`delete-resource-group-machine-group` / `delete-machine-group`~~ | ~~`pai:DeleteResourceGroupMachineGroup` / `pai:DeleteMachineGroup`~~ | **🚫 Forbidden by this skill** — do NOT grant; do NOT invoke. See `not-implementable.md`. |
| ~~`get-resource-group-total`~~ | ~~`pai:GetResourceGroupTotal`~~ | **⚠️ Deprecated** — do NOT use. |
| ~~`get-resource-group-request`~~ | ~~`pai:GetResourceGroupRequest`~~ | **⚠️ Deprecated** — do NOT use. |
| ~~`get-user-view-metrics`~~ | ~~`pai:GetUserViewMetrics`~~ | **⚠️ Deprecated** — do NOT use. |
| ~~`get-node-metrics`~~ | ~~`pai:GetNodeMetrics`~~ | **⚠️ Deprecated** — do NOT use. |

## Scoping examples

Restrict the user to specific ResourceGroups only:

```json
"Resource": [
  "acs:pai:cn-shanghai:123456789:resourcegroup/rg-aaa",
  "acs:pai:cn-shanghai:123456789:resourcegroup/rg-bbb"
]
```

## Permission Failure Handling

On `Forbidden.RAM` / `NoPermission`:

1. STOP immediately. Do NOT retry.
2. Print the failing `Action`, `Resource`, and request ID.
3. Direct the user to attach the missing action from the per-API map above.
4. Do NOT broaden the policy with wildcards (no `pai:*`, no `pai:*ResourceGroup*` in user-managed policies).

## Source references

- https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy
- Yuque (auth required): https://aliyuque.antfin.com/pai/api-doc/bic3z5
