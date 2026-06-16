# CADT Probe Supported Resource Types

The CADT probe service supports discovering the following Alibaba Cloud resource types.

## Compute

| Service Code | Name |
|--------|---------|
| ECS | Elastic Compute Service |
| DDH | Dedicated Host |
| ESS | Elastic Resource Group |
| FC | Function Compute |

## Container

| Service Code | Name |
|--------|---------|
| ACK | Container Service (Dedicated) |
| ACK_MANAGED | Container Service (Managed) |
| ASK | Container Service (Serverless) |
| ACR | Container Registry |

## Network

| Service Code | Name |
|--------|---------|
| VPC | Virtual Private Cloud |
| VSWITCH | VSwitch |
| EIP | Elastic IP Address |
| NAT | NAT Gateway |
| CLB | Classic Load Balancer |
| SLB | Classic Load Balancer |
| ALB | Application Load Balancer |
| NLB | Network Load Balancer |
| VPN | VPN Gateway |
| VBR | Virtual Border Router |
| CBN | Cloud Enterprise Network |
| CBWP | Common Bandwidth Package |
| ENI | Elastic Network Interface |
| SECURITY_GROUP | Security Group |
| ALB_SERVERGROUP | ALB Server Group |

## Storage

| Service Code | Name |
|--------|---------|
| OSS | Object Storage Service |
| NAS | File Storage |
| NAS_TREME | Extreme File Storage |
| CPFS | Cloud Parallel File Storage |
| DISK | Cloud Disk |

## Database

| Service Code | Name |
|--------|---------|
| RDS | ApsaraDB RDS |
| PolarDB | PolarDB |
| DDS | ApsaraDB for MongoDB |
| DDSSHARDING | ApsaraDB for MongoDB (Sharded Cluster) |
| KVSTORE | ApsaraDB for Redis (Tair Compatible) |
| KVSTORE_PREPAID_PUBLIC_CN | ApsaraDB for Redis (Subscription) |
| TAIR | ApsaraDB for Tair |
| HBASE | ApsaraDB for HBase |
| CLICKHOUSE | ApsaraDB for ClickHouse |
| LINDORM | Lindorm (Multi-model Database) |
| SELECTDB | ApsaraDB for SelectDB |
| GDB | Graph Database |
| DRDS | PolarDB Distributed Edition |
| MYBASE | ApsaraDB Dedicated Cluster (MyBase) |

## Data Analytics

| Service Code | Name |
|--------|---------|
| ADB | AnalyticDB |
| HOLOGRES | Hologres (Real-time Data Warehouse) |
| ODPS | MaxCompute |
| EMR | E-MapReduce |
| DATAHUB | DataHub |
| DLA | Data Lake Analytics |
| Flink | Realtime Compute for Apache Flink |
| DIDE | DataWorks |
| DATAWORKS_SPACE | DataWorks Workspace |
| DIDE_EXRESOURCEMIXED_PUBLIC | DataWorks Mixed Resources |

## Middleware

| Service Code | Name |
|--------|---------|
| KAFKA | Message Queue for Apache Kafka |
| KAFKA_SEVERLESS | Message Queue for Apache Kafka (Serverless) |
| ROCKETMQ | Message Queue (RocketMQ) |
| ONSPROXY | Message Queue for RabbitMQ |
| ELASTICSEARCH | Elasticsearch |
| MSE | Microservices Engine |
| APIGATEWAY | API Gateway |

## Security

| Service Code | Name |
|--------|---------|
| WAF | Web Application Firewall |
| DDoSCOO | Anti-DDoS |
| BASTIONHOST | Bastion Host |
| DBAUDIT | Database Audit |

## Others

| Service Code | Name |
|--------|---------|
| ACTIONTRAIL | ActionTrail |
| DNS | Alibaba Cloud DNS |
| CBS | Cloud Backup Service |
| OTS | Tablestore |
| PAI | Platform for AI |
| AIREC | AI Recommendation |
| HCS_SGW | Cloud Storage Gateway |
| SLB_VSERVERGROUP | SLB VServer Group |
| SLS | Simple Log Service (SLS) |

## Notes

- The above list is sourced from the CADT official documentation "Supported Resource List for Probe"
- During actual probing, CADT automatically scans all supported resource types
- Probing relies on resource data provided by the Cloud Config service, which must be enabled first
- `--list-types` values are **case-insensitive**: both `ecs,vpc` and `ECS,VPC` are accepted
