# Security Center Vulnerability Module API Reference (api-reference)

Static reference documentation for the vulnerability module APIs of Alibaba Cloud Security Center (SAS), referenced by the scenario documents and execution flows of this skill. All parameter information is subject to the official API documentation; content has been field-by-field verified against the official documentation (product Sas, version 2018-12-03).

## 1. Common Invocation Elements

| Element | Description |
|---------|-------------|
| Product | Sas (Security Center) |
| API version | 2018-12-03 |
| API style | RPC style |
| RegionId | RegionId is optional for most APIs. SAS is centrally deployed, so region is usually unnecessary — the region of the current aliyun CLI profile applies (some APIs have deprecated RegionId or use it only in specific scenarios such as container images). The SAS service only exposes two endpoints: cn-shanghai (China site) and ap-southeast-1 (International site); International-site accounts must ensure the CLI profile region points to the International site (or pass `--region ap-southeast-1` explicitly), otherwise requests resolve to the wrong site |
| Invocation format | aliyun CLI plugin mode: `aliyun sas <lowercase-hyphenated-command> [parameters]` (e.g., DescribeVulList → `aliyun sas describe-vul-list`) |
| OpenAPI online debug link | `https://api.aliyun.com/api/Sas/2018-12-03/<APIName>` (e.g., `https://api.aliyun.com/api/Sas/2018-12-03/DescribeVulList`) |
| Observability requirement | Every command that calls a cloud API must include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>`, where `<session-id>` is the 32-char lowercase hex string generated at session start. Local commands (configure/plugin/version) are excluded |
| Response field convention | Response fields cited in scenario document examples are subject to actual API response JSON; field casing follows this reference document |

**Unified example command format** (placeholders in angle brackets, replace and copy to execute):

```bash
aliyun sas describe-vul-list --type cve --necessity asap --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

## 2. API Overview

| CLI Command | API Name | Purpose | R/W | Main Scenarios |
|-------------|----------|---------|-----|----------------|
| describe-vul-list | DescribeVulList | Query vulnerability list by type and multi-dimensional filters (main query entry) | Read | Scenario 1 query, Scenario 2 repair polling, Scenario 3 error code retrieval, Scenario 4 status check |
| describe-grouped-vul | DescribeGroupedVul | Grouped statistics by vulnerability name (affected asset counts by urgency) | Read | Scenario 1 grouped statistics |
| describe-cloud-center-instances | DescribeCloudCenterInstances | Query asset (server) information, get UUID and other identifiers | Read | Scenario 1 asset location, Scenario 2 pre-check, Scenario 5 environment detection |
| describe-vul-details | DescribeVulDetails | Query vulnerability details (CVE/CVSS/repair solution/AVD links) | Read | Scenario 1 drill-down, Scenario 5 manual repair guidance |
| describe-can-fix-vul-list | DescribeCanFixVulList | Query fixable vulnerability list (CanFix/CanUpdate/fix commands) | Read | Scenario 2 fix feasibility, Scenario 5 manual repair commands |
| describe-uuids-by-vul-names | DescribeUuidsByVulNames | Get affected (fixable) machines by vulnerability name | Read | Scenario 1/2 machine location |
| describe-version-config | DescribeVersionConfig | Query purchased edition and quota (repair capability / pay-as-you-go switch) | Read | Scenario 2 edition pre-check |
| describe-fix-used-count | DescribeFixUsedCount | Query used vulnerability fix count for pay-as-you-go users | Read | Scenario 2 billing check |
| check-trial-fix-count | CheckTrialFixCount | Validate trial version remaining free fix count (does not trigger repair) | Read | Scenario 2 trial version pre-check |
| describe-vul-fix-statistics | DescribeVulFixStatistics | Vulnerability fix statistics (total and by type) | Read | Scenario 2 repair progress overview |
| describe-vul-num-statistics | DescribeVulNumStatistics | Vulnerability count statistics (by type and urgency) | Read | Scenario 1 statistics overview |
| describe-vul-config | DescribeVulConfig | Query vulnerability management configuration (scan switches / Alibaba Cloud repository etc.) | Read | Scenario 3 repository troubleshooting, Scenario 4 scan severity check |
| modify-vul-config | ModifyVulConfig | Modify vulnerability scan switch configuration | Write (confirm) | Scenario 3 enable "prefer Alibaba Cloud repository" |
| modify-vul-target | ModifyVulTarget | Modify per-machine scan scope switches | Write (confirm) | Scenario 4 detection scope adjustment |
| describe-vul-whitelist | DescribeVulWhitelist | Paginated query of the vulnerability whitelist | Read | Scenario 4 ignore/whitelist check |
| modify-create-vul-whitelist | ModifyCreateVulWhitelist | Add vulnerability whitelist entry | Write (confirm) | Scenario 4 persistent ignore |
| delete-vul-whitelist | DeleteVulWhitelist | Delete vulnerability whitelist entry | Write (confirm) | Scenario 4 undo persistent ignore |
| modify-emg-vul-submit | ModifyEmgVulSubmit | Run emergency vulnerability detection | Write (confirm) | Scenario 4 emergency vulnerability recheck |
| describe-emg-vul-item | DescribeEmgVulItem | Query emergency vulnerability information and detection status | Read | Scenario 4 emergency vulnerability status |
| describe-front-vul-patch-list | DescribeFrontVulPatchList | Query prerequisite patch list for Windows system vulnerabilities | Read | Scenario 2 Windows repair prerequisite |
| describe-once-task | DescribeOnceTask | Query client task (including vulnerability scan task) progress | Read | Scenario 4 scan task progress |
| describe-vul-check-task-status-detail | DescribeVulCheckTaskStatusDetail | Query per-machine vulnerability scan subtask status | Read | Scenario 4 scan subtask progress |
| describe-instance-reboot-status | DescribeInstanceRebootStatus | Query server reboot status | Read | Scenario 2 pending-reboot closure |
| modify-operate-vul | ModifyOperateVul | Unified vulnerability operation entry (fix/verify/ignore etc.) | Write (confirm) | Scenario 2 repair, Scenario 4 re-verification |
| operate-vuls | OperateVuls | Batch fix Linux software vulnerabilities (cve only) | Write (confirm) | Scenario 2 batch repair |
| modify-start-vul-scan | ModifyStartVulScan | Trigger one-click scan (full scans only) | Write (confirm) | Scenario 4 full rescan (requires user confirmation) |
| modify-push-all-task | ModifyPushAllTask | Push security check task to specified servers (targeted scan) | Write (confirm) | Scenario 4 targeted scan of specified servers |
| list-vul-auto-repair-config | ListVulAutoRepairConfig | Query created auto-repair configurations | Read | Scenario 2 auto-repair configuration check |
| create-vul-auto-repair-config | CreateVulAutoRepairConfig | Batch create auto-repair configurations | Write (confirm) | Scenario 2 auto-repair configuration |
| delete-vul-auto-repair-config | DeleteVulAutoRepairConfig | Delete auto-repair configurations | Write (confirm) | Scenario 2 auto-repair configuration removal |

> Note: `Type` terminology contract — `cve`=Linux software vulnerability, `sys`=Windows system vulnerability, `cms`=Web-CMS vulnerability (legacy type), `emg`=emergency vulnerability, `app`=application vulnerability (web scanner), `sca`=application vulnerability (software composition analysis). app and sca both appear under the console's "Application Vulnerabilities" tab.

---

## 3. Core API Details

### 3.1 describe-vul-list (DescribeVulList) — Main vulnerability query entry

Queries the vulnerability list by vulnerability type, supporting multi-dimensional filters by severity, status, asset, and handling state. It is the main entry for queries, repair polling, and error code retrieval.

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | Yes | Vulnerability type: `cve`=Linux software, `sys`=Windows system, `cms`=Web-CMS, `app`=application (web scanner), `emg`=emergency, `sca`=application (SCA) |
| StatusList | string | No | Status filter, comma-separated: `1` unfixed, `2` fix failed, `3` rollback failed, `4` fixing, `5` rolling back, `6` verifying, `7` fixed, `8` fixed-pending-reboot, `9` rollback succeeded, `10` ignored, `11` rollback-pending-reboot, `12` vulnerability does not exist, `20` expired |
| Necessity | string | No | Repair urgency, comma-separated: `asap`=high (fix ASAP), `later`=medium (can defer), `nntf`=low (no fix planned) |
| Dealed | string | No | Handling state: `y`=handled, `n`=unhandled |
| Uuids | string | No | Server UUIDs, comma-separated (obtainable via DescribeCloudCenterInstances) |
| Remark | string | No | Fuzzy filter by asset info: asset name, public IP, or private IP |
| Name | string | No | Vulnerability name |
| AliasName | string | No | Vulnerability alias |
| Ids | string | No | Vulnerability ID list, comma-separated, **up to 50** |
| AttachTypes | string | No | Additional vulnerability type when querying application vulnerabilities; fixed value `sca`. When querying Type=`app`, setting this also returns sca vulnerabilities; otherwise only app vulnerabilities are returned |
| GroupId | string | No | Asset group ID |
| TargetType | string | No | Asset type of the vulnerability: `k8s`=K8s component, `uuid`=server, `containerId`=container |
| ClusterId | string | No | Cluster ID |
| VpcInstanceIds | string | No | VPC instance IDs, comma-separated |
| CurrentPage | integer | No | Page number, default `1` |
| PageSize | integer | No | Items per page, default `10` |
| UseNextToken | boolean | No | Whether to use NextToken pagination: `true`/`false`. **TotalCount is not returned in this mode** |
| NextToken | string | No | Pagination token for NextToken mode; pass empty on the first request, then pass the previous response value |
| ResourceDirectoryAccountId | long | No | Resource Directory member account ID |
| RaspDefend | integer | No | Whether application protection (RASP) supports real-time protection for this vulnerability: `0` no, `1` yes |
| Lang | string | No | Language, default `zh` (Chinese), optional `en` |

**Key response fields:**

| Field | Description |
|-------|-------------|
| TotalCount | Total vulnerability count (not returned when UseNextToken=true) |
| NextToken | Pagination token for NextToken mode |
| VulRecords[].Status | Vulnerability status, same enum as the StatusList request parameter (1~12, 20) |
| VulRecords[].ResultCode / ResultMessage | Repair return code and message (troubleshooting basis when Status=2 fix failed; matches the console's "Cause Details") |
| VulRecords[].Progress | Vulnerability repair progress |
| VulRecords[].Online | Whether the asset Agent client is online (true/false) |
| VulRecords[].Bind | Whether the asset is bound to an authorization (true/false) |
| VulRecords[].AuthVersion | Asset authorization edition: `1` free, `3` enterprise, `5` advanced, `6` anti-virus, `7` ultimate, `10` value-added service edition |
| VulRecords[].Necessity | Repair urgency: asap/later/nntf |
| VulRecords[].Name / AliasName / Related | Vulnerability name / alias / related CVE list (comma-separated) |
| VulRecords[].Tag | Vulnerability tag (e.g., `oval`, `system`, `cms`; must be passed as Info.tag when repairing) |
| VulRecords[].Uuid / InstanceName / InstanceId / InternetIp / IntranetIp / RegionId | Asset identifier information |
| VulRecords[].FirstTs / LastTs / ModifyTs / RepairTs | First detected / last detected / status changed / repaired timestamps (milliseconds) |
| VulRecords[].OsName / OsVersion | Asset OS name and version |
| VulRecords[].ExtendContentJson.RpmEntityList[].UpdateCmd | Manual repair command (basis for manual repair in non-standard environments) |
| VulRecords[].ExtendContentJson.RpmEntityList[].Name / Version / FullVersion / Path | Affected package name / version / full version / path |
| VulRecords[].ExtendContentJson.Necessity.Total_score | Vulnerability repair urgency score: 13.5~15 usually high risk, 7~13.5 medium risk, below 7 low risk |
| VulRecords[].PrimaryId | Vulnerability ID (usable for exact filtering via the Ids parameter) |
| RequestId | Request ID |

**Example:**

```bash
aliyun sas describe-vul-list --type cve --necessity asap --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.2 modify-operate-vul (ModifyOperateVul) — Unified vulnerability operation entry

Handles detected vulnerabilities: fix, verify, ignore, undo ignore, delete. **Write operation — MUST obtain user confirmation before execution.**

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Info | string | Yes | Vulnerability information to process, a JSON array string; each item contains: `name` (vulnerability name), `uuid` (server UUID), `tag` (vulnerability tag: `oval`=Linux software, `system`=Windows system, `cms`=Web-CMS), `isFront` (whether the Windows patch is a prerequisite patch: `0` no, `1` yes; set only for Windows system vulnerabilities, ignorable for other types). Supports batch processing; multiple entries comma-separated |
| OperateType | string | Yes | Operation: `vul_fix`=repair, `vul_verify`=verify, `vul_ignore`=ignore, `vul_undo_ignore`=undo ignore, `vul_delete`=delete |
| Type | string | Yes | Vulnerability type: `cve`, `sys`, `cms`, `emg`, `app`, `sca`. **Emergency vulnerabilities (emg), application vulnerabilities (app), and SCA vulnerabilities (sca) do NOT support the repair (vul_fix) operation** |
| Reason | string | No | Ignore reason; set only when OperateType=`vul_ignore` |
| From | string | No | Request source identifier; fixed to `sas` |

**Key response fields:**

| Field | Description |
|-------|-------------|
| RequestId | Request ID; returned upon successful submission |

**Error codes (the three authorization-related codes are pre-fix check items):**

| Error Code | Description |
|------------|-------------|
| InsufficientAuthorizationCount | Insufficient fix authorization count; purchase more fix quota |
| UnauthorizedMachineNotSupportFix | Machines not bound to an authorization do not support vulnerability repair |
| UserInstanceVersionNotSupportFix | The user instance edition does not support vulnerability repair |
| NoPermission | The current operation is not authorized; the main account must grant permissions in the RAM console |
| ServerError | Service failure; retry later |

**Example:**

```bash
aliyun sas modify-operate-vul --type cve --operate-type vul_fix --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval","isFront":0}]' --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

> **Field-tested notes**: (1) The `name` in the Info JSON is the vulnerability **record name** from DescribeVulList/DescribeGroupedVul — for Linux cve vulnerabilities this is typically an OVAL-style advisory name (e.g., `alilinux3:3:ALINUX3-SA-2026:0223`), **not** the CVE ID; always take it from the queried record. (2) For repairing vulnerabilities on specific hosts, agents commonly use modify-operate-vul instead of operate-vuls — both are valid repair channels documented in SKILL.md; operate-vuls is the batch-oriented alternative (cve only).

### 3.3 describe-cloud-center-instances (DescribeCloudCenterInstances) — Asset query and UUID source

Queries asset (server) information by search conditions. It is the unified entry for getting server UUID, OS, kernel, Agent status, and authorization edition. Supports both pagination and NextToken modes (NextToken recommended).

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Criteria | string | No | Search conditions, JSON format (case-sensitive), e.g., `[{"name":"riskStatus","value":"YES"},{"name":"internetIp","value":"1.2.XX.XX"}]`; supports instance ID, instance name, VPC ID, region, public IP, etc. (use DescribeCriteria to query supported condition names). **Field-tested note (pitfall record): `uuid` as a Criteria condition name may not take effect (returns all instances instead of filtered results); to look up a single asset by exact UUID, fetch pages without Criteria and filter locally with jq: `jq '.Instances[] \| select(.Uuid=="<UUID>")'`** |
| MachineTypes | string | No | Asset type: `ecs`=server, `cloud_product`=cloud product, `eci`=elastic container instance, `rund`=RunD container instance, `runc`=RunC container instance |
| LogicalExp | string | No | Logical relation between multiple search conditions; default `OR`, optional `AND` |
| Importance | integer | No | Asset importance: `2`=important, `1`=general, `0`=test |
| Flags | string | No | Asset vendor, comma-separated: `0`=Alibaba Cloud, `1`=non-cloud, `2`=IDC, `3`/`4`/`5`/`7`/`14`/`16`=other clouds, `8`=lightweight, `9`=SAE, `10`=PAI |
| CurrentPage | integer | No | Page number, default `1` |
| PageSize | integer | No | Items per page, default `20` |
| UseNextToken | boolean | No | Whether to use NextToken mode: `true`/`false`; TotalCount not returned in this mode |
| NextToken | string | No | Pagination token; pass empty on the first request |
| ResourceDirectoryAccountId | integer | No | Resource Directory member account ID |
| Lang | string | No | Language, default `zh` |
| NoGroupTrace | boolean | No | Whether to internationalize the default "Ungrouped" group; default `false` |
| RegionId | string | No | Deprecated; do not set |

**Key response fields:**

| Field | Description |
|-------|-------------|
| Instances[].Uuid | Instance UUID (required parameter for vulnerability queries and repair operations) |
| Instances[].InstanceName / InstanceId / InternetIp / IntranetIp / RegionId / RegionName | Asset identifier information |
| Instances[].Os / OsName / Kernel | OS / OS version / kernel version (basis for non-standard environment detection) |
| Instances[].ClientStatus | Agent client online status: `online`, `offline`, `pause` (protection paused) |
| Instances[].ClientSubStatus | Agent client sub-status: `online`/`offline`/`pause`/`uninstalled`/`stopped` (server shut down) |
| Instances[].Bind / AuthVersion / AuthVersionName | Whether bound to authorization / authorization edition (`1` free, `6` anti-virus, `5` advanced, `3` enterprise, `7` ultimate) / edition name |
| Instances[].Vendor / VendorName / Flag | Asset vendor: `0` Alibaba Cloud, `1` non-cloud, `2` IDC, `3`/`4`/`5`/`7`/`14`/`16` other clouds, `8` lightweight, `9` SAE, `10` PAI |
| Instances[].VulCount / VulStatus | Vulnerability count / whether vulnerabilities exist (YES/NO) |
| Instances[].RiskCount | Risk item statistics JSON (including asapVulCount high-risk count, cveNum, sysNum, cmsNum, emgNum, scaNum, appNum, etc.) |
| Instances[].Status / Importance / GroupId / GroupTrace | Running status (Running/notRunning) / importance / group |
| PageInfo.TotalCount / Count / NextToken | Total / current page count / pagination token |

**Example:**

```bash
aliyun sas describe-cloud-center-instances --machine-types ecs --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.4 describe-can-fix-vul-list (DescribeCanFixVulList) — Fixable vulnerability query

Queries the fixable vulnerability list to determine whether a vulnerability can be repaired via the console and to obtain fix commands. **Supports Type=`cve`/`sca` only.**

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | Yes | Vulnerability type, supports only: `cve`=Linux software, `sca`=application (SCA) |
| StatusList | string | No | Repair status filter, **supports only `1`=unfixed, `4`=fixing, `7`=fixed** |
| Necessity | string | No | Repair urgency: `asap`/`later`/`nntf`, comma-separated |
| Dealed | string | No | Handling state: `y`=handled, `n`=unhandled |
| Name | string | No | Vulnerability name |
| AliasName | string | No | Vulnerability alias |
| Uuids | string | No | Image UUIDs, comma-separated |
| CurrentPage | integer | No | Page number, default `1` |
| PageSize | integer | No | Items per page, default `20` |
| Other container/image parameters | - | No | RepoRegionId, RepoInstanceId, RepoId, RepoName, RepoNamespace, RegionId, InstanceId, Tag, Digest, ClusterId, ScanRange (image/container), ClusterName, ContainerId, Pod, Namespace, Image, etc.; container image scan scenarios only, generally not involved in host vulnerability repair |

**Key response fields:**

| Field | Description |
|-------|-------------|
| VulRecords[].CanFix | Whether console repair is possible: `yes`/`no` |
| VulRecords[].CanUpdate | Whether the vulnerable package supports upgrade via Security Center: `true`/`false` |
| VulRecords[].ExtendContentJson.RpmEntityList[].UpdateCmd | Vulnerability repair command (e.g., `apt-get update && apt-get install libseccomp2 --only-upgrade`) |
| VulRecords[].ExtendContentJson.RpmEntityList[].Name / Version / FullVersion / Path | Affected package information |
| VulRecords[].Status | Repair status (1/4/7) |
| VulRecords[].Name / AliasName / Necessity / Related / Uuid / FirstTs / LastTs | Basic vulnerability and asset information |

**Example:**

```bash
aliyun sas describe-can-fix-vul-list --type cve --status-list 1 --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

> Field-tested note (pitfall record): In host vulnerability scenarios this API was observed to **return no host vulnerability records at all** — querying by unfixed (StatusList=1) or fixed (StatusList=7), with or without Uuids, returns `VulRecords: []` (and no TotalCount field); the parameter table describes Uuids as "image UUID", suggesting this API mainly targets container image scenarios. Therefore: never treat an empty response as "no fixable vulnerabilities", and never use it to judge fixability; host vulnerability queries and fixability determinations must use describe-vul-list records and check-trial-fix-count's CanFix exclusively.

### 3.5 describe-vul-details (DescribeVulDetails) — Vulnerability details

Queries vulnerability details including CVE IDs, CVSS scores, repair solutions, and Alibaba Cloud Vulnerability Database (AVD) links. Only non-deprecated fields are cited.

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Lang | string | Yes | Language: `zh`=Chinese, `en`=English |
| Type | string | Yes | Vulnerability type: `cve`, `sys`, `cms`, `app`, `emg`, `sca` |
| Name | string | Yes | Vulnerability name (obtainable via DescribeVulList or DescribeGroupedVul) |
| AliasName | string | No | Vulnerability bulletin alias |
| ResourceDirectoryAccountId | integer | No | Resource Directory member account ID |

**Key response fields (non-deprecated only):**

| Field | Description |
|-------|-------------|
| Cves[].Title | Vulnerability bulletin title |
| Cves[].Summary | Vulnerability summary |
| Cves[].Solution | Vulnerability repair solution (one source of manual repair guidance) |
| Cves[].CvssScore / CvssVector | AVD CVSS score / CVSS score vector |
| Cves[].VulLevel | Vulnerability severity level: `serious`, `high`, `medium`, `low`. **Note: this system differs from Necessity (asap/later/nntf); do not mix them** |
| Cves[].CveId / CveLink | CVE ID / CVE vulnerability detail link (AVD, e.g., `https://avd.aliyun.com/detail/CVE-2022-1184`) |
| Cves[].Reference | Vulnerability reference link in the Alibaba Cloud vulnerability database |
| Cves[].ReleaseTime | Vulnerability disclosure timestamp (milliseconds) |
| Cves[].Classify / Classifys[] | Vulnerability classification (e.g., remote_code_execution) and classification list |
| Cves[].OtherId | Other vulnerability IDs |
| RequestId | Request ID |

**Example:**

```bash
aliyun sas describe-vul-details --type cve --name <vulnerability-name> --lang zh --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.6 operate-vuls (OperateVuls) — Batch fix Linux software vulnerabilities

Batch fixes Linux software vulnerabilities. **Type is fixed to `cve` and OperateType is fixed to `vul_fix`**; use modify-operate-vul for other vulnerability types. Write operation — MUST obtain user confirmation before execution.

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | Yes | Fixed value `cve` (Linux software vulnerabilities) |
| OperateType | string | Yes | Fixed value `vul_fix` (repair) |
| VulNames | array | Yes | List of vulnerability names to fix (repeatable same-name parameter in the CLI) |
| Uuids | array | Yes | List of server UUIDs to fix (repeatable same-name parameter in the CLI) |

**Key response fields:**

| Field | Description |
|-------|-------------|
| RequestId | Request ID |

**Error codes:** operateVulError (operation error), InsufficientAuthorizationCount (insufficient fix quota), NoPermission, ServerError.

**Example:**

```bash
aliyun sas operate-vuls --type cve --operate-type vul_fix --vul-names <vulnerability-name-1> --vul-names <vulnerability-name-2> --uuids <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.7 modify-start-vul-scan (ModifyStartVulScan) — One-click scan (full scans only)

Starts the one-click scan feature of the console vulnerability management page. **Note: this command is for full scans ONLY; targeted scans of specified servers MUST use modify-push-all-task (targeted scan hard gate).** Write operation — MUST obtain user confirmation before execution.

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Types | string | No | Vulnerability types detected by the one-click scan, comma-separated: `cve`=Linux software, `sys`=Windows system, `cms`=Web-CMS, `app`=application (web scanner), `emg`=emergency, `image`=container image, `sca`=application (SCA). Empty detects all types |
| Uuids | string | No | Server UUID list, comma-separated (obtainable via DescribeCloudCenterInstances). Passing this parameter does NOT change the full-scan semantics — never rely on it for targeted scans (the only targeted entry is modify-push-all-task) |

**Key response fields:**

| Field | Description |
|-------|-------------|
| RequestId | Request ID |

**Example (full scan):**

```bash
aliyun sas modify-start-vul-scan --types cve,sys --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.8 modify-push-all-task (ModifyPushAllTask) — Targeted security check task push

Pushes security check tasks to specified asset servers in one click. It is the correct entry for targeted scans (including vulnerability detection) of specified servers. Write operation — MUST obtain user confirmation before execution.

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Uuids | string | Yes | Server UUID list for the security check, comma-separated |
| Tasks | string | Yes | Check item list, comma-separated: `OVAL_ENTITY`=CVE vulnerabilities, `CMS`=CMS vulnerabilities, `SYSVUL`=system vulnerabilities, `SCA`=application vulnerabilities, `HEALTH_CHECK`=baseline, `WEBSHELL`=web shells, `PROC_SNAPSHOT`=processes, `PORT_SNAPSHOT`=ports, `ACCOUNT_SNAPSHOT`=accounts, `SOFTWARE_SNAPSHOT`=software, `SCA_SNAPSHOT`=middleware/databases/web services, `CROND_SNAPSHOT`=scheduled tasks, `AUTORUN_SNAPSHOT`=startup items, `LKM_SNAPSHOT`=kernel modules, `SCA_PROXY_SNAPSHOT`=web sites |
| SourceIp | string | No | Source IP address of the access |

**Key response fields:**

| Field | Description |
|-------|-------------|
| RequestId | Request ID |
| PushTaskRsp.PushTaskResultList[] | Servers where the security check task failed: Uuid, Success (true/false), Online (client online state), Message (failure details), InstanceName, Ip, OsVersion, InstanceId, Region, GroupId |

**Error codes:** PushTaskError (task push failed), IllegalParam (invalid parameter), FreeVersionNotPermit (free edition not allowed), NoPermission, ServerError.

**Example (targeted vulnerability scan of a specified server):**

```bash
aliyun sas modify-push-all-task --uuids <server-uuid> --tasks OVAL_ENTITY,SYSVUL --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.9 describe-vul-check-task-status-detail (DescribeVulCheckTaskStatusDetail) — Scan subtask status

Queries the subtask status of the vulnerability scan task for a specified machine (scan progress tracking).

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| TaskIds | array | Yes | Task ID list (repeatable same-name parameter in the CLI) |
| Types | array | Yes | Vulnerability type list corresponding to the one-click scan: `cve`, `sys`, `cms`, `sca` |
| Uuid | string | Yes | Server UUID to query |

**Key response fields:**

| Field | Description |
|-------|-------------|
| TaskStatuses[].TaskId | Main task ID |
| TaskStatuses[].TaskStatusList[].Type | Subtask vulnerability type (cve/sys/cms/sca) |
| TaskStatuses[].TaskStatusList[].Status | Subtask status: `0`=pending, `1`=collecting, `2`=collection complete, `3`=matching, `4`=completed |
| TaskStatuses[].TaskStatusList[].Code | Failure code (e.g., `push_command_failed`) |
| TotalCount | Total number of vulnerability subtasks for the machine |
| RequestId | Request ID |

**Example:**

```bash
aliyun sas describe-vul-check-task-status-detail --task-ids <task-id> --types cve --uuid <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 3.10 describe-instance-reboot-status (DescribeInstanceRebootStatus) — Instance reboot status

Queries the reboot status of servers (closure query after Status=8 fixed-pending-reboot).

**Request parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Uuids | string | Yes | Server UUIDs to query reboot status for, comma-separated |

**Key response fields:**

| Field | Description |
|-------|-------------|
| RebootStatuses[].Uuid | Server UUID |
| RebootStatuses[].RebootStatus | Reboot status: `0`=rebooting, `1`=reboot succeeded, `2`=reboot failed |
| RebootStatuses[].Code | Reboot failure error code: `10001`=command dispatch failed, `10002`=reboot failed, `10003`=timeout |
| RebootStatuses[].Msg | Reboot exception message |
| TotalCount | Total number of returned records |
| RequestId | Request ID |

**Example:**

```bash
aliyun sas describe-instance-reboot-status --uuids <server-uuid> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

---

## 4. Compact API Reference

### 4.1 describe-grouped-vul (DescribeGroupedVul) — Grouped statistics

Grouped statistics by vulnerability (name): affected machine counts per vulnerability aggregated by repair urgency, including handled counts.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | No | Vulnerability type, default `cve`: cve/sys/cms/app/sca |
| Necessity | string | No | Repair urgency: asap/later/nntf, comma-separated |
| Dealed | string | No | `y`=handled, `n`=unhandled |
| Uuids | string | No | Server UUIDs, comma-separated |
| AliasName / CveId | string | No | Vulnerability alias / CVE ID |
| GroupId | string | No | Asset group ID |
| SearchTags | string | No | Filter by tag: reboot required, remote exploit, EXP exists, exploitable, local privilege escalation, code execution |
| AttachTypes | string | No | Application vulnerabilities only: `sca`/`app` |
| CurrentPage / PageSize | integer | No | Pagination, default 1 / 10 |

**Key response fields:** GroupedVulItems[] (Name, AliasName, AsapCount/LaterCount/NntfCount asset counts per urgency, HandledCount handled count, TotalFixCount total fixed, GmtFirst/GmtLast first/last detected time, Related related CVEs, Tags, Type, LanguageType sca-only java/php).

**Example:**

```bash
aliyun sas describe-grouped-vul --type cve --necessity asap --dealed n --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.2 describe-uuids-by-vul-names (DescribeUuidsByVulNames) — Machines by vulnerability name

Gets the list of affected (fixable) machines by vulnerability name.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | Yes | Vulnerability type: `cve`=Linux software, `sys`=Windows system |
| VulNames | array | Yes | Vulnerability name set (repeatable same-name parameter in the CLI; obtainable via DescribeGroupedVul) |
| StatusList | string | No | Repair status: `1`=unfixed, `2`=fix failed |
| Level | string | No | Vulnerability severity: `high`, `medium`, `low`. **Note: this system differs from Necessity (asap/later/nntf); do not mix them** |
| Necessity | string | No | Repair urgency: asap/later/nntf |
| Dealed / Remark / GroupId / VpcInstanceIds | - | No | Handling state / asset fuzzy condition (name or IP, fuzzy supported) / group / VPC instance IDs |

**Key response fields:** MachineInfoStatistics[] (Uuid, MachineName, MachineIp, InternetIp, IntranetIp, Os, RegionId, MachineInstanceId), VulCount.

**Example:**

```bash
aliyun sas describe-uuids-by-vul-names --type cve --vul-names <vulnerability-name> --status-list 1 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.3 describe-version-config (DescribeVersionConfig) — Edition and quota

Views the edition details of the purchased Security Center instance (repair capability pre-check).

**Key parameters:** SourceIp (No), ResourceDirectoryAccountId (No). Generally invoke without parameters.

**Key response fields:**

| Field | Description |
|-------|-------------|
| Version / HighestVersion | Purchased edition / highest edition: `1` free, `3` enterprise, `5` advanced, `6` anti-virus, `7` ultimate, `8` multi-edition, `10` value-added services only |
| VulFixCapacity | Purchased vulnerability fix count (times/month) |
| IsPostpay / PostPayModuleSwitch | Whether pay-as-you-go is enabled / pay-as-you-go module switch JSON (`{"VUL":1}` means the vulnerability fix module is on; VUL/CSPM/AGENTLESS/SERVERLESS/CTDR/POST_HOST/SDK/RASP) |
| PostPayStatus | Pay-as-you-go instance status: `1`=normal, `2`=stopped due to arrears |
| AssetLevel / InstanceId / ReleaseTime / OpenTime | Purchased server authorization count / instance ID / expiration time / open time (millisecond timestamps) |
| IsTrialVersion | Whether trial version: `0`=not trial, `1`=trial |

**Example:**

```bash
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.4 describe-fix-used-count (DescribeFixUsedCount) — Used fix count

Queries the used vulnerability fix count for pay-as-you-go users.

**Parameters:** None.

**Key response fields:** UsedCount (total used), UsedCountCn (China region), UsedCountSg (global excluding China), RequestId.

**Example:**

```bash
aliyun sas describe-fix-used-count --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.5 check-trial-fix-count (CheckTrialFixCount) — Trial fix count validation

Validates whether the trial version user's remaining free fix count supports this repair and returns the expected consumption. **Validation only — does not actually trigger repair.**

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | Yes | Vulnerability type: `cve`, `sys`, `cms` |
| Info | string | No | Vulnerability info JSON array (fields same as modify-operate-vul's Info: name/uuid/tag). **Pass via Info or via the VulNames+Uuids combination — choose one** |
| VulNames / Uuids | array | No | Vulnerability name list / server UUID list |

**Key response fields:** isTrial (whether trial version), CanFix (whether repair is supported), ExpendCount (expected consumption this time), RemainCount (remaining count after validation passes), RepairedCount (already repaired count).

**Example:**

```bash
aliyun sas check-trial-fix-count --type cve --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"oval"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.6 describe-vul-fix-statistics (DescribeVulFixStatistics) — Fix statistics

Gets vulnerability fix statistics (total and by type).

**Parameters:** None.

**Key response fields:** FixTotal (FixingNum fixing, FixedTodayNum fixed today, FixedTotalNum total fixed, NeedFixNum pending), FixStat[] (Type: cve/sys/cms/app/emg + same four fields).

**Example:**

```bash
aliyun sas describe-vul-fix-statistics --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.7 describe-vul-num-statistics (DescribeVulNumStatistics) — Vulnerability count statistics

Gets full vulnerability count statistics (by type and urgency).

**Key parameters:** From (No; set to `sas` when querying Security Center data), ResourceDirectoryAccountId (No).

**Key response fields:** CveNum (Linux system vulnerabilities), SysNum (Windows system vulnerabilities), CmsNum (Web-CMS vulnerabilities), AppNum (scanner application vulnerabilities), ScaNum (middleware/SCA vulnerabilities), EmgNum (emergency vulnerabilities), VulAsapSum/VulLaterSum/VulNntfSum (high/medium/low urgency counts).

> Note: The official authorization Action for this API is `yundun-aegis:DescribeVulNumStatistics` (see the exception notes in ram-policies.md).

**Example:**

```bash
aliyun sas describe-vul-num-statistics --from sas --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.8 describe-vul-config (DescribeVulConfig) — Vulnerability management configuration query

Queries vulnerability management configuration (per-type scan switches, Alibaba Cloud repository switch, real-risk mode, vulnerability retention period).

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | No | Configuration type; omit to query all types: `cve`, `sys`, `cms`, `app`, `emg`, `scanMode`=show real-risk vulnerabilities, `imageVulClean`=vulnerability retention period, `yum`=prefer Alibaba Cloud repository for vulnerability repair |

**Key response fields:** TargetConfigs[] (Type, OverAllConfig global switch on/off, Config: on/off for types cve/sys/cms/app/emg/yum; for scanMode: `real`=real-risk vulnerabilities only / `all`=all vulnerabilities; for imageVulClean: retention days).

**Example:**

```bash
aliyun sas describe-vul-config --type yum --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.9 modify-vul-config (ModifyVulConfig) — Modify scan switch configuration [Write]

Modifies vulnerability scan switch configuration. Write operation — MUST obtain user confirmation before execution.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | No | Vulnerability type to modify: `cve`, `sys`, `cms`, `emg`, `app`, `yum`=YUM/APT repository configuration, `scanMode`=real risk |
| Config | string | No | `on`=enable, `off`=disable; when Type is scanMode the values are `real`=real-risk vulnerabilities, `all`=all vulnerabilities |

**Key response fields:** RequestId.

**Example (enable "prefer Alibaba Cloud repository"):**

```bash
aliyun sas modify-vul-config --type yum --config on --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

> **Field-tested note**: the yum "prefer Alibaba Cloud repository" setting is idempotent — writing `on` when it is already `on` has no side effects. When describe-vul-config shows the desired state is already achieved, a compliant agent may legitimately skip the write as a no-op guard; if the user explicitly asks to apply the setting anyway (e.g., to guarantee effect), execute the write regardless of current state.

### 4.10 modify-vul-target (ModifyVulTarget) — Modify scan machine scope [Write]

Modifies per-machine scan switch settings. Write operation — MUST obtain user confirmation before execution.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Config | string | No | Configuration target, JSON format, including `vulType` (vulnerability type: `cve`, `sys`, `cms`, `emg`), e.g., `{"vulType":"sys"}` |
| Target | string | No | Operation targets, JSON array; each item includes `target` (target machine UUID), `targetType` (fixed `uuid`), `flag` (`add`=select, `del`=deselect) |

**Key response fields:** RequestId.

**Example:**

```bash
aliyun sas modify-vul-target --config '{"vulType":"sys"}' --target '[{"target":"<server-uuid>","targetType":"uuid","flag":"add"}]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.11 describe-vul-whitelist (DescribeVulWhitelist) — Vulnerability whitelist query

Paginated query of the vulnerability whitelist.

**Key parameters:** CurrentPage (default 1), PageSize (default 10), Lang.

**Key response fields:** VulWhitelists[] (Id rule ID, Name vulnerability name, AliasName alias, Type, Reason whitelist reason, TargetInfo applicable scope JSON: type=Uuid/GroupId + uuids/groupIds, empty means all assets, Whitelist vulnerability info JSON), TotalCount.

**Example:**

```bash
aliyun sas describe-vul-whitelist --current-page 1 --page-size 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.12 modify-create-vul-whitelist (ModifyCreateVulWhitelist) — Add whitelist entry [Write]

Adds a vulnerability whitelist entry; whitelisted vulnerabilities no longer appear in the alert list (persistent ignore at the vulnerability level, optionally scoped to assets). Write operation — MUST obtain user confirmation before execution.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Whitelist | string | Yes | Whitelist vulnerability info JSON array; fields: Status, GmtLast, LaterCount, AsapCount, Name (vulnerability name), Type (cve/sys/cms/app/emg), Related (related CVEs), HandledCount, AliasName, RuleModifyTime, NntfCount, TotalFixCount, Tags. Obtain these fields via DescribeGroupedVul |
| Reason | string | No | Reason for adding to the whitelist |
| TargetInfo | string | No | Effective scope JSON: `type` (`GroupId`=server group / `Uuid`=host asset) + `groupIds` (Long set) + `uuids` (String set). Empty means all hosts; when type=GroupId groupIds must not be empty, when type=Uuid uuids must not be empty |

**Key response fields:** RequestId; VulWhitelistList.Id (returned only when adding or updating a single whitelist entry).

**Example:**

```bash
aliyun sas modify-create-vul-whitelist --whitelist '[{"Status":0,"Name":"<vulnerability-name>","Type":"cve","AliasName":"<vulnerability-alias>","AsapCount":1,"LaterCount":0,"NntfCount":0,"Related":"<related-cve>","HandledCount":1,"GmtLast":<last-detected-timestamp>,"RuleModifyTime":<publish-timestamp>,"TotalFixCount":0,"Tags":"<tags>"}]' --reason <whitelist-reason> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

> **Field-tested notes (persistence depends on whether the vulnerability name is known to the account's vulnerability library)**:
> 1. **Unknown / fabricated vulnerability name**: the call returns success with a `VulWhitelistList.Id`, but the entry is **not persisted** — DescribeVulWhitelist returns empty, and DeleteVulWhitelist with the returned Id fails with VulWhitelistNotExist. Always build the Whitelist JSON from a real record obtained via DescribeGroupedVul / DescribeVulList.
> 2. **Real vulnerability name**: the entry persists even when the vulnerability is already fixed or the Whitelist JSON contains placeholder field values.
> 3. **Vulnerability fully absent from the library** (e.g., consumed by a prior fix and no longer reported by describe-vul-details / describe-vul-list / describe-grouped-vul — all 0 hits): creation fails with **HTTP 400 InnerError**; retrying does not help — the vulnerability record must be re-detected first.

### 4.13 delete-vul-whitelist (DeleteVulWhitelist) — Delete whitelist entry [Write]

Deletes a specified vulnerability whitelist entry. Write operation — MUST obtain user confirmation before execution.

**Key parameters:** Id (No; whitelist ID, obtainable via DescribeVulWhitelist) or Whitelist (No; whitelist info JSON to delete: Name, Type, AliasName).

**Key response fields:** RequestId.

**Example:**

```bash
aliyun sas delete-vul-whitelist --id <whitelist-id> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.14 modify-emg-vul-submit (ModifyEmgVulSubmit) — Emergency vulnerability detection [Write]

Runs emergency vulnerability detection (re-initiates detection for a specified emergency vulnerability). Write operation — MUST obtain user confirmation before execution.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Name | string | Yes | Emergency vulnerability name |
| UserAgreement | string | Yes | Whether to run detection: **`yes`=run**, `no`=do not run (re-detection must use yes) |
| Lang | string | No | Language, default zh |
| ResourceDirectoryAccountId | integer | No | Resource Directory member account ID |

**Key response fields:** RequestId.

**Example:**

```bash
aliyun sas modify-emg-vul-submit --name <emergency-vulnerability-name> --user-agreement yes --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

> **Field-tested note**: re-detection is only meaningful for emergency vulnerabilities with Status=10 (not detected, see describe-emg-vul-item). When an account has no Status=10 items, a compliant agent correctly concludes "no re-detection needed" and legitimately skips this call — this is expected behavior, not a failure. If the user explicitly requests a re-detection anyway (e.g., forcing one on a specific vulnerability regardless of status), execute it after confirmation.

### 4.15 describe-emg-vul-item (DescribeEmgVulItem) — Emergency vulnerability information

Queries emergency vulnerability information and detection status.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| RiskStatus | string | No | Risk status: `y`=risk exists, `n`=no risk (omit to return all) |
| ScanType | string | No | Detection method: `python`=version detection (server software version), `scan`=network scan (network traffic detection, detects public assets) (omit to return all) |
| CheckType | integer | No | Detection method: `0`=POC verification, `1`=version comparison |
| VulName | string | No | Emergency vulnerability name |
| CurrentPage / PageSize | integer | No | Pagination, default 1 / 10 (PageSize max 50) |

**Key response fields:** GroupedVulItems[] (**Status detection status: `10`=not detected, `20`=detecting, `30`=detection complete**, Type detection method python/scan, Progress detection progress 0~100 (shown only while detecting), PendingCount pending count, AliasName, Name, Description, GmtPublish, GmtLastCheck, RaspDefend).

**Example:**

```bash
aliyun sas describe-emg-vul-item --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.16 describe-front-vul-patch-list (DescribeFrontVulPatchList) — Windows prerequisite patches

Queries the prerequisite patches that must be installed before fixing a specified Windows system vulnerability (Windows repair prerequisite step).

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Info | string | Yes | Windows system vulnerability info to query, JSON array: `[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"system"}]` (tag fixed to system) |
| OperateType | string | Yes | Fixed value `vul_fix` |
| Type | string | Yes | Fixed value `sys` |
| Lang | string | No | Language, default zh |

**Key response fields:** FrontPatchList[] (Uuid server UUID, PatchList[]{Name prerequisite patch number, AliasName vulnerability name}). Prerequisite patches must be fixed first (isFront=1 in modify-operate-vul's Info), then the target vulnerability.

**Example:**

```bash
aliyun sas describe-front-vul-patch-list --info '[{"name":"<vulnerability-name>","uuid":"<server-uuid>","tag":"system"}]' --operate-type vul_fix --type sys --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.17 describe-once-task (DescribeOnceTask) — Client task query

Queries the progress and results of the client task list (including vulnerability scan tasks).

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| TaskType | string | No | Task type: `VUL_CHECK_TASK`=vulnerability scan task, `CLIENT_PROBLEM_CHECK`=client task, `CLIENT_DEV_OPS`=cloud O&M task, `ASSET_SECURITY_CHECK`=asset collection task, `ASSET_REFRESH_HOST`=host asset sync task. **TaskType and RootTaskId cannot both be empty** |
| RootTaskId | string | No | Root task ID |
| Source | string | No | Task source: `schedule`=automatic vulnerability scan scheduling, `console`=console one-click detection (values include but are not limited to these) |
| TaskId | string | No | Task ID |
| StartTimeQuery / EndTimeQuery | integer | No | Root task start / end timestamps (milliseconds) |
| CurrentPage / PageSize | integer | No | Pagination, default 1 / 20 |

**Key response fields:** TaskManageResponseList[] (TaskType, **TaskStatus: `1`=started, `2`=completed, `3`=failed, `4`=timed out**, Progress percentage, TaskStatusText (INIT/START/DISPATCH/SUCCESS/FAIL/TIMEOUT), SuccessCount/FailCount, TaskStartTime/TaskEndTime, TaskId, DetailData execution detail JSON), PageInfo.

**Example:**

```bash
aliyun sas describe-once-task --task-type VUL_CHECK_TASK --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.18 list-vul-auto-repair-config (ListVulAutoRepairConfig) — Auto-repair configuration query

Queries created auto-fixable vulnerability configurations.

**Key parameters:** Type (No: cve/sys), AliasName (No), CurrentPage / PageSize (default 1/10), Lang.

**Key response fields:** VulAutoRepairConfigList[] (Id config ID, Name vulnerability name, Type, AliasName, Reason), PageInfo (TotalCount, etc.).

**Example:**

```bash
aliyun sas list-vul-auto-repair-config --type cve --current-page 1 --page-size 10 --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.19 create-vul-auto-repair-config (CreateVulAutoRepairConfig) — Create auto-repair configuration [Write]

Batch creates the auto-fixable vulnerability list, used for vulnerability list selection in Task Center repair tasks. Write operation — MUST obtain user confirmation before execution.

**Key parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| Type | string | Yes | Vulnerability type: `cve`, `sys`. **Note**: the API parameter enum includes `sys`, but the effective scope of auto-repair is subject to official documentation (currently only non-kernel Linux system vulnerabilities; Windows vulnerabilities do not apply — see the capability limits in scenario-repair.md) |
| VulAutoRepairConfigList | array | Yes | Auto-fixable vulnerability list; each item contains only: `AliasName` (required, vulnerability alias), `Name` (required, vulnerability name) |
| Reason | string | No | Reason description. A top-level standalone parameter (`--reason`), not inside VulAutoRepairConfigList items |

**Key response fields:** Success (true/false), Code (`200` means success), Message, HttpStatusCode.

**Example:**

```bash
aliyun sas create-vul-auto-repair-config --type cve --vul-auto-repair-config-list '[{"Name":"<vulnerability-name>","AliasName":"<vulnerability-alias>"}]' --reason <reason> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

### 4.20 delete-vul-auto-repair-config (DeleteVulAutoRepairConfig) — Delete auto-repair configuration [Write]

Batch deletes Task Center auto-fixable vulnerability list configurations. Write operation — MUST obtain user confirmation before execution.

**Key parameters:** Type (No: cve/sys), AliasName (No), ConfigIdList (No, array; config ID list to delete; IDs are integers — the Id field returned by ListVulAutoRepairConfig).

**Key response fields:** RequestId.

**Example:**

```bash
aliyun sas delete-vul-auto-repair-config --type cve --config-id-list '[123, 456]' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-vul-repair/<session-id>
```

---

## 5. Notes

### 5.1 Pagination and Limits

- **NextToken pagination does not return TotalCount**: With UseNextToken=true, responses of describe-vul-list and describe-cloud-center-instances do not include TotalCount; determine the end by "returned count is 0 or less than PageSize".
- **Ids accepts up to 50**: The Ids parameter of describe-vul-list accepts at most 50 vulnerability IDs; split into batches beyond that.
- Use either normal pagination (CurrentPage/PageSize) or NextToken mode — do not mix them.

### 5.2 Three Severity Systems Must Not Be Mixed

| System | Values | Where It Appears | Meaning |
|--------|--------|------------------|---------|
| Necessity (repair urgency, console primary metric) | `asap`/`later`/`nntf` | describe-vul-list, describe-can-fix-vul-list, describe-grouped-vul, etc. | High (fix ASAP) / medium (can defer) / low (no fix planned) |
| VulLevel (vulnerability severity level) | `serious`/`high`/`medium`/`low` | describe-vul-details response | Serious / high / medium / low |
| Level (vulnerability level) | `high`/`medium`/`low` | describe-uuids-by-vul-names request parameter | High / medium / low risk |

The three systems are used per their own APIs — **cross-system mixing or mutual conversion is forbidden**.

### 5.3 Repair Capability Limits (MUST be explicitly communicated to the user)

- **emg (emergency), app (application), and sca (SCA) vulnerabilities do NOT support vul_fix repair**: explicitly stated in the ModifyOperateVul official documentation; these must be manually repaired following the Solution in the vulnerability details.
- **OperateVuls supports Type=cve only** (Linux software vulnerability batch repair), and OperateType is fixed to vul_fix.
- **DescribeCanFixVulList supports Type=cve/sca only**, and StatusList supports 1/4/7 only.
- **The free edition (AuthVersion=1) has no repair capability**: ModifyPushAllTask also returns FreeVersionNotPermit; verify edition and authorization via describe-version-config / describe-cloud-center-instances before repair.

### 5.4 Never Reference Non-Existent APIs

- **GetVulFixDetails and ModifyFixVul do NOT exist** (no such APIs in the official documentation); never reference them in any scenario. Repair details come from describe-vul-list's ResultCode/ResultMessage and ExtendContentJson.RpmEntityList[].UpdateCmd; repair operations go through modify-operate-vul / operate-vuls.

### 5.5 Other

- Repair failure error codes (e.g., 8009) have no API-level enum documentation; ResultCode/ResultMessage semantics are subject to the official "Vulnerability fix failure troubleshooting" help page; dynamic verification via doc-lookup.md.
- All write commands must present the change list to the user and obtain confirmation before execution; failed write operations are never auto-retried.
- The `<session-id>` in all example commands in this document is a session identifier placeholder; replace it with the 32-char lowercase hex string generated for the current session at execution time.
