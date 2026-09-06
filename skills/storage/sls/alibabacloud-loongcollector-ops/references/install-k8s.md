# Self-built / cross-account Kubernetes install

Official path: [container installation for a self-built Kubernetes cluster](https://help.aliyun.com/zh/sls/loongcollector-installation-kubernetes-1).
Requires user-provided `kubectl` and a confirmed kube-context. ACK same-account same-region uses the ACK install capability instead.

## Required inputs

- kube-context, `region`, `clusterID`
- `values.yaml` fields: `projectName`, `region`, `aliUid`, `net`, `clusterID`
- collection target unless default logs already exist

Missing kubectl uses the fixed Missing kubeconfig subject from `SKILL.md` followed by `[AWAITING: KUBECONFIG]`. **Never** emit `[BLOCKED: PREFLIGHT_FAILED] gate=kubectl` on the first miss. Do not `create-logtail-pipeline-config` or `kubectl apply` until kubectl is provided.

Preflight: `bash scripts/preflight.sh --need-kubectl --region <r>` (kubectl missing is a warn, not a hard fail).

## Package

Download the official **custom package** at runtime. Discover the version from the current download page or cluster-compatible list. **Never treat a doc example (e.g. 3.2.6) as latest.**

Edit `values.yaml`, then:

```bash
bash k8s-custom-install.sh install
kubectl get po -n kube-system
```

Stage gate: `loongcollector-ds` Running. Operator/controller is required only if the user later opts into CRD.

## Secrets

`values.yaml` needs `accessKeyID` / `accessKeySecret`. Do **not** ask the user to paste AK/SK in chat and do not print them. Use a path the user already configured (local file they name, existing Secret). If none exists, stop and ask them to place credentials outside the conversation.

`net`: `intranet` / `internet` / `accelerate` per the official table. Sidecar mode is out of scope.

## Reuse

- Project = `values.yaml` `projectName`
- Machine group = `k8s-group-${clusterID}`

Do not invent an extra IP group.

## Collection after install

**Default SLS API** is bound to the official group, as on ACK. CRD is allowed only when the user explicitly requests GitOps/CR management, the kube-apiserver is reachable, RBAC allows `ClusterAliyunPipelineConfig` creation, and the controller is running.

`kubectl` is required for **install**. After the collector is up, collection does not need a second kubeconfig ask. No `kubectl exec`.

## HITL

Use the fixed self-k8s install approval subject from `SKILL.md`, followed by `[AWAITING: INSTALL_CONFIRMATION]`.
Then the standard create-and-bind question when creating a CR or API config.
