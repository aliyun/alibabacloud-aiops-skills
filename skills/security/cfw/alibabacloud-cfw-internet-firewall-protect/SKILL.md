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
  Scripts compatible with bash >= 3.2 (macOS default).
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
| Query asset protection status, list assets, check which IPs are protected/unprotected | `fw-switch.sh query` with filters |
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

1. **Query**: Run `fw-switch.sh query` with available filters (status, region, resource type). Paginate through results if `total_count` exceeds page size.
2. **Filter**: From the returned `Assets` array, filter by the user's condition (instance name match, specific attributes, etc.). The key fields in each asset: `Name` (instance name), `InternetAddress` (public IP), `IntranetAddress` (private IP), `ProtectStatus`, `ResourceType`, `RegionID`, `BindInstanceId`, `BindInstanceName`.
3. **Impact Preview (Phase 1)**: Present the matched assets summary to the user for confirmation (follow the summary format in "Protection Switch Workflow").
4. **Execute (Phase 2)**: Collect the `InternetAddress` values from matched assets into a comma-separated list, then call `fw-switch.sh enable/disable --ips "ip1,ip2,..."`.
5. **Verify (Phase 3)**: Poll status to confirm the operation completed (follow the polling strategy in "Protection Switch Workflow").

**Edge Case Handling for Step 2 (Filter Results):**

| Filter Result | Phase 2 Action |
|---|---|
| Matched assets exist, some/all have ProtectStatus=closed | `enable --ips "all_matched_ips"` (include both open and closed — API is idempotent) |
| Matched assets exist, ALL already ProtectStatus=open | `enable --ips "all_matched_ips"` (still call — idempotent rule) |
| **Zero assets match the filter condition** | Use the user's original broader dimensions instead: `enable --regions <region> --resource-types <type>` or `enable --ip-version <ver>`. If no broader dimension is available, call `enable-all --yes` as fallback. **Never skip Phase 2.** |

This pattern applies to any condition-based operation — name matching, tag filtering, status-based bulk operations, etc.

## Check CLI Environment

Before any operation, validate the CLI environment:
```bash
bash scripts/validate-cli.sh --check-permission
```

Check results and remediate:
- `cli_installed` = false → run `--install-guide` for installation instructions
- `cli_version_ok` = false → CLI version below 3.3.3, reinstall or update
- `auto_plugin_install` = false → run `aliyun configure set --auto-plugin-install true`
- `credential_valid` = false → no profile configured, run `aliyun configure` to add one
- `permission_check` = false → credentials are invalid/expired or the identity lacks `yundun-cloudfirewall:DescribeAssetList`; check AccessKey status and refer to `references/ram-policies.md`

Note: `credential_valid` only reflects whether a profile exists in `aliyun configure list`. Real credential validity is verified by `permission_check`, which calls the actual CFW business API — invalid/expired AccessKey will fail there.

Show full installation guide:
```bash
bash scripts/validate-cli.sh --install-guide
```

After environment checks pass, ensure plugins are up-to-date:
```bash
aliyun plugin update
```

> **API Version Note:** Cloudfw uses CLI plugin mode (`aliyun-cli-cloudfw`). The API version is managed internally by the plugin (actual version: `2017-12-07`). Call CFW commands using the default invocation — do **NOT** pass `--version`. The plugin rejects any external version override and will error with `unchecked version`. The `call_cfw_api` function in `common.sh` is designed accordingly and does not include `--version`.

## AI-Mode Lifecycle

Before any CLI invocation, enable AI-mode:

```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-internet-firewall-protect"
```

Before delivering the final response (success, failure, error, or user cancellation), always disable AI-mode:

```bash
aliyun configure ai-mode disable
```

AI-mode is only for Agent Skill execution and MUST NOT remain enabled after the skill stops running.

## RAM Policy and Permission Handling

The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`. Read `references/ram-policies.md` for the full permission list.

> **Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this Skill
> 2. Guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Query Assets

```bash
bash scripts/fw-switch.sh query [options]
```

Available filters: `--region`, `--status` (open/closed/opening/closing), `--resource-type`, `--search` (IP or instance ID), `--ip-version` (4/6), `--member-uid`. Each filter accepts a single value.

For multi-region or multi-resource-type queries, the DescribeAssetList API only supports single-value filters. Make separate calls per region or per resource type in parallel, then merge the results. Example: to query both cn-hangzhou and cn-beijing EcsPublicIP assets, call `fw-switch.sh query --region cn-hangzhou --resource-type EcsPublicIP` and `fw-switch.sh query --region cn-beijing --resource-type EcsPublicIP` separately.

Pagination: `--page` (default 1), `--page-size` (default 10). Check `TotalCount` in the response to determine if more pages exist.

The response returns the raw API JSON with an `Assets` array. Each asset contains: `InternetAddress`, `IntranetAddress`, `ProtectStatus`, `ResourceType`, `RegionID`, `Name`, `BindInstanceId`, `BindInstanceName`, `ResourceInstanceId`, `IpVersion`, `MemberUid`.

Present results to the user in a readable format. For `ProtectStatus`: `open` = protected, `closed` = unprotected, `opening` = enabling, `closing` = disabling.

## Enable / Disable Protection Workflow

All enable/disable/enable-all/disable-all operations follow a three-phase workflow: **Impact Preview → User Confirmation → Execute → Result Verification**. Skipping any phase may lead to unintended changes or unverified outcomes.

> **⚠️ MANDATORY: Non-Interactive Execution Rule**
> When running as an Agent (non-interactive mode), `--yes` is implicit user confirmation. You **MUST** complete ALL three phases **unconditionally**:
> - Phase 1 shows **0 affected assets** → **still execute Phase 2 and Phase 3**. Do NOT stop.
> - Phase 1 shows all assets already in desired state → **still execute Phase 2 and Phase 3**. Do NOT stop.
> - **NEVER** terminate the workflow after Phase 1 alone. NEVER output "no action needed" without completing Phase 2+3.
> - The sequence Phase 1 → Phase 2 → Phase 3 is **unconditionally mandatory** in every execution path, regardless of Phase 1 results.

### Phase 1: Impact Preview

Before executing, query the assets that will be affected and present a human-friendly summary:

- **enable** operation: query `--status closed` + same filter dimensions to show assets that will gain protection
- **disable** operation: query `--status open` + same filter dimensions to show assets that will lose protection
- **enable-all**: query `--status closed` to show all currently unprotected assets
- **disable-all**: query `--status open` to show all currently protected assets

Use `--page-size 50` for the preview query. If `TotalCount` exceeds one page, paginate to collect all data for accurate statistics.

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

Wait for **explicit user confirmation** before proceeding to Phase 2.

### Phase 2: Execute

After user confirms, run the actual enable/disable command. If using a condition-based IP list from the preview query, pass the collected IPs via `--ips`.

> **⚠️ MANDATORY: Idempotent Execution Rule**
> Even if Phase 1 shows all target assets are already in the desired state (e.g., all `open` when enabling, or 0 unprotected assets found), you **MUST still execute** the enable/disable command. The API is idempotent — calling it on already-protected assets is safe and returns success. Do NOT skip Phase 2 based on current status or zero-count results.
>
> Examples of WRONG behavior:
> - "All assets are already protected, no action needed" → WRONG, must still call the API
> - "No unprotected assets found, skipping execution" → WRONG, must still call the API

### Phase 3: Result Verification

After execution, poll the asset status to verify the operation took effect:

1. **Initial wait**: sleep 5 seconds
2. **Query**: Run `fw-switch.sh query` with the same filters, check if assets transitioned to the expected status
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

At least one filter dimension is required. They can be combined freely:
```bash
# Single dimension
bash scripts/fw-switch.sh enable --ips "1.2.3.4,5.6.7.8"
bash scripts/fw-switch.sh enable --ip-version 6

# Combined dimensions
bash scripts/fw-switch.sh enable --regions "cn-beijing" --resource-types "EcsPublicIP" --ip-version 4
```

Use `--dry-run` to preview the CLI command before execution. This is recommended when the user provides many IPs or combined filters, so they can verify the parameters.

Read `references/resource-types.md` for the complete list of valid resource type values.

### All Public IPs

```bash
bash scripts/fw-switch.sh enable-all --yes [--instance-id <id>]
bash scripts/fw-switch.sh disable-all --yes [--instance-id <id>]
```

These operations affect every public IP under the account. In non-interactive (Agent) mode, `--yes` is treated as implicit user confirmation — do NOT wait for explicit user input before passing it.

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

Use `--dry-run` to preview the merged config before applying. The `--yes` flag is required for execution.

## Multi-Account Operations

All operations support `--member-uid <uid>` to operate on a member account's assets. When the user manages multiple accounts under a management account, ask which account they want to operate on and pass the member UID.

## Handle Errors

When an API call fails, the scripts output a JSON error with `error_code` and `error_message`, plus diagnostic guidance to stderr. Common scenarios:

- `ErrorInstanceOpenIpNumExceed` / `ErrorGeneralInstanceSpecFull`: protection quota or instance spec reached the limit — suggest upgrading the CFW edition.
- `ErrorBandwidthPenalty`: bandwidth overuse enforcement — advise waiting or contacting support.
- `ErrorInstanceStatusNotNormal`: instance may be unpaid or abnormal — check CFW console.
- `ErrorParamsNotEnough`: at least one filter dimension is required for enable/disable.
- `ErrorAuthentication` / `NoPermission`: credential or permission issue — run `validate-cli.sh` and check `references/ram-policies.md`.

For the full error code reference, read `references/api-errors.md`.

## Script Reference

| Script | Purpose | Key Params |
|---|---|---|
| `fw-switch.sh query` | Query assets and protection status | `--region`, `--status`, `--resource-type`, `--search`, `--ip-version`, `--member-uid`, `--new-resource-tag`, `--page`, `--page-size` |
| `fw-switch.sh enable` | Enable protection (flexible filters) | `--ips`, `--regions`, `--resource-types`, `--ip-version`, `--member-uid` |
| `fw-switch.sh disable` | Disable protection (flexible filters) | same as enable |
| `fw-switch.sh enable-all` | Enable ALL public IP protection | `--instance-id`, `--yes` |
| `fw-switch.sh disable-all` | Disable ALL public IP protection | `--instance-id`, `--yes` |
| `auto-protect.sh query` | Query auto-protection config | (none) |
| `auto-protect.sh modify` | Modify auto-protection config | `--enable`, `--disable`, `--config`, `--region`, `--yes` |
| `validate-cli.sh` | Check CLI and credentials | `--check-permission` |

All scripts support `--dry-run` and `--help`. Exit codes: 0 = success, 1 = parameter error, 2 = API error.
