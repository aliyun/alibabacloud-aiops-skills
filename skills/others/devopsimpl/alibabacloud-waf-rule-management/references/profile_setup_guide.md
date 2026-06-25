# 阿里云 CLI Profile 配置指南

> 本文档提供阿里云CLI profile的配置指导，适用于首次使用本skill的用户。

---

## 📋 什么是Profile？

Profile是阿里云CLI用来存储认证信息（AccessKey ID、AccessKey Secret等）的配置项。使用profile可以：
- ✅ 安全地管理多套账号/环境
- ✅ 避免在命令中明文传递密钥
- ✅ 提高命令的可移植性和安全性

---

## 🔧 配置步骤

### 前置条件：安装阿里云CLI

**macOS (使用Homebrew)**：
```bash
brew install aliyun-cli
aliyun version  # 验证版本 >= 3.3.3
```

**Linux**：
```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/
aliyun version
```

**Windows**：
1. 下载：https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. 解压并添加到PATH环境变量
3. 验证：`aliyun version`

---

### 第1步：获取AccessKey

1. 登录阿里云RAM控制台：https://ram.console.aliyun.com
2. 在左侧导航栏选择 **人员管理** → **用户**
3. 找到您要使用的RAM用户，点击进入详情
4. 点击 **创建AccessKey** 或使用已有的AccessKey
5. ⚠️ **立即保存AccessKey Secret**（只显示一次）

> **安全提示**：
> - ❌ 不要使用阿里云主账号的AccessKey
> - ✅ 创建RAM用户并遵循最小权限原则
> - ✅ 定期轮换AccessKey

---

### 第2步：配置Profile（交互式）

运行以下命令，按提示输入信息：

```bash
aliyun configure
```

系统会提示您输入：
- **Access Key Id**: 粘贴您的AccessKey ID
- **Access Key Secret**: 粘贴您的AccessKey Secret
- **Default Region Id**: 输入 `cn-hangzhou`（国内服务）或 `ap-southeast-1`（海外服务）
- **Default Output Format**: 直接回车（默认json）
- **Default Language**: 输入 `zh`（中文）

---

### 第2步（替代方案）：配置Profile（非交互式）

如果您希望在脚本中自动配置，可以使用非交互式命令：

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

> ⚠️ **安全警告**：非交互式命令会在shell历史中留下密钥记录，建议使用交互式配置或在使用后清理shell历史。

---

### 第3步：配置SLS日志查询凭证（仅WAF技能需要）

WAF日志查询使用`aliyunlog`工具，需要单独配置：

```bash
# 安装aliyunlog（如果未安装）
pip3 install aliyun-log-cli

# 配置凭证
aliyunlog configure
```

按提示输入相同的AccessKey ID和Secret。

---

## ✅ 验证配置

### 验证aliyun CLI

```bash
# 查看所有profile
aliyun configure list

# 测试认证（查询可用区域）
aliyun ecs describe-regions --profile <profile-name> --user-agent AlibabaCloud-Agent-Skills
```

如果配置成功，您将看到JSON格式的区域列表。

### 验证aliyunlog（WAF技能）

```bash
# 测试STS身份获取
aliyun sts get-caller-identity --profile <profile-name> --user-agent AlibabaCloud-Agent-Skills
```

如果配置成功，您将看到AccountId等信息。

---

## 📂 Profile存储位置

配置文件存储在：`~/.aliyun/config.json`

示例内容：
```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AK",
      "access_key_id": "LTAI5tXXXXXXXX",
      "access_key_secret": "8dXXXXXXXXXXXXXXXXXXXXXXXX",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "zh"
    }
  ]
}
```

> 🔒 **安全提示**：确保此文件权限正确：`chmod 600 ~/.aliyun/config.json`

---

## 🔀 管理多个Profile

### 创建命名Profile

```bash
aliyun configure set --profile waf-diag \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

### 使用特定Profile

```bash
# 在命令中指定
aliyun waf-openapi describe-instance --profile waf-diag --user-agent AlibabaCloud-Agent-Skills

# 或通过环境变量
export ALIBABA_CLOUD_PROFILE=waf-diag
aliyun waf-openapi describe-instance --user-agent AlibabaCloud-Agent-Skills
```

### 列出和切换Profile

```bash
# 列出所有profile
aliyun configure list

# 切换默认profile
aliyun configure set --current waf-diag
```

---

## 🔐 认证模式

本skill支持以下认证模式：

| 模式 | 适用场景 | 配置示例 |
|------|---------|---------|
| **AK** | 个人账号/脚本 | `aliyun configure --mode AK` |
| **StsToken** | 临时访问（1-12小时） | `aliyun configure --mode StsToken` |
| **EcsRamRole** | ECS实例RAM角色 | `aliyun configure --mode EcsRamRole` |
| **RamRoleArn** | 跨账号/提权访问 | `aliyun configure --mode RamRoleArn` |

> 💡 **推荐**：日常使用AK模式即可，企业环境建议使用RAM角色或STS临时凭证。

---

## 🚨 常见问题

### Q: 命令返回"InvalidAccessKeyId.NotFound"
**A**: AccessKey ID错误，请检查是否正确复制。

### Q: 命令返回"SignatureDoesNotMatch"
**A**: AccessKey Secret错误，请重新配置。

### Q: 命令返回"Forbidden.RAM"
**A**: 权限不足，请检查RAM用户是否附加了正确的策略。

### Q: 找不到aliyun命令
**A**: 未安装或未添加到PATH，请参考前置条件重新安装。

### Q: aliyunlog命令不存在
**A**: 需要单独安装：`pip3 install aliyun-log-cli`

---

## 📚 参考资源

- 官方文档：https://help.aliyun.com/zh/cli/
- RAM控制台：https://ram.console.aliyun.com/
- AccessKey管理：https://ram.console.aliyun.com/manage/ak

---

## 🔒 安全最佳实践

1. **使用RAM用户而非主账号**：创建专门的RAM用户并授予最小权限
2. **定期轮换密钥**：建议每90天更换一次AccessKey
3. **使用临时凭证**：对于CI/CD或临时访问，使用STS Token
4. **保护配置文件**：`chmod 600 ~/.aliyun/config.json`
5. **不要提交密钥到代码库**：将config.json添加到.gitignore

---

> 配置完成后，您就可以使用本skill进行WAF/云防火墙的诊断和查询了！
