# RAM Policies for MaxCompute Migration Service (MMS)

本文档详细说明 MMS 所需的权限配置，包括 RAM 权限和 MaxCompute 项目权限。

## 权限配置概述

MMS 需要配置三类权限：

| 权限类型 | 授权对象 | 说明 |
|---------|---------|------|
| 服务关联角色 | 阿里云账号 | MMS 访问云资源的角色 |
| RAM 权限 | 执行迁移的 RAM 用户 | MMS 操作权限 |
| MaxCompute 项目权限 | 服务关联角色 | 数据读写权限 |

## 1. 服务关联角色

首次使用 MMS 前，必须创建服务关联角色：

**角色名称**：`AliyunServiceRoleForMaxComputeMMS`

**创建方式**：

### 通过 MaxCompute 控制台
1. 登录 MaxCompute 控制台
2. 选择 数据传输 > 迁移服务
3. 点击 新增数据源
4. 在弹出的对话框中确认创建

### 通过 RAM 控制台
1. 登录 RAM 控制台 > 身份管理 > 角色
2. 点击 创建角色 > 创建服务关联角色
3. 选择信任的云服务：`AliyunServiceRoleForMaxComputeMMS`

> **注意**：RAM 用户需要 `AliyunRAMFullAccess` 权限才能创建服务关联角色

## 2. RAM 权限策略（给 RAM 用户）

### 2.1 MMS 所有操作权限

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListMmsDataSources",
        "odps:CreateMmsDataSource",
        "ram:GetRole",
        "odps:GetMmsDataSource",
        "odps:UpdateMmsDataSource",
        "odps:DeleteMmsDataSource",
        "odps:CreateMmsFetchMetadataJob",
        "odps:GetMmsFetchMetadataJob",
        "odps:ListMmsFetchMetadataJobLogs",
        "odps:ListMmsDbs",
        "odps:GetMmsDb",
        "odps:ListMmsTables",
        "odps:GetMmsTable",
        "odps:ListMmsPartitions",
        "odps:GetMmsPartition",
        "odps:ListMmsJobs",
        "odps:GetMmsJob",
        "odps:CreateMmsJob",
        "odps:DeleteMmsJob",
        "odps:StartMmsJob",
        "odps:StopMmsJob",
        "odps:RetryMmsJob",
        "odps:ListMmsTasks",
        "odps:GetMmsTask",
        "odps:ListMmsTaskLogs",
        "odps:StopMmsTask",
        "odps:StartMmsTask",
        "odps:RetryMmsTask",
        "odps:GetMmsAsyncTask",
        "odps:GetMmsProgress",
        "odps:GetMmsSpeed",
        "odps:CreateMmsAuthFile",
        "odps:ListMmsAgents",
        "odps:ListMmsTimers",
        "odps:GetMmsTimer",
        "odps:UpdateMmsTimer",
        "odps:ListMmsTimerLogs",
        "odps:CreateMmsTimer",
        "odps:UpdateMmsTables",
        "odps:UpdateMmsTable",
        "odps:UpdateMmsDb",
        "odps:ListNetworkLinks"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2.2 MMS 源数据管理权限

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListMmsDataSources",
        "odps:CreateMmsDataSource",
        "ram:GetRole",
        "odps:GetMmsDataSource",
        "odps:UpdateMmsDataSource",
        "odps:DeleteMmsDataSource",
        "odps:CreateMmsFetchMetadataJob",
        "odps:GetMmsFetchMetadataJob",
        "odps:ListMmsFetchMetadataJobLogs",
        "odps:ListMmsDbs",
        "odps:GetMmsDb",
        "odps:ListMmsTables",
        "odps:GetMmsTable",
        "odps:ListMmsPartitions",
        "odps:GetMmsPartition",
        "odps:GetMmsAsyncTask",
        "odps:GetMmsProgress",
        "odps:GetMmsSpeed",
        "odps:CreateMmsAuthFile",
        "odps:ListMmsAgents",
        "odps:UpdateMmsTables",
        "odps:UpdateMmsTable",
        "odps:UpdateMmsDb"
      ],
      "Resource": "*"
    }
  ]
}
```

### 2.3 MMS 迁移作业管理权限

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "odps:ListMmsDataSources",
        "odps:GetMmsDataSource",
        "odps:CreateMmsFetchMetadataJob",
        "odps:GetMmsFetchMetadataJob",
        "odps:ListMmsFetchMetadataJobLogs",
        "odps:ListMmsDbs",
        "odps:GetMmsDb",
        "odps:ListMmsTables",
        "odps:GetMmsTable",
        "odps:ListMmsPartitions",
        "odps:GetMmsPartition",
        "odps:ListMmsJobs",
        "odps:GetMmsJob",
        "odps:CreateMmsJob",
        "odps:DeleteMmsJob",
        "odps:StartMmsJob",
        "odps:StopMmsJob",
        "odps:RetryMmsJob",
        "odps:ListMmsTasks",
        "odps:GetMmsTask",
        "odps:ListMmsTaskLogs",
        "odps:StopMmsTask",
        "odps:StartMmsTask",
        "odps:RetryMmsTask",
        "odps:GetMmsAsyncTask",
        "odps:GetMmsProgress",
        "odps:GetMmsSpeed",
        "odps:ListMmsTimers",
        "odps:GetMmsTimer",
        "odps:UpdateMmsTimer",
        "odps:ListMmsTimerLogs",
        "odps:CreateMmsTimer"
      ],
      "Resource": "*"
    }
  ]
}
```

## 3. MaxCompute 项目权限（给服务关联角色）

在目标项目中，需要为服务关联角色授予数据操作权限：

### 3.1 添加服务关联角色到项目

```sql
USE <target_project>;
ADD USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

### 3.2 粗粒度授权（推荐）

```sql
-- 授予 admin 角色
GRANT admin TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

### 3.3 细粒度授权

**项目级权限：**

```sql
GRANT Read,Write,List,CreateTable,CreateInstance,CreateFunction,CreateResource
ON project <project_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;

-- 或授予所有权限
GRANT ALL ON project <project_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

**表级权限：**

```sql
GRANT Describe,Select,Alter,Update,Drop,ShowHistory
ON table <table_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;

-- 或授予所有权限
GRANT All ON table <table_name> TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

**实例级权限：**

```sql
GRANT Read,Write ON instance <instance_id>
TO USER `RAM$<account_id>:role/AliyunServiceRoleForMaxComputeMMS`;
```

### 3.4 权限说明

| 对象类型 | 支持的权限 |
|---------|-----------|
| Project | Read, Write, List, CreateTable, CreateInstance, CreateFunction, CreateResource, All |
| Table | Describe, Select, Alter, Update, Drop, ShowHistory, All |
| Instance | Read, Write, All |
| Resource | Read, Write, Download, Delete |
| Function | Read, Write, Download, Execute, Delete |

## 4. 快捷授权方案

| 场景 | 推荐方案 |
|-----|---------|
| 主账号操作 | 无需额外配置 RAM 权限 |
| RAM 用户完整 MaxCompute 权限 | 授予 `AliyunMaxComputeFullAccess` |
| RAM 用户仅 MMS 操作权限 | 使用上述自定义权限策略 |
| 创建服务关联角色 | RAM 用户需 `AliyunRAMFullAccess` |

## 5. 通过控制台配置权限

### MaxCompute 控制台配置项目权限

1. 登录 MaxCompute 控制台
2. 选择 管理配置 > 项目管理
3. 点击目标项目的 管理
4. 选择 角色权限 页签
5. 新建角色并配置权限
6. 在成员管理中添加服务关联角色

## 6. 权限排查

### 常见错误

| 错误信息 | 原因 | 解决方案 |
|---------|------|---------|
| Forbidden.RAM | RAM 用户缺少 MMS 操作权限 | 添加 MMS 权限策略 |
| Access Denied | 服务关联角色未授权项目权限 | 在项目中添加用户并授权 |
| ServiceLinkedRole not found | 服务关联角色未创建 | 创建 AliyunServiceRoleForMaxComputeMMS |

### 权限检查清单

- [ ] 服务关联角色已创建
- [ ] RAM 用户已授予 MMS 操作权限
- [ ] 服务关联角色已添加到目标项目
- [ ] 服务关联角色已授予数据操作权限
- [ ] 目标项目已绑定 Quota 资源
