# CLI Installation & Credential Configuration

## CLI Installation

```bash
# One-click install script (recommended)
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash

# Verify version (requires >= 3.3.3)
aliyun version

# Enable auto plugin install
aliyun configure set --auto-plugin-install true

# Update all installed plugins
aliyun plugin update
```

> **Important**: CLI version must be >= 3.3.3. If the version is too low, re-run the install script to update.

## Credential Configuration

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status

```bash
# Check current credential status
aliyun configure list
```

**If no valid profile exists, STOP here.**
1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
3. Return and re-run after `aliyun configure list` shows a valid profile

### Create RAM Sub-account (Recommended)

If the user has no configured credentials, guide them to:

1. Log in to https://ram.console.aliyun.com to create a RAM sub-account (main account AK/SK has excessive permissions and high leak risk)
2. Create an AccessKey for the RAM sub-account
3. Grant permissions according to the permission list in [ram-policies.md](ram-policies.md)
4. Configure in terminal using `aliyun configure` (**never pass credentials in the session**)
