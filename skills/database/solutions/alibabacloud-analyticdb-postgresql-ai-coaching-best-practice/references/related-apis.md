# Related APIs and CLI Commands

All CLI commands and APIs used in the AI Coaching Best Practice skill.

## Supabase Project Management

| Operation | CLI Command | API Action | Description |
|-----------|-------------|------------|-------------|
| Create Supabase Project | `aliyun gpdb create-supabase-project` | CreateSupabaseProject | Create a new Supabase project |
| Get Project Details | `aliyun gpdb get-supabase-project` | GetSupabaseProject | Query Supabase project details |
| Get Project API Keys | `aliyun gpdb get-supabase-project-api-keys` | GetSupabaseProjectApiKeys | Retrieve API keys for Supabase project |
| Modify Security IPs | `aliyun gpdb modify-supabase-project-security-ips` | ModifySupabaseProjectSecurityIps | Update whitelist/IP access rules |

## ADBPG Instance Management

| Operation | CLI Command | API Action | Description |
|-----------|-------------|------------|-------------|
| Create Instance | `aliyun gpdb create-db-instance` | CreateDBInstance | Create ADBPG instance with vector optimization |
| Describe Instances | `aliyun gpdb describe-db-instances` | DescribeDBInstances | List and query ADBPG instances |
| Modify Security IPs | `aliyun gpdb modify-security-ips` | ModifySecurityIps | Update instance whitelist |
| Describe Parameters | `aliyun gpdb describe-parameters` | DescribeParameters | Query instance parameters |
| Modify Parameters | `aliyun gpdb modify-parameters` | ModifyParameters | Modify instance parameters |

## Account Management

| Operation | CLI Command | API Action | Description |
|-----------|-------------|------------|-------------|
| Describe Accounts | `aliyun gpdb describe-accounts` | DescribeAccounts | List database accounts |
| Create Account | `aliyun gpdb create-account` | CreateAccount | Create database account (Super/Normal) |

## Knowledge Base Management

| Operation | CLI Command | API Action | Description |
|-----------|-------------|------------|-------------|
| Initialize Vector DB | `aliyun gpdb init-vector-database` | InitVectorDatabase | Initialize vector database for knowledge base |
| Create Namespace | `aliyun gpdb create-namespace` | CreateNamespace | Create namespace for isolation |
| Create Collection | `aliyun gpdb create-document-collection` | CreateDocumentCollection | Create document collection/knowledge base |
| Upload Document | `aliyun gpdb upload-document-async` | UploadDocumentAsync | Upload and process documents asynchronously |
| Query Content | `aliyun gpdb query-content` | QueryContent | Query/retrieve content from knowledge base |
| Chat with KB | `aliyun gpdb chat-with-knowledge-base` | ChatWithKnowledgeBase | RAG-powered coaching chat with knowledge base |

## VPC Network (Prerequisites)

| Operation | CLI Command | API Action | Description |
|-----------|-------------|------------|-------------|
| Describe VPCs | `aliyun vpc describe-vpcs` | DescribeVpcs | Query VPC list |
| Describe VSwitches | `aliyun vpc describe-vswitches` | DescribeVSwitches | Query VSwitch list |
| Describe VSwitch Attributes | `aliyun vpc describe-vswitch-attributes` | DescribeVSwitchAttributes | Query VSwitch details (CIDR) |
| Describe NAT Gateways | `aliyun vpc describe-nat-gateways` | DescribeNatGateways | Query NAT Gateway list |
| Create NAT Gateway | `aliyun vpc create-nat-gateway` | CreateNatGateway | Create Enhanced NAT Gateway |
| Describe EIP Addresses | `aliyun vpc describe-eip-addresses` | DescribeEipAddresses | Query EIP list |
| Allocate EIP Address | `aliyun vpc allocate-eip-address` | AllocateEipAddress | Allocate a new EIP |
| Associate EIP | `aliyun vpc associate-eip-address` | AssociateEipAddress | Bind EIP to NAT Gateway |
| Create SNAT Entry | `aliyun vpc create-snat-entry` | CreateSnatEntry | Create SNAT rule for public access |

## Common Parameters

**IMPORTANT: All `aliyun gpdb` commands use `--biz-region-id` (not `--RegionId`):**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--biz-region-id` | Yes | Region ID (e.g., `cn-hangzhou`) - **use this, NOT `--RegionId`** |
| `--db-instance-id` | Most operations | ADBPG instance ID (`gp-xxxxx`) |
| `--manager-account` | KB operations | Super account name |
| `--manager-account-password` | KB operations | Super account password |
| `--namespace-password` | Namespace operations | Namespace password |
| `--collection` | Collection operations | Collection name |
| `--profile adbpg` | Recommended | Named profile for credentials |

**VPC commands also use `--biz-region-id`:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--biz-region-id` | Yes | Region ID (e.g., `cn-hangzhou`) |
| `--vpc-id` | VPC operations | VPC ID (`vpc-xxxxx`) |
| `--vswitch-id` | VSwitch operations | VSwitch ID (`vsw-xxxxx`) |

## Example Command Patterns

### Create Supabase Project
```bash
aliyun gpdb create-supabase-project --profile adbpg \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-j \
  --project-name ai_coaching \
  --account-password '<AccountPassword>' \
  --security-ip-list "127.0.0.1" \
  --vpc-id vpc-xxxxx \
  --vswitch-id vsw-xxxxx \
  --project-spec 2C4G \
  --storage-size 20 \
  --pay-type Postpaid \
  --user-agent AlibabaCloud-Agent-Skills
```

### Modify Supabase Security IPs
```bash
# Ask user for whitelist IP (do NOT use curl to external services)
aliyun gpdb modify-supabase-project-security-ips --profile adbpg \
  --biz-region-id cn-hangzhou \
  --project-id spb-xxxxx \
  --security-ip-list "<WhitelistIP>" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Describe DB Instances
```bash
aliyun gpdb describe-db-instances --profile adbpg \
  --biz-region-id cn-hangzhou \
  --output cols="DBInstanceId,DBInstanceStatus,EngineVersion,VectorConfigurationStatus" rows="Items.DBInstance[]" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create ADBPG Instance with Vector Optimization
```bash
aliyun gpdb create-db-instance --profile adbpg \
  --biz-region-id cn-hangzhou \
  --zone-id cn-hangzhou-j \
  --engine gpdb \
  --engine-version "7.0" \
  --db-instance-mode StorageElastic \
  --db-instance-category Basic \
  --instance-spec 4C16G \
  --seg-node-num 2 \
  --storage-size 50 \
  --seg-storage-type cloud_essd \
  --vpc-id vpc-xxxxx \
  --vswitch-id vsw-xxxxx \
  --vector-configuration-status enabled \
  --pay-type Postpaid \
  --user-agent AlibabaCloud-Agent-Skills
```

### Initialize Vector Database
```bash
aliyun gpdb init-vector-database --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<ManagerAccountPassword>' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Namespace
```bash
aliyun gpdb create-namespace --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<ManagerAccountPassword>' \
  --namespace ns_coaching \
  --namespace-password '<NamespacePassword>' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Document Collection
```bash
aliyun gpdb create-document-collection --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --manager-account admin_user \
  --manager-account-password '<ManagerAccountPassword>' \
  --namespace ns_coaching \
  --collection coaching_knowledge \
  --embedding-model text-embedding-v4 \
  --dimension 1024 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Upload Document
```bash
aliyun gpdb upload-document-async --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --namespace ns_coaching \
  --namespace-password '<NamespacePassword>' \
  --collection coaching_knowledge \
  --file-name "domain_knowledge.pdf" \
  --file-url "https://example.com/knowledge.pdf" \
  --document-loader-name ADBPGLoader \
  --chunk-size 500 \
  --chunk-overlap 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Chat with Knowledge Base (AI Coaching)
```bash
aliyun gpdb chat-with-knowledge-base --profile adbpg \
  --biz-region-id cn-hangzhou \
  --db-instance-id gp-xxxxx \
  --model-params '{
    "Model": "qwen-max",
    "Messages": [
      {"Role": "system", "Content": "<system_prompt from coaching_personas>"},
      {"Role": "user", "Content": "<learner message>"}
    ]
  }' \
  --knowledge-params '{
    "SourceCollection": [{
      "Collection": "coaching_knowledge",
      "Namespace": "ns_coaching",
      "NamespacePassword": "<NamespacePassword>",
      "QueryParams": {"TopK": 5}
    }]
  }' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Query Accounts
```bash
aliyun gpdb describe-accounts --profile adbpg \
  --db-instance-id gp-xxxxx \
  --output cols="AccountName,AccountType,AccountStatus" rows="Accounts.DBInstanceAccount[]" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Create Account
```bash
# Note: --account-type defaults to Super; no --biz-region-id, use --region
aliyun gpdb create-account --profile adbpg \
  --db-instance-id gp-xxxxx --region cn-hangzhou \
  --account-name ai_coaching_01 \
  --account-password 'Coach3Acc#2x9K' \
  --user-agent AlibabaCloud-Agent-Skills
```

## NAT Gateway for Supabase Public Access

### Step 1: Check NAT Gateway
```bash
aliyun vpc describe-nat-gateways --profile adbpg \
  --biz-region-id cn-hangzhou \
  --vpc-id vpc-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```
If `TotalCount > 0` and SNAT entries cover the VSwitch CIDR, skip remaining NAT steps.

### Step 2: Get VSwitch CIDR
```bash
aliyun vpc describe-vswitch-attributes --profile adbpg \
  --biz-region-id cn-hangzhou \
  --vswitch-id vsw-xxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```
Record `CidrBlock` from response.

### Step 3: Create Enhanced NAT Gateway (requires user confirmation)
```bash
# 💰 Cost note: NAT Gateway incurs hourly charges
aliyun vpc create-nat-gateway --profile adbpg \
  --biz-region-id cn-hangzhou \
  --vpc-id vpc-xxxxx --vswitch-id vsw-xxxxx \
  --nat-type Enhanced \
  --user-agent AlibabaCloud-Agent-Skills
```
Record `NatGatewayId` and `SnatTableIds.SnatTableId[0]`. Poll until `Status=Available`.

### Step 4: Find or Allocate EIP (requires user confirmation)
```bash
# Check existing EIPs
aliyun vpc describe-eip-addresses --profile adbpg \
  --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills

# If no available EIP, allocate a new one:
# 💰 Cost note: EIP incurs charges; release via VPC console when no longer needed
aliyun vpc allocate-eip-address --profile adbpg \
  --biz-region-id cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```
Record `AllocationId` and `EipAddress`.

### Step 5: Bind EIP to NAT Gateway (requires user confirmation)
```bash
aliyun vpc associate-eip-address --profile adbpg \
  --biz-region-id cn-hangzhou \
  --allocation-id eip-xxxxx \
  --instance-id ngw-xxxxx \
  --instance-type Nat \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 6: Create SNAT Entry (requires user confirmation)
```bash
aliyun vpc create-snat-entry --profile adbpg \
  --biz-region-id cn-hangzhou \
  --snat-table-id stb-xxxxx \
  --source-cidr "<VSwitch-CidrBlock>" --snat-ip "<EipAddress>" \
  --user-agent AlibabaCloud-Agent-Skills
```
