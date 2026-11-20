# Local rule validation

## Validate the configuration

The [validator](../../../scripts/alerting/validate_alert.py) checks a complete rule document
and reports configuration errors and warnings:

```bash
python3 "scripts/alerting/validate_alert.py" --input "$SLS_ALERT_FILE"
```

See [validation results](../validation-results.md) for statuses and report fields.
For an update, `--baseline` can compare the proposed configuration with an existing
`alert get` response:

```bash
python3 "scripts/alerting/validate_alert.py" --input "$SLS_ALERT_FILE" \
  --baseline "$SLS_ALERT_ORIGINAL_FILE"
```

The warning's value, context and `origin` help distinguish existing issues from changes
introduced by an edit. An unchanged warning may be unrelated to the requested update;
removing unknown fields merely to silence it can discard valid configuration.

The [schedule](scheduling.md), [query results](queries/verify-alert-query.md#validate-a-new-or-changed-query)
and [trigger expressions](triggering/define-alert-triggering.md#four-trigger-modes) provide
context for judging the intended behavior.
