---
name: alibabacloud-mining-attack-diagnosis
description: |
  Alibaba Cloud Security Center cryptomining (cryptojacking) diagnosis skill.
  Use when the user reports or suspects a mining infection, receives a mining
  alert, or asks for mining alert detection, IOC extraction (pool IPs,
  malicious domains, sample hashes, malicious processes), affected-asset
  scoping, attack-surface analysis, entry-vector analysis, risk assessment,
  prioritized remediation reporting, cryptomining incident response, or
  mining risk detection. Triggers: "mining", "cryptomining",
  "cryptojacking", "coin mining", "coin-mining", "miner", "mining alert",
  "mining alerts", "mining pool", "pool IPs", "malicious domains",
  "sample hashes", "malicious processes", "mining IOC", "IOC extraction",
  "mining alert detection", "affected-asset scoping",
  "attack-surface analysis", "entry-vector analysis", "risk assessment",
  "prioritized remediation reporting", "cryptomining incident response",
  "mining risk detection", "xmrig", "kdevtmpfsi", "kinsing", "sysrv",
  "minerd", "Security Center", "ECS high CPU mining"
---

# Mining Attack Diagnosis (Read-Only)

## Absolute Rules

1. **CRITICAL — MANDATORY EXECUTION:** You **MUST** run the investigation via the entry script `scripts/mining_investigation.py`. Do **NOT** hand-write bash/python, do **NOT** issue individual `aliyun` CLI calls, do **NOT** skip any step. If the script fails or times out, **re-run it once** before falling back — never abandon the 6-step SOP. The entry script internally invokes **every** Step 1–4 API (`DescribeSuspEvents`, `DescribeAlarmEventDetail`, `DescribeSuspEventDetail`, `DescribeSecurityStatInfo`, `DescribeFieldStatistics`, `DescribeExposedInstanceList`, `DescribeVulList`) regardless of intermediate results, and auto-retries transient `ServiceUnavailable`/`Throttling`/`InternalError` responses — so you must **not** pre-empt or short-circuit it with ad-hoc calls.
2. **ABSOLUTE PROHIBITION (read-only enforcement):** Under **NO** circumstances may you generate, write, or execute any command/script calling a mutating API (`Update*`/`Delete*`/`Disable*`/`Modify*`/`Create*`/`Rotate*`/`Set*`/`Operate*`) — e.g. `OperateSuspiciousTargetBatch`, `ModifySecurityGroupRule`, `DeleteInstance`. This includes scripts "for the user to run manually". If the user asks to quarantine/kill/isolate, only output the manual remediation workflow and declare this skill is read-only.
3. **MANDATORY OUTPUT FORMAT:** When mining is confirmed, the report **MUST** start with the URGENT banner (see Report Output section); the Conclusion section **MUST** include the 4-phase remediation workflow verbatim. Partial output is forbidden.
4. **EXECUTION RULE FOR ERRORS:** On any API error, log `[WARN] <error>` to stderr and continue to the next step — never silently skip. On `Forbidden`/`NoPermission`, record the missing permission and continue. On empty results, set fields to N/A and proceed. On transient errors (`ServiceUnavailable`/`Throttling`/`InternalError`), the entry script retries automatically — do not conclude "service down" from a single failed call.
5. **INFORMATION COMPLETENESS (auto-fill first, ask second):** When the user omits the account UID or region but the request intent is clear (e.g. only an API fragment like "describe susp"), do **NOT** stall asking for what can be derived — auto-derive the UID via `sts:GetCallerIdentity` (the entry script does this when `--account` is omitted), use the default region `cn-hangzhou`, **state the derivation explicitly in your reply and in the report metadata** ("account auto-derived via STS"), then run the full investigation. Only ask a brief clarifying question when the request is too ambiguous to determine the product or investigation goal at all. Never fabricate findings in either path.

## Overview

This skill implements a standard 6-step operating procedure for Alibaba Cloud
cryptomining (cryptojacking) detection and diagnosis. It detects mining alerts
via Security Center (SAS), extracts Indicators of Compromise (IOCs) from alert
detail, scopes the affected assets, detects the attack surface (exposed assets
+ unpatched vulnerabilities) to hypothesize the intrusion entry, assesses risk,
and generates a prioritized handling/remediation report.

**This skill is strictly read-only — it never performs containment,
quarantine, process termination, host isolation, or any handling/mutating
action.** When mining is confirmed it prints a prominent URGENT banner telling
the operator to remediate manually.

## 6-Step Detection & Diagnosis SOP

```
Mining Attack Detection & Diagnosis — SAS Public API
            |
            v
  +-----------------------------------------------+
  | Step 1: Mining Alert Detection                 |
  |   Action: SAS DescribeSuspEvents                 |
  |   Filter: mining keywords (xmrig/mining-pool/...)   |
  |   Output: mining alerts, affected assets, level |
  +-----------------------------------------------+
            |
            v
  +-----------------------------------------------+
  | Step 2: Alert Detail & IOC Extraction          |
  |   Action: DescribeAlarmEventDetail /            |
  |           DescribeSuspEventDetail               |
  |   Output: pool IPs/domains, sample MD5/SHA256,  |
  |           malicious process/command indicators  |
  +-----------------------------------------------+
            |
            v
  +-----------------------------------------------+
  | Step 3: Affected Asset Scope                   |
  |   Group alerts by asset (uuid/name/IP)          |
  |   + DescribeSecurityStatInfo / FieldStatistics  |
  |   Output: blast radius, spread assessment       |
  +-----------------------------------------------+
            |
            v
  +-----------------------------------------------+
  | Step 4: Attack Surface Detection               |
  |   Action: DescribeExposedInstanceList +         |
  |           DescribeVulList (asap)                |
  |   Output: likely intrusion entry vector         |
  +-----------------------------------------------+
            |
            v
  +-----------------------------------------------+
  | Step 5: Risk Assessment                        |
  |   Severity, handled status, spread, entry       |
  +-----------------------------------------------+
            |
            v
  +-----------------------------------------------+
  | Step 6: Handling & Remediation Report          |
  |   IOC table + affected assets + attack surface  |
  |   + P0-P3 prioritized remediation + conclusion  |
  |   Read-only; URGENT banner if mining confirmed  |
  +-----------------------------------------------+
```

## Intent Routing

| User Intent | Action |
|-------------|--------|
| Step 1: Detect mining alerts | Read [references/module1_alert_detection.md](references/module1_alert_detection.md) |
| Step 2: Extract IOCs from an alert | Read [references/module2_alert_detail_ioc.md](references/module2_alert_detail_ioc.md) |
| Step 3: Scope affected assets | Read [references/module3_affected_assets.md](references/module3_affected_assets.md) |
| Step 4: Detect attack surface / entry vector | Read [references/module4_attack_surface.md](references/module4_attack_surface.md) |
| Step 6: Remediation guidance | Read [references/module5_remediation_best_practices.md](references/module5_remediation_best_practices.md) |
| Mining keyword / IOC reference | Read [references/mining_indicators.md](references/mining_indicators.md) |
| End-to-end runtime flow | Read [references/detection_flow.md](references/detection_flow.md) |

## Prerequisites

1. **aliyun CLI 3.x** — required for API access:
   ```bash
   brew install aliyun-cli   # macOS; see https://help.aliyun.com/document_detail/121541.html
   aliyun configure          # stored in ~/.aliyun/config.json
   ```
2. **Credentials** — read-only Security Center (SAS) permissions for the
   Step 1–4 APIs listed in Absolute Rule #1. This skill is strictly read-only:
   it needs no write/mutating permissions and never quarantines, isolates, or
   terminates anything. Full permission list:
   [references/ram-policies.md](references/ram-policies.md).
3. **Python 3.9+** — standard library only, no external dependencies.

## Authentication

Credentials are resolved automatically from the aliyun CLI profile
(`~/.aliyun/config.json`). The scripts never handle or print secrets.

```bash
# Run the investigation
python scripts/mining_investigation.py --account <UID>

# Select a specific profile
python scripts/mining_investigation.py --account <UID> --profile prod
```

## CLI Options

All scripts support `--help`. Common parameters:

- `--account <UID>` — Alibaba Cloud account UID (optional; auto-derived, report label only)
- `--days <N>` — Lookback window in days (default 30)
- `--region <REGION>` — Alibaba Cloud region (default: cn-hangzhou)
- `--format json|markdown` — Report format
- `--output <path>` — Output file (default: `output/mining_report.md`)

Additional pass-through options: `--dealed Y|N|all`, `--profile <name>`
(see [references/detection_flow.md](references/detection_flow.md)).

## Observability

All API calls made by this skill include a `User-Agent` header for
platform-level tracing:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-mining-attack-diagnosis/{session-id}
```

A `session-id` is a 32-character hex string auto-generated per invocation and
attached to every request in the same investigation run; it is logged to
stderr at the start of execution and included in the report metadata.

## Report Output

> **MANDATORY OUTPUT FORMAT:** The report **MUST** follow this structure exactly. When mining is confirmed, the URGENT banner **MUST** appear at the top. The Conclusion **MUST** include the full 4-phase remediation workflow (Phase 1: Preserve & Access → Phase 2: Eradicate & Isolate → Phase 3: Harden → Phase 4: Verify & Recover). Partial or truncated output is forbidden.

Step 6 produces a report with:

1. **Metadata & Severity** — investigation time, account, window, overall severity
2. **URGENT banner** — shown only when mining is confirmed (read-only reminder)
3. **Step 1 — Mining Alerts** — table of matched alerts (level, event, asset, IP, keywords)
4. **Step 2 — IOC table** — mining-pool IPs/domains, sample MD5/SHA256, process/command indicators
5. **Step 3 — Affected Assets** — per-asset alert counts and event names
6. **Step 4 — Attack Surface** — exposed asset count + unpatched vulnerability count
7. **Step 5 — Risk Analysis** — findings (spread, connectivity, entry vector)
8. **Conclusion** — Overview, Intrusion Path & Entry Vector, P0–P3 Remediation

## No-Fabrication Rule

If Security Center returns no mining-matching alerts, report truthfully that no
mining compromise is indicated for the window. Never invent alerts, affected
assets, or IOCs to "complete" a conclusion, and do not print the URGENT banner
in that case.

## Sensitive-Data Handling

- **IOCs are preserved (never masked)** — mining-pool IPs/domains, sample
  hashes, and malicious process names carry forensic value and are needed for
  containment.
- **Account-scoped identifiers are masked** — account UID and asset uuid are
  masked in all output via `_cli.mask_sensitive()`. Set `MINING_NO_MASK=1` to
  emit raw values.
- The AccessKey Secret / security token are used only for signing and are never
  printed or logged.

## Available Scripts

| Script | Type | Description |
|--------|------|-------------|
| `scripts/mining_investigation.py` | Entry | 6-step detection & diagnosis orchestrator |

Standalone step scripts (`scripts/query_*.py`) and internal modules
(`scripts/_cli.py`, `scripts/_constants.py`) are invoked by the entry script;
do not run them directly.

## Error Handling

On any error, log `[WARN] <error>` to stderr and **continue** to the next step
— never silently skip a step or abort the investigation. Transient errors
(`ServiceUnavailable`/`Throttling`/`InternalError`) are auto-retried by the
entry script; permission/parameter errors degrade gracefully with the failed
step recorded in the report. Full error table: see Absolute Rule #4 and
[references/detection_flow.md](references/detection_flow.md).
