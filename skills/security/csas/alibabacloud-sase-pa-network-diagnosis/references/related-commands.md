# Related Commands: SASE PA Network Diagnosis

## API List

> **Invocation rule**: Use Aliyun CLI plugin mode with lowercase kebab-case actions and parameters. Do not use PascalCase API names or `--force` generic mode in CLI examples.

| Product | API Name | Method | Description | CLI Invocation |
|---------|----------|--------|-------------|----------------|
| csas | `ListUserDevices` | GET | Query user device list | `aliyun csas list-user-devices --username ... --hostname ...` |
| csas | `CreatePADiagnosisTask` | POST | Create Private Access diagnosis task | `aliyun csas create-pa-diagnosis-task --diagnose-type ...` |
| csas | `GetPADiagnosisTask` | GET | Query Private Access diagnosis task details | `aliyun csas get-pa-diagnosis-task --diagnose-id ...` |

## CLI Plugin Mode

Use plugin mode actions and parameters:

```bash
aliyun <product> <kebab-case-action> --<kebab-case-param> <value> ...
```

**Key notes**:
- Use `create-pa-diagnosis-task`, `get-pa-diagnosis-task`, and `list-user-devices`
- Do not add `--force` or `--method`; plugin mode handles the API method
- Set the skill user agent once via `aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sase-pa-network-diagnosis"` before CLI calls
- Use `--cli-dry-run` to preview the request without sending it

## Pre-check and Lifecycle Commands

| Purpose | CLI Command |
|---------|-------------|
| Verify CLI version | `aliyun version` |
| Enable automatic plugin installation | `aliyun configure set --auto-plugin-install true` |
| Update installed plugins | `aliyun plugin update` |
| Verify credential profile | `aliyun configure list` |
| Enable AI-mode | `aliyun configure ai-mode enable` |
| Set skill user agent | `aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-sase-pa-network-diagnosis"` |
| Disable AI-mode | `aliyun configure ai-mode disable` |

## list-user-devices Parameters (Query Device DevTag)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--current-page` | int | Yes | Page number |
| `--page-size` | int | Yes | Items per page |
| `--username` | String | No | Filter by username |
| `--hostname` | String | No | Filter by hostname |
| `--device-types` | list | No | Device type filter: `Windows` / `macOS` / `Linux` etc. |
| `--app-statuses` | list | No | App status filter: `Online` / `Offline` etc. |

The `DeviceTag` field in the response is the `DevTag` parameter required for FullLink diagnosis.

## create-pa-diagnosis-task Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--diagnose-type` | String | Yes | Diagnosis type: `FullLink` / `Application` |
| `--host` | String | Yes | Target address (IP or domain) |
| `--port` | String | Yes | Target port |
| `--protocol` | String | Yes | Protocol: `TCP` / `UDP` |
| `--pop-mode` | String | Yes | POP selection mode: `AutoSelect` / `ManualSelect` |
| `--username` | String | No | Username (used for FullLink diagnosis) |
| `--dev-tag` | String | No | Device ID (used for FullLink diagnosis) |
| `--user-group-id` | String | No | User group ID (used for Application diagnosis) |
| `--pop-id` | String | No | POP entry point ID (required when ManualSelect) |
| `--udp-extra-configs` | object | No | UDP extra config: `RequestContent=... ExpectedResponse=...` |

## get-pa-diagnosis-task Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--diagnose-id` | String | Yes | Diagnosis task ID, e.g. `diag-58d0750e8786919a` |

## Task Status Values

| Status | Description |
|--------|-------------|
| `Running` | Task is executing |
| `Finished` | Task completed |
| `Failed` | Task execution failed |

## Common `--cli-query` Expressions

| Purpose | JMESPath Expression |
|---------|---------------------|
| Extract DiagnoseId | `DiagnosisTask.DiagnoseId` |
| Check task status | `DiagnosisTask.Status` |
| Check diagnosis success | `DiagnosisTask.Result.Success` |
| Check error message | `DiagnosisTask.Result.ErrorMessage` |
| View network nodes | `DiagnosisTask.Result.NetworkLinkInfo.Nodes` |
| View link info | `DiagnosisTask.Result.NetworkLinkInfo.Links` |
| View DNS info | `DiagnosisTask.Result.NetworkLinkInfo.Dns` |
| View zero-trust policy | `DiagnosisTask.Result.PolicyInfo.ZeroTrustPolicyInfo` |
