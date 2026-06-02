# Success Verification Methods

This document describes how to verify successful execution of each phase of the `alibabacloud-aes-sysom-pai-diagnosis` skill.

---

## Phase 1: Environment Setup Verification (Steps 0–3)

| Step | Verification Command | Success Criteria |
|------|---------------------|------------------|
| 0. AI-Mode | `aliyun configure ai-mode get` | Output shows `ai-mode: enabled` |
| 1. CLI Version | `aliyun version` | Version >= `3.3.1` |
| 2. Auto Plugin Install | `aliyun configure get --auto-plugin-install` | Returns `true` |
| 3. Credentials | `aliyun configure list` | At least one profile shows valid AK / STS / OAuth identity |

---

## Phase 2: Diagnosis Execution Verification (Steps 4–8)

### Step 4 — Parameter Confirmation

✅ Required parameters `region` and `instance` are confirmed. `product` is auto-inferred from the `instance` prefix (`eas-` → `EAS`, `dlc` → `DLC`); only asked when inference fails.

### Step 5 — SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

✅ Response returns success without authorization errors.

### Step 6 — Resource Validation

#### 6A. EAS — Verify Service Exists

```bash
aliyun eas list-services --region <region> --filter <eas_service_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

✅ Response contains a non-empty `Services` array; at least one entry's `ServiceId` exactly matches the user-provided ID.

❌ Failure indicators:
- Empty `Services` array or no entry matches the `ServiceId` → invalid `ServiceId` for the given `region`
- `Forbidden` error → missing `eas:ListServices` permission

#### 6B. DLC — Verify Resource Type is Lingjun

```bash
aliyun pai-dlc get-job --region <region> --job-id <dlc_job_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

✅ Response contains `ResourceType` field with value `Lingjun`.

❌ Failure indicators:
- Job not found / empty response → invalid DLC job ID
- `ResourceType` is not `Lingjun` → unsupported resource type, stop pipeline
- `Forbidden` error → missing `pai-dlc:GetJob` permission

### Step 7 — Invoke Diagnosis

```bash
aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '<JSON>' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

✅ Response contains a non-empty `task_id` field.

⚠️ Special case: `Sysom.TaskInProgress` → extract existing `task_id` from error message and continue to polling (treated as success).

### Step 7 — Poll Diagnosis Result

```bash
aliyun sysom get-diagnosis-result --task-id <task_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis
```

| Returned `status` | Meaning | Action |
|-------------------|---------|--------|
| `Ready` / `Running` | In progress | Continue polling (max 60 attempts, 10s interval) |
| `Success` | ✅ Complete | Proceed to Step 8 |
| `Fail` | ❌ Failed | Report failure to user, stop pipeline |

### Step 8 — Result Output

✅ The user is shown:
- `summary.overall_status`
- `summary.root_cause`
- `summary.suggestions`
- Key entries from `issues[]`
- Echo of `product` field (to confirm correct routing)

---

## End-to-End Acceptance

A complete successful run satisfies **all** of:

1. Phase 1 environment setup commands return successfully
2. For EAS: `ListServices` confirms the service ID exists; for DLC: `GetJob` confirms job exists and `ResourceType` is `Lingjun`
3. `invoke-diagnosis` returns a `task_id`
4. `get-diagnosis-result` polling reaches `Success` within 60 attempts
5. The diagnosis report is presented to the user with the correct `product` field echoed
6. AI-Mode is disabled at the end (`aliyun configure ai-mode disable`)
