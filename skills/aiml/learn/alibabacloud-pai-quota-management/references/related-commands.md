# Related Commands — PAI Quota

All commands must run through `aliyun paistudio <action>` or `aliyun aiworkspace <action>` (no SDK / curl / MCP substitutes).

## Quota CRUD (`paistudio`)

| CLI command | Description | Required parameters | Notable optional parameters |
| --- | --- | --- | --- |
| `aliyun paistudio list-quotas` | List quotas in a region | `--region` | `--quota-name`, `--resource-type ECS|Lingjun|ACS`, `--parent-quota-id`, `--quota-ids`, `--workspace-ids`, `--workspace-name`, `--statuses`, `--labels`, `--layout-mode Tree|List`, `--has-resource`, `--gpu-type`, `--cluster-type`, `--versions`, `--sort-by`, `--order`, `--page-number`, `--page-size`, `--verbose` |
| `aliyun paistudio get-quota` | Get quota detail | `--region`, `--quota-id` | `--verbose true`, `--with-node-meta true` |
| `aliyun paistudio create-quota` | Create root or child quota | `--region`, `--quota-name`, `--min` (JSON) | Root: `--resource-type`, `--resource-group-ids`. Child: `--parent-quota-id`. Common: `--allocate-strategy ByNodeSpecs|ByMachineGroupIds`, `--description`, `--labels`, `--queue-strategy`, `--quota-config` |
| `aliyun paistudio update-quota` | Update quota metadata | `--region`, `--quota-id` | `--quota-name`, `--description`, `--labels`, `--queue-strategy`, `--quota-config` |
| `aliyun paistudio scale-quota` | Reapply `Min` (absolute target) | `--region`, `--quota-id`, `--min` (JSON) | `--resource-group-ids` |
| `aliyun paistudio delete-quota` | Delete quota | `--region`, `--quota-id` | — |

## Quota usage / workloads (`paistudio`)

| CLI command | Description | Required parameters | Notes |
| --- | --- | --- | --- |
| `aliyun paistudio list-quota-workloads` | In-flight workloads consuming this quota | `--region`, `--quota-id` | `--page-size`, `--page-number`, `--workload-statuses` |
| `aliyun paistudio list-quota-active-user-usages` | Per-user active usage | `--region`, `--quota-id` | `--page-size`, `--page-number` |

## Workspace binding (`aiworkspace`)

| CLI command | Description | Required parameters | Notes |
| --- | --- | --- | --- |
| `aliyun aiworkspace list-workspaces` | List workspaces | `--region` | `--page-number`, `--page-size`, `--workspace-name`, `--status` |
| `aliyun aiworkspace get-workspace` | Get workspace detail | `--region`, `--workspace-id` | — |
| `aliyun aiworkspace list-resources` | List resources attached to a workspace | `--region`, `--workspace-id` | `--resource-type ECS|Lingjun|ACS|MaxCompute|FLINK` |
| `aliyun aiworkspace create-workspace-resource` | Attach a Quota to a workspace | `--region`, `--workspace-id`, `--option Attach`, `--resources` (JSON array) | `--resources` items: `{ProductType:"PAI", ResourceType, WorkspaceId, Quotas:[{Id}]}` |
| `aliyun aiworkspace update-workspace-resource` | Update a workspace-resource binding | `--region`, `--workspace-id`, `--resource-id` | — |
| `aliyun aiworkspace delete-workspace-resource` | Detach quota from a workspace | `--region`, `--workspace-id`, `--option Detach|DetachAndDelete`, `--resource-type`, `--resource-ids` | Detach only: `--option Detach`. Detach + delete underlying binding: `--option DetachAndDelete` (default) |

## VPC mutability cheat-sheet (`--quota-config.UserVpc`)

| Quota type | Mutable via `update-quota` | Notes |
| --- | --- | --- |
| Lingjun | `UserVpc.SwitchId` (extend only) | `VpcId`, `SecurityGroupId`, `DefaultRoute`, `ExtendedCIDRs`, `RoleArn`, `DefaultForwardInfo` immutable post-create. |
| ECS | None | VPC settings are frozen at create time. To change, delete and recreate the Quota (or change at the source ResourceGroup layer). |

## Global flags worth knowing

| Flag | Purpose |
| --- | --- |
| `--cli-dry-run` | Print the resolved request payload without sending. **MUST** be used before any destructive call (`update-quota`, `scale-quota`, `delete-quota`, `delete-workspace-resource`). |
| `--cli-read-timeout` / `--cli-connect-timeout` | Override request timeouts. |
| `--output cols=...` | Restrict tabular output to specific columns. |
| `--profile <name>` | Select a non-default Aliyun CLI profile. |
