# Aliyun CLI Installation and Configuration Guide

This Skill invokes Alibaba Cloud WAF 3.0 OpenAPI through `aliyun-cli`. The CLI must be installed and configured beforehand.

## Installation

### macOS (Homebrew recommended)

```bash
brew install aliyun-cli
brew upgrade aliyun-cli

aliyun version
```

### Linux

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

aliyun version
```

### Windows

1. Download: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract and add the directory to your system PATH
3. Run `aliyun version` to verify

Version >= 3.3.3 is required.

## Configure Credentials

> **Security reminder**: The commands below are for users to run **outside of an Agent session**. When executing this Skill, the Agent must only use `aliyun configure list` to verify credential status and must never run `aliyun configure set` with plaintext AK/SK.

### AK Mode

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

### Multiple Profiles

```bash
aliyun configure set --profile production \
  --mode AK \
  --access-key-id <ak> \
  --access-key-secret <sk> \
  --region cn-hangzhou

export ALIBABA_CLOUD_PROFILE=production
```

## Verification

```bash
# Check credential status
aliyun configure list

# Test permissions
aliyun waf-openapi describe-instance \
  --version 2021-10-01 --force --region cn-hangzhou \
  --read-timeout 30 --connect-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

## References

- Official documentation: https://help.aliyun.com/zh/cli/
- Configure credentials: https://help.aliyun.com/zh/cli/configure-credentials
