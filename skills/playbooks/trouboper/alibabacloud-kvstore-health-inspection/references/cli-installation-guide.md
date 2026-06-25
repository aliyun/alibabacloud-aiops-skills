# Aliyun CLI Installation Guide

This guide covers installation, configuration, and troubleshooting of the Aliyun CLI for the KVStore health inspection tool.

## Prerequisites

- **Operating System**: Linux, macOS, or Windows
- **Python**: Version 3.7 or higher
- **Network**: Internet access to download CLI and plugins

## Installation

### Linux

#### Using curl (recommended)

```bash
curl -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/
```

#### Using package manager

**Ubuntu/Debian:**
```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | sudo bash
```

**CentOS/RHEL:**
```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | sudo bash
```

### macOS

#### Using Homebrew (recommended)

```bash
brew install aliyun-cli
```

#### Using curl

```bash
curl -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-darwin-latest-amd64.tgz
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/
```

### Windows

#### Using installer

1. Download the installer from: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract the zip file
3. Add the extracted directory to your system PATH

#### Using Chocolatey

```powershell
choco install aliyun-cli
```

## Verification

After installation, verify the CLI is working:

```bash
aliyun version
```

Expected output:
```
aliyun version 3.x.x
```

## Configuration

### Basic Configuration

Configure your AccessKey credentials:

```bash
aliyun configure
```

You will be prompted for:
- **AccessKey ID**: Your Alibaba Cloud AccessKey ID
- **AccessKey Secret**: Your Alibaba Cloud AccessKey Secret
- **Default Region ID**: Default region (e.g., cn-hangzhou, cn-shanghai)
- **Default Language**: Language preference (en or zh)

### Multiple Profiles

For multiple accounts or environments:

```bash
# Create a profile
aliyun configure --profile production
aliyun configure --profile development

# Use a specific profile (use kebab-case plugin form, with SA-2.11 --user-agent)
aliyun r-kvstore describe-instances \
  --profile production \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}"

# Set default profile
aliyun configure set --profile production
```

### Environment Variables

Alternatively, use environment variables:

```bash
export ALICLOUD_ACCESS_KEY="your-access-key-id"
export ALICLOUD_SECRET_KEY="your-access-key-secret"
export ALICLOUD_REGION="cn-hangzhou"
```

## Plugin Management

The KVStore inspection tool requires specific CLI plugins. The tool automatically installs them, but you can manage them manually:

### List Installed Plugins

```bash
aliyun plugin list
```

### Install Plugins

```bash
# R-KVStore plugin
aliyun plugin install --name aliyun-cli-r-kvstore

# DAS plugin
aliyun plugin install --name aliyun-cli-das

# CloudMonitor plugin
aliyun plugin install --name aliyun-cli-cms
```

### Update Plugins

```bash
aliyun plugin update
```

### Uninstall Plugins

```bash
aliyun plugin uninstall --name aliyun-cli-r-kvstore
```

### Enable Auto-Install

Enable automatic plugin installation:

```bash
aliyun configure set --auto-plugin-install true
```

## Troubleshooting

### Common Issues

#### 1. Command not found: aliyun

**Problem**: CLI is not in PATH

**Solution**:
```bash
# Find aliyun location
which aliyun || find / -name aliyun 2>/dev/null

# Add to PATH (adjust path as needed)
export PATH=$PATH:/usr/local/bin
```

#### 2. Plugin installation fails

**Problem**: Network issues or plugin repository unavailable

**Solution**:
```bash
# Retry with verbose output
aliyun plugin install --name aliyun-cli-r-kvstore --verbose

# Manual plugin download
curl -o plugin.zip https://aliyuncli.alicdn.com/plugins/aliyun-cli-r-kvstore-latest.zip
```

#### 3. "text file busy" error

**Problem**: Plugin file is locked during installation

**Solution**:
```bash
# Wait and retry
sleep 2
aliyun plugin install --name aliyun-cli-r-kvstore

# Or sync filesystem
sync
aliyun plugin install --name aliyun-cli-r-kvstore
```

#### 4. Authentication errors

**Problem**: Invalid or expired credentials

**Solution**:
```bash
# Reconfigure credentials
aliyun configure

# Verify configuration
aliyun configure list
```

#### 5. Throttling errors

**Problem**: Too many API requests

**Solution**:
- The inspection tool includes automatic retry with exponential backoff
- Reduce inspection frequency
- Contact Alibaba Cloud to increase API quota

### Debug Mode

Enable debug output for troubleshooting:

```bash
aliyun r-kvstore describe-instances \
  --debug \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-kvstore-health-inspection/${ALICLOUD_SKILL_SESSION_ID}"
```

## Upgrading

### Linux/macOS

```bash
# Download latest version
curl -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/

# Or using package manager (Ubuntu/Debian/CentOS/RHEL)
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | sudo bash

# Or using Homebrew (macOS)
brew upgrade aliyun-cli
```

### Windows

Download the latest installer and run it, or use Chocolatey:

```powershell
choco upgrade aliyun-cli
```

## Uninstallation

### Linux/macOS

```bash
sudo rm /usr/local/bin/aliyun
rm -rf ~/.aliyun
```

### Windows

1. Remove the aliyun directory from PATH
2. Delete the aliyun folder (usually in C:\Users\<username>\.aliyun)

## Additional Resources

- **Official Documentation**: https://help.aliyun.com/document_detail/139508.html
- **GitHub Repository**: https://github.com/aliyun/aliyun-cli
- **API Explorer**: https://api.aliyun.com/
- **Support**: https://www.alibabacloud.com/support

## Next Steps

After installing and configuring the CLI:

1. Verify permissions (see [RAM Policies](ram-policies.md))
2. Run your first inspection:
   ```bash
   python3 scripts/health-inspect.py <instance-id>
   ```
3. Review the generated report in `~/Downloads/`
