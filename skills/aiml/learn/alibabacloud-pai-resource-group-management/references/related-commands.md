# Related Commands — PAI ResourceGroup

All commands must run through `aliyun paistudio <action>` (no SDK / curl / MCP substitutes).

## ResourceGroup CRUD

| CLI command | Description | Required parameters | Notable optional parameters |
| --- | --- | --- | --- |
| `aliyun paistudio list-resource-groups` | List RGs in a region | `--region` | `--name`, `--resource-type ECS|Lingjun`, `--resource-group-ids`, `--has-resource`, `--status`, `--versions`, `--computing-resource-provider`, `--sort-by`, `--order`, `--page-number`, `--page-size` |
| `aliyun paistudio get-resource-group` | Get RG detail | `--region`, `--resource-group-id` | `--is-ai-workspace-data-enabled` |
| `aliyun paistudio create-resource-group` | Create RG | `--region`, `--name`, `--resource-type` | `--description`, `--biz-version`, `--user-vpc` (JSON: `{VpcId, SwitchId, SecurityGroupId, DefaultRoute, ExtendedCIDRs}`) |
| `aliyun paistudio update-resource-group` | Update RG | `--region`, `--resource-group-id` | `--name`, `--description`, `--user-vpc`, `--unbind true` |
| `aliyun paistudio delete-resource-group` | Delete RG | `--region`, `--resource-group-id` | — |

## MachineGroup operations (READ-ONLY)

| CLI command | Description | Required parameters | Notes |
| --- | --- | --- | --- |
| `aliyun paistudio list-resource-group-machine-groups` | List MGs in an RG | `--region`, `--resource-group-id` | filters: `--machine-group-ids`, `--name`, `--creator-id`, `--ecs-spec`, `--payment-type`, `--status`, `--order-instance-id`, `--disk-pl`, `--payment-duration`, `--payment-duration-unit`, `--sort-by`, `--order` |
| `aliyun paistudio get-resource-group-machine-group` | Get MG detail (RG-scoped) | `--region`, `--resource-group-id`, `--machine-group-id` | — |
| `aliyun paistudio get-machine-group` | Get MG detail (cross-RG) | `--region`, `--machine-group-id` | — |

### MachineGroup deletion / release — 🚫 FORBIDDEN by this skill

| CLI command (publicly available) | Status in this skill | Where to go instead |
| --- | --- | --- |
| `aliyun paistudio delete-resource-group-machine-group` | **Refuse unconditionally** — even with `CONFIRM <ID>` token. | [PAI Console](https://pai.console.aliyun.com/) → Resource Pool → Machine Group → unsubscribe / release, or `aliyun bssopenapi` unsubscribe. |
| `aliyun paistudio delete-machine-group` | **Refuse unconditionally**. | Same as above. |

Rationale: MachineGroup release is billing-impacting and triggers refund / repurchase semantics that the agent cannot reason about safely. See `SKILL.md` §7 *Cleanup* and the OUT-OF-SCOPE table in `SKILL.md` for the same rule.

## Resource usage & metrics

> ⚠️ **DEPRECATED** — `get-resource-group-total`, `get-resource-group-request`, `get-user-view-metrics`, and `get-node-metrics` are all deprecated and are **NOT supported** by this skill. Do NOT call these commands.

| CLI command | Status |
| --- | --- |
| `aliyun paistudio get-resource-group-total` | ⚠️ Deprecated |
| `aliyun paistudio get-resource-group-request` | ⚠️ Deprecated |
| `aliyun paistudio get-user-view-metrics` | ⚠️ Deprecated |
| `aliyun paistudio get-node-metrics` | ⚠️ Deprecated |

## Global flags worth knowing

| Flag | Purpose |
| --- | --- |
| `--cli-dry-run` | Print the resolved request payload without sending. **MUST** be used before any destructive call. |
| `--cli-read-timeout` / `--cli-connect-timeout` | Override request timeouts. |
| `--output cols=...` | Restrict tabular output to specific columns. |
| `--profile <name>` | Select a non-default Aliyun CLI profile. |
