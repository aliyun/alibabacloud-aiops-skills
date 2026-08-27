---
name: alibabacloud-waf-report
description: Generate or review Alibaba Cloud WAF 3.0 security operations reports, customer assessments, rule-tuning reports, and focused false-positive or false-negative investigations using WAF OpenAPI, SLS traffic logs, authorized read-only verification, or user-supplied offline WAF samples and exports. Use for WAF monthly reports, security patrols, API Security reviews, BOT analysis, and OWASP API Security Top 10 coverage. Do not use for unauthorized testing or direct production rule changes.
---

# Alibaba Cloud WAF Security Operations Report

Produce an evidence-based WAF security operations report or focused assessment. Separate observed facts, technical inferences, and unverified assumptions. Optimize protection effectiveness and business accuracy rather than maximizing block volume.

## Scope and authorization

Inspect the material already provided and ask only for missing inputs that affect execution:

- Customer name, report type, assessment interval, and time zone
- Alibaba Cloud region, WAF instance ID, SLS project, and logstore
- An existing authenticated aliyun CLI context or offline exports
- Main domains, sensitive business flows, trusted sources, partner callbacks, and approved test sources
- Known false positives, known false negatives, recent changes, and requested output format
- Authorization scope for read-only cloud queries and public endpoint verification

Use only the aliyun CLI default credential chain or an already configured profile. Never request, inspect, print, persist, transform, or pass AccessKey credentials. Redact cookies, tokens, AccessKeys, phone numbers, government identifiers, and other sensitive values from artifacts.

Default to read-only collection and analysis. Changing WAF rules, allowlists, blocklists, BOT policies, or logging settings is a separate write operation and requires explicit user approval for the exact change.

Check whether SLS retention covers the requested interval. If coverage is incomplete, analyze the available data but state the coverage ratio, missing interval, and impact on conclusions. Never interpret missing data as no risk.

Choose the execution mode from the supplied evidence:

- **Offline analysis:** When the user supplies exports, fixtures, or summarized evidence and requests offline analysis, do not call cloud APIs, the aliyun CLI, `curl`, or other network services. Analyze only the supplied evidence, preserve its stated scope, and mark unsupported conclusions `unverifiable`.
- **Online collection:** Use the authenticated read-only workflow only when the task requires live evidence and the required cloud context is available.

Match collection depth to the requested deliverable. A focused configuration inventory, API Security review, BOT analysis, report review, or false-positive investigation must not expand into an unrelated full assessment. Run the complete WAF, API Security, SLS, 20-category, and OWASP workflow only for a full assessment or when the user explicitly requests that coverage.

For a focused offline rule-tuning, false-positive, or false-negative investigation based on supplied samples, use the samples directly. Read only the assessment methodology, produce the requested compact analysis, and stop. Do not load the 20-category checklist, OWASP guide, SLS cookbook, or full report template unless the user explicitly requests that broader coverage.

## Load references progressively

Read only the reference needed for the current phase:

- Before constructing cloud commands, read [OpenAPI and SLS command reference](references/openapi-cheatsheet.md) and [required RAM permissions](references/ram-policies.md). Current plugin help and official API documentation take precedence over examples.
- For baseline statistics, attack checks, or BOT analysis, read [SLS query cookbook](references/sls-query-cookbook.md). Adapt every query to the actual fields, indexes, and interval.
- Before classifying a risk, false positive, or false negative, read [assessment methodology](references/methodology.md). For a focused supplied-sample investigation, this is the only required reference.
- Before an explicitly requested 20-category attack-surface analysis, read [attack analysis checklist](references/attack-analysis-checklist.md) completely and record coverage, findings, and evidence gaps for all 20 categories.
- For an explicitly requested OWASP API Security Top 10 analysis, read [OWASP API query guide](references/owasp-api-top10-queries.md).
- For a full assessment report, copy and fill [report template](assets/report-template.md). Do not load the template for a focused investigation unless the user requests the full report structure, and never modify the template source.

## Observability

All outbound requests in one assessment must use one consistent identifier.

### User-Agent template

Every `curl` request must use this exact format:

```text
AlibabaCloud-Agent-Skills/alibabacloud-waf-report/{session-id}
```

Example:

```bash
curl -sS --connect-timeout 5 --max-time 10 \
  -A "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}" \
  "https://ipinfo.io/192.0.2.1/json"
```

### Session-ID convention

- Generate one 32-character lowercase hexadecimal ID at the start of the assessment with `openssl rand -hex 16`.
- Store it in `SESSION_ID` and reuse it for every `curl` request, CLI request annotation, and evidence log in that assessment.
- Never create a new session ID for retries, pagination, or parallel collection within the same assessment.
- For aliyun CLI commands that support it, append `--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-report/${SESSION_ID}"`.

## Collect and preserve evidence

Prefer user-provided exports. For online collection, use only lowercase-hyphenated aliyun CLI plugin-mode commands within the authorized scope. Do not use PascalCase RPC-style commands.

For a full assessment, collect and record all applicable evidence below. For a focused task, collect only the requested evidence and its direct prerequisites:

1. WAF instance capabilities, protected domains, and defense templates.
2. Defense rules by type, including action, scope, pagination, and last modification time.
3. API Security events, risks, matched hosts, and rules, with page-count reconciliation.
4. SLS baselines for volume, host, action, rule, source, time, path, status, and response size.
5. BOT actions, scene IDs, user agents, sources, and path distributions.

Retain raw responses or reproducible queries. Label every evidence item with its source, time interval, query or command, collection time, and session ID. Never invent instance IDs, rule IDs, fields, or page counts.

## Analyze findings

For a full online assessment, establish the traffic baseline before reviewing rules, Web attacks, API Security, OWASP API Security Top 10, and BOT behavior. For a full assessment or an explicitly requested coverage review, every one of the 20 attack categories and all ten OWASP items must have a result. For a focused task, evaluate only the supplied or requested categories and direct dependencies; do not run or simulate a baseline when the user supplied complete offline samples. Label unrelated areas `outside requested scope` without extra queries. If current data cannot support a requested conclusion, mark the item `not covered` or `unverifiable` and name the required evidence.

For each candidate finding, record:

| Field | Requirement |
| --- | --- |
| Classification | Attack probe, suspected attack, blocked attack, possible false negative, or legitimate traffic incorrectly blocked |
| Severity | P0, P1, P2, or observation, with rationale |
| Evidence | URI, method, time, source, user agent, parameter or body signature, status, response size, rule, and action |
| Data scope | Source, query, start and end time, sample size, and missing fields |
| Confidence | High, medium, or low, with remaining assumptions |
| Recommendation | Least-scoped action, validation metric, observation period, and rollback condition |

Traffic share, QPS, path concentration, and user agent are investigation signals, not proof of malicious or legitimate behavior. Validate partner, office egress, cloud-provider, mobile, and proxy traffic against business ownership and request behavior; do not classify traffic from ASN alone.

## Perform authorized verification

Verify only domains and paths owned by or explicitly authorized by the user. Default to side-effect-free GET or HEAD requests with `--connect-timeout 5 --max-time 10`. Do not send exploit payloads, trigger state changes, enumerate objects, bypass authentication, or generate load.

Record status, content type, and only the minimal redacted response excerpt needed for evidence. A `200` response may be an SPA fallback page; `401`, `403`, or `405` does not prove the authenticated path is safe.

Use four questions to reassess a suspected false positive:

1. Does the endpoint have real successful calls after authentication?
2. Can the alert signature appear only after login or on an internal network?
3. Is there object-level, function-level, or credential-scope risk?
4. Can the endpoint or leaked information form an attack chain?

If verification requires a real business token, a write request, or offensive testing, stop that online check and provide a minimal validation plan for separate approval.

## Generate the report

For a full assessment, use `assets/report-template.md` as the report skeleton, match the user's requested language, keep the ten main chapters, and include data coverage and limitations, traceable P0/P1/P2 findings, API Security and BOT analysis, the 20-category and OWASP coverage matrices, a prioritized action plan, validation metrics, observation periods, rollback conditions, a false-positive archive, and reproducible queries.

For a focused investigation, do not use the full report template. Output only the supplied evidence, classification, confidence, missing evidence, and least-scoped validation or remediation steps. Do not add unrelated matrices, chapters, or collection phases.

Use Markdown pipe tables. Cite verifiable sources for external facts. Label unsupported external claims as technical inference rather than fabricating official wording or URLs.

## Completion checks

- Confirm the interval, time zone, pagination totals, retention coverage, and evidence gaps.
- For a full assessment or explicit coverage review, confirm all 20 attack categories and all ten OWASP items have conclusions or explicit missing-data notes.
- Confirm every risk, false positive, and false negative has traceable evidence and a confidence level.
- Confirm sensitive values are redacted and no credentials or full tokens appear in artifacts.
- Confirm recommendations use the narrowest practical exception and include validation, observation, and rollback.
- Confirm every outbound request uses the same session ID, required User-Agent, and a bounded timeout.
- If a RAM action is denied, identify the exact missing read permission from `references/ram-policies.md`; continue only with unaffected evidence and mark blocked checks unverifiable.
