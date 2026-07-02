# Aliyun CLI Installation & Plugin Setup (OpenAPI Troubleshoot)

This guide covers the minimum setup to run `openapiexplorer` troubleshoot commands. For full CLI installation, credential configuration, and OAuth setup, see [alibabacloud-cli-guidance/references/installation-guide.md](../../alibabacloud-cli-guidance/references/installation-guide.md).

## Version Requirement

**Aliyun CLI >= 3.4.0 required.**

```bash
aliyun version
```

If not installed or version too low:

```bash
curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash
```

Or on macOS with Homebrew:

```bash
brew install aliyun-cli
brew upgrade aliyun-cli
```

## Install OpenAPI Explorer Plugin

```bash
aliyun plugin install --names aliyun-cli-openapiexplorer
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

Verify:

```bash
aliyun plugin list | grep openapiexplorer
aliyun openapiexplorer get-request-log --help
aliyun openapiexplorer get-own-request-log --help
aliyun openapiexplorer get-error-code-solutions --help
```

## Configure Credentials

```bash
# Interactive setup (recommended for first-time users)
aliyun configure

# Or via environment variables (automation / CI)
export ALIBABA_CLOUD_ACCESS_KEY_ID=<key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<key-secret>
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

Verify:

```bash
aliyun configure list
aliyun sts GetCallerIdentity
```

**Security:** Never echo or log AK/SK values.

## User-Agent (Agent Sessions)

Every cloud API CLI command must include `--user-agent` with a session ID. See the **Observability** section in [SKILL.md](../SKILL.md) for session-id generation rules and the UA template.

## Quick Smoke Test

Replace `<REQUEST_ID>` with a valid uppercase UUID from a recent API call by the current account:

```bash
aliyun openapiexplorer get-own-request-log --log-request-id <REQUEST_ID> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
aliyun openapiexplorer get-error-code-solutions --product Ecs --error-code Account.Arrearage --user-agent AlibabaCloud-Agent-Skills/alibabacloud-error-troubleshoot/{session-id}
```
