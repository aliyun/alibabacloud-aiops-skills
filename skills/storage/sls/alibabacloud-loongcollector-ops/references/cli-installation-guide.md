# Aliyun CLI + SLS Plugin Installation

## 1. Install / upgrade Aliyun CLI (>= 3.3.3, >= 3.3.5 recommended)

First install or major upgrade (universal script):
```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
```

Routine update when CLI >= 3.3.5 (prefer built-in self-update):
```bash
aliyun upgrade
```

Verify:
```bash
aliyun version   # must be >= 3.3.3
```

Installing/upgrading the CLI is a local environment change — inform the user before doing it.

## 2. Install the SLS plugin

Collection subcommands use the dedicated `aliyun-cli-sls` plugin, which exposes hyphenated subcommands (e.g. `aliyun sls get-logs-v2`, `aliyun sls list-machines`).

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin install --names aliyun-cli-sls
aliyun plugin update
```

Verify the plugin is active (help header notes "provided by the installed plugin 'aliyun-cli-sls'"):
```bash
aliyun sls --help
```

Verified baseline: Aliyun CLI 3.4.6 + aliyun-cli-sls 0.7.0 (API version 2020-12-30).

## 3. Configure credentials (outside this session)

Do NOT paste AK/SK into the chat. Configure via terminal:
```bash
aliyun configure    # interactive; sets profile, region
```
Then confirm status only (never prints secrets):
```bash
aliyun configure list
```

## 4. Notes

- If the base CLI shows RESTful usage (`aliyun sls <ApiName>`) instead of hyphenated subcommands, the plugin is not installed/active — re-run step 2.
- Always read `aliyun sls <cmd> --help` before first use of a command to confirm exact flags for the installed plugin version.
