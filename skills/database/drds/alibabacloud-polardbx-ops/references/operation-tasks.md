# Operation Tasks & Events APIs

PolarDB-X O&M events (active operation tasks), maintenance configuration, history events, and health checks. All CLI examples use the `aliyun polardbx` subcommand in plugin mode.

> Note: Region flag is `--biz-region-id`.

---

## DescribeActiveOperationTasks

Query pending/ongoing O&M event tasks (e.g. scheduled maintenance).

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `task-type` | String | Task type; `all` for all tasks |
| `product-id` | String | Product, default `polarx` |
| `db-type` | String | Database type, fixed `polarx` |
| `ins-name` | String | Instance name filter |
| `change-level` | String | `all` / `S0` (fault fix) / `S1` (system O&M) |
| `status` | Integer | `-1` all pending+running / `3` pending / `4` running |
| `allow-change` | Integer | Filter tasks allowing time change |
| `allow-cancel` | Integer | Filter tasks allowing cancel |
| `page-number` / `page-size` | Integer | Pagination |

### CLI example

```bash
aliyun polardbx describe-active-operation-tasks \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --task-type all \
  --status -1 \
  --page-number 1 --page-size 25 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeActiveOperationTasks`

---

## DescribeActiveOperationTaskCount

Get the total count of O&M event tasks.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `product` | String | Product, default `polarx` |

### CLI example

```bash
aliyun polardbx describe-active-operation-task-count \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeActiveOperationTaskCount`

---

## DescribeActiveOperationMaintainConf

Show the O&M maintenance time configuration.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |

### CLI example

```bash
aliyun polardbx describe-active-operation-maintain-conf \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeActiveOperationMaintainConf`

---

## ModifyActiveOperationMaintainConf

Modify the O&M maintenance time configuration.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `cycle-type` | String | Cycle mode: `Week` |
| `cycle-time` | String | Weekday selection `1-7`, e.g. `1,2,3,4,5,6,7` |
| `maintain-start-time` | String | Start time (UTC), e.g. `02:00:00Z` |
| `maintain-end-time` | String | End time (UTC), e.g. `04:00:00Z` |
| `status` | Integer | `1` enabled / `0` disabled |

### CLI example

```bash
aliyun polardbx modify-active-operation-maintain-conf \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --cycle-type Week \
  --cycle-time 1,2,3,4,5,6,7 \
  --maintain-start-time 02:00:00Z \
  --maintain-end-time 04:00:00Z \
  --status 1 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyActiveOperationMaintainConf`

---

## ModifyActiveOperationTasks

Modify the execution time of O&M event tasks.

> **[MUST] Secondary confirmation required.** Rescheduling may trigger maintenance actions. Confirm with the user.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `ids` | String | O&M event ID(s) |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `switch-time` | String | Switch start time `YYYY-MM-DDThh:mm:ssZ` |
| `immediate-start` | Integer | `1` immediate / `0` at specified time |

### CLI example

```bash
aliyun polardbx modify-active-operation-tasks \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --ids 111 \
  --switch-time 2024-08-15T12:00:00Z \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:ModifyActiveOperationTasks`

---

## CancelActiveOperationTasks

Cancel O&M event tasks.

> **[MUST] Secondary confirmation required.** Confirm the event IDs with the user before cancelling.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |
| `ids` | String | Event ID set, comma-separated |

### CLI example

```bash
aliyun polardbx cancel-active-operation-tasks \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --ids 111,112 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CancelActiveOperationTasks`

---

## DescribeEvents

Query historical events.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region ID |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start-time` | String | Start time, e.g. `2024-10-18T03:07:25Z` |
| `end-time` | String | End time |
| `page-number` / `page-size` | Integer | Pagination |

### CLI example

```bash
aliyun polardbx describe-events \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --start-time 2024-10-01T00:00:00Z \
  --end-time 2024-10-31T00:00:00Z \
  --page-number 1 --page-size 20 \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeEvents`

---

## SkipCurrentStep

Skip the current step of a task (e.g. an import task pre-check).

> **[MUST] Secondary confirmation required.** Skipping a task step can bypass safety checks. Confirm with the user.

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `current-step` | String | Current step, e.g. `PRE_CHECK` |
| `slink-task-id` | String | Import task ID |

### CLI example

```bash
aliyun polardbx skip-current-step \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --current-step PRE_CHECK \
  --slink-task-id etx-******** \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:SkipCurrentStep`

---

## CheckHealth

Perform a service health check.

> Note: This action may require the latest `aliyun` CLI plugin. If `aliyun polardbx check-health --help` reports an unknown command, update the plugin (`aliyun plugin update`) or call the OpenAPI directly. It takes no business parameters beyond global flags.

### CLI example

```bash
aliyun polardbx check-health \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:CheckHealth`

---

## DescribeComponentPropeties

Get property information of a specified component.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `biz-region-id` | String | Region where the instance resides |
| `commodity-code` | String | Commodity type |
| `component-name` | String | Component name |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `storage-type` | String | Storage type |

### CLI example

```bash
aliyun polardbx describe-component-propeties \
  --biz-region-id cn-hangzhou \
  --region cn-hangzhou \
  --commodity-code <commodity-code> \
  --component-name <component> \
  --connect-timeout 3 --read-timeout 10 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-polardbx-ops/{session-id}
```

### RAM action

`polardbx:DescribeComponentPropeties`
