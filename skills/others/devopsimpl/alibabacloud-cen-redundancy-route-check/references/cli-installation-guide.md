# Aliyun CLI Installation and Configuration Guide

This skill requires Aliyun CLI 3.3.3 or later; the latest stable release is recommended. Before any other skill step, detect the local command and automatically install it on supported platforms when it is absent.

## Mandatory Detection and Bootstrap

Run on macOS/Linux before authentication or any cloud API invocation:

```bash
if ! command -v aliyun >/dev/null 2>&1; then
  case "$(uname -s)" in
    Darwin|Linux)
      /bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
      ;;
    *)
      echo "Aliyun CLI is not installed and automatic installation is unsupported on this platform." >&2
      exit 1
      ;;
  esac
fi
command -v aliyun >/dev/null 2>&1 && aliyun version
```

If download, installation, command discovery, or version verification fails, stop before inspecting credentials or calling cloud APIs. This bootstrap must not configure credentials or modify cloud resources.

## Installation or Major Upgrade

For an installed version below 3.3.3 or a major upgrade on macOS/Linux, run:

```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
aliyun version
```

On Windows, automatic installation is unsupported by this skill. Stop and direct the user to the official Alibaba Cloud CLI installer.

## Routine Upgrade

For CLI 3.3.5 and later, prefer:

```bash
aliyun upgrade
aliyun version
```

## Plugin Configuration

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

This skill uses the `cbn` and `vpc` plugins. If they are not installed automatically, run:

```bash
aliyun plugin install --names aliyun-cli-cbn aliyun-cli-vpc
```

## Credential Configuration Principles

- Prefer short-lived identities such as OAuth, STS, or RAM Role.
- Never expose the AccessKey ID/Secret in the conversation, command arguments, logs, or repository.
- Credentials MUST be configured by the user outside the current session.
- The skill only checks for a valid profile with:

```bash
aliyun configure list
```

If no valid profile exists, stop calling cloud APIs, obtain or request a suitable identity from [RAM AccessKey Management](https://ram.console.aliyun.com/manage/ak), and configure it in a secure terminal.

## Multiple Profiles

Select a configured profile with `--profile <profile-name>`, or have the user confirm the current profile before execution. The Agent MUST NOT guess the profile.

## Troubleshooting

| Symptom | Resolution |
|------|------|
| `command not found` | Check PATH and reinstall the CLI |
| Plugin command not found | Update or install `aliyun-cli-cbn` and `aliyun-cli-vpc` |
| `InvalidAccessKeyId.NotFound` | The user checks the credential configuration in a secure environment |
| `InvalidSecurityToken.Expired` | The user refreshes the STS/OAuth identity |
| `Forbidden.RAM` | Follow the Permission Failure Handling process in SKILL.md |
| Empty result | Check profile, region, resource ID, pagination, and permissions; never infer a healthy state |

## Official References

- [Alibaba Cloud CLI documentation](https://www.alibabacloud.com/help/en/cli/)
- [RAM Console](https://ram.console.aliyun.com/)
