# Acceptance Criteria: alibabacloud-analyticdb-mysql-copilot

**Scenario**: ADB MySQL Operations & Diagnosis
**Purpose**: Skill test acceptance criteria

---

# Correct CLI Command Patterns

## 1. Product — Verify Product Name Exists

#### ✅ CORRECT
```bash
aliyun adb describe-db-clusters --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-hangzhou --query "What is BUILD" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

#### ❌ INCORRECT
```bash
aliyun adbx describe-db-clusters --biz-region-id cn-hangzhou  # Product name does not exist
aliyun ADB describe-db-clusters --biz-region-id cn-hangzhou   # Product name should be lowercase
aliyun adb describe-chat-message                       # Product name mismatch, should be adbai
```

## 2. Command — Verify Action Exists

#### ✅ CORRECT
```bash
aliyun adb describe-db-clusters --biz-region-id cn-hangzhou --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-hangzhou --query "What is BUILD" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

#### ❌ INCORRECT
```bash
aliyun adb GetDBClusters --biz-region-id cn-hangzhou   # Action name incorrect
aliyun adb list-clusters --biz-region-id cn-hangzhou   # Action name incorrect
aliyun adbai describe-chat --biz-region-id cn-hangzhou # Action name incomplete
```

## 3. Parameters — Verify Parameter Names Exist

#### ✅ CORRECT
```bash
# Cluster management (aliyun adb): parameters use camelCase naming
aliyun adb describe-db-clusters --biz-region-id cn-hangzhou --region cn-hangzhou --page-number 1 --page-size 100 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
aliyun adb describe-db-cluster-attribute --biz-region-id cn-hangzhou --region cn-hangzhou --db-cluster-id am-xxx --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Intelligent diagnosis (aliyun adbai)
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-hangzhou --query "What is BUILD" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

#### ❌ INCORRECT
```bash
aliyun adb describe-db-clusters --RegionId cn-hangzhou          # Parameter name format incorrect (should use --biz-region-id)
aliyun adb describe-db-cluster-attribute --biz-region-id cn-hangzhou --region cn-hangzhou   # Missing --db-cluster-id
aliyun adb describe-db-cluster-attribute --db-cluster-id am-xxx     # Missing --biz-region-id, --region (this Skill mandates them)
aliyun adbai describe-chat-message --biz-region-id cn-hangzhou     # Missing --region, --endpoint
```

## 4. Parameter Value Formats — Verify Parameter Value Format

#### ✅ CORRECT (Query Format)
```bash
# Instance diagnosis: Query includes cluster ID + natural language question
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-hangzhou --query "am-xxx slow query diagnosis for the last 3 hours" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Product knowledge Q&A: Query asks directly
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-hangzhou --query "What is BUILD" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

#### ❌ INCORRECT (Query Format)
```bash
# Instance diagnosis Query missing cluster ID
aliyun adbai describe-chat-message --biz-region-id cn-hangzhou --query "slow query diagnosis for the last 3 hours"  # Missing --region, --endpoint
```

---

# Correct Response Output Patterns

## 1. Command String Must Be at the Beginning of the Response

#### ✅ CORRECT
```
Command executed: `aliyun adb describe-db-clusters --biz-region-id cn-hangzhou --region cn-hangzhou`

Query complete! There are 2 ADB MySQL clusters in the Hangzhou region...
```

#### ❌ INCORRECT
```
Query complete! There are 2 clusters in the Hangzhou region... (command string not output)

I called the API to query the cluster list... (complete command not output)

Cluster list below... Command: aliyun adb describe-db-clusters... (command at the end)
```

## 2. Must Execute API Calls

#### ✅ CORRECT
- User asks "view cluster list" → Execute `describe-db-clusters`
- User asks "data skew diagnosis", "BadSQL detection", "slow query diagnosis", "instance health inspection" and other diagnosis questions → Execute `describe-chat-message`

#### ❌ INCORRECT
- User asks "view cluster list" → Directly output documentation content, not calling API
- User asks "data skew diagnosis" → Only explain data skew concept, not calling API
- User asks "BadSQL detection" → Give general optimization suggestions, not calling API

---

# Correct Product Boundary Judgment

## 1. Cluster ID Identification

#### ✅ CORRECT
- `am-xxx` or `amv-xxx` → ADB MySQL, cluster management uses `aliyun adb`, intelligent diagnosis uses `aliyun adbai`
- No need to verify ownership through other product APIs

#### ❌ INCORRECT
- `am-xxx` → Use `aliyun rds` to verify → Failure
- `am-xxx` → Use `aliyun polardb` to verify → Failure
- `am-xxx` → Use `aliyun adb describe-chat-message` → Failure (product name mismatch, should be adbai)

## 2. Product Boundary Notification

#### ✅ CORRECT
- User mentions Elasticsearch → Inform "This Skill only applies to ADB MySQL"
- User mentions RDS MySQL → Inform "This Skill only applies to ADB MySQL"

#### ❌ INCORRECT
- User mentions Elasticsearch → Attempt to use `aliyun adb` command → Failure