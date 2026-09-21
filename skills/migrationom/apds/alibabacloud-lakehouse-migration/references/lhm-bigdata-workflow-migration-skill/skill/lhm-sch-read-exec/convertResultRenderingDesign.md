# 结果摘要生成逻辑

## 触发时机

在 read-exec SKILL 的执行流程中，`结果总结` 发生在 convert 阶段完成之后、SKILL 向用户输出最终结果之时。时序如下：

```
[read-exec SKILL 内部]

1. Schema 兜底校验 ──→ 通过
2. 触发 read  ──→ 里程碑反馈"读取完成"
3. 触发 convert ──→ 里程碑反馈"转换完成"
4. 【结果总结】读取 convert_statistics.json ──→ 生成摘要 ──→ 输出给用户
```

## 数据读取策略

| 步骤 | 读取文件 | 必要性 | 失败处理 |
|------|---------|--------|---------|
| 1 | `<output_dir>/metadata/convert_statistics.json` | **必读** | 若不存在→降级为"执行完成，但无法生成摘要，请检查产物目录" |
| 2 | `<output_dir>/manifest.json` | 可选 | 缺失不影响摘要生成，仅影响"失败节点定位" |

> **设计选择**：SKILL 侧**只读 convert_statistics.json 即可生成完整摘要**。manifest.json 仅在需要列出失败节点的详细路径时读取。这保证了 SKILL 的简单性——一个 JSON 文件包含摘要所需的全部信息。

## 摘要生成算法

```
输入：convert_statistics.json 内容（已 parse 为对象 stats）
输出：格式化的聊天文本

算法：
1. 判断 stats.summary.failed_nodes == 0 且 stats.issues 中无 ERROR
   → 全成功模板
   否则 → 部分失败模板

2. 拼接顶行：
   全成功："✓ 转换完成 — {source.datasource_name} → {target.datasource_name}"
   部分失败："⚠ 转换完成（有问题需关注）— {source.datasource_name} → {target.datasource_name}"

3. 拼接概览区：
   "概览：\n"
   "  工作流 {total_workflows} 个 | 节点 {total_nodes} 个\n"
   "  成功 {success_nodes} | 失败 {failed_nodes} | 降级 {degraded_nodes}"
   （若 skipped_nodes > 0）" | 跳过 {skipped_nodes}"
   " | 耗时 {format_duration(duration_ms)}\n"

4. 拼接节点类型分布（仅当 node_type_distribution 非空）：
   "节点类型分布：\n"
   "  " + 按数量降序取 Top 5，格式 "{type}({count})"，空格分隔
   （若超过5种类型）+ " ...等 {total_types} 种"

5. 拼接问题汇总（仅当 issues 非空）：
   "问题汇总：\n"
   按 level 分组统计：
     ERROR: "  [ERROR] {count} 个节点转换失败"
            若 count <= 3，追加节点名 "（{node_id1}, {node_id2}）"
     WARNING: "  [WARNING] {count} 个告警"
              拼接各 category 的子计数
     INFO: "  [INFO] {count} 条信息提示"

6. 拼接产物引导：
   "报告：{output_artifacts.excel_report_path}\n"
   "详情：执行 /lhm-sch-read-explain 可深入查看\n"
```
##  输出模板

### 全成功模板
```

✓ 转换完成 — dolphin_prod → dw_target

概览：
  工作流 5 个 | 节点 42 个
  成功 42 | 失败 0 | 降级 0 | 耗时 12.5s

节点类型分布：
  ODPS_SQL(20)  SHELL(10)  DI(8)  PyODPS(3)  EMR_SPARK(1)

报告：LHMPackageOverview.xls
详情：执行 /lhm-sch-read-explain 可深入查看
```

### 部分失败模板
```

⚠ 转换完成（有问题需关注）— dolphin_prod → dw_target

概览：
  工作流 5 个 | 节点 42 个
  成功 38 | 失败 2 | 降级 2 | 耗时 12.5s

节点类型分布：
  ODPS_SQL(20)  SHELL(10)  DI(8)  PyODPS(3)  EMR_SPARK(1)

问题汇总：
  [ERROR] 2 个节点转换失败（proc_complex_etl, custom_ftp_upload）
  [WARNING] 3 个告警（2 个类型降级, 1 个数据源映射不确定）
  [INFO] 1 条信息提示

报告：LHMPackageOverview.xls
详情：执行 /lhm-sch-read-explain 可深入查看
```

### 耗时格式化规则

| duration_ms 范围 | 输出格式 | 示例 |
|-----------------|---------|------|
| < 1000 | `{ms}ms` | `800ms` |
| 1000 ~ 60000 | `{sec}s` | `12.5s` |
| 60000 ~ 3600000 | `{min}m{sec}s` | `2m30s` |
| >= 3600000 | `{hour}h{min}m` | `1h5m` |

### 异常处理

当 `convert_statistics.json` 不存在或格式异常时，SKILL 应给出友好提示并引导用户检查产物目录。AI SKILL 自身具备容错降级能力，无需为每种异常场景预定义固定模板。


### 带 sqlNodeTypeMapping 的结果总结

当用户传入了自定义节点类型映射时，摘要需要额外体现"哪些节点走了近似映射"：

```
⚠ 转换完成（有问题需关注）— dolphin_prod → dw_target

概览：
  工作流 5 个 | 节点 42 个
  成功 38 | 失败 0 | 降级 4 | 耗时 12.5s

应用的自定义映射：
  CUSTOM_SQL → ODPS_SQL（命中 4 个节点）

节点类型分布：
  ODPS_SQL(24)  SHELL(10)  DI(8)

问题汇总：
  [WARNING] 4 个节点通过自定义映射降级写入（近似类型，可能需人工调整）

报告：LHMPackageOverview.xls
详情：执行 /lhm-sch-read-explain 可深入查看
```

**触发条件**：当 `convert_config_applied.sqlNodeTypeMapping` 非空 且 `degraded_nodes > 0` 时，追加"应用的自定义映射"区块。
