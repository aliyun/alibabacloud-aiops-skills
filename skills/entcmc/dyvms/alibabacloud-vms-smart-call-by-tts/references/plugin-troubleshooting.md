# Plugin Installation Troubleshooting — dyvmsapi (SubmitIntent)

> This document is dedicated to diagnosing and fixing failures at any step of `SKILL.md` §1 "Installation".
> **Each symptom maps to exactly one root cause and one fix path** — do not jump around speculatively.

---

## Decision Tree

```
aliyun dyvmsapi submit-intent --help fails?
├── "aliyun: command not found"          → see §A: CLI not installed
├── "unknown command \"submit-intent\""  → see §B: plugin missing or wrong build installed
├── "lookup cli.aliyun-inc.com: no such host"
│                                        → see §C: not on the Alibaba intranet
├── "invalid flag \"names\"" / "invalid flag \"source-base\""
│                                        → see §D: CLI version too old
├── install command returns 403/404      → see §E: wrong source path or version
├── permission denied (~/.aliyun/...)    → see §F: directory permission issue
└── anything else                        → see §G: catch-all diagnostics
```

---

## §A. `aliyun: command not found`

**Root cause**: Aliyun CLI is not installed.

**Fix**: re-enter SKILL.md §1.1 and run the **environment-aware fallback chain** there (it auto-picks `brew install aliyun-cli` first; if `brew` is unavailable it falls back to a **user-level binary tarball** dropped under `$HOME/.local/bin`). The chain **never pipes a remote install script to a shell** — older one-liner installers that did so silently retried with `sudo`, deadlocked in non-interactive shells (agent sandboxes / CI runners), and are now treated as a security violation by static scanners. The full per-OS / per-architecture / sudo-less recipe matrix lives in [`cli-installation-guide.md`](./cli-installation-guide.md).

After install, **reopen the shell** or `source ~/.zshrc` / `source ~/.bashrc`, then go back to SKILL.md §1.1 and start over.

---

## §B. `unknown command "submit-intent"`

**Root cause**: the dyvmsapi plugin is not installed, or a build that does not contain `submit-intent` is installed (the public-release build / an older pre-release build).

**Step 1: diagnose current plugin state**
```bash
aliyun plugin list 2>&1
```

**Step 2: fix according to the result**

| Current State | Action |
|---|---|
| The list does **not** contain `aliyun-cli-dyvmsapi` | Run the install command from SKILL.md §1.3 directly |
| The list contains `aliyun-cli-dyvmsapi`, but `submit-intent --help` fails | A build without `submit-intent` is installed; uninstall first, then install (below) |

**Uninstall first, then install** (note: `plugin uninstall --name` takes the same plugin name passed to `plugin install --names`, i.e. `dyvmsapi` — not `aliyun-cli-dyvmsapi`. `plugin install` / `plugin uninstall` are CLI tooling commands and DO NOT accept `--user-agent`):
```bash
aliyun plugin uninstall --name dyvmsapi
aliyun plugin install --names dyvmsapi \
  --version 0.1.0 \
  --source-base https://cli.aliyun-inc.com/registry_id/2/env/online/plugins
```

---

## §C. `lookup cli.aliyun-inc.com: no such host` / `connection timeout`

**Root cause**: `cli.aliyun-inc.com` is an **Alibaba intranet-only** domain; the public DNS does not resolve it.

**Fix (one of, by priority)**:

1. **Restore the primary path first**: use the Skill from an Alibaba office network, or connect to the Alibaba intranet via VPN, then return to SKILL.md §1.3 and retry.
2. **Otherwise switch to the external fallback path**: when running in a public sandbox / external CI/CD / non-Alibaba-employee environment with no intranet access, **do not abort the Skill** — switch to SKILL.md §1.alt → §6.alt and route through the zero-dependency Python script [../scripts/dyvmsapi_rpc.py](../scripts/dyvmsapi_rpc.py) which calls the public `dyvmsapi` gateway directly (functionally equivalent). The full execution manual is the reference document [external-network-fallback.md](./external-network-fallback.md).

> **Note**: under path B (external fallback), `SubmitIntent` visibility in the metadata center remains `private` and **has no SLA**; use it only as a fallback. As long as the primary path is reachable, do not switch to the fallback.

**Do not**: try to pull this plugin from any other public registry (`registry.npmjs.org` / `github.com`, etc.) — none of them distribute it.

---

## §D. `invalid flag "names"` / `invalid flag "source-base"` / `unknown shorthand flag`

**Root cause**: the Aliyun CLI version is too old; the reported flag does not exist in the installed CLI version. Inter-version notes:

| Reported flag | First introduced | Notes |
|---|---|---|
| `invalid flag "names"` | Pre-3.3.3 the `plugin` subcommand had a different flag shape | Upgrade to ≥ 3.3.8 |
| `invalid flag "source-base"` | **v3.3.7 (2026-04-16)** first release (see [PR #1299](https://github.com/aliyun/aliyun-cli/pull/1299)) | Upgrade to ≥ 3.3.8 |

**Fix**: re-enter SKILL.md §1.1 and run the **environment-aware fallback chain** there. It auto-picks `brew upgrade aliyun-cli` first, then falls back to a **user-level binary tarball** under `$HOME/.local/bin`, and self-verifies with `aliyun version` at the end. The chain deliberately **does not pipe a remote install script to a shell** — that pattern is flagged as a security violation and also deadlocks waiting for `sudo` in non-interactive shells. After the upgrade, return to SKILL.md §1.3 and retry.

> **[FORBIDDEN] Do not misdiagnose this as a network problem and switch to the external fallback** — `invalid flag` is a **CLI local argument-parsing error**; it has nothing to do with the network, the plugin source, or the plugin name. The external fallback path (SKILL.md §1.alt) is **reserved for `no such host` / `connection timeout` only**. If `nslookup cli.aliyun-inc.com` resolves to an Alibaba intranet IP (`100.64.x.x` / `100.67.x.x`, etc.), the primary path has not failed — the CLI is simply too old and **must** be upgraded.

---

## §E. install returns 403/404 / `plugin not found`

**Root cause**: a parameter is misspelled (most commonly the URL path or version number).

**Cross-check item by item**:

| Item | Must be | Do NOT write |
|---|---|---|
| Domain | `cli.aliyun-inc.com` | `cli.aliyuncs.com` / `aliyuncli.alicdn.com` |
| Path | `/registry_id/2/env/online/plugins` | `/registry_id/2/env/pre/plugins` (deprecated) / missing `registry_id/2` |
| `--names` value | `dyvmsapi` | `aliyun-cli-dyvmsapi` / `vms` / `dyvmsapi-cli` |
| `--version` | `0.1.0` | `0.0.1` / `latest` / omitted |

Copy the full correct command verbatim (`plugin install` is a CLI tooling command and DOES NOT accept `--user-agent`):
```bash
aliyun plugin install --names dyvmsapi \
  --version 0.1.0 \
  --source-base https://cli.aliyun-inc.com/registry_id/2/env/online/plugins
```

---

## §F. `permission denied` writing to `~/.aliyun/plugins/`

**Root cause**: ownership of `~/.aliyun` is wrong (commonly seen after running `aliyun` under `sudo`, or under write-restricted containers / sandboxes).

**Fix** (try **option 1 first**; only fall back to option 2 if ownership repair fails):
```bash
# Option 1 — Repair ownership in place. Non-destructive; preserves credentials, plugins, and ai-mode config.
sudo chown -R $(whoami):$(id -gn) ~/.aliyun

# Option 2 — Quarantine the broken directory by RENAMING it (NOT deleting it).
# This preserves AK/STS credentials, plugins, and ai-mode config in a timestamped backup
# so they can be recovered later (e.g. `cp ~/.aliyun.bak.<ts>/config.json ~/.aliyun/`).
# **Never** run `rm -rf ~/.aliyun` — it is irrecoverable and a static-scanner red flag.
mv ~/.aliyun ~/.aliyun.bak."$(date +%Y%m%d-%H%M%S)"
# Then re-run `aliyun configure` to create a fresh profile.
```

After the fix, return to SKILL.md §1.3 and retry.

---

## §G. Catch-all diagnostics (none of the above match)

Run the diagnostic block below and paste the output to the user:

```bash
# Note: `aliyun version` / `plugin list` / `submit-intent --help` are system / tooling /
# help-mode commands and do NOT accept --user-agent. Only business calls
# (e.g. `aliyun dyvmsapi submit-intent --user-message ...`) carry --user-agent.
echo "=== CLI ===" && aliyun version 2>&1
echo "=== Plugins ===" && aliyun plugin list 2>&1
echo "=== DNS ===" && nslookup cli.aliyun-inc.com 2>&1 | head -5
echo "=== HTTPS ===" && curl -sS -o /dev/null -w "HTTP %{http_code}\n" \
  https://cli.aliyun-inc.com/registry_id/2/env/online/plugins/dyvmsapi/0.1.0/manifest.json 2>&1
echo "=== Help ===" && aliyun dyvmsapi submit-intent --help 2>&1 | head -10
```

Re-triage by comparing the output against §A–§F above. If the issue still cannot be located, advise the user to contact Alibaba Cloud Voice Service technical support.

---

## Quick Reference: what a successful state looks like

```
$ aliyun plugin install --names dyvmsapi --version 0.1.0 \
    --source-base https://cli.aliyun-inc.com/registry_id/2/env/online/plugins
Downloading aliyun-cli-dyvmsapi 0.1.0...
Plugin aliyun-cli-dyvmsapi 0.1.0 installed successfully!

$ aliyun dyvmsapi submit-intent --help
Aliyun CLI 3.3.X
Description: Submit a text intent; the system parses it and executes the corresponding action.
API Version: 2017-05-25
Usage:
  aliyun dyvmsapi submit-intent [parameters]
Parameters:
  --user-message string, natural-language description from the user (required)
  ...
```

As long as `submit-intent --help` produces output of the form above, installation is successful — even if the `plugin install` step printed an `already installed ... will replace` notice in the middle.
