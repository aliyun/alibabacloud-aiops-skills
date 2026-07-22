# Cloud Product Mapping Reference

> Last updated: 2026-05-28
> Purpose: used by the cloud-migration-survey skill when analyzing survey materials to map source cloud vendor products to their Alibaba Cloud counterparts.
> Note: the product mapping may change as the Alibaba Cloud product line evolves; always rely on the latest official documentation.
> Version risks: for mappings that involve version changes, see [version-risks.md](version-risks.md).

---

## Source Cloud Platform Identification Clues

| Cloud Vendor | Product Name Clues | Region Naming Traits | Other Clues |
|--------|-------------|----------------|---------|
| Baidu Cloud | BCC/BOS/CCE/CFS/BLB/SCS | bj/gz/su | Baidu AI Cloud console |
| Huawei Cloud | ECS/OBS/CCE/SFS/ELB/DCS/DWS/DMS/GaussDB | cn-north/cn-south/ap-southeast | Huawei Cloud bill, MyHuaweiCloud |
| AWS | EC2/S3/EKS/EFS/ELB/ElastiCache/MSK/Aurora/DynamoDB/Lambda | us-east/eu-west/ap-northeast | AWS Console, ARN format |
| Azure | VM/Blob/AKS/Files/CosmosDB/ServiceBus/EventGrid | eastus/westeurope/japaneast | Azure Portal, Resource Group |
| GCP | GCE/GCS/GKE/Filestore/BigQuery/Pub/Sub/CloudSQL | us-central1/europe-west1/asia-east1 | GCP Console, Project ID |
| Tencent Cloud | CVM/COS/TKE/CFS/CLB/DCS/TDSQL/CKafka/TDMQ | ap-guangzhou/ap-shanghai | Tencent Cloud console |
| IDC | physical servers/VMware/Hyper-V/self-hosted databases/self-hosted middleware | data center location, rack number | leased-line access, physical device models |

---

## 1. Network Product Mapping

### Alibaba Cloud network product matrix

| Alibaba Cloud Product | Positioning | Applicable Scenarios |
|-----------|------|---------|
| **VPC (Virtual Private Cloud)** | Network infrastructure | Network foundation for every project |
| **VSwitch** | Subnet within a VPC | AZ-level subnet division |
| **CEN (Cloud Enterprise Network)** | Cross-region / cross-VPC interconnect | Multi-region multi-VPC networking, cross-cloud interconnect |
| **TR (Transit Router)** | Core component of CEN | Large-scale network interconnect, routing policy control |
| **EIP (Elastic IP)** | Public IP address | Public ingress, NAT egress |
| **NAT Gateway** | SNAT/DNAT | Private instances to public network, port mapping |
| **CLB (Classic Load Balancer)** | L4/L7 load balancing (classic) | Traditional L4/L7 load, gradually replaced by ALB/NLB |
| **ALB (Application Load Balancer)** | L7 load balancing (new generation) | HTTP/HTTPS/gRPC L7 load, content routing |
| **NLB (Network Load Balancer)** | L4 load balancing (new generation) | TCP/UDP/TLS L4 high-performance load |
| **Shared Bandwidth** | Bandwidth reuse | Multiple EIPs share a bandwidth package to reduce cost |
| **VPN Gateway** | VPN gateway | Hybrid cloud Site-to-Site VPN |
| **Express Connect** | Leased-line access | IDC physical leased line into Alibaba Cloud |
| **PrivateLink** | Private network connect | Cross-VPC private service exposure |
| **Alibaba Cloud DNS** | Public DNS | Domain resolution, smart routing |
| **PrivateZone** | Private DNS | Service discovery inside a VPC |
| **Global Accelerator (GA)** | Global network acceleration | Cross-country / cross-region access acceleration |
| **WAF (Web Application Firewall)** | Web protection | HTTP/HTTPS application-layer protection |
| **Anti-DDoS Pro** | DDoS scrubbing | Protection against large-traffic DDoS attacks |
| **Cloud Firewall** | Network firewall | East-west / north-south traffic control |

### Source cloud → Alibaba Cloud network mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | Baidu Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|--------|-----|---------|
| Virtual network | VPC | VNet | VPC | VPC | VPC | VPC | self-hosted VLAN | **VPC** |
| Subnet | Subnet | Subnet | Subnet | Subnet | Subnet | Subnet | — | **VSwitch** |
| Cross-VPC interconnect | VPC Peering / Transit Gateway | VNet Peering / vWAN | VPC Peering / Cloud Interconnect | VPC Peering / CC | Peering / CCN | VPC Peering | — | **CEN / TR** |
| Public IP | Elastic IP | Public IP | External IP | EIP | EIP | EIP | fixed public IP | **EIP** |
| NAT gateway | NAT Gateway | NAT Gateway | Cloud NAT | NAT Gateway | NAT Gateway | NAT Gateway | self-hosted iptables | **NAT Gateway** |
| L4 load balancing | NLB / CLB | Load Balancer | Internal/External LB | ELB (L4) | CLB (L4) | BLB | F5 / LVS | **NLB / CLB** |
| L7 load balancing | ALB / ELB | Application Gateway | HTTP(S) LB | ELB (L7) | CLB (L7) | BLB | Nginx / HAProxy | **ALB** |
| CDN | CloudFront | Azure CDN | Cloud CDN | CDN | CDN / ECDN | CDN | self-hosted/3rd-party | **CDN / DCDN** |
| VPN | VPN Gateway | VPN Gateway | Cloud VPN | VPN Gateway | VPN Gateway | VPN Gateway | hardware VPN | **VPN Gateway** |
| Leased line | Direct Connect | ExpressRoute | Partner Interconnect | Direct Connect (DC) | Direct Connect | Direct Connect | physical leased line | **Express Connect** |
| Public DNS | Route 53 | Azure DNS | Cloud DNS | DNS resolution | DNSPod | Domain resolution | BIND/self-hosted | **Alibaba Cloud DNS** |
| Private DNS | Route 53 Resolver | Private DNS Zones | Cloud DNS Private | internal DNS | PrivateZone | — | self-hosted DNS | **PrivateZone** |
| Global acceleration | Global Accelerator | Front Door | — | — | Global Application Acceleration | — | — | **GA** |
| WAF | AWS WAF | Azure WAF | Cloud Armor | WAF | WAF | — | self-hosted WAF | **WAF** |
| DDoS protection | Shield Advanced | DDoS Protection | Cloud Armor | Anti-DDoS | DaYu | — | hardware scrubbing | **Anti-DDoS Pro** |
| Network firewall | Network Firewall | Azure Firewall | Cloud NGFW | CFW | Security Group | — | iptables/hardware | **Cloud Firewall** |

---

## 2. Database Product Mapping

### Alibaba Cloud database product matrix

| Alibaba Cloud Product | Positioning | Compatible Protocol | Currently Selectable Versions |
|-----------|------|---------|------------|
| **RDS MySQL** | Managed MySQL database | MySQL | 5.6 / 5.7 / 8.0 / 8.4 |
| **RDS PostgreSQL** | Managed PostgreSQL | PG | 10 / 11 / 12 / 13 / 14 / 15 / 16 |
| **RDS SQL Server** | Managed SQL Server | TDS | 2012 / 2014 / 2016 / 2017 / 2019 / 2022 |
| **RDS MariaDB** | Managed MariaDB | MySQL | 10.3 / 10.4 / 10.5 / 10.6 |
| **PolarDB for MySQL** | MySQL-compatible cloud-native database | MySQL | 5.6 / 5.7 / 8.0 |
| **PolarDB for PostgreSQL** | PG-compatible cloud-native database | PG | 11 / 14 / 15 |
| **PolarDB-O** | Oracle-compatible database | Oracle | Oracle syntax compatible |
| **PolarDB-X** | Distributed relational database | MySQL | — |
| **Tair (memory edition)** | Full-feature Redis + Tair extended commands | Redis + TairHash/TairString/TairDoc | 6.0 / 7.0 |
| **Tair (persistent memory edition)** | Persistent memory + some extended commands | Redis + exHash/exString/Cpc | 6.0 |
| **Tair (disk edition)** | Disk storage (basic data structures only) | Redis 6.0 basic commands | 6.0 |
| **ApsaraDB for Redis** | Standard managed Redis | Redis | 5.0 / 6.0 / 7.0 |
| **ApsaraDB for MongoDB** | Managed MongoDB | MongoDB | 4.0 / 4.2 / 4.4 / 5.0 / 6.0 / 7.0 |
| **Lindorm** | Multi-model database (wide-table/time-series/search) | HBase API / CQL / S3 / time-series | — |
| **Tablestore** | Serverless wide-table | OTS API | — |
| **SelectDB (Doris)** | Real-time analytical database | MySQL | — |
| **ClickHouse** | Columnar analytical engine | ClickHouse | — |
| **AnalyticDB for MySQL** | MySQL-compatible analytical engine | MySQL | — |
| **AnalyticDB for PostgreSQL** | PG-compatible MPP warehouse | PG | — |
| **Hologres** | Real-time warehouse (serving + analytics) | PG | — |
| **MaxCompute** | Serverless big-data compute | SQL + MR | — |
| **DTS** | Data migration/sync/subscription | — | — |
| **DMS** | Database ops management | — | — |
| **ADAM** | Heterogeneous database migration assessment | — | — |
| **DBS** | Database backup | — | — |

### Source cloud → Alibaba Cloud database mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | Baidu Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|--------|-----|---------|
| MySQL | RDS MySQL / Aurora MySQL | Azure MySQL | Cloud SQL MySQL | RDS MySQL | CDB MySQL | RDS MySQL | self-hosted MySQL | **RDS MySQL / PolarDB-MySQL** |
| PostgreSQL | RDS PG / Aurora PG | Azure PG | Cloud SQL PG | RDS PG | — | — | self-hosted PG | **RDS PG / PolarDB-PG** |
| SQL Server | RDS SQL Server | Azure SQL | — | — | — | — | self-hosted SQL Server | **RDS SQL Server** |
| MariaDB | RDS MariaDB | Azure MariaDB | — | — | — | — | self-hosted MariaDB | **RDS MariaDB** |
| Oracle | self-hosted on EC2 / RDS Custom | self-hosted on Azure VM | Bare Metal | GaussDB(for Oracle) | — | — | self-hosted Oracle | **PolarDB-O + ADAM** |
| Distributed DB | Aurora Serverless v2 | Cosmos DB | Spanner | GaussDB (distributed) | TDSQL | — | TiDB/OceanBase | **PolarDB-X / PolarDB** |
| Redis | ElastiCache Redis | Azure Cache Redis | Memorystore Redis | DCS Redis / GeminiDB Redis | Cloud Redis | SCS Redis | self-hosted Redis | **ApsaraDB for Redis / Tair (see version risks)** |
| Memcached | ElastiCache Memcached | — | Memorystore Memcached | DCS Memcached | — | — | self-hosted Memcached | **ApsaraDB for Memcache** |
| MongoDB | DocumentDB | Cosmos DB (Mongo API) | — | DDS MongoDB | Cloud MongoDB | — | self-hosted MongoDB | **ApsaraDB for MongoDB (see version risks)** |
| HBase | EMR HBase | HDInsight HBase | — | CloudTable HBase | — | — | self-hosted HBase | **Lindorm** |
| DynamoDB / wide-table | DynamoDB | Table Storage / Cosmos DB | Datastore / Bigtable | — | — | — | — | **Tablestore / Lindorm** |
| ClickHouse | — | — | — | — | — | — | self-hosted ClickHouse | **ClickHouse / SelectDB** |
| Elasticsearch | OpenSearch | Azure Search | — | CSS | — | — | self-hosted ES | **Elasticsearch** |
| Data warehouse | Redshift / Athena | Synapse | BigQuery | DWS | CDWPG / DLC | — | Hive/DW | **MaxCompute / ADB / Hologres** |

### Tair selection guide (must-read for Redis migration)

| Source Situation | Recommended Alibaba Cloud Product | Reason |
|---------|-------------|------|
| Source uses only basic Redis data structures (String/Hash/List/Set/ZSet) | ApsaraDB for Redis or Tair disk edition | Lowest cost |
| Source uses Huawei GeminiDB Redis exHash extended commands | **Tair memory edition** | Full TairHash compatibility (~27 commands) |
| Source uses Redis extended commands but data volume is large and cost-sensitive | **Tair persistent memory edition** | Supports exHash/exString/Cpc, moderate cost |
| Source uses RedisJSON / RediSearch / RedisGraph | **Tair memory edition** (TairDoc/TairSearch/TairGis) | Confirm the exact module correspondence |
| Source Redis data volume > 50GB with a high proportion of cold data | **Tair disk edition** + hot/cold separation | Significantly reduces cost |

> **Warning**: the Tair disk edition **does not support any extended data structures** (exHash/exZset/GIS, etc.); it is only compatible with the Redis 6.0 basic data structures. If the source uses extended commands and the disk edition is chosen, it will cause runtime errors.

### Database migration tool selection

| Migration Scenario | Recommended Tool | Notes |
|---------|---------|------|
| Homogeneous full + incremental | DTS | MySQL→MySQL, PG→PG, MongoDB→MongoDB |
| Heterogeneous migration assessment | ADAM + DTS | Oracle→PolarDB-O: assess with ADAM first, then migrate |
| MongoDB migration | mongodump + DTS | DTS supports oplog incremental sync |
| Redis migration | Redis-Shake / DTS | Supports RDB+AOF+online sync |
| HBase migration | LTS (BDS) | Dedicated Lindorm migration tool |
| ES migration | Logstash / Snapshot | snapshot→OSS→restore, or Logstash pipeline |
| Data warehouse migration | DataWorks DI / Tunnel | Use Tunnel or DataWorks for MaxCompute |

---

## 3. Middleware Product Mapping

### Alibaba Cloud middleware product matrix

| Alibaba Cloud Product | Positioning | Applicable Scenarios |
|-----------|------|---------|
| **RocketMQ 5.x** | Transactional/scheduled/ordered messages | E-commerce transactions, financial-grade messaging, distributed transactions |
| **Kafka (ApsaraMQ)** | High-throughput streaming messages | Log collection, big-data pipelines, IoT data streams |
| **RabbitMQ (ApsaraMQ)** | AMQP protocol compatible | Delay queues, routing distribution, smooth AMQP ecosystem migration |
| **MQTT (ApsaraMQ)** | Lightweight IoT messaging | IoT device communication, mobile push |
| **EventBridge** | Event-driven architecture | Cross-system event routing, SaaS integration |
| **MNS (Message Service)** | Lightweight queue | Simple decoupling (gradually replaced by RocketMQ) |

### Middleware selection decision matrix

| Requirement | Recommended | Not Recommended |
|---------|---------|--------|
| Transactional messages / distributed transactions | **RocketMQ** | Kafka / RabbitMQ |
| Scheduled / delayed messages | **RocketMQ** | Kafka |
| Ordered messages | **RocketMQ** | RabbitMQ |
| Log collection / streaming pipeline | **Kafka** | RocketMQ / RabbitMQ |
| Big-data pipeline (Flink/Spark data source) | **Kafka** | RocketMQ |
| AMQP protocol compatibility / delay queue | **RabbitMQ** | RocketMQ (requires refactoring) |
| Smooth migration of existing RabbitMQ apps | **RabbitMQ** | RocketMQ (requires code refactoring) |
| IoT device communication | **MQTT** | Kafka / RocketMQ |
| Event-driven / SaaS integration | **EventBridge** | Kafka |

### Source cloud → Alibaba Cloud middleware mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | Baidu Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|--------|-----|---------|
| Transactional MQ | Amazon MQ (ActiveMQ) / SQS | Service Bus | Pub/Sub | DMS RocketMQ | TDMQ RocketMQ | — | self-hosted RocketMQ/ActiveMQ | **RocketMQ 5.x** |
| Kafka | MSK | Event Hubs (Kafka) | — | DMS Kafka | CKafka / TDMQ Kafka | ApsaraMQ Kafka | self-hosted Kafka | **Kafka** |
| RabbitMQ | Amazon MQ (RabbitMQ) | Service Bus (AMQP) | — | DMS RabbitMQ | TDMQ RabbitMQ | — | self-hosted RabbitMQ | **RabbitMQ** |
| Simple queue | SQS / SNS | Storage Queue | Pub/Sub | — | CMQ | — | — | **RocketMQ / MNS** |
| IoT messaging | IoT Core MQTT | IoT Hub | Cloud IoT | IoTDA | IoT Hub | — | self-hosted MQTT Broker | **MQTT** |
| Event-driven | EventBridge | Event Grid | Eventarc | — | — | — | — | **EventBridge** |

---

## 4. Microservices Product Mapping

### Alibaba Cloud microservices product matrix

| Alibaba Cloud Product | Positioning | Applicable Scenarios |
|-----------|------|---------|
| **MSE Nacos** | Registry / config center | Spring Cloud / Dubbo service discovery, dynamic config |
| **MSE ZooKeeper** | Distributed coordination | Kafka/HBase/Solr components that depend on ZK, distributed locks |
| **MSE Sentinel** | Traffic governance | Rate limiting, circuit breaking, degradation, system protection |
| **Cloud-native Gateway (MSE Ingress)** | API gateway / traffic ingress | K8s Ingress, microservice gateway, canary routing |
| **API Gateway** | API management | API publishing, authentication, metering |
| **SchedulerX** | Distributed task scheduling | Scheduled tasks, distributed jobs |
| **ARMS** | APM | Full-link tracing, application performance diagnostics |
| **EDAS** | Microservice governance platform | Application hosting, canary release |

### Source cloud / self-hosted → Alibaba Cloud microservices mapping

| Source Component | → Alibaba Cloud Product | Migration Method |
|---------|-----------|---------|
| Nacos (self-hosted) | **MSE Nacos** | Config import / dual-registration smooth migration |
| Consul | **MSE Nacos** | Service dual-registration transition |
| Eureka | **MSE Nacos** | Client switches to Nacos SDK |
| ZooKeeper (self-hosted) | **MSE ZooKeeper** | Data migration + client reconnect |
| Apollo (Ctrip config center) | **MSE Nacos config management** | Bulk config import |
| Sentinel (open source) | **MSE Sentinel** | Seamless upgrade, enhanced by the managed edition |
| Hystrix / Resilience4j | **MSE Sentinel** | Client refactoring |
| Spring Cloud Gateway | **Cloud-native Gateway** | YAML migration |
| Kong / APISIX | **Cloud-native Gateway / API Gateway** | Route config conversion |
| AWS API Gateway | **API Gateway / Cloud-native Gateway** | API reconfiguration |
| XXL-Job (self-hosted) | **SchedulerX** | Job config migration + Agent deployment |
| Elastic-Job | **SchedulerX** | Job config migration |
| Quartz | **SchedulerX** | Adapt to the SchedulerX SDK |
| AWS X-Ray / Datadog | **ARMS** | Agent replacement |
| Jaeger / Zipkin | **ARMS** | OpenTelemetry compatible |

---

## 5. Compute and Storage Product Mapping

### Source cloud → Alibaba Cloud storage mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | Baidu Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|--------|-----|---------|
| Object storage | S3 | Blob Storage | GCS | OBS | COS | BOS | MinIO/Ceph | **OSS** |
| File storage | EFS | Azure Files | Filestore | SFS | CFS | CFS | NFS/GlusterFS | **NAS** |
| Parallel file system | FSx for Lustre | Azure HPC Cache | — | — | — | Parallel File System | Lustre/GPFS | **CPFS** |
| HDFS | EMR HDFS | HDInsight HDFS | Dataproc HDFS | MRS HDFS | EMR HDFS | — | self-hosted Hadoop | **OSS-HDFS / EMR** |
| Block storage | EBS | Managed Disk | Persistent Disk | EVS | CBS | CDS | SAN/local disk | **ESSD** |

### Alibaba Cloud compute product quick reference

| Product | Positioning | Applicable Scenarios |
|------|------|---------|
| ECS (g/c/r series) | general/compute/memory optimized | Web, middleware, general workloads |
| ECS (hfc/hfr) | high frequency | High-performance computing, gaming |
| ECS (gn6/gn7) | GPU | AI inference/training, rendering |
| Bare Metal (Shenlong) | physical-machine-level performance | High-performance databases, compliance |
| ECI | Serverless container | Bursty containers, CI/CD |
| FC (Function Compute) | Serverless FaaS | Event-driven functions |
| SAE | Serverless application hosting | Ops-free microservices |

---

## 6. Big Data Product Mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|-----|---------|
| Offline warehouse | Redshift / Athena | Synapse SQL | BigQuery | DWS / DLV | CDWPG / DLC | Hive/Spark | **MaxCompute / ADB / Hologres** |
| Data development | Glue / Data Pipeline | Data Factory (ADF) | Dataflow | DataArts | WeData | Airflow/Azkaban | **DataWorks** |
| Open-source big data | EMR | HDInsight | Dataproc | MRS | EMR | self-hosted Hadoop | **EMR** |
| Real-time computing | Kinesis / Managed Flink | Stream Analytics | Dataflow Streaming | DLI (Flink) | Oceanus | self-hosted Flink | **Flink** |
| Search/logs | OpenSearch | Azure Search | — | CSS | — | self-hosted ES | **Elasticsearch** |
| ML platform | SageMaker | Azure ML | Vertex AI | ModelArts | TI-ONE | self-hosted | **PAI** |

---

## 7. Container Product Mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | Baidu Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|--------|-----|---------|
| Container orchestration | EKS | AKS | GKE | CCE | TKE | CCE | self-hosted K8s | **ACK** |
| Image registry | ECR | ACR | Artifact Registry | SWR | TCR | — | Harbor | **ACR** |
| Service mesh | App Mesh / Istio | OSM | Anthos SM | ASM | TCM | — | self-hosted Istio | **ASM** |
| AI container | EKS (GPU) | AKS (GPU) | GKE (GPU) | CCE (GPU) | TKE (GPU) | — | — | **ACS / ACK (GPU)** |

> **Container migration note**: do not use SMC to migrate container clusters; redeploy via YAML or use Velero backup/restore.

---

## 8. Security and Identity Product Mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|-----|---------|
| Identity management | IAM | Azure AD / Entra ID | IAM | IAM | CAM | LDAP/AD | **RAM** |
| Key management | KMS | Key Vault | Cloud KMS | DEW | KMS | Vault | **KMS** |
| SSL certificate | ACM | App Service Cert | Cert Manager | CCM | SSL Certificate | self-signed/Let's Encrypt | **SSL Certificate Service** |
| Security center | Security Hub | Defender | SCC | SecMaster | Host Security | self-hosted SIEM | **Security Center** |
| Bastion host | — | Bastion | — | CBH | BH | self-hosted | **Bastionhost** |

---

## 9. Observability Product Mapping

| Function | AWS | Azure | GCP | Huawei Cloud | Tencent Cloud | IDC | → Alibaba Cloud |
|------|-----|-------|-----|--------|--------|-----|---------|
| Logs | CloudWatch Logs | Log Analytics | Cloud Logging | LTS | CLS | ELK | **SLS** |
| Monitoring | CloudWatch | Azure Monitor | Cloud Monitoring | CES | Cloud Monitor | Prometheus/Zabbix | **CloudMonitor** |
| APM | X-Ray | App Insights | Cloud Trace | AOM | APM | SkyWalking/Jaeger | **ARMS** |
| Audit | CloudTrail | Activity Log | Audit Logs | CTS | CloudAudit | self-hosted | **ActionTrail** |

---

## Mapping Usage Rules

1. **Identify the source cloud platform**: use the "Source Cloud Platform Identification Clues" table to determine it.
2. **Look up mapping by category**: first determine the category (network/database/middleware/microservices/big data/container), then look it up in the corresponding table.
3. **Check version risks**: when a database or middleware version change is involved, you **must** consult [version-risks.md](version-risks.md).
4. **Middleware selection**: use the "Middleware selection decision matrix" to choose the correct message queue product.
5. **Tair selection**: for Redis migration you must confirm whether the source uses extended data structures and choose the Tair type accordingly.
6. **Container migration**: do not use SMC; redeploy via YAML or use Velero.
7. **Database version upgrade**: when a version upgrade is involved, you must recommend introducing a traffic replay tool (go-replay/tcpcopy) for validation.
