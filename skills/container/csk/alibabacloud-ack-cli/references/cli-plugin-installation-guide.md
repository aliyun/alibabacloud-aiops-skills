# Aliyun CLI + `cs` Plugin Installation Guide

ACK from the terminal needs two things: the `aliyun` CLI binary (≥ 3.3.3) and
the `cs` plugin. This file walks through both, plus the RAM permissions and
verification that should be in place before you start running commands.

Generic CLI topics (full 6-mode credential matrix, multiple profile management,
security best practices, advanced troubleshooting) are the Aliyun CLI's own
domain — consult its documentation for those. This file covers what an ACK
user specifically needs.

## Contents

- [§1 Install / upgrade the aliyun CLI](#1-install--upgrade-the-aliyun-cli)
- [§2 Configure credentials](#2-configure-credentials)
- [§3 Install the cs plugin](#3-install-the-cs-plugin)
- [§4 Verify everything is wired up](#4-verify-everything-is-wired-up)
- [§5 Common troubleshooting](#5-common-troubleshooting)
- [§6 Where to go next](#6-where-to-go-next)

> RAM identity / policy requirements are intentionally out of scope here —
> consult ACK RAM documentation for the policies and Actions to attach.

## 1. Install / upgrade the `aliyun` CLI

`aliyun` ≥ 3.3.3 is required by this skill.

### macOS / Linux (recommended one-liner)

Auto-detects architecture (amd64 / arm64) and installs to `/usr/local/bin`:

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/setup.sh)"
aliyun version    # expect >= 3.3.3
```

The same command upgrades an existing install — re-run it whenever a new
version is released.

### macOS — Homebrew (alternative)

```bash
brew install aliyun-cli
brew upgrade aliyun-cli   # to update later
```

### Linux — manual binary (when curl/setup.sh isn't an option)

```bash
# x86_64
wget -qO- https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz | tar xz
sudo mv aliyun /usr/local/bin/

# ARM64
wget -qO- https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-arm64.tgz | tar xz
sudo mv aliyun /usr/local/bin/
```

### Windows

Download `https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip`,
extract, add the directory to `PATH`, then `aliyun version` in a fresh shell.

## 2. Configure credentials

ACK API calls need an authenticated identity. Most teams use long-lived AK
(Access Key) for development and `EcsRamRole` for in-cluster automation.

### AK mode — the common default

```bash
aliyun configure set \
  --mode AK \
  --access-key-id <your-key-id> \
  --access-key-secret <your-key-secret> \
  --region cn-hangzhou
```

Get keys from the RAM console:
<https://ram.console.aliyun.com/manage/ak>. Use a **RAM user**, never the
root account; the secret is shown only once on creation.

### Other modes (one-line summary; see parent skill for full guide)

| Mode | When |
| ---- | ---- |
| `StsToken` | Short-lived credentials in CI/CD; pass `--sts-token <token>` along with AK |
| `EcsRamRole` | Running on an ECS instance with a RAM role attached — no AK needed: `--mode EcsRamRole --ram-role-name <role>` |
| `RamRoleArn` | Cross-account access via role assumption: AK + `--ram-role-arn <arn>` |
| `RsaKeyPair` | RSA key-pair-based identity (rare) |
| `RamRoleArnWithEcs` | ECS RAM role + cross-account assume-role chain |

### Environment variables (override config file — useful in CI)

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=<key-id>
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=<key-secret>
export ALIBABA_CLOUD_SECURITY_TOKEN=<sts-token>   # only for StsToken mode
export ALIBABA_CLOUD_REGION_ID=cn-hangzhou
```

Priority: command-line flag > env var > config file > built-in default.

### Multiple profiles (per-account / per-environment)

```bash
aliyun configure set --profile prod    --mode AK --access-key-id ... --access-key-secret ... --region cn-hangzhou
aliyun configure set --profile staging --mode AK --access-key-id ... --access-key-secret ... --region cn-shanghai

aliyun cs describe-clusters-for-region --profile prod --biz-region-id cn-hangzhou
aliyun configure switch --profile prod
```

## 3. Install the `cs` plugin

The `cs` (Container Service) plugin is what makes `aliyun cs ...` commands
work. Install is idempotent:

```bash
aliyun plugin install --names cs
aliyun plugin list | grep cs                   # confirm: aliyun-cli-cs <version>
```

Or use the bundled scripts (they hard-code `cs` and verify CLI version + plugin
presence in one shot):

```bash
./scripts/check-cs-plugin.sh                   # ✓ ready  /  ✗ exits 1 with fix instructions
./scripts/install-cs-plugin.sh                 # idempotent; --update for non-interactive update
```

### Frequently paired plugins

```bash
aliyun plugin install --names vpc ecs ram      # vSwitches, instance-shape lookups, RAM role queries
```

These come up when creating clusters (need vSwitch IDs, instance types) or
managing per-cluster RAM permissions.

## 4. Verify everything is wired up

One command exercises CLI + plugin + auth:

```bash
aliyun cs describe-clusters-for-region --biz-region-id cn-hangzhou \
  --output cols=cluster_id,name,state rows='clusters[]'
```

Expected outcomes:

| Result | Meaning |
| ------ | ------- |
| List of clusters (or empty list) | ✅ Ready to go |
| `Error: plugin 'cs' not found` | Plugin not installed → step 3 |
| `InvalidAccessKeyId.NotFound` | Wrong AK → re-run `aliyun configure set` |
| `SignatureDoesNotMatch` | Wrong AK secret or whitespace pasted into the secret |
| `Forbidden.RAM` / `NoPermission` | Missing policy → step 4 |
| `aliyun: command not found` | CLI not on PATH → step 1 |

## 5. Common troubleshooting

### CLI version too old

```text
$ aliyun version
3.0.103
```

Plugin commands silently fall back to legacy or fail with cryptic errors.
Re-run the install one-liner from step 1 — it upgrades in place.

### `aliyun plugin install` fails with network error

The plugin manifest is hosted on `aliyuncli.alicdn.com`. If your network
blocks it (offline / restricted CI), download the plugin binary manually
from <https://github.com/aliyun/aliyun-cli> releases and install via
`aliyun plugin install --files <path>`.

### Credentials look right but every call fails with `Forbidden.RAM`

Check the RAM identity actually has the policy attached — sometimes a
policy is attached to a *user group* the user doesn't belong to. From the
RAM console: Users → click user → Permissions tab.

### Wrong endpoint after switching regions

`aliyun configure set --region <r>` changes the **default** region for
subsequent calls. To override per command, pass `--region <r>` (endpoint)
or `--biz-region-id <r>` (business param on `*ForRegion` APIs — see
SKILL.md §6).

### STS token expired mid-session

`InvalidSecurityToken.Expired` — STS credentials are short-lived (usually
1–12 hours). Re-issue them via `sts:AssumeRole` and re-run
`aliyun configure set --mode StsToken`.

## 6. Where to go next

After verification succeeds, return to SKILL.md — its 12 instruction sections
cover the ACK-specific patterns (plugin vs OpenAPI, `--help` discipline,
async tasks, complex JSON, region-unitised APIs, deprecated avoidance, common
commands, kubeconfig, output filtering, pagination, debugging).

For deeper generic CLI topics (security best practices, advanced credential
chains, all 6 auth modes spelled out), consult the Aliyun CLI's own
documentation at <https://help.aliyun.com/zh/cli/>.
