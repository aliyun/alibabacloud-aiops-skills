# oomcheck (OOM Diagnosis)

> Parameter notes are based on `service_scripts/oomcheck_pre.py`.

## Overview

Runs SysOM oomcheck on target instances and analyzes **OOM / oom-killer** paths with memgraph artifacts.

## When to Use (Agent)

- Cloud-side **OOM / oom-killer** diagnosis with SysOM remote flow.
- Do **not** confuse with parent-repo local-only OOM tooling (`linux-memory-oom` / `sysom_cli memory oom`).
- Remote OOM diagnosis must be triggered by `./scripts/osops.sh memory oom --deep-diagnosis ...` to call SysOM `InvokeDiagnosis`.

## Agent Conventions

General conventions (working directory, Bash execution, local/remote split, credential safety): [agent-conventions.md](../agent-conventions.md).  
This section lists oomcheck-specific rules only.

### Multiple OOM Events

- If local quick output shows multiple OOM events, use `--oom-at` to anchor one event.
- For remote oomcheck, pass `--oom-time` or `time` in `--params`. If user already provided time, do **not** run unbounded default commands.

### Time Formats

- CLI accepts ISO, `YYYY-MM-DD HH:MM:SS`, Unix seconds, journal-like formats, and converts to Unix seconds before InvokeDiagnosis.

## `params` Fields

| Field | Type | Required | Meaning | Default | Notes |
|------|------|------|------|------|------|
| `region` | string | yes* | Region | — | `--region` |
| `instance` | string | yes* | Instance ID | — | `--instance` |
| `pod` | string | no | Pod name | `""` | non-empty appends `-p` |
| `time` | string | no | OOM timestamp or `start~end` | `""` | from CLI `--oom-time`; converted to Unix seconds |

## Platform Constraints

| Item | Value |
|----|-----|
| support_channel | **all** |
| support_mode | **all** |

## Recommended Usage

Current instance (CLI auto-fills region/instance):

```bash
./scripts/osops.sh memory oom --deep-diagnosis --channel ecs --timeout 300
```

Remote instance:

```bash
./scripts/osops.sh memory oom --deep-diagnosis --channel ecs \
  --region cn-hangzhou --instance i-xxx --timeout 300
```

Local quick-only options: `--oom-at`, `--max-oom-summaries` (default 64), `--max-oom-full-logs` (default 1).  
Remote mode: `--oom-time` is written to `params.time` and converted to Unix seconds. Historical window should be **<= 1 hour and within 7 days**.
