# Success Verification: alibabacloud-aes-ack-pod-performance-profiling

This document describes the success verification methods for each phase. Non-system `aliyun` CLI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling`. System commands (`configure`, `version`, `plugin`) **MUST NOT** use the `--user-agent` flag.

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

### 2.1 Cluster Information Retrieval

```bash
aliyun cs GET /clusters/<cluster_id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

**Success criteria**: Response contains `region_id`, `name`, and `state` is `running`

### 2.2 SysOM Role Initialization

```bash
aliyun sysom initial-sysom --check-only false --source aes-skills --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

**Success criteria**: No error returned

### 2.3 Diagnosis Execution

> **⚠️ `description` sanitization (mandatory)**: MUST match `^[a-zA-Z0-9_-]*$`. Replace spaces with `_` and strip non-ASCII characters before calling. Otherwise `Sysom.InvalidParameter` is returned.

```bash
aliyun sysom invoke-diagnosis \
  --service-name ocd \
  --channel ecs \
  --params '{"product":"ACK","region":"<region_id>","instance":"ack-<cluster_id>","cluster_id":"<cluster_id>","namespace":"<namespace>","pod":"<pod_name>","description":"<sanitized_description>","start_time":0,"end_time":0,"enable_diagnosis":true}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

**Success criteria**: Response contains `task_id`

### 2.4 Diagnosis Result

```bash
aliyun sysom get-diagnosis-result \
  --task-id <task_id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-ack-pod-performance-profiling
```

**Success criteria**: `status` is `Success`, response contains `summary` and `issues` data
