# Management and Query Scenario Detailed Steps

## TOC

- [Scenario 5: Query Version and Feature Info](#scenario-5-query-version-and-feature-info)
- [Scenario 6: Query or Modify Asset Authorization](#scenario-6-query-or-modify-asset-authorization)
- [Scenario 7: Query Assets with Specific Software](#scenario-7-query-assets-with-specific-software)
- [Scenario 8: Uninstall Security Center Agent](#scenario-8-uninstall-security-center-agent)
- [Scenario 9: Security Risk Detection and Query](#scenario-9-security-risk-detection-and-query)
- [General Reference: Version Number Mapping](#general-reference-version-number-mapping)
- [General Reference: Pay-As-You-Go Module Codes](#general-reference-pay-as-you-go-module-codes)
- [General Reference: Cost Estimation Methods](#general-reference-cost-estimation-methods)

---

## Scenario 5: Query Version and Feature Info

### Step 1: Query Version Details

```bash
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills
```

Extract and display the following key information:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Current version | `Version` | Subscription version number, see version mapping table below |
| Highest version | `HighestVersion` | Highest purchased subscription version |
| Instance ID | `InstanceId` | Subscription instance ID |
| Authorized cores | `VmCores` | Purchased core quota |
| Purchase time | `GmtCreate` | 13-digit timestamp, convert to YYYY-MM-DD HH:mm:ss |
| Expiration time | `ReleaseTime` | 13-digit timestamp, convert to YYYY-MM-DD HH:mm:ss |
| Pay-as-you-go enabled | `IsPostpay` / `PostPayStatus` | Whether pay-as-you-go is also enabled |
| Pay-as-you-go instance ID | `PostPayInstanceId` | Pay-as-you-go instance ID |
| Pay-as-you-go protection level | `PostPayHostVersion` | Pay-as-you-go host protection level (version number) |
| Pay-as-you-go activation time | `PostPayOpenTime` | 13-digit timestamp, convert to YYYY-MM-DD HH:mm:ss |
| Pay-as-you-go modules | `PostPayModuleSwitch` | JSON string, each module's switch status |

> Timestamp fields (GmtCreate, ReleaseTime, PostPayOpenTime) are converted to "YYYY-MM-DD HH:mm:ss" format, because raw 13-digit timestamps are unreadable.
> Subscription info (InstanceId, HighestVersion, VmCores, GmtCreate, ReleaseTime) is only displayed when a subscription order exists (IsPaidUser=true or InstanceId has a value).
> Pay-as-you-go info (PostPayInstanceId, PostPayHostVersion, PostPayOpenTime, PostPayModuleSwitch) is only displayed when pay-as-you-go is enabled (IsPostpay=true).
>
> **[MUST] `MergedVersion` is a sensitive internal field — NEVER display, output, save, or include it in any response, file, or variable exposed to the user. When processing the `describe-version-config` response, strip `MergedVersion` before any output. Use `Version` and `HighestVersion` instead.**

When displaying `PostPayModuleSwitch` module switch statuses, fetch current prices from the billing documentation page. Add "Billing Method" and "Unit Price Reference" columns to the module status table. For disabled modules, only mark "Disabled" without showing price details. Modules that do not support pay-as-you-go (WEB_LOCK, IMAGE_SCAN) are marked "Subscription only". See "Cost Estimation Methods" below for pricing retrieval and module classification.

### Step 2: Query Authorization Usage

```bash
aliyun sas get-auth-summary --user-agent AlibabaCloud-Agent-Skills
```

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Total authorization quota (cores) | `Machine.TotalCoreCount` | Total core quota |
| Bound cores | `Machine.BindCoreCount` | Used core count |
| Unbound cores | `Machine.UnBindCoreCount` | Remaining available cores |
| Total assets (servers) | `Machine.TotalEcsCount` | Total asset count |
| Bound servers | `Machine.BindEcsCount` | Servers with authorization bound |
| Version breakdown | `VersionSummary[]` | Quota and usage per version |

> Note: GetAuthSummary returns Machine and VersionSummary under the response root object, not wrapped in a Data object.

### Step 3: Query Pay-As-You-Go Serverless Status (on demand)

Execute only when the user asks about Serverless / pay-as-you-go feature status:

```bash
aliyun sas get-serverless-auth-summary --user-agent AlibabaCloud-Agent-Skills
```

Display pay-as-you-go module switch status (`PostPaidModuleSwitch` JSON field), showing each module with its name and switch status in a table. Module codes are listed in the reference table below. Also display SERVERLESS module tiered pricing for reference (prices fetched from billing documentation page).

### Step 4: Modify Pay-As-You-Go Module Switches (on demand)

Execute only when the user explicitly requests enabling or disabling a pay-as-you-go feature module. This is a **write operation** requiring confirmation.

First obtain `PostPayInstanceId` from Step 1, then:

```bash
aliyun sas modify-post-pay-module-switch \
  --post-pay-instance-id "<pay-as-you-go-instance-id>" \
  --post-pay-module-switch '{"<module-code>": <0-or-1>}' \
  --user-agent AlibabaCloud-Agent-Skills
```

> Modules not included in the request remain unchanged.

#### Cost Estimation (when enabling modules)

When the user requests to **enable** a module, include cost estimates in the confirmation details:

**Data preparation**: Ensure get-auth-summary data (server cores/count) from Step 2 and billing page prices are available. If Step 2 has not been executed, run it first. Prices are dynamically fetched from the billing documentation (see "Cost Estimation Methods" below).

**Display costs by module category** (categories in "Cost Estimation Methods" below):

- **Estimable monthly cost modules** (POST_HOST, SERVERLESS):
  - POST_HOST requires confirming the protection level first, because pricing differs up to 30x between levels. Display level-specific unit prices for the user to choose; if already specified in conversation, use directly
    - Virus Protection: bound cores x unit price/core/month
    - Advanced Edition (legacy): bound servers x unit price/server/month. **Only show this option when user's current `PostPayHostVersion` corresponds to Advanced Edition**; otherwise hide it (this version is no longer available for new activation)
    - Host Comprehensive Protection: bound servers x unit price/server/month
    - Host & Container Comprehensive Protection: bound servers x unit price/server/month + bound cores x unit price/core/month
  - SERVERLESS: display tiered ranges, estimate monthly cost based on the tier matching current core count
- **Usage-based billing modules** (VUL, CSPM, AGENTLESS, etc.): display unit price and billing unit, note "cost depends on actual usage, monthly fee cannot be estimated"
- **Subscription-only modules** (WEB_LOCK, IMAGE_SCAN): inform that pay-as-you-go is not supported, must be purchased via console

**Base service fee check**: If all modules in `PostPayModuleSwitch` are currently disabled (value 0), remind the user that the first activation will also incur a base service fee (~0.05 CNY/hour, approx. 36 CNY/month).

**Confirmation details**: Display the module to be modified, target status, estimated cost (or unit price reference), note "estimates are based on current asset data; actual fees are subject to the Alibaba Cloud bill". Execute after user confirmation.

---

## Scenario 6: Query or Modify Asset Authorization

### Step 1: Query Asset Current Status

Obtain the server identifier from the user (instance ID, IP, name, etc.) and query asset info:

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"<instance-id>"}]' \
  --page-size 20 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Instance ID | `InstanceId` | Server instance ID |
| Instance name | `InstanceName` | Server name |
| UUID | `Uuid` | Asset UUID (used for bind/unbind) |
| Client status | `ClientStatus` | online / offline |
| Current auth version | `AuthVersion` | Currently bound version number |
| Auth modification time | `AuthModifyTime` | Last auth change timestamp |
| OS | `Os` | Operating system type |
| Asset type | `MachineType` | ecs / cloud_vm etc. |
| Cluster ID | `ClusterId` | K8s/ACK cluster ID (if applicable) |

### Step 2: Confirm Operation Type and Billing Mode

- **View authorization**: Step 1 is sufficient; display results directly
- **Bind/upgrade authorization**:
  - If subscription order exists (`IsPaidUser=true` or `InstanceId` has value) -> Step 3 (subscription binding)
  - If only pay-as-you-go (`IsPostpay=true` with no subscription) -> Step 4 (pay-as-you-go binding)
  - If both exist, ask which billing mode the user wants
- **Unbind authorization (subscription)**: Go to Step 3
- **Unbind / downgrade to free version (pay-as-you-go)**: Go to Step 4
- **Change pay-as-you-go version**: Go to Step 4

### Step 3: Bind or Unbind Authorization (Subscription)

**Important constraints** (inform the user, because these operations have irreversible implications):
- Under subscription mode, assets bound to any paid version **cannot be unbound within 30 days**; premature unbinding wastes authorization
- K8s / ACK cluster assets **only support Ultimate Edition** (Version=7); binding other versions will return an error
- Bind/unbind operations use the asset's UUID, not the instance ID

#### 3a: Version Selection

If the user has not specified a target version, display available versions:

| Version | Version Number | Description |
|---------|---------------|-------------|
| Advanced | 5 | Basic host security protection |
| Enterprise | 3 | Enhanced security detection |
| Anti-virus | 6 | Virus scanning capabilities |
| Ultimate | 7 | Host and container comprehensive protection |

> If the user has already specified a version in conversation (e.g. "bind Ultimate"), use the corresponding version number directly without asking again.

#### 3b: Secondary Confirmation

Display operation details and obtain **explicit confirmation** before executing:

```
About to execute bind operation:
- Server name: <InstanceName>
- Instance ID: <InstanceId>
- UUID: <Uuid>
- Current version: <current-version-name> (AuthVersion=<current-number>)
- Target version: <target-version-name> (AuthVersion=<target-number>)
- Billing mode: Subscription
- Constraint: Cannot unbind within 30 days after binding

Proceed? (yes/no)
```

After confirmation, execute binding:
```bash
aliyun sas bind-auth-to-machine \
  --auth-version <version-number> \
  --bind "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills
```

Unbind authorization (also requires secondary confirmation):
```bash
aliyun sas bind-auth-to-machine \
  --un-bind "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Change Pay-As-You-Go Version Binding

#### 4a: Protection Level Selection and Cost Estimation

Pay-as-you-go protection levels differ from the subscription version system. If the user has not specified a protection level, confirm it first by displaying unit prices for each level.

**Data preparation**: Ensure `get-auth-summary` has been executed for asset data, and billing page prices have been fetched (see "Cost Estimation Methods" below).

Display available protection levels and corresponding costs:

| Protection Level | Billing Dimension | Estimated Incremental Cost |
|-----------------|-------------------|---------------------------|
| Virus Protection | Per core | <cores> cores x <price>/core/month |
| Advanced (legacy) | Per server | <servers> servers x <price>/server/month |
| Host Comprehensive | Per server | <servers> servers x <price>/server/month |
| Host & Container Comprehensive | Per server + per core | <servers> x <price>/server/month + <cores> x <price>/core/month |

> **Advanced Edition is a legacy version**: Only display the "Advanced" option when the user currently holds pay-as-you-go Advanced Edition (check `PostPayHostVersion` from `describe-version-config`). If not held, remove the Advanced row -- this version is no longer available for new activation.
> Cost estimates are based on the incremental cost of binding this asset (i.e., the asset's cores/servers x corresponding unit price), not total cost.
> If the user has already specified a level in conversation (e.g. "bind Ultimate"), display cost estimates for that level only.
> If real-time prices cannot be fetched, display billing dimension descriptions and provide the billing page link.

#### 4b: Secondary Confirmation

Display operation details and cost estimates, obtain **explicit confirmation** before executing:

```
About to execute pay-as-you-go version binding:
- Server name: <InstanceName>
- Instance ID: <InstanceId>
- UUID: <Uuid>
- Current version: <current-version-name> (AuthVersion=<current-number>)
- Target version: <target-version-name> (AuthVersion=<target-number>)
- Billing mode: Pay-as-you-go
- Estimated incremental cost: <cores/servers> x <price> = approx. <monthly-cost>/month
- Disclaimer: Estimates based on current asset data and real-time pricing; actual fees subject to Alibaba Cloud bill

Proceed? (yes/no)
```

After confirmation, execute:
```bash
aliyun sas update-post-paid-bind-rel \
  --bind-action '[{"Version": "<version-number>", "UuidList": ["<UUID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 4c: Unbind / Downgrade to Free Version (Pay-as-you-go)

If the user requests to downgrade a pay-as-you-go server to free version (unbind authorization), use `update-post-paid-bind-rel` with `Version=1`:

Display operation details and obtain **explicit confirmation** before executing:

```
About to downgrade pay-as-you-go server to free version:
- Server name: <InstanceName>
- Instance ID: <InstanceId>
- UUID: <Uuid>
- Current version: <current-version-name> (AuthVersion=<current-number>)
- Target version: Free (AuthVersion=1)
- Note: Server will lose paid protection features after downgrade

Proceed? (yes/no)
```

After confirmation, execute:
```bash
aliyun sas update-post-paid-bind-rel \
  --bind-action '[{"UuidList": ["<UUID>"], "Version": 1}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 5: Verify Change

After the operation completes, re-query asset status to confirm the authorization version has changed:

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Scenario 7: Query Assets with Specific Software

### Step 1: Confirm Query Conditions

Confirm with the user:
- **Software name**: The middleware/database/web service name to query (e.g. nginx, mysql, redis)
- **Software type** (optional):
  - `sca` (default): Middleware
  - `sca_database`: Database
  - `sca_web`: Web service
- **Subtype** (optional): system_service, software_library, docker_component, database, web_container, jar, web_framework

### Step 2: Query Asset Fingerprint

```bash
aliyun sas describe-property-sca-detail \
  --search-item name \
  --search-info "<software-name>" \
  --biz <sca|sca_database|sca_web> \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

> Only pass parameters the user has specified. If --biz is not specified, omit it (defaults to sca).
> **Common software type mapping**: Redis, MySQL, PostgreSQL, MongoDB, MariaDB -> `sca_database`; Nginx, Apache, Tomcat -> `sca` (default); if the default type returns no results, retry with other types (`sca_database`, `sca_web`).

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Server name | `InstanceName` | Server with the software installed |
| Instance ID | `InstanceId` | Server instance ID |
| Public IP | `InternetIp` | Public IP address |
| Private IP | `IntranetIp` | Private IP address |
| Software name | `Name` | Detected software name |
| Software version | `Version` | Software version number |
| Listening port | `Port` | Process listening port |
| Process ID | `Pid` | Running process ID |
| Running user | `User` | Process owner |

If `TotalCount` exceeds the current `PageSize`, inform the user there are more results and ask whether to view the next page.

### Step 3: Query Detailed Asset Info (on demand)

If the user needs further information about a server's client status, authorization version, etc.:

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"<instance-id>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

---

## Scenario 8: Uninstall Security Center Agent

### Step 1: Get Target Server Info

Obtain the server identifier from the user (instance ID, IP, name, etc.) and query asset info to get the UUID:

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceName","value":"<server-name>"}]' \
  --page-size 20 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Instance name | `InstanceName` | Server name |
| UUID | `Uuid` | Unique identifier required for uninstall |
| Client status | `ClientStatus` | online / offline / pause |
| OS | `Os` | Operating system type |
| Public IP | `InternetIp` | Public IP address |
| Private IP | `IntranetIp` | Private IP address |
| Asset type | `MachineType` | ecs / cloud_vm etc. |

### Step 2: Display Uninstall Details and Confirm

Display the server information to be uninstalled in table format, with warnings:

**Uninstall confirmation info**:
- Server name: {InstanceName}
- UUID: {Uuid}
- Current client status: {ClientStatus}
- OS: {Os}

**Important warnings** (must inform user):
- After uninstalling, the server will **lose all Security Center protection capabilities**, including intrusion detection, vulnerability scanning, baseline checks, etc.
- Client status must be `online` to execute uninstall; offline agents cannot be uninstalled via this API

> This is a write operation; explicit user confirmation is required before execution.

### Step 3: Execute Uninstall

After confirmation, execute the uninstall command:

```bash
aliyun sas add-uninstall-clients-by-uuids \
  --uuids "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills
```

To uninstall multiple servers simultaneously, separate UUIDs with commas:

```bash
aliyun sas add-uninstall-clients-by-uuids \
  --uuids "<UUID1>,<UUID2>" \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Verify Uninstall Result

Wait approximately 30 seconds, then re-query asset status to confirm the agent has been uninstalled:

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"uuid","value":"<UUID>"}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

Check if `ClientStatus` has changed to `offline` or if the asset has been removed from the list.

---

## Scenario 9: Security Risk Detection and Query

> **[HARD GATE] ALL scan dispatch operations in this scenario are host-based (agent-dependent).** The target server's Security Center agent MUST be `ClientStatus=online` before ANY scan can be dispatched. If the agent is not installed or offline, scans CANNOT execute and WILL produce NO results. There is NO agentless scanning mode. Do NOT bypass this requirement under any circumstances — guide the user to install or bring the agent online first.
>
> Additionally, the target server MUST be bound to a paid authorization version (`AuthVersion > 1`). Free version servers (`AuthVersion <= 1`) cannot be scanned.
>
> **Exception**: Querying existing risk results (Step 2: describe-grouped-vul, list-check-item-warning-summary, describe-susp-events) is a READ operation that retrieves historical data from Security Center's database. This does NOT trigger new scans, does NOT require the agent to be online, and does NOT require paid authorization.

### Step 1: Confirm Detection Type

Route to the corresponding sub-flow based on user intent:

- User wants to **view existing risk results** (vulnerabilities, baseline, alerts) -> Step 2
- User wants to **trigger a new security scan** -> Step 3
- User vaguely says "detect security risks" -> Ask whether to view existing results or trigger a new scan

### Step 2: Query Risk Results

Execute the corresponding query based on the risk types the user is interested in. Multiple types can be queried simultaneously.

#### 2a: Query Vulnerability Risks

```bash
aliyun sas describe-grouped-vul \
  --type cve \
  --dealed n \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

Vulnerability type (--type) options:
- `cve`: Linux vulnerabilities
- `sys`: Windows vulnerabilities
- `cms`: Web-CMS vulnerabilities
- `app`: Application vulnerabilities (scanning)
- `sca`: Application vulnerabilities (composition analysis)

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Vulnerability name | `AliasName` | Vulnerability alias |
| Vulnerability type | `Type` | cve / sys / cms / app / sca |
| High priority count | `AsapCount` | Count requiring urgent fix |
| Medium priority count | `LaterCount` | Count that can be fixed later |
| Low priority count | `NntfCount` | Count that can be ignored for now |
| Handled count | `HandledCount` | Vulnerabilities already handled |
| First discovered | `GmtFirst` | 13-digit timestamp, convert to readable format |
| Last discovered | `GmtLast` | 13-digit timestamp, convert to readable format |
| Related CVEs | `Related` | Associated CVE identifiers |
| Tags | `Tags` | e.g. "Remote Exploit", "Code Execution" |

If `TotalCount` exceeds `PageSize`, notify that more results are available.

#### 2b: Query Baseline Risks

```bash
aliyun sas list-check-item-warning-summary \
  --check-warning-status 1 \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

Risk status (--check-warning-status) options: 1=Failed, 3=Passed, 6=Whitelisted, 8=Fixed.

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Check item | `CheckItem` | Check item description |
| Risk level | `CheckLevel` | high / medium / low |
| Check category | `CheckType` | Check item classification |
| Affected machines | `WarningMachineCount` | Servers that failed this check |
| Remediation advice | `Advice` | Check item recommendation |
| Description | `Description` | Check item details |

Can filter by specific level via `--check-level` parameter (e.g. high-risk only: `--check-level high`).

#### 2c: Query Security Alerts

```bash
aliyun sas describe-susp-events \
  --dealed N \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

Optional filter parameters:
- `--levels`: Alert level (serious=critical, suspicious=suspicious, remind=informational)
- `--parent-event-types`: Alert types (e.g. abnormal process behavior, webshell, abnormal login)
- `--uuids`: Specific server UUID

Extract and display:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Alert name | `AlarmEventNameDisplay` | Alert display name |
| Alert type | `AlarmEventTypeDisplay` | Alert type display name |
| Severity level | `Level` | serious / suspicious / remind |
| Affected instance | `InstanceName` | Server name |
| Public IP | `InternetIp` | Associated instance public IP |
| Private IP | `IntranetIp` | Associated instance private IP |
| First occurrence | `OccurrenceTime` | First occurrence time |
| Last occurrence | `LastTime` | Last occurrence time |
| Event status | `EventStatus` | 1=Pending, 4=Confirmed, 32=Handled |
| Description | `Desc` | Alert event impact summary |

### Step 3: Trigger Security Scan (Write Operations)

> **Reminder: ALL scans below are host-based and agent-dependent.** Before dispatching ANY scan task, the target server(s) MUST have `ClientStatus=online` AND `AuthVersion > 1`. If either condition is not met, do NOT dispatch the scan. The prerequisite check flows below enforce this gate.

All operations below are **write operations** requiring operation details display and user confirmation before execution.

**Dispatch strategy**:
- **User specified target assets** (targeted scan): Use `modify-push-all-task` uniformly with the target UUID, which includes vulnerability scan, baseline check, asset fingerprint collection and other check items. Prerequisites chain (authorization + client) must be completed first. **[HARD GATE] NEVER use `modify-start-vul-scan` for targeted scans — it is a global command that scans ALL servers in the entire account, not just the target. Using it for a single-server scan is a critical error.**
- **User did not specify target assets** (full scan): First run full asset prerequisite check (client online + authorization bound), then use separate scan commands (modify-start-vul-scan, exec-strategy, generate-once-task, create-virus-scan-once-task)

#### 3a: Targeted Asset Scan (Fully Automated Flow)

When the user specifies a particular server for security scanning, follow this prerequisite chain automatically. **Only pause for confirmation when paid authorization binding is needed; all other steps are automated**.

> **[HARD GATE] Command selection**: In this entire 3a flow, use ONLY `modify-push-all-task` for vulnerability/baseline/fingerprint scanning. Do NOT call `modify-start-vul-scan` under any circumstances — it is a global full-scan command reserved exclusively for flow 3b.

##### Prerequisite Chain Flow

```
Query asset -> Check auth version -> [Need binding? -> Show cost -> User confirms] -> Check client -> [Need install? -> Auto install -> Wait online] -> Dispatch scan
```

##### Check 1: Query Asset Info

```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceName","value":"<server-name>"}]' \
  --page-size 20 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

Extract key fields: `Uuid`, `InstanceId`, `AuthVersion`, `ClientStatus`, `ClientSubStatus`, `Os`, `Cores`, `RegionId`

> **[MUST] Region field distinction**: The SAS response contains both `Region` (e.g. `cn-hangzhou-dg-a01`, physical availability zone) and `RegionId` (e.g. `cn-hangzhou`, standard API region). When calling ECS APIs later (describe-cloud-assistant-status, run-command, describe-invocation-results), always use the `RegionId` field. Using `Region` causes `InvalidInstance.NotFound` or `RegionId.ApiNotSupported` errors because dedicated sub-zones are not recognized by standard ECS API endpoints. The ECS API parameter name is `--biz-region-id` (NOT `--RegionId` or `--region-id`). **Additionally, when the target region differs from the CLI's default configured region, you MUST also add `--region <RegionId>` to route the request to the correct ECS endpoint** — `--biz-region-id` only sets the request body parameter, not the endpoint routing.

##### Check 2: Authorization Version Check

Based on `AuthVersion`:

- **AuthVersion > 1** (paid version bound) -> Skip, proceed to Check 3
- **AuthVersion = 1 or 0** (free/unauthorized) -> Paid version binding required before scan dispatch; enter binding flow

**Binding flow (requires user confirmation)**:

1. Query account version info to confirm available billing modes:
```bash
aliyun sas describe-version-config --user-agent AlibabaCloud-Agent-Skills
```

2. Based on billing mode, display binding options and costs:

**a) Subscription mode** (`IsPaidUser=true` or `InstanceId` has value):

First query remaining quota:
```bash
aliyun sas get-auth-summary --user-agent AlibabaCloud-Agent-Skills
```

Display confirmation:
```
Target server is currently on free version; a paid version binding is required to dispatch security scan.

Current subscription authorization:
- Version: <HighestVersion name>
- Remaining quota: <UnBindCoreCount> cores / <UnBindEcsCount> servers
- Expiration: <ReleaseTime>

Will bind authorization for:
- Server: <InstanceName> (<InstanceId>)
- Target version: <version-name> (AuthVersion=<number>)
- Constraint: Cannot unbind within 30 days

Confirm binding? (yes/no)
```

After confirmation, auto-execute:
```bash
aliyun sas bind-auth-to-machine --auth-version <version-number> --bind "<UUID>" --user-agent AlibabaCloud-Agent-Skills
```

**b) Pay-as-you-go mode** (`IsPostpay=true` with no subscription):

Display protection levels and costs for user selection:

| Protection Level | Billing Dimension | Estimated Cost (this asset) |
|-----------------|-------------------|-----------------------------|
| Virus Protection | Per core | <Cores> cores x <price>/core/month |
| Advanced (legacy) | Per server | 1 server x <price>/server/month |
| Host Comprehensive | Per server | 1 server x <price>/server/month |
| Host & Container Comprehensive | Per server + per core | 1 server x <price>/server/month + <Cores> cores x <price>/core/month |

> Advanced is a legacy version; only display when `PostPayHostVersion` corresponds to Advanced, otherwise hide.
> Prices are dynamically fetched from billing documentation (see "Cost Estimation Methods" below).

```
Target server is currently on free version; a pay-as-you-go version binding is required for security scan.
Select a protection level (see table above) to bind for:
- Server: <InstanceName> (<InstanceId>)
- Estimates based on current asset data; actual fees subject to Alibaba Cloud bill

Confirm protection level and binding?
```

After confirmation, auto-execute:
```bash
aliyun sas update-post-paid-bind-rel \
  --bind-action '[{"Version": "<version-number>", "UuidList": ["<UUID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills
```

**c) Both billing modes exist**: Display both options for user selection, then follow the corresponding flow.

**d) No paid version available**: Inform the user they must first activate a paid Security Center version (subscription purchase or enable pay-as-you-go); provide the console link and terminate the flow.

##### Check 3: Client Status Check

Based on `ClientStatus`:

- **`ClientStatus` = `online`** -> Skip, proceed to scan dispatch
- **`ClientStatus` = `offline` and `ClientSubStatus` = `uninstalled`** -> Agent not installed; enter auto-install flow
- **`ClientStatus` = `offline` and `ClientSubStatus` is not `uninstalled`** -> Agent installed but offline; prompt user to check server status and terminate scan flow

**Auto-install flow** (no user confirmation needed, executes automatically):

1. Get install code:
```bash
aliyun sas describe-install-codes --user-agent AlibabaCloud-Agent-Skills
```
Match criteria: Os matches target server, VendorName=ALIYUN, OnlyImage=false

2. Check cloud assistant status:
```bash
aliyun ecs describe-cloud-assistant-status --region <RegionId> --biz-region-id <RegionId> --instance-id "<InstanceId>" --user-agent AlibabaCloud-Agent-Skills
```

3a. **Cloud assistant online** -> Dispatch install command via cloud assistant:
```bash
aliyun ecs run-command \
  --region <RegionId> \
  --biz-region-id <RegionId> \
  --type RunShellScript \
  --command-content "<Base64-encoded-install-command>" \
  --instance-id "<InstanceId>" \
  --content-encoding Base64 \
  --user-agent AlibabaCloud-Agent-Skills
```

Install command (Linux internal):
```
wget "https://update2.aegis.aliyun.com/download/install/2.0/linux/AliAqsInstall.sh" && chmod +x AliAqsInstall.sh && ./AliAqsInstall.sh -k=<install-code>
```

Windows internal (RunPowerShellScript):
```
(New-Object Net.WebClient).DownloadFile('https://update2.aegis.aliyun.com/download/install/2.0/windows/AliAqsInstall.exe', $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath('.\AliAqsInstall.exe')); ./AliAqsInstall.exe -k=<install-code>
```

> Installation takes time; intermediate error messages can be ignored; success is determined by the final output.

4. Wait for installation to complete, query execution results:
```bash
aliyun ecs describe-invocation-results --region <RegionId> --biz-region-id <RegionId> --invoke-id "<InvokeId>" --user-agent AlibabaCloud-Agent-Skills
```

Poll until `InvocationStatus` is no longer `Running` (recommended 30-second interval); confirm final status is `Success`.

5. After successful installation, wait approximately 10 seconds for the agent to come online, then re-query client status to confirm `ClientStatus=online`.

3b. **Cloud assistant not online** -> Cannot auto-install; display install command for user to execute manually and terminate the automated flow:
```
Cloud assistant is not online; cannot auto-install the agent. Please log into the server and manually execute:
<display the install command matching the OS and network access method>
Initiate scanning again after installation completes.
```

##### Checks Passed -> Dispatch Scan

After all prerequisite checks pass (confirmed: `ClientStatus=online` AND `AuthVersion > 1`), automatically dispatch scan tasks (no additional confirmation needed, because the user explicitly requested scanning initially):

> **Final gate**: Do NOT reach this point unless Check 2 (authorization) and Check 3 (client online) have both passed. If the client is still offline or unauthorized, go back and resolve those issues first.

> **[HARD GATE] Targeted scan command restriction**: In this targeted scan flow, use ONLY `modify-push-all-task` (with the target UUID) for vulnerability/baseline/fingerprint scanning. NEVER call `modify-start-vul-scan` — it is a global full-scan command that scans ALL servers account-wide, not just the target. `modify-start-vul-scan` is reserved exclusively for the full-scan flow (3b).

**a) Security check (modify-push-all-task)**:

**Baseline detection prerequisite**: Before dispatching the security check, evaluate whether to include baseline detection (`HEALTH_CHECK`) based on `describe-version-config` data from Check 2:

- **Either condition met** -> Tasks **include** `HEALTH_CHECK`:
  - Pre-paid host protection version: `Version > 1` (i.e. Advanced/Enterprise/Anti-virus/Ultimate purchased)
  - Cloud Security Posture Management enabled: `PostPayModuleSwitch` JSON has `CSPM` value `1`
- **Neither met** -> **Remove** `HEALTH_CHECK` from Tasks, and explain: "Pre-paid host protection version not activated and CSPM not enabled; skipping baseline detection"

Tasks with baseline detection:
```bash
aliyun sas modify-push-all-task \
  --uuids "<UUID>" \
  --tasks "OVAL_ENTITY,CMS,SYSVUL,SCA,HEALTH_CHECK,WEBSHELL,PROC_SNAPSHOT,PORT_SNAPSHOT,ACCOUNT_SNAPSHOT,SOFTWARE_SNAPSHOT,SCA_SNAPSHOT" \
  --user-agent AlibabaCloud-Agent-Skills
```

Tasks without baseline detection:
```bash
aliyun sas modify-push-all-task \
  --uuids "<UUID>" \
  --tasks "OVAL_ENTITY,CMS,SYSVUL,SCA,WEBSHELL,PROC_SNAPSHOT,PORT_SNAPSHOT,ACCOUNT_SNAPSHOT,SOFTWARE_SNAPSHOT,SCA_SNAPSHOT" \
  --user-agent AlibabaCloud-Agent-Skills
```

**b) Virus scan (create-virus-scan-once-task)**:

> **[MUST] Parameter format**: The `--business-type` parameter must be the exact string `"VIRUS_SCAN_ONCE_TASK"`. Do NOT use numeric codes (1, 3, 4, etc.) — they will return 400 `illegal businessType`.

Execute the following 4 steps in sequence:

1. Create asset selection configuration:
```bash
aliyun sas create-asset-selection-config \
  --business-type "VIRUS_SCAN_ONCE_TASK" \
  --target-type "instance" \
  --platform "all" \
  --user-agent AlibabaCloud-Agent-Skills
```
Record the returned `SelectionKey`.

2. Add target asset to selection configuration:
```bash
aliyun sas add-asset-selection-criteria \
  --selection-key "<SelectionKey>" \
  --target-operation-list Target="<UUID>" Operation=add \
  --user-agent AlibabaCloud-Agent-Skills
```
> Multiple servers can be added by repeating `--target-operation-list Target=<UUID> Operation=add`.

3. Associate selection configuration to virus scan business:
```bash
aliyun sas update-selection-key-by-type \
  --business-type "VIRUS_SCAN_ONCE_TASK" \
  --selection-key "<SelectionKey>" \
  --user-agent AlibabaCloud-Agent-Skills
```

4. Create virus scan task:
```bash
aliyun sas create-virus-scan-once-task \
  --scan-type "system" \
  --selection-key "<SelectionKey>" \
  --user-agent AlibabaCloud-Agent-Skills
```
> --scan-type values: `system` (system scan, scans all critical paths), `user` (custom scan, requires additional --scan-path). Default is `system`.

##### Full Flow Output Example

The agent should display progress to the user in real-time during execution:

```
[1/6] Querying asset info... Done. Found shucang-test (i-bp1xxx)
[2/6] Checking auth version... Done. Ultimate bound (AuthVersion=7)
      (or: Warning: Currently free version, paid binding needed -> Show confirmation)
[3/6] Checking client status... Done. Client online
      (or: Warning: Client not installed, auto-installing...)
[4/6] Installing agent... Done. (Install success)
[5/6] Dispatching security check... Done. Vulnerability scan/baseline check/fingerprint tasks dispatched
      (or: Done. Vulnerability scan/fingerprint tasks dispatched (pre-paid version/CSPM not enabled, baseline detection skipped))
[6/6] Dispatching virus scan... Done. Virus scan task dispatched

Scan results will be available in approximately 5 minutes; you can then query vulnerability/baseline/alert/virus scan data.
```

#### Full Scan Prerequisite Check (shared by 3b-3e)

> **[HARD GATE]** Full scans are also host-based and agent-dependent. Only servers with `ClientStatus=online` AND `AuthVersion > 1` can be scanned. Servers that do not meet BOTH conditions MUST be excluded from scan dispatch. If NO servers meet the conditions, terminate the scan flow entirely.

Before full scan, query all asset client and authorization statuses to show the user asset readiness.

**Step one: Query all asset statuses**

```bash
aliyun sas describe-cloud-center-instances \
  --page-size 20 --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

> If `TotalCount` exceeds `PageSize`, paginate until all assets are retrieved.

**Step two: Asset classification statistics**

Classify each asset by `ClientStatus` and `AuthVersion`:

| Category | Condition | Scannable |
|----------|-----------|-----------|
| Ready | `ClientStatus=online` and `AuthVersion > 1` | Yes |
| Unauthorized | `ClientStatus=online` but `AuthVersion <= 1` | No (bind authorization first) |
| Client offline | `ClientStatus=offline` | No (bring client online first) |
| Client not installed | `ClientStatus=offline` and `ClientSubStatus=uninstalled` | No (install client first) |

**Step three: Display asset readiness**

Show the user a summary and list of non-scannable assets:

```
Full scan asset readiness check:
- Total assets: X servers
- Scannable: Y servers (client online + authorization bound)
- Not scannable: Z servers
  - Unauthorized (client online but no paid version): A servers
  - Client offline/not installed: B servers

Non-scannable asset list:
| Server Name | Instance ID | Client Status | Auth Version | Reason |
|-------------|-------------|---------------|--------------|--------|
| ... | ... | ... | ... | Unauthorized/Offline/Not installed |
```

**Step four: Confirm whether to continue**

- **All ready** (Z=0): Display confirmation then execute scan
- **Partially ready** (Y>0 and Z>0): Inform the user that scanning will only cover the Y ready servers; the Z non-scannable servers need handling first (bind authorization/install client). Ask whether to continue
- **None scannable** (Y=0): Inform the user there are no scannable servers; authorization binding and client installation must be completed first. Terminate scan flow

> After user confirmation, execute scan tasks 3b-3e in sequence.

---

#### 3b: Full Vulnerability Scan (modify-start-vul-scan)

Scan all ready servers for vulnerabilities:

```bash
aliyun sas modify-start-vul-scan \
  --types "cve,sys,cms,app,sca" \
  --user-agent AlibabaCloud-Agent-Skills
```

> Omitting --types scans all vulnerability types.

#### 3c: Full Baseline Check (exec-strategy)

Used when no specific assets are targeted.

**Prerequisites**: Baseline detection requires the user to meet either condition; otherwise skip this step and inform the user why:
- Pre-paid host protection version: `describe-version-config` returns `Version > 1` (i.e. Advanced/Enterprise/Anti-virus/Ultimate purchased)
- Cloud Security Posture Management enabled: `describe-version-config` returns `PostPayModuleSwitch` JSON with `CSPM` value `1`

> If neither is met, inform the user: "Pre-paid host protection version not activated and Cloud Security Posture Management (CSPM) not enabled; baseline check cannot be executed. To use baseline detection, purchase a paid Security Center version or enable the pay-as-you-go CSPM module."

First query baseline strategy list for user selection.

**Step one: Query baseline strategy list**

```bash
aliyun sas describe-strategy --user-agent AlibabaCloud-Agent-Skills
```

Display strategy list in table format:

| Info Item | Field | Notes |
|-----------|-------|-------|
| Strategy ID | `Id` | StrategyId needed for baseline check execution |
| Strategy name | `Name` | Strategy display name |
| Strategy type | `CustomType` | common=Standard / custom=Custom |
| Check cycle | `CycleDays` | Cycle in days |
| Execution window | `StartTime` ~ `EndTime` | Check execution time window |
| Associated servers | `EcsCount` | Servers covered by this strategy |
| Risk item count | `RiskCount` | Currently detected risk items |
| Pass rate | `PassRate` | Baseline check pass rate (%) |

> If there is only one strategy, display its info and ask the user whether to use it.

**Step two: Execute baseline check after user selection**

After the user selects a strategy, execute (write operation, requires confirmation):

```bash
aliyun sas exec-strategy \
  --strategy-id <user-selected-strategy-id> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### 3d: Full Asset Fingerprint Collection (generate-once-task)

Collect asset fingerprints from all ready servers:

```bash
aliyun sas generate-once-task \
  --task-type "ASSETS_COLLECTION" \
  --task-name "ASSETS_COLLECTION" \
  --param '{"items":"ACCOUNT_SNAPSHOT,PORT_SNAPSHOT,PROC_SNAPSHOT,SOFTWARE_SNAPSHOT,CROND_SNAPSHOT,SCA_SNAPSHOT,LKM_SNAPSHOT,AUTORUN_SNAPSHOT,SCA_PROXY_SNAPSHOT"}' \
  --user-agent AlibabaCloud-Agent-Skills
```

Collection items:
- `ACCOUNT_SNAPSHOT`: Account snapshot
- `PORT_SNAPSHOT`: Port snapshot
- `PROC_SNAPSHOT`: Process snapshot
- `SOFTWARE_SNAPSHOT`: Software snapshot
- `CROND_SNAPSHOT`: Scheduled task snapshot
- `SCA_SNAPSHOT`: Middleware snapshot
- `LKM_SNAPSHOT`: Kernel module snapshot
- `AUTORUN_SNAPSHOT`: Auto-start item snapshot
- `SCA_PROXY_SNAPSHOT`: Proxy middleware snapshot

#### 3e: Full Virus Scan (create-virus-scan-once-task)

Scan all ready servers for viruses:

Execute the following 2 steps in sequence:

1. Create full asset selection configuration:
```bash
aliyun sas create-asset-selection-config \
  --business-type "VIRUS_SCAN_ONCE_TASK" \
  --target-type "all_instance" \
  --platform "all" \
  --user-agent AlibabaCloud-Agent-Skills
```
Record the returned `SelectionKey`.

> When `target-type=all_instance`, the selection configuration is automatically associated to the business type. No need to call `update-selection-key-by-type` — that step is only required for targeted single-server scans (`target-type=instance`).

2. Create virus scan task:
```bash
aliyun sas create-virus-scan-once-task \
  --scan-type "system" \
  --selection-key "<SelectionKey>" \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Virus Scan Result Query

Query the latest virus scan task progress:
```bash
aliyun sas get-virus-scan-latest-task-statistic --user-agent AlibabaCloud-Agent-Skills
```

Key return fields:
| Field | Notes |
|-------|-------|
| `Status` | Task status (10=In progress, 20=Completed) |
| `Progress` | Progress percentage |
| `ScanMachine` | Machines being scanned |
| `CompleteMachine` | Machines completed |
| `UnCompleteMachine` | Machines not completed |
| `SafeMachine` | Clean machines |
| `SuspiciousMachine` | Machines with viruses found |
| `SuspiciousCount` | Total viruses found |
| `TaskId` | Task ID |

Query machines where viruses were found:
```bash
aliyun sas list-virus-scan-machine --current-page 1 --page-size 20 --user-agent AlibabaCloud-Agent-Skills
```

Query virus event details for a specific machine:
```bash
aliyun sas list-virus-scan-machine-event \
  --uuid "<UUID>" \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

### Step 4: Poll Task Progress and Query Results

After scan tasks are dispatched, **do not use fixed waits**; instead poll the corresponding interfaces for each task's execution status. Recommended polling interval: **30 seconds**. If not completed after **10 minutes**, prompt the user to query manually later.

#### 4a: Vulnerability Scan Progress (describe-once-task)

```bash
aliyun sas describe-once-task \
  --task-type "VUL_CHECK_TASK" \
  --current-page 1 \
  --page-size 1 \
  --user-agent AlibabaCloud-Agent-Skills
```

Check the latest task (first item): 
- `TaskStatusText = "PROCESSING"`: In progress, display `Progress` to user, continue polling
- `TaskStatusText != "PROCESSING"`: Completed, proceed to result query

#### 4b: Baseline Check Progress (describe-strategy)

Only poll if baseline check (exec-strategy) was triggered:

```bash
aliyun sas describe-strategy --strategy-ids "<strategy-id-used>" --user-agent AlibabaCloud-Agent-Skills
```

Check the corresponding strategy's status:
- `ExecStatus = 2`: Executing, display `Percent` progress to user, continue polling
- `ExecStatus = 1`: Completed, proceed to result query

#### 4c: Virus Scan Progress (get-virus-scan-latest-task-statistic)

```bash
aliyun sas get-virus-scan-latest-task-statistic --user-agent AlibabaCloud-Agent-Skills
```

Check status:
- `Status = 10`: In progress, display `CompleteMachine`/`ScanMachine` progress, continue polling
- `Status = 20`: Completed, proceed to result query

#### Polling Output Example

The agent should display progress to the user in real-time during polling:

```
Scan tasks dispatched, polling progress...

[Vulnerability Scan] In progress... 40% (3/5 servers completed)
[Virus Scan] In progress... 66% (2/3 servers completed)

--- 30 seconds later ---

[Vulnerability Scan] Completed
[Virus Scan] In progress... 66% (2/3 servers completed)

--- 30 seconds later ---

[Vulnerability Scan] Completed
[Virus Scan] Completed (3/3 servers, 3 clean, 0 viruses found)

All scans completed, querying risk results...
```

#### 4d: Query Final Results

After all tasks complete, automatically query risk results (the queries from Step 2), presenting a complete security risk report to the user.

---

## General Reference: Version Number Mapping

| Version Name | Version Number |
|-------------|----------------|
| Free | 1 |
| Enterprise | 3 |
| Advanced | 5 |
| Anti-virus | 6 |
| Ultimate | 7 |
| Value-added Service | 10 |

## General Reference: Pay-As-You-Go Module Codes

| Module Code | Name |
|-------------|------|
| POST_HOST | Host & Container Security |
| VUL | Vulnerability Fix |
| CSPM | Cloud Security Posture Management |
| AGENTLESS | Agentless Detection |
| SERVERLESS | Serverless Security |
| CTDR | Agent SOC |
| SDK | Malicious File Detection SDK |
| RASP | Application Protection |
| CTDR_STORAGE | Log Management |
| ANTI_RANSOMWARE | Anti-Ransomware Management |
| AI_DIGITAL | Agent SOC - Security Operations Agent |
| WEB_LOCK | Web Tamper Protection |
| IMAGE_SCAN | Image Scanning |

> BASIC_SERVICE is an internal base service module; do not display to the user.

## General Reference: Cost Estimation Methods

### Module Three-Way Classification

| Category | Module Codes | Estimation Method |
|----------|-------------|-------------------|
| Estimable monthly cost (server/core billing) | POST_HOST, SERVERLESS | Use get-auth-summary core/server counts x unit price to calculate monthly cost |
| Usage-based billing | VUL, CSPM, AGENTLESS, SDK, RASP, CTDR, CTDR_STORAGE, ANTI_RANSOMWARE, AI_DIGITAL | Display unit price and billing unit, note "cost depends on actual usage" |
| Subscription only | WEB_LOCK, IMAGE_SCAN | Indicate "pay-as-you-go not supported, purchase subscription via console" |

### POST_HOST Protection Levels

POST_HOST has different billing dimensions and unit prices per protection level; confirm the level before enabling:

| Protection Level | Billing Dimension | Estimation Formula |
|-----------------|-------------------|--------------------|
| Virus Protection | Per core | Bound cores (`Machine.PostPaidBindCoreCount`) x unit price/core/month |
| Advanced (legacy) | Per server | Bound servers (`Machine.PostPaidBindEcsCount`) x unit price/server/month |
| Host Comprehensive | Per server | Bound servers (`Machine.PostPaidBindEcsCount`) x unit price/server/month |
| Host & Container Comprehensive | Per server + per core | Bound servers x unit price/server/month + Bound cores (`Machine.PostPaidBindCoreCount`) x unit price/core/month |

> **Advanced Edition check**: Use `PostPayHostVersion` from `describe-version-config`; only show the Advanced option in the protection level list when this value corresponds to Advanced. If the user does not hold pay-as-you-go Advanced, hide this option because the version is no longer available for new activation.
> If the user has already specified a level in conversation (e.g. "enable Ultimate pay-as-you-go"), use the corresponding level directly without asking again.

### Base Service Fee

When any pay-as-you-go module is enabled, an additional base service fee applies: ~0.05 CNY/hour (approx. 36 CNY/month), settled daily. If other modules are already enabled, the base service fee is already being charged; no additional reminder needed.

### Price Retrieval Method

The agent fetches current unit prices from the billing documentation page on the first pricing need per session:

- Billing documentation URL: https://help.aliyun.com/zh/security-center/product-overview/billing-overview
- Cache and reuse within the session, because prices do not change within a single session
- If unable to access or parse content, inform the user that real-time prices could not be retrieved and provide the billing page link
- In degraded scenarios, still display module classification info (estimable/usage-based/subscription-only), because classification does not depend on specific prices

### Disclaimer

Cost estimates are based on current asset counts and real-time unit prices; actual fees are subject to the Alibaba Cloud bill. Tiered billing modules (CSPM, CTDR, SERVERLESS) display tier-specific unit prices for reference.
