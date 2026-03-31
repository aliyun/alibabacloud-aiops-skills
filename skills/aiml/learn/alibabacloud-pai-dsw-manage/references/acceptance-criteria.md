# Acceptance Criteria: alibabacloud-pai-dsw-manage

**Scenario**: PAI DSW Instance Lifecycle Management
**Purpose**: Test acceptance criteria for the skill

---

## 1. Get Workspace ID (Required for CreateInstance)

> See SKILL.md "Parameter Confirmation" section for WorkspaceId requirements and `list-workspaces` command.

#### ✅ CORRECT
```bash
aliyun aiworkspace list-workspaces \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Assuming workspace ID without confirming with user
aliyun pai-dsw create-instance --workspace-id 12345 ...
# WRONG: Must confirm workspace with user first
```

---

## 2. Product Name

#### ✅ CORRECT
```bash
aliyun pai-dsw create-instance ...
aliyun pai-dsw list-instances ...
aliyun pai-dsw get-instance ...
```

#### ❌ INCORRECT
```bash
aliyun paidsw CreateInstance ...   # Traditional API format
aliyun pai_dsw create-instance ... # Underscore in product name
aliyun PAI-DSW create-instance ... # Uppercase
```

---

## 3. Command Format (kebab-case)

#### ✅ CORRECT
```bash
aliyun pai-dsw create-instance
aliyun pai-dsw update-instance
aliyun pai-dsw get-instance
aliyun pai-dsw list-instances
aliyun pai-dsw list-ecs-specs
aliyun pai-dsw start-instance
aliyun pai-dsw stop-instance
```

#### ❌ INCORRECT
```bash
aliyun pai-dsw CreateInstance     # PascalCase (traditional API)
aliyun pai-dsw createinstance     # No separator
aliyun pai-dsw create_instance    # Underscore separator
```

---

## 4. Parameter Names

### Check Instance Existence (before CreateInstance)

#### ✅ CORRECT
```bash
# Step 1: Query by instance name
aliyun pai-dsw list-instances \
  --instance-name my_instance \
  --region cn-shanghai \
  --resource-id ALL \
  --user-agent AlibabaCloud-Agent-Skills

# Step 2: Verify exact name match in response
# Parse the JSON response and check EACH instance:
#
# Response example:
# {
#   "TotalCount": 3,
#   "Instances": [
#     {"InstanceName": "my_instance_v2", "InstanceId": "dsw-xxx"},
#     {"InstanceName": "my_instance_backup", "InstanceId": "dsw-yyy"},
#     {"InstanceName": "my_instance", "InstanceId": "dsw-zzz"}  ← EXACT MATCH!
#   ]
# }
#
# Algorithm:
# found = false
# for instance in Instances:
#     if instance.InstanceName == "my_instance":  # EXACT string equality
#         found = true
#         break
#
# if found:
#     # Name already exists - DO NOT create, return existing instance
# else:
#     # Name is available - proceed to create
```

#### ❌ INCORRECT
```bash
# Wrong pattern 1: Relying solely on TotalCount > 0
if TotalCount > 0:
    print("Name already exists")  # May miss partial matches

# Wrong pattern 2: Assuming no exact match without checking
# Response: TotalCount=2, Instances=[{"InstanceName":"my_instance_v2"}, {"InstanceName":"my_instance"}]
# Agent incorrectly concludes: "ExactNameMatch: false"
# This is WRONG - must verify by iterating through ALL instances

# Wrong pattern 3: Not checking case-sensitivity
if instanceName.lower() == targetName.lower():  # WRONG - case sensitive comparison
    # DSW instance names are case-sensitive
```

> **[CRITICAL] Common failure pattern**:
>
> The `--instance-name` filter returns **all instances whose name contains the query string**.
>
> Example failure scenario:
> - Query: `--instance-name llm_train_001`
> - Response: `TotalCount: 1`, `Instances: [{InstanceName: "llm_train_001"}]`
> - Agent incorrectly reports: "ExactNameMatch: false, proceeding with creation"
> - Result: CreateInstance returns HTTP 400 "instance name already exists"
>
> **Root cause**: Agent did not properly compare `instance.InstanceName === "llm_train_001"`.

### CreateInstance

#### ✅ CORRECT
```bash
# With image URL (recommended)
aliyun pai-dsw create-instance \
  --workspace-id 12345 \
  --instance-name my_instance \
  --ecs-spec ecs.g6.xlarge \
  --image-url dsw-registry-vpc.cn-shanghai.cr.aliyuncs.com/pai/modelscope:1.34.0-pytorch2.3.1-cpu-py311-ubuntu22.04 \
  --region cn-shanghai \
  --accessibility PRIVATE \
  --user-agent AlibabaCloud-Agent-Skills

# With image ID
aliyun pai-dsw create-instance \
  --workspace-id 12345 \
  --instance-name my_instance \
  --ecs-spec ecs.g6.xlarge \
  --image-id image-xxxxx \
  --region cn-shanghai \
  --accessibility PRIVATE \
  --user-agent AlibabaCloud-Agent-Skills
```

> **[IMPORTANT] Non-blocking creation**: After `create-instance` returns `InstanceId`, immediately return the ID and status to the user. Do NOT block waiting for `Running` status. Instance startup takes 2–5 minutes; the agent should remain responsive.

#### ❌ INCORRECT
```bash
# Blocking after creation (WRONG approach)
aliyun pai-dsw create-instance ...
# Then polling until Running - WRONG: Agent blocks and cannot respond to other requests

# Missing --region parameter
aliyun pai-dsw create-instance \
  --workspace-id 12345 \
  --instance-name my_instance \
  --ecs-spec ecs.g6.xlarge \
  --image-url <image-url>
  # WRONG: --region must be specified and confirmed with user

# Cannot specify both image-id and image-url
aliyun pai-dsw create-instance \
  --image-id image-xxxxx \
  --image-url dsw-registry-vpc.cn-shanghai.cr.aliyuncs.com/pai/xxx

# PascalCase parameter names
aliyun pai-dsw create-instance \
  --WorkspaceId 12345 \
  --InstanceName my_instance \
  --EcsSpec ecs.g6.xlarge
```

> **[IMPORTANT] Region is required**: The `--region` parameter must be explicitly specified and confirmed with the user. Do NOT rely on CLI default region.

### UpdateInstance

#### ✅ CORRECT
```bash
# Step 1: Check current instance configuration
aliyun pai-dsw get-instance \
  --instance-id dsw-730xxxxxxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
# Response: {"EcsSpec": "ecs.g7.xlarge", ...}

# Step 2: Compare with target and decide
# - If current.EcsSpec === targetSpec: Already at target, skip update
# - If current.EcsSpec !== targetSpec: Proceed with update

# Step 3a: Skip update (already at target)
# Return current instance info to user

# Step 3b: Update EcsSpec with auto-start (if change needed)
aliyun pai-dsw update-instance \
  --instance-id dsw-730xxxxxxxxxx \
  --ecs-spec ecs.g6.xlarge \
  --start-instance true \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Updating to the same spec (no actual change)
aliyun pai-dsw update-instance \
  --instance-id dsw-730xxxxxxxxxx \
  --ecs-spec ecs.g7.xlarge \  # Same as current, API returns 400
  --user-agent AlibabaCloud-Agent-Skills

aliyun pai-dsw update-instance \
  --id dsw-730xxxxxxxxxx \      # Wrong parameter name
  --name new_name               # Wrong parameter name
```

> **[IMPORTANT] Check before update**: Calling `update-instance` with the same value as current configuration will cause API error (HTTP 400). Always compare current value with target value first and skip update if already at target.

### StopInstance

#### ✅ CORRECT
```bash
aliyun pai-dsw stop-instance \
  --instance-id dsw-730xxxxxxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun pai-dsw stop-instance \
  --id dsw-730xxxxxxxxxx    # Wrong parameter name
```

> **Note**: To save the environment as a custom image, use the PAI Console. See [Create a DSW Instance Image](https://help.aliyun.com/zh/pai/user-guide/create-a-dsw-instance-image).

### StartInstance

#### ✅ CORRECT
```bash
aliyun pai-dsw start-instance \
  --instance-id dsw-730xxxxxxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

> **Prerequisite**: Instance must be in `Stopped` or `Failed` state.

#### ❌ INCORRECT
```bash
aliyun pai-dsw start-instance \
  --id dsw-730xxxxxxxxxx    # Wrong parameter name
```

### ListInstances

#### ✅ CORRECT
```bash
# List running instances with sorting by creation time (newest first)
aliyun pai-dsw list-instances \
  --workspace-id 512607 \
  --status Running \
  --page-number 1 \
  --page-size 20 \
  --sort-by GmtCreateTime \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Using only --sort-by without --order (causes API validation error)
aliyun pai-dsw list-instances \
  --status Running \
  --sort-by GmtCreateTime \
  --user-agent AlibabaCloud-Agent-Skills

# Using only --order without --sort-by (causes API validation error)
aliyun pai-dsw list-instances \
  --status Running \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills
```

> **[IMPORTANT] Sorting parameters**: `--sort-by` and `--order` **must be used together**. Using only one will cause API validation error.

### ListEcsSpecs

> **[MUST] Choose accelerator type based on user requirements**:
> - **Default recommendation**: GPU for 大模型训练/深度学习, CPU for 数据分析/轻量任务
> - **Match image type** (strong indicator): GPU image URL (contains `-gpu-` or `cu`) → GPU specs
> - **Always confirm with user** if the use case is ambiguous

#### ✅ CORRECT
```bash
# User specified GPU image URL → query GPU specs
aliyun pai-dsw list-ecs-specs \
  --accelerator-type GPU \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills

# User specified CPU image URL → query CPU specs
aliyun pai-dsw list-ecs-specs \
  --accelerator-type CPU \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# User specified GPU image but queried CPU specs
aliyun pai-dsw list-ecs-specs \
  --accelerator-type CPU \
  --region cn-hangzhou
  # WRONG: User specified GPU image URL (contains -gpu-), must use GPU

# Missing --region parameter
aliyun pai-dsw list-ecs-specs \
  --accelerator-type CPU
  # WRONG: --region must be specified and confirmed with user

# Missing required --accelerator-type
aliyun pai-dsw list-ecs-specs --user-agent AlibabaCloud-Agent-Skills

# PascalCase parameter
aliyun pai-dsw list-ecs-specs --AcceleratorType CPU

# Lowercase enum value
aliyun pai-dsw list-ecs-specs --accelerator-type cpu

# Traditional API format
aliyun pai-dsw ListEcsSpecs --accelerator-type CPU
```

### Enum Constraints

| Parameter | Valid Values |
|---|---|
| `--status` | `Creating`, `Running`, `Stopped`, `Stopping`, `Starting`, `Failed`, `Updating`, `Queuing`, `EnvPreparing`, `Saving`, `Saved`, `SaveFailed`, `Deleting`, `Recovering`, `ResourceAllocating` |
| `--accessibility` | `PUBLIC`, `PRIVATE` |
| `--accelerator-type` | `CPU`, `GPU` |
| `--payment-type` | `PayAsYouGo`, `Subscription` |
| `--sort-by` | `Priority`, `GmtCreateTime`, `GmtModifiedTime` |
| `--order` | `ASC`, `DESC` |

---

## 5. User-Agent Flag

#### ✅ CORRECT
```bash
aliyun pai-dsw get-instance \
  --instance-id dsw-730xxxxxxxxxx \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun pai-dsw get-instance --instance-id dsw-730xxxxxxxxxx
# Missing --user-agent
```

---

## 6. Parameter Value Formats

### InstanceId

| ✅ Valid | ❌ Invalid |
|---|---|
| `dsw-730xxxxxxxxxx` | `730xxxxxxxxxx` (missing prefix) |
| | `instance-730xxx` (wrong prefix) |

### InstanceName

| ✅ Valid | ❌ Invalid |
|---|---|
| `my_instance_01` (letters, digits, underscores; <=27 chars) | `my-instance-01` (hyphens not allowed) |
| `training_data` | `my instance` (spaces not allowed) |
| | `very_long_instance_name_over_27_chars` (exceeds limit) |

### Accessibility

| ✅ Valid | ❌ Invalid |
|---|---|
| `PUBLIC` | `public` (must be uppercase) |
| `PRIVATE` | `Private` (must be uppercase) |

### JSON Parameters (UserVpc)

#### ✅ CORRECT
```bash
--user-vpc '{"VpcId":"vpc-xxx","VSwitchId":"vsw-xxx","SecurityGroupId":"sg-xxx"}'
```

#### ❌ INCORRECT
```bash
--user-vpc vpc-xxx    # Must be a JSON object
--user-vpc '{"vpc_id":"vpc-xxx","vswitch_id":"vsw-xxx"}'  # Wrong: snake_case field names
```

### Dataset Mount Parameters

> **[MUST] User confirmation required**: The `--datasets` parameter requires explicit user confirmation. Do NOT assume or auto-generate dataset configurations.

#### ✅ CORRECT
```bash
# Use CLI list format (NOT JSON array)
--datasets DatasetId=d-xxx MountPath=/mnt/data MountAccess=RO
```

#### ❌ INCORRECT
```bash
--datasets '[{"dataset_id":"d-xxx","mount_path":"/mnt/data","mount_access":"RO"}]'  # Wrong: JSON format
--datasets DatasetId=d-xxx MountPath=/mnt/data MountAccess=ro  # Wrong: MountAccess must be uppercase
--datasets d-xxx      # Wrong: Must use key=value format
```

---

## 7. Non-Blocking Workflow (IMPORTANT)

> **Problem**: DSW instance creation takes 2–5 minutes. If the agent blocks waiting for `Running` status, it cannot respond to other user requests during this time.
>
> **Solution**: Return immediately after creation, let the user check status later.

### ✅ CORRECT: Non-blocking Creation Flow

```
User: "Create a DSW instance..."

Agent: 1. Call list-workspaces (if needed)
       2. Call list-ecs-specs to show available specs
       3. Call create-instance
       4. Immediately return:
          "Instance created!
           InstanceId: dsw-xxx
           Current Status: Creating

           Instance startup typically takes 2–5 minutes. Run this command to check status:
           aliyun pai-dsw get-instance --instance-id dsw-xxx --user-agent AlibabaCloud-Agent-Skills"
```

### ❌ INCORRECT: Blocking Flow

```
User: "Create a DSW instance..."

Agent: 1. Call create-instance
       2. Start polling get-instance every 10 seconds...
       3. [BLOCKED - cannot respond to other requests]
       4. ... waiting ...
       5. ... waiting ...
       6. Finally return after 3 minutes
          "Instance is Running, access URL: ..."
```

### When to Poll

| User Request | Agent Behavior |
|--------------|----------------|
| "Create instance" | Return immediately after creation |
| "Create instance and wait for it to be ready" | Poll until Running (user explicitly asked) |
| "Check instance status" | Return current status immediately |
| "Wait for instance to be Running" | Poll until Running (user explicitly asked) |

---

## Manual Verification Only

| Item | Reason | Method |
|---|---|---|
| `aliyun pai-dsw --help` output | CLI not installed locally | Run after installation |
| CreateInstance RAM Action | Undocumented | Verify in RAM console |
| CLI parameter casing | Inferred from metadata | Confirm via `--help` |
| Instance URL reachability | Browser required | Open `InstanceUrl` in browser |
