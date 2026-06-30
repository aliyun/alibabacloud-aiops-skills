# Acceptance Criteria: alibabacloud-datahub-manage

**Scenario**: DataHub Resource Management (Full Lifecycle)
**Purpose**: Skill testing acceptance criteria for CLI command patterns and workflow correctness

---

# Correct CLI Command Patterns

## 1. Product — verify product subcommand exists

#### ✅ CORRECT
```bash
aliyun datahub list-projects
```

#### ❌ INCORRECT
```bash
aliyun dh list-projects        # Wrong product name
aliyun data-hub list-projects  # Wrong product name format
```

---

## 2. Command — verify action exists under the product

#### ✅ CORRECT
```bash
aliyun datahub create-project
aliyun datahub create-topic
aliyun datahub create-subscription
aliyun datahub list-projects
aliyun datahub list-topics
aliyun datahub list-subscriptions
aliyun datahub get-project
aliyun datahub get-topic
aliyun datahub get-subscription
aliyun datahub update-project
aliyun datahub update-topic
aliyun datahub delete-project
aliyun datahub delete-topic
aliyun datahub delete-subscription
```

#### ❌ INCORRECT
```bash
aliyun datahub CreateProject         # Wrong: uses PascalCase API format instead of plugin mode
aliyun datahub create_project        # Wrong: uses underscore instead of hyphen
aliyun datahub remove-project        # Wrong: action does not exist
aliyun datahub update-subscription   # Wrong: action does not exist for subscriptions
```

---

## 3. Parameters — verify each parameter name exists for the command

### 3.1 create-project

#### ✅ CORRECT
```bash
aliyun datahub create-project \
  --project-name my_project \
  --comment "My project description" \
  --region cn-hangzhou
```

#### ❌ INCORRECT
```bash
aliyun datahub create-project \
  --name my_project              # Wrong: parameter is --project-name, not --name
  --description "My project"     # Wrong: parameter is --comment, not --description
```

### 3.2 create-topic

#### ✅ CORRECT
```bash
aliyun datahub create-topic \
  --project-name my_project \
  --topic-name my_topic \
  --shard-count 4 \
  --lifecycle 7 \
  --record-type BLOB \
  --comment "Topic description"
```

#### ❌ INCORRECT
```bash
aliyun datahub create-topic \
  --project my_project        # Wrong: parameter is --project-name
  --topic my_topic            # Wrong: parameter is --topic-name
  --shards 4                  # Wrong: parameter is --shard-count
  --ttl 7                     # Wrong: parameter is --lifecycle
  --type BLOB                 # Wrong: parameter is --record-type
```

### 3.3 create-subscription

#### ✅ CORRECT
```bash
# Without explicit subscription-id (auto-generated)
aliyun datahub create-subscription \
  --project-name my_project \
  --topic-name my_topic \
  --application "My consumer app" \
  --comment "Subscription description"

# With explicit subscription-id
aliyun datahub create-subscription \
  --project-name my_project \
  --topic-name my_topic \
  --application "My consumer app" \
  --comment "Subscription description" \
  --subscription-id my_sub_001
```

#### ❌ INCORRECT
```bash
aliyun datahub create-subscription \
  --project-name my_project \
  --topic-name my_topic \
  --app-name "My app"          # Wrong: parameter is --application
  --desc "Description"          # Wrong: parameter is --comment
  --sub-id my_sub              # Wrong: parameter is --subscription-id
```

---

## 4. Parameter Values — verify enum and format constraints

### 4.1 record-type (create-topic)

#### ✅ CORRECT
```bash
--record-type BLOB
--record-type TUPLE
```

#### ❌ INCORRECT
```bash
--record-type blob      # Wrong: must be uppercase
--record-type Blob      # Wrong: must be uppercase
--record-type STRING    # Wrong: invalid value, only BLOB or TUPLE
```

### 4.2 subscription-id format

#### ✅ CORRECT
```bash
--subscription-id my_sub_001        # Lowercase letter start, 4-40 chars
--subscription-id data_consumer_01  # Valid format
```

#### ❌ INCORRECT
```bash
--subscription-id My_Sub_001       # Wrong: must start with lowercase letter, no uppercase
--subscription-id 123sub           # Wrong: must start with lowercase letter
--subscription-id ab               # Wrong: too short (min 4 characters)
```

### 4.3 record-schema format (create-topic with TUPLE)

#### ✅ CORRECT
```bash
# JSON object format (recommended)
--record-schema '{"fields":[{"name":"field1","type":"STRING","notnull":"false"}]}'

# Escaped string format (also supported)
--record-schema '"{\"fields\":[{\"name\":\"field1\",\"type\":\"STRING\",\"notnull\":\"false\"}]}"'
```

#### ❌ INCORRECT
```bash
--record-schema '[{"name":"field1","type":"STRING"}]'   # Wrong: missing "fields" wrapper object
--record-schema '{"name":"field1","type":"STRING"}'      # Wrong: must be {"fields":[...]} array structure
--record-schema '{"fields":[{"name":"f1","type":"TEXT"}]}'  # Wrong: unsupported type (valid: STRING, BIGINT, INTEGER, SMALLINT, TINYINT, FLOAT, DOUBLE, DECIMAL, BOOLEAN, TIMESTAMP, JSON)
```

---

## 5. Workflow Order — verify resource dependency chain

#### ✅ CORRECT (Creation Order)
```
1. create-project → 2. create-topic → 3. create-subscription
```

#### ✅ CORRECT (Deletion Order — reverse)
```
1. delete-subscription → 2. delete-topic → 3. delete-project
```

#### ❌ INCORRECT
```
# Deleting project before cleaning topics/subscriptions
1. delete-project  # Will fail — must delete topics first
```

---

## 6. Pre-deletion Checks

#### ✅ CORRECT
```bash
# Before deleting a topic, list subscriptions to ensure none exist
aliyun datahub list-subscriptions --project-name my_project --topic-name my_topic --region cn-hangzhou

# Before deleting a project, list topics to ensure none exist
aliyun datahub list-topics --project-name my_project --region cn-hangzhou
```

#### ❌ INCORRECT
```bash
# Deleting topic without checking for active subscriptions
aliyun datahub delete-topic --project-name my_project --topic-name my_topic --region cn-hangzhou
# May fail if subscriptions still exist
```

---

## 7. User-Agent — verify observability compliance

#### ✅ CORRECT
```bash
aliyun datahub create-project \
  --project-name my_project \
  --comment "Demo" \
  --region cn-hangzhou \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

#### ❌ INCORRECT
```bash
# Missing --user-agent flag entirely
aliyun datahub create-project --project-name my_project --comment "Demo" --region cn-hangzhou

# Using export env var approach (deprecated)
export ALIBABA_CLOUD_USER_AGENT=AlibabaCloud-Agent-Skills/alibabacloud-datahub-manage/session123
```
