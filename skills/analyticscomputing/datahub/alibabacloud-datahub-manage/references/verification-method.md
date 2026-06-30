# Success Verification Method: DataHub Resource Management

## Overview

Each step in the workflow has a corresponding verification command to confirm successful execution.

---

## Step 1: Verify Project Creation

**Expected Outcome**: Project exists and is accessible.

```bash
aliyun datahub get-project \
  --region <region> \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: Response returns project details with matching `ProjectName` and `Comment`.

---

## Step 2: Verify Topic Creation

**Expected Outcome**: Topic exists under the project with correct configuration.

```bash
aliyun datahub get-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: Response contains:
- `RecordType` matches the configured type (BLOB or TUPLE)
- `ShardCount` matches the configured value
- `Lifecycle` matches the configured value
- For TUPLE topics: `RecordSchema` contains the defined fields

---

## Step 3: Verify Subscription Creation

**Expected Outcome**: Subscription exists under the topic.

```bash
aliyun datahub get-subscription \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --subscription-id <subscription-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: Response returns subscription details with matching `Application` and `Comment`.

---

## Step 4: Verify Topic Update

**Expected Outcome**: Topic description is updated.

```bash
aliyun datahub get-topic \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: `Comment` field reflects the updated description.

---

## Step 5: Verify Resource Cleanup

### 5.1 Verify Subscription Deleted

```bash
aliyun datahub list-subscriptions \
  --region <region> \
  --project-name <project-name> \
  --topic-name <topic-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: The deleted subscription ID no longer appears in the list.

### 5.2 Verify Topic Deleted

```bash
aliyun datahub list-topics \
  --region <region> \
  --project-name <project-name> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: The deleted topic no longer appears in the list.

### 5.3 Verify Project Deleted

```bash
aliyun datahub list-projects \
  --region <region> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/<session-id>
```

**Success Indicator**: The deleted project no longer appears in the list.
