# Step 3: Detection Config

## Purpose
Configure trigger conditions and advanced settings.

---

## Configuration Items

| Item | Description | Default |
|------|-------------|---------|
| **Check Frequency** | Check every N minutes | 1 minute |
| **Trigger Condition** | Comparison logic + threshold | `Value > Threshold` |
| **Evaluation Periods** | N consecutive periods meeting condition | 3 times |
| **Severity Level** | Critical / Warn / Info | Critical |
| **No Data Alert** | Alert when data is missing | No |

---

## Check Frequency (Suggest + Confirm)

Check frequency defaults to **1 minute**, need to confirm with user:

```
Model: "Check frequency defaults to 1 minute. Do you need to adjust?
  Common options: 1 min / 5 min / 15 min / 1 hour"

User: "Use default" → Use 1 minute
User: "Check every 5 minutes" → Use 5 minutes
```

---

## Comparison Operators

| Operator | Meaning | CLI Value |
|----------|---------|-----------|
| `>=` | Greater than or equal | `GreaterThanOrEqualToThreshold` |
| `>` | Greater than | `GreaterThanThreshold` |
| `<=` | Less than or equal | `LessThanOrEqualToThreshold` |
| `<` | Less than | `LessThanThreshold` |
| `==` | Equal | `EqualToThreshold` |
| `!=` | Not equal | `NotEqualToThreshold` |

---

## Unit Auto-Adaptation

Automatically recognize metric units and convert:

| User Input | Metric Unit | Conversion |
|------------|-------------|------------|
| "exceeds 1G" | Byte | `1073741824` |
| "exceeds 1s" | Millisecond | `1000` |
| "exceeds 80%" | Percentage | `80` |

---

## Next Step
→ `step4-notification.md`
