---
name: alibabacloud-ecs-disaster-recovery-snapshot
description: |
  Alibaba Cloud ECS snapshot-based cross-AZ disaster recovery skill. Two scenarios:
  Scenario A (Full Instance Recovery): Recover ECS instance to a different AZ via snapshots —
  multi-disk uses snapshot consistency group for crash consistency, creates full custom image
  (system + data disks), launches new instance in target AZ; single-disk uses individual snapshot.
  Scenario B (Disk-Level Recovery): Snapshot specific disks from source instance,
  create new disks from snapshots, and attach them to an existing target instance.
  Triggers: cross-AZ disaster recovery, cross-zone backup, ECS snapshot recovery,
  snapshot backup, DR recovery, create instance from snapshot in another AZ,
  attach disk snapshot to another instance, create instance replica via snapshot.
  可用区灾备恢复、跨可用区备份、ECS 快照恢复、快照备份、灾备恢复、
  在另一个可用区从快照创建实例、把盘快照挂载到其他实例、用快照在另一个可用区创建实例副本、
  恢复这台机器到另一个可用区、跨实例磁盘备份。
  Note: This is "backup" not "migration" — the original instance remains untouched.
---
# ECS Snapshot-Based Disaster Recovery Backup

This skill provides snapshot-based disaster recovery **backup** for ECS instances. The original
instance and all its resources remain untouched — this is a **backup operation, not a migration**.
It supports two scenarios:

- **Scenario A — Full Instance Backup**: Backs up an entire ECS instance to a different availability
  zone. **Multi-disk** (system + ≥1 data disk): uses **snapshot consistency group** (CreateSnapshotGroup)
  for cross-disk consistency, then creates a **full image** (system + data disks) — run-instances
  directly from the image, data disks auto-restored.
  **Single-disk** (system only): uses individual snapshot (create-snapshot) + system-disk-only image.
  Use when: AZ failure, datacenter backup, full instance cloning.
- **Scenario B — Disk-Level Backup**: Takes a snapshot of specific disk(s) from a source instance,
  creates new disk(s) from the snapshot, and attaches them to an existing target instance.
  Use when: back up specific data disk to another instance, cross-instance disk backup,
  or attach source disk data to an existing DR instance.

## Scenario Detection

At the start of the workflow, determine which scenario applies based on the user's intent:

| User Intent                                                                        | Scenario    |
| ---------------------------------------------------------------------------------- | ----------- |
| "back up this instance to another AZ" / "create a DR instance"                     | **A** |
| "snapshot a disk and attach to another instance" / "mount disk to target instance" | **B** |
| Ambiguous — ask the user to clarify                                               | Ask         |

Once the scenario is determined, follow the corresponding workflow below.

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.3 required**
>
> 1. Run `aliyun version` to check if CLI is installed and its version.
> 2. If CLI is **not installed** (command not found): inform the user and ask whether to install it.
>    Only after user confirmation, download the installer with `curl -fsSL --connect-timeout 10 --max-time 60 https://aliyuncli.alicdn.com/setup.sh -o /tmp/aliyun_cli_setup.sh`,
>    then run `bash /tmp/aliyun_cli_setup.sh` to execute the downloaded script.
> 3. If CLI is installed but **version < 3.3.3**: inform the user of the current version and the minimum requirement,
>    then ask whether to upgrade. Only after user confirmation, run the upgrade command.
> 4. If CLI is installed and **version >= 3.3.3**: proceed directly, no action needed.
>
> **IMPORTANT: Do NOT upgrade Aliyun CLI without explicit user confirmation. Only prompt for upgrade when the version check fails.**

> **Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
>
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **NEVER** export or set AK/SK as environment variables in commands (e.g. `export ALIBABA_CLOUD_ACCESS_KEY_ID=...` is FORBIDDEN). Always use `aliyun` CLI directly — it uses local credentials automatically.
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
>
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
>
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

## CLI Command Standards

> **[MUST]** All CLI commands MUST follow these standards to avoid parameter errors.

| Rule                        | Correct                                                                                               | Incorrect                             |
| --------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------------------- |
| **Command name**      | `describe-instances` (kebab-case)                                                                   | `DescribeInstances` (PascalCase)    |
| **User agent**        | Always include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot/{session-id}` | Missing user-agent or session-id      |
| **Region parameter**  | Use `--biz-region-id` for commands that support it; use `--endpoint` only for `create-snapshot` and `attach-disk` | `--region-id` or `--RegionId`     |
| **Endpoint**          | Add `--endpoint ecs.<region>.aliyuncs.com` when CLI default region differs                          | Omitting endpoint                     |
| **List parameters**   | `--disk-id val1 val2` (space-separated)                                                             | `--disk-id.1 val1 --disk-id.2 val2` |
| **VSwitch parameter** | `--vswitch-id`                                                                                      | `--v-switch-id`                     |

**[MUST] CLI User-Agent** — Every `aliyun` CLI command that calls a cloud API must include:
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot/{session-id}`
(See Observability section below for session-id generation rules)

## RAM Policy

See [references/ram-policies.md](references/ram-policies.md) for the full list of required RAM permissions.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) once for the entire session. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot/{session-id}
```
Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun ecs describe-instances --biz-region-id cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.
## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, instance IDs,
> IP addresses, etc.) MUST be confirmed with the user. Do NOT assume or use default
> values without explicit user approval.

### User Interaction Pattern

> **[MUST] Use interactive choice prompts for all user decisions.**
> Use `AskUserQuestion` tool to present 2–4 concrete options with short descriptions.
> Put recommended option first with `(Recommended)` suffix. Never just "STOP and ask" —
> always provide clickable options so the user can decide with a single click.

### Scenario A — Full Instance Backup

| Parameter Name   | Required/Optional | Description                          | Default Value               |
| ---------------- | ----------------- | ------------------------------------ | --------------------------- |
| `InstanceId`   | Required          | Source ECS instance ID               | N/A                         |
| `RegionId`     | Required          | Region where the instance is located | Auto-detected from instance |
| `TargetZoneId` | Required          | Target availability zone             | N/A                         |
| `InstanceName` | Optional          | Name for the new instance            | `recovery-<source-instance-name>` |

### Scenario B — Disk-Level Backup

| Parameter Name       | Required/Optional | Description                               | Default Value               |
| -------------------- | ----------------- | ----------------------------------------- | --------------------------- |
| `SourceInstanceId` | Required          | Source ECS instance ID (disk owner)       | N/A                         |
| `SourceDiskIds`    | Required          | Specific disk ID(s) to snapshot           | All data disks (ask user)   |
| `TargetInstanceId` | Required          | Target ECS instance ID to attach disks to | N/A                         |
| `RegionId`         | Required          | Region where instances are located        | Auto-detected from instance |
| `DiskCategory`     | Optional          | Disk category for new disk(s)             | Same as source disk         |

## Execution Steps — Scenario A: Full Instance Backup

### Step 1: Gather Information

Confirm the following inputs with the user (proactively ask if not provided):

- **Source instance ID** (required)
- **Target availability zone** (required, e.g. cn-beijing-l)
- **Instance name** (optional, default: `recovery-<source-instance-name>`)

The source instance's RegionId can be auto-detected from instance details — no need to ask the user.

### Step 2: Query Source Instance Details

Make two parallel API calls to gather all information:

```bash
# Query instance details (spec, security group, VPC, VSwitch)
aliyun ecs describe-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-ids '["<instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot

# Query disk information
aliyun ecs describe-disks \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Extract and record from the results:
- RegionId, ZoneId (current availability zone)
- **InstanceName** (source instance name, used for default DR instance naming)
- InstanceType (instance spec)
- SecurityGroupId
- VpcId, VSwitchId
- **InstanceChargeType** — instance billing mode (PrePaid/PostPaid), must be replicated on the new instance
- **InternetChargeType** — network billing mode (PayByTraffic/PayByBandwidth), must be replicated
- **InternetMaxBandwidthOut** — outbound bandwidth cap (Mbps), must be replicated
- **PublicIpAddress** — whether the source has a public IP assigned. The DR instance MUST replicate this exactly:
  - If source **has** public IP → set `InternetMaxBandwidthOut` to the same value as source (must be > 0)
  - If source **has NO** public IP → **MUST** set `InternetMaxBandwidthOut=0` and **MUST NOT** assign any public IP to the new instance. This is a hard constraint — never enable public IP on the DR instance if the source does not have one.
- All disks' DiskId, **device path** (e.g. `/dev/xvda`, `/dev/xvdb`), Type (system/data), Category, Size, and **PerformanceLevel** (e.g. PL0, PL1 — only applicable to cloud_essd family).
  This information is critical for Step 3 (snapshot creation) and Step 6 (instance creation).

### Step 3: Create Snapshots

Determine the snapshot strategy based on the disk count from Step 2:

| Disk Configuration | Strategy |
| --- | --- |
| **System disk + ≥1 data disk** (multi-disk) | Use **snapshot consistency group** (`create-snapshot-group`) |
| **System disk only** (single-disk) | Use **individual snapshot** (`create-snapshot`) |

> **Why snapshot consistency group for multi-disk?**
> Snapshot consistency groups guarantee **cross-disk crash consistency** — all disk snapshots
> are taken at the same point-in-time. This is critical for applications that span multiple disks
> (e.g. database with separate data/log disks).

#### Path A: Multi-Disk — Snapshot Consistency Group

```bash
aliyun ecs create-snapshot-group \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <instance-id> \
  --name "SnapGroup_<instance-id>_<date>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Poll with `describe-snapshot-groups` until `Status: accomplished`:

```bash
aliyun ecs describe-snapshot-groups \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --snapshot-group-id <snapshot-group-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Extract: **system snapshot ID** (`SourceDiskType: system`) + **data snapshot IDs** (`SourceDiskType: data`).

> **Important**: Snapshot consistency groups support **Instant Access** — snapshots can be used for `create-image` as soon as group status is `accomplished`.

#### Path B: Single-Disk — Individual Snapshot
```bash
aliyun ecs create-snapshot \
  --endpoint ecs.<region>.aliyuncs.com \
  --disk-id <system-disk-id> \
  --snapshot-name "Snap_<instance-id>_sys_<date>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Poll with `describe-snapshots` until `Available: true` AND `Progress: 100%` AND `Status: accomplished`.

> **Failure Handling**: See [Error Handling Guide](references/error-handling.md#scenario-a--step-3-snapshot-creation) for retry strategy, timeout handling, and user interaction patterns.

**Important**: The system snapshot must be fully ready before proceeding to Step 4 (create-image). Report progress to the user at each poll check.

### Step 4: Create Image

#### Multi-Disk — Full Image (System + Data Disks)
Create an image containing **ALL disk snapshots** from the consistency group (system + every data disk).

```bash
aliyun ecs create-image \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --image-name "Create_from_<instance-id>_<date>" \
  --disk-device-mapping DiskType=system SnapshotId=<system-snapshot-id> Size=<system-disk-size> \
  --disk-device-mapping DiskType=data SnapshotId=<data-snapshot-id-1> Size=<data-disk-1-size> \
  --disk-device-mapping DiskType=data SnapshotId=<data-snapshot-id-2> Size=<data-disk-2-size> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

> Add one `--disk-device-mapping DiskType=data SnapshotId=... Size=...` for **each data disk**. Snapshot IDs come from the consistency group (Step 3 Path A).

#### Single-Disk — System-Disk-Only Image
```bash
aliyun ecs create-image \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --image-name "Create_from_<instance-id>_<date>" \
  --disk-device-mapping DiskType=system SnapshotId=<system-snapshot-id> Size=<system-disk-size> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Image naming convention: `Create_from_<instance-id>`. Append date suffix `_YYYYMMDD` if name conflicts.

After creation, confirm Status is Available using `describe-images`:
```bash
aliyun ecs describe-images \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --image-id <image-id> \
  --status "Creating,Available,UnAvailable" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Poll every 60 seconds until Status is `Available`. Report progress to the user at each check.

> **Failure Handling**: See [Error Handling Guide](references/error-handling.md#scenario-a--step-4-image-creation) for retry strategy and timeout handling.

### Step 5: Prepare Target Availability Zone Resources

Query VSwitch and resource availability in the target AZ:
```bash
aliyun ecs describe-vswitches \
  --biz-region-id <region> --endpoint ecs.<region>.aliyuncs.com \
  --vpc-id <vpc-id> --zone-id <target-az> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot

aliyun ecs describe-available-resource \
  --biz-region-id <region> --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-az> --destination-resource InstanceType \
  --instance-type <instance-type> --instance-charge-type PostPaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot

aliyun ecs describe-available-resource \
  --biz-region-id <region> --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-az> --destination-resource SystemDisk \
  --instance-type <instance-type> --instance-charge-type PostPaid \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

**Decisions (always use `AskUserQuestion`):**
- **No VSwitch in target AZ** → ask user: `Create VSwitch (Recommended)` / `Choose another AZ`
- **Instance type no stock** → present alternatives (similar vCPU/memory) or alternative AZs
- **Disk category unsupported** → present available alternatives as clickable options

### Step 6: Create Disaster Recovery Instance

The image contains all disk snapshots (multi-disk) or system disk snapshot only (single-disk).
While `run-instances` auto-restores data disk **content** from the image, it does **NOT** inherit the source data disk's **category** or **performance level** — these **MUST** be overridden via `--data-disk Device=<path> ...` parameters.

**Critical**: The DR instance MUST inherit the source instance's properties:
- **VPC + Security Group**: Same VpcId (find/create VSwitch in target AZ) and same SecurityGroupId.
- **Public IP (CRITICAL)**: The DR instance's public IP status MUST exactly match the source:
  - Source **has** public IP → set `InternetMaxBandwidthOut` to the same value as source (> 0)
  - Source **has NO** public IP → **MUST** set `InternetMaxBandwidthOut=0`. **NEVER** assign a public IP or set bandwidth > 0 when the source instance has no public IP. Violating this rule will expose the DR instance to the internet unexpectedly.
- **System Disk**: Category, Size, **PerformanceLevel** must match source exactly.
  > **CRITICAL**: `--system-disk-performance-level` is **mandatory** for cloud_essd disks. If omitted, the API defaults to PL1.
- **Data Disk(s) (CRITICAL)**: Each data disk MUST be overridden via `--data-disk Device=<device-path> Category=<category> Size=<size> PerformanceLevel=<PL>` matching the source. The `Device=` path comes from Step 2 (e.g. `/dev/xvdb`). Without this, the system defaults to `cloud_auto` and loses the original performance spec.
- **Billing**: `InstanceChargeType` (PrePaid/PostPaid) and `InternetChargeType` (PayByTraffic/PayByBandwidth) must match source exactly.

**Disk category decision — always ask the user via `AskUserQuestion`:**
Note the system disk category compatibility in the target AZ. If the original disk category is unsupported,
use `AskUserQuestion` to present available alternatives as clickable options.
Do NOT silently substitute a disk category.

**Instance Naming (MUST follow)**:
The default instance name format is `recovery-<source-instance-name>`, where `<source-instance-name>` is the `InstanceName` field extracted in Step 2 from `describe-instances`.
For example, if the source instance name is `prod-web-server`, the DR instance name MUST be `recovery-prod-web-server`.
Only override this default if the user explicitly provides a custom name.
Do NOT use instance ID, generic prefixes like `dr-backup-`, or any other naming pattern.

```bash
aliyun ecs run-instances \
  --biz-region-id <region> \
  --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-az> \
  --image-id <image-id> \
  --instance-type <instance-type> \
  --security-group-id <sg-id> \
  --vswitch-id <target-vswitch-id> \
  --system-disk-category <system-disk-category> \
  --system-disk-size <system-disk-size> \
  --system-disk-performance-level <system-disk-performance-level> \
  --data-disk Device=<device-path> Category=<data-disk-category> Size=<data-disk-size> PerformanceLevel=<data-disk-PL> \
  --instance-name "recovery-<source-instance-name>" \
  --instance-charge-type <instance-charge-type> \
  --internet-charge-type <internet-charge-type> \
  --internet-max-bandwidth-out <internet-max-bandwidth-out> \
  --amount 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

> **Note**: `--data-disk` with `Device=` **overrides** the parameters of that disk in the image — it does NOT create new disks.
> - `Device=/dev/xvdb` — overrides the image's data disk parameters (correct). Multiple data disks: use multiple `--data-disk` flags.
> - `SnapshotId=s-xxx` — creates an **additional** disk (incorrect, never use). Do NOT use `--data-disk-N-*` form; it does not support PL.
> - For single-disk (system only), omit `--data-disk`.

After creation, wait ~15 seconds then confirm Running via `describe-instances`. Verify each data disk's **Category** and **PerformanceLevel** match source via `describe-disks`.

> **Failure Handling**: See [Error Handling Guide](references/error-handling.md#scenario-a--step-6-instance-creation-run-instances) for error diagnosis table, retry strategy, and status abnormality handling.

## Execution Steps — Scenario B: Disk-Level Backup

### Step 1: Gather Information

Confirm the following inputs with the user (proactively ask if not provided):

- **Source instance ID** (required) — the instance whose disk(s) will be snapshotted
- **Target disk(s)** (required) — which disk(s) to snapshot (system disk, data disk, or specific disk IDs).
  If the user says "data disk", query disks and confirm which data disk(s) to include.
- **Target instance ID** (required) — the existing instance to attach the recovered disk(s) to

The RegionId can be auto-detected from the source instance details.

### Step 2: Query Source Disk and Target Instance Details

```bash
aliyun ecs describe-disks \
  --biz-region-id <region> --endpoint ecs.<region>.aliyuncs.com \
  --instance-id <source-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot

aliyun ecs describe-instances \
  --biz-region-id <region> --endpoint ecs.<region>.aliyuncs.com \
  --instance-ids '["<target-instance-id>"]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

Extract: Source disk(s) DiskId/Type/Category/Size; Target instance ZoneId.

### Step 3: Create Snapshots

For each disk, create an individual snapshot (poll until `Status: accomplished` + `Progress: 100%`):

```bash
aliyun ecs create-snapshot \
  --endpoint ecs.<region>.aliyuncs.com \
  --disk-id <disk-id> \
  --snapshot-name "Snap_<instance-id>_<disk-type>_<date>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

> **Failure Handling**: See [Error Handling Guide](references/error-handling.md#scenario-b--step-3-snapshot-creation).

### Step 4: Create Disk(s) from Snapshot(s)

Create new disk(s) in the **target instance's AZ**. Use `AskUserQuestion` if disk category is unavailable.

> **CRITICAL**: For cloud_essd disks, always pass `--performance-level` matching the source disk. If omitted, the API defaults to PL1, which changes the disk's performance specification.

```bash
aliyun ecs create-disk \
  --biz-region-id <region> --endpoint ecs.<region>.aliyuncs.com \
  --zone-id <target-instance-zone> --snapshot-id <snapshot-id> \
  --disk-category <disk-category> --size <disk-size> \
  --performance-level <performance-level> \
  --disk-name "data-from-source" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

### Step 5: Attach Disk(s) and Verify

```bash
aliyun ecs attach-disk \
  --endpoint ecs.<region>.aliyuncs.com \
  --disk-id <new-disk-id> --instance-id <target-instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disaster-recovery-snapshot
```

> **Failure Handling**: See [Error Handling Guide](references/error-handling.md#scenario-b--steps-4-5-disk-creation--attachment).

Verify disks show `Status: In_use` via `describe-disks`. Remind user that the new disk needs to be mounted on the target instance, but **NEVER** output system commands (e.g. `lsblk`, `mount`, `fdisk`, `mkfs`) — you don't know the user's OS or usage scenario.

## Safety Rules

- **Never delete instances, disks, or snapshots without explicit user confirmation.**
- **Do not stop the source instance** — snapshot operations support Running instances.
- **Never make resource-changing decisions on behalf of the user.** Always use `AskUserQuestion` to present clickable options before proceeding.

## Key Constraints and Pitfalls

1. **Multi-disk MUST use snapshot consistency group**: When the instance has system disk + ≥1 data disk, always use `create-snapshot-group` to ensure cross-disk crash consistency. Then create a **full image** with all disk snapshots (DiskType=system + DiskType=data entries). The image provides snapshot data, but `--data-disk Device=<path> Category=... Size=... PerformanceLevel=...` MUST be passed in `run-instances` to **override** each data disk's parameters — without it, data disks default to `cloud_auto`.
2. **Single-disk uses individual snapshot**: When the instance has only a system disk, use `create-snapshot` + system-disk-only image.
3. **create-image for multi-disk includes all disks**: Use `--disk-device-mapping` with `DiskType=system` for the system snapshot AND one `DiskType=data` entry per data disk snapshot. All snapshot IDs come from the consistency group.
4. **Disk category availability varies by zone**: `cloud_essd_entry` is not supported in all zones. Verify with `describe-available-resource` before creation; **ask the user** which alternative to use.
5. **`create-snapshot` and `attach-disk` do NOT support `--biz-region-id`**: Use `--endpoint ecs.<region>.aliyuncs.com` only.
6. **Snapshot must be ready before create-image**: For consistency groups, poll until group `Status: accomplished`. For individual snapshots, poll until `Available: true` AND `Progress: 100%`.
7. **Scenario B — create-disk requires snapshot Progress 100%**: Unlike `create-image` which works with InstantAccess snapshots, `create-disk` requires the snapshot to be fully completed.
8. **Scenario B — Disk must be in the same AZ as target instance**: A disk can only be attached to an instance in the same availability zone.
9. **DR instance must inherit source instance properties**: VPC (same VpcId), security group (same SecurityGroupId), public IP status (has/not-has), and disk specs (Category/Size/**PerformanceLevel**) must all match the source instance exactly. Do NOT use different VPC, security group, or disk specifications. **CRITICAL: If the source instance has NO public IP, the DR instance MUST set `InternetMaxBandwidthOut=0` — never enable public IP on the DR instance when the source does not have one.**
10. **System disk PerformanceLevel MUST be explicitly specified**: `run-instances` defaults to PL1 for cloud_essd if `--system-disk-performance-level` is omitted. Always pass the source disk's exact PerformanceLevel (PL0, PL1, PL2, PL3) to prevent unintended spec changes.
11. **DR instance name MUST be `recovery-<source-instance-name>`**: Use the `InstanceName` field from Step 2's `describe-instances` result, prefixed with `recovery-`. Do NOT use the instance ID, generic prefixes (e.g. `dr-backup-`, `backup-`), or any other naming pattern. Only override if the user explicitly provides a custom name.

## Output Format

Upon completion, present a comparison table showing Source Instance vs DR Instance (for Scenario A)
or an operation summary table (for Scenario B). Include: Instance IDs, names, zones, types,
IP addresses, disk details, image info, and status. For Scenario B, also show target instance's
full disk layout table.
## Reference Links

| Document                                                                                 | Description                                            |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| [CLI Installation Guide](references/cli-installation-guide.md)                              | Aliyun CLI installation and configuration instructions |
| [Error Handling Guide](references/error-handling.md)                                        | Retry strategies, timeout handling, error diagnosis    |
| [RAM Policies](references/ram-policies.md)                                                  | Required RAM permissions for this skill                |
| [Related Commands](references/related-commands.md)                                          | Full CLI command reference table                       |
| [ECS API Reference](https://www.alibabacloud.com/help/ecs/developer-reference/api-overview) | ECS API documentation                                  |
| [Aliyun CLI Documentation](https://www.alibabacloud.com/help/cli/what-is-alibaba-cloud-cli) | CLI usage guide                                        |