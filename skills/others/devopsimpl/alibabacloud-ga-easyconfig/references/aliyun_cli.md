# Alibaba Cloud CLI Configuration Guide

> **Version requirement**: This skill requires Alibaba Cloud CLI (`aliyun`) **version 3.3.3 or higher**. Run `aliyun version` to confirm; if the version is below 3.3.3, upgrade using the instructions in the *Install aliyun CLI* section below before executing any `aliyun ga` command.

## Check aliyun CLI Installation

### Linux/macOS

```bash
which aliyun
aliyun version
```

### Windows (PowerShell)

```powershell
Get-Command aliyun
aliyun version
```

### Windows (CMD)

```cmd
where aliyun
aliyun version
```

## Install aliyun CLI

Install or upgrade the CLI **3.3.3 or higher** following the official documentation: [Install Alibaba Cloud CLI](https://help.aliyun.com/document_detail/121541.html). On Windows, download and install the official package from the same page.

Do not download, unpack, or install the CLI from inside an agent session, and do not write binaries into system paths with `sudo`. If the CLI is missing or too old, stop and ask the user to perform the installation, then re-check with `aliyun version`.

## Configure Credentials

Refer to [Configure credentials in Alibaba Cloud CLI](https://help.aliyun.com/zh/cli/configure-credentials). AccessKey authentication is recommended; OAuth is the alternative.

**Security requirement**: Do not ask users for passwords or secrets. Generate an interactive configuration command for the user to run in their terminal. Never attempt to read the user's credential configuration files.

### PowerShell configuration example

```powershell
aliyun configure
```

After running, follow the prompts to enter the AccessKey ID, AccessKey Secret, default region (you can use `cn-hangzhou`), and default output format (recommended: `json`).

## Verify Configuration

### Linux/macOS / Windows (Bash)

```bash
aliyun sts get-caller-identity
```

### Windows (PowerShell)

```powershell
aliyun sts get-caller-identity | ConvertFrom-Json
```

If user information (such as AccountId, UserId, Arn) is returned, the configuration is successful.

## Windows PowerShell Tips

1. **JSON parsing**: In PowerShell, use `ConvertFrom-Json` instead of `jq`:
   ```powershell
$Result = aliyun ga get-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" | ConvertFrom-Json
   $Result.State
   ```

2. **Variable definition**: Use the `$` prefix:
   ```powershell
   $GA_ID = "ga-bp1xxxx"
aliyun ga get-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT"
   ```

3. **Line continuation**: Use the backtick `` ` `` as the line continuation character:
   ```powershell
aliyun ga create-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --user-agent "$env:GA_USER_AGENT" `
  --charge-type POSTPAY
   ```

4. **Output redirection**: To save CLI output to a file and then parse it:
   ```powershell
aliyun ga get-basic-accelerator `
  --biz-region-id cn-hangzhou `
  --accelerator-id "$GA_ID" `
  --user-agent "$env:GA_USER_AGENT" > ga.json
   Get-Content ga.json | ConvertFrom-Json
   ```
