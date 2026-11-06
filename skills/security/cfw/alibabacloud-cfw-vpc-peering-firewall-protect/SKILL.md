---
name: alibabacloud-cfw-vpc-peering-firewall-protect
description: >
  Manage Alibaba Cloud Firewall (CFW) VPC boundary firewall for VPCs connected by Express Connect /
  VPC peering (对等连接): query firewalls and switch status, view detail, enable/disable the protection
  switch, assess protectable pairs and produce an enablement plan, run the creation pre-check, create
  a firewall, rename it or adjust its protected route (CIDR) tables, and read or adjust its IPS
  defense config (mode / rule group) and ACL engine mode (strict vs loose).
  Deleting/releasing is NOT supported: close the switch instead; release happens in the console.
  CEN-based VPC firewalls are out of scope.
  管理阿里云云防火墙（CFW）VPC边界防火墙（高速通道/VPC对等连接）：查询防火墙与开关状态、查看详情、
  开启/关闭防护开关、开墙评估与方案、创建预检查、创建VPC防火墙、重命名或调整防护路由（CIDR）表、
  读取或调整IPS入侵防御配置与访问控制引擎模式（严格/宽松）。不支持删除/释放防火墙，需用户在控制台
  自行操作；不含云企业网CEN类VPC防火墙。适用于VPC对等连接防火墙、及该防火墙下的IPS入侵防御引擎
  与ACL访问控制引擎（严格/宽松）等场景。
  Triggers: "对等连接防火墙", "VPC peering firewall", "VPC对等链接防火墙".
license: Apache-2.0
compatibility: >
  Requires aliyun CLI >= 3.3.3 with the CFW plugin and Vpc plugin installed.
  Scripts compatible with bash >= 3.2 (macOS default). python3 required for the
  route auto-discovery and JSON assembly.
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
| Query VPC firewall list / which peering pairs are protected | `vpc-fw-switch.sh query` with filters |
| Inspect one firewall (local/peer VPC, ENI, protected route tables) | `vpc-fw-switch.sh detail --vpc-firewall-id <id>` |
| **Which peering pairs are unprotected, and how do I protect them?** | `vpc-fw-lifecycle.sh assess --region <id>` (read-only inventory + blockers) |
| **Can THIS peering pair be protected? Give me the enablement plan** | `vpc-fw-lifecycle.sh assess --local-vpc-id <id> --local-region <id> --peer-vpc-id <id> --peer-region <id>` (adds the pre-check + route discovery + a ready-to-run plan) |
| Enable/disable protection for **specific VPC firewalls** | `vpc-fw-switch.sh enable/disable --vpc-firewall-ids "..."` (three-phase workflow below) |
| Check whether a peering pair can have a firewall created | `vpc-fw-lifecycle.sh precheck` |
| Create a VPC firewall for a peering pair | Creation workflow: assess -> `vpc-fw-lifecycle.sh create` |
| Rename a firewall / adjust the protected route (CIDR) tables | `vpc-fw-lifecycle.sh update` (built-in verification runs automatically) |
| **Read or adjust the IPS defense configuration** (defense mode, rule group, basic rules, virtual patching) | `vpc-fw-engine.sh ips --vpc-firewall-id <id>` - read-only with no write flag; see the Engine Settings workflow |
| **Read or adjust the ACL engine mode** (strict vs loose) | `vpc-fw-engine.sh acl-engine --vpc-firewall-id <id>` - read-only without `--strict-mode`; see the Engine Settings workflow |
| Delete / release a VPC firewall | **NOT SUPPORTED - releasing the resource is the user's own action.** Offer `vpc-fw-switch.sh disable` to stop protection, and point to the console (`开关 -> VPC边界防火墙 -> 对等连接 -> 删除`). `vpc-fw-lifecycle.sh delete` only prints this guidance plus a read-only impact report |

Key concept: one peering pair (a local VPC + a peer VPC connected by Express Connect or VPC peering) maps to exactly one VPC boundary firewall. The firewall must be **created** before its switch can be toggled. `FirewallSwitchStatus` `opened` means the switch is on (protecting); `closed` means off; `notconfigured` means no firewall exists for the pair yet.

> **Scope:** this skill covers the **Express Connect / VPC peering** family (`DescribeVpcFirewallList`, `ConnectSubType` = `vpc2vpc` / `vpcpeer`). CEN-based VPC firewalls use a different API family and are out of scope. It does NOT protect IPv6, `100.64.0.0/10`, cross-region/cross-account, or VPC-to-VBR traffic.

> **MANDATORY: Write Scope Boundary Rule.** The user's request defines the write scope: only the operation they asked for is in scope, plus read-only lookups. If that operation is blocked by missing state - the pair reads `notconfigured`, the engine reports `FirewallNotConfigured`, the pair is already occupied, an authorization is pending - STOP and hand the blocker back with the options, listing any prerequisite write (create the firewall, open the switch, grant the authorization) as a SEPARATE proposal that needs its own impact preview and explicit user confirmation. Never issue `CreateVpcFirewallConfigure`, `ModifyVpcFirewallSwitchStatus`, `ModifyVpcFirewallConfigure` or an engine modify as a "prerequisite", "unblock" or "make the request complete" step on your own initiative: a plan item you ticked yourself is not user confirmation, and a failed attempt (4xx) does not license trying another write path. A firewall the user never asked for costs quota, billing and route changes they never agreed to.

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
- `permission_check` = false -> credentials are invalid/expired or the identity lacks `yundun-cloudfirewall:DescribeVpcFirewallList`; check AccessKey status and refer to `references/ram-policies.md`

**Create-mode permission pre-probe:** before `assess --local-vpc-id ...` or `create` (which rely on route auto-discovery), probe the VPC READ permissions in one shot - it calls the read APIs with fake resource IDs (nothing is created) and classifies each action as `granted` / `missing` / `unknown`:
```bash
bash scripts/validate-cli.sh --check-permission --mode create [--region cn-hangzhou]
```
Check `create_mode_ready` and `missing_required_permissions`. If a read permission is missing, either grant it or pass `--local-cidr-json` / `--peer-cidr-json` explicitly to `create`.

Note: `credential_valid` only reflects whether a profile exists in `aliyun configure list`. Real credential validity is verified by `permission_check`, which calls the actual CFW business API.

Show the full installation guide:
```bash
bash scripts/validate-cli.sh --install-guide
```

After environment checks pass, ensure plugins are up-to-date:
```bash
aliyun plugin update
```

> **API Version Note:** Cloudfw and Vpc use CLI plugin mode. The API version is managed internally by the plugin (Cloudfw actual version: `2017-12-07`). Call commands using the default invocation - do **NOT** pass `--version`; the plugin rejects any external version override.

## Observability

**User-Agent template** (every `aliyun` CLI call must carry it):

```
AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-peering-firewall-protect/{session-id} skill-version/{skill-version}
```

The value is **two space-separated tokens**: the skill/session token first, then the `skill-version/{skill-version}` token. Keep the space - do not fold the version into the path.

**skill-version rule**: `{skill-version}` is read from the top-level `version` field (a non-empty string) of `references/manifest.json`. `scripts/common.sh` loads it on startup and treats it as a **hard gate** - if the manifest is missing, unreadable, or has no non-empty string `version`, the script aborts with exit code 1 **before any Alibaba Cloud API call**, so a request can never be emitted with an incomplete User-Agent. Bump `version` in the manifest on every release; do not hardcode the version anywhere else.

**session-id generation rule**: 32-character lowercase hex, generated **once per session** and reused **identically by every call** in that session, so all API calls of one session can be correlated. `scripts/common.sh` implements this on load - it reuses `SKILL_SESSION_ID` when already exported (to join an existing session), otherwise generates one from `uuidgen` and falls back to `/dev/urandom` when that binary is absent (minimal containers, including the evaluation sandbox, ship without it). If neither source yields 32 lowercase hex characters the script aborts with exit code 1 **before any Alibaba Cloud API call**, so a partial User-Agent is never emitted. It then exports `ALIBABA_CLOUD_USER_AGENT` with the template above. Both API wrappers (`call_cfw_api` / `call_vpc_api`) pass it via `--user-agent`, so scripted calls need no extra work. Any ad-hoc CLI call outside the scripts MUST add `--user-agent "$ALIBABA_CLOUD_USER_AGENT"` explicitly.

> **CLI invocation mode:** Cloudfw / Vpc run as CLI plugins that keep PascalCase API names and flags (`aliyun Cloudfw DescribeVpcFirewallList --CurrentPage 1`), and MUST NOT receive `--version`.

## RAM Policy and Permission Handling

The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`. Read `references/ram-policies.md` for the full permission list (including the two `vpc:Describe*` read permissions used by route auto-discovery).

> **Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this Skill
> 2. Guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Query VPC Firewalls

```bash
bash scripts/vpc-fw-switch.sh query [options]
```

Available filters: `--region`, `--status` (`opened`/`closed`/`notconfigured`/`configured`/`configuring`), `--vpc-id`, `--vpc-firewall-id`, `--vpc-firewall-name`, `--connect-subtype` (`vpc2vpc`/`vpcpeer`), `--peer-uid`, `--member-uid`. Each filter accepts a single value. For multi-region queries, make separate calls and merge the results.

Pagination: `--page` (default 1), `--page-size` (default 10, max 50). The list API paginates with `CurrentPage`. Check `TotalCount` to determine if more pages exist.

The response returns the raw API JSON with a `VpcFirewalls` array and `TotalCount`. Key fields per entry: `VpcFirewallId`, `VpcFirewallName`, `FirewallSwitchStatus`, `ConnectSubType`, `Bandwidth`, `RegionStatus`, `ResultCode`, `LocalVpc.VpcId/VpcName/RegionNo`, `PeerVpc.VpcId/VpcName/RegionNo`, `IpsConfig`, `AclConfig.StrictMode`.

**Status semantics** (present in a human-friendly way):

| FirewallSwitchStatus | Meaning |
|---|---|
| `opened` | Protection enabled (switch open) |
| `closed` | Protection disabled (switch closed) |
| `notconfigured` | No VPC firewall configured for this pair yet |
| `configuring` | Transitional, right after creation - poll until it settles |
| `configured` | Configured (transitional/other) |

> **MANDATORY: Table Presentation Rule**
> Whenever presenting VPC firewall query results, you MUST render them as a **Markdown table** - never dump raw JSON, and never describe the assets in prose only. This applies to every query-driven answer: asset inventory, impact previews (Phase 1), and result verifications (Phase 3).
>
> **Columns** (fixed order): `VpcFirewallId | VpcFirewallName | LocalVpc | PeerVpc | Region | Status | ConnectSubType`
>
> Rules:
> - `Status` must be shown as **Chinese/English paired semantics**, e.g. `opened（防护开启）`, `closed（防护关闭）`, `notconfigured（未配置）`.
> - For `notconfigured` rows carrying a `ResultCode` (`Unauthorized` / `RegionDisable`), append the reason - it is the key blocker clue.
> - Below the table, always add one summary line: `共 N 条 | 第 X/Y 页 | 过滤条件: ...`. If more pages exist, tell the user explicitly.
> - **Empty result is NOT silence**: if `VpcFirewalls` is empty, still output the table header plus `(无匹配记录)`, the summary line, and suggest retrying without (or with looser) filters.
>
> Template:
>
> ```
> | VpcFirewallId | VpcFirewallName | LocalVpc | PeerVpc | Region | Status | ConnectSubType |
> |---|---|---|---|---|---|---|
> | vfw-example0001 | vpc-fw-prod | vpc-example0001 | vpc-example0002 | cn-hangzhou | opened（防护开启） | vpcpeer |
>
> 共 1 条 | 第 1/1 页 | 过滤条件: status=opened
> ```

## Enable / Disable Switch Workflow

All enable/disable operations follow a three-phase workflow: **Impact Preview -> User Confirmation -> Execute -> Result Verification**. Skipping any phase may lead to unintended changes or unverified outcomes.

> **MANDATORY: Business Impact Warning**
> Opening or closing a VPC boundary firewall triggers **route re-learning that takes about 5~30 minutes** (depends on the route entry count), during which **long-lived connections suffer a second-level interruption** (short connections unaffected). In Phase 1 you MUST warn the user and recommend operating during business off-peak hours.

> **MANDATORY: Non-Interactive Execution Rule**
> Every write subcommand hard-gates without `--yes`: it exits 2 with `error_code=ConfirmationRequired`, prints the impact preview and the exact per-ID command, and calls nothing. Relay that preview to the user, get an explicit confirmation, and only then re-run the same command with `--yes`. **A confirmation you produced yourself is not a confirmation** - when the user has not replied, stop at the preview and wait.
>
> "Unconditionally" below means **never let what you saw in Phase 1 talk you out of Phase 2 and Phase 3**. It does **not** license skipping the confirmation above:
> - Phase 1 shows **0 affected firewalls** -> **still execute Phase 2 and Phase 3** once the user has confirmed. Do NOT stop.
> - Phase 1 shows all firewalls already in the desired state -> **still execute Phase 2 and Phase 3** once the user has confirmed. Do NOT stop.
> - **NEVER** terminate the workflow after Phase 1 alone once the user has confirmed.

### Phase 1: Impact Preview

Query the firewalls that will be affected and present a human-friendly table:
- **enable**: `vpc-fw-switch.sh query --status closed` (+ user's region/pair filters)
- **disable**: `vpc-fw-switch.sh query --status opened` (+ user's region/pair filters)

Summarize to the user:
- If total <= 5: list all (VpcFirewallId, VpcFirewallName, LocalVpc, PeerVpc, Region)
- If total > 5: list 3 representative examples, then summarize the rest by region

Warn: switching re-learns routes (5~30 minutes) and causes a second-level flap of long-lived connections. For **disable**, additionally warn: once closed, the east-west traffic between the two VPCs no longer passes through Cloud Firewall - access control policies and IPS on the VPC boundary stop working.

Wait for **explicit user confirmation** before proceeding to Phase 2.

### Phase 2: Execute

After the user confirms, run the switch command with the VpcFirewallIds collected in Phase 1. Running it **without** `--yes` is a safe first pass: it stops at a hard gate with `error_code=ConfirmationRequired` (exit 2), prints the affected IDs, the business impact and the exact per-ID command in `command_preview`, and calls nothing. Relay that preview, then re-run the same command with `--yes`:

```bash
bash scripts/vpc-fw-switch.sh enable --vpc-firewall-ids "vfw-example0001,vfw-example0002" --yes
bash scripts/vpc-fw-switch.sh disable --vpc-firewall-ids "vfw-example0001" --yes
```

> **MANDATORY: Idempotent Execution Rule**
> Even if Phase 1 shows all target firewalls already in the desired state (or 0 matches), you **MUST still execute** the command. Do NOT skip Phase 2 based on current status or zero-count results.

> **KNOWN API BEHAVIOR:** `ModifyVpcFirewallSwitchStatus` returns only a `RequestId`. A success response means the request was **accepted**, NOT that the switch finished. Phase 3 verification is the only reliable confirmation. See `references/api-errors.md`.

> **MANDATORY: Batch Result Rule.** The script's JSON summary derives `success` from the per-ID results: it is `true` **only** when `failed_count` is 0 and `succeeded_count` > 0. On a partial failure `success` is `false` and `note` begins with `PARTIAL FAILURE`. Report per ID from the `succeeded` / `failed` arrays - never tell the user protection is on unless that specific ID appears in `succeeded` **and** Phase 3 shows `opened`.

### Phase 3: Result Verification

Poll the firewall status to verify the operation took effect:

1. **Initial wait**: sleep 30 seconds (route re-learning is slow)
2. **Query**: `vpc-fw-switch.sh query --vpc-firewall-id <id>`
3. **Adaptive polling**: poll every 30 seconds, up to 30 minutes total
4. **Report results**:
   - All transitioned: "[OK] Done. VPC firewall switch enabled for all N firewalls."
   - Partial/still transitioning: "vfw-example0002 is still switching (route re-learning takes 5~30 minutes). Confirm the final status in the console."
   - Firewall not found after a switch call: treat as FAILED and report with the RequestId.

Expected status transitions: enable -> `closed` -> (transitional) -> `opened`; disable -> `opened` -> (transitional) -> `closed`.

> **MANDATORY: Proof-of-Write Rule.** Phase 3 verifies a write YOU issued; it is not evidence that a write happened. The only proof your call ran is its own response - the script's JSON `success` / `error_code` and the RequestId it relays. A later read-back that happens to equal the target state proves nothing about who changed it: on a shared account another task may have created, renamed or released the same resource minutes earlier. If you did not issue the write call, say so - never report "created / renamed / switched" from a read-back alone, and never narrate a duration or a RequestId for a call you did not make.

## Assessment (run BEFORE creation)

Assessment happens in **two stages**: a region-wide inventory to pick the peering pair, then a deep single-pair evaluation that produces the enablement plan.

### Stage 1 - inventory (pick the pair)

When the user asks to enable/configure VPC firewall protection - especially without specifying a pair - ALWAYS run the read-only assessment first and present its result as tables:

```bash
bash scripts/vpc-fw-lifecycle.sh assess --region cn-hangzhou
```

The report returns `configured` (existing firewalls with their switch status) and `protectable` (peering pairs with `notconfigured` status, each with `blockers` derived from `ResultCode` / `RegionStatus`: unauthorized VPC, unsupported region).

### Stage 2 - enablement plan (immediately after the pair is chosen)

> **MANDATORY: Plan-First Rule.** As soon as the target pair is known, run the single-pair evaluation and present ONE complete plan. Do NOT ask the name or the switch state as separate sequential questions before the evaluation - decide them from the plan, then confirm once.

```bash
bash scripts/vpc-fw-lifecycle.sh assess --local-vpc-id vpc-example0001 --local-region cn-hangzhou \
    --peer-vpc-id vpc-example0002 --peer-region cn-hangzhou
```

This adds the **pre-check** (`precheck.items`, each with `name` / `display` / `status` / `suggestion`, and `failed_items`), the **auto-discovered route tables** (`discovered_routes.local` / `.peer` / `.masked32`), `actionable`, `blockers`, `risks`, `business_impact`, `estimated_duration`, the `command` template, and `post_steps`. Present every pre-check item using its `display` label.

The `command` template **deliberately omits `--yes`** - creation is a write operation and must be confirmed first. Two fields make the go/no-go explicit: when `actionable` is `false`, `do_not_execute` is `true` and `resolve_first` lists the blockers to clear before re-assessing; when `actionable` is `true`, `do_not_execute` is `false` and `resolve_first` is empty.

Present the plan as a compact table (discovered routes, blockers, risks, duration, business impact), then ask for confirmation with a SINGLE question bundling the parameters still needing a decision (name / switch after creation). Skip straight to remediation when `blockers` is non-empty - never offer to create.

> **MANDATORY: Resource Identity Rule (applies to EVERY clarification question).**
> Whenever a question asks the user to pick a target resource (peering pair, VPC firewall, VPC, etc.), each option MUST contain the resource's **FULL ID and FULL name** - never truncated or ellipsized (e.g. `vpc-example0001 (prod-vpc)`, NOT `vpc-exam...`).
> - Recommended label format: `<full-ID>（<name>）`. Put the full ID at the very beginning of the option description too, since some UIs collapse labels to A/B/C.
> - Keep option descriptions minimal: identity first, then at most one line of decision-relevant facts. Secondary details belong in the summary table in the message body.

> **MANDATORY: Assessment Freshness Rule.** The assess report is a **point-in-time snapshot**: the user can change the environment in the console at any moment (add/remove routes, change authorization, delete the peering connection), silently invalidating a previous report. If ANY console change happened (or is suspected) since the assess run, **re-run `assess` before proceeding**. `create` re-reads the current state at execution time.

The assessment is purely read-only; missing VPC read permissions degrade route discovery to a note instead of failing.

## Creation Workflow

Use when the user wants to protect a peering pair that has no VPC firewall yet.

> **MANDATORY: Clarification Rule.** Every required parameter (`--local-vpc-id`, `--local-region`, `--peer-vpc-id`, `--peer-region`, `--vpc-firewall-name`, `--firewall-switch`) MUST come from the user's request or the assessment. When any is missing or ambiguous, STOP and ask. NEVER default a value from the documentation examples - examples are syntax illustrations only.

1. **Assess in two stages** (see above): Stage 1 inventory -> user picks the pair -> Stage 2 produces the plan (includes the pre-check + route discovery). Skip only if the user already provided the full pair identity AND confirmed the routes.
2. **Read the plan instead of re-running the checks**: `plan.actionable` and `precheck.failed_items` cover the pre-check, `discovered_routes` supplies the two CIDR table lists, and `command` is the creation command **template**. Check `do_not_execute` first - if it is `true`, stop and work through `resolve_first`; never run the command. A blocking item that may clear on its own (a release in progress, an authorization pending) is still a blocker: hand it and the options back to the user - including "wait for it to clear, then create" - and let the user pick. Never clear a blocker by issuing a different write (toggle a switch, rename or re-scope the existing instance) on your own initiative - see the Write Scope Boundary Rule. Never poll the account on your own initiative and then continue the write flow as if the pre-check had passed. Otherwise append `--yes` only after step 3's confirmation.
3. **Impact preview & confirm**: explain that creation takes about **5 minutes** and has **no business impact** while the switch stays closed (default). Ask for the name (`--vpc-firewall-name`) and whether to open immediately (`--firewall-switch open|close`, default `close`) if not given. Running `create` without `--yes` is a safe first pass: it stops at a hard gate with `error_code=ConfirmationRequired` (exit 2), prints the exact command in `command_preview`, and sends no API request. Relay that preview, then re-run with `--yes` only after the user confirms.
4. **Create** (routes auto-discovered):
   ```bash
   bash scripts/vpc-fw-lifecycle.sh create \
     --local-vpc-id vpc-example0001 --local-region cn-hangzhou \
     --peer-vpc-id vpc-example0002 --peer-region cn-hangzhou \
     --vpc-firewall-name vpc-fw-prod --firewall-switch close --yes
   ```
   When auto-discovery is unavailable (missing VPC read permission), pass the two lists explicitly with `--local-cidr-json` / `--peer-cidr-json` (format in `references/vpc-prerequisites.md`). The command runs the pre-check first and aborts on any blocking item unless `--skip-precheck` is passed after the user accepts the risk.
5. **Verify**: poll `vpc-fw-switch.sh query --vpc-firewall-id <id>` every 30 seconds until the firewall appears with status `closed` (or `opened` if created open). Creation takes ~5 minutes; opening takes 5~30 minutes.
6. **Optional enable**: creation leaves the switch closed by default. If the user also wants protection active, run the Enable/Disable Switch Workflow afterwards (with the flap warning).

> **Note:** Cloud Firewall auto-creates the diversion route entries (remarked `Created by cloud firewall. Do not modify or delete it.`) and the `Cloud_Firewall_Security_Group` inside both VPCs. Never delete or modify them while the firewall exists. IPS defense settings and the ACL engine mode are NOT parameters of create/update - adjust them afterwards with `vpc-fw-engine.sh` (see Engine Settings below).

## Update (Rename / Protected CIDRs)

```bash
bash scripts/vpc-fw-lifecycle.sh update --vpc-firewall-id vfw-example0001 --vpc-firewall-name <name>
```

`ModifyVpcFirewallConfigure` requires the name AND both CIDR table lists. When you only rename, the script reads the current name and both route tables from `DescribeVpcFirewallDetail` and passes them through unchanged. To adjust the protected CIDRs, pass `--local-cidr-json` / `--peer-cidr-json`.

> **MANDATORY: Confirmation gate.** `update` is a write. Run it first WITHOUT `--yes`: it stops with `error_code=ConfirmationRequired` (exit 2), prints the resolved name, both CIDR table lists and the exact command in `command_preview`, and calls nothing. Show that preview, get an explicit confirmation, then re-run the same command with `--yes`. `--dry-run` prints the command and changes nothing. Never rename or re-scope an existing firewall as a workaround for a create that the pre-check blocked - report the blocker instead.

**Built-in verification (automatic):** because the modify API returns only a RequestId, the script re-reads the firewall via `DescribeVpcFirewallList` (up to 3 tries) and fails with `VerifyFailed` (exit 2) unless the live name matches. Use `--skip-verify` only when the verifying API is unavailable.

## Engine Settings (IPS Defense + ACL Engine Mode)

Two protection-strength settings live OUTSIDE create/update, behind their own APIs. Both are per-firewall, and both stay read-only until a write flag is passed.

```bash
# Read the current IPS defense configuration
bash scripts/vpc-fw-engine.sh ips --vpc-firewall-id vfw-example0001
# Read the current ACL engine mode
bash scripts/vpc-fw-engine.sh acl-engine --vpc-firewall-id vfw-example0001
```

Console labels for the same settings: `入侵防御` (IPS defense) and `访问控制 -> 引擎模式` (ACL engine mode).

| Setting | Flag | Values | Console label |
|---|---|---|---|
| IPS defense mode | `--run-mode` | `0` observe / `1` block | `防御模式`: `观察模式` / `拦截模式` |
| IPS rule group | `--rule-class` | `1` loose / `2` medium / `3` strict (`0` = not applicable, observe mode only) | `规则组`: `宽松` / `中等` / `严格` |
| Basic rules | `--basic-rules` | `0` off / `1` on | `基础规则` |
| Virtual patching | `--enable-all-patch` | `0` off / `1` on | `虚拟补丁` |
| ACL engine mode | `--strict-mode` | `0` loose / `1` strict | `引擎模式`: `宽松模式` / `严格模式` |

> **MANDATORY: Same three-phase workflow as the switch.** Every engine write follows Impact Preview -> explicit user confirmation -> execute -> read-back verification. Run the command first WITHOUT `--yes`: it prints the current -> target diff and exits 2 with `ConfirmationRequired` plus the exact command. Show that diff to the user, and only after an explicit confirmation re-run the same command with `--yes`. `--dry-run` prints the command and changes nothing.

> **MANDATORY: Downgrade Disclosure.** When a change weakens protection - `run-mode` 1 to 0, a lower `rule-class`, either capability 1 to 0, or `strict-mode` 1 to 0 - the script logs `PROTECTION DOWNGRADE`. Relay that to the user in plain language BEFORE asking for confirmation, and recommend an off-peak window. For `strict-mode` 1 to 0 state the concrete consequence: in loose mode, traffic from unrecognized applications or domains passes without further policy matching, so deny policies aimed at unknown traffic stop applying.

> **MANDATORY: No Silent Field Reset.** `run-mode`, `basic-rules` and `enable-all-patch` are REQUIRED by the IPS modify API; omitting one is a CLI error, not a preserved value. The script fills every one of them you omit from a read-back of the current values, so passing `--run-mode 0` alone never resets the two capability switches. Never hand-build the CLI call with only the field the user asked about.

> **MANDATORY: `--rule-class` only when the user asked for the rule group.** The service couples `RuleClass` to `RunMode` and does NOT simply store what you send: in observe mode (`run-mode 0`) it always stores `0` ("not applicable") whatever value was passed, and in block mode (`run-mode 1`) an explicit `0` is normalized to `3` (strict) while an omitted flag keeps the current group. So a `--rule-class` echoed from a stale read-back can silently move the rule group. The script therefore sends the flag only when you passed it, derives the expected value from the coupling, and reports `rule_class_derived_by_service: true` when the stored value will differ from the requested one - relay that to the user instead of calling it a failure.

**Prerequisite - the firewall must be configured.** A firewall whose `FirewallSwitchStatus` is `notconfigured` has no engine instance, and both write APIs reject its ID with `ErrorParametersFirewallId`. The script therefore refuses the write up front with `FirewallNotConfigured` and points to the create workflow. Reads still work, but the answer carries `"configured": false` because those values are the account defaults rather than a live instance - say so explicitly instead of presenting them as the current setting. That refusal is the correct END of this workflow, not a to-do list: "points to the create workflow" means offering creation to the user as a separately confirmed proposal under the Write Scope Boundary Rule - never creating the firewall or toggling its switch yourself to unblock the engine write.

**Verification is automatic.** Both modify APIs return only a `RequestId`. The script re-reads the value, up to 3 tries, and fails with `VerifyFailed` (exit 2) unless the live value equals the requested one. Never report success from the modify response alone.

> **CLI naming caveat:** aliyun CLI 3.4.x registers the two IPS APIs in kebab-case only (`modify-vpc-firewall-default-ips-config`), which then also requires kebab-case flags, while `ModifyVpcFirewallAclEngineMode` and `DescribeVpcFirewallList` are PascalCase. Use the scripts instead of hand-built calls; details in `references/api-errors.md`.

## Stopping Protection: Close vs Release (deletion is out of scope)

> **MANDATORY: No Resource Release Rule.** This Skill NEVER deletes a VPC boundary firewall.
> `DeleteVpcFirewallConfigure` is not called anywhere, and `--yes` does not override this.
> When a user asks to "delete / remove / `释放` / `下线`" a VPC firewall, FIRST clarify which of the two they mean:

| | Close protection (supported) | Release the resource (NOT supported here) |
|---|---|---|
| Command | `vpc-fw-switch.sh disable --vpc-firewall-ids <id>` | Console: `开关 -> VPC边界防火墙 -> 对等连接 -> 删除` |
| API | `ModifyVpcFirewallSwitchStatus --FirewallSwitch close` | `DeleteVpcFirewallConfigure` (never called by this Skill) |
| Firewall instance | **Kept** - can be re-enabled anytime | **Destroyed**, irreversible |
| Authorization quota | Still occupied | Freed |
| Business impact | 5~30 min route re-learning with a second-level flap | Same flap, plus close+delete together when still enabled |

In most cases "stop the VPC firewall" means **close**, which is reversible. Recommend that first. When the user genuinely wants the resource released, run the read-only helper for the console operation, then hand it over:

```bash
bash scripts/vpc-fw-lifecycle.sh delete --vpc-firewall-id vfw-example0001   # refuses; prints guidance + impact report
```

The script's `release_guidance.how` is an **English gloss** (script output must stay ASCII). When relaying it to the user, present the console path with its **localized labels** - `开关 -> VPC边界防火墙 -> 对等连接 -> 删除` - because that is what the user actually sees in the console.

Do NOT attempt to work around this restriction with raw CLI calls - see `references/acceptance-criteria.md`.

## Multi-Account Operations

`query`, `enable`, `disable`, `assess`, `precheck`, `create`, `update`, and both `vpc-fw-engine.sh` subcommands all support `--member-uid <uid>` to operate a member account's firewalls under a management account. When the user manages multiple accounts, ask which account to operate on.

## Handle Errors

When an API call fails, the scripts output a JSON error with `error_code` and `error_message`, plus diagnostic guidance to stderr. Common scenarios:

- `ErrorVpcFirewallExist`: a firewall already exists for the pair - query it and use the switch workflow instead of creating.
- `ErrorFirewallCannotOpen` / `ErrorVpcFirewall.CannotOpen`: the firewall is transitioning - wait 5~30 minutes and retry.
- `ErrorDestCidrEmpty` / `ErrorRouteTableIdNotFound`: the route lists are empty or stale - re-run `assess` to re-discover, or pass corrected `--*-cidr-json`.
- `ErrorCenVpcEcConflict`: a CEN VPC conflicts with this Express Connect VPC - a pair can be protected by only one connection type.
- `ErrorFirewallQuotaNotEmpty` / `ErrorGeneralInstanceSpecFull`: purchase more VPC firewall quota or upgrade the CFW spec.
- `ErrorParametersFirewallId` / `FirewallNotConfigured`: the firewall has never been configured, so it has no IPS/ACL engine instance - create and open it first, then tune the engine.
- `ConfirmationRequired`: a write was requested without `--yes`. Show the printed impact preview to the user, get an explicit confirmation, then re-run the same command with `--yes`.
- `NoPermission` / `Forbidden.RAM`: run `validate-cli.sh` and check `references/ram-policies.md`.

For the full error code reference (including verified API behaviors), read `references/api-errors.md`. For creation prerequisites and business impact details, read `references/vpc-prerequisites.md`.

## Script Reference

| Script | Purpose | Key Params |
|---|---|---|
| `vpc-fw-switch.sh query` | Query VPC firewalls and switch status | `--region`, `--status`, `--vpc-id`, `--vpc-firewall-id`, `--vpc-firewall-name`, `--connect-subtype`, `--peer-uid`, `--member-uid`, `--page`, `--page-size` |
| `vpc-fw-switch.sh detail` | Query one firewall's detail (local/peer VPC, ENI, route tables) | `--vpc-firewall-id` (required), `--local-vpc-id`, `--peer-vpc-id` |
| `vpc-fw-switch.sh enable` | Enable protection switch; stops at a confirmation gate until `--yes` is given | `--vpc-firewall-ids` (required, comma-separated), `--member-uid`, `--yes` |
| `vpc-fw-switch.sh disable` | Disable protection switch; stops at a confirmation gate until `--yes` is given | `--vpc-firewall-ids` (required, comma-separated), `--member-uid`, `--yes` |
| `vpc-fw-lifecycle.sh assess` | Read-only inventory; with a pair also the pre-check + enablement `plan` | `--region`, or `--local-vpc-id`+`--local-region`+`--peer-vpc-id`+`--peer-region`, `--member-uid` |
| `vpc-fw-lifecycle.sh precheck` | Local validation of one peering pair | `--local-vpc-id`, `--local-region`, `--peer-vpc-id`, `--peer-region` (all required) |
| `vpc-fw-lifecycle.sh create` | Create a VPC boundary firewall (routes auto-discovered) | `--local-vpc-id`, `--local-region`, `--peer-vpc-id`, `--peer-region`, `--vpc-firewall-name`, `--firewall-switch` (required), `--local-cidr-json`, `--peer-cidr-json`, `--skip-precheck`, `--yes` |
| `vpc-fw-lifecycle.sh update` | Rename / adjust protected CIDRs (auto-verified); stops at a confirmation gate until `--yes` is given | `--vpc-firewall-id` (required), `--vpc-firewall-name`, `--local-cidr-json`, `--peer-cidr-json`, `--skip-verify`, `--yes` |
| `vpc-fw-lifecycle.sh delete` | **DISABLED**: never deletes. Prints the close-vs-release guidance + a read-only impact report | `--vpc-firewall-id` (optional, enables the report) |
| `vpc-fw-engine.sh ips` | Read / adjust the IPS defense config; read-only until a write flag is given | `--vpc-firewall-id` (required), `--run-mode`, `--rule-class`, `--basic-rules`, `--enable-all-patch`, `--member-uid`, `--yes` |
| `vpc-fw-engine.sh acl-engine` | Read / adjust the ACL engine mode; read-only until `--strict-mode` is given | `--vpc-firewall-id` (required), `--strict-mode`, `--member-uid`, `--yes` |
| `validate-cli.sh` | Check CLI and credentials; probe create-mode VPC read permissions | `--check-permission`, `--mode query\|create`, `--region`, `--install-guide` |

All scripts support `--dry-run` and `--help`. Exit codes: 0 = success, 1 = parameter error, 2 = API/verification error.

`--dry-run` never writes, but it is not always offline. `update --dry-run` still issues one **read-only** `DescribeVpcFirewallDetail` call to read back whichever of the three required fields you omitted - pass `--vpc-firewall-name` together with `--local-cidr-json` and `--peer-cidr-json` for a fully offline preview (zero API calls). Both `vpc-fw-engine.sh` subcommands always issue read-only calls first, because the impact preview and the omitted-field fill-in are computed from the live values; the `--dry-run` output is the exact modify command that `--yes` would run.

## Regression Tests (offline)

```bash
bash tests/run_unit_tests.sh
```

Runs with **no credentials and no API calls** (helpers are driven with canned payloads and stubbed API layers) and must stay green after any script change. The groups guard: error extraction on the failure path, the peering-route filter (next-hop type + /32 detection), the detail->CIDR extraction, the list summary, the pre-check verdict, empty-array expansion under bash 3.2, static code guards, documentation consistency, the resource-release lockdown (R1~R4), the platform validation rules, the engine subcommands and their write gates (N-series), the create/switch write gates (W-series), and JSON escaping of quoted user input. The engine and write-gate groups run the real scripts against `tests/mocks/aliyun` on PATH, so a mocked call log - not a crashed assertion - is what proves nothing was written.

## References

| Document | Contents |
|---|---|
| [references/vpc-prerequisites.md](references/vpc-prerequisites.md) | Creation dependencies, business impact, route learning, CIDR table list format, usage limits |
| [references/api-errors.md](references/api-errors.md) | Full error-code reference + verified API behaviors (RequestId-only responses, pagination, /32 masks) |
| [references/ram-policies.md](references/ram-policies.md) | Required RAM actions per capability, including the VPC read permissions and the create-mode probe |
| [references/verification-method.md](references/verification-method.md) | Step-by-step verification of every subcommand: expected transitions, polling budgets, common errors |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Correct vs incorrect usage patterns and the acceptance checklist for changes |
