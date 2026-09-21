# 数据校验接口枚举值速查

本文档仅收录 API 请求/响应参数中直接涉及的枚举，按 **状态类 → 配置类** 组织。

> 所有枚举源自 `data-validation-core` 模块 `com.aliyun.lhm.enums` 包。

---

## 1. 状态类枚举

### 1.1 checkType — 校验规则类型

**枚举类**: `CheckTypeEnums` · **参数名**: `checkType` · **类型**: Integer (ordinal)

| 值 | 枚举名 | 中文 | 说明 |
|----|--------|------|------|
| 0 | ByCount | 数据量比对 | 对比源/目标表行数 |
| 1 | ByMetric | 指标比对 | 对比 SUM/AVG/MIN/MAX 等聚合指标 |
| 2 | ByQuantity | 弱内容对比 | MD5/CRC32 校验和比对 |

**涉及接口**: `AddDataCheckTask`(req)、`AddDataCheckConfig`(req)、`ExecDataCheckSaveTask`(req)、`ListDataCheckReport`(req 过滤)

---

### 1.2 checkResult — 校验结果

**枚举类**: `CheckResultEnums` · **参数名**: `checkResult` · **类型**: Integer (ordinal)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | NO_RECORD | 无记录 |
| 1 | PASSED | 通过 |
| 2 | FAILED | 不通过 |

**涉及接口**: `ListDataCheckTaskHistory`(req 过滤, resp)、`ListDataCheckReport`(req 过滤, resp)、`ListDataCheckReportStep`(req 过滤, resp)、`ListDataCheckColumnResults`(req 过滤, resp)

---

### 1.3 execStatus — 批次执行状态

**枚举类**: `ExecStatus` · **参数名**: `execStatus` · **类型**: Integer (ordinal)

| 值 | 枚举名 | 中文 | 终止态 | 说明 |
|----|--------|------|--------|------|
| 0 | TODO | 待运行 | ✗ | 批次已创建但未触发 |
| 1 | RUNNING | 运行中 | ✗ | 可调用 stop 终止 |
| 2 | STOPPED | 终止运行 | ✓ | 用户主动终止 |
| 3 | FAILED | 运行失败 | ✓ | 可查看 errMessage |
| 4 | FINISHED | 运行完成 | ✓ | 可查看报告 |

**状态流转**:

```
TODO(0) ──run──▶ RUNNING(1) ──完成──▶ FINISHED(4)
                   │
                   ├──stop──▶ STOPPED(2)
                   └──异常──▶ FAILED(3) ──重跑──▶ TODO(0)
```

**涉及接口**: `ListDataCheckTaskHistory`(req 过滤, resp)

---

### 1.4 jobStatus — 作业/Step 状态

**枚举类**: `JobStatus` · **参数名**: `jobStatus` / `status` · **类型**: Byte (status 字段)

| 值 | 枚举名 | 中文 | type | 说明 |
|----|--------|------|------|------|
| 0 | INIT | 创建 | 0(未结束) | 初始状态 |
| 1 | RUNNING | 运行中 | 0(未结束) | 正在执行 |
| 2 | FINISHED | 运行完成 | 1(已终止) | 成功完成 |
| 3 | STOPPED | 停止 | 1(已终止) | 被终止 |
| 4 | FAIL | 执行失败 | 1(已终止) | 执行异常 |
| 6 | READY | 就绪 | 0(未结束) | 已进入校验执行队列 |
| 7 | SKIPPED | 跳过 | 1(已终止) | 条件不满足，跳过 |

> **type 字段**: `0`=未结束（可继续流转），`1`=已终止（终态）。
> 终态集合: `{FINISHED, STOPPED, FAIL, SKIPPED}`

**状态流转**:

```
INIT(0) ──▶ READY(6) ──▶ RUNNING(1) ──▶ FINISHED(2)
                           │
                           ├──▶ STOPPED(3)
                           ├──▶ FAIL(4)
                           └──▶ SKIPPED(7)
```

**涉及接口**: `ListDataCheckReport`(req 过滤, resp)、`ListDataCheckReportStep`(req 过滤, resp)

---

### 1.5 isConsistent — 一致性状态

**枚举类**: `ConsistentStatus` · **参数名**: `isConsistent` · **类型**: Byte (status 字段)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | IN_CONSISTENT | 不一致 |
| 1 | CONSISTENT | 一致 |

**状态流转**:

```
null ──▶ IN_CONSISTENT(0) (终态)
null ──▶ CONSISTENT(1)    (终态)
```

**涉及接口**: `ListDataCheckReportStep`(resp)、`ListDataCheckColumnResults`(resp)、`GetStepResultOverview`(resp)

---

### 1.6 reportStatus — 报告生成状态

**枚举类**: `ReportStatusEnums` · **参数名**: `reportStatus` · **类型**: Byte (status 字段)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | NO_RECORD | 无记录 |
| 1 | GENERATING | 生成中 |
| 2 | DONE | 已完成 |
| 3 | FAIL | 生成失败 |

**涉及接口**: `GetDataCheckReportOverview`(resp)、`GetDataCheckReportStatus`(resp)、`ExecDataCheckGenerateReport`(前置检查)

---

## 2. 配置类枚举

### 2.1 taskMode — 任务创建方式

**枚举类**: `CheckCreateModeEnums` · **参数名**: `taskMode` · **类型**: Integer (code 字段)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | By_Table | 逐表精细化创建 |
| 1 | By_Batch | 同模式批量创建 |

**涉及接口**: `AddDataCheckTask`(req)

---

### 2.2 executeType — 执行类型

**枚举类**: `CheckExecuteTypeEnum` · **参数名**: `executeType` · **类型**: Integer (code 字段)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | MANUAL | 手动执行（默认） |
| 1 | SCHEDULE | 定时执行 |

**涉及接口**: `ExecDataCheckSaveTask`(req)

---

### 2.3 scopeFilterType — 范围过滤类型

**枚举类**: `ScopeFilterTypeEnums` · **参数名**: `scopeFilter.type` · **类型**: Integer (code 字段)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | NONO | 不筛选（默认） |
| 1 | LAST_N_PARTITION | 最近 N 个分区 |
| 2 | LAST_N_DAY | 最近 N 天的分区 |
| 3 | BY_MODIFY_TIME | 按修改时间筛选 |
| 4 | BY_CREATE_TIME | 按创建时间筛选 |

**涉及接口**: `ExecDataCheckSaveTask`(req, scopeFilter 子项)

---

### 2.4 runFailType — 重跑失败类型

**枚举类**: `RunFailTypeEnum` · **参数名**: `runFailType` · **类型**: Integer (code 字段)

| 值 | 枚举名 | 中文 |
|----|--------|------|
| 0 | ONLY_FAIL | 仅重跑失败的表 |
| 1 | FAIL_AND_NOT_PASS | 重跑失败 + 不通过的表 |
| 2 | FAIL_AND_STOP | 重跑失败 + 被终止的表 |

**涉及接口**: `ExecDataCheckRunFailed`(req)

---

### 2.5 布尔型标志字段

接口中使用 `0` / `1` 整数值：

| 值 | 含义 | 涉及参数 | 涉及接口 |
|----|------|---------|---------|
| 0 | 否 | isFullTableCount, isSkipped, startImmediately, isScheduled | AddDataCheckConfig, ExecDataCheckSaveTask |
| 1 | 是 | 同上 | 同上 |

---

### 2.6 checkTemplateId — 内置校验模板

**参数名**: `checkTemplateId` · **类型**: String

| templateId | 模板名 | 说明 | 状态 |
|-----------|--------|------|------|
| 1001 | MIX | NUM + LEN 组合，覆盖最全 | **推荐** |
| 1002 | NUM | 行数 + 数值字段 avg/max/min | 可用 |
| 1003 | LEN | String/Map/Array 字段长度之和 | 可用 |
| ~~1004~~ | ~~XXHASH64~~ | ~~基础数据类型 hash 分位数~~ | **已废弃** |

**涉及接口**: `AddDataCheckTask`(req)、`UpdateDataCheckTask`(req)、`GetDataCheckTaskConfig`(resp)

**自定义指标字段**：如果内置模板不满足需求，可在 `AddDataCheckConfig` 的 `sourceColumns`/`targetColumns` 中手动填写：
- 只校验某字段：直接填字段名（如 `id`）
- 自定义聚合：必须使用 `AS` 别名，源端目标端别名一致（如 `max(ifNull(id,0)) AS max_id`）

---

### 2.7 dataTypeGroup — 数据类型分组

**枚举类**: `DataTypeGroupEnum` · **类型**: Integer (ordinal)

模板规则按数据类型分组配置校验方法，每组可用的校验方法受 `check_template_base_rule` 约束。

**基础类型 (dataTypeClassify=0):**

| 值 | 分组名 | 包含类型 | 可用校验方法 |
|----|--------|---------|-------------|
| 0 | INTEGER | TINYINT, SMALLINT, INT, BIGINT | SUM, AVG, MIN, MAX |
| 1 | FLOAT | FLOAT, DOUBLE, DECIMAL | SUM, AVG, MIN, MAX |
| 2 | BOOLEAN | BOOLEAN | SUM, AVG, MIN, MAX |
| 3 | STRING | STRING, VARCHAR, CHAR | SUM_CRC32, SUM_LENGTH, COUNT_DISTINCT |
| 4 | DATE | DATE, TIMESTAMP | MIN, MAX, SUM_CRC32, COUNT |

**复合类型 (dataTypeClassify=1):**

| 值 | 分组名 | 包含类型 | 可用校验方法 |
|----|--------|---------|-------------|
| 5 | ARRAY | ARRAY_NUMBER, ARRAY_STR, ARRAY_TIME, ARRAY_COMPLEX | SUM_CRC32, SUM_SIZE, MAX_SIZE, MIN_SIZE |
| 6 | MAP | MAP\<K,V\> | SUM_CRC32, SUM_SIZE, MAX_SIZE, MIN_SIZE |
| 7 | STRUCT | STRUCT | 拆分为基础类型后对比 |

> **约束**：自定义指标模板的 `checkMethods` 必须在上述范围内，不可跨组使用。

**涉及接口**: 模板创建/更新（`AddDataCheckTemplate` req, `UpdateDataCheckTemplate` req）

---

### 2.8 checkMethod — 校验方法

**枚举类**: `CheckMethodEnum` · **类型**: String (name 字段)

| 方法名 | 适用分组 | 说明 |
|--------|---------|------|
| SUM | INTEGER, FLOAT, BOOLEAN | 求和 |
| AVG | INTEGER, FLOAT, BOOLEAN | 平均值 |
| MIN | INTEGER, FLOAT, BOOLEAN, DATE | 最小值 |
| MAX | INTEGER, FLOAT, BOOLEAN, DATE | 最大值 |
| COUNT | DATE | 计数 |
| COUNT_DISTINCT | STRING | 去重计数 |
| SUM_CRC32 | STRING, DATE, ARRAY, MAP | CRC32 校验和 |
| SUM_LENGTH | STRING | 长度求和 |
| SUM_SIZE | ARRAY, MAP | 元素个数求和 |
| MAX_SIZE | ARRAY, MAP | 元素个数最大值 |
| MIN_SIZE | ARRAY, MAP | 元素个数最小值 |

**涉及接口**: 模板创建/更新（metricRules 子项）
