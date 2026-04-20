# Acceptance Criteria: MaxCompute Migration Service (MMS)

**Scenario**: MaxCompute Migration Service (MMS) - 将多种数据源迁移至 MaxCompute
**Purpose**: Skill testing acceptance criteria

---

# Correct Usage Patterns

## 1. CLI Commands

### ✅ CORRECT

```bash
# 列出项目
aliyun maxcompute list-projects --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# 获取项目详情
aliyun maxcompute get-project --project my_project --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service

# 列出表
aliyun maxcompute list-tables --project my_project --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service
```

### ❌ INCORRECT

```bash
# 缺少 --user-agent
aliyun maxcompute list-projects --region cn-hangzhou

# 使用错误的 API 格式（非 plugin mode）
aliyun maxcompute ListProjects --RegionId cn-hangzhou

# 缺少必要参数
aliyun maxcompute get-project --region cn-hangzhou
```

## 2. Console Operations

### ✅ CORRECT

1. 登录 MaxCompute 控制台
2. 进入 **数据传输 > 迁移服务**
3. 按步骤创建数据源和迁移作业

### ❌ INCORRECT

1. 直接使用 CLI 创建 MMS 数据源（当前不支持）
2. 跳过准备工作直接创建迁移作业

## 3. Parameter Handling

### ✅ CORRECT

- 确认所有用户参数后再执行操作
- 使用用户提供的具体值，不假设默认值
- 列出参数确认表供用户确认

### ❌ INCORRECT

```markdown
# 错误：假设默认值
aliyun maxcompute list-projects --region cn-hangzhou  # 假设用户要查询杭州地域

# 错误：使用占位符直接执行
aliyun maxcompute get-project --project <project-name>
```

## 4. Credential Handling

### ✅ CORRECT

```bash
# 只检查凭证状态
aliyun configure list
```

输出中显示有效的 profile (AK, STS, 或 OAuth identity)。

### ❌ INCORRECT

```bash
# 读取或打印 AK/SK 值
echo $ALIBABA_CLOUD_ACCESS_KEY_ID

# 让用户在命令行输入凭证
aliyun configure set --access-key-id <user-input>
```

## 5. Error Handling

### ✅ CORRECT

1. 捕获错误信息
2. 分析错误原因
3. 提供解决方案
4. 引导用户使用 `ram-permission-diagnose` skill 处理权限问题

### ❌ INCORRECT

- 忽略错误继续执行
- 不提供解决建议
- 重复执行相同失败的操作

---

# Feature Verification Checklist

## MMS Core Features

- [ ] 支持的数据源类型识别 (Hive, BigQuery, Databricks, MaxCompute)
- [ ] 迁移作业类型说明 (整库、多表、多分区)
- [ ] 准备工作步骤完整
- [ ] 数据源创建流程清晰
- [ ] 迁移作业创建流程清晰
- [ ] 监控和验证方法明确

## CLI Commands

- [ ] 所有 `aliyun` 命令包含 `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-maxcompute-migration-service`
- [ ] 使用 plugin mode 格式 (如 `list-projects` 而非 `ListProjects`)
- [ ] 必要参数完整

## Documentation

- [ ] RAM Policy 文档完整
- [ ] Related Commands 文档完整
- [ ] Verification Method 文档完整
- [ ] CLI Installation Guide 复制到 references 目录

## Security

- [ ] 不暴露 AK/SK 值
- [ ] 使用 `aliyun configure list` 验证凭证
- [ ] RAM 权限列表完整
