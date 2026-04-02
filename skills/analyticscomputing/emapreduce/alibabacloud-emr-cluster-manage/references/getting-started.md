# Quick Start: Create Your First EMR Cluster from Scratch

This guide helps first-time users complete: prerequisite check → create first cluster → verify running → cleanup resources.

## Prerequisites

### 1. CLI Environment

```bash
# Verify Alibaba Cloud CLI installed
aliyun version

# Verify credentials configured (should show current profile)
aliyun configure list
```

### 2. Network Resources

Creating EMR cluster requires the following cloud resources, if not available need to create first. **Before execution confirm RegionId with user** (e.g., `cn-hangzhou`, `cn-beijing`, `cn-shanghai`):

```bash
# Check if VPC available
aliyun vpc DescribeVpcs --RegionId <RegionId>

# Check if VSwitch under VPC
aliyun vpc DescribeVSwitches --RegionId <RegionId> --VpcId vpc-xxx

# Check if regular security group available (Note: EMR doesn't support enterprise security group)
aliyun ecs DescribeSecurityGroups --RegionId <RegionId> --VpcId vpc-xxx --SecurityGroupType normal

# Check if SSH key pair available
aliyun ecs DescribeKeyPairs --RegionId <RegionId>
```

> **Don't have these resources?** Please first create VPC, VSwitch, security group and key pair via Alibaba Cloud console or CLI. Claude can help you complete these operations.

### 3. Confirm Zone Information

Record the following information, will be used when creating cluster:
- RegionId (e.g., `cn-hangzhou`)
- ZoneId (e.g., `cn-hangzhou-h`, from VSwitch所在 zone)
- VpcId、VSwitchId、SecurityGroupId、KeyPairName

## Step 1: View Available Versions

```bash
# Query EMR versions available for data lake cluster
aliyun emr ListReleaseVersions --RegionId cn-hangzhou --ClusterType DATALAKE
```

Select latest version (e.g., `EMR-5.16.0`), new clusters recommend always using latest version.

## Step 2: View Available Instance Types

```bash
# Query MASTER node available specs
aliyun emr ListInstanceTypes --RegionId cn-hangzhou --ZoneId cn-hangzhou-h \
  --ClusterType DATALAKE --PaymentType PayAsYouGo --NodeGroupType MASTER

# Query CORE node available specs
aliyun emr ListInstanceTypes --RegionId cn-hangzhou --ZoneId cn-hangzhou-h \
  --ClusterType DATALAKE --PaymentType PayAsYouGo --NodeGroupType CORE
```

**Dev/test recommended**: `ecs.g8i.xlarge` (4 vCPU / 16 GiB), low cost and meets test needs.

## Step 3: Create Cluster

Below is a **minimal cluster for dev/test**, using NORMAL deployment mode (non-HA), pay-as-you-go:

> **Need public network access?** MASTER node's `WithPublicIp` field controls whether to allocate public IP. Set to `true` to SSH directly to MASTER node; set to `false` (default) means only private IP, need access via jumpbox, VPN etc. **Dev/test recommend enable, production recommend disable.**

```bash
aliyun emr RunCluster --RegionId cn-hangzhou \
  --ClientToken $(uuidgen) \
  --ClusterName "my-first-emr" \
  --ClusterType "DATALAKE" \
  --ReleaseVersion "EMR-5.16.0" \
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
      "WithPublicIp": true,
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

Returns `ClusterId` (e.g., `c-xxx`), record it for subsequent operations.

> **Note**: Creating cluster incurs cost. NORMAL mode only 1 MASTER node, suitable for dev/test, don't use for production. Enabling public IP incurs small public network bandwidth cost.

## Step 4: Verify Cluster Status

Cluster creation is async operation, usually takes 5-15 minutes.

```bash
# View cluster status
aliyun emr GetCluster --RegionId cn-hangzhou --ClusterId c-xxx
```

**State Transition**: `STARTING` → `BOOTSTRAPPING` → `RUNNING`

Wait for `ClusterState` to become `RUNNING` means cluster ready.

## Step 5: View Node Information

```bash
# View node groups
aliyun emr ListNodeGroups --RegionId cn-hangzhou --ClusterId c-xxx

# View all nodes
aliyun emr ListNodes --RegionId cn-hangzhou --ClusterId c-xxx
```

Confirm all node states are `Running`.

### Access Cluster

Depending on whether MASTER node enabled `WithPublicIp` when creating cluster, access methods differ:

**Public network enabled (WithPublicIp: true): Direct SSH**

Get MASTER node's public IP from `ListNodes` result, login directly:

```bash
ssh -i ~/.ssh/my-keypair.pem root@<MASTER_PUBLIC_IP>
```

**Public network disabled (default): Via jumpbox or other methods**

Cluster nodes only have private IP, can access via:

- **Jumpbox**: Jump via ECS with public network in same VPC
  ```bash
  ssh -i ~/.ssh/my-keypair.pem -J root@<JUMPBOX_PUBLIC_IP> root@<MASTER_PRIVATE_IP>
  ```
- **Workbench**: Passwordless login to node instance in ECS console
- **VPN**: Connect to VPC internal network via VPN gateway

## Common Creation Failure Causes

| Symptom | Possible Cause | Diagnosis Method |
|------|---------|---------|
| START_FAILED | VPC/VSwitch/Security group configuration error | Check if network resources exist and in same zone |
| START_FAILED | Security group type error | EMR only supports **regular security group**, not enterprise security group |
| START_FAILED | Instance type stock insufficient | Change zone or change spec, query with ListInstanceTypes |
| START_FAILED | RAM role missing | Confirm AliyunECSInstanceForEMRRole role created |
| START_FAILED | Key pair doesn't exist | Check if KeyPairName correct |

## Next Steps

- When need other scenarios, return to intent routing table in `SKILL.md` to select the appropriate reference document.