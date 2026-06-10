# Related Commands — PAI Node

All commands must run through `aliyun paistudio <action>`. **Forbidden substitutes** (non-exhaustive — any "bypass the PAI control plane and touch the node object directly" path is forbidden):

- Python / Java / Go SDK (`aliyun-*-sdk-paistudio`) — even when the user explicitly requests a snippet.
- Raw `curl` against the PAI internal API.
- MCP tools (`pai_list_nodes` / `pai_get_node` / etc.) — used as a CLI shortcut.
- Terraform (`alicloud_pai_*` data sources / resources) — used to enumerate or mutate nodes.
- `kubectl` against the underlying cluster — any subcommand (`cordon` / `uncordon` / `drain` / `get nodes` / `describe node` / `top node` / `exec` / `logs` / `get pods --field-selector spec.nodeName=...` / `label node` / `taint node`).
- SSH into a node / `scp` / `nvidia-smi` / `top` / `dmesg` / `journalctl` / `crictl` / `docker ps` on the node.
- Prometheus node-exporter / DCGM-exporter direct query.
- Manual clicks in the PAI browser console — out of scope as a programmatic surface.

This skill is **mostly read-only** by design (the single mutating surface is `operate-node` for Cordon / Uncordon / Drain, gated by the `CONFIRM-NODE-OP <NODE_ID>` two-step protocol).

## Node inspection

| CLI command | Description | Required parameters | Notable optional parameters |
| --- | --- | --- | --- |
| `aliyun paistudio list-nodes` | List nodes in one or more RGs | `--region`, `--resource-group-ids` (CSV) | `--machine-group-ids` (CSV), `--node-names` (CSV), `--statuses` (CSV: `Running,Initializing,Stopped,Failed`), `--ecs-spec`, `--gpu-type`, `--cluster-id`, `--zone-id`, `--sort-by`, `--order`, `--page-number`, `--page-size` |
| ~~`aliyun paistudio get-node`~~ | ⚠️ **NOT available** in the public CLI — use `list-nodes --node-names "${NODE_NAME}"` to inspect a single node. | — | — |
| ~~`aliyun paistudio get-node-metrics`~~ | ⚠️ **NOT available** in the public CLI — node-level metrics are no longer exposed by this skill. | — | — |

## Context / cross-reference (covered by sibling skills, listed for convenience)

| CLI command | Purpose |
| --- | --- |
| `aliyun paistudio list-resource-groups` | Resolve `--resource-group-id` candidates. |
| `aliyun paistudio list-resource-group-machine-groups` | Resolve `--machine-group-ids` candidates. |
| ~~`aliyun paistudio get-resource-group-total`~~ | ⚠️ **Deprecated** — do NOT call. |
| ~~`aliyun paistudio get-user-view-metrics`~~ | ⚠️ **Deprecated** — do NOT call. |
| ~~`aliyun paistudio get-resource-group-request`~~ | ⚠️ **Deprecated** — do NOT call. |

## CSV vs space-separated list flags (gotcha)

| Command | Flag | Format |
| --- | --- | --- |
| `list-nodes` | `--resource-group-ids` / `--machine-group-ids` / `--node-names` / `--statuses` | **CSV string** (`"a,b,c"`) |
| `create-quota` / `scale-quota` | `--resource-group-ids` | **Space-separated** repeated values (`rg-a rg-b`) |

Always confirm with `--help` before scripting.

## Global flags worth knowing

| Flag | Purpose |
| --- | --- |
| `--cli-dry-run` | Print the resolved request payload without sending. Useful for verifying CSV vs list-flag behavior. |
| `--cli-read-timeout` / `--cli-connect-timeout` | Override request timeouts. |
| `--output cols=...` | Restrict tabular output to specific columns (e.g. `NodeName,Status,MachineGroupId`). |
| `--profile <name>` | Select a non-default Aliyun CLI profile. |
