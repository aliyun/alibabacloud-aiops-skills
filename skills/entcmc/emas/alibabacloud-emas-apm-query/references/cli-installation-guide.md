# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI.

> **Aliyun CLI 3.3.0+**: Supports installing and using all published Alibaba Cloud product plugins. Make sure to upgrade to 3.3.0 or later for full plugin ecosystem coverage.

## Installation

### macOS / Linux (Recommended)

One command to install or update — works on both macOS and Linux, auto-detects architecture:

```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
```

After installation, verify:
```bash
aliyun version   # should be >= 3.3.0
```

### macOS — Homebrew (Alternative)

```bash
brew install aliyun-cli
# Upgrade to latest
brew upgrade aliyun-cli
```

### Linux — Manual Binary (Alternative)

Use these only if the setup script above is not suitable.

**x86_64**
```bash
wget --connect-timeout=10 --read-timeout=120 --tries=3 -qO- https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz
sudo mv aliyun /usr/local/bin/
```

**ARM64**
```bash
wget --connect-timeout=10 --read-timeout=120 --tries=3 -qO- https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz | tar xz
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

**OAuth (browser login)** — If the environment can open a web browser (for example a local desktop with a GUI), **prefer OAuth** over storing AccessKey pairs in configuration: credentials are not kept as plaintext AK/SecretKey. Requires Alibaba Cloud CLI **3.0.299** or later and is **not** suitable for headless servers (for example SSH-only Linux without a browser on the same machine).

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

Use the RAM role attached to an ECS instance — no credentials needed.

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
        "LocalName": "East China 1 (Hangzhou)"
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

Don't: Use Aliyun root account credentials
Do: Create RAM users with specific permissions

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

## References

- Official Documentation: https://help.aliyun.com/en/cli/
- RAM Console: https://ram.console.aliyun.com/
- Access Key Management: https://ram.console.aliyun.com/manage/ak

---

## Extra requirements for this Skill (the emas-appmonitor plugin)

All commands in this Skill rely on the `aliyun emas-appmonitor` plugin. Before you start, confirm the three items below:

### 1. CLI version

```bash
aliyun version
```

Required: `>= 3.3.3`. If lower, upgrade per the "Installation" section above.

### 2. Enable auto plugin install (recommended)

```bash
aliyun configure set --auto-plugin-install true
```

Once enabled, the first invocation of `aliyun emas-appmonitor` will auto-download the `aliyun-cli-emas-appmonitor` plugin to `~/.aliyun/plugin/`.

### 3. Install or update the plugin manually

```bash
aliyun plugin install --name emas-appmonitor
aliyun plugin update --name emas-appmonitor
```

Verify availability:

```bash
aliyun emas-appmonitor --help | head -40
```

The output should contain subcommands such as `get-issues`, `get-issue`, `get-errors`, `get-error`.

### 4. Credential pre-check (**never read or print AK/SK**)

```bash
aliyun configure list
```

There must be at least one `current` profile with non-empty `Mode` / `RegionId`. **This Skill does not read or print AK/SK field contents at runtime**; when errors occur, check them yourself using the command above.

### 5. RAM permissions

All commands in this Skill are **read-only queries**. See `ram-policies.md` for the least-privilege set; the core requirements are:

- `emasha:ViewIssues`
- `emasha:ViewIssue`
- `emasha:ViewErrors`
- `emasha:ViewError`

When you see `Forbidden.NoRAMPermission`, follow the "Permission Failure Handling" flow in `ram-policies.md`.
