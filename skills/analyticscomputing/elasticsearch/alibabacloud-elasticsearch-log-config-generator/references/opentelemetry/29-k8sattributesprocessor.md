# k8sattributes processor

> Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/k8sattributesprocessor/README.md
>
> Watches the K8s API and decorates resource attributes on logs/metrics/traces with pod/namespace/workload metadata.

## Authentication

| Field | Default | Description |
|---|---|---|
| `auth_type` | `serviceAccount` | `serviceAccount`, `kubeConfig`, or `none`. |
| `context` | — | Kubeconfig context (only with `kubeConfig`). |
| `passthrough` | `false` | Skip K8s API; only forward pod IP. Use on agent → gateway pattern. |

## Default extracted metadata

- `k8s.namespace.name`
- `k8s.pod.name`
- `k8s.pod.uid`
- `k8s.pod.start_time`
- `k8s.deployment.name`
- `k8s.node.name`

Additional optional fields (opt-in via `extract.metadata`):

`k8s.pod.ip`, `k8s.pod.hostname`, `k8s.replicaset.*`, `k8s.daemonset.*`, `k8s.statefulset.*`, `k8s.job.*`, `k8s.cronjob.*`, `k8s.cluster.uid`, `container.id`, `container.image.name`, `container.image.tag`, `service.name`, `service.namespace`, `service.version`, `service.instance.id`.

## pod_association

Rules evaluated in order; first match wins. Up to 4 sources per rule.

Source types:

- `connection` — uses incoming request IP (gRPC/HTTP).
- `resource_attribute` — match attribute name (e.g., `k8s.pod.ip`, `k8s.pod.uid`).

If `pod_association` is omitted, association falls back to connection IP.

## Typical YAML

```yaml
processors:
  k8sattributes:
    auth_type: serviceAccount
    passthrough: false
    filter:
      node_from_env_var: KUBE_NODE_NAME    # downward API: only watch this node
    extract:
      metadata:
        - k8s.namespace.name
        - k8s.pod.name
        - k8s.pod.uid
        - k8s.pod.start_time
        - k8s.deployment.name
        - k8s.node.name
        - service.name
        - service.version
      annotations:
        - tag_name: commit_sha
          key: git-commit
          from: pod
      labels:
        - tag_name: app.label.component
          key: app.kubernetes.io/component
          from: pod
      otel_annotations: true
    pod_association:
      - sources:
          - from: resource_attribute
            name: k8s.pod.ip
      - sources:
          - from: resource_attribute
            name: k8s.pod.uid
      - sources:
          - from: connection
    exclude:
      pods:
        - name: jaeger-agent
        - name: jaeger-collector
```

Required env var for node filtering:

```yaml
env:
  - name: KUBE_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
```

## RBAC

Cluster-scoped: `get`, `watch`, `list` on `pods`, `namespaces`. Plus:

- `replicasets` (when extracting deployment data via RS)
- `nodes` (when extracting node metadata or `k8s.node.uid`)
- `jobs` (when extracting cronjob/job data)

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: collector
  namespace: <OTEL_COL_NAMESPACE>
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: otel-collector
rules:
- apiGroups: [""]
  resources: ["pods", "namespaces", "nodes"]
  verbs: ["get", "watch", "list"]
- apiGroups: ["apps"]
  resources: ["replicasets", "deployments", "statefulsets", "daemonsets"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["batch"]
  resources: ["jobs"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["extensions"]
  resources: ["replicasets"]
  verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: otel-collector
subjects:
- kind: ServiceAccount
  name: collector
  namespace: <OTEL_COL_NAMESPACE>
roleRef:
  kind: ClusterRole
  name: otel-collector
  apiGroup: rbac.authorization.k8s.io
```

For namespace-scoped RBAC, swap to `Role`/`RoleBinding` and set `filter.namespace` — but `k8s.cluster.uid` won't resolve.

## Caveats

- **Memory**: each watched pod is cached. On agent deployments, *always* filter to the local node.
- **`hostNetwork: true`** pods can't be matched by IP.
- **Sidecar deployment is unsupported** — use the K8s downward API instead.
