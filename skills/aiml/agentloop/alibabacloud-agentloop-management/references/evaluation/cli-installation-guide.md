# Alibaba Cloud CLI Installation Guide

## Prerequisites

- macOS, Linux, or Windows (WSL recommended)
- Python 3.8+ (bundled with CLI installer on most platforms)

## First-time install or major upgrade

Use the universal install script. Download it first so you can review the contents before execution:

```bash
# Step 1: Download the setup script
curl -fsSL --connect-timeout 10 --max-time 120 -o /tmp/aliyun-cli-setup.sh https://aliyuncli.alicdn.com/setup.sh

# Step 2: Review the script contents before running it
less /tmp/aliyun-cli-setup.sh

# Step 3: Execute after verifying the script is safe
/bin/bash /tmp/aliyun-cli-setup.sh
```

> **Security note:** Avoid piping `curl` output directly into `bash` (`curl ... | bash`), as a compromised server or intercepted connection could execute arbitrary code on your machine. Always download, review, then execute.

## Routine update (CLI >= 3.3.5)

Prefer the built-in self-update subcommand:

```bash
aliyun upgrade
```

## Verify

```bash
aliyun version   # must be >= 3.3.3; >= 3.3.5 recommended
```

## Enable automatic plugin installation

```bash
aliyun configure set --auto-plugin-install true
```

## Update existing plugins

```bash
aliyun plugin update
```

## Install AgentLoop plugin

```bash
aliyun plugin install --name aliyun-cli-agentloop
```

Verify:

```bash
aliyun plugin show --name aliyun-cli-agentloop
aliyun agentloop version
```

## Install SLS plugin (for result analysis)

```bash
aliyun plugin install --name aliyun-cli-sls
```

Verify:

```bash
aliyun plugin show --name aliyun-cli-sls
```

## Configure credentials

Run in a terminal outside of the agent session:

```bash
aliyun configure
```

Or set environment variables in your shell profile:

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<your-ak>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<your-sk>
```

Verify (without exposing key values):

```bash
aliyun configure list
```

## Multiple profiles

```bash
# Create a named profile
aliyun configure --profile <profile-name>

# Use a specific profile for a single command
ALIBABA_CLOUD_PROFILE=<profile-name> aliyun agentloop list-evaluators --agent-space <space>
```
