# Investigation Flow (Dual-Backend, Public API Edition)

This document captures the end-to-end runtime flow of the AK-leak incident
response skill: the shared dual-backend dispatch layer, the account-level
self-check script, and the 6-step chain-following orchestrator.

All Alibaba Cloud API calls go through a single entry point, `_cli.call()`, so
the business scripts never need to know whether the request was served by the
aliyun CLI or by the direct V3-signed HTTPS fallback.

---

## 1. Dual-Backend Dispatch Layer

Every SAS / RAM / ActionTrail / STS call funnels through `_cli.call()`.

```mermaid
flowchart TD
    A["Script calls _cli.call(product, action, params)"] --> B{"_select_backend()<br/>AK_LEAK_BACKEND override?"}
    B -->|"cli / aliyun detected"| C["Backend 1: aliyun CLI<br/>(subprocess)"]
    B -->|"http / no CLI"| D["Backend 2: direct HTTPS<br/>V3 signature ACS3-HMAC-SHA256"]
    C --> E["Parse JSON response<br/>(identical shape for both)"]
    D --> E
    E --> F["Return dict / raise CliError"]
```

- Backend is chosen once per process and cached.
- Credentials: CLI backend uses the aliyun profile (`~/.aliyun/config.json`);
  HTTP fallback resolves env AK/SK (+ optional security token) or config.json.
- The AccessKey Secret / security token are used only for signing and are
  never printed or logged.

---

## 2. Account-Level Leak Self-Check — `query_notification.py`

Runs with zero required input: with only a configured credential it derives the
UID and lists all leaks flagged for the account.

```mermaid
flowchart TD
    S["Start query_notification.py"] --> CK["check_cli_available()"]
    CK --> UID{"--account provided?"}
    UID -->|"no"| RID["resolve_account_id()<br/>STS GetCallerIdentity -> UID<br/>(display only)"]
    UID -->|"yes"| GO
    RID --> GO["Resolve time window (--days, default 30)"]

    GO --> ST1["Step 1: query_ak_leak_detection<br/>SAS DescribeAccesskeyLeakList"]
    ST1 --> SCOPE{"--ak provided?"}
    SCOPE -->|"no -> account-level"| ALL["List ALL leaked AKs<br/>(no filter)"]
    SCOPE -->|"yes -> AK-level"| ONE["Query=ak:AK<br/>verify one AK only"]
    ALL --> BAN
    ONE --> BAN["Step 1: infer_ban_from_actiontrail<br/>ActionTrail LookupEvents"]

    BAN --> DET{"--detail-id?"}
    DET -->|"yes"| GD["get_leak_detail<br/>DescribeAccessKeyLeakDetail (read-only)"]
    DET -->|"no"| OUT
    GD --> OUT["Output json / text<br/>(stdout or --output)<br/>read-only: no write/mutating calls"]
```

---

## 3. Six-Step Chain-Following Orchestrator — `ak_leak_investigation.py`

`--ak` is required (the leaked AK is the starting point); `--account` is optional
and auto-derived for report labeling only.

```mermaid
flowchart TD
    M["Start: --ak required, --account optional"] --> MB["check_cli_available()"]
    MB --> MU{"--account provided?"}
    MU -->|"no"| MR["STS GetCallerIdentity -> UID<br/>(display/report label only)"]
    MU -->|"yes"| P1
    MR --> P1["Step 1: leak alert check (SAS, Query=ak:AK)<br/>+ ActionTrail ban inference"]
    P1 --> P2["Step 2: AK info<br/>RAM GetAccessKeyLastUsed"]
    P2 --> P3A["Step 3-A: sub-accounts created by the leaked AK<br/>ActionTrail LookupEvents (service=Ram)"]
    P3A --> P3B["Step 3-B: AK-centric cross-product audit<br/>LookupEvents (ak filter) -> group by 14 services"]
    P3B --> P45["Step 4-5: trace_ak_chain (recursive)<br/>AK -> sub-users -> new AKs (max_depth=5, dedup)"]
    P45 --> P6["Step 6: generate report<br/>(alerts / ban / AK info / dangerous ops / chain / timeline / conclusion / recommendations)"]
    P6 --> SAVE["Write output/ak_leak_report.md<br/>(markdown / json)"]
```

---

## Key Notes

- **Backend is transparent to business logic** — all calls above route through
  `_cli.call()`; scripts do not care whether CLI or HTTP served the request.
- **UID is display-only** — the auto-derived UID is used purely for report /
  log labeling; it is never passed as an API parameter (queries are scoped to
  the account bound to the credential).
- **Account-level vs AK-level** — `query_notification.py` without `--ak` is
  account-wide; the orchestrator is always AK-centric (starts from the leaked
  AK and follows the chain).
- **No write operations** — this skill is strictly read-only; it never marks
  leak-deal status, disables, modifies, or deletes any AccessKey. When a leak
  is confirmed (Security Center alert, inferred ban, or high-risk activity),
  `ak_leak_investigation.py` prints a prominent URGENT banner at the top of the
  report telling the operator to manually **disable** the leaked AK, **replace**
  it with a new one everywhere it is used, then **delete** it.
- **Sensitive-data masking** — sensitive identifiers (AccessKey ID, account
  UID) are masked in all output (console logs, markdown / text report, and JSON)
  via `_cli.mask_sensitive()`. Set `AK_LEAK_NO_MASK=1` to emit raw values.
  The AccessKey Secret and security token are never emitted in any form.
```
