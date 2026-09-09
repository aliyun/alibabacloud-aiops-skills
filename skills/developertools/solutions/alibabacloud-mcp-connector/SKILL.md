---
name: alibabacloud-mcp-connector
description: Operate, run O&M for, and manage Alibaba Cloud through local commands, with no MCP configuration needed. CallCLI runs Alibaba Cloud CLI/API commands to create, read, update and delete resources of any product; RunScript runs Python batch scripts; RunIaC runs Terraform orchestration; plus API retrieval and official-document retrieval to follow the best-practice path. Use this whenever the user needs to do anything with Alibaba Cloud — inspect or change ECS, OSS, VPC, RDS, SLS resources, run batch operations, provision infrastructure, or look up official Alibaba Cloud product documentation. Triggers include "阿里云", "aliyun", "ECS", "OSS", "阿里云 API", "阿里云文档", "官方文档", "产品文档", "云资源", "运维", "Terraform", "documentation".
triggers:
  - "阿里云"
  - "aliyun"
  - "ECS"
  - "OSS"
  - "阿里云 API"
  - "阿里云文档"
  - "云资源"
  - "运维"
  - "Terraform"
---

# Operate, O&M, and Manage Alibaba Cloud

## Observability (MUST follow for every aliyun command)

Before any cloud API invocation, read `references/manifest.json` from this skill's root and use only its top-level non-empty string `version` as `{skill-version}`. If missing or invalid, STOP. NEVER invent, guess, or reuse a version from another skill.

Bind version and session to the current skill name and skill root. Before this skill's first cloud API invocation in a conversation, generate a fresh random 32-character lowercase hexadecimal session ID. Reuse that session ID for this skill throughout the conversation; each skill MUST use a distinct session ID. NEVER copy one from documentation, examples, another skill, or a previous conversation, and NEVER send the literal `{session-id}` placeholder. On a skill switch or return, reread that skill's manifest; never cross-skill reuse either value.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**

Markdown examples may omit the flag for brevity. The Agent MUST append the exact flag to every actual execution, including commands generated or extended at runtime.

**Attach the User-Agent at the remote cloud-call boundary:**

- `CallCLI`: put `--user-agent "..."` inside the JSON `command` field, as part of its Alibaba Cloud CLI string. NEVER pass `--user-agent` as an argument to `mcpx.py`; that is a local usage error (exit code 2).
- `RunScript`: define the complete UA in the submitted Python script and pass `user_agent=UA` to EVERY `call_cli(...)` invocation. Environment variables supplied to the local `mcpx.py` process are not automatically available inside the remotely executed script.
- `RunIaC`: put the complete UA directly in `configuration_source` inside every submitted `provider "alicloud"` block. Local `TF_VAR_*` environment variables do not reach the remote Terraform process, so resolve the real session ID and manifest version into the submitted HCL. An `apply` or `destroy` using `previousProcessId` reuses that planned code.

Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag
and should be excluded.

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
```

**Runtime templates:**

```bash
mcpx call CallCLI '{"command":"aliyun ecs describe-regions --region cn-hangzhou --user-agent \"AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}\""}'
```

```python
UA = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
result = await call_cli(product="Ecs", action="DescribeRegions", params={}, user_agent=UA)
```

```hcl
provider "alicloud" {
  region               = "cn-hangzhou"
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
}
```

```bash
SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version} uv run --python 3.11 scripts/mcpx.py doctor
```

## Confirm with the user before changing anything

Read-only work needs no permission: queries, doc lookups and API discovery run straight away. But before any call that creates, modifies, deletes or costs money, state in plain language what is about to change — product, region, resource identifiers, action — and wait for the user's explicit go-ahead. A general request such as "clean up the idle machines" is not approval for a specific deletion; `RunIaC` `apply` / `destroy` and every mutating `CallCLI` or `RunScript` still need one. If the user has not answered yet, do not proceed.

## When to use

Use this whenever you need to do anything with Alibaba Cloud. The 15 tools cover the full path from "figure out how" to "verify it is done":

| Goal | Main tools | What they do |
|---|---|---|
| **Operate** — perform a concrete action | `CallCLI` | **First choice.** Run Alibaba Cloud CLI/API commands to create, read, update, delete resources of any product |
| **O&M** — batch and multi-step | `RunScript` + `GetTask` | One Python script handles many resources / multi-step flows; poll async tasks to a terminal state |
| **Manage** — infrastructure orchestration | `RunIaC` + `GetTask` | Terraform HCL, plan → apply → destroy, with state management |
| Find the right API | `SearchApis` `ListApis` `GetApiDefinition` `GenerateCLICommand` `ListProducts` `ListProductRegions` | Unsure which API, how to pass parameters, which regions are available |
| Look up authoritative docs | `SearchDocuments` `GetDocument` `GetDocumentTree` `GrepDocuments` | Official doc search, per-product retrieval, full text |
| Transfer files | `GetPresignedUrl` | OSS presigned URL, to pass large files into `RunScript` / `RunIaC` |

**What "best-practice path" means:**

- If unsure, confirm parameters with `GetApiDefinition` or the docs first, then run `CallCLI` — do not guess-and-try
- Do batch operations in one `RunScript` run, not by looping `CallCLI`
- Do infrastructure changes via `RunIaC` plan-then-apply (see the diff before landing), not scattered commands
- Read calls carry `x_output_jmespath_filter` by default; do not push a 50KB raw response into context
- For Alibaba Cloud official documentation, use `SearchDocuments` / `GetDocument` / `GetDocumentTree` / `GrepDocuments` — **never `web_search`, and never scrape `help.aliyun.com` via `web_fetch`**. These tools query the official Alibaba Cloud doc corpus directly, scoped by product, and are authoritative and current; web searching/scraping is unscoped, slower, and may return outdated or third-party content. This holds even for a pure "search the docs" request with no resource operation involved.

The capability comes from `alibabacloud.mcp-proxy`, exposed as local commands by `scripts/mcpx.py`, covering all Alibaba Cloud product lines.

No MCP configuration is needed — so it also works in environments where `mcpServers` cannot be injected into the agent client. It keeps no resident process; each call is reclaimed when done.

## Mandatory: route every cloud operation through `mcpx`

When this skill is active, **every** Alibaba Cloud operation goes through `mcpx call <Tool>` (tool mapping: see "When to use" and "Selection order"). Do **not** bypass it with direct tools — even when a direct tool seems simpler and would also work. Bypassing skips the proxy's authentication, transport, validation, cost preview, and observability, and is out of scope for this skill:

- **No direct `aliyun` CLI in the shell.** Wrap it: `mcpx call CallCLI '{"command":"aliyun ..."}'`. (The only `aliyun` you run directly is none — `mcpx login` / `mcpx doctor` already wrap it.)
- **No cloud SDKs and no hand-rolled request signing** — that includes Alibaba Cloud SDK packages (`oss2`, `alibabacloud-*`, `aliyun-python-sdk-*`) and any code that computes a signature itself. For a presigned URL use `mcpx call GetPresignedUrl`; for custom logic use `mcpx call RunScript`.
- **No local `terraform`.** Use `mcpx call RunIaC` (plan → apply → destroy) + `mcpx call GetTask`.
- **No `web_search` / `web_fetch` for Alibaba Cloud docs.** Use `mcpx call SearchDocuments` / `GetDocument` / `GetDocumentTree` / `GrepDocuments`.

If a task seems doable with a direct CLI/SDK/terraform/web call, it is still in scope here — do it through the matching `mcpx call <Tool>` instead.

## Prerequisites

| Dependency | Purpose | Required to call tools | Required to set up credentials first time |
|---|---|---|---|
| `uv` / `uvx` | Starts the service and provides the Python runtime (no system Python needed) | Yes | Yes |
| Alibaba Cloud identity | Authentication | Yes | — |
| Network egress | Downloads dependencies on first run | First run | Yes |
| `aliyun` CLI | Configures credentials | No | **Yes** |

The `aliyun` CLI row is easy to misread: **calling tools does not need it** (calls execute remotely), but `login` hard-depends on it. So in an environment with no credentials yet, it is **required to get started**; the real dependency chain is:

```
doctor (no credentials) → install aliyun CLI → login → doctor passes
```

Only when credentials are already in place (`~/.aliyun/config.json` exists, or on ECS via the metadata service) is it truly optional.

`doctor` tells you what is missing. In an environment where `uv` is absent and there is no network egress, it cannot run — do not retry repeatedly; state the situation directly.

## Step 1: mandatory self-check

```bash
uv run --python 3.11 scripts/mcpx.py doctor
```

**Do not attempt any tool call before the self-check passes.** Credential problems surface at the handshake stage; forcing a tool call only yields a meaningless error.

`doctor` checks in order: MCP server command availability → Python runtime → credential source → handshake connectivity → current identity (`AccountId` / `Arn` / `IdentityType`).

## First-time setup

### Step 1: run `doctor` to see what is missing

### Step 2: install `uv` if missing

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 3: install the `aliyun` CLI if missing

Most environments do not have it.

**macOS / Linux** (auto-detects architecture):

```bash
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"
```

**Windows** (PowerShell; writing the Machine-level PATH needs admin rights):

```powershell
# Download
Invoke-WebRequest -Uri "https://aliyuncli.alicdn.com/aliyun-cli-windows-latest-amd64.zip" -OutFile "aliyun-cli.zip"

# Extract
Expand-Archive -Path aliyun-cli.zip -DestinationPath C:\aliyun-cli

# Add to PATH: read the Machine scope, then append
$machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
[Environment]::SetEnvironmentVariable("Path", "$machinePath;C:\aliyun-cli", "Machine")

# Verify in a new terminal
aliyun version
```

> On Windows, do **not** use `$env:Path += ...` and then write the whole `$env:Path` back to the Machine scope. In PowerShell `$env:Path` is the merged Machine+User value, so writing it back permanently copies user-level entries into the machine level, bloating it on every run. The form above reads Machine only and appends, avoiding this.

After installing, confirm `aliyun version` is >= 3.3.3. On Windows you must open a new terminal to see the PATH change.

> **This modifies the system. Get the user's explicit consent before running it on their behalf.** If they decline, give them the command to run themselves.

The `aliyun` CLI is only needed to configure credentials — it is **not a runtime dependency**; tool calls execute remotely.

### Step 4: log in (only if `doctor` reports no usable credential)

**Skip this when `doctor` already passed** — a passing handshake means a working credential (AK/SK, OAuth token, STS, or an ECS RAM role) is already in place and in use; do not re-login. Only log in when `doctor` reports no credential, or an invalid/expired one. (A 403 at the handshake is a missing RAM permission, not a credential problem — re-login does not fix it; see Troubleshooting.)

```bash
uv run --python 3.11 scripts/mcpx.py login --region cn-hangzhou
```

> **Run this in the background.** It waits for a human to click authorize in a browser, so the duration is unpredictable: about 5s when the browser already has an authorized session, or it waits until timeout when nobody authorizes. A foreground blocking call will hang.

> **It overwrites credentials.** Without `--profile`, `login` configures the **currently active aliyun profile**, replacing its existing credentials. Before starting, `login` prints `即将配置 aliyun profile: X` — **relay this line to the user** and get confirmation that overwriting is OK. To write elsewhere, use `--profile NAME`.

`login` auto-answers all terminal prompts and prints the authorization URL immediately. **As soon as you read the URL from the output, relay it to the user** and ask them to complete authorization in the browser. The user clicks once; everything else is automatic.

Also remind the user: **whichever identity is logged into the browser is the identity that gets authorized.** If the browser is logged into the primary account, the resulting credentials are the primary account's — which conflicts with the "use a least-privilege RAM user" principle. After login, check `IdentityType` with `doctor`.

Optional flags: `--profile` (defaults to overwriting the active profile), `--region` (default `cn-hangzhou`), `--site cn|intl` (default `cn`), `--timeout` (default 180s). Use `--site intl` for the international site.

### Step 5: verify

```bash
uv run --python 3.11 scripts/mcpx.py doctor
```

When the `[5]` identity line prints real account info, you can start calling tools.

### Servers without a browser

The OAuth callback address is `127.0.0.1:12345` on the machine running the command. On a remote server, copying the URL to a local browser **cannot reach the callback**. Two options:

- SSH port forwarding: `ssh -L 12345:127.0.0.1:12345 user@host`, then run `login`
- Skip OAuth: on ECS, bind a RAM role to the instance (no keys or files needed), or have the user run `aliyun configure --mode AK` in their own terminal

## Credential security baseline

Every tool call (`CallCLI` / `RunScript` / `RunIaC`) authenticates **server-side** through the proxy's credential chain (the `~/.aliyun/config.json` / env / ECS-metadata source that `doctor` reports). You never need to read, set, pass, inspect, or debug credentials yourself — and you must never expose them. These five are non-negotiable:

1. **Never ask the user to paste AK/SK into the conversation.** Once pasted, the secret enters the session record and logs. To configure a key, output a command and let the user run it in their own terminal.
2. **Never print, echo, log, or dump credential values** — including the credential env vars `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` / `ALIBABA_CLOUD_SECURITY_TOKEN`: do not `env` / `printenv` / `os.environ` them, and do not write code that reads or prints them. Do not turn on verbose/debug logging that surfaces auth headers (`TF_LOG=debug` for Terraform, HTTP-client debug, `aliyun --debug`) — these print the live `x-acs-security-token` / `Authorization` value into the transcript. When diagnosing, report only "set / not set", plus the identity returned by `aliyun sts get-caller-identity`.
3. **Never write credentials to any file.** Not into this skill directory, not into files you create, not into logs. When the user needs to create `~/.aliyun/config.json` by hand, the user does it.
4. **Never put credentials into any tool argument** — not the `command` string of `CallCLI`, not the `code` (HCL) of `RunIaC`, not the `script` of `RunScript`. All of them are sent to the remote gateway and may be logged. For `RunIaC` specifically, do **not** put `access_key` / `secret_key` in the `provider "alicloud"` block — credentials are injected automatically server-side; the provider block only needs `region` (plus the UA `configuration_source`).
5. **Use a least-privilege RAM user, not the primary account's AK.**

Two more prohibitions:

- **Do not** run `aliyun configure set --access-key-secret <value>`: command-line args are visible to other processes on the same machine (`ps`) and land in shell history.
- **Do not** put `export ALIBABA_CLOUD_ACCESS_KEY_SECRET=...` into `~/.zshrc`: a long-term key in plaintext on disk is worse than a `~/.aliyun/config.json` with 600 permissions.

### How the credential chain resolves (and its trap)

Priority is **environment variables → `~/.aliyun/config.json` → ECS metadata service**. Two consequences:

- An `export` the user ran **in some other terminal** never reaches this script: the script is started by the agent, in a different process tree, inheriting the agent's own environment. Explain this, then guide them to `login`.
- But any `ALIBABA_CLOUD_*` var that **is** present in the agent's own environment outranks `config.json`. If that set is incomplete — for instance an STS identity whose `ALIBABA_CLOUD_SECURITY_TOKEN` is set but empty — the proxy still signs with it and the gateway rejects the signature, **even though `config.json` holds a valid credential that is never reached**. Telltale sign: the gateway's echoed `CanonicalRequest` carries no `x-acs-security-token` header.

Fix: `unset ALIBABA_CLOUD_ACCESS_KEY_ID ALIBABA_CLOUD_ACCESS_KEY_SECRET ALIBABA_CLOUD_SECURITY_TOKEN` so the chain falls back to `config.json`, or set them to valid values. Then re-run `doctor`.

**On any signature or authentication failure, diagnose with `mcpx doctor` — never print or dump the credential env vars.** `doctor` reports set / not set, without exposing any value.

## Three invocation commands

Below, `mcpx` stands for `uv run --python 3.11 scripts/mcpx.py`; see [references/examples.md](references/examples.md) for how to define it as a shell function.

```bash
# List all tools
mcpx list

# Print a tool's input schema
mcpx schema CallCLI

# Call a tool
mcpx call CallCLI '{"command":"aliyun ecs describe-regions --region cn-hangzhou"}'

# When the argument contains double quotes, pass it via - from stdin to avoid escaping
echo '{"command":"aliyun ossutil ls oss://my-bucket --include \"*.log\""}' \
  | mcpx call CallCLI -

# Tools with no required parameter can omit the argument
mcpx call ListProducts
```

Use the short tool name (`CallCLI`); the script auto-prepends the `AlibabaCloud___` prefix. The full name is also accepted.

stdout carries only the tool's returned payload, so it pipes cleanly to `| jq`. All diagnostics go to stderr.

## Tool reference

The verbatim original `description` of all 15 tools and their parameters is in [references/tool-reference.md](references/tool-reference.md). **For the meaning and constraints of any parameter, that file is authoritative** — consult it before calling a tool.

## Verified examples

Copy-pasteable, run-verified examples for every tool — CallCLI, RunScript, RunIaC, the API discovery tools and the documentation tools, in both bash and PowerShell — are in [references/examples.md](references/examples.md).

## Key behaviors of this script

These are behaviors of `mcpx.py` itself; the MCP tool descriptions do not cover them:

1. **`processID` is valid across processes.** This script is one process per call. A `processID` from `RunScript` / `RunIaC` can be picked up by `GetTask` in any later new process — task state lives server-side.

2. **Save the `RunScript` return to disk before reading `processID`.** It is at the start of the returned JSON; viewing with `tail` truncates it, and losing the handle means re-running the whole task:

   ```bash
   mcpx call RunScript '{"script":"result = await call_cli(product=\"Ecs\", action=\"DescribeRegions\", params={})"}' > /tmp/start.json
   PID=$(python3 -c 'import json;print(json.load(open("/tmp/start.json"))["processID"])')
   echo "processID = $PID"
   ```

   PowerShell equivalent (reads the key with `ConvertFrom-Json`, no system `python3`):

   ```powershell
   mcpx call RunScript '{"script":"result = await call_cli(product=\"Ecs\", action=\"DescribeRegions\", params={})"}' > $env:TEMP\start.json
   $PID_ = ($(Get-Content $env:TEMP\start.json -Raw | ConvertFrom-Json)).processID
   "processID = $PID_"
   ```

3. **`--timeout` works before or after the subcommand.** `mcpx --timeout 600 list` equals `mcpx list --timeout 600`.

4. **The script warns when a filter returns empty.** See empirical finding 1 below. When you see the warning, actually re-check by calling bare; do not skip it as noise.

5. **stdout is only the tool payload; all diagnostics go to stderr.** So `| jq` is always clean; to troubleshoot, read stderr.

## Empirical findings not covered by the official descriptions

The verbatim descriptions are already complete — **how to pass parameters, OpenMeta being the single source of truth, checking the definition first for an unfamiliar API, all `nextAction` states including the three approval states, how to write `costManifest`: the original text covers all of it; just follow it.**

The following are not in the original text; all are empirically verified behaviors:

1. **A wrong jmespath path silently returns `null`, with no error.** It is indistinguishable from "genuinely no data". Example: `ListProductRegions` for SLS with `[].regionId` yields `null`, while the response top level is an object and the correct path is `data.endpoints[].regionId`. Treating that `null` as "this product has no region data" leads to borrowing another product's (e.g. ECS's) region list — the result: **7 regions never scanned, yet coverage reported as complete.**

   The script warns, but **the re-check must actually be done**:

   ```bash
   mcpx call ListProductRegions '{"product":"Sls"}'   # remove the filter to see the real structure
   ```

2. **XML responses do not support filter.** OSS's `ossutil api list-buckets` returns XML; forcing a filter reproduces the silent `null` above. Save to disk and parse locally; judge pagination with `grep -E 'IsTruncated|NextMarker'`:

   ```bash
   mcpx call CallCLI '{"command":"aliyun ossutil api list-buckets --region cn-hangzhou --max-keys 1000"}' > /tmp/oss.xml
   uv run --python 3.11 python -c "
   import xml.etree.ElementTree as ET
   for b in ET.parse('/tmp/oss.xml').getroot().iter('Bucket'):
       print(b.findtext('Region'), b.findtext('Name'))
   "
   ```

3. **A jmespath key with non-ASCII or other non-identifier characters must be double-quoted.** `{"总数": TotalCount}` works, `{总数: TotalCount}` errors.

4. **The `CallCLI` command form varies by product.** ECS/VPC/RDS are OpenAPI-style; SLS and OSS are plugin-style kebab-case subcommands. Using the wrong form yields a misleading error that points at the version number and "contact support", even though the version is correct — the real cause is the command form. **Get the authoritative command with `GenerateCLICommand` and use it verbatim**; in the response prefer `unifiedCli`, or `cli` if it is empty:

   ```bash
   mcpx call GenerateCLICommand '{"product":"Oss","apiName":"ListBuckets","apiVersion":"2019-05-17","regionId":"cn-hangzhou"}'
   # → aliyun ossutil api list-buckets --region cn-hangzhou    (ossutil, not the deprecated oss command)
   ```

5. **Determine resource scope empirically; "no RegionId" does not imply "global".** SLS and OSS both lack a RegionId parameter, yet their scopes are opposite:

   | Product / API | Scope | Observed |
   |---|---|---|
   | SLS `ListProject` | **region-level** | Hangzhou returns 55, Beijing returns 4, no overlap |
   | OSS `ListBuckets` | **account-global** | one call returns 17 buckets across 4 regions |

   Test: call the same API in two regions. Results that vary by region and do not overlap ⇒ region-level; one call returning cross-region data ⇒ global.

6. **Iterate regions with that product's own `ListProductRegions`; do not borrow ECS's.** SLS has 33 regions, ECS has 32; they do not coincide.

7. **The `RunScript` sandbox forbids dunder attribute access.** `type(exc).__name__` is rejected (`attribute not allowed: __name__`); use `str(exc)` for the error message. Wrapping `call_cli` itself in `try/except` works.

8. **`params` must be passed explicitly as `{}` even when empty.** Omitting it is rejected with `BLK-4001` (`call_cli is missing required kwarg(s): ['params']`).

9. **Pure Python logic (no `call_cli` call) is rejected by the safety check**, returning `BLK-4002`. Merely defining a `call_cli` call in the function body does not count as "reachable".

10. **Read a bulk job's errors one by one, distinguishing two classes:**

    | Error | Meaning | Data gap? |
    |---|---|---|
    | `endpoint not configured for product 'x' in region 'y'` | no service endpoint in that region | **No** — there cannot be resources |
    | `Forbidden` / `AccessDenied` | permission problem | **Yes** — there may be resources you cannot see; must declare |

    So **keep the full error text** rather than recording only `True/False`: `errs[rid] = str(exc)[:200]`

## Selection order

- Known exact command → `CallCLI`
- Unsure of the API → `SearchApis` → `ListApis` → `GetApiDefinition`
- Looking up Alibaba Cloud official docs → `SearchDocuments` / `GetDocument` / `GetDocumentTree` / `GrepDocuments` (not `web_search` / `web_fetch`)
- Batch or multi-step → `RunScript` + `GetTask`
- Infrastructure orchestration → `RunIaC`

## Full workflow for an unfamiliar product

The findings above are scattered rules. **To query a product you have never touched** (not ECS/VPC/RDS), follow the six steps in [references/unfamiliar-product-checklist.md](references/unfamiliar-product-checklist.md): read the parameter table → get the authoritative command → determine resource scope → use that product's own region list → run a probe → scale to the full set. That checklist also includes the "before drawing a conclusion" checks.

## Troubleshooting

### Exit codes

| Code | Meaning | Action |
|---|---|---|
| 0 | Success | — |
| 1 | Tool returned `isError` | Read the payload in stderr; usually a parameter or permission problem |
| 2 | Usage error | Misspelled tool name, invalid JSON. stderr lists the available tool names |
| 3 | Transport-layer or precondition failure | See below |

### Cases of exit code 3

The stderr signatures below are quoted verbatim from what `mcpx.py` actually prints.

| stderr signature | Cause | Action |
|---|---|---|
| `找不到可执行文件 'uvx'` | uv not installed | Setup step 2 |
| `未检测到可用的阿里云凭证` | No credentials and not on ECS | Setup step 4 (login) |
| `阿里云凭证无效` | Credentials expired or wrong | Re-run `login` |
| **`凭证可用但被拒绝`** | **Missing RAM permission**, see below | Request `AliyunOpenAPIMCPServerStaticCredentialAccess` |
| `MCP 服务未响应即退出` | Unknown failure | Read the server's original text; also suspect RAM permission first, see below |
| `等待 MCP 服务响应超时` | First-run dependency download too slow | Increase `--timeout`; it works before or after the subcommand: `mcpx call CallCLI '{...}' --timeout 600` or `mcpx --timeout 600 call CallCLI '{...}'` |

### A sub-account must pass two independent gates

For a sub-account to use this skill, **two unrelated things** must both be in place. Confusing them sends you troubleshooting in the wrong direction:

| # | Gate | Decides | Who configures | Failure symptom |
|---|---|---|---|---|
| 1 | The `official-cli` third-party app is installed in the primary account, and the sub-account is added to its **visitor list** | Whether OAuth **login** works | Primary account / RAM admin only | The authorization **page** rejects directly, no terminal error, `login` waits until timeout (exit 3) |
| 2 | The sub-account has the `AliyunOpenAPIMCPServerStaticCredentialAccess` RAM permission | Whether it can **connect to MCP** after login | Primary account / RAM admin | `login` succeeds, but the handshake reports `code: 403, You are not authorized to perform this action` |

To tell which gate is stuck:

- **`login` reports `授权未在时限内完成`** → go back and look at the browser page. Gate 1's error is only on the page; the terminal gets nothing.
- **`login` succeeds but the `doctor` handshake fails** → gate 2, see below.

#### Gate 1 page text (verbatim)

Accessing the authorization link with a sub-account that is not assigned to the app, the browser page shows:

```
账号未允许当前身份访问该应用。
将以下信息发送给 RAM 访问控制管理员，请管理员将当前访问身份添加至应用的访问者列表中。
访问身份
<子账号名>@<主账号UID>.onaliyun.com
应用管理地址
https://ram.console.aliyun.com/applications/4038181954557748008?appType=ThirdPartyApp
管理员配置后请刷新页面或重新访问应用。
```

At this point the terminal shows **no error at all** — you cannot click authorize, the callback never comes, and `mcpx login` can only wait until timeout. Do not assume it is a slow network and raise `--timeout`; that does not fix it.

**Ask the user which situation applies.** Both fixes need a primary-account / RAM administrator; the sub-account cannot do either itself.

**Situation A — the primary account has never installed the official-cli app.** The administrator installs it first:

1. Open https://ram.console.aliyun.com/applications?activeTab=ThirdParty
2. Click "安装官方应用" (install official application) → "官方 CLI" (official CLI)
3. Select `alibabacloud-cli@app.1263926834388048.onaliyun.com`

**Situation B — the app is installed but the current sub-account is not in its visitor list.** The administrator assigns it:

1. Open https://ram.console.aliyun.com/applications/4038181954557748008?appType=ThirdPartyApp&activeTab=Assignments
2. Click "添加用户或角色" (add user or role)
3. Select the current sub-account user

After the administrator finishes, refresh the authorization page or re-run `mcpx login`. The appId `4038181954557748008` on the page is the same as the `client_id` in the authorization link.

### Logged in but cannot connect: check RAM permission first

**A successful `aliyun` CLI login does not mean you have permission to use this MCP service; the two are separate.** This is the most typical cause of "login clearly succeeded but cannot connect".

The MCP service requires the account to have this RAM permission point to issue credentials for the caller:

```
AliyunOpenAPIMCPServerStaticCredentialAccess
```

Symptom: `login` succeeds, `aliyun sts get-caller-identity` returns the identity, but `doctor` fails at the handshake step.

**Server's original text:**

```
凭证可用但被拒绝, MCP 服务在握手前已退出。
服务端原始信息:
Error: Failed to discover MCP server URL: code: 403, You are not authorized to perform this action. request id: ...
```

Note the difference from "invalid credentials" — the two look similar but differ in status code and wording:

| Error | Meaning |
|---|---|
| `code: 403, You are not authorized to perform this action` | Credentials valid, **but missing the RAM permission** |
| `code: 404, Specified access key is not found` | Credentials themselves invalid; re-run `login` |

When you see the 403 one, do not re-login — **login is not the problem**; go add the permission.

The wording may change in future, so the script also attaches this hint on unknown failures it cannot classify. The criterion is "credentials are fine but the handshake fails"; do not fixate on the exact text.

Action: request or add this RAM permission point **for the identity currently logged in**, then re-run `doctor`. First confirm which identity you are using:

```bash
mcpx call CallCLI '{"command":"aliyun sts get-caller-identity"}'
```

A sub-account and the primary account are different identities — adding the permission to the primary account does not grant the sub-account. Do not repeatedly re-run `login` in this case; login is not the problem. The permission is declared in [references/ram-policies.md](references/ram-policies.md).

### When a description disagrees with the server

The tool reference is authoritative; copy it for normal calls. Only when you suspect the server version changed, or need a deeply nested structure not expanded there, use these two commands to get the server's truth:

```bash
uv run --python 3.11 scripts/mcpx.py list
uv run --python 3.11 scripts/mcpx.py schema GetPresignedUrl
```

For example, the array-element structure of `GetPresignedUrl.requests` or the full shape of `RunScript.costManifest` do not fit in a table; use `schema`.

### Running tests

```bash
uv run --python 3.11 --with pytest -m pytest tests/ -q
```

No network or Alibaba Cloud account needed; runs fully offline.
