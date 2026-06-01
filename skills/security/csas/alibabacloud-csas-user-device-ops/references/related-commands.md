# Related CLI Commands

All Aliyun CLI commands used by this skill. Product: `csas` (SASE / Secure Access Service Edge).

## Query Commands (Read-Only)

| Command | Description | Key Parameters |
|---------|-------------|----------------|
| `aliyun csas list-user-devices` | Query devices with full filter support | `--department`, `--device-types`, `--device-statuses`, `--dlp-statuses`, `--pa-statuses`, etc. |
| `aliyun csas list-users` | Query user accounts | `--fuzzy-username`, `--department`, `--status` |
| `aliyun csas list-user-applications` | Query user's authorized apps | `--sase-user-id` (required), `--name`, `--address` |
| `aliyun csas get-user-device` | Get single device detail | `--device-tag` (required) |
| `aliyun csas get-active-idp-config` | Get active IDP configuration | (none) |
| `aliyun csas list-user-groups` | Query user groups | `--name`, `--attribute-value`, `--user-group-ids` |

## Write Commands

| Command | Description | Key Parameters |
|---------|-------------|----------------|
| `aliyun csas update-user-devices-status` | Lock/unlock/mark devices | `--device-tags` (required), `--device-action` (required) |

## Common Usage Patterns

### Full pagination (auto)
```bash
aliyun csas list-user-devices --current-page 1 --page-size 500 --pager
```

### Filter by multiple conditions
```bash
aliyun csas list-user-devices --department "Engineering" --device-types Windows macOS --dlp-statuses Disabled --pager
```

### JMESPath output filtering
```bash
aliyun csas list-user-devices --current-page 1 --page-size 100 --cli-query "Devices[?DeviceStatus=='Online'].{Tag:DeviceTag,User:Username,Host:Hostname}"
```

### Count only (check TotalNum)
```bash
aliyun csas list-user-devices --device-statuses Locked --current-page 1 --page-size 1 --cli-query "TotalNum"
```

### Lock devices
```bash
aliyun csas update-user-devices-status --device-action Locked --device-tags tag1 tag2 tag3
```

### Unlock devices
```bash
aliyun csas update-user-devices-status --device-action Unlocked --device-tags tag1 tag2
```

## Global Options (available for all commands)

| Option | Description |
|--------|-------------|
| `--pager` / `--all-pages` | Auto-paginate and merge all pages |
| `--cli-query <jmespath>` | Filter output with JMESPath expression |
| `--cli-dry-run` | Print request details without sending |
| `--region <id>` | Override region |
| `--endpoint <url>` | Override service endpoint |
| `--log-level <level>` | DEBUG/INFO/WARN/ERROR |
| `-q` / `--quiet` | Suppress output |
