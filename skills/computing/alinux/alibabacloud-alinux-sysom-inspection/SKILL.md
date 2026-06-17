---
name: alibabacloud-alinux-sysom-inspection
version: 0.1.0
description: Inspect ECS instance health, detect anomalies in memory, disk, CPU, load, and resource leaks, and automatically trigger deep diagnosis when critical memory issues are detected. Suitable for routine inspections, troubleshooting, and risk warning scenarios. Trigger keywords: SysOM, inspection, instance diagnosis, memory_usage_rate, memory usage.
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

Run `./scripts/osops.sh` from the skill root directory.

Currently implemented command:
- `inspection`

## Quick Start

```bash
cd <alibabacloud-alinux-sysom-inspection>
./scripts/init.sh
./scripts/osops.sh inspection \
  --region-id cn-hangzhou \
  --managed-type all
```

## Observability

- **UA template (required for all SDK requests):**
  - `AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`
  - Runtime resolved form in this skill: `AlibabaCloud-Agent-Skills/alibabacloud-alinux-sysom-inspection/<SKILL_SESSION_ID>`
- **Unified session-id rule:**
  - A single `SKILL_SESSION_ID` must be reused across all API calls in one CLI execution.
  - Injection priority is: external env `SKILL_SESSION_ID` (preferred) -> auto-generated fallback `sid-<uuid4>`.
  - Accepted format is `[A-Za-z0-9][A-Za-z0-9._:-]{7,127}`; invalid injected values fall back to generated id.
  - The resolved value is exported to process env `SKILL_SESSION_ID` to keep downstream calls consistent.

## Execution Flow

- Before each inspection, the CLI calls ROA API `POST /api/v1/openapi/initial_sysom` (`source=skill_hub`) to verify permissions and SysOM activation.
- If SysOM is not activated or role readiness is missing, the CLI interactively asks whether to continue with activation + installation.
- After user confirmation, it calls `InitialSysom(check_only=false, source=skill_hub)` for activation, then calls `InstallAgentWithType`.
- After installation, it re-checks readiness using `InitialSysom(check_only=true, source=skill_hub)`. Inspection continues only when re-check succeeds.
- Local threshold/event-rule configuration is not used; anomaly decisions come from the server-side inspection report.
- If `--instance-id` is not provided, the CLI calls `ListAllInstances` (`region` / `instanceType=ecs` / `managedType` / `current` / `pageSize`) and lets the user pick an instance interactively.
- It always calls ROA inspection API `POST /api/v1/inspection/createInstanceInspection` with `source=skill_hub`, and supports optional `metricSource` (`cms` / `sysom` / `auto`).
- If `--metric-source` is not explicitly provided, the CLI maps automatically from management status: `managed -> sysom`, `unmanaged -> cms`, `unknown -> auto`.
- To inspect all items, pass `items=[]` (in CLI, provide an explicit empty `--inspection-items`).
- If the standard inspection API returns `InvalidAction.NotFound`, the CLI marks the API as unavailable and stops follow-up flow to avoid invalid retries.
- Report lookup uses ROA API `GET /api/v1/inspection/getInspectionReport`.
- If create API is unavailable, the CLI still sends one `GetInspectionReport` probe call and records the result for observability.
- If report contains `sysom:metric:memory_usage_rate` anomaly, the CLI automatically triggers `InvokeDiagnosis` for `memgraph`.
- `InvokeDiagnosis` injects `__sysom_diagnosis_source=skill_hub` into `params` and validates business `code=Success`.
- After diagnosis is started, the CLI polls `GetDiagnosisResult` until `success` / `fail` / timeout.
- Auto diagnosis can be disabled via `--disable-memgraph-diagnosis`.

## Extensibility Notes

- Inspection items can be overridden via `--inspection-items`.
- Instance filtering can be controlled by `--managed-type` (`managed` / `unmanaged` / `all`) and pagination args `--current`, `--page-size`.
- Metric source can be specified via `--metric-source` (`cms` / `sysom` / `auto`); if omitted, default behavior is preserved.
- If `InitialSysom` indicates not activated, the CLI asks for terminal confirmation before activation attempt + recheck.
- Memory anomaly trigger logic is implemented in `scripts/sysom_cli/inspection/command.py`.
- To add more post-inspection specialized diagnosis actions, reuse the `InvokeDiagnosis` integration pattern.
