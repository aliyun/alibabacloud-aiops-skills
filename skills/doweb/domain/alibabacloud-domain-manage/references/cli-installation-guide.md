# Aliyun CLI Installation & Configuration Guide

## Version Requirement

> **Aliyun CLI >= 3.3.3 is REQUIRED.**

Check current version:
```bash
aliyun version
```

If CLI is not installed or version is below 3.3.3, follow the installation steps below.

## Installation

### Quick Install (All Platforms)

```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
aliyun version
```

### macOS

```bash
# Using Homebrew (Recommended)
brew install aliyun-cli
brew upgrade aliyun-cli

# Or download binary
curl -sSL https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz | tar xz
sudo mv aliyun /usr/local/bin/
```

### Linux

```bash
# x86_64
curl -sSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz
sudo mv aliyun /usr/local/bin/

# ARM64
curl -sSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz | tar xz
sudo mv aliyun /usr/local/bin/
```

### Windows

Download from: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip

Unzip and add `aliyun.exe` to your system PATH.

## Post-Installation Configuration

### Enable Auto Plugin Installation

**[MUST]** Run this command after installation:

```bash
aliyun configure set --auto-plugin-install true
```

### Update Plugins

**[MUST]** Ensure plugins are up-to-date:

```bash
aliyun plugin update
```

### Configure Credentials

1. Obtain AccessKey from: https://ram.console.aliyun.com/manage/ak
2. Configure credentials in terminal:
   ```bash
   aliyun configure
   ```
3. Or use environment variables:
   ```bash
   export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-ak>
   export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-sk>
   ```

> **SECURITY**: NEVER ask users to input AK/SK directly in the chat conversation.

## Domain API Special Notes

- **No Region Required**: Domain API is a **global service**. Do NOT pass `--region-id` parameter.
- **Product Code**: Always use `domain` (lowercase) as the product code.
- **User-Agent**: All commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage`.

## Verify Installation

```bash
# Check version
aliyun version

# Verify domain plugin works (requires valid credentials)
aliyun domain query-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `command not found: aliyun` | CLI not in PATH; reinstall or add to PATH |
| `Error: plugin domain not found` | Run `aliyun configure set --auto-plugin-install true` then retry |
| `SDK.ServerError: InvalidVersion` | CLI version too old; upgrade to >= 3.3.3 |
| `Error: No credential found` | Run `aliyun configure` to set up credentials |

## Reference

- Official CLI Documentation: https://help.aliyun.com/zh/cli/
- CLI GitHub Repository: https://github.com/aliyun/aliyun-cli
