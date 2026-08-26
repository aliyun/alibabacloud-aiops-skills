---
name: alibabacloud-actiontrail-diagnosis
description: |
  Read-only query and diagnosis of Alibaba Cloud ActionTrail operation audit events: find out who performed which operation, when, from which source IP, and on which resource, across one or many regions, rendered as a 12-column event table or machine-readable JSON. Use when the user asks about the audit log or operation history of an Alibaba Cloud account; wants to know who changed, created, deleted, or operated on a resource; asks when a resource was operated on; needs to trace read/write operation records, console sign-ins, or API calls of a cloud service; or wants to investigate suspicious or failed operations recorded by ActionTrail. Triggers: audit log, operation history, operation records, who changed, who operated, who deleted, when was it operated, action history, read/write operations, ActionTrail, audit event, operation trace.
---

# ActionTrail Diagnosis

## Absolute Rules — read before doing anything

1. **Strictly READ-ONLY. Never write.** Under NO circumstances execute any command or API call that mutates state (`Create*`, `Update*`, `Modify*`, `Delete*`, `Disable*`, `Set*`, `Start*`, `Stop*`, …). This skill only queries ActionTrail audit events and the caller identity; any write-API attempt is a hard failure.
2. **Never output credentials.** Never print, cat, or quote credential files (`~/.aliyun/config.json`), environment variable values, AccessKey pairs, or STS tokens. Reference credential fields by name only; do not echo secrets into the conversation or the report.
3. **Ask before running when information is insufficient.** If a required input (region, time range, target product/event) is missing and cannot be safely defaulted, ask the user first — do NOT guess and run wide, unfiltered queries. UID is the only input that may always be auto-derived (see Information Completeness).
4. **Output must be based on real API returns. Never fabricate.** Every event, count, operator, timestamp, or error in the answer must come from the script's actual output. Empty results are a valid finding — report them truthfully; never invent events, fill gaps from imagination, or claim operations happened without evidence.

## Overview

This skill queries the Alibaba Cloud ActionTrail `LookupEvents` API in read-only mode to retrieve operation audit events for an account, with multi-region batch querying, automatic pagination, flexible time input (ISO8601 UTC or Beijing time), server-side filtering via `LookupAttribute`, and client-side refinement filters. The single entry script `scripts/lookup_events.py` handles credential routing, retries, error degradation, and result rendering.

## Orchestration

Products involved: **STS** (caller identity) and **ActionTrail** (audit events). Every diagnosis follows one fixed call order, executed by `scripts/lookup_events.py`:

1. **STS `GetCallerIdentity`** — always called first and unconditionally, even when `--uid` is supplied, so the effective account is known and can be cross-checked.
2. **Region resolution** — `--region all` expands to the built-in common region list; a global-service `ServiceName` overrides the request and pins the query to `cn-hangzhou`.
3. **ActionTrail `LookupEvents`** — called once per resolved region, paginated via `NextToken` until exhaustion or the per-region page cap.
4. **Client-side refinement** — `--filter-event` / `--filter-resource-type` are applied to the merged event set after all regions return.
5. **Rendering** — the 12-column table plus the Friendly Summary, or the `--json` contract.

Decision criteria that drive the orchestration:

| Decision | Criterion |
|---|---|
| Whether to derive the UID | `--uid` absent → use the STS-derived value; present but different → emit the account-mismatch warning and continue on the credential's account |
| Which regions to query | Explicit region list; `all` → built-in common regions; global `ServiceName` → forced to `cn-hangzhou` regardless of `--region` |
| Server-side vs client-side filtering | `ServiceName` / `EventRW` / `EventName` / `ResourceName` / `Username` go to `LookupAttribute` (max 2, AND); substring and resource-type narrowing happen client-side afterwards |
| When to stop paginating | No `NextToken`, or the per-region page cap is reached → mark `truncated` and guide the downgrade steps |
| How a failure is handled | Transient (429 / 5xx / network) → retried with backoff; other 4xx → not retried; one region failing → `partial=true` plus `failed_regions`, the run continues |
| Which output channel | Non-technical reader → Friendly Summary first; downstream agent → the full `--json` contract |

## Quick Start

```bash
python3 scripts/lookup_events.py \
    --region cn-hangzhou \
    --start-time '2026-07-01 00:00:00' --end-time '2026-07-02 23:59:59' \
    --lookup-attribute 'ServiceName=Vpc' --lookup-attribute 'EventRW=Write'
```

Minimal runnable form: one region, a narrow time window, and up to two `--lookup-attribute Key=Value` filters. `--uid` is omitted here and auto-derived from the active credential. Prefer narrow time windows and precise attributes over broad scans.

## User Confirmation / Information Completeness

| Input | Required | Notes |
|---|---|---|
| `--region` | YES | One or more region ids, or `all`. Global services (Cen, Ram, Ims, Cdn, ResourceManager, AasCustomer, AasSub) are automatically pinned to `cn-hangzhou`. |
| Time range (`--start-time` / `--end-time`) | YES in practice | Ask the user when missing; ActionTrail defaults to recent days, but an explicit window keeps results focused. Values without a timezone are treated as Beijing time. |
| Product / event target (`--lookup-attribute`) | YES in practice | Ask which cloud service, event name, resource, or user to focus on; avoid unfiltered account-wide scans. Keys and values are case-sensitive; at most 2 conditions, combined with AND. Rules in [lookup-attribute.md](references/lookup-attribute.md). |
| `--uid` | NO | Auto-derived via STS `GetCallerIdentity` when omitted (5-25 digits). If the provided `--uid` differs from the credential's UID, the script prints an ACCOUNT MISMATCH WARNING — surface it explicitly to the user. |

Missing a required item → restate what is known, ask the user, and wait. Never silently expand scope beyond the confirmed region/time/product.

## CLI Options

| Option | Description |
|---|---|
| `--uid <UID>` | Optional. Account UID (5-25 digits); auto-derived via STS GetCallerIdentity when omitted. |
| `--region <id> [<id> ...]` | Required. One or more region ids; `all` expands to the built-in common regions. Global services are pinned to `cn-hangzhou`. |
| `--start-time <time>` / `--end-time <time>` | Optional. ISO8601 UTC (`2026-07-02T08:19:40Z`) or Beijing time (`2026-07-02 16:19:40`); values without a timezone are treated as Beijing time. |
| `--max-results <n>` | Optional. Results per page, 1-50, default 50. |
| `--direction <BACKWARD\|FORWARD>` | Optional. Sort direction; default `BACKWARD` (newest first). |
| `--lookup-attribute Key=Value` | Optional, repeatable up to 2. Server-side filter, AND semantics, case-sensitive. |
| `--json` | Optional. Emit raw JSON for agent consumption (sensitive fields masked). |
| `--summary` | Optional. Append a one-line summary (total, success/failed counts, top operators). |
| `--filter-event <keyword>` | Optional, repeatable. Client-side eventName substring filter (case-insensitive, ORed). |
| `--filter-resource-type <type>` | Optional. Client-side exact match on referencedResources resource type, e.g. `ACS::VPC::EIPAddress`. |
| `--profile <name>` | Optional. Credential profile passed through to the OpenAPI backend. |

## Output Specification

Default output is a Markdown table with exactly these 12 columns, in this order: `Event Time (Beijing) | Event Name | Event ID | Cloud Service | Event Source | Region | Operator (Type) | Read/Write | Event Type | Source IP | Role Session | Related Resources`. Failure events are marked in the Related Resources column with `❌` plus an error label (a non-empty `errorCode` yields that code; a non-empty `errorMessage` alone yields `Failed`). After the table (and any truncation warning), table mode always appends a **Friendly Summary** — plain English, plain text, at most 20 lines, computed from the actual result — with four fixed sections: `## Query Scope` (account UID with provided/derived source, regions checked, human-readable Beijing-time window, plain-language translation of the filters), `## Key Findings` (total events, read/write breakdown, top 3 operators, top 3 services, failed-operation count; for zero events it states that no matching events were found in this scope plus one likely reason), `## Points to Note` (only when applicable: truncation, partial region failures, account mismatch, unrecognized ServiceName, global-service pinning — each explained in non-technical terms), and `## Suggested Next Steps` (1–3 actionable recommendations derived from the actual result state). The Friendly Summary is written for non-technical readers and goes through the same masking as the table. With `--summary`, only the one-line summary is appended instead of the Friendly Summary; with `--json`, no Friendly Summary is emitted.

With `--json`, the top-level contract fields are: `success`, `partial`, `failed_regions`, `truncated`, `events`, `total_count`, `start_time`, `end_time`, `pages`, `regions`, `per_region`, `uid`, `uid_source`, `lookup_attributes`, `direction`. `uid` is the effective account UID and the only intentionally plaintext identifier in the JSON — UIDs embedded inside `events` (accountId / principalId / ARN) remain masked; `uid_source` is `provided` when `--uid` was passed explicitly and `derived` when the UID was resolved via STS GetCallerIdentity. `lookup_attributes` is the effective `Key=Value` filter list after malformed entries were dropped, and `direction` is the sort direction — together with `uid` / `regions` / `start_time` / `end_time` they make the JSON fully self-describing so a downstream agent can reproduce or continue the query. When `--start-time` / `--end-time` are omitted, `start_time` / `end_time` echo the effective query window reported by the LookupEvents response (ISO8601 UTC), degrading to the placeholder wording only if the API echoes no window; explicitly provided times are reported as their normalized UTC values.

Output red lines:

1. **The Operator (Type) column must NEVER display `accountId`.** The only exception is the script's own fallback for a root-account event whose `principalId` is missing — do not add accountId to the table yourself in any other case.
2. **`AccessKeyId` and `requestParameters` are NOT displayed by default.** Show them only when the user explicitly asks, and extract them verbatim from the raw `--json` output — never invent, guess, or paraphrase them.
3. **The Friendly Summary is the user-facing narrative layer.** It may be paraphrased, condensed, or made more conversational when presented to the user, but its facts must never be altered, invented, or padded into long-form analysis beyond what the result supports. `--summary` mode remains a single line.

When `truncated` is true, results are incomplete — do NOT present them as exhaustive. Guide the user through three downgrade steps, in order:
1. Narrow the time window (`--start-time` / `--end-time`).
2. Add more precise `--lookup-attribute` conditions (e.g. `EventRW=Write`, a specific `EventName` or `ResourceName`).
3. For long-term or full-volume audit needs, recommend delivering ActionTrail events to SLS (Log Service) instead of querying the event API.

`_queryRegion` is a private provenance field injected by the script into every event; it is not displayed by default. Render it — read from the `--json` output — only when the user explicitly asks to group events by the actual query region.

## Reporting to Mixed Audiences

The output serves two audiences at once. For end users (often non-technical), present the Friendly Summary first — paraphrasing or further colloquializing it is encouraged — and never hand the raw 12-column table to a non-technical user as the only answer. For a downstream agent or the next diagnosis stage, pass the complete `--json` contract (`uid`, `regions`, `start_time` / `end_time`, `lookup_attributes`, `direction`, `per_region`, `events`) so the query can be reproduced or continued verbatim. Keep the two channels separate: human-readable narrative from the Friendly Summary, machine-readable context from `--json`.

## References

- [service-mapping.md](references/service-mapping.md) — map user-facing product names to the exact ActionTrail ServiceName values.
- [lookup-attribute.md](references/lookup-attribute.md) — all supported LookupAttribute keys, valid two-condition combinations, and case-sensitivity rules.
- [api-reference.md](references/api-reference.md) — LookupEvents request/response field semantics and event structure.
- [network-events-catalog.md](references/network-events-catalog.md) — catalog of common network-product event names for tracing typical operations.
- [ram-policies.md](references/ram-policies.md) — the minimum read-only RAM policy (`actiontrail:LookupEvents` + `sts:GetCallerIdentity`).

## Prerequisites

Aliyun CLI 3.x installed and configured (recommended), or credentials provided via environment variables / `~/.aliyun/config.json`; the script falls back to direct signed HTTPS calls when the CLI is unavailable. Python dependencies: `pip install -r scripts/requirements.txt`. Read-only credentials per [ram-policies.md](references/ram-policies.md).

## Error Handling

- **Transient failures (throttling / 429, 5xx, network):** retried automatically with backoff; do not invent manual retry paths.
- **Per-region failures:** a single region failing degrades to `per_region.<region>.error` and `failed_regions`; the run continues for other regions (`partial=true`). Report the failed regions and their errors honestly alongside the successful results.
- **ACCOUNT MISMATCH WARNING:** when `--uid` does not match the credential's account, results reflect only the credential's account and may be empty. Surface the warning verbatim to the user; empty results do NOT prove "nothing happened" in the requested account.
- **Credential resolution failure:** if `--uid` is omitted and cannot be derived, the script exits with an explicit error — ask the user for `--uid` or valid credentials.
- **Exit codes (identical in table and `--json` mode):** `0` = success or partial success (at least one region succeeded; `partial=true` / `failed_regions` carry the degraded parts), `1` = all queried regions failed or a fatal error, `2` = invalid arguments.

## Observability

Every Alibaba Cloud API call this skill makes carries a User-Agent for server-side audit correlation:

- **UA template:** `AlibabaCloud-Agent-Skills/{skill-name}/{session-id}` — here `{skill-name}` is `alibabacloud-actiontrail-diagnosis`.
- **session-id:** a 32-character lowercase-hex string, generated once per process run and shared unchanged by every call in that run (both the CLI backend and the HTTP fallback), so all calls of one diagnosis correlate.
- **Inheritance:** set the environment variable `ACTIONTRAIL_SESSION_ID` to a valid 32-hex value to make a parent process and the script share one session-id; otherwise a fresh id is generated automatically. No manual configuration is required.
