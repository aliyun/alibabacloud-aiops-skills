# Related Commands: alibabacloud-aes-sysom-lingjun-diagnosis

This skill uses the `aliyun` CLI to call SysOM APIs (plus the ECS Cloud Assistant status API) for **lingjun node** diagnosis. All OpenAPI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}` (see the Observability section in `SKILL.md`). Local/system commands (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`) **MUST NOT** carry `--user-agent`.

> **Not part of this skill**: `aliyun sysom install-agent`, `aliyun sysom list-instance-status` and `aliyun sysom uninstall-agent` — node enrollment / Agent installation is unsupported and these commands MUST NOT be called.

---

## Diagnosis Phase

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom initial-sysom --check-only false --source aes-skills` | Initialize SysOM role authorization |
| sysom | `aliyun sysom check-instance-support --instances <node_id> --biz-region <region>` | Check if the lingjun node supports diagnosis |
| sysom | `aliyun sysom invoke-diagnosis --service-name ocd --channel eflo --params '<JSON>'` | Invoke intelligent diagnosis (channel is always `eflo` for lingjun; params keys use snake_case, must include `type: "ocd"` and `product: "LINGJUN"`) |
| sysom | `aliyun sysom get-diagnosis-result --task-id <task_id>` | Get diagnosis result |
| ecs | `aliyun ecs describe-cloud-assistant-status --biz-region-id <region> --instance-id <node_id>` | Check Cloud Assistant online status (pass the lingjun node ID) |

## Alert Phase

| Product | CLI Command | Description |
|---------|------------|-------------|
| sysom | `aliyun sysom list-alert-items` | Get available alert items list |

## Alert Strategy Creation (SDK Call, NOT supported by CLI)

> CLI does not support the `destinations` parameter — alert strategy creation must use the SDK script.

| SDK Script | Description |
|-----------|-------------|
| `.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py --name <name> --items <items> --clusters <clusters> --destinations <ids>` | Create alert strategy (supports destinations to associate alert destinations); requires `SKILL_SESSION_ID=<session-id>` in the environment |

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

No cleanup command is needed — diagnosis is read-only. Alert destinations and strategies created by this skill can be removed from the SysOM console.

## Fixed Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `--channel` | `eflo` | Diagnosis channel (fixed value for lingjun nodes) |
| `--service-name` | `ocd` | Diagnosis type (intelligent diagnosis) |
| `--user-agent` | `AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}` | Must be appended to all OpenAPI commands; `{session-id}` is generated once per session |
| `SKILL_SESSION_ID` | `<session-id>` | Environment variable that propagates the same `{session-id}` to the Python SDK scripts |
