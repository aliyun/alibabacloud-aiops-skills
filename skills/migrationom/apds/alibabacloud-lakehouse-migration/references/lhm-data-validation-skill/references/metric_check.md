# 指标校验详细说明

## 模板选择

| 模板 | templateId | 说明 | 状态 |
|------|-----------|------|------|
| MIX | 1001 | NUM + LEN 组合，覆盖最全 | **推荐** |
| NUM | 1002 | 行数 + 数值字段 avg/max/min | 可用 |
| LEN | 1003 | String/Map/Array 字段长度之和 | 可用 |
| XXHASH64 | 1004 | **已废弃**，不要用 | 废弃 |

## 自定义聚合字段

- 自定义聚合须用 `AS` 别名且源端目标端别名一致（如 `max(ifNull(id,0)) AS max_id`）
- 只校验某字段直接填字段名（如 `id`）

**前置条件**：如需在 `add_data_check_config` 中指定 `source_columns` / `target_columns` 自定义聚合字段，请确保已在控制台「**迁移准备 → 资源组与服务代理 → 服务代理**」页面安装服务代理，否则将返回 `E002R901: Agent is not active` 错误。不指定自定义字段时使用模板默认聚合，无需服务代理。

## MaxCompute 数据源

指标校验同样需要在 `exec_data_check_save_task` 中设置全局参数，否则分区表会报 `ODPS-0130071` 全表扫描限制错误：

```python
# 源端是 MaxCompute
source_global_params='odps.sql.allow.fullscan=true'

# 目标端是 MaxCompute
target_global_params='odps.sql.allow.fullscan=true'

# 两端都是 MaxCompute
source_global_params='odps.sql.allow.fullscan=true',
target_global_params='odps.sql.allow.fullscan=true'
```

## 字段结果解读

字段明细中使用 `src_alias` 标识指标类型（如 `min_col_bigint`、`avg_col_int`），**不存在** `compare_type` 字段。

判断一致性使用 `is_consistent`（0=不一致 / 1=一致），**不是** `check_result`（0/1/2）。

## MAP 类型字段与 GROUP BY 问题

MIX 模板（1001）会自动对表中所有字段生成 GROUP BY 聚合 SQL。**MAP、ARRAY、STRUCT 等复杂类型字段无法参与 GROUP BY**，会导致如下错误：

```
ODPS-0130071: column <col_map> should appear in GROUP BY key or be used in an aggregate function
```

**解决方法**：通过 `source_columns` / `target_columns` 显式指定要校验的字段，**排除 MAP 等复杂类型字段**：

```python
tables = [{
    'source_table': 'src_db.metric_demo_src',
    'target_table': 'dst_db.metric_demo_tgt',
    'source_columns': 'col_bigint,col_int,col_string,col_double,col_boolean,col_float,col_datetime,col_decimal,col_timestamp',
    'target_columns': 'col_bigint,col_int,col_string,col_double,col_boolean,col_float,col_datetime,col_decimal,col_timestamp',
}]
```

## 阈值机制与 total_count_threshold 陷阱

### 相似度计算公式

指标校验的相似度公式为：`similarity = min(src_value, dst_value) / max(src_value, dst_value) * 100%`

`expect_threshold` 默认为 100%，即要求两端指标完全一致。

### total_count_threshold 的作用

`total_count_threshold` 用于数据量校验（check_type=0），表示行数差异的容忍百分比（如 0.05 = 允许 5% 的行数差异）。

### ⚠️ 指标校验切勿传 total_count_threshold=0.0

**在指标校验（check_type=1）中，如果将 `total_count_threshold` 设为 `0.0`，所有数值指标（包括 min/max/avg 差异巨大的情况）都会被错误地标记为 PASSED。** 这是一个已知问题。

**正确做法**：指标校验时 `threshold` 参数传 `None`（不传），让系统使用默认值：

```python
# ✅ 正确：threshold 默认 None，不传 total_count_threshold
task_id, batch_id = run_metric_check(client, task_name='指标校验', ...)

# ❌ 错误：threshold=0.0 导致所有指标误判 PASSED
task_id, batch_id = run_metric_check(client, task_name='指标校验', threshold=0.0)
```

`run_metric_check` 和 `run_batch_check`（check_type=1）的 `threshold` 参数默认值已从 `0.0` 改为 `None`，仅在显式传入非 None 值时才会传递给后端。
