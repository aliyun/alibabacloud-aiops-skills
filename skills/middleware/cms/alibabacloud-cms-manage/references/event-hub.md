# Event Hub Module

> Global conventions (credentials, output format, error codes, command prefix, distributions) — see [../SKILL.md](../SKILL.md).

## Architecture

```
Alert Rule triggers → Event written to SLS LogStore → event-hub queries via SLS GetLogs API
```

| Resource | Naming Format |
|----------|--------------|
| SLS Project | `cms-alert-center-{userId}-{region}` |
| SLS LogStore | `cms-event-store-{workspace}` |
| Workspace | `default-cms-{userId}-{region}` |

The CLI auto-derives Project/LogStore/Region from `--workspace`. Override with `--project` + `--logstore` if needed.

## Command Overview

| Command | Description | Backend |
|---------|-------------|---------|
| `event-hub list` | Query events with time range and filters | SLS GetLogs |
| `event-hub get` | Get single event by ID | SLS GetLogs (id filter) |

## Workflows

### List Recent Events

```bash
# Default: last 15 minutes, newest first
aliyun cms2 event-hub list --workspace default-cms-<userId>-<regionId>

# Filter by severity
aliyun cms2 event-hub list --workspace default-cms-<userId>-<regionId> \
  --query "severity: CRITICAL"

# Custom time range (epoch seconds)
aliyun cms2 event-hub list --workspace default-cms-<userId>-<regionId> \
  --from 1779070321 --to 1779071221

# Paginate
aliyun cms2 event-hub list --workspace default-cms-<userId>-<regionId> \
  --page 2 --size 50
```

### Get Event Details

```bash
# Get by event ID (searches last 30 days)
aliyun cms2 event-hub get --event-id <event-id> \
  --workspace default-cms-<userId>-<regionId>
```

### Common Query Patterns

| Goal | `--query` value |
|------|----------------|
| Critical alerts only | `severity: CRITICAL` |
| Specific alert rule | `subject: "rule-name"` |
| By source type | `sourcetype: ALERT_ALIYUN_ARMS` |
| By status | `status: OCCURRED` |
| Combined filter | `severity: CRITICAL AND status: OCCURRED` |
| By rule name (label) | `alertname: "my-rule"` |

### Manual SLS Project/LogStore

When workspace format is non-standard:

```bash
aliyun cms2 event-hub list \
  --project cms-alert-center-<userId>-<region> \
  --logstore cms-event-store-<workspace> \
  --region <region>
```

## Event Data Model

Events follow CloudEvents spec. Key fields:

| Field | Description |
|-------|-------------|
| `id` | Unique event ID |
| `type` | Event type (e.g. `ALERT`) |
| `subject` | Alert rule name / event title |
| `severity` | `CRITICAL` / `ERROR` / `WARNING` / `INFO` |
| `status` | `OCCURRED` / `PERSISTENT` / `RESOLVED` |
| `time` | ISO 8601 timestamp |
| `timestamp` | Millisecond epoch |
| `source` | `/{userId}/{source_type}/{integration_id}` |
| `sourcetype` | Source category (e.g. `ALERT_ALIYUN_ARMS`) |
| `labels` | JSON string — rule metadata, integration info |
| `annotations` | JSON string — alert message, current value, query SQL |

### Important Labels

| Key | Meaning |
|-----|---------|
| `_cms_rule_name` | Alert rule name |
| `_cms_rule_id` | CMS rule ID |
| `_cms_workspace` | Workspace |
| `_cms_domain` | Domain (apm / rum / infra) |
| `alertname` | Alert name |
| `severity` | Severity (lowercase) |

### Important Annotations

| Key | Meaning |
|-----|---------|
| `message` | Human-readable alert message |
| `value` / `current_value` | Trigger value |
| `_cms_rule_display_statement` | Rule condition description |
| `query_sql` | Monitoring query |

## Key Constraints

### Permissions

Requires SLS read access on `cms-alert-center-*` projects:
- `log:GetLogStoreLogs`
- `log:GetIndex`

### Time Defaults

- `list`: last **15 minutes** if `--from`/`--to` not specified
- `get`: searches last **30 days** for the event ID

### Input Validation (`list`)

The CLI rejects out-of-range pagination/time values up-front so you never silently hit the SLS API with invalid input:

- `--page` and `--size` must be `>= 1`
- `--from` and `--to` must be `>= 0` (epoch seconds)
- When both `--from` and `--to` are set, `--from <= --to` must hold

### Cross-Account

AK/SK must belong to the same account that owns the SLS project. If the project belongs to a different account, you'll get `"The project does not belong to you"`.

## Related Module

Alert rules that generate these events are managed by the **alerting** module — see [alerting.md](alerting.md).
