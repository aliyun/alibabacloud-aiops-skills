---
name: alibabacloud-csas-user-device-ops
description: >
  Use this skill when users ask about SASE terminal device management, user account
  queries, inactive device analysis, or device locking on Alibaba Cloud SASE
  (product code: csas). Trigger scenarios: "查下哪些设备长期离线", "某部门有多少
  终端设备", "锁定闲置设备", "查看用户被授权了哪些应用".
  Capabilities: flexible device querying with 20+ filters (department, device type,
  OS, SASE feature status, etc.), user listing, user application authorization
  queries, inactive device analysis, and locking inactive devices.
  Deletion or irreversible operations are NOT supported — users are guided to the
  SASE console.
  当用户询问 SASE 终端设备管理、用户账号查询、非活跃设备分析、设备锁定时使用此 Skill。
  支持灵活的设备条件组合查询（20+ 筛选项）、用户列表查询、应用授权查询、非活跃设备分析、
  锁定非活跃终端。不支持删除等不可逆操作。
  注意：当前不支持用户活跃度分析（API 不提供用户最后活跃时间，设备绑定关系会变更）。
license: Apache-2.0
compatibility: >
  Requires Aliyun CLI (aliyun) >= 3.3.3 with csas plugin.
  Scripts compatible with bash >= 3.2 (macOS default).
  Compatible engines: qwen-code, qoder, openclaw.
metadata:
  domain: aiops
  owner: sase-team
allowed-tools: Bash Read
---

## Pre-checks

**Aliyun CLI >= 3.3.3 required**

```bash
aliyun version
```

If not installed or version too low, see `references/cli-installation-guide.md`.

**Plugin setup (MUST run before first use)**

```bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
```

**AI-Mode Lifecycle (MUST follow)**

At the START of workflow (before any CLI invocation):
```bash
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-csas-user-device-ops"
```

At EVERY exit point (success, failure, error, cancellation, including after every write operation completes):
```bash
aliyun configure ai-mode disable
```

**[MUST]** Run `ai-mode disable` even when the operation succeeds. It is part of the success path, not just the error path.

## Credential Verification

> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values
> - **NEVER** ask users to input AK/SK in conversation
> - **ONLY** use `aliyun configure list` to check credential status

```bash
aliyun configure list
```

If no valid profile exists, STOP. Guide user to configure credentials outside this session.

## RAM Policy & Permission Handling

Required permissions are listed in `references/ram-policies.md`.

> **[MUST] Permission Failure Handling:** When any command fails due to permission errors (HTTP 403, "AccessDenied", "Forbidden", "no permission", or similar):
> 1. STOP execution immediately. Do NOT retry blindly.
> 2. Identify the failing API from the error message (e.g. `csas:ListUserDevices`, `csas:UpdateUserDevicesStatus`).
> 3. Tell the user the exact RAM Action that failed and offer two paths:
>    - **Quick path:** Attach the system policy `AliyunCSASFullAccess` to the RAM user/role (covers all CSAS operations).
>    - **Minimal path:** Add only the specific failing Action(s) to a custom policy. See `references/ram-policies.md` for the minimal policy template.
> 4. Pause and wait until the user confirms permissions have been granted.
> 5. After confirmation, retry the failed operation.

**Permission error message template:**
> "Permission denied calling `csas:<ApiName>`. Please grant either `AliyunCSASFullAccess` (system policy, covers all) or add `csas:<ApiName>` to a custom RAM policy. See `references/ram-policies.md` for details. Reply 'done' after granting and I will retry."

## Operation Routing

Match user intent to the execution path:

| User Intent | Execution |
|---|---|
| Query/filter devices (any condition combo) | `aliyun csas list-user-devices` with params |
| Query user list (by department, status, name) | `aliyun csas list-users` with params |
| Check what apps a user can access | `aliyun csas list-user-applications` |
| Get single device detail | `aliyun csas get-user-device` |
| Check IDP identity source config | `aliyun csas get-active-idp-config` |
| Query user groups | `aliyun csas list-user-groups` |
| Analyze inactive devices | `bash scripts/inactive-analysis.sh` |
| Lock inactive devices | `bash scripts/cleanup-inactive.sh` |
| Delete user accounts or devices | **NOT supported** — guide to SASE console |

**Example query translations:**

- "Show devices in QA dept running macOS with DLP disabled" →
  `aliyun csas list-user-devices --department QA --device-types macOS --dlp-statuses Disabled --pager`
- "Which devices are personal and long-term offline" →
  `aliyun csas list-user-devices --device-belong Personal --device-statuses LongTermOffline --pager`
- "What internal apps is a user authorized to access" →
  `aliyun csas list-user-applications --sase-user-id <ID> --current-page 1 --page-size 100`
- "How many Windows devices are online" →
  `aliyun csas list-user-devices --device-types Windows --device-statuses Online --current-page 1 --page-size 1` (check TotalNum)

## Direct CLI Commands

All queries use `aliyun csas` plugin mode directly. Use `--pager` to auto-paginate full results.
Full parameter details: see `references/api-reference.md`.

### Parameter Validation Rules

**[MUST] Validate parameters before calling API to avoid InvalidParameter errors:**

Source: `aliyun csas <command> --help`

| Parameter | Constraint | Example | Source |
|---|---|---|---|
| `--current-page` | int, 1~10000 | `1` | CLI help |
| `--page-size` | int, 1~500 (list-user-applications: 1~100) | `100` | CLI help |
| `--device-action` | enum: `Locked` `Lost` `Unbound` `Unlocked` `Found` | `Locked` | CLI help |
| `--device-statuses` | enum list | `Online LongTermOffline` | CLI help |
| `--device-types` | enum list | `Windows macOS` | CLI help |
| `--device-belong` | enum: `Personal` `Company` | `Company` | CLI help |
| `--sort-by` | enum: `Username` `AppVersion` `UpdateTime` | `UpdateTime` | CLI help |
| `--status` (list-users) | enum: `Enabled` `Disabled` | `Enabled` | CLI help |
| `--dlp-statuses` | enum list: `Enabled` `Disabled` `Unprovisioned` `Unauthorized` | `Disabled Unprovisioned` | CLI help |
| `--pa-statuses` | enum list: `Enabled` `Disabled` `Unprovisioned` | `Enabled` | CLI help |
| `--ia-statuses` | enum list: `Enabled` `Disabled` `Unprovisioned` | `Disabled` | CLI help |
| `--nac-statuses` | enum list: `Enabled` `Disabled` `Unprovisioned` | `Unprovisioned` | CLI help |
| `--sase-user-id` | From API response `SaseUserId` field | `su_2e10e16a****0566abea4ce6` | Observed |
| `--sase-user-ids` | list of SaseUserId | `su_2e10****4ce6 su_ef48****573b` | Observed |
| `--device-tag` | From API response `DeviceTag` field | `480F8E02-****-5932A5FF60BC` | Observed |
| `--device-tags` | list of DeviceTag | `480F8E02-****-60BC 24BB1571-****-86EF` | Observed |
| `--username` | string | `test001` | CLI help |
| `--fuzzy-username` | string, fuzzy match | `zhang` | CLI help |
| `--precise-username` | string, exact match | `zhangsan` | CLI help |
| `--department` | string | `Engineering` | CLI help |
| `--hostname` | string | `MacBook-Pro` | CLI help |
| `--mac` | string | `3c:06:****:79:1b` | CLI help |
| `--inner-ip` | string | `10.0.**.**` | CLI help |
| `--user-group-ids` | list | `usergroup-51bd****a540` | Observed |
| `--name` (list-user-applications) | string | `CRM` | CLI help |
| `--address` (list-user-applications) | string (IPv4/CIDR/domain) | `192.168.1.0/24` | CLI help |

All enum values are **case-sensitive**. List parameters use **space-separated** values (NOT comma).

**[MUST] When user provides a SaseUserId or DeviceTag that looks wrong:**
> Do NOT blindly call the API. Offer to look up the correct value:
> - SaseUserId: use `aliyun csas list-users --fuzzy-username <name>` to find real ID
> - DeviceTag: use `aliyun csas list-user-devices --username <name>` to find real tag

### list-user-devices

Query devices with any combination of 20+ filters:

```bash
aliyun csas list-user-devices --current-page 1 --page-size 100 [OPTIONS] [--pager]
```

Key filters: `--department`, `--device-types` (list), `--device-statuses` (list), `--dlp-statuses`, `--pa-statuses`, `--ia-statuses`, `--nac-statuses`, `--username`, `--device-belong`, `--hostname`, `--sort-by`.

List params use space-separated values: `--device-types Windows macOS`

Enum values:
- **DeviceStatuses**: `Online` `Offline` `LongTermOffline` `Locked` `Lost` `Unbound`
- **DeviceTypes**: `Windows` `macOS` `Linux` `Android` `iOS` `Windows_Wuying`
- **DlpStatuses**: `Enabled` `Disabled` `Unprovisioned` `Unauthorized`
- **PaStatuses/IaStatuses/NacStatuses**: `Enabled` `Disabled` `Unprovisioned`

### list-users

```bash
aliyun csas list-users --current-page 1 --page-size 100 [OPTIONS] [--pager]
```

Key filters: `--fuzzy-username`, `--precise-username`, `--department`, `--status` (Enabled/Disabled), `--sase-user-ids` (list).

### list-user-applications

Query private access applications authorized to a user:

```bash
aliyun csas list-user-applications --sase-user-id <ID> --current-page 1 --page-size 100
```

Required: `--sase-user-id`. Optional: `--name`, `--address`.

### get-user-device

Get full detail for a single device:

```bash
aliyun csas get-user-device --device-tag <TAG>
```

### get-active-idp-config

Get the active Identity Provider configuration:

```bash
aliyun csas get-active-idp-config
```

### list-user-groups

```bash
aliyun csas list-user-groups --current-page 1 --page-size 100 [OPTIONS] [--pager]
```

Key filters: `--name`, `--attribute-value`, `--user-group-ids` (list), `--pa-policy-id`.

## Output Formatting

When presenting query results to users, follow these rules to avoid overwhelming output:

**Result count thresholds:**
- ≤10 items: show all
- 11–50 items: show top 20 + total count
- \>50 items: show top 20 + total count + suggest narrowing filters

**Table format:** Use markdown table with key columns only (not full JSON). Example columns for devices: `#`, user, hostname, device type, relevant status, department.

**Use `--cli-query` to extract fields at API level:**
```bash
aliyun csas list-user-devices --dlp-statuses Disabled --current-page 1 --page-size 100 \
  --cli-query "{total: TotalNum, devices: Devices[].{user: Username, host: Hostname, type: DeviceType, dlp: DlpStatus, dept: Department}}"
```

**Always state the total** before showing partial results, e.g. "Total 844 devices with DLP disabled, showing top 20:"

## Script-Based Operations

### Inactive Analysis (read-only)

Identifies inactive devices based on UpdateTime threshold:

```bash
bash scripts/inactive-analysis.sh --days 30 [--max-days 180]
```

Options: `--days N` (>=1, default 30), `--max-days M` (optional, upper bound), `--department`, `--device-type`, `--page-size`

**Parameter semantics:**
- `--days N` alone: select all devices with UpdateTime < today-N (inactive ≥ N days)
- `--days N --max-days M`: select devices with today-M ≤ UpdateTime < today-N (inactive N~M days)

**Common patterns:**

| User says | Parameters |
|---|---|
| "Inactive for 90+ days" | `--days 90` |
| "Inactive 90~180 days" | `--days 90 --max-days 180` |
| "Inactive for 180+ days" | `--days 180` |
| "Inactive for over a year" | `--days 365` |
| "Inactive 6 months to 1 year" | `--days 180 --max-days 365` |

**[MUST] When user's time range is ambiguous, ask to clarify before executing:**
> "Does 'inactive for 90 days' mean all devices ≥90 days, or only the 90~180 day window?"

Output: JSON with inactive device list and summary statistics. No write operations.

> **Note:** User activity analysis is NOT supported. Reason: the list-users API does not return
> a last-active timestamp, and device binding changes when another user logs in (each device
> only retains the most recent user). Therefore user activity status cannot be determined accurately.
> For user-level analysis, refer to the SASE console audit logs.

When users ask about dormant accounts or stale devices, this is the starting point.

### Cleanup Inactive Devices (destructive, reversible)

Lock devices inactive for N days. Follows Write Operation Rules below.

**Step 1 — Preview:**
```bash
bash scripts/cleanup-inactive.sh --days 90 --dry-run
```

Present dry-run output to user:
- Total devices scanned, inactive count, device list with details
- Follow Output Formatting rules above (≤10 show all, >10 show top 20 + total)
- **Ask user for explicit confirmation** before Step 2

**Step 2 — Execute (only after user confirms):**
```bash
bash scripts/cleanup-inactive.sh --days 90 --yes
```

Locks all inactive devices in batches (≤100 per API call). Lock is idempotent and reversible.

**Step 3 — Verify and report:**

After execution:
1. **Post-action verification** — call `aliyun csas get-user-device --device-tag <TAG>` for each locked device (or sample if many) to confirm `DeviceStatus == "Locked"`. This forms the operation closure: pre-state (dry-run) → execute → post-state (verify).
2. **Format the result for the user** — do NOT dump the raw script JSON. Convert into a markdown summary:
   - One-line conclusion, e.g. "Lock complete: 3 scanned, 1 locked, 0 failed."
   - Markdown table of locked devices (DeviceTag, Username, Hostname, DeviceType, new status)
   - Recovery hint: `aliyun csas update-user-devices-status --device-action Unlocked --device-tags <TAGS>` to revert.
3. **If failures exist** — list failed DeviceTags and advise retry on those tags only.

## Write Operation Rules

**[MUST] All write operations require user confirmation:**
1. Present what will be done (target devices/users, action, count)
2. Ask user to confirm and **wait for explicit yes**
3. Only execute after user confirms — NEVER auto-execute

**[MUST] Cancellation handling:**
When user cancels (replies "no", "cancel", "stop", or anything other than explicit confirmation):
1. Do NOT execute the destructive action
2. Do NOT silently end the session — offer next-step options:
   > "Operation cancelled. Other options: (a) modify scope (e.g. different time range or filters); (b) view the device list only without locking; (c) export DeviceTag list for manual review; (d) exit. Which would you like?"
3. Wait for user choice before proceeding
4. If user confirms exit, end gracefully with a summary of what was NOT done

**[MUST] Idempotent execution:**
- Even if target set is empty (0 devices match), still run the command and report "0 affected"
- Even if devices are already in target state (e.g. already Locked), still execute — the API is idempotent
- Never skip execution with "already done" — always run and report actual result

**[MUST] Post-action verification (operation closure):**
Every write operation must form a closed loop: `pre-check → execute → post-verify`.
1. Before write: confirm the target list (dry-run preview).
2. Execute the write operation.
3. After write: re-query the affected resources (e.g. `get-user-device --device-tag <TAG>`) and confirm the new state matches the intended action.
4. Report the verified result, not just the script's success flag.

**[MUST] Final result formatting:**
Never dump raw script JSON to the user as the final answer. Always:
1. Lead with a one-line conclusion (e.g. "✅ Lock complete: 1/1 devices locked, 0 failed")
2. Show key details in a markdown table (key columns only)
3. Append a recovery / next-step hint when applicable
4. End with the AI-Mode disable command (see Pre-checks)

**[MUST] Quiet execution:**
During multi-step operations, minimize narration between tool calls.
- Do NOT announce trivial steps like "Now I will enable AI mode" or "Executing the lock command"
- Do NOT echo `(no output)` or empty tool results
- Only speak to the user when: (a) presenting preview/results, (b) asking for confirmation, (c) reporting errors
- Internal tool chaining should be silent until a user-facing milestone is reached

**Applies to:**
- `bash scripts/cleanup-inactive.sh --yes` (batch lock)
- `aliyun csas update-user-devices-status --device-action <ACTION> --device-tags <TAGS>` (direct lock/unlock)

**Confirmation template:**
> "About to execute [Locked/Unlocked/Lost/Found] on N devices. Confirm?"

## Capability Boundary

**This skill does NOT perform irreversible operations:**
- Delete user accounts (DeleteClientUser)
- Delete terminal devices (DeleteUserDevices)
- Freeze/unfreeze user accounts (UpdateUsersStatus)
- Analyze user activity (API limitation: no user last-active time available)

**[MUST] When users request deletion of inactive users/devices, follow this flow:**

1. **Clarify scope** — This skill only analyzes and operates on **devices**, not user activity:
   > "Only inactive device queries and device locking are supported. User activity analysis is not available (API limitation). Want to check which devices have been inactive for N+ days?"

2. **Guide to device analysis** — Lead user to specify a time range for devices:
   > "I can help you: query devices inactive for N+ days; query devices inactive within N~M day range; lock these devices (reversible, unlock anytime). Which time range do you need?"

3. **Explain why deletion is not supported:**
   > "Deletion is irreversible — this skill does not perform it. Locking has the same effect (device cannot connect). You can delete via console after confirming."

4. **Offer the lock alternative** with specific details:
   > "Lock these N devices instead? Once locked, they cannot access the network. Unlock anytime."

5. **If user insists on deletion**, guide to console:
   > "Go to Alibaba Cloud Console → SASE → Terminal Management to delete manually. I can export the DeviceTag list for batch operations in the console."

6. **If user accepts lock**, proceed with Write Operation Rules (preview → confirm → execute).

**Never silently refuse.** Always present the alternative action path.

## Error Handling

All scripts output structured JSON with `success: true/false`. On failure, check `error` and `message` fields.

Common errors:
- `ApiCallFailed` — Check network, credentials, and permissions
- `ValidationError` — Invalid parameter; see error message for details
- `Permission denied` / HTTP 403 / `AccessDenied` — Follow RAM Policy & Permission Handling section above. Suggest `AliyunCSASFullAccess` (quick) or add specific `csas:<ApiName>` Action (minimal).
- File system errors (write_file failed, output path not exist) — Check that the output directory exists and is writable. Fall back to printing the report to stdout if the path cannot be written.

All write operations are idempotent. Safe to retry on partial failure. Even if target is empty or already in desired state, execute anyway and report result.

## Script Reference

| Script | Purpose |
|---|---|
| `scripts/validate-cli.sh` | CLI environment validation |
| `scripts/inactive-analysis.sh` | Read-only inactive device analysis |
| `scripts/cleanup-inactive.sh` | Lock inactive devices (destructive, reversible) |
| `scripts/common.sh` | Shared utilities (sourced by other scripts) |

Full API parameter reference: `references/api-reference.md`
CLI command list: `references/related-commands.md`
