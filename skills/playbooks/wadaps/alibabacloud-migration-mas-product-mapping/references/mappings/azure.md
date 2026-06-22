# Azure → Alibaba Cloud Product Mapping

## Compute

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Virtual Machines | ECS | SMC Server Migration Center | Compute | Medium |
| Virtual Machine Scale Sets | Auto Scaling ESS | Policy Rebuild | Compute | Low |
| Azure Spot Virtual Machines | Preemptible Instance | Policy Rebuild | Compute | Low |
| Azure Kubernetes Service (AKS) | ACK Container Service | Image Migration+YAML Migration | Compute | High |
| Azure Container Instances | ECI Elastic Container Instance / Serverless Container ASK | Image Migration+Configuration Adaptation | Compute | Medium |
| Azure Container Registry | Container Registry ACR | Image Sync Tool | Compute | Low |
| Azure Functions | Function Compute FC | CodeMigration+Adaptation | Compute | High |
| Azure App Service | SAE Application Engine | Application Redeployment | Compute | Medium |
| Azure Spring Apps | SAE Application Engine / EDAS | Application Redeployment | Compute | Medium |
| Azure Batch | Batch Compute BatchCompute | TaskRebuild | Compute | Medium |

## Storage

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Blob Storage | OSS Object Storage | Online MigrationService/ossimport | Storage | Low |
| Azure Blob Cool/Archive | OSS Infrequent Access/Archive/Deep Cold Archive | Online MigrationService | Storage | Low |
| Managed Disks Managed Disk | ESSD Cloud Disk | SMC withInstanceMigration | Storage | Low |
| Azure Files | NAS File Storage | DataMigrationTool/nasimport | Storage | Medium |
| Azure NetApp Files | NAS Ultra/CPFS | DataMigration | Storage | Medium |
| Azure Data Box | Lightning Cube/DataMigrationService | Offline Migration | Storage | Medium |
| Azure Backup | Cloud Backup HBR | Policy Rebuild | Storage | Low |

## Database

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Database for MySQL | RDS MySQL / PolarDB MySQL | DTS Data TransmissionService | Data | Medium |
| Azure Database for PostgreSQL | RDS PostgreSQL / PolarDB PostgreSQL | DTS Data TransmissionService | Data | Medium |
| Azure SQL Database | RDS SQL Server | DTS Data TransmissionService | Data | Medium |
| Azure SQL Managed Instance | RDS SQL Server (High AvailabilityEdition) | DTS Data TransmissionService | Data | High |
| Azure Database for MariaDB | RDS MariaDB | DTS Data TransmissionService | Data | Medium |
| Azure Cosmos DB (MongoDB API) | ApsaraDB MongoDB Edition | DTS Data TransmissionService | Data | High |
| Azure Cosmos DB (Table API) | Tablestore Tablestore | CustomMigration | Data | High |
| Azure Cosmos DB (Cassandra API) | Lindorm | CustomMigration | Data | High |
| Azure Cache for Redis | ApsaraDB Redis Edition | DTS/redis-shake | Cache | Medium |
| Azure Managed Instance for Apache Cassandra | Lindorm | CustomMigration | Data | High |
| Azure Time Series Insights | Time Series Database TSDB / Lindorm | CustomMigration | Data | High |

## Network & CDN

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Virtual Network (VNet) | VPC VPC | ManualRebuild | Network | Low |
| Azure Load Balancer | SLB/NLB Load Balancer | ManualRebuild | Network | Low |
| Application Gateway | ALB ApplicationLoad Balancer | ManualRebuild | Network | Low |
| NAT Gateway | NAT Gateway | ManualRebuild | Network | Low |
| Public IP Address | Elastic Public IP (EIP) | Manual Allocation | Network | Low |
| VPN Gateway | VPN Gateway | Manual Configuration | Network | Low |
| ExpressRoute | Express Connect Express Connect | Line Application | Network | High |
| Virtual WAN | CEN CEN / Transit Router TR | ManualRebuild | Network | Medium |
| Azure CDN | CDN CDN | Domain Switch | Network | Low |
| Azure DNS | DNS DNS | ManualRebuild | Network | Low |
| Azure Front Door | Global Accelerator GA / DCDN | Manual Configuration | Network | Medium |
| Azure Private DNS | PrivateZone | ManualRebuild | Network | Low |

## Messaging & Middleware

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Event Hubs (Kafka) | Message Queue Kafka Edition | MirrorMaker/Kafka Connect | Middleware | High |
| Azure Service Bus | Message Queue RocketMQ Edition | Application LayerAdaptation | Middleware | High |
| Azure Queue Storage | Message Service MNS | Application LayerAdaptation | Middleware | Medium |
| Azure Event Grid | EventBridge EventBridge | RuleMigration | Middleware | Medium |
| Azure API Management | API Gateway | Configuration Migration+Adaptation | Middleware | Medium |
| Azure Logic Apps | Serverless Workflow | WorkflowRebuild | Middleware | High |

## Big Data & Analytics

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Synapse Analytics | MaxCompute / AnalyticDB | DataX/DataWorks | Big Data | High |
| Azure HDInsight | E-MapReduce EMR | DataX/distcp | Big Data | High |
| Azure Cognitive Search | Elasticsearch | reindex/Snapshot Restore | Data | Medium |
| Azure Data Lake Analytics | Data Lake Analytics / MaxCompute | SQL Adaptation | Big Data | Medium |
| Azure Databricks | EMR (Spark) / PAI | JobMigration+Adaptation | Big Data | High |
| Power BI | Quick BI | ReportRebuild | Big Data | Medium |
| Azure Stream Analytics | Realtime Compute Flink Edition | JobMigration+Adaptation | Big Data | High |
| Azure Data Factory | DataWorks Data Integration | TaskRebuild | Big Data | High |
| Azure Monitor Logs | Log Service SLS | Log Delivery Adaptation | Big Data | Medium |

## Security & Identity

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Active Directory (Entra ID) | RAM Access Control | Policy Rebuild | Security | Medium |
| Azure Key Vault | Key ManagementService KMS | KeyRebuild | Security | Medium |
| Azure WAF | Web Application Firewall WAF | RuleMigration | Security | Medium |
| Azure DDoS Protection | DDoS Protection Anti-DDoS | Manual Configuration | Security | Low |
| Azure App Service Certificates | SSL Certificate Service | Certificate Reissuance | Security | Low |
| Microsoft Defender for Cloud | Security Center | Manual Configuration | Security | Medium |
| Azure Activity Log | ActionTrail ActionTrail | Manual Configuration | Security | Low |
| Azure Bastion | Bastion Host | Policy Rebuild | Security | Medium |

## Operations & Monitoring

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Monitor | CloudMonitor CMS | Manual Configuration | Operations | Low |
| Application Insights | Tracing OpenTelemetry Edition / ARMS | Application Adaptation | Operations | Medium |
| Azure Resource Manager (ARM) | Resource Orchestration ROS / Terraform | Template Conversion | Operations | Medium |
| Azure Automation | Operation Orchestration OOS / Cloud Assistant | ManualRebuild | Operations | Medium |
| Azure Cost Management | Billing Center / Cost Manager | — | Operations | Low |

## AI & Machine Learning

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Machine Learning | PAI Machine Learning Platform | Model Export/Import | AI | High |
| Azure OpenAI Service | Model Studio / DashScope | API Adaptation | AI | Medium |
| Azure AI Vision (Computer Vision) | Vision Intelligence Platform | API Adaptation | AI | Medium |
| Azure AI Translator | Machine Translation | API Adaptation | AI | Low |
| Azure AI Speech | Intelligent Speech Interaction | API Adaptation | AI | Medium |
| Azure AI Language | NLP Self-learning Platform | API Adaptation | AI | Medium |

## Other

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Azure Virtual Desktop | Wuying Cloud Desktop | Image Migration | Other | Medium |
| Azure DevOps | Yunxiao Flow + Codeup | Pipeline/RepositoryMigration | DevOps | Medium |
| Azure IoT Hub | IoT Platform IoT Platform | DeviceMigration+RuleRebuild | IoT | High |
| Azure App Service Domains | Domain Name Service | Domain Transfer | Other | Low |
