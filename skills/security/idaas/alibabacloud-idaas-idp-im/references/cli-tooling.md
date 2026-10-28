# CLI Tool Matrix and Execution Modes · reference

Definitions of the dual execution modes, the CLI tooling required for each identity source type (installation / auth / liveness probe / capability boundaries), the credential transfer principles, the step × type capability matrix, and the steps that must remain manual. Command details change with tool versions; before executing, treat the live `<tool> --help` output as authoritative.

## Execution modes (selected at S0, settled in one ask)

| Mode | Who executes | Write operations | Read operations |
|---|---|---|---|
| `cli` (provisioned via CLI) | The skill generates and executes the commands | For every command: first show the **exact command** (dry-run first where a dry-run is supported) + the impact statement; execute only after the user confirms, then read back to verify | Execute directly; output is **desensitized before display** |
| `manual` (self-configured in the console) | The administrator operates in their own consoles | The skill provides only steps + impact statements; it does not execute on their behalf | Same as left (or, after the user authorizes it, the skill runs the lookup on their behalf, with the same desensitization) |

- **What counts as "the user confirms" (write-gate semantics)**: the user describing the desired end state in natural language — even imperatively ("rewrite the sync scope to X, then read it back") — states the **goal** and does **not** count as confirmation of a command; in cli mode every write still requires showing the exact command (dry-run first where a dry-run is supported) + the impact statement and receiving the explicit go-ahead. Only an explicit waiver ("no need to confirm, just run it") lifts the gate, and it lifts it only for what it names.
- If not specified, ask this together with `idp_type`/`goals` at S0 in **one single message**; do not assume.
- **Hybrid is the norm**: in `cli` mode, when the tooling falls short for a given step (e.g., creating a WeCom app), that step falls back to `manual` (console steps are provided) while the remaining steps continue over CLI. Declare each fallback as it happens; never fall back silently.
- Modes can be switched at any time; switching does not re-run steps already completed.

## Tool matrix (by idp_type)

| idp_type | Source-side CLI | IDaaS-side CLI (required for all types) | Degree of source-side automation |
|---|---|---|---|
| `dingtalk` | `dws` (dingtalk-workspace-cli, Apache-2.0) | `aliyun` | **High**: full coverage of app creation / credential retrieval / permission grants / release |
| `feishu` | `lark-cli` (`@larksuite/cli`, MIT) | `aliyun` | **Medium**: app creation requires one browser-assisted round; some permissions require Feishu administrator approval before release |
| `wecom` | `wecom-cli` (`@wecom/cli`, MIT) | `aliyun` | **Low**: directory queries only; app creation / credentials / trusted domains / callback domains are not supported at all (the same holds for outbound — the contacts-sync Secret, permissions, and the two trusted-IP entries likewise can only be configured in the console) |

### `aliyun` CLI (IDaaS side, required for all types)

- **Version requirement: >= 3.3.3.** The command forms this skill relies on (kebab-case plugin calls, `--force` hidden interfaces, the `--user-agent` flag) assume a CLI at or above this floor. Check with `aliyun version`; the CLI has no built-in self-update subcommand, so when the installed version is older, upgrade through the official distribution channel it was installed from — `brew upgrade aliyun-cli` on macOS, or the latest release package from the official aliyun CLI releases — before running any command in this skill.
- Liveness probe: `aliyun version`; requires a working, configured profile (region + credentials, from the instance handover deliverable).
- All EIAM invocations in this skill use the **kebab-case plugin form** (`aliyun eiam create-identity-provider`) with kebab-case parameters; the sole exception is the hidden interfaces, which exist only in PascalCase + `--force` form (see `idp-model-openapi.md`).

#### Versioned user-agent bootstrap (required before the first cloud call of a session)

The bootstrap recipe — a fail-closed read of the skill's version file (no cloud call at all when it is unreadable), a fresh random 32-character lowercase hexadecimal session ID generated per session and never shared across skills, and the `--user-agent` declaration on every cloud call in the required format `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}` — is defined in the "Execution mode and CLI tools" section of the main skill file. Every `aliyun` command in this reference assumes that bootstrap has already run; do not repeat it per command.

#### Shell companion tools (declared minimum versions)

The command examples in this skill assume these shell companions at these minimum versions: `curl ≥ 7.29.0` (probes and install scripts; every curl example carries `--connect-timeout 10 --max-time 30`), `jq ≥ 1.5` (credential JSON extraction with `-r`), `openssl ≥ 1.0.2` (session-ID generation with `rand -hex`); `grep`/`read`/`unset`/`history` are POSIX shell utilities with no version floor. The source-side CLIs additionally need Node.js ≥ 18 (`@wecom/cli`, `@larksuite/cli` npm route) or Go 1.23+ / Python 3 when building lark-cli from source. When a companion tool is missing, fall back to the equivalent console step or hand the user a manual command — do not install dependencies on their behalf without asking.
- ⚠️ **Cross-product calls must pass an explicit `--endpoint`**: the profile's global endpoint (e.g., a dedicated eiam endpoint) hijacks calls to other products — `aliyun ecs authorize-security-group` without `--endpoint ecs.cn-hangzhou.aliyuncs.com` (assembled from the target product + region) fails with `InvalidVersion`; the same applies to the other product domains. Also, **`--endpoint` must come before the product name** (`aliyun --endpoint <endpoint> <product> <API> …`) — placed after the API, it errors with: not a valid parameter or flag. (The example is an endpoint-hijacking illustration only — this skill never operates ECS.)
- Read-only validation APIs and pitfalls (parameter naming, key sets that are not fixed, the `--force` hidden APIs): **see `idp-model-openapi.md` for all of them**; not repeated here.
- **Write path (cli mode)**: `create-identity-provider` in one full pass → read back and verify via the hidden APIs → `enable-identity-provider-ud-pull` → `run-synchronization-job` triggers the full sync → `get-synchronization-job`/`list-synchronization-jobs` to follow up → `list-users` to verify the landing. For the step-by-step walkthrough see the `idp-model-openapi.md` section "CLI execution mode: IDaaS-side write path".
- ⚠️ Programmatically desensitize the output of any read API before displaying it (`get-identity-provider` returns the source-side secret in plaintext).
- **Versioned user-agent bootstrap (required before the first cloud call of a session)** — see the dedicated section below.

### `dws` (DingTalk)

- Installation (macOS/Linux): `curl -fsSL --connect-timeout 10 --max-time 30 https://raw.githubusercontent.com/DingTalk-Real-AI/dingtalk-workspace-cli/main/scripts/install.sh | sh` (on Windows go through PowerShell; see the project README). musl (Alpine) is not supported.
- Authentication: OAuth device flow, **requires enterprise administrator authorization**; zero-trust architecture (domain allowlist + least privilege).
- Liveness probe: `dws --version`; write operations always go `--dry-run` preview → confirm → `--yes`; everything carries `--format json`.
- Capabilities (mapped to the main flow): `dws devapp +create` creates an enterprise-internal app (S1, **the response directly contains appKey**; the tool schema takes only the three parameters name/description/icon-media-id, so what gets created is a bare app whose permissions/config must be set separately); `dws devapp +credentials-get` retrieves AppKey/AppSecret (S1; credential JSON paths `data.appKey` / `data.appSecret`); `dws dev app permission add/list` grants permissions per permission point (scopeValue) (S4, **not** `dws permission add`); `dws dev app security config --redirect-urls` configures the login redirect URI (S3, a **hard dependency** of DingTalk QR code logon — without it you get `无效的appid`; see dingtalk.md for details); `dws dev app version create/check-approval/publish/status` is the channel that brings changes into effect (⚠️ the `+version-publish` shortcut is intercepted by the dws security gate with `缺少安全测试租户与回滚合同`; the full path `dws dev app version publish` works); `event subscribe` for event subscriptions; `dws contact` to look up members (source-side data verification; step ① of the three-step attribution in the failure table).
- Boundaries: **the approver must be decided by the user — dws explicitly forbids the agent from choosing on their behalf**; `unifiedAppId` is the primary key that locates write operations and must not be auto-inferred from a list hit; secrets are desensitized. For command specifics defer to the live `dws --help` output.
- The quick binding path (chapter A of the DingTalk reference) has **no CLI equivalent** (QR-code activation/binding is a browser interaction) — for a fully automated flow, take the advanced configuration route (first-party app in chapter B).

### `lark-cli` (Feishu/Lark)

- Installation: `npx @larksuite/cli@latest install` (npm route; building from source requires Go 1.23+ and Python 3).
- Authentication: `lark-cli config init` (configures the app credentials, **must be completed once by the user in a browser**) → `auth login --recommend` or `--scope <scope>` (authorization, likewise browser/device code) → liveness probe `auth status`; `auth check` validates per scope (exit 0 = the permission is held). ⚠️ **`auth login`/`auth check` cover only `用户身份 user_access_token` and cannot serve as the S4 gate on the account-sync side** — IDaaS sync goes through `应用身份 tenant_access_token` (App ID+Secret), whose scopes must be checked separately in the developer console at `权限管理 > 开通权限 > 切到『应用身份权限 tenant_access_token』页`; no CLI or public OpenAPI can grant them. QR-code-logon authentication uses the user identity (`auth login` suffices); sync uses the tenant identity, and the gate only counts as passed once `lark-cli api ... --as bot` actually reads user_id/mobile successfully (see feishu.md S4 and its "CLI-mode recipes and API chains" section for details).
- Capabilities: `lark-cli api GET/POST <endpoint>` for generic calls (covering 2500+ APIs), `schema <method>` to introspect parameters/scope/identity, contact to search users by name/email/mobile number (source-side data verification).
- Boundaries: app creation (config init --new) outputs an authorization link that the user completes in their browser — **not headless**; some `contact:*` scopes require submitting a release request + administrator approval in the Feishu admin console, and **the CLI cannot substitute for that approval**; the redirect URL / event request URL / app homepage / IP allowlist all belong to Feishu's **management plane**, which **has no public OpenAPI write API — `lark-cli` cannot change them** (the `application` domain has only slash-command CRUD, with no scope/version/security commands) — in cli mode these spots are invariably manual: the user fills them in by hand in the developer console. Callback URL rule = `https://<IDaaS-login-domain>/login/common/oauth2/callback`.
- Risk-control note: lark-cli by default sends minimized risk-control signals (OS type, device hardware model) to Feishu's official domains; for enterprise integration / centralized credential management, use the official *Integrating a Self-Developed Agent with the Feishu CLI* guide and the `extension/` extension package; do not change the default security configuration.
- Output contract: success is `ok==true` (stdout, exit code 0), with the error envelope on stderr — judge success by `ok`/the exit code, **not by `code==0`**.

### `wecom-cli` (WeCom)

- Installation: `npm install -g @wecom/cli`. Node ≥ 18.
- Authentication: interactive credential configuration (QR code by default, `--manual` for manual entry).
- Capabilities: messages, mail, docs, to-dos, calendar, meetings, WeDrive, **searching directory members by name/pinyin/alias + fetching members' basic info** (source-side data verification).
- **Boundaries (critical — tell the user up front, truthfully)**: **there is no application-management capability** — creating a self-built app, obtaining AgentId/Secret, configuring trusted domains / enterprise trusted IPs / the authorized callback domain, and setting the visible range are all unsupported (defer to the live `wecom-cli --help`); the contacts-sync Secret, the `读取并编辑通讯录` permission, and the writable range additionally required for outbound likewise can only be configured in the console (see the Outbound (push) chapter of `wecom.md`). → WeCom under cli mode is necessarily hybrid: fully manual on the source side, fully CLI on the IDaaS side.

## Credential transfer principles (implementing hard boundary 1 in cli mode)

**Overall principle: credentials never pass through the conversation/transcript — neither have the user paste a Secret into the chat, nor print out a Secret the CLI has read.**

1. **Credentials already held by the source-side CLI → pass them through directly via command substitution** (DingTalk route; credential JSON paths `data.appKey`/`data.appSecret`):
   ```bash
   CRED=$(dws devapp +credentials-get --unified-app-id <id> --format json)   # not printed
   APPKEY=$(echo "$CRED" | jq -r '.data.appKey')
   APPSECRET=$(echo "$CRED" | jq -r '.data.appSecret')
   aliyun eiam create-identity-provider --profile <p> \
     --instance-id <instance> \
     --dingtalk-app-config AppKey="$APPKEY" AppSecret="$APPSECRET" CorpId=<…> …
     # object parameters as Key=Value pairs; nested JSON is rejected (see the write path in idp-model-openapi.md)
   unset CRED APPKEY APPSECRET
   ```
   Note: once the variables expand, the command-line arguments are visible to `ps` on the same machine for the instant of execution and may end up in shell history (`history` records the unexpanded form) — for customers with stricter security requirements, switch to a temp file (written under `umask 077`, deleted right after use) or fall back to filling the field in by hand in the console; spell out this residual risk before executing.
2. **Credentials the CLI cannot obtain (the WeCom Secret, the Feishu AppSecret) → placeholder template or temp file**: generate the complete command with placeholders such as `<WeComSecret>` and hand it to the user to fill in and run in their local terminal; or the user chooses to fill the field in by hand in the console. **Never ask for the plaintext.** ⚠️ **WeCom outbound uses two Secrets** (the self-built app's `CorpSecret` + the contacts-sync `ContactSecret`, both mandatory; see the Outbound (push) chapter of `wecom.md`) — the two each go through this rule separately, written to separate temp files with distinguishing names. ⚠️ **Feishu AppSecret: lark-cli stores the AppSecret encrypted in the keychain and `config show` masks it as `****`, so the plaintext cannot be exported** — the sole authoritative source of the plaintext is the `凭证与基础信息` page of the developer console — so Feishu must go through this rule (placeholder/temp file) and cannot pass through directly via command substitution the way DingTalk does. Temp-file method: the user enters it silently via `read -rs` → write a temp file with 600 permissions → the command injects it with `--lark-config AppSecret="$(cat /tmp/.xxx)"` → wipe it with `rm -P` after verification. **If the user's shell is zsh**: `read -rs -p "prompt" VAR` fails with `read: -p: no coprocess`; the correct zsh form is `read -rs "VAR?prompt"`, or wrap it in `bash -c '…'`.

   **2a. Build the IDP in the console + paste the AppSecret in by hand (credentials touch neither the CLI nor the conversation; the preferred fallback when security requirements are high)**: when the user is unwilling to use a temp file, or the source-side CLI simply cannot export the plaintext (Feishu is exactly that case), guide the user to **complete everything manually between the two consoles**; the skill only provides step-by-step guidance and never touches the plaintext:
   1. **Get the plaintext AppSecret**: in the source-side developer console (Feishu: the app's `凭证与基础信息` page; DingTalk: the app's `凭证与基础信息`; WeCom: the self-built app's detail page), copy `App Secret` (for Feishu, the first time requires clicking `查看/重置` and passing verification). That page is the sole authoritative source of the plaintext — **do not let the user send it into the conversation**.
   2. **Create the IDP**: IDaaS console → Identity Providers → Other identity providers → pick the corresponding type (Feishu/DingTalk/WeCom) → enter the binding wizard.
   3. **Fill in the credentials**: at the wizard's `应用凭证` step, paste in `App ID`/`App Secret` (for DingTalk: `AppKey`/`AppSecret`+`CorpId`; for WeCom: `CorpID`/`AgentId`/the app `Secret`), plus, for Feishu, `企业编号` → next step; IDaaS validates the API/data permissions on the spot.
   4. **Remaining dimensions**: the sync destination organizational unit, the authentication (QR code logon) toggle, and the field mapping are configured in the wizard's later steps; the result is equivalent to what cli mode produces via `create-identity-provider` (for the field-by-field correspondence see idp-model-openapi.md).
   5. **Verify the landing**: once created, use `aliyun eiam get-identity-provider` (desensitize the output first, see item 3) or the console to check the status of the three dimensions; the subsequent S7 sync can still return to cli mode and be run by the skill.
   - **Hybrid is the norm**: hand-pasting the source-side credential (manual) + running the IDaaS-side sync/verification over the CLI (cli) is a normal combination; just declare each part explicitly (see the "Execution modes" section of this file).
3. **Desensitize the output of any `aliyun eiam` read API first** (programmatically strip by key names `Secret|Password|Token|EncryptKey`) before it enters the conversation/logs/handover deliverable.
4. **Scrub raw error output of cloud credentials before display**: SDK/server error texts (Go-style `Post "https://…?AccessKeyId=STS.NZrb…&SecurityToken=…&Signature=…"`) embed the STS credentials in the signed URL query string; before quoting any raw error into the conversation/logs, programmatically erase the `AccessKeyId`/`SecurityToken`/`Signature` query fields (keep at most the host, path, and error code). Pasting the error verbatim "because it is just an error message" is a leak.
5. **Never dump the environment or credential files wholesale when diagnosing**: no `env`/`printenv` full output and no catting of credential/config files (`~/.aliyun/config.json`, temp credential files, keychain dumps) into the conversation; probe by variable name and print presence only, e.g. `[ -n "$ALIBABA_CLOUD_SECURITY_TOKEN" ] && echo "ALIBABA_CLOUD_SECURITY_TOKEN: set"`.

## Step × type capability matrix (cli mode)

| Main-flow step | DingTalk | Feishu | WeCom |
|---|---|---|---|
| S1 Create the source-side app | `dws devapp +create` | `lark-cli config init` (browser, once) | ❌ Console |
| S1 Retrieve credentials | `dws devapp +credentials-get` → piped straight through | Copy in the console (lark-cli stores it encrypted in the keychain; the plaintext cannot be exported) | ❌ Console → placeholder template |
| S3 Network domain / callback backfill | **Required** for QR code logon: `dws dev app security config --redirect-urls` backfills the IDaaS callback URI (without it you get `无效的appid`) | ❌ Console (management plane; no public OpenAPI write API) | WeCom side ❌ Console; IDaaS side NAE can be done via CLI (NAT/EIP/SNAT are administrator-side billing prerequisites and are not created on the user's behalf; for readiness conditions see the `wecom.md` section "Dedicated public egress IP prerequisites and NAE creation") |
| S4 Source-side authorization / permissions | `dws dev app permission add` (permission changes must release a new version via `version publish` before they enter the effective snapshot) | ⚠️ **Two identities**: QR code logon uses `auth login --scope` (user); account sync must enable the `应用身份 tenant_access_token` scope in the developer console — no CLI can grant it | ❌ Console (visible range) |
| S2/S5/S6 IDaaS-side configuration | `aliyun eiam create-identity-provider` in one full pass (identical across the three types, mapping and authentication config included) | Same as left | Same as left |
| S6 Mapping verification | Hidden API `GetIdentityProviderUserProfileMapping` read back for comparison (identical across the three types) | Same as left | Same as left |
| S7 First full sync | `run-synchronization-job` (identical across the three types; requires explicit user confirmation before triggering) | Same as left | Same as left |
| S7 Authentication live test | **Manual** QR code logon | **Manual** QR code logon | **Manual** QR code logon |

## Steps that must remain manual (not executed on the user's behalf even in cli mode)

1. **Approver selection**: the DingTalk version release (`+version-check-approval` lists the candidates; the user makes the call) and the Feishu release approval — both CLIs explicitly stipulate that the agent must not choose on the user's behalf and must not default to the first candidate.
2. **Browser OAuth / QR-code authorization**: the first `dws` device flow, `lark-cli config init`/`auth login`, WeCom credential configuration.
3. **Live login test for the authentication dimension**: `AuthnStatus=enabled` is only a switch; it counts only when the login page shows the method and a real sign-in succeeds (main SKILL.md S7).
4. **Triggering the first full sync**: deletion risk (hard boundary 3) — even via `run-synchronization-job`, it must not execute until the user explicitly gives the nod.
