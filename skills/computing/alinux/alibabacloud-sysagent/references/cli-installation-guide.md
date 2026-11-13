# Aliyun CLI Installation Guide

Install or upgrade the Aliyun CLI host used by SysAgent. SysAgent needs **Aliyun CLI 3.4.0 or later**. If the selected executable is already compatible, keep it and return to [SysAgent CLI Setup](setup.md#2-install-or-update-the-sysom-plugin).

## Installation

### macOS with Homebrew

```bash
brew install aliyun-cli
```

For a Homebrew-managed installation that is already present:

```bash
brew upgrade aliyun-cli
```

### Linux or macOS without Homebrew

To use the official installer:

```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/install.sh)"
```

For a manual installation, use the archive for your platform from the [official Alibaba Cloud CLI guide](https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli). Check the architecture with `uname -m` if selecting a Linux package. Prefer a user-writable installation if you do not manage the system package directory. For Windows, follow the official guide's Windows instructions.

### Existing standalone installation

If the existing CLI supports the built-in upgrade command, use it:

```bash
aliyun upgrade
```

If `upgrade` is unavailable or the Host is too old, reinstall using the official installation method for the platform. Use the package manager for installations it manages.

## Verification

```bash
command -v aliyun
aliyun version
```

Confirm that this executable is the one you intended to install or update. If another copy is earlier on PATH, use the compatible absolute path for subsequent commands. Continue with [plugin setup and credentials](setup.md) after the version check passes.
