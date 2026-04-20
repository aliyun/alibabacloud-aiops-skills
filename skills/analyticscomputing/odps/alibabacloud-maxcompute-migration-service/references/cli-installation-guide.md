# CLI Installation Guide

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

## Configuration

### Quick Start

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

**Where to Get Access Keys**

1. Log in to Aliyun Console: https://ram.console.aliyun.com/
2. Navigate to: AccessKey Management
3. Create a new AccessKey pair
4. Save the secret immediately — it's only shown once

### Environment Variables

**Access Key Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

### Verification

```bash
# Basic test - list regions
aliyun ecs describe-regions

# Expected output: JSON array of regions
```

## Plugin Installation

After installing CLI 3.3.1+, enable automatic plugin installation:

```bash
aliyun configure set --auto-plugin-install true
```

Install specific product plugins:

```bash
aliyun plugin install --names maxcompute
```
