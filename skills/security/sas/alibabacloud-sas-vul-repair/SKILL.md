---
name: alibabacloud-sas-vul-repair
description: |
  Alicloud Service Scenario-Based Skill. Use for the vulnerability module of Alibaba Cloud Security Center (SAS): querying and filtering vulnerabilities (by severity/type/asset/status), triggering vulnerability repair and post-fix re-verification, interpreting repair failure error codes (8009, 8037, 9003, etc.) with repository and network troubleshooting, handling "fixed but still detected" status refresh, and manual repair guidance for non-standard systems (self-compiled kernels, non-Alibaba-Cloud hosts, offline environments, custom images, EOL systems).
  Triggers: "Security Center vulnerability", "vulnerability repair", "vulnerability fix", "fix failed", "repair failed", "vulnerability error code", "fixed but still detected", "re-verify vulnerability", "unfixed vulnerability list", "self-compiled kernel", "manual vulnerability fix", "CVE", "漏洞修复", "修复失败", "漏洞错误码", "已修复仍检出", "重新验证漏洞", "漏洞复检", "未修复漏洞清单", "yum 源超时", "自编译内核", "手动修复漏洞".
---

# SAS Vulnerability Repair

Handle the vulnerability module of Alibaba Cloud Security Center (Security Center, SAS) via the aliyun CLI plugin mode (command format `aliyun sas <lowercase-hyphenated-command>`): vulnerability query and filtering, vulnerability repair and post-fix verification, repair failure error code troubleshooting, "fixed but still detected" re-verification, and non-standard system manual repair and adaptation.

## Architecture

Security Center (SAS) + Server Assets (Alibaba Cloud ECS / Non-Alibaba Cloud hosts) + Security Agent (client)

---

## 1. Installation

### Aliyun CLI

**Pre-check: Aliyun CLI >= 3.3.3 required**
> [MUST] Verify: `aliyun version` — must be >= 3.3.3.
> - **First install or major upgrade:** `/bin/bash -c "$(curl -fsSL --connect-timeout 10 --max-time 120 https://aliyuncli.alicdn.com/setup.sh)"`
> - **Routine update (CLI >= 3.3.5):** `aliyun upgrade` — prefer this built-in self-update over re-running the install script.
> - See [references/cli-installation-guide.md](references/cli-installation-guide.md) for full installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

---

## 2. Environment Variables

No environment variables are required by this skill. Credentials are read from the aliyun CLI profile (verified via `aliyun configure list` in Section 3).

> **Note**: SAS is a centralized service. It only exposes two endpoints: `cn-shanghai` (China site) and `ap-southeast-1` (International site). For International-site accounts, make sure the CLI profile region points to the International site (or pass `--region ap-southeast-1` explicitly); otherwise requests may be resolved to the wrong site. Most SAS APIs do not require `RegionId`.

---

## 3. Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## 4. RAM Policy

SAS APIs and corresponding RAM permissions used by this skill (full list in [references/ram-policies.md](references/ram-policies.md)):

| Product | RAM Action | Description |
|---------|-----------|-------------|
| SAS | `yundun-sas:DescribeVulList` | Query vulnerability list (main query entry) |
| SAS | `yundun-sas:DescribeGroupedVul` | Query grouped vulnerability statistics |
| SAS | `yundun-sas:DescribeCloudCenterInstances` | Query asset (server) information, get UUID |
| SAS | `yundun-sas:DescribeVulDetails` | Query vulnerability details (CVE/CVSS/solution) |
| SAS | `yundun-sas:DescribeCanFixVulList` | Query fixable vulnerability list (cve/sca only) |
| SAS | `yundun-sas:DescribeUuidsByVulNames` | Get affected machines by vulnerability name |
| SAS | `yundun-sas:DescribeVersionConfig` | Query purchased SAS edition and quota |
| SAS | `yundun-sas:DescribeFixUsedCount` | Query used vulnerability fix count (pay-as-you-go) |
| SAS | `yundun-sas:CheckTrialFixCount` | Validate trial-version remaining free fix count |
| SAS | `yundun-sas:DescribeVulFixStatistics` | Vulnerability fix statistics |
| SAS | `yundun-aegis:DescribeVulNumStatistics` | Vulnerability count statistics by type |
| SAS | `yundun-sas:DescribeVulConfig` | Query vulnerability management configuration |
| SAS | `yundun-sas:DescribeVulWhitelist` | Query vulnerability whitelist |
| SAS | `yundun-sas:DescribeEmgVulItem` | Query emergency vulnerability information |
| SAS | `yundun-sas:DescribeVulCheckTaskStatusDetail` | Query per-machine scan subtask status |
| SAS | `yundun-sas:DescribeInstanceRebootStatus` | Query instance reboot status |
| SAS | `yundun-sas:DescribeOnceTask` | Query client task (scan task) progress |
| SAS | `yundun-sas:DescribeFrontVulPatchList` | Query Windows prerequisite patches |
| SAS | `yundun-sas:ListVulAutoRepairConfig` | Query auto-repair configuration |
| SAS | `yundun-sas:ModifyOperateVul` | Unified vulnerability operation entry (fix/verify/ignore/delete) |
| SAS | `yundun-aegis:OperateVuls` | Batch fix Linux software vulnerabilities (cve only) |
| SAS | `yundun-aegis:ModifyStartVulScan` | Trigger full-account vulnerability scan |
| SAS | `yundun-sas:ModifyPushAllTask` | Push targeted security check task to specified servers |
| SAS | `yundun-sas:ModifyVulConfig` | Modify vulnerability scan configuration |
| SAS | `yundun-sas:ModifyVulTarget` | Modify per-machine scan target scope |
| SAS | `yundun-sas:ModifyCreateVulWhitelist` | Add vulnerability whitelist entry |
| SAS | `yundun-sas:DeleteVulWhitelist` | Delete vulnerability whitelist entry |
| SAS | `yundun-sas:ModifyEmgVulSubmit` | Run emergency vulnerability detection |
| SAS | `yundun-sas:CreateVulAutoRepairConfig` | Create auto-repair configuration |
| SAS | `yundun-sas:DeleteVulAutoRepairConfig` | Delete auto-repair configuration |

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

> **[MUST] Error Handling and Human-In-The-Loop (HITL):** When any command or API call fails, identify the error type and follow the corresponding handling process. For ALL error types listed below, you MUST immediately stop further execution, output the exact error message received, and respond with the standardized error message format. Do NOT attempt to retry, rephrase the command, or proceed to the next step. Report the error to the user with remediation guidance — the user will decide next steps.
>
> **Error Identification and Handling Rules:**
>
> | Error Type | Error Codes / Keywords | Handling Process |
> |------------|----------------------|------------------|
> | **Permission** | `401`, `403`, `Forbidden`, `NoPermission`, `Unauthorized`, `caller has no permission` | 1. Read [references/ram-policies.md](references/ram-policies.md) for required permissions\n2. Use `ram-permission-diagnose` skill to guide the user\n3. Output: "Operation failed — insufficient RAM permissions. Please grant the required permissions and retry."\n4. **Report the error to the user with remediation guidance** |
> | **Authorization / Quota** | `InsufficientAuthorizationCount`, `UnauthorizedMachineNotSupportFix`, `UserInstanceVersionNotSupportFix`, `FreeVersionNotPermit` | 1. Explain the unmet repair precondition (fix quota / authorization binding / edition)\n2. Output: "Operation failed — repair precondition not met: [details]."\n3. **Report the error to the user with remediation guidance** (see [references/scenario-repair.md](references/scenario-repair.md) Step 2) |
> | **Parameter** | `400`, `InvalidParameter`, `MissingParameter`, `IllegalParam`, `invalid` | 1. List the specific invalid/missing parameters from the error message\n2. Output: "Operation failed — parameter error: [details]. Please verify the parameters and retry."\n3. **Report the error to the user with remediation guidance** |
> | **Throttling** | `503`, `Throttling`, `flow control`, `rate limit` | 1. Output: "Operation failed — request throttled. Please wait a moment and retry later."\n2. **Report the error to the user with remediation guidance** — do NOT auto-retry |
> | **System** | `500`, `InternalError`, `ServiceUnavailable`, `ServerError`, `operateVulError`, `PushTaskError` | 1. Output: "Operation failed — server error. Please retry later or contact Alibaba Cloud support."\n2. **Report the error to the user with remediation guidance** |
>
> **Standardized Error Message Format (MUST use for all unrecoverable errors):**
> ```
> Operation failed — requires human intervention: [error reason].
> Please verify permissions/parameters and retry.
> ```
> Your error report MUST contain the exact phrase `Operation failed — requires human intervention:` — do NOT substitute alternative phrasing such as "I cannot proceed", "Please check", or "Error occurred".
>
> **[MUST] Error Transparency:** When a command or API call fails, capture and print the complete original error — including the HTTP status code, error code (e.g., `NoPermission`, `InsufficientAuthorizationCount`, `IllegalParam`), and the raw error message from stderr/stdout — BEFORE giving remediation guidance. Example: `Error: HTTP 403 | Code: NoPermission | Message: The current operation is not authorized`. Never swallow, paraphrase-only, or truncate the original error text.
>
> **[CRITICAL] Do NOT refuse to help:** When an error occurs, NEVER use refusal phrases such as "I cannot help", "I am unable to help", or equivalents in any language. Instead, explain the specific error, its cause, and the exact steps the user should take to resolve it, then hand the decision back to the user.
>
> **[CRITICAL] No Auto-Retry:** If a command fails with any error code listed in the table above, you MUST immediately STOP execution. Do NOT retry the same command, do NOT modify parameters and retry, and do NOT proceed to the next workflow step. Output the exact error message and the standardized HITL response. Re-executing a failed write command without explicit user approval is a violation. (Read-only diagnostic queries used to analyze a failure are allowed and are not considered retries.)

---

## 5. Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, server names, vulnerability names,
> vulnerability types, UUIDs, filter conditions, page sizes, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.
>
> **Confirmation Rules:**
> 1. If the user has already provided all required parameters (vulnerability name, type, target servers, etc.) in their message, you MAY proceed directly without additional confirmation.
> 2. If any required parameter is missing or ambiguous, you MUST ask the user to obtain the missing parameter before execution.
> 3. If asking returns empty or fails, use the parameters from the user's original message. Do NOT proceed with inferred or default values for missing required parameters.
> 4. For optional parameters not specified by the user, use the defaults listed in the table below.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `--type` | Required (query) | Vulnerability type: `cve`=Linux software, `sys`=Windows system, `cms`=Web-CMS, `app`=application (web scanner), `sca`=application (SCA), `emg`=emergency | - |
| `--name` | Optional | Vulnerability name (exact match) or CVE ID | - |
| `--uuids` | Optional | Server UUID(s), comma-separated (from `describe-cloud-center-instances`) | All assets |
| `--necessity` | Optional | Repair urgency: `asap`=high, `later`=medium, `nntf`=low | - |
| `--status-list` | Optional | Status filter: 1 unfixed, 2 fix failed, 4 fixing, 6 verifying, 7 fixed, 8 fixed-pending-reboot, 10 ignored, 20 expired | - |
| `--dealed` | Optional | Handling state: `y`=handled, `n`=unhandled | - |
| `--remark` | Optional | Fuzzy filter by asset name / public IP / private IP | - |
| `--current-page` | Optional | Page number | `1` |
| `--page-size` | Optional | Items per page | `20` |
| `--operate-type` | Required (modify-operate-vul) | Operation: `vul_fix` / `vul_verify` / `vul_ignore` / `vul_undo_ignore` / `vul_delete` | - |
| `--info` | Required (modify-operate-vul) | JSON array of `{name, uuid, tag, isFront}`; tag: `oval`=Linux, `system`=Windows, `cms`=Web-CMS | - |
| `--tasks` | Required (modify-push-all-task) | Check items: `OVAL_ENTITY`=CVE, `SYSVUL`=system vul, `SCA`=application vul, etc. | - |
| `--lang` | Optional | Response language for `describe-vul-details` | `zh` |

---

## 6. Observability (MUST follow for every aliyun command)

Upon loading this skill, generate a random session ID (32-char lowercase hex string) ONCE for the entire session by running:

```bash
SKILL_SESSION_ID=$(python3 -c 'import secrets; print(secrets.token_hex(16))')
```

If `python3` is unavailable, use: `SKILL_SESSION_ID=$(openssl rand -hex 16)`.
Do NOT use `xxd` (not available in all environments). The value MUST be exactly 32 lowercase hex characters (`secrets.token_hex(16)` and `openssl rand -hex 16` both produce exactly 32) — do NOT concatenate or repeat the value. Use it as `{session-id}` below.

**Rule: Every `aliyun` CLI command that calls a cloud API MUST include the `--user-agent` flag.**
Local utility commands (e.g. `configure`, `plugin`, `version`) do not support this flag and should be excluded.

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}
```

Example (assuming session-id is `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6`):
```bash
aliyun sas describe-vul-list --type cve --necessity asap --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

Do not skip, alter the format, or omit `--user-agent` on any `aliyun` API command invocation.

Do NOT use `aliyun configure ai-mode` (it mutates the user's global CLI config) and do NOT use `export ALIBABA_CLOUD_USER_AGENT=...` env vars (they do not survive across separate shell invocations) — always pass `--user-agent` explicitly on every API command.

---

## 7. Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

**Execution model:**
- **Read operations** (all `describe-*` / `check-*` / `list-*` commands): execute directly; state the intent in one sentence before each call, then report the real response.
- **Write operations** (all `modify-*` / `operate-*` / `create-*` / `delete-*` commands): MUST first present the change list (vulnerability names, affected assets, reboot requirement, snapshot and billing notes) and obtain explicit user confirmation before execution. Never auto-retry a failed write operation.
- **Never fabricate API responses**: every conclusion must come from real command output or official documentation.

All commands are `aliyun sas` subcommands (CLI plugin mode, lowercase-hyphenated). For the full command list see [references/related-commands.md](references/related-commands.md); for parameter details see [references/api-reference.md](references/api-reference.md).

### Scenario Routing

#### Scenario 0: Triage of Vague Requests

When the user's request is vague (e.g., "my server has vulnerabilities, what should I do"), do NOT call any tool first. Collect three items, then route:
1. Vulnerability type (Type): Linux software (`cve`) / Windows system (`sys`) / application (`app`, `sca`) / emergency (`emg`), or a CVE ID provided by the user
2. Affected assets: which server(s)
3. Goal: view the list only / repair now / verify an already-applied fix

If information is insufficient, ask the user to clarify.

#### Scenario 1: Vulnerability Query and Filtering

Typical requests: "show high-severity unfixed vulnerabilities", "what vulnerabilities does this server have", "how many vulnerabilities before I fix them".

1. Confirm filter intent (type / urgency `Necessity` / status `StatusList` / asset scope)
2. Locate assets to get UUIDs (`describe-cloud-center-instances`), then run the combined query (`describe-vul-list`)
3. Present the list as a table; drill down into details (`describe-vul-details`) and fix commands on demand

> Detailed workflow and query recipes: [references/scenario-query.md](references/scenario-query.md)

#### Scenario 2: Vulnerability Repair and Post-Fix Verification

Typical requests: "fix CVE-xxx for me", "batch fix Linux vulnerabilities", "can this vulnerability be fixed with one click".

1. Pre-fix chain: type check (emg/app/sca → manual repair guidance) → edition and quota check → Agent online check → collect vulnerability info (`Info` parameter) → Windows prerequisite patch check
2. Present the change list (vulnerabilities / assets / reboot requirement / snapshot and billing notes), then execute repair after confirmation (`modify-operate-vul` or `operate-vuls`)
3. Post-fix closure: poll status until terminal state; for pending-reboot (Status=8), guide the reboot and track post-reboot verification

> Detailed workflow: [references/scenario-repair.md](references/scenario-repair.md)

#### Scenario 3: Repair Failure and Error Code Troubleshooting

Typical requests: "repair failed with error code 8009", "yum repository timeout, what to do", "vulnerability keeps failing to fix".

1. Locate failure records (`describe-vul-list` with `--status-list 2`, read `ResultCode`/`ResultMessage`)
2. Interpret via the high-frequency error code table (note: the official meaning of 8009 is "update process is running" — the YUM repository is not Alibaba Cloud's or a fix process is running; it is NOT "yum repository timeout", which corresponds to `Errno 12 Timeout` etc.)
3. Run the repository/network five-step troubleshooting (vulnerability management config → server repository → cache refresh and retry → connectivity check → greyed-out fix button causes)

> Error code table and troubleshooting steps: [references/scenario-errors.md](references/scenario-errors.md)

#### Scenario 4: "Fixed but Still Detected" and Re-verification

Typical requests: "I already fixed it, why is it still reported", "why doesn't the status update", "re-verify this vulnerability".

1. Check the current status (`describe-vul-list`) and explain the vulnerability state machine and scan refresh mechanism
2. Locate the cause via the official cause checklist (kernel vulnerability without reboot, page cache, scan severity not covered, Agent offline, GRUB not switched to the new kernel, etc.)
3. Trigger re-verification (`vul_verify`) or a targeted/full scan, then poll task progress until completion

> State machine and action flow: [references/scenario-recheck.md](references/scenario-recheck.md)

#### Scenario 5: Non-Standard System Repair and Adaptation

Typical requests: "can a self-compiled kernel be fixed with one click", "how to fix Ubuntu on AWS", "how to patch in an offline environment", "my custom image has vulnerabilities".

1. Determine the environment (`describe-cloud-center-instances`: Vendor / OS / kernel / edition fields)
2. Route to one of five branches: self-compiled kernel (force fix or manual kernel upgrade) / non-Alibaba Cloud host (repository and backup adaptation) / offline environment (intranet repository or manual patches) / custom image (pre-installation cautions) / EOL system (OS upgrade)
3. Provide copyable manual repair commands (from API-returned `UpdateCmd`/`Solution`) and verification methods

> Five-branch guidance: [references/scenario-nonstandard.md](references/scenario-nonstandard.md)

#### Fallback Scenario

For vulnerability-management-settings requests (scan switches / scan severity / Alibaba Cloud repository / retention period), follow the settings section in [references/scenario-errors.md](references/scenario-errors.md). For any other unmatched request, honestly state it is not supported and point the user to the official vulnerability management documentation https://help.aliyun.com/zh/security-center/user-guide/vulnerability-management/ (dynamic lookup strategy: [references/doc-lookup.md](references/doc-lookup.md)) or an Alibaba Cloud ticket.

### Hard Gates (MUST follow)

> **[HARD GATE] Never use `modify-start-vul-scan` for targeted scans**: `modify-start-vul-scan` triggers a **full scan of ALL servers under the account**, not just the specified targets. To scan specific servers (targeted scan), you MUST use `modify-push-all-task` with the server UUIDs — it is the only correct command for targeted vulnerability scanning. `modify-start-vul-scan` is reserved for full-account scans with no specified targets, and requires explicit user confirmation (explain the impact scope first).
>
> **Repair capability limits**: Emergency vulnerabilities (`emg`), application vulnerabilities (`app`/`sca`) do NOT support one-click repair (`vul_fix`); `operate-vuls` supports `cve` only; the free edition (`AuthVersion=1`) has no repair capability.
>
> **Never reference non-existent APIs**: `GetVulFixDetails` and `ModifyFixVul` do NOT exist — never use them in any scenario.

---

## 8. Success Verification Method

For detailed verification steps per scenario, see [references/verification-method.md](references/verification-method.md).

**Quick verification**: After submitting a repair, poll the vulnerability status until it reaches a terminal state:

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --uuids <server-uuid> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}
```

**[MUST] Data Integrity Rules:**
1. **Never modify API output**: Do NOT alter, rename, or transliterate any field values returned by the API (e.g., vulnerability names, UUIDs, status values, error codes). Always output original values verbatim. Copy values programmatically (e.g., via JSON parsing) instead of retyping them by hand.
2. **Post-operation verification**: After executing a write operation (fix/verify/ignore/whitelist/config change), you MUST re-query (`describe-vul-list` / `describe-vul-config` / `describe-vul-whitelist` as appropriate) to verify the operation took effect. If the verification result contradicts the operation result, report the discrepancy to the user.
3. **Accurate counting**: When summarizing or counting results (e.g., number of vulnerabilities by severity), you MUST parse the raw API output line by line and count exact occurrences. Do NOT use words like "approximately", "about", "~". If the output is truncated, explicitly state "Output truncated — exact count unavailable".

---

## 9. Cleanup

This skill does not create standalone cloud resources; "cleanup" means reverting configuration changes made during the session:

### Remove a Vulnerability Whitelist Entry

```bash
aliyun sas delete-vul-whitelist --id <whitelist-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}
```

### Delete an Auto-Repair Configuration

```bash
aliyun sas delete-vul-auto-repair-config --type cve --config-id-list '[<config-id>]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}
```

### Undo an Ignore / Restore a Scan Target

```bash
# Undo ignore (vulnerability returns to detection)
aliyun sas modify-operate-vul --type cve --operate-type vul_undo_ignore --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval","isFront":0}]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}

# Add a server back into the scan scope
aliyun sas modify-vul-target --config '{"vulType":"cve"}' --target '[{"target":"<server-uuid>","targetType":"uuid","flag":"add"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}
```

> **Note**: All cleanup operations above are write operations — present the change list and obtain user confirmation before execution.

---

## 10. Command Tables

For the complete list of CLI commands (read/write grouped, with scenario mapping), see [references/related-commands.md](references/related-commands.md).

---

## 11. Best Practices

1. **Pre-checks first**: Complete the CLI version and credential pre-checks before any operation; stop and guide the user if either fails.
2. **Locate before querying**: In query scenarios, first locate asset UUIDs (`describe-cloud-center-instances`), then apply combined filters (`describe-vul-list`) — avoid unbounded full pulls.
3. **Three-way pre-fix check**: Before repair, verify vulnerability type, edition/quota, and Agent online status before entering change confirmation and execution.
4. **Full change list before writes**: Present vulnerability names, assets, reboot impact, snapshot and billing notes before every write operation; execute only after explicit confirmation.
5. **Targeted scans only via `modify-push-all-task`** with target UUIDs; `modify-start-vul-scan` is for full-account scans only, after user confirmation.
6. **Poll to terminal states**: After repair, poll until the status reaches fixed (7) / pending-reboot (8) / failed (2); for Status=8, guide the reboot and track post-reboot verification.
7. **Error codes from the table first**: Consult the embedded high-frequency error code table first; for unmatched codes, dynamically fetch the official error code page per [references/doc-lookup.md](references/doc-lookup.md).
8. **Verify volatile facts**: Billing prices, scan cycles, and OS support lists change frequently — verify against official documentation before citing; never quote from memory.
9. **Consistent observability**: Reuse the same session-id for the whole session and include `--user-agent` on every API command.

---

## 12. Reference Links

| Reference | Contents |
|-----------|----------|
| [references/api-reference.md](references/api-reference.md) | Full API parameter details, enums, and copyable examples |
| [references/scenario-query.md](references/scenario-query.md) | Scenario 1: vulnerability query and filtering workflow and recipes |
| [references/scenario-repair.md](references/scenario-repair.md) | Scenario 2: vulnerability repair and post-fix verification closure |
| [references/scenario-errors.md](references/scenario-errors.md) | Scenario 3: high-frequency error code table and repository/network troubleshooting |
| [references/scenario-recheck.md](references/scenario-recheck.md) | Scenario 4: state machine, "fixed but still detected" troubleshooting and re-verification |
| [references/scenario-nonstandard.md](references/scenario-nonstandard.md) | Scenario 5: five-branch manual repair and adaptation for non-standard systems |
| [references/related-commands.md](references/related-commands.md) | Complete command reference (read/write grouped) |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission list and permission failure handling |
| [references/doc-lookup.md](references/doc-lookup.md) | Official documentation dynamic lookup strategy (3-tier chain) |
| [references/verification-method.md](references/verification-method.md) | Success verification methods per scenario |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria (correct/incorrect patterns) |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Aliyun CLI installation guide |
