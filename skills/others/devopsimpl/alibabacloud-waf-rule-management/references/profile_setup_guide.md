# Alibaba Cloud CLI Profile Configuration Guide

> This document provides configuration guidance for Alibaba Cloud CLI profiles, suitable for users using this skill for the first time.

---

## What is a Profile?

A profile is a configuration item used by Alibaba Cloud CLI to store authentication information (AccessKey ID, AccessKey Secret, etc.). Using a profile allows you to:
- ✅ Securely manage multiple accounts/environments
- ✅ Avoid passing credentials in plain text in commands
- ✅ Improve portability and security of commands

---

## Configuration Steps

### Prerequisite: Install Alibaba Cloud CLI

**macOS (using Homebrew)**:
```bash
brew install aliyun-cli
aliyun version  # Verify version >= 3.3.3
```

**Linux**:
```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
mkdir -p ~/.local/bin && mv aliyun ~/.local/bin/
export PATH="$HOME/.local/bin:$PATH"  # Add to ~/.bashrc or ~/.zshrc for persistence
aliyun version
```

**Windows**:
1. Download: https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip
2. Extract and add to PATH environment variable
3. Verify: `aliyun version`

---

### Step 1: Obtain AccessKey

1. Log in to Alibaba Cloud RAM Console: https://ram.console.aliyun.com
2. In the left navigation, select **Identity Management** → **Users**
3. Find the RAM user you want to use, click to enter details
4. Click **Create AccessKey** or use an existing AccessKey
5. ⚠️ **Save the AccessKey Secret immediately** (only shown once)

> **Security Tips**:
> - ❌ Do NOT use the primary account's AccessKey
> - ✅ Create a RAM user and follow the principle of least privilege
> - ✅ Rotate AccessKeys regularly

---

### Step 2: Configure Profile (Interactive)

Run the following command and follow the prompts:

```bash
aliyun configure
```

The system will prompt you to enter:
- **Access Key Id**: Paste your AccessKey ID
- **Access Key Secret**: Paste your AccessKey Secret
- **Default Region Id**: Enter `cn-hangzhou` (domestic) or `ap-southeast-1` (overseas)
- **Default Output Format**: Press Enter directly (default json)
- **Default Language**: Enter `en` (English)

---

### Step 2 (Alternative): Configure Profile (Non-Interactive)

If you want to configure automatically in a script, you can use the non-interactive command:

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-access-key-id> \
  --access-key-secret <your-access-key-secret> \
  --region cn-hangzhou
```

> ⚠️ **Security Warning**: Non-interactive commands will leave credential traces in shell history. It is recommended to use interactive configuration or clear shell history after use.

---

### Step 3: Configure SLS Log Query Credentials (Required for WAF Skill)

WAF log queries use the `aliyun sls get-logs-v2` command, which requires the SLS plugin:

```bash
# Install SLS plugin (if not installed)
aliyun plugin install --names aliyun-cli-sls

# Verify installation
aliyun sls get-logs-v2 --help
```

Credentials use the same default credential chain configured in Step 2.

---

## Verify Configuration

### Verify aliyun CLI

```bash
# Test authentication (query available regions)
aliyun ecs describe-regions \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

If configuration is successful, you will see a JSON-formatted list of regions.

### Verify SLS Query

```bash
# Test STS identity retrieval
aliyun sts get-caller-identity \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-rule-management/{{SESSION_ID}}"
```

If configuration is successful, you will see AccountId and other information.

---

## Profile Storage Location

The configuration file is stored at: `~/.aliyun/config.json`

Example content:
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

> 🔒 **Security Tip**: Ensure this file has correct permissions: `chmod 600 ~/.aliyun/config.json`

---

## Important: Do NOT Use --profile Parameter in This Skill

**CRITICAL**: This Skill relies on the **default credential chain**. Do NOT use the `--profile` parameter in any CLI command.

- ❌ `aliyun waf-openapi describe-instance --profile waf-diag` (FORBIDDEN)
- ✅ `aliyun waf-openapi describe-instance` (rely on default credential chain)

If you have multiple profiles, set the desired profile as default before using this Skill:
```bash
# Set default profile
aliyun configure set --current <profile-name>
```

---

## Authentication Modes

This skill supports the following authentication modes:

| Mode | Use Case | Configuration Example |
|------|---------|---------|
| **AK** | Personal account/scripts | `aliyun configure --mode AK` |
| **StsToken** | Temporary access (1-12 hours) | `aliyun configure --mode StsToken` |
| **EcsRamRole** | ECS instance RAM role | `aliyun configure --mode EcsRamRole` |
| **RamRoleArn** | Cross-account/elevated access | `aliyun configure --mode RamRoleArn` |

> 💡 **Recommendation**: Daily use with AK mode is sufficient. For enterprise environments, RAM roles or STS temporary credentials are recommended.

---

## Common Issues

### Q: Command returns "InvalidAccessKeyId.NotFound"
**A**: AccessKey ID is incorrect, please check if it was copied correctly.

### Q: Command returns "SignatureDoesNotMatch"
**A**: AccessKey Secret is incorrect, please reconfigure.

### Q: Command returns "Forbidden.RAM"
**A**: Insufficient permissions, please check if the RAM user has the correct policies attached.

### Q: aliyun command not found
**A**: Not installed or not in PATH, please refer to prerequisites to reinstall.

### Q: aliyun sls get-logs-v2 command not found
**A**: SLS plugin not installed, run: `aliyun plugin install --names aliyun-cli-sls`

---

## Reference Resources

- Official documentation: https://help.aliyun.com/zh/cli/
- RAM Console: https://ram.console.aliyun.com/
- AccessKey Management: https://ram.console.aliyun.com/manage/ak

---

## Security Best Practices

1. **Use RAM users instead of primary account**: Create a dedicated RAM user and grant minimum permissions
2. **Rotate keys regularly**: Recommend changing AccessKey every 90 days
3. **Use temporary credentials**: For CI/CD or temporary access, use STS Token
4. **Protect configuration files**: `chmod 600 ~/.aliyun/config.json`
5. **Do NOT commit credentials to code repositories**: Add config.json to .gitignore

---

> Once configuration is complete, you can use this skill for WAF diagnosis and queries!
