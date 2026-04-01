# Acceptance Criteria: alibabacloud-analyticdb-mysql-copilot

**Scenario**: ADB MySQL 运维诊断
**Purpose**: Skill 测试验收标准

---

# 正确的 CLI 命令模式

## 1. Product — 验证产品名存在

#### ✅ CORRECT
```bash
aliyun adb DescribeDBClusters --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun adbx DescribeDBClusters --RegionId cn-hangzhou  # 产品名不存在
aliyun ADB DescribeDBClusters --RegionId cn-hangzhou   # 产品名应小写
```

## 2. Command — 验证 Action 存在

#### ✅ CORRECT
```bash
aliyun adb describe-db-clusters --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
aliyun adb DescribeDBClusters --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun adb GetDBClusters --RegionId cn-hangzhou   # Action 名称错误
aliyun adb list-clusters --RegionId cn-hangzhou   # Action 名称错误
```

## 3. Parameters — 验证参数名存在

#### ✅ CORRECT
```bash
aliyun adb DescribeDBClusters --RegionId cn-hangzhou --PageNumber 1 --PageSize 100 --user-agent AlibabaCloud-Agent-Skills
aliyun adb DescribeDBClusterAttribute --RegionId cn-hangzhou --DBClusterId am-xxx --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun adb DescribeDBClusters --region-id cn-hangzhou          # 参数名格式错误（应使用驼峰）
aliyun adb DescribeDBClusterAttribute --RegionId cn-hangzhou   # 缺少 --DBClusterId
aliyun adb DescribeDBClusterAttribute --DBClusterId am-xxx     # 缺少 --RegionId（本 Skill 强制要求）
```

## 4. Enum Values — 验证枚举值有效

#### ✅ CORRECT
```bash
# DescribeAvailableAdvices --PageSize
aliyun adb DescribeAvailableAdvices --RegionId cn-hangzhou --DBClusterId am-xxx \
  --AdviceDate 20260322 --PageNumber 1 --PageSize 30 --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills

# DescribeInclinedTables --TableType
aliyun adb DescribeInclinedTables --RegionId cn-hangzhou --DBClusterId am-xxx \
  --TableType FactTable --PageSize 30 --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
# PageSize 只允许 30/50/100
aliyun adb DescribeAvailableAdvices --PageSize 20   # 无效值

# AdviceDate 格式错误
aliyun adb DescribeAvailableAdvices --AdviceDate 2026-03-22   # 应为 20260322
aliyun adb DescribeAvailableAdvices --AdviceDate "2026-03-22T00:00:00Z"  # 格式错误
```

## 5. Parameter Value Formats — 验证参数值格式

#### ✅ CORRECT (时间格式)
```bash
# ISO 8601 UTC（用于 Performance/BadSQL/SQLPatterns）
aliyun adb DescribeDBClusterPerformance --StartTime 2026-03-20T07:00Z --EndTime 2026-03-20T08:00Z

# Unix 毫秒（用于 DescribeDiagnosisRecords）
aliyun adb DescribeDiagnosisRecords --StartTime 1742475600000 --EndTime 1742479200000

# QueryCondition JSON
aliyun adb DescribeDiagnosisRecords --QueryCondition '{"Type":"status","Value":"running"}'
```

#### ❌ INCORRECT (时间格式)
```bash
# 时间格式混用
aliyun adb DescribeDiagnosisRecords --StartTime 2026-03-20T07:00Z   # 应为 Unix 毫秒
aliyun adb DescribeDBClusterPerformance --StartTime 1742475600000   # 应为 ISO 8601

# QueryCondition 格式错误
aliyun adb DescribeDiagnosisRecords --QueryCondition "status=running"  # 应为 JSON
```

## 6. User-Agent Flag — 验证 --user-agent 存在

#### ✅ CORRECT
```bash
aliyun adb DescribeDBClusters --RegionId cn-hangzhou --user-agent AlibabaCloud-Agent-Skills
```

#### ❌ INCORRECT
```bash
aliyun adb DescribeDBClusters --RegionId cn-hangzhou   # 缺少 --user-agent
```

---

# 正确的回复输出模式

## 1. 命令字符串必须在回复开头

#### ✅ CORRECT
```
执行命令：`aliyun adb DescribeDBClusters --RegionId cn-hangzhou`

查询完成！杭州区域共有 2 个 ADB MySQL 集群...
```

#### ❌ INCORRECT
```
查询完成！杭州区域共有 2 个集群... （未输出命令字符串）

我调用了API查询集群列表... （未输出完整命令）

集群列表如下... 命令：aliyun adb DescribeDBClusters... （命令在末尾）
```

## 2. 必须执行 API 调用

#### ✅ CORRECT
- 用户问"查看集群列表" → 执行 `DescribeDBClusters`
- 用户问"数据倾斜诊断" → 执行 `DescribeInclinedTables`
- 用户问"BadSQL检测" → 执行 `DescribeBadSqlDetection`

#### ❌ INCORRECT
- 用户问"查看集群列表" → 直接输出文档内容，不调用 API
- 用户问"数据倾斜诊断" → 仅解释数据倾斜概念，不调用 API
- 用户问"BadSQL检测" → 给出通用优化建议，不调用 API

---

# 正确的产品边界判断

## 1. 集群 ID 识别

#### ✅ CORRECT
- `am-xxx` 或 `amv-xxx` → ADB MySQL，使用 `aliyun adb` 命令
- 无需通过其他产品 API 验证归属

#### ❌ INCORRECT
- `am-xxx` → 使用 `aliyun rds` 验证 → 失败
- `am-xxx` → 使用 `aliyun polardb` 验证 → 失败

## 2. 产品边界告知

#### ✅ CORRECT
- 用户提到 Elasticsearch → 告知"本 Skill 仅适用于 ADB MySQL"
- 用户提到 RDS MySQL → 告知"本 Skill 仅适用于 ADB MySQL"

#### ❌ INCORRECT
- 用户提到 Elasticsearch → 尝试使用 `aliyun adb` 命令 → 失败