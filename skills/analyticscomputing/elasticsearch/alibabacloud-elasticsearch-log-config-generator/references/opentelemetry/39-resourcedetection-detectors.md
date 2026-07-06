# resourcedetection — per-detector options

> Companion to `08-resourcedetectionprocessor.md`. Source: https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/processor/resourcedetectionprocessor/README.md
>
> Each detector exposes its own option block. The cross-cutting fields (`detectors`, `override`, `timeout`, `refresh_interval`) are documented in `08-…`.

> Every detector also accepts a `resource_attributes:` map of `<attr>.enabled: bool` toggles to opt fields in/out of the produced Resource. Per-detector default-enabled lists live in the upstream `internal/<detector>/documentation.md` files.

## env

- No detector-specific options.
- Reads `OTEL_RESOURCE_ATTRIBUTES` (`k1=v1,k2=v2,…`) and `OTEL_SERVICE_NAME`.

## ec2

| Field | Default | Notes |
|---|---|---|
| `tags` | `[]` | Regex patterns; matching EC2 tag keys are emitted as resource attributes. |
| `tags_from_imds` | `false` | `true` fetches tags via IMDS (no IAM permissions needed; instance must have `InstanceMetadataTags=enabled`). |
| `max_attempts` | `3` | IMDS retry count. |
| `max_backoff` | `20s` | Retry backoff. |
| `fail_on_missing_metadata` | `false` | Without it, missing IMDS only logs an error. |

## eks

| Field | Default | Notes |
|---|---|---|
| `node_from_env_var` | — | Env var holding the node name (used in IMDS-fallback for cluster name). |
| `resource_attributes.k8s.cluster.name.enabled` | `false` | Requires `EC2:DescribeInstances` IAM permission on a node-attached EC2 role. |

## aks

| Field | Default | Notes |
|---|---|---|
| `resource_attributes.k8s.cluster.name.enabled` | `false` | Cluster name parsed from IMDS infrastructure resource group field (`MC_<rg>_<cluster>_<location>`). |

## k8snode

| Field | Default | Notes |
|---|---|---|
| `auth_type` | `serviceAccount` | Or `none`, `kubeConfig`. |
| `node_from_env_var` | `K8S_NODE_NAME` | Env var with the node name; populate from downward API `spec.nodeName`. |

## kubeadm

| Field | Default | Notes |
|---|---|---|
| `auth_type` | `serviceAccount` | Or `none`, `kubeConfig`. |

RBAC: `get` on the `kubeadm-config` ConfigMap in `kube-system`. Attribute set: cluster.name from kubeadm.

## gcp

| Field | Default | Notes |
|---|---|---|
| `labels` | `[]` | Regex patterns matching GCE instance label keys to lift as attributes. Requires `roles/compute.viewer` on the instance's service account. |

Auto-detects platform: GCE / GKE / Cloud Run Service / Cloud Run Job / Cloud Functions / App Engine.

## azure

| Field | Default | Notes |
|---|---|---|
| `tags` | `[]` | Regex patterns; matched Azure tag keys are emitted as `azure.tags.<key>`. |

## docker

- No detector-specific options.
- Requires the Docker socket mounted into the collector. Not supported on macOS.

## openshift

| Field | Default | Notes |
|---|---|---|
| `address` | `KUBERNETES_SERVICE_HOST:PORT` | API server URL. |
| `token` | in-pod SA token | Bearer token. |
| `tls.insecure` | `false` | Skip server cert verification. |
| `tls.ca_file` | in-pod SA CA when TLS on | CA bundle. |

RBAC: `get/watch/list` on `infrastructures` and `infrastructures/status` (`config.openshift.io`).

## heroku

- No detector-specific options. Mapping of dyno env vars:

| Env var | Resource attribute |
|---|---|
| `HEROKU_APP_ID` | `heroku.app.id` |
| `HEROKU_APP_NAME` | `service.name` |
| `HEROKU_DYNO_ID` | `service.instance.id` |
| `HEROKU_RELEASE_CREATED_AT` | `heroku.release.creation_timestamp` |
| `HEROKU_RELEASE_VERSION` | `service.version` |
| `HEROKU_SLUG_COMMIT` | `heroku.release.commit` |

## Stacked AWS-on-K8s example

```yaml
processors:
  resourcedetection/aws_k8s:
    detectors: [env, eks, ec2, k8snode]
    timeout: 15s
    override: false
    refresh_interval: 5m

    ec2:
      tags: ["^Name$", "^env$", "^team-.*$"]
      tags_from_imds: false
      max_attempts: 5
      resource_attributes:
        host.name: { enabled: false }   # let k8snode/eks own host.name
        host.id:   { enabled: true }

    eks:
      node_from_env_var: K8S_NODE_NAME
      resource_attributes:
        k8s.cluster.name: { enabled: true }

    k8snode:
      auth_type: serviceAccount
      node_from_env_var: K8S_NODE_NAME
```

Pair with the workload's downward API:

```yaml
env:
  - name: K8S_NODE_NAME
    valueFrom:
      fieldRef:
        fieldPath: spec.nodeName
```

## Conflict resolution

When multiple detectors emit the same attribute, **the first to set it wins** (override at the processor level controls whether *the workload's* existing Resource is replaced — see `08-…`).
