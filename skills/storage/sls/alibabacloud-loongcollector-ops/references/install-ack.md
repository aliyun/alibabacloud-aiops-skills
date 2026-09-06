# ACK install (same account, same region)

ACK addon name is **`loongcollector`**. `loongcollector-ds` is the in-cluster DaemonSet, not the addon API name. `describe-addon loongcollector-ds` returns AddonNotFound.

Verified CLI: `aliyun` 3.4.6 + `aliyun-cli-cs`. The executable contracts are listed below. `<ua>` is `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops session/<session-id>"`.

## Required inputs

- `region`, ACK `cluster_id` (unless the user explicitly asked to **create** a cluster)
- collection target (namespace/container filter or file path) unless the user only wants to query already-ingested default logs

## First-use account (Skill capability)

Eval hooks may already have opened ACK and created `sls-eval-loop-ack` so tests start warm. That is a **fixture**, not a substitute for Skill. On a real first-use account, do not stop at `ErrorNotEnabled` / `cskpro` / `EntityNotExist.Role`.

After the fixed ACK install approval subject and `[AWAITING: INSTALL_CONFIRMATION]`:

```bash
bash scripts/ensure_ack_prereq.sh --region <r>
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

Any later CS write (`install-cluster-addons`, `create-cluster`, …) that returns `ErrorNotEnabled` / `cskpro` / `NotEnabled` → run `ensure_ack_prereq.sh` again, wait a few seconds, **retry that write once**. Same for `EntityNotExist.Role` / `AliyunCSDefaultRole`. A second identical failure can then `[BLOCKED]`.

### Create cluster (only if the user asked)

Creating a cluster is **opt-in**. Do not auto-create `sls-eval-loop-ack` or any other eval fixture name in production. Creating ECS / inventing a VPC is still out of scope — ask for an existing `vpcid` + `vswitch-ids` (and name) if they asked to create a cluster.

```bash
aliyun cs create-cluster --name <name> --biz-region-id <r> --region <r> \
  --cluster-type ManagedKubernetes --biz-profile Default --cluster-spec ack.standard \
  --vpcid <vpc> --vswitch-ids <vsw> \
  --addons name=flannel --addons name=loongcollector \
  --container-cidr 172.16.0.0/16 --service-cidr 172.19.0.0/20 \
  --snat-entry true --user-agent <ua>
```

- Never pass `--profile` (CLI treats it as a credential profile). Use `--biz-profile Default`.
- Spec order: `ack.standard` first, then `ack.pro.small` if Basic is refused and Pro is enabled.
- On `ErrorNotEnabled` / `cskpro`: run `open-ack-service` and retry that spec once.
- On `EntityNotExist.Role`: `ensure_ack_prereq.sh` then retry once.

Then wait until `describe-cluster-detail` `state=running` and continue to addon install.

## Observe first

```bash
aliyun cs describe-addon --addon-name loongcollector --cluster-id <cid> --region <r> --user-agent <ua>
aliyun cs list-cluster-addon-instances --cluster-id <cid> --region <r> --user-agent <ua>
aliyun cs describe-cluster-addon-instance --cluster-id <cid> --addon-name loongcollector --region <r> --user-agent <ua>
```

- If `logtail` / `logtail-ds` is already installed and mutex with `loongcollector`, **stop**. Do not auto-uninstall (R4).
- Preflight: `bash scripts/preflight.sh --need-cs --region <r>` (CS plugin is the only hard gate; unopened ACK is a warn)

## Install / upgrade

```bash
aliyun cs install-cluster-addons --cluster-id <cid> --biz-body name=loongcollector --region <r> --user-agent <ua>
aliyun cs upgrade-cluster-addons --cluster-id <cid> --biz-body component_name=loongcollector --region <r> --user-agent <ua>
```

Current plugin flag is `--biz-body`, not `--body`. Optional `version=` only after `describe-addon` (never hardcode a doc example).

Wait: `bash scripts/wait_cs_task.sh --cluster-id <cid> --addon-name loongcollector --region <r>`
or bounded `describe-cluster-addon-instance` polls. Stage gate: addon `active` and `loongcollector-ds` Running.

## Reuse official cloud resources

After a successful addon install ACK creates:

- Project `k8s-log-${cluster_id}`
- Machine group `k8s-group-${cluster_id}`

**Must reuse.** Do not create an unrelated IP machine group.

**Ownership gate:** run `get-project --project k8s-log-${cluster_id}` first. An `Unauthorized` / 401 response whose message says the project does not belong to the current account means the official project belongs to **another account** — emit `[BLOCKED: RESOURCE_RESOLUTION_FAILED]`. Do **not** enter the permission-recovery HITL, do not `create-project` with that official name, and do not install the addon into a cluster whose official project you do not own. Prefer the cluster named `sls-eval-loop-ack` in this account; a fallback cluster ID is writable only after this get-project succeeds.

Also list existing logstores and pipeline configs / CRs. If the user only asked to “install and see logs” and a default stdout logstore already has data → `[Idempotent-Skip]` create, run U4–U6 on that logstore.

## Collection after install

**Default SLS API.** Create Logstore + Pipeline (`k8s_stdio` / `k8s_file`) and bind **only** `k8s-group-${cluster_id}`. Do not ask for kubeconfig. Addon readiness uses CS APIs (`describe-cluster-addon-instance`, `list-cluster-addon-instance-resources` DaemonSet `numberReady`) — that is not kube-apiserver access.

CRD apply is opt-in: the user must explicitly request GitOps/CR management, a public API Server must be reachable through a temporary KubeConfig, RBAC must allow `ClusterAliyunPipelineConfig` creation, and the controller must be running. CloudShell is not an Agent channel.

`kubectl get/describe/apply` only on that opt-in path. `kubectl exec` is forbidden. Never print kubeconfig.

## HITL

Use the fixed ACK install approval subject from `SKILL.md`, followed by `[AWAITING: INSTALL_CONFIRMATION]`.
After confirm, if ACK is not opened or CS roles are missing, run `scripts/ensure_ack_prereq.sh` first, then the addon install. Do not ask a second enablement question.
Then the standard create-and-bind question when a new CR or API config is required.
