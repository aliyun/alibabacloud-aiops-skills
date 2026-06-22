# Huawei Cloud Product to Alibaba Cloud Product Mapping and Migration Methods

# Huawei Cloud Product to Alibaba Cloud Product Mapping and Migration Methods

| Source Cloud | Product & Middleware | Target Alibaba Cloud | Cloud Product | Migration Method | Applicable Scenario |
| --- | --- | --- | --- | --- | --- |
| Huawei Cloud | CCE | Alibaba Cloud | ACK | Redeploy | |
| Huawei Cloud | CDN | Alibaba Cloud | CDN | Configure on Alibaba Cloud | |
| Huawei Cloud | DDS | Alibaba Cloud | ApsaraDB for MongoDB | DTS | |
| Huawei Cloud | ECS | Alibaba Cloud | ECS | SMC | |
| Huawei Cloud | Auto ScalingAS | Alibaba Cloud | Auto ScalingESS | Configure on Alibaba Cloud | |
| Huawei Cloud | VPC | Alibaba Cloud | VPC | Configure on Alibaba Cloud | |
| Huawei Cloud | NAT | Alibaba Cloud | NATGateway | Configure on Alibaba Cloud | |
| Huawei Cloud | EIP | Alibaba Cloud | EIP | Configure on Alibaba Cloud | |
| Huawei Cloud | VPN | Alibaba Cloud | VPNGateway | Configure on Alibaba Cloud | |
| Huawei Cloud | Cloud ConnectCC | Alibaba Cloud | CENCEN | Configure on Alibaba Cloud | |
| Huawei Cloud | EVS | Alibaba Cloud | EBS | Rsync | |
| Huawei Cloud | OBS | Alibaba Cloud | OSS | Online Migration Service | |
| Huawei Cloud | SFS | Alibaba Cloud | NAS | Online Migration Service | |
| Huawei Cloud | Cloud Backup CBR | Alibaba Cloud | Cloud Backup HBR | Configure on Alibaba Cloud | |
| Huawei Cloud | Cloud Storage Gateway CSG | Alibaba Cloud | Cloud Storage Gateway CSG | Configure on Alibaba Cloud | |
| Huawei Cloud | ApsaraDB MySQL | Alibaba Cloud | RDS MySQL | DTS | |
| Huawei Cloud | ApsaraDBSQL Server | Alibaba Cloud | RDS SQL Server | DTS | |
| Huawei Cloud | ApsaraDBPostgreSQL | Alibaba Cloud | RDS PostgreSQL | DTS | |
| Huawei Cloud | GaussDB for MySQL | Alibaba Cloud | PolarDB MySQLEdition | DTS | |
| Huawei Cloud | GaussDB for Redis | Alibaba Cloud | ApsaraDB for Redis | DTS | |
| Huawei Cloud | Distributed Cache ServiceMemcachedEdition | Alibaba Cloud | ApsaraDBMemcacheEdition | Configure on Alibaba Cloud | |
| Huawei Cloud | GaussDB for Cassandra | Alibaba Cloud | ApsaraDBCassandraEdition | ViaCopycommand migration | |
| Huawei Cloud | Table Store ServiceCloudTable | Alibaba Cloud | Table StoreTableStore | Configure on Alibaba Cloud | |
| Huawei Cloud | SWR | Alibaba Cloud | ACR | source image importOSS | |
| Huawei Cloud | AOS | Alibaba Cloud | ROS | Configure on Alibaba Cloud | |
| Huawei Cloud | Function Workflow | Alibaba Cloud | Function Compute | Configure on Alibaba Cloud | |
| Huawei Cloud | CSE | Alibaba Cloud | MSE | Configure on Alibaba Cloud | |
| Huawei Cloud | APIG | Alibaba Cloud | APIGateway | Configure on Alibaba Cloud | |
| Huawei Cloud | 4LayerLoad Balancer | Alibaba Cloud | NLB | Configure on Alibaba Cloud | |
| Huawei Cloud | 7LayerLoad Balancer | Alibaba Cloud | ALB | Configure on Alibaba Cloud | |
| Huawei Cloud | 4LayerELB | Alibaba Cloud | NLB | Configure on Alibaba Cloud | |
| Huawei Cloud | 7LayerELB | Alibaba Cloud | ALB | Configure on Alibaba Cloud | |
| Huawei Cloud | DistributedMessage QueueRabbitMQEdition | Alibaba Cloud | Message QueueRabbitMQEdition | migrate via export/import | |
| Huawei Cloud | DistributedMessage QueueRocketMQEdition | Alibaba Cloud | Message QueueRocketMQEdition | Alibaba Cloudofficial migration tool | |
| Huawei Cloud | DistributedMessage QueueKafkaEdition | Alibaba Cloud | Message QueueKafkaEdition | Kafkaconsole migration tool | |
| Huawei Cloud | LTS | Alibaba Cloud | SLS | Configure on Alibaba Cloud | |
| Huawei Cloud | MapReduceServiceMRS | Alibaba Cloud | E-MapReduce | Configure on Alibaba Cloud | |
| Huawei Cloud | DWS | Alibaba Cloud | ADB | Online Migration Service | |
| Huawei Cloud | DWS | Alibaba Cloud | Hologres | Online Migration Service | |
| Huawei Cloud | DDM | Alibaba Cloud | Polar-X | internal migration tool | |
| Huawei Cloud | CSS | Alibaba Cloud | ElasticSearch | Snapshot method | for large data volume scenarios |
| Huawei Cloud | CSS | Alibaba Cloud | ElasticSearch | Logstash | results need to be filtered |
| Huawei Cloud | DCS | Alibaba Cloud | ApsaraDB for Redis | RedisShake | |
| Huawei Cloud | Security Group | Alibaba Cloud | Security Group | Configure on Alibaba Cloud | |
| Huawei Cloud | subnet | Alibaba Cloud | vSwitch | Configure on Alibaba Cloud | |
| Huawei Cloud | CAE | Alibaba Cloud | SAE | Configure on Alibaba Cloud | |
| Huawei Cloud | Bandwidth | Alibaba Cloud | Shared Bandwidth | Configure on Alibaba Cloud | |
| Huawei Cloud | Simple Message NotificationSMN | Alibaba Cloud | LightweightMessage Queue | Configure on Alibaba Cloud | |
| Huawei Cloud | WAF | Alibaba Cloud | WAF | Configure on Alibaba Cloud | |

# Huawei CloudSelf-hostedmiddleware staysMigrationmethod to migrate to cloudMigration Method

| Source Cloud | Product & Middleware | Target Alibaba Cloud | Cloud Product | Migration Method | Applicable Scenario |
| --- | --- | --- | --- | --- | --- |
| Self-hosted | MySQL | Self-hosted | MySQL | DTS | |
| Self-hosted | SQL Server | Self-hosted | SQL Server | DTS | |
| Self-hosted | PostgreSQL | Self-hosted | PostgreSQL | DTS | |
| Self-hosted | Redis | Self-hosted | Redis | RedisShake | |
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