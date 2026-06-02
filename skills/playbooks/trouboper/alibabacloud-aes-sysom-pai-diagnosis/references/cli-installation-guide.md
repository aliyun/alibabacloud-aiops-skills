# Aliyun CLI Installation and Configuration Guide

This skill requires `aliyun` CLI version **>= 3.3.1**.

---

## Check Current Version

```bash
aliyun version
```

If the version is lower than `3.3.1`, follow the installation steps below.

---

## Installation

### macOS (Homebrew)

```bash
brew install aliyun-cli
```

### macOS / Linux (Manual Download)

```bash
# macOS amd64
curl -O https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz
tar xzf aliyun-cli-macosx-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Linux amd64
curl -O https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/
```

### Windows

Download from the [official release page](https://github.com/aliyun/aliyun-cli/releases) and extract `aliyun.exe` into your `PATH`.

---

## Post-Installation Configuration

### 1. Enable AI-Mode (required by this skill)

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-pai-diagnosis"
```

### 2. Update Plugins

```bash
aliyun plugin update
```

### 3. Enable Auto Plugin Install

```bash
aliyun configure set --auto-plugin-install true
```

### 4. Verify Credentials

```bash
aliyun configure list
```

If no valid profile exists (AK / STS / OAuth identity), configure credentials **outside the conversation session** via `aliyun configure` in your terminal or via environment variables in your shell profile.

> **⚠️ Credential Security**: NEVER paste AccessKey ID / Secret values into the AI conversation. Configure them locally and verify only via `aliyun configure list`.

---

## Plugin Requirements

This skill depends on the following CLI plugins (auto-installed when `--auto-plugin-install` is enabled):

| Plugin | Used For |
|--------|----------|
| `sysom` | SysOM diagnosis APIs (`initial-sysom`, `invoke-diagnosis`, `get-diagnosis-result`) |
| `eas` | PAI EAS APIs (`list-services` with `--filter`) |

Verify both plugins are installed:

```bash
aliyun plugin list
```
