# 修复策略库

## 策略 1：配置差异容忍率

- **适用模式**: DECIMAL 精度误差（模式 1）、TIMESTAMP 微小偏移（模式 6）
- **操作**: 在任务配置中设置 threshold 或 diffTolerateValues
- **示例**:
  - 全局容忍: threshold = 97.0（一致率 >= 97% 判定通过）
  - 指标容忍: diffTolerateValues = {"SUM": 0.001, "AVG": 0.01}
- **注意**: 指标校验的 threshold 默认不传（None），切勿传 0.0

## 策略 2：升级服务版本

- **适用模式**: DECIMAL 前导零缺失（模式 2）、SUPER 类型 NULL（模式 3）
- **操作**: 联系技术支持升级到修复版本
- **已知修复版本**:
  - v1.17.2: PostgresDialect.getDecimalFormatter（前导零）、RedShiftDialect.ifNullFunction（SUPER 类型）
- **验证**: 升级后重跑校验，确认差异消失

## 策略 3：自定义 SQL 校验

- **适用模式**: ARRAY 元素顺序（模式 5）、NULL vs 空字符串（模式 7）、复杂类型展开
- **操作**: 生成自定义 SQL（忽略顺序/类型转换），提交为自定义指标校验
- **详见**: custom-check-sql.md

## 策略 4：校验算法替换

- **适用模式**: CRC32 不兼容（模式 4）
- **操作**: 将弱内容校验算法从 CRC32 替换为 MD5
- **注意**: 在方案推荐阶段即避免选择不兼容的算法

## 策略 5：字段过滤

- **适用模式**: TIMESTAMP 时区偏移（模式 6，如业务可接受）、BOOLEAN 格式化（模式 8）
- **操作**: 在模板或任务配置中排除特定字段
- **方式**:
  - 模板级: filterColumnName（按列名排除）
  - 表级: sourceColumns/targetColumns（只校验指定列）
  - 模板级: 不配置特定 dataTypeGroup 的 metricRule

## 策略 6：ETL 层修复

- **适用模式**: 数据丢失（模式 10）、大字段截断（模式 9）、NULL vs 空字符串（模式 7）
- **操作**: 修复 ETL 逻辑（如显式转换时区、处理 NULL、调整字段长度）
- **验证**: 修复后重跑校验

## 策略 7：重跑校验

- **适用模式**: 偶发性失败、网络超时
- **操作**: 使用"重跑失败任务"功能
- **类型**:
  - type=0: 仅重跑执行失败的
  - type=1: 重跑执行失败 + 校验不通过的
  - type=2: 重跑执行失败 + 被手动停止的
