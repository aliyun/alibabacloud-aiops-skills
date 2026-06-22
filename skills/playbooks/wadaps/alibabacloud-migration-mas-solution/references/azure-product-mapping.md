# Azure Product to Alibaba Cloud Product Mapping and Migration Methods

# Azure Product to Alibaba Cloud Product Mapping and Migration Methods

| Source Cloud | Product & Middleware | Target Alibaba Cloud | Cloud Product | Migration Method | Applicable Scenario |
| --- | --- | --- | --- | --- | --- |
| Azure | Virtual Machine | Alibaba Cloud | ECS | SMC | |
| Azure | Azure Compute Gallery | Alibaba Cloud | ESS | onConfigure on Alibaba Cloud | |
| Azure | Batch | Alibaba Cloud | BatchCompute | Configure on Alibaba Cloud | |
| Azure | Virtual Network | Alibaba Cloud | VPC | Configure on Alibaba Cloud | |
| Azure | Azure ExpressRoute | Alibaba Cloud | Express Connect | Configure on Alibaba Cloud | |
| Azure | ER Gateway | Alibaba Cloud | VBR | Configure on Alibaba Cloud | |
| Azure | VPN Gateway | Alibaba Cloud | VPN Gateway | Configure on Alibaba Cloud | |
| Azure | ER Global Reach | Alibaba Cloud | CEN | Configure on Alibaba Cloud | |
| Azure | CDN | Alibaba Cloud | CDN | Configure on Alibaba Cloud | |
| Azure | Azure DNS | Alibaba Cloud | DNSDNS | Configure on Alibaba Cloud | |
| Azure | Disk Storage | Alibaba Cloud | EBS | Rsync | |
| Azure | Blob | Alibaba Cloud | OSS | Online Migration Service | |
| Azure | Azure File | Alibaba Cloud | NAS | Online Migration Service | |
| Azure | File Storage | Alibaba Cloud | NAS | Online Migration Service | |
| Azure | SQL | Alibaba Cloud | RDS SQL Server | DTS | |
| Azure | Azure Database for MySQL | Alibaba Cloud | RDS MySQL | DTS | |
| Azure | Azure Database for PostgreSQL | Alibaba Cloud | RDS PostgreSQL | DTS | |
| Azure | Azure Database for MariaDB | Alibaba Cloud | RDS MariaDB | DTS | |
| Azure | Azure Cache for Redis | Alibaba Cloud | ApsaraDB for Redis | Redis-Shake | |
| Azure | CassandraManaged Instance | Alibaba Cloud | ApsaraDBCassandraEdition | ViaCopycommand migration | |
| Azure | Time series insights | Alibaba Cloud | Lindorm | Configure on Alibaba Cloud | |
| Azure | CosmosDB | Alibaba Cloud | ApsaraDB MongoDBEdition | backup and restoremethod migration | |
| Azure | AKS | Alibaba Cloud | ACK | Redeploy | |
| Azure | Azure Container Registry | Alibaba Cloud | ACR | source image importOSSmethod | |
| Azure | Azure Functions | Alibaba Cloud | Function Compute | Configure on Alibaba Cloud | |
| Azure | LB | Alibaba Cloud | SLB/NLB/ALB | Configure on Alibaba Cloud | |
| Azure | Elastic | Alibaba Cloud | ElasticSearch | Snapshot method | for large data volume scenarios |
| Azure | Elastic | Alibaba Cloud | ElasticSearch | Logstash | results need to be filtered |
| Azure | OCR | Alibaba Cloud | OCR | Configure on Alibaba Cloud | |
| Azure | Application Gateway | Alibaba Cloud | ALB | Configure on Alibaba Cloud | |
| | | | | | |

# AzureSelf-hostedmiddleware staysMigrationmethod to migrate to cloudMigration Method

| Self-hosted | MySQL | Self-hosted | MySQL | DTS | |
| --- | --- | --- | --- | --- | --- |
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