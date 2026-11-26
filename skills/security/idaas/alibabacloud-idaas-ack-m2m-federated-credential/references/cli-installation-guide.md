# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

The Skill requires Aliyun CLI 3.5.1 or later. Use an existing installation that meets this minimum, or install a current release.

## Installation

### macOS with Homebrew

```bash
brew install aliyun-cli
```

### Linux and other macOS installation methods

Choose a numbered release at or above the minimum and download the package for your OS and CPU architecture from the official release page. Verify the archive against a trusted SHA-256 checksum from the publisher or your approved distributor before extracting it. Follow the installation instructions for that package. [Aliyun CLI releases](https://github.com/aliyun/aliyun-cli/releases) and [official installation instructions](https://help.aliyun.com/en/cli/install-update-alibaba-cloud-cli)

### Windows

For a separate Windows CLI installation, choose a numbered Windows package and follow the Windows steps in the [official installation guide](https://help.aliyun.com/en/cli/install-update-alibaba-cloud-cli#install-alibaba-cloud-cli).

### Upgrade and verify

For a Homebrew installation, use `brew upgrade aliyun-cli`. For other supported installations of CLI 3.3.5 or later, use `aliyun upgrade`. With an older CLI, use the current package installation instructions to upgrade. Confirm the installed version is 3.5.1 or later. [Official upgrade guide](https://help.aliyun.com/en/cli/install-update-alibaba-cloud-cli#update-alibaba-cloud-cli)

```bash
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

All `aliyun configure` commands support non-interactive flags, which is the recommended approach -
it works in scripts, CI/CD pipelines, and agent-driven automation without hanging on stdin prompts.

**Where to Get Access Keys**

1. Log in to Aliyun Console: https://ram.console.aliyun.com/
2. Navigate to: AccessKey Management
3. Create a new AccessKey pair
4. Save the secret immediately - it's only shown once

### Configuration Modes

**OAuth (browser login)** - If the environment can open a web browser (for example a local desktop with a GUI), **prefer OAuth** over storing AccessKey pairs in configuration: credentials are not kept as plaintext AK/SecretKey. Requires Alibaba Cloud CLI **3.0.299** or later and is **not** suitable for headless servers (for example SSH-only Linux without a browser on the same machine).

Run interactively:

```bash
aliyun configure --profile <your-profile-name> --mode OAuth
```

Full setup (administrator consent, RAM assignments, site `CN` vs `INTL`) is covered in the official guide: [Configure OAuth authentication for Alibaba Cloud CLI](https://www.alibabacloud.com/help/en/doc-detail/2995960.html).

---

The sections below describe **six** authentication modes that are typically driven with **non-interactive** flags (scripts, CI/CD, automation). Use these when OAuth is not available or when you must supply explicit keys or tokens.

#### 1. AK Mode (Access Key)

Most common mode for personal accounts and scripts.

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
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
      "access_key_id": "<your-access-key-id>",
      "access_key_secret": "<your-access-key-secret>",
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
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --sts-token <your-sts-token> \
  --region cn-hangzhou
```

Use cases: CI/CD pipelines, temporary access for external contractors, cross-account access.

#### 3. RamRoleArn Mode (Assume RAM Role)

Assume a RAM role for elevated or cross-account access.

```bash
aliyun configure set \
  --mode RamRoleArn \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --ram-role-arn <your-ram-role-arn> \
  --role-session-name <your-role-session-name> \
  --region cn-hangzhou
```

Use cases: cross-account resource access, temporary elevated privileges, role-based access control.

#### 4. EcsRamRole Mode (ECS Instance RAM Role)

Use the RAM role attached to an ECS instance - no credentials needed.

```bash
aliyun configure set \
  --mode EcsRamRole \
  --ram-role-name <your-ecs-ram-role-name> \
  --region cn-hangzhou
```

Requirements: must be running on an ECS instance with a RAM role attached.

Use cases: scripts and automation running on ECS instances.

#### 5. RsaKeyPair Mode (RSA Key Pair)

Use RSA key pair for authentication (generate key pair in Aliyun Console first).

```bash
aliyun configure set \
  --mode RsaKeyPair \
  --private-key <path-to-your-private-key.pem> \
  --key-pair-name <your-key-pair-name> \
  --region cn-hangzhou
```

#### 6. RamRoleArnWithEcs Mode (ECS + RAM Role)

Combine ECS instance role with RAM role assumption for cross-account access from ECS.

```bash
aliyun configure set \
  --mode RamRoleArnWithEcs \
  --ram-role-name <your-ecs-ram-role-name> \
  --ram-role-arn <your-ram-role-arn> \
  --role-session-name <your-role-session-name> \
  --region cn-hangzhou
```

### Environment Variables

**Highest priority** - overrides config file

**Access Key Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

**STS Token Mode**
```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-access-key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-access-key-secret>
export ALIBABA_CLOUD_SECURITY_TOKEN=<your-sts-token>
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
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
  --access-key-id <your-first-access-key-id> \
  --access-key-secret <your-first-access-key-secret> \
  --region cn-hangzhou

aliyun configure set --profile projectB \
  --mode AK \
  --access-key-id <your-second-access-key-id> \
  --access-key-secret <your-second-access-key-secret> \
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
aliyun configure switch --profile projectA    # Switch default profile
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
        "LocalName": "China (Hangzhou)"
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
aliyun ecs describe-regions --log-level debug

# Check credential provider
aliyun configure get mode
```

## Security Best Practices

### 1. Use RAM Users (Not Root Account)

Do not use Aliyun root account credentials. Create RAM users with specific permissions.

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
aliyun configure set --access-key-id <your-access-key-id> --access-key-secret <your-access-key-secret>
# Delete old access key from console
```

### 4. Use STS Tokens for Temporary Access

```bash
aliyun configure set --mode StsToken \
  --access-key-id <your-access-key-id> --access-key-secret <your-access-key-secret> \
  --sts-token <your-sts-token> --region cn-hangzhou
```

### 5. Use ECS RAM Roles When Possible

```bash
aliyun configure set --mode EcsRamRole --ram-role-name <your-ecs-ram-role-name> --region cn-hangzhou
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
aliyun ecs describe-regions --log-level debug

# Check credentials in console
# Verify access key is active
```

### Issue: Permission Denied

For `Forbidden.RAM`, record the failed Action and request ID. Ask the RAM administrator to check the selected CLI identity against the [Skill's custom RAM policy](ram-policies.md#custom-policy-json-for-m2m-federation).

### Issue: STS Token Expired

```bash
# Error: InvalidSecurityToken.Expired

# Reconfigure with new token
aliyun configure set --mode StsToken \
  --access-key-id <your-access-key-id> --access-key-secret <your-access-key-secret> \
  --sts-token <your-sts-token> --region cn-hangzhou
```

### Issue: Wrong Region

```bash
# Some resources may not exist in the specified region

# Check available regions
aliyun ecs describe-regions

# Update default region
aliyun configure set --region cn-shanghai
```

## Advanced Configuration

### Timeout Settings

```bash
# Connection timeout
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30

# Read timeout
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

## Next Steps

After installation and configuration:

1. **Install plugins** for services you need (v3.5.1+ supports all published product plugins):
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

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak
