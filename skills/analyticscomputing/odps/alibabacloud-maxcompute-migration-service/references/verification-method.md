# Verification Method for MaxCompute Migration Service (MMS)

This document provides steps to verify the success of MMS migration operations.

## Migration Job Verification

### Step 1: Check Migration Job Status

通过 MaxCompute 控制台验证：

1. 登录 [MaxCompute 控制台](https://maxcompute.console.aliyun.com/)
2. 选择地域，进入 **数据传输 > 迁移服务 > 迁移作业**
3. 查看作业状态：
   - **运行中**: 作业正在执行
   - **成功**: 作业执行完成
   - **失败**: 作业执行失败，查看错误信息

### Step 2: Verify Data Count

验证迁移后的数据条数：

```sql
-- 在 MaxCompute 项目中执行
SELECT COUNT(*) FROM <target_table>;
```

与源端数据条数对比：

```sql
-- 在源数据源执行（如 Hive）
SELECT COUNT(*) FROM <source_table>;
```

### Step 3: Verify Data Sample

抽样验证数据内容：

```sql
-- 在 MaxCompute 项目中执行
SELECT * FROM <target_table> LIMIT 10;
```

检查数据格式、字段值是否正确。

### Step 4: Verify Partition Data (if applicable)

验证分区数据：

```sql
-- 查看分区列表
SHOW PARTITIONS <target_table>;

-- 验证分区数据量
SELECT COUNT(*) FROM <target_table> WHERE <partition_column> = '<partition_value>';
```

### Step 5: Check Data Validation Results

如开启了数据校验，查看校验结果：

1. 进入 **迁移服务 > 迁移作业**
2. 点击作业名称，查看任务详情
3. 查看 **任务日志** 中的校验结果

校验方法：比对源端和目标端的 `SELECT COUNT(*)` 结果。

## Verification Commands Summary

| Verification | Command/Method | Expected Result |
|-------------|----------------|-----------------|
| 作业状态 | 控制台查看 | 状态为"成功" |
| 数据条数 | `SELECT COUNT(*)` | 源端与目标端一致 |
| 数据内容 | `SELECT * LIMIT N` | 数据格式正确 |
| 分区数据 | `SHOW PARTITIONS` | 分区完整 |
| 数据校验 | 任务日志 | 校验通过 |

## Troubleshooting

### Migration Job Failed

1. 查看错误日志，定位失败原因
2. 常见问题：
   - 网络不通：检查网络配置
   - 权限不足：检查 RAM 权限
   - 源端不可用：检查数据源状态
   - 资源不足：检查 MaxCompute CU 资源

### Data Count Mismatch

1. 检查是否有迁移任务失败
2. 检查分区过滤条件是否正确
3. 检查源端是否有数据变更
4. 重新执行数据校验

### Data Format Error

1. 检查字段类型映射是否正确
2. 检查字符编码设置
3. 检查数据源配置
