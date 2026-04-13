# RAM Policies - MongoDB Instance Management

This document lists the RAM permission policies required for MongoDB instance management (Standalone/Replica Set/Sharded Cluster), covering all operations throughout the instance lifecycle.

## Required Permissions

### Core Permissions (Required for instance creation)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:CreateDBInstance",
        "dds:DescribeDBInstances",
        "dds:DescribeDBInstanceAttribute",
        "dds:DescribeRegions",
        "dds:DescribeAvailableResource"
      ],
      "Resource": "*"
    }
  ]
}
```

### VPC Network Permissions (Query VPC and VSwitch)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches"
      ],
      "Resource": "*"
    }
  ]
}
```

### KMS Key Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "kms:CreateKey",
        "kms:ListKeys",
        "kms:DescribeKey",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion"
      ],
      "Resource": "*"
    }
  ]
}
```

### Resource Group Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "rm:CreateResourceGroup",
        "rm:ListResourceGroups",
        "rm:GetResourceGroup",
        "rm:DeleteResourceGroup"
      ],
      "Resource": "*"
    }
  ]
}
```

### BssOpenApi Permissions (Create KMS instance)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bss:CreateInstance",
        "bss:QueryAvailableInstances",
        "bss:DescribePricingModule"
      ],
      "Resource": "*"
    }
  ]
}
```

### Instance Management Permissions (Full management)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:CreateDBInstance",
        "dds:CreateShardingDBInstance",
        "dds:DeleteDBInstance",
        "dds:DescribeDBInstances",
        "dds:DescribeDBInstanceAttribute",
        "dds:DescribeRegions",
        "dds:DescribeAvailableResource",
        "dds:DescribeRdsVpcs",
        "dds:DescribeRdsVSwitchs",
        "dds:ModifyDBInstanceSpec",
        "dds:ModifyDBInstanceDiskType",
        "dds:ModifyDBInstanceDescription",
        "dds:ModifyDBInstanceMaintainTime",
        "dds:RestartDBInstance",
        "dds:ResetAccountPassword",
        "dds:ModifySecurityIps",
        "dds:DescribeSecurityIps",
        "dds:ModifySecurityGroupConfiguration",
        "dds:DescribeSecurityGroupConfiguration",
        "dds:CreateGlobalSecurityIPGroup",
        "dds:DescribeGlobalSecurityIPGroup",
        "dds:ModifyGlobalSecurityIPGroup",
        "dds:DeleteGlobalSecurityIPGroup",
        "dds:ModifyDBInstanceGlobalSecurityIPGroup",
        "dds:AllocatePublicNetworkAddress",
        "dds:ReleasePublicNetworkAddress",
        "dds:AllocateDBInstanceSrvNetworkAddress",
        "dds:DescribeReplicaSetRole",
        "dds:DescribeShardingNetworkAddress",
        "dds:RenewDBInstance",
        "dds:TransformInstanceChargeType",
        "dds:ModifyInstanceAutoRenewalAttribute",
        "dds:CreateNode",
        "dds:CreateNodeBatch",
        "dds:ModifyNodeSpec",
        "dds:ModifyNodeSpecBatch",
        "dds:DeleteNode"
      ],
      "Resource": "*"
    }
  ]
}
```

### Network Security Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:ModifySecurityIps",
        "dds:DescribeSecurityIps"
      ],
      "Resource": "*"
    }
  ]
}
```

### Backup and Restore Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:DescribeBackups",
        "dds:CreateBackup"
      ],
      "Resource": "*"
    }
  ]
}
```

### Account Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:ResetAccountPassword"
      ],
      "Resource": "*"
    }
  ]
}
```

### Tag Management Permissions

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:TagResources",
        "dds:UntagResources",
        "dds:ListTagResources"
      ],
      "Resource": "*"
    }
  ]
}
```

## Complete Permission Policy

The following is the complete policy containing all permissions required for MongoDB instance management:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dds:CreateDBInstance",
        "dds:CreateShardingDBInstance",
        "dds:DeleteDBInstance",
        "dds:DescribeDBInstances",
        "dds:DescribeDBInstanceAttribute",
        "dds:DescribeRegions",
        "dds:DescribeAvailableResource",
        "dds:DescribeRdsVpcs",
        "dds:DescribeRdsVSwitchs",
        "dds:ModifyDBInstanceSpec",
        "dds:ModifyDBInstanceDiskType",
        "dds:ModifyDBInstanceDescription",
        "dds:ModifyDBInstanceMaintainTime",
        "dds:RestartDBInstance",
        "dds:ResetAccountPassword",
        "dds:ModifySecurityIps",
        "dds:DescribeSecurityIps",
        "dds:ModifySecurityGroupConfiguration",
        "dds:DescribeSecurityGroupConfiguration",
        "dds:CreateGlobalSecurityIPGroup",
        "dds:DescribeGlobalSecurityIPGroup",
        "dds:ModifyGlobalSecurityIPGroup",
        "dds:DeleteGlobalSecurityIPGroup",
        "dds:ModifyDBInstanceGlobalSecurityIPGroup",
        "dds:AllocatePublicNetworkAddress",
        "dds:ReleasePublicNetworkAddress",
        "dds:AllocateDBInstanceSrvNetworkAddress",
        "dds:DescribeReplicaSetRole",
        "dds:DescribeShardingNetworkAddress",
        "dds:RenewDBInstance",
        "dds:TransformInstanceChargeType",
        "dds:ModifyInstanceAutoRenewalAttribute",
        "dds:CreateNode",
        "dds:CreateNodeBatch",
        "dds:ModifyNodeSpec",
        "dds:ModifyNodeSpecBatch",
        "dds:DeleteNode",
        "dds:DescribeBackups",
        "dds:CreateBackup",
        "dds:ResetAccountPassword",
        "dds:TagResources",
        "dds:UntagResources",
        "dds:ListTagResources"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:CreateVpc",
        "vpc:CreateVSwitch"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:CreateKey",
        "kms:ListKeys",
        "kms:ListKmsInstances",
        "kms:DescribeKey",
        "kms:ScheduleKeyDeletion",
        "kms:CancelKeyDeletion"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rm:CreateResourceGroup",
        "rm:ListResourceGroups",
        "rm:GetResourceGroup",
        "rm:DeleteResourceGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:CreateInstance",
        "bss:QueryAvailableInstances",
        "bss:DescribePricingModule"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Description

| Permission | Action | Description | Required Level |
|-----------|--------|-------------|---------------|
| Create instance | `dds:CreateDBInstance` | Create MongoDB replica set instance | Required |
| Delete instance | `dds:DeleteDBInstance` | Delete MongoDB instance | Required for cleanup |
| Query instance list | `dds:DescribeDBInstances` | Query instance list | Required |
| Query instance details | `dds:DescribeDBInstanceAttribute` | Query instance details | Required |
| Query regions | `dds:DescribeRegions` | Query available regions and zones | Required |
| Query available resources | `dds:DescribeAvailableResource` | Query available instance specs | Recommended |
| Modify instance name | `dds:ModifyDBInstanceDescription` | Modify instance name | Optional |
| Modify spec | `dds:ModifyDBInstanceSpec` | Modify instance specification | Optional |
| Restart instance | `dds:RestartDBInstance` | Restart instance | Optional |
| Modify whitelist | `dds:ModifySecurityIps` | Modify IP whitelist | Optional |
| Query whitelist | `dds:DescribeSecurityIps` | Query IP whitelist | Optional |
| Query backups | `dds:DescribeBackups` | Query backup list | Required for cloning |
| Create backup | `dds:CreateBackup` | Manually create backup | Optional |
| Reset password | `dds:ResetAccountPassword` | Reset root password | Optional |
| Query VPC | `vpc:DescribeVpcs` | Query VPC list | Required |
| Query VSwitch | `vpc:DescribeVSwitches` | Query VSwitch list | Required |
| Create VPC | `vpc:CreateVpc` | Create VPC | Optional |
| Create VSwitch | `vpc:CreateVSwitch` | Create VSwitch | Optional |
| Create KMS key | `kms:CreateKey` | Create encryption key | Required for disk encryption |
| Query key list | `kms:ListKeys` | Query KMS key list | Optional |
| Query key details | `kms:DescribeKey` | Query key details | Optional |
| Create resource group | `rm:CreateResourceGroup` | Create resource group | Optional |
| Query resource groups | `rm:ListResourceGroups` | Query resource group list | Optional |
| Create KMS instance | `bss:CreateInstance` | Create KMS instance via BssOpenApi | Optional |
| Query available instances | `bss:QueryAvailableInstances` | Query purchased instances | Optional |

## System Policies

Alibaba Cloud provides the following built-in system policies for direct use:

| Policy Name | Description |
|-------------|-------------|
| `AliyunMongoDBFullAccess` | Full access to MongoDB |
| `AliyunMongoDBReadOnlyAccess` | Read-only access to MongoDB |
| `AliyunVPCReadOnlyAccess` | Read-only access to VPC |
| `AliyunKMSFullAccess` | Full access to KMS |
| `AliyunKMSReadOnlyAccess` | Read-only access to KMS |
| `AliyunResourceGroupFullAccess` | Full access to Resource Groups |
| `AliyunBSSFullAccess` | Full access to Billing Management |

## Full Permission Quick Reference

The following is the complete quick reference table for all permissions required by this skill (including Standalone/Replica Set/Sharded Cluster creation, spec modification, node management, renewal, security configuration, and all other operations):

| Permission Name | Description |
|----------------|-------------|
| `dds:CreateDBInstance` | Create MongoDB Standalone/Replica Set instance |
| `dds:CreateShardingDBInstance` | Create MongoDB Sharded Cluster instance |
| `dds:DescribeDBInstances` | Query instance list |
| `dds:DescribeDBInstanceAttribute` | Query instance details |
| `dds:DescribeShardingNetworkAddress` | Query sharded cluster network addresses |
| `dds:DescribeRegions` | Query available regions |
| `dds:DescribeAvailableResource` | Query available resources |
| `dds:DescribeRdsVpcs` | Query MongoDB-available VPC list |
| `dds:DescribeRdsVSwitchs` | Query MongoDB-available VSwitch list |
| `dds:DeleteDBInstance` | Delete instance (required for cleanup) |
| `dds:ModifyDBInstanceDescription` | Modify instance name |
| `dds:RestartDBInstance` | Restart instance |
| `dds:ResetAccountPassword` | Reset root password |
| `dds:ModifySecurityIps` | Modify IP whitelist |
| `dds:DescribeSecurityIps` | Query IP whitelist |
| `dds:ModifySecurityGroupConfiguration` | Modify ECS security group binding |
| `dds:DescribeSecurityGroupConfiguration` | Query ECS security group binding |
| `dds:CreateGlobalSecurityIPGroup` | Create global whitelist template |
| `dds:DescribeGlobalSecurityIPGroup` | Query global whitelist template |
| `dds:ModifyGlobalSecurityIPGroup` | Modify global whitelist template |
| `dds:DeleteGlobalSecurityIPGroup` | Delete global whitelist template |
| `dds:ModifyDBInstanceGlobalSecurityIPGroup` | Associate global whitelist template with instance |
| `dds:ModifyDBInstanceMaintainTime` | Modify instance maintenance window |
| `dds:AllocatePublicNetworkAddress` | Allocate public network address |
| `dds:ReleasePublicNetworkAddress` | Release public network address |
| `dds:AllocateDBInstanceSrvNetworkAddress` | Allocate SRV address (cloud disk Replica Set/Sharded Cluster only) |
| `dds:DescribeReplicaSetRole` | Query replica set network addresses |
| `dds:DescribeShardingNetworkAddress` | Query sharded cluster network addresses |
| `dds:RenewDBInstance` | Manually renew Subscription instance |
| `dds:TransformInstanceChargeType` | Convert instance billing type (PayAsYouGo ↔ Subscription) |
| `dds:ModifyInstanceAutoRenewalAttribute` | Enable/disable auto-renewal |
| `dds:ModifyDBInstanceSpec` | Modify instance spec configuration |
| `dds:ModifyDBInstanceDiskType` | Cloud disk reconfiguration (ESSD → ESSD AutoPL / adjust provisioned IOPS) |
| `dds:CreateNode` | Add sharded cluster node |
| `dds:CreateNodeBatch` | Batch add sharded cluster nodes |
| `dds:ModifyNodeSpec` | Modify sharded cluster node spec |
| `dds:ModifyNodeSpecBatch` | Batch modify sharded cluster node specs |
| `dds:DeleteNode` | Delete sharded cluster node |
| `vpc:DescribeVpcs` | Query VPC list (alternative) |
| `vpc:DescribeVSwitches` | Query VSwitch list (alternative) |
| `vpc:CreateVpc` | Create VPC (when new VPC is needed) |
| `vpc:CreateVSwitch` | Create VSwitch (when new VSwitch is needed) |
| `kms:CreateKey` | Create KMS key (required for disk encryption) |
| `kms:ListKeys` | Query key list |
| `kms:ListKmsInstances` | Query KMS instance list |
| `kms:DescribeKey` | Query key details |
| `rm:CreateResourceGroup` | Create resource group |
| `rm:ListResourceGroups` | Query resource group list |
| `bss:CreateInstance` | Create KMS instance (via BssOpenApi) |
| `bss:QueryAvailableInstances` | Query available instances |

## Principle of Least Privilege

It is recommended to select permissions based on actual needs following the principle of least privilege:

1. **Instance creation only**: Use core permissions + VPC read permissions
2. **Full management**: Use instance management permissions + VPC permissions + network security permissions
3. **Including backup/restore**: Additionally add backup and restore permissions

## Common Errors

| Error Code | Description | Solution |
|------------|-------------|----------|
| `Forbidden.RAM` | No operation permission | Add the corresponding Action permission |
| `InvalidAccessKeyId.NotFound` | Invalid AccessKey | Check AccessKey configuration |
| `SignatureDoesNotMatch` | Signature error | Check AccessKeySecret |
