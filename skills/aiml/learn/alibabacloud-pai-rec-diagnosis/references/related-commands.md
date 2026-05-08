# Related CLI Commands

This document provides a comprehensive reference of all Alibaba Cloud CLI commands used in the PAI-Rec Engine Diagnosis and Configuration Validation skill.

## PAI-EAS Commands

### describe-service

Queries the details about a PAI-EAS service.

**Usage:**
```bash
aliyun eas describe-service \
  --cluster-id <cluster-id> \
  --service-name <service-name>
```

**Parameters:**
- `--cluster-id` (required): The ID of the region where the service is deployed
- `--service-name` (required): The service name
- `--region` (optional): Override region ID

**Response Fields:**
- `ServiceId`: Service identifier
- `ServiceName`: Name of the service
- `Resource`: EAS service resource ID (e.g., `eas-r-xxxxxxxxxxxx`)
- `ServiceConfig`: Service configuration including environment variables
- `Status`: Service status (Running/Stopped/etc.)
- `CurrentVersion`: Current deployed version
- `Metadata`: Additional service metadata

**Example:**
```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall
```

**Common Use Cases:**
- Get EAS service resource ID
- Extract environment variables (INSTANCE_ID, CONFIG_NAME, REGION, PAIREC_ENVIRONMENT)
- Check service status before diagnosis
- Verify service configuration

---

### describe-service-log

Queries the information about the logs of a PAI-EAS service.

**Usage:**
```bash
aliyun eas describe-service-log \
  --cluster-id <cluster-id> \
  --service-name <service-name> \
  [--keyword <keyword>] \
  [--start-time <utc-time>] \
  [--end-time <utc-time>] \
  [--page-num <number>] \
  [--page-size <number>]
```

**Parameters:**
- `--cluster-id` (required): The ID of the region where the service is deployed
- `--service-name` (required): The service name
- `--keyword` (optional, **strongly recommended for request-level diagnosis**): Keyword to filter logs, e.g., `request_id`. See pitfall note below.
- `--start-time` (optional): Beginning of time range. Format MUST be `yyyy-MM-dd HH:mm:ss` in UTC (space separator, no `T` / no `Z`). ISO-8601 like `2025-04-28T00:00:00Z` will be rejected with `InvalidParameter`.
- `--end-time` (optional): End of time range (same format as `--start-time`).
- `--page-num` (optional): Page number (default: 1)
- `--page-size` (optional): Entries per page (default: 500)
- `--container-name` (optional): Container name
- `--instance-name` (optional): Instance name
- `--ip` (optional): Instance IP address
- `--previous` (optional): Query logs before last restart

**[CRITICAL] Pitfall — keyword + time range returns no business logs:**
When `--keyword` is combined with `--start-time` / `--end-time`, PAI-Rec application logs (`controller.go`, `feed.go`, `recall.go`, `rank_service.go`, etc.) are silently dropped by the CLI, even if the time window covers the real log timestamp. Only `/bin/sh` wrapper heartbeats and `502 Bad Gateway` noise remain. For request-level diagnosis, always use `--keyword` **without** `--start-time` / `--end-time`.

**Response Fields:**
- `Logs`: Array of log entries
- `PageNum`: Current page number
- `TotalCount`: Total log count
- `TotalPageNum`: Total pages

**Example — recommended pattern for request-level diagnosis (keyword only):**
```bash
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --keyword "941b4e14-d1c5-489f-a184-b2b17f8b4fdb" \
  --page-size 500
```

**Example — broad time-window scan without keyword (infrastructure logs only):**
```bash
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --start-time "2025-04-28 08:00:00" \
  --end-time   "2025-04-28 09:00:00" \
  --page-size 500
```

**Common Use Cases:**
- Trace request processing by `request_id` (use keyword-only pattern)
- Debug error messages
- Monitor service behavior
- Analyze performance issues

**Query Strategy Recommendations:**
- Request-level diagnosis: `--keyword <request_id>` only, no time range
- Service-level scan: omit `--keyword`, use time window in `yyyy-MM-dd HH:mm:ss` UTC
- Log retention: EAS logs have a limited retention window; diagnose issues promptly

---

## PAI-RecService Commands

### list-engine-configs

Lists engine configuration versions for a PAI-Rec instance.

**Usage:**
```bash
aliyun pairecservice list-engine-configs \
  --instance-id <instance-id> \
  [--environment <Prod|Pre>] \
  [--name <config-name>] \
  [--status <status>] \
  [--version <version>] \
  [--page-number <number>] \
  [--page-size <number>]
```

**Parameters:**
- `--instance-id` (required): The PAI-Rec instance ID
- `--environment` (optional): Environment filter (`Prod` or `Pre`)
- `--name` (optional): Configuration name filter
- `--status` (optional): Status filter (e.g., `Released`, `Draft`, `Archived`)
- `--version` (optional): Version filter
- `--page-number` (optional): Page number for pagination
- `--page-size` (optional): Number of results per page

**Response Fields:**
- `EngineConfigs`: Array of engine configurations
  - `EngineConfigId`: Configuration version ID
  - `Name`: Configuration name
  - `Version`: Version number
  - `Status`: Configuration status
  - `Environment`: Target environment
  - `GmtCreateTime`: Creation timestamp
  - `GmtModifiedTime`: Last modification timestamp

**Example:**
```bash
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod \
  --status Released \
  --name my_engine_config
```

**Common Use Cases:**
- Find released configurations
- List all versions of a configuration
- Filter by environment (Prod/Pre)
- Select configuration for validation

**Environment Mapping:**
- Service environment `product` → CLI parameter `Prod`
- Service environment `prepub` → CLI parameter `Pre`

---

### get-engine-config

Retrieves detailed information about a specific engine configuration.

**Usage:**
```bash
aliyun pairecservice get-engine-config \
  --instance-id <instance-id> \
  --engine-config-id <config-id>
```

**Parameters:**
- `--instance-id` (required): The PAI-Rec instance ID
- `--engine-config-id` (required): The specific configuration version ID

**Response Fields:**
- `EngineConfig`: Configuration object
  - `EngineConfigId`: Configuration ID
  - `Name`: Configuration name
  - `Version`: Version number
  - `Status`: Current status
  - `Environment`: Target environment
  - `ConfigValue`: The actual configuration content (JSON/YAML)
  - `Description`: Configuration description
  - `GmtCreateTime`: Creation time
  - `GmtModifiedTime`: Last modified time

**Example:**
```bash
aliyun pairecservice get-engine-config \
  --instance-id pairec-cn-xxxxx \
  --engine-config-id config-12345
```

**Common Use Cases:**
- Retrieve configuration for validation
- Export configuration for backup
- Compare different versions
- Debug configuration issues

**ConfigValue Structure:**
The `ConfigValue` field contains the engine configuration in JSON or YAML format, typically including:
- Recall configurations
- Ranking configurations
- Filter rules
- Scene definitions
- Feature mappings
- Model endpoints

---

## Utility Commands

### aliyun configure list

Checks current credential configuration status.

**Usage:**
```bash
aliyun configure list
```

**Output:**
Lists all configured profiles with their authentication method (AK, STS, OAuth).

**Common Use Cases:**
- Verify credentials before running commands
- Check which profile is active
- Troubleshoot authentication issues

---

### aliyun configure ai-mode enable

Enables AI-mode for agent skill execution.

**Usage:**
```bash
aliyun configure ai-mode enable
```

**Common Use Cases:**
- Required before executing skill commands
- Must be enabled at skill start

---

### aliyun configure ai-mode set-user-agent

Sets the user-agent for AI-mode.

**Usage:**
```bash
aliyun configure ai-mode set-user-agent \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis"
```

**Common Use Cases:**
- Track skill invocations
- Required after enabling AI-mode

---

### aliyun configure ai-mode disable

Disables AI-mode after skill execution completes.

**Usage:**
```bash
aliyun configure ai-mode disable
```

**Common Use Cases:**
- Must be called at ALL exit points
- Cleanup after skill execution

---

### aliyun plugin update

Updates all installed CLI plugins to latest versions.

**Usage:**
```bash
aliyun plugin update
```

**Common Use Cases:**
- Ensure latest plugin versions before execution
- Required as part of skill prerequisites

---

## Command Chaining Examples

### Full Diagnosis Flow

```bash
# 1. Enable AI-mode
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis"

# 2. Get service info
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall

# 3. Query logs by request_id (keyword-only pattern — do NOT add --start-time / --end-time)
aliyun eas describe-service-log \
  --cluster-id cn-hangzhou \
  --service-name embedding_recall \
  --keyword "941b4e14-d1c5-489f-a184-b2b17f8b4fdb" \
  --page-size 500

# 4. List engine configs
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod \
  --status Released

# 5. Get specific config
aliyun pairecservice get-engine-config \
  --instance-id pairec-cn-xxxxx \
  --engine-config-id config-12345

# 6. Disable AI-mode
aliyun configure ai-mode disable
```

### Configuration Validation Flow

```bash
# 1. Enable AI-mode
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-pai-rec-diagnosis"

# 2. List available versions
aliyun pairecservice list-engine-configs \
  --instance-id pairec-cn-xxxxx \
  --environment Prod \
  --name my_config

# 3. Get specific version for validation
aliyun pairecservice get-engine-config \
  --instance-id pairec-cn-xxxxx \
  --engine-config-id config-67890

# 4. Disable AI-mode
aliyun configure ai-mode disable
```

## Error Handling

### Common Error Codes

| Error Code | Description | Solution |
|------------|-------------|----------|
| `Forbidden.RAM` | Insufficient RAM permissions | Check RAM policies |
| `InvalidParameter` | Invalid parameter value | Verify parameter format |
| `ServiceNotFound` | Service does not exist | Check service name and cluster ID |
| `ConfigNotFound` | Configuration not found | Verify instance ID and config ID |

### Debugging Commands

Check command execution details:
```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name test \
  --log-level DEBUG
```

Dry-run mode (no actual execution):
```bash
aliyun eas describe-service \
  --cluster-id cn-hangzhou \
  --service-name test \
  --cli-dry-run
```

## Related Documentation

- [EAS API Reference](https://www.alibabacloud.com/help/eas/developer-reference/)
- [PAI-RecService API Reference](https://www.alibabacloud.com/help/pai/developer-reference/)
- [Aliyun CLI User Guide](https://www.alibabacloud.com/help/cli/)
