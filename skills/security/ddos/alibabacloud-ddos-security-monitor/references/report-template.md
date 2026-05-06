# DDoS Security Inspection Report Template

> **Mandatory**: Every inspection report output MUST strictly follow this template structure. No sections may be omitted.

---

## Normal Situation Template

```markdown
# DDoS Security Inspection Report

## Inspection Summary

| Item | Value |
|------|-------|
| Inspection Time | <current time> |
| Base Period | <base_start> ~ <base_end> |
| Compare Period | <compare_start> ~ <compare_end> |
| Inspection Mode | <day-over-day / hour-over-hour / 30-min-over-30-min / custom> |
| Products Covered | <Basic Protection / Native Protection / Anti-DDoS Pro> |

---

## Asset Inventory

| Product | Status | Asset Details |
|---------|--------|---------------|
| DDoS Basic Protection | OK/Warning/Error | <instance count> ECS instances, <IP count> public IPs |
| DDoS Native Protection | OK/Warning/Error | <instance count> instances, <protected IP count> protected IPs |
| DDoS Anti-DDoS Pro/Premium | OK/Warning/Error | <instance count> instances, <domain count> domains |

### Detailed Asset List

#### Basic Protection Assets
| Instance Name | Instance ID | Public IP | Protection Status |
|--------------|-------------|-----------|-------------------|
| <...> | <...> | <...> | <...> |

#### Native Protection Assets
| Instance ID | Protected IP | Product Type | Region | Status |
|-------------|-------------|-------------|--------|--------|
| <...> | <...> | <...> | <...> | <...> |

#### Anti-DDoS Pro/Premium Assets
| Instance ID | Anti-DDoS IP | Associated Domains |
|-------------|-------------|-------------------|
| <...> | <...> | <...> |

---

## Inspection Results

### 1. DDoS Attack Events

| Product | Base Period Events | Compare Period Events | Change |
|---------|-------------------|----------------------|--------|
| Basic Protection | <N> events | - | - |
| Native Protection | <N> events | <N> events | <no change/increase/decrease> |
| Anti-DDoS Pro | <N> events | <N> events | <no change/increase/decrease> |

---

### 2. L4 Traffic Analysis (Peak)

| Product | Base Period Peak | Compare Period Peak | Change Rate |
|---------|----------------|--------------------|----|
| Native Protection | <N> Mbps | <N> Mbps | <+/-X% or no data> |
| Anti-DDoS Pro | <N> Mbps | <N> Mbps | <+/-X% or no data> |

---

### 3. L7 QPS Analysis

| Product | Base Period Peak | Compare Period Peak | Change Rate |
|---------|----------------|--------------------|----|
| Anti-DDoS Pro | <N> QPS | <N> QPS | <+/-X% or no data> |

---

### 4. HTTP Status Code Analysis

| Type | Base Period | Compare Period | Change Rate |
|------|-----------|---------------|-------------|
| Frontend 4xx | <N> times | <N> times | <+/-X% or no data> |
| Frontend 5xx | <N> times | <N> times | <+/-X% or no data> |

---

## Conclusion: No anomalies found in this inspection

**All metrics normal** during the past <time range>:
- No DDoS attack events
- No abnormal traffic fluctuations
- No status code anomalies

---

## Data Notes

| Product | Data Status | Reason |
|---------|------------|--------|
| <product> | <has data/no data> | <explanation> |
```

---

## Anomaly Template

When anomalies are found, replace the conclusion section with:

```markdown
## Conclusion: <N> anomalies found

### Anomaly Summary
| Product | Metric | Anomaly Type | Details |
|---------|--------|-------------|---------|
| <product> | <metric name> | Anomaly/Attention needed | <change rate/event details> |

### Remediation Recommendations
1. <specific actionable recommendation>
2. <...>
```
