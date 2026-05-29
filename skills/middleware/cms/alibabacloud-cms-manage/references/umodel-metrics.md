# UModel Metric Catalog (K8s Pod)

> Companion to [alerting.md](alerting.md). Use this table for `aliyun cms2 alert rule create` with `datasourceConfig.type=UMODEL`.
>
> **Lookup flow**: user describes the metric (e.g. "Pod memory usage") → look it up by Chinese display name → fill `metricSet` + `metric` in `queryConfig`. ✅ marks verified IDs; the rest are inferred (on failure, retry with a similar metric in the same metricSet — max 3 attempts).

## metricSet 1: `k8s.metric.high_level_metric_pod`

Source: cAdvisor. Resource usage / network throughput / health alerts.

| Display Name (zh-CN) | metric ID | Unit | Status |
|----------------------|-----------|------|--------|
| Pod CPU 使用率 | `pod_cpu_usage` | % | inferred |
| Pod CPU 使用率 / Request | `pod_cpu_usage_against_request` | % | inferred |
| Pod CPU 使用率 / Limit | `pod_cpu_usage_against_limit` | % | inferred |
| Pod 内存使用量 | `pod_memory_usage` | bytes | inferred |
| Pod 内存工作集 | `pod_memory_working_set` | bytes | inferred |
| Pod 内存使用率 / Request | `pod_memory_usage_against_request` | % | inferred |
| Pod 内存使用率 / Limit | `pod_memory_usage_against_limit` | % | inferred |
| Pod 网络接收速率 | `pod_network_rx_rate` | bytes/s | inferred |
| Pod 网络发送速率 | `pod_network_tx_rate` | bytes/s | inferred |
| Pod 网络总 IO 速率 | `pod_network_io_rate` | bytes/s | inferred |
| Pod 文件系统使用量 | `pod_filesystem_usage` | bytes | inferred |
| Pod 文件系统使用率 | `pod_filesystem_usage_rate` | % | inferred |
| Pod 重启次数 | `pod_restart_count` | count | inferred |

## metricSet 2: `k8s.metric.pod_status` (unverified)

Source: kube-state-metrics + cAdvisor. Lifecycle / scheduling / container-status alerts.

Resource requests/limits: `kube_pod_container_resource_requests_memory_bytes` `kube_pod_container_resource_limits_memory_bytes` `kube_pod_container_resource_requests_cpu_cores` `kube_pod_container_resource_limits_cpu_cores` `kube_pod_container_resource_requests` `kube_pod_container_resource_limits`

Container status: `kube_pod_container_status_running` `kube_pod_container_status_waiting` `kube_pod_container_status_terminated` `kube_pod_container_status_terminated_reason` `kube_pod_container_status_ready` `kube_pod_container_status_ready_time` `kube_pod_container_status_restarts_total` `kube_pod_container_info`

Pod lifecycle: `kube_pod_created` `kube_pod_completion_time` `kube_pod_start_time` `kube_pod_status_ready_time` `kube_pod_status_ready` `kube_pod_status_reason` `kube_pod_status_phase` `kube_pod_status_scheduled_time` `kube_pod_init_container_status_ready_time`

Metadata: `kube_pod_owner` `kube_pod_labels` `kube_pod_info`

Ephemeral storage: `kube_pod_ephemeral_storage_capacity_bytes` `kube_pod_ephemeral_storage_used_bytes` `kube_pod_ephemeral_storage_available` `kube_pod_ephemeral_storage_inodes` `kube_pod_ephemeral_storage_inodes_used` `kube_pod_ephemeral_storage_inodes_free`

Container resources (raw cAdvisor): `container_memory_rss` `container_memory_cache` `container_memory_working_set_bytes` `container_fs_writes_bytes_total` `container_cpu_cfs_throttled_seconds_total` `container_network_receive_bytes_total` `container_network_transmit_bytes_total`

---

## Validation & Recommendation Workflow (MANDATORY)

Before creating a UModel alert:

1. **Look up** the user description in the Chinese display-name column above.
2. **Hit** → fill `metricSet` + `metric` ID, proceed with CREATE.
3. **Miss** → do not create blindly. List the top-3 closest semantic matches and call `ask_user_question` to confirm:
   - "usage rate" → `pod_cpu_usage` / `pod_memory_usage_against_limit`
   - "restart" → `pod_restart_count` / `kube_pod_container_status_restarts_total`
   - "status / lifecycle" → `kube_pod_status_phase` / `kube_pod_status_reason`
   - "OOM" → `kube_pod_container_status_terminated_reason` (reason = `OOMKilled`)
4. **Verify inferred IDs** (back-fill this table after a successful CREATE):

```bash
aliyun cms2 alert rule list --workspace <workspace> -o json \
  | jq '.data.data.alertRules[] | select(.queryConfig.type=="UMODEL_METRICSET_QUERY")
        | {name: .displayName, metricSet: .queryConfig.metricSet, metric: .queryConfig.metric}'
```

5. **Fallback**: if an inferred ID returns 400/500 on CREATE, or the console shows "no data", swap it for a similar metric in the same metricSet — **max 3 retries**. Beyond that, ask the user to copy the exact ID from the console.
