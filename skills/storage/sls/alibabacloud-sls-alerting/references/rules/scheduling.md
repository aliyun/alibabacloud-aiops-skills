# Check frequency

A schedule determines when a rule evaluates its queries. Configure it through
the rule's `schedule` object; the query time window is configured separately.

## Choose a schedule type

| Usage | Requirement | `schedule.type` | Required parameter |
| --- | --- | --- | --- |
| Ordinary | Check at a regular interval | `FixedRate` | `interval`, such as `1m`, `5m`, or `1h` |
| Optional | Check at calendar times | `Cron` | `cronExpression` and an explicit `timeZone` |

Prefer `FixedRate`. It is easier to reason about and is the normal choice for a
rolling log window.

`FixedRate.interval` must be a duration string ending in `s`, `m`, `h`, or `d`.
Its value must be between 60 and 2,592,000 seconds. For example, use `"60s"`,
not the unitless string `"60"`.

```json
{
  "type": "FixedRate",
  "interval": "1m"
}
```

Use `Cron` only when the requirement is calendar-aligned. SLS alert Cron uses a
five-field, minute-resolution expression. Confirm the intended timezone instead
of inheriting the agent's local timezone.

```json
{
  "type": "Cron",
  "cronExpression": "0 18 * * *",
  "timeZone": "+0800"
}
```

Use the `+HHMM` or `-HHMM` timezone format shown below. Do not add a seconds
field or assume UTC. Check that the Cron expression and timezone produce the
intended schedule; the local rule validator checks field shape, not Cron grammar.

## Schedule fields

| Field | Valid value |
| --- | --- |
| `FixedRate.interval` | Unit-suffixed duration from 60 seconds through 30 days: `s`, `m`, `h`, or `d` |
| `Cron.cronExpression` | Five fields, minute resolution, 1–64 characters |
| `Cron.timeZone` | `+HHMM` or `-HHMM`, from `-1200` through `+1400`; specify it explicitly |
| `delay` | Optional integer from 0 through 86400 seconds |

For other schedule fields and examples, see the
[official creation guide](https://help.aliyun.com/zh/sls/create-an-alert-monitoring-rule-for-logs).

## Keep the three clocks separate

- `schedule.interval` or `schedule.cronExpression` controls when evaluation runs.
- `configuration.queryList[].start` and `end` control which logs each run reads.
- `configuration.policyConfiguration.repeatInterval` controls repeated
  notifications for an already-firing alert.

For example, checking every minute, querying `-5m` through `now`, and repeating
notifications every hour are compatible choices. Set each from the requirement.

When creating or updating a rule, serialize the complete `schedule` object from
the prepared rule document as a JSON string and pass it to `--schedule`. Preserve
all schedule fields unrelated to the requested change.
