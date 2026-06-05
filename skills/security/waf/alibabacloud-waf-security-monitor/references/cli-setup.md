# CLI Credential Setup

## CLI Installation

Version >= 3.3.3 required. See cli-installation-guide.md referenced in SKILL.md for installation instructions.

## Credential Configuration

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
> - Configure credentials **outside of agent sessions** via `aliyun configure` in terminal or environment variables

```bash
# Check current credential configuration (view status only, never print credential values)
aliyun configure list
```

### Recommended: OAuth Mode

```bash
# OAuth mode login (recommended, no manual AK/SK management needed)
aliyun configure --mode OAuth
```

### Create RAM Sub-account (Recommended)

If the user has no AK/SK, guide them to:

1. Log in to https://ram.console.aliyun.com to create a RAM sub-account (root account AK/SK has excessive permissions, high leak risk)
2. Create an AccessKey for the RAM sub-account
3. Run `aliyun configure` outside of agent sessions to configure credentials
4. Grant permissions to the sub-account per the RAM policies referenced in SKILL.md
