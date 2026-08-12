# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> **Aliyun CLI 3.3.3+**: Supports installing and using all published Alibaba Cloud product plugins. Make sure to upgrade to 3.3.3 or later for full plugin ecosystem coverage.

## Installation

Prefer a package manager because it verifies package integrity as part of the
installation workflow. If a package manager is unavailable, use a version-pinned
release and verify its SHA256 digest **before** extracting or executing it.

### macOS

**Using Homebrew (Recommended)**
```bash
brew install aliyun-cli
# Upgrade to latest
brew upgrade aliyun-cli

# Verify version (>= 3.3.3)
aliyun version
```

**Using a verified binary (fallback)**

The example below pins Aliyun CLI `3.4.8`. When updating the version, copy the new
digest from the official [GitHub release page](https://github.com/aliyun/aliyun-cli/releases)
and update `EXPECTED_SHA256` at the same time. Never reuse a digest from a different
version or architecture.

```bash
VERSION="3.4.8"
ARCHIVE="aliyun-cli-macosx-${VERSION}-universal.tgz"
EXPECTED_SHA256="ec3b300f6aca79b8317d1cbcd051fefd77f75ab9b5ec1afc7b54f113b29d512b"
DOWNLOAD_URL="https://github.com/aliyun/aliyun-cli/releases/download/v${VERSION}/${ARCHIVE}"

# Require HTTPS, download the pinned archive, and verify it before extraction.
curl --proto '=https' --tlsv1.2 --fail --location \
  --output "${ARCHIVE}" "${DOWNLOAD_URL}"
printf '%s  %s\n' "${EXPECTED_SHA256}" "${ARCHIVE}" | shasum -a 256 --check -
tar -xzf "${ARCHIVE}"

# Install for the current user; no administrator privileges are required.
install -d "${HOME}/.local/bin"
install -m 0755 aliyun "${HOME}/.local/bin/aliyun"
export PATH="${HOME}/.local/bin:${PATH}"

aliyun version
```

To persist the user-local installation, add
`export PATH="${HOME}/.local/bin:${PATH}"` to your shell profile.

### Linux

The same verified installation works on Debian, Ubuntu, CentOS, and RHEL. The
architecture check below rejects unsupported values instead of downloading an
unrelated executable.

```bash
VERSION="3.4.8"
case "$(uname -m)" in
  x86_64|amd64)
    ARCH="amd64"
    EXPECTED_SHA256="359419867fb8e850f327745315a312f1ec9749e64ec8747cc8b09f67d6df4868"
    ;;
  aarch64|arm64)
    ARCH="arm64"
    EXPECTED_SHA256="a8b22c72c1984e0ef4db441ab1e7f1720a03553fae79cff9fb113806229e7876"
    ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

ARCHIVE="aliyun-cli-linux-${VERSION}-${ARCH}.tgz"
DOWNLOAD_URL="https://github.com/aliyun/aliyun-cli/releases/download/v${VERSION}/${ARCHIVE}"

curl --proto '=https' --tlsv1.2 --fail --location \
  --output "${ARCHIVE}" "${DOWNLOAD_URL}"
printf '%s  %s\n' "${EXPECTED_SHA256}" "${ARCHIVE}" | sha256sum --check -
tar -xzf "${ARCHIVE}"

install -d "${HOME}/.local/bin"
install -m 0755 aliyun "${HOME}/.local/bin/aliyun"
export PATH="${HOME}/.local/bin:${PATH}"

aliyun version
```

To persist the user-local installation, add
`export PATH="${HOME}/.local/bin:${PATH}"` to your shell profile.

**Optional system-wide installation**

Installing into `/usr/local/bin` changes a system-owned directory and therefore
requires administrator privileges. Only do this after the SHA256 check succeeds
and after confirming the destination:

```bash
sudo install -m 0755 aliyun /usr/local/bin/aliyun
```

### Windows

**Using a verified binary with PowerShell**

```powershell
$Version = "3.4.8"
$Archive = "aliyun-cli-windows-$Version-amd64.zip"
$ExpectedSha256 = "5c53b104defcc968cdc53b43e07790861d7196d3f52ab7fef2f4a7ae7e258825"
$DownloadUrl = "https://github.com/aliyun/aliyun-cli/releases/download/v$Version/$Archive"

Invoke-WebRequest -Uri $DownloadUrl -OutFile $Archive
$ActualSha256 = (Get-FileHash -Algorithm SHA256 -Path $Archive).Hash.ToLowerInvariant()
if ($ActualSha256 -ne $ExpectedSha256) {
    Remove-Item -LiteralPath $Archive
    throw "SHA256 verification failed; the archive was deleted."
}

$InstallDir = Join-Path $HOME "bin\aliyun-cli"
Expand-Archive -Path $Archive -DestinationPath $InstallDir -Force

# Update only the current user's PATH; administrator privileges are not required.
$UserPath = [Environment]::GetEnvironmentVariable("Path", [System.EnvironmentVariableTarget]::User)
if (($UserPath -split ";") -notcontains $InstallDir) {
    $NewUserPath = (@($UserPath, $InstallDir) | Where-Object { $_ }) -join ";"
    [Environment]::SetEnvironmentVariable(
        "Path",
        $NewUserPath,
        [System.EnvironmentVariableTarget]::User
    )
}
$env:Path = "$InstallDir;$env:Path"

aliyun version
```

Changing the machine-wide PATH requires administrator privileges and is not needed
for a per-user installation.

## Configuration

### Quick Start

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

All `aliyun configure` commands support non-interactive flags, which is the recommended approach —
it works in scripts, CI/CD pipelines, and agent-driven automation without hanging on stdin prompts.

**Where to Get Access Keys**

1. Log in to Aliyun Console: https://ram.console.aliyun.com/
2. Navigate to: AccessKey Management
3. Create a new AccessKey pair
4. Save the secret immediately — it's only shown once

### Configuration Modes

Aliyun CLI supports 6 authentication modes. All examples below use non-interactive flags.

#### 1. AK Mode (Access Key)

Most common mode for personal accounts and scripts.

```bash
aliyun configure set \
  --mode AK \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --region cn-hangzhou
```

Configuration is stored in `~/.aliyun/config.json`:

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "AK",
      "access_key_id": "LTAI5tXXXXXXXX",
      "access_key_secret": "8dXXXXXXXXXXXXXXXXXXXXXXXX",
      "region_id": "cn-hangzhou",
      "output_format": "json",
      "language": "en"
    }
  ]
}
```

#### 2. StsToken Mode (Temporary Credentials)

For short-lived access (tokens expire in 1-12 hours).

```bash
aliyun configure set \
  --mode StsToken \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --sts-token v1.0:XXXXXXXXXXXXXXXX \
  --region cn-hangzhou
```

Use cases: CI/CD pipelines, temporary access for external contractors, cross-account access.

#### 3. RamRoleArn Mode (Assume RAM Role)

Assume a RAM role for elevated or cross-account access.

```bash
aliyun configure set \
  --mode RamRoleArn \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --ram-role-arn acs:ram::123456789012:role/AdminRole \
  --role-session-name my-session \
  --region cn-hangzhou
```

Use cases: cross-account resource access, temporary elevated privileges, role-based access control.

#### 4. EcsRamRole Mode (ECS Instance RAM Role)

Use the RAM role attached to an ECS instance — no credentials needed.

```bash
aliyun configure set \
  --mode EcsRamRole \
  --ram-role-name MyEcsRole \
  --region cn-hangzhou
```

Requirements: must be running on an ECS instance with a RAM role attached.

Use cases: scripts and automation running on ECS instances.

#### 5. RsaKeyPair Mode (RSA Key Pair)

Use RSA key pair for authentication (generate key pair in Aliyun Console first).

```bash
aliyun configure set \
  --mode RsaKeyPair \
  --private-key /path/to/private-key.pem \
  --key-pair-name my-key-pair \
  --region cn-hangzhou
```

#### 6. RamRoleArnWithEcs Mode (ECS + RAM Role)

Combine ECS instance role with RAM role assumption for cross-account access from ECS.

```bash
aliyun configure set \
  --mode RamRoleArnWithEcs \
  --ram-role-name MyEcsRole \
  --ram-role-arn acs:ram::123456789012:role/TargetRole \
  --role-session-name my-session \
  --region cn-hangzhou
```

### Environment Variables

**Highest priority** - overrides config file

**Access Key Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

**STS Token Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=your_access_key_id
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=your_access_key_secret
export ALIBABA_CLOUD_SECURITY_TOKEN=your_sts_token
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

**ECS RAM Role Mode**
```bash
export ALIBABA_CLOUD_ECS_METADATA=role_name
```

**Use Case**:
- CI/CD pipelines
- Docker containers
- Temporary credential override

### Managing Multiple Profiles

**Create Named Profiles**

```bash
aliyun configure set --profile projectA \
  --mode AK \
  --access-key-id LTAI5tAAAAAAAA \
  --access-key-secret 8dAAAAAAAAAAAAAAAAAAAAAAAA \
  --region cn-hangzhou

aliyun configure set --profile projectB \
  --mode AK \
  --access-key-id LTAI5tBBBBBBBB \
  --access-key-secret 8dBBBBBBBBBBBBBBBBBBBBBBBB \
  --region cn-shanghai
```

**Use Specific Profile**

```bash
aliyun ecs describe-instances --profile projectA

export ALIBABA_CLOUD_PROFILE=projectA
aliyun ecs describe-instances   # Uses projectA
```

**List and Switch Profiles**

```bash
aliyun configure list                      # List all profiles
aliyun configure set --current projectA    # Switch default profile
```

### Credential Priority

Credentials are loaded in this order (first found wins):

1. **Command-line flag**: `--profile <name>`
2. **Environment variable**: `ALIBABA_CLOUD_PROFILE`
3. **Environment credentials**: `ALIBABA_CLOUD_ACCESS_KEY_ID`, etc.
4. **Configuration file**: `~/.aliyun/config.json` (current profile)
5. **ECS Instance RAM Role**: If running on ECS with attached role

## Verification

### Test Authentication

```bash
# Basic test - list regions
aliyun ecs describe-regions

# Expected output: JSON array of regions
```

**If successful**, you'll see:
```json
{
  "Regions": {
    "Region": [
      {
        "RegionId": "cn-hangzhou",
        "RegionEndpoint": "ecs.cn-hangzhou.aliyuncs.com",
        "LocalName": "<localized region name>"
      },
      ...
    ]
  },
  "RequestId": "..."
}
```

**If failed**, you'll see error messages:
- `InvalidAccessKeyId.NotFound` - Wrong Access Key ID
- `SignatureDoesNotMatch` - Wrong Access Key Secret
- `InvalidSecurityToken.Expired` - STS token expired (for StsToken mode)
- `Forbidden.RAM` - Insufficient permissions

### Debug Configuration

```bash
# Show current configuration
aliyun configure get

# Test with debug logging
aliyun ecs describe-regions --log-level=debug

# Check credential provider
aliyun configure get mode
```

## Security Best Practices

### 1. Use RAM Users (Not Root Account)

❌ **Don't**: Use Aliyun root account credentials
✅ **Do**: Create RAM users with specific permissions

```bash
# Create RAM user in console
# Attach only necessary policies
# Use RAM user's access keys
```

### 2. Principle of Least Privilege

Grant only the minimum permissions needed:

```bash
# Example: Read-only ECS access
# Attach policy: AliyunECSReadOnlyAccess
```

### 3. Rotate Access Keys Regularly

```bash
# Create new access key in RAM Console, then update configuration
aliyun configure set --access-key-id NEW_KEY --access-key-secret NEW_SECRET
# Delete old access key from console
```

### 4. Use STS Tokens for Temporary Access

```bash
aliyun configure set --mode StsToken \
  --access-key-id XXXX --access-key-secret XXXX \
  --sts-token XXXX --region cn-hangzhou
```

### 5. Use ECS RAM Roles When Possible

```bash
aliyun configure set --mode EcsRamRole --ram-role-name MyRole --region cn-hangzhou
```

### 6. Never Commit Credentials

```bash
# Add to .gitignore
echo "~/.aliyun/config.json" >> .gitignore

# Use environment variables in CI/CD instead
```

### 7. Secure Config File

```bash
# Restrict permissions
chmod 600 ~/.aliyun/config.json
```

## Troubleshooting

### Issue: Command Not Found

```bash
# Check installation
which aliyun

# Check PATH
echo $PATH

# Reinstall or add to PATH
```

### Issue: Authentication Failed

```bash
# Verify configuration
aliyun configure get

# Test with debug
aliyun ecs describe-regions --log-level=debug

# Check credentials in console
# Verify access key is active
```

### Issue: Permission Denied

```bash
# Error: Forbidden.RAM

# Check RAM user permissions
# Attach necessary policies in RAM console
# Example: AliyunECSFullAccess for ECS operations
```

### Issue: STS Token Expired

```bash
# Error: InvalidSecurityToken.Expired

# Reconfigure with new token
aliyun configure set --mode StsToken \
  --access-key-id XXXX --access-key-secret XXXX \
  --sts-token NEW_TOKEN --region cn-hangzhou
```

### Issue: Wrong Region

```bash
# Some resources may not exist in the specified region

# Check available regions
aliyun ecs describe-regions

# Update default region
aliyun configure set region cn-shanghai
```

## Advanced Configuration

### Custom Endpoint

```bash
# Use custom or private endpoint
export ALIBABA_CLOUD_ECS_ENDPOINT=ecs-vpc.cn-hangzhou.aliyuncs.com
```

### Proxy Settings

```bash
# HTTP proxy
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# No proxy for specific domains
export NO_PROXY=localhost,127.0.0.1,.aliyuncs.com
```

### Timeout Settings

```bash
# Connection timeout (default: 10s)
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30

# Read timeout (default: 10s)
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

## Next Steps

After installation and configuration:

1. **Install plugins** for services you need (v3.3.0+ supports all published product plugins):
   ```bash
   aliyun plugin install --names ecs vpc rds

   # List all available plugins
   aliyun plugin list-remote
   ```

2. **Explore commands**:
   ```bash
   aliyun ecs --help
   aliyun fc --help
   ```

3. **Read documentation**:
   - [Command Syntax Guide](./command-syntax.md)
   - [Global Flags Reference](./global-flags.md)
   - [Common Scenarios](./common-scenarios.md)

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak
- Plugin Repository: https://github.com/aliyun/aliyun-cli
