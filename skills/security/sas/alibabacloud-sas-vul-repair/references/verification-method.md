# Verification Method

Success criteria and verification commands for the five functional scenarios. Each scenario is organized as "success criteria → verification steps → verification commands"; commands can be copied and executed directly (`<placeholders>` are parameters to replace; `<session-id>` is the 32-char hex identifier of this session). All commands use aliyun CLI plugin mode and must carry `--user-agent`.

## Scenario 1: Vulnerability Query and Filtering

**Success criteria:**

1. The number of returned vulnerabilities matches the filter conditions (type, severity, status, and asset scope all consistent).
2. Pagination is normal: no duplicates or omissions across pages; the last page is correctly determined.
3. Detail drill-down is reachable: details of any vulnerability can be obtained (CVE ID, CVSS, repair suggestion, AVD link).

**Verification steps and commands:**

① Basic query (e.g., "high-severity unfixed Linux software vulnerabilities"):

```bash
aliyun sas describe-vul-list --type cve --necessity asap --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

② **Consistency spot-check — compare with a different filter set**: replace `--necessity asap` with `--necessity later` (or `--dealed n` with `y`, or `--type cve` with `--type sys`) and re-query; verify the two result sets do not overlap and each satisfies its filter semantics:

```bash
aliyun sas describe-vul-list --type cve --necessity later --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

③ Specified-asset filter recheck: limit assets with `--uuids <server-uuid>` and verify that `VulRecords[].Uuid` of all returned records equals that UUID:

```bash
aliyun sas describe-vul-list --type cve --uuids <server-uuid> --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

④ Pagination verification: fetch the next page with `--current-page 2` (PageSize unchanged) and verify no duplicates with page 1; if the returned count is less than PageSize or 0, it is the last page. When using NextToken mode (`--use-next-token true --next-token <NextToken-from-previous-response>`), note that **this mode does not return TotalCount** — determine the end by "returned count less than PageSize".

⑤ Detail drill-down (take any `Name` from the ① results):

```bash
aliyun sas describe-vul-details --type cve --name <vulnerability-name> --lang zh --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Verify the returned `Cves[]` contains complete `CveId`, `CvssScore`, `VulLevel` (serious/high/medium/low system), `Solution`, `CveLink` (AVD link), and they correspond to the list page's `AliasName`/`Related`.

**Common failure signals:** returned records contain fields contradicting the filter conditions (e.g., `--dealed n` returns Status=7 records); duplicate records across pages; the details API returns empty `Cves[]` (mostly a wrong Name — it must exactly match the list's returned `Name`, not `AliasName`).

## Scenario 2: Vulnerability Repair and Post-Fix Verification

**Success criteria:**

1. `modify-operate-vul` dispatch succeeds: a RequestId is returned and the vulnerability status enters transition.
2. Polling `describe-vul-list` shows Status transitioning as expected: **4 (fixing) → 7 (fixed) / 8 (fixed-pending-reboot) / 2 (fix failed)**, with Progress increasing in sync.
3. The Status=8 reboot closure is complete: reboot status transition is queryable → reboot succeeded → verification triggered → status finally becomes 7.

**Verification steps and commands:**

① Dispatch repair (write operation — present the change list and obtain user confirmation first):

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_fix --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval","isFront":0}]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: the response contains `RequestId` with no error code. If `InsufficientAuthorizationCount` / `UnauthorizedMachineNotSupportFix` / `UserInstanceVersionNotSupportFix` is returned, it is an unmet prerequisite (authorization count/binding/edition), not a command error — handle per the pre-fix chain.

② Poll repair status (recommended: run multiple times at 30-60 second intervals):

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --uuids <server-uuid> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: observe `Status` going from 1 → 4 (fixing, `Progress` increasing) → finally one of 7 / 8 / 2. Terminal state judgment:

| Terminal State | Meaning | Follow-up Action |
|------|------|----------|
| 7 | Fixed | Non-kernel vulnerabilities generally complete auto-detection; flow closed |
| 8 | Fixed-pending-reboot | Enter the ③ reboot closure |
| 2 | Fix failed | Route to Scenario 3 error code troubleshooting (read ResultCode/ResultMessage) |

③ **Reboot closure verification for Status=8**:

- Before reboot, prompt the user to confirm the reboot window (write operation). After reboot, query the reboot status:

```bash
aliyun sas describe-instance-reboot-status --uuids <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: `RebootStatus` transitions to `1` (reboot succeeded); if `2` (reboot failed), read `Code` (10001 command delivery failed / 10002 reboot failed / 10003 timeout) and `Msg` for further troubleshooting.

- After reboot succeeds, trigger re-verification (write operation — requires confirmation):

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_verify --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval","isFront":0}]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

- Poll ② again; success judgment: `Status` finally becomes **7** (fixed).

④ Repair statistics corroboration (optional):

```bash
aliyun sas describe-vul-fix-statistics --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Verify the increment of `FixTotal.FixedTodayNum` / `FixedTotalNum` matches this repair action.

**Common failure signals:** after dispatch, Status stays at 1 with no transition for a long time (mostly Agent offline — go back to describe-cloud-center-instances to check ClientStatus); polling shows 2 (route to Scenario 3).

## Scenario 3: Repair Failure Error Code Interpretation

**Success criteria:**

1. The `ResultCode`/`ResultMessage` obtained via `describe-vul-list` matches what the console's "Cause Details" displays.
2. After troubleshooting and handling per the error code table (see scenario-errors.md), the retry repair yields a definitive result (success transitions to 7/8, or the next-step action is provided).

**Verification steps and commands:**

① Fetch fix-failed records and error codes:

```bash
aliyun sas describe-vul-list --type cve --status-list 2 --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: records with `Status=2` have non-empty `ResultCode` (e.g., `8009`, `8037`) and `ResultMessage`; the codes match what the user sees in the console vulnerability details' "Cause Details" (cross-confirming data correctness).

② Locate handling actions per the error code (against scenario-errors.md's high-frequency error code table). For example, `ResultCode=8009` (official semantics "update process is running": YUM repository is not Alibaba Cloud, or a repair process is running) → guide enabling "prefer Alibaba Cloud repository" and retry after the repair process ends:

```bash
aliyun sas describe-vul-config --type yum --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

If `Config=off` is returned, enable it after user confirmation (write operation):

```bash
aliyun sas modify-vul-config --type yum --config on --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

③ After server-side handling completes, retry repair (back to Scenario 2 ①), using Scenario 2 ②'s polling result as the "retry result" evidence: transition to 7/8 closes the troubleshooting loop; still 2 means reading the new ResultCode and continuing to troubleshoot.

**Common failure signals:** explaining 8009 as "yum repository timeout" (official semantics is update process is running; repository timeout corresponds to Errno 12 Timeout and 202/9002/9007/9008 etc.); auto-retrying a write-operation failure without any troubleshooting (this skill forbids auto-retry of write-operation failures).

## Scenario 4: "Fixed but Still Detected" and Re-verification

**Success criteria:**

1. `vul_verify` dispatch succeeds; the vulnerability status shows the "6 (verifying)" transitional state, finally transitioning to 7 (confirmed fixed) or back to 1 (verification failed — vulnerability still exists).
2. If taking the scan path: the targeted scan task dispatches successfully and all subtasks complete (subtask Status=4).

**Verification steps and commands:**

① Query the current status to confirm the "fixed but still detected" fact:

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --uuids <server-uuid> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

② Trigger single-vulnerability re-verification (write operation — requires confirmation):

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_verify --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval","isFront":0}]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

③ Poll verification status transitions:

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --uuids <server-uuid> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: **Status briefly becomes 6 (verifying) → finally 7 (verification passed) or back to 1 (verification failed — still detected)**. When it returns to 1, continue per scenario-recheck.md's official cause troubleshooting table (kernel not rebooted, cache, scan severity, Agent offline — 11 items). Field-tested note (pitfall record): when triggering vul_verify on a vulnerability already at 7 (fixed), field tests show the transition 7 → 6 (about 1 minute) → back to 7 — it does not necessarily reach 12 (vulnerability does not exist); returning to 7 with the vulnerability no longer appearing in the unfixed list (no records with StatusList=1 query) can be judged as verification passed.

④ Scan path verification (for multi-vulnerability / whole-machine rechecks, choose targeted scan after user confirmation — **HARD GATE: specified servers use only modify-push-all-task; modify-start-vul-scan is exclusively for full scans**):

```bash
aliyun sas modify-push-all-task --uuids <server-uuid> --tasks OVAL_ENTITY,SYSVUL --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Dispatch success judgment: a RequestId is returned and `PushTaskRsp.PushTaskResultList` has no failure record for that server (or Online=true, Success=true). Field-tested note (pitfall record): a targeted task dispatched by `modify-push-all-task` may not immediately appear in the `describe-once-task` task list (initially only the schedule periodic task is visible — there is a registration delay). Judge dispatch success by PushTaskResultList; the task list is only auxiliary corroboration — do not judge dispatch failure just because it is absent from the list.

⑤ Scan task progress verification:

```bash
aliyun sas describe-once-task --task-type VUL_CHECK_TASK --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: the task's `TaskStatus` reaches `2` (completed), `Progress=100%`, and `FailCount` matches expectations. Then check subtasks per machine:

```bash
aliyun sas describe-vul-check-task-status-detail --task-ids <task-id> --types cve --uuid <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: all `TaskStatusList[].Status` are `4` (completed; transitional states: 0 unprocessed/1 collecting/2 collection complete/3 matching); on failure, read `Code` (e.g., push_command_failed — mostly Agent offline).

⑥ Emergency vulnerability re-check path (emg type; write operation requires confirmation):

```bash
aliyun sas modify-emg-vul-submit --name <emergency-vulnerability-name> --user-agreement yes --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
aliyun sas describe-emg-vul-item --vul-name <emergency-vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: `Status` goes from `10` (not detected) → `20` (detecting, `Progress` increasing) → `30` (detection completed).

⑦ Scan target scope adjustment path (modify-vul-target; write operation requires confirmation; used to move a server out of / back into the scan scope of a vulnerability type — difference explanation in scenario-recheck.md's "Scan Target Scope Adjustment" section):

```bash
aliyun sas modify-vul-target --config '{"vulType":"cve"}' --target '[{"target":"<server-uuid>","targetType":"uuid","flag":"del"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

After execution, verify the target configuration took effect with describe-vul-config:

```bash
aliyun sas describe-vul-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Success judgment: the modify-vul-target response contains `RequestId` with no error code; the configuration state of the corresponding vulnerability type in describe-vul-config's returned `TargetConfigs[]` matches this target change (i.e., the target configuration took effect). If the configuration did not change, verify the vulType/target/flag parameters, explain to the user, then retry (write-operation failures are not auto-retried).

**Common failure signals:** using modify-start-vul-scan with uuids for a "targeted scan" (violates the hard gate — that command triggers a full-account scan); Status stays at 6 for a long time after verification (Agent offline or task backlog — check ClientStatus and describe-once-task).

## Scenario 5: Manual Repair and Adaptation for Non-Standard Systems

**Success criteria:**

1. Environment judgment fields are read correctly and completely, serving as the basis for branch decisions.
2. The branch selection matches the explanation given to the user (which branch was chosen and why).
3. The manual repair commands provided to the user **come from the API-returned UpdateCmd or Solution** — not fabricated or written from memory.

**Verification steps and commands:**

① Read environment judgment fields (the sole basis for the five-branch decision):

```bash
aliyun sas describe-cloud-center-instances --machine-types ecs --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Check and record the following fields of the target asset item by item:

| Field | Branch Judgment Purpose |
|------|--------------|
| `Kernel` / `OsName` / `Os` | Self-compiled or non-standard kernel judgment (Branch A); EOL system judgment (Branch E) |
| `Vendor` / `Flag` / `VendorName` | 0 Alibaba Cloud / 1 other clouds / 2 IDC / 3+ other clouds (Branch B: non-Alibaba-Cloud machines do not support snapshot repair and rollback) |
| `AuthVersion` | 1 free edition (no repair capability) / 3/5/6/7 paid editions |
| `ClientStatus` / `ClientSubStatus` | online/offline/pause; uninstalled/stopped (offline routes to install-agent guidance) |

Success judgment: the environment conclusion restated to the user (e.g., "this machine is a non-Alibaba-Cloud asset with Vendor=1 and a self-compiled kernel") corresponds one-to-one with the raw field values above; filling gaps from experience when fields are missing is forbidden.

② Obtain manual repair commands (must come from the API response):

```bash
aliyun sas describe-vul-list --type cve --name <vulnerability-name> --uuids <server-uuid> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Take `ExtendContentJson.RpmEntityList[].UpdateCmd` (the repair command including package name and version); auxiliary check via `describe-can-fix-vul-list`'s `CanFix` (yes/no) and `CanUpdate` (true/false) (field-tested note: this API returned an empty list consistently in host-vulnerability scenarios — it can only be an optional auxiliary; an empty return does not mean unfixable — see the pitfall record in api-reference.md section 3.4):

```bash
aliyun sas describe-can-fix-vul-list --type cve --name <vulnerability-name> --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

For emg/app/sca types (console repair not supported), take the repair suggestion from details instead:

```bash
aliyun sas describe-vul-details --type <vulnerability-type> --name <vulnerability-name> --lang zh --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

Take `Cves[].Solution` as the manual repair guidance.

Success judgment: every server-side command given to the user can be traced to its source in the API responses of ①② (UpdateCmd or Solution); a vulnerability with CanFix=no must not be claimed "one-click repairable".

③ Closure after manual repair: guide the user to execute the commands on the server and confirm the result (e.g., verify the new kernel with `uname -av`, check package versions), then return to Scenario 4 (vul_verify or targeted scan) to trigger re-check, using Status transitioning to 7 as the final success criterion.

**Common failure signals:** defaulting to standard Alibaba Cloud ECS handling without reading Vendor/Kernel and other fields; promising console snapshot rollback capability for AWS/self-built machines (non-Alibaba-Cloud assets do not support it); the provided repair commands cannot be traced to any API response (fabricated commands).

## Generic Final Checks (all scenarios)

- Every executed command carries `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>` (missing = non-compliant execution).
- Every write operation (modify-*/operate-*/create-*/delete-*) has a change-list presentation and user confirmation record before execution; no auto-retry after failure.
- Every number and status value stated to the user can be traced to a specific response field of a specific command; untraceable conclusions must not be output (no fabrication).
