# ACK CLI Worked Scenarios

Practical end-to-end examples for ACK (Container Service) `cs` plugin operations.
These complement SKILL.md — read SKILL.md first for the core rules (plugin vs
OpenAPI, async task pattern, complex JSON parameters), then come here for
copy-pasteable workflows.

## Contents

- [§1 Discover and inspect clusters](#1-discover-and-inspect-clusters)
- [§2 Get kubeconfig and use kubectl](#2-get-kubeconfig-and-use-kubectl)
- [§3 Node pool operations](#3-node-pool-operations)
- [§4 Addon management (the JSON-string-inside-JSON trap)](#4-addon-management-the-json-string-inside-json-trap)
- [§5 Cluster upgrade](#5-cluster-upgrade)
- [§6 Modify cluster configuration](#6-modify-cluster-configuration)
- [§7 Delete a cluster (writes!)](#7-delete-a-cluster-writes)
- [§8 Putting it together: create cluster → wait → get kubeconfig](#8-putting-it-together-create-cluster--wait--get-kubeconfig)

> All examples assume `aliyun` ≥ 3.3.3 with the `cs` plugin installed
> (`aliyun plugin install --names cs`) and a profile with at minimum
> a RAM identity with the `cs` Actions you'll call (read or write).

> **Region routing (important):** examples that take a `--cluster-id` also pass
> `--region <region>` to route directly to that cluster's regional CS
> endpoint (SKILL.md §6 Rule B). Examples that target a region directly
> (the `*ForRegion` APIs) take `--biz-region-id <region>` instead — that's
> the *required business parameter*, not the global endpoint flag (SKILL.md
> §6 Rule A). Substitute `<region>` with the actual value
> (`cn-hangzhou`, `cn-beijing`, etc.). If you don't yet know the cluster's
> region, list with `describe-clusters-for-region --biz-region-id <region>`
> first.

## 1. Discover and inspect clusters

When the region is known (the common case), use the **region-unitised** API
`describe-clusters-for-region` rather than the legacy global aggregator
`describe-clusters-v1`. The region-unitised endpoint is faster, has higher
quotas, and stays available when the global aggregator is degraded. Reserve
`describe-clusters-v1` for the rare case where you genuinely want one call to
span all regions.

```bash
# ✅ List clusters in a specific region (use this most of the time)
#    Note the *business* parameter --biz-region-id (required), not the global --region.
aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou

# Tabular summary of running clusters only
aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou \
  --cli-query "clusters[?state=='running'].{id:cluster_id,name:name,version:current_version,size:size}" \
  --output table

# Recent operation plans (auto-upgrade, AutoMode, CVE auto-fix) for the region
aliyun cs list-operation-plans-for-region --biz-region-id cn-hangzhou

# Cluster events for the region (audit-friendly view)
aliyun cs describe-events-for-region --biz-region-id cn-hangzhou

# Cross-region aggregate (legacy fallback — only when you truly need every region)
aliyun cs describe-clusters-v1

# Drill into one cluster
aliyun cs describe-cluster-detail --cluster-id ce914461c0fb4901ae8908be4a10a7a1 --region cn-hangzhou

# What addons are installed (versions, status)
aliyun cs list-cluster-addon-instances --cluster-id <cid> --region <region>

# What addons are AVAILABLE for this cluster (with config_schema!)
aliyun cs list-addons --cluster-id <cid> --region <region>

# Detail for one specific addon (config_schema, supported versions, etc.)
aliyun cs describe-addon --cluster-id <cid> --addon-name <name> --region <region>
```

`list-addons` is the single most useful read command for addon work — its
response embeds each addon's `config_schema`, which tells you exactly what
fields are valid in the `config` JSON-string when installing/upgrading.

## 2. Get kubeconfig and use kubectl

```bash
# Public-endpoint kubeconfig (works from your laptop if cluster has public APIServer)
aliyun cs describe-cluster-user-kubeconfig \
  --cluster-id <cid> \
  --region <region> \
  --private-ip-address false \
  | jq -r '.config' > ~/.kube/ack-<cid>.yaml

# Private-endpoint kubeconfig (works inside the cluster's VPC)
aliyun cs describe-cluster-user-kubeconfig \
  --cluster-id <cid> \
  --region <region> \
  --private-ip-address true \
  | jq -r '.config' > ~/.kube/ack-<cid>-internal.yaml

export KUBECONFIG=~/.kube/ack-<cid>.yaml
kubectl get nodes
kubectl get pods -A
```

Tips:

- If the cluster has no public endpoint, the public-endpoint kubeconfig will
  return but won't actually work — check `describe-cluster-detail` for
  `master_url.api_server_endpoint` (public) vs `intranet_api_server_endpoint`.
- Kubeconfigs issued for RAM users may be temporary (STS-backed). Re-fetch when
  they expire instead of editing the token in place.

## 3. Node pool operations

```bash
# Inventory
aliyun cs describe-cluster-node-pools --cluster-id <cid> --region <region>

# One node pool's details (full spec, scaling config, status)
aliyun cs describe-cluster-node-pool-detail \
  --cluster-id <cid> \
  --region <region> \
  --nodepool-id <npid>

# Resize to an absolute desired count: modify-cluster-node-pool with
# desired_size sets the target size directly. (scale-cluster-node-pool --count
# is a delta — adds N nodes — and rarely matches "scale to N" intent.)
aliyun cs modify-cluster-node-pool \
  --cluster-id <cid> \
  --region <region> \
  --nodepool-id <npid> \
  --scaling-group desired_size=5

# Upgrade node pool to a specific kubelet/runtime version
aliyun cs upgrade-cluster-nodepool \
  --cluster-id <cid> \
  --region <region> \
  --nodepool-id <npid> \
  --kubernetes-version 1.30.1-aliyun.1 \
  --runtime-version 1.6.28 \
  --image-id aliyun_3_x64_20G_alibase_20240819.vhd
```

`modify-cluster-node-pool`, `scale-cluster-node-pool`, and
`upgrade-cluster-nodepool` are all async — they return a `task_id`. Track
with `describe-task-info` (see SKILL §4 for the lifecycle).

### Creating a new node pool

`create-cluster-node-pool` takes three nested groups: `nodepool_info` (name +
type), `scaling_group` (instance shapes, AZs, vSwitches, system disk), and
`kubernetes_config` (labels, taints, runtime, etc.):

```bash
aliyun cs create-cluster-node-pool \
  --cluster-id <cid> \
  --region <region> \
  --nodepool-info '{"name":"workers-2","type":"ess"}' \
  --scaling-group '{
    "instance_types": ["ecs.g7.xlarge", "ecs.g7.large"],
    "vswitch_ids":   ["vsw-bp1xxx", "vsw-bp1yyy"],
    "system_disk_category": "cloud_essd",
    "system_disk_size":     120,
    "desired_size":         3,
    "key_pair":             "my-keypair"
  }' \
  --kubernetes-config '{
    "runtime":         "containerd",
    "runtime_version": "1.6.28",
    "labels":          [{"key":"role","value":"worker"}],
    "taints":          []
  }'
```

Build large JSON blobs in a file (`--scaling-group "$(cat scaling.json)"`) when
they get unwieldy on the command line — it's much easier than escaping.

## 4. Addon management (the JSON-string-inside-JSON trap)

The `config` field on every addon body is a JSON document **encoded as a string**.
This is the most error-prone shape in the entire `cs` API. Build it with `jq`:

```bash
# Compose the addons body safely with jq
ADDONS_BODY=$(jq -nc '
  [
    {
      name: "logtail-ds",
      config: ({sls_project_name: "k8s-log-ce123"} | tojson)
    }
  ]
')

aliyun cs install-cluster-addons \
  --cluster-id <cid> \
  --region <region> \
  --body "$ADDONS_BODY"
```

Without `jq`, you'd hand-write something like:

```bash
--body '[{"name":"logtail-ds","config":"{\"sls_project_name\":\"k8s-log-ce123\"}"}]'
```

…which is correct but easy to break. Prefer the `jq | tojson` approach for any
`config` longer than one key.

### Upgrade installed addons

```bash
aliyun cs upgrade-cluster-addons \
  --cluster-id <cid> \
  --region <region> \
  --body '[{"component_name":"logtail-ds","next_version":"1.8.0"}]'
```

### Uninstall addons

```bash
aliyun cs un-install-cluster-addons \
  --cluster-id <cid> \
  --region <region> \
  --body '[{"name":"logtail-ds","cleanup_cloud_resources":false}]'
```

`cleanup_cloud_resources=true` lets ACK delete cloud resources the addon created
(e.g. SLB, log projects). Use sparingly — defaulting to `false` is safer.

## 5. Cluster upgrade

```bash
# What target versions can this cluster upgrade to?
# describe-cluster-detail only shows the single "next" version field; for the
# full list of upgradable versions plus release/expiry metadata, query the
# version metadata API directly:
CURRENT=$(aliyun cs describe-cluster-detail --cluster-id <cid> --region <region> \
  --cli-query 'current_version' --output text)

aliyun cs describe-kubernetes-version-metadata \
  --cluster-type ManagedKubernetes \
  --biz-region <region> \
  --kubernetes-version "$CURRENT" \
  --query-upgradable-version true \
  --cli-query "[].{version:version,release:release_date,expire:expiration_date,upgradable:upgradable_versions}"

# Kick off control-plane upgrade — returns task_id for tracking and control.
# --master-only scopes the upgrade to the control plane; node pools upgrade
# separately via upgrade-cluster-nodepool (§3).
RESP=$(aliyun cs upgrade-cluster \
  --cluster-id <cid> \
  --region <region> \
  --next-version 1.30.1-aliyun.1 \
  --master-only true)

UPGRADE_TID=$(echo "$RESP" | jq -r '.task_id')

# Mid-upgrade control via task APIs:
aliyun cs pause-task  --task-id "$UPGRADE_TID" --region <region>
aliyun cs resume-task --task-id "$UPGRADE_TID" --region <region>
aliyun cs cancel-task --task-id "$UPGRADE_TID" --region <region>
```

Cluster upgrade is async. Track the `task_id` from `upgrade-cluster`, and
remember: control-plane upgrade and node-pool upgrade are separate steps —
running `upgrade-cluster` does **not** roll your nodes.

## 6. Modify cluster configuration

`cs modify-cluster` updates cluster-level configuration in place — name,
deletion protection, maintenance window, resource group, API Server access
options, control-plane settings, and more. It's the right API for "change
this attribute on an existing cluster"; for tagging see the dedicated
`tag-resources` API family (out of scope here).

### Common attributes you can change

| Field | Flag | Notes |
| ----- | ---- | ----- |
| Cluster display name | `--cluster-name <name>` | 1–63 chars; digits/letters/Chinese/dash; can't start with `-` |
| Deletion protection | `--deletion-protection true\|false` | Blocks `delete-cluster` via console + API |
| Instance deletion protection | `--instance-deletion-protection true\|false` | Blocks node release |
| Resource group | `--resource-group-id rg-xxx` | Affects RAM/cost-allocation scope |
| Maintenance window | `--maintenance-window '...'` | Pro Managed clusters only |
| Auto-ops policy | `--operation-policy '...'` | Auto-upgrade channel etc. |
| Control-plane SG | `--security-group-id sg-xxx` | |
| Control-plane vSwitches | `--vswitch-ids vsw-a vsw-b` | New control-plane nodes will spawn here on scale |
| API Server EIP | `--api-server-eip true` + `--api-server-eip-id eip-xxx` | Expose APIServer publicly |
| API Server cert SANs | `--api-server-custom-cert-sans '...'` | Add custom SANs (managed clusters only) |
| RRSA | `--enable-rrsa true\|false` | OIDC-style pod-level credentials (managed only) |
| Cluster timezone | `--timezone Asia/Shanghai` | |

Run `aliyun cs modify-cluster --help` for the full list.

### Worked examples

```bash
# Rename + enable deletion protection in one call
aliyun cs modify-cluster \
  --cluster-id <cid> \
  --region <region> \
  --cluster-name my-prod-cluster \
  --deletion-protection true

# Move cluster into a different resource group
aliyun cs modify-cluster \
  --cluster-id <cid> \
  --region <region> \
  --resource-group-id rg-xxx

# Configure a maintenance window (Pro managed clusters only)
aliyun cs modify-cluster \
  --cluster-id <cid> \
  --region <region> \
  --maintenance-window '{"enable":true,"maintenance_time":"01:00:00Z","duration":"3h","weekly_period":"Tuesday,Saturday"}'

# Bind a public EIP to API Server
aliyun cs modify-cluster \
  --cluster-id <cid> \
  --region <region> \
  --api-server-eip true \
  --api-server-eip-id eip-bp1xxx
```

### Tips

- **Pair with `--cli-dry-run`** for non-trivial changes (especially
  `maintenance-window` / `operation-policy` / `api-server-custom-cert-sans`,
  which take JSON objects — easy to escape wrong). See SKILL §12.
- The maintenance window controls when ACK auto-upgrade runs for managed
  components — recommended for production clusters.
- `--deletion-protection true` is cheap insurance against accidental
  `delete-cluster` calls; combine it with dry-run discipline.
- Some fields take JSON object structures (`--maintenance-window`,
  `--operation-policy`, `--api-server-custom-cert-sans`,
  `--control-plane-config`, `--system-events-logging`). Always inspect the
  exact `structure: { ... }` shape via `--help` before composing — guessing
  produces `InvalidParameter.Format`.

## 7. Delete a cluster (writes!)

```bash
aliyun cs delete-cluster \
  --cluster-id <cid> \
  --region <region> \
  --keep-slb false \
  --retain-resources '[]'
```

Returns `task_id` — track it. Once the task succeeds, the cluster is gone and
its IDs cannot be recovered. **Always confirm with the user before issuing
`delete-cluster`** — it's the most expensive irreversible operation in this API.

## 8. Putting it together: create cluster → wait → get kubeconfig

```bash
# 1. Create (returns task_id immediately)
RESP=$(aliyun cs create-cluster \
  --biz-region-id cn-beijing \
  --region cn-beijing \
  --cluster-type ManagedKubernetes \
  --profile Default \
  --cluster-spec ack.pro.small \
  --auto-mode '{"enable":true}' \
  --name my-ack-cluster \
  --kubernetes-version 1.30.1-aliyun.1)

CID=$(echo "$RESP" | jq -r '.cluster_id')
TID=$(echo "$RESP" | jq -r '.task_id')
echo "Cluster $CID, task $TID — waiting..."

# 2. Wait (after confirming with user)
./scripts/wait-for-task.sh "$TID" cn-beijing

# 3. Fetch kubeconfig (cluster lives in cn-beijing per the create-cluster call)
aliyun cs describe-cluster-user-kubeconfig --cluster-id "$CID" --region cn-beijing \
  | jq -r '.config' > ~/.kube/ack-$CID.yaml
export KUBECONFIG=~/.kube/ack-$CID.yaml
kubectl get nodes
```

For network plugin selection (Terway vs Flannel) and multi-AZ vSwitch wiring,
see the worked example in §4 above plus SKILL.md §5 (the JSON-string-inside-
JSON pattern). AutoMode (`--auto-mode '{"enable":true}'`) is the easiest path
when you don't want to specify everything by hand.
