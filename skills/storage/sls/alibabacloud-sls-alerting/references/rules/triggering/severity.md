# Alert severity

## Severity order is semantic

One severity branch is enough for an ordinary alert. When the requirement maps
different conditions to different levels, SLS evaluates branches from top to
bottom and stops at the first match. Use this order whenever those levels are
present:

| Level | Numeric `severity` |
| --- | --- |
| Critical | `10` |
| High | `8` |
| Medium | `6` |
| Low | `4` |
| Report | `2` |

Larger values mean greater severity. This same scale applies to notification
policy conditions; it is not a 1-based priority ranking. See the
[official severity mapping](https://help.aliyun.com/zh/sls/developer-reference/data-structure-of-an-alert-monitoring-rule).

Include only the required levels, but never place a broader lower-severity
condition before a higher one. This configuration reports Critical for 100 or
more errors and High for 20 through 99:

```json
[
  {
    "severity": 10,
    "evalCondition": {
      "condition": "errorCount >= 100",
      "countCondition": ""
    }
  },
  {
    "severity": 8,
    "evalCondition": {
      "condition": "errorCount >= 20",
      "countCondition": ""
    }
  }
]
```
