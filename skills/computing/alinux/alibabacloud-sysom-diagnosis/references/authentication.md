# 阿里云认证配置指南

本文档详细说明如何配置阿里云认证，以便使用 SysOM 诊断工具的远程功能。

## 前提条件

- 已安装阿里云 CLI（如未安装，执行 `yum install aliyun-cli -y`）
- 拥有阿里云账号或 RAM 用户权限

## 支持的认证模式

SysOM 工具支持三种主要认证方式：

| 认证方式 | 适用场景 | 推荐程度 |
|---------|---------|---------|
| **ECS RAM Role** | ECS 实例内执行 | ⭐⭐⭐⭐⭐ 强烈推荐 |
| **AccessKey (AK)** | 本地开发/测试环境 | ⭐⭐⭐ 仅限开发使用 |
| **STS Token** | 短时会话/跨账号临时授权 | ⭐⭐⭐⭐ 推荐（优于长期 AK） |

---

## 方式 1: ECS RAM Role（推荐）

### 为什么推荐 RAM Role？

- **零配置**：无需手动管理 AccessKey
- **最安全**：自动轮换临时凭证，无泄露风险
- **最便捷**：SDK 自动从元数据服务获取凭证

### 配置步骤

#### 步骤 1: 创建 RAM 角色（如未创建）

1. 登录 [RAM 控制台](https://ram.console.aliyun.com/roles)
2. 点击"创建角色" → 选择"阿里云服务" → 选择"普通服务角色"
3. 选择受信服务类型：**云服务器（ECS）**
4. 输入角色名称（如 `SysomRole`）和备注
5. 点击"完成"创建角色

> 📖 详细文档：[创建 RAM 角色](https://help.aliyun.com/zh/ram/user-guide/create-a-ram-role-for-a-trusted-alibaba-cloud-service)

#### 步骤 2: 授予 AliyunSysomFullAccess 权限（⚠️ 必需）

**重要**：必须为 RAM 角色授予 `AliyunSysomFullAccess` 权限，否则无法访问 SysOM API。

1. 在 [RAM 控制台角色列表](https://ram.console.aliyun.com/roles) 中找到刚创建的角色
2. 点击角色名称进入详情页
3. 点击"权限管理"标签页 → "新增授权"
4. 在搜索框输入 `AliyunSysomFullAccess`
5. 勾选该权限策略，点击"确定"

> 📖 权限策略详情：[AliyunSysomFullAccess 权限说明](https://ram.console.aliyun.com/policies/AliyunSysomFullAccess/System/content)

**权限验证**：
- 确保权限策略列表中包含 `AliyunSysomFullAccess`
- 权限类型为"系统策略"

#### 步骤 3: 为 ECS 实例绑定 RAM 角色

1. 登录 [ECS 控制台](https://ecs.console.aliyun.com/server)
2. 找到目标 ECS 实例
3. 点击实例右侧的"更多" → "实例设置" → "绑定/解绑 RAM 角色"
4. 在弹出框中选择刚创建的 RAM 角色（如 `SysomRole`）
5. 点击"确定"完成绑定

**绑定后验证**：
- 实例详情页"配置信息"标签可看到"RAM 角色"字段
- 在实例内执行 `curl http://100.100.100.200/latest/meta-data/ram/security-credentials/` 可看到角色名

> 📖 详细文档：[为 ECS 实例绑定 RAM 角色](https://help.aliyun.com/zh/ecs/user-guide/attach-an-instance-ram-role-to-an-ecs-instance)

#### 步骤 4: 在 ECS 实例内配置 aliyun CLI

登录到 ECS 实例，执行以下命令配置 aliyun CLI 使用 RAM Role：

```bash
# 配置使用 ECS RAM Role 模式
aliyun configure --mode EcsRamRole --ram-role-name <RAM角色名>
```

**示例**：

```bash
aliyun configure --mode EcsRamRole --ram-role-name SysomRole
```

**配置文件示例**（`~/.aliyun/config.json`）：

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "EcsRamRole",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "zh"
    }
  ],
  "meta_path": ""
}
```

**注意**：
- 配置文件中**不需要** `ram_role_name` 字段
- SDK 会自动从 ECS 元数据服务（`http://100.100.100.200`）获取角色名和临时凭证
- 只要实例绑定了 RAM 角色，SDK 就能自动获取

#### 步骤 5: 验证配置

```bash
# 运行预检查（唯一推荐的验证方法）
cd /path/to/sysom-diagnosis
./scripts/osops.sh precheck
```

`precheck` 命令会自动执行以下检查：

1. **检查 ECS 元数据服务**：通过 `curl http://100.100.100.200/latest/meta-data/ram/security-credentials/` 查看实例是否绑定了 RAM 角色
2. **检查环境变量**：验证 `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET`（及可选 `ALIBABA_CLOUD_SECURITY_TOKEN`）
3. **检查配置文件**：解析 `~/.aliyun/config.json` 中的认证配置（AK / StsToken / EcsRamRole 模式）
4. **验证 SysOM API**：调用 `InitialSysom` API 验证权限是否充足

**预期输出（成功）**：

```json
{
  "ok": true,
  "method": "ECS RAM Role (SysomRole)",
  "role": "SysomRole",
  "message": "认证验证成功，拥有 SysOM 访问权限",
  "check_details": [
    {"method": "ECS元数据", "status": "✓ 实例已绑定 RAM 角色: SysomRole"},
    {"method": "环境变量 AKSK", "status": "✗ 未配置"}
  ]
}
```

**预期输出（检测到 RAM 角色但权限不足）**：

```json
{
  "ok": false,
  "error": "未找到有效的认证配置",
  "ecs_role_name": "SysomRole",
  "suggestion": "检测到实例已绑定 RAM 角色 'SysomRole'，请为该角色授予 AliyunSysomFullAccess 权限，然后配置 aliyun CLI 使用 EcsRamRole 模式",
  "check_details": [
    {"method": "ECS元数据", "status": "✓ 实例已绑定 RAM 角色: SysomRole"},
    {"method": "环境变量 AKSK", "status": "✗ 未配置"},
    {"method": "配置文件", "status": "✗ 未配置或配置无效"}
  ]
}
```

**注意**：请使用 `osops precheck` 验证配置，不要使用 `aliyun ecs describe-instances` 等命令，因为 SysOM 需要特定的 API 权限。

### 故障排查

**问题 1：绑定 RAM 角色后，precheck 仍然失败**

可能原因：
- RAM 角色未授予 `AliyunSysomFullAccess` 权限
- 权限刚授予，需要等待 2-5 分钟生效

解决方案：
```bash
# 1. 检查元数据服务是否可访问
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/

# 2. 检查角色名是否正确
curl http://100.100.100.200/latest/meta-data/ram/security-credentials/<RAM角色名>

# 3. 等待几分钟后重新运行 precheck
./scripts/osops.sh precheck
```

**问题 2：找不到 RAM 角色**

确认操作：
- 在 [RAM 控制台](https://ram.console.aliyun.com/roles) 确认角色已创建
- 在 [ECS 控制台](https://ecs.console.aliyun.com/) 实例详情中确认角色已绑定

> 📖 更多故障排查：[ECS 实例 RAM 角色常见问题](https://help.aliyun.com/zh/ecs/user-guide/faq-about-instance-ram-roles)

---

## 方式 2: AccessKey (AK)

### 注意事项

- ⚠️ **安全风险**：长期密钥泄露风险高，仅用于开发/测试
- ⚠️ **不支持命令行直接指定**：出于安全考虑，AK/SK 不能通过命令行参数传递

### 配置步骤

#### 步骤 0: Agent / 多终端场景（优先）

若你在 **COSH** 中：**不要在对话里向 Agent 提供或粘贴 AccessKey/Secret**（会进入聊天记录与日志）。

请优先在**本机终端**（由 Agent 调用 Bash 或用户自己打开终端），在 sysom-diagnosis（技能根）执行 **`./scripts/osops.sh configure`**（交互式写入 `~/.aliyun/config.json`），再执行 **`./scripts/osops.sh precheck`**。若必须用环境变量，仅在**同一 shell 一条命令**内：`export ... && ./scripts/osops.sh precheck`，且**勿在聊天中发送密钥**。

若 Agent 调用的终端**不支持交互**（无 PTY），`osops configure` 无法读入密钥：在 **COSH** 中可通过 **`/settings`** 使能「**交互式Shell（PTY）**」，或使用 **`/bash`** 进入交互式 Bash，再在技能根执行 **`./scripts/osops.sh configure`**。

#### 步骤 1: 获取 AccessKey

1. 登录 [RAM 控制台](https://ram.console.aliyun.com/)
2. 创建或选择 RAM 用户
3. 创建 AccessKey，记录 `AccessKey ID` 和 `AccessKey Secret`

#### 步骤 2: 配置认证（选择一种方式）

**方式 A: 手动编辑配置文件（推荐）**

创建或编辑 `~/.aliyun/config.json`：

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AK",
      "access_key_id": "LTAI...",
      "access_key_secret": "...",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "zh"
    }
  ],
  "meta_path": ""
}
```

**方式 B: 使用 osops configure 交互式配置**

在 sysom-diagnosis（技能根）执行：

```bash
./scripts/osops.sh configure
```

按提示输入 Access Key ID、Access Key Secret、Region ID（如 `cn-hangzhou`）；Secret 不会回显。

#### 步骤 3: 验证配置

```bash
# 运行预检查（唯一推荐的验证方法）
./scripts/osops.sh precheck
```

预检查命令会自动执行以下检查：
1. 检查 ECS 元数据服务（如果在 ECS 环境中）
2. 检查环境变量中的 AKSK / STS Token
3. 检查 `~/.aliyun/config.json` 配置
4. 调用 SysOM API 验证权限

**预期输出（成功）**：

```json
{
  "ok": true,
  "method": "配置文件 AKSK",
  "message": "认证验证成功，拥有 SysOM 访问权限",
  "check_details": [
    {"method": "ECS元数据", "status": "✗ HTTP 404: 无法访问元数据服务"},
    {"method": "环境变量 AKSK", "status": "✗ 未配置"}
  ]
}
```

**注意**：请使用 `osops precheck` 验证配置，不要使用 `aliyun ecs describe-instances` 等命令，因为 SysOM 需要特定的 API 权限。

---

## 方式 3: STS Token（临时凭证）

### 适用场景

- 通过 `AssumeRole` 等方式获取了临时凭证（`AccessKeyId` / `AccessKeySecret` / `SecurityToken`）
- 希望避免长期 AK/SK，降低密钥泄露风险

### 配置方式 A：环境变量

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="STS.xxx"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="..."
export ALIBABA_CLOUD_SECURITY_TOKEN="CAIS..."
./scripts/osops.sh precheck
```

兼容变量名：
- `ALICLOUD_ACCESS_KEY_ID`
- `ALICLOUD_ACCESS_KEY_SECRET`
- `ALICLOUD_SECURITY_TOKEN`
- `SECURITY_TOKEN`

### 配置方式 B：`~/.aliyun/config.json`（`mode=StsToken`）

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "StsToken",
      "access_key_id": "STS.xxx",
      "access_key_secret": "...",
      "sts_token": "CAIS...",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "zh"
    }
  ],
  "meta_path": ""
}
```

`sts_token` 也可写为 `security_token`（兼容字段）。

### 预期输出（成功）

环境变量方式示例：

```json
{
  "ok": true,
  "method": "环境变量 STS Token",
  "message": "认证验证成功，拥有 SysOM 访问权限"
}
```

配置文件方式示例：

```json
{
  "ok": true,
  "method": "配置文件 STS Token",
  "message": "认证验证成功，拥有 SysOM 访问权限"
}
```

---

## 环境变量方式（用于 Python SDK）

如果直接使用 Python SDK（而非 `aliyun` CLI），可以通过环境变量配置：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID="LTAI..."
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="..."
export ALIBABA_CLOUD_REGION_ID="cn-hangzhou"
# 如果使用 STS 临时凭证，额外配置：
export ALIBABA_CLOUD_SECURITY_TOKEN="CAIS..."
```

或创建 `.env` 文件（推荐用于开发）：

```bash
# 在 sysom-diagnosis 目录创建 .env
cat > .env <<EOF
ALIBABA_CLOUD_ACCESS_KEY_ID=LTAI...
ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
ALIBABA_CLOUD_REGION_ID=cn-hangzhou
# STS 场景可加：
# ALIBABA_CLOUD_SECURITY_TOKEN=CAIS...
EOF

# 确保不提交到 Git
echo ".env" >> .gitignore
```

**注意**：
- 环境变量仅适用于 Python SDK，不适用于 `aliyun` CLI
- SysOM 工具的 `precheck` 命令会检测环境变量配置

---

## 权限配置

### 授予 AliyunSysomFullAccess 权限

无论使用哪种认证方式，都需要授予 **AliyunSysomFullAccess** 权限：

#### 对于 RAM 用户（AK 模式）

1. 登录 [RAM 控制台](https://ram.console.aliyun.com/)
2. 找到对应的 RAM 用户
3. 点击"添加权限"
4. 搜索并选择 `AliyunSysomFullAccess`
5. 确认授权

#### 对于 RAM 角色（ECS RAM Role 模式）

1. 登录 [RAM 控制台](https://ram.console.aliyun.com/)
2. 进入"角色"页面，找到对应角色
3. 点击"添加权限"
4. 搜索并选择 `AliyunSysomFullAccess`
5. 确认授权

### 权限验证

运行 `precheck` 命令验证配置是否正确：

```bash
./scripts/osops.sh precheck
```

预检查命令会自动执行以下检查：
- ✅ 检查 ECS 元数据服务（`curl http://100.100.100.200/latest/meta-data/ram/security-credentials/`）
- ✅ 检查环境变量中的 AKSK / STS Token 配置
- ✅ 检查 `~/.aliyun/config.json` 中的认证配置（AK / StsToken / EcsRamRole）
- ✅ 调用 SysOM API 验证权限是否充足（`InitialSysom`）

**输出示例**：

如果在 ECS 上检测到 RAM 角色但权限不足：
```json
{
  "ok": false,
  "ecs_role_name": "AliyunECSInstanceForSysOM",
  "suggestion": "检测到实例已绑定 RAM 角色 'AliyunECSInstanceForSysOM'，请为该角色授予 AliyunSysomFullAccess 权限"
}
```

如果配置正确：
```json
{
  "ok": true,
  "method": "配置文件 AKSK",
  "message": "认证验证成功，拥有 SysOM 访问权限"
}
```

---

## 安全最佳实践

### 生产环境

1. **优先使用 ECS RAM Role**
   - 零配置，无需管理密钥
   - 自动轮换临时凭证
   
2. **最小权限原则**
   - 只授予必需的权限
   - 定期审计权限使用情况

3. **启用 MFA**
   - 为主账号和关键 RAM 用户启用多因素认证

### 开发环境

1. **使用 .env 文件管理密钥**
   ```bash
   # 添加到 .gitignore
   echo ".env" >> .gitignore
   ```

2. **定期轮换 AccessKey**
   - 建议每 90 天轮换一次
   - 在 RAM 控制台可设置自动轮换

3. **避免硬编码**
   - 不要在代码中硬编码 AccessKey
   - 不要将配置文件提交到 Git

---

## 故障排查

### 问题 1: 预检查失败 - 未找到认证配置

**症状**：
```
✗ 检查失败
  未找到有效的认证配置
```

**解决方案**：
1. 检查配置文件是否存在：`cat ~/.aliyun/config.json`
2. 检查环境变量：`echo $ALIBABA_CLOUD_ACCESS_KEY_ID`
3. 在 sysom-diagnosis（技能根）重新执行：`./scripts/osops.sh configure`

### 问题 2: 权限不足

**症状**：
```
✗ 检查失败
  认证成功但权限不足
```

**解决方案**：
1. 确认已授予 `AliyunSysomFullAccess` 权限
2. 等待 2-5 分钟让权限生效
3. 重新运行 `./scripts/osops.sh precheck`

### 问题 3: ECS RAM Role 不可用

**症状**：
```
✗ 检查失败
  ECS RAM Role 配置失败
```

**解决方案**：
1. 确认实例已绑定 RAM 角色：
   ```bash
   curl http://100.100.100.200/latest/meta-data/ram-role-name
   ```
2. 确认角色有 `AliyunSysomFullAccess` 权限
3. 检查元数据服务是否可访问：
   ```bash
   curl http://100.100.100.200/latest/meta-data/instance-id
   ```

### 问题 4: AccessKey 泄露怎么办？

**立即行动**：
1. 登录 RAM 控制台，禁用泄露的 AccessKey
2. 创建新的 AccessKey
3. 更新所有使用该 AccessKey 的配置
4. 审查近期操作日志，排查异常行为

---

## 参考资源

- [阿里云 CLI 认证方式](https://help.aliyun.com/zh/cli/configure-credentials)
- [ECS RAM 角色配置](https://help.aliyun.com/zh/ecs/user-guide/attach-an-instance-ram-role-to-an-ecs-instance)
- [RAM 权限管理](https://help.aliyun.com/zh/ram/user-guide/overview)
- [SysOM API 文档](https://help.aliyun.com/zh/sysom)
- [ECS Metadata 服务](./metadata-api.md)
