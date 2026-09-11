# Scenario 4: "Fixed but Still Detected" and Re-verification

This scenario addresses requests like "the vulnerability is clearly fixed — why is it still shown/reported, why hasn't the status changed, please re-verify it for me": explain the vulnerability state machine and scan refresh mechanism, troubleshoot "fixed but still detected" causes per the official FAQ priority, and guide the user to trigger the correct re-verification or scan action.

## Trigger Conditions

Example user phrasings (enter this scenario when any matches):

- "The vulnerability is already fixed — why does the console still show unfixed / still report it?"
- "I manually upgraded on the server — why does Security Center still detect this vulnerability?"
- "What does 'fixed-pending-reboot' mean? What should I do after rebooting?"
- "Please re-verify this vulnerability / rescan this server"
- "How do I re-detect an emergency vulnerability?"

## Prerequisites

1. CLI and credential checks, session-id generation: see SKILL.md. All API commands must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>`.
2. Write operations (verify, ignore, scan) must be confirmed with the user first; the impact scope must be explained before triggering a full scan.
3. Query the current status before explaining anything (do not draw conclusions from the user's description alone) — see Step 1 of the handling action flow.

## Vulnerability State Machine

Status enum versus console status names, and transition rules (one-click repair chain: 1→4→7/8/2; manual repair chain: 1→6→7 or back to 1):

| Status | Console Status Name | Transition Rules |
|---|---|---|
| 1 | Unfixed | Initial state; after one-click repair starts → 4; after manual repair, click "Verify" → 6 |
| 2 | Fix failed | Terminal state of one-click repair failure; after troubleshooting, re-repair → 4 (see references/scenario-errors.md) |
| 3 | Rollback failed | Terminal state of a failed rollback; requires manual analysis |
| 4 | Fixing | One-click repair in progress; completed → 7 (success) / 8 (success, pending reboot) / 2 (failure) |
| 5 | Rolling back | Rollback in progress; completed → 9 / 11 / 3 |
| 6 | Verifying | Verification or re-verification after manual repair in progress; pass → 7, fail → back to 1 |
| 7 | Fixed | Terminal state of repaired and verified (rollback available — see references/scenario-repair.md) |
| 8 | Fixed-pending-reboot | Patch installed, awaiting reboot to take effect; **not auto-verified** — after reboot + verification → 7 (see handling action flow) |
| 9 | Rollback succeeded | Terminal state of rollback completed |
| 10 | Ignored | Terminal state after ignoring; can un-ignore (vul_undo_ignore) to return to 1 |
| 11 | Rollback succeeded-pending-reboot | Rollback completed, awaiting reboot to take effect |
| 12 | Vulnerability does not exist | Verification confirmed the vulnerability does not exist (e.g., file already deleted) |
| 20 | Expired | Vulnerability record expired (e.g., OS reinstallation, officially delisted); also reachable via automatic expiry |

Supplementary note: Status and Dealed are two views — Dealed (y/n) is a coarse-grained "handled or not" marker; Status is the fine-grained state. When presenting to users, use the readable Status state names; avoid presenting both systems at once to prevent confusion.

## Status Refresh Mechanism (the basis for explaining to users)

### Scan Cycle Table

The numbers below are subject to the latest official documentation (retrieval method in references/doc-lookup.md):

| Vulnerability Type | Automatic Scan Cycle | Customizable |
|---|---|---|
| Linux software / Windows system vulnerabilities | Free, value-added service, and anti-virus editions: automatic scan every 2 days; Advanced, Enterprise, and Ultimate editions: automatic scan daily | System default cycle, not modifiable |
| Application vulnerabilities (app/sca) | Customizable: every 3 days / weekly / bi-weekly | Customizable |
| Emergency vulnerabilities (emg) | Customizable cycle | Customizable |

- Manual scans and automatic scans are independent: manually triggering a scan does not affect the automatic cycle.
- A manual scan task can only be manually stopped 15 minutes after creation; it usually completes within 30 minutes (subject to the latest official documentation).
- **After the first scan does not detect a vulnerability, the record is retained for a while before being cleared** (anti-misjudgment mechanism): system vulnerability (cve/sys) records are retained 3 days; application vulnerability (app/sca) records are retained 30 days — i.e., after a vulnerability is fixed/disappears, if the first scan does not find it, the record does not vanish immediately. This is one of the most common mechanistic causes of "fixed but still shown".
- Status updates have a sync delay of several minutes — this is normal.

## "Fixed but Still Detected" Cause Troubleshooting Table (ordered by official FAQ priority)

Before checking item by item, ask the user three things: whether they rebooted, whether they repaired manually, and what repair method was used (one-click / manual / mitigation). Each item contains symptom/cause/handling action:

Usage notes: #1/#2 in the table are the highest-frequency causes — verify them first; #7/#8/#9 apply only to Linux kernel-class vulnerabilities; #10 applies only to Windows; after a match, execute the corresponding handling action — actions containing write operations require confirmation first. Old kernel uninstallation (#8) requires a snapshot first.

| # | Symptom/Cause | Handling Action |
|---|---|---|
| 1 | Kernel vulnerability fixed without reboot (most common): patch installed but the running kernel is still the old version | Guide a reboot via the details page/console (Alibaba Cloud ECS can reboot via the console; non-Alibaba-Cloud machines reboot by themselves) → after reboot completes, trigger verification (see Step 3 of the handling action flow) |
| 2 | The "fixed-pending-reboot" status is never auto-verified: without reboot and verification the status stays put | Must reboot + manually trigger verification; otherwise only wait for the periodic scan, and after the first scan misses it the record is still retained (system vulnerabilities 3 days, application vulnerabilities 30 days) |
| 3 | Page cache/sync delay: the actual status already changed but the page did not refresh | Force-refresh the page (Ctrl+F5) and wait a few minutes |
| 4 | The "vulnerability scan severity" in Vulnerability Management Settings does not cover this vulnerability's severity: vulnerabilities of that severity are never rescanned | Three-step handling: ① first use `aliyun sas describe-vul-config --user-agent ...` (pass --type as needed, e.g., cve/sys) to check the current scan configuration (full command in the supplement after this table) → ② console adjustment entry: Security Center console → Risk Governance → Vulnerabilities → Vulnerability Management Settings (location of scan severity adjustment) → ③ the exact setting location is subject to official documentation — dynamic retrieval in references/doc-lookup.md; after adjustment, wait for the next scan or run a targeted scan to recheck (otherwise the status never updates) |
| 5 | Agent offline: verification/scan commands cannot be delivered, status cannot update | Restore the client online first: point to the `alibabacloud-sas-install-agent` skill |
| 6 | Incomplete repair: only one of multiple vulnerability paths was fixed; or an application vulnerability used a "mitigation" that changed configuration without upgrading the version — version detection still reports | Upgrade to the safe version (per UpdateCmd/Solution); if upgrading is truly impossible, ignore after confirming the risk |
| 7 | Ubuntu GRUB not switched to the new kernel: kernel installed but the boot entry not switched | Before repair, set `export DEBIAN_FRONTEND=noninteractive` then repair; or after repair, edit /etc/default/grub, run `update-grub`, then reboot |
| 8 | Old kernel packages remain: old kernels are still installed, so scans still detect them | Confirm the running kernel with `uname -av` and `cat /proc/version` → find old packages with `rpm -qa \| grep kernel` → **create a snapshot first** → uninstall with `rpm -e kernel-<old-version>` → if still reported, ignore |
| 9 | `yum update kernel` shows Nothing to do: the command itself needs no execution — this does not mean the vulnerability is gone | Still recommend rebooting once + triggering verification |
| 10 | Windows special case: installing the latest cumulative update is considered to cover historical vulnerabilities — it shows fixed even if old patches are not installed | This is a normal mechanism — explain it to the user; no action needed |
| 11 | Status updates after ignore/verification have a sync delay | Normal — wait a few minutes and refresh |

Full verification command for troubleshooting table #4 step ① (omitting `--type` returns all type configurations; pass `--type cve`/`--type sys` etc. as needed):

```bash
aliyun sas describe-vul-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

## Reboot and Verification Closure (dedicated flow for Status=8)

Standard handling path for pending-reboot vulnerabilities, executed step by step:

1. **Guide the reboot**: confirm the reboot window with the user; Alibaba Cloud ECS can reboot via the ECS console or the user reboots themselves; non-Alibaba-Cloud servers do not support console reboot — the user must reboot on the source platform.
2. **Query reboot status** (Alibaba Cloud machines):

```bash
aliyun sas describe-instance-reboot-status --uuids <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

   - `RebootStatus` enum: 0 rebooting, 1 reboot succeeded, 2 reboot failed; wait for 1 before proceeding.
3. **Trigger verification** (write operation — requires user confirmation): `modify-operate-vul --type <type> --operate-type vul_verify` (command in Step 3 of the handling action flow).
4. **Re-check status**: re-query the vulnerability and observe 6 verifying → 7 fixed; if it falls back to 1 unfixed, continue locating per troubleshooting table #6/#7/#8.

Supplement: after a non-kernel vulnerability is fixed, the system auto-detects it — no manual verification needed; kernel vulnerabilities must go through the reboot + verification closure.

## User Situation Quick Reference Table

| User's Exact Words | Most Likely Cause (troubleshooting table #) | First Action |
|---|---|---|
| "Fixed yesterday, still reported today" | #2 pending-reboot unhandled, or #11 sync delay | Query Status; if 8, run the reboot-verification closure |
| "I manually upgraded with yum and it still reports" | #6 incomplete repair, or #9 Nothing to do | Compare running version vs required version; trigger verification |
| "The status on the page never moves" | #3 cache, or #5 Agent offline | Force-refresh the page; check ClientStatus |
| "I rebooted — why hasn't it changed?" | #4 scan severity not covered, or #11 delay | Handle per troubleshooting table #4's three steps (describe-vul-config check of current scan configuration + adjust severity in console Vulnerability Management Settings); trigger single-vulnerability verification |
| "Re-detect the emergency vulnerability" | emg type dedicated path | Step 5 of the handling action flow |
| "Ubuntu installed the new kernel and still reports" | #7 GRUB not switched to the new kernel | update-grub + reboot + verify |
| "Can you stop reporting this?" | The user wants noise suppression | Explain the ignore vs whitelist difference, then execute as needed |
| "Can you stop scanning this machine?" | The user wants per-machine exclusion | Scan target adjustment (modify-vul-target del) or vulnerability whitelist — differences in the dedicated section below |

## Handling Action Flow

### Step 1: Query the current status

Intent: confirm the vulnerability's real Status at this moment via the API, avoiding being misled by page cache.

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Read the `Status` field, locate it against the state machine table; Status=8 goes directly to Step 3's reboot + verification closure.

### Step 2: Locate cause item by item per the troubleshooting table

- Ask the user first: rebooted or not / repaired manually or not / repair method (one-click, manual upgrade, mitigation).
- Compare against #1 → #11 in order above; when matched, execute the corresponding handling action.
- When the official repair suggestion is needed, use `describe-vul-details`'s `Solution`.

### Step 3: Trigger actions (choose as needed; all are write operations requiring user confirmation)

Two confirmations before dispatching any scan:
- Intent clarification: confirm whether the user wants "vulnerability re-check only" (handled by this skill) or "a full security check including baseline checks / virus detection" (the latter points to the `alibabacloud-sas-install-agent` skill).
- Eligibility check: use `describe-cloud-center-instances` to check the target asset's `AuthVersion` (free edition has no scan/repair capability) and `ClientStatus` (offline assets must be restored online before dispatch).

Single-vulnerability re-verification:

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_verify --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"<oval|system|cms>","isFront":0}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Targeted scan of specified servers (HARD GATE — wording consistent with the install-agent skill):

```bash
aliyun sas modify-push-all-task --uuids <server-uuid> --tasks OVAL_ENTITY,SYSVUL --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Tasks are check items: OVAL_ENTITY=CVE vulnerabilities, SYSVUL=system vulnerabilities, SCA=application vulnerabilities, etc. (full values in references/api-reference.md); choose per the vulnerability types the user cares about.

> **[HARD GATE] NEVER use modify-start-vul-scan for targeted scans**: `modify-start-vul-scan` triggers a full scan of ALL servers in the entire account — not just the target server. When scanning specified servers (targeted scan), you must and can only use `modify-push-all-task` + the target server UUIDs. `modify-start-vul-scan` is reserved exclusively for "full-account scans with no target specified".

Full-account full scan (write operation — requires user confirmation; explain the impact scope before triggering — scans all assets with some workload):

```bash
aliyun sas modify-start-vul-scan --types cve,sys --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Types is optional (comma-separated vulnerability types; omitting scans all types); full parameters in references/api-reference.md.

### Step 4: Progress polling

Intent: track scan/verification task progress; after completion, re-check the status transition (e.g., 6 verifying → 7 fixed).

```bash
aliyun sas describe-once-task --task-type VUL_CHECK_TASK --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Task status enum: 1 started, 2 completed, 3 failed, 4 timed out; at least one of TaskType and RootTaskId must be passed (full parameters in references/api-reference.md).

- For subtask-granularity progress use `describe-vul-check-task-status-detail` (subtask Status enum: 0 unprocessed, 1 collecting, 2 collection complete, 3 matching, 4 completed; requires TaskIds, Types, Uuid — see references/api-reference.md).
- Suggested polling rhythm: every 30-60 seconds; manual scan tasks usually complete within 30 minutes (subject to the latest official documentation).

### Step 5: Emergency vulnerability re-check (emg type only)

```bash
aliyun sas modify-emg-vul-submit --name <emergency-vulnerability-name> --user-agreement yes --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- (Write operation — requires user confirmation) Name is required; UserAgreement=yes indicates the user agrees to re-detection.
- Query detection progress: `describe-emg-vul-item`; `Status`: 10 not detected, 20 detecting, 30 completed; `Progress`: 0-100.

## Ignore vs Whitelist

| Comparison Item | Ignore | Whitelist |
|---|---|---|
| Command | `modify-operate-vul --operate-type vul_ignore`; can un-ignore with `vul_undo_ignore` | `modify-create-vul-whitelist` to create / `delete-vul-whitelist` to delete |
| Effective scope | Applies only to the current process/instance; may be detected again after application restart | Persistent by CVE category, and can limit the asset scope |
| Suitable for | Temporary noise suppression, confirmed false positives | Vulnerability categories not of long-term concern |
| Restore detection | Un-ignore or wait for process restart | After deleting the whitelist rule, the vulnerability is detected again |

Both are write operations — explain the effective-scope difference before execution so users don't assume ignore = permanent disappearance.

Operation examples (all require user confirmation):

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_ignore --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"<oval|system|cms>","isFront":0}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

```bash
aliyun sas modify-create-vul-whitelist --whitelist '[{"Status":0,"Name":"<vulnerability-name>","Type":"cve","AliasName":"<vulnerability-alias>","AsapCount":1,"LaterCount":0,"NntfCount":0,"Related":"<related-cves>","HandledCount":0,"GmtLast":<last-detected-timestamp>,"RuleModifyTime":<published-timestamp>,"TotalFixCount":0,"Tags":"<tags>"}]' --reason <whitelist-reason> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Whitelist fields can be obtained from describe-grouped-vul; asset scope limitation (TargetInfo) and other parameters in references/api-reference.md — confirm each item with the user before creation.
- Additionally, `vul_delete` (delete the vulnerability record from the list) — use with caution: only for scenarios where the user explicitly requests clearing the record; after deletion, a rescan will still detect it.
- Field-tested notes (pitfall records):
  - After un-ignoring (vul_undo_ignore), the system **automatically triggers a re-verification**; the status transitions 10 → 6 (verifying) → back to 1. Queries by Status=1 during the verification window may temporarily return empty — poll until verification completes before confirming.
  - After ignore/un-ignore/whitelist add/delete operations, the vulnerability record may **temporarily disappear from describe-vul-list queries** (unfindable with or without StatusList); field tests show the recovery window can extend to the next day (case: disappeared during round-trip testing in the evening, re-detected with Status=1 after the next day's scheduled scan, with GmtFirst/GmtLast reset to the re-detection time). During the disappearance window, never conclude "the vulnerability is gone" — explicitly tell the user to defer to the console or the next scan round.
  - After a successful whitelist add, the `modify-create-vul-whitelist` response directly returns `VulWhitelistList.Id`; use that Id to call `delete-vul-whitelist --id` for deletion — no need to query the whitelist list for the Id.

## Scan Target Scope Adjustment (modify-vul-target)

Purpose: when the user asks "stop scanning this machine", "remove a server from the vulnerability scan scope", or "add a removed server back to the scan scope", adjust the scan target of a specified vulnerability type (vulType: cve/sys/cms/emg) at the machine dimension via modify-vul-target.

Difference from the vulnerability whitelist (explain to the user before choosing): scan target adjustment is a **scan target configuration** (machine dimension — moving an entire server out of / back into the scan scope of a vulnerability type; once removed, that machine is no longer covered by scans of that type); the vulnerability whitelist is a **persistent per-CVE exclusion** (the vulnerability category is no longer reported, with optional asset scope — see the comparison table above). If a whole machine should not participate in a certain scan type (e.g., test machines), use modify-vul-target; to suppress only individual vulnerability categories, use the whitelist.

Write-operation confirmation gate (must be completed before execution): first present the change list to the user — target asset UUID (with name/IP), vulnerability type (vulType), operation direction (add back / del remove), impact description (after removal, that machine is no longer covered by scans of that vulnerability type — vulnerabilities cannot be detected or tracked) — execute only after explicit user confirmation.

Command example (add a server back to the Linux software vulnerability scan scope; write operation, requires user confirmation):

```bash
aliyun sas modify-vul-target --config '{"vulType":"cve"}' --target '[{"target":"<server-uuid>","targetType":"uuid","flag":"add"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- flag values: `add`=selected (add back to scan scope), `del`=deselected (remove from scan scope — "can you stop scanning this machine" uses del); the Target array supports multiple machines in one call.
- Full parameters (Config/Target structure) in references/api-reference.md section 4.10; after execution, verify the target configuration took effect with describe-vul-config (verification method in references/verification-method.md Scenario 4⑦).

## User Communication Key Points

- Mechanism explanation phrasing (plain version): "Vulnerability status is not real-time — it refreshes via periodic scans. System vulnerabilities are generally scanned every 1-2 days (depending on edition). And to prevent misjudgment, when the first scan doesn't find a vulnerability, the record is retained for a while before being cleared (3 days for system vulnerabilities, 30 days for application vulnerabilities). So seeing a stale status within hours of repair is normal."
- Pending-reboot explanation phrasing: "'Fixed-pending-reboot' means the patch is already installed. The new kernel/components only truly take effect after a reboot, and then a verification must be triggered for the status to become 'fixed'."
- Pre-reboot confirmation phrasing: "A reboot of this server is required before verification. Please confirm the workload can tolerate this reboot window (estimated X minutes of interruption)."
- Pre-full-scan confirmation phrasing: "A full scan initiates vulnerability scanning on all servers in the account. It usually completes within 30 minutes with small but existing workload impact. If you only care about a specific server, I suggest a targeted scan instead. Please confirm which to run?"
- Targeted scan boundary phrasing: "Only the server you specified will be scanned — other machines are unaffected."

## Notes and Boundaries

- **Scan hard gate**: targeted scans use only `modify-push-all-task` + UUIDs; `modify-start-vul-scan` is exclusively for full-account scans and never for specified-server scenarios.
- **Verification and scanning are different things**: vul_verify updates a single vulnerability's status; scanning is the process of rediscovering vulnerabilities. When the user says "re-verify", confirm their true intent first.
- **Write-operation confirmation**: verification, ignore, un-ignore, whitelist, targeted/full scans all require user confirmation; failures are not auto-retried.
- Item #8 old kernel uninstallation has boot risk — a snapshot and user confirmation are mandatory first; "fixed but still detected" on EOL systems may mean no patches are available — route to references/scenario-nonstandard.md Branch E.
- Non-Alibaba-Cloud servers do not support console reboot and rollback — related guidance in references/scenario-nonstandard.md Branch B.
- Numbers like scan cycles and retention days are subject to the latest official documentation — retrieval method in references/doc-lookup.md.

## Related Documents

- Command parameters and response fields: [references/api-reference.md](api-reference.md)
- Official FAQ and mechanism documentation retrieval: [references/doc-lookup.md](doc-lookup.md)
- Repair flow and pending-reboot closure: [references/scenario-repair.md](scenario-repair.md)
- Repair failure troubleshooting: [references/scenario-errors.md](scenario-errors.md)
- Non-standard systems (kernel/non-Alibaba-Cloud/EOL): [references/scenario-nonstandard.md](scenario-nonstandard.md)
- Scenario entry and boundary overview: [../SKILL.md](../SKILL.md)
