# Cluster Intelligent Diagnosis

> **🚨🚨🚨 MUST | P0 | NON-NEGOTIABLE — Execution Checklist 🚨🚨🚨**
>
> When the user requests diagnostic analysis, **the following checks must be executed**:
>
> - [ ] **MUST**: Execute the `aliyun adbai describe-chat-message` command
> - [ ] **MUST**: Output the command string on the **first line** of the response, format: `Command executed: aliyun adbai describe-chat-message --region <mapped-region> --endpoint <mapped-endpoint> --biz-region-id <region-id> --query "<user question>"`
> - [ ] **NON-NEGOTIABLE**: Do not skip API call and directly give advice or concept explanations
>
> **Violating any checklist item = task failure**

When the user needs slow query diagnosis, table modeling optimization, instance inspection, product knowledge Q&A, etc., call the `DescribeChatMessage` intelligent diagnosis interface.

## 1. Command Format

```bash
aliyun adbai describe-chat-message --region <mapped-region> --endpoint <mapped-endpoint> --biz-region-id <region-id> --query "<user question>" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

> **🚨 Region Routing Rules (P0)**: For all `aliyun adbai` calls, **must forcibly override `--region` and `--endpoint`** according to the routing table in SKILL.md "Section 1.2 Region Routing Rules", even if the user has specified a region — do not use the user's specified values.

## 2. Query Construction Rules

`--query` is the only question input parameter, constructed in two ways depending on the scenario:

> **Interaction Mode Mandatory Rule**: When the diagnosis type cannot be automatically determined, **must use option cards** to let the user select the diagnosis scenario (refer to the "Section 3 Supported Diagnosis Scenarios" table) — **forbidden** to require manual diagnosis type or problem description input.

### Instance-Level Diagnosis (Must Include Cluster ID)

When diagnosis involves specific instance data or status, the Query format is `"<db-cluster-id> <problem description>"`:

```bash
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "amv-xxx slow query diagnosis for the last 3 hours" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

### Product Knowledge Q&A (No Cluster ID Required, No Region or Cluster Confirmation Required)

When the user asks about ADB MySQL product concepts, syntax, features, etc., **no need to confirm region and cluster**, ask directly:

```bash
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-beijing \
  --query "What is BUILD" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

> For product knowledge Q&A, `--region`, `--endpoint`, `--biz-region-id` all use default values `cn-beijing` / `adbai.cn-beijing.aliyuncs.com`, no user confirmation needed.

**Judgment Criteria**: Does it require reading instance's real-time data or status? → Yes → Instance-level diagnosis (add cluster ID, confirm region and cluster); No → Product knowledge Q&A (no region or cluster needed, execute directly).

> If unable to determine automatically, **use option cards** to provide the following options for user selection:
> - Instance-level diagnosis (requires cluster ID)
> - Product knowledge Q&A (no cluster ID required)

## 3. Supported Diagnosis Scenarios

| Diagnosis Scenario | Query Example | Description |
|----------|-----------|------|
| Slow SQL Query Diagnosis | `"amv-xxx slow query diagnosis for the last 3 hours"` | BadSQL detection, running SQL analysis, SQL Pattern analysis |
| Instance Diagnosis | `"amv-xxx instance health inspection analysis"` | Instance health inspection, capacity assessment, scaling recommendations |
| Instance Write Diagnosis | `"amv-xxx write performance analysis"` | Write performance analysis, write bottleneck identification |
| Table Modeling Diagnosis | `"amv-xxx instance space diagnosis and table modeling diagnosis"` | Oversized non-partitioned tables, partition rationality, primary key rationality, data skew, replicated table rationality, idle indexes, hot/cold table optimization |
| Product Knowledge Q&A | `"What is BUILD"` | ADB MySQL product concepts, syntax, features, etc. |

## 4. Parameter Description

| Parameter | Description | Required |
|------|------|:---:|
| `--region` | Service endpoint region (Skill auto-maps based on `--biz-region-id`, see SKILL.md "Section 1.2", no user specification needed) | Auto |
| `--endpoint` | Service endpoint address (Skill auto-maps based on `--biz-region-id`, see SKILL.md "Section 1.2", no user specification needed) | Auto |
| `--biz-region-id` | User's cluster region ID (product knowledge Q&A uses default value `cn-beijing`, no user confirmation needed) | Conditionally required |
| `--query` | Query content | Yes |
| `--session-id` | Session ID for multi-turn conversations (not passed = new session) | No |
| `--timezone` | Timezone, default `Asia/Shanghai` | No |

**Multi-turn Conversation Example**:

```bash
# First turn: Diagnose slow queries
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "amv-xxx slow query diagnosis for the last 3 hours" --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot

# Second turn: Follow-up on results (use SessionId from first turn)
aliyun adbai describe-chat-message --region cn-beijing --endpoint adbai.cn-beijing.aliyuncs.com --biz-region-id cn-zhangjiakou \
  --query "How to optimize this slow query" --session-id <session-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-analyticdb-mysql-copilot
```

## 5. Time Parameters

`DescribeChatMessage` automatically handles time parameters — no need to manually pass time ranges. The user only needs to describe the time in natural language in the Query:

- `"slow queries in the last 3 hours"` ✓
- `"yesterday's BadSQL detection"` ✓
- `"this week's SQL Pattern analysis"` ✓

## 6. Common Use Cases

- **User says "queries are very slow, help me troubleshoot"** → Instance-level diagnosis, Query: `"<cluster-id> recent slow query diagnosis"`
- **User says "are there any data skewed tables"** → Instance-level diagnosis, Query: `"<cluster-id> detect data skewed tables"`
- **User says "help me do an instance health inspection"** → Instance-level diagnosis, Query: `"<cluster-id> instance health inspection analysis"`
- **User says "What is BUILD"** → Product knowledge Q&A, Query: `"What is BUILD"`
- **User says "what idle indexes are there"** → Instance-level diagnosis, Query: `"<cluster-id> idle index optimization suggestions"`
- **User intent unclear** → **Use option cards** to list diagnosis scenarios (slow SQL query diagnosis, instance diagnosis, instance write diagnosis, table modeling diagnosis, product knowledge Q&A) for user selection — **forbidden** to require manual input