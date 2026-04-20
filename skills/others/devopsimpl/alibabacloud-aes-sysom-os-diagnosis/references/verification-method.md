# Success Verification: alibabacloud-aes-sysom-os-diagnosis

This document describes the success verification methods for each phase. All `aliyun` CLI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills`.

---

## 1. Environment Setup Verification

### 1.1 CLI Version

```bash
aliyun version --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Version >= 3.3.1

### 1.2 Credential Configuration

```bash
aliyun configure list --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Output contains a valid profile (AK, STS, or OAuth identity)

---

## 2. Diagnosis Phase Verification

### 2.1 Cloud Assistant Online Check

```bash
aliyun ecs describe-cloud-assistant-status \
  --biz-region-id <region> \
  --instance-id <instance_id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: `CloudAssistantStatus` is `"true"` in the response

### 2.2 SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: No error returned

### 2.3 Instance Support Check

```bash
aliyun sysom check-instance-support \
  --instances <instance_id> \
  --biz-region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Instance is marked as supported in the response

### 2.4 Diagnosis Execution

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"instanceId":"<instance_id>","region":"<region>","enableDiagnosis":true,"startTime":0,"endTime":0,"aiRoadmap":true,"enableSysomLink":false}' \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Response contains `task_id`

### 2.5 Diagnosis Result

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: `status` is `Success`, response contains `summary` and `issues` data

---

## 3. Enrollment Phase Verification

### 3.1 Instance Enrollment

```bash
aliyun sysom install-agent \
  --instances instance=<instance_id> region=<region> \
  --install-type InstallAndUpgrade \
  --agent-id 74a86327-3170-412c-8e67-da3389ec56a9 \
  --agent-version 3.12.0-1 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: No error returned

### 3.2 Instance Status Polling

```bash
aliyun sysom list-instance-status \
  --instance <instance_id> \
  --biz-region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: Instance `status` is `running`

### 3.3 Cluster Enrollment

```bash
aliyun sysom install-agent-for-cluster \
  --cluster-id <cluster_id> \
  --agent-id 74a86327-3170-412c-8e67-da3389ec56a9 \
  --agent-version 3.12.0-1 \
  --config-id 8gj86wrt7-3170-412c-8e67-da3389ecg6a9 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: No error returned

### 3.4 Cluster Status Polling

```bash
aliyun sysom list-clusters \
  --cluster-id <cluster_id> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Success criteria**: `cluster_status` is `Running`

---

## 4. Alert Phase Verification

### 4.1 SDK Environment Initialization

```bash
bash scripts/setup-sdk.sh
```

**Success criteria**: Output shows `✅ SDK installation successful`, Python version >= 3.8

### 4.2 Alert Destination Creation (Script Call)

```bash
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py 'https://oapi.dingtalk.com/robot/send?access_token=xxx'
```

**Success criteria**: stdout outputs `destination_id` (a pure number), stderr outputs `✅ Alert destination created successfully`

### 4.3 Alert Strategy Creation (SDK Script Call)

```bash
.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
  --name "aliyun-aes-skills-create-<YYYYMMDDHHmm>" \
  --items "<alert_items>" \
  --clusters "default" \
  --destinations "<destination_id>"
```

**Success criteria**: stdout outputs strategy name, stderr outputs `✅ Alert strategy created successfully`
