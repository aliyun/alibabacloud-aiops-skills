# AWS Product to Alibaba Cloud Product Mapping and Migration Methods

| Source Cloud | Product & Middleware | Target | Cloud Product | Migration Method | Applicable Scenario |
| --- | --- | --- | --- | --- | --- |
| AWS | DocumentDB | Alibaba Cloud | ApsaraDB for MongoDB | DTS | |
| AWS | Airflow | Alibaba Cloud | DataWorks | Configure on Alibaba Cloud | |
| AWS | EC2 | Alibaba Cloud | ECS | SMC | |
| AWS | EFS | Alibaba Cloud | NAS | Online Migration Service | |
| AWS | EIP | Alibaba Cloud | EIP | Configure on Alibaba Cloud | |
| AWS | EKS | Alibaba Cloud | ACK | Redeploy | |
| AWS | ElastiCache | Alibaba Cloud | ApsaraDB for Redis | Redis-Shake | |
| AWS | ALB | Alibaba Cloud | ALB | Configure on Alibaba Cloud | |
| AWS | NLB | Alibaba Cloud | NLB | Configure on Alibaba Cloud | |
| AWS | CLB | Alibaba Cloud | CLB | Configure on Alibaba Cloud | |
| AWS | Kafka（MSK） | Alibaba Cloud | Message QueueKafkaEdition | Kafkaconsole migration tool | |
| AWS | Lambda | Alibaba Cloud | Function Compute | Configure on Alibaba Cloud | |
| AWS | NAT Gateway | Alibaba Cloud | NAT Gateway | Configure on Alibaba Cloud | |
| AWS | OpenSearch（ElasticSearch） | Alibaba Cloud | ElasticSearch | Logstash | |
| AWS | OpenSearch（ElasticSearch） | Alibaba Cloud | ElasticSearch | OSSSnapshot | |
| AWS | RDS for SQL Server | Alibaba Cloud | RDS SQL Server | DTS | |
| AWS | RDS for MySQL | Alibaba Cloud | RDS MySQL | DTS | |
| AWS | RDS for PostgreSQL | Alibaba Cloud | RDS PostgreSQL | DTS | |
| AWS | RDS for MariaDB | Alibaba Cloud | RDS MariaDB | DTS | |
| AWS | RDS for Oracle | Alibaba Cloud | PolarDB Oracle | DTS | |
| AWS | RDS for Db2 | Alibaba Cloud | PolarDB MySQL | DTS | |
| AWS | Aurora MySQL | Alibaba Cloud | RDS MySQL | DTS | |
| AWS | Aurora PostgreSQL | Alibaba Cloud | RDS PostgreSQL | DTS | |
| AWS | MemoryDB | Alibaba Cloud | ApsaraDBRedis Edition | DTS | |
| AWS | Redshift | Alibaba Cloud | Hologres | Data Integration | |
| AWS | S3 | Alibaba Cloud | OSS | Online Migration Service | |
| AWS | SQS | Alibaba Cloud | LightweightMessage Queue（NativeMNS） | Configure on Alibaba Cloud | |
| AWS | SNS | Alibaba Cloud | LightweightMessage Queue（NativeMNS） | Configure on Alibaba Cloud | |
| AWS | Auto Scaling | Alibaba Cloud | ESS | Configure on Alibaba Cloud | |
| AWS | ECS | Alibaba Cloud | SAE | Configure on Alibaba Cloud | |
| AWS | DynamoDB | Alibaba Cloud | ApsaraDB for MongoDB | NimoShake | |
| AWS | Batch | Alibaba Cloud | Batch Compute | Configure on Alibaba Cloud | |
| AWS | VPC | Alibaba Cloud | VPC | Configure on Alibaba Cloud | |
| AWS | VPN | Alibaba Cloud | VPN Gateway | Configure on Alibaba Cloud | |
| AWS | CloudFront | Alibaba Cloud | CDN | Configure on Alibaba Cloud | |
| AWS | Route 53 | Alibaba Cloud | DNSDNS | Configure on Alibaba Cloud | |
| AWS | Elastic Block Store | Alibaba Cloud | EBS | Rsync | |
| AWS | Backup | Alibaba Cloud | Cloud Backup HBR | Configure on Alibaba Cloud | |
| AWS | Timestream | Alibaba Cloud | Lindorm | Configure on Alibaba Cloud | |
| AWS | Neptune | Alibaba Cloud | Graph Database GDB | Configure on Alibaba Cloud | |
| AWS | KMS | Alibaba Cloud | KMS | Configure on Alibaba Cloud | |
| AWS | ECR | Alibaba Cloud | ACR | source image importOSSmethod | |
| AWS | Fargate | Alibaba Cloud | ECI | Configure on Alibaba Cloud | |
| AWS | CloudFormation | Alibaba Cloud | OOS | Configure on Alibaba Cloud | |
| AWS | API Gateway | Alibaba Cloud | API Gateway | Configure on Alibaba Cloud | |
| AWS | EMR | Alibaba Cloud | E-MapReduce | Configure on Alibaba Cloud | |
| AWS | QuickSight | Alibaba Cloud | QuickBI | Configure on Alibaba Cloud | |
| AWS | EventBridge | Alibaba Cloud | EventBridge | Configure on Alibaba Cloud | |
| Self-hosted | MySQL | Self-hosted | MySQL | DTS | |
| Self-hosted | SQL Server | Self-hosted | SQL Server | DTS | |
| Self-hosted | PostgreSQL | Self-hosted | PostgreSQL | DTS | |
| Self-hosted | Redis | Self-hosted | Redis | Redis-Shake | |
| Self-hosted | MongoDB | Self-hosted | MongoDB | Mongo-Shake | |
| Self-hosted | K8S | Self-hosted | K8S | Redeploy | |
| Self-hosted | ElasticSearch | Self-hosted | ElasticSearch | Snapshot method | for large data volume scenarios |
| Self-hosted | ElasticSearch | Self-hosted | ElasticSearch | Logstash | results need to be filtered |
| Self-hosted | Kafka | Self-hosted | Kafka | MirrorMaker | |
| Self-hosted | RabbitMQ | Self-hosted | RabbitMQ | export/import metadata migration | |
| Self-hosted | RocketMQ | Self-hosted | RocketMQ | metadata export/import method | |
| Self-hosted | MariaDB | Self-hosted | MariaDB | DTS | |
| Self-hosted | Oracle | Self-hosted | Oracle | | |
| Self-hosted | ClickHouse | Self-hosted | ClickHouse | ClickHousebuilt-in migration tool | |
| Self-hosted | Zookeeper | Self-hosted | Zookeeper | backup and restore | |
| Self-hosted | Nacos | Self-hosted | Nacos | backup and restore | |
| Self-hosted | Docker | Self-hosted | ACK | Redeploy | |
| Self-hosted | Apollo | Self-hosted | Apollo | export/import | |
| Self-hosted | Consul | Self-hosted | Consul | export/import | |
| Self-hosted | Dubbo Nacos | Self-hosted | Dubbo Nacos | backup and restore | |
| Self-hosted | Eureka | Self-hosted | Eureka | Configure on Alibaba Cloud | |
| Self-hosted | MQTT | Self-hosted | MQTT | Configure on Alibaba Cloud | |
| Self-hosted | Nginx | Self-hosted | Nginx | Redeploy | |
| Self-hosted | Habor | Self-hosted | Habor | Configure on Alibaba Cloud | |
| Self-hosted | Hbase | Self-hosted | Hbase | export/import | |