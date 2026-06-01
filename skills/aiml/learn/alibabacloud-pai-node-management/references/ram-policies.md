# RAM Policies — PAI Node

## Minimum policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "pai:ListNodes",
        "pai:GetResourceGroup",
        "pai:ListResourceGroups",
        "pai:ListQuotas",
        "pai:GetQuota",
        "pai:UpdateResourceGroup",
        "pai:UpdateQuota"
      ],
      "Resource": ["acs:pai:*:*:resourcegroup/*", "acs:pai:*:*:quota/*", "acs:pai:*:*:node/*"]
    }
  ]
}
```

> Note: `pai:GetNode` is not yet available in the public CLI. Use `list-nodes --node-names` to inspect a single node.
>
> `get-node-gpu-metrics` and `list-node-pods` are NOT available in the public CLI — do NOT grant or attempt to invoke `pai:GetNodeGPUMetrics` / `pai:ListNodePods`.
>
> `pai:UpdateResourceGroup` and `pai:UpdateQuota` are required for node operations (cordon/uncordon/drain). The backend accepts **either** permission (logical OR).

## Per-API permission map

| API / CLI command | RAM Action checked | Resource ARN |
| --- | --- | --- |
| `list-nodes` (by RG) | `pai:GetResourceGroup` | `acs:pai:{region}:{tenant}:resourcegroup/{rgId}` (per RG) |
| `list-nodes` (by Quota) | `pai:GetQuota` | `acs:pai:{region}:{tenant}:quota/{quotaId}` |
| ~~`get-node-gpu-metrics`~~ | — | **🚫 Not available** in the public CLI. Do NOT invoke. |
| ~~`list-node-pods`~~ | — | **🚫 Not available** in the public CLI. Do NOT invoke. |
| `operate-node` | `pai:UpdateResourceGroup` **OR** `pai:UpdateQuota` | RG: `acs:pai:{region}:{tenant}:resourcegroup/{rgId}` / Quota: `acs:pai:{region}:{tenant}:quota/{rootQuotaId}` |
| `list-resource-groups` | `pai:ListResourceGroups` | Used for name → ID resolution |
| `list-quotas` | `pai:ListQuotas` | Used for quota name → RG IDs resolution |
| `get-resource-group` | `pai:GetResourceGroup` | |
| `get-quota` | `pai:GetQuota` | Used to read ResourceGroupIds from a Quota |

## Scoping examples

Restrict to specific ResourceGroups only:

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
4. Do NOT broaden the policy with wildcards (no `pai:*`, no `pai:*Node*` in user-managed policies).

## Source references

- https://help.aliyun.com/zh/pai/user-guide/configure-custom-ram-authorization-policy
- Public PAI OpenAPI portal: https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview
