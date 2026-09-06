# ClusterAliyunPipelineConfig (opt-in management plane)

Source: `loongcollector-oncall/knowledge/base/collection-config/config-model.md`.
Kind: `ClusterAliyunPipelineConfig` (`telemetry.alibabacloud.com/v1alpha1`, cluster-scoped).
`metadata.name` **is** the SLS pipeline config name.

Do not create `AliyunLogConfig` or `NamespaceAliyunPipelineConfig`.

## Default is SLS API

ACK / self-k8s **collection** defaults to:

```bash
aliyun sls create-logtail-pipeline-config ...
aliyun sls apply-config-to-machine-group --machine-group k8s-group-<cid> ...
```

Do not start collection by asking for kubeconfig. Missing kubectl is not a collection blocker on ACK.

## Local render / validate (no cluster)

If the user only asked to render or validate a `ClusterAliyunPipelineConfig` (no apply, no cluster):

```bash
python3 scripts/render_crd.py --input task.json
python3 scripts/validate_pipeline.py --file <spec.config or rendered pipeline>
```

Run these as two standalone calls and keep each script's JSON/status visible on stdout. `tee` may persist the same output, but do not redirect it only to a file and leave the call result with just an exit code.

Do **not** call `aliyun cs`, `open-ack-service`, `describe-clusters`, `kubectl`, or fetch kubeconfig. State that the output was rendered and validated locally without connecting to a cluster.

## When to use CRD (opt-in)

Use CRD only when **all** of these hold:

1. The user explicitly asked for `ClusterAliyunPipelineConfig` / GitOps / `kubectl apply` CR.
2. Environment is ACK or self-built K8s.
3. `kubectl` is on PATH (or the user named a working context).
4. A **reachable** kube-apiserver is proven (see Temporary public KubeConfig below).
5. `kubectl auth can-i create clusteraliyunpipelineconfigs` is `yes`.
6. `kubectl get crd clusteraliyunpipelineconfigs.telemetry.alibabacloud.com` succeeds.
7. `alibaba-log-controller` or `loongcollector-operator` is running.

If any check fails, **stay on SLS API** and say so. Do not emit `[AWAITING: KUBECONFIG]` for ACK collection. Do not open a public API Server / bind EIP unless the user explicitly asks (R2).

**Do not write API** onto a config the controller already owns. CR registered but controller down → wait/fix U3; do not create a second plane.

## Temporary public KubeConfig (ACK, optional CRD only)

CS OpenAPI can **issue credentials**. It cannot `kubectl apply`. CloudShell / console Workbench are browser terminals, not an Agent channel.

Verified: `aliyun` 3.4.6 + `aliyun-cli-cs`. If `describe-cluster-detail` `master_url.api_server_endpoint` is empty, `--private-ip-address false` still returns the **intranet** `6443` and is useless from outside the VPC.

```bash
aliyun cs describe-cluster-detail --cluster-id <cid> --region <r> --user-agent <ua>
# require non-empty master_url.api_server_endpoint (public). intranet-only → stay on API.

aliyun cs describe-cluster-user-kubeconfig \
  --cluster-id <cid> --region <r> \
  --private-ip-address false \
  --temporary-duration-minutes 15 \
  --user-agent <ua>
```

Write `config` to a `0600` tempfile and set `KUBECONFIG`. **Never** print, `cat`, or paste kubeconfig / client cert / token into the conversation. Probe `https://<public-host>:6443` (TCP or `/readyz`) before `kubectl`. Unreachable → delete the file, stay on API.

Expiry is 15–4320 minutes. Re-fetch when expired. Do not overwrite `~/.kube/config`; use a per-cluster tempfile.

`list-cluster-addon-instance-resources` shows Helm objects (DaemonSet status, not a pod list). That is **not** kube-apiserver access and cannot apply a CR.

## Double-write

One config, one plane. Before apply:

```bash
kubectl get clusteraliyunpipelineconfigs
kubectl get aliyunlogconfigs --all-namespaces
aliyun sls get-logtail-pipeline-config --project <p> --config-name <c> --region <r> --user-agent <ua>
```

Same name (or the same collection) already on the other plane → STOP. `enableUpgradeOverride` defaults to `false`.

## Render and apply (opt-in path only)

```bash
python3 scripts/render_crd.py --input task.json
python3 scripts/validate_pipeline.py --file <spec.config.json>
python3 scripts/normalize_diff.py --kind auto
```

Show the YAML diff, then use the fixed create-and-bind approval subject from `SKILL.md`.

After approval:

```bash
kubectl apply --dry-run=server -f <cr.yaml>
kubectl apply -f <cr.yaml>
kubectl get clusteraliyunpipelineconfigs <name> -o yaml
```

`spec.project.name` is required (ACK: `k8s-log-${cid}`). `spec.config` matches CreateLogtailPipelineConfig. `spec.machineGroups` must be `k8s-group-${cid}`.

## Acceptance (CRD path)

| ID | Check |
|---|---|
| U1 | CR exists; `spec.config.inputs` and `flushers` non-empty; optional API `get-logtail-pipeline-config` after reconcile |
| U2 | `spec.machineGroups` contains the target; cloud bindings agree once controller synced |
| U3 | `status.success=true`, `lastAppliedConfig` non-empty |
| U4–U6 | same as API |

Empty U5 is not collection success.

## Rollback

Delete CR is R4 and may remove the cloud config. Inverse of apply is the pre-apply YAML snapshot.
