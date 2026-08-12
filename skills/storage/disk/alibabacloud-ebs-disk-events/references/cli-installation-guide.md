# Aliyun CLI Installation and Configuration Guide

This Skill requires the Aliyun CLI and EBS plugin. Follow the steps below to complete installation and configuration.

> **Aliyun CLI 3.3.3+**: Supports installing and using all published Alibaba Cloud product plugins. Upgrading to 3.3.3 or later is recommended.

---

## Install Aliyun CLI

### macOS

**Using Homebrew (Recommended)**

```bash
brew install aliyun-cli
# Upgrade to the latest version
brew upgrade aliyun-cli

# Verify version (>= 3.3.3)
aliyun version
```

**Using Binary Package**

```bash
# Download
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz

# Extract
tar -xzf aliyun-cli-macosx-latest-amd64.tgz

# Move to user PATH (no sudo required)
mkdir -p ~/.local/bin && mv aliyun ~/.local/bin/
# Ensure ~/.local/bin is on your PATH (add to ~/.zshrc or ~/.bashrc if needed)

# Verify
aliyun version
```

### Linux

**Debian/Ubuntu / CentOS / RHEL (Universal Method)**

```bash
# Download
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz

# Extract and install (no sudo required)
tar -xzf aliyun-cli-linux-latest-amd64.tgz
mkdir -p ~/.local/bin && mv aliyun ~/.local/bin/
# Ensure ~/.local/bin is on your PATH (add to ~/.bashrc if needed)

# Verify
aliyun version
```

**ARM64 Architecture**

```bash
# Download ARM64 version
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz

# Extract and install (no sudo required)
tar -xzf aliyun-cli-linux-latest-arm64.tgz
mkdir -p ~/.local/bin && mv aliyun ~/.local/bin/
# Ensure ~/.local/bin is on your PATH (add to ~/.bashrc if needed)

# Verify
aliyun version
```

### Windows

**Using Binary Package**

1. Download: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract the ZIP file
3. Add the extracted directory to the system PATH environment variable
4. Open a new Command Prompt or PowerShell
5. Verify: `aliyun version`

**Using PowerShell**

```powershell
# Download
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"

# Extract
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli

# Add to PATH (requires administrator privileges)
$env:Path += ";C:\aliyun-cli"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)

# Verify
aliyun version
```

---

## Install EBS Plugin

This Skill depends on the `aliyun-cli-ebs` plugin.

```bash
# Enable automatic plugin installation
aliyun configure set --auto-plugin-install true

# Install EBS plugin
aliyun plugin install --names aliyun-cli-ebs

# Update all plugins
aliyun plugin update

# Verify DescribeEvents command availability
aliyun ebs describe-events --help
```

---

## Configure Credentials

### Quick Start (AK Mode)

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

All `aliyun configure` commands support non-interactive flags, recommended for scripts, CI/CD, and Agent automation.

**Obtain AccessKey**

1. Log in to Alibaba Cloud Console: https://ram.console.aliyun.com/
2. Navigate to **AccessKey Management**
3. Create a new AccessKey pair
4. Save the Secret immediately; it is only displayed once

### Configuration Modes

Aliyun CLI supports 6 authentication modes. All examples below use non-interactive flags.

#### 1. AK Mode (Access Key)

Most commonly used for personal accounts and scripts.

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

Suitable for short-term access (Token expires in 1–12 hours).

```bash
aliyun configure set \
  --mode StsToken \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --sts-token v1.0:XXXXXXXXXXXXXXXX \
  --region cn-hangzhou
```

Use cases: CI/CD pipelines, temporary access, cross-account access.

#### 3. RamRoleArn Mode (Assume RAM Role)

```bash
aliyun configure set \
  --mode RamRoleArn \
  --access-key-id LTAI5tXXXXXXXX \
  --access-key-secret 8dXXXXXXXXXXXXXXXXXXXXXXXX \
  --ram-role-arn acs:ram::123456789012:role/AdminRole \
  --role-session-name my-session \
  --region cn-hangzhou
```

Use cases: Cross-account resource access, temporary privilege escalation, role-based access control.

#### 4. EcsRamRole Mode (ECS Instance RAM Role)

When an ECS instance has a bound RAM role, no AK/SK configuration is needed.

```bash
aliyun configure set \
  --mode EcsRamRole \
  --ram-role-name MyEcsRole \
  --region cn-hangzhou
```

Requirement: Must run on an ECS instance with a bound RAM role.

#### 5. RsaKeyPair Mode (RSA Key Pair)

```bash
aliyun configure set \
  --mode RsaKeyPair \
  --private-key /path/to/private-key.pem \
  --key-pair-name my-key-pair \
  --region cn-hangzhou
```

#### 6. RamRoleArnWithEcs Mode (ECS + RAM Role Cross-Account)

```bash
aliyun configure set \
  --mode RamRoleArnWithEcs \
  --ram-role-name MyEcsRole \
  --ram-role-arn acs:ram::123456789012:role/TargetRole \
  --role-session-name my-session \
  --region cn-hangzhou
```

### Environment Variables

Environment variables take the highest priority and override configuration files.

**AK Mode**

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

Use cases: CI/CD pipelines, Docker containers, temporary credential overrides.

### Multi-Profile Management

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

**Use a Specific Profile**

```bash
aliyun ebs describe-events --RegionId cn-hangzhou --profile projectA

export ALIBABA_CLOUD_PROFILE=projectA
aliyun ebs describe-events --RegionId cn-hangzhou
```

**List and Switch Profiles**

```bash
aliyun configure list                      # List all profiles
aliyun configure set --current projectA    # Switch default profile
```

### Credential Loading Priority

Credentials are loaded in the following order (first match wins):

1. Command-line `--profile <name>`
2. Environment variable `ALIBABA_CLOUD_PROFILE`
3. Environment variables `ALIBABA_CLOUD_ACCESS_KEY_ID`, etc.
4. Configuration file `~/.aliyun/config.json` (current profile)
5. ECS instance RAM role (if running on ECS)

---

## Verification

### Test Authentication

```bash
# Basic test - list regions
aliyun ecs describe-regions

# Expected output: JSON region array
```

**Success**: Returns JSON containing `RequestId`.

**Failure**:

- `InvalidAccessKeyId.NotFound` - Incorrect Access Key ID
- `SignatureDoesNotMatch` - Incorrect Access Key Secret
- `InvalidSecurityToken.Expired` - STS Token expired
- `Forbidden.RAM` - Insufficient permissions

### Debug Configuration

```bash
# Display current configuration
aliyun configure get

# Test with DEBUG logging
aliyun ebs describe-events --RegionId cn-hangzhou --log-level=debug

# View current authentication mode
aliyun configure get mode
```

---

## Security Best Practices

1. **Use RAM users, not the root account**
2. **Least privilege principle**: Only grant the `ebs:DescribeEvents` permission required by this Skill
3. **Rotate AccessKeys regularly**
4. **Use RAM roles**: Prefer RAM roles in ECS instances or container environments
5. **Do not commit credentials**: Add `~/.aliyun/config.json` to `.gitignore`
6. **Protect configuration file permissions**:

```bash
chmod 600 ~/.aliyun/config.json
```

---

## Troubleshooting

### Issue: Command Not Found

```bash
which aliyun
echo $PATH
```

Check whether the installation path is in PATH. Reinstall or add to PATH if necessary.

### Issue: Authentication Failed

```bash
aliyun configure get
aliyun ebs describe-events --RegionId cn-hangzhou --log-level=debug
```

- Check whether the AccessKey is valid in the console
- Confirm that AK/SK has no extra spaces or line breaks

### Issue: Permission Denied

```bash
# Error: Forbidden or Forbidden.Action
# Check whether the RAM user has a policy containing ebs:DescribeEvents attached
aliyun ram list-policies-for-user --user-name YOUR_USER_NAME
```

### Issue: STS Token Expired

```bash
# Error: InvalidSecurityToken.Expired
# Reconfigure with a new STS Token
aliyun configure set --mode StsToken \
  --access-key-id XXXX --access-key-secret XXXX \
  --sts-token NEW_TOKEN --region cn-hangzhou
```

### Issue: Incorrect Region

```bash
# Some resources may not be in the specified region
aliyun ecs describe-regions

# Update default region
aliyun configure set region cn-shanghai
```

---

## Advanced Configuration

### Custom Endpoint

```bash
export ALIBABA_CLOUD_EBS_ENDPOINT=ebs-vpc.cn-hangzhou.aliyuncs.com
```

### Proxy Settings

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# Bypass proxy for specific domains
export NO_PROXY=localhost,127.0.0.1,.aliyuncs.com
```

### Timeout Settings

```bash
# Connection timeout (default 10s)
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30

# Read timeout (default 10s)
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

---

## Next Steps

After completing installation and configuration:

1. **Keep plugins up to date**:
   ```bash
   aliyun plugin update
   ```

2. **Explore commands**:
   ```bash
   aliyun ebs --help
   aliyun ebs describe-events --help
   ```

3. **Read documentation**:
   - Aliyun CLI documentation: https://help.aliyun.com/zh/cli/
   - EBS API reference: https://api.aliyun.com/api/ebs/2021-07-30
   - RAM console: https://ram.console.aliyun.com/

---

## References

- Aliyun CLI official documentation: https://help.aliyun.com/zh/cli/
- RAM console: https://ram.console.aliyun.com/
- AccessKey management: https://ram.console.aliyun.com/manage/ak
- EBS API reference: https://api.aliyun.com/api/ebs/2021-07-30
