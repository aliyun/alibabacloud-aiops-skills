# CLI Installation Guide

## Required Plugins

This skill orchestrates **two** Alibaba Cloud CLI plugins (plugin mode, lowercase-hyphenated commands):

| Plugin | Source | Used For |
|---|---|---|
| `eflo-controller` | OpenAPI plugin (lingjun controller) | F1-F3 power, F5 node spec change, F6 repair, F7 run-command, F8 group update, F9 tag/RG, all read-only inventory |
| `bssopenapi` | Built-in | F4 subscription renewal (`renew-instance`) and order verification (`query-orders`) |

## Verify aliyun core

```bash
aliyun version
# expected: >= 3.3.3
```

If older or missing:

```bash
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash
exec $SHELL -l
aliyun version
```

## Install plugins

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --name eflo-controller
aliyun plugin install --name bssopenapi
aliyun plugin update
```

## Verify plugins

```bash
aliyun eflo-controller version
aliyun bssopenapi version
```

A non-zero exit / `unknown command` means the plugin is missing - re-run install.

## Configure credentials

```bash
aliyun configure list
# add a profile:
aliyun configure --profile default --mode AK
# or use STS:
aliyun configure --profile sts --mode StsToken
```

**Never** paste real AccessKey ID / Secret in chat - render as `***` when discussing.

## Common installation errors

| Error | Fix |
|---|---|
| `unknown command: "eflo-controller"` | `aliyun plugin install --name eflo-controller` |
| `unknown command: "renew-instance"` (BssOpenApi) | Built-in product; use plugin-mode commands `aliyun bssopenapi renew-instance` / `query-orders` (lowercase-hyphenated commands and flags) |
| `permission denied` when running setup.sh | Use `sudo` or install to `~/.aliyun-cli/`; do not request `required_permissions=all` here. |
| `aliyun: command not found` after install | Add `~/.aliyun-cli/bin` to `PATH` (or `~/.local/bin/aliyun`). |
