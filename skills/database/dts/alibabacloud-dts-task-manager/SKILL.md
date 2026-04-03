---
name: alibabacloud-dts-task-manager
description: "Create, view, and manage Alibaba Cloud DTS data migration/synchronization tasks interactively. Automatically triggered when the user mentions keywords such as \"DTS task\", \"DTS migration\", \"DTS sync\", \"data migration task\", \"data sync task\", \"create migration\", \"create DTS\", \"new DTS\", \"DTS status\", \"migration status\", \"sync status\", \"stop migration\", \"suspend DTS\", \"release DTS\"."
---

# Alibaba Cloud DTS Task Manager

## Overview

Manage Alibaba Cloud DTS (Data Transmission Service) tasks: create data migration/synchronization tasks, view task status/latency, stop/start/release tasks. All operations are guided interactively.

## Parameter Parsing

Determine the operation mode based on user input, and read the corresponding references file for detailed workflow:

| User Intent | Keywords | Action | Reference File |
|------------|----------|--------|---------------|
| Create migration task | empty / "create" / "new" / "migration" | Interactive creation | `references/create-task.md` |
| Create sync task | "sync" / "synchronization" | Interactive sync task creation | `references/create-task.md` |
| View task list | "list" / "view" / "ls" | List all tasks | `references/list-tasks.md` |
| View task status | "status ID" | View specified task details | `references/task-status.md` |
| Stop task | "stop ID" / "suspend ID" / "pause ID" | Suspend specified task | `references/suspend-task.md` |
| Start/Resume task | "start ID" / "resume ID" | Start or resume task | `references/start-task.md` |
| Release task | "release ID" / "delete ID" / "remove ID" | Release (delete) task | `references/delete-task.md` |
| Environment setup | "setup" / "configure" / "init" | Check and configure environment | `references/setup.md` |

When no parameters are provided, ask the user to choose the desired operation.

## Step-by-Step Operation Workflows

### Create Task (Migration / Sync)

**Steps** (full details in `references/create-task.md`):
1. Prerequisites check (CLI installed, auth configured)
2. Select Region + Task type (MIGRATION or SYNC)
3. Configure source: engine type, access method, connection info, optional SSL
4. Configure destination: engine type, access method, connection info, optional SSL
5. Define migration objects: full database or specific tables, with optional name mapping
6. Select migration types: schema / full data / incremental (default: all)
7. Select instance class: micro / small / medium / large
8. Review summary (passwords shown as `******`) and confirm
9. Execute: CreateDtsInstance -> ConfigureDtsJob -> StartDtsJob
10. On failure at any step after instance creation, auto-release the instance

**Example input**: "Create a MySQL to Kafka sync task"
**Example output**:
```
DTS task created successfully!
  Instance ID: <dts-instance-id>
  Job ID:      <job-id>
  Status:      Initializing

To check status:  aliyun dts DescribeDtsJobDetail --DtsJobId <job-id> --RegionId cn-hangzhou
```

### List Tasks

**Steps** (full details in `references/list-tasks.md`):
1. Prerequisites check
2. Query tasks by each JobType (MIGRATION, SYNC, SUBSCRIBE) separately
3. Display consolidated results in table format

**Example input**: "List my DTS tasks"
**Example output**:
```
| Task ID        | Name                         | Type      | Status         | Source       | Destination  | Delay  |
|----------------|------------------------------|-----------|----------------|--------------|--------------|--------|
| <job-id-1>     | migration-mysql-mysql-0401   | MIGRATION | Migrating      | RDS MySQL    | RDS MySQL    | -      |
| <job-id-2>     | sync-mysql-kafka-0401        | SYNC      | Synchronizing  | RDS MySQL    | Kafka        | 128ms  |
```

### View Task Status

**Steps** (full details in `references/task-status.md`):
1. Prerequisites check
2. Resolve ID: if only one ID given, look up via DescribeDtsJobs first
3. Call DescribeDtsJobDetail
4. Display status, progress, delay (convert ms to readable format)

**Example input**: "Check status of <job-id>"
**Example output**:
```
Task: <job-id> (migration-mysql-mysql-0401)
Type:   MIGRATION
Status: Migrating
Progress:
  Schema migration:    Finished
  Full data migration: Finished (1,234,567 rows)
  Incremental:         Running, delay 236ms
Source:      RDS MySQL <source-instance-id> (cn-hangzhou)
Destination: RDS MySQL <dest-instance-id> (cn-hangzhou)
```

### Stop / Start / Release Task

**Stop** (full details in `references/suspend-task.md`):
1. Resolve ID, display task info, confirm, then call SuspendDtsJob

**Start/Resume** (full details in `references/start-task.md`):
1. Resolve ID, then call StartDtsJob

**Release/Delete** (full details in `references/delete-task.md`):
1. Resolve ID
2. **Pre-check**: call DescribeDtsJobDetail to check current status
3. If task is active (Synchronizing/Migrating/InitializingDataLoad), warn user and require explicit confirmation
4. Double confirmation required before calling DeleteDtsJob

### Environment Setup

**Steps** (full details in `references/setup.md`):
1. Check aliyun CLI installation
2. Check authentication configuration
3. Test connectivity with a DescribeDtsJobs call

## Edge Cases

- **User provides only one ID**: Try it as DtsJobId first; look up DtsInstanceId via DescribeDtsJobs. If DtsInstanceID field is empty on the task, pass only DtsJobId.
- **API parameter case inconsistency**: `DescribeDtsJobDetail` uses `--DtsInstanceID` (uppercase D), while `DeleteDtsJob`/`ConfigureDtsJob` use `--DtsInstanceId` (lowercase d). Always verify with `aliyun dts <API> help` before calling.
- **Ambiguous ID format**: If the ID doesn't clearly match DtsJobId or DtsInstanceId pattern, fuzzy search via DescribeDtsJobs.
- **Delete active task**: Never delete a running task without pre-check. Query status first; if Synchronizing/Migrating, prompt user to suspend first or explicitly confirm forced deletion.
- **Creation failure mid-flow**: If CreateDtsInstance succeeds but ConfigureDtsJob or StartDtsJob fails, auto-release the created instance to avoid ongoing charges.
- **Timeout / retry**: All API calls use `--read-timeout 30 --connect-timeout 10`. CreateDtsInstance includes `--ClientToken` (UUID) for idempotent retries.
- **Multi-region queries**: When listing tasks, query MIGRATION/SYNC/SUBSCRIBE separately per region. The `--JobType` parameter defaults to MIGRATION; omitting it silently drops sync/subscribe tasks. Never use `--Type` (causes InvalidParameter).
- **MongoDB specifics**: MongoDB endpoints require `--SourceEndpointDatabaseName` in ConfigureDtsJob.

## Interaction Rules

**Important: All information gathering must use interactive selections to avoid workflow interruption from free-text questions.**

### Selection-type information: Provide fixed options
Applicable to scenarios with fixed choices: task type, engine type, access method, instance selection, migration type, specification selection, etc.

### Free-input information: Provide common defaults + custom input
Applicable to scenarios requiring user free input: IP address, port, username, password, database name, table name, etc.
Provide common default values as options; users can select or enter custom values.
Consolidate related input items into as few interaction rounds as possible.

### Sensitive information: Never display in plaintext

**CRITICAL**: Passwords, AccessKey Secrets, certificates, and private keys must **NEVER** appear in plaintext anywhere in the conversation — this applies to ALL stages:

- **During collection**: When the user provides a password or secret in a message (e.g., "password: MyPass123"), you MUST immediately treat it as sensitive. **Do NOT quote, repeat, summarize, or reference the plaintext value in your response.** Simply acknowledge receipt, e.g., "Source database password received." Then internally store it for later CLI execution. Even if the user typed the password in plain text, your reply must NEVER contain it.
- **When summarizing user input**: If the user provides multiple fields including a password in one message (e.g., "username: dts, password: abc123"), your acknowledgment must mask the password: "Username: dts, Password: ******". Never reproduce the password portion of the user's message.
- **In confirmation summaries**: Always show `******` for password fields.
- **In CLI commands displayed to the user**: Show passwords as `'******'`, never the actual value. The real value is only used internally when executing the command.
- **In error messages / logs**: If an API error response contains sensitive fields, redact them before displaying.
- **In stored variables or references**: Never repeat the plaintext value in follow-up messages.
- **In local files**: Never write passwords or secrets to any local file (scripts, configs, logs, temp files, etc.). All sensitive values must only exist in memory during CLI execution.

Use single quotes around passwords in actual CLI execution to prevent shell expansion.

## Prerequisites

**Before executing any operation, the following checks must be performed:**

### 1. Check aliyun CLI installation

```bash
which aliyun
```

If not installed, prompt the user:
- macOS: `brew install aliyun-cli`
- Or download from https://github.com/aliyun/aliyun-cli/releases
- After installation, run `aliyun configure` to set up authentication

### 2. Check authentication configuration

```bash
aliyun configure list
```

If not configured, guide the user through setup:
```bash
aliyun configure --mode AK
```
Requires: AccessKey ID, AccessKey Secret, Region Id

**Important**: Never display the user's AccessKey Secret in the conversation. Protect sensitive information.

### 3. Select Region

Let the user select a Region using interactive choices, not text input.

Supported Region list:

**Mainland China**:
| Region ID | Name |
|-----------|------|
| cn-beijing | China North 2 (Beijing) |
| cn-hangzhou | China East 1 (Hangzhou) |
| cn-shanghai | China East 2 (Shanghai) |
| cn-shenzhen | China South 1 (Shenzhen) |
| cn-guangzhou | China South 3 (Guangzhou) |
| cn-qingdao | China North 1 (Qingdao) |
| cn-zhangjiakou | China North 3 (Zhangjiakou) |
| cn-huhehaote | China North 5 (Hohhot) |
| cn-wulanchabu | China North 6 (Ulanqab) |
| cn-heyuan | China South 2 (Heyuan) |
| cn-chengdu | China Southwest 1 (Chengdu) |
| cn-nanjing | China East 5 (Nanjing - Local Region) |
| cn-fuzhou | China East 6 (Fuzhou - Local Region) |
| cn-wuhan-lr | China Central 1 (Wuhan - Local Region) |

**Hong Kong (China) and International**:
| Region ID | Name |
|-----------|------|
| cn-hongkong | China (Hong Kong) |
| ap-southeast-1 | Singapore |
| ap-southeast-3 | Malaysia (Kuala Lumpur) |
| ap-southeast-5 | Indonesia (Jakarta) |
| ap-southeast-6 | Philippines (Manila) |
| ap-southeast-7 | Thailand (Bangkok) |
| ap-northeast-1 | Japan (Tokyo) |
| ap-northeast-2 | South Korea (Seoul) |
| eu-central-1 | Germany (Frankfurt) |
| eu-west-1 | UK (London) |
| us-east-1 | US (Virginia) |
| us-west-1 | US (Silicon Valley) |
| me-east-1 | UAE (Dubai) |
| na-south-1 | Mexico |

**Interactive pagination**:
- First screen (common): cn-beijing (China North 2 - Beijing), cn-hangzhou (China East 1 - Hangzhou), cn-shanghai (China East 2 - Shanghai), cn-shenzhen (China South 1 - Shenzhen)
- After selecting Other: cn-guangzhou, cn-qingdao, cn-chengdu, cn-hongkong
- Continue Other: Show remaining Regions or let user input Region ID directly

This step can be combined with Step 1 (task type) to reduce interaction rounds.

## Error Handling

- When API calls fail, parse error messages and provide actionable suggestions
- If instance creation succeeds but subsequent steps fail, automatically release the created instance to avoid charges
- Common errors:
  - `InvalidAccessKeyId.NotFound` - Invalid AccessKey, check configuration
  - `Forbidden.RAM` - Insufficient RAM permissions, requires AliyunDTSFullAccess policy
  - `InvalidParameter` - Parameter error, check input
  - `UnSupportedTaskType` - Unsupported link combination, suggest changing engine or access method
  - `OperationDenied` - Operation denied, task status may not allow this operation
  - Network timeout - Check network connection

## CLI Call Standards

- All aliyun CLI commands must include `--user-agent AlibabaCloud-Agent-Skills` parameter (except local configuration commands like `aliyun configure`)
- All aliyun CLI API calls must set timeouts: `--read-timeout 30 --connect-timeout 10`
- All aliyun CLI command responses are JSON; parse JSON to extract key information for display

### Input Validation and Injection Prevention

**CRITICAL**: Before constructing any CLI command, ALL user-provided input parameters must be validated and sanitized to prevent command injection.

**Validation rules by parameter type**:

| Parameter | Validation Rule |
|-----------|----------------|
| IP address | Must match IPv4 pattern (`^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$`), each octet 0-255 |
| Port | Integer only, range 1-65535 |
| Instance ID | Alphanumeric, hyphens, and underscores only (`^[a-zA-Z0-9_-]+$`) |
| Database name | Alphanumeric, underscores, hyphens only (`^[a-zA-Z0-9_-]+$`) |
| Table name | Alphanumeric, underscores, hyphens, dots only (`^[a-zA-Z0-9_.\-]+$`) |
| Username | Alphanumeric, underscores, hyphens, dots only (`^[a-zA-Z0-9_.\-]+$`) |
| Region ID | Must match known Region ID list or pattern `^[a-z]{2}-[a-z]+-?\d*$` |
| DtsJobName | Alphanumeric, hyphens, underscores, dots only, max 128 chars |

**Shell injection prevention**:
- **All** user-provided parameter values must be wrapped in single quotes (`'...'`) when passed to CLI commands, not just passwords
- Before quoting, reject any input containing single quotes (`'`), or escape them properly (`'\''`)
- Reject any input containing shell metacharacters (`` ; | & $ ` ( ) { } \n ``) for parameters where they are never valid (IP, port, instance ID, username, database name)
- DbList JSON must be validated as syntactically correct JSON before passing to `--DbList`
- If validation fails, display a clear error message and ask the user to re-enter the value; never pass unvalidated input to the shell

## Notes

- **Never display passwords, certificates, keys, or other sensitive information in any output**; show as `******` in confirmation summaries
- Releasing a task is an irreversible operation; always require double confirmation
- Creating tasks incurs charges (pay-as-you-go); remind users
- If the ID format is ambiguous, attempt fuzzy search matching via DescribeDtsJobs
- Use the Region from the configuration file by default, unless the user specifies a different Region
- All information gathering must use interactive methods to avoid workflow interruption
- Consolidate related input items into the same interaction round to minimize rounds
