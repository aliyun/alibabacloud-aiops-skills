# ACK install (same account, same region)

ACK addon name is **`loongcollector`**. `loongcollector-ds` is the in-cluster DaemonSet, not the addon API name. `describe-addon loongcollector-ds` returns AddonNotFound.

The executable contracts below inherit the [shared User-Agent setup](../../../SKILL.md#observability).

## Required inputs

- `region`, ACK `cluster_id` (unless the user explicitly asked to **create** a cluster)
- collection target (namespace/container filter or file path) when collection onboarding is requested

Keep the same CLI credential profile for preflight, CS/RAM operations and addon
polling. Pass `--profile <profile>` to direct CLI calls and both ACK helpers when
one was explicitly selected. Without this option, helpers retain the CLI's normal
environment/default-profile selection; do not change the saved default.

## First-use account (Skill capability)

On a first-use account, handle `ErrorNotEnabled` / `cskpro` / `EntityNotExist.Role`.

After user authorization for installation and the first-use account setup:

```bash
bash scripts/loongcollector/ensure_ack_prereq.sh --region <r> --profile <profile>
```

The script is idempotent and does two things:

1. `aliyun cs open-ack-service --type propayasgo` — opens ACK Pro + Basic (pay-as-you-go). Already-enabled is a no-op.
2. Ensure CS service roles (`get-role` / `create-role` + `attach-policy-to-role` System policy):
   - `AliyunCSDefaultRole`
   - `AliyunCSManagedKubernetesRole`
   - `AliyunCSManagedNetworkRole`
   - `AliyunCSManagedLogRole`
   - `AliyunCSManagedCmsRole`
   - `AliyunCSManagedCsiRole`
   - `AliyunCSManagedAutoScalerRole`

Missing DefaultRole after the script enters the fixed permission-recovery HITL, not `[BLOCKED: PREFLIGHT_FAILED]`. Point the user at the ACK RAM role authorization page. Do not invent a second plane.

The script reports ready only after the service-open call succeeds and every listed
role has its required System policy. A failed service call blocks RAM changes;
failed role or policy setup blocks completion even if DefaultRole already exists.

Any later CS write (`install-cluster-addons`, `create-cluster`, …) that returns `ErrorNotEnabled` / `cskpro` / `NotEnabled` → run `ensure_ack_prereq.sh` again, wait a few seconds, **retry that write once**. Same for `EntityNotExist.Role` / `AliyunCSDefaultRole`. Stop and report a second identical failure.

### Create cluster (only if the user asked)

Creating a cluster is **opt-in**. Use the cluster selected by the user. Creating ECS / inventing a VPC is still out of scope — ask for an existing `vpcid` + `vswitch-ids` (and name) if they asked to create a cluster.

```bash
aliyun cs create-cluster --name <name> --biz-region-id <r> --region <r> \
  --cluster-type ManagedKubernetes --biz-profile Default --cluster-spec ack.standard \
  --vpcid <vpc> --vswitch-ids <vsw> \
  --addons name=flannel --addons name=loongcollector \
  --container-cidr 172.16.0.0/16 --service-cidr 172.19.0.0/20 \
  --snat-entry true
```

- Use `--biz-profile Default` for the cluster profile. `--profile` selects CLI credentials.
- Spec order: `ack.standard` first, then `ack.pro.small` if Basic is refused and Pro is enabled.
- On `ErrorNotEnabled` / `cskpro`: run `open-ack-service` and retry that spec once.
- On `EntityNotExist.Role`: `ensure_ack_prereq.sh` then retry once.

Then wait until `describe-cluster-detail` `state=running` and continue to addon install.

## Observe first

```bash
aliyun cs describe-addon --addon-name loongcollector --cluster-id <cid> --region <r>
aliyun cs list-cluster-addon-instances --cluster-id <cid> --region <r>
aliyun cs describe-cluster-addon-instance --cluster-id <cid> --addon-name loongcollector --region <r>
```

- If `logtail` / `logtail-ds` is already installed and mutex with `loongcollector`, **stop**. Do not auto-uninstall (R4).
- Preflight: `bash scripts/loongcollector/preflight.sh --need-cs --region <r>` (missing CS plugin or a failed CS availability probe blocks; an explicit not-enabled response is a warning). See [preflight gates](../prerequisites.md).

## Install / upgrade

```bash
aliyun cs install-cluster-addons --cluster-id <cid> --biz-body name=loongcollector --region <r>
aliyun cs upgrade-cluster-addons --cluster-id <cid> --biz-body component_name=loongcollector --region <r>
```

Current plugin flag is `--biz-body`, not `--body`. Optional `version=` only after `describe-addon` (never hardcode a doc example).

Wait: `bash scripts/loongcollector/wait_cs_task.sh --cluster-id <cid> --addon-name loongcollector --region <r> --profile <profile>`
or bounded `describe-cluster-addon-instance` polls. Stage gate: addon `active` and `loongcollector-ds` Running.

## Reuse official cloud resources

After a successful addon install ACK creates:

- Project `k8s-log-${cluster_id}`
- Machine group `k8s-group-${cluster_id}`

**Must reuse.** Do not create an unrelated IP machine group.

**Ownership gate:** run `project get --project k8s-log-${cluster_id}` first. An `Unauthorized` / 401 response whose message says the project does not belong to the current account means the official project belongs to **another account** — emit `[BLOCKED: RESOURCE_RESOLUTION_FAILED]`. Do **not** enter the permission-recovery HITL, do not `project create` with that official name, and do not install the addon into a cluster whose official project you do not own. Verify project ownership for the selected cluster before installation.

Also list existing logstores and pipeline configs / CRs. If the user only asked to “install and see logs” and a default stdout logstore already has data → skip creating duplicate collection resources, record the existing resources used, and run U4–U6 on that logstore.

## Collection after install

Stop after addon/collector readiness for installation-only requests. Follow this section when collection onboarding or end-to-end verification was requested.

**Default SLS API.** Create Logstore + Pipeline (`k8s_stdio` / `k8s_file`) and bind **only** `k8s-group-${cluster_id}`. Do not ask for kubeconfig. Addon readiness uses CS APIs (`describe-cluster-addon-instance`, `list-cluster-addon-instance-resources` DaemonSet `numberReady`) — that is not kube-apiserver access.

CRD apply is opt-in: the user must explicitly request GitOps/CR management, a public API Server must be reachable through a temporary KubeConfig, RBAC must allow `ClusterAliyunPipelineConfig` creation, and the controller must be running. CloudShell is not an Agent channel.

`kubectl get/describe/apply` only on that opt-in path. `kubectl exec` is forbidden. Never print kubeconfig.

## Authorization

Installation, first-use account setup and collection changes require user authorization. Showing planned changes as a diff is recommended.
After authorization, if ACK is not opened or CS roles are missing, run `scripts/loongcollector/ensure_ack_prereq.sh` first, then install the addon. Existing authorization covering first-use setup also covers this step.
Only create a CR or API config when it is within the requested and authorized collection workflow.
