# Aliyun CLI Installation & Configuration Guide

> **Aliyun CLI 3.3.1+** required for full plugin ecosystem support.

## Installation

### macOS (Homebrew)

```bash
brew install aliyun-cli
brew upgrade aliyun-cli
aliyun version  # verify >= 3.3.1
```

### macOS (Binary)

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz
tar -xzf aliyun-cli-macosx-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/
aliyun version
```

### Linux

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/
aliyun version
```

### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli
$env:Path += ";C:\aliyun-cli"
aliyun version
```

## Configuration

```bash
# Interactive configuration
aliyun configure

# Or set via environment variables (see official docs for details)
# Note: AK/SK should be configured through `aliyun configure` or credential files,
# not echoed/printed in chat. See SKILL.md security rules.
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

## Enable Auto Plugin Install

```bash
aliyun configure set --auto-plugin-install true
```

## Verification

```bash
aliyun ecs describe-regions --user-agent AlibabaCloud-Agent-Skills   # test authentication
aliyun configure list         # show current configuration
```

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak
