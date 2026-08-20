---
name: alibabacloud-alinux-sysom-inspection
version: 0.2.0
description: >
  Inspect ECS instance health, detect anomalies in memory, disk, CPU, load,
  and resource leaks, and automatically trigger deep diagnosis when critical
  memory issues are detected. Suitable for routine inspections, troubleshooting,
  and risk warning scenarios. Trigger keywords: SysOM, inspection, instance
  diagnosis, memory_usage_rate, memory usage.
layer: application
category: os-ops
lifecycle: operations
tags:
  - sysom
  - inspection
  - ecs
  - memory
  - diagnosis
status: beta
---

# SysOM Inspection (`sysom-inspection`)

Inspections are launched with the `sysom-osops` CLI command
(`sysom-osops inspection ecs ...`). Always go through the CLI instead of calling
the inspection OpenAPI directly.

## CLI Setup

Check whether the CLI is available:

```bash
command -v sysom-osops
```

If it is missing, install it:

```bash
curl -fsSL --connect-timeout 1000 https://sysom-prd-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/sysom_prd/skill_cli/install.sh | sudo bash
```

Then verify only the binary:

```bash
command -v sysom-osops
```

If the CLI is installed but has no `inspection` subcommand yet, run
`sysom-osops update` first, then retry.

If a command fails due to missing RAM permissions, follow
`references/ram-policies.md` to attach the minimum permission policy.

## Quick Start

```bash
# Focused inspection by intent (--query)
# Run only CPU/load related items (keyword mapping)
sysom-osops inspection ecs --region cn-shenzhen --instance i-xxxxxxxx --query "cpu related inspection"

# Combined intent: memory and disk
sysom-osops inspection ecs --region cn-shenzhen --instance i-xxxxxxxx --query "memory and disk"

# Natural-language sentence: intent is extracted automatically, matching packet-loss items
sysom-osops inspection ecs --region cn-shenzhen --instance i-xxxxxxxx --query "check whether this machine has network packet loss"

# If the query matches no items, it falls back to a full inspection automatically

# Batch inspection (--scope-type batch, auto diagnosis supported)
# Inspect all specified instances -> auto root-cause diagnosis on the Top-3 most severe
# anomalous instances -> LLM summary (the rest get copy-ready deep-dive commands in the report)
sysom-osops inspection ecs --region cn-shenzhen --scope-type batch --instances i-aaa,i-bbb,i-ccc

# Region-wide inspection (--scope-type all, auto diagnosis supported)
# Auto-discover every ECS instance in the region (limit 5000) -> Top-3 anomalies auto-diagnosed
# -> LLM summary; one command for the full closed loop
sysom-osops inspection ecs --region cn-shenzhen --scope-type all

# Re-check an existing report (--report-id)
# Returns immediately without re-running (auto-generated in inspection next_steps)
sysom-osops inspection ecs --report-id inspection-82a64d9d-11c5-45b2-a81c-27fc754891e8
```

## Invocation Modes

- **Focused inspection:** `--query "<intent>"` maps keywords or extracted intent to concrete
  items (CPU/load keyword mapping, combined intents such as memory + disk, natural-language
  sentences such as network packet-loss checks). A query matching no items falls back to a
  full inspection automatically.
- **Batch:** `--scope-type batch --instances i-aaa,i-bbb,...` inspects all specified instances,
  auto-diagnoses the Top-3 most severe anomalous ones, and lists copy-ready deep-dive commands
  for the rest in the report.
- **Region-wide:** `--scope-type all` auto-discovers every ECS instance in the region
  (limit 5000), then applies the same Top-3 auto-diagnosis and LLM summarization in one command.
- **Report replay:** `--report-id <reportId>` returns the existing report immediately without
  re-running the inspection; inspection results emit this replay command in `next_steps`
  automatically.

## Observability

- **UA template (required for all SDK requests):**
  - `AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`
  - Runtime resolved form in this skill: `AlibabaCloud-Agent-Skills/alibabacloud-alinux-sysom-inspection/<SKILL_SESSION_ID>`
- **Unified session-id rule:**
  - A single session-id is generated once per session (one CLI execution) and must be
    reused consistently across all API calls, both CLI and SDK requests.
  - Generation priority: external env `SKILL_SESSION_ID` (preferred) -> auto-generated
    fallback `sid-<32-char hex>` (uuid4 hex); invalid injected values fall back to the
    generated id.
  - Accepted format: `[A-Za-z0-9][A-Za-z0-9._:-]{7,127}`.
  - The resolved value is exported to process env `SKILL_SESSION_ID` so downstream calls
    stay consistent.
- The `sysom-osops` CLI injects the UA header automatically and follows the same unified
  session-id rule.

## Execution Flow

- Before each inspection, the CLI verifies SysOM activation and permissions (`InitialSysom`,
  `source=skill_hub`); activation and installation prompts are handled by the CLI itself.
- Every new inspection calls ROA API `POST /api/v1/inspection/createInstanceInspection` with
  `source=skill_hub`; selected items come from `--query` keyword/intent mapping, and a query
  matching no items falls back to a full inspection.
- Each mode runs a full closed loop: inspect (metrics + logs) -> automatic root-cause diagnosis
  on detected anomalies -> LLM-summarized Chinese report.
- Automatic root-cause diagnosis is triggered via `InvokeDiagnosis` (injecting
  `__sysom_diagnosis_source=skill_hub` into `params`) and polled via `GetDiagnosisResult`
  until `success` / `fail` / timeout.
- Batch (`--scope-type batch --instances ...`) inspects every specified instance; region-wide
  (`--scope-type all`) auto-discovers all ECS instances in the region (limit 5000). Both
  automatically diagnose the Top-3 most severe anomalous instances and include copy-ready
  deep-dive commands for the remaining ones in the report.
- Report lookup uses ROA API `GET /api/v1/inspection/getInspectionReport`; the CLI polls until
  the report succeeds or times out.
- `--report-id <reportId>` skips task creation and directly fetches the existing report;
  inspection results also emit this replay command in `next_steps` automatically.
- Local threshold/event-rule configuration is not used; anomaly decisions come from the
  server-side inspection report.

## Error Handling

When a CLI invocation fails, classify the failure by the error text (`Error: <Code>: ...`)
and handle it as follows instead of blind retries:

- **Permission (`Forbidden.RAM`)**: explain that `sysom:InitialSysom` /
  `sysom:InvokeAgentCli` is missing and point the user to `references/ram-policies.md`
  for the minimum policy; do not retry.
- **Parameter (`InvalidParameter`, invalid argument)**: identify the offending argument
  and guide the user to verify the instance id and region; do not attribute it to the
  service.
- **Throttling (`Throttling`)**: tell the user the request was rate-limited and advise
  retrying later; do not retry automatically in a loop.
- **Internal (`InternalError`)**: report the temporary service failure honestly and
  suggest retrying later; do not attribute it to user input.
- **Empty region (`no ECS instances found`)**: not an error. Report that the region has
  no ECS instances and skip the inspection; never fabricate a report.

## Extensibility Notes

- Inspection focus is controlled by `--query` (keyword/intent mapping to concrete items);
  unmatched queries fall back to a full inspection.
- Use `--scope-type batch --instances ...` for batch inspection and `--scope-type all` for the
  whole region (limit 5000 instances); both auto-diagnose the Top-3 most severe anomalies.
- Use `--report-id` to re-check an existing report without re-execution; the replay command is
  emitted automatically in inspection `next_steps`.
- A local Python CLI (`./scripts/osops.sh inspection`) is kept only as a fallback for
  environments where `sysom-osops` is unavailable.
- Memory anomaly trigger logic of the fallback path stays implemented in
  `scripts/sysom_cli/inspection/command.py`.
- To add more post-inspection specialized diagnosis actions, reuse the `InvokeDiagnosis`
  integration pattern.
