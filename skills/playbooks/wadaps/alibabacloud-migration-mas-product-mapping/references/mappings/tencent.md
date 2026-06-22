# Tencent Cloud → Alibaba Cloud Product Mapping

## Compute

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CVM | ECS | SMC Server Migration Center | Compute | Medium |
| Auto Scaling AS | Auto Scaling ESS | Policy Rebuild | Compute | Low |
| Spot Instance | Preemptible Instance | Policy Rebuild | Compute | Low |
| Simple Application Server Lighthouse | Simple Application Server SWAS | Manual Migration | Compute | Medium |
| TKE Container Service | ACK Container Service | Image Migration+YAML Migration | Compute | High |
| EKS Elastic Container Instance | ECI Elastic Container Instance / Serverless Container ASK | Image Migration+Configuration Adaptation | Compute | Medium |
| TCR Container Registry | Container Registry ACR | Image Sync Tool | Compute | Low |
| SCF Cloud Function | Function Compute FC | CodeMigration+Adaptation | Compute | High |
| Serverless App Engine TEM | SAE Application Engine | Application Redeployment | Compute | Medium |
| Batch Compute Batch | Batch Compute BatchCompute | TaskRebuild | Compute | Medium |

## Storage

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| COS Object Storage | OSS Object Storage | Online MigrationService/ossimport | Storage | Low |
| COS Infrequent Access/Archive/Deep Cold Archive | OSS Infrequent Access/Archive/Deep Cold Archive | Online MigrationService | Storage | Low |
| CBS Cloud Disk | ESSD Cloud Disk | SMC withInstanceMigration | Storage | Low |
| CFS File Storage | NAS File Storage | DataMigrationTool/nasimport | Storage | Medium |
| CFS Turbo | NAS Ultra/CPFS | DataMigration | Storage | Medium |
| StorageGateway CSG | Cloud StorageGateway CSG | SolutionRebuild | Storage | Medium |
| Hybrid Backup Recovery | Cloud Backup HBR | Policy Rebuild | Storage | Low |

## Database

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CDB MySQL | RDS MySQL | DTS Data TransmissionService | Data | Medium |
| CDB PostgreSQL | RDS PostgreSQL | DTS Data TransmissionService | Data | Medium |
| CDB MariaDB | RDS MariaDB | DTS Data TransmissionService | Data | Medium |
| CDB SQL Server | RDS SQL Server | DTS Data TransmissionService | Data | Medium |
| TDSQL-C MySQL | PolarDB MySQL | DTS Data TransmissionService | Data | Medium |
| TDSQL-C PostgreSQL | PolarDB PostgreSQL | DTS Data TransmissionService | Data | Medium |
| TDSQL MySQL（Distributed） | PolarDB-X Distributed Database | DTS Data TransmissionService | Data | High |
| TDSQL-H（HTAP） | PolarDB MySQL (HTAPMode) | DTS Data TransmissionService | Data | High |
| TencentDB Redis | ApsaraDB Redis Edition | DTS/redis-shake | Cache | Medium |
| TencentDB Memcached | ApsaraDB Memcache Edition | Application LayerAdaptation | Cache | Medium |
| TencentDB MongoDB | ApsaraDB MongoDB Edition | DTS Data TransmissionService | Data | Medium |
| TencentDB for ClickHouse | ApsaraDB ClickHouse | DataMigrationTool | Data | High |
| CTSDB Time Series Database | Time Series Database TSDB / Lindorm | CustomMigration | Data | High |
| Graph Database KonisGraph | Graph Database GDB | Data Export/Import | Data | High |
| TcaplusDB Game Database | Tablestore Tablestore | CustomMigration | Data | High |
| DBbrain Database Autonomy Service | DAS Database Autonomy Service | No needMigration(Management Tool) | Operations | Low |

## Network & CDN

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| VPC VPC | VPC VPC | ManualRebuild | Network | Low |
| CLB Load Balancer | SLB/ALB/NLB Load Balancer | ManualRebuild | Network | Low |
| NAT Gateway | NAT Gateway | ManualRebuild | Network | Low |
| EIP Elastic Public IP | Elastic Public IP (EIP) | Manual Allocation | Network | Low |
| VPN Connect | VPN Gateway | Manual Configuration | Network | Low |
| Dedicated LineAccess DC | Express Connect Express Connect | Line Application | Network | High |
| Cloud Connect Network CCN | CEN CEN / Transit Router TR | ManualRebuild | Network | Medium |
| CDN CDN | CDN CDN | Domain Switch | Network | Low |
| DNSPod DNS | DNS DNS | ManualRebuild | Network | Low |
| Global Accelerator GAAP | Global Accelerator GA | Manual Configuration | Network | Low |
| PrivateZone DNS Private DNS | PrivateZone | ManualRebuild | Network | Low |

## Messaging & Middleware

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CKafka Message Queue | Message Queue Kafka Edition | MirrorMaker/Kafka Connect | Middleware | High |
| TDMQ RocketMQ | Message Queue RocketMQ Edition | Configuration Migration+MessageMigration | Middleware | High |
| TDMQ RabbitMQ | Message Queue RabbitMQ Edition | Image Migration/shovel | Middleware | Medium |
| CMQ Message Queue | Message Queue RocketMQ Edition | Application LayerAdaptation | Middleware | High |
| EventBridge EventBridge | EventBridge EventBridge | RuleMigration | Middleware | Medium |
| API Gateway | API Gateway | Configuration Migration+Adaptation | Middleware | Medium |
| Microservice Engine TSE | Microservice Engine MSE | Configuration Migration+Adaptation | Middleware | Medium |

## Big Data & Analytics

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CDWPG Cloud Data Warehouse PostgreSQL | AnalyticDB PostgreSQL | DataMigrationTool | Big Data | High |
| EMR Elastic MapReduce | E-MapReduce EMR | DataX/distcp | Big Data | High |
| Elasticsearch Service | Elasticsearch | reindex/Snapshot Restore | Data | Medium |
| Data Lake Compute DLC | Data Lake Analytics / MaxCompute | SQL Adaptation | Big Data | Medium |
| Cloud Data Warehouse CDW ClickHouse | ApsaraDB ClickHouse | DataMigrationTool | Big Data | High |
| Business Intelligence BI | Quick BI | ReportRebuild | Big Data | Medium |
| Stream Computing Oceanus (Flink) | Realtime Compute Flink Edition | JobMigration+Adaptation | Big Data | High |
| DataWorks WeData | DataWorks Data Integration | TaskRebuild | Big Data | High |
| Log Service CLS | Log Service SLS | Log Delivery Adaptation | Big Data | Medium |

## Security & Identity

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CAM Access Management | RAM Access Control | Policy Rebuild | Security | Medium |
| KMS Key Management | Key ManagementService KMS | KeyRebuild | Security | Medium |
| Web Application Firewall WAF | Web Application Firewall WAF | RuleMigration | Security | Medium |
| DDoS Protection | DDoS Protection Anti-DDoS | Manual Configuration | Security | Low |
| SSL Certificate | SSL Certificate Service | Certificate Reissuance | Security | Low |
| Host Security（Cloud Mirror） | Security Center | Manual Configuration | Security | Medium |
| Cloud Audit CloudAudit | ActionTrail ActionTrail | Manual Configuration | Security | Low |
| Bastion Host BH | Bastion Host | Policy Rebuild | Security | Medium |
| Data Security Audit | Database Audit | Manual Configuration | Security | Low |

## Operations & Monitoring

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CloudMonitor CM | CloudMonitor CMS | Manual Configuration | Operations | Low |
| Frontend Performance Monitoring RUM | Application Real-Time Monitoring Service ARMS | Application Adaptation | Operations | Medium |
| Application Real-Time Monitoring APM | Tracing OpenTelemetry Edition | Application Adaptation | Operations | Medium |
| Resource Orchestration TIC | Resource Orchestration ROS / Terraform | Template Conversion | Operations | Medium |
| Automation Assistant TAT | Cloud Assistant | ManualRebuild | Operations | Low |
| Billing Center | Billing Center / Cost Manager | — | Operations | Low |

## AI & Machine Learning

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| TI Platform (TI-ONE) | PAI Machine Learning Platform | Model Export/Import | AI | High |
| Hunyuan Model | Model Studio / DashScope | API Adaptation | AI | Medium |
| Face Recognition | Vision Intelligence Platform | API Adaptation | AI | Medium |
| Machine Translation TMT | Machine Translation | API Adaptation | AI | Low |
| Speech Recognition ASR | Intelligent Speech Interaction | API Adaptation | AI | Medium |
| NLP NLP | NLP Self-learning Platform | API Adaptation | AI | Medium |

## Other

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Cloud Desktop CVD | Wuying Cloud Desktop | Image Migration | Other | Medium |
| CODING DevOps | Yunxiao Flow + Codeup | Pipeline/RepositoryMigration | DevOps | Medium |
| IoT Explorer IoT | IoT Platform IoT Platform | DeviceMigration+RuleRebuild | IoT | High |
| Domain Registration | Domain Name Service | Domain Transfer | Other | Low |
