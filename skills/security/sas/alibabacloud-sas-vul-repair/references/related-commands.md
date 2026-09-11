# Complete Command Reference (related-commands)

All commands are `aliyun sas` subcommands (aliyun CLI plugin mode, lowercase-hyphenated names, corresponding to the Sas product 2018-12-03 OpenAPI). Every command that calls a cloud API [MUST] include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/{session-id}` (session-id is a 32-char lowercase hex value generated once at session start and reused for the entire session; local commands `aliyun configure` / `aliyun plugin` / `aliyun version` are excluded).

Scenario mapping: Scenario 1 query and filtering / Scenario 2 repair and verification / Scenario 3 error code troubleshooting / Scenario 4 "fixed but still detected" and re-verification / Scenario 5 non-standard systems.

## Read Operations (execute directly)

| Command | Purpose | Main Scenarios |
|---------|---------|----------------|
| `aliyun sas describe-vul-list` | Main vulnerability query entry: filter the vulnerability list by type (Type) / repair urgency (Necessity) / status (StatusList) / asset (Uuids, Remark); returns repair progress (Progress) and failure codes (ResultCode/ResultMessage) | Scenario 1 list query, Scenario 2 vulnerability info collection, Scenario 3 failure record location, Scenario 4 current status check |
| `aliyun sas describe-grouped-vul` | Grouped vulnerability query: aggregate by vulnerability to view affected asset counts and urgency distribution | Scenario 1 grouped statistics |
| `aliyun sas describe-cloud-center-instances` | Query asset information by conditions: get server UUID, client status (ClientStatus: online/offline/pause), authorization edition (AuthVersion), asset vendor (Vendor: 0 Alibaba Cloud / 1 non-cloud / 2 IDC), OS and kernel | All-scenario prerequisite: asset location and environment detection (Scenario 5 entry) |
| `aliyun sas describe-vul-details` | Query vulnerability details: summary, CVSS score, repair solution (Solution), CVE/AVD links | Scenario 1 detail drill-down |
| `aliyun sas describe-can-fix-vul-list` | Query fixable vulnerability list (cve/sca types only), with fixable (CanFix) / updatable (CanUpdate) flags and fix commands | Scenario 2 pre-fix assessment, manual repair path command retrieval |
| `aliyun sas describe-uuids-by-vul-names` | Get affected (fixable) machines by vulnerability name (including Level severity) | Scenario 2 asset scoping before batch repair |
| `aliyun sas describe-version-config` | Query purchased Security Center edition details: edition (Version), authorization count, expiration, vulnerability fix quota fields | Scenario 2 edition and quota pre-check |
| `aliyun sas describe-fix-used-count` | Query used vulnerability fix count for pay-as-you-go users (China / global regions) | Scenario 2 pay-as-you-go quota pre-check |
| `aliyun sas check-trial-fix-count` | Validate whether the trial version's remaining free fix count supports this repair, returns expected consumption (does not actually trigger repair) | Scenario 2 trial version pre-check |
| `aliyun sas describe-vul-fix-statistics` | Vulnerability fix statistics: pending, fixing, fixed today, fixed total | Scenario 2 repair result summary |
| `aliyun sas describe-vul-num-statistics` | Vulnerability count statistics by type | Scenario 1 overall overview |
| `aliyun sas describe-vul-config` | Query vulnerability management configuration: per-type scan switches, real-risk mode (scanMode), vulnerability retention period, prefer Alibaba Cloud repository (Type=yum) | Scenario 3 repository troubleshooting, Scenario 4 scan severity check |
| `aliyun sas describe-vul-whitelist` | Paginated query of the vulnerability whitelist | Scenario 4 whitelist check and maintenance |
| `aliyun sas describe-emg-vul-item` | Query emergency vulnerability information: risk status (RiskStatus), detection method (version check / network scan), detection status and progress | Scenario 4 emergency vulnerability recheck |
| `aliyun sas describe-vul-check-task-status-detail` | Query per-machine vulnerability scan subtask status (Status: 0 pending ~ 4 completed) | Scenario 4 scan progress polling |
| `aliyun sas describe-instance-reboot-status` | Query instance reboot status (RebootStatus: 0 rebooting / 1 success / 2 failed) | Scenario 2 pending-reboot closure tracking |
| `aliyun sas describe-once-task` | Query client task list (TaskType=VUL_CHECK_TASK for vulnerability scan task progress) | Scenario 2/4 task progress polling |
| `aliyun sas describe-front-vul-patch-list` | Query prerequisite patches that must be installed before fixing a Windows system vulnerability (Info needs isFront=1 when repairing) | Scenario 2 Windows repair pre-check |
| `aliyun sas list-vul-auto-repair-config` | Query vulnerability auto-repair configuration | Scenario 2 repair |

## Write Operations (require user confirmation)

| Command | Purpose | Main Scenarios |
|---------|---------|----------------|
| `aliyun sas modify-operate-vul` | Unified vulnerability operation entry: fix (vul_fix) / verify (vul_verify) / ignore (vul_ignore) / undo ignore (vul_undo_ignore) / delete (vul_delete); Info parameter is a JSON array (name/uuid/tag/isFront) | Scenario 2 repair and post-fix verification, Scenario 4 re-verification, ignore handling |
| `aliyun sas operate-vuls` | Batch fix Linux software vulnerabilities (Type fixed to cve, OperateType fixed to vul_fix, submitted by VulNames+Uuids) | Scenario 2 batch repair |
| `aliyun sas modify-start-vul-scan` | Trigger a full-account vulnerability one-click scan (covers all servers under the account). [HARD GATE] Full scans only — NEVER use for targeted scans of specific servers | Scenario 4 full rescan (requires user confirmation) |
| `aliyun sas modify-push-all-task` | Push targeted security check tasks to specified server UUIDs (check items include vulnerabilities OVAL_ENTITY/SYSVUL, baseline HEALTH_CHECK, etc.). The only correct command for targeted scans | Scenario 4 targeted scan |
| `aliyun sas modify-vul-config` | Modify vulnerability scan configuration: per-type detection switches, real-risk mode, prefer Alibaba Cloud repository (Type=yum, Config=on/off) | Scenario 3 repository handling, scan scope adjustment |
| `aliyun sas modify-vul-target` | Modify per-machine scan target settings: add (add) / remove (del) scan selection for target machines by vulnerability type (vulType) | Scenario 3/4 scan target adjustment |
| `aliyun sas modify-create-vul-whitelist` | Add vulnerability whitelist entry: persistent whitelist by vulnerability name (Whitelist JSON), optionally scoped to assets via TargetInfo (group or UUID) | Scenario 4 persistent ignore |
| `aliyun sas delete-vul-whitelist` | Delete a vulnerability whitelist entry (by whitelist ID or vulnerability info) | Scenario 4 whitelist maintenance |
| `aliyun sas modify-emg-vul-submit` | Run emergency vulnerability detection (requires user agreement, UserAgreement=yes) | Scenario 4 emergency vulnerability recheck |
| `aliyun sas create-vul-auto-repair-config` | Batch create the auto-fixable vulnerability list (auto-repair configuration for the Task Center vulnerability repair task) | Scenario 2 auto-repair configuration |
| `aliyun sas delete-vul-auto-repair-config` | Batch delete Task Center auto-repair configurations (by config ID list) | Scenario 2 auto-repair configuration maintenance |

## Additional Notes

- **Repair capability limits**: Emergency vulnerabilities (emg) and application vulnerabilities (app/sca) do not support one-click repair (vul_fix); `operate-vuls` supports cve only; the free edition (AuthVersion=1) has no repair capability
- **Scan hard gate**: Targeted scans (specific servers) use `modify-push-all-task` + UUID only; `modify-start-vul-scan` is for full-account scans after user confirmation only (consistent with the `alibabacloud-sas-install-agent` skill family)
- For parameter details of each command (required fields, types, enums, copyable examples), see [api-reference.md](api-reference.md)
