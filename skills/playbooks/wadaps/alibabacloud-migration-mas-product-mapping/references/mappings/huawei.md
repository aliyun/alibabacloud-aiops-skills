# Huawei Cloud → Alibaba Cloud Product Mapping

## Compute

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| ECS | ECS | SMC Server Migration Center | Compute | Medium |
| AS Auto Scaling | Auto Scaling ESS | Policy Rebuild | Compute | Low |
| Spot Instance | Preemptible Instance | Policy Rebuild | Compute | Low |
| CCE Cloud Container Engine | ACK Container Service | Image Migration+YAML Migration | Compute | High |
| CCI CloudContainerInstance | ECI Elastic Container Instance / Serverless Container ASK | Image Migration+Configuration Adaptation | Compute | Medium |
| SWR Container Registry | Container Registry ACR | Image Sync Tool | Compute | Low |
| FunctionGraph Function Workflow | Function Compute FC | CodeMigration+Adaptation | Compute | High |
| ServiceStage Application Management Platform | SAE Application Engine | Application Redeployment | Compute | Medium |
| Batch Compute | Batch Compute BatchCompute | TaskRebuild | Compute | Medium |

## Storage

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| OBS Object Storage | OSS Object Storage | Online MigrationService/ossimport | Storage | Low |
| OBS Infrequent Access/Archive/Deep Cold Archive | OSS Infrequent Access/Archive/Deep Cold Archive | Online MigrationService | Storage | Low |
| EVS Cloud Disk | ESSD Cloud Disk | SMC withInstanceMigration | Storage | Low |
| SFS Elastic File Service | NAS File Storage | DataMigrationTool/nasimport | Storage | Medium |
| SFS Turbo | NAS Ultra/CPFS | DataMigration | Storage | Medium |
| Storage Disaster Recovery SDRS | Cloud Backup HBR | Policy Rebuild | Storage | Medium |
| Cloud Backup CBR | Cloud Backup HBR | Policy Rebuild | Storage | Low |

## Database

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| RDS MySQL | RDS MySQL | DTS Data TransmissionService | Data | Medium |
| RDS PostgreSQL | RDS PostgreSQL | DTS Data TransmissionService | Data | Medium |
| RDS SQL Server | RDS SQL Server | DTS Data TransmissionService | Data | Medium |
| RDS MariaDB | RDS MariaDB | DTS Data TransmissionService | Data | Medium |
| GaussDB(for MySQL) | PolarDB MySQL | DTS Data TransmissionService | Data | Medium |
| GaussDB(for PostgreSQL) | PolarDB PostgreSQL | DTS Data TransmissionService | Data | High |
| GaussDB（Distributed） | PolarDB-X Distributed Database | DTS Data TransmissionService | Data | High |
| DCS Redis | ApsaraDB Redis Edition | DTS/redis-shake | Cache | Medium |
| DCS Memcached | ApsaraDB Memcache Edition | Application LayerAdaptation | Cache | Medium |
| DDS Document Database MongoDB | ApsaraDB MongoDB Edition | DTS Data TransmissionService | Data | Medium |
| GeminiDB Cassandra | Lindorm | CustomMigration | Data | High |
| GeminiDB InfluxDB | Time Series Database TSDB / Lindorm | CustomMigration | Data | High |
| GeminiDB Redis | Tair（Redis EnterpriseEdition） | DTS/redis-shake | Cache | Medium |
| Graph Engine Service GES | Graph Database GDB | Data Export/Import | Data | High |
| DAS Data Management Service | DAS Database Autonomy Service | No needMigration(Management Tool) | Operations | Low |

## Network & CDN

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| VPC VPC | VPC VPC | ManualRebuild | Network | Low |
| ELB ElasticLoad Balancer | SLB/ALB/NLB Load Balancer | ManualRebuild | Network | Low |
| NAT Gateway | NAT Gateway | ManualRebuild | Network | Low |
| EIP Elastic Public IP | Elastic Public IP (EIP) | Manual Allocation | Network | Low |
| VPN VPC | VPN Gateway | Manual Configuration | Network | Low |
| DC CloudDedicated Line | Express Connect Express Connect | Line Application | Network | High |
| CC Cloud Connect | CEN CEN / Transit Router TR | ManualRebuild | Network | Medium |
| CDN CDN | CDN CDN | Domain Switch | Network | Low |
| DNS DNS | DNS DNS | ManualRebuild | Network | Low |
| GA Global Accelerator | Global Accelerator GA | Manual Configuration | Network | Low |
| Internal DNS | PrivateZone | ManualRebuild | Network | Low |

## Messaging & Middleware

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| DMS Kafka | Message Queue Kafka Edition | MirrorMaker/Kafka Connect | Middleware | High |
| DMS RocketMQ | Message Queue RocketMQ Edition | Configuration Migration+MessageMigration | Middleware | High |
| DMS RabbitMQ | Message Queue RabbitMQ Edition | Image Migration/shovel | Middleware | Medium |
| SMN Message Notification | Message Service MNS / EventBridge EventBridge | Application LayerAdaptation | Middleware | Medium |
| EG EventGrid | EventBridge EventBridge | RuleMigration | Middleware | Medium |
| APIG API Gateway | API Gateway | Configuration Migration+Adaptation | Middleware | Medium |
| CSE Microservice Engine | Microservice Engine MSE | Configuration Migration+Adaptation | Middleware | Medium |

## Big Data & Analytics

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| DWS Data Warehouse | AnalyticDB PostgreSQL / MaxCompute | DataMigrationTool | Big Data | High |
| MRS MapReduce Service | E-MapReduce EMR | DataX/distcp | Big Data | High |
| CSS OpenSearch Elasticsearch | Elasticsearch | reindex/Snapshot Restore | Data | Medium |
| DLI Data Lake Analytics | Data Lake Analytics / MaxCompute | SQL Adaptation | Big Data | Medium |
| CloudTable (ClickHouse) | ApsaraDB ClickHouse | DataMigrationTool | Big Data | High |
| DLV Data Visualization | Quick BI | ReportRebuild | Big Data | Medium |
| DLI Flink Job | Realtime Compute Flink Edition | JobMigration+Adaptation | Big Data | High |
| DataArts Studio Data Governance | DataWorks Data Integration | TaskRebuild | Big Data | High |
| LTS CloudLog Service | Log Service SLS | Log Delivery Adaptation | Big Data | Medium |

## Security & Identity

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| IAM Unified Identity Authentication | RAM Access Control | Policy Rebuild | Security | Medium |
| DEW Data Encryption (KMS) | Key ManagementService KMS | KeyRebuild | Security | Medium |
| WAF Web Application Firewall | Web Application Firewall WAF | RuleMigration | Security | Medium |
| AAD Anti-DDoS Traffic Scrubbing | DDoS Protection Anti-DDoS | Manual Configuration | Security | Low |
| SCM SSL Certificate Management | SSL Certificate Service | Certificate Reissuance | Security | Low |
| HSS Host Security | Security Center | Manual Configuration | Security | Medium |
| CTS Cloud Audit | ActionTrail ActionTrail | Manual Configuration | Security | Low |
| CBH Cloud Bastion Host | Bastion Host | Policy Rebuild | Security | Medium |
| DBSS Database Security | Database Audit | Manual Configuration | Security | Low |

## Operations & Monitoring

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CES CloudMonitor | CloudMonitor CMS | Manual Configuration | Operations | Low |
| APM Application Performance Management | Tracing OpenTelemetry Edition | Application Adaptation | Operations | Medium |
| AOM Application Management | Application Real-Time Monitoring Service ARMS | Application Adaptation | Operations | Medium |
| RFS Resource Orchestration | Resource Orchestration ROS / Terraform | Template Conversion | Operations | Medium |
| COC Operations Center | Cloud Assistant / Operation Orchestration OOS | ManualRebuild | Operations | Low |
| Billing Center | Billing Center / Cost Manager | — | Operations | Low |

## AI & Machine Learning

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| ModelArts | PAI Machine Learning Platform | Model Export/Import | AI | High |
| Pangu Models | Model Studio / DashScope | API Adaptation | AI | Medium |
| Face Recognition FRS | Vision Intelligence Platform | API Adaptation | AI | Medium |
| Machine Translation | Machine Translation | API Adaptation | AI | Low |
| Speech Interaction SIS | Intelligent Speech Interaction | API Adaptation | AI | Medium |
| NLP NLP | NLP Self-learning Platform | API Adaptation | AI | Medium |

## Other

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Workspace Cloud Desktop | Wuying Cloud Desktop | Image Migration | Other | Medium |
| CodeArts | Yunxiao Flow + Codeup | Pipeline/RepositoryMigration | DevOps | Medium |
| IoTDA Device Access | IoT Platform IoT Platform | DeviceMigration+RuleRebuild | IoT | High |
| Domain Registration Domains | Domain Name Service | Domain Transfer | Other | Low |
