# Common Metrics Quick Reference (Fallback)

> **Primary method**: Use `aliyun cms describe-metric-meta-list --namespace <ns>` to dynamically discover metrics.
> This file serves as a **fallback reference** when the API call fails or for quick offline lookup.

---

## ECS (acs_ecs_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| CPUUtilization | CPU utilization | % | Average | > 85-95% |
| memory_usedutilization | Memory utilization (Agent required) | % | Average | > 85-95% |
| diskusage_utilization | Disk usage (Agent required) | % | Average | > 85-95% |
| InternetOutRate_Percent | Outbound bandwidth usage | % | Average | > 80-95% |
| packetOutDropRates | Outbound packet drop rate | % | Maximum | > 1-5% |
| packetInDropRates | Inbound packet drop rate | % | Maximum | > 1-5% |

---

## RDS MySQL (acs_rds_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| CpuUsage | CPU usage | % | Average | > 80-90% |
| DiskUsage | Disk usage | % | Average | > 80-85% |
| MemoryUsage | Memory usage | % | Average | > 80-90% |
| ConnectionUsage | Connection usage | % | Average | > 70-80% |
| IOPSUsage | IOPS usage | % | Average | > 70-80% |
| DataDelay | Read replica data delay | s | Average | > 30-60s |
| MySQL_IbufReadHit | InnoDB buffer pool hit rate | % | Average | < 95% |

---

## RDS PostgreSQL (acs_rds_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| cpu_usage | CPU usage | % | Average | > 80-90% |
| iops_usage | IOPS usage | % | Average | > 70-80% |
| local_fs_size_usage | Local disk usage | % | Average | > 80-85% |
| conn_usgae | Connection usage | % | Average | > 70-80% |
| PG_RO_ReadLag | Read-only instance lag | s | Average | > 10-30s |

---

## SQL Server (acs_rds_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| SQLServer_CpuUsage | CPU usage | % | Average | > 80-90% |
| SQLServer_DiskUsage | Disk usage | % | Average | > 80-85% |
| SQLServer_MemoryUsage | Memory usage | % | Average | > 80-90% |

---

## RDS Cluster (acs_rds_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| Cluster_CpuUsage | Cluster CPU usage | % | Average | > 80-90% |
| Cluster_MemoryUsage | Cluster memory usage | % | Average | > 80-90% |
| Cluster_IOPSUsage | Cluster IOPS usage | % | Average | > 70-80% |

---

## SLB (acs_slb_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| DropConnection | Dropped connections | count/s | Average | > 0 |
| DropTrafficRX | Dropped inbound traffic | bit/s | Average | > 0 |
| DropTrafficTX | Dropped outbound traffic | bit/s | Average | > 0 |
| HeathyServerCount | Healthy backend server count | count | Average | < expected |
| UnhealthyServerCount | Unhealthy backend server count | count | Average | > 0 |

---

## OSS (acs_oss_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| Availability | Service availability | % | **Value** | < 99.9% |
| RequestValidRate | Valid request rate | % | Value | < 99% |
| TotalRequestCount | Total request count | count | Value | Business-dependent |

**Note**: Use `--resources '[{"resource":"_ALL"}]'` to monitor all buckets in a region.

---

## MongoDB (acs_mongodb)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| CPUUtilization | CPU utilization (replica set) | % | Average | > 80% |
| MemoryUtilization | Memory utilization | % | Average | > 80% |
| DiskUtilization | Disk utilization | % | Average | > 80% |
| IOPSUtilization | IOPS utilization | % | Average | > 70-80% |
| ConnectionUtilization | Connection utilization | % | Average | > 70-80% |
| ShardingCPUUtilization | Sharding CPU utilization | % | Average | > 80% |
| ShardingDiskUtilization | Sharding disk utilization | % | Average | > 80% |

---

## Redis (acs_kvstore)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| StandardCpuUsage | Standard edition CPU usage | % | Average | > 80% |
| StandardMemoryUsage | Standard edition memory usage | % | Average | > 80% |
| StandardConnectionUsage | Standard edition connection usage | % | Average | > 70-80% |
| ShardingCpuUsage | Cluster edition CPU usage | % | Average | > 80% |
| ShardingMemoryUsage | Cluster edition memory usage | % | Average | > 80% |

---

## PolarDB (acs_polardb)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| cluster_cpu_utilization | MySQL cluster CPU utilization | % | Average | > 80% |
| cluster_memory_utilization | MySQL cluster memory utilization | % | Average | > 80% |
| pg_cpu_total | PostgreSQL CPU usage | % | Average | > 80% |
| pg_conn_usage | PostgreSQL connection usage | % | Average | > 70-80% |
| oracle_cpu_total | Oracle CPU usage | % | Average | > 80% |

---

## Elasticsearch (acs_elasticsearch)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| ClusterStatus | Cluster health (0=green, 1=yellow, 2=red) | value | **Value** | >= 2 |
| NodeDiskUtilization | Node disk utilization | % | Average | > 75-85% |
| NodeHeapMemoryUtilization | Node heap memory utilization | % | Average | > 80% |

---

## Hologres (acs_hologres)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| cpu_usage | CPU usage | % | Average | > 90-99% |
| memory_usage | Memory usage | % | Average | > 85-90% |
| storage_usage_percent | Storage usage | % | Average | > 80% |
| connection_usage | Connection usage | % | Average | > 70-80% |

---

## NAT Gateway (acs_nat_gateway)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| SnatConnection | SNAT connections | count | Average | Business-dependent |
| SessionNewLimitDropConnection | New session drop count | count | Average | > 0-3 |
| SessionActiveConnectionWaterLever | Active connection watermark | % | Average | > 80-90% |

---

## EIP (acs_vpc_eip)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| net_rx.rate | Inbound bandwidth | bytes/s | Average | Near bandwidth limit |
| net_tx.rate | Outbound bandwidth | bytes/s | Average | Near bandwidth limit |
| out_ratelimit_drop_speed | Rate limit drop speed | packets/s | Average | > 0 |

---

## OceanBase (acs_oceanbase)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| cpu_util_instance | Instance CPU utilization | % | Average | > 90-95% |
| disk_ob_data_usage_instance | OB data disk usage | % | Average | > 85-88% |
| memory_used_percent_instance | Instance memory usage | % | Average | > 80-90% |

---

## DRDS (acs_drds)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| CPUUsageOfCN | Compute node CPU usage | % | Average | > 85-90% |
| DiskUsageOfDN | Data node disk usage | % | Average | > 85-90% |
| ConnUsageOfDN | Data node connection usage | % | Average | > 70-80% |

---

## GPDB / AnalyticDB PostgreSQL (acs_hybriddb)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| adbpg_query_blocked | Query blocked count | count | Average | > 0 |
| node_mem_used_percent | Node memory usage | % | Average | > 80-85% |
| node_cpu_used_percent | Node CPU usage | % | Average | > 80-85% |

---

## HBase (acs_hbase)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| LoadPerCpu | Load per CPU | value | Average | > 2-3 |
| cpu_idle | CPU idle percentage | % | Average | < 15-20% |
| CapacityUsedPercent | Storage capacity usage | % | Average | > 75-80% |

---

## RocketMQ (acs_rocketmq)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| ThrottledReceiveRequestsPerGid | Throttled receive requests per GID | count | Average | >= 1 |
| MessageAccumulation | Message accumulation | count | Average | Business-dependent |
| ConsumerLag | Consumer lag | count | Average | Business-dependent |

---

## KMS (acs_kms)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| code_5xx_1m | Server errors (5xx) per minute | count | Sum | > 0 |
| code_4xx_1m | Client errors (4xx) per minute | count | Sum | Business-dependent |
| latency_1m | Request latency per minute | ms | Average | > 3000-5000ms |

---

## SWAS / Simple Application Server (acs_swas)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| CPUUtilization | CPU utilization | % | Average | > 85-90% |
| MemoryUtilization | Memory utilization | % | Average | > 85-90% |
| DiskUtilization | Disk utilization | % | Average | > 80-85% |

---

## Serverless App Engine (acs_serverless)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| cpu | CPU usage | % | Average | > 90-95% |
| memoryPercent | Memory usage | % | Average | > 90-95% |

---

## EMR (acs_emr)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| serverless_starrocks_be_cpu_idle | StarRocks BE CPU idle | % | Average | < 10-15% |
| serverless_starrocks_be_disks_utilization | StarRocks BE disk utilization | % | Average | > 80% |

---

## CloudBox (acs_cloudbox)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| idc_rack_temperature | Rack temperature | °C | Average | > 30°C or < 5°C |
| ebs_capacity_utilization | EBS capacity utilization | % | Average | > 80% |

---

## IoT (acs_iot)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| MessageWatermarkTps_instance | Message TPS watermark | % | Average | > 85-90% |
| OnlineDeviceCount | Online device count | count | Value | Business-dependent |

---

## HSM (acs_hsm)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| Hsmhealthy | HSM health status (1=healthy, 0=unhealthy) | value | Value | == 0 |
| CPUUtilization | CPU utilization | % | Average | > 80-85% |

---

## Milvus (acs_milvus)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| ProcessCPUUtilizationV2 | Process CPU utilization | % | Average | > 85-90% |
| ProcessResidentMemoryUtilizationV2 | Process memory utilization | % | Average | > 80% |

---

## OpenSearch (acs_opensearch)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| DocSizeRatiobyApp | Document storage usage ratio | % | Average | > 80-85% |
| LossQPSbyApp | Lost QPS by application | count | Sum | > 0 |

---

## HBR / Hybrid Backup Recovery (acs_hbr)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| hw_appliance_disk_used_percent | Appliance disk usage | % | Average | > 80-85% |

---

## CEN / Cloud Enterprise Network (acs_cen)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| InternetOutRatePercentByConnectionRegion | Cross-region bandwidth usage | % | Average | > 75-80% |

---

## Shared Bandwidth (acs_bandwidth_package)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| net_tx.ratePercent | Outbound bandwidth usage | % | Average | > 80% |
| net_rx.ratePercent | Inbound bandwidth usage | % | Average | > 80% |

---

## SLS Dashboard (acs_sls_dashboard)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| ConsumerGroupFallBehind | Consumer group fall behind time | s | Average | > 300-600s |
| LogInflow | Log inflow | bytes/s | Average | Business-dependent |

---

## E-HPC (acs_ehpc)

| MetricName | Description | Unit | Statistics | Typical Threshold |
|------------|-------------|------|------------|-------------------|
| cluster_cpu_utilization | Cluster CPU utilization | % | Average | > 80-90% |
| cluster_memory_utilization | Cluster memory utilization | % | Average | > 80-90% |

---

## Notes

- This is a **subset** of available metrics. Use `describe-metric-meta-list` API for the complete list.
- Thresholds are reference values. Adjust based on your actual workload and SLA requirements.
- Some metrics require CloudMonitor agent to be installed (e.g., ECS memory, disk metrics).
- Statistics column shows the most commonly used aggregation method. Some metrics support multiple statistics (Average, Maximum, Minimum, Value, Sum).
- For cluster/sharding type products, use the appropriate metric variant (e.g., `ShardingCPUUtilization` for MongoDB sharding, `StandardCpuUsage` for Redis standard edition).
