---
name: alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
description: |
  Implement AI Coaching best practices on AnalyticDB for PostgreSQL (ADBPG): Leverage Supabase projects (training data management) + ADBPG instances with vector optimization to build RAG-driven coaching systems that guide users through domain-specific workflows, decision-making, or skill development.
  Use when: User wants to create Supabase projects (spb-xxx), ADBPG instances (gp-xxx), vector knowledge bases, or RAG-driven coaching systems on ADBPG.
  Triggers: "Supabase", "ADBPG", "vector database", "knowledge base", "RAG", "AI coaching", "coaching system", "spb-xxx", "gp-xxx"
---

# ADBPG AI Coaching Best Practice

Build RAG-driven coaching systems using **ADBPG Supabase** (training data management) + **ADBPG Vector Knowledge Base** (RAG-driven intelligent coaching).

**Core Capabilities**:
- **Supabase Project**: PostgreSQL-based platform for managing coaching domains, learners, and session records
- **Vector Knowledge Base**: ADBPG instance with vector optimization for RAG-driven coaching
- **Seamless Integration**: Supabase stores structured data, ADBPG powers intelligent AI coaching dialogue

---

## Pre-check: Aliyun CLI >= 3.3.3 Required

> **IMPORTANT**: Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
>
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> **[MUST]** run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

---

## [MUST] CLI User-Agent

> **Every `aliyun` CLI command invocation must include:**
> `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice`

---

## [MUST] CLI AI-Mode Configuration

At the **start** of the Core Workflow (before any CLI invocation):

**[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
Run the following commands before any CLI invocation:
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice"
```

**[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
```bash
aliyun configure ai-mode disable
```

---

## Pre-check: Alibaba Cloud Credentials Required

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly
> - **NEVER** print passwords or API Keys in plain text in logs or stdout
> - **ONLY** use `aliyun configure list` to check credential status
> - When displaying API Keys, show only the first 6 characters + `***` (e.g., `sk-abc1***`)

```bash
aliyun configure list
```

**If no valid profile exists, STOP here.** Configure credentials outside of this session via `aliyun configure` or environment variables.

---

## Scenario Description

| Scenario | Use Case | Target Users |
|----------|----------|--------------|
| **Workflow Coaching** | Guide professionals through structured business processes (sales cycles, project management) | Sales teams, project managers |
| **Decision Support** | Help engineers evaluate trade-offs and make informed technical decisions | Engineers, architects |
| **Skill Development** | Develop communication, negotiation, or technical skills through guided practice | Professionals, new hires |
| **Onboarding** | Systematically guide new team members through technical and process onboarding | New employees, mentors |

### Architecture

```
User (Web / Terminal / Agent)
           │
    ┌──────┴──────┐
    v             v
┌─────────────┐  ┌────────────────────────┐
│  Supabase   │  │  Agent Mode            │
│  (spb-xxx)  │  │  ChatWithKnowledgeBase │
│  - Domains  │  └───────────┬────────────┘
│  - Sessions │              │
└──────┬──────┘              │
       v                     v
┌────────────────────────────────────────┐
│  ADBPG Instance (gp-xxx) + KB          │
│  Domain Knowledge + RAG + LLM          │
└────────────────────────────────────────┘
```

---

## RAM Policy

### Required Permissions

| Operation | RAM Permission |
|-----------|----------------|
| Supabase Project Management | `gpdb:CreateSupabaseProject`, `gpdb:GetSupabaseProject`, `gpdb:ModifySupabaseProjectSecurityIps` |
| ADBPG Instance Management | `gpdb:CreateDBInstance`, `gpdb:DescribeDBInstances`, `gpdb:ModifySecurityIps` |
| Account Management | `gpdb:DescribeAccounts`, `gpdb:CreateAccount` |
| Knowledge Base Operations | `gpdb:InitVectorDatabase`, `gpdb:CreateNamespace`, `gpdb:CreateDocumentCollection`, `gpdb:UploadDocumentAsync`, `gpdb:ChatWithKnowledgeBase` |
| VPC Network | `vpc:DescribeVpcs`, `vpc:DescribeVSwitches`, `vpc:DescribeVSwitchAttributes` |
| NAT Gateway & EIP | `vpc:DescribeNatGateways`, `vpc:CreateNatGateway`, `vpc:DescribeEipAddresses`, `vpc:AllocateEipAddress`, `vpc:AssociateEipAddress`, `vpc:CreateSnatEntry` |

**Recommended System Policies:** `AliyunGPDBFullAccess`, `AliyunVPCFullAccess` (or `AliyunVPCReadOnlyAccess` if NAT already exists)

See [references/ram-policies.md](references/ram-policies.md) for complete list.

> **[MUST] Permission Failure Handling:** When any command fails due to permission errors:
> 1. Read [references/ram-policies.md](references/ram-policies.md) for required permissions
> 2. Use `ram-permission-diagnose` skill to guide the user
> 3. Pause and wait until user confirms permissions granted

---

## Core Workflow

When user says "Help me set up an AI coaching system" or similar, execute the following steps:

> **Smart Defaults Mode**: User only needs minimal input (e.g., "北京i"). The agent auto-parses region, discovers VPC/VSwitch, generates passwords, and presents all parameters for one-click confirmation.

### Step 1: Create Supabase Project

> **Parameters to confirm for this step:**
>
> | Parameter | Default | Notes |
> |-----------|---------|-------|
> | `RegionId` | Auto-parse | "北京i" → `cn-beijing`, "上海b" → `cn-shanghai`, "杭州" → `cn-hangzhou`, "深圳" → `cn-shenzhen` |
> | `ZoneId` | Auto-parse | "北京i" → `cn-beijing-i`; query zones when only city provided |
> | `VpcId` | Auto-discover | Query available VPCs, select one with most available IPs |
> | `VSwitchId` | Auto-discover | Query VSwitches in target zone, select one with most available IPs |
> | `ProjectName` | `ai_coaching` | Supabase project name |
> | `AccountPassword` | Auto-generate | **Password rules:** 8-32 chars, at least 3 of uppercase/lowercase/digits/special (`@#$%^&*`), avoid `!` |

#### 1.1 Check/Create NAT Gateway

> **Important:** Supabase public connection requires a NAT Gateway with SNAT rules in the VPC.

```bash
# Check existing NAT Gateways in VPC
aliyun vpc describe-nat-gateways --profile adbpg \
  --biz-region-id <RegionId> --vpc-id <VpcId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

- **If `TotalCount > 0`** and SNAT entries cover the VSwitch CIDR → **Skip to Step 1.2**
- **If no NAT Gateway** → Get user confirmation, then:

```bash
# 1.1a: Get VSwitch CIDR
aliyun vpc describe-vswitch-attributes --profile adbpg \
  --biz-region-id <RegionId> --vswitch-id <VSwitchId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
# Record: CidrBlock

# 1.1b: Create Enhanced NAT Gateway (requires user confirmation)
# 💰 Cost note: NAT Gateway incurs hourly charges
aliyun vpc create-nat-gateway --profile adbpg \
  --biz-region-id <RegionId> --vpc-id <VpcId> --vswitch-id <VSwitchId> \
  --nat-type Enhanced \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
# Record: NatGatewayId and SnatTableIds.SnatTableId[0]
# Poll until Status=Available

# 1.1c: Find or allocate EIP (requires user confirmation)
# 💰 Cost note: EIP incurs charges; release via VPC console when no longer needed
aliyun vpc describe-eip-addresses --profile adbpg \
  --biz-region-id <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
# If no available EIP:
aliyun vpc allocate-eip-address --profile adbpg \
  --biz-region-id <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
# Record: AllocationId and EipAddress

# 1.1d: Bindind EIP to NAT Gateway (requires user confirmation)
aliyun vpc associate-eip-address --profile adbpg \
  --biz-region-id <RegionId> \
  --allocation-id <EIP-AllocationId> --instance-id <NatGatewayId> \
  --instance-type Nat \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice

# 1.1e: Create SNAT entry (requires user confirmation)
aliyun vpc create-snat-entry --profile adbpg \
  --biz-region-id <RegionId> \
  --snat-table-id <SnatTableId> \
  --source-cidr "<VSwitch-CidrBlock>" --snat-ip "<EipAddress>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

#### 1.2 Create Supabase Project

```bash
aliyun gpdb create-supabase-project --profile adbpg \
  --biz-region-id <RegionId> --zone-id <ZoneId> \
  --project-name <ProjectName> --account-password '<AccountPassword>' \
  --security-ip-list "127.0.0.1" --vpc-id <VpcId> --vswitch-id <VSwitchId> \
  --project-spec 2C4G --storage-size 20 --pay-type Postpaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

**Record:** `ProjectId` (sbp-xxx), `PublicConnectUrl`, API Keys (store securely; do NOT print full API Keys in logs)

> **Timeout:** Supabase project creation takes **5-10 minutes**. Poll status until `running`:
> ```bash
> aliyun gpdb get-supabase-project --profile adbpg \
>   --biz-region-id <RegionId> --project-id <ProjectId> \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
> ```
> Check `Status` field. Retry every 30 seconds until `Status=running`.

### Step 2: Initialize Coaching Platform Database

> **Note:** Steps 2-3 execute on **Supabase Project**, Steps 4-8 on **ADBPG Instance**. They are independent.

Modify whitelist, then connect via psql and execute schema from [references/database-schema.md](references/database-schema.md).

```bash
# Ask user for whitelist IP (do NOT use curl to external services)
# Example: "Please provide the IP address to add to the whitelist"

# Set whitelist
aliyun gpdb modify-supabase-project-security-ips --profile adbpg \
  --biz-region-id <RegionId> --project-id <ProjectId> \
  --security-ip-list "<WhitelistIP>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

### Step 3: Insert Preset Coaching Domains

Execute SQL from [references/database-schema.md](references/database-schema.md) via psql to insert coaching domains and coaching personas.

### Step 4: Discover / Select / Create ADBPG Instance

#### 4.1 Discover Existing Instances

```bash
aliyun gpdb describe-db-instances --profile adbpg \
  --biz-region-id <RegionId> --page-size 100 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

Filter results: `DBInstanceStatus=Running` AND `VectorConfigurationStatus=enabled`.

#### 4.2 User Selects Instance

Present qualifying instances to user:

> **Available Instances (Running + Vector Enabled):**
> | # | Instance ID | Spec | Region | Status | Description |
> |---|-------------|------|--------|--------|-------------|
> | 1 | `gp-xxxxx` | 4C32G | cn-hangzhou | Running | Production |
> | 2 | `gp-yyyyy` | 8C64G | cn-hangzhou | Running | Testing |
>
> Select an instance, or enter "Create New".

- **User selects existing** → Go to Step 4.3
- **User selects "Create New"** → Go to Step 4.4
- **No qualifying instances** → Inform user, go to Step 4.4

#### 4.3 Verify Selected Instance (when using existing)

```bash
aliyun gpdb describe-db-instance-attribute --profile adbpg \
  --db-instance-id <DBInstanceId> --region <RegionId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

Confirm: `DBInstanceStatus=Running` + `VectorConfigurationStatus=enabled`. Then proceed to Step 5.

#### 4.4 Create New Instance (when no existing or user chooses new)

> **Must present configuration and get user confirmation before execution:**
>
> 💰 **Cost note:** Creating an instance incurs charges. Release or pause via [ADBPG Console](https://gpdbnext.console.aliyun.com/) when not in use.

| Config | Default | Notes |
|--------|---------|-------|
| RegionId | `cn-hangzhou` | User-specified |
| ZoneId | `cn-hangzhou-j` | Auto-query VPC/VSwitch after selection |
| EngineVersion | `7.0` | |
| DBInstanceMode | `StorageElastic` | Storage elastic mode |
| DBInstanceCategory | `Basic` | Default Basic; optional HighAvailability |
| InstanceSpec | `4C16G` | Basic: 4C16G/8C32G/16C64G; HA: 4C32G/8C64G/16C128G |
| SegNodeNum | `2` | Basic default 2 (multiples of 2); HA default 4 (multiples of 4) |
| StorageSize | `50` GB | Range: 50–8000 GB |
| SegStorageType | `cloud_essd` | ESSD cloud disk |
| VPC/VSwitch | Auto-discover | Select VSwitch with most available IPs |
| VectorConfigurationStatus | `enabled` | Must be enabled for AI coaching |
| PayType | `Postpaid` | Pay-as-you-go; optional Prepaid |

**Query VSwitch list for the zone:**
```bash
aliyun vpc describe-vswitches --profile adbpg \
  --biz-region-id <RegionId> --zone-id <ZoneId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

Present VSwitch options to user, recommend the one with most available IPs.

After user confirms:
```bash
aliyun gpdb create-db-instance --profile adbpg \
  --biz-region-id <RegionId> --zone-id <ZoneId> \
  --engine gpdb --engine-version "7.0" \
  --db-instance-mode StorageElastic --db-instance-category Basic \
  --instance-spec 4C16G --seg-node-num 2 \
  --storage-size 50 --seg-storage-type cloud_essd \
  --vpc-id <VpcId> --vswitch-id <VSwitchId> \
  --vector-configuration-status enabled --pay-type Postpaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

> **Timeout:** Instance creation takes **10–15 minutes** (max 30 min). Poll every 30–60 seconds:
> ```bash
> aliyun gpdb describe-db-instance-attribute --profile adbpg \
>   --db-instance-id <DBInstanceId> --region <RegionId> \
>   --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
> ```
> Wait until `DBInstanceStatus=Running`.

### Step 5: Configure Database Account

Check if the ADBPG instance already has a database account:

```bash
aliyun gpdb describe-accounts --profile adbpg \
  --db-instance-id <DBInstanceId> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

**Case A: No existing account** → Create a new account:

> **Suggest account creation, confirm with user before executing:**
> - Account name: auto-generate `ai_coaching_XX` (XX = random 2-digit number), or user-specified
> - Password: auto-generate a compliant password (8-32 chars, at least 3 character types, avoid `!`), or user-specified
> - Example: `Account: ai_coaching_01, Password: Coach3Acc#2x9K` — Please confirm or provide your own.
>
> ⚠️ **Important:**
> - **Account name cannot be changed after creation** — confirm carefully!
> - Password can be reset via console, but save it securely now.
> - This account will be used as `ManagerAccount` in Step 6.

```bash
aliyun gpdb create-account --profile adbpg \
  --db-instance-id <DBInstanceId> --region <RegionId> \
  --account-name <ManagerAccount> --account-password '<ManagerAccountPassword>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

**Case B: Account already exists** → Inform the user. If the account was not created by the agent, **ask the user for the existing account password** before proceeding to Step 6.

> **Record:** `ManagerAccount` and `ManagerAccountPassword` — these will be used in Step 6 for knowledge base initialization.

### Step 6: Create Knowledge Base

> **Parameters to confirm for this step:** Auto-generate the following, present to user for confirmation (user may modify), then execute.
>
> | Parameter | Default | Notes |
> |-----------|---------|-------|
> | `Namespace` | `ns_coaching` | Namespace name, cannot be changed after creation |
> | `NamespacePassword` | Auto-generate | Namespace password (same password rules); needed for uploads and coaching sessions |
> | `Collection` | `coaching_knowledge` | Knowledge base name |
> | `EmbeddingModel` | `text-embedding-v4` | Embedding model |

Using the `ManagerAccount` and `ManagerAccountPassword` from Step 5, after user confirms the above parameters, execute:

```bash
# Initialize vector database
aliyun gpdb init-vector-database --profile adbpg \
  --biz-region-id <RegionId> --db-instance-id <DBInstanceId> \
  --manager-account <ManagerAccount> --manager-account-password '<ManagerAccountPassword>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice

# Create namespace
aliyun gpdb create-namespace --profile adbpg \
  --biz-region-id <RegionId> --db-instance-id <DBInstanceId> \
  --manager-account <ManagerAccount> --manager-account-password '<ManagerAccountPassword>' \
  --namespace <Namespace> --namespace-password '<NamespacePassword>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice

# Create document collection
aliyun gpdb create-document-collection --profile adbpg \
  --biz-region-id <RegionId> --db-instance-id <DBInstanceId> \
  --manager-account <ManagerAccount> --manager-account-password '<ManagerAccountPassword>' \
  --namespace <Namespace> --collection <Collection> \
  --embedding-model <EmbeddingModel> --dimension 1024 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

### Step 7 (Optional): Upload Domain Knowledge Documents

> If the user has domain knowledge documents (PDF/TXT/Markdown, etc.), upload them to the knowledge base to enhance coaching quality. This step can be skipped — proceed directly to Step 8 to start coaching.

```bash
aliyun gpdb upload-document-async --profile adbpg \
  --biz-region-id <RegionId> --db-instance-id <DBInstanceId> \
  --namespace <Namespace> --namespace-password '<NamespacePassword>' \
  --collection <Collection> --file-name "domain_knowledge.pdf" \
  --file-url "https://example.com/knowledge.pdf" \
  --document-loader-name ADBPGLoader --chunk-size 500 --chunk-overlap 50 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

**Recommended documents by scenario:** Sales methodologies, process guides (Workflow); Architecture patterns, design docs (Decision Support); Communication frameworks, best practices (Skill Development); Tech stack docs, onboarding guides (Onboarding).

### Step 8: Start Coaching Session

> **Optional parameters for this step:**
>
> | Parameter | Default | Notes |
> |-----------|---------|-------|
> | `Model` | `qwen-max` | LLM model; use `qwen-turbo` for daily practice (lower cost) |
> | `TopK` | `5` | RAG retrieval count |

> **Note:** `SourceCollection` element **MUST include `Namespace` field**.

```bash
aliyun gpdb chat-with-knowledge-base --profile adbpg \
  --biz-region-id <RegionId> --db-instance-id <DBInstanceId> \
  --model-params '{"Model": "<Model>", "Messages": [
    {"Role": "system", "Content": "<system_prompt from coaching_personas>"},
    {"Role": "user", "Content": "<learner message>"}
  ]}' \
  --knowledge-params '{"SourceCollection": [{
    "Collection": "<Collection>", "Namespace": "<Namespace>",
    "NamespacePassword": "<NamespacePassword>", "QueryParams": {"TopK": <TopK>}
  }]}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-postgresql-ai-coaching-best-practice
```

---

## Scenario Quick Reference

| Scenario | Flow |
|----------|------|
| Workflow Coaching | Query `sales_workflow_coach` → Inject coaching persona + process KB → Guide learner through sales stages → Record session |
| Decision Support | Query `architecture_advisor` → Inject coaching persona + tech KB → Guide trade-off analysis → Document decision |
| Skill Development | Query `communication_coach` → Inject coaching persona + best practices KB → Practice scenarios → Provide feedback |
| Onboarding | Query `onboarding_mentor` → Inject coaching persona + tech docs KB → Progressive learning → Verify understanding |

---

## Success Verification

See [references/verification-method.md](references/verification-method.md) for detailed verification steps.

**Quick verification:**
1. Supabase project exists and is `Running`
2. ADBPG instance has `VectorConfigurationStatus=enabled`
3. Database tables exist (coaching_domains, coaching_personas, learners, coaching_sessions)
4. Preset coaching domains are queryable
5. `ChatWithKnowledgeBase` returns meaningful coaching responses

---

## Best Practices

1. **Supabase for data, KB for AI** — Session records through Supabase, coaching dialogue through RAG
2. **Coaching persona is key** — Quality of `system_prompt` determines coaching effectiveness
3. **Always store session records** — Write every coaching round for review and improvement
4. **All operations use `--profile adbpg`** — Consistent credential management
5. **Team isolation with namespaces** — Different teams use different `Namespace`
6. **TopK recommendation: 5** — Reduces token consumption
7. **Daily practice: qwen-turbo** (low cost), **assessments: qwen-max** (high quality)
8. **Idempotent write operations** — Before any resource creation (CreateSupabaseProject, CreateDBInstance, CreateAccount, CreateNamespace, etc.), always query first (Describe/List) to check if the resource already exists. Only create when the resource does not exist. This prevents duplicate resources on retry

---

## References

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation |
| [references/related-apis.md](references/related-apis.md) | All CLI commands and APIs used |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM permissions |
| [references/database-schema.md](references/database-schema.md) | SQL schema and preset coaching domains |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct/incorrect patterns |
| [references/verification-method.md](references/verification-method.md) | Success verification steps |
