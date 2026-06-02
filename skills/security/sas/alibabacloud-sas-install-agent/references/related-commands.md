# CLI Command Reference

Complete list of all CLI commands used by this skill. All commands use plugin mode (kebab-case) and MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent`.

## SAS (Security Center) Commands

| Command | Type | Purpose |
|---------|------|---------|
| `aliyun sas describe-cloud-center-instances` | Read | Query server client status by instance ID/IP |
| `aliyun sas refresh-assets` | Read | Sync latest asset data |
| `aliyun sas describe-install-codes` | Read | Get existing install code list |
| `aliyun sas add-install-code` | Write | Generate new install code |
| `aliyun sas create-or-update-asset-group` | Write | Create or update asset group |
| `aliyun sas get-auth-summary` | Read | Get authorization quota and usage per version |
| `aliyun sas describe-version-config` | Read | Get version, feature modules, expiration |
| `aliyun sas get-serverless-auth-summary` | Read | Get pay-as-you-go serverless status |
| `aliyun sas modify-post-pay-module-switch` | Write | Toggle pay-as-you-go module switches |
| `aliyun sas bind-auth-to-machine` | Write | Bind/unbind authorization version |
| `aliyun sas update-post-paid-bind-rel` | Write | Change pay-as-you-go version binding |
| `aliyun sas describe-property-sca-detail` | Read | Query software info on servers |
| `aliyun sas add-uninstall-clients-by-uuids` | Write | Uninstall agent from specified servers |
| `aliyun sas modify-push-all-task` | Write | Dispatch security check tasks to servers |
| `aliyun sas modify-start-vul-scan` | Write | Trigger one-click vulnerability scan |
| `aliyun sas describe-grouped-vul` | Read | Query grouped vulnerability statistics |
| `aliyun sas exec-strategy` | Write | Execute baseline check strategy |
| `aliyun sas describe-strategy` | Read | Query baseline check strategy list |
| `aliyun sas list-check-item-warning-summary` | Read | Get baseline check risk statistics |
| `aliyun sas describe-susp-events` | Read | Query security alert events |
| `aliyun sas generate-once-task` | Write | Trigger full asset fingerprint collection |
| `aliyun sas create-asset-selection-config` | Write | Create virus scan asset selection |
| `aliyun sas add-asset-selection-criteria` | Write | Add assets to selection config |
| `aliyun sas update-selection-key-by-type` | Write | Associate selection to virus scan |
| `aliyun sas create-virus-scan-once-task` | Write | Create one-time virus scan task |
| `aliyun sas get-virus-scan-latest-task-statistic` | Read | Query latest virus scan task stats |
| `aliyun sas list-virus-scan-machine` | Read | Query machines involved in virus scan |
| `aliyun sas list-virus-scan-machine-event` | Read | Query virus events on a specific machine |
| `aliyun sas describe-once-task` | Read | Poll vulnerability scan task progress |

## ECS (Elastic Compute Service) Commands

| Command | Type | Purpose |
|---------|------|---------|
| `aliyun ecs describe-instances` | Read | Query ECS instance info and running status |
| `aliyun ecs describe-cloud-assistant-status` | Read | Check if cloud assistant is online |
| `aliyun ecs run-command` | Write | Remote install command execution |
| `aliyun ecs invoke-command` | Write | Execute existing command on instances |
| `aliyun ecs describe-invocation-results` | Read | Query command execution results |

## Execution Rules

- **Read** commands execute directly with brief intent statement
- **Write** commands require: display operation details -> user confirmation -> execute -> report result
- All commands MUST include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-sas-install-agent`
- Limit to 8 CLI tool calls per scenario (proxy scenarios may extend moderately)
