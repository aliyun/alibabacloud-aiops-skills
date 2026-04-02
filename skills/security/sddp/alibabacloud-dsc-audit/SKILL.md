---
name: alibabacloud-dsc-audit
description: |
  Query and handle security risk events from Alibaba Cloud Data Security Center. Supports viewing the list of unprocessed risk events and performing manual handling operations on risk events.
  Trigger words: "Data Security Center", "security risk events", "DSC", "risk handling", "DescribeRiskRules", "PreHandleAuditRisk"
---

# Alibaba Cloud Data Security Center Risk Event Query and Handling

This skill uses Alibaba Cloud Python Common SDK (generic invocation) to query security risk events from the Data Security Center and handle them.

## Architecture

```
User → Python Common SDK → Data Security Center (Sddp) API
                              ├── DescribeRiskRules (Query risk events)
                              └── PreHandleAuditRisk (Handle risk events)
```

## Installation

```bash
pip3 install -r scripts/requirements.txt
```

Or install packages individually:
```bash
pip3 install alibabacloud_tea_openapi==0.4.3 alibabacloud_credentials==1.0.8 alibabacloud_tea_util==0.3.14 alibabacloud_openapi_util==0.2.4
```

> **Pre-check: Aliyun CLI >= 3.3.1 required**
> Run `aliyun version` to verify >= 3.3.1. If not installed or version too low,
> see `references/cli-installation-guide.md` for installation instructions.
> Then [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

## Authentication

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

## RAM Permissions

Before using this skill, ensure the current user has the required RAM permissions. For detailed permission lists and policy configurations, refer to [references/ram-policies.md](references/ram-policies.md)

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter | Required/Optional | Description | Default |
|-----------|-------------------|-------------|---------|
| `CurrentPage` | Optional | Current page number | 1 |
| `PageSize` | Optional | Records per page | 10 |
| `HandleStatus` | Optional | Processing status, PROCESSED means handled, UNPROCESSED means not handled | UNPROCESSED |
| `RiskId` | Required for handling | Risk event ID | - |
| `HandleDetail` | Required for handling | Handling details description | - |

## Core Workflow

### Step 1: Query Unprocessed Security Risk Events

Use the `scripts/query_risk.py` script to query unprocessed security risk events. This is a paginated API that returns the first 20 records by default.

```bash
python3 scripts/query_risk.py
```

Example output:
```
Found 31 unprocessed security risk events
================================================================================
Risk ID: 75110196
Rule Name: jiangyu_test_mysqldump
Risk Level: High Risk
Product Type: RDS
Alert Count: 20
Asset Count: 2
Rule Category: Database Dump Attack
--------------------------------------------------------------------------------
```

### Query Result Field Descriptions

The query results return the following key fields. **Risk Event ID (RiskId) is a required parameter for handling**:

| Field | Description |
|-------|-------------|
| **RiskId** | Risk event ID, **required for handling** |
| RuleName | Rule name |
| WarnLevelName | Risk level (High Risk/Medium Risk/Low Risk) |
| ProductCode | Product type (RDS/OSS, etc.) |
| AlarmCount | Alert count |
| InstanceCount | Number of affected assets |
| FirstAlarmTime | First discovery time |
| LastAlarmTime | Last discovery time |

### Step 2: Handle Security Risk Events

Use the `scripts/handle_risk.py` script to handle specified risk events.

```bash
python3 scripts/handle_risk.py <RiskID> <HandleDetail>
```

Example:
```bash
python3 scripts/handle_risk.py 75110196 "Confirmed as false positive, closing this alert"
```

Example output:
```
Handling risk event...
Risk ID: 75110196
Handle Detail: Confirmed as false positive, closing this alert
--------------------------------------------------
✅ Handling successful!
RequestId: C34D813F-A234-5D66-842D-504D84D5C680
```

### Handling Parameter Descriptions

| Parameter | Description |
|-----------|-------------|
| `RiskId` | Risk event ID, obtained from `DescribeRiskRules` API |
| `HandleType` | Handling type, fixed as `Manual` (manual handling) |
| `HandleMethod` | Handling method, fixed as `0` |
| `HandleDetail` | Handling details, **requires user to input specific handling description** |

## Success Verification

### Verify Query Operation

1. After executing the query code, check if the returned `statusCode` is `200`
2. Check if the returned `body` contains the `Items` list
3. Verify that `TotalCount` matches the actual number of returned records

### Verify Handling Operation

1. After executing the handling code, check if the returned `statusCode` is `200`
2. Call `DescribeRiskRules` again to query the `RiskId` and confirm the status has changed

## Cleanup

This skill is primarily used for query and handling operations, does not involve resource creation, and requires no cleanup.

## API and Command Reference

| Product | API Action | Script | Description |
|---------|------------|--------|-------------|
| Sddp | DescribeRiskRules | `scripts/query_risk.py` | Query security risk events |
| Sddp | PreHandleAuditRisk | `scripts/handle_risk.py` | Handle security risk events |

### Script Usage

| Script | Usage | Description |
|--------|-------|-------------|
| `query_risk.py` | `python3 scripts/query_risk.py` | Execute directly, no parameters required |
| `handle_risk.py` | `python3 scripts/handle_risk.py <RiskID> <HandleDetail>` | Requires Risk ID and handling description |

For detailed API information, refer to [references/related-apis.md](references/related-apis.md)

## Best Practices

1. **Paginated Query**: When using paginated APIs, increment the `CurrentPage` parameter until all records are retrieved
2. **Record RiskId**: The `RiskId` in query results is a required parameter for handling operations, make sure to record it
3. **Handle Description**: Provide a clear `HandleDetail` description when handling for subsequent auditing
4. **Error Handling**: Implement retry mechanisms for temporary errors like `Throttling`
5. **Credential Security**: Use `CredentialClient` to manage credentials, do not hardcode AK/SK

## Reference Links

| Reference Document | Description |
|--------------------|-------------|
| [references/related-apis.md](references/related-apis.md) | API detailed documentation |
| [references/ram-policies.md](references/ram-policies.md) | RAM permission configuration |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation guide |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria |
| [Generic Invocation Documentation](https://help.aliyun.com/zh/sdk/developer-reference/generalized-call-python) | Alibaba Cloud Python SDK generic invocation documentation |

## Important Notes

> **Warning**: This skill **only** uses the Data Security Center's `DescribeRiskRules` and `PreHandleAuditRisk` APIs.
> If these two APIs cannot be found, report an error. **Do NOT call other OpenAPIs without authorization**.
> Do not use Alibaba Cloud CLI tools to call APIs.
