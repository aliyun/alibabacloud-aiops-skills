# AWS → Alibaba Cloud Product Mapping

## Compute

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| EC2 | ECS | SMC Server Migration Center | Compute | Medium |
| EC2 Auto Scaling | Auto Scaling ESS | Policy Rebuild | Compute | Low |
| EC2 Spot Instances | Preemptible Instance | Policy Rebuild | Compute | Low |
| Lightsail | Simple Application Server SWAS | Manual Migration | Compute | Medium |
| EKS Container Service | ACK Container Service | Image Migration+YAML Migration | Compute | High |
| ECS (Fargate) | Serverless Container ASK | YAML Migration+Adaptation | Compute | High |
| ECR Container Registry | Container Registry ACR | Image Sync Tool | Compute | Low |
| Lambda Function Compute | Function Compute FC | CodeMigration+Adaptation | Compute | High |
| Elastic Beanstalk | SAE Application Engine | Application Redeployment | Compute | Medium |
| App Runner | SAE Application Engine | Application Redeployment | Compute | Medium |

## Storage

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| S3 Object Storage | OSS Object Storage | Online MigrationService/ossimport | Storage | Low |
| S3 Glacier | OSS Archive/Deep Cold Archive | Online MigrationService | Storage | Low |
| EBS ElasticBlock Storage | ESSD Cloud Disk | SMC withInstanceMigration | Storage | Low |
| EFS Elastic File System | NAS File Storage | DataMigrationTool/nasimport | Storage | Medium |
| FSx for Windows | NAS SMB Protocol | DataMigrationTool | Storage | Medium |
| FSx for Lustre | CPFS Parallel File System | DataMigration | Storage | Medium |
| Storage Gateway | Cloud StorageGateway CSG | SolutionRebuild | Storage | Medium |
| AWS Backup | Cloud Backup HBR | Policy Rebuild | Storage | Low |

## Database

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| RDS MySQL | RDS MySQL / PolarDB MySQL | DTS Data TransmissionService | Data | Medium |
| RDS PostgreSQL | RDS PostgreSQL / PolarDB PostgreSQL | DTS Data TransmissionService | Data | Medium |
| RDS MariaDB | RDS MariaDB | DTS Data TransmissionService | Data | Medium |
| RDS Oracle | RDS PPAS / PolarDB-O | DTS + ADAM MigrationAssessment | Data | High |
| RDS SQL Server | RDS SQL Server | DTS Data TransmissionService | Data | Medium |
| Aurora MySQL | PolarDB MySQL | DTS Data TransmissionService | Data | Medium |
| Aurora PostgreSQL | PolarDB PostgreSQL | DTS Data TransmissionService | Data | Medium |
| DynamoDB | Tablestore Tablestore / Lindorm | CustomMigration/EMR | Data | High |
| DocumentDB | ApsaraDB MongoDB Edition | DTS Data TransmissionService | Data | Medium |
| ElastiCache Redis | ApsaraDB Redis Edition | DTS/redis-shake | Cache | Medium |
| ElastiCache Memcached | ApsaraDB Memcache Edition | Application LayerAdaptation | Cache | Medium |
| MemoryDB for Redis | Tair（Redis EnterpriseEdition） | DTS/redis-shake | Cache | Medium |
| Neptune (Graph Database) | Graph Database GDB | Data Export/Import | Data | High |
| Timestream | Time Series Database TSDB / Lindorm | CustomMigration | Data | High |

## Network & CDN

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| VPC | VPC VPC | ManualRebuild | Network | Low |
| Internet Gateway | Public IP / EIP | Manual Configuration | Network | Low |
| NAT Gateway | NAT Gateway | ManualRebuild | Network | Low |
| ELB/ALB/NLB | SLB/ALB/NLB Load Balancer | ManualRebuild | Network | Low |
| Route 53 | DNS DNS | DomainMigration | Network | Low |
| CloudFront | CDN CDN | Domain Switch | Network | Low |
| Direct Connect | Express Connect Express Connect | Line Application | Network | High |
| VPN Gateway | VPN Gateway | Manual Configuration | Network | Low |
| Transit Gateway | CEN CEN / Transit Router TR | ManualRebuild | Network | Medium |
| Elastic IP | Elastic Public IP (EIP) | Manual Allocation | Network | Low |
| Global Accelerator | Global Accelerator GA | Manual Configuration | Network | Low |

## Messaging & Middleware

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| MSK (Kafka) | Message Queue Kafka Edition | MirrorMaker/Kafka Connect | Middleware | High |
| SQS Message Queue | Message Queue RocketMQ Edition | Application LayerAdaptation | Middleware | High |
| SNS Notification Service | Message Service MNS / EventBridge EventBridge | Application LayerAdaptation | Middleware | High |
| EventBridge | EventBridge EventBridge | RuleMigration | Middleware | Medium |
| MQ (RabbitMQ) | Message Queue RabbitMQ Edition | Image Migration/shovel | Middleware | Medium |
| Step Functions | Serverless Workflow | WorkflowRebuild | Middleware | High |
| API Gateway | API Gateway | Configuration Migration | Middleware | Medium |

## Big Data & Analytics

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| Redshift | MaxCompute / AnalyticDB | DataX/DataWorks | Big Data | High |
| EMR (Hadoop/Spark) | E-MapReduce EMR | DataX/distcp | Big Data | High |
| Athena | Data Lake Analytics / MaxCompute | SQL Adaptation | Big Data | Medium |
| Glue (ETL) | DataWorks Data Integration | TaskRebuild | Big Data | High |
| QuickSight | Quick BI | ReportRebuild | Big Data | Medium |
| OpenSearch Service | Elasticsearch / OpenSearch | reindex/Snapshot Restore | Data | Medium |
| Kinesis Data Streams | Log Service SLS / DataHub | Application LayerAdaptation | Big Data | High |

## Security & Identity

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| IAM | RAM Access Control | Policy Rebuild | Security | Medium |
| KMS Key Management | Key ManagementService KMS | KeyRebuild | Security | Medium |
| WAF | Web Application Firewall WAF | RuleMigration | Security | Medium |
| Shield (DDoS) | DDoS Protection Anti-DDoS | Manual Configuration | Security | Low |
| Certificate Manager | SSL Certificate Service | Certificate Reissuance | Security | Low |
| GuardDuty | Security Center | Manual Configuration | Security | Medium |
| CloudTrail | ActionTrail ActionTrail | Manual Configuration | Security | Low |

## Operations & Monitoring

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| CloudWatch | CloudMonitor CMS | Manual Configuration | Operations | Low |
| CloudWatch Logs | Log Service SLS | Log Delivery Adaptation | Operations | Medium |
| X-Ray | Tracing OpenTelemetry Edition | Application Adaptation | Operations | Medium |
| CloudFormation | Resource Orchestration ROS / Terraform | Template Conversion | Operations | Medium |
| Systems Manager | Operation Orchestration OOS | ManualRebuild | Operations | Medium |
| Cost Explorer | Billing Center / Cost Manager | — | Operations | Low |

## AI & Machine Learning

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| SageMaker | PAI Machine Learning Platform | Model Export/Import | AI | High |
| Bedrock | Model Studio / DashScope | API Adaptation | AI | Medium |
| Rekognition | Vision Intelligence Platform | API Adaptation | AI | Medium |
| Translate | Machine Translation | API Adaptation | AI | Low |

## Other

| Source Product | Alibaba Cloud Product | Recommended Migration Tool | Layer | Complexity |
|---------|-----------|------------|---------|-------|
| WorkSpaces | Wuying Cloud Desktop | Image Migration | Other | Medium |
| CodePipeline | Yunxiao Flow | Pipeline Rebuild | DevOps | Medium |
| CodeCommit | Yunxiao Codeup | RepositoryMigration | DevOps | Low |
| IoT Core | IoT Platform IoT Platform | DeviceMigration+RuleRebuild | IoT | High |
