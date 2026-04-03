# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> **Aliyun CLI 3.3.1+**: Supports installing and using all published Alibaba Cloud product plugins. Make sure to upgrade to 3.3.1 or later for full plugin ecosystem coverage.

## Installation

### macOS

**Using Homebrew (Recommended)**
```bash
brew install aliyun-cli
# Upgrade to latest
brew upgrade aliyun-cli

# Verify version (>= 3.3.1)
aliyun version
```

**Using Binary**
```bash
# Download
wget --connect-timeout=10 --read-timeout=60 https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz

# Extract
tar -xzf aliyun-cli-macosx-latest-amd64.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

### Linux

**Debian/Ubuntu**
```bash
# Download
wget --connect-timeout=10 --read-timeout=60 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**CentOS/RHEL**
```bash
# Download
wget --connect-timeout=10 --read-timeout=60 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**ARM64 Architecture**
```bash
# Download ARM64 version
wget --connect-timeout=10 --read-timeout=60 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/
```

### Windows

**Using Binary**
1. Download from: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract the ZIP file
3. Add the directory to your PATH environment variable
4. Open new Command Prompt or PowerShell
5. Verify: `aliyun version`

**Using PowerShell**
```powershell
# Download
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"

# Extract
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli

# Add to PATH (requires admin privileges)
$env:Path += ";C:\aliyun-cli"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)

# Verify
aliyun version
```

## Configuration

> **安全警告 / SECURITY WARNING**
> 
> 本技能严禁显式处理 AK/SK 凭证，应依赖默认凭证链。
> **仅支持 OAuth 认证模式**，无需管理 AccessKey。
> 
> This skill prohibits explicit handling of AK/SK credentials.
> **Only OAuth authentication mode is supported** - no AccessKey management required.

### Quick Start (OAuth Mode - Required)

```bash
# OAuth 模式登录（唯一支持的模式）
aliyun configure --mode OAuth
```

### ECS RAM Role Mode (For ECS Instances)

如果在 ECS 实例上运行，可以使用实例 RAM 角色，无需任何凭证：

```bash
aliyun configure set \
  --mode EcsRamRole \
  --ram-role-name MyEcsRole \
  --region cn-hangzhou
```

要求：必须在绑定了 RAM 角色的 ECS 实例上运行。

## Verification

### Test Authentication

```bash
# 检查认证状态
aliyun configure list

# 基本测试 - 列出地域
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills
```

**If successful**, you'll see:
```json
{
  "Regions": {
    "Region": [
      {
        "RegionId": "cn-hangzhou",
        "RegionEndpoint": "ecs.cn-hangzhou.aliyuncs.com",
        "LocalName": "华东 1（杭州）"
      },
      ...
    ]
  },
  "RequestId": "..."
}
```

**If failed**, you'll see error messages:
- `Forbidden.RAM` - Insufficient permissions
- `OAuth token expired` - Re-run `aliyun configure --mode OAuth`

### Debug Configuration

```bash
# Show current configuration
aliyun configure get

# Test with debug logging
aliyun ecs describe-regions --log-level=debug --user-agent AlibabaCloud-Agent-Skills

# Check credential provider
aliyun configure get mode
```

## Security Best Practices

### 1. Use OAuth Mode (Required for This Skill)

```bash
aliyun configure --mode OAuth
```

### 2. Use RAM Users (Not Root Account)

✔️ **Do**: Create RAM users with specific permissions
✔️ **Do**: Use OAuth login for RAM users

### 3. Principle of Least Privilege

Grant only the minimum permissions needed in RAM Console.

### 4. Use ECS RAM Roles When Running on ECS

```bash
aliyun configure set --mode EcsRamRole --ram-role-name MyRole --region cn-hangzhou
```

### 5. Secure Config File

```bash
# Restrict permissions
chmod 600 ~/.aliyun/config.json
```

## Troubleshooting

### Issue: Command Not Found

```bash
# Check installation
which aliyun

# Check PATH
echo $PATH

# Reinstall or add to PATH
```

### Issue: Authentication Failed

```bash
# Verify configuration
aliyun configure list

# Re-authenticate with OAuth
aliyun configure --mode OAuth

# Test with debug
aliyun ecs describe-regions --log-level=debug --user-agent AlibabaCloud-Agent-Skills
```

### Issue: Permission Denied

```bash
# Error: Forbidden.RAM

# Check RAM user permissions in RAM console
# Attach necessary policies
# Example: AliyunECSFullAccess for ECS operations
```

### Issue: Wrong Region

```bash
# Some resources may not exist in the specified region

# Check available regions
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills

# Update default region
aliyun configure set region cn-shanghai
```

## Advanced Configuration

### Custom Endpoint

```bash
# Use custom or private endpoint
export ALIBABA_CLOUD_ECS_ENDPOINT=ecs-vpc.cn-hangzhou.aliyuncs.com
```

### Proxy Settings

```bash
# HTTP proxy
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# No proxy for specific domains
export NO_PROXY=localhost,127.0.0.1,.aliyuncs.com
```

### Timeout Settings

```bash
# Connection timeout (default: 10s)
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30

# Read timeout (default: 10s)
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

## Next Steps

After installation and configuration:

1. **Install plugins** for services you need (v3.3.1+ supports all published product plugins):
   ```bash
   aliyun plugin install --names ecs vpc rds

   # List all available plugins
   aliyun plugin list-remote
   ```

2. **Explore commands**:
   ```bash
   aliyun ecs --help
   aliyun fc --help
   ```

3. **Read documentation**:
   - [Command Syntax Guide](./command-syntax.md)
   - [Global Flags Reference](./global-flags.md)
   - [Common Scenarios](./common-scenarios.md)

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Plugin Repository: https://github.com/aliyun/aliyun-cli
