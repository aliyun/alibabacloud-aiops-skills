# Verification Method — alibabacloud-pai-dsw-manage

Step-by-step verification commands and success criteria for each operation.

## 1. Verify Credentials

```bash
aliyun configure list
```

**Expected**: A valid profile with a non-empty AccessKey.

---

## 2. Verify Plugin Installation

```bash
aliyun pai-dsw --help --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Expected**: Help output listing available `pai-dsw` subcommands.

---

## 3. Verify ListWorkspaces (Required before CreateInstance)

```bash
aliyun aiworkspace list-workspaces \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- `TotalCount` >= 1 (user has at least one workspace)
- `Workspaces` array contains workspace objects with `WorkspaceId`, `WorkspaceName`, `Status`
- At least one workspace has `Status == "ENABLED"`

> See SKILL.md "Parameter Confirmation" section for how to get WorkspaceId.

---

## 4. Verify ListEcsSpecs

```bash
aliyun pai-dsw list-ecs-specs \
  --accelerator-type CPU \
  --region <region> \
  --page-number 1 \
  --page-size 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage

aliyun pai-dsw list-ecs-specs \
  --accelerator-type GPU \
  --region <region> \
  --page-number 1 \
  --page-size 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- `TotalCount` >= 0
- `EcsSpecs` array present (may be empty)
- `Success` is `true`
- Each entry contains `InstanceType`, `IsAvailable`, `CPU`, `Memory`
- CPU results: `AcceleratorType == "CPU"`, `GPU == 0`
- GPU results: `AcceleratorType == "GPU"`, `GPU >= 1`, `GPUType` non-empty

---

## 5. Verify Instance Existence Check

See SKILL.md Section 2.1 for check-then-act pattern and decision logic.

> **[WARNING]** The `--instance-name` filter may return partial matches. See SKILL.md "Exact name match required" for details.

---

## 6. Verify CreateInstance

```bash
aliyun pai-dsw list-instances \
  --instance-name <your-instance-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- Instance appears in results
- `InstanceId` is non-empty (`dsw-xxxxx` format)
- `Status` is `Creating`, `Starting`, or `Running`

> See SKILL.md "Return immediately after creation" for non-blocking workflow.

---

## 7. Verify Instance State (On-Demand)

```bash
aliyun pai-dsw get-instance \
  --instance-id <instance-id> \
  --read-timeout 30 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Key fields**:
- `.Status` — Current lifecycle state
- `.InstanceUrl` — Accessible when `Running`
- `.ReasonCode` / `.ReasonMessage` — Failure diagnostics

> See SKILL.md Step 4 for polling guidance (when to poll, timeout limits, intervals).

**State transitions**: See [`related-commands.md`](related-commands.md#instance-status-values).

---

## 8. Verify UpdateInstance

```bash
aliyun pai-dsw get-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- Modified fields (`InstanceName`, `EcsSpec`, `ImageId`) reflect new values
- `Status` is `Running` or `Stopped` (not `Updating`)

---

## 9. Verify ListInstances

```bash
aliyun pai-dsw list-instances \
  --page-number 1 \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- `TotalCount` >= 0
- `Instances` array present (may be empty)
- `Success` is `true`

---

## 10. Verify StartInstance

```bash
aliyun pai-dsw get-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- `Status` eventually reaches `Running`
- `InstanceUrl` is populated

---

## 11. Verify StopInstance

```bash
aliyun pai-dsw get-instance \
  --instance-id <instance-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dsw-manage
```

**Success criteria**:
- `Status` eventually reaches `Stopped`

> To save the environment as a custom image, use the PAI Console. See SKILL.md Step 5.

---

## Manual Verification Only

| Item | Reason | How to Verify |
|---|---|---|
| CreateInstance RAM Action | Undocumented in official docs | Confirm in [RAM Console](https://ram.console.aliyun.com/) |
| Instance URL reachability | Requires web browser | Open `InstanceUrl` in a browser |
| VPC network connectivity | Requires in-container access | Run connectivity tests from DSW Terminal |
