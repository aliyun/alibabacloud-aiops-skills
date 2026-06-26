---
name: alibabacloud-agent-toolkit-install
description: >
  Install Alibaba Cloud Agent Toolkit end-to-end: verify and set up prerequisites
  (uv, Alibaba Cloud CLI, authentication, CLI plugins, MCP Server Core, bearer
  token exchange), then install the toolkit via openplugin. Use when: alibabacloud
  agent toolkit install, environment check, prerequisite check, setup alibabacloud,
  plugin install, toolkit setup, mcp core setup, aliyun CLI setup.
license: Apache-2.0
metadata:
  domain: environment-setup
  owner: sdk-team
---

# Alibaba Cloud Agent Toolkit — Installation

This skill sets up all prerequisites and installs the Alibaba Cloud Agent Toolkit.
Execute each step **in order** — later steps depend on earlier ones.

## Safety Policy

Each step is classified by risk level. Follow these rules strictly:

| Classification | Agent behavior |
|----------------|----------------|
| **Auto** (read-only check) | Execute without asking. |
| **Confirm** (local install / CLI plugin install) | Show the user the exact command, explain what it does, and **wait for explicit approval** before executing. Never pipe-to-shell silently. |
| **User-only** (interactive / browser-based) | Display instructions for the user to run in a **separate terminal**. Do not attempt to execute. |
| **Confirm-cloud** (cloud-side write) | Explain the cloud resource that will be created, then **wait for explicit approval** before executing. |

---

## Checklist Overview

Run through these steps sequentially. **Skip any step whose check already passes.**

1. [Check / Install `uv`](#step-1-uv) — Confirm
2. [Check / Install Alibaba Cloud CLI (`aliyun`)](#step-2-aliyun-cli) — Confirm
3. [Check CLI authentication](#step-3-cli-authentication) — Auto (check) / User-only (login)
4. [Check / Install CLI plugins](#step-4-cli-plugins) — Confirm
5. [Check / Create MCP Server Core](#step-5-mcp-server-core) — Auto (check) / Confirm-cloud (create)
6. [Check Bearer token exchange](#step-6-bearer-token-exchange) — Auto (check)
7. [Install Alibaba Cloud Agent Toolkit](#step-7-install-toolkit) — Confirm

---

## Observability

All `aliyun` CLI business API commands in this skill **must** include the
`--user-agent` flag for attribution tracking:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-toolkit-install/{session-id}
```

**`{session-id}` generation rules:**

- Generate a UUID v4 once at the **start** of the skill run.
- Reuse the same `{session-id}` value for **every** `aliyun` command within the same
  skill invocation.
- Do **not** replace `{session-id}` with a literal — it is a template variable resolved
  at runtime.

---

## Step 1: `uv` {#step-1-uv}

`uv` is the Python package manager required to start MCP servers.

### Check (Auto)

```bash
uv --version
```

- **Pass** → output shows a version string (e.g. `uv 0.6.x`). Proceed to Step 2.
- **Fail** → `command not found`. Install below.

### Install (Confirm — ask user before executing)

Present the appropriate command to the user and **wait for approval**:

| Platform        | Command |
|-----------------|---------|
| macOS / Linux   | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows (PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

> **Security note:** These are pipe-to-shell commands. Show the command to the user
> and let them decide whether to run it. Do not execute without explicit consent.

After installation, verify with `uv --version`. If the shell cannot find `uv`,
instruct the user to restart their terminal or source their shell profile
(`source ~/.bashrc`, `source ~/.zshrc`, etc.) so the PATH update takes effect.

---

## Step 2: Alibaba Cloud CLI (`aliyun`) {#step-2-aliyun-cli}

### Check (Auto)

```bash
aliyun version
```

- **Pass** → outputs a version string (e.g. `3.x.x`). Proceed to Step 3.
- **Fail** → `command not found`. Install below.

### Install (Confirm — ask user before executing)

Present the appropriate command to the user and **wait for approval**:

#### macOS / Linux

```bash
/bin/bash -c "$(curl -fsSL https://aliyuncli.alicdn.com/install.sh)"
```

> **Security note:** This is a pipe-to-shell command. Show the command and let the
> user decide. Do not execute without explicit consent.

#### Windows (PowerShell)

The installer script is located at [`scripts/install-aliyun-cli-windows.ps1`](scripts/install-aliyun-cli-windows.ps1).

Instruct the user to download or copy the script, then run:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\install-aliyun-cli-windows.ps1
```

After installation, verify with `aliyun version`. If the command is not found,
instruct the user to open a new terminal session so the updated PATH takes effect.

---

## Step 3: CLI Authentication {#step-3-cli-authentication}

### Check (Auto)

```bash
aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-toolkit-install/{session-id}
```

- **Pass** → returns JSON containing `AccountId`, `Arn`, and `UserId`. **Record the
  authentication mode** (AK vs OAuth) — it affects Step 6. Proceed to Step 4.
- **Fail** → error response (e.g. `InvalidAccessKeyId`, `ERROR: ...`,
  or similar). Guide the user through OAuth login below.

> **Note:** The output of `aliyun sts get-caller-identity` tells you who the current
> user is. Share this with the user so they can confirm the correct identity is in use.

### OAuth Login (User-only — user must run in a separate terminal)

The OAuth login flow is **interactive** — it opens a browser. The agent **must not**
attempt to execute this. Display the following instructions for the user:

```
Please run this command in a separate terminal:

    aliyun configure --mode OAuth --profile <ProfileName>

Replace <ProfileName> with a name of your choice (e.g. "default", "myprofile").
This will open a browser for Alibaba Cloud login. Follow the prompts to complete authentication.
```

After the user confirms they have completed the OAuth flow, set the profile as current
and re-run the check:

```bash
aliyun configure set --current <ProfileName>
aliyun sts get-caller-identity --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-toolkit-install/{session-id}
```

If it still fails, suggest the user verify their profiles:

```bash
aliyun configure list
```

---

## Step 4: CLI Plugins {#step-4-cli-plugins}

Two CLI plugins are required. Check each and install any that are missing.

### Check (Auto)

```bash
aliyun plugin show --name openapiexplorer
aliyun plugin show --name sts
```

- **All pass** → each outputs plugin metadata. Proceed to Step 5.
- **Any fail** → `plugin not found` or error. Install the missing ones below.

### Install (Confirm — ask user before executing)

Install only the missing plugins. Show the command and **wait for approval**:

```bash
aliyun plugin install --name openapiexplorer
aliyun plugin install --name sts
```

After installation, re-run the check commands to verify.

---

## Step 5: MCP Server Core {#step-5-mcp-server-core}

The MCP Server Core is a cloud-side resource that can only be created **once** per account.

### Check (Auto)

```bash
aliyun openapiexplorer list-api-mcp-server-cores --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-toolkit-install/{session-id}
```

- **Pass** → response contains `"totalCount": 1`. The MCP Core already exists. Proceed to Step 6.
- **Fail (totalCount 0)** → no core exists. Create one below.
- **Fail (permission error)** → the user's RAM identity lacks the required permission.
  See [Permission Error](#permission-error) below.

### Create (Confirm-cloud — ask user before executing)

This will create a cloud-side MCP Server Core resource in the user's Alibaba Cloud
account (region: cn-hangzhou). **Explain this to the user and wait for explicit approval.**

```bash
aliyun openapiexplorer create-api-mcp-server-core --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-toolkit-install/{session-id}
```

Possible outcomes:

| Result | Meaning | Action |
|--------|---------|--------|
| Success (200) | Core created | Re-run the check to confirm `totalCount: 1` |
| Quota exceeded error | Core already exists (only one allowed) | Treat as success — the core is already provisioned |
| Permission denied / Forbidden | Missing RAM permission | See below |

### Permission Error {#permission-error}

If the user receives a permission error when listing or creating the MCP Core, they need
the following **system policy** attached to their RAM identity:

```
AliyunOpenAPIMCPServerStaticCredentialAccess
```

Instruct the user (or their account administrator) to:

1. Go to the [RAM Console](https://ram.console.aliyun.com/)
2. Find the RAM user or role in use
3. Attach the system policy **AliyunOpenAPIMCPServerStaticCredentialAccess**
4. Re-run the check / create commands

---

## Step 6: Bearer Token Exchange {#step-6-bearer-token-exchange}

This step verifies that the MCP Server Core can successfully exchange a bearer token,
which is required for the MCP server to authenticate API calls at runtime.

### Check (Auto)

> **CRITICAL — use the exact command below, do NOT modify or substitute it.**
>
> `aliyun RamOAuth GenerateAccessToken` is a **non-standard aliyun CLI invocation**.
> It does NOT follow the normal `aliyun <product> <action>` pattern and will NOT
> appear in `aliyun help`, product listings, or OpenAPI metadata. The product name
> `RamOAuth`, the action `GenerateAccessToken`, the `--version`, `--ClientId`,
> `--Scope`, `--endpoint`, and `--method` flags are all **hardcoded values** that
> must be used verbatim.
>
> **Do NOT:**
> - Attempt to discover or construct an alternative command (e.g. `aliyun auth ...`,
>   `aliyun ram ...`, `aliyun sts ...`)
> - Call RAM/STS/IMS APIs to "check" token exchange capability — those APIs serve
>   different purposes
> - Skip this step or replace it with other verification methods
>
> **Just copy and run the command exactly as written:**

```bash
aliyun RamOAuth GenerateAccessToken \
  --version 2026-04-21 \
  --ClientId 4071151845732613353 \
  --Scope "/internal/acs/openapi" \
  --force \
  --endpoint ramoauth.aliyuncs.com \
  --method POST \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-agent-toolkit-install/{session-id}
```

- **Pass** → returns a valid token response. **All prerequisites are satisfied.**
- **Fail (permission error)** → see [Token Permission Error](#token-permission-error).
- **Fail (other error)** → see [OAuth Application Not Installed](#oauth-app-not-installed).

### Token Permission Error {#token-permission-error}

If the error indicates **insufficient permissions** (e.g. `Forbidden`, `NoPermission`,
`User not authorized`), the user needs the system policy:

```
AliyunOpenAPIMCPServerStaticCredentialAccess
```

This is the same policy required in Step 5. If it was already attached, verify it
covers the current RAM identity by re-checking `aliyun sts get-caller-identity`.

### OAuth Application Not Installed {#oauth-app-not-installed}

If the error is **not** a permission error (e.g. `InvalidClient`, `AppNotFound`,
token exchange fails for other reasons), the user likely has not installed the
**API MCP Server official OAuth application** or has not authorized the current user.

Instruct the user to:

1. Open the [RAM Applications Console](https://ram.console.aliyun.com/applications?activeTab=ThirdParty)
2. Find and install the **API MCP Server** official application
3. Authorize the current RAM user/role to use the application
4. Re-run the token exchange check

### AK Mode Users {#ak-mode-users}

If the user authenticated with **AK mode** (AccessKey) in Step 3, the bearer token
exchange can work **without** the API MCP Server OAuth application — AK credentials
can exchange tokens directly.

- If the token exchange **succeeds** in AK mode without the OAuth application installed,
  inform the user that they can optionally remove the default OAuth application at
  the [RAM Applications Console](https://ram.console.aliyun.com/applications?activeTab=ThirdParty)
  if they exclusively use AK mode and want to reduce their application surface.
- If the token exchange **fails** in AK mode, the issue is likely the
  `AliyunOpenAPIMCPServerStaticCredentialAccess` policy — see
  [Token Permission Error](#token-permission-error).

---

## Step 7: Install Alibaba Cloud Agent Toolkit {#step-7-install-toolkit}

All prerequisites are now satisfied. Install the toolkit itself.

### Install (Confirm — ask user before executing)

> **CRITICAL — use `npx openplugin` exactly as shown below. No alternatives.**
>
> The toolkit is distributed through the `openplugin` registry and can **only** be
> installed via `npx openplugin`. It is NOT available on PyPI, npm, or as an
> `aliyun plugin`.
>
> **Do NOT:**
> - Install via `pip` / `uv pip install` (e.g. `alibabacloud-mcp-server` or any
>   other PyPI package — these are different packages)
> - Install via `npm install`
> - Install via `aliyun plugin install`
> - Search for alternative package names or installation methods
>
> **Just run the exact command below:**

```bash
npx openplugin aliyun/alibabacloud-agent-toolkit
```

Show the command and **wait for approval** before executing.

After the command completes, the toolkit plugins are installed and ready to use.

---

## Completion

When all seven steps pass, report a summary:

```
Installation complete:
  ✓ uv installed
  ✓ Alibaba Cloud CLI installed
  ✓ CLI authenticated (as <AccountId / UserName>)
  ✓ CLI plugins installed (openapiexplorer, sts)
  ✓ MCP Server Core provisioned
  ✓ Bearer token exchange verified
  ✓ Alibaba Cloud Agent Toolkit installed
```

The Alibaba Cloud Agent Toolkit is ready to use.
