# 常用指标快速参考（回退备用）

> **首选方式**：使用 `aliyun cms describe-metric-meta-list --namespace <ns>` 动态发现指标。
> 本文件作为 API 调用失败时或快速离线查阅的**回退参考**。

---

## ECS (acs_ecs_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| CPUUtilization | CPU 利用率 | % | Average | > 85-95% |
| memory_usedutilization | 内存利用率（需安装 Agent） | % | Average | > 85-95% |
| diskusage_utilization | 磁盘使用率（需安装 Agent） | % | Average | > 85-95% |
| InternetOutRate_Percent | 出方向带宽使用率 | % | Average | > 80-95% |
| packetOutDropRates | 出方向丢包率 | % | Maximum | > 1-5% |
| packetInDropRates | 入方向丢包率 | % | Maximum | > 1-5% |

---

## RDS MySQL (acs_rds_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| CpuUsage | CPU 使用率 | % | Average | > 80-90% |
| DiskUsage | 磁盘使用率 | % | Average | > 80-85% |
| MemoryUsage | 内存使用率 | % | Average | > 80-90% |
| ConnectionUsage | 连接数使用率 | % | Average | > 70-80% |
| IOPSUsage | IOPS 使用率 | % | Average | > 70-80% |
| DataDelay | 只读副本数据延迟 | s | Average | > 30-60s |
| MySQL_IbufReadHit | InnoDB 缓冲池命中率 | % | Average | < 95% |

---

## RDS PostgreSQL (acs_rds_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| cpu_usage | CPU 使用率 | % | Average | > 80-90% |
| iops_usage | IOPS 使用率 | % | Average | > 70-80% |
| local_fs_size_usage | 本地磁盘使用率 | % | Average | > 80-85% |
| conn_usgae | 连接数使用率 | % | Average | > 70-80% |
| PG_RO_ReadLag | 只读实例延迟 | s | Average | > 10-30s |

---

## SQL Server (acs_rds_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| SQLServer_CpuUsage | CPU 使用率 | % | Average | > 80-90% |
| SQLServer_DiskUsage | 磁盘使用率 | % | Average | > 80-85% |
| SQLServer_MemoryUsage | 内存使用率 | % | Average | > 80-90% |

---

## RDS 集群 (acs_rds_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| Cluster_CpuUsage | 集群 CPU 使用率 | % | Average | > 80-90% |
| Cluster_MemoryUsage | 集群内存使用率 | % | Average | > 80-90% |
| Cluster_IOPSUsage | 集群 IOPS 使用率 | % | Average | > 70-80% |

---

## SLB (acs_slb_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| DropConnection | 丢弃连接数 | count/s | Average | > 0 |
| DropTrafficRX | 丢弃入方向流量 | bit/s | Average | > 0 |
| DropTrafficTX | 丢弃出方向流量 | bit/s | Average | > 0 |
| HeathyServerCount | 健康后端服务器数 | count | Average | < 预期值 |
| UnhealthyServerCount | 不健康后端服务器数 | count | Average | > 0 |

---

## OSS (acs_oss_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| Availability | 服务可用性 | % | **Value** | < 99.9% |
| RequestValidRate | 有效请求率 | % | Value | < 99% |
| TotalRequestCount | 总请求数 | count | Value | 视业务而定 |

**注意**：使用 `--resources '[{"resource":"_ALL"}]'` 可监控某地域下所有 Bucket。

---

## MongoDB (acs_mongodb)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| CPUUtilization | CPU 利用率（副本集） | % | Average | > 80% |
| MemoryUtilization | 内存利用率 | % | Average | > 80% |
| DiskUtilization | 磁盘利用率 | % | Average | > 80% |
| IOPSUtilization | IOPS 利用率 | % | Average | > 70-80% |
| ConnectionUtilization | 连接数利用率 | % | Average | > 70-80% |
| ShardingCPUUtilization | 分片集群 CPU 利用率 | % | Average | > 80% |
| ShardingDiskUtilization | 分片集群磁盘利用率 | % | Average | > 80% |

---

## Redis (acs_kvstore)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| StandardCpuUsage | 标准版 CPU 使用率 | % | Average | > 80% |
| StandardMemoryUsage | 标准版内存使用率 | % | Average | > 80% |
| StandardConnectionUsage | 标准版连接数使用率 | % | Average | > 70-80% |
| ShardingCpuUsage | 集群版 CPU 使用率 | % | Average | > 80% |
| ShardingMemoryUsage | 集群版内存使用率 | % | Average | > 80% |

---

## PolarDB (acs_polardb)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| cluster_cpu_utilization | MySQL 集群 CPU 利用率 | % | Average | > 80% |
| cluster_memory_utilization | MySQL 集群内存利用率 | % | Average | > 80% |
| pg_cpu_total | PostgreSQL CPU 使用率 | % | Average | > 80% |
| pg_conn_usage | PostgreSQL 连接数使用率 | % | Average | > 70-80% |
| oracle_cpu_total | Oracle CPU 使用率 | % | Average | > 80% |

---

## Elasticsearch (acs_elasticsearch)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| ClusterStatus | 集群健康状态（0=green，1=yellow，2=red） | value | **Value** | >= 2 |
| NodeDiskUtilization | 节点磁盘利用率 | % | Average | > 75-85% |
| NodeHeapMemoryUtilization | 节点堆内存利用率 | % | Average | > 80% |

---

## Hologres (acs_hologres)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| cpu_usage | CPU 使用率 | % | Average | > 90-99% |
| memory_usage | 内存使用率 | % | Average | > 85-90% |
| storage_usage_percent | 存储使用率 | % | Average | > 80% |
| connection_usage | 连接数使用率 | % | Average | > 70-80% |

---

## NAT 网关 (acs_nat_gateway)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| SnatConnection | SNAT 连接数 | count | Average | 视业务而定 |
| SessionNewLimitDropConnection | 新建会话丢弃数 | count | Average | > 0-3 |
| SessionActiveConnectionWaterLever | 活跃连接水位 | % | Average | > 80-90% |

---

## EIP (acs_vpc_eip)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| net_rx.rate | 入方向带宽 | bytes/s | Average | 接近带宽上限 |
| net_tx.rate | 出方向带宽 | bytes/s | Average | 接近带宽上限 |
| out_ratelimit_drop_speed | 限速丢包速率 | packets/s | Average | > 0 |

---

## OceanBase (acs_oceanbase)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| cpu_util_instance | 实例 CPU 利用率 | % | Average | > 90-95% |
| disk_ob_data_usage_instance | OB 数据盘使用率 | % | Average | > 85-88% |
| memory_used_percent_instance | 实例内存使用率 | % | Average | > 80-90% |

---

## DRDS (acs_drds)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| CPUUsageOfCN | 计算节点 CPU 使用率 | % | Average | > 85-90% |
| DiskUsageOfDN | 数据节点磁盘使用率 | % | Average | > 85-90% |
| ConnUsageOfDN | 数据节点连接数使用率 | % | Average | > 70-80% |

---

## GPDB / AnalyticDB PostgreSQL (acs_hybriddb)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| adbpg_query_blocked | 查询阻塞数 | count | Average | > 0 |
| node_mem_used_percent | 节点内存使用率 | % | Average | > 80-85% |
| node_cpu_used_percent | 节点 CPU 使用率 | % | Average | > 80-85% |

---

## HBase (acs_hbase)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| LoadPerCpu | 每 CPU 负载 | value | Average | > 2-3 |
| cpu_idle | CPU 空闲百分比 | % | Average | < 15-20% |
| CapacityUsedPercent | 存储容量使用率 | % | Average | > 75-80% |

---

## RocketMQ (acs_rocketmq)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| ThrottledReceiveRequestsPerGid | 每 GID 被限流的接收请求数 | count | Average | >= 1 |
| MessageAccumulation | 消息堆积量 | count | Average | 视业务而定 |
| ConsumerLag | 消费延迟 | count | Average | 视业务而定 |

---

## KMS (acs_kms)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| code_5xx_1m | 每分钟服务端错误（5xx） | count | Sum | > 0 |
| code_4xx_1m | 每分钟客户端错误（4xx） | count | Sum | 视业务而定 |
| latency_1m | 每分钟请求延迟 | ms | Average | > 3000-5000ms |

---

## SWAS / 轻量应用服务器 (acs_swas)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| CPUUtilization | CPU 利用率 | % | Average | > 85-90% |
| MemoryUtilization | 内存利用率 | % | Average | > 85-90% |
| DiskUtilization | 磁盘利用率 | % | Average | > 80-85% |

---

## Serverless 应用引擎 (acs_serverless)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| cpu | CPU 使用率 | % | Average | > 90-95% |
| memoryPercent | 内存使用率 | % | Average | > 90-95% |

---

## EMR (acs_emr)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| serverless_starrocks_be_cpu_idle | StarRocks BE CPU 空闲率 | % | Average | < 10-15% |
| serverless_starrocks_be_disks_utilization | StarRocks BE 磁盘利用率 | % | Average | > 80% |

---

## CloudBox (acs_cloudbox)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| idc_rack_temperature | 机柜温度 | °C | Average | > 30°C 或 < 5°C |
| ebs_capacity_utilization | EBS 容量利用率 | % | Average | > 80% |

---

## IoT (acs_iot)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| MessageWatermarkTps_instance | 消息 TPS 水位 | % | Average | > 85-90% |
| OnlineDeviceCount | 在线设备数 | count | Value | 视业务而定 |

---

## HSM (acs_hsm)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| Hsmhealthy | HSM 健康状态（1=健康，0=不健康） | value | Value | == 0 |
| CPUUtilization | CPU 利用率 | % | Average | > 80-85% |

---

## Milvus (acs_milvus)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| ProcessCPUUtilizationV2 | 进程 CPU 利用率 | % | Average | > 85-90% |
| ProcessResidentMemoryUtilizationV2 | 进程内存利用率 | % | Average | > 80% |

---

## OpenSearch (acs_opensearch)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| DocSizeRatiobyApp | 文档存储使用率 | % | Average | > 80-85% |
| LossQPSbyApp | 应用丢失 QPS | count | Sum | > 0 |

---

## HBR / 混合云备份 (acs_hbr)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| hw_appliance_disk_used_percent | 一体机磁盘使用率 | % | Average | > 80-85% |

---

## CEN / 云企业网 (acs_cen)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| InternetOutRatePercentByConnectionRegion | 跨地域带宽使用率 | % | Average | > 75-80% |

---

## 共享带宽 (acs_bandwidth_package)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| net_tx.ratePercent | 出方向带宽使用率 | % | Average | > 80% |
| net_rx.ratePercent | 入方向带宽使用率 | % | Average | > 80% |

---

## SLS 日志服务 (acs_sls_dashboard)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| ConsumerGroupFallBehind | 消费组落后时间 | s | Average | > 300-600s |
| LogInflow | 日志写入流量 | bytes/s | Average | 视业务而定 |

---

## E-HPC (acs_ehpc)

| MetricName | 描述 | 单位 | Statistics | 典型阈值 |
|------------|------|------|------------|----------|
| cluster_cpu_utilization | 集群 CPU 利用率 | % | Average | > 80-90% |
| cluster_memory_utilization | 集群内存利用率 | % | Average | > 80-90% |

---

## 说明

- 以上仅为可用指标的**子集**。请使用 `describe-metric-meta-list` API 获取完整列表。
- 阈值为参考值，请根据实际工作负载和 SLA 要求进行调整。
- 部分指标需要安装云监控 Agent（如 ECS 内存、磁盘指标）。
- Statistics 列显示最常用的聚合方式。部分指标支持多种聚合方式（Average、Maximum、Minimum、Value、Sum）。
- 对于集群/分片类产品，请使用对应的指标变体（如 MongoDB 分片使用 `ShardingCPUUtilization`，Redis 标准版使用 `StandardCpuUsage`）。
