# 模板手动配置指引

## 当前状态

模板管理已支持 SDK 编程调用（`list_templates` / `create_template` / `update_template` / `delete_templates`），可通过 AI 直接操作。如偏好控制台可视化配置，也可在 LHM 控制台手动创建，然后将模板 ID 提供给 AI 使用。

## 创建步骤

1. 登录 LHM 控制台 → 数据校验 → 模板管理
2. 点击「新建模板」
3. 填写模板名称和描述
4. 选择校验类型：
   - **指标比对**（checkType=1）：按数据类型分组配置聚合方法和容差
   - **弱内容比对**（checkType=2）：配置参与校验的列类型和列名过滤
5. 选择适用的数据源和引擎范围
6. 配置校验规则（参见下方详细说明）
7. 保存模板，在模板列表中复制模板 ID（UUID 格式）

## 指标模板配置要点

配置规则时，按数据类型分组选择校验方法。可选方法受系统约束：

| 数据类型分组 | 包含类型 | 可选方法 |
|-------------|---------|---------|
| 整型 | TINYINT, SMALLINT, INT, BIGINT | SUM, AVG, MIN, MAX |
| 浮点 | FLOAT, DOUBLE, DECIMAL | SUM, AVG, MIN, MAX |
| 布尔 | BOOLEAN | SUM, AVG, MIN, MAX |
| 字符串 | STRING, VARCHAR, CHAR | SUM(CRC32), SUM(LENGTH), COUNT(DISTINCT) |
| 日期 | DATE, TIMESTAMP | MIN, MAX, SUM(CRC32), COUNT |
| 数组 | ARRAY | SUM(CRC32), SUM(SIZE), MAX(SIZE), MIN(SIZE) |
| 映射 | MAP | SUM(CRC32), SUM(SIZE), MAX(SIZE), MIN(SIZE) |

每组可单独设置容差（统一阈值或按方法自定义）。

完整配置说明见 `knowledge/patterns/template-guide.md`。

## 弱内容模板配置要点

- 可选择参与校验的列类型（如只校验 VARCHAR 和 TEXT 列）
- 可通过列名表达式过滤（如排除 `id` 和 `create_time` 列）
- 哈希算法由系统决定，不支持手动选择

## 提供模板 ID 给 AI

创建完成后，告诉 AI 模板 ID 和配置概要即可，例如：

> "我在控制台创建了一个自定义指标模板，ID 是 `a1b2c3d4-e5f6-7890-abcd-ef1234567890`，只校验整数列的 SUM 和 AVG，浮点列容差 0.01。"

AI 会在后续校验中通过 `--check-template-id` 参数使用该模板。

## 编程方式替代

如不想手动操作控制台，可直接通过 AI 管理模板：
- 查看可用模板：`list_templates(client, check_type=1, is_builtin=1)`
- 创建模板：`create_template(client, name=..., check_type=1, ds_engine_rels=..., metric_rules=...)`
- 更新模板：`update_template(client, template_id=..., metric_rules=...)`（内部自动处理 basic/complex 拆分）
- 删除模板：`delete_templates(client, [template_id1, template_id2])`

CLI 入口：`atomic-skills/lhm-template-manage/scripts/run.py --action <list|detail|create|update|delete>`
