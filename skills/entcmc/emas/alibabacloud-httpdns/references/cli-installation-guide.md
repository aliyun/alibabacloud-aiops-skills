# Alibaba Cloud CLI Installation Guide

This reference is used only when `aliyun` is not installed or the installed
version is older than `3.3.3`.

## macOS

```bash
brew install aliyun-cli
aliyun version
```

## Linux

```bash
curl -fsSL https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz
mkdir -p "$HOME/.local/bin"
mv aliyun "$HOME/.local/bin/"
export PATH="$HOME/.local/bin:$PATH"
aliyun version
```

Do not request elevated privileges or move binaries into system directories from
this skill. If a system-wide installation is required, the user should perform it
outside the agent workflow according to their organization's workstation policy.

## Configure credentials

Do not ask the agent to read or print credential files. Let the user configure
the profile interactively:

```bash
aliyun configure --mode AK --profile <profileName>
aliyun configure list
```

## Plugin setup

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun httpdns --help
```
