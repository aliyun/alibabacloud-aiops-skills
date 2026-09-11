# Scenario 2: Vulnerability Repair and Post-Fix Verification

This scenario addresses requests like "fix this vulnerability for me / batch fix high-severity vulnerabilities / how do I confirm it is fixed after repair": complete the pre-fix check chain, execute one-click repair after user confirmation, and close the loop by tracking repair status until verification completes.

## Trigger Conditions

Example user phrasings (enter this scenario when any matches):

- "Fix this vulnerability / the high-severity vulnerabilities on these servers"
- "Batch fix Linux software vulnerabilities"
- "How do I verify it is fixed after repair?"
- "It shows fixed-pending-reboot — what's next?"
- "Can I roll back if the repair breaks something?"

## Prerequisites

1. CLI and credential checks, session-id generation: see SKILL.md. All API commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>`.
2. This scenario includes write operations: present the change list and obtain confirmation before execution; auto-execution and auto-retry after failure are forbidden.
3. The target vulnerability list and affected assets have been clarified via Scenario 1 (references/scenario-query.md).

## Pre-Fix Chain (7 steps; evaluate each step; any failed step goes to its branch)

### Step 1: Type check (determines one-click repair vs manual repair)

Intent: confirm whether the target vulnerability type supports one-click repair.

| Type | One-click repair (vul_fix) | Route |
|------|---------------------------|-------|
| `cve` (Linux software) | Supported | Continue to Step 2 |
| `sys` (Windows system) | Supported | Continue to Step 2 (note Step 5 prerequisite patches) |
| `emg` (emergency) | Not supported | Go to the "Manual Repair Path" section below |
| `app`/`sca` (application) | Not supported | Go to the "Manual Repair Path" section below |

Determination: from the Type in the query results; when unsure, show the vulnerability name and type to the user for confirmation.

### Step 2: Edition and repair quota check

Intent: confirm the asset edition has repair capability and sufficient quota, avoiding immediate failure after submission.

```bash
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Result interpretation notes:
- `VulFixCapacity`: purchased vulnerability fix count (pay-as-you-go fix quota); `PostPayModuleSwitch`: pay-as-you-go module switch state.
- Free-edition (AuthVersion=1) assets have no repair capability: an edition upgrade or paid authorization binding is required first — explain to the user and pause the repair flow here.

```bash
aliyun sas check-trial-fix-count --type cve --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Trial repair eligibility: check `CanFix` (whether repair is supported) and `RemainCount` (remaining count after validation passes); if trial quota is available, proactively inform the user; this command only validates and does not trigger repair.

```bash
aliyun sas describe-fix-used-count --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Used pay-as-you-go fix count: for estimating the cost magnitude of this repair (prices are subject to the official page — verify dynamically, see communication points).

Failure branches (handling guidance for the three authorization errors):

| Error Identifier | Meaning | User-facing Handling Points |
|------------------|---------|------------------------------|
| InsufficientAuthorizationCount | Insufficient fix authorization count | "The vulnerability fix quota is used up; purchase more fix count or wait for the quota policy adjustment before repairing" |
| UnauthorizedMachineNotSupportFix | Target server not bound to an authorization | "This server is not bound to a paid edition authorization and cannot be repaired; bind an authorized edition first" (guide authorization management to the alibabacloud-sas-install-agent skill) |
| UserInstanceVersionNotSupportFix | Server edition does not support repair | "The current server edition does not support one-click repair; upgrade the edition, or use the manual repair path" |

### Step 3: Agent online check

Intent: repair commands execute via the client — the Agent must be online.

```bash
aliyun sas describe-cloud-center-instances --criteria '[{"name":"internetIp","value":"<public-ip>"}]' --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Judgment: repair can be submitted only when `ClientStatus=online`; `offline`/`pause` (ClientSubStatus additionally has uninstalled/stopped) cannot be submitted.
- Failure branch: Agent offline or uninstalled → point to the `alibabacloud-sas-install-agent` skill to restore client online first, then return to continue repair.

### Step 4: Collect vulnerability info (assemble the Info parameter)

Intent: obtain the vulnerability name, asset uuid, and tag required by the repair command.

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Take from the response: `Name` (vulnerability name), target asset `Uuid`, `Tag` (use lowercase keys name/uuid/tag when writing the Info parameter).
- Tag-to-type mapping (contract enum, determines the Info value): `oval`=Linux software, `system`=Windows system, `cms`=Web-CMS.

### Step 5: Windows prerequisite patch check (Type=sys only)

Intent: some Windows vulnerabilities require prerequisite patches (e.g., Servicing Stack updates) before repair; missing them causes failure.

```bash
aliyun sas describe-front-vul-patch-list --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"system"}]' --operate-type vul_fix --type sys --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Non-empty response: prerequisite patches exist. When executing repair, set `isFront` to `1` for the corresponding item in Info (default 0); prerequisite patches are submitted together with the repair.
- Empty response: continue normally; keep `isFront` at 0.

### Step 6: User confirmation (write-operation gate — must complete before execution)

Intent: let the user confirm repair with full awareness (reboot impact, snapshot, billing).

Change list template to present:

| Item | Content |
|------|---------|
| Vulnerability list | Vulnerability names, severity (high/medium/low), affected asset count |
| Affected assets | Asset name/IP list (or count + samples) |
| Reboot required | See reboot determination rules below |
| Snapshot advice | Recommend "auto-create snapshot and repair" (rollback on failure); the user can also choose "repair directly" (no snapshot, no rollback) |
| Billing note | Pay-as-you-go repair counts only on success — failed repairs are not counted; prices are subject to the official page, verify dynamically (see references/doc-lookup.md for retrieval) |

Reboot determination rules:
- Windows system vulnerabilities: always require a reboot.
- Linux kernel vulnerabilities or bulletins tagged "reboot required": require a reboot.
- Multiple reboot-requiring vulnerabilities: reboot once at the end instead of per vulnerability.

Force-fix note (state honestly to the user): when repairing kernel vulnerabilities, Security Center validates the compatibility of the upgraded kernel with the client; selecting "force fix" skips this validation with compatibility risk (in severe cases the system cannot boot) — a snapshot must be created first. See references/scenario-nonstandard.md Branch A.

Batch limit: a single Linux batch repair supports at most 100 vulnerabilities (the limit is on vulnerability count, not host count); split larger batches to reduce impact.

Confirmation phrasing template: "About to repair Y vulnerabilities on X servers (severity: high/medium). Windows system vulnerabilities require a reboot after repair — schedule this during off-peak hours. We recommend creating a snapshot for rollback. Pay-as-you-go repair is billed only on success. Please confirm whether to proceed?"

### Step 7: Execute repair (write operation — requires user confirmation)

Single vulnerability or small repairs (general entry for cve/sys/emg fix/verify/ignore):

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_fix --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"<oval|system|cms>","isFront":0}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Batch repair (cve only — Linux software vulnerabilities):

```bash
aliyun sas operate-vuls --type cve --operate-type vul_fix --vul-names <vulnerability-name> --uuids <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- `modify-operate-vul`'s Info is a JSON array with multiple items comma-separated; `operate-vuls`'s VulNames and Uuids are array parameters (repeatable). See references/api-reference.md for full parameter descriptions.
- After execution, report to the user that the task is accepted, then enter post-fix closure.
- Field-tested note (pitfall record): when batch-repairing multiple vulnerabilities on the same machine (operate-vuls), repair tasks **execute serially in a queue**: in testing a single item took about 10 minutes and a 7-item batch took over 30 minutes; queued vulnerabilities show Status=4 with ResultCode null (not yet reached), and only executed ones get ResultCode and yum logs backfilled. When polling, do not misjudge a long Status=4 without logs as stuck or failed; widen the polling interval to 2-3 minutes and explain the serial mechanism and estimated duration to the user upfront.

## Post-Fix Closure

### Poll repair status

Intent: track Status transitions (4 fixing → 7 fixed / 8 fixed-pending-reboot / 2 fix failed), reporting to the user together with the Progress field.

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Suggested polling rhythm: every 30-60 seconds; when there is no change for several consecutive polls, explain that repair runs in the background — wait patiently and do not repeatedly submit.
- Status=2 (fix failed): take ResultCode/ResultMessage and go to references/scenario-errors.md for interpretation; retry is a write operation requiring confirmation again — never auto-retry.
- Field-tested notes (pitfall records):
  - Status=4 (fixing) can last about 10 minutes before reaching a terminal state — this is normal; during this period `ResultCode` is null first, and after the repair action actually executes, `ResultCode="0"` is backfilled and `ResultMessage` contains the full yum/apt execution log (including "Complete!") — report this as real execution evidence to the user.
  - After repair reaches a terminal state, the vulnerability record may disappear from the **default query without StatusList** (polling returns an empty array). This does not mean data loss: query explicitly with `--status-list 7,8,2` to see the terminal-state record; do not misjudge or resubmit repair because of an empty query.

### Reboot closure for pending-reboot vulnerabilities (Status=8)

1. Guide the user to reboot the server:
   - Alibaba Cloud ECS: reboot via the ECS console, or the user reboots themselves;
   - Non-Alibaba Cloud servers: console reboot is not supported — the user must reboot on the source platform.
2. Query reboot status (Alibaba Cloud machines):

```bash
aliyun sas describe-instance-reboot-status --uuids <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

   - `RebootStatus` enum: 0 rebooting, 1 reboot succeeded, 2 reboot failed; wait for 1 before proceeding.
3. After reboot completes, trigger verification (write operation — requires user confirmation):

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_verify --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"<oval|system|cms>","isFront":0}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Note: non-kernel vulnerabilities are automatically detected after a successful repair — no manual verification needed; kernel vulnerabilities follow the reboot + verification closure above after fixed-pending-reboot.

### Rollback notes

- Applicability: only one-click-repair Linux/Windows vulnerabilities support rollback; non-Alibaba Cloud servers do not support rollback.
- Rollback path (console operation — describe to the user): accumulated handled → fixed records → select "Rollback"; the system rolls back to the snapshot automatically created before repair.
- Precondition: "auto-create snapshot and repair" was selected during repair; "repair directly" cannot be rolled back.

## Manual Repair Path (application/emergency vulnerabilities or when one-click repair is unsupported)

Intent: for emg/app/sca types and scenarios without one-click repair support, guide the user to execute repair commands on the server themselves.

1. Get the repair command and fixability determination:

```bash
aliyun sas describe-vul-list --type app --name <vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

   - Take the repair command from the response's `ExtendContentJson.RpmEntityList[].UpdateCmd`; check `CanFix` (yes/no) and `CanUpdate` to determine current one-click/upgrade fix conditions.
   - cve/sca types can also use `describe-can-fix-vul-list` to get the fixable list and commands (parameters in references/api-reference.md). Field-tested note (pitfall record): this API was observed to return no records (always empty) in host vulnerability scenarios; host vulnerability repair commands must come from describe-vul-list / describe-vul-details responses — see the pitfall record in section 3.4 of api-reference.md.
2. Emergency vulnerabilities (emg): first check the `Solution` in `describe-vul-details` (official repair solution) and guide the user accordingly — do not give generic commands from experience.
3. Guide the user to log in to the server and execute the command in UpdateCmd (with root/admin privileges; command content is subject to the API response — never rewrite key parameters).
4. After completion, return to Security Center to trigger verification (write operation — requires user confirmation): `modify-operate-vul --type <type> --operate-type vul_verify` (same command as post-fix closure); after verification passes, the status becomes fixed.

## Auto-Repair Configuration (brief)

Intent: when the user wants the system to repair automatically on a schedule with less manual involvement, introduce capability limits and configuration items.

- View: `aliyun sas list-vul-auto-repair-config`; create: `aliyun sas create-vul-auto-repair-config` (write operation — requires user confirmation); delete: `aliyun sas delete-vul-auto-repair-config` (write operation — requires user confirmation). See references/api-reference.md for parameter details.
- Capability limits: supports only non-kernel Linux system vulnerabilities; kernel vulnerabilities, Windows vulnerabilities, and application vulnerabilities do not apply.
- Configuration overview: repair cycle, vulnerability severity, whether to create snapshots, effective asset scope. Confirm each item with the user before creation.

## User Communication Points

- Pre-execution confirmation: fully present the change list (vulnerability names / assets / counts / reboot / snapshot / billing); submit only after explicit "confirm".
- Billing explanation: "For pay-as-you-go vulnerability repair, only successful repairs are counted — failed repairs are not; specific prices are subject to the official page's real-time prices."
- Repairing explanation: "Vulnerability repair runs in the background on the server; the transition from 'fixing' to 'fixed / pending-reboot / fix failed' takes minutes to tens of minutes depending on patch size and network — I will keep tracking it."
- Pending-reboot explanation: "The status 'fixed-pending-reboot' means the patch is installed and takes effect after reboot; without a reboot, verification will not pass automatically."
- Failure explanation: first restate the error code and its meaning, then give troubleshooting steps (go to references/scenario-errors.md), finally state "re-repair after handling requires your confirmation again — I will not auto-retry".
- Rollback explanation: "If business anomalies occur after repair, you can roll back the 'fixed' record — the system restores to the snapshot automatically created before repair; 'repair directly' has no snapshot to roll back to, which is why the snapshot option is recommended."

## Notes and Boundaries

- **Hard repair capability limits**: `emg`/`app`/`sca` do not support vul_fix; `operate-vuls` supports `cve` only; the free edition (AuthVersion=1) has no repair capability. Never submit repair for unsatisfied combinations.
- **Write-operation discipline**: repair, verification, and auto-repair configuration add/remove are all write operations — confirm each time; never auto-retry on failure.
- **Scanning is not verification**: when the user asks to "rescan to confirm it's fixed", distinguish single-vulnerability verification (vul_verify) from scanning (targeted/full); see references/scenario-recheck.md for the scan hard gate.
- For non-standard systems (self-compiled kernels, non-Alibaba Cloud hosts, offline environments, etc.), first go to references/scenario-nonstandard.md to determine the branch, then decide one-click or manual.
- Do not promise specific repair durations; report based on actual Progress and Status responses.

## Related Documents

- Command parameters and response fields: [references/api-reference.md](api-reference.md)
- Repair failure error code interpretation: [references/scenario-errors.md](scenario-errors.md)
- State machine and re-verification: [references/scenario-recheck.md](scenario-recheck.md)
- Non-standard system repair adaptation: [references/scenario-nonstandard.md](scenario-nonstandard.md)
- Vulnerability query (target location before repair): [references/scenario-query.md](scenario-query.md)
- Official documentation dynamic lookup (billing/mechanisms): [references/doc-lookup.md](doc-lookup.md)
- Scenario entry and boundary overview: [../SKILL.md](../SKILL.md)
