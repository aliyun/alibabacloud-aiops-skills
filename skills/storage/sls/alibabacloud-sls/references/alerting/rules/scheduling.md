# Check frequency

A schedule determines when a rule evaluates its queries. Configure it through
the rule's `schedule` object; the query time window is configured separately.

## Choose a schedule type

| Usage | Requirement | `schedule.type` | Required parameter |
| --- | --- | --- | --- |
| Ordinary | Check at a regular interval | `FixedRate` | `interval`, such as `1m`, `5m`, or `1h` |
| Optional | Check at calendar times | `Cron` | `cronExpression`; `timeZone` is optional |

Prefer `FixedRate`. It is easier to reason about and is the normal choice for a
rolling log window.

```json
{
  "type": "FixedRate",
  "interval": "1m"
}
```

Use `Cron` for calendar-aligned checks. When execution time depends on a
timezone, confirm the service default or set it explicitly; do not infer it
from the execution environment's timezone.

```json
{
  "type": "Cron",
  "cronExpression": "0 18 * * *",
  "timeZone": "+0800"
}
```

## Schedule fields

| Field | Valid value |
| --- | --- |
| `FixedRate.interval` | Unit-suffixed duration from 60 seconds through 30 days: `s`, `m`, `h`, or `d` |
| `Cron.cronExpression` | Five fields, minute resolution, 1–64 characters |
| `Cron.timeZone` | Optional string; missing or empty uses the service default. A nonempty value uses `+HHMM` or `-HHMM`, from `-1200` through `+1400`. |
| `delay` | Optional integer from 0 through 86400 seconds |

`FixedRate` does not require a timezone. For `Cron`, check that the expression
and timezone produce the intended schedule.

For other schedule fields and examples, see the
[official creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs).

## Keep the three clocks separate

- `schedule.interval` or `schedule.cronExpression` controls when evaluation runs.
- `configuration.queryList[].start` and `end` control which logs each run reads.
- `configuration.policyConfiguration.repeatInterval` controls repeated
  notifications for an already-firing alert.

For example, checking every minute, querying `-5m` through `now`, and repeating
notifications every hour are compatible choices. Set each from the requirement.

Keep the complete `schedule` object in the prepared rule document and preserve
all fields unrelated to the requested change. See
[rule target](../cli-execution.md#target) for submission.
