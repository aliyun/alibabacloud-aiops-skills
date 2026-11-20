# Validation tools

`dashboard.py validate` checks configuration, chart references, token dependencies
and grid overlaps.

```sh
python3 scripts/dashboard/dashboard.py validate --input final.json
python3 scripts/dashboard/dashboard.py validate --chart --input chart.json --layout grid
```

For a single chart, `--layout grid|free` supplies its layout context. Without it,
layout checks are skipped. A complete Dashboard supplies its own `attribute.type`.
Cross-chart references, token dependencies and overlaps require the complete Dashboard.

`--input FILE` reads UTF-8 JSON; `--input -` reads stdin. Duplicate keys and non-finite
numbers are rejected. Reports go to stdout by default; `--output FILE` saves the
JSON report to a path distinct from inputs and any baseline.

Reports contain `result`, `errors`, `warnings` and may include `unchecked` items
describing checks not performed. Each diagnostic includes `code`, `path` and
`message`, with context such as `chartId` or `origin` where applicable.

| `result` | Meaning | Default exit code | With `--strict` |
| --- | --- | --- | --- |
| `valid` | No errors or warnings | 0 | 0 |
| `warning` | Warnings only | 0 | 1 |
| `error` | One or more errors | 1 | 1 |

`--strict` changes only the exit code. Malformed or unreadable input produces an
`INPUT_ERROR` report with exit code 1. Argument errors use exit code 2 and a usage
message; other runtime failures produce a JSON error report on stderr.

Unknown fields and legacy formats may produce warnings; review them without discarding
saved fields merely to silence diagnostics. Legacy `search.query` receives only basic
structure checks. Top-fixed and hidden controls are excluded from grid-overlap checks.
For layout defaults and chart-specific requirements, see [layout](../features/layout.md)
and the [chart references](../charts/charts.md).

## Update validation

An original get response can serve as the baseline for classifying existing and
introduced problems:

```sh
python3 scripts/dashboard/dashboard.py validate --mode update --input final.json --baseline source.json
```

Existing problems unaffected by the edit appear as warnings with `origin: "baseline"`.
Changed fields and dependencies are checked as new input. Charts are matched by
stable `title` ID. This mode requires the original baseline as an input.

An external-token warning identifies a reference without a matching definition or
explicit default; an empty default such as `${{name|}}` counts as a default.

## Reports from other tools

`build` and `merge-additions` produce Dashboard JSON and a validation report.
Warnings appear on stderr as `{"validation": {...}}`; `--report check.json` saves
the report separately. Validation errors stop artifact output. The report path
is distinct from inputs and the Dashboard output.

For an update merge, `--base` is the working copy and
`--mode update --baseline source.json` selects the original get response.
