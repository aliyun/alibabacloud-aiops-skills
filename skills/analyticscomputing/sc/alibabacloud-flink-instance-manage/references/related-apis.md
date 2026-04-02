# Related APIs and Command Mapping

Alibaba Cloud Flink (Real-Time Compute) API version `2021-10-28`.

## Mandatory execution rule

Use this document for mapping/reference only.  
During task execution, always run operations through:

```bash
python scripts/instance_ops.py <command> ...
```

Do not execute raw product commands such as `aliyun foasconsole ...`.

## Command to API mapping (create/query only)

| Script Command | API Action | Notes |
|---|---|---|
| `describe_regions` | `DescribeSupportedRegions` | List supported regions |
| `describe_zones` | `DescribeSupportedZones` | List zones in a region |
| `create` | `CreateInstance` | Create a Flink instance |
| `describe` | `DescribeInstances` | List/query instances |
| `create_namespace` | `CreateNamespace` | Create namespace |
| `describe_namespaces` | `DescribeNamespaces` | Query namespaces |
| `list_tags` | `ListTagResources` | Query tags |

## Notes

- Product code is still `foasconsole`, but this remains an internal implementation detail.
- Confirmation checks are required only for create commands.
- For executable examples, follow `SKILL.md` and `core-execution-flow.md`.
