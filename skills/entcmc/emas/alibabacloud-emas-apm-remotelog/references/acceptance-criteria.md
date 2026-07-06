# Acceptance Criteria: alibabacloud-emas-apm-remotelog

**Scenario**: EMAS APM Remote Log (TLog) CLI Operations
**Purpose**: Skill testing acceptance criteria for remote log retrieval workflows

---

# Correct CLI Command Patterns

## 1. Product — verify product name exists (`emas-appmonitor`)

### ✅ CORRECT
```bash
aliyun emas-appmonitor get-tlog-device-list --region cn-shanghai --app-key 123456 --os android
```
Product `emas-appmonitor` is the correct plugin name for EMAS APM.

### ❌ INCORRECT
```bash
aliyun emas-app-monitor get-tlog-device-list ...
```
Product name uses underscores, not hyphens: `emas-appmonitor`, not `emas-app-monitor`.

### ❌ INCORRECT
```bash
aliyun emas get-tlog-device-list ...
```
The generic `emas` product does not contain TLog APIs. Use `emas-appmonitor`.

## 2. Command — verify action exists under the product

### ✅ CORRECT
```bash
aliyun emas-appmonitor get-tlog-device-list ...
aliyun emas-appmonitor create-tlog-task ...
aliyun emas-appmonitor get-tlog-task-info ...
aliyun emas-appmonitor get-tlog-task-collections ...
aliyun emas-appmonitor search-tlog ...
aliyun emas-appmonitor get-tlog-collect-list ...
```
All commands use lowercase hyphenated plugin mode format.

### ❌ INCORRECT
```bash
aliyun emas-appmonitor GetTlogDeviceList ...
aliyun emas-appmonitor CreateTlogTask ...
```
Plugin mode uses lowercase hyphenated actions, not PascalCase API names.

### ❌ INCORRECT
```bash
aliyun emas-appmonitor get-tlog-device ...
aliyun emas-appmonitor query-tlog-task ...
```
These command names do not exist. Use the exact API-to-plugin mapping.

## 3. Parameters — verify each parameter name exists

### ✅ CORRECT
```bash
aliyun emas-appmonitor get-tlog-device-list \
  --region cn-shanghai \
  --app-key 123456 \
  --os android \
  --user-nick testuser \
  --page-index 1 \
  --page-size 10
```

### ✅ CORRECT
```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key 123456 \
  --os android \
  --ali-yun-name operator \
  --days 1 \
  --task-name my-task \
  --source-type USER \
  --device-json '[{"deviceId":"xxx","os":"android"}]'
```

### ❌ INCORRECT
```bash
aliyun emas-appmonitor get-tlog-device-list --AppKey 123456
```
Parameter names are lowercase with hyphens: `--app-key`, not `--AppKey`.

### ❌ INCORRECT
```bash
aliyun emas-appmonitor search-tlog --start-time 1234567890000
```
The correct parameter is `--begin-date`, not `--start-time`.

## 4. Dry-run before write operations

### ✅ CORRECT
```bash
# First: dry-run to preview
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key 123456 \
  --os android \
  --ali-yun-name operator \
  --days 1 \
  --task-name my-task \
  --source-type USER \
  --device-json '[{"deviceId":"xxx","os":"android"}]' \
  --cli-dry-run

# Second: after confirmation, execute without --cli-dry-run
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key 123456 \
  --os android \
  --ali-yun-name operator \
  --days 1 \
  --task-name my-task \
  --source-type USER \
  --device-json '[{"deviceId":"xxx","os":"android"}]'
```
Always use `--cli-dry-run` first for create-tlog-task.

### ❌ INCORRECT
```bash
aliyun emas-appmonitor create-tlog-task \
  --region cn-shanghai \
  --app-key 123456 \
  --os android \
  --ali-yun-name operator \
  --days 1 \
  --task-name my-task \
  --source-type USER \
  --device-json '[{"deviceId":"xxx","os":"android"}]'
```
Skipping dry-run for write operations may create unintended tasks.

## 5. OS parameter values

### ✅ CORRECT
```bash
aliyun emas-appmonitor get-tlog-device-list --os android ...
aliyun emas-appmonitor get-tlog-device-list --os iphoneos ...
```

### ❌ INCORRECT
```bash
aliyun emas-appmonitor get-tlog-device-list --os iOS ...
aliyun emas-appmonitor get-tlog-device-list --os Android ...
```
Valid values are `android` and `iphoneos` (case-sensitive, lowercase).

## 6. Time format for SearchTlog

### ✅ CORRECT
```bash
aliyun emas-appmonitor search-tlog \
  --begin-date 1700000000000 \
  --end-date 1700086400000
```
Unix milliseconds, 13 digits.

### ❌ INCORRECT
```bash
aliyun emas-appmonitor search-tlog \
  --begin-date 1700000000 \
  --end-date 1700086400
```
10-digit Unix seconds are incorrect; must be 13-digit milliseconds.

## 7. source-type values for GetTlogCollectList

### ✅ CORRECT
```bash
aliyun emas-appmonitor get-tlog-collect-list --source-type POSITIVE
aliyun emas-appmonitor get-tlog-collect-list --source-type USER
```

### ❌ INCORRECT
```bash
aliyun emas-appmonitor get-tlog-collect-list --source-type positive
```
Value must be uppercase: `POSITIVE`, `USER`.

---

# Correct Common SDK Code Patterns

## 1. Import Patterns

### ✅ CORRECT
```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_emas_appmonitor20190611.client import Client as EmasAppmonitorClient
```

## 2. Authentication — must use CredentialClient

### ✅ CORRECT
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'emas-appmonitor.cn-shanghai.aliyuncs.com'

# REQUIRED: identify this skill in the User-Agent for server-side telemetry,
# matching the CLI ai-mode user-agent set in SKILL.md.
config.user_agent = "AlibabaCloud-Agent-Skills/alibabacloud-emas-apm-remotelog"

# REQUIRED: set explicit timeouts (milliseconds) — never rely on framework defaults,
# which can hang indefinitely on slow networks or backend stalls.
config.connect_timeout = 10000   # 10s for the TCP/TLS handshake
config.read_timeout    = 30000   # 30s for the response body
                                 # Tune up for log-heavy calls like SearchTlog
                                 # (e.g. 60000 ms when paging large windows).

client = EmasAppmonitorClient(config)
```

### ❌ INCORRECT
```python
config = open_api_models.Config(
    access_key_id='LTAI5tXXXX',
    access_key_secret='xxxxxxxx'
)
```
Never hardcode credentials. Use CredentialClient.

### ❌ INCORRECT (missing timeouts)
```python
credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'emas-appmonitor.cn-shanghai.aliyuncs.com'
# No connect_timeout / read_timeout — request can hang forever if the
# backend or network stalls. Always set both.
client = EmasAppmonitorClient(config)
```

## 3. Timeout configuration

| Field | Unit | Recommended | Notes |
|---|---|---|---|
| `config.connect_timeout` | milliseconds | `10000` (10s) | TCP/TLS handshake. Bump only when running through a slow proxy. |
| `config.read_timeout` | milliseconds | `30000` (30s) default; `60000`+ for `SearchTlog` with large pages | Time waiting for the response body. Don't leave unset. |

**Rule**: every Config instance MUST set both `connect_timeout` and `read_timeout` before being passed to `EmasAppmonitorClient`. The TLog APIs in this skill — especially `search-tlog` over wide time windows — can return slowly when the backing store is busy; without explicit timeouts a single hung call will block the entire workflow.
