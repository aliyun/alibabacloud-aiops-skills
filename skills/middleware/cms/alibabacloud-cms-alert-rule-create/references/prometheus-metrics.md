# Prometheus 指标参考

本文档包含容器和应用监控的常用 PromQL 模式及 ARMS Prometheus 指标。

## ARMS Prometheus 集群类型

| 集群类型 | 描述 | Cluster ID 格式 |
|----------|------|-----------------|
| 托管版 Prometheus | ARMS 全托管 Prometheus | `c<32位字母数字>` |
| 容器服务 | ACK Kubernetes 集群 | `c<32位字母数字>` |
| 自建接入 | 自建 Prometheus | 用户自定义 |

## 常用 PromQL 模式

### Kubernetes 节点指标

| 指标 | PromQL 表达式 | 描述 |
|------|---------------|------|
| CPU 使用率 | `100 - (avg by (instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` | 节点 CPU 使用百分比 |
| 内存使用率 | `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100` | 内存使用百分比 |
| 磁盘使用率 | `(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100` | 磁盘使用百分比 |
| 网络接收速率 | `irate(node_network_receive_bytes_total[5m])` | 网络接收速率 |
| 网络发送速率 | `irate(node_network_transmit_bytes_total[5m])` | 网络发送速率 |
| 系统负载 | `node_load1` / `node_load5` / `node_load15` | 系统平均负载 |

### Kubernetes Pod/容器指标

| 指标 | PromQL 表达式 | 描述 |
|------|---------------|------|
| 容器 CPU 使用率 | `rate(container_cpu_usage_seconds_total[5m])` | 容器 CPU 使用速率 |
| 容器内存使用量 | `container_memory_usage_bytes` | 容器内存使用量 |
| 容器重启 | `rate(kube_pod_container_status_restarts_total[10m])` | Pod 重启速率 |
| Pod 未就绪 | `kube_pod_status_ready{condition="false"}` | 未处于就绪状态的 Pod |
| OOM 被杀 | `kube_pod_container_status_terminated_reason{reason="OOMKilled"}` | 因 OOM 被终止的容器 |
| 镜像拉取错误 | `kube_pod_container_status_waiting_reason{reason="ImagePullBackOff"}` | 镜像拉取失败 |

### 应用性能指标（APM）

| 指标 | PromQL 表达式 | 描述 |
|------|---------------|------|
| 错误率 | `sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))` | HTTP 5xx 错误率 |
| 请求速率 | `sum(rate(http_requests_total[5m]))` | 每秒请求数 |
| P95 延迟 | `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 第 95 百分位延迟 |
| P99 延迟 | `histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))` | 第 99 百分位延迟 |
| 活跃连接数 | `sum(http_connections_active)` | 活跃 HTTP 连接数 |
| JVM 堆使用率 | `jvm_memory_used_bytes{area="heap"} / jvm_memory_max_bytes{area="heap"}` | JVM 堆内存使用比例 |
| GC 暂停时间 | `rate(jvm_gc_pause_seconds_sum[5m])` | GC 暂停时间速率 |

### 数据库指标

| 指标 | PromQL 表达式 | 描述 |
|------|---------------|------|
| MySQL 连接数 | `mysql_global_status_threads_connected` | MySQL 活跃连接数 |
| MySQL 慢查询 | `rate(mysql_global_status_slow_queries[5m])` | 慢查询速率 |
| Redis 内存使用率 | `redis_memory_used_bytes / redis_memory_max_bytes` | Redis 内存使用率 |
| Redis 连接数 | `redis_connected_clients` | Redis 客户端连接数 |

## PromQL 运算符参考

### 比较运算符

| 运算符 | 描述 | 示例 |
|--------|------|------|
| `==` | 等于 | `up == 1` |
| `!=` | 不等于 | `up != 1` |
| `>` | 大于 | `cpu_usage > 80` |
| `<` | 小于 | `free_memory < 1000000000` |
| `>=` | 大于等于 | `disk_usage >= 85` |
| `<=` | 小于等于 | `available_nodes <= 2` |

### 聚合运算符

| 运算符 | 描述 | 示例 |
|--------|------|------|
| `sum()` | 求和 | `sum(rate(http_requests_total[5m]))` |
| `avg()` | 平均值 | `avg(cpu_usage)` |
| `max()` | 最大值 | `max(memory_usage)` |
| `min()` | 最小值 | `min(disk_free)` |
| `count()` | 计数 | `count(up == 1)` |
| `rate()` | 每秒速率 | `rate(http_requests_total[5m])` |
| `irate()` | 瞬时速率 | `irate(cpu_seconds_total[5m])` |

### 时间范围

| 范围 | 描述 | 适用场景 |
|------|------|----------|
| `[1m]` | 1 分钟 | 高频指标 |
| `[5m]` | 5 分钟 | 标准评估窗口 |
| `[10m]` | 10 分钟 | 更平滑的趋势 |
| `[30m]` | 30 分钟 | 长期趋势 |
| `[1h]` | 1 小时 | 日常趋势 |

## 告警阈值建议

| 指标 | 警告阈值 | 紧急阈值 | 原因 |
|------|----------|----------|------|
| CPU 使用率 | 70% | 85% | 为突发峰值预留空间 |
| 内存使用率 | 75% | 90% | 防止 OOM 终止 |
| 磁盘使用率 | 80% | 90% | 预留清理时间 |
| 错误率 | 1% | 5% | 平衡灵敏度 |
| P95 延迟 | 500ms | 1000ms | 用户体验阈值 |
| Pod 重启 | 0.1 次/分 | 0.5 次/分 | 崩溃循环检测 |

## 常用标签选择器

| 标签 | 描述 | 示例 |
|------|------|------|
| `instance` | 目标实例 | `instance="192.168.1.1:9100"` |
| `job` | 采集任务名称 | `job="kubernetes-nodes"` |
| `namespace` | K8s namespace | `namespace="production"` |
| `pod` | Pod 名称 | `pod="nginx-7d4c7b8c5-x2v9p"` |
| `container` | 容器名称 | `container="nginx"` |
| `status` | HTTP 状态码 | `status=~"5.."` |

## 持续时间参数指南

Prometheus 规则中的 `duration` 参数指定条件必须持续多长时间才会触发告警：

| 持续时间 | 适用场景 |
|----------|----------|
| `60s` | 快速响应型告警（高 CPU、内存） |
| `300s`（5 分钟） | 标准告警（错误率、延迟） |
| `600s`（10 分钟） | 趋势类告警（磁盘增长） |
| `900s`（15 分钟） | 稳定性告警（Pod 健康状态） |

## 注解最佳实践

在 Prometheus 告警中建议包含以下标准注解：

| 注解 | 用途 | 示例 |
|------|------|------|
| `message` | 人类可读的告警描述 | "CPU usage is above 80%" |
| `runbook_url` | 故障处理手册链接 | "https://wiki/runbooks/high-cpu" |
| `severity` | 告警严重级别 | "critical" |
| `team` | 负责团队 | "platform" |
