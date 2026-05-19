# 阿里云CLI配置指南

## 版本要求

阿里云 CLI >= 3.3.3。运行 `aliyun version` 查看当前版本。

## 安装阿里云CLI

### Linux/macOS（推荐：分步安装）
```bash
# 1. 下载安装包
curl -fsSL -o /tmp/aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# 2. 校验文件完整性（确保下载未被篡改）
#    获取官方 SHA256 校验和
curl -fsSL -o /tmp/aliyun-cli.tgz.sha256 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz.sha256
#    执行校验
cd /tmp && shasum -a 256 -c aliyun-cli.tgz.sha256

# 3. 解压并安装
tar xzf /tmp/aliyun-cli.tgz -C /tmp
sudo mv /tmp/aliyun /usr/local/bin/

# 4. 验证安装
aliyun version
```

### macOS (Homebrew)
```bash
brew install aliyun-cli
aliyun version
```

### Windows (PowerShell)
```powershell
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "$env:TEMP\aliyun-cli.zip"
Expand-Archive -Path "$env:TEMP\aliyun-cli.zip" -DestinationPath "$env:TEMP\aliyun-cli" -Force
Move-Item "$env:TEMP\aliyun-cli\aliyun.exe" "$env:LOCALAPPDATA\Microsoft\WindowsApps\" -Force
aliyun version
```

## 配置AccessKey
```bash
aliyun configure
# 按提示输入：
# Access Key ID: [您的AccessKey ID]
# Access Key Secret: [您的AccessKey Secret]
# Default Region Id: cn-shanghai
# Default Output Format: json
```

## 配置 AI-Mode
阿里云 CLI 提供了 AI 模式。启用后，CLI 会自动附加Skill身份信息，使服务端能够识别并优化技能调用链路。
```bash
# Enable AI-Mode
aliyun configure ai-mode enable

# Set AI-Mode user-agent identifier
aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill

# View AI-Mode configuration
aliyun configure ai-mode show

# Aliyun CLI Plugin Update
aliyun plugin update

# Disable AI-Mode
aliyun configure ai-mode disable
```

## 验证配置
```bash
aliyun configure list
aliyun ehpcinstant ListJobs --region cn-shanghai \
    --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ehpc-instant-job-skill
```

## 常见问题
- **认证失败**：检查 `~/.aliyun/config.json` 文件中的 AccessKey 配置
- **区域错误**：确保使用正确的区域（如 cn-shanghai）
- **权限不足**：确保 AccessKey 具有 E-HPC Instant 相关权限