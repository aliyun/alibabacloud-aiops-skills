# Related API Calls and Parameters

This document lists all API calls used by the FinOps Resource Inspection skill, organized by resource type.

---

## ECS APIs

### DescribeRegions
- **Purpose**: Discover all enabled regions under the account
- **SDK**: `alibabacloud_ecs20140526`
- **Method**: `describe_regions`
- **Key Parameters**:
  - `InstanceChargeType` (optional): Filter by billing method
- **Key Response Fields**:
  - `Regions.Region[].RegionId`: Region ID
  - `Regions.Region[].LocalName`: Region display name

### DescribeInstances
- **Purpose**: Retrieve all ECS instances in a region
- **SDK**: `alibabacloud_ecs20140526`
- **Method**: `describe_instances`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `PageSize` (optional, default 10): Set to 100 for efficiency
  - `NextToken` (optional): For pagination
  - `Status` (optional): Filter by instance status
- **Key Response Fields**:
  - `Instances.Instance[].InstanceId`: Instance ID
  - `Instances.Instance[].InstanceName`: Instance name
  - `Instances.Instance[].Status`: Running/Stopped/etc.
  - `Instances.Instance[].InstanceType`: Instance type
  - `Instances.Instance[].InstanceChargeType`: PrePaid/PostPaid
  - `Instances.Instance[].CreationTime`: Creation timestamp
  - `Instances.Instance[].ExpiredTime`: Expiration timestamp (PrePaid)

### DescribeDisks
- **Purpose**: Retrieve cloud disks
- **SDK**: `alibabacloud_ecs20140526`
- **Method**: `describe_disks`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `Status` (optional): Filter by disk status (Available/In_use)
  - `DiskType` (optional): data/system/all
  - `PageSize` (optional): Set to 100
  - `NextToken` (optional): For pagination
- **Key Response Fields**:
  - `Disks.Disk[].DiskId`: Disk ID
  - `Disks.Disk[].DiskName`: Disk name
  - `Disks.Disk[].Status`: Available/In_use/etc.
  - `Disks.Disk[].DiskType`: data/system
  - `Disks.Disk[].Category`: cloud_essd/cloud_ssd/etc.
  - `Disks.Disk[].Size`: Disk size in GB
  - `Disks.Disk[].CreationTime`: Creation timestamp
  - `Disks.Disk[].InstanceId`: Attached instance ID (if any)

---

## RDS APIs

### DescribeDBInstances
- **Purpose**: Retrieve all RDS instances
- **SDK**: `alibabacloud_rds20140815`
- **Method**: `describe_dbinstances`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `PageSize` (optional, default 30): Set to 100
  - `PageNumber` (optional): For pagination
  - `DBInstanceStatus` (optional): Filter by status
- **Key Response Fields**:
  - `Items.DBInstance[].DBInstanceId`: Instance ID
  - `Items.DBInstance[].DBInstanceDescription`: Instance description
  - `Items.DBInstance[].Engine`: MySQL/PostgreSQL/SQLServer/MariaDB
  - `Items.DBInstance[].EngineVersion`: Engine version
  - `Items.DBInstance[].DBInstanceClass`: Instance class
  - `Items.DBInstance[].PayType`: PrePaid/PostPaid/Serverless
  - `Items.DBInstance[].DBInstanceStatus`: Running/etc.
  - `Items.DBInstance[].CreationTime`: Creation timestamp
  - `Items.DBInstance[].ExpireTime`: Expiration timestamp

---

## VPC APIs (EIP, NAT)

### DescribeEipAddresses
- **Purpose**: Retrieve all EIPs
- **SDK**: `alibabacloud_vpc20160428`
- **Method**: `describe_eip_addresses`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `PageSize` (optional, default 10): Set to 50
  - `PageNumber` (optional): For pagination
  - `Status` (optional): Available/InUse/Associating
- **Key Response Fields**:
  - `EipAddresses.EipAddress[].AllocationId`: EIP allocation ID
  - `EipAddresses.EipAddress[].IpAddress`: EIP address
  - `EipAddresses.EipAddress[].Status`: Available/InUse
  - `EipAddresses.EipAddress[].InstanceId`: Bound instance ID (if any)
  - `EipAddresses.EipAddress[].Name`: EIP name
  - `EipAddresses.EipAddress[].Bandwidth`: Bandwidth in Mbps

### DescribeNatGateways
- **Purpose**: Retrieve NAT gateways
- **SDK**: `alibabacloud_vpc20160428`
- **Method**: `describe_nat_gateways`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `NetworkType` (optional): internet (public NAT) / intranet (private NAT)
  - `PageSize` (optional): Set to 50
  - `PageNumber` (optional): For pagination
- **Key Response Fields**:
  - `NatGateways.NatGateway[].NatGatewayId`: NAT gateway ID
  - `NatGateways.NatGateway[].Name`: NAT gateway name
  - `NatGateways.NatGateway[].Status`: Available/etc.
  - `NatGateways.NatGateway[].NetworkType`: internet/intranet
  - `NatGateways.NatGateway[].BandwidthPackageIds`: Bound EIP package IDs
  - `NatGateways.NatGateway[].NatGatewayPrivateInfo.IpLists`: EIP list

### DescribeSnatTableEntries
- **Purpose**: Retrieve SNAT rules for a NAT gateway
- **SDK**: `alibabacloud_vpc20160428`
- **Method**: `describe_snat_table_entries`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `NatGatewayId` (required): NAT gateway ID
- **Key Response Fields**:
  - `SnatTableEntries.SnatTableEntry[].SnatEntryId`: SNAT entry ID
  - `SnatTableEntries.SnatTableEntry[].SnatIp`: SNAT EIP address
  - `SnatTableEntries.SnatTableEntry[].SourceCIDR`: Source CIDR

### DescribeForwardTableEntries
- **Purpose**: Retrieve DNAT rules for a NAT gateway
- **SDK**: `alibabacloud_vpc20160428`
- **Method**: `describe_forward_table_entries`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `ForwardTableId` (required): Forward table ID
- **Key Response Fields**:
  - `ForwardTableEntries.ForwardTableEntry[].ForwardEntryId`: DNAT entry ID
  - `ForwardTableEntries.ForwardTableEntry[].IpProtocol`: Protocol
  - `ForwardTableEntries.ForwardTableEntry[].ExternalIp`: External EIP
  - `ForwardTableEntries.ForwardTableEntry[].ExternalPort`: External port

---

## SLB (CLB) APIs

### DescribeLoadBalancers
- **Purpose**: Retrieve CLB instances
- **SDK**: `alibabacloud_slb20140515`
- **Method**: `describe_load_balancers`
- **Key Parameters**:
  - `RegionId` (required): Target region
- **Key Response Fields**:
  - `LoadBalancers.LoadBalancer[].LoadBalancerId`: CLB ID
  - `LoadBalancers.LoadBalancer[].LoadBalancerName`: CLB name
  - `LoadBalancers.LoadBalancer[].Address`: CLB IP address
  - `LoadBalancers.LoadBalancer[].Status`: active/inactive/locked
  - `LoadBalancers.LoadBalancer[].PayType`: PayByCLCU/PrePaid/PostPaidByLcu

### DescribeLoadBalancerListeners
- **Purpose**: Retrieve listeners for a CLB instance
- **SDK**: `alibabacloud_slb20140515`
- **Method**: `describe_load_balancer_listeners`
- **Key Parameters**:
  - `RegionId` (required): Target region
  - `LoadBalancerId` (required): CLB ID
- **Key Response Fields**:
  - `Listeners.Listener[].ListenerPort`: Listener port
  - `Listeners.Listener[].Protocol`: TCP/HTTP/HTTPS/UDP
  - `Listeners.Listener[].BackendServers`: Backend server list with weights

---

## ALB APIs

### ListLoadBalancers
- **Purpose**: Retrieve ALB instances
- **SDK**: `alibabacloud_alb20200616`
- **Method**: `list_load_balancers`
- **Key Parameters**:
  - `MaxResults` (optional): Results per page
  - `NextToken` (optional): For pagination
- **Key Response Fields**:
  - `LoadBalancers[].LoadBalancerId`: ALB ID
  - `LoadBalancers[].LoadBalancerName`: ALB name
  - `LoadBalancers[].LoadBalancerStatus`: Active/Inactive
  - `LoadBalancers[].AddressType`: internet/intranet

### ListListeners
- **Purpose**: Retrieve ALB listeners
- **SDK**: `alibabacloud_alb20200616`
- **Method**: `list_listeners`
- **Key Parameters**:
  - `LoadBalancerId` (optional): Filter by ALB ID
  - `MaxResults` (optional): Results per page
  - `NextToken` (optional): For pagination
- **Key Response Fields**:
  - `Listeners[].ListenerId`: Listener ID
  - `Listeners[].ListenerProtocol`: HTTP/HTTPS/TCP
  - `Listeners[].ServerGroupId`: Associated server group ID
  - `Listeners[].Status`: Running/Stopped

### ListServerGroups
- **Purpose**: Retrieve ALB server groups
- **SDK**: `alibabacloud_alb20200616`
- **Method**: `list_server_groups`
- **Key Parameters**:
  - `LoadBalancerId` (optional): Filter by ALB ID
  - `MaxResults` (optional): Results per page
- **Key Response Fields**:
  - `ServerGroups[].ServerGroupId`: Server group ID
  - `ServerGroups[].ServerGroupName`: Server group name
  - `ServerGroups[].ServerGroupType`: Instance/Ip/Fc

### ListServerGroupServers
- **Purpose**: Retrieve servers in an ALB server group
- **SDK**: `alibabacloud_alb20200616`
- **Method**: `list_server_group_servers`
- **Key Parameters**:
  - `ServerGroupId` (required): Server group ID
- **Key Response Fields**:
  - `Servers[].ServerId`: Server ID
  - `Servers[].Port`: Server port
  - `Servers[].Weight`: Server weight
  - `Servers[].ServerType`: ecs/eni/eci

---

## NLB APIs

### ListLoadBalancers
- **Purpose**: Retrieve NLB instances
- **SDK**: `alibabacloud_nlb20220430`
- **Method**: `list_load_balancers`
- **Key Parameters**:
  - `MaxResults` (optional): Results per page
  - `NextToken` (optional): For pagination
- **Key Response Fields**:
  - `LoadBalancers[].LoadBalancerId`: NLB ID
  - `LoadBalancers[].LoadBalancerName`: NLB name
  - `LoadBalancers[].LoadBalancerStatus`: Active/Inactive
  - `LoadBalancers[].AddressType`: internet/intranet

### ListListeners
- **Purpose**: Retrieve NLB listeners
- **SDK**: `alibabacloud_nlb20220430`
- **Method**: `list_listeners`
- **Key Parameters**:
  - `LoadBalancerId` (optional): Filter by NLB ID
  - `MaxResults` (optional): Results per page
- **Key Response Fields**:
  - `Listeners[].ListenerId`: Listener ID
  - `Listeners[].ListenerProtocol`: TCP/UDP/TCPSSL
  - `Listeners[].ServerGroupId`: Associated server group ID
  - `Listeners[].Status`: Running/Stopped

### ListServerGroups
- **Purpose**: Retrieve NLB server groups
- **SDK**: `alibabacloud_nlb20220430`
- **Method**: `list_server_groups`
- **Key Parameters**:
  - `LoadBalancerId` (optional): Filter by NLB ID
  - `MaxResults` (optional): Results per page
- **Key Response Fields**:
  - `ServerGroups[].ServerGroupId`: Server group ID
  - `ServerGroups[].ServerGroupName`: Server group name

---

## CloudMonitor (CMS) APIs

### DescribeMetricLast
- **Purpose**: Query the latest CloudMonitor metrics with daily aggregation
- **SDK**: `alibabacloud_cms20190101`
- **Method**: `describe_metric_last`
- **Key Parameters**:
  - `Namespace` (required): Metric namespace (e.g., acs_ecs_dashboard)
  - `MetricName` (required): Metric name (e.g., CPUUtilization)
  - `Dimensions` (required): JSON string with resource identifier
  - `Period` (optional): Aggregation period, use 86400 for daily
- **Key Response Fields**:
  - `Datapoints`: JSON array of data points
  - `Code`: Response code (200 = success)
  - `Success`: Boolean success flag

### DescribeMetricList
- **Purpose**: Query CloudMonitor metric history over a time range
- **SDK**: `alibabacloud_cms20190101`
- **Method**: `describe_metric_list`
- **Key Parameters**:
  - `Namespace` (required): Metric namespace
  - `MetricName` (required): Metric name
  - `Dimensions` (required): JSON string with resource identifier
  - `StartTime` (required): Start timestamp (milliseconds)
  - `EndTime` (required): End timestamp (milliseconds)
  - `Period` (optional): Aggregation period

---

## Metric Namespaces and Metrics

### ECS (acs_ecs_dashboard)
| Metric | Description |
|--------|-------------|
| CPUUtilization | CPU utilization (%) |
| memory_usedutilization | Memory utilization (%) |
| DiskReadIOPS | Disk read IOPS |
| DiskWriteIOPS | Disk write IOPS |
| IntranetInRate | Inbound intranet bandwidth (Kbps) |
| IntranetOutRate | Outbound intranet bandwidth (Kbps) |

### RDS (acs_rds_dashboard)
| Metric | Description |
|--------|-------------|
| CpuUsage | CPU usage (%) |
| MemoryUsage | Memory usage (%) |
| IOPSUsage | IOPS usage (%) |
| ConnectionUsage | Connection usage (%) |

### EIP (acs_vpc_eip)
| Metric | Description |
|--------|-------------|
| net_rx.rate | Inbound traffic rate (bytes/s) |
| net_tx.rate | Outbound traffic rate (bytes/s) |
