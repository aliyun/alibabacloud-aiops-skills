# Local validation results

The rule and notification-resource validators accept a UTF-8 JSON file through
`--input FILE` or a positional file argument; `--input -` reads stdin. Duplicate
keys and non-finite numbers are rejected. Reports go to stdout by default;
`--output FILE` saves the JSON report to a path distinct from inputs and any baseline.

Reports contain `result`, `errors` and `warnings`. Each diagnostic includes `code`,
`path` and `message`. A baseline annotates diagnostic `origin` as `candidate` or
`baseline` without changing severity.

| `result` | Meaning | Default exit code | With `--strict` |
| --- | --- | --- | --- |
| `valid` | No errors or warnings | 0 | 0 |
| `warning` | Warnings only | 0 | 1 |
| `error` | One or more errors | 1 | 1 |

`--strict` changes only the exit code. Malformed or unreadable input produces an
`INPUT_ERROR` report with exit code 1. Argument errors use exit code 2 and a usage
message; other runtime failures produce a JSON error report on stderr.

| Top-level field | Meaning |
| --- | --- |
| `resource_name` | Resource namespace; resource validator only. |
| `purpose` | Validation purpose: `read` or `custom-write`; resource validator only. |
| `identity_mapping` | Record ID and tag derived from the resource value; resource validator only. |
