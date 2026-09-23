# Aliyun CLI Installation Guide

## Install / Update

```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
```

Verify:

```bash
aliyun version
# Must be >= 3.3.3
```

## Enable Auto-Plugin Install

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

## Configure Credentials

```bash
aliyun configure
```

Or use an existing profile:

```bash
aliyun configure --profile waf-test
```

Verify credentials are configured:

```bash
aliyun configure list
```

## Platform-Specific Notes

### macOS

Homebrew is also available:

```bash
brew install aliyun-cli
```

### Linux

```bash
# x86_64
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash

# aarch64
curl -fsSL https://aliyuncli.alicdn.com/setup_arm64.sh | bash
```

### Windows

Download from: https://github.com/aliyun/aliyun-cli/releases
