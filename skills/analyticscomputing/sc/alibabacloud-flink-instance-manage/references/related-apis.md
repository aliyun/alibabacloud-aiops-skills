# Related APIs and Command Mapping

Alibaba Cloud Flink (Real-Time Compute) API version `2021-10-28`.

## Mandatory execution rule

Use this document for **mapping/reference only**.  
During task execution, always run operations through:

```bash
python scripts/instance_ops.py <command> ...
```

Do **not** execute raw product commands such as `aliyun foasconsole ...`.

---

## Command to API mapping

| Script Command | API Action | Notes |
|---|---|---|
| `describe_regions` | `DescribeSupportedRegions` | List supported regions |
| `describe_zones` | `DescribeSupportedZones` | List zones in a region |
| `create` | `CreateInstance` | Create a Flink instance |
| `describe` | `DescribeInstances` | List/query instances |
| `modify_spec` | `ModifyInstanceSpec` | Change instance spec |
| `delete` | `DeleteInstance` | Delete instance |
| `renew` | `RenewInstance` | Renew subscription instance |
| `convert` | `ConvertInstance` / `ConvertPrepayInstance` | Convert billing mode |
| `create_namespace` | `CreateNamespace` | Create namespace |
| `describe_namespaces` | `DescribeNamespaces` | Query namespaces |
| `modify_namespace_spec` | `ModifyNamespaceSpecV2` | Modify namespace spec |
| `delete_namespace` | `DeleteNamespace` | Delete namespace |
| `tag_resources` | `TagResources` | Add tags |
| `list_tags` | `ListTagResources` | List tags |
| `untag_resources` | `UntagResources` | Remove tags |

---

## Notes

- Product code is still `foasconsole`, but this should stay an internal implementation detail.
- All confirmation checks and guardrails are enforced by `scripts/instance_ops.py`.
- For executable examples, follow the execution protocol in `SKILL.md` and run `scripts/instance_ops.py`.
