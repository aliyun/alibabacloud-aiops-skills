# RAM Policies for Lingjun Cluster Management

This document defines all required RAM permissions for the Alibaba Cloud Lingjun Cluster Management skill, organized into 4 permission sets following the principle of least privilege.

## Permission Sets Overview

| Permission Set | Permissions Count | Use Case |
|----------------|-------------------|----------|
| **Read-Only** | 8 | Query clusters, nodes, resources (incl. ECS custom images) |
| **Scaling** | 3 | Scale clusters up/down, track tasks |
| **Node Management** | 9 | Manage node groups / individual nodes / BSS purchase & order polling |
| **Full** | 20 (all) | Complete cluster lifecycle management |

**Namespace coverage** (aligned with design doc §1.2):
- `eflo:*` — Eflo-Controller (cluster / node / node-group / task / images / machine-types)
- `bss:*` — BssOpenApi (Lingxiao purchase, order polling for Lingjun nodes)
- `ecs:*` — ECS (custom image query via `DescribeImages`)

---

## Permission Set 1: Read-Only Permissions

For users who only need to view cluster information without making changes.

### Permissions (8)

| Permission | API Action | Description |
|------------|------------|-------------|
| `eflo:ListClusters` | ListClusters | List all clusters in a region |
| `eflo:DescribeCluster` | DescribeCluster | Get detailed cluster information |
| `eflo:ListClusterNodes` | ListClusterNodes | List nodes in a cluster |
| `eflo:DescribeRegions` | DescribeRegions | Query supported regions |
| `eflo:ListMachineTypes` | ListMachineTypes | List available machine types |
| `eflo:DescribeNodeType` | DescribeNodeType | Get machine type specifications |
| `eflo:ListImages` | ListImages | List available Lingjun system images |
| `ecs:DescribeImages` | DescribeImages | List ECS **custom** images (used when user selects a non-system image for node provisioning) |

### RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ListClusters",
        "eflo:DescribeCluster",
        "eflo:ListClusterNodes",
        "eflo:DescribeRegions",
        "eflo:ListMachineTypes",
        "eflo:DescribeNodeType",
        "eflo:ListImages"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeImages"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Permission Set 2: Scaling Permissions

For users who manage cluster capacity (expand/shrink operations).

### Permissions (3)

| Permission | API Action | Description |
|------------|------------|-------------|
| `eflo:ExtendCluster` | ExtendCluster | Add nodes to cluster |
| `eflo:ShrinkCluster` | ShrinkCluster | Remove nodes from cluster |
| `eflo:DescribeTask` | DescribeTask | Track async task progress |

### RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ExtendCluster",
        "eflo:ShrinkCluster",
        "eflo:DescribeTask"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: Scaling permissions typically require Read-Only permissions as well to query cluster state before operations.

---

## Permission Set 3: Node Management Permissions

For users who manage node groups and individual nodes.

### Permissions (9)

| Permission | API Action | Description |
|------------|------------|-------------|
| `eflo:ListNodeGroups` | ListNodeGroups | List node groups in cluster |
| `eflo:DescribeNodeGroup` | DescribeNodeGroup | Get node group details |
| `eflo:CreateNodeGroup` | CreateNodeGroup | Create new node group |
| `eflo:UpdateNodeGroup` | UpdateNodeGroup | Update an existing node group (name / image / password / user-data / file-system-mount) |
| `eflo:DescribeNode` | DescribeNode | Get node details |
| `eflo:DeleteNode` | DeleteNode | Release unused node |
| `eflo:ChangeNodeGroup` | ChangeNodeGroup | Move node between groups |
| `bss:CreateInstance` | CreateInstance | Purchase new Lingjun nodes via Lingxiao BssOpenApi (`ProductCode=bccluster`) |
| `bss:QueryOrders` | QueryOrders | Poll Lingxiao order status during node provisioning |

### RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ListNodeGroups",
        "eflo:DescribeNodeGroup",
        "eflo:CreateNodeGroup",
        "eflo:UpdateNodeGroup",
        "eflo:DescribeNode",
        "eflo:DeleteNode",
        "eflo:ChangeNodeGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:CreateInstance",
        "bss:QueryOrders"
      ],
      "Resource": "*"
    }
  ]
}
```

**Note**: Node creation via BssOpenApi requires both `bss:CreateInstance` (submit order) and `bss:QueryOrders` (track order). The BSS namespace is separate from `eflo:*` and must be granted explicitly.

---

## Permission Set 4: Full Permissions

Complete cluster lifecycle management combining all permission sets.

### Full Permission List (20)

**Read-Only (8)**: ListClusters, DescribeCluster, ListClusterNodes, DescribeRegions, ListMachineTypes, DescribeNodeType, ListImages, **ecs:DescribeImages**

**Scaling (3)**: ExtendCluster, ShrinkCluster, DescribeTask

**Node Management (9)**: ListNodeGroups, DescribeNodeGroup, CreateNodeGroup, **UpdateNodeGroup**, DescribeNode, DeleteNode, ChangeNodeGroup, **bss:CreateInstance**, **bss:QueryOrders**

### RAM Policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ListClusters",
        "eflo:DescribeCluster",
        "eflo:ListClusterNodes",
        "eflo:ExtendCluster",
        "eflo:ShrinkCluster",
        "eflo:DescribeTask",
        "eflo:DescribeRegions",
        "eflo:ListMachineTypes",
        "eflo:DescribeNodeType",
        "eflo:ListImages",
        "eflo:ListNodeGroups",
        "eflo:DescribeNodeGroup",
        "eflo:CreateNodeGroup",
        "eflo:UpdateNodeGroup",
        "eflo:DescribeNode",
        "eflo:DeleteNode",
        "eflo:ChangeNodeGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:CreateInstance",
        "bss:QueryOrders"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeImages"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Recommended Permission Combinations

### Development Environment
**Read-Only + Node Management** - Allows developers to query resources and test node operations without affecting production clusters.

### Operations Team
**Read-Only + Scaling** - Enables capacity management while preventing accidental node group modifications.

### Platform Administrators
**Full Permissions** - Complete control over cluster lifecycle for production management.

---

## Applying RAM Policies

### Method 1: Alibaba Cloud Console

1. Navigate to [RAM Console](https://ram.console.aliyun.com/)
2. Go to **Identities** > **Users** (or **Roles**)
3. Select target user/role → **Add Permissions**
4. Click **Create Policy** → **JSON**
5. Paste the appropriate policy JSON from above
6. Name the policy (e.g., `LingjunReadOnly`, `LingjunFullAccess`)
7. Click **OK** to create and attach

### Method 2: Aliyun CLI

```bash
# Create custom policy
aliyun ram create-policy \
  --policy-name LingjunFullAccess \
  --policy-document '{
    "Version": "1",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "eflo:ListClusters",
        "eflo:DescribeCluster",
        "eflo:ListClusterNodes",
        "eflo:ExtendCluster",
        "eflo:ShrinkCluster",
        "eflo:DescribeTask",
        "eflo:DescribeRegions",
        "eflo:ListMachineTypes",
        "eflo:DescribeNodeType",
        "eflo:ListImages",
        "eflo:ListNodeGroups",
        "eflo:DescribeNodeGroup",
        "eflo:CreateNodeGroup",
        "eflo:UpdateNodeGroup",
        "eflo:DescribeNode",
        "eflo:DeleteNode",
        "eflo:ChangeNodeGroup"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bss:CreateInstance",
        "bss:QueryOrders"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeImages"
      ],
      "Resource": "*"
    }]
  }'

# Attach policy to RAM user
aliyun ram attach-policy-to-user \
  --policy-name LingjunFullAccess \
  --policy-type Custom \
  --user-name <your-ram-user>
```

---

## Resource-Specific Policies

To restrict permissions to specific clusters or resource groups, use resource ARNs:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eflo:DescribeCluster",
        "eflo:ExtendCluster",
        "eflo:ShrinkCluster"
      ],
      "Resource": [
        "acs:eflo:cn-wulanchabu:*:cluster/i116913051663373010974",
        "acs:eflo:cn-hangzhou:*:cluster/i116913051663373010975"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "eflo:ListClusters",
        "eflo:DescribeRegions"
      ],
      "Resource": "*"
    }
  ]
}
```

**Resource ARN Format**: `acs:eflo:<region>:<account-id>:cluster/<cluster-id>`

---

## Permission Troubleshooting

### Error: User not authorized to operate on the specified resource

**Cause**: Missing required RAM permission for the API action.

**Solution**:
1. Identify the failed API action from error message
2. Check which permission set includes that action (see tables above)
3. Contact account administrator to grant the appropriate permission set
4. Use `ram-permission-diagnose` skill for guided troubleshooting

### Error: Forbidden.RAM

**Cause**: Resource-specific restriction blocking access.

**Solution**:
1. Verify resource ARN in RAM policy matches target resource
2. Check for conflicting `Deny` statements in attached policies
3. For development/testing, use `"Resource": "*"` if security requirements allow

### Error: Insufficient Balance (when creating nodes)

**Cause**: Missing billing permissions or insufficient account balance.

**Solution**:
1. Ensure `bss:CreateInstance` and `bss:QueryOrders` permissions are granted
2. Verify account has sufficient balance for the purchase
3. Check billing console for payment issues

---

## Verifying Current Permissions

```bash
# Check current identity
aliyun sts get-caller-identity

# List policies attached to user
aliyun ram list-policies-for-user --user-name <ram-user>

# Get policy details
aliyun ram get-policy --policy-name LingjunFullAccess --policy-type Custom

# Get policy version document
aliyun ram get-policy-version \
  --policy-name LingjunFullAccess \
  --policy-type Custom \
  --version-id v1
```

---

## Best Practices

### 1. Principle of Least Privilege
Grant only the minimum permissions needed:
- **DevOps**: Read-Only + Scaling
- **Developers**: Read-Only + Node Management (for testing)
- **Admins**: Full Permissions

### 2. Use Resource Groups
Organize clusters by project/environment and apply group-level permissions:
```json
{
  "Effect": "Allow",
  "Action": ["eflo:*"],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "eflo:ResourceGroup": "rg-production"
    }
  }
}
```

### 3. Separate Read/Write Policies
Create distinct policies for querying vs modifying resources to simplify auditing.

### 4. Enable MFA for Sensitive Operations
Require multi-factor authentication for destructive actions:
- ShrinkCluster
- DeleteNode

### 5. Regular Permission Audits
- Review attached policies quarterly
- Remove unused permissions
- Update policies when skill features change

### 6. Use RAM Roles for Applications
Prefer temporary credentials via roles over static AK/SK for automated systems.

---

## Changes from Previous Version

**Added Permissions (13)**:
- `eflo:ListMachineTypes` - Query available machine types
- `eflo:DescribeNodeType` - Get machine type specifications
- `eflo:ListImages` - Query available Lingjun system images
- `eflo:ListNodeGroups` - List node groups in cluster
- `eflo:DescribeNodeGroup` - Get node group details
- `eflo:CreateNodeGroup` - Create new node group
- `eflo:UpdateNodeGroup` - Update node group (design doc §3.1.8)
- `eflo:DescribeNode` - Get node details
- `eflo:DeleteNode` - Release unused node
- `eflo:ChangeNodeGroup` - Move node between groups
- `bss:CreateInstance` - Purchase new Lingjun nodes (Lingxiao BssOpenApi)
- `bss:QueryOrders` - Poll Lingxiao order status
- `ecs:DescribeImages` - Query ECS custom images for node provisioning

**Removed Permissions (1)**:
- `eflo:ListFreeNodes` - ❌ No longer supported/needed

**Organization Changes**:
- Permissions now organized into 4 logical sets (Read-Only, Scaling, Node Management, Full)
- Added resource-specific policy examples
- Enhanced troubleshooting guide

---

## Related Documentation

- [Alibaba Cloud RAM Documentation](https://www.alibabacloud.com/help/ram)
- [RAM Policy Language Reference](https://www.alibabacloud.com/help/ram/developer-reference/ram-policy-language)
- [Eflo-Controller API Reference](https://api.aliyun.com/api/eflo-controller/2022-12-15)
- [RAM Best Practices](https://www.alibabacloud.com/help/ram/user-guide/ram-best-practices)
