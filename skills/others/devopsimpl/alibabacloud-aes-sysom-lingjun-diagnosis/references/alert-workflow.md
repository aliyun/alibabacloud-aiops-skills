# Alert Configuration Detailed Workflow (lingjun)

This document contains the detailed execution steps for SysOM DingTalk alert configuration (Steps 10–12).

All `aliyun` CLI commands that call OpenAPI **MUST** include `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}`, reusing the single session-id generated in Step 0; SDK scripts receive the same value through the `SKILL_SESSION_ID` environment variable (see the Observability section in `SKILL.md`). Local/system commands (`aliyun version`, `aliyun configure ...`, `aliyun plugin ...`) **MUST NOT** carry `--user-agent`.

> **⛔ Channel Constraint (MUST OBEY):** Every alert step below goes **exclusively** through the SysOM channel (`aliyun sysom list-alert-items` and the two `scripts/*.py` SDK scripts). It is **STRICTLY FORBIDDEN** to call CloudMonitor (CMS / CMS2) or any other product's APIs — workspaces, integration policies, contacts (`PutContact`), alert rules, etc. — to accomplish alerting. A `403 Forbidden` on such a call means the wrong channel was used, not that permissions are missing.
>
> **⛔ Enrollment is not part of this skill.** `aliyun sysom install-agent` / `list-instance-status` / `uninstall-agent` MUST NOT be called. If the user asks to enroll a node or install the Agent, state plainly that this skill does not support it and stop.

---

## When to Run This Phase

| User intent in the request | Behavior |
|---------------------------|----------|
| Asks for DingTalk alerts / an alert strategy (with or without a Webhook URL) | Run Steps 10–12 immediately after the diagnosis result — do **NOT** ask whether they want it |
| Says nothing about alerts | End after Step 9; do **NOT** turn alert configuration into a question |
| Explicitly declines monitoring / alerts | End after Step 9 with the mandatory closing statement below |

> **⚠️ Mandatory Closing Statement on Decline:** Whenever the user has stated they do not want monitoring / enrollment / alerts, your closing message **MUST** explicitly state, **in the same language the user used**, that no alert configuration was performed and that this was a one-time diagnosis.
>
> - Example: `As requested, monitoring and alert configuration are skipped — this was a one-time diagnosis.`
>
> **Do NOT** re-pitch alert configuration after the user has declined.

---

## Alert Configuration Phase (Pipeline Pattern)

Alert configuration runs as one uninterrupted pipeline: create the alert destination (Webhook), list the alert items, then create the alert strategy.

### Step 10 — Collect DingTalk Webhook and Create Alert Destination (SDK Call)

**⚠️ Mandatory Rule: When the user has asked for alerts, run this step right after presenting the diagnosis result. Do NOT skip it, and do NOT ask whether they want alerts.**

Alert destinations are used to push SysOM alerts to DingTalk group bots. This feature is **NOT supported by CLI** — use Python SDK scripts under `scripts/`.

> **⚠️ SDK Prerequisites**
>
> Before executing this step, run `scripts/setup-sdk.sh` to initialize the SDK environment (checks Python >= 3.8, creates virtual environment, installs SDK):
> ```bash
> bash scripts/setup-sdk.sh
> ```

#### Step 10a — Obtain the Webhook URL

If the user already provided a Webhook URL in the request, use it as-is and go straight to Step 10b — **do NOT ask again**. Only when it is missing, output the following complete content:

---

> 📲 Please provide the DingTalk group bot **Webhook URL** for receiving alert notifications.
> Format: `https://oapi.dingtalk.com/robot/send?access_token=xxx`
>
> 💡 How to get it: DingTalk Group Settings → Bot Management → Add Bot → Custom Bot → Optional keyword: alert → Copy Webhook URL

---

**After outputting the above, STOP. Wait for user reply.**

#### Step 10b — Create Alert Destination

With the Webhook URL in hand, **immediately create the alert destination via script** — no further confirmation needed:

```bash
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-destination.py '<user-provided-webhook-url>'
```

Optionally specify a destination name:

```bash
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-destination.py '<webhook-url>' '<destination-name>'
```

> **⚠️ You MUST use the virtual environment Python to execute scripts**
>
> **FORBIDDEN** to use `python3` or `python` directly — system Python dependencies may be incompatible, causing signature verification failures.
>
> **⚠️ You MUST inject `SKILL_SESSION_ID=<session-id>`** — the script builds its SDK User-Agent as `AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}` from it, so SDK calls stay traceable under the same session as the CLI commands.

On success, **stdout outputs `destination_id` (a pure number)**, detailed info is output to stderr.

**Result handling**:

- **Success** → Display destination ID and name, inform user of successful creation, record `destination_id` for Step 12, **immediately proceed to Step 11**
- **Failure** → Display error message, suggest checking Webhook URL format and RAM permissions

---

### Step 11 — Alert Item Selection

**⚠️ Mandatory Rule: After successful alert destination creation, you MUST immediately display the alert items list. Do NOT skip this step. If the user already stated the selection (e.g. "all", "all NODE items"), apply it directly and go to Step 12 without asking again.**

**11a. Get Available Alert Items List**

```bash
aliyun sysom list-alert-items --user-agent AlibabaCloud-Agent-Skills/alibabacloud-aes-sysom-lingjun-diagnosis/{session-id}
```

**11b. Display Alert Items List to User**

Display the API-returned alert items categorized, each with a number. Format:

---

> ## 🔔 Please select alert items to enable
>
> Enter numbers, separated by spaces:
>
> **Quick selection**: `all` = select all | `node-all` = all NODE items | `pod-all` = all POD items
>
> **[NODE Saturation]**
>   1. Node CPU Usage Detection
>   2. Node Kernel CPU Usage Detection
>   ... (populate based on actual API response)

---

**After outputting, STOP. Wait for user reply.**

#### User Input Parsing Rules

| User Input | Parsing Method |
|-----------|---------------|
| `all` | Select all alert items |
| `node-all` | Select all NODE category items |
| `pod-all` | Select all POD category items |
| `1 2 4 11 12 21` | Select by number |
| `node-all 22 23` | Mixed usage |

---

### Step 12 — Create Alert Strategy

Once the alert items are known, **create the alert strategy directly** with `destinations` set to the destination ID from Step 10.

**12a. Determine clusters Parameter**

Always use `["default"]`.

**12b. Execute Creation (SDK Call)**

> **⚠️ CLI does NOT support the `destinations` parameter — you MUST use the SDK script to create alert strategies.**

```bash
SKILL_SESSION_ID=<session-id> .sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
  --name "aliyun-aes-skills-create-<YYYYMMDDHHmm>" \
  --items "<alert_item_1>,<alert_item_2>" \
  --clusters "<clusters_value>" \
  --destinations "<destination_id>"
```

Parameter reference:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `--name` | Strategy name | `aliyun-aes-skills-create-202604151900` |
| `--items` | Alert item names, comma-separated | `Node CPU Usage Detection,Node Memory Usage Detection` |
| `--clusters` | Clusters, comma-separated (always `default`) | `default` |
| `--destinations` | Alert destination IDs, comma-separated | `1,2` |
| `--k8s-label` | Enable k8s labels (optional) | Defaults to false if omitted |

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN.
>
> **⚠️ `SKILL_SESSION_ID` MUST carry the same session-id used by every CLI command in this session.**

On success, **stdout outputs the strategy name**, detailed info is output to stderr.

**12c. Display Results**

- **Success** → Display strategy name, alert item count, status, associated alert destinations; inform user that alerts will be pushed to DingTalk via SysOM
- **Failure** → Display error message, suggest checking RAM permissions, node support status, network connectivity

---

### Alert Destination Management (On Demand)

Users can manage existing alert destinations via SDK as needed. The following operations all use the Python SDK — **NOT supported by CLI**.

#### Get Alert Destination Details

```python
from alibabacloud_sysom20231230 import models

request = models.GetAlertDestinationRequest(id=<destination_id>)
response = client.get_alert_destination(request)
```

#### Update Alert Destination

Only fill in the fields that need to be modified:

```python
from alibabacloud_sysom20231230 import models

request = models.UpdateAlertDestinationRequest(
    id='<destination_id>',
    name='<new_name>',                         # optional
    target='dingtalk',                         # optional
    params=models.UpdateAlertDestinationRequestParams(
        webhook='<new_webhook_url>'            # optional
    )
)
response = client.update_alert_destination(request)
```

#### Delete Alert Destination

```python
from alibabacloud_sysom20231230 import models

request = models.DeleteAlertDestinationRequest(id=<destination_id>)
response = client.delete_alert_destination(request)
```

#### List All Alert Destinations

Filter by `name` parameter (optional); omit to return all:

```python
from alibabacloud_sysom20231230 import models

request = models.ListAlertDestinationsRequest(name='<optional_filter_name>')
response = client.list_alert_destinations(request)
```
