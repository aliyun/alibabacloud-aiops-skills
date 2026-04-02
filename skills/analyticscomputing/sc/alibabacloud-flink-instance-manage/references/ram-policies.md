# RAM Policies for Flink Instance Operations

Alibaba Cloud RAM (Resource Access Management) permissions required by
`scripts/instance_ops.py`.

> Note: For OpenAPI 2021-10-28, official action names use the `stream:*`
> namespace.

---

## Required Permissions

The following actions cover all implemented commands in this skill:

- `stream:CreateVvpInstance` - `create`
- `stream:DescribeVvpInstances` - `describe`
- `stream:ModifyVvpInstanceSpec` - `modify_spec`
- `stream:DeleteVvpInstance` - `delete`
- `stream:RenewVvpInstance` - `renew`
- `stream:ConvertVvpInstance` - `convert` and `convert_prepay_instance`
- `stream:CreateVvpNamespace` - `create_namespace`
- `stream:DescribeVvpNamespaces` - `describe_namespaces`
- `stream:ModifyVvpNamespaceSpec` - `modify_namespace_spec`
- `stream:DeleteVvpNamespace` - `delete_namespace`
- `stream:TagVvpResources` - `tag_resources`
- `stream:QueryTagVvpResources` - `list_tags`
- `stream:UnTagVvpResources` - `untag_resources`

`DescribeSupportedRegions` and `DescribeSupportedZones` pages currently state
"暂无授权信息透出", so they are intentionally not listed as mandatory actions.

---

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
        "stream:ModifyVvpInstanceSpec",
        "stream:DeleteVvpInstance",
        "stream:RenewVvpInstance",
        "stream:ConvertVvpInstance",
        "stream:CreateVvpNamespace",
        "stream:DescribeVvpNamespaces",
        "stream:ModifyVvpNamespaceSpec",
        "stream:DeleteVvpNamespace",
        "stream:TagVvpResources",
        "stream:QueryTagVvpResources",
        "stream:UnTagVvpResources"
      ],
      "Resource": [
        "acs:stream:*:*:vvpinstance/*",
        "acs:stream:*:*:vvpinstance/*/vvpnamespace/*"
      ]
    }
  ]
}
```

---

## Permission Breakdown by Operation

| API Action | RAM Action |
|------------|------------|
| `CreateInstance` | `stream:CreateVvpInstance` |
| `DescribeInstances` | `stream:DescribeVvpInstances` |
| `ModifyInstanceSpec` | `stream:ModifyVvpInstanceSpec` |
| `DeleteInstance` | `stream:DeleteVvpInstance` |
| `RenewInstance` | `stream:RenewVvpInstance` |
| `ConvertInstance` | `stream:ConvertVvpInstance` |
| `ConvertPrepayInstance` | `stream:ConvertVvpInstance` |
| `CreateNamespace` | `stream:CreateVvpNamespace` |
| `DescribeNamespaces` | `stream:DescribeVvpNamespaces` |
| `ModifyNamespaceSpecV2` | `stream:ModifyVvpNamespaceSpec` |
| `DeleteNamespace` | `stream:DeleteVvpNamespace` |
| `TagResources` | `stream:TagVvpResources` |
| `ListTagResources` | `stream:QueryTagVvpResources` |
| `UntagResources` | `stream:UnTagVvpResources` |

---

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
        "stream:ModifyVvpInstanceSpec",
        "stream:RenewVvpInstance"
      ],
      "Resource": "acs:stream:cn-hangzhou:123456789012:vvpinstance/f-cn-xxx"
    }
  ]
}
```

---

## Predefined System Policies

Alibaba Cloud currently provides these common system policies:

- `AliyunStreamFullAccess`
- `AliyunStreamReadOnlyAccess`

If your organization requires least privilege, prefer custom policy with
explicit `stream:*` actions shown above.

---

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
2. Rotate/recreate AccessKey and update local config.

---

## References

- [OpenAPI RAM actions](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-ram)
- [OpenAPI overview](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-overview)
- [RAM Console](https://ram.console.aliyun.com/)
