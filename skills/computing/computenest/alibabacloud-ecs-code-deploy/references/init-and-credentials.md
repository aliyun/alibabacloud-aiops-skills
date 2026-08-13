# Init & Credentials Reference

## Observability: User-Agent Injection (MANDATORY before any CLI call)

> **⛔ Every `aliyun` CLI call MUST carry this skill's User-Agent** so all API requests are traceable in cloud-side logs. Export the UA env var ONCE at session start, before any `aliyun` / `deploy_toolkit.py` invocation.

**Full UA template:**

```
AlibabaCloud-Agent-Skills/alibabacloud-ecs-code-deploy/{session-id}
```

**session-id unified rules:**
- Generate ONCE per agent session: `SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')` — lowercase UUID (any lowercase-hex random token ≥ 16 chars is equivalent).
- Reuse the SAME session-id for ALL CLI calls within the session — NEVER regenerate per command, otherwise one deployment scatters into untraceable fragments.

**Injection method (modern — env var):**

```bash
# Run ONCE per session (persistent shell); or prefix each command with the same literal value
export SESSION_ID=$(uuidgen | tr '[:upper:]' '[:lower:]')
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills/alibabacloud-ecs-code-deploy/${SESSION_ID}"
```

> ⛔ The legacy `aliyun configure ai-mode enable / set-user-agent / show / disable` mechanism is DEPRECATED — do NOT use it. Do NOT combine `ALIBABA_CLOUD_USER_AGENT` with ai-mode or per-command env prefixes for the same skill token: the CLI stacks these sources and produces duplicate UAs. Set the env var ONCE per session and leave it.

---

## CLI Install/Upgrade Method Priority

> Avoid the "repeated upgrade" pitfall: `/usr/local/bin/` is often shadowed by earlier PATH entries like `/opt/homebrew/bin`.

**On Linux/macOS (Unix):**
1. brew-managed (`check` prints "managed by Homebrew") -> `brew upgrade aliyun-cli`; do NOT overwrite `/usr/local/bin/` again.
2. sudo available -> overwrite into `/usr/local/bin/`, then verify: `hash -r && which -a aliyun && aliyun version`.
3. No sudo -> install to `~/bin/`, ask user to approve appending `export PATH="$HOME/bin:$PATH"` to `~/.zshrc` / `~/.bashrc`.

**On Windows (PowerShell)** — no `brew`/`sudo`/`.zshrc`; `check` auto-detects `os.name == "nt"` and prints PowerShell guidance:
1. Scoop/Chocolatey managed -> `scoop update aliyun-cli` or `choco upgrade aliyun-cli -y`.
2. Otherwise download the official zip and extract into `%USERPROFILE%\bin` (no admin rights), then persist the **User** PATH via `[Environment]::SetEnvironmentVariable("PATH", "$dest;$userPath", "User")` (full snippet in the "Windows (PowerShell) install" section below).
3. After install/upgrade, open a **NEW** terminal so the updated User PATH takes effect, then re-run check.

After install/upgrade, ALWAYS rerun `deploy_toolkit.py check` to confirm. On Unix, if `which -a aliyun` still shows the old binary first, fix PATH order — DO NOT repeat the same overwrite.

---

## Fallback: Manual CLI Verification & Install (only when deploy_toolkit.py unavailable)

**Version requirements**: aliyun CLI >= 3.3.19, appmanager-cli >= 1.1.1

> **🪟 Windows users**: The `curl | sudo tar xz`, `brew`, `~/.zshrc`/`~/.bashrc` PATH and `~/.aliyun/appmanager-venv/bin/python` snippets in this section are **Unix-only (Linux/macOS)**. On native Windows (cmd/PowerShell), skip them and jump to the **"Windows (PowerShell) install"** subsection below. `deploy_toolkit.py check` auto-detects the platform (`os.name == "nt"`) and already prints the correct Windows PowerShell guidance — the manual steps here are only for when the toolkit script is unavailable.

> **⚠️ Privilege requirement (Unix)**: The install commands below extract to `/usr/local/bin/`, which requires elevated privileges (`sudo` on Linux/macOS for non-root users). If running as a non-root user, prepend `sudo` to the `tar` step. Alternatively, extract to a user-writable directory in `$PATH` (e.g., `~/.local/bin`). On Windows there is no `sudo`; install into `%USERPROFILE%\bin` (no admin rights needed) — see the Windows subsection.
> **⚠️ Supply chain note**: The downloads come from Alibaba Cloud's official OSS bucket over HTTPS. For higher assurance, verify the binary's SHA256 checksum against the version listed at https://help.aliyun.com/document_detail/121541.html before adding to `$PATH`.

> **⚠️ PATH conflict pitfall (MUST READ)**: On macOS Apple Silicon, `/opt/homebrew/bin` is ahead of `/usr/local/bin` by default. If brew already installed `aliyun-cli`, extracting a fresh build into `/usr/local/bin/` will be shadowed by the brew-installed older version. Symptom: "the upgrade looks successful right after install, but the next shell session reverts to the old version -> repeated upgrades". Before AND after any install/upgrade, run `which -a aliyun` to list **all** matching binaries on PATH and confirm the one resolved by `aliyun version` is the new one.

```bash
# 0. List all aliyun binaries on PATH (the first one wins). Detect any conflict.
which -a aliyun
aliyun version 2>&1     # the version actually in effect right now

# 1. Check aliyun CLI version
aliyun version 2>&1
# → Not found or < 3.3.19: install below. >= 3.3.19: skip to step 2.

# 2. Check appmanager-cli version (only if ~/.aliyun/appmanager-venv exists)
~/.aliyun/appmanager-venv/bin/python -c "from importlib.metadata import version; print(version('appmanager-cli'))" 2>/dev/null
# → < 1.1.1 or fails: rm -rf ~/.aliyun/appmanager-venv (auto-recreates on next run)

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
aliyun version                       # MUST be >= 3.3.19
# If the first entry of `which -a` is still the old version (e.g. /opt/homebrew/bin/aliyun), the PATH conflict
# is unresolved:
#   - if the old version is from brew, switch to Priority A: brew upgrade aliyun-cli
#   - otherwise, manually `rm` the old binary, or fix PATH order in ~/.zshrc
```

### Windows (PowerShell) install

> On native Windows there is no `curl | sudo tar` / `brew` / `.zshrc`. Use PowerShell to download the official Windows zip, extract into `%USERPROFILE%\bin`, and persist the **User** PATH (no admin rights required). Pick amd64 or arm64 to match your CPU.

```powershell
# 1. Check current version (skip install if >= 3.3.19)
aliyun version 2>$null

# 2. Download + extract the official Windows build into %USERPROFILE%\bin
$u    = "https://aliyun-cli.oss-cn-hangzhou.aliyuncs.com/aliyun-cli-windows-latest-amd64.zip"  # arm64: replace amd64 -> arm64
$zip  = "$env:TEMP\aliyun-cli.zip"
$dest = "$env:USERPROFILE\bin"
Invoke-WebRequest -Uri $u -OutFile $zip
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -Path $zip -DestinationPath $dest -Force

# 3. Persist PATH at the User scope (survives new terminals; no admin needed)
$userPath = [Environment]::GetEnvironmentVariable("PATH","User")
if ($userPath -notlike "*$dest*") { [Environment]::SetEnvironmentVariable("PATH", "$dest;$userPath", "User") }
$env:PATH = "$dest;$env:PATH"   # take effect in the current session immediately

# 4. Verify (open a NEW terminal so the persisted User PATH is picked up)
aliyun version   # MUST be >= 3.3.19
```

> **Package-manager alternative** (if Scoop or Chocolatey is installed): `scoop install aliyun-cli`  or  `choco install aliyun-cli -y`.
>
> **appmanager-cli venv on Windows**: the self-managed venv lives at `%USERPROFILE%\.aliyun\appmanager-venv`, and its interpreter is `Scripts\python.exe` (NOT `bin/python`). To check the version:
> ```powershell
> & "$env:USERPROFILE\.aliyun\appmanager-venv\Scripts\python.exe" -c "from importlib.metadata import version; print(version('appmanager-cli'))"
> ```
> If it is `< 1.1.1` or fails, delete the folder `%USERPROFILE%\.aliyun\appmanager-venv` (it auto-recreates on the next `aliyun appmanager` run).

---

## Configure Credentials

> **⛔ PREFER OAuth OVER AK**: This skill SHOULD guide users to use **OAuth authentication** as the PRIMARY method for providing Alibaba Cloud permissions. OAuth is more secure and convenient than AccessKey (no long-term secret storage needed). The Agent MUST present OAuth as the first option before mentioning AK-based methods.
>
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

1. **OAuth** (RECOMMENDED — most secure and convenient) — the Agent **may run the login command directly**. Before executing, warn the user (verbatim): “⚠️ About to run the OAuth login command. It will open a browser authorization page. **Please complete the authorization in the browser** — otherwise the command keeps blocking and the Agent gets stuck at this step.” Then run:
   ```bash
   aliyun configure --mode OAuth --profile oauth
   ```
   This opens a browser authorization link, then prompts for region (e.g. `cn-hangzhou`) and language (e.g. `zh`). After setup, verify with:
   ```bash
   aliyun sts get-caller-identity --profile oauth
   ```
2. **ECS RAM Role** (recommended on Alibaba Cloud ECS) — instance metadata service auto-provides rotating STS credentials. The user configures it once with `aliyun configure --mode EcsRamRole --ram-role-name <role>` (`<role>` is an identifier, **not a secret**). No AK/SK ever leaves the instance.
3. **Environment variables** — `ALIBABA_CLOUD_ACCESS_KEY_ID`, `ALIBABA_CLOUD_ACCESS_KEY_SECRET`, optionally `ALIBABA_CLOUD_SECURITY_TOKEN`. Set by the **user** in their shell profile, secrets manager, or CI vault — outside the Agent session. The Agent MUST NOT read or echo these values.
4. **Pre-existing profile** in `~/.aliyun/config.json` — created in advance by the user with interactive `aliyun configure` (NOT by the Agent passing flags). The skill reads only the profile name and a masked AK preview for diagnostics.

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
> - **Method A · OAuth** (RECOMMENDED — most secure and convenient, no long-term secret storage). The Agent may run this directly after warning the user to authorize in the browser (otherwise the command blocks and the Agent gets stuck):
>   `aliyun configure --mode OAuth --profile oauth`
>   (This opens a browser authorization link, then prompts for region like `cn-hangzhou` and language like `zh`)
> - **Method B · ECS RAM Role** (recommended on Alibaba Cloud ECS; no AK/SK):
>   `aliyun configure --mode EcsRamRole --ram-role-name <your-role-name>`
> - **Method C · Environment variables** (write into your `~/.zshrc` / `~/.bashrc` / CI Secret; effective after re-login):
>   `export ALIBABA_CLOUD_ACCESS_KEY_ID=...`
>   `export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...`
>   (For temporary credentials also set `export ALIBABA_CLOUD_SECURITY_TOKEN=...`)
> - **Method D · AccessKey one-liner** (a single command — fill in your own AK/SK and run it **in your own terminal**; credentials only land in local `~/.aliyun/config.json`):
>   `aliyun configure set --profile default --mode AK --access-key-id <your-access-key-id> --access-key-secret <your-access-key-secret> --region cn-hangzhou`
>   (Replace `cn-hangzhou` with the target region. Do NOT paste real AK/SK into this chat — run the command yourself.)
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

### Listing existing ECS instances before `--ecs existing`

When the user chooses existing ECS, query the account's 10 most-recently-created instances **in the chosen region** and present them for selection (also support manual instance ID entry):

```bash
# aliyun CLI outputs JSON by default for OpenAPI calls — do NOT add `--output json`
# Plugin mode: lowercase-hyphenated command + kebab-case params.
# ⚠️ Region param is --biz-region-id; ALSO pass --region <REGION> to override the
#    endpoint (otherwise the profile's default region endpoint rejects the call
#    with InvalidOperation.NotSupportedEndpoint).
# ⚠️ Use --profile <DEPLOY_PROFILE> (same account as deployment); if omitted, the CLI
#    falls back to its default profile, which may point to a different account.
aliyun ecs describe-instances --biz-region-id <REGION> --region <REGION> --page-size 100 --profile <DEPLOY_PROFILE> \
  | jq -r '.Instances.Instance | sort_by(.CreationTime) | reverse | .[:10] | .[]
      | "\(.InstanceId)\t\(.InstanceName)\t\(.Status)\t\(.CreationTime)\t\(.PublicIpAddress.IpAddress[0] // "-")"'
```

- Present as a numbered list (InstanceId / Name / Status / CreationTime / PublicIP); user picks by number OR types an instance ID manually.
- **⚠️ Profile must match deployment**: use the same `--profile` (same account) as the deploy step; otherwise the CLI falls back to its default profile, which may point to a different account/site and return zero / wrong instances. `aliyun configure list` shows the available profiles.
- `jq` unavailable → fall back to `aliyun ecs describe-instances --biz-region-id <REGION> --region <REGION> --page-size 10 --profile <DEPLOY_PROFILE> --output cols=InstanceId,InstanceName,Status,CreationTime 'rows=Instances.Instance[]'` (quote `rows=...[]` so the shell does not glob the `[]`; ordering not guaranteed).
- **⚠️ Plugin prerequisite**: `ecs describe-instances` requires the `aliyun-cli-ecs` plugin. If the CLI prompts "Plugin ... not installed", enable auto-install ONCE: `aliyun configure set --auto-plugin-install true` (or `aliyun plugin install --name ecs`). Without this, non-interactive scripts hang on the prompt.
- Zero instances in region → tell the user, then ask for a manual ID or switch to New ECS.
- Pass the chosen ID to `aliyun appmanager init ... --ecs existing --instance-id <ID>`.

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
