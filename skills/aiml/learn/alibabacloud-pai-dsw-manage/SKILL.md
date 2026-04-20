---
name: alibabacloud-pai-dsw-manage
description: |
  Manage the full lifecycle of Alibaba Cloud PAI DSW (Data Science Workshop) instances — create, update, query, list, start, stop, and look up ECS specs.
  Triggers: PAI DSW, DSW instance, create instance, start instance, stop instance, update instance, query instance, instance list, ECS spec, CreateInstance, UpdateInstance, GetInstance, ListInstances, StartInstance, StopInstance, ListEcsSpecs
---

# PAI DSW Instance Management

Manage the full lifecycle of Alibaba Cloud PAI DSW (Data Science Workshop) instances — from provisioning through configuration changes, status monitoring, and start/stop operations. Also supports querying available ECS compute specs.

**Architecture**: `PAI Workspace + DSW Instance + ECS Spec + Image + VPC + Dataset`

**API Version**: `pai-dsw/2022-01-01`

---

## Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
>
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to update,
> or see [`references/cli-installation-guide.md`](references/cli-installation-guide.md) for installation instructions.

> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

```bash
# macOS (recommended)
brew install aliyun-cli

# Verify version (>= 3.3.3)
aliyun version

# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true

# Update existing plugins
aliyun plugin update

# Install pai-dsw plugin
aliyun plugin install --names pai-dsw
```

**[MUST] CLI User-Agent** — Every `aliyun` CLI command invocation must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage`

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in a terminal or environment variables in a shell profile)
> 3. Return and retry after `aliyun configure list` shows a valid profile

---

## RAM Permissions

See [`references/ram-policies.md`](references/ram-policies.md) for the complete permission list and minimum-privilege policy.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this skill
> 2. Use the `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call, ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks, passwords, domain names, resource specifications, etc.) MUST be confirmed with the user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required | Description | Default |
|---|---|---|---|
| `WorkspaceId` | Required | PAI workspace ID | None — user must provide |
| `InstanceName` | Required | Instance name (letters, digits, underscores only; max 27 chars) | None — user must provide |
| `EcsSpec` | Required (post-paid) | ECS compute spec, e.g., `ecs.c6.large`. Query via `list-ecs-specs` | None |
| `ImageId` | Mutually exclusive with `ImageUrl` | Image ID from PAI console | None |
| `ImageUrl` | Mutually exclusive with `ImageId` | Container image URL. See [`references/common-images.md`](references/common-images.md) for common official images | None |
| `RegionId` | Required | Region, e.g., `cn-hangzhou`, `cn-shanghai` | None — user must confirm |
| `Accessibility` | Optional | Visibility scope: `PUBLIC` (all workspace users) or `PRIVATE` | `PRIVATE` |
| `InstanceId` | Required (update/get/start/stop) | Instance ID (`dsw-xxxxx` format) | None |
| `VpcId` | Optional | VPC ID for private network access | None |
| `VSwitchId` | Optional | VSwitch ID within the VPC | None |
| `SecurityGroupId` | Optional | Security group ID | None |
| `AcceleratorType` | Required (spec query) | Accelerator type: `CPU` or `GPU` | None — user must confirm |
| `Datasets` | Optional | Dataset mounts in CLI list format: `DatasetId=<> MountPath=<> MountAccess=RO|RW` | None — **user must confirm, no default** |
| `--read-timeout` | Optional | CLI read timeout in seconds (for long-running operations) | `10` |
| `--connect-timeout` | Optional | CLI connection timeout in seconds | `10` |

> **How to get WorkspaceId**: If the user doesn't know their workspace ID, run:
> ```bash
> aliyun aiworkspace list-workspaces --region <region> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
> ```
> This returns all workspaces the user has access to. Select the appropriate one based on `WorkspaceName` or ask the user to confirm.
>
> Reference: [Create and Manage Workspaces](https://help.aliyun.com/zh/pai/user-guide/create-and-manage-workspaces)

---

## Core Workflow

> Full command syntax and parameter details: [`references/related-commands.md`](references/related-commands.md).

### 1. Query Available ECS Specs

Run `aliyun pai-dsw list-ecs-specs --accelerator-type <CPU|GPU> --region <region>` to list available compute specs.

> **[MUST] Region confirmation**: The `--region` parameter is required. Spec availability varies by region — always confirm the region with the user before querying.

> **[MUST] Determine accelerator type correctly**:
> - **User mentions a spec name** (e.g., `ecs.hfc6.10xlarge`): Query **BOTH** CPU and GPU types, then match `InstanceType` in results. Use the returned `AcceleratorType` field to confirm the classification.
> - **User specifies image type**: GPU image URL (contains `-gpu-` or `cu`) → query GPU specs; CPU image URL → query CPU specs.
> - **User describes use case only**: GPU for 大模型训练/深度学习, CPU for 数据分析/轻量任务. **Always confirm with user** if ambiguous.
> - **[IMPORTANT] Do NOT guess from spec name prefix** — the naming convention is unreliable. Always verify via API response.

> **[MUST] Choose accelerator type based on user requirements**:
> - **Default recommendation**: GPU for 大模型训练/深度学习, CPU for 数据分析/轻量任务
> - **Match image type** (strong indicator): If user specifies a GPU image URL (contains `-gpu-` or `cu`), query GPU specs. If CPU image, query CPU specs.
> - **Spec name requires verification**: If user mentions a spec name, query both types and find the match in results
> - **Always confirm with user** before querying if the use case is ambiguous and no spec name is provided

**Key response fields**:
- `InstanceType`: Spec name (e.g., `ecs.hfc6.10xlarge`)
- `AcceleratorType`: `CPU` or `GPU` — the actual classification from API
- `IsAvailable`: **PRIMARY indicator** — `true` means the spec is available for pay-as-you-go/subscription
- `SpotStockStatus`: **SECONDARY indicator** — only for spot instances: `WithStock` (available) or `NoStock` (unavailable)
- `CPU` / `Memory` / `GPU` / `GPUType`: Hardware details
- `Price`: Hourly price in CNY

> **[MUST] Availability check logic**:
> - For **pay-as-you-go/subscription**: Check `IsAvailable == true`
> - For **spot instances**: Check `IsAvailable == true` AND `SpotStockStatus == "WithStock"`
> - **DO NOT** use `SpotStockStatus` alone to judge availability — many specs have `IsAvailable: true` but `SpotStockStatus: "NoStock"`
> - **Example**: `ecs.hfc6.10xlarge` with `IsAvailable: true, SpotStockStatus: "NoStock"` → **Available for pay-as-you-go**

### 2. Create Instance (check-then-act)

> **[MUST] Idempotency guarantee**: The CreateInstance API does not support ClientToken, so idempotency is ensured via a check-then-act pattern. Before creating, you **must** call `list-instances --instance-name <name>` to check if the name already exists.

**Step 2.1 — Check existence**

```bash
aliyun pai-dsw list-instances \
  --instance-name <name> \
  --region <region> \
  --resource-id ALL \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Decision logic**:
- `TotalCount == 0` → Name is available, proceed to Step 2.2 to create
- `TotalCount >= 1` → **[MUST] Verify exact name match**:
  1. Iterate through the returned `Instances` array
  2. For each instance, compare its `InstanceName` field with the target name **character by character** (case-sensitive, exact string match)
  3. **Exact match found** (`instance.InstanceName === targetName`) → Name already exists:
     - Extract the `InstanceId` from the matching instance
     - Call `get-instance --instance-id <id>` to get full details
     - Compare key parameters (`EcsSpec`, `ImageUrl`, `Accessibility`, etc.)
     - **Match** → Return the existing `InstanceId`, **do not recreate**
     - **Mismatch** → Ask user to choose a different name
  4. **No exact match found** (no instance has `InstanceName === targetName`) → Name is available, proceed to Step 2.2 to create

> **[WARNING] Critical: Exact name match required**
>
> The `--instance-name` filter may return **partial matches**. For example:
> - Query: `--instance-name llm_train_001`
> - Response may include: `llm_train_001`, `llm_train_001_v2`, `llm_train_001_backup`
>
> **You MUST verify exact match** by checking:
> ```
> for instance in response.Instances:
>     if instance.InstanceName == targetName:  # EXACT string equality
>         # Name already exists - DO NOT create
> ```
>
> **Do NOT** assume name is available just because `TotalCount > 0` but you "think" no exact match. If `TotalCount >= 1`, **carefully check each instance's InstanceName field**.

**Step 2.2 — Provision**

Run `aliyun pai-dsw create-instance` with required args: `--workspace-id`, `--instance-name`, `--ecs-spec`, `--region`, and either `--image-url` or `--image-id`.

> **[MUST] Region confirmation**: The `--region` parameter is required and must be confirmed with the user. Do NOT use CLI default region without explicit user approval. Spec availability and pricing vary by region.

> **[MUST] Match EcsSpec with image type**:
> - GPU image URL (contains `-gpu-` or `cu`) → Must select a GPU spec (e.g., `ecs.gn6v-c4g1.xlarge`)
> - CPU image URL (contains `-cpu-`) → Must select a CPU spec (e.g., `ecs.c6.large`)
> - The spec type MUST match the image type, otherwise the instance will fail to start
> - Use case (大模型训练/数据分析) is only a recommendation, image type is the definitive indicator

> **Dataset mounting** (optional): If the user specifies a dataset to mount, use the `--datasets` parameter in CLI list format:
> ```bash
> --datasets DatasetId=<dataset-id> MountPath=<mount-path> MountAccess=RO
> ```
> **[MUST]** Dataset parameters require **explicit user confirmation** — do NOT assume or auto-generate dataset configurations.
>
> Official images: [`references/common-images.md`](references/common-images.md).
>
> Advanced usage (VPC, datasets): [`references/related-commands.md`](references/related-commands.md).

**Response**: `{"InstanceId": "dsw-xxxxx", ...}`

> **[IMPORTANT] Return immediately after creation**: After `create-instance` returns `InstanceId`, **do NOT block waiting for `Running` status**. Instead:
> 1. Return the `InstanceId` and current status (`Creating`) to the user immediately
> 2. Provide the user with a command to check status later:
>    ```bash
>    aliyun pai-dsw get-instance --instance-id <instance-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
>    ```
> 3. Inform the user that instance startup typically takes 2–5 minutes
>
> **Why this matters**: Blocking polling prevents the agent from responding to other user requests. DSW instance creation is a long-running operation; the agent should return control to the user promptly.

### 3. List Instances

Run `aliyun pai-dsw list-instances`. Filter by `--workspace-id` or `--status`; paginate with `--page-number` / `--page-size`.

### 4. Get Instance Details

Run `aliyun pai-dsw get-instance --instance-id <id>` to check instance status and details.

> **When to poll**: Only poll when the user **explicitly asks** to wait for a status change (e.g., "wait until it's running"). Otherwise, return the current status immediately.
>
> **Timeout limits**: Maximum 60 polls (30 minutes total). If exceeded, stop and prompt user to check manually.
>
> **Polling interval**: 10–30 seconds between calls.
>
> **CLI timeout**: For long-running operations, increase read timeout:
> ```bash
> aliyun pai-dsw get-instance --instance-id <id> --read-timeout 30 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
> ```
>
> Once `Status == "Running"`, access the instance via `InstanceUrl`.
>
> For complete status transitions, see Instance Status Values in [`references/related-commands.md`](references/related-commands.md#instance-status-values).

### 5. Stop Instance

Run `aliyun pai-dsw stop-instance --instance-id <id>`.

> **Status transition**: `Running` → `Stopping` → `Stopped`
>
> **Save environment image**: To save the environment as a custom image before stopping, use the PAI Console. See [Create a DSW Instance Image](https://help.aliyun.com/zh/pai/user-guide/create-a-dsw-instance-image) for instructions.

### 6. Update Instance

Run `aliyun pai-dsw update-instance --instance-id <id>` to modify `--instance-name`, `--ecs-spec`, `--image-id`, `--accessibility`, `--datasets`, etc.

> **[MUST] Before updating**:
> 1. Call `get-instance` to check current status and configuration
> 2. **Check if update is needed**:
>    - For `--ecs-spec`: Compare current `EcsSpec` with target spec. If already equal, **skip update** and inform user
>    - For `--image-id`/`--image-url`: Compare current `ImageId`/`ImageUrl` with target
>    - For `--instance-name`: Compare current `InstanceName` with target
> 3. If already at target configuration, return current instance info — **do not call update-instance**
> 4. If update is needed, use `--start-instance true` to auto-start after update
>
> **[IMPORTANT]** Always update the **specified instance** by its `InstanceId`. Do NOT substitute with another instance that already has the target spec — the user's request is to upgrade the specific instance, not to find an alternative.

### 7. Start Instance

Run `aliyun pai-dsw start-instance --instance-id <id>`, then poll (Step 4) until `Running`.

> **Prerequisite**: Instance must be in `Stopped` or `Failed` state. Call `get-instance` to confirm before starting.

---

## Success Verification

Full verification steps: [`references/verification-method.md`](references/verification-method.md).

Quick check: `get-instance` should return `Status == "Running"` with a non-empty `InstanceUrl`.

---

## Cleanup

> This skill does **not** expose instance deletion (irreversible operation — use the console).
>
> To stop incurring charges, stop the instance via Step 5 (`stop-instance`).

---

## Best Practices

1. **Always run check-then-act before creation** — use `list-instances --instance-name <name>` to avoid duplicate-instance errors.
2. **Prefer `PRIVATE` visibility** — prevents accidental operations by other workspace users.
3. **Check instance status before update** — call `get-instance` first; some parameters require Stopped state, others can be updated while Running.
4. **Use `--resource-id ALL` with `list-instances`** — the default only returns post-paid instances.
5. **Observe polling timeout limits** — see Step 4 for timeout and interval guidance.
6. **Verify spec availability before provisioning** — run `list-ecs-specs` to confirm the spec is available in the target region.
7. **Tag instances with Labels** — simplifies batch queries and lifecycle management.

---

## References

| Document | Path |
|---|---|
| CLI Installation | [`references/cli-installation-guide.md`](references/cli-installation-guide.md) |
| RAM Policies | [`references/ram-policies.md`](references/ram-policies.md) |
| CLI Commands | [`references/related-commands.md`](references/related-commands.md) |
| Verification | [`references/verification-method.md`](references/verification-method.md) |
| Acceptance Criteria | [`references/acceptance-criteria.md`](references/acceptance-criteria.md) |
| Common Images | [`references/common-images.md`](references/common-images.md) |
| PAI DSW API Overview | [help.aliyun.com](https://help.aliyun.com/zh/pai/developer-reference/api-pai-dsw-2022-01-01-overview) |
