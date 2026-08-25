---
name: alibabacloud-cfw-nat-firewall-protect
description: >
  Manage Alibaba Cloud Firewall (CFW) NAT Firewall (NAT boundary firewall): query firewalls and
  protection status, enable/disable the protection switch, assess which NAT gateways can be
  protected and produce a plan, run the creation pre-check, diagnose route-entry inconsistency
  (route-diff), prepare manual-mode diversion assets, create a firewall (auto or manual vswitch
  diversion), and change engine strict mode. Deleting/releasing a firewall is NOT supported:
  protection can be switched off, but the resource must be released by the user in the console.
  Use when users mention NAT firewall, NAT boundary firewall, NAT gateway protection, protecting
  private-network outbound traffic, opening/closing the NAT firewall switch, assessing how to
  enable protection, or diagnosing creation failures from inconsistent custom route entries.
  管理阿里云云防火墙（CFW）NAT边界防火墙：查询防火墙与防护状态、开启/关闭防护开关、开墙评估与开墙方案、
  创建预检查、路由条目不一致诊断、手动引流准备、创建NAT防火墙、修改引擎模式。不支持删除/释放防火墙，
  需用户在控制台自行操作。适用于NAT防火墙、NAT网关防护、私网出方向防护、开关NAT墙、开墙评估等场景。
license: Apache-2.0
compatibility: >
  Requires aliyun CLI >= 3.3.3 with CFW plugin and Vpc plugin installed.
  Scripts compatible with bash >= 3.2 (macOS default). python3 required for
  the create command's route auto-discovery.
  Compatible engines: qwen-code, qoder, openclaw.
metadata:
  domain: aiops
  owner: cfw-team
  contact: cfw-agent@alibaba-inc.com
allowed-tools: Bash Read
---

## Operation Routing

Identify the user's intent, then route to the matching execution path:

| User Intent | Execution Path |
|---|---|
| Query NAT firewall list / which NAT gateways are protected | `nat-fw-switch.sh query` with filters |
| **Which NAT gateways are unprotected, and how should I protect them?** | `nat-fw-lifecycle.sh assess` (read-only assessment + per-gateway recommendation) |
| **Can THIS NAT gateway be protected? Give me the enablement plan** | `nat-fw-lifecycle.sh assess --nat-gateway-id <id>` (adds the server pre-check + a ready-to-run `plan`) |
| Enable/disable protection for **specific NAT firewalls** | `nat-fw-switch.sh enable/disable --proxy-ids "..."` (three-phase workflow below) |
| Check whether a NAT gateway can have a NAT firewall created | `nat-fw-lifecycle.sh precheck` |
| Query NAT firewall authorization quota | `nat-fw-lifecycle.sh quota` |
| **Diagnose inconsistent custom route entries** (creation failed with `ErrorNatCustomRouteEntryDifferent`, or assess warned about it) | `nat-fw-lifecycle.sh route-diff` (read-only per-table diff + alignment plan; NEVER modifies routes) |
| Prepare manual-mode assets (vswitch + custom route table) | `nat-fw-lifecycle.sh prepare` (idempotent; reuses qualifying assets) |
| Create a NAT firewall for a NAT gateway | Creation workflow: assess -> quota -> precheck -> `nat-fw-lifecycle.sh create` |
| Delete / release a NAT firewall | **NOT SUPPORTED - releasing the resource is the user's own action.** Offer `nat-fw-switch.sh disable` to stop protection instead, and point to the Cloud Firewall console (NAT Boundary Firewall -> Delete) for the actual release. `nat-fw-lifecycle.sh delete` only prints this guidance plus a read-only impact report |
| Rename a NAT firewall / change loose-strict engine mode | `nat-fw-lifecycle.sh update` (built-in verification runs automatically) |

Key concept: one NAT gateway maps to exactly one NAT firewall. The firewall must be **created** before its switch can be toggled. Status `normal` means the switch is open (protecting); `closed` means the switch is off.

## Check CLI Environment

Before any operation, validate the CLI environment:
```bash
bash scripts/validate-cli.sh --check-permission
```

Check results and remediate:
- `cli_installed` = false -> run `--install-guide` for installation instructions
- `cli_version_ok` = false -> CLI version below 3.3.3, reinstall or update
- `auto_plugin_install` = false -> run `aliyun configure set --auto-plugin-install true`
- `credential_valid` = false -> no profile configured, run `aliyun configure` to add one
- `permission_check` = false -> credentials are invalid/expired or the identity lacks `yundun-cloudfirewall:DescribeSecurityProxy`; check AccessKey status and refer to `references/ram-policies.md`

**Manual-mode permission pre-probe:** before the manual diversion workflow (especially before `prepare`), probe the VPC WRITE permissions in one shot - it calls the write APIs with fake resource IDs (nothing is created) and classifies each action as `granted` / `missing` / `unknown`:
```bash
bash scripts/validate-cli.sh --check-permission --mode manual [--region cn-hangzhou]
```
Check `manual_mode_ready` and `missing_required_permissions` in the output. VPC write permissions are granted per-action - this probe prevents discovering `Forbidden.RAM` failures one action at a time mid-workflow. See `references/ram-policies.md` section Manual Mode Preparation Permissions.

Note: `credential_valid` only reflects whether a profile exists in `aliyun configure list`. Real credential validity is verified by `permission_check`, which calls the actual CFW business API - invalid/expired AccessKey will fail there.

**Install or upgrade the CLI (required when `cli_installed` or `cli_version_ok` is false):** this skill requires aliyun CLI >= 3.3.3. The official installer handles both fresh installation and in-place upgrade - re-run it to reach the required version:
```bash
curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh | bash
```
Verify with `aliyun version`. Show the full step-by-step installation guide:
```bash
bash scripts/validate-cli.sh --install-guide
```

After environment checks pass, ensure plugins are up-to-date:
```bash
aliyun plugin update
```

> **API Version Note:** Cloudfw uses CLI plugin mode (`aliyun-cli-cloudfw`). The API version is managed internally by the plugin (actual version: `2017-12-07`). Call CFW commands using the default invocation - do **NOT** pass `--version`. The plugin rejects any external version override and will error with `unchecked version`. The `call_cfw_api` function in `common.sh` is designed accordingly and does not include `--version`.

## Observability

**User-Agent template** (every `aliyun` CLI call must carry it):

```
AlibabaCloud-Agent-Skills/alibabacloud-cfw-nat-firewall-protect/{session-id}
```

**session-id generation rule**: 32-character lowercase hex, generated **once per session** and reused **identically by every call** in that session, so all API calls of one session can be correlated. `scripts/common.sh` implements this on load - it reuses `SKILL_SESSION_ID` when already exported (to join an existing session), otherwise generates one (`uuidgen` with a `/dev/urandom` fallback) and exports `ALIBABA_CLOUD_USER_AGENT` with the template above. All four API wrappers (`call_cfw_api` / `call_vpc_api` / `call_ecs_api` / `call_quotas_api`) pass it via `--user-agent`, so scripted calls need no extra work. Any ad-hoc CLI call outside the scripts MUST add `--user-agent "$ALIBABA_CLOUD_USER_AGENT"` explicitly.

This script-level `--user-agent` injection is the ONLY UA mechanism. Do NOT enable, configure, or disable any global agent-mode or global user-agent setting via `aliyun configure` - UA injection happens per-call, exclusively through the scripts.

> **CLI invocation mode:** Cloudfw / Vpc / Ecs run as CLI plugins that keep PascalCase API names and flags (`aliyun Cloudfw DescribeSecurityProxy --PageNo 1`), and MUST NOT receive `--version`. The `quotas` plugin instead requires kebab-case for BOTH the API name and its flags (`aliyun quotas get-product-quota --product-code vpc --quota-action-code q_e1mq5l`).

## RAM Policy and Permission Handling

The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`. Read `references/ram-policies.md` for the full permission list (including the two `vpc:Describe*` read permissions used by `create`'s route auto-discovery).

> **Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this Skill
> 2. Guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Query NAT Firewalls

```bash
bash scripts/nat-fw-switch.sh query [options]
```

Available filters: `--region`, `--status`, `--nat-gateway-id`, `--vpc-id`, `--proxy-id`, `--proxy-name`, `--member-uid`. Each filter accepts a single value. For multi-region queries, make separate calls and merge the results.

Pagination: `--page` (default 1), `--page-size` (default 10, max 50). Check `TotalCount` in the response to determine if more pages exist.

The response returns the raw API JSON with a `ProxyList` array and `TotalCount`. Key fields per entry: `ProxyId`, `ProxyName`, `NatGatewayId`, `NatGatewayName`, `VpcId`, `VpcName`, `RegionNo`, `Status`, `CidrBlock`, `SnatIpList`, `VSwitchId`, `MemberUid`, `Detail`.

**Status semantics** (present in a human-friendly way):

| Status | Meaning |
|---|---|
| `normal` | Protection enabled (switch open) |
| `closed` | Protection disabled (switch closed) |
| `opening` / `closing` | Enabling / disabling in progress |
| `configuring` | NAT firewall being created |
| `deleting` | NAT firewall being deleted |
| `abnormal` | Abnormal - show the `Detail` field and suggest checking the console |

> ** MANDATORY: Table Presentation Rule**
> Whenever presenting NAT firewall query results to the user, you MUST render them as a **Markdown table** - never dump raw JSON, and never describe the assets in prose only. This applies to every query-driven answer: asset inventory requests, impact previews (Phase 1), and result verifications (Phase 3).
>
> **Columns** (fixed order, keep all of them):
> `ProxyId | ProxyName | NatGatewayId | Region | Status | SnatIp | VpcName`
>
> Rules:
> - `Status` must be shown as **English semantics paired with the Chinese console wording**, e.g. `normal (protection on)`, `closed (protection off)`, `abnormal`.
> - `SnatIp` joins `SnatIpList` with `, `.
> - For `abnormal` rows, append the `Detail` content right below the table or in the Status cell - it is the key troubleshooting clue.
> - Below the table, always add one summary line: `Total N | Page X/Y | Filters: ...`. If more pages exist, tell the user explicitly.
> - **Empty result is NOT silence**: if `ProxyList` is empty, still output the table header plus `(no matching records)`, the summary line, and suggest retrying without (or with looser) filters to distinguish "no assets" from "filter too strict".
>
> Template:
>
> ```
> | ProxyId | ProxyName | NatGatewayId | Region | Status | SnatIp | VpcName |
> |---|---|---|---|---|---|---|
> | proxy-bp1xxxx | nat-fw-prod | ngw-bp1xxxx | cn-hangzhou | normal (protection on) | 47.96.x.x | prod-vpc |
>
> Total 1 | Page 1/1 | Filters: status=normal
> ```

## Enable / Disable Switch Workflow

All enable/disable operations follow a three-phase workflow: **Impact Preview -> User Confirmation -> Execute -> Result Verification**. Skipping any phase may lead to unintended changes or unverified outcomes.

> ** MANDATORY: Business Impact Warning**
> Every switch operation (enable AND disable) triggers NAT route switching, causing a **1~2 second interruption of long-lived connections** (short connections unaffected). In Phase 1 you MUST warn the user and recommend operating during business off-peak hours.

> ** MANDATORY: Non-Interactive Execution Rule**
> When running as an Agent (non-interactive mode), `--yes`-style confirmation is implicit. You **MUST** complete ALL three phases **unconditionally**:
> - Phase 1 shows **0 affected firewalls** -> **still execute Phase 2 and Phase 3**. Do NOT stop.
> - Phase 1 shows all firewalls already in desired state -> **still execute Phase 2 and Phase 3**. Do NOT stop.
> - **NEVER** terminate the workflow after Phase 1 alone. NEVER output "no action needed" without completing Phase 2+3.

### Phase 1: Impact Preview

Query the NAT firewalls that will be affected and present a human-friendly summary:

- **enable**: `nat-fw-switch.sh query --status closed` (+ user's region/gateway filters)
- **disable**: `nat-fw-switch.sh query --status normal` (+ user's region/gateway filters)

Summarize to the user:

- If total <= 5: list all (ProxyId, ProxyName, NatGatewayId, RegionNo)
- If total > 5: list 3 representative examples, then summarize the rest by region

Example format:
```
This operation will ENABLE the NAT firewall switch for the following 3 NAT firewalls:

1. proxy-bp1xxxx (nat-fw-prod, NAT gateway ngw-bp1xxxx, cn-hangzhou)
2. proxy-bp2yyyy (nat-fw-test, NAT gateway ngw-bp2yyyy, cn-shanghai)
3. proxy-bp3zzzz (nat-fw-dev, NAT gateway ngw-bp3zzzz, cn-beijing)

WARNING: Switching triggers NAT route changes and causes a 1~2 second interruption
of long-lived connections (short connections unaffected). Recommend off-peak hours.

Confirm execution?
```

For **disable**, additionally warn: once closed, private-to-internet traffic no longer passes through Cloud Firewall - access control policies and threat intelligence on the NAT boundary stop working.

Wait for **explicit user confirmation** before proceeding to Phase 2.

### Phase 2: Execute

After user confirms, run the switch command with the ProxyIds collected in Phase 1:

```bash
bash scripts/nat-fw-switch.sh enable --proxy-ids "proxy-xxxx,proxy-yyyy"
bash scripts/nat-fw-switch.sh disable --proxy-ids "proxy-xxxx"
```

> ** MANDATORY: Idempotent Execution Rule**
> Even if Phase 1 shows all target firewalls already in the desired state (or 0 matches), you **MUST still execute** the command. Do NOT skip Phase 2 based on current status or zero-count results.

> ** KNOWN API BEHAVIOR:** `SwitchSecurityProxy` returns success even for non-existent ProxyIds. A successful API response does NOT prove the switch changed - Phase 3 verification is the only reliable confirmation. See `references/api-errors.md`.

### Phase 3: Result Verification

Poll the firewall status to verify the operation took effect:

1. **Initial wait**: sleep 5 seconds
2. **Query**: `nat-fw-switch.sh query --proxy-id <id>` for each operated proxy (or a filtered list query)
3. **Adaptive polling**: if not transitioned, poll every 5 seconds, maximum 30 seconds total
4. **Report results**:
   - All transitioned: "Done. NAT firewall switch enabled for all 3 NAT firewalls."
   - Partial: "2/3 completed. proxy-bp3zzzz still in status `opening`. Check the Cloud Firewall console to confirm final status."
   - Proxy not found in query results after a switch call: treat as FAILED (API silently accepts unknown IDs) and report to the user with the RequestId.

Expected status transitions:
- enable -> `closed` -> `opening` -> `normal`
- disable -> `normal` -> `closing` -> `closed`

## Assessment (run BEFORE creation)

Assessment happens in **two stages**: a region-wide inventory to pick the gateway, then a deep single-gateway evaluation that produces the enablement plan.

### Stage 1 - inventory (pick the gateway)

When the user asks to enable/configure NAT firewall protection - especially without specifying a gateway - ALWAYS run the read-only assessment first and present its result as tables before touching anything:

```bash
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou [--vpc-id vpc-xxx]
```

### Stage 2 - enablement plan (immediately after the gateway is chosen)

> ** MANDATORY: Plan-First Rule.** As soon as the target gateway is known, run the single-gateway evaluation and present ONE complete plan. Do NOT ask the diversion mode, the name, the switch state or the engine mode as separate sequential questions - the mode is a *conclusion of the evaluation*, not an opening question, and asking it before the evaluation means deciding on incomplete data.

```bash
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou --nat-gateway-id ngw-xxx
```

This adds the authoritative **server-side pre-check** and a `plan` object: `actionable`, `mode`, `gateway` facts, `quota`, `parameters` (recommended diversion + defaults needing confirmation), `blockers`, `risks` (each with `what` / `impact` / `options`), `estimated_duration`, `business_impact`, `reversibility`, the ready-to-run `command`, and `post_steps`. The pre-check result sits in `precheck`: `status`, `item_count`, `items` (ALL items, each with `name` / `display` / `status` / `suggestion`) and `failed_items`. Present every item using its `display` label - there is no need to run the `precheck` subcommand separately. When the gateway already has a firewall, `plan.actionable` is `false` with the existing firewall and the switch-workflow next step.

Present the plan as a compact table (diversion mode + parameters, duration, business impact, blockers, risks), then ask for confirmation with a SINGLE question that bundles the parameters still needing a decision (name / switch after creation / engine mode) plus an option to change the diversion mode. Skip straight to remediation when `blockers` is non-empty - never offer to create.

The report contains, per region:

- **Quota** (`total` / `used`) and **already-protected gateways** (`protected_firewalls`)
- **Every unprotected NAT gateway** (`unprotected_gateways`): VPC, availability zone, EIP count, SNAT/DNAT status, VPC CIDR
- **Free /28 CIDR candidates** inside the VPC (`free_cidr_candidates`) - options for auto mode
- **Eligible existing vswitches** (`manual_candidates`: same zone, >= /28, free IPs > EIP count, bound to a custom route table without a 0.0.0.0/0 entry, and carrying no attached ENI) - options for manual mode. Candidates whose route table holds **business routes** (next hop `Instance` / `HaVip` / `NatGateway` ...) or whose vswitch already hosts ENIs are **dropped** with the reason in `notes`, because manual mode requires a route table freshly created for the firewall. Per candidate: `route_table_clean` (`yes` = empty table, `no` = holds tolerated cross-VPC return routes), `route_table_entry_count`, `route_table_entries` (the actual entries) and `attached_eni_count`. Clean candidates are ranked first, so `suggested_vswitch_id` prefers an empty table; when only a `route_table_clean: no` candidate exists, the recommendation `reason` carries a WARNING - relay it and have the user confirm the pre-existing entries are the intended return routes, or run `prepare` to build clean assets
- **Recommendation** per gateway (`recommendation.mode` = `auto` / `manual` / `none`, with `reason` and `suggested_vswitch_cidr` / `suggested_vswitch_id`)
- **Post-creation quota projection** (`quota_projection` per gateway): whether creation would exhaust VPC resources - custom route tables (`vpc_quota_route_tables_num`, auto mode +1), vswitches (`vpc_quota_vswitches_num`, auto mode +1), SNAT entries (`natgw_quota_snat_entry_num`, +1 in both modes) and **VPN-pointing custom routes** (`vpc_quota_vpn_custom_route_entry`, auto mode inherits the diversion-scope VPN entries into the firewall route table). Each item carries `current` / `limit` / `after_create` / `status` (`ok` / `warning` >= 80% / `exceeded` / `unknown`). Limits are resolved live via Quotas Center (`quotas:GetProductQuota`, opaque `q_*` action codes - see `references/ram-policies.md`) - documentation defaults are deliberately NOT assumed, because customers may have raised their quotas. `status: exceeded` on route tables / vswitches / VPN routes downgrades the recommendation from `auto` to `manual` (or `none`). **Caveat when recommending manual mode as the workaround for VPN-route quota exceeded**: manual mode only avoids the AUTOMATIC inheritance (`+0` in the projection); if the user wants to protect cross-VPC traffic they must manually add the return routes - including the VPN-pointing ones - to the firewall route table, which can still exhaust the same quota. Always relay this caveat (the projection carries it in `vpn_custom_routes.note` when applicable) and advise raising the quota or cleaning up redundant routes first - never present "switch to manual mode" as a guaranteed fix for the VPN-route quota. **If `quota_projection_note` says the permission is missing, follow the Permission Failure Handling process: guide the user to grant `quotas:GetProductQuota` (see `references/ram-policies.md`) and re-run assess - do NOT present the projection as reliable**
- **Route-entry consistency** across the **diversion route tables** - the tables that actually hold an entry whose next hop is the target NAT gateway (exactly the rows the console lists under "Select Route Table"). Tables with no route to the gateway never participate in the diversion, so they are NOT compared; comparing every VPC table produces false positives. An `inconsistent` result is reported in `notes` and in the recommendation `reason` - it means auto-mode creation may fail with `ErrorNatCustomRouteEntryDifferent` (top auto-mode failure cause in service orders). Why it matters: auto mode builds the firewall's diversion-vswitch route table from those custom entries; inconsistent tables would make the firewall vswitch inherit routes (vppeer/vpngateway) that some business vswitches deliberately do not want, and all diverted traffic forwarding through it would suffer route diffusion. This is also why "narrowing the protection scope" (diverting fewer tables) works as a real-world workaround. Surface the warning when present, and point the user to `nat-fw-lifecycle.sh route-diff --region <id> --vpc-id <id>` for the deep diagnosis (see below)
- **Diversion scope** in `notes`: how many route tables carry a route to the gateway. **Zero is a blocker** - nothing to divert, and auto-mode creation would fail with `MissingNatRouteEntryList`; the fix is to add a `0.0.0.0/0` route to the NAT gateway in the business route table first. Note that subnets whose route table has no route to the gateway are NOT covered by the firewall (no egress through it) - call out such coverage gaps when the user expects those subnets to be protected
- **Blockers** (no EIP, no SNAT table, **SNAT table with 0 entries**, DNAT entries exist) and **notes** (degraded checks due to missing read permissions)

> ** MANDATORY: Assessment Freshness Rule (environment drift)**
> The assess report is a **point-in-time snapshot**: the user can change the environment in the console at any moment (delete/modify vswitches, add DNAT entries, bind/unbind EIPs, edit route tables), silently invalidating a previous report.
> - Every report carries `assessed_at` and a `freshness_warning` - surface both when presenting results.
> - If ANY console change happened (or is suspected) since the assess run, **re-run `assess` before proceeding** - do NOT reuse stale candidates.
> - `create` re-validates its inputs at execution time (vswitch existence/constraints, CIDR overlap) and instructs re-running `assess` when referenced resources are gone - if you hit such an error, re-run `assess`, re-present the refreshed recommendations, and only then retry `create`.

Present to the user:

1. A table of unprotected gateways (ID, name, VPC, zone, EIPs, blockers)
2. Ask the user to pick the target gateway via a NEUTRAL question (full IDs - see the Resource Identity Rule below)
3. Then run **Stage 2** for that gateway and present the resulting plan + a single confirmation question. Do NOT pre-ask the diversion mode in step 2

The assessment is purely read-only; missing VPC read permissions degrade individual fields to `notes` instead of failing.

## Route-Diff Diagnosis (route-entry inconsistency)

Run this when `assess` reports a route-entry consistency warning, or when creation fails with `ErrorNatCustomRouteEntryDifferent`:

```bash
bash scripts/nat-fw-lifecycle.sh route-diff --region cn-hangzhou --vpc-id vpc-xxx
```

The command is **read-only**. Its JSON report contains: `route_tables` (per-table custom entry counts), `divergent_entries` (which entries exist in which tables and are missing from which), `divergent_next_hop_types` + `classification` (`business_topology` = VPN/peering/CEN/RouterInterface/VBR routes, i.e. deliberate topology differences, NOT misconfiguration), `alignment_plan` (union-add / intersection-remove lists), `options` and `recommendation`.

**Decision flow is STAGED - never merge these steps into one question:**

> ** MANDATORY: Staged Question Design.**
> 1. **Gateway question first** (Stage 1): ask only which NAT gateway to protect, with full IDs. Do NOT bundle the diversion mode into it.
> 2. **Plan, then ONE confirmation** (Stage 2): run `assess --nat-gateway-id`, present the plan (recommended mode + parameters + duration + business impact + risks), then ask a single confirmation question bundling the open parameters (name / switch after creation / engine mode) and an option to override the diversion mode. The mode must be presented as the evaluation's recommendation with its factual basis - never as a bare "auto vs manual" question asked before the evaluation.
> 3. **Risk handling only when real**: if `plan.risks` contains `route_entry_inconsistent` (the DIVERSION tables genuinely differ), present its `options` and let the user decide:
>    - **Try auto-mode diversion directly** (proceed; fall back to manual mode per the Fallback Rule if the server rejects it), or
>    - **Switch to manual-mode diversion** (low risk, keeps existing routes untouched), or
>    - **Align the inconsistent route entries** (per the `route-diff` alignment plan - HIGH risk, executed by the user/network team, see below).
> 4. Never use leading labels (no "verification-failed scenario" / "direct success"); describe each option factually.
> 5. The same pattern applies to any creation failure: report the error first, then offer the matching remediation options.

> ** MANDATORY: Resource Identity Rule (applies to EVERY clarification question).**
> Whenever a question asks the user to pick a target resource (NAT gateway, NAT firewall, vswitch, route table, etc.), each option MUST contain the resource's **FULL ID and FULL name** - never truncated, abbreviated, or ellipsized (e.g. `ngw-bp1exampleid00000001 (nat-prod)`, NOT `ngw-bp1exam...`). Rationale: truncated IDs are indistinguishable and force the user to scroll back to the table to guess which resource an option refers to.
> - Recommended option label format: `<full-ID>(<name>)`, e.g. `ngw-bp1exampleid00000001(nat-prod)`.
> - Some UIs render only the option DESCRIPTION (labels collapse to A/B/C). Therefore the full `<ID>(<name>)` MUST appear in the description text as well, at its very beginning. Never put contextual fields (VPC ID, zone) ahead of the resource identity.
> - If the UI imposes a label length limit, keep the full ID intact and shorten prose instead - the ID is never expendable.
> - Keep option descriptions minimal: identity first, then at most one line of decision-relevant facts. Secondary details (pre-check status, blockers) belong in the summary table in the message body, not crammed into every option.

Option details for step 2:

- **Option A - manual-mode diversion (recommended, low risk)**: divert via a dedicated vswitch bound to a NEW custom route table (`prepare` -> `create --vswitch-id`); existing route tables stay untouched. This is exactly how the top real-world service order was eventually worked around.
- **Option B - align custom route entries (HIGH risk)**: make every route table carry the identical entry set per `alignment_plan`. This changes forwarding for ALL vswitches bound to those tables and may reroute or blackhole production traffic - divergent entries are usually deliberate business topology (VPN to IDC, peering, CEN).

> ** MANDATORY: Never Auto-Execute Option B.** `route-diff` only generates the plan; the skill MUST NOT create/delete route entries itself. If the user picks option B, hand the `alignment_plan` to them (or their network team) for manual review and execution in the console, then re-run `assess` to confirm consistency before retrying auto-mode creation. When `classification` is `business_topology` or `mixed`, explicitly advise against option B.

## Creation Workflow

Use when the user wants to protect a NAT gateway that has no NAT firewall yet. Steps:

1. **Assess in two stages** (see the Assessment section above): Stage 1 inventory -> user picks the gateway -> Stage 2 `assess --nat-gateway-id` produces the plan (includes quota + the server-side pre-check). Skip only if the user already provided a specific gateway AND mode.
2. **Read the plan instead of re-running the checks**: `plan.quota.sufficient` covers the quota check (`false` -> stop and advise purchasing more authorizations), `precheck.status` covers the dependency pre-check, `plan.blockers` lists everything that must be fixed first, and `plan.command` is the ready-to-run creation command. Steps 3-4 below are only needed when Stage 2 was skipped or its checks degraded.
3. **Locate the NAT gateway**: confirm `--nat-gateway-id`, `--region`, `--vpc-id` with the user (or take them from the assessment). If Cloud Firewall reports the gateway is not found (error `-360838`), it needs 1~5 minutes to sync - retry later or use "Asset Sync" in the console.
4. **Pre-check**:
   ```bash
   bash scripts/nat-fw-lifecycle.sh precheck --nat-gateway-id ngw-xxx --region cn-hangzhou --vpc-id vpc-xxx
   ```
   Present every check item result. Item names come verbatim from the API and some phrasings are awkward - present them in **requirement-style** wording; in particular the negative-style DNAT pre-check item must be presented as a requirement (the NAT gateway must have NO DNAT entries - DNAT entries are mutually exclusive with a NAT firewall and must be deleted first). Every item in the `assess` plan carries this friendly requirement-style label in its `display` field - prefer it over `name`. If any item fails, read `references/nat-prerequisites.md` and guide the user to fix it. Typical causes:
   - DNAT entries exist (delete them first)
   - no SNAT entries configured
   - missing `0.0.0.0/0` route to the NAT gateway
   - no free /28 subnet inside the VPC
   - **EIP count out of range**: fewer than 1 EIP, or more than the Cloud Firewall supported bound-EIP count (default **20**). A user hitting the upper bound has usually ALREADY raised the NAT gateway's own binding quota - the fix is a **Cloud Firewall-side ticket** or a **PDSA whitelisting evaluation**. NEVER advise unbinding EIPs, and NEVER advise raising the NAT gateway quota again

   Do NOT proceed to create until the pre-check passes or the user explicitly accepts the risk.
5. **Impact preview & confirm**: explain that creation (auto mode) auto-creates a diversion vswitch + custom route table + SNAT entries, takes about **2~5 minutes per bound EIP**, and has **no business impact** while the switch stays closed (default). Ask for the name (`--proxy-name`), the diversion mode, and engine mode if not given (default: loose mode).
   - **Auto mode (recommended)**: needs a free CIDR for the diversion vswitch (`--vswitch-cidr`, e.g. `10.0.3.0/28` inside the VPC, must not overlap existing vswitches; use the assessment's `suggested_vswitch_cidr`).
   - **Manual mode**: reuses an EXISTING vswitch (`--vswitch-id`; use the assessment's `suggested_vswitch_id`). Use it when the VPC has no spare address space. The vswitch MUST be bound to a **NEW custom route table** (no `0.0.0.0/0` entry, no business routes - only cross-VPC return routes may pre-exist) and MUST have no other cloud resources on it - either the user prepared it, or run the **Prepare** step below first. `create` re-verifies both at execution time and refuses when the table carries business routes or the vswitch hosts ENIs. See `references/nat-prerequisites.md` section Traffic Diversion Mode.
5b. **Prepare manual-mode assets (manual mode only, when no qualifying vswitch exists)**: first probe permissions (`validate-cli.sh --check-permission --mode manual`), then:
   ```bash
   bash scripts/nat-fw-lifecycle.sh prepare \
     --region cn-hangzhou --vpc-id vpc-xxx --nat-gateway-id ngw-xxx \
     [--vswitch-cidr 10.0.4.0/28] --yes
   ```
   Idempotent: reuses an existing qualifying vswitch (same zone, >= /28, free IPs > EIP count, clean custom route table) and an orphan custom route table (unbound, no 0.0.0.0/0 - e.g. a leftover `Cloud_Firewall_ROUTE_TABLE`). `--vswitch-cidr` is only required when nothing can be reused. Preview with `--dry-run` first. The output's `next_step` field contains the ready-to-run `create` command.

   > ** MANDATORY: Prepare Confirmation Rule.** After the `--dry-run` preview, present the preparation plan together with the manual checklist (the route table is brand-new, the vswitch carries no other cloud resources, cross-VPC return routes are intended) and request user confirmation BEFORE running `prepare --yes`. When the dry-run shows PURE REUSE of qualifying existing assets, still present the checklist alongside the plan (the script has already validated every hard constraint, so the confirmation carries lower weight). When running as an Agent (non-interactive mode), present the plan + checklist, then proceed - but the checklist MUST appear in the output BEFORE execution, never only in a post-hoc final report.
6. **Create** (auto mode):
   ```bash
   bash scripts/nat-fw-lifecycle.sh create \
     --nat-gateway-id ngw-xxx --region cn-hangzhou --vpc-id vpc-xxx \
     --proxy-name nat-fw-prod --firewall-switch close --strict-mode 0 \
     --vswitch-cidr 10.0.3.0/28 --yes
   ```
   Manual mode (mutually exclusive with `--vswitch-cidr`):
   ```bash
   bash scripts/nat-fw-lifecycle.sh create \
     --nat-gateway-id ngw-xxx --region cn-hangzhou --vpc-id vpc-xxx \
     --proxy-name nat-fw-prod --firewall-switch close --strict-mode 0 \
     --vswitch-id vsw-xxx --yes
   ```
   The route entry list (`NatRouteEntryList`) is auto-discovered via VPC APIs. If auto-discovery fails (e.g. missing VPC read permission), ask the user for the route entries and pass `--route-entry-json`.

   **Built-in CIDR pre-check (auto mode, automatic):** before route discovery, the script validates `--vswitch-cidr`: format (python3 `ipaddress`), subnet-of-VPC (incl. secondary CIDRs via `DescribeVpcAttribute`), and no overlap with existing vswitches (`DescribeVSwitches`). On conflict it exits 1 with the conflicting vswitch IDs and up to 3 free `/28` suggestions. If the two VPC read permissions are missing, the check degrades to a warning and lets the create API enforce the constraint.

   **Built-in vswitch pre-check (manual mode, automatic):** before route discovery, the script validates `--vswitch-id` against the official hard constraints: vswitch exists, same VPC, same availability zone as the NAT gateway (`NatGatewayPrivateInfo.IzNo`), prefix >= /28, `AvailableIpAddressCount` > bound-EIP count, bound route table is a custom (non-system) table without a 0.0.0.0/0 entry. It then prints a **MANDATORY human checklist** (the CLI cannot verify: the route table is brand-new, no other cloud resources attached to the vswitch, cross-VPC return routes added) - present it to the user and get confirmation before executing. Missing VPC read permissions degrade to a warning.
7. **Verify**: poll `nat-fw-switch.sh query --nat-gateway-id ngw-xxx` every 30 seconds (creation takes minutes) until status transitions `configuring` -> `normal`/`closed`. Maximum polling: 15 minutes; otherwise tell the user to check the console.
8. **Optional enable**: creation leaves the switch closed by default. If the user also wants protection active, run the Enable/Disable Switch Workflow afterwards (with the 1~2s flap warning).

> **Note on diversion mode:** This skill supports both modes - auto vswitch creation (`--vswitch-cidr`, recommended) and manual vswitch selection (`--vswitch-id`). Key differences of manual mode: the vswitch stays a user asset (NOT reclaimed when the firewall is deleted), and the user must pre-create and bind a NEW custom route table. Full constraints and checklist: `references/nat-prerequisites.md` section Traffic Diversion Mode.

> ** MANDATORY: Auto -> Manual Fallback Rule.** When creation or switch-on fails with any of the following, do NOT keep retrying auto mode - explain the cause and switch to manual mode (reuse an existing vswitch via `--vswitch-id`, or ask the user to prepare a dedicated vswitch + custom route table first):
> - `ErrorNatCustomRouteEntryDifferent` ("custom route entries in the routing tables are inconsistent") - route tables carry divergent custom entries (VpnGateway / peer / prefix-list routes). `assess` warns about this beforehand; if it was flagged, remind the user of that warning. Run `route-diff` for the per-table diagnosis and present BOTH resolution options (below) before deciding.
> - "firewall vswitch creation failed" / vswitch creation failure in auto mode - typically the auto-selected availability zone no longer allows new vswitch creation (e.g. AZ decommissioned). Pick a candidate vswitch in an active AZ from the assessment's `manual_candidates`.
> - Persistent default-route conflicts that the network team cannot remove (e.g. CEN-learned routes) - manual mode with a dedicated route table avoids rewriting production routes.
>
> **Timeout handling:** `create` retries timeout-like failures automatically (max 3 attempts) and verifies via `DescribeSecurityProxy` before each retry to avoid duplicate creation. If it still times out (common with large CENs), poll the status instead of re-submitting blindly.

## Stopping Protection: Close vs Release (deletion is out of scope)

> ** MANDATORY: No Resource Release Rule.** This Skill NEVER deletes a NAT firewall.
> `DeleteSecurityProxy` is not called anywhere, and `--yes` does not override this.
> When a user asks to "delete / remove / release / decommission" a NAT firewall, FIRST clarify which of the
> two they actually mean, because the two are routinely confused:

| | Close protection (supported) | Release the resource (NOT supported here) |
|---|---|---|
| Command | `nat-fw-switch.sh disable --proxy-ids <id>` | Cloud Firewall console: NAT Boundary Firewall -> locate the firewall -> Delete |
| API | `SwitchSecurityProxy --Switch close` | `DeleteSecurityProxy` (never called by this Skill) |
| Firewall instance | **Kept** - can be re-enabled anytime | **Destroyed**, irreversible |
| Authorization quota | Still occupied | Freed |
| Diversion assets | Untouched | Auto-mode vswitch reclaimed; manual-mode vswitch and the custom route table are left behind |
| Traffic path | Routes switch back to the original NAT path | Routes switch back to the original NAT path |
| Business impact | 1~2 second interruption of long-lived connections | Same flap, plus close+delete happening together when it is still enabled |

In most cases "I want to stop the NAT firewall" means **close**, which is reversible and keeps
everything in place. Recommend that first.

When the user genuinely wants the resource released, run the read-only helper to give them what they
need for the console operation, then hand it over:

```bash
bash scripts/nat-fw-lifecycle.sh delete --proxy-id proxy-xxx    # refuses; prints guidance + impact report
```

It reports the firewall's current status (warning that a console deletion while `normal` performs
close+delete at once) and the **assets that will NOT be reclaimed** - the manual-mode vswitch and
orphan custom route tables such as a leftover `Cloud_Firewall_ROUTE_TABLE`, which `prepare` can reuse
for a future firewall. Advise closing first during off-peak hours, then deleting in the console.

Do NOT attempt to work around this restriction with raw CLI calls - see
`references/acceptance-criteria.md`.

## Update (Rename / Engine Mode)

```bash
bash scripts/nat-fw-lifecycle.sh update --proxy-id proxy-xxx --proxy-name <name> [--strict-mode 0|1]
```

The `UpdateSecurityProxy` API requires `ProxyName` - when only changing strict mode, query the current name first and pass it back unchanged. Loose mode (0) prioritizes availability; strict mode (1) blocks unrecognized app/domain traffic when a deny rule exists.

**Built-in verification (automatic):** because `UpdateSecurityProxy` silently returns success even for unknown ProxyIds, the script verifies every update before reporting success:

1. **Existence check** - `DescribeSecurityProxy --ProxyId <id>`: if the proxy is missing, the command fails with `VerifyFailed / proxy_not_found` (exit 2) instead of claiming success. This also discovers the proxy's `RegionNo`.
2. **Field comparison** - `DescribeNatFirewallList --RegionNo <region>`: compares `ProxyName` and (when `--strict-mode` was given) `StrictMode` against the requested values, retrying up to 3 times to tolerate sync delay.
3. **Result** - exit 0 with `"verification": {"verified": true, ...}` only when the live state matches. Use `--skip-verify` only when the verifying APIs are unavailable (output then carries `"verified": false`).

> **Why two APIs:** `DescribeSecurityProxy` (used by `nat-fw-switch.sh query`) does NOT return `StrictMode` - verifying a StrictMode change against it yields a misleading absence. `DescribeNatFirewallList` is the authoritative source for `StrictMode`. The script handles this automatically; if you verify manually, use `aliyun Cloudfw DescribeNatFirewallList --RegionNo <region>`.

## Multi-Account Operations

`nat-fw-switch.sh query` supports `--member-uid <uid>` to query a member account's NAT firewalls under a management account. When the user manages multiple accounts, ask which account to operate on.

## Handle Errors

When an API call fails, the scripts output a JSON error with `error_code` and `error_message`, plus diagnostic guidance to stderr. Common scenarios:

- `-360838` ("The NAT gateway was not found"): the NAT gateway has not synced into Cloud Firewall - verify IDs and wait/retry.
- `ErrorNatCustomRouteEntryDifferent`: custom route entries differ across the VPC's route tables - run the Route-Diff Diagnosis below and present both resolution options (A: manual-mode diversion, recommended; B: align entries, high risk).
- `ErrorVswitchCidrNotInVpc`: the auto-mode CIDR is outside the VPC range - pick a CIDR inside the VPC (use the assessment's `free_cidr_candidates`).
- Creation/switch timeout (`SocketTimeout` etc.): common with large CENs - the script retries automatically; otherwise poll status before re-submitting.
- "firewall vswitch creation failed": the auto-selected AZ likely forbids new vswitch creation - fall back to manual mode.
- `MissingNatRouteEntryList`: route entries missing - re-run `create` (auto-discovery) or pass `--route-entry-json`.
- Quota exceeded: `nat-fw-lifecycle.sh quota` shows `UsedCount >= TotalCount` - purchase more authorizations.
- `ErrorInstanceStatusNotNormal`: instance may be unpaid or abnormal - check CFW console.
- `ErrorAuthentication` / `NoPermission`: credential or permission issue - run `validate-cli.sh` and check `references/ram-policies.md`.

For the full error code reference (including verified API behaviors), read `references/api-errors.md`. For creation prerequisites and business impact details, read `references/nat-prerequisites.md`.

## Script Reference

| Script | Purpose | Key Params |
|---|---|---|
| `nat-fw-switch.sh query` | Query NAT firewalls and status | `--region`, `--status`, `--nat-gateway-id`, `--vpc-id`, `--proxy-id`, `--proxy-name`, `--member-uid`, `--page`, `--page-size` |
| `nat-fw-switch.sh enable` | Enable protection switch | `--proxy-ids` (required, comma-separated) |
| `nat-fw-switch.sh disable` | Disable protection switch | `--proxy-ids` (required, comma-separated) |
| `nat-fw-lifecycle.sh precheck` | Creation pre-check | `--nat-gateway-id`, `--region`, `--vpc-id` (all required) |
| `nat-fw-lifecycle.sh quota` | Query authorization quota | (none) |
| `nat-fw-lifecycle.sh assess` | Read-only assessment: unprotected gateways + mode recommendation; with `--nat-gateway-id` also the server pre-check + enablement `plan` | `--region` (required), `--vpc-id` (optional filter), `--nat-gateway-id` (single-gateway plan) |
| `nat-fw-lifecycle.sh route-diff` | Read-only diagnosis of inconsistent custom route entries: per-table diff, next-hop classification, alignment plan (never applies it) | `--region`, `--vpc-id` (both required) |
| `nat-fw-lifecycle.sh prepare` | Prepare manual-mode assets (idempotent vswitch + route table) | `--region`, `--vpc-id`, `--nat-gateway-id` (required), `--vswitch-cidr` (when nothing reusable), `--vswitch-name`, `--route-table-name`, `--yes` |
| `nat-fw-lifecycle.sh create` | Create NAT firewall (auto or manual vswitch) | `--nat-gateway-id`, `--region`, `--vpc-id`, `--proxy-name` (required), `--vswitch-cidr` (auto mode) \| `--vswitch-id` (manual mode) - exactly one, `--firewall-switch`, `--strict-mode`, `--route-entry-json`, `--yes` |
| `nat-fw-lifecycle.sh delete` | **DISABLED**: never deletes. Prints the close-vs-release explanation, the console path, and a read-only impact report | `--proxy-id` (optional, enables the report), `--dry-run` |
| `nat-fw-lifecycle.sh update` | Rename / change strict mode (auto-verified) | `--proxy-id`, `--proxy-name`, `--strict-mode`, `--skip-verify` |
| `validate-cli.sh` | Check CLI and credentials; probe manual-mode VPC write permissions | `--check-permission`, `--mode auto\|manual`, `--region` (probe region) |

All scripts support `--dry-run` and `--help`. Exit codes: 0 = success, 1 = parameter error, 2 = API error.

## Regression Tests (offline)

```bash
bash tests/run_unit_tests.sh
```

Runs with **no credentials and no API calls** (helpers are driven with canned payloads and stubbed API layers) and must stay green after any script change. Every case pins a bug that shipped once, so a red result means a regression, not a flaky test. The 8 groups guard: error extraction on the failure path, quota-projection sentinels, diversion-scope consistency, manual-mode route-table/vswitch hygiene, empty-array expansion under bash 3.2, static code guards, documentation consistency, and the resource-release lockdown (R1~R4).

See [references/verification-method.md](references/verification-method.md) for detailed verification steps of live operations, and [references/acceptance-criteria.md](references/acceptance-criteria.md) for the correct/incorrect usage patterns and the acceptance checklist a change must satisfy.

## References

| Document | Contents |
|---|---|
| [references/nat-prerequisites.md](references/nat-prerequisites.md) | Creation dependencies, diversion-mode hard constraints, business impact, usage limits |
| [references/api-errors.md](references/api-errors.md) | Full error-code reference + verified API behaviors (silent successes, timeouts) |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM actions per capability, including manual-mode VPC writes and the permission probe |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification of every subcommand: expected status transitions, polling budgets, common errors |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct vs incorrect usage patterns and the acceptance checklist for changes |
