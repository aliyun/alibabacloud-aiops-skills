# Credential Check Guide

## Security Rules

- **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
- **NEVER** ask the user to input AK/SK directly in the conversation or command line
- **NEVER** use `aliyun configure set` with literal credential values
- **ONLY** use `aliyun configure list` to check credential status

## Pre-flight Check Steps

### Step 1: Verify CLI Installed

```bash
aliyun version
```

If not installed or version < 3.3.3, install via `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash`.

### Step 2: Check Credential Profile

```bash
aliyun configure list
```

Check the output for a valid profile with configured credentials (AK, STS, or OAuth identity).

**If no valid profile exists, STOP here.** Guide the user:
1. Obtain credentials from https://ram.console.aliyun.com/manage/ak
2. Configure credentials **outside of this session** via `aliyun configure` in terminal
3. Return and re-run after `aliyun configure list` shows a valid profile

### Step 3: Verify Credentials Work

Execute a lightweight test command:

```bash
aliyun domain query-domain-list \
  --api-version 2018-01-29 \
  --page-num 1 \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-domain-manage
```

- **Success**: Returns domain list (even if empty) — credentials are valid
- **Error `InvalidAccessKeyId.NotFound`**: AccessKey is invalid; guide user to recreate
- **Error `SignatureDoesNotMatch`**: AccessKey/Secret mismatch; guide user to reconfigure
- **Error `Forbidden.RAM`**: Credentials valid but insufficient permissions; guide user to attach `AliyunDomainReadOnlyAccess` system policy or create a custom policy with the required domain query permissions

## Error Handling

| Error Code | Meaning | Action |
|-----------|---------|--------|
| `InvalidAccessKeyId.NotFound` | AK does not exist | Guide user to https://ram.console.aliyun.com/manage/ak |
| `SignatureDoesNotMatch` | AK/SK mismatch | Guide user to run `aliyun configure` and re-enter credentials |
| `Forbidden.RAM` | Insufficient permissions | Guide user to attach `AliyunDomainReadOnlyAccess` system policy or create a custom policy with required domain query permissions |
| `IncompleteSignature` | Malformed request | Check CLI version, upgrade if needed |

## Output Format

After credential verification, report status to user:

```
Credential Status:
- CLI Version: {version}
- Profile: {profile_name}
- Identity: {account_type}
- Domain API Access: {OK / Failed - reason}
```
