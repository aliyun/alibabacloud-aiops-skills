# Init & Credentials Reference

## Fallback: Manual CLI Verification & Install (only when deploy_toolkit.py unavailable)

**Version requirements**: aliyun CLI >= 3.3.14, appmanager-cli >= 1.0.9

> **⚠️ Privilege requirement**: The install commands below extract to `/usr/local/bin/`, which requires elevated privileges (`sudo` on Linux/macOS for non-root users). If running as a non-root user, prepend `sudo` to the `tar` step. Alternatively, extract to a user-writable directory in `$PATH` (e.g., `~/.local/bin`).
> **⚠️ Supply chain note**: The downloads come from Alibaba Cloud's official OSS bucket over HTTPS. For higher assurance, verify the binary's SHA256 checksum against the version listed at https://help.aliyun.com/document_detail/121541.html before adding to `$PATH`.

> **⚠️ PATH conflict pitfall (MUST READ)**: On macOS Apple Silicon, `/opt/homebrew/bin` is ahead of `/usr/local/bin` by default. If brew already installed `aliyun-cli`, extracting a fresh build into `/usr/local/bin/` will be shadowed by the brew-installed older version. Symptom: "the upgrade looks successful right after install, but the next shell session reverts to the old version -> repeated upgrades". Before AND after any install/upgrade, run `which -a aliyun` to list **all** matching binaries on PATH and confirm the one resolved by `aliyun version` is the new one.

```bash
# 0. List all aliyun binaries on PATH (the first one wins). Detect any conflict.
which -a aliyun
aliyun version 2>&1     # the version actually in effect right now

# 1. Check aliyun CLI version
aliyun version 2>&1
# → Not found or < 3.3.14: install below. >= 3.3.14: skip to step 2.

# 2. Check appmanager-cli version (only if ~/.aliyun/appmanager-venv exists)
~/.aliyun/appmanager-venv/bin/python -c "from importlib.metadata import version; print(version('appmanager-cli'))" 2>/dev/null
# → < 1.0.9 or fails: rm -rf ~/.aliyun/appmanager-venv (auto-recreates on next run)

# 3. Install aliyun CLI — choose ONE path below by priority
#    Priority A: macOS already manages aliyun-cli via Homebrew -> upgrade with brew
#                (avoids being shadowed by PATH ordering)
brew list --formula | grep -qx aliyun-cli && brew upgrade aliyun-cli

#    Priority B: system-directory install (recommended; writing to /usr/local/bin needs sudo)
#    macOS Apple Silicon:
curl --connect-timeout 30 --max-time 120 -fsSL https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-macosx-latest-arm64.tgz | sudo tar xz -C /usr/local/bin/
#    macOS Intel:
curl --connect-timeout 30 --max-time 120 -fsSL https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-macosx-latest-amd64.tgz | sudo tar xz -C /usr/local/bin/
#    Linux amd64:
curl --connect-timeout 30 --max-time 120 -fsSL https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-linux-latest-amd64.tgz | sudo tar xz -C /usr/local/bin/
#    Linux arm64:
curl --connect-timeout 30 --max-time 120 -fsSL https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-linux-latest-arm64.tgz | sudo tar xz -C /usr/local/bin/

#    Priority C: no-sudo fallback (only when B is not viable) — install into ~/bin and persist PATH in shell rc
mkdir -p ~/bin
curl --connect-timeout 30 --max-time 120 -fsSL <platform-specific URL> | tar xz -C ~/bin/
# ⚠️ `export PATH` only affects the current shell session; it MUST also be appended to the shell rc
#    file, otherwise the next session reverts to the old version:
grep -q 'HOME/bin' ~/.zshrc 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
# bash users edit ~/.bashrc instead. Then refresh the current session immediately:
hash -r    # zsh users: rehash
export PATH="$HOME/bin:$PATH"

# 4. Mandatory post-install/upgrade re-verification (skipping this causes the "repeated upgrade" loop)
which -a aliyun                     # the first entry MUST be the dir you just installed into (/usr/local/bin or ~/bin)
aliyun version                       # MUST be >= 3.3.14
# If the first entry of `which -a` is still the old version (e.g. /opt/homebrew/bin/aliyun), the PATH conflict
# is unresolved:
#   - if the old version is from brew, switch to Priority A: brew upgrade aliyun-cli
#   - otherwise, manually `rm` the old binary, or fix PATH order in ~/.zshrc
```

---

## Configure Credentials

> **⛔ SA-2.12 — DO NOT explicitly handle AK/SK**: This skill MUST rely on the **default credential chain** of the aliyun CLI/SDK. The Agent:
> - **MUST NOT** ask the user to paste AccessKey ID / Secret / STS Token values into the chat
> - **MUST NOT** put raw AK/SK/Token in tool-call arguments, command lines, scripts, or any persisted file (logs, ran_scripts, outputs)
> - **MUST NOT** print or echo credential values, even partially, except for the masked profile diagnostic that `deploy_toolkit.py check` already produces
> - **MUST** instead instruct the user to configure credentials **out-of-band** (in their own terminal / shell profile / RAM role / secrets vault) and only verify by an identity-check call
>
> The ONLY accepted Agent action is: **detect whether some credential source is already in place**, and if not, tell the user how to set one up **themselves**.

> **CRITICAL PROHIBITION**: NEVER run standalone `appmanager` or `aliyun appmanager login`. Credentials must come from the default credential chain below — never from interactive Agent prompts that collect AK/SK.

### Default credential chain (aliyun CLI / SDK auto-resolves in this order)

The Agent only needs ONE of the sources below to be in place:

1. **ECS RAM Role** (recommended on Alibaba Cloud ECS) — instance metadata service auto-provides rotating STS credentials. The user configures it once with `aliyun configure --mode EcsRamRole --ram-role-name <role>` (`<role>` is an identifier, **not a secret**). No AK/SK ever leaves the instance.
2. **Environment variables** — `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, optionally `ALIBABA_CLOUD_SECURITY_TOKEN`. Set by the **user** in their shell profile, secrets manager, or CI vault — outside the Agent session. The Agent MUST NOT read or echo these values.
3. **Pre-existing profile** in `~/.aliyun/config.json` — created in advance by the user with interactive `aliyun configure` (NOT by the Agent passing flags). The skill reads only the profile name and a masked AK preview for diagnostics.

### Verification (the ONLY Agent action — never reads raw credential values)

```bash
# Identity check — succeeds iff some credential source in the default chain is valid.
# Output reveals only Account / RoleArn / UserId, never AK/SK material.
aliyun sts get-caller-identity --output json >/dev/null 2>&1 \
  && echo "✅ credentials valid via default credential chain" \
  || echo "❌ no usable credentials — see remediation below"
```

`deploy_toolkit.py check` already runs an equivalent check. If it exits 1 due to missing credentials, the Agent MUST stop and execute the remediation flow below — it MUST NOT prompt the user for AK/SK in the chat.

### Remediation when credentials are missing

The Agent MUST present these self-service options to the user **verbatim** and wait for the user to confirm completion in their own terminal. **Do not collect AK/SK in the chat under any circumstance.**

> No usable credentials were detected. Please configure them yourself in your own terminal **using one of the methods below** (do NOT paste the AccessKey into this chat or any file):
>
> - **Method A · ECS RAM Role** (recommended on Alibaba Cloud ECS; no AK/SK):
>   `aliyun configure --mode EcsRamRole --ram-role-name <your-role-name>`
> - **Method B · Environment variables** (write into your `~/.zshrc` / `~/.bashrc` / CI Secret; effective after re-login):
>   `export ALIBABA_CLOUD_ACCESS_KEY_ID=...`
>   `export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...`
>   (For temporary credentials also set `export ALIBABA_CLOUD_SECURITY_TOKEN=...`)
> - **Method C · Interactive `aliyun configure`** (credentials only land in local `~/.aliyun/config.json`):
>   `aliyun configure --profile <name> --mode AK` (enter values **at the terminal prompt**, not in this chat)
>
> When done, reply "ready" and I will rerun `aliyun sts get-caller-identity` to verify. **You will never need to paste any AK/SK value into this conversation.**

After the user confirms, the Agent re-runs the verification command above. If it still fails, ask the user to double-check the configuration — do not offer to "help" by accepting AK/SK in chat.

### API Key for Agent type (separate from cloud control-plane credentials)

`$ALIYUN_DASHSCOPE_API_KEY` (matches `sk-*`) is required for the AgentScope runtime — it's a model-service key, **not** a cloud AK/SK, but the handling rule is identical:

- The Agent verifies presence with `[ -n "$ALIYUN_DASHSCOPE_API_KEY" ] && echo "set" || echo "missing"` (never echoes the value).
- If missing, instruct the user to obtain one at https://bailian.console.aliyun.com/cn-beijing?tab=model#/api-key and persist it in their own shell profile.
- The skill never asks the user to paste the key value into the chat.

### Fixing credential errors

`InvalidSecurityToken.Expired` / `InvalidAccessKeyId` → instruct the user to refresh credentials via the same out-of-band methods (A / B / C). Re-verify with `aliyun sts get-caller-identity`. Never accept new AK/SK in the chat.

---

## Non-interactive Init Examples

**For App type (new ECS — default):**
```
aliyun appmanager init --non-interactive \
  --name my-app \
  --type app \
  --region cn-beijing \
  --port 8080
```

**For App type (existing ECS — user provided instance ID):**
```
aliyun appmanager init --non-interactive \
  --name my-app \
  --type app \
  --ecs existing \
  --instance-id i-bp1xxxxxxxx \
  --region cn-beijing \
  --port 8080
```

**For Agent type (new ECS):**
```
aliyun appmanager init --non-interactive \
  --name my-agent \
  --type agent \
  --region cn-beijing \
  --model qwen3.6-plus \
  --api-key sk-xxxxxxxx
```

**For Agent type (existing ECS):**
```
aliyun appmanager init --non-interactive \
  --name my-agent \
  --type agent \
  --ecs existing \
  --instance-id i-bp1xxxxxxxx \
  --region cn-beijing \
  --model qwen3.6-plus \
  --api-key sk-xxxxxxxx
```

> **Note**: `--port` is optional for App type — omit it for background services that don't listen on HTTP. App type does NOT need `--api-key`. Agent type REQUIRES `--api-key` for the AI model runtime. Agent type does NOT use `--port`. `--ecs existing --instance-id` is only needed when user chooses to deploy to an existing ECS instance.

### JSON mode (full config passthrough)

```
aliyun appmanager init --from-json '{
  "metadata": {"name": "my-app", "type": "agent", "regionId": "cn-beijing"},
  "agent": {"model": {"name": "qwen3.6-plus", "apiKey": "sk-xxx"}}
}' --output json
```

### Output

Creates `.appmanager/config.yaml` in the current directory with deployment configuration.

> **WARNING**: `aliyun appmanager init` does NOT support `--overwrite` flag. If config already exists, delete `.appmanager/` directory first or edit the YAML directly.
