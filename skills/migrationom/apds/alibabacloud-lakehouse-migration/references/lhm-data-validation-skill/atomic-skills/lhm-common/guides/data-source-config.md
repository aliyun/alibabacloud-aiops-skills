## 数据源配置指南

### 什么是数据源

数据源是 LHM 校验的源端和目标端数据库连接。在校验任务中，你需要指定一个源端数据源和一个目标端数据源，LHM 会对比两端的数据一致性。

### 支持的数据源类型

| 类型 | 说明 |
|------|------|
| MaxCompute | 阿里云大数据计算服务 |
| Hive | Hadoop 数据仓库 |
| ClickHouse | 列式分析数据库 |
| Hologres | 阿里云实时数仓 |
| StarRocks | 新一代极速分析数据库 |
| Doris | Apache Doris 分析数据库 |
| MySQL | 关系型数据库 |
| Synapse | Azure Synapse Analytics |
| Databricks | 统一数据湖平台 |
| Redshift | AWS 数据仓库 |
| Athena | AWS Serverless 查询服务 |

### 配置步骤

**Step 1: 在 LHM 控制台添加数据源**
1. 进入 [LHM 数据源管理](https://apds.console.aliyun.com/lake-house/datasource-manage)
2. 点击「新建数据源」
3. 选择数据源类型
4. 填写连接信息（集群地址、数据库名、用户名、密码等）
5. 测试连接是否成功
6. 保存并记录数据源 ID 和名称

**Step 2: 在 lhm-common 中注册别名**

在 LHM 控制台创建的数据源有 ds_id 和 ds_name，但使用时记 ID 不方便。lhm-common 支持为数据源设置别名：

```bash
python run.py config add-ds \
  --alias mc_source \
  --ds-id ds-abc123 \
  --ds-name "订单MaxCompute" \
  --ds-type MaxCompute

python run.py config add-ds \
  --alias sr_target \
  --ds-id ds-xyz456 \
  --ds-name "订单StarRocks" \
  --ds-type StarRocks
```

之后执行校验任务时，只需说"用 mc_source 和 sr_target"，AI 会自动从配置中读取对应的 ds_id。

### 管理已配置的数据源

```bash
# 查看所有数据源
python run.py config list

# 查看某个数据源详情
python run.py config show --alias mc_source

# 删除数据源
python run.py config remove-ds --alias mc_source
```

### 注意事项

- 数据源必须在 LHM 控制台先创建，拿到 ds_id 后才能注册到 data_validation_config.yaml
- 别名由你自定义，建议使用有意义的名称（如 `prod_mc`、`test_sr`）
- 同一别名不可重复添加
- MaxCompute 分区表校验时，需要在全局参数中设置 `odps.sql.allow.fullscan=true`

官方文档：https://help.aliyun.com/zh/cmh/lakehouse-migration/user-guide/instructions-for-use
