---
name: alibabacloud-ak-leak-incident-response
description: |
  Investigate an Alibaba Cloud AccessKey (AK) leakage incident and produce a read-only investigation report. Use when the user reports a leaked / exposed / stolen / compromised Alibaba Cloud AccessKey (AK / AK-SK / access key / secret key / RAM credential); receives an AK-leak alert, risk notification, SMS, or email; finds an AK/secret exposed on GitHub, Gitee, a public repo, logs, or config files; needs AK-leak incident response, post-theft investigation, or risk assessment; or wants to trace a leaked AK's malicious operations, attack chain, created sub-users (RAM users), or new AccessKeys.
---

# AK Leak Incident Response

## Absolute Rules — read before doing anything

1. **ONE command does the whole investigation.** Run the entry script `scripts/ak_leak_investigation.py` (see Quick Start). Do NOT hand-write bash/Python, do NOT issue individual `aliyun` CLI calls, do NOT call any `scripts/query_*.py` helper individually, and do NOT reproduce the steps manually. The script orchestrates every step, sequences the APIs correctly, degrades gracefully, and emits the required report. If the script fails or produces truncated output, re-run with adjusted parameters (`--days`, `--source-ip`); never assemble the report manually. The script's output is the ONLY valid report — do not restructure, summarize, or omit any of the six sections or the four-step workflow. **Exception:** when the user request explicitly asks to verify API channel failures with direct read-only CLI queries, executing bare `aliyun <product> <Action>` read-only calls is permitted before running the entry script.
2. **Strictly READ-ONLY. Never write.** Under NO circumstances generate, write, or execute any command/script that calls a mutating API (`Update*`, `Delete*`, `Disable*`, `Modify*`, `Create*`, `Rotate*`, `Set*`, …) — e.g. `ram:update-access-key`. This includes writing a helper script "for the user to run manually". Remediation is manual guidance only (the four-step workflow in Rule 3), never an action you perform. If asked to disable/rotate/delete the AK, reply only with that manual workflow and state the skill is read-only. **Empty / not-found is a valid result — never react to it with a write.** If the AK does not exist, all queries return empty, or RAM reports the entity does not exist, that is a normal, complete finding: report it truthfully and STOP. Do NOT try to create, re-create, verify, "test", validate, or repair the AK, and do NOT fall back to hand-written `aliyun` CLI calls (except the read-only verification permitted by Rule 1's Exception) — always stay inside the entry script's read-only flow. Any write-API attempt (or CLI call that mutates state) is a hard failure of this skill.
3. **Mandatory report format.** The report MUST begin with the exact banner line `🔒 READ-ONLY SKILL — NO CHANGES WERE MADE`, and its Remediation section MUST contain the full four-step workflow verbatim: (1) disable the leaked AK, (2) create a replacement AK, (3) migrate all workloads to it and verify no disruption, (4) delete the old AK — plus investigating the leak source (a separate P1 item, NOT step 5). The four-step workflow MUST appear as a standalone block before any P0–P3 priority recommendations; do not split, renumber, or interleave. After running the entry script, verify banner + six sections (I. Incident Overview · II. Intrusion Path · III. Impact Actions Detail · IV. Impact Scope · V. Risk Analysis · VI. Remediation Recommendations) + four-step workflow all present before presenting; if any element is missing, explicitly append it.
4. **Never skip a step silently on error.** The entry script handles all error recovery automatically (logging warnings to stderr and continuing). If the script encounters permission or parameter errors, it will degrade gracefully and still produce a report. Do not invent alternative error-handling paths. See [internal_implementation.md](references/internal_implementation.md) for error detail.
5. **Credential hygiene.** Never print, cat, or quote the contents of credential artifacts (`~/.aliyun/config.json`, environment variables, credential/profile files). When you must inspect them for diagnostics, reference fields by name only. Secrets (AccessKey **Secret**, STS tokens, private key material) must always be masked (e.g. `LTAI5t…jeSfT`) in output, logs, and the report. The AccessKey **ID** is a non-secret identifier supplied by the user as the investigation target: it may appear verbatim in queries and as the CLI `--ak` argument (the tool requires it); mask every other sensitive value.
6. **Parameter provenance.** Never read `evals/` directories, test-scenario files, or eval config files to obtain user parameters (target AK, UID, region). When the request lacks them, either ask the user or derive them via STS / defaults — and explicitly declare the source of every derived value in the reply (e.g. “UID auto-derived via sts:GetCallerIdentity”).

## Overview

This skill runs the standard 6-step chain-following procedure for Alibaba Cloud AK-leak incident response and produces an operational timeline report with risk assessment and remediation guidance. All API access is read-only; the entry script handles credential routing and error recovery automatically.

## Quick Start

```bash
python scripts/ak_leak_investigation.py --ak <LEAKED_AK> --account <UID> --region <REGION> [--days N]
```

The script performs all steps read-only and prints the full report (mandatory banner + six-section conclusion + four-step remediation). Your job: confirm scope with the user (below), run this command, then present the report it produced. `--account` is optional (auto-derived from the credential, for report labeling only); `--profile` selects a credential.

## User Confirmation

The skill makes read-only calls only; it never disables, rotates, modifies, or deletes any resource. Before running the command, restate the scope to the user — target leaked AK (masked, e.g. `LTAI5t…jeSfT`), the account under investigation (the UID bound to the active credential), the region, the lookback window (`--days`), and that only read-only audit APIs will be called. An explicit investigation request that already names the leaked AK is sufficient authorization — restate and proceed; if the target AK, account, or credential is ambiguous, ask and wait before making any API call. Never expand scope beyond the confirmed AK/account; never call a mutating API (see Rule 2). In your summary, state the read-only nature — the report auto-prepends the `🔒 READ-ONLY SKILL — NO CHANGES WERE MADE` banner; repeat that no write operations were performed. Never claim the AK was disabled/rotated or that its Security Center leak record was marked handled — the skill cannot and does not do this.

## Information Completeness

Apply BEFORE running the sanctioned command. If the request names a specific AK (e.g. `LTAI5t…`) but omits `--account` or `--region`, auto-fill instead of stopping (`--account` is derived from the active credential, `--region` defaults to `cn-shanghai` or a region the user previously named); do not print "cannot proceed / missing parameter"; in your scope restatement, explicitly state "Account UID: auto-derived" and "Region: cn-shanghai (default)".

## Account Scope

The investigation is bound to the account of the active credential (via `--profile`, env AK/SK, or the `current` profile in `~/.aliyun/config.json`); `--account`/UID is only a report label. The `--ak` filter only sees that credential account's data plane — a foreign (cross-account) AK returns empty results, which must NOT be misread as "no leak / no abuse". The script always derives the credential UID; if `--account` differs it prints a prominent ACCOUNT MISMATCH banner stating that findings reflect only the credential's account and that empty results do NOT prove the AK is safe — you MUST surface this mismatch warning explicitly in your user-facing summary, do not bury it in logs. The compared UID is the main-account UID, identical for the root account, all its RAM sub-users, and assumed-roles, so a RAM sub-account or AssumeRole credential does not trigger a false mismatch. To investigate an AK in another account, run authenticated as that account; there is no cross-account mechanism.

## CLI Options

`--ak <AK>` (required, the chain's starting point); `--account <UID>` and `--region <REGION>` (optional, auto-filled); plus pass-through options `--days N` (default 30, max 90), `--profile <name>`, `--source-ip <IP>`, `--user <name>`. Run `--help` for full list.

## Report Output

The Step-6 report contains a six-section English conclusion: I. Incident Overview · II. Intrusion Path · III. Impact Actions Detail · IV. Impact Scope · V. Risk Analysis · VI. Remediation Recommendations (P0-P3, must include the full four-step workflow). Banner and four-step workflow are non-negotiable (see Rule 3); all AKs use sequential letters ordered by `createTime` (AK-A, AK-B, …), never numeric or out-of-order labels. See [module4_timeline_report.md](references/module4_timeline_report.md) and [module5_remediation_best_practices.md](references/module5_remediation_best_practices.md) for full report structure.

## References

Full detail: [investigation_flow.md](references/investigation_flow.md), [module3_actiontrail_audit.md](references/module3_actiontrail_audit.md), [high_risk_api_list.md](references/high_risk_api_list.md), [module4_timeline_report.md](references/module4_timeline_report.md), [module5_remediation_best_practices.md](references/module5_remediation_best_practices.md), [internal_implementation.md](references/internal_implementation.md).

## Available Scripts

Entry point: `scripts/ak_leak_investigation.py`. Other files (`query_*.py`, `_cli.py`, `_constants.py`) are internal — invoked by the entry script automatically; never call directly.

## Prerequisites

Requires aliyun CLI 3.x (recommended) or Python 3.9+ with `pip install -r scripts/requirements.txt`, plus read-only credentials (see `references/ram-policies.md`). The skill never disables, modifies, or deletes anything.

## Error Handling

See Rule 4 for mandatory behavior on errors (never skip silently). The entry script handles all error recovery automatically.

## Observability

Every Alibaba Cloud API call this skill makes carries a User-Agent for server-side audit correlation, on BOTH backends:

- **UA template:** `AlibabaCloud-Agent-Skills/{skill-name}/{session-id}` — here `{skill-name}` is `alibabacloud-ak-leak-incident-response`.
- **session-id rule:** a 32-character lowercase-hex string, generated once per investigation (`uuid.uuid4().hex`) and **shared unchanged by every call in that run** — CLI subprocesses and the HTTP fallback use the identical id, so all calls of one investigation correlate. Override via env `AK_LEAK_SESSION_ID` (must be 32 hex chars) to align with a parent process.
- **CLI backend:** the id is passed as `--user-agent <UA>` on every `aliyun` command.
- **HTTP fallback backend:** the id is set as the `User-Agent` request header (it is not part of the V3 signature, so signing is unaffected).

The entry script prints the session-id and full User-Agent once at startup (to stderr, keeping JSON stdout clean). No manual configuration is required.
