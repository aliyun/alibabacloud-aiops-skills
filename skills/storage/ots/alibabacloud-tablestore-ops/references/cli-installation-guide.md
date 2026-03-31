# Aliyun CLI Installation Guide (with otsutil for Tablestore)

Complete guide for installing and configuring Aliyun CLI to use Tablestore operations via `aliyun otsutil`.

> **CRITICAL: Version Requirement**
>
> The `otsutil` subcommand is **only available in Aliyun CLI version 3.3.0 or later**.
> - Homebrew version may be outdated (e.g., 3.0.x) and does NOT include otsutil
> - Always download directly from the official CDN to ensure you get the latest version
> - The otsutil subcommand automatically downloads and manages the Tablestore CLI binary on first use

## Installation

### Recommended: Download from Official CDN

> **WARNING:** Do NOT use `brew install aliyun-cli` - it may install an outdated version without otsutil support.

| Platform | Architecture | Download URL |
|----------|--------------|--------------|
| macOS | Universal (Intel + Apple Silicon) | https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz |
| macOS | GUI Installer | https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg |
| Linux | AMD64 | https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz |
| Linux | ARM64 | https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz |
| Windows | AMD64 | https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip |

### macOS (Universal Binary - Recommended)

```bash
# Download
curl -L -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz

# Extract
tar -xzf aliyun-cli.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify version (MUST be 3.3.0 or later)
aliyun version

# Verify otsutil is available
aliyun otsutil help
```

### macOS (GUI Installer)

1. Download the [Mac PKG](https://aliyuncli.alicdn.com/aliyun-cli-latest.pkg)
2. Double-click the PKG file to install
3. Follow the installer prompts
4. Verify: `aliyun version` (must show 3.3.0+)
5. Verify otsutil: `aliyun otsutil help`

### Linux (AMD64)

```bash
# Download
curl -L -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract
tar -xzf aliyun-cli.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify version (MUST be 3.3.0 or later)
aliyun version

# Verify otsutil is available
aliyun otsutil help
```

### Linux (ARM64)

```bash
# Download
curl -L -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

# Extract
tar -xzf aliyun-cli.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify version (MUST be 3.3.0 or later)
aliyun version

# Verify otsutil is available
aliyun otsutil help
```

### Windows

1. Download the [Windows ZIP](https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip)
2. Extract the zip file to get `aliyun.exe`
3. Add the directory to your PATH environment variable
4. Run from Command Prompt or PowerShell:
   - `aliyun version` (must show 3.3.0+)
   - `aliyun otsutil help` (verify otsutil is available)

## Configuration

### Basic Configuration (Interactive)

```bash
aliyun configure
```

Follow the prompts:
```
Configuring profile 'default' ...
Aliyun Access Key ID [None]: <Your AccessKey ID>
Aliyun Access Key Secret [None]: <Your AccessKey Secret>
Default Region Id [None]: cn-hangzhou
Default output format [json]: json
Default Language [zh]: en
```

### Configuration with Named Profile

```bash
# Create a dedicated profile for Tablestore operations
aliyun configure --profile tablestore-ops

# Use the profile
aliyun otsutil --profile tablestore-ops list_instance -r cn-hangzhou
```

### Authentication Modes

| Mode | Use Case | Configure Command |
|------|----------|-------------------|
| AK | Direct AccessKey (default) | `aliyun configure --mode AK` |
| RamRoleArn | RAM role assumption | `aliyun configure --mode RamRoleArn` |
| EcsRamRole | ECS instance role | `aliyun configure --mode EcsRamRole` |
| OIDC | OIDC-based SSO | `aliyun configure --mode OIDC` |
| External | External credential provider | `aliyun configure --mode External` |

#### RAM Role Assumption Example

```bash
aliyun configure --mode RamRoleArn --profile role-user

# Follow prompts:
# Access Key Id []: <AccessKey ID>
# Access Key Secret []: <AccessKey Secret>
# Sts Region []: cn-hangzhou
# Ram Role Arn []: acs:ram::<account-id>:role/<role-name>
# Role Session Name []: tablestore-session
# Expired Seconds []: 900
```

### Configuration Options

| Option | Description |
|--------|-------------|
| `--profile <name>` | Specify profile name |
| `--mode <mode>` | Authentication mode (AK, RamRoleArn, etc.) |
| `--region <region>` | Default region ID |
| `--language <lang>` | Language (en, zh) |

## Using otsutil

### First Run

On the first run, `aliyun otsutil` automatically downloads the Tablestore CLI binary:

```bash
aliyun otsutil help
```

The binary is downloaded to `~/.aliyun/` and managed automatically.

### Configure Instance Endpoint

Before running table operations, configure the instance endpoint:

```bash
aliyun otsutil config --endpoint https://<instance>.cn-hangzhou.ots.aliyuncs.com --instance <instance>
```

### Endpoint Format

#### Public Network

```
https://<instance_name>.<region_id>.ots.aliyuncs.com
```

Example: `https://myinstance.cn-hangzhou.ots.aliyuncs.com`

#### VPC Network

```
https://<instance_name>.<region_id>.vpc.tablestore.aliyuncs.com
```

Example: `https://myinstance.cn-hangzhou.vpc.tablestore.aliyuncs.com`

## Common Regions

| Region | Region ID |
|--------|-----------|
| China (Hangzhou) | cn-hangzhou |
| China (Shanghai) | cn-shanghai |
| China (Beijing) | cn-beijing |
| China (Shenzhen) | cn-shenzhen |
| China (Hong Kong) | cn-hongkong |
| Singapore | ap-southeast-1 |
| US (Virginia) | us-east-1 |
| Germany (Frankfurt) | eu-central-1 |

## Troubleshooting

### otsutil command not found

**Symptom:** `aliyun otsutil` returns "ERROR: 'otsutil' is not a valid command or product"

**Cause:** You have an outdated version of Aliyun CLI (< 3.3.0). The Homebrew version is often outdated.

**Solution:**
1. Check your version: `aliyun version`
2. If version is below 3.3.0, download the latest version from CDN:
   ```bash
   # Remove old version (if installed via homebrew)
   brew uninstall aliyun-cli 2>/dev/null
   
   # Download latest from CDN
   curl -L -o aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-universal.tgz
   tar -xzf aliyun-cli.tgz
   sudo mv aliyun /usr/local/bin/
   
   # Verify
   aliyun version  # Should show 3.3.0+
   aliyun otsutil help  # Should work now
   ```

### Command not found: aliyun

Ensure the `aliyun` binary is in your PATH:

```bash
# Check if aliyun is in PATH
which aliyun

# If not found, add to PATH
export PATH=$PATH:/usr/local/bin
```

### Authentication failed

1. Verify credentials with:
   ```bash
   aliyun sts GetCallerIdentity
   ```

2. Re-configure if needed:
   ```bash
   aliyun configure
   ```

3. Check RAM user has `AliyunOTSReadOnlyAccess` permission

### otsutil download failed

If the Tablestore CLI binary fails to download:

1. Check network connectivity
2. Try running with verbose output:
   ```bash
   aliyun otsutil help
   ```
3. The binary is stored in `~/.aliyun/ts` - check if it exists

### Connection timeout

- Check your network connection
- Verify the endpoint URL is correct
- Ensure the instance exists in the specified region

### Profile not found

```bash
# List available profiles
aliyun configure list

# Create a new profile
aliyun configure --profile <name>
```

## Verification

Test your installation and configuration:

```bash
# Verify Aliyun CLI installation
aliyun version

# Verify credentials
aliyun sts GetCallerIdentity

# Verify otsutil (will auto-download Tablestore CLI if needed)
aliyun otsutil help

# List instances in a region
aliyun otsutil list_instance -r cn-hangzhou
```

If configured correctly, you'll see a list of instances (or empty array if none exist).

## Supported Platforms

The `aliyun otsutil` command supports the following platforms:

| Platform | Architecture | Support |
|----------|--------------|---------|
| Linux | AMD64 | Yes |
| Linux | ARM64 | Yes |
| macOS | AMD64 (Intel) | Yes |
| macOS | ARM64 (Apple Silicon) | Yes |
| Windows | AMD64 | Yes |

## References

- [Aliyun CLI GitHub](https://github.com/aliyun/aliyun-cli)
- [Aliyun CLI Documentation](https://www.alibabacloud.com/help/doc-detail/121988.html)
- [Tablestore Product Page](https://www.aliyun.com/product/ots)
- [Official Documentation](https://help.aliyun.com/zh/tablestore/)
