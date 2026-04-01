# Aliyun CLI Installation Guide

Complete guide for installing Aliyun CLI.

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
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz

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
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**CentOS/RHEL**
```bash
# Download
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**ARM64 Architecture**
```bash
# Download ARM64 version
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

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

---

## Configuration

> **Important**: For credential configuration (AccessKey, STS Token, RAM Role, etc.), please refer to the official Alibaba Cloud documentation:
> - [CLI Configuration Guide](https://help.aliyun.com/zh/cli/configure-aliyun-cli)
> - [Authentication Methods](https://help.aliyun.com/zh/cli/configure-credentials)

### Recommended Authentication Methods

For production and automated environments, we recommend:

1. **EcsRamRole Mode** (Running on ECS instances)
   - No credentials needed in configuration
   - Uses the RAM role attached to the ECS instance
   - See official docs for setup

2. **RamRoleArn Mode** (Cross-account access)
   - Assumes a RAM role for temporary credentials
   - See official docs for setup

### Verification

```bash
# Basic test - list regions
aliyun ecs describe-regions

# Expected output: JSON array of regions
```

---

## Install Plugins

After CLI installation, install required plugins:

```bash
# Install commonly used plugins
aliyun plugin install --names ecs vpc rds cms nis

# List all available plugins
aliyun plugin list-remote

# Verify installed plugins
aliyun plugin list
```

---

## Troubleshooting

### Issue: Command Not Found

```bash
# Check installation
which aliyun

# Check PATH
echo $PATH

# Reinstall or add to PATH
```

### Issue: Plugin Not Found

```bash
# Install missing plugin
aliyun plugin install --names <plugin-name>

# Example: Install NIS plugin
aliyun plugin install --names nis
```

### Issue: Wrong Region

```bash
# Some resources may not exist in the specified region

# Check available regions
aliyun ecs describe-regions
```

---

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- Plugin Repository: https://github.com/aliyun/aliyun-cli
