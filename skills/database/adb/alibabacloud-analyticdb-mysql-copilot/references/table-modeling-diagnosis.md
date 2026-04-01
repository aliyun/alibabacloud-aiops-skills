# ADB MySQL 实例空间诊断

> **公共规则**
> - **RegionId 与 DBClusterId**：凡命令中含 `--DBClusterId` 的，必须同时传 `--RegionId`
> - **DBClusterId 提取规则**：识别以 `am-` 或 `amv-` 开头的子串，从前缀起严格截取前 20 位，剔除冒号、端口、域名后缀等
> - **通用单位换算**：将字节按阶梯换算：>= 1024^4 为 TB；>= 1024^3 为 GB；>= 1024^2 为 MB；>= 1024 为 KB，保留两位小数
> - **展示约束**：表格中最多展示 5 条记录；必须使用 Markdown 表格，严禁使用列表展示详细信息

## 一、诊断流程

**并行执行**以下 7 项诊断，全部完成后汇总结果。

### 1. 过大非分区表诊断

```bash
aliyun adb DescribeOversizeNonPartitionTableInfos --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> --PageSize 30 --Lang zh --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：非分区表 DML 操作容易触发全表 Build，占用过多临时空间导致磁盘飙升，降低实例性能。
**优化建议**：调整为分区表并迁移数据（需备份）。

| 输出字段 | 含义 |
|----------|------|
| `data.Tables[].SchemaName` | 数据库名 |
| `data.Tables[].TableName` | 表名 |
| `data.Tables[].DataSize` | 表数据量 (Bytes) |
| `data.Tables[].RowCount` | 表行数 |

### 2. 表分区合理性诊断

```bash
aliyun adb DescribeTablePartitionDiagnose --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> --PageSize 5 --Lang zh --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：分区过大导致 Build 任务耗时长；分区过小消耗内存并降低查询性能。
**优化建议**：重新设计分区字段或粒度。

| 输出字段 | 含义 |
|----------|------|
| `data.Items[].SchemaName` | 数据库名 |
| `data.Items[].TableName` | 表名 |
| `data.Items[].TotalSize` | 表数据量 (Bytes) |

### 3. 表主键字段合理性诊断

```bash
aliyun adb DescribeExcessivePrimaryKeys --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> --PageSize 30 --Lang zh --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：主键过多增加存储开销和磁盘锁定风险，降低写入性能。
**优化建议**：重新设计并精简主键字段（需备份）。

| 输出字段 | 含义 |
|----------|------|
| `data.Tables[].SchemaName` | 数据库名 |
| `data.Tables[].TableName` | 表名 |
| `data.Tables[].PrimaryKeyCount` | 主键包含字段数 |
| `data.Tables[].ColumnCount` | 全表总字段数 |
| `data.Tables[].PrimaryKeyIndexSize` | 主键物理空间大小 (Bytes) |

### 4. 表数据倾斜诊断

```bash
aliyun adb DescribeInclinedTables --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> --TableType FactTable --PageSize 30 --Lang zh --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：数据倾斜导致资源使用不均衡，影响查询性能，极易引发集群锁定和查询长尾。
**优化建议**：调整倾斜表的分布键（需备份）。

| 输出字段 | 含义 |
|----------|------|
| `data.Items.Table[].Schema` | 数据库名 |
| `data.Items.Table[].Name` | 表名 |
| `data.Items.Table[].Size` | 倾斜的 Shard 数 |
| `data.Items.Table[].TotalSize` | 表数据量 (Bytes) |

### 5. 复制表合理性诊断

```bash
aliyun adb DescribeInclinedTables --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> --TableType DimensionTable --PageSize 30 --Lang zh --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：复制表单表行数过多会降低实例整体写入性能。
**优化建议**：将超限的复制表调整为普通表（需备份）。

| 输出字段 | 含义 |
|----------|------|
| `data.Items.Table[].Schema` | 数据库名 |
| `data.Items.Table[].Name` | 表名 |
| `data.Items.Table[].TotalSize` | 表数据量 (Bytes) |
| `data.Items.Table[].RowCount` | 表行数 |

### 6. 空闲索引优化建议

```bash
aliyun adb DescribeAvailableAdvices --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> \
  --AdviceDate <yyyyMMdd> --AdviceType INDEX --PageNumber 1 --PageSize 30 --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：冗余索引占用磁盘空间，增加存储成本，拖慢数据写入速度。
**优化建议**：前往控制台【空间诊断 > 索引诊断】执行清理。

| 输出字段 | 含义 |
|----------|------|
| `data.Items[].SchemaName` | 数据库名 |
| `data.Items[].TableName` | 表名 |
| `data.Items[].IndexFields` | 索引字段 |
| `data.Items[].Reason` | 具体优化建议 |
| `data.Items[].Benefit` | 预期优化收益 |

> **注意**：`--AdviceDate` 为 `yyyyMMdd` 格式（如 `20260322`），建议填 T-1 或更早。

### 7. 冷热表优化建议

```bash
aliyun adb DescribeAvailableAdvices --version 2021-12-01 --RegionId <region-id> --DBClusterId <cluster-id> \
  --AdviceDate <yyyyMMdd> --AdviceType TIERING --PageNumber 1 --PageSize 30 --Lang zh \
  --user-agent AlibabaCloud-Agent-Skills
```

**风险说明**：最近 15 天未访问且访问率小于 1% 的热表，导致整体成本过高。
**优化建议**：开启冷热分层存储，将低频访问的热表转换为冷表。

| 输出字段 | 含义 |
|----------|------|
| `data.Items[].SchemaName` | 数据库名 |
| `data.Items[].TableName` | 表名 |
| `data.Items[].Reason` | 具体优化建议 |
| `data.Items[].Benefit` | 预期优化收益 |

## 二、诊断报告模板

```markdown
# 🚀 ADB MySQL 实例健康巡检报告

## 1. 基本信息
- **分析实例**: `{cluster-id}`
- **报告日期**: `{report-date}`

## 2. 诊断概览

| 诊断维度 | 问题数 | 状态 | 详情摘要 |
| :--- | :--- | :--- | :--- |
| **过大非分区表诊断** | {count1} | {✅/🔴} | {前1~3条：库.表、物理容量、行数} |
| **表分区合理性诊断** | {count2} | {✅/⚠️} | {前1~3条：库.表、物理容量} |
| **主键字段合理性诊断** | {count3} | {✅/⚠️} | {前1~3条：库.表、主键/总字段数} |
| **表数据倾斜诊断** | {count4} | {✅/🔴} | {前1~3条：库.表、数据量、倾斜情况} |
| **复制表合理性诊断** | {count5} | {✅/⚠️} | {前1~3条：库.表、物理容量、行数} |
| **空闲索引优化建议** | {count6} | {💡} | {前1~3条：库.表、索引字段、建议} |
| **冷热表优化建议** | {count7} | {💡} | {前1~3条：库.表、建议} |

状态列：问题数 = 0 填 ✅，> 0 填该维度等级符号。

## 3. 诊断详情
{各诊断项分段展示，每项单独成小节，包含完整数据表格及修复动作}
```