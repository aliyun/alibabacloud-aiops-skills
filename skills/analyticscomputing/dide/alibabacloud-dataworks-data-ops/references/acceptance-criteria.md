# Acceptance Criteria: alibabacloud-dataworks-data-ops

**Scenario**: DataWorks task instance operations
**Purpose**: Skill test acceptance standards

---

# Correct CLI Command Patterns

## 1. Product — Verify product name exists

#### ✅ CORRECT
```bash
aliyun dataworks-public list-task-instances --region cn-hangzhou --project-id 12345 --bizdate 1743350400000 --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Wrong product name
aliyun dataworks list-task-instances ...
# Missing --region
aliyun dataworks-public list-task-instances --project-id 12345 --bizdate 1743350400000 --user-agent AlibabaCloud-Agent-Skills
# Missing --user-agent
aliyun dataworks-public list-task-instances --region cn-hangzhou --project-id 12345 --bizdate 1743350400000
```

## 2. Command — Verify API name is correct

#### ✅ CORRECT
```bash
# Use plugin mode format (lowercase hyphen)
aliyun dataworks-public list-task-instances ...
aliyun dataworks-public get-task-instance-log ...
aliyun dataworks-public list-regions ...
```

#### ❌ INCORRECT
```bash
# Use traditional API format (camelCase)
aliyun dataworks-public ListTaskInstances ...
aliyun dataworks-public GetTaskInstanceLog ...
```

## 3. Parameters — Verify parameter names are correct

#### ✅ CORRECT
```bash
# ListTaskInstances required parameters
aliyun dataworks-public list-task-instances \
  --region cn-hangzhou \
  --project-id 12345 \
  --bizdate 1743350400000 \
  --status Failure \
  --user-agent AlibabaCloud-Agent-Skills

# GetTaskInstanceLog required parameters
aliyun dataworks-public get-task-instance-log \
  --region cn-hangzhou \
  --id 67890 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Missing --region
aliyun dataworks-public list-task-instances --project-id 12345 --bizdate 1743350400000 ...
# Wrong parameter name
aliyun dataworks-public list-task-instances --projectId 12345 ...
aliyun dataworks-public list-task-instances --biz_date 1743350400000 ...
```

## 4. Enum Values — Verify enum values are valid

#### ✅ CORRECT
```bash
# Status enum values are correct
--status Failure
--status Success
--status Running
--status NotRun
--status WaitTime
--status WaitResource
```

#### ❌ INCORRECT
```bash
# Wrong status value
--status failed
--status FAILED
--status Error
```

# Security Patterns

## 1. Credential Handling

#### ✅ CORRECT
```bash
# Only check credential status
aliyun configure list
```

#### ❌ INCORRECT
```bash
# Read/print AK/SK
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
echo $ALIBABA_CLOUD_ACCESS_KEY_SECRET

# Ask user to input credentials
read -p "Enter AK: " ak
aliyun configure set --access-key-id $ak
```

## 2. User Agent

#### ✅ CORRECT
```bash
# Every aliyun command includes user-agent
aliyun dataworks-public list-task-instances --region cn-hangzhou --project-id 12345 --bizdate 1743350400000 --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# Missing user-agent
aliyun dataworks-public list-task-instances --region cn-hangzhou --project-id 12345 --bizdate 1743350400000
```
