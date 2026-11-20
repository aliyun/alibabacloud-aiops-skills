# Aliyun CLI installation

Use this guide to install or update the Aliyun CLI and SLS plugin.
See [version requirements](../SKILL.md#requirements).

## Installation

### macOS or Linux

The official installer writes the executable to `/usr/local/bin/aliyun`.
Writing to this directory may require administrator privileges.

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

For installation without administrator privileges, download and extract the
package for [macOS](https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz),
[Linux x86-64](https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz), or
[Linux ARM64](https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz).
Place the executable in a writable directory on `PATH`:

```bash
mkdir -p "$HOME/.local/bin"
install -m 755 ./aliyun "$HOME/.local/bin/aliyun"
export PATH="$HOME/.local/bin:$PATH"
```

To retain this PATH setting in new shells, add the `export` line to the
appropriate shell startup file.

### Windows

Download the [Windows package](https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip),
extract it, and add its directory to `PATH`. Open a new terminal.

## Version checks and updates

After installation, or when checking an existing setup, compare the installed versions
with the [requirements](../SKILL.md#requirements):

```bash
aliyun version
aliyun sls version
```

If the CLI is below the required version, update it using the installation steps above.
If the SLS plugin is missing, install it:

```bash
aliyun plugin install --names sls
```

If the plugin is below the required version, or a required command or option is
unavailable, update it:

```bash
aliyun plugin update --name sls
```

Check the versions again after updating.

## Authentication and profiles

For authentication setup and profile selection, see [profile configuration](profile-configuration.md).
For command or access failures, see [troubleshooting](troubleshooting.md).
