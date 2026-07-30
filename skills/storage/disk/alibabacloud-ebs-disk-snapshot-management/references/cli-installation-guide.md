# Alibaba Cloud CLI Installation Guide

The snapshot management workflows in this skill are executed through the Alibaba Cloud CLI
(`aliyun`). This guide covers installation and version requirements.

## Version requirement

- **Minimum version: 3.3.3.**
- Verify with:

  ```bash
  aliyun version
  ```

If the command is not found or reports a version lower than 3.3.3, install or update using the
instructions below.

## Install / update

### macOS and Linux (recommended one-liner)

```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
```

### macOS (Homebrew)

```bash
brew install aliyun-cli
```

### Manual installation

1. Download the package for your platform from the
   [Alibaba Cloud CLI release page](https://github.com/aliyun/aliyun-cli/releases).
2. Extract the archive and move the `aliyun` binary to a directory on your `PATH`
   (for example `/usr/local/bin`).
3. Run `aliyun version` to confirm the installation.

## Plugin configuration

After installation, enable automatic plugin installation and update existing plugins:

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

## Verify credentials

Do **not** print AK/SK values. Only check credential status:

```bash
aliyun configure list
```

Confirm a valid profile (AK, STS, or OAuth identity) is present before running snapshot
operations. See the Authentication section in [`../SKILL.md`](../SKILL.md) for the full
security rules.

## References

- [Alibaba Cloud CLI documentation](https://www.alibabacloud.com/help/en/cli)
- [Configure credentials](https://www.alibabacloud.com/help/en/cli/configure-credentials)
