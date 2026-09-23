---
name: alibabacloud-cfw-internet-firewall-protect
description: >
  Manage Cloud Firewall (CFW) Internet Firewall public IP protection switches on Alibaba Cloud.
  Use this Skill when enabling or disabling firewall protection for public IPs,
  querying asset protection status, batch protecting ECS/EIP/NAT/SLB resources,
  toggling all public IPs at once, or configuring auto-protection for new assets.
  Supports multi-account management via member-uid.
  管理阿里云云防火墙（CFW）互联网防火墙的公网IP防护开关。
  当用户需要开启云防火墙、管理互联网防火墙开关、查看公网IP是否受保护、
  批量开启ECS/EIP/NAT/SLB等资源的防火墙、配置新资产自动防护时使用此Skill。
  支持多账号管理（member-uid）。
license: Apache-2.0
compatibility: >
  Requires aliyun CLI >= 3.3.3 with CFW plugin installed.
  Requires python3 >= 3.6 for JSON merging and CSV export.
  Scripts compatible with bash >= 3.2 (macOS default).
  Compatible engines: qwen-code, qoder, openclaw.
metadata:
  domain: aiops
  owner: cfw-team
allowed-tools: Bash Read
---

## Operation Routing

Identify the user's intent, then route to the matching execution path:

| User Intent | Execution Path |
|---|---|
| Query asset protection status, list assets, check which IPs are protected/unprotected | `fw-switch.sh query` with filters |
| Export asset protection status to CSV/Excel for audit or reporting | `fw-switch.sh query --all-pages --export-csv <file>` |
| List newly discovered assets (last hour / day / 7 days) | `fw-switch.sh query --new-resource-tag "discovered in 7 days"` |
| Enable/disable protection for **specific IPs** | `fw-switch.sh enable/disable --ips "ip1,ip2,..."` |
| Enable/disable protection for a **region** | `fw-switch.sh enable/disable --regions "cn-hangzhou,..."` |
| Enable/disable protection for a **resource type** (e.g. all ECS public IPs) | `fw-switch.sh enable/disable --resource-types "EcsPublicIP,..."` |
| Enable/disable protection for all **IPv4** or **IPv6** assets | `fw-switch.sh enable/disable --ip-version 4` or `6` |
| **Combined filter** (e.g. Beijing region + ECS public IP + IPv4) | `fw-switch.sh enable/disable --regions cn-beijing --resource-types EcsPublicIP --ip-version 4` |
| Enable/disable protection for **ALL** public IPs at once | `fw-switch.sh enable-all/disable-all --yes` |
| Enable protection for assets matching a **condition** (name, label, etc.) | Multi-step: query → filter → enable by IP list (see below) |
| Query auto-protection settings for new assets | `auto-protect.sh query` |
| Modify auto-protection settings | `auto-protect.sh modify --enable/--disable <types> --yes` |

Parameters can be freely combined. The `--ips`, `--regions`, `--resource-types`, and `--ip-version` options work together — provide at least one.

## Conditional Multi-Step Workflow

When the user's filter criteria cannot be directly passed to the API (e.g. "enable protection for all instances whose name contains Dify"), orchestrate a multi-step workflow:

1. **Query**: Run `fw-switch.sh query` with available filters (status, region, resource type). Fetch the complete set — the filter is applied locally in step 2, so a truncated page would silently drop matches. See the pagination guidance in "Query Assets" (`--page-size 1000` first, `--all-pages` only beyond that).
2. **Filter**: From the returned `Assets` array, filter by the user's condition (instance name match, specific attributes, etc.). The key fields in each asset: `Name` (instance name), `InternetAddress` (public IP), `IntranetAddress` (private IP), `ProtectStatus`, `ResourceType`, `RegionID`, `BindInstanceId`, `BindInstanceName`.

   For a name condition, match against **both** `Name` and `BindInstanceName`, case-insensitively, as a substring: `Name` can be empty (e.g. some NAT gateway assets return `Name=""` while `BindInstanceName` holds the real name), so relying on either field alone misses assets.
3. **Impact Preview (Phase 1)**: Present the matched assets summary to the user for confirmation (follow the summary format in "Enable / Disable Protection Workflow").
4. **Execute (Phase 2)**: Collect the `InternetAddress` values from matched assets into a comma-separated list, then call `fw-switch.sh enable/disable --ips "ip1,ip2,..."`.
5. **Verify (Phase 3)**: Poll status to confirm the operation completed (follow the polling strategy in "Enable / Disable Protection Workflow").

**Edge Case Handling for Step 2 (Filter Results):**

| Filter Result | Phase 2 Action |
|---|---|
| Matched assets exist, some/all have ProtectStatus=closed | `enable --ips "all_matched_ips"` (include both open and closed — API is idempotent) |
| Matched assets exist, ALL already ProtectStatus=open | `enable --ips "all_matched_ips"` (still call — idempotent rule) |
| **Zero assets match the filter condition** | Fall back to a broader dimension **only** when the user's own request supplied one (a region, resource type, or IP version they named) — e.g. `enable --regions <region> --resource-types <type>`. If they supplied none, report the zero-match outcome and state that nothing was changed: that **is** a completed workflow, not a skipped Phase 2. **Never escalate to `enable-all` / `disable-all` to compensate for a zero match** — the user's condition is a scope limit, and widening it would touch assets they explicitly excluded. |

This pattern applies to any condition-based operation — name matching, tag filtering, status-based bulk operations, etc.

## Check CLI Environment

Generate the session-id described in "Observability" below **before** running anything here — `validate-cli.sh --check-permission` already calls a real CFW API, so it needs the session-id too. Passing it as `SKILL_SESSION_ID={session-id} bash scripts/validate-cli.sh --check-permission` keeps every call from the very first one attributable to this session.

**Pre-check: Aliyun CLI >= 3.3.3 is required.** Verify with `aliyun version`. 3.3.3 is the baseline for the plugin ecosystem — older versions cannot load the Cloudfw plugin, so every command in this Skill would fail. Install or upgrade first if the version is below it:

```bash
# First install, or major upgrade
/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"

# Routine self-update (supported from CLI 3.3.5)
aliyun upgrade --yes

# Alternative on macOS
brew install aliyun-cli      # or: brew upgrade aliyun-cli
```

`aliyun upgrade` writes into the CLI's install directory, so it needs elevated privileges when the binary lives in a system path such as `/usr/local/bin`. See `references/cli-installation-guide.md` for the full installation and troubleshooting instructions.

Once the CLI version is acceptable, validate the rest of the environment:
```bash
bash scripts/validate-cli.sh --check-permission
```

Check results and remediate:
- `cli_installed` = false → install the CLI with one of the commands above, or run `--install-guide` for the full walkthrough
- `cli_version_ok` = false → CLI version below 3.3.3, upgrade with `aliyun upgrade --yes`
- `auto_plugin_install` = `unknown` (the normal value) → the CLI exposes no way to read this setting back, so the script reports it as unknown rather than guessing. It is a local convenience switch, not a prerequisite: run `aliyun configure set --auto-plugin-install true` once if you want missing plugins auto-installed, and do not treat `unknown` as a failure to remediate on every run.
- `credential_valid` = false → no profile configured; configure one **outside this session** with `aliyun configure`, then re-run. The CLI resolves credentials from its default credential chain — this Skill never reads or handles credentials itself.
- `permission_check` = false → credentials are invalid/expired or the identity lacks `yundun-cloudfirewall:DescribeAssetList`; check the credential status in the RAM console and refer to `references/ram-policies.md`

Note: `credential_valid` only reflects whether a profile exists in `aliyun configure list`. Real credential validity is verified by `permission_check`, which calls the actual CFW business API — invalid or expired credentials will fail there.

Show full installation guide:
```bash
bash scripts/validate-cli.sh --install-guide
```

After environment checks pass, ensure plugins are up-to-date:
```bash
aliyun plugin update
```

> **API Version Note:** Cloudfw uses CLI plugin mode (`aliyun-cli-cloudfw`). The API version is managed internally by the plugin (actual version: `2017-12-07`). Call CFW commands using the default invocation — do **NOT** pass `--version`. The plugin rejects any external version override and will error with `unchecked version`. The `call_cfw_api` function in `common.sh` is designed accordingly and does not include `--version`.

## Observability

Every cloud API call this Skill makes should be attributable to one Agent session, so cloud-side logs can correlate all actions back to a single execution. Tag each call with a session-scoped User-Agent.

**UA template:**

```
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-internet-firewall-protect/{session-id} skill-version/{skill-version}"
```

- The Skill `name` segment is fixed: `alibabacloud-cfw-internet-firewall-protect`.
- `{session-id}` is a placeholder — replace it with the current session identifier before running the command; never send the literal text `{session-id}`.
- `{skill-version}` is a placeholder for the `version` string in `references/manifest.json`, which is the only accepted source for it. Read it before the first cloud call: when the file is missing, the JSON is invalid, or `version` is empty or not a string, stop and report the error rather than guessing a value. An invented or borrowed version mislabels cloud-side telemetry, and because every call in a session shares one version, one wrong read corrupts correlation for the whole session.

**session-id generation rules:**
- Generate it **once per session**, at the first CLI invocation; do not regenerate on later calls.
- Format: a **32-character lowercase hexadecimal** string (128 bits), e.g. `3f2a9c1b4d5e6f708192a3b4c5d6e7f8`. A portable way to produce one is `python3 -c "import uuid; print(uuid.uuid4().hex)"`.
- Reuse the **same session-id in every call** for the whole session, so all actions share one correlatable identifier.

**How the flag reaches the API:**

The scripts read the session-id from `SKILL_SESSION_ID`, resolve `{skill-version}` from `references/manifest.json`, and append `--user-agent` to every cloud API call themselves, so pass the session-id in when invoking them:

```bash
SKILL_SESSION_ID={session-id} bash scripts/fw-switch.sh query --region cn-hangzhou
SKILL_SESSION_ID={session-id} bash scripts/auto-protect.sh modify --enable "EIP" --yes
```

`SKILL_SESSION_ID` is mandatory: a call that carries no session attribution cannot be traced back to this session, so the scripts refuse it and exit 1 with `SKILL_SESSION_ID is not set` before any API is contacted. The same applies to an unreadable manifest version. Set the session-id at the first invocation of this Skill rather than retrying without it.

When you call the `aliyun` CLI directly instead of through these scripts, add the flag yourself on each cloud API command. Local CLI commands (`configure`, `plugin`, `version`, `upgrade`, `help`) do not accept `--user-agent` — do not add it to them.

## RAM Policy and Permission Handling

The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`. Read `references/ram-policies.md` for the full permission list.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission
> errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

Before executing any command or API call, make sure the user-customizable parameters below are the ones the user actually intends. Do not silently substitute a default or invent a value the user never mentioned:

`fw-switch.sh enable` / `disable`:

| Parameter | Required | Description | Default when omitted |
|---|---|---|---|
| `--ips` | At least one of these four | Explicit public IP list | Not IP-restricted — **every** IP matching the other filters |
| `--regions` | At least one of these four | Region filter, e.g. `cn-hangzhou` | **All regions** — widens scope |
| `--resource-types` | At least one of these four | Asset type filter, e.g. `EcsPublicIP` | **All resource types** — widens scope |
| `--ip-version` | At least one of these four | `4` or `6` | Both IPv4 and IPv6 |
| `--member-uid` | Optional | Member account UID | The management account itself |

`enable` / `disable` refuse a call with **none** of the four scope dimensions — the script checks this locally and exits 1 with `At least one of --ips, --regions, --resource-types, --ip-version is required`, calling no API. An empty filter is therefore not the same as "everything".

`fw-switch.sh enable-all` / `disable-all`:

| Parameter | Required | Description | Default when omitted |
|---|---|---|---|
| `--instance-id` | Optional | CFW instance ID | The account's default instance |

These two take **no scope parameters at all**: `--ips`, `--regions`, `--resource-types`, `--ip-version` and `--member-uid` are all rejected with `Unknown option` (exit 1). Their scope is the whole account by design — that is the only thing to confirm with the user. If the user wants a narrower scope, use `enable` / `disable` with filters instead.

`auto-protect.sh modify`:

| Parameter | Required | Description | Default when omitted |
|---|---|---|---|
| `--enable` / `--disable` | One of these, or `--config` | Comma-separated resource types to turn on / off | no change to those types |
| `--config` | Mutually exclusive with the above | Full replacement JSON for the auto-protection map | — |

`--config` replaces the **whole** map in one submission: a resource type absent from the JSON is written as not auto-protected. Passing `--config '{"EIP":true,"NatEIP":true}'` for a user who asked to auto-protect EIP and NAT therefore silently switches the other ~26 types off. When the user names only some types, do **not** hand their partial list straight to `--config` — either run `auto-protect.sh query` first and merge the request into the map you got back before submitting the full JSON, or use incremental mode (`--enable` / `--disable`), which performs that read-merge-write itself. Either way, say in the report which types the submitted map leaves at `false`.

Informal type names in the user's JSON (`eip`, `ecs`, `slb`) are not API values. Resolve every key through `references/resource-types.md` before it reaches the command: the map keys are case-sensitive, and an unrecognised key is not something the API reports back as an error — it simply fails to protect anything.

Auto-protection is configured at the account's default scope and takes **no region parameter** — there is no per-region variant to confirm with the user. If the user asks to limit auto-protection to one region, tell them the API does not support a readable region-scoped config, and offer `fw-switch.sh enable --regions <region>` for the existing assets in that region instead.

`fw-switch.sh query` (read-only, so no confirmation gate applies):

| Parameter | Required | Description | Default when omitted |
|---|---|---|---|
| `--region` / `--status` / `--resource-type` / `--ip-version` / `--member-uid` | Optional | Single-value filters | No filter on that dimension |
| `--search` | Optional | IP or instance ID substring | none |
| `--new-resource-tag` | Optional | Asset discovery window: `discovered in 1 hour` / `1 day` / `7 days` | none |
| `--page` / `--page-size` | Optional | Paging only, never affects what gets changed | page 1, size 10 |

Confirm only what is genuinely undetermined. A parameter the user already stated explicitly in their request is confirmed by definition — restate it in the Phase 1 impact preview instead of asking about it a second time.

The parameters that do need a decision are the ones the user left out **and** that widen scope — on `enable` / `disable`, an omitted region or resource type means "everything matching the remaining filters". Rather than pausing to ask, surface that interpretation concretely in the Phase 1 preview (asset count plus region distribution) so the user sees the true blast radius, and let the confirmation gate described in "Confirmation and the `--yes` Flag" handle the decision. `enable-all` / `disable-all` have no such parameter to resolve: their scope is always the whole account, so the preview itself is the disclosure.

> Parameter confirmation never overrides the non-interactive execution rule. In Agent mode the Phase 1 preview is informational and `--yes` is the confirmation — do not add an extra round-trip with the user, and never stop before Phase 2 and Phase 3.

## Query Assets

```bash
bash scripts/fw-switch.sh query [options]
```

Available filters: `--region`, `--status` (open/closed/opening/closing), `--resource-type`, `--search` (IP or instance ID), `--ip-version` (4/6), `--member-uid`, `--new-resource-tag`. Each filter accepts a single value.

`--new-resource-tag` filters by **asset discovery time**, not by a user-defined tag. It accepts only three values: `discovered in 1 hour`, `discovered in 1 day`, `discovered in 7 days`. Use it when the user asks about newly discovered or recently added assets.

For multi-region or multi-resource-type queries, the DescribeAssetList API only supports single-value filters. Make separate calls per region or per resource type in parallel, then merge the results. Example: to query both cn-hangzhou and cn-beijing EcsPublicIP assets, call `fw-switch.sh query --region cn-hangzhou --resource-type EcsPublicIP` and `fw-switch.sh query --region cn-beijing --resource-type EcsPublicIP` separately.

Pagination: `--page` (default 1), `--page-size` (default 10). Check `TotalCount` in the response to determine if more pages exist. The API accepts a large `--page-size` (1000 is known to work), so an account with up to roughly a thousand public IPs can be fetched completely in a **single** call — try `--page-size 1000` first, since it avoids pagination entirely. Only reach for `--all-pages` when `TotalCount` exceeds what one page can hold; `--all-pages` walks every page and returns a single merged result, and it needs `python3` to do the merging.

The response returns the raw API JSON with an `Assets` array. Each asset contains: `InternetAddress`, `IntranetAddress`, `ProtectStatus`, `ResourceType`, `RegionID`, `Name`, `BindInstanceId`, `BindInstanceName`, `ResourceInstanceId`, `IpVersion`, `MemberUid`.

Present results to the user in a readable format. For `ProtectStatus`: `open` = protected, `closed` = unprotected, `opening` = enabling, `closing` = disabling.

### Export Query Results

For security audit or reporting scenarios where the user wants a spreadsheet of asset protection status:

```bash
bash scripts/fw-switch.sh query --status open --all-pages --export-csv ./protected-assets.csv
```

`--export-csv <file>` writes one row per asset with all the fields listed above. The file is UTF-8 with a BOM, so it opens directly in Excel with Chinese instance names rendered correctly — no separate `.xlsx` conversion needed. Combine it with `--all-pages`, otherwise only the current page is exported.

When `--export-csv` is used, stdout carries an export summary (`exported_file`, `row_count`) instead of the full asset JSON. Report the file path and row count to the user; read the CSV back only if you need the contents for further analysis.

The target directory must already exist — the script does not create directories, and exits 1 if the path is unwritable.

## Enable / Disable Protection Workflow

All enable/disable/enable-all/disable-all operations follow a three-phase workflow: **Phase 1 Impact Preview → Phase 2 Execute → Phase 3 Result Verification**. Confirmation is a gate inside Phase 1, and how that gate is satisfied depends on the execution mode — see "Confirmation and the `--yes` Flag" below. Skipping any phase may lead to unintended changes or unverified outcomes.

This workflow covers the `fw-switch.sh` protection switches only. `auto-protect.sh modify` has its own three-step workflow without polling — see "Auto-Protection Settings → Modify Settings".

> **⚠️ MANDATORY: Non-Interactive Execution Rule**
> When running as an Agent (non-interactive mode), `--yes` is implicit user confirmation. You **MUST** complete ALL three phases **unconditionally**:
> - Phase 1 shows **0 affected assets** → **still execute Phase 2 and Phase 3**. Do NOT stop.
> - Phase 1 shows all assets already in desired state → **still execute Phase 2 and Phase 3**. Do NOT stop.
> - **NEVER** terminate the workflow after Phase 1 alone. NEVER output "no action needed" without completing Phase 2+3.
> - The sequence Phase 1 → Phase 2 → Phase 3 is **unconditionally mandatory** in every execution path, regardless of Phase 1 results.
>
> **Scope boundary:** this rule forbids skipping Phase 2 **for the scope the user asked for** — it never authorises widening that scope. When the target set comes from a user-supplied condition (instance name, tag, etc.) and nothing matched it, there is no in-scope target to act on; reporting the zero match is the correct terminal state. See the zero-match row in "Conditional Multi-Step Workflow".

### Confirmation and the `--yes` Flag

`--yes` is a **script-level safety interlock**, not a user-facing prompt. Two separate things are involved — do not conflate them:

- **The confirmation gate** in Phase 1 is satisfied by the user in interactive mode, and by the Agent itself in non-interactive mode.
- **The `--yes` flag** is a CLI argument that the caller must pass on destructive commands. The script never prompts and never reads stdin.

Exactly which commands take `--yes` — the flag is accepted **only** by the two rows marked Required:

| Command | `--yes` | Why |
|---|---|---|
| `fw-switch.sh query`, `auto-protect.sh query` | **Not accepted** | Read-only |
| `fw-switch.sh enable` / `disable` | **Not accepted** | Scoped to explicit IP/region/type/version filters |
| `fw-switch.sh enable-all` / `disable-all` | **Required** | Affects every public IP in the account |
| `auto-protect.sh modify` | **Required** | Changes account-wide auto-protection policy |

"Not accepted" is stricter than "optional": passing `--yes` to those commands aborts with `[ERROR] Unknown option: --yes` and exit code 1, calling no API. So pass `--yes` on exactly the two Required commands — never add it defensively elsewhere.

When `--yes` is required but omitted, the script outputs `{"success": false, "error_code": "NotConfirmed", ...}` and exits with code **1 without performing any write operation** — nothing is changed. (`auto-protect.sh modify` reads the current config first, so it may issue one read-only API call before stopping.) This is intended safety behaviour — but it also means a non-interactive run that forgets `--yes` accomplishes nothing at all. As an Agent, pass `--yes` on the Required commands as part of normal execution; do not treat it as something to withhold pending a further round-trip with the user.

One caveat when previewing: `--dry-run` is evaluated **before** the interlock, so `enable-all --dry-run` prints the command preview and exits 0 even without `--yes`. A successful dry-run therefore proves nothing about `--yes` — still pass it on the real invocation.

A second caveat, specific to `auto-protect.sh modify`: its incremental form (`--enable` / `--disable`) cannot show a merged config without first reading the current one, so `--dry-run` there **does** call `DescribeResourceTypeAutoEnable` for real. It consequently needs `SKILL_SESSION_ID` like any other cloud call, and without it exits 1 with `SKILL_SESSION_ID is not set` before printing any preview. Only `--config --dry-run` is purely local, since a full replacement needs no read. Passing the session-id on every invocation — dry-run included — makes the distinction irrelevant.

### Phase 1: Impact Preview

Before executing, query the assets that will be affected and present a human-friendly summary:

- **enable** operation: query `--status closed` + same filter dimensions to show assets that will gain protection
- **disable** operation: query `--status open` + same filter dimensions to show assets that will lose protection
- **enable-all**: query `--status closed` to show all currently unprotected assets
- **disable-all**: query `--status open` to show all currently protected assets

Use the same single-fetch approach as "Query Assets" for the preview query: `--page-size 1000` retrieves the whole result set in one call, which is what an accurate count and region distribution need. Only paginate (or use `--all-pages`) when `TotalCount` exceeds what that one page returned.

**Summarize** the result to the user:

- If total ≤ 5 assets: list all (IP, instance name, region, resource type)
- If total > 5 assets: list 3 representative examples, then summarize the rest with region distribution

Example format:
```
This operation will enable firewall protection for the following 45 unprotected public IPs:

1. 47.96.xx.xx (ECS instance web-server-01, cn-hangzhou, EcsPublicIP)
2. 120.55.xx.xx (NAT gateway nat-prod, cn-hangzhou, NatEIP)
3. 39.108.xx.xx (ECS instance api-gateway, cn-beijing, EcsPublicIP)
...and 42 more public IPs across cn-hangzhou(25), cn-beijing(12), cn-shanghai(5).

Confirm execution?
```

For **disable** and **disable-all**, additionally warn: disabling protection means traffic no longer passes through Cloud Firewall, access control policies and intrusion detection will stop working.

Three forms carry a blast radius the preview is the only chance to expose — `enable-all`, `disable-all`, and any `disable` — so for them the Phase 1 disclosure is mandatory in **content**, not just in form. Put all of it in the message that precedes Phase 2:

- the scope in words: "every public IP under this account" for `enable-all` / `disable-all`, or the exact filter set for `disable`;
- the affected asset count from the preview query, plus region distribution once it exceeds 5;
- for both `disable` forms, the protection-loss consequence spelled out above.

That disclosure is the Agent-mode stand-in for an interactive confirmation prompt — it is what leaves the operation reviewable in the transcript. Deliver it and keep going; do not convert it into a question and wait.

Then satisfy the confirmation gate according to the execution mode:

- **Interactive mode** (a human is answering): wait for explicit user confirmation before proceeding to Phase 2.
- **Non-interactive / Agent mode**: the preview above is informational only. Do **NOT** wait for input — proceed directly to Phase 2, passing `--yes` on the commands that require it.

A request phrased as "先看看有哪些，确认没问题再开启" does not change this in Agent mode. What the user is asking for is to *see* the affected assets before anything changes, and the Phase 1 preview is exactly that — deliver it, state what will run next, then run it. Reading it as "stop and wait for my reply" leaves the task unfinished, which is the one outcome the user did not ask for.

Two situations are the exception, and in both of them you **do** stop and ask:

- **The user named an interaction point.** "如果有多个候选，请先列出并让我确认后再继续", "先问我再改", "列出来我看过再执行" — this is not a generic confirmation ritual, it is an instruction about how to run the task. Present the candidates, ask, and wait for the answer.
- **A value central to the request is missing and cannot be safely inferred.** "帮我关闭几个公网IP的防护" names no IP, region, resource type, or IP version, so there is no scope to preview and nothing safe to assume. Ask which targets are meant rather than picking a scope yourself; guessing here risks disabling protection on assets the user never mentioned.

The difference from the paragraph above is who introduced the stop: a preview the user asked to see is not a question, while an explicit "ask me first" or a missing scope is.

### Phase 2: Execute

Once the confirmation gate is satisfied, run the actual enable/disable command. If using a condition-based IP list from the preview query, pass the collected IPs via `--ips`.

> **⚠️ MANDATORY: Idempotent Execution Rule**
> Even if Phase 1 shows all target assets are already in the desired state (e.g., all `open` when enabling, or 0 unprotected assets found), you **MUST still execute** the enable/disable command. The API is idempotent — calling it on already-protected assets is safe and returns success. Do NOT skip Phase 2 based on current status or zero-count results.
>
> Examples of WRONG behavior:
> - "All assets are already protected, no action needed" → WRONG, must still call the API
> - "No unprotected assets found, skipping execution" → WRONG, must still call the API

### Phase 3: Result Verification

After execution, poll the asset status to verify the operation took effect:

1. **Initial wait**: sleep 5 seconds
2. **Query**: Run `fw-switch.sh query` with the same **scope** filters as Phase 1 (region, resource type, IP list, IP version, member UID) but **drop the `--status` filter**. Then read each asset's `ProtectStatus` and count how many reached the target state versus how many are still `opening`/`closing`.

   Keeping `--status closed` here inverts the result: once the enable succeeds nothing is `closed` any more, so the query returns an empty set — which reads as "nothing transitioned" when in fact everything did. An empty result under a retained status filter is the *success* signal, not a failure. Dropping the filter removes that ambiguity entirely.
3. **Adaptive polling**: If not all assets have transitioned:
   - Poll every 5 seconds
   - Estimate: ~5 seconds per 20 assets
   - Maximum total polling: 30 seconds
4. **Report results** using the same summary style (examples + count):
   - All transitioned: "✓ Done. Firewall protection enabled for all 45 public IPs."
   - Partial within 30s: "38/45 assets completed. 7 still in progress (status: opening). Check the Cloud Firewall console to confirm final status."
   - Timeout: "Waited 30 seconds. 12 assets have not completed the status transition. Large-scale changes may take longer — check the Cloud Firewall console to confirm."

Expected status transitions:
- enable → `closed` → `opening` → `open`
- disable → `open` → `closing` → `closed`

Treat `opening`/`closing` as "in progress" — the operation was accepted but not yet complete.

## Enable / Disable Protection

### By IP, Region, Resource Type, or IP Version

```bash
bash scripts/fw-switch.sh enable [options]
bash scripts/fw-switch.sh disable [options]
```

Options: `--ips`, `--regions`, `--resource-types`, `--ip-version`, `--member-uid`, `--dry-run`.

At least one filter dimension is required. The dimensions you do pass are combined with **AND**, and any dimension you omit is left **unrestricted** — so `--regions cn-hangzhou` on its own covers every resource type and both IP versions in that region, while `--regions cn-hangzhou --resource-types EcsPublicIP` narrows to just ECS public IPs there. They can be combined freely:
```bash
# Single dimension
bash scripts/fw-switch.sh enable --ips "1.2.3.4,5.6.7.8"
bash scripts/fw-switch.sh enable --ip-version 6

# Combined dimensions
bash scripts/fw-switch.sh enable --regions "cn-beijing" --resource-types "EcsPublicIP" --ip-version 4
```

Use `--dry-run` to preview the CLI command before execution. This is recommended when the user provides many IPs or combined filters, so they can verify the parameters.

`references/resource-types.md` maps product names users actually say (for example, `负载均衡`) to exact API values; `references/region-ids.md` maps regional labels (for example, `华北2`) to region IDs. Consult both before passing filters, because a plausible-looking but non-existent value is rejected rather than corrected.

### All Public IPs

```bash
bash scripts/fw-switch.sh enable-all --yes [--instance-id <id>]
bash scripts/fw-switch.sh disable-all --yes [--instance-id <id>]
```

These operations affect every public IP under the account. `--yes` is mandatory: without it the script exits with `NotConfirmed` (exit code 1) and calls no API. In non-interactive (Agent) mode, `--yes` is treated as implicit user confirmation — do NOT wait for explicit user input before passing it.

Impact preview is especially important for these operations — always run Phase 1 to show the user exactly how many assets will be affected before proceeding.

> **⚠️ MANDATORY: Idempotent Execution Rule for enable-all / disable-all**
> Even if Phase 1 shows 0 unprotected assets (all already `open` for enable-all) or 0 protected assets (all already `closed` for disable-all), you **MUST still execute** the command. Do NOT output "All assets are already in the target state, no action needed" and stop — that skips Phase 2 and Phase 3.

## Auto-Protection Settings

### Query Current Settings

```bash
bash scripts/auto-protect.sh query
```

Returns a `ResourceTypeAutoEnable` map showing which resource types have auto-protection enabled (new assets of that type will be automatically protected).

### Modify Settings

Auto-protection changes follow their own three-step workflow. It is **not** the polling workflow used for protection switches: a config change has no `opening`/`closing` intermediate state, so there is nothing to poll for.

1. **Preview** — run `auto-protect.sh query` and show the user which of the requested types are currently `true` / `false`, i.e. what will actually change.
2. **Execute** — run `auto-protect.sh modify` with `--yes` (see the mandatory rule below). Always run it, whatever the preview showed.
3. **Verify** — run `auto-protect.sh query` **once** and report the resulting state of the requested types. No `sleep`, no polling loop. If a type does not yet read as requested, report the observed value rather than retrying blindly — repeated writes will not change the outcome.

Incremental mode (recommended):
```bash
bash scripts/auto-protect.sh modify --enable "EIP,NatEIP" --disable "SlbEIP" --yes
```

The script reads the current config, merges the changes, and submits the full config. This avoids accidentally overwriting other settings.

> **⚠️ MANDATORY: Idempotent Execution Rule for auto-protect modify**
> When the user requests enabling certain resource types, you **MUST** call `auto-protect.sh modify --enable <types> --yes` regardless of what the current config shows.
> - Even if `auto-protect.sh query` shows the requested types are already `true`, **still execute the modify command**. The API call is idempotent and safe.
> - Do NOT conclude "no modification needed" or skip modify based on query results alone.
> - Examples of WRONG behavior:
>   - Query shows `EcsPublicIP: true` → "Already enabled, no action needed" → **WRONG**, must still call modify
>   - Query shows all requested types already enabled → "Config is already in the target state, skipping" → **WRONG**, must still call modify

Full config mode:
```bash
bash scripts/auto-protect.sh modify --config '{"EIP":true,"NatEIP":false,...}' --yes
```

Use `--dry-run` to preview the merged config before applying — with `--enable` / `--disable` that preview reads the current config from the API, so it needs `SKILL_SESSION_ID` (see the second caveat in "Confirmation and the `--yes` Flag"). `--yes` is required for execution — without it the script exits with `NotConfirmed` (exit code 1) and the config is left unchanged. In non-interactive (Agent) mode, pass it as part of normal execution.

## Multi-Account Operations

`--member-uid <uid>` operates on a member account's assets, but only the asset-scoped commands accept it:

| Command | `--member-uid` |
|---|---|
| `fw-switch.sh query` | Supported |
| `fw-switch.sh enable` / `disable` | Supported |
| `fw-switch.sh enable-all` / `disable-all` | **Rejected** (`Unknown option`, exit 1) |
| `auto-protect.sh query` / `modify` | **Rejected** (`Unknown option`, exit 1) |

When the user manages multiple accounts under a management account, ask which account they want to operate on and pass the member UID on the commands that accept it. For a member account's assets, reach the whole-account effect via `enable --regions ... --member-uid <uid>` rather than `enable-all`, which cannot target a member account. Auto-protection settings are configured per account — switch profile or credentials to configure a member account's auto-protection.

## Handle Errors

When an API call fails, the scripts output a JSON error with `error_code` and `error_message`, plus diagnostic guidance to stderr. Common scenarios:

- `ErrorInstanceOpenIpNumExceed` / `ErrorGeneralInstanceSpecFull`: protection quota or instance spec reached the limit — suggest upgrading the CFW edition.
- `ErrorBandwidthPenalty`: bandwidth overuse enforcement — advise waiting or contacting support.
- `ErrorInstanceStatusNotNormal`: instance may be unpaid or abnormal — check CFW console.
- `ErrorParamsNotEnough`: at least one filter dimension is required for enable/disable. The scripts guard this locally first (exit 1, no API call), so reaching this error means the guard was bypassed — re-check the filters passed in.
- `ErrorAuthentication` / `NoPermission`: credential or permission issue — run `validate-cli.sh` and check `references/ram-policies.md`.

For the full error code reference, read `references/api-errors.md`.

## Script Reference

| Script | Purpose | Key Params |
|---|---|---|
| `fw-switch.sh query` | Query assets and protection status | `--region`, `--status`, `--resource-type`, `--search`, `--ip-version`, `--member-uid`, `--new-resource-tag`, `--page`, `--page-size`, `--all-pages`, `--export-csv` |
| `fw-switch.sh enable` | Enable protection (flexible filters) | `--ips`, `--regions`, `--resource-types`, `--ip-version`, `--member-uid` |
| `fw-switch.sh disable` | Disable protection (flexible filters) | same as enable |
| `fw-switch.sh enable-all` | Enable ALL public IP protection | `--instance-id`, `--yes` |
| `fw-switch.sh disable-all` | Disable ALL public IP protection | `--instance-id`, `--yes` |
| `auto-protect.sh query` | Query auto-protection config | (none) |
| `auto-protect.sh modify` | Modify auto-protection config | `--enable`, `--disable`, `--config`, `--yes` |
| `validate-cli.sh` | Check CLI and credentials | `--check-permission` |

All scripts support `--dry-run` and `--help`. Exit codes: 0 = success, 1 = parameter error, 2 = API error.

`--dry-run` previews the **functional** parameters (API action plus the filters that decide what gets changed). At execution time `call_cfw_api` additionally appends infrastructure flags that are identical on every call and never need reviewing — the request/connect timeouts and the `--user-agent` observability tag described above.

The underlying switch APIs also accept their own server-side `DryRun` precheck flag and a `ClientToken` for idempotency. These scripts deliberately surface neither: `--dry-run` stays a local command preview (with the single read-only exception noted above), and a retry after a failed enable/disable is safe without a token because the switch APIs are idempotent by target state. Do not try to pass `--DryRun` or `--ClientToken` through the scripts — they are rejected as `Unknown option`.
