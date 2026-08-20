# Success Verification: alibabacloud-aes-sysom-lingjun-diagnosis

This document describes the success verification methods for each phase. All `aliyun` CLI commands that call OpenAPI **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}` (see the Observability section in `SKILL.md`); local/system commands (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`) **MUST NOT** carry `--user-agent`.

---

## 1. Environment Setup Verification

### 1.1 CLI Version

```bash
aliyun version
```

**Success criteria**: Version >= 3.3.1

### 1.2 Credential Configuration

```bash
aliyun configure list
```

**Success criteria**: Output contains a valid profile (AK, STS, or OAuth identity)

---

## 2. Diagnosis Phase Verification

### 2.1 Cloud Assistant Online Check

```bash
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <region> \
  --instance-id <instance_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**Success criteria**: `CloudAssistantStatus` is `"true"` in the response (`--instance-id` takes the lingjun node ID `e01-cn-xxxxx`)

**Non-fatal**: only an explicit `"false"` blocks the diagnosis. If the call itself fails (e.g. `403 Forbidden.RAM` on `ecs:DescribeCloudAssistantStatus`), the pre-check is skipped and the pipeline continues — this does not count as a verification failure.

### 2.2 SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**Success criteria**: No error returned

### 2.3 Instance Support Check

```bash
aliyun sysom check-instance-support \
  --instances <instance_id> \
  --biz-region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**Success criteria**: The lingjun node is marked as supported in the response. `support: false` is a **blocked** diagnosis — the reason must be reported and the pipeline stopped (this skill does not enroll nodes); it must never be reported as a clean result.

### 2.4 Diagnosis Execution

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel eflo \
  --params '{"instance":"<instance_id>","region":"<region>","start_time":0,"end_time":0,"type":"ocd","ai_roadmap":true,"enable_sysom_link":false,"product":"LINGJUN"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**Success criteria**: Response contains `task_id`

### 2.5 Diagnosis Result

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**Success criteria**: `status` is `Success`, response contains `summary` and `issues` data

---

## 3. Alert Phase Verification

### 3.1 SDK Environment Initialization

```bash
bash scripts/setup-sdk.sh
```

**Success criteria**: Output shows `✅ SDK installation successful`, Python version >= 3.8

### 3.2 Alert Destination Creation (Script Call)

```bash
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-destination.py 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
```

**Success criteria**: stdout outputs `destination_id` (a pure number), stderr outputs `✅ Alert destination created successfully`

### 3.3 Alert Strategy Creation (SDK Script Call)

```bash
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
  --name "aliyun-aes-skills-create-<YYYYMMDDHHmm>" \
  --items "<alert_items>" \
  --clusters "default" \
  --destinations "<destination_id>"
```

**Success criteria**: stdout outputs strategy name, stderr outputs `✅ Alert strategy created successfully`

---

## 4. Observability Verification

**Success criteria**:
- Every OpenAPI CLI command carries `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/<session-id>`
- The `<session-id>` is a 32-character lowercase hexadecimal string and is **identical** across all commands and SDK calls of the session
- SDK script invocations carry `SKILL_SESSION_ID=<session-id>` and do **not** emit the `⚠️ SKILL_SESSION_ID is not set` warning on stderr
- Local/system commands (`aliyun version`, `aliyun configure list`, `aliyun configure set`, `aliyun plugin update`) carry **no** `--user-agent` flag
