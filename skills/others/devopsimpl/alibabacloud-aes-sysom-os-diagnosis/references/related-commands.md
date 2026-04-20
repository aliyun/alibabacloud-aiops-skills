# Related Commands: alibabacloud-aes-sysom-os-diagnosis

This skill uses the `aliyun` CLI to call SysOM and ECS APIs. All commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills`.

---

## Diagnosis Phase

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom initial-sysom --check-only false --source aes-skills` | Initialize SysOM role authorization |
| sysom | `aliyun sysom check-instance-support --instances <id> --biz-region <region>` | Check if instance supports diagnosis |
| sysom | `aliyun sysom invoke-diagnosis --service-name ocd --channel ecs --params '<JSON>'` | Invoke intelligent diagnosis (params keys use snake_case, must include `type: "ocd"`) |
| sysom | `aliyun sysom get-diagnosis-result --task-id <task_id>` | Get diagnosis result |
| ecs | `aliyun ecs describe-cloud-assistant-status --biz-region-id <region> --instance-id <id>` | Check Cloud Assistant online status |

## Enrollment Phase

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom install-agent --instances instance=<id> region=<region> --install-type InstallAndUpgrade --agent-id <id> --agent-version <ver>` | Enroll instance |
| sysom | `aliyun sysom install-agent-for-cluster --cluster-id <id> --agent-id <id> --agent-version <ver> --config-id <id>` | Enroll ACK cluster |
| sysom | `aliyun sysom list-instance-status --instance <id> --biz-region <region>` | Query instance enrollment status |
| sysom | `aliyun sysom list-clusters` | Get full cluster list (do not pass cluster-id; match target from response by cluster_id) |

## Alert Phase

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom list-alert-items` | Get available alert items list |

## Alert Strategy Creation (SDK Call, NOT supported by CLI)

> CLI does not support the `destinations` parameter — alert strategy creation must use the SDK script.

| SDK Script | Description |
|-----------|-------------|
| `.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py --name <name> --items <items> --clusters <clusters> --destinations <ids>` | Create alert strategy (supports destinations to associate alert destinations) |

## Alert Destination (SDK Call, NOT supported by CLI)

> The following APIs are called via Python SDK (`alibabacloud_sysom20231230`), NOT supported by `aliyun` CLI.

| SDK Method | Description |
|-----------|-------------|
| `client.create_alert_destination(request)` | Create alert destination (DingTalk bot Webhook) |
| `client.update_alert_destination(request)` | Update alert destination |
| `client.delete_alert_destination(request)` | Delete alert destination |
| `client.get_alert_destination(request)` | Get alert destination details |
| `client.list_alert_destinations(request)` | List alert destinations (filterable by name) |

## Cleanup

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom uninstall-agent --instances instance=<id> region=<region> --agent-id <id> --agent-version <ver>` | Uninstall Agent |

## Fixed Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--agent-id` | `74a86327-3170-412c-8e67-da3389ec56a9` | Agent ID |
| `--agent-version` | `3.12.0-1` | Agent version |
| `--install-type` | `InstallAndUpgrade` | Installation type (default) |
| `--config-id` | `8gj86wrt7-3170-412c-8e67-da3389ecg6a9` | Cluster component config ID |
| `--channel` | `ecs` | Diagnosis channel (fixed) |
| `--service-name` | `ocd` | Diagnosis type (intelligent diagnosis) |
| `--user-agent` | `AlibabaCloud-Agent-Skills` | Must be appended to all commands |
