# Validation and verification

| Check | Establishes |
| --- | --- |
| Plan/facts format | Required fields, types and source identities |
| Query configuration | Supported sources and required query settings |
| Chart configuration | Known options and supported bindings |
| Relationships | IDs, token dependencies, row references and grid overlaps |
| Baseline and diff | Intended changes and observed conflicts |
| Online query | Actual results and execution progress |
| Readback review | Saved configuration inspected separately after publishing |

Run dashboard.py validate to check a dashboard. It reports errors, warnings and
unchecked items. Supply --baseline when editing to compare against the original
configuration. Review unchecked items before publishing.

Empty existing layout settings are checked as `free` with a warning; new dashboard
publication still requires an explicit layout type. See [layout](../features/layout.md).

```sh
python3 scripts/dashboard.py validate --input final.json --baseline source.json
```

For an individual chart or a basic dashboard configuration check:

```sh
python3 scripts/validator.py --chart --json chart.json
python3 scripts/validator.py --dashboard --json dashboard.json
```

Use dashboard.py validate for cross-chart relationships, baseline comparison and
overlap checks. Both validators are offline: verify field availability and query
behavior with query results, and check visual changes in the dashboard. Follow
[publish verification](../workflows/publish.md) for conflict checks and readback.

Check removed controls and row children for dangling references. For external-token
warnings, confirm that the caller supplies the variable. Resolve query-field text
placeholders against the returned fields.
