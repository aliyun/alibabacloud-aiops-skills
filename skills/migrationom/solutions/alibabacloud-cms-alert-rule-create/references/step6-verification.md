# Step 6: Verification

## Purpose
Check alert status and provide best practice recommendations.

---

## Status Confirmation

### CMS 1.0

```bash
aliyun cms describe-metric-rule-list --rule-id "<rule-id>"
```

**Expected Result:**
- `AlertState` = "OK" or "ALARM"

---

## Common Management Commands

### CMS 1.0

```bash
# List rules
aliyun cms describe-metric-rule-list --namespace <ns>

# Enable rule
aliyun cms enable-metric-rules --ids '["<id>"]'

# Disable rule
aliyun cms disable-metric-rules --ids '["<id>"]'

# Delete rule
aliyun cms delete-metric-rules --ids '["<id>"]'
```

---

## Best Practice Recommendations

### 1. Recovery Notification
Recommend enabling "Recovery Notification" switch.

### 2. Multi-level Alerting
Recommend configuring both Warn and Critical thresholds.

### 3. Silence Period
Recommend 5-10 minutes silence period in production to avoid alert storms.

---

## Example Scenarios

### Scenario: CMS 1.0 Resource Alert

**User**: "Help me monitor ECS CPU, alert when exceeds 85%"

**Skill Path**:
1. ✅ Identify as **CMS 1.0 alert** (`step0`)
2. ✅ Get Namespace=`acs_ecs_dashboard`, confirm instance scope (`step1`)
3. ✅ Extract `CPUUtilization` from metric library (`step2`)
4. ✅ Configure threshold 85% (`step3`)
5. ✅ Query CMS contact groups (`step4`)
6. ✅ Preview configuration and execute (`step5`)
7. ✅ Verify status (`step6`)

---

## Completion
Alert creation complete!
