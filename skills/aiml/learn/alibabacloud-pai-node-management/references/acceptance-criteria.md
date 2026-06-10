# Acceptance Criteria — PAI Node

## Product / action

- ✅ `aliyun paistudio list-nodes`, `aliyun paistudio operate-node`.
- ✅ To inspect a single node, use `list-nodes --node-names "<name>"` (since `get-node` is not yet available).
- ❌ `aliyun paistudio get-node` (not yet available in the public CLI).
- ❌ `aliyun paistudio get-node-gpu-metrics` (not available in the public CLI).
- ❌ `aliyun paistudio list-node-pods` (not available in the public CLI).
- ❌ `aliyun paistudio list-node-types` (not yet available in the public CLI).
- ❌ `aliyun pai list-nodes` (wrong product prefix — plugin is `paistudio`).
- ❌ `aliyun paistudio ListNodes` (PascalCase — CLI uses kebab-case).

## Required parameters

- ✅ Always pass `--region "${REGION_ID}"` (no implicit region inference; never derive from environment heuristics).
- ✅ `list-nodes` requires **both** `--region` AND exactly one scope flag (`--resource-group-ids` CSV **OR** `--quota-id`); mutually exclusive, never both, never neither.
- ✅ Single node inspection: `list-nodes --region "${REGION_ID}" --resource-group-ids "<rg>" --node-names "<name>" --page-number 1 --page-size 1` — `--region`, `--resource-group-ids`, and `--page-size 1` are **all mandatory** for single-node lookup.
- ❌ Single-node lookup without `--region` (`list-nodes --resource-group-ids "<rg>" --node-names "<name>"`).
- ❌ Single-node lookup without `--resource-group-ids` (`list-nodes --region "..." --node-names "<name>"` — backend rejects with scope error).
- ❌ Single-node lookup with `--page-size 50` / `--page-size 100` (MUST be collapsed to `1` for single-node intent; larger pages over-fetch and obscure the exactly-one-match assertion).
- ❌ Calling `get-node` (not available — use `list-nodes --node-names` instead).
- ❌ Calling `get-node-gpu-metrics` or `list-node-pods` (not available in the public CLI).

## List-flag format gotcha

- ✅ `aliyun paistudio list-nodes --resource-group-ids "rg-aaa,rg-bbb"` — CSV string.
- ✅ `aliyun paistudio list-nodes --machine-group-ids "mg-aaa,mg-bbb"` — CSV string.
- ✅ `aliyun paistudio list-nodes --node-names "node-1,node-2"` — CSV string.
- ❌ `aliyun paistudio list-nodes --resource-group-ids rg-aaa rg-bbb` (space-separated — `list-nodes` requires CSV, unlike `create-quota`).

## Enums

- ✅ `--metric-type cpu|memory|gpu|disk|net`.
- ✅ `--statuses "Running,Failed"`.
- ❌ `--metric-type GPU` (lowercase only).
- ❌ `--statuses "running"` (PascalCase only: `Running`).

## Read-only enforcement

- ✅ Refuse any node power (start / stop / reboot) / replace / migrate request — these are NOT implementable, and the agent MUST direct the user to a Lingjun ops ticket / account manager (per the SKILL.md §1 out-of-scope list).
- ❌ Falling back to the underlying ECS instance's power-state CLI / SDK (any form — kebab-case `aliyun ecs …`, legacy CamelCase actions, SDK) from inside this skill — even as a *suggestion* to the user. Power-state mutation of a PAI-managed node is out of scope, period.
- ❌ 🚫 **Echoing the literal forbidden command names in the refusal reply.** Even when explaining "why I can't reboot the node", the agent MUST NOT print the literal CLI / SDK action names in any executable form (backtick code, inline `<code>`, shell example, "I cannot run X" sentences). Describe the forbidden path in plain natural language ("node power-state-related commands" / "the underlying instance's power-state CLI") — see the *Forbidden literal-string rule for node power / reboot refusals* callout in `SKILL.md` §1.

## `operate-node` `--operation-parameters` JSON

- ✅ Cordon / Uncordon scoped: `'{"CordonParameters":{"QuotaId":"q-xxx","WorkspaceId":"ws-xxx","Comment":"..."}}'` — `QuotaId` and `WorkspaceId` set together.
- ✅ Cordon / Uncordon unscoped: omit BOTH `QuotaId` and `WorkspaceId` from the parameters object.
- ✅ Drain by sub-product: `'{"DrainParameters":{"PodFromSubProducts":["DLC","DSW"]}}'` (allowed values: `DLC`, `DSW`, `EAS`, `Tensorboard`).
- ❌ Cordon / Uncordon with only one of `QuotaId` / `WorkspaceId` set — backend rejects with `"both quota id and workspace id should be provided"`.
- ❌ Drain `PodFromSubProducts` containing any value other than `DLC` / `DSW` / `EAS` / `Tensorboard`.
- ❌ 🚫 **Including `"Force"` in `DrainParameters`** (e.g. `'{"DrainParameters":{"Force":true}}'`) — `Force` is gated to a backend-managed operator whitelist and MUST NOT be set by this skill. If the user requests force-drain, refuse and refer them to the platform operations team.

## Tool selection

- ✅ All operations through `aliyun paistudio <action>`.
- ❌ Falling back to MCP (`pai_list_nodes` / `pai_get_node` / any `pai_*` node tool), raw `curl`, Python SDK (`aliyun-python-sdk-paistudio`), Java SDK (`aliyun-java-sdk-paistudio`), Go SDK, Terraform (`alicloud_pai_*` data sources / resources), web-console clicks, or any form of node-level direct-access (nodes are platform-managed resources; there is no user-reachable direct-access path).
- ❌ Suggesting `kubectl` (any subcommand: `cordon` / `uncordon` / `drain` / `get nodes` / `describe node` / `top node` / `exec` / `logs` / `get pods --field-selector spec.nodeName=...` / `label node` / `taint node`) as a fallback — even when the user explicitly asks for it ("I'll just `kubectl drain --force` myself, can you give me the command?"). The agent MUST refuse and MUST NOT echo or complete the `kubectl` command.
- ❌ Suggesting `nvidia-smi` as a fallback for per-node GPU metrics — whether via SSH, `kubectl exec`, or any other path. The reply MUST direct the user to the PAI Console ResourceGroup / Quota dashboards instead.
- ❌ Suggesting SSH to the node / `scp` / `top` / `dmesg` / `journalctl` / `crictl` / `docker ps` on the node as a workaround for `GetNode` / `GetNodeGPUMetrics` / `ListNodePods` gaps.
- ❌ Suggesting Prometheus node-exporter / DCGM-exporter direct query as a workaround for per-node metrics.

## Forbidden channels for node enumeration & inspection

- ✅ `aliyun paistudio list-nodes --region "${REGION_ID}" --resource-group-ids "<rg-csv>"` — the **only** legal channel for node enumeration.
- ❌ Python / Java / Go SDK `ListNodes` / `DescribeNodes` direct invocation.
- ❌ `curl https://pai.<region>.aliyuncs.com/...` against the PAI internal API.
- ❌ MCP tools (`pai_list_nodes`, etc.) used as a "shortcut" around the CLI.
- ❌ Terraform `data "alicloud_pai_nodes"` (or equivalent) used to enumerate nodes.
- ❌ `kubectl get nodes` against the underlying cluster.
- ❌ SSH into a single node to enumerate siblings.

> Even when the user explicitly asks for one of the forbidden channels ("just give me the Python SDK snippet, I don't want to install the CLI"), the agent MUST refuse and respond with the `aliyun paistudio list-nodes` command instead.
