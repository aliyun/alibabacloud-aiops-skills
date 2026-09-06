# CRD templates

`ClusterAliyunPipelineConfig` only — **opt-in** when the user asks for GitOps/CR. Default K8s collection is SLS API (`assets/pipeline-templates/`).
Replace `<cluster_id>` and filters before apply. Render from task JSON with `scripts/render_crd.py`.

| File | Scenario |
|---|---|
| `k8s_stdio.yaml` | K8s stdout → official `k8s-group-<cluster_id>` |
