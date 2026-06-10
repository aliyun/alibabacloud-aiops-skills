# NOT Implementable via Public CLI/SDK — PAI Quota

The following Quota-related capabilities exist in the internal Yuque API spec (https://aliyuque.antfin.com/pai/api-doc/pgmtpuwcv6k9vo7q) but are **NOT exposed** through the public `aliyun paistudio` / `aliyun aiworkspace` plugins or the public PAI / AIWorkSpace OpenAPI (cross-check at https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview and https://next.api.aliyun.com/document/AIWorkSpace/2021-02-04/overview). They cannot be invoked from this skill.

| Internal API | Reason / Workaround |
| --- | --- |
| `ScaleInQuota` / `ScaleOutQuota` (incremental scale) | Not exposed publicly. Use `scale-quota` with an **absolute** target `Min` instead. |
| ECS quota `UserVpc` mutation post-create | The public `update-quota` does not accept VPC changes for `ResourceType=ECS`. Delete the quota and recreate it. |
| Lingjun quota `UserVpc.{VpcId,SecurityGroupId,DefaultRoute,ExtendedCIDRs,RoleArn,DefaultForwardInfo}` mutation | Only `UserVpc.SwitchId` is mutable (extension). All other VPC fields are immutable post-create. |
| Cross-account Quota sharing | Not exposed publicly. |
| Quota historical metrics / billing breakdown | Use the Cloud Monitoring / BSS OpenAPI; not part of `paistudio`. |
| Quota preemption queue introspection beyond `list-quota-workloads` | Console only. |

> Rule: if a capability is not in the public OpenAPI portal or in the `aliyun paistudio --help` / `aliyun aiworkspace --help` output, treat it as **not implementable** by this skill. Do NOT fall back to SDK / curl / MCP / Terraform.
