# NOT Implementable / Forbidden via this skill — PAI ResourceGroup

The following ResourceGroup-related capabilities exist in the internal Yuque API spec (https://aliyuque.antfin.com/pai/api-doc/bic3z5) but are **NOT exposed** through the public `aliyun paistudio` plugin (v0.3.0) or the public PAI OpenAPI (cross-check at https://next.api.aliyun.com/document/PaiStudio/2022-01-12/overview). They cannot be invoked from this skill.

| Internal API | Reason / Workaround |
| --- | --- |
| `CreateMachineGroup` (purchase hardware into an RG) | Pure BSS purchase flow. Use the [PAI Console](https://pai.console.aliyun.com/) or the BSS OpenAPI. |
| `UpdateMachineGroup` (modify spec / payment / quantity) | Console-only / BSS flow. |
| `RenewMachineGroup` (subscription renewal) | BSS billing flow, not exposed via `paistudio`. |
| `ChangeMachineGroupCharge` (PostPaid ↔ Subscription switch) | BSS billing flow. |
| `OperateMachineGroup` (start / stop / reboot bulk) | Use `aliyun ecs ...` directly on the underlying ECS instances. |
| `GetResourceGroupRequest` | **Deprecated** on the public portal; not exposed in the plugin. |
| `GetResourceGroupTotal` | **Deprecated** — ResourceGroup-level capacity totals are no longer supported. |
| `GetUserViewMetrics` | **Deprecated** — User-view metrics on ResourceGroup are no longer supported. |
| `GetNodeMetrics` | **Deprecated** — Node metrics on ResourceGroup are no longer supported. |
| Cross-account RG sharing | Not exposed publicly. |

## Forbidden by this skill (publicly available, but intentionally NOT used)

| Public CLI action | Why this skill refuses it | Where the user should go |
| --- | --- | --- |
| `aliyun paistudio delete-resource-group-machine-group` | **Billing-impacting**: releases purchased ECS / Lingjun capacity, may trigger refund / repurchase semantics that the agent cannot reason about safely. Even with a `CONFIRM <MACHINE_GROUP_ID>` token, the agent MUST refuse. | [PAI Console](https://pai.console.aliyun.com/) → Resource Pool → Machine Group → Unsubscribe/Release, or `aliyun bssopenapi` unsubscribe APIs. |
| `aliyun paistudio delete-machine-group` | Same rationale as above — directly releases a MachineGroup. | [PAI Console](https://pai.console.aliyun.com/) or BSS OpenAPI. |

> Rule: if a capability is not in the public OpenAPI portal or in the `aliyun paistudio --help` output, treat it as **not implementable** by this skill. Do NOT fall back to SDK / curl / MCP / Terraform.
>
> Rule (forbidden list): even when a CLI command IS publicly available, if it appears in the "Forbidden by this skill" table above, the agent MUST refuse to invoke it and redirect the user to the documented alternative.
