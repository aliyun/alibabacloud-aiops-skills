# RAM Policies: alibabacloud-cadt-probe

This document lists all Alibaba Cloud APIs and their RAM permission declarations involved during Skill execution.

---

## Permission Summary

| Service | Action | Purpose | Phase |
|---------|--------|---------|-------|
| BPStudio | `bpstudio:ExecuteOperation` | Execute sync operations (CreateOneClickJob, GetOneClickStatus, GetProbeResourceSummary, GetProbeRelatedItems, GetLastProbeTime, GetProbeRegions, GetProbeResult) | Main flow |
| Config | `config:GetDiscoveredResourceCountsGroupByResourceType` | Get resource counts grouped by type | Resource discovery |
| Config | `config:ListDiscoveredResources` | List discovered resources | Resource discovery |
| Config | `config:DescribeDiscoveredResourceBatch` | Batch describe discovered resources | Resource discovery |
| Config | `config:ListDiscoveredResourceRelationsBatch` | Batch list resource relations | Resource discovery |
| Config | `config:ListResourceRelations` | List resource relations | Resource discovery |
| Config | `config:ListDiscoveredResourceRelationsBatchByPage` | Paginated batch list resource relations | Resource discovery |
| Resource Sharing | `resourcesharing:ListSharedResources` | List shared resources | Resource discovery |
| VPC | `vpc:DescribeVSwitchAttributes` | Query VSwitch attributes | Resource discovery |
| VPC | `vpc:DescribeVpcs` | List VPCs | Resource discovery |
| VPC | `vpc:DescribeCommonBandwidthPackages` | List common bandwidth packages | Flink subthread |
| VPC | `vpc:GetNatGatewayAttribute` | Get NAT Gateway attributes | Relation subthread |
| VPC | `vpc:DescribeSnatTableEntries` | List SNAT table entries | Relation subthread |
| VPC | `vpc:DescribeForwardTableEntries` | List forward table entries | Relation subthread |
| RDS | `rds:DescribeDBInstances` | List RDS instances | Resource discovery |
| RDS | `rds:DescribeSecurityGroupConfiguration` | Query RDS security group config | Relation subthread |
| Redis (R-KVStore) | `kvstore:DescribeInstanceAttribute` | Query Redis instance attributes | Resource discovery |
| Redis (R-KVStore) | `kvstore:DescribeSecurityGroupConfiguration` | Query Redis security group config | Relation subthread |
| NAS | `nas:DescribeFileSystems` | List NAS file systems | Resource discovery |
| Resource Manager | `resourcemanager:ListResourceGroups` | List resource groups | Resource discovery |
| ACK (CS) | `cs:DescribeClusterDetail` | Query ACK cluster details | Resource discovery / Relation |
| ACK (CS) | `cs:DescribeClusterResources` | List ACK cluster resources | Relation subthread |
| ACK (CS) | `cs:DescribeClusterNodes` | List ACK cluster nodes | Relation subthread |
| Lindorm | `lindorm:GetLindormInstanceList` | List Lindorm instances | Lindorm subthread |
| Lindorm | `lindorm:GetLindormInstance` | Get Lindorm instance details | Lindorm subthread |
| DataWorks | `dataworks:ListProjects` | List DataWorks projects | DIDE subthread |
| DataWorks | `dataworks:ListResourceGroups` | List DataWorks resource groups | DIDE subthread |
| DIDE | `dide:ListUserResources` | List DIDE user resources | DIDE subthread |
| Flink (Stream) | `stream:DescribeVvpInstances` | List Flink VVP instances | Flink subthread |
| SelectDB | `selectdb:DescribeDBInstances` | List SelectDB instances | Flink subthread |
| CloudFW | `yundun-cloudfirewall:DescribeUserBuyVersion` | Query CloudFW subscription version | Flink subthread |
| EMR | `emr:ListClusters` | List EMR clusters | EMR subthread |
| EMR | `emr:GetCluster` | Get EMR cluster details | EMR subthread |
| EMR | `emr:ListNodeGroups` | List EMR node groups | EMR subthread |
| EMR | `emr:ListOnKubeClusters` | List EMR on Kubernetes clusters | EMR subthread |
| EMR Serverless Spark | `emr-serverless-spark:ListWorkspaces` | List EMR Serverless Spark workspaces | EMR subthread |
| EMR Serverless StarRocks | `sr:DescribeInstances` | List StarRocks instances | EMR subthread |
| RocketMQ 5.0 | `rocketmq:ListInstances` | List RocketMQ instances | RMQ subthread |
| RocketMQ 5.0 | `rocketmq:GetInstance` | Get RocketMQ instance details | RMQ subthread |
| OceanBase | `oceanbasepro:DescribeInstances` | List OceanBase instances | OB subthread |
| ClickHouse | `clickhouse:DescribeDBClusters` | List ClickHouse clusters | ClickHouse subthread |
| ClickHouse | `clickhouse:DescribeDBInstances` | List ClickHouse instances (Enterprise) | ClickHouse subthread |
| ClickHouse | `clickhouse:DescribeDBInstanceAttribute` | Get ClickHouse instance attributes (Enterprise) | ClickHouse subthread |
| Hologres | `hologram:ListInstances` | List Hologres instances | Hologres subthread |
| SLB | `slb:DescribeVServerGroups` | List SLB virtual server groups | Relation subthread |
| SLB | `slb:DescribeVServerGroupAttribute` | Get SLB virtual server group attributes | Relation subthread |
| SLB | `slb:DescribeMasterSlaveServerGroups` | List SLB master-slave server groups | Relation subthread |
| SLB | `slb:DescribeMasterSlaveServerGroupAttribute` | Get SLB master-slave server group attributes | Relation subthread |
| SLB | `slb:DescribeLoadBalancerListeners` | List SLB listeners | Relation subthread |
| ALB | `alb:GetLoadBalancerAttribute` | Get ALB load balancer attributes | Relation subthread |
| ALB | `alb:ListListeners` | List ALB listeners | Relation subthread |
| ALB | `alb:ListServerGroups` | List ALB server groups | Relation subthread |
| ALB | `alb:ListServerGroupServers` | List ALB server group servers | Relation subthread |
| NLB | `nlb:ListListeners` | List NLB listeners | Relation subthread |
| NLB | `nlb:GetListenerAttribute` | Get NLB listener attributes | Relation subthread |
| NLB | `nlb:ListServerGroups` | List NLB server groups | Relation subthread |
| NLB | `nlb:ListServerGroupServers` | List NLB server group servers | Relation subthread |
| ESS | `ess:DescribeScalingInstances` | List ESS scaling instances | Relation subthread |
| CEN | `cen:DescribeCenAttachedChildInstances` | List CEN attached child instances | Relation subthread |
| CEN | `cen:DescribeCenAttachedChildInstanceAttribute` | Get CEN attached child instance attributes | Relation subthread |
| PolarDB | `polardb:DescribeDBClusterAccessWhitelist` | Get PolarDB cluster access whitelist | Relation subthread |
| MongoDB (DDS) | `dds:DescribeSecurityGroupConfiguration` | Query MongoDB security group config | Relation subthread |
| PolarDB-X | `polardbx:DescribeDBInstances` | List PolarDB-X instances | PolarDB-X subthread |
| PolarDB-X | `polardbx:DescribeDBInstanceAttribute` | Get PolarDB-X instance attributes | PolarDB-X subthread |

---

## Least-Privilege RAM Policy (JSON)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bpstudio:ExecuteOperation"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "alb:GetLoadBalancerAttribute",
        "alb:ListListeners",
        "alb:ListServerGroupServers",
        "alb:ListServerGroups",
        "cen:DescribeCenAttachedChildInstanceAttribute",
        "cen:DescribeCenAttachedChildInstances",
        "clickhouse:DescribeDBClusters",
        "clickhouse:DescribeDBInstanceAttribute",
        "clickhouse:DescribeDBInstances",
        "config:DescribeDiscoveredResourceBatch",
        "config:GetDiscoveredResourceCountsGroupByResourceType",
        "config:ListDiscoveredResourceRelationsBatch",
        "config:ListDiscoveredResourceRelationsBatchByPage",
        "config:ListDiscoveredResources",
        "config:ListResourceRelations",
        "cs:DescribeClusterDetail",
        "cs:DescribeClusterNodes",
        "cs:DescribeClusterResources",
        "dataworks:ListProjects",
        "dataworks:ListResourceGroups",
        "dds:DescribeSecurityGroupConfiguration",
        "dide:ListUserResources",
        "emr-serverless-spark:ListWorkspaces",
        "emr:GetCluster",
        "emr:ListClusters",
        "emr:ListNodeGroups",
        "emr:ListOnKubeClusters",
        "ess:DescribeScalingInstances",
        "hologram:ListInstances",
        "kvstore:DescribeInstanceAttribute",
        "kvstore:DescribeSecurityGroupConfiguration",
        "lindorm:GetLindormInstance",
        "lindorm:GetLindormInstanceList",
        "nas:DescribeFileSystems",
        "nlb:GetListenerAttribute",
        "nlb:ListListeners",
        "nlb:ListServerGroupServers",
        "nlb:ListServerGroups",
        "oceanbasepro:DescribeInstances",
        "polardb:DescribeDBClusterAccessWhitelist",
        "polardbx:DescribeDBInstanceAttribute",
        "polardbx:DescribeDBInstances",
        "rds:DescribeDBInstances",
        "rds:DescribeSecurityGroupConfiguration",
        "resourcemanager:ListResourceGroups",
        "resourcesharing:ListSharedResources",
        "rocketmq:GetInstance",
        "rocketmq:ListInstances",
        "selectdb:DescribeDBInstances",
        "slb:DescribeLoadBalancerListeners",
        "slb:DescribeMasterSlaveServerGroupAttribute",
        "slb:DescribeMasterSlaveServerGroups",
        "slb:DescribeVServerGroupAttribute",
        "slb:DescribeVServerGroups",
        "sr:DescribeInstances",
        "stream:DescribeVvpInstances",
        "vpc:DescribeCommonBandwidthPackages",
        "vpc:DescribeForwardTableEntries",
        "vpc:DescribeSnatTableEntries",
        "vpc:DescribeVSwitchAttributes",
        "vpc:DescribeVpcs",
        "vpc:GetNatGatewayAttribute",
        "yundun-cloudfirewall:DescribeUserBuyVersion"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Per-Operation Permission Details

### Main Flow: BPStudio ExecuteOperationSync

All probe operations are executed through the BPStudio `ExecuteOperationSync` API with `service_type="probe"`. A single RAM permission `bpstudio:ExecuteOperation` covers all 7 operations below.

| Operation | SDK Method | Description |
|-----------|-----------|-------------|
| `CreateOneClickJob` | `start_probe_job()` | Submit a new probe task |
| `GetOneClickStatus` | `get_probe_progress()` | Poll probe task progress |
| `GetProbeResourceSummary` | `get_probe_resource_summary()` | Fetch aggregated resource summary |
| `GetProbeRelatedItems` | `get_probe_related_items()` | Query resources related to a specific resource |
| `GetLastProbeTime` | `get_last_probe_time()` | Get time since last probe run |
| `GetProbeRegions` | `get_probe_regions()` | Get list of cached probe regions |
| `GetProbeResult` | `get_probe_result()` | Fetch detailed probe results |

### Subthread: Config (Resource Discovery)

| API | Permission | Description |
|-----|-----------|-------------|
| `GetDiscoveredResourceCountsGroupByResourceType` | `config:GetDiscoveredResourceCountsGroupByResourceType` | Get resource counts grouped by type |
| `ListDiscoveredResources` | `config:ListDiscoveredResources` | List discovered resources |
| `DescribeDiscoveredResourceBatch` | `config:DescribeDiscoveredResourceBatch` | Batch describe discovered resources |
| `ListDiscoveredResourceRelationsBatch` | `config:ListDiscoveredResourceRelationsBatch` | Batch list resource relations |
| `ListResourceRelations` | `config:ListResourceRelations` | List resource relations |
| `ListDiscoveredResourceRelationsBatchByPage` | `config:ListDiscoveredResourceRelationsBatchByPage` | Paginated batch list resource relations |

### Subthread: Relation (Network & Load Balancing)

| API | Permission | Description |
|-----|-----------|-------------|
| `DescribeVServerGroups` | `slb:DescribeVServerGroups` | List SLB virtual server groups |
| `DescribeVServerGroupAttribute` | `slb:DescribeVServerGroupAttribute` | Get SLB virtual server group attributes |
| `DescribeMasterSlaveServerGroups` | `slb:DescribeMasterSlaveServerGroups` | List SLB master-slave server groups |
| `DescribeMasterSlaveServerGroupAttribute` | `slb:DescribeMasterSlaveServerGroupAttribute` | Get SLB master-slave server group attributes |
| `DescribeLoadBalancerListeners` | `slb:DescribeLoadBalancerListeners` | List SLB listeners |
| `GetLoadBalancerAttribute` | `alb:GetLoadBalancerAttribute` | Get ALB load balancer attributes |
| `ListListeners` | `alb:ListListeners` | List ALB listeners |
| `ListServerGroups` | `alb:ListServerGroups` | List ALB server groups |
| `ListServerGroupServers` | `alb:ListServerGroupServers` | List ALB server group servers |
| `ListListeners` | `nlb:ListListeners` | List NLB listeners |
| `GetListenerAttribute` | `nlb:GetListenerAttribute` | Get NLB listener attributes |
| `ListServerGroups` | `nlb:ListServerGroups` | List NLB server groups |
| `ListServerGroupServers` | `nlb:ListServerGroupServers` | List NLB server group servers |
| `DescribeClusterDetail` | `cs:DescribeClusterDetail` | Query ACK cluster details |
| `DescribeClusterResources` | `cs:DescribeClusterResources` | List ACK cluster resources |
| `DescribeClusterNodes` | `cs:DescribeClusterNodes` | List ACK cluster nodes |
| `GetNatGatewayAttribute` | `vpc:GetNatGatewayAttribute` | Get NAT Gateway attributes |
| `DescribeSnatTableEntries` | `vpc:DescribeSnatTableEntries` | List SNAT table entries |
| `DescribeForwardTableEntries` | `vpc:DescribeForwardTableEntries` | List forward table entries |
| `DescribeScalingInstances` | `ess:DescribeScalingInstances` | List ESS scaling instances |
| `DescribeCenAttachedChildInstances` | `cen:DescribeCenAttachedChildInstances` | List CEN attached child instances |
| `DescribeCenAttachedChildInstanceAttribute` | `cen:DescribeCenAttachedChildInstanceAttribute` | Get CEN attached child instance attributes |
| `DescribeSecurityGroupConfiguration` | `rds:DescribeSecurityGroupConfiguration` | Query RDS security group config |
| `DescribeDBClusterAccessWhitelist` | `polardb:DescribeDBClusterAccessWhitelist` | Get PolarDB cluster access whitelist |
| `DescribeSecurityGroupConfiguration` | `kvstore:DescribeSecurityGroupConfiguration` | Query Redis security group config |
| `DescribeSecurityGroupConfiguration` | `dds:DescribeSecurityGroupConfiguration` | Query MongoDB security group config |

### Subthread: Product-Specific Discovery

| Subthread | API | Permission | Description |
|-----------|-----|-----------|-------------|
| Lindorm | `GetLindormInstanceList` | `lindorm:GetLindormInstanceList` | List Lindorm instances |
| Lindorm | `GetLindormInstance` | `lindorm:GetLindormInstance` | Get Lindorm instance details |
| DIDE | `ListProjects` | `dataworks:ListProjects` | List DataWorks projects |
| DIDE | `ListResourceGroups` | `dataworks:ListResourceGroups` | List DataWorks resource groups |
| DIDE | `ListUserResources` | `dide:ListUserResources` | List DIDE user resources |
| Flink | `DescribeInstances` | `stream:DescribeVvpInstances` | List Flink VVP instances |
| Flink | `DescribeDBInstances` | `selectdb:DescribeDBInstances` | List SelectDB instances |
| Flink | `DescribeCommonBandwidthPackages` | `vpc:DescribeCommonBandwidthPackages` | List common bandwidth packages |
| Flink | `DescribeUserBuyVersion` | `yundun-cloudfirewall:DescribeUserBuyVersion` | Query CloudFW subscription version |
| EMR | `ListClusters` | `emr:ListClusters` | List EMR clusters |
| EMR | `GetCluster` | `emr:GetCluster` | Get EMR cluster details |
| EMR | `ListNodeGroups` | `emr:ListNodeGroups` | List EMR node groups |
| EMR | `ListOnKubeClusters` | `emr:ListOnKubeClusters` | List EMR on Kubernetes clusters |
| EMR Spark | `GET /api/v1/workspaces` | `emr-serverless-spark:ListWorkspaces` | List EMR Serverless Spark workspaces |
| EMR StarRocks | `ListInstances` | `sr:DescribeInstances` | List StarRocks instances |
| RMQ | `GET /instances` | `rocketmq:ListInstances` | List RocketMQ instances |
| RMQ | `GET /instances/{instanceId}` | `rocketmq:GetInstance` | Get RocketMQ instance details |
| OB | `DescribeInstances` | `oceanbasepro:DescribeInstances` | List OceanBase instances |
| ClickHouse | `DescribeDBClusters` | `clickhouse:DescribeDBClusters` | List ClickHouse clusters |
| ClickHouse | `DescribeDBInstances` | `clickhouse:DescribeDBInstances` | List ClickHouse instances (Enterprise) |
| ClickHouse | `DescribeDBInstanceAttribute` | `clickhouse:DescribeDBInstanceAttribute` | Get ClickHouse instance attributes |
| Hologres | `POST /api/v1/instances` | `hologram:ListInstances` | List Hologres instances |
| PolarDB-X | `DescribeDBInstances` | `polardbx:DescribeDBInstances` | List PolarDB-X instances |
| PolarDB-X | `DescribeDBInstanceAttribute` | `polardbx:DescribeDBInstanceAttribute` | Get PolarDB-X instance attributes |

### Main Class: Primary Resource Discovery

| API | Permission | Description |
|-----|-----------|-------------|
| `GetDiscoveredResourceCountsGroupByResourceType` | `config:GetDiscoveredResourceCountsGroupByResourceType` | Get resource counts grouped by type |
| `ListDiscoveredResources` | `config:ListDiscoveredResources` | List discovered resources |
| `DescribeDiscoveredResourceBatch` | `config:DescribeDiscoveredResourceBatch` | Batch describe discovered resources |
| `ListDiscoveredResourceRelationsBatch` | `config:ListDiscoveredResourceRelationsBatch` | Batch list resource relations |
| `ListResourceRelations` | `config:ListResourceRelations` | List resource relations |
| `ListDiscoveredResourceRelationsBatchByPage` | `config:ListDiscoveredResourceRelationsBatchByPage` | Paginated batch list resource relations |
| `ListSharedResources` | `resourcesharing:ListSharedResources` | List shared resources |
| `DescribeVSwitchAttributes` | `vpc:DescribeVSwitchAttributes` | Query VSwitch attributes |
| `DescribeVpcs` | `vpc:DescribeVpcs` | List VPCs |
| `DescribeDBInstances` | `rds:DescribeDBInstances` | List RDS instances |
| `DescribeInstanceAttribute` | `kvstore:DescribeInstanceAttribute` | Query Redis instance attributes |
| `DescribeFileSystems` | `nas:DescribeFileSystems` | List NAS file systems |
| `ListResourceGroups` | `resourcemanager:ListResourceGroups` | List resource groups |
| `DescribeClusterDetail` | `cs:DescribeClusterDetail` | Query ACK cluster details |
| `DescribeClusterResources` | `cs:DescribeClusterResources` | List ACK cluster resources |
