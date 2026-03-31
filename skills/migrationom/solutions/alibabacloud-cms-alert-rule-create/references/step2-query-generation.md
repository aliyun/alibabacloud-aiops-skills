# Step 2: Query Generation

## Purpose
Discover and select the correct metric for the alert rule.

---

## Dynamic Metric Discovery (Primary Method)

### CRITICAL RULE
> **MUST call `describe-metric-meta-list` API to discover metrics. DO NOT rely solely on hardcoded metric lists.**

### Step 1: Query Available Metrics

After determining the namespace in Step 1, query all available metrics:

```bash
aliyun cms describe-metric-meta-list \
  --namespace "<namespace>" \
  --page-size 100
```

**Example Output:**
```json
{
  "Resources": {
    "Resource": [
      {
        "MetricName": "CPUUtilization",
        "Description": "CPU utilization rate",
        "Unit": "%",
        "Statistics": "Average,Minimum,Maximum",
        "Periods": "60,300,900",
        "Dimensions": "userId,instanceId"
      }
    ]
  }
}
```

### Step 2: Match User Intent to Metric

Based on user's description, match to the appropriate metric:

| User Intent | Common MetricName Keywords |
|-------------|---------------------------|
| CPU usage/utilization | `CPU`, `cpu` |
| Memory/RAM usage | `Memory`, `memory`, `Mem` |
| Disk space/usage | `Disk`, `disk`, `Storage`, `storage` |
| Network traffic | `Net`, `net`, `Traffic`, `Bandwidth`, `Rate` |
| Connections | `Connection`, `connection`, `Conn`, `conn` |
| IOPS | `IOPS`, `iops`, `IO` |
| Latency/delay | `Latency`, `latency`, `Delay`, `delay` |
| Error/failure | `Error`, `error`, `Fail`, `fail`, `Drop` |
| Load/queue | `Load`, `Queue`, `queue` |

### Step 3: Confirm with User

Present the matched metric(s) and ask user to confirm:

```
Based on your requirement, I found the following matching metrics:

1. CPUUtilization
   - Description: CPU utilization rate
   - Unit: %
   - Statistics: Average, Minimum, Maximum

Would you like to use this metric, or choose another one?
```

### Step 4: Extract Key Parameters

From the selected metric's metadata, extract:
- **MetricName**: For `--metric-name` parameter
- **Statistics**: Recommend `Average` unless user specifies otherwise; use `Value` for OSS/special metrics
- **Periods**: Use to validate the `--interval` parameter
- **Dimensions**: To understand required resource identifiers

---

## CLI Help Discovery

If unsure about command syntax or parameters:

```bash
# List all CMS commands
aliyun cms --help

# Show detailed usage for a specific command
aliyun cms describe-metric-meta-list --help
```

This will show available parameters, required fields, and usage examples.

---

## Static Reference (Fallback)

If `describe-metric-meta-list` API call fails (timeout, auth error, etc.), fall back to the common metrics reference in `metrics.md`.

See `metrics.md` for the common metrics quick reference table.

---

## Next Step
→ `step3-detection-config.md`
