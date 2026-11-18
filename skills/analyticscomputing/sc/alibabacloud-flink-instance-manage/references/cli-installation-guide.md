# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> Aliyun CLI is optional and is used for credential and environment diagnostics. Flink operations in this skill use the Python SDK.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Security Best Practices](#security-best-practices)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)
- [Next Steps](#next-steps)
- [References](#references)

## Installation

Run `aliyun version` to check for an existing installation. If installation is needed, the user selects an approved version and downloads the asset for their operating system and architecture from the [official Aliyun CLI releases](https://github.com/aliyun/aliyun-cli/releases).

Compare the downloaded file's SHA-256 digest with the digest for the exact asset on its release page or in an approved artifact repository. If the digest is unavailable or differs, stop. Once verified, follow the official platform installation instructions and run `aliyun version` to confirm the installed version matches the selected release.

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

Set the confirmed profile name for the Python SDK credential chain.

```bash
export ALIBABA_CLOUD_PROFILE=projectA
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

Use local diagnostics to check the installed CLI and configured profiles.

```bash
aliyun version
aliyun configure list
```

For a live read-only credential check requested by the user, first [initialize the skill session](../SKILL.md#initialize-the-session), then run the following from the skill root.

```bash
python scripts/instance_ops.py describe_regions
```

Check for `success: true`, `operation: "describe_regions"`, and the supported regions in `data`. If the command fails, inspect `error.code`, `error.message`, and `request_id` when available. Common authentication errors include the following.

- `InvalidAccessKeyId.NotFound` - Wrong Access Key ID
- `SignatureDoesNotMatch` - Wrong Access Key Secret
- `InvalidSecurityToken.Expired` - STS token expired (for StsToken mode)
- `Forbidden.RAM` - Insufficient permissions

### Debug Configuration

```bash
aliyun configure list
```

For cloud failures, use the script's structured error fields and request ID. Keep credential values out of diagnostic output.

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

Grant only the explicitly listed Flink RAM actions needed for the requested operation. Use the [RAM policies reference](ram-policies.md) to select the required actions and resource constraints.

### 3. Rotate Access Keys Regularly

```bash
# Create new access key in RAM Console, then refresh configuration
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
aliyun configure list
```

Ask the user to verify that the configured identity is active. If the user requests a live check, follow [Test Authentication](#test-authentication) and inspect the returned error fields.

### Issue: Permission Denied

For `Forbidden.RAM`, follow the [permission failure procedure](../SKILL.md#ram-authorization). Provide the failed Flink operation, region, error code, and request ID to the permission diagnosis skill or the user's RAM administrator.

### Issue: STS Token Expired

```bash
# Error: InvalidSecurityToken.Expired

# Reconfigure with new token
aliyun configure set --mode StsToken \
  --access-key-id XXXX --access-key-secret XXXX \
  --sts-token NEW_TOKEN --region cn-hangzhou
```

### Issue: Wrong Region

Confirm the target region with the user and pass it as `--region_id` to the requested Flink command. If the user requests a live supported-region query, follow [Test Authentication](#test-authentication).

## Advanced Configuration

### Flink Endpoint

The script derives the Flink OpenAPI endpoint from the validated `--region_id`.

### Proxy Settings

```bash
# HTTP proxy
export HTTP_PROXY=<proxy-url>
export HTTPS_PROXY=<proxy-url>

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

1. **Explore commands**:
   ```bash
   aliyun --help
   ```

2. **Read documentation**:
   - Command Syntax Guide
   - Global Flags Reference
   - Common Scenarios

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak
- Plugin Repository: https://github.com/aliyun/aliyun-cli
