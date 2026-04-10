# Alibaba Cloud RAM Permissions

Required RAM policies for the AI Coaching Best Practice skill.

## Minimum Permission Requirements

The following RAM permissions are required for all operations in this skill.

### Supabase Project Operations

| API Action | RAM Permission | Description |
|------------|----------------|-------------|
| CreateSupabaseProject | `gpdb:CreateSupabaseProject` | Create Supabase projects |
| GetSupabaseProject | `gpdb:GetSupabaseProject` | Query project details |
| GetSupabaseProjectApiKeys | `gpdb:GetSupabaseProjectApiKeys` | Retrieve API keys |
| ModifySupabaseProjectSecurityIps | `gpdb:ModifySupabaseProjectSecurityIps` | Update project whitelist |

### ADBPG Instance Operations

| API Action | RAM Permission | Description |
|------------|----------------|-------------|
| CreateDBInstance | `gpdb:CreateDBInstance` | Create ADBPG instances |
| DescribeDBInstances | `gpdb:DescribeDBInstances` | List/query instances |
| DescribeDBInstanceAttribute | `gpdb:DescribeDBInstanceAttribute` | Get instance attributes |
| ModifySecurityIps | `gpdb:ModifySecurityIps` | Update instance whitelist |
| DescribeParameters | `gpdb:DescribeParameters` | Query parameters |
| ModifyParameters | `gpdb:ModifyParameters` | Modify parameters |

### Account Operations

| API Action | RAM Permission | Description |
|------------|----------------|-------------|
| DescribeAccounts | `gpdb:DescribeAccounts` | List database accounts |
| CreateAccount | `gpdb:CreateAccount` | Create database accounts |
| DescribeAccountPrivilege | `gpdb:DescribeAccountPrivilege` | Query account privileges |

### Knowledge Base Operations

| API Action | RAM Permission | Description |
|------------|----------------|-------------|
| InitVectorDatabase | `gpdb:InitVectorDatabase` | Initialize vector database |
| CreateNamespace | `gpdb:CreateNamespace` | Create namespace |
| CreateDocumentCollection | `gpdb:CreateDocumentCollection` | Create knowledge base |
| UploadDocumentAsync | `gpdb:UploadDocumentAsync` | Upload documents |
| QueryContent | `gpdb:QueryContent` | Query knowledge base |
| ChatWithKnowledgeBase | `gpdb:ChatWithKnowledgeBase` | RAG-powered coaching chat |
| DescribeVectorDatabase | `gpdb:DescribeVectorDatabase` | Query vector DB status |

### VPC Network Operations (Prerequisites)

| API Action | RAM Permission | Description |
|------------|----------------|-------------|
| DescribeVpcs | `vpc:DescribeVpcs` | Query VPC list |
| DescribeVSwitches | `vpc:DescribeVSwitches` | Query VSwitch list |
| DescribeVSwitchAttributes | `vpc:DescribeVSwitchAttributes` | Query VSwitch details (CIDR) |
| DescribeNatGateways | `vpc:DescribeNatGateways` | Query NAT Gateway list |
| CreateNatGateway | `vpc:CreateNatGateway` | Create Enhanced NAT Gateway |
| DescribeEipAddresses | `vpc:DescribeEipAddresses` | Query EIP addresses |
| AllocateEipAddress | `vpc:AllocateEipAddress` | Allocate a new EIP |
| AssociateEipAddress | `vpc:AssociateEipAddress` | Bind EIP to NAT Gateway |
| CreateSnatEntry | `vpc:CreateSnatEntry` | Create SNAT rule |

## System Policies

Use these system policies as baseline:

| Policy Name | Type | Permissions |
|-------------|------|-------------|
| `AliyunGPDBFullAccess` | System | Full access to AnalyticDB PostgreSQL |
| `AliyunVPCFullAccess` | System | Full access to VPC resources (needed for NAT/EIP creation) |
| `AliyunVPCReadOnlyAccess` | System | Read-only access to VPC resources (if NAT already exists) |

## Custom Policy Example

For least-privilege access, create a custom policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "gpdb:CreateSupabaseProject",
        "gpdb:GetSupabaseProject",
        "gpdb:GetSupabaseProjectApiKeys",
        "gpdb:ModifySupabaseProjectSecurityIps",
        "gpdb:CreateDBInstance",
        "gpdb:DescribeDBInstances",
        "gpdb:DescribeDBInstanceAttribute",
        "gpdb:ModifySecurityIps",
        "gpdb:DescribeAccounts",
        "gpdb:CreateAccount",
        "gpdb:InitVectorDatabase",
        "gpdb:CreateNamespace",
        "gpdb:CreateDocumentCollection",
        "gpdb:UploadDocumentAsync",
        "gpdb:QueryContent",
        "gpdb:ChatWithKnowledgeBase"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "vpc:DescribeVpcs",
        "vpc:DescribeVSwitches",
        "vpc:DescribeVSwitchAttributes",
        "vpc:DescribeNatGateways",
        "vpc:CreateNatGateway",
        "vpc:DescribeEipAddresses",
        "vpc:AllocateEipAddress",
        "vpc:AssociateEipAddress",
        "vpc:CreateSnatEntry"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission by Scenario

### Scenario 1: Full Deployment (Create Everything)

Required policies:
- `AliyunGPDBFullAccess`
- `AliyunVPCReadOnlyAccess`

### Scenario 2: Only Knowledge Base Operations

If instance already exists, only need:
- `gpdb:InitVectorDatabase`
- `gpdb:CreateNamespace`
- `gpdb:CreateDocumentCollection`
- `gpdb:UploadDocumentAsync`
- `gpdb:QueryContent`
- `gpdb:ChatWithKnowledgeBase`

### Scenario 3: Only Supabase Project Management

Required policies:
- `gpdb:CreateSupabaseProject`
- `gpdb:GetSupabaseProject`
- `gpdb:GetSupabaseProjectApiKeys`
- `gpdb:ModifySupabaseProjectSecurityIps`

### Scenario 4: Read-Only Operations

For querying and analysis only:
- `gpdb:DescribeDBInstances`
- `gpdb:DescribeDBInstanceAttribute`
- `gpdb:DescribeAccounts`
- `gpdb:GetSupabaseProject`
- `gpdb:QueryContent`

## Permission Failure Handling

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read this `ram-policies.md` file to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## RAM Role Configuration

For ECS-based deployment, attach the custom policy to a RAM role:

1. Create RAM role in console: https://ram.console.aliyun.com/roles
2. Attach the custom policy above
3. Assign role to ECS instance
4. Configure CLI with `--mode EcsRamRole`

```bash
aliyun configure set \
  --mode EcsRamRole \
  --ram-role-name ADBPGCoachingRole \
  --region cn-hangzhou
```

## Security Best Practices

1. **Use RAM users, not root account** - Create dedicated RAM users for automation
2. **Apply least privilege** - Only grant permissions actually needed
3. **Rotate access keys** - Update credentials periodically
4. **Use STS for temporary access** - For short-lived operations
5. **Scope resources when possible** - Use resource-level permissions

## Troubleshooting Permission Errors

### Error: `Forbidden.RAM`

```
Error code: Forbidden.RAM
Error message: The specified action is not authorized.
```

**Solution:**
1. Check which API action triggered the error
2. Verify the RAM user has the corresponding permission
3. Attach the missing policy or action

### Error: `InvalidAccount.NotExist`

```
Error code: InvalidAccount.NotExist
Error message: The specified account does not exist.
```

**Solution:**
- Create the Super account first using `CreateAccount`

### Error: `OperationDenied.InstanceStatus`

```
Error code: OperationDenied.InstanceStatus
Error message: The instance status does not support this operation.
```

**Solution:**
- Wait for instance to be in `Running` state before proceeding
