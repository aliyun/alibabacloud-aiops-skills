# Aliyun CLI Installation Guide

## Prerequisites

- Aliyun CLI ≥ **3.3.3** (plugin mode required).
- Network egress to Aliyun OpenAPI endpoints.

## Install / upgrade

### macOS

```bash
brew install aliyun-cli           # first install
brew upgrade aliyun-cli           # upgrade
```

### Linux

```bash
curl -L -o aliyun-cli.tgz https://github.com/aliyun/aliyun-cli/releases/latest/download/aliyun-cli-linux-amd64.tgz
tar -xzf aliyun-cli.tgz
sudo mv aliyun /usr/local/bin/aliyun
aliyun version
```

### Windows

Download the MSI from https://github.com/aliyun/aliyun-cli/releases and run it.

## Configure credentials (USER does this, never the agent)

```bash
aliyun configure
# Default profile? <Enter>
# Authenticate type: AK
# Access Key Id: <USER ENTERS>
# Access Key Secret: <USER ENTERS>
# Default Region Id: cn-shanghai
# Default Output Format: json
# Default Language: en
```

The agent verifies only via `aliyun configure list` — it never reads or writes AK/SK.

## Install / update the `paistudio` and `aiworkspace` plugins

```bash
aliyun configure --auto-plugin-install true
aliyun plugin update
aliyun plugin list | grep -E "paistudio|aiworkspace"
```

The plugins are fetched on demand the first time you run any `aliyun paistudio ...` or `aliyun aiworkspace ...` command.

## Verify

```bash
aliyun version
aliyun paistudio list-quotas --region cn-shanghai --page-size 1
aliyun aiworkspace list-workspaces --region cn-shanghai --page-size 1
```

## References

- Official Documentation: https://help.aliyun.com/zh/cli/
- Plugin sources:
  - https://github.com/aliyun/aliyun-cli-paistudio
  - https://github.com/aliyun/aliyun-cli-aiworkspace
