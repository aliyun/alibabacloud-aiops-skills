# Alibaba Cloud CLI Installation Guide

This skill requires Alibaba Cloud CLI because all diagnosis data is collected
through read-only Alibaba Cloud APIs.

## macOS

```bash
brew install aliyun-cli
```

## Linux

Download the official CLI package from Alibaba Cloud:

```bash
curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz
sudo mv aliyun /usr/local/bin/
```

## Configure Credentials

Configure credentials through the aliyun CLI default credential chain. A local
CLI profile is the recommended local setup:

```bash
aliyun configure
```

For AgentHub evaluation, use the platform-provided account or role-assumption
configuration in the evaluation UI. The skill scripts delegate authentication
to the aliyun CLI default chain. If no local CLI profile is configured, the
environment-backed default provider may be used as the fallback.

## Verify

```bash
aliyun version
aliyun ecs describe-instances --region cn-hangzhou --read-timeout 30 --connect-timeout 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-network-diagnose/00000000000000000000000000000000
```

The verification command is read-only.
