# Aliyun CLI Installation & Configuration Guide

Complete guide for installing and configuring Aliyun CLI for the index configuration manager skill.

> **Aliyun CLI 3.3.8+**: Supports installing and using all published Alibaba Cloud product plugins.
> Make sure to upgrade to 3.3.8 or later for full plugin ecosystem coverage, including the `sls` plugin used by this skill.

## Installation

### macOS

**Using Homebrew (Recommended)**

```bash
brew install aliyun-cli
brew upgrade aliyun-cli

aliyun version
```

**Using Binary**

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-macosx-latest-amd64.tgz
tar -xzf aliyun-cli-macosx-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

aliyun version
```

### Linux

**Debian/Ubuntu and CentOS/RHEL (amd64)**

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz
tar -xzf aliyun-cli-linux-latest-amd64.tgz
sudo mv aliyun /usr/local/bin/

aliyun version
```

**ARM64 Architecture**

```bash
wget https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz
tar -xzf aliyun-cli-linux-latest-arm64.tgz
sudo mv aliyun /usr/local/bin/
```

### Windows

**Using Binary**

1. Download from <https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip>
2. Extract the ZIP
3. Add the directory to your `PATH`
4. Open a new Command Prompt or PowerShell
5. Verify with `aliyun version`

**Using PowerShell**

```powershell
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli
$env:Path += ";C:\aliyun-cli"
[Environment]::SetEnvironmentVariable("Path", $env:Path, [System.EnvironmentVariableTarget]::Machine)

aliyun version
```

### Install / Update the SLS Plugin

```bash
aliyun plugin update
aliyun plugin install --names sls   # only if `aliyun sls --help` says "command not found"
aliyun sls --help
```

## Configuration

### Credential Setup

The skill may check whether credentials exist, but it must not read or print credential values.
Use only this command inside the agent session:

```bash
aliyun configure list
```

If no valid profile is listed, stop and ask the user to configure credentials in their own
terminal. The user can run the interactive wizard:

```bash
aliyun configure
```

Aliyun CLI supports AK, StsToken, RamRoleArn, EcsRamRole, RsaKeyPair, and RamRoleArnWithEcs
authentication modes. Pick the mode that matches the deployment environment:

| Mode | Typical use |
|------|-------------|
| AK | Local development and manually managed RAM users |
| StsToken | Temporary credentials and CI/CD jobs |
| RamRoleArn | Cross-account or role-assumption workflows |
| EcsRamRole | Automation running on ECS with an attached RAM role |
| RsaKeyPair | RSA key-pair authentication |
| RamRoleArnWithEcs | ECS role plus cross-account role assumption |

Credential priority, highest first:

1. `--profile <name>` command-line flag.
2. `ALIBABA_CLOUD_PROFILE`.
3. Environment credentials already present in the process environment.
4. The active profile in the Aliyun CLI config file.
5. ECS instance RAM role.

When multiple profiles are configured, use a profile-specific command rather than changing global
state:

```bash
aliyun sls get-index --profile projectA --project p --logstore l
```

Do not run commands that display secret values, such as `aliyun configure get`,
`cat ~/.aliyun/config.json`, or commands that print credential environment variables.

## Verification

### Test Authentication

```bash
aliyun ecs describe-regions
```

Successful invocation returns a JSON list of regions. Any of the following errors indicates a credential issue:

- `InvalidAccessKeyId.NotFound`
- `SignatureDoesNotMatch`
- `InvalidSecurityToken.Expired`
- `Forbidden.RAM`

### Test SLS plugin & permissions

```bash
aliyun sls get-index --project <project> --logstore <logstore>
```

- Success → both CLI and `log:GetIndex` are working.
- `IndexConfigNotExist` (404) → CLI is working; the Logstore simply has no index. Proceed to the create-index workflow.
- `Unauthorized` → grant the policies in [ram-policies.md](ram-policies.md).

## Security Best Practices

1. **Use RAM users**, not the root account.
2. **Principle of least privilege** — grant only the actions in [ram-policies.md](ram-policies.md) that match the user's task.
3. **Rotate access keys** regularly.
4. **Prefer STS or ECS RAM Role** for temporary or in-cloud workflows.
5. **Never commit `~/.aliyun/config.json`**; add it to `.gitignore`.
6. `chmod 600 ~/.aliyun/config.json` to restrict local file permissions.

## Troubleshooting

### Issue: Command Not Found

```bash
which aliyun
echo $PATH
```

Reinstall or add the binary directory to `PATH`.

### Issue: `aliyun sls --help` says "command not found"

```bash
aliyun plugin update
aliyun plugin install --names sls
```

### Issue: Authentication Failed

```bash
aliyun configure list
aliyun ecs describe-regions
```

### Issue: Permission Denied (`Forbidden.RAM`)

Check that the RAM user has the policies described in [ram-policies.md](ram-policies.md).

### Issue: Wrong Region

```bash
aliyun sls get-index --region cn-shanghai --project <project> --logstore <logstore>
```

A Project lives in exactly one region; a region mismatch returns `ProjectNotExist`.

## Advanced Configuration

### Custom Endpoint

```bash
export ALIBABA_CLOUD_LOG_ENDPOINT=<custom-or-internal-sls-endpoint>
```

### Proxy Settings

```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
export NO_PROXY=localhost,127.0.0.1,.aliyuncs.com
```

### Timeout Settings

```bash
export ALIBABA_CLOUD_CONNECT_TIMEOUT=30
export ALIBABA_CLOUD_READ_TIMEOUT=30
```

## References

- Official Documentation: <https://help.aliyun.com/zh/cli/>
- RAM Console: <https://ram.console.aliyun.com/>
- Access Key Management: <https://ram.console.aliyun.com/manage/ak>
- Aliyun CLI source: <https://github.com/aliyun/aliyun-cli>
