# CLI Envelope Output Format (sysom-diagnosis)

This document was split out from `SKILL.md` and describes the field structure and consumption conventions of the JSON envelope printed to `osops` CLI stdout.

## Envelope Version

- **`format`**: `sysom_agent`
- **`version`**: `3.4` (field contract version; increase when removing/changing committed `data`/`agent` keys)

## Top-Level Structure

| Field | Description |
|------|------|
| `ok` | Boolean, success/failure |
| `action` | Command action identifier (`memory_classify`, `memory_memgraph_hint`, etc.) |
| `error` | On failure includes `code`/`message`/`request_id` (if present) |
| `agent` | Model-facing summary and guidance (see below) |
| `data` | Business payload (see below) |
| `execution` | Execution metadata (`subsystem`, `phase`, `mode`) |

## `agent` Block

| Field | Description |
|------|------|
| `summary` | One-paragraph summary; **`--verbose-envelope`** expands full detail |
| `findings` | Findings list; each item includes `kind` and key metrics |
| `next` | Structured next step (`action_kind`/`command`/`purpose_zh`); empty after successful deep diagnosis |

## `data` Block (memory quick path)

| Field | Description |
|------|------|
| `data.routing` | Routing result: `recommended_service_name`/`confidence`/`categories`/`oom_signal`, etc. |
| `data.local` | Local snapshot: `facts`/`oom_local`/`meminfo_facts`/`rss_top_sample` |
| `data.remote` | Present only with `--deep-diagnosis`: `ok`/`task_id`/`result`/`error` |

## CLI Tunables

- **Common options**: `--channel`, `--region`, `--instance`, `--timeout`, `--poll-interval`, `--verbose-envelope`
- **Diagnosis-specific params**: pass OpenAPI `params` via **`--params` (JSON string) or `--params-file` (JSON file)**; fields are documented in corresponding files under [diagnoses/](./diagnoses/)
- **Local memory quick** (without `--deep-diagnosis`): default strategy is fixed; tunable parameters apply to remote deep diagnosis via `--params`
