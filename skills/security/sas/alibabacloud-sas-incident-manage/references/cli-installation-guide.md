# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> **Aliyun CLI 3.3.1+**: Supports installing and using all published Alibaba Cloud product plugins. Make sure to upgrade to 3.3.1 or later for full plugin ecosystem coverage.

## Installation

### macOS

**Using Homebrew (Recommended)**
```bash
brew install aliyun-cli
# Upgrade to latest
brew upgrade aliyun-cli

# Verify version (>= 3.3.1)
aliyun version
```

**Using Binary**
```bash
# Download
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz

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
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**CentOS/RHEL**
```bash
# Download
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

# Verify
aliyun version
```

**ARM64 Architecture**
```bash
# Download ARM64 version
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

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
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"

# Extract
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli

# Add to PATH (requires admin privileges)
$env:Path += ";C:\aliyun-cli"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)

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

### Credential Chain

Aliyun CLI uses the **default credential chain** - credentials are loaded automatically in this order (first found wins):

1. **Command-line flag**: `--profile <name>`
2. **Environment variable**: `ALIBABA_CLOUD_PROFILE`
3. **Configuration file**: `~/.aliyun/config.json` (current profile)
4. **ECS Instance RAM Role**: If running on ECS with attached role

> **Security Note**: Skills should NEVER set credentials via environment variables. Always rely on pre-configured credentials via `aliyun configure`.

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

## Verification

```bash
# Verify configuration
aliyun configure list

# Test with a simple API call
aliyun ecs describe-regions
```

## Security Best Practices

1. **Use RAM Users** (not root account) with specific permissions
2. **Principle of Least Privilege** - grant only minimum permissions
3. **Rotate Access Keys** regularly
4. **Use ECS RAM Roles** when running on ECS instances
5. **Never Commit Credentials** to version control

```bash
# Secure config file permissions
chmod 600 ~/.aliyun/config.json
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Command not found | Check PATH, reinstall CLI |
| Authentication failed | Run `aliyun configure list` to verify |
| Permission denied | Check RAM policies |
| Wrong region | Use `--region` flag or update default |

## Next Steps

```bash
# Install cloud-siem plugin for this skill
aliyun plugin install --names cloud-siem

# Verify installation
aliyun cloud-siem --api-version 2024-12-12 --help
```

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/