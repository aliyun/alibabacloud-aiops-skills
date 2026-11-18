# RAM Policies for Flink Instance Operations

Alibaba Cloud RAM permissions for Flink instance, namespace, and Flink AI Service operations in `scripts/instance_ops.py`.

> For OpenAPI 2021-10-28, official action names use the `stream:` prefix.

## Required Permissions

The following actions cover allowed commands in this skill:

- `stream:CreateVvpInstance` - `create`
- `stream:DescribeVvpInstances` - `describe`
- `stream:CreateVvpNamespace` - `create_namespace`
- `stream:DescribeVvpNamespaces` - `describe_namespaces`
- `stream:QueryTagVvpResources` - `list_tags`

The documentation for `DescribeSupportedRegions` and `DescribeSupportedZones`
currently lists no published RAM authorization information.

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

## Flink AI Service

Grant the RAM permissions for the operations the identity needs.

| API | RAM Action | Resource |
|---|---|---|
| `GetFlinkAiService` | `stream:GetFlinkAiService` | `*` |
| `GetFlinkAiServiceFreeQuota` | `stream:GetFlinkAiServiceFreeQuota` | `*` |
| `OpenFlinkAiService` | `stream:OpenFlinkAiService` | `*` |
| `CloseFlinkAiService` | `stream:CloseFlinkAiService` | `*` |
| `ModifyAiServiceProtection` | `stream:ModifyAiServiceProtection` | `*` |

The official references cover activation, status and quota queries, deactivation, and closure protection changes. [Flink RAM permissions](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-ram) · [Resource group permissions](https://www.alibabacloud.com/help/zh/flink/realtime-flink/security-and-compliance/fine-grained-resource-control-using-resource-groups-33) · [ModifyAiServiceProtection API](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-modifyaiserviceprotection)

The Alibaba Cloud account can activate the service in the console. For console activation, a RAM identity needs `AliyunBSSOrderAccess` and `AliyunStreamFullAccess`. [Console activation requirements](https://help.aliyun.com/zh/flink/realtime-flink/flink-ai-service)

For an API permission error, give the administrator the API operation, region, error code, and `request_id` to verify the required authorization.

## Predefined System Policies

Alibaba Cloud currently provides these common system policies:

- `AliyunStreamFullAccess`
- `AliyunStreamReadOnlyAccess`

For least privilege, prefer a custom policy that explicitly enumerates the
`stream:` actions listed above.

## Troubleshooting

### Error: `Forbidden.RAM`

Use `ram-permission-diagnose` or ask the user's RAM administrator to verify the policy for the calling identity. Provide the failed operation, region, error code, and request ID when available. Wait for the user to confirm that the necessary permissions are available before retrying. For Flink AI service writes, follow the [AI service write authorization procedure](../SKILL.md#ai-service-write-authorization).

### Error: `InvalidAccessKeyId.NotFound`

Ask the user or their administrator to verify whether the configured identity is still valid and update the local profile if needed. Use the configured credential provider and keep access keys and tokens out of diagnostic messages.

## References

- [OpenAPI RAM actions](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-ram)
- [OpenAPI overview](https://help.aliyun.com/zh/flink/realtime-flink/developer-reference/api-foasconsole-2021-10-28-overview)
- [RAM Console](https://ram.console.aliyun.com/)
