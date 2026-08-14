# CLI Installation & Configuration

This file is loaded when a pre-flight check fails, to fix aliyun CLI environment, configuration, and identity issues.

---

## 1. CLI version requirements

- Minimum version: `3.3.3`
- Recommended: always use the latest stable release

### Check command

```bash
aliyun --version
```

### Success example

```
Alibaba Cloud Command Line Interface Version 3.0.230
```

### Install or upgrade

```bash
# macOS / Linux
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash

# Verify
aliyun --version
```

For routine updates when already on CLI >= 3.3.5, prefer:

```bash
aliyun upgrade
```

---

## 2. Automatic plugin installation

PolarDB-X product commands are provided by the aliyun CLI plugin. Enable automatic installation and keep plugins up-to-date.

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

---

## 3. Credential configuration

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status

### Check existing configuration

```bash
aliyun configure list
```

### Success example

```
ProfileName | RegionId    | Mode
default     | cn-hangzhou | AK
```

### When no valid profile exists

**STOP here.** Credentials must be configured outside of this session:

1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
3. Return and re-run after `aliyun configure list` shows a valid profile

> The agent must NEVER handle credential values directly. Only verify credential status via `aliyun configure list`.

---

## 4. Identity verification

```bash
aliyun sts get-caller-identity
```

### Success example

```json
{
  "AccountId": "123456789012****",
  "UserId": "123456789012****",
  "Arn": "acs:ram::123456789012****:user/your-user"
}
```

If it fails, first confirm credentials are configured correctly, or that the STS service is reachable.

---

## 5. jq installation

`jq` is used to parse JSON output from the aliyun CLI.

### macOS

```bash
brew install jq
```

### Linux

```bash
# Debian / Ubuntu
sudo apt-get install jq

# CentOS / RHEL / Alibaba Cloud Linux
sudo yum install jq
```

### Verify

```bash
jq --version
```

Success example:

```
jq-1.7.1
```
