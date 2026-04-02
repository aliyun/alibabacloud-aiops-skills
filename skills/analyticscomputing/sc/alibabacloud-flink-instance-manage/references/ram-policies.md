# RAM Policies for Flink Instance Operations

Alibaba Cloud RAM permissions required by `scripts/instance_ops.py` under a
create/query-only execution model.

> Note: For OpenAPI 2021-10-28, official action names use the `stream:*`
> namespace.

## Required Permissions

The following actions cover allowed commands in this skill:

- `stream:CreateVvpInstance` - `create`
- `stream:DescribeVvpInstances` - `describe`
- `stream:CreateVvpNamespace` - `create_namespace`
- `stream:DescribeVvpNamespaces` - `describe_namespaces`
- `stream:QueryTagVvpResources` - `list_tags`

`DescribeSupportedRegions` and `DescribeSupportedZones` pages currently state
"暂无授权信息透出", so they are intentionally not listed as mandatory actions.

## Minimum Permission Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "stream:CreateVvpInstance",
        "stream:DescribeVvpInstances",
        "stream:CreateVvpNamespace",
        "stream:DescribeVvpNamespaces",
        "stream:QueryTagVvpResources"
      ],
      "Resource": [
        "acs:stream:*:*:vvpinstance/*",
        "acs:stream:*:*:vvpinstance/*/vvpnamespace/*"
      ]
    }
  ]
}
```

## Permission Breakdown by Operation

| API Action | RAM Action |
|------------|------------|
| `CreateInstance` | `stream:CreateVvpInstance` |
| `DescribeInstances` | `stream:DescribeVvpInstances` |
| `CreateNamespace` | `stream:CreateVvpNamespace` |
| `DescribeNamespaces` | `stream:DescribeVvpNamespaces` |
| `ListTagResources` | `stream:QueryTagVvpResources` |

## Resource ARN Examples

Use resource-level constraints when possible:

- Instance: `acs:stream:{regionId}:{accountId}:vvpinstance/{instanceId}`
- Namespace:
  `acs:stream:{regionId}:{accountId}:vvpinstance/{instanceId}/vvpnamespace/{namespace}`

Example policy for one specific instance:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "stream:DescribeVvpInstances",
        "stream:DescribeVvpNamespaces"
      ],
      "Resource": "acs:stream:cn-hangzhou:123456789012:vvpinstance/f-cn-xxx"
    }
  ]
}
```

## Predefined System Policies

Alibaba Cloud currently provides these common system policies:

- `AliyunStreamFullAccess`
- `AliyunStreamReadOnlyAccess`

If your organization requires least privilege, prefer custom policy with
explicit `stream:*` actions listed above.

## Troubleshooting

### Error: `Forbidden.RAM`

1. Verify attached policies:
   ```bash
   aliyun ram ListPoliciesForUser --UserName <your-username>
   ```
2. Attach a policy that includes required `stream:*` actions.
3. Retry the operation.

### Error: `InvalidAccessKeyId.NotFound`

1. Verify AccessKey:
   ```bash
   aliyun ram ListAccessKeys --UserName <your-username>
   ```
2. Rotate/recreate AccessKey and refresh local profile.

## References

- [OpenAPI RAM actions](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-ram)
- [OpenAPI overview](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-overview)
- [RAM Console](https://ram.console.aliyun.com/)
