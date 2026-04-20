# Related CLI Commands — alibabacloud-pai-dsw-manage

All PAI DSW instance management commands in plugin mode (kebab-case).

> Every command must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage`

## Workspace Commands

| Operation | Command | Description |
|---|---|---|
| List workspaces | `aliyun aiworkspace list-workspaces` | Get all workspaces the user has access to |

```bash
# List all workspaces in a region
aliyun aiworkspace list-workspaces \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# With verbose output (shows full details)
aliyun aiworkspace list-workspaces \
  --region <region> \
  --verbose true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

> See SKILL.md "Parameter Confirmation" for WorkspaceId requirements.

---

## Instance Lifecycle Commands

| Operation | Command | Description |
|---|---|---|
| Check existence | `aliyun pai-dsw list-instances --instance-name <name>` | Check if instance name already exists |
| Create | `aliyun pai-dsw create-instance` | Provision a new DSW instance |
| Update | `aliyun pai-dsw update-instance --instance-id <id>` | Modify instance attributes |
| Get | `aliyun pai-dsw get-instance --instance-id <id>` | Retrieve single instance details |
| List | `aliyun pai-dsw list-instances` | List instances with filters |
| Specs | `aliyun pai-dsw list-ecs-specs --accelerator-type <type>` | Available ECS compute specs (CPU/GPU) |
| Start | `aliyun pai-dsw start-instance --instance-id <id>` | Start a stopped instance |
| Stop | `aliyun pai-dsw stop-instance --instance-id <id>` | Stop a running instance |

---

## Command Examples

### Check Instance Existence

> Use `list-instances --instance-name <name>` to check if an instance exists.
>
> **[WARNING]** The `--instance-name` filter may return partial matches. See SKILL.md "Exact name match required" for details.

```bash
aliyun pai-dsw list-instances \
  --instance-name <instance-name> \
  --region <region> \
  --resource-id ALL \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

---

### CreateInstance

```bash
# With image URL (recommended — official preset images)
aliyun pai-dsw create-instance \
  --workspace-id <workspace-id> \
  --instance-name <instance-name> \
  --ecs-spec <ecs-spec> \
  --image-url <image-url> \
  --region <region> \
  --accessibility PRIVATE \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# With image ID
aliyun pai-dsw create-instance \
  --workspace-id <workspace-id> \
  --instance-name <instance-name> \
  --ecs-spec <ecs-spec> \
  --image-id <image-id> \
  --region <region> \
  --accessibility PRIVATE \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# With VPC configuration
aliyun pai-dsw create-instance \
  --workspace-id <workspace-id> \
  --instance-name <instance-name> \
  --ecs-spec <ecs-spec> \
  --image-url <image-url> \
  --region <region> \
  --user-vpc '{"VpcId":"<vpc-id>","VSwitchId":"<vswitch-id>","SecurityGroupId":"<sg-id>","ExtendedCIDRs":["<cidr>"]}' \
  --accessibility PRIVATE \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# With dataset mounts
aliyun pai-dsw create-instance \
  --workspace-id <workspace-id> \
  --instance-name <instance-name> \
  --ecs-spec <ecs-spec> \
  --image-url <image-url> \
  --region <region> \
  --datasets DatasetId=<dataset-id> MountPath=/mnt/data MountAccess=RO \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

> See SKILL.md for parameter requirements (Region, Dataset confirmation, etc.).
>
> **Dataset mount parameters** (use CLI list format, NOT JSON):
> - `DatasetId` — Dataset ID (required)
> - `MountPath` — Mount path in container (required)
> - `MountAccess` — Access mode: `RO` or `RW`
> - `DatasetVersion`, `Dynamic`, `OptionType`, `Options`, `Uri` — Optional

---

### UpdateInstance

> See SKILL.md Step 6 for pre-update check requirements (compare current vs target configuration).

```bash
# Rename instance
aliyun pai-dsw update-instance \
  --instance-id <instance-id> \
  --instance-name <new-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# Change image
aliyun pai-dsw update-instance \
  --instance-id <instance-id> \
  --image-id <new-image-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# Change compute spec and auto-start after update
aliyun pai-dsw update-instance \
  --instance-id <instance-id> \
  --ecs-spec <new-ecs-spec> \
  --start-instance true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

---

### GetInstance

```bash
aliyun pai-dsw get-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

---

### ListInstances

```bash
# All instances
aliyun pai-dsw list-instances \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# Filter by status
aliyun pai-dsw list-instances \
  --status Running \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# By workspace, paginated with sorting
# Note: --sort-by and --order must be used together
aliyun pai-dsw list-instances \
  --workspace-id <workspace-id> \
  --status Running \
  --page-number 1 \
  --page-size 20 \
  --sort-by GmtCreateTime \
  --order DESC \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# All workspaces, all billing types
aliyun pai-dsw list-instances \
  --workspace-id ALL \
  --resource-id ALL \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Sorting parameters**:
- `--sort-by`: Sort field — `Priority`, `GmtCreateTime`, `GmtModifiedTime`
- `--order`: Sort direction — `ASC` or `DESC`
- **Note**: `--sort-by` and `--order` must be used together. Using only one will cause API validation error.

---

### StartInstance

> **Prerequisite**: Instance must be in `Stopped` or `Failed` state.

```bash
aliyun pai-dsw start-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

---

### StopInstance

```bash
aliyun pai-dsw stop-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

> To save the environment as a custom image, see SKILL.md Step 5.

---

## Helper Commands

### ListEcsSpecs

> **[MUST] Choose accelerator type based on user requirements**:
> - **Default recommendation**: GPU for 大模型训练/深度学习, CPU for 数据分析/轻量任务
> - **Match image type** (strong indicator): GPU image URL (contains `-gpu-` or `cu`) → GPU specs; CPU image → CPU specs
> - **Always confirm with user** if the use case is ambiguous

```bash
# CPU specs in a specific region
aliyun pai-dsw list-ecs-specs \
  --accelerator-type CPU \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# GPU specs in a specific region
aliyun pai-dsw list-ecs-specs \
  --accelerator-type GPU \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# Paginated with sort
aliyun pai-dsw list-ecs-specs \
  --accelerator-type CPU \
  --region <region> \
  --page-number 1 \
  --page-size 20 \
  --order ASC \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

# Filter by resource type
aliyun pai-dsw list-ecs-specs \
  --accelerator-type GPU \
  --region <region> \
  --resource-type ECS \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

> See SKILL.md Step 1 for key response fields (`InstanceType`, `IsAvailable`, etc.).

---

### Help & Plugin Management

```bash
# List all pai-dsw subcommands
aliyun pai-dsw --help

# Command-specific help
aliyun pai-dsw create-instance --help
aliyun pai-dsw update-instance --help
aliyun pai-dsw get-instance --help
aliyun pai-dsw list-instances --help
aliyun pai-dsw start-instance --help
aliyun pai-dsw stop-instance --help

# Install pai-dsw plugin (if missing)
aliyun plugin install --names pai-dsw
```

---

## Instance Status Values

| Status | Description |
|---|---|
| `Creating` | Instance is being provisioned |
| `ResourceAllocating` | Computing resources are being allocated |
| `Queuing` | Waiting in provisioning queue |
| `Starting` | Instance is booting up |
| `EnvPreparing` | Runtime environment is being set up |
| `Running` | Instance is active and accessible |
| `Stopping` | Instance is shutting down |
| `Stopped` | Instance is fully stopped |
| `Updating` | Instance configuration is being modified |
| `Saving` | Environment image is being saved |
| `Saved` | Image saved successfully |
| `SaveFailed` | Image save failed |
| `Deleting` | Instance is being deleted |
| `Failed` | Operation failed |
| `Recovering` | Instance is being restored |
