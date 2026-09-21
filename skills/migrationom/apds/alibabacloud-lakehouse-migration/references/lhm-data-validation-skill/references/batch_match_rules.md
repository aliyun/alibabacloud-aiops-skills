# taskConfigMatchRule 批量匹配规则参考

> **适用场景**：`taskMode=1`（同模式批量创建）时，通过 `taskConfigMatchRule` 字段传入批量匹配规则，自动发现并配置待校验的表。
>
> **参考文档
**：[校验范围批量配置规则 — 阿里云](https://help.aliyun.com/zh/cmh/lakehouse-migration/user-guide/rules-for-verification-scope)

## 规则格式

每行一条规则，字段以竖线 `|` 分隔：

```
源端库名|目标端库名|源表名|目标表名|分区条件|字段映射
```

| 位置 | 字段    | 必填 | 说明                                                |
|----|-------|----|---------------------------------------------------|
| 1  | 源端库名  | 是  | 源端数据库名（Hive 用 database，MaxCompute 用 project）      |
| 2  | 目标端库名 | 是  | 目标端数据库名                                           |
| 3  | 源表名   | 是  | 支持精确名、正则 `.*`、通配符 `*`（见下方「通配符与正则的区别」） |
| 4  | 目标表名  | 否  | 省略时与源表名一致；支持 `${replace:}` `${pre:}` `${end:}` 变换 |
| 5  | 分区条件  | 否  | 源端分区过滤 + 目标端分区条件，以 `;` 分隔                         |
| 6  | 字段映射  | 否  | 分区字段映射，多组以 `;` 分隔（如 `pt:dt;year:new_year`）        |

## 一、精确表名映射

### 1.1 基本映射（无分区）

```
hive_db|mc_project|aliyun_order|alibaba_order
```

校验 `hive_db.aliyun_order` 与 `mc_project.alibaba_order`，分区以源端分区为准。

### 1.2 带分区筛选 + 字段映射

```
hive_db|mc_project|aliyun_order|alibaba_order|pt>'20240115'|pt:dt
```

校验 `aliyun_order` 与 `alibaba_order`，仅校验源端 `pt>'20240115'` 的分区，且将源端分区字段 `pt` 映射到目标端的 `dt`。

### 1.3 多级分区字段映射

```
hive_db|mc_project|aliyun_order|alibaba_order|pt>'20240115'|pt:dt;year:new_year
```

分区字段 `pt → dt`，同时 `year → new_year`。

### 1.4 整表校验 + 字段映射

```
hive_db|mc_project|aliyun_order|alibaba_order||pt:dt
```

不筛选分区（整表校验），但做分区字段映射。

### 1.5 分区完全映射（源端和目标端各自指定）

```
hive_db|mc_project|aliyun_order|alibaba_order|pt='20240116';dt='20240118'
```

源端 `pt='20240116'` 与目标端 `dt='20240118'` 做精确映射。

## 二、正则匹配表名

### 2.1 正则匹配（表名/字段不变）

```
hive_db|mc_project|aliyun.*
```

匹配 `hive_db` 下所有 `aliyun` 开头的表，目标端表名与源端一致，做全表校验。

```
hive_db|mc_project|aliyun.*|aliyun.*|dt>'20240115'
```

匹配 `aliyun` 开头的表，仅校验 `dt>'20240115'` 的分区。

### 2.2 全库校验

```
hive_db|mc_project|*
```

源端所有表与目标端同名表校验。如果目标端不存在同名表，任务中标识"目标表不存在"。

### 2.3 关键字替换

```
hive_db|mc_project|aliyun.*|aliyun.*|||${replace:aliyun:alibaba}
```

匹配 `aliyun` 开头的表，将表名中 `aliyun` 替换为 `alibaba` 作为目标表名。

### 2.4 添加前缀

```
hive_db|mc_project|aliyun.*|aliyun.*|||${pre:alibaba_}
```

为所有匹配表批量添加前缀 `alibaba_` 作为目标表名。

### 2.5 添加后缀

```
hive_db|mc_project|aliyun.*|aliyun.*|||${end:_alibaba}
```

为所有匹配表批量添加后缀 `_alibaba` 作为目标表名。

### 2.6 MaxCompute 分区表批量校验

MaxCompute 分区表在批量模式下**必须同时满足以下两点**，否则会出现 `full scan with all partitions` 或规划结果为空：

1. 保存任务时设置全局参数：
   ```
   source_global_params = "odps.sql.allow.fullscan=true"
   target_global_params = "odps.sql.allow.fullscan=true"
   ```
2. 匹配规则中显式写出**源端和目标端**的分区条件，以 `;` 分隔：
   ```
   source_db|source_db|lhm_test_count_src|lhm_test_count_tgt|dt='2026-01-01';dt='2026-01-01'
   ```

> 注意：只写源端分区或只设 `fullscan` 参数，仍可能因目标端无分区条件导致按 `dt` 全表分组，从而校验结果不一致。

## 三、内置日期变量

分区条件中可使用以下内置变量替代硬编码日期：

| 表达式                                    | 说明     | 示例                                                        |
|----------------------------------------|--------|-----------------------------------------------------------|
| `ds='20210805'`                        | 指定日期   | `ds='20210805'`                                           |
| `${bizdate}`                           | 当天     | `dt=${bizdate:yyyyMMdd}` → `dt=20240315`                  |
| `lastNDate('${bizdate}',N)`            | 前 N 天  | `dt=lastNDate('${bizdate:yyyyMMdd}',3)` → `dt='20240312'` |
| `tdBeginNDate('${bizdate}','w')`       | 本周初    | → `dt='20240422'`                                         |
| `tdBeginNDate('${bizdate}','m')`       | 本月初    | → `dt='20240401'`                                         |
| `tdBeginNDate('${bizdate}','q')`       | 本季初    | → `dt='20240401'`                                         |
| `cBeginNDate('${bizdate}','y')`        | 本年初    | → `dt='20240101'`                                         |
| `cEndNDate('${bizdate}','w')`          | 本周末    | → `dt='20240428'`                                         |
| `cEndNDate('${bizdate}','m')`          | 本月末    | → `dt='20240430'`                                         |
| `cEndNDate('${bizdate}','q')`          | 本季末    | → `dt='20240630'`                                         |
| `cEndNDate('${bizdate}','y')`          | 本年末    | → `dt='20241231'`                                         |
| `rRangeDate(${bizdate:fmt},start,end)` | 日期范围筛选 | `rRangeDate(${bizdate:yyyyMMdd},5,10}`                    |
| `rRangeNumber(num,start,end)`          | 数字范围筛选 | `rRangeNumber(20240312,3,6)`                              |

### 日期变量组合示例

```
hive_db|mc_project|aliyun_order|alibaba_order|pt='lastNDate('${bizdate:yyyy-MM-dd}',2)';dt='lastNDate('${bizdate:yyyy-MM-dd}',2)'
```

源端 `pt='2024-01-13'` 与目标端 `dt='2024-01-13'` 精确映射（假设今天 2024-01-15）。

```
hive_db|mc_project|aliyun_order|alibaba_order|pt>'lastNDate('${bizdate:yyyy-MM-dd}',2)'|pt:dt
```

源端 `pt>'2024-01-13'` 与目标端 `dt>'2024-01-13'` 做分区映射。

## 四、注意事项

- 校验任务配置中的`taskConfigInfo` 仅在 `taskMode=1` 时生效，可以只填写这个一个字段即可；
- 规则中的库名对应数据源下的实际库，需与 `srcDsName` / `dstDsName` 配置一致
- 正则 `.*` 匹配零到多个字符，`*` 匹配所有表
- 分区条件为空时（两个 `||` 之间），表示整表校验
- 字段映射为空时，分区字段名保持一致（无需映射）

## 五、性能影响

- 匹配规则的范围直接影响执行时间：`*`（全库）或 `xxx.*` 可能匹配数十到数百张表，每张表需独立执行校验 SQL
- 建议先用精确表名或少量正则验证流程，确认无误后再扩大匹配范围
- 批量模式推荐轮询超时设为 1200s（20 分钟），逐表模式 600s（10 分钟）
- 可通过 `list_data_check_report(batch_id=xxx)` 查看已完成的表数量与总数之比，估算进度
- 正则 `zqj.*` 这类宽泛规则在大项目中可能匹配大量表，建议先用 `list_data_check_report` 确认匹配数量是否合理
