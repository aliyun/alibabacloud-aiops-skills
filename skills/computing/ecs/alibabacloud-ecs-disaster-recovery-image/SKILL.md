---
name: alibabacloud-ecs-disaster-recovery-image
description: |
  阿里云 ECS 跨可用区灾备恢复技能。从现有 ECS 实例创建系统镜像，并在不同可用区部署新实例。
  当用户提到以下场景时使用：可用区故障恢复、跨可用区备份、跨可用区实例克隆、ECS 灾备、
  用镜像在其他可用区创建实例、"帮我做个镜像然后换个可用区创建实例"等。
  也适用于：灾备实例、镜像备份、换个可用区创建实例、可用区容灾、
  制作镜像、跨可用区创建、从镜像创建实例。
  注意：本技能是"备份"而非"迁移"，不会释放或影响原始实例的资源。
---

# ECS Cross-AZ Disaster Recovery (Whole-Instance Image)

## 1. Scenario

This Skill guides the user through creating a **whole-instance image** (system disk + all data disks) from an existing ECS instance, and deploying a new instance in **a different availability zone within the same region** using that image, to achieve AZ-level disaster recovery. The original instance and all its resources remain **completely untouched** -- this is a **backup**, not a migration.

**Architecture**: ECS Source Instance -> ECS Custom Image (full disk mappings) -> ECS New Instance (target zone) + VSwitch (existing or newly created in source VPC)

**Key characteristics**:
- No downtime: `create-image` supports Running instances
- Whole-instance image: automatically includes mappings for the system disk and all data disks
- Single-shot creation: use `run-instances --data-disk Device=...` to **override** disk Category/PL on the image during instance creation, avoiding separate disk attachment
- All parameters explicit: network / billing / bandwidth / disk PL are read from the source instance and reused

## 2. Installation

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> 1. Run `aliyun version` to check whether the CLI is installed and verify the version
> 2. If not installed: notify the user, and after user confirmation run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash`, or refer to [references/cli-installation-guide.md](references/cli-installation-guide.md)
> 3. If installed but version < 3.3.3: report the current version and the minimum requirement, then upgrade after user confirmation
> 4. If installed and version >= 3.3.3: proceed to the next step

> **[MUST] Pre-check: Aliyun CLI plugin update**
> ```bash
> aliyun configure set --auto-plugin-install true
> aliyun plugin update
> ```

## 3. Environment Variables

This Skill does not require any environment variables; all parameters (RegionId, etc.) are passed explicitly on the command line. **Do NOT** use `export ALIBABA_CLOUD_USER_AGENT=...`, because environment variables do not survive across separate bash invocations in multi-agent clients.

## 4. Authentication

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
> Inspect the output for a valid profile (AK / STS / OAuth identity).
>
> **If no valid profile exists, STOP here:**
> 1. Obtain credentials from the [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in a terminal or environment variables in the shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## 5. RAM Policy

RAM Actions used by this Skill (detailed resource scoping and policy JSON are in [references/ram-policies.md](references/ram-policies.md)):

| Action | Purpose |
|--------|---------|
| `ecs:DescribeInstances` | Query the source instance / verify the new instance |
| `ecs:DescribeDisks` | Query disks on the source / new instance |
| `ecs:CreateImage` | Create a whole-instance image from the source instance |
| `ecs:DescribeImages` | Monitor image creation progress |
| `ecs:DescribeAvailableResource` | Check stock in the target availability zone |
| `ecs:DescribeVSwitches` | List VSwitches under the VPC |
| `ecs:RunInstances` | Create the new instance in the target availability zone |
| `vpc:CreateVSwitch` | Create a VSwitch when none exists in the target zone |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read [references/ram-policies.md](references/ram-policies.md) to obtain the full list of permissions required by this Skill
> 2. Use the `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## 6. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** -- Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `InstanceId` | Required | Source ECS instance ID | N/A |
| `RegionId` | Required | Region of the source instance | N/A |
| `TargetZoneId` | Required (chosen by the user in Step 5) | Target availability zone (must differ from source) | N/A |
| `ImageName` | Optional | Image name | `Create_from_<instance-id>` |
| `InstanceName` | Optional | New instance name | `recovery-<original-name>` |
| `InstanceType` | Optional | New instance type (defaults to source type) | Source instance `InstanceType` |
| `VSwitchId` | Optional | Existing VSwitch in target zone (otherwise must be created) | From `describe-vswitches` |
| `CidrBlock` | Conditional | Confirmed by the user when a new VSwitch must be created | Confirmed by the user |

### User Interaction Pattern

> **[MUST] Every user decision point must use `AskUserQuestion` with 2-4 clickable options.**
> - Never just "stop and ask" -- always present clear, clickable options with short descriptions
> - Place the recommended option first and tag it `(Recommended)`
> - Once an option is clicked, the workflow continues immediately without further confirmation
>
> Example -- VSwitch creation:
> - Question: "Target zone cn-beijing-l has no VSwitch in the current VPC. Create a new one?"
> - Options: `Create VSwitch (Recommended)` / `Pick another zone`
>
> Example -- Instance type out of stock:
> - Question: "Original type ecs.g7.xlarge is out of stock in cn-beijing-l. Pick an alternative:"
> - Options: `ecs.g7e.xlarge (similar, in stock) (Recommended)` / `ecs.g8i.xlarge (newer generation, in stock)` / `Pick another zone`

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

## 7. Core Workflow

### General CLI Conventions

| Rule | Correct | Incorrect |
|------|---------|-----------|
| Command name | `describe-instances` (plugin mode, hyphenated) | `DescribeInstances` (PascalCase) |
| Region parameter | `--biz-region-id` | `--region-id`, `--RegionId` |
| Cross-region default | `--endpoint ecs.<region>.aliyuncs.com` | Endpoint omitted |
| User-Agent | Every API command carries `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}` | Missing |

The complete command list with parameter notes is in [references/related-commands.md](references/related-commands.md).

### Workflow Overview

```
Step 1: describe-instances + describe-disks -> Collect source instance and disk info
Step 2: create-image -> Create the whole-instance image (system disk + all data disks)
Step 3: describe-images -> Poll until the image is Available
Step 4: describe-available-resource + describe-vswitches -> Pick the target availability zone
Step 5: run-instances -> Create the instance in the target zone (use --data-disk Device= to control PL)
Step 6: Verify the new instance is Running and disk Category/PL match the source
```

### Step 1: Collect source instance information

```bash
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-ids '["<instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}

aliyun ecs describe-disks \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Record: `RegionId`, `ZoneId`, `InstanceType`, `ImageId`, `OSName`, `VpcId`, `VSwitchId`, `SecurityGroupId`, `InstanceChargeType`, `InternetChargeType`, `InternetMaxBandwidthOut`, and for each disk `DiskId`, `Device`, `Category`, `Size`, `PerformanceLevel`.

> The CLI default region may differ from the actual region of the instance. Requests outside the CLI default region **must** include `--endpoint`, otherwise they may silently return empty results.

### Step 2: Create the whole-instance image

`create-image` supports Running instances. The image automatically includes mappings for **all** disks (system disk + data disks).

After confirming the image name with the user (recommended `Create_from_<instance-id>`), run:

```bash
aliyun ecs create-image \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <instance-id> \
  --image-name "<image-name>" \
  --description "System image for AZ disaster recovery" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Record the returned `ImageId` for later use.

> **Error handling:** Retryable errors such as `InternalError` / `ServiceUnavailable` / `Throttling` / `OperationConflict` -- notify the user, then wait 15s and retry up to 3 times. Non-retryable errors such as `InvalidInstanceId.NotFound` / `IncorrectInstanceStatus` / `InvalidImageName.Duplicated` -- stop immediately and report the cause to the user.

### Step 3: Poll image status

Poll every 60 seconds until the image becomes `Available`:

```bash
aliyun ecs describe-images \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --image-id <image-id> \
  --status "Creating,Available,UnAvailable" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Report `Progress` percentage to the user on each poll. Typical duration is 3-10 minutes.

> **Timeout handling:** If the image is still `Creating` after 5 minutes, use `AskUserQuestion` to offer: `Keep waiting (Recommended)` / `Open the console` (provide the link `https://ecs.console.aliyun.com/image/<region>/images`) / `Abort this operation`.
> If the status becomes `UnAvailable`, stop immediately and report the failure reason from the `Description` field.

### Step 4: Pick the target availability zone

#### 4a. Check stock for the instance type across zones (excluding the source zone)

```bash
aliyun ecs describe-available-resource \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --destination-resource InstanceType \
  --instance-type <instance-type> \
  --instance-charge-type PostPaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Show the user a table containing **only zone IDs and stock status** (no VSwitch info), and use `AskUserQuestion` to let the user pick the target zone.

**Instance-type decision -- must use `AskUserQuestion`:**
- Original type **in stock** in the chosen zone: options `Keep original type (Recommended)` / `Choose another type`
- Original type **out of stock** in the chosen zone: list alternative types as options. **Do NOT** auto-substitute.

#### 4b. Check VSwitches in the source VPC for the target zone

```bash
aliyun ecs describe-vswitches \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --vpc-id <vpc-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

- Target zone has a VSwitch with matching `ZoneId` -> use it directly
- Otherwise -> use `AskUserQuestion` with options `Create VSwitch (Recommended)` (include a suggested CIDR in the description) / `Pick another zone`. **Never create a VSwitch without confirmation.** After the user confirms:

```bash
aliyun vpc create-vswitch \
  --biz-region-id <region> \
  --endpoint vpc.<region>.aliyuncs.com \
  --vpc-id <vpc-id> \
  --zone-id <target-zone> \
  --cidr-block <cidr-block> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

#### 4c. Check disk types supported by the target zone

```bash
aliyun ecs describe-available-resource \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-zone> \
  --destination-resource SystemDisk \
  --instance-type <instance-type> \
  --instance-charge-type PostPaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Record the supported disk types -- Step 5 may need them.

### Step 5: Create the instance in the target zone

The image is a **whole-instance image** that already contains mappings for all disks. To control disk type and PerformanceLevel, use `--data-disk Device=<device-path> ...`; this **overrides** parameters of data disks defined in the image -- it does NOT create new disks.

> **Critical: network and billing parameters MUST reuse values recorded in Step 1, not hard-coded defaults.**

```bash
aliyun ecs run-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-zone> \
  --image-id <image-id> \
  --instance-type <instance-type> \
  --vswitch-id <target-vswitch-id> \
  --security-group-id <security-group-id> \
  --instance-name "<new-instance-name>" \
  --instance-charge-type <instance-charge-type> \
  --internet-charge-type <internet-charge-type> \
  --internet-max-bandwidth-out <internet-max-bandwidth-out> \
  --system-disk-category <system-disk-category> \
  --system-disk-size <system-disk-size> \
  --system-disk-performance-level <system-disk-PL> \
  --data-disk Device=<data-disk-device> Category=<data-disk-category> Size=<data-disk-size> PerformanceLevel=<PL> \
  --amount 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

> **[MUST] Always specify the system disk PerformanceLevel explicitly.** When omitted, PL takes the instance-type default and may not match the source (e.g., PL0 -> PL1). Only the cloud_essd family supports PL; omit this parameter for `cloud_auto`, `cloud_essd_entry`, etc.

> **[CRITICAL] `--data-disk` must use `Device=` rather than `SnapshotId=`!**
> - `Device=/dev/xvdb` -- **overrides** the parameters of that device's disk in the image (correct)
> - `SnapshotId=s-xxx` -- creates an **additional** disk on top of the disks auto-restored by the image (incorrect)
> - Do not use the `--data-disk-N-*` form (e.g., `--data-disk-1-performance-level`); it does not support PL and causes PL downgrades.
>
> Multiple data disks: use multiple `--data-disk` flags: `--data-disk Device=/dev/xvdb ... --data-disk Device=/dev/xvdc ...`

> If the target zone does not support the source system disk type (e.g., `cloud_essd_entry`), use `AskUserQuestion` to present supported types from 4c as clickable options, marking the closest compatible type as Recommended. **Never silently substitute.**

> **`run-instances` error diagnosis (do not retry blindly):**
>
> | Error Code | Root cause | Action |
> |------------|-----------|--------|
> | `QuotaExceeded.*` | Insufficient quota | Notify the user, provide the quota management console link |
> | `OperationDenied.NoStock` / `InvalidInstanceType.ValueNotSupported` | Out of stock | Use `AskUserQuestion` to offer alternative types or another zone |
> | `InvalidDiskCategory.NotSupported` | Disk category unsupported | Provide alternatives based on 4c results |
> | `InvalidParameter.Conflict` / `InvalidParameter` | Parameter conflict | Surface the specific conflict; check disk parameters vs. instance-type compatibility |
> | `IncorrectImageStatus` | Image not ready | Return to Step 3 and wait |
> | `Account.Arrearage` / `InvalidPayMethod` | Account arrears / payment problem | Notify the user to resolve |
> | `InternalError` / `ServiceUnavailable` | Transient server-side failure | Wait 15s and retry up to 3 times |
> | Other unknown | Unknown | Show the full error code and message; suggest opening a ticket |
>
> **Principle:** Always tell the user the **root cause** of the failure and **actionable next steps**, not just "creation failed".

### Step 6: Verify the new instance

```bash
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-ids '["<new-instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}

aliyun ecs describe-disks \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <new-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-image/{session-id}
```

Confirm `Status == "Running"`, `ZoneId` equals the target zone, `InstanceType` is correct, and a private IP is assigned. Compare each disk's Category, Size, PerformanceLevel, and Device against the source. Show the comparison table to the user.

Full verification steps are in [references/verification-method.md](references/verification-method.md).

## 8. Success Verification Method

Success criteria (full comparison in [references/verification-method.md](references/verification-method.md)):

| Criterion | Standard |
|-----------|----------|
| Image creation | Status `Available`, contains all source disk mappings |
| New instance | Status `Running`, private IP assigned |
| Zone switch | New instance `ZoneId` != source `ZoneId`, `RegionId` is the same |
| Disk recovery | Each disk's Category / Size / PerformanceLevel matches the source |
| Network/billing | InstanceChargeType / InternetChargeType / InternetMaxBandwidthOut match the source |
| Source instance integrity | Source instance not stopped / released / modified |

## 9. Command Tables

The complete CLI command list with key parameters is in [references/related-commands.md](references/related-commands.md).

## 10. Best Practices

1. **CLI-First**: This Skill uses `aliyun` CLI plugin mode (hyphenated command names) throughout; avoid the PascalCase form.
2. **Always include `--endpoint` for cross-region calls**: Requests outside the CLI default region may silently return empty results when the endpoint is omitted.
3. **Whole-instance image + Device override**: Using a whole-instance image plus `--data-disk Device=...` is the cleanest recovery approach and avoids creating disks separately.
4. **Reuse source instance parameters**: All network / billing / bandwidth / disk PL values are read from `describe-instances` and `describe-disks` and reused -- never hard-coded.
5. **Always use `AskUserQuestion` at decision points**: Provide clickable options for choosing zones, instance types, VSwitch creation, disk type substitution, etc.
6. **Zero-touch credentials**: Only use `aliyun configure list` to check credentials; never read, print, or set AK/SK.
7. **Do not stop the source instance**: `create-image` works directly on Running instances; this Skill is a backup flow only and never modifies source resources.
8. **Classify errors before reacting**: Categorize API errors first (resource / quota / parameter / server-side), then decide whether to retry or stop.
9. **No destructive operations**: This Skill **must NOT** execute any `delete-instance`, `delete-image`, `delete-disk`, `release-instance`, or other `delete-*` / `release-*` commands. This is a **backup** flow; the new instance and image are kept by default and the user cleans them up via the console or outside the session.

## 11. Reference Links

| Document | Description |
|----------|-------------|
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation and configuration guide |
| [references/related-commands.md](references/related-commands.md) | Full CLI command list and parameter notes |
| [references/ram-policies.md](references/ram-policies.md) | Detailed RAM permission list and policy JSON |
| [references/verification-method.md](references/verification-method.md) | Success verification method for each step |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria with correct / incorrect patterns |
| [ECS API Reference](https://www.alibabacloud.com/help/ecs/developer-reference/api-overview) | ECS API documentation |
| [Aliyun CLI Documentation](https://www.alibabacloud.com/help/cli/what-is-alibaba-cloud-cli) | CLI usage documentation |
