# Alibaba Cloud CLI Installation Guide

Aliyun CLI is the core external dependency of this Skill. All Alibaba Cloud OpenAPI read-only calls and profile credential resolution (`~/.aliyun/config.json`) depend on aliyun CLI. Ensure it is installed with valid credentials and the version meets requirements.

## First-Time Installation

First-time installation (macOS / Linux, via the official setup script). Always download and review the script before executing -- never pipe remote output directly into a shell:

```bash
# Step 1: Download the setup script for local review
curl -fsSL --connect-timeout 10 --max-time 120 \
  -o /tmp/aliyun-setup.sh \
  https://aliyuncli.alicdn.com/setup.sh

# Step 2: Inspect the script content before execution
less /tmp/aliyun-setup.sh

# Step 3: Execute only after confirming the script is safe
/bin/bash /tmp/aliyun-setup.sh && rm /tmp/aliyun-setup.sh
```

> The setup script automatically detects the system architecture and installs the latest aliyun CLI to PATH. After installation, run [Version Verification](#version-verification) to confirm.

## Routine Update (CLI >= 3.3.5)

When already installed and version >= 3.3.5, use the built-in self-upgrade command (no need to re-run the setup script):

```bash
aliyun upgrade
```

> If the current version is below 3.3.5 and does not support `aliyun upgrade`, re-run the setup script from [First-Time Installation](#first-time-installation) to upgrade.

## Version Verification

Verify the version after installation/upgrade, must be >= 3.3.3:

```bash
aliyun version   # must be >= 3.3.3
```

> Versions below 3.3.3 may have incompatible subcommands and plugin behavior. Upgrade before continuing.

## Related Documentation

- Credentials / profile configuration and account mapping: see [starops-config.md](starops-config.md)
- env-check verifies aliyun CLI installation, valid credentials, and profile list: see [session-management.md](session-management.md)
- Permission failure handling: see [ram-policies.md](ram-policies.md)
