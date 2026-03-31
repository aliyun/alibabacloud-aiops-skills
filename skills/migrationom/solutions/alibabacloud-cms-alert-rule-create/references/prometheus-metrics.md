# Prometheus Metrics Reference

This document contains common PromQL patterns and ARMS Prometheus metrics for container and application monitoring.

## ARMS Prometheus Cluster Types

| Cluster Type | Description | Cluster ID Format |
|--------------|-------------|-------------------|
| Managed Prometheus | ARMS fully managed Prometheus | `c<32-char-alphanumeric>` |
| Container Service | ACK Kubernetes cluster | `c<32-char-alphanumeric>` |
| External | Self-hosted Prometheus | User-defined |

## Common PromQL Patterns

### Kubernetes Node Metrics

| Metric | PromQL Expression | Description |
|--------|-------------------|-------------|
| CPU Usage | `100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` | Node CPU usage percentage |
| Memory Usage | `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100` | Memory usage percentage |
| Disk Usage | `(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100` | Disk usage percentage |
| Network Receive Rate | `irate(node_network_receive_bytes_total[5m])` | Network receive rate |
| Network Transmit Rate | `irate(node_network_transmit_bytes_total[5m])` | Network transmit rate |
| Load Average | `node_load1` / `node_load5` / `node_load15` | System load average |

### Kubernetes Pod/Container Metrics

| Metric | PromQL Expression | Description |
|--------|-------------------|-------------|
| Container CPU Usage | `rate(container_cpu_usage_seconds_total[5m])` | Container CPU usage rate |
| Container Memory Usage | `container_memory_usage_bytes` | Container memory usage |
| Container Restarts | `rate(kube_pod_container_status_restarts_total[10m])` | Pod restart rate |
| Pod Not Ready | `kube_pod_status_ready{condition="false"}` | Pods not in ready state |
| OOM Killed | `kube_pod_container_status_terminated_reason{reason="OOMKilled"}` | OOM killed containers |
| Image Pull Errors | `kube_pod_container_status_waiting_reason{reason="ImagePullBackOff"}` | Image pull failures |

### Application Performance Metrics (APM)

| Metric | PromQL Expression | Description |
|--------|-------------------|-------------|
| Error Rate | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | HTTP 5xx error rate |
| Request Rate | `sum(rate(http_requests_total[5m]))` | Requests per second |
| P95 Latency | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 95th percentile latency |
| P99 Latency | `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 99th percentile latency |
| Active Connections | `sum(http_connections_active)` | Active HTTP connections |
| JVM Heap Usage | `jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}` | JVM heap usage ratio |
| GC Pause Time | `rate(jvm_gc_pause_seconds_sum[5m])` | GC pause time rate |

### Database Metrics

| Metric | PromQL Expression | Description |
|--------|-------------------|-------------|
| MySQL Connections | `mysql_global_status_threads_connected` | MySQL active connections |
| MySQL Slow Queries | `rate(mysql_global_status_slow_queries[5m])` | Slow query rate |
| Redis Memory Usage | `redis_memory_used_bytes / redis_memory_max_bytes` | Redis memory usage |
| Redis Connections | `redis_connected_clients` | Redis client connections |

## PromQL Operators Reference

### Comparison Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equal | `up == 1` |
| `!=` | Not equal | `up != 1` |
| `>` | Greater than | `cpu_usage > 80` |
| `<` | Less than | `free_memory < 1000000000` |
| `>=` | Greater than or equal | `disk_usage >= 85` |
| `<=` | Less than or equal | `available_nodes <= 2` |

### Aggregation Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `sum()` | Sum of values | `sum(rate(http_requests_total[5m]))` |
| `avg()` | Average of values | `avg(cpu_usage)` |
| `max()` | Maximum value | `max(memory_usage)` |
| `min()` | Minimum value | `min(disk_free)` |
| `count()` | Count of series | `count(up == 1)` |
| `rate()` | Per-second rate | `rate(http_requests_total[5m])` |
| `irate()` | Instant rate | `irate(cpu_seconds_total[5m])` |

### Time Ranges

| Range | Description | Use Case |
|-------|-------------|----------|
| `[1m]` | 1 minute | High-frequency metrics |
| `[5m]` | 5 minutes | Standard evaluation window |
| `[10m]` | 10 minutes | Smoother trends |
| `[30m]` | 30 minutes | Long-term patterns |
| `[1h]` | 1 hour | Daily patterns |

## Alert Threshold Recommendations

| Metric | Warning Threshold | Critical Threshold | Rationale |
|--------|-------------------|-------------------|-----------|
| CPU Usage | 70% | 85% | Leave headroom for spikes |
| Memory Usage | 75% | 90% | Prevent OOM kills |
| Disk Usage | 80% | 90% | Allow time for cleanup |
| Error Rate | 1% | 5% | Balance sensitivity |
| P95 Latency | 500ms | 1000ms | User experience threshold |
| Pod Restarts | 0.1/min | 0.5/min | Crash loop detection |

## Common Label Selectors

| Label | Description | Example |
|-------|-------------|---------|
| `instance` | Target instance | `instance="192.168.1.1:9100"` |
| `job` | Scraping job name | `job="kubernetes-nodes"` |
| `namespace` | K8s namespace | `namespace="production"` |
| `pod` | Pod name | `pod="nginx-7d4c7b8c5-x2v9p"` |
| `container` | Container name | `container="nginx"` |
| `status` | HTTP status code | `status=~"5.."` |

## Duration Parameter Guidelines

The `duration` parameter in Prometheus rules specifies how long a condition must persist before triggering an alert:

| Duration | Use Case |
|----------|----------|
| `60s` | Fast-reacting alerts (high CPU, memory) |
| `300s` (5m) | Standard alerts (error rates, latency) |
| `600s` (10m) | Trend-based alerts (disk growth) |
| `900s` (15m) | Stability-focused alerts (pod health) |

## Annotations Best Practices

Include these standard annotations in Prometheus alerts:

| Annotation | Purpose | Example |
|------------|---------|---------|
| `message` | Human-readable alert description | "CPU usage is above 80%" |
| `runbook_url` | Link to remediation guide | "https://wiki/runbooks/high-cpu" |
| `severity` | Alert severity level | "critical" |
| `team` | Responsible team | "platform" |
