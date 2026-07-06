# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> **Aliyun CLI 3.3.3+**: Supports installing and using all published Alibaba Cloud product plugins. Make sure to upgrade to 3.3.3 or later for full plugin ecosystem coverage.

## Installation

### Security & Integrity Considerations

Before running any of the installation flows below, please understand and accept the following risks. They apply to every binary or script shown in this section.

| Risk | Where it shows up | Mitigation |
|---|---|---|
| **Remote script piped to shell** (`curl … \| bash`) | SKILL.md Installation section | Use the [Safer installation flow](#safer-installation-flow) below — download, inspect, then execute. |
| **Privilege elevation via `sudo mv … /usr/local/bin/`** | macOS / Debian / Ubuntu / CentOS / RHEL / ARM64 binary install | Only run `sudo` after verifying the downloaded archive's source (HTTPS host = `aliyuncli.alicdn.com`) and contents (`file aliyun` to confirm it's an ELF/Mach-O executable, not a shell script). Prefer per-user installs (`~/.local/bin`, no `sudo`) where possible. |
| **System-wide PATH modification** (`SetEnvironmentVariable(..., Machine)` on Windows) | Windows PowerShell flow | Requires Administrator. Only do this for binaries you've verified you trust. Prefer the user-scope target (`User`) when a per-user install is acceptable. |
| **Tampered binary** (compromised CDN, MITM bypassing TLS, malicious mirror) | All download flows | Pin checksums when Aliyun publishes them; otherwise verify the host (`aliyuncli.alicdn.com`) and rely on HTTPS. Don't pull binaries from third-party mirrors. |

> All installation commands in this guide download from `https://aliyuncli.alicdn.com/`. Verify this host before piping anything to a shell or moving a binary into a privileged location.

### Safer installation flow

When you cannot pipe a remote script directly into `bash` (e.g. policy forbids it, or you want to read what runs on your host first), replace the SKILL.md one-liner with:

```bash
# 1. Download the installer to a local file (does NOT execute it)
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh -o /tmp/aliyun-setup.sh

# 2. Inspect the script before running it
less /tmp/aliyun-setup.sh         # or: cat / sha256sum / diff against a known-good copy

# 3. Execute only after you're satisfied with what it will do
bash /tmp/aliyun-setup.sh

# 4. Verify the install
aliyun version

# 5. Clean up
rm /tmp/aliyun-setup.sh
```

The same principle applies to the binary archives below: `wget` first, run `file aliyun` and (when checksums are available) `sha256sum -c`, then move into `/usr/local/bin/` with `sudo`.

### macOS

**Using Homebrew (Recommended)**
```bash
brew install aliyun-cli
# Upgrade to latest
brew upgrade aliyun-cli

# Verify version (>= 3.3.3)
aliyun version
```

**Using Binary**
```bash
# Download
wget --connect-timeout=10 --read-timeout=120 --tries=3 https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz

# Extract
tar -xzf aliyun-cli-macosx-latest-amd64.tgz

# Move to PATH
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

### Linux

**Debian/Ubuntu**
```bash
# Download
wget --connect-timeout=10 --read-timeout=120 --tries=3 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**CentOS/RHEL**
```bash
# Download
wget --connect-timeout=10 --read-timeout=120 --tries=3 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**ARM64 Architecture**
```bash
# Download ARM64 version
wget --connect-timeout=10 --read-timeout=120 --tries=3 https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/
```

### Windows

**Using Binary**
1. Download from: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract the ZIP file
3. Add the directory to your PATH environment variable
4. Open new Command Prompt or PowerShell
5. Verify: `aliyun version`

**Using PowerShell**
```powershell
# Download
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip" -ConnectionTimeoutSeconds 10 -OperationTimeoutSeconds 120

# Extract
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli

# Add to PATH for the current session (no elevation needed)
$env:Path += ";C:\aliyun-cli"

# Persist PATH change. Pick ONE of the two:
#
#   USER scope (recommended; no Administrator required, only affects current Windows user):
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::User)
#
#   MACHINE scope (system-wide; requires Administrator; only do this after you have verified
#   the downloaded binary is the genuine Aliyun CLI — granting Machine PATH is privilege-elevation
#   surface, and any malicious binary in this folder will be reachable for ALL users on the host):
# [Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)

# Verify
aliyun version
```

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
        "LocalName": "华东 1（杭州）"
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

1. **Install plugins** for services you need (v3.3.3+ supports all published product plugins):
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
