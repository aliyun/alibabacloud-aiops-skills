# CLI Installation Guide

## macOS

```bash
# Recommended: One-click install script
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash

# Or use Homebrew
brew install aliyun-cli
```

## Linux

```bash
# One-click install script
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
```

## Windows

Download and install from GitHub Releases: https://github.com/aliyun/aliyun-cli/releases

## Verify Installation

```bash
aliyun version
# Requires >= 3.3.3
```

## Enable Auto Plugin Install & Update

```bash
# Enable auto plugin install
aliyun configure set --auto-plugin-install true

# Update all installed plugins to latest version
aliyun plugin update
```

## Verify Credentials

```bash
# Check current configuration (view status only, never print credential values)
aliyun configure list
```

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
> - Configure credentials **outside of agent sessions** via `aliyun configure` in terminal

## Reference Documentation

- Alibaba Cloud CLI Official Docs: https://help.aliyun.com/zh/cli/
- Calling RPC/ROA APIs: https://help.aliyun.com/zh/cli/call-rpc-api-and-roa-api
