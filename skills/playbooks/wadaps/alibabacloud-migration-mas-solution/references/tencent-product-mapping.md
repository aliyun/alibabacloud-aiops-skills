# Tencent Cloud Product to Alibaba Cloud Product Mapping and Migration Methods

Self-hostedKafka Via MirrorMaker migrate to Self-hostedKafka

| Source Cloud | Product & Middleware | Target Alibaba Cloud | Cloud Product | Migration Method | Applicable Scenario |
| --- | --- | --- | --- | --- | --- |
| Tencent Cloud | CVM | Alibaba Cloud | ECS | SMC | |
| Tencent Cloud | API Gateway | Alibaba Cloud | API Gateway | Reconfigure | |
| Tencent Cloud | CFS | Alibaba Cloud | NAS | Online Migration Service | |
| Tencent Cloud | COS | Alibaba Cloud | OSS | Online Migration Service | |
| Tencent Cloud | ElasticSearch | Alibaba Cloud | ElasticSearch | Snapshot method | for large data volume scenarios |
| Tencent Cloud | ElasticSearch | Alibaba Cloud | ElasticSearch | Logstash | results need to be filtered |
| Tencent Cloud | Message QueueCKafka | Alibaba Cloud | Message QueueKafkaEdition | Kafkaconsole migration tool | |
| Tencent Cloud | NAT Gateway | Alibaba Cloud | NAT Gateway | Configure on Alibaba Cloud | |
| Tencent Cloud | MongoDB | Alibaba Cloud | ApsaraDB for MongoDB | DTS | |
| Tencent Cloud | PostgreSQL | Alibaba Cloud | RDS PostgreSQL | DTS | |
| Tencent Cloud | TDSQL-MySQL | Alibaba Cloud | PolarDB MySQLEdition | DTS | |
| Tencent Cloud | TencentDB for Redis | Alibaba Cloud | Redis Open Source Edition | Redis Shake | |
| Tencent Cloud | TencentDB for MySQL | Alibaba Cloud | RDS MySQL | DTS | |
| Tencent Cloud | TencentDB for SQL Server | Alibaba Cloud | RDS SQL Server | DTS | |
| Tencent Cloud | TencentDB for PostgreSQL | Alibaba Cloud | RDS PostgreSQL | DTS | |
| Tencent Cloud | TencentDB for MariaDB | Alibaba Cloud | RDS MariaDB | DTS | |
| Tencent Cloud | TDSQL PostgreSQLEdition | Alibaba Cloud | PolarDB PostgreSQLEdition | DTS | |
| Tencent Cloud | TencentDB for Memcached | Alibaba Cloud | ApsaraDBMemcacheEdition | Configure on Alibaba Cloud | |
| Tencent Cloud | TKE | Alibaba Cloud | ACK | Redeploy | |
| Tencent Cloud | VPN Connect | Alibaba Cloud | VPNGateway | Configure on Alibaba Cloud | |
| Tencent Cloud | Cloud FunctionSCF | Alibaba Cloud | Function Compute | Configure on Alibaba Cloud | |
| Tencent Cloud | CBS | Alibaba Cloud | EBS | Rsync | |
| Tencent Cloud | Cloud Connect Network CCN | Alibaba Cloud | CEN | Configure on Alibaba Cloud | |
| Tencent Cloud | EIP | Alibaba Cloud | EIP | Configure on Alibaba Cloud | |
| Tencent Cloud | CDN | Alibaba Cloud | CDN | Configure on Alibaba Cloud | |
| Tencent Cloud | ElasticMapReduce | Alibaba Cloud | E-MapReduce | Configure on Alibaba Cloud | |
| Tencent Cloud | Log ServiceCLS | Alibaba Cloud | SLS | Configure on Alibaba Cloud | |
| Tencent Cloud | Load Balancer CLB | Alibaba Cloud | SLB/NLB/ALB | Configure on Alibaba Cloud | |
| Tencent Cloud | Auto Scaling AS | Alibaba Cloud | Auto Scaling ESS | Configure on Alibaba Cloud | |
| Tencent Cloud | Batch Compute Batch | Alibaba Cloud | Batch Compute BatchCompute | Configure on Alibaba Cloud | |
| Tencent Cloud | VPC | Alibaba Cloud | VPC | Configure on Alibaba Cloud | |
| Tencent Cloud | Archive Storage | Alibaba Cloud | HBR | Configure on Alibaba Cloud | |
| Tencent Cloud | Storage Gateway | Alibaba Cloud | Cloud Storage Gateway CSG | Configure on Alibaba Cloud | |
| Tencent Cloud | Time Series DatabaseCTSDB | Alibaba Cloud | Lindorm | Configure on Alibaba Cloud | |
| Tencent Cloud | TCR | Alibaba Cloud | ACR | source image importOSSmethod | |
| Tencent Cloud | Configuration Center TSE | Alibaba Cloud | MSE Nacos | Configure on Alibaba Cloud | |
| Tencent Cloud | Microservice Platform TSF | Alibaba Cloud | MSE | Configure on Alibaba Cloud | |
| Tencent Cloud | Message QueueTDMQ | Alibaba Cloud | Message QueueRocketMQEdition | Configure on Alibaba Cloud | |
| Tencent Cloud | Message QueuePulsarEdition | Alibaba Cloud | Message QueueRocketMQEdition | Configure on Alibaba Cloud | |
| Tencent Cloud | Message QueueRabbitMQEdition | Alibaba Cloud | Message QueueRabbitMQEdition | export/importmigrate metadata | |
| Tencent Cloud | Message QueueRocketMQEdition | Alibaba Cloud | Message QueueRocketMQEdition | Message QueueRocketMQcloud migration tool | |
| Tencent Cloud | TCM | Alibaba Cloud | ASM | Configure on Alibaba Cloud | |
| Tencent Cloud | Cloud Data WarehousePostgreSQL | Alibaba Cloud | ADB / Hologres | OSSrelay method | |
| Tencent Cloud | Cloud Data Warehouse ClickHouse | Alibaba Cloud | ApsaraDBClickHouse | console migration | |
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
| Self-hosted | Oracle | Self-hosted | Oracle | Configure on Alibaba Cloud | |
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