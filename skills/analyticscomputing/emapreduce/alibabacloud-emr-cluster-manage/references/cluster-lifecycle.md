# Cluster Full Lifecycle: Planning → Creation → Management → Clone

## Table of Contents

- [1. Planning Phase](#1-planning-phase): Cluster type selection, deployment mode, node planning, disk, payment method
- [2. Creation Phase](#2-creation-phase): Dev/test / small production / large production / Spot instance four templates
- [3. Query and Monitoring](#3-query-and-monitoring): Cluster list, details, state machine
- [4. Attribute Management](#4-attribute-management): Rename, deletion protection, auto renewal
- [5. Clone Cluster](#5-clone-cluster): GetClusterCloneMeta → RunCluster two-step process

## 1. Planning Phase

### Cluster Type Selection

| Cluster Type | Use Case | Recommended Application Combination |
|---------|---------|-------------|
| **DATALAKE** | Data lake, offline batch processing, ETL, data warehouse | Typical: HADOOP-COMMON + HDFS + YARN + HIVE + SPARK3; common optional see below |
| **OLAP** | Real-time analytics, interactive query | ZOOKEEPER + engines choose multiple: STARROCKS3 (recommended) / STARROCKS2 / DORIS / CLICKHOUSE (STARROCKS2 and STARROCKS3 mutually exclusive, others can be combined) |
| **DATAFLOW** | Real-time stream processing | Typical: HADOOP-COMMON + HDFS + YARN + FLINK + OPENLDAP; optional see below (FLINK strongly depends on OPENLDAP) |
| **DATASERVING** | Data service, NoSQL storage | Typical: HADOOP-COMMON + HDFS + ZOOKEEPER + HBASE; optional see below |
| **CUSTOM** | Custom component combination | Freely select from 32 components, see below |

> **Component Selection Rules**: No mandatory required components, but need at least one service. If selected components have dependencies, must also select their dependent components (see [Component Dependencies](#component-dependencies) below).

> **Not sure which to choose?** 80% of scenarios can choose DATALAKE.

**DATALAKE Optional Components**:

| Category | Component | Description |
|------|------|------|
| Compute Engine | SPARK3 / SPARK2 | **Mutually exclusive**, cannot select both. New clusters recommend SPARK3 |
| SQL Engine | HIVE, TEZ, KYUUBI, TRINO, PRESTO | TEZ significantly accelerates Hive queries; Kyuubi provides multi-tenant Spark SQL |
| Storage | HDFS / OSS-HDFS | **Mutually exclusive**, cannot select both. OSS-HDFS suitable for storage-compute separated architecture |
| Lake Format | ICEBERG, HUDI, PAIMON, DELTALAKE | Select by data lake framework |
| Data Integration | SQOOP, FLUME | Traditional data import tools |
| Security | RANGER, KERBEROS, KNOX, OPENLDAP | Production environment recommends RANGER for permission control |
| Acceleration | JINDOCACHE, CELEBORN | JindoCache local cache acceleration; Celeborn accelerates Shuffle |
| Basic | ZOOKEEPER, MYSQL | Internal dependencies, usually auto-selected |

**DATAFLOW Optional Components**:

| Category | Component | Description |
|------|------|------|
| Storage | HDFS / OSS-HDFS | **Mutually exclusive**, cannot select both |
| Lake Format | PAIMON | Flink native lake format |
| Security | RANGER, RANGER-PLUGIN, KERBEROS, KNOX, OPENLDAP | Production environment recommends RANGER |
| Acceleration | — | — |
| Basic | ZOOKEEPER | Internal dependency |

**DATASERVING Optional Components**:

| Category | Component | Description |
|------|------|------|
| SQL Engine | PHOENIX | SQL query layer on HBase |
| Storage | HDFS / OSS-HDFS | **Mutually exclusive**, cannot select both |
| Security | RANGER, RANGER-PLUGIN, KERBEROS, KNOX, OPENLDAP | Production environment recommends RANGER |
| Acceleration | JINDOCACHE | JindoCache local cache acceleration |
| Basic | MYSQL | Internal dependency |

**CUSTOM All Components** (32, freely select):

HADOOP-COMMON, HDFS, YARN, ZOOKEEPER, HIVE, SPARK3, SPARK2, FLINK, HBASE, PHOENIX, TEZ, KYUUBI, TRINO, PRESTO, SQOOP, FLUME, ICEBERG, HUDI, PAIMON, DELTALAKE, STARROCKS3, STARROCKS2, RANGER, RANGER-PLUGIN, KERBEROS, KNOX, OPENLDAP, JINDOCACHE, CELEBORN, OSS-HDFS, MYSQL

**Mutual Exclusion Rules** (apply to all cluster types):
- SPARK2 and SPARK3 cannot be selected simultaneously
- HDFS and OSS-HDFS cannot be selected simultaneously
- STARROCKS2 and STARROCKS3 cannot be selected simultaneously

### Component Dependencies

When selecting components need to satisfy dependency relationships, otherwise cluster creation will fail. In the table below HDFS|OSS-HDFS means choose one.

**Core Dependency Chain** (selecting left requires selecting right):

> **Note**: JINDOSDK is internal service, no need for user to manually select, system will auto-install based on selected components.

| Component | Hard Dependency (Required) | Optional Integration |
|------|--------------|---------|
| HADOOP-COMMON | — | — |
| HDFS | HADOOP-COMMON, ZOOKEEPER | — |
| OSS-HDFS | HADOOP-COMMON | — |
| YARN | HADOOP-COMMON, HDFS\|OSS-HDFS, ZOOKEEPER | — |
| HIVE | YARN, HDFS\|OSS-HDFS, ZOOKEEPER, MYSQL | TEZ, DELTALAKE, HUDI, ICEBERG, PAIMON |
| TEZ | YARN, HDFS\|OSS-HDFS | — |
| FLINK | YARN, HDFS\|OSS-HDFS, ZOOKEEPER, OPENLDAP | — |
| HBASE | HDFS\|OSS-HDFS, ZOOKEEPER | — |
| PHOENIX | HBASE | — |
| SPARK3 / SPARK2 | YARN, HDFS\|OSS-HDFS, HIVE | CELEBORN, DELTALAKE, HUDI, ICEBERG, PAIMON |
| KYUUBI | SPARK3, ZOOKEEPER, OPENLDAP | — |
| TRINO | HADOOP-COMMON, HDFS, HIVE, OPENLDAP | DELTALAKE, HUDI, ICEBERG, PAIMON |
| PRESTO | HADOOP-COMMON, HDFS, HIVE, OPENLDAP | DELTALAKE, HUDI, ICEBERG |
| SQOOP | YARN, HIVE | — |
| FLUME | HADOOP-COMMON, HDFS | HIVE, HBASE |
| KNOX | HDFS, YARN, OPENLDAP | SPARK2/3, TRINO, TEZ, HBASE, RANGER |
| RANGER | MYSQL, RANGER-PLUGIN, OPENLDAP | — |
| RANGER-PLUGIN | HDFS | HIVE, SPARK2/3, HBASE, YARN, TRINO |
| CLICKHOUSE | ZOOKEEPER | — |

**No Dependency Components** (can be independently selected): ZOOKEEPER, OPENLDAP, MYSQL, KERBEROS, JINDOCACHE, CELEBORN, ICEBERG, HUDI, PAIMON, DELTALAKE, DORIS, STARROCKS2, STARROCKS3

> **Recursive Dependency**: Dependencies are transitive. E.g., selecting HIVE → needs YARN → YARN also needs HADOOP-COMMON + HDFS + ZOOKEEPER. Complete dependency chain: HIVE needs YARN + HDFS + HADOOP-COMMON + ZOOKEEPER + MYSQL.

### Deployment Mode Decision

| Mode | MASTER Node Count | Use Case | Decision Rule |
|------|-------------|---------|---------|
| **HA** (High Availability) | 3 | Production environment | Production **must** use HA |
| **NORMAL** | 1 | Dev/test | Only for dev/test, cost-sensitive scenarios |

**HA Mode Additional Requirements**:
- **Must select ZOOKEEPER**——HA mode NameNode/ResourceManager depends on ZooKeeper for master-standby switching
- **Hive Metastore metadata must use external RDS**——Multiple MASTER need shared metadata storage, need to prepare RDS MySQL instance before creating HA cluster (in same VPC as cluster)
- **Ranger uses MASTER internal MYSQL component**——No need for external RDS
- NORMAL mode can use MASTER local MySQL, no RDS needed

### Node Group Roles and Planning

| Node Type | Responsibility | Instance Selection Recommendation | Disk Recommendation | Count Recommendation |
|---------|------|------------|---------|---------|
| **MASTER** | NameNode, ResourceManager, HiveServer2, Ranger, Knox etc. management services | Few components (3-4): 4-8 vCPU (g7.xlarge ~ 2xlarge); Many components (5+): 16-32 vCPU (g7.4xlarge ~ 8xlarge); Ultra-large scale clusters may need higher specs | System disk 120GB + data disk 80GB × 1 | HA=3, NORMAL=1 |
| **MASTER-EXTEND** | MASTER load extension, share management service pressure | Similar specs to MASTER | System disk 120GB + data disk 80GB × 1 | Only HA clusters support (EMR-3.51.1+ / EMR-5.17.1+), add as needed |
| **CORE** | DataNode (HDFS storage) + NodeManager (compute) | 4-16 vCPU, select by data volume | System disk 120GB + data disk by storage need | Minimum 2, expand by data volume |
| **TASK** | Pure compute (no HDFS storage) | Select by compute need, can use Spot instances | System disk 120GB + data disk 80GB × 1 | Elastic adjustment by compute need |
| **GATEWAY** | Job submission node, deploys client and auto-syncs cluster config, separates spark-submit/hive etc. operations from MASTER | Select by submission concurrency, generally g series sufficient | System disk 120GB + data disk 80GB × 1 | Supports DataLake/DataFlow(5.10.1+)/Custom(5.17.1+), add as needed |

> **MASTER-EXTEND Use Case**: When cluster is large and MASTER node CPU/memory load is持续 high, can add MASTER-EXTEND node group to分散 deploy some management services. New services won't auto-deploy to MASTER-EXTEND by default, need to check as needed during creation.

### Disk Type Selection

| Disk Type | Performance Level | IOPS | Use Case |
|---------|---------|------|---------|
| cloud_essd | PL0 | 10,000 | Dev/test, low IO scenarios |
| cloud_essd | PL1 (default) | 50,000 | Most production scenarios |
| cloud_essd | PL2 | 100,000 | High IO production scenarios |
| cloud_essd | PL3 | 1,000,000 | Extremely high IO scenarios |
| cloud_ssd | - | - | Older generation SSD, not recommended for new clusters |
| cloud_efficiency | - | - | High efficiency cloud disk, lowest cost but average performance |

### Payment Method

| Payment Method | Use Case | Description |
|---------|---------|------|
| **PayAsYouGo** (Pay-as-you-go) | Dev/test, short-term tasks, uncertain usage | Billed hourly, can release anytime |
| **Subscription** (Monthly/Yearly subscription) | Production environment, long-term stable operation | Prepaid more economical, need to configure renewal strategy |

## 2. Creation Phase

Check versions and specs:

```bash
# Query available versions (replace ClusterType and RegionId)
aliyun emr ListReleaseVersions --RegionId cn-hangzhou --ClusterType DATALAKE

# Query available instance types
aliyun emr ListInstanceTypes --RegionId cn-hangzhou --ZoneId cn-hangzhou-h \
  --ClusterType DATALAKE --PaymentType PayAsYouGo --NodeGroupType CORE
```

### Storage-Compute Architecture Selection

Before creating cluster, first determine storage-compute architecture, this determines storage component and instance type selection:

| Architecture | Storage Component | CORE Instance Type | Data Storage Location | Elasticity Capability | Use Case |
|------|---------|----------|------------|---------|---------|
| **Storage-Compute Separated** (recommended) | OSS-HDFS | g series (general purpose) | Remote OSS object storage, local disks only for cache and shuffle | CORE/TASK can freely scale, storage无限扩展 | Most scenarios, good elasticity, low storage cost |
| **Storage-Compute Integrated** | HDFS | d series (local disk type) | Data stored on CORE node local disks | CORE scaling limited by HDFS data migration | Extremely low latency scenarios with high data locality requirements |

> Storage-compute separation is recommended architecture—independent scaling of storage and compute, lower cost, better elasticity. Storage-compute integrated is suitable for scenarios extremely sensitive to read/write latency with predictable data volume.
>
> **Before choosing storage-compute separation must enable OSS-HDFS**: Go to OSS console to enable HDFS service for target Bucket, get OSS-HDFS path (e.g., `oss://bucket-name.cn-hangzhou.oss-dls.aliyuncs.com/`). This path will be used as cluster's `fs.defaultFS`, table data, job logs, temporary data will all be stored here.

### Template 1: Dev/Test Cluster (Lowest Cost)

NORMAL mode + pay-as-you-go + minimum specs, suitable for function verification and learning.

```bash
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken $(uuidgen) \
  --ClusterName "dev-datalake" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.21.0" \
  --DeployMode "NORMAL" \
  --PaymentType "PayAsYouGo" \
  --Applications '[
    {"ApplicationName": "HADOOP-COMMON"},
    {"ApplicationName": "HDFS"},
    {"ApplicationName": "YARN"},
    {"ApplicationName": "HIVE"},
    {"ApplicationName": "SPARK3"}
  ]' \
  --ApplicationConfigs '[
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "LOCAL"
    },
    {
      "ApplicationName": "SPARK3",
      "ConfigFileName": "hive-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "LOCAL"
    }
  ]' \
  --NodeAttributes '{
    "VpcId": "vpc-xxx",
    "ZoneId": "cn-hangzhou-h",
    "SecurityGroupId": "sg-xxx",
    "KeyPairName": "my-keypair"
  }' \
  --NodeGroups '[
    {
      "NodeGroupType": "MASTER",
      "NodeGroupName": "master",
      "NodeCount": 1,
      "InstanceTypes": ["ecs.g8i.xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}]
    },
    {
      "NodeGroupType": "CORE",
      "NodeGroupName": "core",
      "NodeCount": 2,
      "InstanceTypes": ["ecs.g8i.xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 2}]
    }
  ]'
```

### Template 2: Production Cluster — Storage-Compute Separated (Recommended)

HA + OSS-HDFS storage + g series general purpose instances + JINDOCACHE local cache acceleration. Data in OSS, CORE local disks only for cache and shuffle, free elasticity.

> **Prerequisite**: Need to enable HDFS service for target Bucket in OSS console first. When creating cluster, set `OSS_ROOT_URI` via `ApplicationConfigs` to point to that Bucket (format `oss://<bucket-name>.<region>.oss-dls.aliyuncs.com/`), table data, job logs, temporary data will all be stored under this path.

```bash
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken $(uuidgen) \
  --ClusterName "prod-datalake-disaggregated" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.21.0" \
  --DeployMode "HA" \
  --PaymentType "PayAsYouGo" \
  --DeletionProtection true \
  --Applications '[
    {"ApplicationName": "HADOOP-COMMON"},
    {"ApplicationName": "OSS-HDFS"},
    {"ApplicationName": "YARN"},
    {"ApplicationName": "ZOOKEEPER"},
    {"ApplicationName": "HIVE"},
    {"ApplicationName": "SPARK3"},
    {"ApplicationName": "TEZ"},
    {"ApplicationName": "JINDOCACHE"}
  ]' \
  --ApplicationConfigs '[
    {
      "ApplicationName": "OSS-HDFS",
      "ConfigFileName": "common.conf",
      "ConfigItemKey": "OSS_ROOT_URI",
      "ConfigItemValue": "oss://your-bucket.cn-hangzhou.oss-dls.aliyuncs.com/"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "DLF"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionURL",
      "ConfigItemValue": "jdbc:mysql://rm-xxx.mysql.rds.aliyuncs.com:3306/hivemeta?createDatabaseIfNotExist=true&characterEncoding=UTF-8"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionUserName",
      "ConfigItemValue": "hive_user"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionPassword",
      "ConfigItemValue": "YourRdsPassword123"
    },
    {
      "ApplicationName": "SPARK3",
      "ConfigFileName": "hive-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "DLF"
    }    
  ]' \
  --NodeAttributes '{
    "VpcId": "vpc-xxx",
    "ZoneId": "cn-hangzhou-h",
    "SecurityGroupId": "sg-xxx",
    "KeyPairName": "my-keypair"
  }' \
  --NodeGroups '[
    {
      "NodeGroupType": "MASTER",
      "NodeGroupName": "master",
      "NodeCount": 3,
      "InstanceTypes": ["ecs.g8i.2xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}]
    },
    {
      "NodeGroupType": "CORE",
      "NodeGroupName": "core",
      "NodeCount": 3,
      "InstanceTypes": ["ecs.g8i.2xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 300, "Count": 4}]
    },
    {
      "NodeGroupType": "TASK",
      "NodeGroupName": "task",
      "NodeCount": 2,
      "InstanceTypes": ["ecs.g8i.2xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}]
    }
  ]'
```

> **Storage-Compute Separation Key Points**: CORE node DataDisks are for JindoCache local cache and Spark shuffle data, not storing persistent data. Scaling CORE nodes doesn't affect data safety. Storage capacity is determined by OSS bucket, no need to estimate disk.
>
> **HA + Hive Metadata**: HA mode must use external RDS to store Hive Metastore metadata (multiple MASTER need to share), RDS instance must be in same VPC as EMR cluster. Replace `ConnectionURL`, `ConnectionUserName`, `ConnectionPassword` in above example with actual RDS connection info.

### Template 3: Production Cluster — Storage-Compute Integrated

HA + HDFS local storage + d series local disk instance types. Data stored on CORE node local disks, low read/write latency but limited elasticity.

```bash
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken $(uuidgen) \
  --ClusterName "prod-datalake-converged" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.16.0" \
  --DeployMode "HA" \
  --PaymentType "Subscription" \
  --DeletionProtection true \
  --SubscriptionConfig '{
    "PaymentDurationUnit": "Month",
    "PaymentDuration": 1,
    "AutoRenew": true,
    "AutoRenewDurationUnit": "Month",
    "AutoRenewDuration": 1
  }' \
  --Applications '[
    {"ApplicationName": "HADOOP-COMMON"},
    {"ApplicationName": "HDFS"},
    {"ApplicationName": "YARN"},
    {"ApplicationName": "ZOOKEEPER"},
    {"ApplicationName": "HIVE"},
    {"ApplicationName": "SPARK3"},
    {"ApplicationName": "TEZ"}
  ]' \
  --ApplicationConfigs '[
    {
      "ApplicationName": "HDFS",
      "ConfigFileName": "hdfs-site.xml",
      "ConfigItemKey": "dfs.replication",
      "ConfigItemValue": "3"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "DLF"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionURL",
      "ConfigItemValue": "jdbc:mysql://rm-xxx.mysql.rds.aliyuncs.com:3306/hivemeta?createDatabaseIfNotExist=true&characterEncoding=UTF-8"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionUserName",
      "ConfigItemValue": "hive_user"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionPassword",
      "ConfigItemValue": "YourRdsPassword123"
    }
  ]' \
  --NodeAttributes '{
    "VpcId": "vpc-xxx",
    "ZoneId": "cn-hangzhou-h",
    "SecurityGroupId": "sg-xxx",
    "KeyPairName": "my-keypair"
  }' \
  --NodeGroups '[
    {
      "NodeGroupType": "MASTER",
      "NodeGroupName": "master",
      "NodeCount": 3,
      "InstanceTypes": ["ecs.g8i.4xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120, "PerformanceLevel": "PL1"},
      "DataDisks": [{"Category": "cloud_essd", "Size": 120, "Count": 1, "PerformanceLevel": "PL1"}]
    },
    {
      "NodeGroupType": "CORE",
      "NodeGroupName": "core",
      "NodeCount": 6,
      "InstanceTypes": ["ecs.d3s.4xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "DeploymentSetStrategy": "CLUSTER",
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "local_hdd_pro", "Size": 11918, "Count": 8}]
    },
    {
      "NodeGroupType": "TASK",
      "NodeGroupName": "task",
      "NodeCount": 4,
      "InstanceTypes": ["ecs.g8i.4xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}]
    }
  ]'
```

> **Storage-Compute Integrated Key Points**: CORE uses d series local disk instance types, data stored in local HDFS. Shrinking CORE nodes needs to wait for HDFS data migration to complete, recommend subscription to lock resources. TASK nodes still use g series, pure compute without data. CORE nodes recommend enabling `DeploymentSetStrategy: "CLUSTER"` to分散 deploy instances on different physical servers, avoid single physical server failure causing multiple HDFS replicas lost simultaneously.
>
> **HA + Hive Metadata**: HA mode must use external RDS to store Hive Metastore metadata (multiple MASTER need to share), RDS instance must be in same VPC as EMR cluster. Replace `ConnectionURL`, `ConnectionUserName`, `ConnectionPassword` in above example with actual RDS connection info.

### Template 4: Spot Instance TASK Nodes (Reduce Compute Cost)

Create complete cluster with Spot TASK node group. To add Spot TASK node group to existing cluster, refer to CreateNodeGroup operation in [Scaling Guide](scaling.md).

```bash
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken $(uuidgen) \
  --ClusterName "cost-optimized-cluster" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.16.0" \
  --DeployMode "HA" \
  --PaymentType "PayAsYouGo" \
  --Applications '[
    {"ApplicationName": "HADOOP-COMMON"},
    {"ApplicationName": "OSS-HDFS"},
    {"ApplicationName": "YARN"},
    {"ApplicationName": "ZOOKEEPER"},
    {"ApplicationName": "HIVE"},
    {"ApplicationName": "SPARK3"}
  ]' \
  --ApplicationConfigs '[
    {
      "ApplicationName": "OSS-HDFS",
      "ConfigFileName": "common.conf",
      "ConfigItemKey": "OSS_ROOT_URI",
      "ConfigItemValue": "oss://your-bucket.cn-hangzhou.oss-dls.aliyuncs.com/"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "hive.metastore.type",
      "ConfigItemValue": "DLF"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionURL",
      "ConfigItemValue": "jdbc:mysql://rm-xxx.mysql.rds.aliyuncs.com:3306/hivemeta?createDatabaseIfNotExist=true&characterEncoding=UTF-8"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionUserName",
      "ConfigItemValue": "hive_user"
    },
    {
      "ApplicationName": "HIVE",
      "ConfigFileName": "hivemetastore-site.xml",
      "ConfigItemKey": "javax.jdo.option.ConnectionPassword",
      "ConfigItemValue": "YourRdsPassword123"
    }
  ]' \
  --NodeAttributes '{
    "VpcId": "vpc-xxx",
    "ZoneId": "cn-hangzhou-h",
    "SecurityGroupId": "sg-xxx",
    "KeyPairName": "my-keypair"
  }' \
  --NodeGroups '[
    {
      "NodeGroupType": "MASTER",
      "NodeGroupName": "master",
      "NodeCount": 3,
      "InstanceTypes": ["ecs.g8i.xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}]
    },
    {
      "NodeGroupType": "CORE",
      "NodeGroupName": "core",
      "NodeCount": 3,
      "InstanceTypes": ["ecs.g8i.xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 200, "Count": 4}]
    },
    {
      "NodeGroupType": "TASK",
      "NodeGroupName": "task-spot",
      "NodeCount": 4,
      "InstanceTypes": ["ecs.g8i.2xlarge", "ecs.g8i.xlarge", "ecs.c8i.2xlarge"],
      "VSwitchIds": ["vsw-xxx"],
      "SystemDisk": {"Category": "cloud_essd", "Size": 120},
      "DataDisks": [{"Category": "cloud_essd", "Size": 80, "Count": 1}],
      "SpotStrategy": "SpotAsPriceGo"
    }
  ]'
```

> **Spot Instance Tips**: Configure multiple InstanceTypes to improve Spot availability. TASK nodes have no HDFS data, being reclaimed doesn't affect data safety. Storage-compute separated architecture works better with Spot because CORE also has no persistent data.

## 3. Query and Monitoring

### Cluster List

```bash
# All clusters
aliyun emr ListClusters --RegionId cn-hangzhou

# Only running clusters
aliyun emr ListClusters --RegionId cn-hangzhou \
  --force --ClusterStates.1 RUNNING

# Filter by type and payment method
aliyun emr ListClusters --RegionId cn-hangzhou \
  --force --ClusterTypes.1 DATALAKE --PaymentTypes.1 PayAsYouGo

# Search by name
aliyun emr ListClusters --RegionId cn-hangzhou --ClusterName "prod"

# Find abnormal clusters
aliyun emr ListClusters --RegionId cn-hangzhou \
  --force --ClusterStates.1 START_FAILED --ClusterStates.2 TERMINATED_WITH_ERRORS --ClusterStates.3 TERMINATE_FAILED
```

### Cluster Details

```bash
aliyun emr GetCluster --RegionId cn-hangzhou --ClusterId c-xxx
```

### Cluster State Machine

| State | Meaning | Next Action |
|------|------|---------|
| `STARTING` | Creating ECS instances | Wait, usually 5-15 minutes |
| `BOOTSTRAPPING` | Installing and configuring components | Wait |
| `RUNNING` | Cluster ready | Normal use |
| `START_FAILED` | Creation failed | Check StateChangeReason to diagnose cause |
| `TERMINATING` | Deleting | Wait |
| `TERMINATED` | Normally deleted | No action needed |
| `TERMINATED_WITH_ERRORS` | Abnormal termination | Check StateChangeReason to diagnose cause |
| `TERMINATE_FAILED` | Deletion failed | Retry deletion or contact support |

## 4. Attribute Management

```bash
# Modify cluster name
aliyun emr UpdateClusterAttribute --RegionId cn-hangzhou --ClusterId c-xxx \
  --ClusterName "new-cluster-name"

# Modify description
aliyun emr UpdateClusterAttribute --RegionId cn-hangzhou --ClusterId c-xxx \
  --Description "Production data lake for team-A"

# Enable deletion protection (recommended for production clusters)
aliyun emr UpdateClusterAttribute --RegionId cn-hangzhou --ClusterId c-xxx \
  --DeletionProtection true
```

### Auto Renewal Management (Subscription Clusters Only)

```bash
# Enable auto renewal (renew monthly)
aliyun emr UpdateClusterAutoRenew --RegionId cn-hangzhou --ClusterId c-xxx \
  --ClusterAutoRenew true --ClusterAutoRenewDuration 1 --ClusterAutoRenewDurationUnit Month

# Disable auto renewal
aliyun emr UpdateClusterAutoRenew --RegionId cn-hangzhou --ClusterId c-xxx \
  --ClusterAutoRenew false

# Enable renewal for all cluster instances
aliyun emr UpdateClusterAutoRenew --RegionId cn-hangzhou --ClusterId c-xxx \
  --ClusterAutoRenew true --ClusterAutoRenewDuration 1 --ClusterAutoRenewDurationUnit Month \
  --RenewAllInstances true
```

## 5. Clone Cluster

When need to create a new cluster with same configuration as existing cluster (e.g., setting up test environment), use two-step clone:

```bash
# Step 1: Get clone metadata
aliyun emr GetClusterCloneMeta --RegionId cn-hangzhou --ClusterId c-xxx
```

Returned metadata contains complete cluster configuration. Modify fields that need adjustment (cluster name, node count, etc.), then create new cluster:

```bash
# Step 2: Create new cluster based on metadata (modify ClusterName etc. fields)
# Extract Applications, NodeGroups, NodeAttributes etc. fields from clone metadata,
# Pass in RunCluster named parameter format (don't use --body)
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken $(uuidgen) \
  --ClusterName "cloned-cluster" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.16.0" \
  --DeployMode "HA" \
  --PaymentType "PayAsYouGo" \
  --Applications '[... # Copy from clone metadata]' \
  --ApplicationConfigs '[... # Copy from clone metadata]' \
  --NodeAttributes '{... # Modify network parameters}' \
  --NodeGroups '[... # Adjust node count and specs as needed]'
```

**Cross-Region Clone Notes**:
- Must modify network parameters: VpcId, ZoneId, SecurityGroupId, VSwitchIds
- Need to confirm target region's instance types, zone stock availability
- EMR versions may differ across regions

## Related Documentation

- When need to continue reading other scenarios, please return to intent routing table in `SKILL.md` to select the appropriate reference document.