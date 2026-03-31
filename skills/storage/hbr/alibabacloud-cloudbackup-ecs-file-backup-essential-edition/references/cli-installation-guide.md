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
wget --timeout=30 --connect-timeout=10 https://aliyuncli.alicdn.com/aliyun-cli-macosx-3.3.3-amd64.tgz

# Extract
tar -xzf aliyun-cli-macosx-3.3.3-amd64.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

### Linux

**Debian/Ubuntu**
```bash
# Download
wget --timeout=30 --connect-timeout=10 https://aliyuncli.alicdn.com/aliyun-cli-linux-3.3.3-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-3.3.3-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**ARM64 Architecture**
```bash
# Download ARM64 version
wget --timeout=30 --connect-timeout=10 https://aliyuncli.alicdn.com/aliyun-cli-linux-3.3.3-arm64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-3.3.3-arm64.tgz
sudo mv aliyun /usr/local/bin/
```

### Windows

**Using Binary**
1. Download from: https://aliyuncli.alicdn.com/aliyun-cli-windows-3.3.3-amd64.zip
2. Extract the ZIP file
3. Add the directory to your PATH environment variable
4. Open new Command Prompt or PowerShell
5. Verify: `aliyun version`

## Configuration

Aliyun CLI relies on the default credential chain for authentication. Run `aliyun configure` interactively to set up credentials:

```bash
aliyun configure
```

The default credential chain resolves credentials in the following order:
1. Environment variables (automatically detected by the CLI)
2. Configuration file (`~/.aliyun/config.json`)
3. Instance metadata (ECS instance role, available when running on ECS)

> **Security**: Do not pass access keys explicitly via command-line arguments or hardcode them in scripts. Always rely on the default credential chain.

**Where to Get Credentials**

1. Log in to Aliyun Console: https://ram.console.aliyun.com/
2. Navigate to: AccessKey Management
3. Create a new AccessKey pair
4. Save the secret immediately — it's only shown once

## Verification

```bash
# Basic test - list regions
aliyun ecs describe-regions

# Show current configuration
aliyun configure get
```

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak
