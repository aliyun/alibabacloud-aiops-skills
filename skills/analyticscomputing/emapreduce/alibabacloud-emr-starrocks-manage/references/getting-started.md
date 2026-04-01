# Quick Start: Create Your First StarRocks Instance from Scratch

This guide helps first-time users complete: Prerequisites check → Create first instance → Verify running → Clean up resources.

## Prerequisites

### 1. CLI Environment

```bash
# Verify Alibaba Cloud CLI is installed
aliyun version

# Verify credentials are configured (should display current profile)
aliyun configure list
```

### 2. Network Resources

Creating a StarRocks instance requires the following cloud resources; if unavailable, they need to be created first. **Confirm the RegionId with the user before proceeding** (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`, etc.):

```bash
# Check if there is an available VPC
aliyun vpc DescribeVpcs --RegionId <RegionId>

# Check if the VPC has a VSwitch
aliyun vpc DescribeVSwitches --RegionId <RegionId> --VpcId vpc-xxx

# Check if there is a security group
aliyun ecs DescribeSecurityGroups --RegionId <RegionId> --VpcId vpc-xxx
```

> **Don't have these resources?** Please create VPC, VSwitch, and Security Group first via the Alibaba Cloud console or CLI.

### 3. Confirm Availability Zone Information

Record the following information, which will be needed when creating the instance:
- RegionId (e.g., `cn-hangzhou`)
- ZoneId (e.g., `cn-hangzhou-h`, from the availability zone where the VSwitch is located)
- VpcId, VSwitchId, SecurityGroupId

## Step 1: Create Instance

The following is a **minimal instance for development and testing**, using shared-data architecture, standard specs, pay-as-you-go:

> **Important**: `AdminPassword` is a required parameter used to set the initial password for the StarRocks admin account. Password requirements: 8-30 characters, containing at least three of the following: uppercase letters, lowercase letters, digits, and special characters (`@#$%^*_+-.`).

```bash
aliyun starrocks CreateInstanceV1 --RegionId cn-hangzhou --body '{
  "RegionId": "cn-hangzhou",
  "InstanceName": "my-first-starrocks",
  "AdminPassword": "YourP@ssw0rd",
  "Version": "3.3",
  "RunMode": "shared_data",
  "PackageType": "official",
  "PayType": "postPaid",
  "VpcId": "vpc-xxx",
  "ZoneId": "cn-hangzhou-h",
  "VSwitchId": "vsw-xxx",
  "VSwitches": [{"VswId": "vsw-xxx", "ZoneId": "cn-hangzhou-h", "Primary": true}],
  "SecurityGroupId": "sg-xxx",
  "OssAccessingRoleName": "AliyunEMRDefaultRole",
  "Cu": 8,
  "FrontendNodeGroups": [
    {
      "NodeGroupName": "defaultFeNodeGroup",
      "Cu": 8,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "BackendNodeGroups": [
    {
      "NodeGroupName": "default_warehouse",
      "Cu": 8,
      "SpecType": "standard",
      "ResidentNodeNumber": 1,
      "DiskNumber": 1,
      "StorageSize": 200,
      "StoragePerformanceLevel": "pl1"
    }
  ],
  "ClientToken": "uuid-xxx"
}'
```

The response returns an `InstanceId` (e.g., `c-xxx`); note it down for subsequent operations.

> **Note**: Creating an instance incurs costs. The minimum 8 CU configuration is suitable for development and testing; do not use it for production environments.

## Step 2: Verify Instance Status

Instance creation is an asynchronous operation, typically taking 5-10 minutes.

```bash
# Check instance status
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceId c-xxx
```

**Status Transition**: `creating` → `running`

The instance is ready when `InstanceStatus` becomes `running`.

### Instance Status Descriptions

| Status | English | Description |
|--------|---------|-------------|
| Not initialized | not_init | Not initialized |
| Creating | creating | Instance is being created |
| Creation failed | creating_failed | Creation failed |
| Running | running | Running normally |
| Agent creating | agent_creating | Agent is being created |
| Gateway updating | gateway_updating | Gateway operations such as toggling public SLB are in progress; most write operations are rejected during this period, typically lasting a few minutes |
| Deleting | deleting | Instance is being released |
| Deletion failed | deleting_failed | Deletion failed |
| Deleted with error | deleted_with_error | Ended after creation failure |
| Deleted | deleted | Deleted |

## Step 3: Get Connection Information

After the instance is ready, obtain the connection address:

```bash
# Query instance details to get connection address
aliyun starrocks DescribeInstances --RegionId cn-hangzhou --InstanceId c-xxx
```

Key information in the response:
- **JDBC Connection Address**: `jdbc:mysql://<host>:<port>`
- **HTTP Connection Address**: `http://<host>:<http_port>`
- **Default Username**: `admin`
- **Initial Password**: The password set via `AdminPassword` during creation

### Connection Examples

```bash
# Connect using MySQL client
mysql -h <host> -P <port> -u admin -p

# Connect using JDBC
jdbc:mysql://<host>:<port>?user=admin&password=<password>
```

## Trial Cluster Limitations

The first 8 CU instance created may be marked as a trial cluster, with the following limitations:

| Limitation | Behavior | Error Message |
|-----------|----------|---------------|
| FE CU | FE CU can only be 4 during creation | `Cu of fe should be select from set [4]` |
| FE Node Count | FE node count can only be 1 during creation | `Number of fe should be in range [1, 1]` |
| BE CU | BE CU can only be 8 during creation | `Cu of be should be select from set [8]` |
| CU Scaling | ModifyCu / ModifyCuPreCheck rejected | `Can't modify resource config of trial cluster` |
| Config Modification | ModifyInstanceConfig rejected | `Invalid configuration change` |
| Add Gateway | Insufficient FE resources (only 1 node/4CU), cannot add gateway | `The available number of nodes exceed` |

> **Unrestricted Operations**: TogglePublicSlb, DescribeInstances, DescribeNodeGroups, DescribeInstanceConfigs can all be executed normally.

## Common Creation Failure Causes

| Symptom | Possible Cause | Troubleshooting |
|---------|---------------|-----------------|
| creating_failed | VPC/VSwitch configuration error | Check if network resources exist and are in the same availability zone |
| creating_failed | Security group configuration error | Check if the security group is properly configured |
| creating_failed | Insufficient inventory | Switch availability zone or change specs |
| creating_failed | Missing RAM permissions | Check if starrocks:CreateInstanceV1 permission is granted |
| Forbidden.RAM | Insufficient RAM permissions | Check RAM user permission configuration |

## Next Steps

- Need a production-grade instance? → Refer to the production configuration templates in [Instance Full Lifecycle](instance-lifecycle.md)
- Daily operations? → Refer to [Daily Operations](operations.md)
- API parameter lookup? → Refer to [API Parameter Reference](api-reference.md)
