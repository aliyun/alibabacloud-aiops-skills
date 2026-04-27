# OOS Related Commands Reference

CLI command reference for ECS Extension Installation skill.

## Command Format Standards

- For OOS commands, use plugin mode (lowercase-hyphenated) operation names: `list-templates`, `get-template`, `start-execution`, `list-executions`
- All OOS plugin flags use kebab-case: `--biz-region-id`, `--template-type`, `--share-type`, `--max-results`, `--template-name`, `--execution-id`, etc.
- Always include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension`
- OOS command format: `aliyun oos <action> --biz-region-id <region> [parameters]`

> **[RECOMMENDED] Flag Verification:** Run `aliyun oos <action> --help` to confirm exact flag names for the installed plugin version.

---

## list-templates

Query available OOS templates (extension packages).

### Command

```bash
aliyun oos list-templates \
  --biz-region-id <region-id> \
  --template-type Package \
  --share-type Public \
  --max-results <max-results> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

### Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--biz-region-id` | Yes | String | Region ID, e.g., `cn-hangzhou` |
| `--template-type` | No | String | Template type, `Package` for extension packages |
| `--share-type` | No | String | Share type, `Public` for public templates |
| `--max-results` | No | Integer | Maximum number of results, range 1-100 |
| `--next-token` | No | String | Pagination token |
| `--user-agent` | Yes | String | Fixed value `AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension` |

### Output Example

```json
{
  "Templates": [
    {
      "TemplateId": "t-xxxxxxxxxxxxxxxx",
      "TemplateName": "ACS-Extension-BaoTaPanelFree-One-Click-1853370294850618",
      "TemplateVersion": "v1",
      "Description": "{\"categories\":[\"application\"],\"en\":\"BaoTa Panel free edition one-click installation\",\"zh-cn\":\"BaoTa Panel free edition one-click installation\",\"name-en\":\"BaoTaPanelFree-One-Click\",\"name-zh-cn\":\"BaoTaPanelFree-One-Click\",\"image\":\"https://oos-public-template.oss-cn-beijing.aliyuncs.com/BaoTaPanelFree/icon.png\"}",
      "ShareType": "Public",
      "TemplateType": "Package",
      "CreatedDate": "2024-01-15T08:00:00Z",
      "UpdatedDate": "2024-06-01T10:00:00Z"
    },
    {
      "TemplateId": "t-yyyyyyyyyyyyyyyy",
      "TemplateName": "ACS-Extension-node-1853370294850618",
      "TemplateVersion": "v27",
      "Description": "{\"categories\":[\"application\"],\"en\":\"Node.js environment one-click installation\",\"zh-cn\":\"Node.js environment one-click installation\",\"name-en\":\"Node.js\",\"name-zh-cn\":\"Node.js\",\"image\":\"https://oos-public-template.oss-cn-beijing.aliyuncs.com/Nodejs/icon.png\"}",
      "ShareType": "Public",
      "TemplateType": "Package",
      "CreatedDate": "2024-03-10T06:00:00Z",
      "UpdatedDate": "2024-07-15T12:00:00Z"
    }
  ],
  "MaxResults": 100,
  "TotalCount": 2,
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Output Field Description

| Field | Description |
|-------|-------------|
| `Templates` | Array of template information |
| `TemplateId` | Unique template ID |
| `TemplateName` | Template name (used as extension package name) |
| `TemplateVersion` | Template version |
| `Description` | Template description (JSON string, see parsing notes below) |
| `ShareType` | Share type: `Public` or `Private` |
| `TemplateType` | Template type: `Package` or `Automation` |
| `TotalCount` | Total number of templates |
| `RequestId` | Request ID (for troubleshooting) |

> **Description Field Parsing:** The `Description` field is a JSON string containing localized metadata. Parse it to extract:
> - `name-zh-cn`: Chinese display name (preferred for display)
> - `name-en`: English display name
> - `zh-cn`: Chinese description
> - `en`: English description
> - `categories`: Category tags array
> - `doc-zh-cn`: Chinese documentation link
> - `doc-en`: English documentation link
> - `image`: Icon URL

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `unknown endpoint for oos/<region>` | Automatic endpoint resolution failed (network issue or location service unreachable) | Verify `--biz-region-id` value is correct; if still fails, check network connectivity |
| `unknown flag: --RegionId` | Using PascalCase flag instead of kebab-case | Use `--biz-region-id` instead of `--RegionId` |
| `Forbidden.RAM` | Insufficient permissions | Ensure required RAM permissions are granted (see SKILL.md Required Permissions section) |

---

## get-template

Get detailed information of a specific OOS template.

### Command

**Recommended: redirect output to a temporary file** (the `Content` field is usually very large and will be truncated in terminal):

```bash
aliyun oos get-template \
  --biz-region-id <region-id> \
  --template-name <template-name> \
  [--template-version <version>] \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension > /tmp/oos-template.json
```

Then extract parameters using `jq`:

```bash
# Extract installation parameters
jq -r '(.Content | fromjson | .Parameters)' /tmp/oos-template.json

# Extract template description
jq -r '.Description' /tmp/oos-template.json
```

> **[IMPORTANT] Output Truncation Warning**: `get-template` returns a `Content` field that contains full installation scripts and can be extremely large. Always redirect to a file first, then parse with `jq` or file read tools. Do **not** rely on terminal output directly.

### Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--biz-region-id` | Yes | String | Region ID, e.g., `cn-hangzhou` |
| `--template-name` | Yes | String | Template name |
| `--template-version` | No | String | Template version, defaults to latest if not specified |
| `--user-agent` | Yes | String | Fixed value `AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension` |

### Output Example

```json
{
  "Template": {
    "TemplateId": "t-xxxxxxxxxxxxxxxx",
    "TemplateName": "ACS-Extension-node-1853370294850618",
    "TemplateVersion": "v27",
    "Description": "{\"categories\":[\"application\"],\"en\":\"Node.js environment one-click installation\",\"zh-cn\":\"Node.js environment one-click installation\",\"name-en\":\"Node.js\",\"name-zh-cn\":\"Node.js\",\"image\":\"https://oos-public-template.oss-cn-beijing.aliyuncs.com/Nodejs/icon.png\"}",
    "Content": "{\"FormatVersion\":\"OOS-2019-06-01\",\"Description\":\"Node.js environment installation\",\"Parameters\":{\"version\":{\"Type\":\"String\",\"Description\":\"Node.js version number\",\"Default\":\"v22.13.1\"}},\"Tasks\":[...]}",
    "CreatedDate": "2024-03-10T06:00:00Z",
    "UpdatedDate": "2024-07-15T12:00:00Z"
  },
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Content Field Parsing

The `Content` field is a JSON string containing the complete template definition. Key fields:

```json
{
  "FormatVersion": "OOS-2019-06-01",
  "Description": "Template description",
  "Parameters": {
    "version": {
      "Type": "String",
      "Description": "Parameter description",
      "Default": "default value",
      "AllowedValues": ["v1", "v2"]
    }
  },
  "Tasks": [...]
}
```

| Field | Description |
|-------|-------------|
| `Parameters` | Template parameters, defines installation options |
| `Parameters.{name}.Type` | Parameter type: `String`, `Integer`, `Boolean`, etc. |
| `Parameters.{name}.Description` | Parameter description |
| `Parameters.{name}.Default` | Default value |
| `Parameters.{name}.AllowedValues` | List of allowed values |
| `Tasks` | Execution task definitions |

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `TemplateNotFound` | Template name does not exist | Check if the template name is correct, use `list-templates` to query |
| `MissingTemplateName` | Missing `--template-name` parameter | Add `--template-name` parameter |

---

## start-execution

Start an OOS execution to install the extension.

### Command

```bash
aliyun oos start-execution \
  --biz-region-id <region-id> \
  --template-name "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL" \
  --mode "Automatic" \
  --tags "{}" \
  --parameters '<json-parameters>' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

### Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--biz-region-id` | Yes | String | Region ID, must match the target instance region |
| `--template-name` | Yes | String | Fixed value `ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL` |
| `--mode` | Yes | String | Execution mode, `Automatic` for automatic execution |
| `--tags` | No | String | Tags, JSON format string, e.g., `"{}"` |
| `--parameters` | Yes | String | Execution parameters, JSON format string |
| `--user-agent` | Yes | String | Fixed value `AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension` |

### Parameters Field Structure

```json
{
  "regionId": "cn-hangzhou",
  "OOSAssumeRole": "",
  "targets": {
    "ResourceIds": ["i-bp12z30vh0wadpyv3jo3"],
    "RegionId": "cn-hangzhou",
    "Type": "ResourceIds"
  },
  "rateControl": {
    "Mode": "Concurrency",
    "Concurrency": 1,
    "MaxErrors": 0
  },
  "action": "install",
  "packageName": "ACS-Extension-node-1853370294850618",
  "packageVersion": "v27",
  "parameters": {
    "version": "v22.13.1"
  }
}
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `regionId` | Yes | Region ID, must be consistent with `--biz-region-id` |
| `OOSAssumeRole` | No | RAM role assumed by OOS, leave empty to use default |
| `targets.ResourceIds` | Yes | Array of target instance IDs |
| `targets.RegionId` | Yes | Region ID of target instances |
| `targets.Type` | Yes | Fixed value `ResourceIds` |
| `rateControl.Mode` | Yes | Rate control mode, `Concurrency` or `Batch` |
| `rateControl.Concurrency` | Yes | Number of concurrent executions |
| `rateControl.MaxErrors` | Yes | Maximum number of errors allowed |
| `action` | Yes | Fixed value `install` |
| `packageName` | Yes | Extension package name |
| `packageVersion` | No | Extension package version |
| `parameters` | No | Extension-specific parameters (JSON object) |

### Output Example

```json
{
  "Execution": {
    "ExecutionId": "exec-xxxxxxxxxxxxxxxx",
    "TemplateName": "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL",
    "Status": "Running",
    "CreateDate": "2024-08-01T10:00:00Z",
    "UpdateDate": "2024-08-01T10:00:00Z",
    "Parameters": {...}
  },
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Output Field Description

| Field | Description |
|-------|-------------|
| `ExecutionId` | Unique execution ID, used to query execution status |
| `TemplateName` | Template name |
| `Status` | Execution status: `Running`, `Success`, `Failed`, `Cancelled` |
| `CreateDate` | Execution creation time |
| `UpdateDate` | Execution update time |
| `Parameters` | Execution parameters |

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `InvalidParameter` | Parameter format error | Check if `--parameters` is a valid JSON string |
| `TemplateNotFound` | Template does not exist | Check if `packageName` is correct |
| `EntityNotExists.Instance` | Instance does not exist | Check if `InstanceId` is correct |
| `InvalidInstance.NotRunning` | Instance is not in running state | Start the instance first |
| `Forbidden.RAM` | Insufficient permissions | Ensure required RAM permissions are granted (see SKILL.md Required Permissions section) |
| `RateLimit` | API rate limit exceeded | Wait a moment and retry |

---

## list-executions (Auxiliary Command)

Query OOS execution status and results.

### Command

```bash
aliyun oos list-executions \
  --biz-region-id <region-id> \
  --execution-id <execution-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

### Parameters

| Parameter | Required | Type | Description |
|-----------|----------|------|-------------|
| `--biz-region-id` | Yes | String | Region ID |
| `--execution-id` | Yes | String | Execution ID returned by `start-execution` |
| `--user-agent` | Yes | String | Fixed value `AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension` |

### Output Example

```json
{
  "Executions": [
    {
      "ExecutionId": "exec-xxxxxxxxxxxxxxxx",
      "TemplateName": "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL",
      "Status": "Success",
      "StatusReason": "Execution completed successfully",
      "CreateDate": "2024-08-01T10:00:00Z",
      "UpdateDate": "2024-08-01T10:05:00Z",
      "Outputs": {
        "result": "Installation completed"
      },
      "Tasks": [
        {
          "TaskName": "installPackage",
          "Status": "Success",
          "StatusReason": "Task completed"
        }
      ]
    }
  ],
  "TotalCount": 1,
  "RequestId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

### Execution Status Description

| Status | Description |
|--------|-------------|
| `Running` | Execution in progress |
| `Success` | Execution successful |
| `Failed` | Execution failed |
| `Cancelled` | Execution cancelled |
| `Pending` | Waiting to execute |

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ExecutionNotFound` | Execution ID does not exist | Check if the execution ID is correct |

---

## JSON Parameter Escaping Notes

When passing JSON parameters via the command line, pay attention to escaping:

### Bash

```bash
# Use single quotes to wrap the entire JSON to avoid shell escaping issues
aliyun oos start-execution \
  --biz-region-id cn-hangzhou \
  --template-name "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL" \
  --parameters '{"regionId":"cn-hangzhou","targets":{"ResourceIds":["i-xxx"],"RegionId":"cn-hangzhou","Type":"ResourceIds"},"action":"install","packageName":"ACS-Extension-node-1853370294850618","parameters":{"version":"v22.13.1"}}'
```

### Complex Parameters

For complex parameters, it is recommended to write them to a file first:

```bash
# Write parameters to file
cat > /tmp/oos-params.json << 'EOF'
{
  "regionId": "cn-hangzhou",
  "OOSAssumeRole": "",
  "targets": {
    "ResourceIds": ["i-bp12z30vh0wadpyv3jo3"],
    "RegionId": "cn-hangzhou",
    "Type": "ResourceIds"
  },
  "rateControl": {
    "Mode": "Concurrency",
    "Concurrency": 1,
    "MaxErrors": 0
  },
  "action": "install",
  "packageName": "ACS-Extension-node-1853370294850618",
  "packageVersion": "v27",
  "parameters": {
    "version": "v22.13.1"
  }
}
EOF

# Read from file
aliyun oos start-execution \
  --biz-region-id cn-hangzhou \
  --template-name "ACS-ECS-BulkyConfigureOOSPackageWithTemporaryURL" \
  --parameters "$(cat /tmp/oos-params.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-install-extension
```

## Error Handling Best Practices

1. **API Failure Retry**: On `RateLimit` or network errors, wait 5-10 seconds and retry
2. **Permission Error**: Ensure required RAM permissions are granted, then use `ram-permission-diagnose` skill
3. **Parameter Error**: Carefully check JSON format and required fields
4. **Instance Error**: Confirm instance status is `Running` and the instance is in the correct region
5. **Execution Failure**: Use `list-executions` to query detailed error information; check `StatusReason` and `Tasks` fields
