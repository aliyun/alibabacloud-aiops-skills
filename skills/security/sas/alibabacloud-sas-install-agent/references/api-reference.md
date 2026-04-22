# Security Center Onboarding - API Reference

This document lists all Alibaba Cloud OpenAPIs used by this skill and their invocation via aliyun CLI.

> **Every `aliyun` CLI command MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent`.**

## Table of Contents

- [1. describe-cloud-center-instances - Query Asset Information](#1-describe-cloud-center-instances---query-asset-information)
- [2. describe-instances - Query ECS Instances](#2-describe-instances---query-ecs-instances)
- [3. describe-cloud-assistant-status - Query Cloud Assistant Status](#3-describe-cloud-assistant-status---query-cloud-assistant-status)
- [4. invoke-command / run-command - Execute Command via Cloud Assistant](#4-invoke-command--run-command---execute-command-via-cloud-assistant)
- [4b. describe-invocation-results - Query Command Execution Results](#4b-describe-invocation-results---query-command-execution-results)
- [5. refresh-assets - Sync Asset Status](#5-refresh-assets---sync-asset-status)
- [6. describe-install-codes - Query Install Codes](#6-describe-install-codes---query-install-codes)
- [7. add-install-code - Create Install Code](#7-add-install-code---create-install-code)
- [8. create-or-update-asset-group - Create/Update Asset Group](#8-create-or-update-asset-group---createupdate-asset-group)
- [9. describe-version-config - Query Version Details](#9-describe-version-config---query-version-details)
- [10. get-auth-summary - Query Authorization Summary](#10-get-auth-summary---query-authorization-summary)
- [11. get-serverless-auth-summary - Query Serverless Authorization](#11-get-serverless-auth-summary---query-serverless-authorization)
- [12. modify-post-pay-module-switch - Toggle Pay-as-you-go Module Switch](#12-modify-post-pay-module-switch---toggle-pay-as-you-go-module-switch)
- [13. bind-auth-to-machine - Bind Authorization to Server](#13-bind-auth-to-machine---bind-authorization-to-server)
- [14. update-post-paid-bind-rel - Change Pay-as-you-go Version](#14-update-post-paid-bind-rel---change-pay-as-you-go-version)
- [15. describe-property-sca-detail - Query Asset Fingerprint Software](#15-describe-property-sca-detail---query-asset-fingerprint-software)
- [16. add-uninstall-clients-by-uuids - Uninstall Client](#16-add-uninstall-clients-by-uuids---uninstall-client)
- [17. modify-push-all-task - One-click Security Check](#17-modify-push-all-task---one-click-security-check)
- [18. modify-start-vul-scan - Vulnerability Scan](#18-modify-start-vul-scan---vulnerability-scan)
- [19. describe-grouped-vul - Query Vulnerability Information](#19-describe-grouped-vul---query-vulnerability-information)
- [20. exec-strategy - Execute Baseline Check](#20-exec-strategy---execute-baseline-check)
- [21. list-check-item-warning-summary - Query Baseline Risks](#21-list-check-item-warning-summary---query-baseline-risks)
- [22. describe-susp-events - Query Security Alerts](#22-describe-susp-events---query-security-alerts)
- [23. generate-once-task - Asset Fingerprint Collection](#23-generate-once-task---asset-fingerprint-collection)
- [24. describe-strategy - Query Baseline Policies and Execution Status](#24-describe-strategy---query-baseline-policies-and-execution-status)
- [25. create-asset-selection-config - Create Asset Selection Config](#25-create-asset-selection-config---create-asset-selection-config)
- [26. add-asset-selection-criteria - Add Assets to Selection Config](#26-add-asset-selection-criteria---add-assets-to-selection-config)
- [27. update-selection-key-by-type - Associate Asset Selection to Business](#27-update-selection-key-by-type---associate-asset-selection-to-business)
- [28. create-virus-scan-once-task - Create Virus Scan Task](#28-create-virus-scan-once-task---create-virus-scan-task)
- [29. get-virus-scan-latest-task-statistic - Query Virus Scan Progress](#29-get-virus-scan-latest-task-statistic---query-virus-scan-progress)
- [30. list-virus-scan-machine - Query Virus Scan Machine List](#30-list-virus-scan-machine---query-virus-scan-machine-list)
- [31. list-virus-scan-machine-event - Query Machine Virus Events](#31-list-virus-scan-machine-event---query-machine-virus-events)
- [32. describe-once-task - Query Scan Task Status](#32-describe-once-task---query-scan-task-status)

---

## 1. describe-cloud-center-instances - Query Asset Information

**Purpose**: Query server client status (online/offline).

**CLI invocation**:
```bash
aliyun sas describe-cloud-center-instances \
  --criteria '[{"name":"instanceId","value":"i-xxx"}]' \
  --machine-types ecs \
  --page-size 20 \
  --current-page 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Common query conditions (criteria field)**:
- `instanceId`: Instance ID
- `instanceName`: Instance name
- `internetIp`: Public IP
- `intranetIp`: Private IP
- `uuid`: Asset UUID

**Key response fields**:
- `ClientStatus`: Client status (`online` / `offline` / `pause`)
- `Status`: Running status (`Running` / `notRunning`)
- `InstanceId`: Instance ID
- `Uuid`: Asset UUID
- `Os`: Operating system

---

## 2. describe-instances (ECS) - Query ECS Instance Status

**Purpose**: Query ECS instance basic information and running status.

**CLI invocation**:
```bash
aliyun ecs describe-instances \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --instance-ids '["i-xxx"]' \
  --page-size 10 \
  --page-number 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

> **[MUST] ECS API Region parameter rules** (applies to ALL ECS API calls in this skill):
> - The parameter name is `--biz-region-id` (NOT `--RegionId`, `--region-id`, or `--Region`). Using wrong parameter names causes `unknown flag` errors.
> - When the region comes from a SAS `describe-cloud-center-instances` response, use the **`RegionId`** field (e.g. `cn-hangzhou`), NOT the **`Region`** field (e.g. `cn-hangzhou-dg-a01`). The `Region` field is a physical availability zone identifier for dedicated clusters — standard ECS API endpoints do not recognize it, causing `InvalidInstance.NotFound` or `RegionId.ApiNotSupported` errors.
> - **[MUST] Endpoint routing**: When the target instance's region differs from the CLI's default configured region, you MUST also add `--region <RegionId>` to route the request to the correct ECS endpoint. `--biz-region-id` only sets the RegionId in the request body but does NOT change the API endpoint. Without `--region`, the request goes to the wrong endpoint and returns `InvalidOperation.NotSupportedEndpoint`.

**Key response fields**:
- `InstanceId`: Instance ID
- `InstanceName`: Instance name
- `Status`: Running status
- `PublicIpAddress`: Public IP
- `InnerIpAddress`: Private IP
- `OSType`: OS type (linux/windows)
- `RegionId`: Region

---

## 3. describe-cloud-assistant-status (ECS) - Query Cloud Assistant Status

**Purpose**: Check whether Cloud Assistant Agent is installed and online on ECS instances, to determine if remote command dispatch is possible.

**CLI invocation**:
```bash
aliyun ecs describe-cloud-assistant-status \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --instance-id "i-xxx" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --biz-region-id | string | Yes | Region where the instance resides |
| --instance-id | list | Yes | Instance ID list (space-separated: `--instance-id i-xxx1 i-xxx2`) |

**Key response fields**:
- `InstanceCloudAssistantStatus[]`:
  - `InstanceId`: Instance ID
  - `CloudAssistantStatus`: Cloud Assistant status (`true` = heartbeat within 2 minutes, online; `false` = offline)
  - `CloudAssistantVersion`: Cloud Assistant version (empty means not installed)

---

## 4. invoke-command / run-command (ECS) - Execute Command via Cloud Assistant

**Purpose**: Remotely execute installation commands on ECS instances via Cloud Assistant (requires Cloud Assistant to be online).

**CLI invocation**:
```bash
aliyun ecs invoke-command \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --command-id "c-xxx" \
  --instance-id "i-xxx" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

> Note: You need to first create a command via `create-command`, or use an existing command ID. Alternatively, use `run-command` for a one-step approach.

**run-command alternative**:
```bash
aliyun ecs run-command \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --type RunShellScript \
  --command-content "$(echo 'wget "https://update.aegis.aliyun.com/download/install.sh" && chmod +x install.sh && ./install.sh -k=<KEY>' | base64)" \
  --instance-id "i-xxx" \
  --content-encoding Base64 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

---

## 4b. describe-invocation-results (ECS) - Query Command Execution Results

**Purpose**: Query execution results of cloud assistant commands dispatched via invoke-command or run-command, used to poll whether remote installation completed successfully.

**CLI invocation**:
```bash
aliyun ecs describe-invocation-results \
  --region cn-hangzhou \
  --biz-region-id cn-hangzhou \
  --invoke-id "<InvokeId>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --biz-region-id | string | Yes | Region where the instance resides |
| --invoke-id | string | No | Command execution ID (returned by invoke-command or run-command) |
| --instance-id | string | No | Filter by instance ID |
| --command-id | string | No | Filter by command ID |
| --invoke-record-status | string | No | Filter by status: Running, Finished, Success, Failed, PartialFailed, Stopped |
| --content-encoding | string | No | Output encoding: PlainText (raw) or Base64 (default) |
| --max-results | integer | No | Max results per page, max 50, default 10 |
| --next-token | string | No | Pagination token from previous response |

**Key response fields**:
- `Invocation.InvocationResults.InvocationResult[]`:
  - `InvokeId`: Command execution ID
  - `InstanceId`: Instance ID
  - `InvocationStatus`: Execution status (`Running`, `Success`, `Failed`, `Stopped`, `Stopping`)
  - `ExitCode`: Command exit code (0 = success)
  - `Output`: Command output (Base64 encoded by default)
  - `ErrorInfo`: Error info if failed
  - `StartTime`: Execution start time
  - `FinishedTime`: Execution end time

> **Polling pattern**: After dispatching a command via run-command, use the returned InvokeId to poll describe-invocation-results. Check `InvocationStatus`: when it is no longer `Running`, execution is complete. Recommended polling interval: 30 seconds.

---

## 5. refresh-assets - Sync Asset Status

**Purpose**: Sync asset data when servers are not found in the asset list.

**CLI invocation**:
```bash
aliyun sas refresh-assets \
  --asset-type ecs \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
- `--asset-type`: Asset type to sync (`ecs` = servers, `cloud_product` = cloud products, `container_image` = container images)
- `--vendor`: Server vendor (0 = Alibaba Cloud, 1 = non-cloud, 2 = IDC)

---

## 6. describe-install-codes - Query Install Code List

**Purpose**: Query generated install codes and their corresponding installation commands.

**CLI invocation**:
```bash
aliyun sas describe-install-codes \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Key response fields**:
- `InstallCodes` (array):
  - `CaptchaCode`: Install verification code (the key used in install commands)
  - `Os`: Operating system (linux/windows)
  - `VendorName`: Vendor name
  - `GroupId` / `GroupName`: Group information
  - `OnlyImage`: Whether image-based installation
  - `ExpiredDate`: Expiration time (13-digit timestamp)

---

## 7. add-install-code - Create Install Code

**Purpose**: Generate a new install code and installation command.

**CLI invocation**:
```bash
aliyun sas add-install-code \
  --os linux \
  --vendor-name "ALIYUN" \
  --expired-date 1735689600000 \
  --only-image false \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --os | string | No | Operating system, defaults to linux. Values: linux, windows |
| --vendor-name | string | No | Vendor, defaults to ALIYUN |
| --group-id | long | No | Asset group ID to bind |
| --expired-date | long | No | Validity period, 13-digit timestamp |
| --only-image | boolean | No | Whether image-based installation, defaults to false |

---

## 8. create-or-update-asset-group - Create/Update Asset Group

**Purpose**: Create a new asset group, or modify the asset list of an existing group.

**CLI invocation**:

Create a new group:
```bash
aliyun sas create-or-update-asset-group \
  --group-name "<group-name>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Create a group and associate servers simultaneously:
```bash
aliyun sas create-or-update-asset-group \
  --group-name "<group-name>" \
  --uuids "<uuid1>,<uuid2>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Modify assets in an existing group:
```bash
aliyun sas create-or-update-asset-group \
  --group-id <group-ID> \
  --uuids "<uuid1>,<uuid2>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --group-name | string | Required for creation | Group name |
| --group-id | long | Required for modification | Group ID (do not pass when creating) |
| --uuids | string | No | Server UUID list, multiple separated by commas |

**Usage scenarios**:
- **Create group**: Do not pass --group-id; --group-name is required; --uuids is optional
- **Modify group assets**: --group-id and --uuids are both required

**Key response fields**:
- `GroupId`: Group ID (returns the new group ID when creating)
- `RequestId`: Request ID

---

## 9. describe-version-config - Query Version Details

**Purpose**: Get detailed information about the purchased Security Center instance, including version, feature modules, and validity period.

**CLI invocation**:
```bash
aliyun sas describe-version-config \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --resource-directory-account-id | long | No | Alibaba Cloud account ID using Security Center |
| --source-ip | string | No | Source IP |

**Key response fields**:
- `Version`: Current version number (1=Free, 3=Enterprise, 5=Advanced, 6=Anti-virus, 7=Ultimate)
- `HighestVersion`: Highest purchased version number
- `InstanceId`: Subscription instance ID
- `VmCores`: Purchased core quota
- `GmtCreate`: Purchase time (13-digit timestamp)
- `ReleaseTime`: Expiration time (13-digit timestamp)
- `IsPaidUser`: Whether a paid user
- `IsPostpay`: Whether pay-as-you-go is also enabled
- `PostPayInstanceId`: Pay-as-you-go instance ID
- `PostPayStatus`: Pay-as-you-go status (1=enabled)
- `PostPayModuleSwitch`: Pay-as-you-go feature module switches (JSON string)
- `PostPayOpenTime`: Pay-as-you-go activation time
- `AntiRansomwareCapacity`: Anti-ransomware capacity (GB)
- `LogCapacity`: Log storage capacity (GB)
- `ImageScanCapacity`: Image scan quota
- `RaspCapacity`: Application protection quota

> **[MUST] The response also contains a `MergedVersion` field — this is a sensitive internal field. NEVER display, output, save to file, or include it in any response exposed to the user. Strip it before any output.**

---

## 10. get-auth-summary - Query Authorization Summary

**Purpose**: Get authorization quota and usage statistics for each Security Center version.

**CLI invocation**:
```bash
aliyun sas get-auth-summary \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**: No required parameters.

**Key response fields**:
- `HighestVersion`: Highest purchased version number
- `Machine`: Total asset statistics
  - `TotalCoreCount`: Total cores
  - `BindCoreCount`: Bound cores
  - `UnBindCoreCount`: Unbound cores
  - `TotalEcsCount`: Total assets (count)
  - `BindEcsCount`: Bound assets (count)
  - `UnBindEcsCount`: Unbound assets (count)
  - `RiskCoreCount`: At-risk cores
  - `RiskEcsCount`: At-risk assets
- `VersionSummary[]`: Per-version details
  - `Version`: Version number
  - `TotalCount`: Total quota
  - `UnUsedCount`: Unused count
  - `UsedCoreCount`: Used cores
  - `UsedEcsCount`: Used assets
  - `TotalCoreAuthCount`: Total core authorization
  - `TotalEcsAuthCount`: Total asset authorization

---

## 11. get-serverless-auth-summary - Query Serverless Authorization

**Purpose**: Get authorization status and binding statistics for pay-as-you-go Serverless features.

**CLI invocation**:
```bash
aliyun sas get-serverless-auth-summary \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Optional parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --app-region-id | string | No | Application region ID |
| --machine-type | string | No | Server type: RunD, ECI |
| --vendor-type | string | No | Cloud product: ASK, SAE, ACS |

**Key response fields** (within `Data` object):
- `IsPostPaid`: Whether pay-as-you-go
- `IsServerlessPostPaidValid`: Whether Serverless pay-as-you-go is active
- `PostPaidStatus`: Pay-as-you-go status
- `PostPaidModuleSwitch`: Module switches (JSON string)
- `PostPaidOpenTime`: Activation time
- `AutoBind`: Whether auto-binding is enabled
- `TotalBindAppCount`: Bound application count
- `TotalBindCoreCount`: Bound core count
- `TotalBindInstanceCount`: Bound instance count

---

## 12. modify-post-pay-module-switch - Toggle Pay-as-you-go Module Switch

**Purpose**: Enable or disable pay-as-you-go feature modules.

**CLI invocation**:
```bash
aliyun sas modify-post-pay-module-switch \
  --post-pay-instance-id "<pay-as-you-go-instance-ID>" \
  --post-pay-module-switch '{"VUL": 1, "CSPM": 0}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --post-pay-instance-id | string | No | Pay-as-you-go instance ID (obtained via describe-version-config) |
| --post-pay-module-switch | string | No | Module switch JSON. Key = module code, Value = 0 (off) or 1 (on) |
| --post-paid-host-auto-bind | integer | No | Auto-bind new assets switch (0=off, 1=on) |
| --post-paid-host-auto-bind-version | integer | No | Auto-bind version (1=Free, 3=Enterprise, 5=Advanced, 6=Anti-virus, 7=Ultimate) |

**Module code reference**:
| Code | Module Name |
|------|-------------|
| POST_HOST | Host & Container Security |
| VUL | Vulnerability Fix |
| CSPM | Cloud Security Posture Management |
| AGENTLESS | Agentless Detection |
| SERVERLESS | Serverless Security |
| CTDR | Agent SOC |
| SDK | Malicious File Detection SDK |
| RASP | Application Protection |
| CTDR_STORAGE | Log Management |
| ANTI_RANSOMWARE | Anti-ransomware |
| AI_DIGITAL | Agent SOC - Security Operations Agent |
| WEB_LOCK | Web Tamper Proofing |
| IMAGE_SCAN | Image Scan |

> BASIC_SERVICE is an internal base service module and is not exposed to users. Modules not included in the request remain unchanged.

---

## 13. bind-auth-to-machine - Bind Authorization to Server

**Purpose**: Bind or unbind a specific version authorization for servers.

**CLI invocation**:

Bind authorization:
```bash
aliyun sas bind-auth-to-machine \
  --auth-version 7 \
  --bind "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Unbind authorization:
```bash
aliyun sas bind-auth-to-machine \
  --un-bind "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Batch bind:
```bash
aliyun sas bind-auth-to-machine \
  --auth-version 7 \
  --bind "<UUID1>" "<UUID2>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --auth-version | integer | No | Authorization version: 5=Advanced, 3=Enterprise, 6=Anti-virus, 7=Ultimate, 10=Value-added Service |
| --bind | list | No | UUIDs to bind (space-separated; --bind and --un-bind cannot both be empty) |
| --un-bind | list | No | UUIDs to unbind (space-separated; --bind and --un-bind cannot both be empty) |
| --bind-all | boolean | No | Whether to bind all, defaults to false |
| --auto-bind | integer | No | Auto-bind switch (0=off, 1=on) |
| --criteria | string | No | Search criteria JSON |
| --logical-exp | string | No | Multi-condition logic (OR/AND) |

**Important constraints**:
- In subscription (pre-paid) mode, any paid version binding cannot be unbound within 30 days
- K8s / ACK cluster assets only support binding to Ultimate edition (--auth-version 7)

---

## 14. update-post-paid-bind-rel - Change Pay-as-you-go Version

**Purpose**: Change the protection version binding relationship for pay-as-you-go service.

**CLI invocation**:

Bind / upgrade to paid version:
```bash
aliyun sas update-post-paid-bind-rel \
  --bind-action '[{"Version": "7", "UuidList": ["<UUID>"]}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Unbind / downgrade to free version (Version=1):
```bash
aliyun sas update-post-paid-bind-rel \
  --bind-action '[{"UuidList": ["<UUID>"], "Version": 1}]' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --bind-action | structure list | No | Binding actions JSON array. Each element: `{"Version": "<ver>", "UuidList": ["<uuid>"], "BindAll": false}`. Use `Version=1` to downgrade to free version |
| --auto-bind | integer | No | Auto-bind new assets (0=off, 1=on) |
| --auto-bind-version | integer | No | Auto-bind version number |
| --update-if-necessary | boolean | No | Whether to force version upgrade |

---

## 15. describe-property-sca-detail - Query Asset Fingerprint Software

**Purpose**: Query software information installed on servers, including middleware, databases, and web services.

**CLI invocation**:

Query by software name:
```bash
aliyun sas describe-property-sca-detail \
  --search-item name \
  --search-info "nginx" \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query by software type:
```bash
aliyun sas describe-property-sca-detail \
  --search-item type \
  --search-info "web_container" \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query database type:
```bash
aliyun sas describe-property-sca-detail \
  --biz sca_database \
  --search-item name \
  --search-info "mysql" \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --biz | string | No | Query type: sca (middleware, default), sca_database (database), sca_web (web service) |
| --biz-type | string | No | Sub-type: system_service, software_library, docker_component, database, web_container, jar, web_framework |
| --search-item | string | No | Query condition type: name (by name), type (by type) |
| --search-info | string | No | Query content (used together with --search-item) |
| --sca-name | string | No | Asset fingerprint name |
| --sca-version | string | No | Software version |
| --remark | string | No | Search condition (server name or IP, supports fuzzy search) |
| --uuid | string | No | Specific server UUID |
| --port | string | No | Process listening port |
| --pid | string | No | Process ID |
| --user | string | No | Running user |
| --current-page | integer | No | Page number, defaults to 1 |
| --page-size | integer | No | Items per page, defaults to 10 |

**Key response fields**:
- `PageInfo`: Pagination info
  - `TotalCount`: Total count
  - `CurrentPage`: Current page
  - `PageSize`: Page size
- `Propertys[]`: Software list
  - `InstanceName`: Server name
  - `InstanceId`: Instance ID
  - `InternetIp`: Public IP
  - `IntranetIp`: Private IP
  - `Name`: Software name
  - `Version`: Software version
  - `Port`: Listening port
  - `Pid`: Process ID
  - `User`: Running user
  - `BizType`: Software type
  - `BizTypeDispaly`: Type display name

---

## 16. add-uninstall-clients-by-uuids - Uninstall Client

**Purpose**: Uninstall the Security Center client from specified servers. Applicable to any server with an online client.

**CLI invocation**:

Uninstall from a single server:
```bash
aliyun sas add-uninstall-clients-by-uuids \
  --uuids "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Batch uninstall from multiple servers:
```bash
aliyun sas add-uninstall-clients-by-uuids \
  --uuids "<UUID1>,<UUID2>,<UUID3>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --uuids | string | Yes | Server UUIDs to uninstall client from, multiple separated by commas. Obtained via describe-cloud-center-instances |
| --biz-region | string | No | Server region |
| --call-method | string | No | Method name, defaults to init |
| --feedback | string | No | Feedback info (e.g., reinstall) |
| --source-ip | string | No | Source IP, auto-detected by the system |

**Key response fields**:
- `RequestId`: Request ID

**Important constraints**:
- Client status must be `online` to execute uninstallation; offline clients cannot be uninstalled via this API
- After uninstallation, the server loses all Security Center protection capabilities
- Insufficient permissions return `403 NoPermission`; contact the primary account to configure RAM permissions

---

## 17. modify-push-all-task - One-click Security Check

**Purpose**: Dispatch security check tasks to specified servers.

**CLI invocation**:
```bash
aliyun sas modify-push-all-task \
  --uuids "<UUID1>,<UUID2>" \
  --tasks "OVAL_ENTITY,CMS,SYSVUL,SCA,HEALTH_CHECK,WEBSHELL,PROC_SNAPSHOT,PORT_SNAPSHOT,ACCOUNT_SNAPSHOT,SOFTWARE_SNAPSHOT,SCA_SNAPSHOT" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --uuids | string | Yes | Server UUID list, multiple separated by commas |
| --tasks | string | Yes | Check items list, multiple separated by commas |
| --source-ip | string | No | Source IP, auto-detected by the system |

**Tasks check item descriptions**:

*Vulnerability scanning*:
| Check Item | Description |
|------------|-------------|
| OVAL_ENTITY | Linux vulnerability detection (CVE) |
| CMS | Web-CMS vulnerability detection |
| SYSVUL | Windows system vulnerability detection |

*Security detection*:
| Check Item | Description |
|------------|-------------|
| HEALTH_CHECK | Baseline check (requires subscription host protection Version>1 or pay-as-you-go CSPM=1; otherwise do not include) |
| WEBSHELL | Web shell detection |

*Asset fingerprint collection*:
| Check Item | Description |
|------------|-------------|
| SCA | Middleware fingerprint collection |
| SCA_SNAPSHOT | Middleware snapshot |
| PROC_SNAPSHOT | Process snapshot |
| PORT_SNAPSHOT | Port snapshot |
| ACCOUNT_SNAPSHOT | Account snapshot |
| SOFTWARE_SNAPSHOT | Software snapshot |

> This API performs a comprehensive security check covering vulnerability scanning, baseline detection, and asset fingerprint collection. It is suitable for thorough security inspection of specified assets. HEALTH_CHECK (baseline check) should only be included in Tasks when the user has subscription host protection (Version>1) or has enabled Cloud Security Posture Management pay-as-you-go (CSPM=1); otherwise exclude it.

**Key response fields**:
- `RequestId`: Request ID
- `PushTaskRsp.PushTaskResultList[]`: Task execution results
  - `Uuid`: Server UUID
  - `InstanceName`: Server name
  - `Success`: Whether execution succeeded
  - `Online`: Whether client is online
  - `Message`: Detailed failure information

**Important constraints**:
- Target servers must be bound to a paid version (not Free edition); Free edition returns `FreeVersionNotPermit` error
- Servers with offline clients cannot execute check tasks
- Check results are obtained by polling the corresponding APIs (describe-once-task / describe-strategy / get-virus-scan-latest-task-statistic)

---

## 18. modify-start-vul-scan - Vulnerability Scan

**Purpose**: Trigger one-click vulnerability scanning.

**CLI invocation**:

Scan all vulnerability types:
```bash
aliyun sas modify-start-vul-scan \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Specify vulnerability types and servers:
```bash
aliyun sas modify-start-vul-scan \
  --types "cve,sys,cms" \
  --uuids "<UUID1>,<UUID2>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --types | string | No | Vulnerability types, multiple separated by commas. Omit to scan all types. Values: cve (Linux), sys (Windows), cms (Web-CMS), app (application vulnerability - scan), sca (application vulnerability - component analysis) |
| --uuids | string | No | Server UUID list. Omit to scan all servers |

**Key response fields**:
- `RequestId`: Request ID

---

## 19. describe-grouped-vul - Query Vulnerability Information

**Purpose**: Query vulnerability risk statistics grouped by vulnerability.

**CLI invocation**:

Query unhandled Linux vulnerabilities:
```bash
aliyun sas describe-grouped-vul \
  --type cve \
  --dealed n \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query high-priority vulnerabilities:
```bash
aliyun sas describe-grouped-vul \
  --necessity asap \
  --dealed n \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --type | string | No | Vulnerability type, defaults to cve. Values: cve (Linux), sys (Windows), cms (Web-CMS), app (application - scan), sca (application - component analysis) |
| --dealed | string | No | Whether handled: y (handled), n (unhandled) |
| --necessity | string | No | Fix priority, multiple separated by commas: asap (high), later (medium), nntf (low) |
| --alias-name | string | No | Vulnerability alias (fuzzy search) |
| --cve-id | string | No | CVE ID |
| --uuids | string | No | Server UUIDs, multiple separated by commas |
| --group-id | string | No | Asset group ID |
| --current-page | integer | No | Page number, defaults to 1 |
| --page-size | integer | No | Items per page, defaults to 10 |
| --lang | string | No | Language: zh (Chinese), en (English), defaults to zh |

**Key response fields**:
- `TotalCount`: Total count
- `GroupedVulItems[]`: Vulnerability information list
  - `AliasName`: Vulnerability alias
  - `Name`: Vulnerability name
  - `Type`: Vulnerability type
  - `AsapCount`: High-priority count
  - `LaterCount`: Medium-priority count
  - `NntfCount`: Low-priority count
  - `HandledCount`: Handled count
  - `GmtFirst`: First discovery time (13-digit timestamp)
  - `GmtLast`: Last discovery time (13-digit timestamp)
  - `Related`: Related CVE list
  - `Tags`: Vulnerability tags (e.g., "remote exploitation", "code execution")

---

## 20. exec-strategy - Execute Baseline Check

**Purpose**: Execute a specified baseline check policy.

**CLI invocation**:
```bash
aliyun sas exec-strategy \
  --strategy-id <strategy-ID> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --strategy-id | integer | No | Baseline check policy ID |
| --exec-action | string | No | Execution action, defaults to exec |
| --lang | string | No | Language: zh (Chinese), en (English), defaults to zh |

**Key response fields**:
- `RequestId`: Request ID

---

## 21. list-check-item-warning-summary - Query Baseline Risks

**Purpose**: Get risk statistics for baseline check items.

**CLI invocation**:

Query failed check items:
```bash
aliyun sas list-check-item-warning-summary \
  --check-warning-status 1 \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query high-risk items:
```bash
aliyun sas list-check-item-warning-summary \
  --check-warning-status 1 \
  --check-level high \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --check-warning-status | integer | No | Risk status: 1 (failed), 3 (passed), 6 (whitelisted), 8 (fixed). Defaults to all |
| --check-level | string | No | Risk level: high, medium, low. Defaults to all |
| --check-type | string | No | Check item category name |
| --check-item-fuzzy | string | No | Check item name fuzzy match |
| --group-id | long | No | Asset group ID |
| --current-page | integer | No | Page number, defaults to 1 |
| --page-size | integer | No | Items per page, defaults to 20 |
| --lang | string | No | Language: zh (Chinese), en (English), defaults to zh |

**Key response fields**:
- `PageInfo`: Pagination info
  - `TotalCount`: Total count
  - `CurrentPage`: Current page
- `List[]`: Check item risk list
  - `CheckItem`: Check item description
  - `CheckLevel`: Risk level (high/medium/low)
  - `CheckType`: Check item category
  - `Status`: Risk status (1=failed, 3=passed, 6=whitelisted, 8=fixed)
  - `WarningMachineCount`: Number of affected machines
  - `Advice`: Remediation advice
  - `Description`: Detailed description
  - `CheckId`: Check item ID

---

## 22. describe-susp-events - Query Security Alerts

**Purpose**: Query security alert event list.

**CLI invocation**:

Query pending alerts:
```bash
aliyun sas describe-susp-events \
  --dealed N \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query critical alerts:
```bash
aliyun sas describe-susp-events \
  --dealed N \
  --levels serious \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query alerts for a specific server:
```bash
aliyun sas describe-susp-events \
  --uuids "<UUID>" \
  --dealed N \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --dealed | string | No | Whether handled: N (pending), Y (handled) |
| --levels | string | No | Alert level, multiple separated by commas: serious (critical), suspicious (suspicious), remind (informational) |
| --parent-event-types | string | No | Alert type (e.g., abnormal process behavior, web shell, abnormal login) |
| --remark | string | No | Alert name or asset info (supports fuzzy query) |
| --uuids | string | No | Server UUIDs, multiple separated by commas |
| --group-id | long | No | Asset group ID |
| --name | string | No | Affected asset name |
| --status | string | No | Event status: 1 (pending), 2 (ignored), 4 (confirmed), 32 (resolved) |
| --current-page | string | No | Page number, defaults to 1 |
| --page-size | string | No | Items per page, defaults to 20, max 100 |
| --lang | string | No | Language: zh (Chinese), en (English), defaults to zh |

**Key response fields**:
- `TotalCount`: Total alert event count
- `SuspEvents[]`: Alert event list
  - `AlarmEventNameDisplay`: Alert name
  - `AlarmEventTypeDisplay`: Alert type
  - `Level`: Severity level (serious/suspicious/remind)
  - `InstanceName`: Affected instance name
  - `InstanceId`: Instance ID
  - `InternetIp`: Public IP
  - `IntranetIp`: Private IP
  - `Uuid`: Instance UUID
  - `OccurrenceTime`: First occurrence time
  - `LastTime`: Last occurrence time
  - `EventStatus`: Event status (1=pending, 4=confirmed, 32=resolved)
  - `Desc`: Alert description
  - `AlarmUniqueInfo`: Alert unique identifier
  - `Details[]`: Alert detail list
    - `NameDisplay`: Detail display name
    - `ValueDisplay`: Detail display value

---

## 23. generate-once-task - Asset Fingerprint Collection

**Purpose**: Trigger a one-time asset fingerprint collection task across all servers, collecting account, port, process, software, cron job, and other information.

**CLI invocation**:
```bash
aliyun sas generate-once-task \
  --task-type "ASSETS_COLLECTION" \
  --task-name "ASSETS_COLLECTION" \
  --param '{"items":"ACCOUNT_SNAPSHOT,PORT_SNAPSHOT,PROC_SNAPSHOT,SOFTWARE_SNAPSHOT,CROND_SNAPSHOT,SCA_SNAPSHOT,LKM_SNAPSHOT,AUTORUN_SNAPSHOT,SCA_PROXY_SNAPSHOT"}' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --task-type | string | Yes | Task type, fixed as `ASSETS_COLLECTION` for asset fingerprint collection |
| --task-name | string | Yes | Task name, fixed as `ASSETS_COLLECTION` for asset fingerprint collection |
| --param | string | Yes | Task parameter JSON. The `items` field specifies collection items, comma-separated |

**Collection items**:
| Item | Description |
|------|-------------|
| ACCOUNT_SNAPSHOT | Account snapshot |
| PORT_SNAPSHOT | Port snapshot |
| PROC_SNAPSHOT | Process snapshot |
| SOFTWARE_SNAPSHOT | Software snapshot |
| CROND_SNAPSHOT | Cron job snapshot |
| SCA_SNAPSHOT | Middleware snapshot |
| LKM_SNAPSHOT | Kernel module snapshot |
| AUTORUN_SNAPSHOT | Auto-start item snapshot |
| SCA_PROXY_SNAPSHOT | Proxy middleware snapshot |

**Key response fields**:
- `RequestId`: Request ID

---

## 24. describe-strategy - Query Baseline Policies and Execution Status

**Purpose**: Query baseline check policy list to obtain policy IDs for exec-strategy, and check execution progress via ExecStatus.

**CLI invocation**:

Query all policies:
```bash
aliyun sas describe-strategy \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query standard policies:
```bash
aliyun sas describe-strategy \
  --custom-type common \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Query custom policies:
```bash
aliyun sas describe-strategy \
  --custom-type custom \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --custom-type | string | No | Policy type: common (standard), custom (custom). Omit to query all |
| --strategy-ids | string | No | Policy ID list, multiple separated by commas |
| --lang | string | No | Language: zh (Chinese), en (English), defaults to zh |

**Key response fields**:
- `Strategies[]`: Policy list
  - `Id`: Policy ID (the --strategy-id parameter for exec-strategy)
  - `Name`: Policy name
  - `CustomType`: Policy type (common=standard / custom=custom)
  - `CycleDays`: Check cycle (days)
  - `StartTime`: Execution start time
  - `EndTime`: Execution end time
  - `EcsCount`: Associated server count
  - `RiskCount`: Risk item count
  - `PassRate`: Pass rate (percentage)
  - `ExecStatus`: Execution status (1=not executed/completed, 2=in progress)
  - `Percent`: Check progress percentage (only returned when ExecStatus=2)

> **Polling baseline check progress**: After triggering exec-strategy, poll describe-strategy to check the corresponding policy's ExecStatus. When ExecStatus=2, the check is in progress and you can get progress via Percent. When ExecStatus returns to 1, execution is complete. Recommended polling interval: 30 seconds.

---

## 25. create-asset-selection-config - Create Asset Selection Config

**Purpose**: Create an asset selection configuration for virus scanning and other business operations, and obtain a SelectionKey.

**CLI invocation**:

Specify instances:
```bash
aliyun sas create-asset-selection-config \
  --business-type "VIRUS_SCAN_ONCE_TASK" \
  --target-type "instance" \
  --platform "all" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

All instances:
```bash
aliyun sas create-asset-selection-config \
  --business-type "VIRUS_SCAN_ONCE_TASK" \
  --target-type "all_instance" \
  --platform "all" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --business-type | string | Yes | Business type, must be the exact string value: `VIRUS_SCAN_ONCE_TASK` (one-time virus scan) or `VIRUS_SCAN_CYCLE_CONFIG` (periodic virus scan). Do NOT use numeric codes |
| --target-type | string | Yes | Target type: `all_instance` (all servers), `instance` (by instance), `group` (by group), `vpc` (by VPC) |
| --platform | string | No | OS platform: `all`, `windows`, `linux`. Defaults to all |

**Key response fields**:
- `Data.SelectionKey`: Asset selection unique identifier (used in subsequent steps)
- `Data.BusinessType`: Business type
- `Data.TargetType`: Target type

---

## 26. add-asset-selection-criteria - Add Assets to Selection Config

**Purpose**: When TargetType is `instance`, add specific target assets to the SelectionKey.

**CLI invocation**:

Add a single asset:
```bash
aliyun sas add-asset-selection-criteria \
  --selection-key "<SelectionKey>" \
  --target-operation-list Target="<UUID>" Operation=add \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Add multiple assets:
```bash
aliyun sas add-asset-selection-criteria \
  --selection-key "<SelectionKey>" \
  --target-operation-list Target="<UUID1>" Operation=add \
  --target-operation-list Target="<UUID2>" Operation=add \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --selection-key | string | Yes | Asset selection identifier returned by create-asset-selection-config |
| --target-operation-list | struct list | No | Each entry: `Target=<UUID> Operation=<add\|del>`. Repeat for multiple assets |

**Key response fields**:
- `RequestId`: Request ID

---

## 27. update-selection-key-by-type - Associate Asset Selection to Business

**Purpose**: Associate an asset selection configuration (SelectionKey) to a specified business type.

**CLI invocation**:
```bash
aliyun sas update-selection-key-by-type \
  --business-type "VIRUS_SCAN_ONCE_TASK" \
  --selection-key "<SelectionKey>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --business-type | string | No | Business type, same as create-asset-selection-config |
| --selection-key | string | No | Asset selection identifier |

**Key response fields**:
- `RequestId`: Request ID

---

## 28. create-virus-scan-once-task - Create Virus Scan Task

**Purpose**: Create a one-time virus scan task.

**CLI invocation**:
```bash
aliyun sas create-virus-scan-once-task \
  --scan-type "system" \
  --selection-key "<SelectionKey>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --scan-type | string | No | Scan type: `system` (system scan, full-disk key paths), `user` (custom scan, requires --scan-path) |
| --selection-key | string | No | Asset selection identifier |
| --scan-path | list | No | Custom scan paths (only used when --scan-type=user, space-separated) |

**Key response fields**:
- `RequestId`: Request ID

**Invocation flow**: Complete create-asset-selection-config -> [add-asset-selection-criteria] -> update-selection-key-by-type before calling this API.

---

## 29. get-virus-scan-latest-task-statistic - Query Virus Scan Progress

**Purpose**: Query the progress and statistics of the most recent virus scan task.

**CLI invocation**:
```bash
aliyun sas get-virus-scan-latest-task-statistic \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**: No required parameters.

**Key response fields**:
- `Data.TaskId`: Task ID
- `Data.Status`: Task status (10=in progress, 20=completed)
- `Data.Progress`: Progress percentage
- `Data.ScanType`: Scan type (system / user)
- `Data.ScanTime`: Scan start time (13-digit timestamp)
- `Data.ScanMachine`: Total machines scanned
- `Data.CompleteMachine`: Completed machine count
- `Data.UnCompleteMachine`: Incomplete machine count
- `Data.SafeMachine`: Safe machine count (no virus found)
- `Data.SuspiciousMachine`: Machine count with viruses found
- `Data.SuspiciousCount`: Total virus count found

---

## 30. list-virus-scan-machine - Query Virus Scan Machine List

**Purpose**: Query the list of machines involved in virus scanning.

**CLI invocation**:
```bash
aliyun sas list-virus-scan-machine \
  --current-page 1 \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

Filter by asset:
```bash
aliyun sas list-virus-scan-machine \
  --current-page 1 \
  --page-size 20 \
  --uuid "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --current-page | integer | Yes | Current page number |
| --page-size | integer | Yes | Items per page |
| --uuid | string | No | Filter by asset UUID |
| --remark | string | No | Fuzzy search by asset name or IP |

**Key response fields**:
- `Data[]`: Machine list
- `PageInfo.TotalCount`: Total count

---

## 31. list-virus-scan-machine-event - Query Machine Virus Events

**Purpose**: Query virus scan event details for a specified machine.

**CLI invocation**:
```bash
aliyun sas list-virus-scan-machine-event \
  --current-page 1 \
  --page-size 20 \
  --uuid "<UUID>" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --current-page | integer | Yes | Current page number |
| --page-size | integer | Yes | Items per page |
| --uuid | string | No | Asset UUID |
| --lang | string | No | Language: zh (Chinese), en (English) |

**Key response fields**:
- `Data[]`: Virus event list
- `PageInfo.TotalCount`: Total count

---

## 32. describe-once-task - Query Scan Task Status

**Purpose**: Query execution status and progress of one-time tasks such as vulnerability scans and asset collection, used for polling task completion.

**CLI invocation**:

Query vulnerability scan task:
```bash
aliyun sas describe-once-task \
  --task-type "VUL_CHECK_TASK" \
  --current-page 1 \
  --page-size 5 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| --task-type | string | No | Task type: `VUL_CHECK_TASK` (vulnerability scan), `CLIENT_PROBLEM_CHECK` (client check), `CLIENT_DEV_OPS` (cloud operations), `ASSET_SECURITY_CHECK` (asset collection). Cannot be empty simultaneously with --root-task-id |
| --root-task-id | string | No | Root task ID. Cannot be empty simultaneously with --task-type |
| --task-id | string | No | Task ID |
| --source | string | No | Task source: `schedule` (auto-scheduled), `console` (one-click check) |
| --start-time-query | long | No | Root task start timestamp (milliseconds) |
| --end-time-query | long | No | Root task end timestamp (milliseconds) |
| --current-page | integer | No | Current page number, defaults to 1 |
| --page-size | integer | No | Items per page, defaults to 20 |

**Key response fields**:
- `TaskManageResponseList[]`: Task list
  - `TaskId`: Task ID
  - `TaskType`: Task type
  - `TaskName`: Task name
  - `TaskStatus`: Task status number (1=in progress)
  - `TaskStatusText`: Task status text (`PROCESSING`=in progress)
  - `Progress`: Progress percentage (e.g., "40%")
  - `TotalCount`: Total machine count
  - `SuccessCount`: Completed machine count
  - `FailCount`: Failed machine count
  - `TaskStartTime`: Task start timestamp (milliseconds)
  - `Source`: Task source (schedule / console)
  - `Context`: Task context (JSON string, contains scan type info)
- `PageInfo.TotalCount`: Total task count

> **Polling vulnerability scan progress**: After triggering modify-start-vul-scan, poll describe-once-task (--task-type=VUL_CHECK_TASK) and check the latest task's TaskStatusText. When it is no longer `PROCESSING`, the scan is complete. Recommended polling interval: 30 seconds.
