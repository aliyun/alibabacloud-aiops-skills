# Enrollment and Alert Detailed Workflow

This document contains the detailed execution steps for SysOM instance enrollment and alert configuration (Steps 10–15).

All `aliyun` CLI commands **MUST** include `--user-agent AlibabaCloud-Agent-Skills`.

---

## Enrollment Recommendation Phase (Inversion + Pipeline Pattern)

After diagnosis is complete, **proactively recommend instance enrollment to the user**. After enrollment, SysOM will continuously monitor instance health. When performance issues occur, it will automatically trigger diagnosis and push reports to DingTalk group bots, enabling 24/7 unattended intelligent operations.

### Step 10 — Enrollment Recommendation and Intent Collection (Inversion Double Gate)

This step contains two strictly separated gates that **MUST be executed in order — merging, skipping, or simplifying is FORBIDDEN**.

#### Step 10A — Prominent Enrollment Recommendation (First Gate)

**⚠️ Mandatory Rule: After presenting diagnosis results, you MUST immediately output the following recommendation content verbatim. Do NOT abbreviate, omit, or rephrase in your own words.**

You must output the following complete content (replace `<instance_id>` with the actual instance ID):

---

> ## 🔔 Recommendation: Enroll Instance for 24/7 Automated Diagnosis
>
> The diagnosis just performed was a one-time manual operation. If you want SysOM to **continuously protect** this instance, we recommend **instance enrollment**.
>
> ### After enrollment, you will get:
>
> - 🔍 **Automated Diagnosis**: When the instance experiences performance issues like CPU spikes, memory leaks, or IO latency, SysOM will **automatically trigger deep diagnosis** without manual intervention
> - 📲 **DingTalk Alerts**: Diagnosis reports will be **automatically pushed to DingTalk group bots**, notifying the ops team immediately
> - 🛡️ **Continuous Monitoring**: 24/7 uninterrupted protection, shifting from "investigate after problems occur" to "automatically told the root cause when problems occur"
>
> **Would you like to enroll instance `<instance_id>`?**

---

**After outputting the above, STOP. Wait for user reply.**

- User **declines** → end the pipeline
- User **agrees** → proceed to Step 10B

**⚠️ Do NOT ask about enrollment method in Step 10A.**

#### Step 10B — Ask Enrollment Method (Second Gate)

**Only execute this step after the user explicitly agrees to enrollment in Step 10A.**

You must output the following complete content (replace `<instance_id>` and `<region>` with actual values):

---

> ### Please choose an enrollment method
>
> **A. Enroll current instance only**
> Only enroll the instance just diagnosed: `<instance_id>` (`<region>`)
>
> **B. Enroll ACK cluster**
> If this instance belongs to an ACK cluster, you can enroll **all nodes** in the cluster with one click.
> Newly added nodes will be automatically enrolled — no manual action needed.
> 👉 Please provide the **ACK Cluster ID** (e.g., `c9d7f3fc3d42********c1100ffb19d`)
>
> **C. Enroll multiple specified instances**
> Batch enroll multiple instances.
> 👉 Please provide the instance list in the format `InstanceID:Region`, separated by spaces
> Example: `i-xxx:cn-beijing i-yyy:cn-hangzhou`
>
> Please choose A / B / C, or tell me your requirements directly.

---

**After outputting the above, STOP. Wait for user reply.**

#### Intent Parsing Rules

| User Reply | Enrollment Mode | Parameters to Collect |
|-----------|----------------|----------------------|
| Choose A / enroll current instance / agree directly | Single instance | No additional parameters needed, reuse instance_id and region from Step 4 |
| Choose B / provided a cluster ID | Cluster | `cluster_id` (ask if not provided) |
| Choose C / provided multiple instances | Multi-instance | Parse the instance list provided by user |

---

### Step 11 — Execute Enrollment

#### Enroll Single or Multiple Instances

```bash
aliyun sysom install-agent \
  --instances instance=<instance_id_1> region=<region_1> \
  --instances instance=<instance_id_2> region=<region_2> \
  --install-type InstallAndUpgrade \
  --agent-id 74a86327-3170-412c-8e67-da3389ec56a9 \
  --agent-version 3.12.0-1 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Enroll ACK Cluster

```bash
aliyun sysom install-agent-for-cluster \
  --cluster-id <cluster_id> \
  --agent-id 74a86327-3170-412c-8e67-da3389ec56a9 \
  --agent-version 3.12.0-1 \
  --config-id 8gj86wrt7-3170-412c-8e67-da3389ecg6a9 \
  --user-agent AlibabaCloud-Agent-Skills
```

#### install-type Enum Values

| Value | Description |
|-------|-------------|
| `InstallAndUpgrade` | Install if not present, upgrade if present (default) |
| `OnlyInstallNotHasAgent` | Install if not present, skip if present |
| `OnlyUpgradeHasAgent` | Skip if not present, upgrade if present |
| `OnlyInstallWithoutStart` | Install component only, do not start service |

> **Note**: For cluster enrollment, the initial enrollment installs the agent on all current ECS instances in the cluster (first batch limited to 50 if exceeding 50 instances). Newly added ECS instances will be automatically enrolled.

---

### Step 12 — Enrollment Status Confirmation and Result Output

#### Instance Mode — Poll Instance Status (interval: 10s, max: 60 attempts)

```bash
aliyun sysom list-instance-status \
  --instance <instance_id> \
  --biz-region <region> \
  --user-agent AlibabaCloud-Agent-Skills
```

#### Cluster Mode — Poll Cluster Status

Get the full cluster list (**do NOT pass `--cluster-id`**), then match the target cluster by `cluster_id` field:

```bash
aliyun sysom list-clusters \
  --user-agent AlibabaCloud-Agent-Skills
```

From the returned cluster list, iterate through each cluster object, find the entry where `cluster_id` matches the target, and check its `cluster_status` field. Also record the `name` field for later use in create-alert-strategy.

#### Enrollment Status Reference

| Status | Meaning | Icon |
|--------|---------|------|
| `installing` / `Installing` | Installing | ⏳ |
| `running` / `Running` | Enrollment successful | ✅ |
| `failed` / `Offline` | Failed/Abnormal | ❌ |
| `stopped` | Agent stopped | ⏹️ |

#### Result Display

- **All successful** → Inform user that all instances are enrolled, SysOM will continuously monitor
- **Partially failed** → List successful and failed instances, suggest checking failed ones
- **All failed** → Suggest checking network connectivity, RAM permissions, OS compatibility

---

## Alert Configuration Phase (Pipeline Pattern)

After enrollment is complete, **proceed directly to alert configuration**: first create alert destination (collect Webhook), then select alert items, and finally create alert strategy.

### Step 13 — Collect DingTalk Webhook and Create Alert Destination (Inversion Gate + SDK Call)

**⚠️ Mandatory Rule: After successful enrollment, you MUST immediately collect the DingTalk bot Webhook URL from the user. Do NOT skip this step.**

Alert destinations are used to push SysOM alerts to DingTalk group bots. This feature is **NOT supported by CLI** — use Python SDK scripts under `scripts/`.

> **⚠️ SDK Prerequisites**
>
> Before executing this step, run `scripts/setup-sdk.sh` to initialize the SDK environment (checks Python >= 3.8, creates virtual environment, installs SDK):
> ```bash
> bash scripts/setup-sdk.sh
> ```

#### Step 13a — Collect Webhook URL from User

You must output the following complete content:

---

> 📲 Please provide the DingTalk group bot **Webhook URL** for receiving alert notifications.
> Format: `https://oapi.dingtalk.com/robot/send?access_token=xxx`
>
> 💡 How to get it: DingTalk Group Settings → Bot Management → Add Bot → Custom Bot → Optional keyword: alert → Copy Webhook URL

---

**After outputting the above, STOP. Wait for user reply.**

#### Step 13b — Create Alert Destination

After the user provides the Webhook URL, **immediately create the alert destination via script** — no further confirmation needed:

```bash
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py '<user-provided-webhook-url>'
```

Optionally specify a destination name:

```bash
.sysom-sdk-venv/bin/python scripts/create-alert-destination.py '<webhook-url>' '<destination-name>'
```

> **⚠️ You MUST use the virtual environment Python to execute scripts**
>
> **FORBIDDEN** to use `python3` or `python` directly — system Python dependencies may be incompatible, causing signature verification failures.

On success, **stdout outputs `destination_id` (a pure number)**, detailed info is output to stderr.

**Result handling**:

- **Success** → Display destination ID and name, inform user of successful creation, record `destination_id` for Step 15, **immediately proceed to Step 14**
- **Failure** → Display error message, suggest checking Webhook URL format and RAM permissions

---

### Step 14 — Alert Item Selection (Inversion Gate)

**⚠️ Mandatory Rule: After successful alert destination creation, you MUST immediately display the alert items list. Do NOT skip this step.**

**14a. Get Available Alert Items List**

```bash
aliyun sysom list-alert-items --user-agent AlibabaCloud-Agent-Skills
```

**14b. Display Alert Items List to User**

Display the API-returned alert items categorized, each with a number. Format:

---

> ## 🔔 Please select alert items to enable
>
> Enter numbers, separated by spaces:
>
> **Quick selection**: `all` = select all | `node-all` = all NODE items | `pod-all` = all POD items
>
> **【NODE Saturation】**
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

### Step 15 — Create Alert Strategy

After the user selects alert items, **create the alert strategy directly** with `destinations` set to the destination ID from Step 13.

**15a. Determine clusters Parameter**

| Enrollment Mode | clusters Value |
|----------------|---------------|
| Instance mode (Step 10 chose A or C) | `["default"]` |
| Cluster mode (Step 10 chose B) | `["<cluster_name>"]` (note: name, NOT ID) |

**15b. Execute Creation (SDK Call)**

> **⚠️ CLI does NOT support the `destinations` parameter — you MUST use the SDK script to create alert strategies.**

```bash
.sysom-sdk-venv/bin/python scripts/create-alert-strategy.py \
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
| `--clusters` | Clusters, comma-separated (use `default` for instance mode) | `default` |
| `--destinations` | Alert destination IDs, comma-separated | `1,2` |
| `--k8s-label` | Enable k8s labels (optional) | Defaults to false if omitted |

> **⚠️ You MUST use `.sysom-sdk-venv/bin/python` to execute scripts** — using system `python3` is FORBIDDEN.

On success, **stdout outputs the strategy name**, detailed info is output to stderr.

**15c. Display Results**

- **Success** → Display strategy name, alert item count, cluster, status, associated alert destinations; inform user that alerts will be pushed to DingTalk via SysOM
- **Failure** → Display error message, suggest checking RAM permissions, enrollment status, network connectivity

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
