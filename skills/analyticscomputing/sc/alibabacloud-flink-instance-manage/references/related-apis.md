# Related APIs and Command Mapping

Alibaba Cloud Flink (Real-Time Compute) API version `2021-10-28`.

## Mandatory execution rule

Use this document for mapping/reference only.  
During task execution, always run operations through:

```bash
python scripts/instance_ops.py <command> ...
```

Do not execute raw product commands such as `aliyun foasconsole ...`.

## Command to API Mapping

| Script Command | API Action | Notes |
|---|---|---|
| `describe_regions` | `DescribeSupportedRegions` | List supported regions |
| `describe_zones` | `DescribeSupportedZones` | List zones in a region |
| `create` | `CreateInstance` | Create a Flink instance |
| `describe` | `DescribeInstances` | List/query instances |
| `create_namespace` | `CreateNamespace` | Create namespace |
| `describe_namespaces` | `DescribeNamespaces` | Query namespaces |
| `list_tags` | `ListTagResources` | Query tags |
| `get_flink_ai_service` | `GetFlinkAiService` | Query AI service status and closure protection in the specified region |
| `get_flink_ai_service_free_quota` | `GetFlinkAiServiceFreeQuota` | Query free quota and usage in the specified region |
| `open_flink_ai_service` | `OpenFlinkAiService` | Activate AI service in the specified region |
| `close_flink_ai_service` | `CloseFlinkAiService` | Deactivate AI service in the specified region |
| `modify_ai_service_protection` | `ModifyAiServiceProtection` | Set closure protection in the specified region |

## Notes

- Product code is still `foasconsole`, but this remains an internal implementation detail.
- Use `--confirm` for instance or namespace creation, AI service activation or deactivation, and closure protection changes.
- The AI service commands use `alibabacloud_foasconsole20211028.models` and `alibabacloud_foasconsole20211028.client.Client`. See the command parameters and verification examples in the [Flink AI Service guide](flink-ai-service.md).
- For executable examples, follow `SKILL.md` and `core-execution-flow.md`.
