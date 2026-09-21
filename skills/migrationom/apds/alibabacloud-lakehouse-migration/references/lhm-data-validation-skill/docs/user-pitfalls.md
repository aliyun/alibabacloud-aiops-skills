# 客户常见误区

## 1. threshold=0.0 陷阱

**误区**: "threshold 设为 0 表示精确匹配"
**事实**: threshold=0.0 意味着"一致率 >= 0% 就算通过"，即所有校验都判定为 PASSED。
**正确做法**: 不传 threshold（使用系统默认精确匹配）或传 100。

## 2. 指标校验 threshold 传 0.0

**误区**: "指标校验的 threshold 也设为 0"
**事实**: 指标校验传 0.0 会导致所有数值指标误判为 PASSED。
**正确做法**: 指标校验的 threshold 默认不传（None），由系统使用默认值。

## 3. batch_id vs task_id 混淆

**误区**: 调 API 时 batch_id 和 task_id 混用
**事实**:
- task_id: 任务级 ID，创建任务时返回
- batch_id: 批次级 ID，每次执行产生新的 batch_id
- 报告查询用 batch_id，任务操作用 task_id

## 4. CRC32 兼容性假设

**误区**: "CRC32 是标准算法，两端一定兼容"
**事实**: Redshift 的 CRC32 使用非标准多项式，且返回 hex 字符串而非整数。与 MaxCompute/Hive 的 CRC32 完全不兼容。
**正确做法**: Redshift 相关的数据源对，弱内容校验使用 MD5。

## 5. MaxCompute 分区表批量校验未开启全表扫描或未指定双边分区条件

**误区**: "直接校验分区表就行"
**事实**: MaxCompute 默认禁止全表扫描；批量模式下还需在匹配规则中显式指定源端和目标端分区条件，仅设一端会导致规划为空或校验结果异常。
**正确做法**: 同时设置 `source_global_params = "odps.sql.allow.fullscan=true"` 和 `target_global_params = "odps.sql.allow.fullscan=true"`，并在匹配规则中写明双边分区条件，例如 `dt='2026-01-01';dt='2026-01-01'`。

## 6. DECIMAL 前导零误判

**误区**: "0.1 和 .1 是数据差异"
**事实**: PostgreSQL 系（PG/Redshift/GaussDB/Hologres/ADBPG）的 TO_CHAR 格式化会丢失前导零，是显示格式问题而非数据差异。
**正确做法**: 升级到 v1.17.2+，或识别此为已知格式差异。

## 7. 弱内容校验全部不一致时的恐慌

**误区**: "弱内容校验差异率 100%，数据全丢了"
**事实**: 可能原因：1) CRC32 不兼容 2) SUPER 类型 NULL 处理 3) DECIMAL 前导零。不一定是数据丢失。
**正确做法**: 先检查是否为已知差异模式（参考 difference-patterns.md），再判断是否需要处理。

## 8. 忽略 global_params 中的多参数分隔

**误区**: "source_global_params 只设一个参数"
**事实**: 多个参数用分号分隔，如 `odps.sql.allow.fullscan=true;set odps.sql.type.system.odps2=true`
**正确做法**: 确认所有需要的参数都已配置。

## 9. 自定义指标表达式缺少 AS 别名

**误区**: "自定义指标直接写 sum(col) 就行"
**事实**: 指标校验的自定义表达式需要 AS 关键字才能被系统识别。
**正确做法**: 必须写为 `sum(col) AS sum_col` 格式。注意：自定义SQL校验类型当前不支持，自定义指标通过指标校验实现。

## 10. 一致性判定字段误读

**误区**: "看 checkResult 判断是否一致"
**事实**: checkResult 是校验结果（PASSED/FAILED），isConsistent 才是数据一致性判定（0=不一致，1=一致）。
**正确做法**: 使用 isConsistent 字段判断数据一致性。

## 11. 批量匹配规则通配符误用

**误区**: "`*` 和 `.*` 都能匹配任意字符"
**事实**: 批量匹配规则的表名字段按正则解析。`lhm_*` 表示 `lhm` 后跟零到多个下划线，只能匹配 `lhm`、`lhm_`、`lhm__` 等；要匹配所有 `lhm_` 开头的表应写 `lhm_.*`。匹配全部表直接用 `*`。
**正确做法**: 将规则当作正则编写，不确定时先用 `*` 做全库校验，再逐步收窄。

## 12. 任务名包含特殊字符

**误区**: "任务名可以随便写"
**事实**: LHM 后端对 `task_name` 有严格校验，仅允许中英文、数字，空格、下划线、连字符等均会触发 `E500R103`。
**正确做法**: 使用纯中文或英文加数字命名，例如 `'每日全库校验'`、`'HiveToMaxComputeCount'`。
