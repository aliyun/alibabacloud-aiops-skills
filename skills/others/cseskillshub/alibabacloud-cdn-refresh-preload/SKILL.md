---
name: alibabacloud-cdn-refresh-preload
description: |
  Read-only diagnostics for Alibaba Cloud CDN refresh and preload issues.
  Use when a URL/file/directory refresh or preload looks ineffective -
  refresh failed, preload failed, cache not cleared, or the task failed.
  Verifies task records and edge cache status, and produces a diagnosis
  report; never submits refresh/preload jobs.
  Triggers: "refresh failed", "preload failed", "cache not cleared",
  "purge not working", "prefetch not cached", "warm up ineffective",
  "invalidation unsuccessful", "pre-warming failure", "pre-fetching".
---

# CDN Refresh and Preload Diagnostics

Diagnose CDN refresh and preload issues: "content not updated after refresh", "preload failed", "cache not cleared", "URL refresh not effective", "directory refresh still shows old content".

Core approach: First query refresh/preload task records to confirm task status, then follow different diagnostic branches based on refresh type (file / directory / preload).

## Observability

All OpenAPI calls (invoked through the aliyun CLI) include:
- **User-Agent**: `--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`
- **SKILL_NAME**: `alibabacloud-cdn-refresh-preload`
- **session-id**: 32-character hex string generated per diagnostic session

## Prerequisites

1. **Python 3.11+** and **aliyun CLI** — required: `aliyun cdn describe-refresh-tasks` and `aliyun sts assume-role` are both invoked via the `aliyun` CLI (no direct HTTP signing). No external Python SDK dependencies.
2. **Alibaba Cloud credentials** — Credentials are resolved automatically by the aliyun CLI default credential chain (environment or ~/.aliyun/config.json). Do not read, print, or pass AK/SK/STS tokens explicitly.
3. **Target inputs**: URL (the resource to diagnose) and UID (the Alibaba Cloud account UID). UID can be omitted — it defaults to the caller account derived via `aliyun sts get-caller-identity`. Auto-fill first, ask second: never ask the user for UID or role name when they can be derived.

   **Auto-fill declaration requirement**: Whenever any parameter is auto-filled (UID, domain, URL, or role name), the Agent MUST explicitly declare this in the response or report metadata. For example: "UID auto-derived via sts:GetCallerIdentity: 1772241626973633" or "Domain auto-discovered via DescribeUserDomains: tofirae.com" or "URL auto-extracted from refresh task records: https://tofirae.com/1.png". This declaration is mandatory and must appear in the final output.

   **URL auto-completion**: If the user provides only a domain name (without URL), the skill queries task records for that domain and auto-extracts the most recent URL. If neither URL nor domain is provided, the skill queries all task records and auto-extracts the most recent URL. This enables "information incomplete" scenarios where the user doesn't provide a specific URL.

## Authentication: Identity Verification

Credentials are resolved automatically by the aliyun CLI default credential chain (environment or ~/.aliyun/config.json). Do not read, print, or pass AK/SK/STS tokens explicitly.

```bash
SKILL_DIR=~/.qoderwork/skills/alibabacloud-cdn-refresh-preload

# Verify caller identity and derive the caller UID (auto-cached)
# --uid is informational only (recorded in the report for traceability); credentials always come from the CLI default credential chain
# --role-name defaults to cseesadiagnosticrole if omitted; do not ask the user for it
cd $SKILL_DIR && python3 scripts/sts_token.py --json
```

`sts_token.py` only performs identity verification and UID derivation — it does not carry, print, or pass credentials.

**Identity Verification Failure**: If `sts_token.py` fails, the account has not granted investigation permissions. Guide the customer to authorize via RAM console.

**Note**: `sts_token.py` only performs identity verification (via `aliyun sts get-caller-identity` plus a nested-role detection hint); it never calls `aliyun sts assume-role`. If the runtime already injected a session of the diagnosis role (caller Arn is `assumed-role/cseesadiagnosticrole/...`), the script simply relies on the aliyun CLI default credential chain — no extra authorization step is needed.

## Diagnostic Flow

### Step 1: Query Refresh/Preload Task Records

```bash
# Mode 1: URL provided (existing behavior)
# uid omitted -> auto-derived via aliyun sts get-caller-identity
cd $SKILL_DIR && python3 scripts/cdn_refresh_preload.py --url <URL>

# Mode 2: Domain-only (auto-extract URL from task records)
cd $SKILL_DIR && python3 scripts/cdn_refresh_preload.py --domain <DOMAIN>

# Mode 3: No params (auto-extract most recent URL from all task records)
cd $SKILL_DIR && python3 scripts/cdn_refresh_preload.py
```

| Result | Next Step |
|--------|-----------|
| No task records found | Scenario R4: No operation executed or wrong entry point |
| Tasks found but status is Failed | Scenario R5: Task execution failed |
| Tasks found, status Complete (file refresh) | Step 2a |
| Tasks found, status Complete (directory refresh) | Step 2b |
| Tasks found, status Complete (preload) | Step 2c |

### Step 2a: File Refresh Complete but Not Effective

1. Compare refresh URL with user's actual test URL. Mismatch = **Scenario R1**.
2. Remote cache verification (Step 3):
   - MISS = refresh effective, likely client/browser cache issue
   - HIT = check Age header; if old cache persists = **Scenario R6**

### Step 2b: Directory Refresh Complete but Not Effective

1. Bound origin probe with `If-Modified-Since` / `If-None-Match` headers (Step 4):
   - Origin returns 304 = **Scenario R2**: origin resource unchanged, CDN keeps old cache
   - Origin returns 200 with content change = continue investigation
2. Remote cache verification (Step 3)
3. Still abnormal = **Scenario R6** (fallback)

### Step 2c: Preload Complete but Not Effective

1. Remote cache verification (Step 3):
   - HIT = preload effective
   - MISS = continue
2. Bound origin probe, check origin Cache-Control / status code (Step 4):
   - Origin returns `no-cache` / `no-store` / `private` = **Scenario R3**
   - Origin returns non-200 status = **Scenario R3**
   - Origin normal 200 with cache headers = **Scenario R6** (fallback)

### Step 3: Remote Cache Verification

```bash
cd $SKILL_DIR && python3 scripts/cdn_probe.py 'curl -ksI "<URL>"'
```

Focus: `X-Cache` (HIT/MISS), `Age`, `Via`, `Cache-Control`, `Last-Modified`, `ETag`.

If the HTTPS probe fails with an SSL/TLS handshake error (e.g., curl exit code 35), retry the same probe using the http:// scheme - HTTP responses still carry the CDN cache headers (X-Cache/Age).

**ALL probe commands (dig/curl/openssl) MUST be executed through scripts/cdn_probe.py — never run dig or curl directly in the shell.**

### Step 4: Bound Origin Probe (optional, agent-driven with curl/dig)

No script in this skill fetches origin configuration automatically (all scripts are CLI-based read-only queries). The agent must first obtain the origin address manually:
- Ask the customer for the origin IP/domain, or
- Use `cdn_probe.py 'dig <accelerated domain>'` to inspect DNS resolution as a clue.

**ALL probe commands (dig/curl/openssl) MUST be executed through scripts/cdn_probe.py — never run dig or curl directly in the shell.**

Then extract `Last-Modified` and `ETag` from the Step 3 response and run the bound origin probe:

```bash
cd $SKILL_DIR && python3 scripts/cdn_probe.py 'curl -ksI -H "Host: <CDN domain>" -H "If-Modified-Since: <Last-Modified>" -H "If-None-Match: <ETag>" --resolve <origin host>:443:<origin IP> "https://<origin host>/<path>"'
```

Focus: Origin returns 304 (resource unchanged) or 200 (resource changed). Also check `Cache-Control`, `Pragma`, `Set-Cookie`.

If the origin address cannot be obtained, skip this step and conclude from Steps 2/3 results.

### Step 5: Output Diagnostic Report

Generate report per [references/report-template.md](references/report-template.md).

## Fault Scenarios

### R1: Refresh URL Mismatch
File refresh Complete but user still sees old content. The submitted refresh URL does not match the visited URL (protocol, path, parameters). **Fix**: resubmit with exact URL.

### R2: Directory Refresh (Expire Mode) + Origin 304
Directory refresh uses "expire" mode. CDN validates with origin; origin returns 304 (unchanged), CDN keeps old cache. **Fix**: use "force delete" mode, or origin updates Last-Modified/ETag. See [references/cache-rules.md](references/cache-rules.md).

### R3: Origin No-Cache Policy Causes Preload Failure
Origin returns `no-cache` / `no-store` / `private` / non-200 / `Set-Cookie`. CDN respects origin policy and does not cache. **Fix**: adjust origin Cache-Control, or CDN console overrides. See [references/cache-rules.md](references/cache-rules.md).

### R4: No Task Records
User claims refresh/preload done but no records found. **Fix**: confirm domain/URL and operation entry point.

### R5: Task Execution Failed
Task status Failed. **Fix**: check URL format, domain config, HTTPS cert, origin reachability.

### R6: Node Cache Not Synced (Fallback)
Task Complete, origin normal, but specific nodes still return old content. **Fix**: wait and retry, or bind specific node IP to locate anomalous node. Requires PE escalation.

## Constraints

- **Read-only operations**: Only queries task records and performs diagnostics; never submits refresh/preload operations.
- **Solutions must be evidence-based**: Based on verified product features or official documentation only.
- **Reference**: [references/cache-rules.md](references/cache-rules.md) for CDN cache priority rules and status code cache behavior.

## Available Scripts

| Script | Purpose |
|--------|---------|
| `scripts/cdn_refresh_preload.py` | Query refresh/preload task records, verify cache hit status |
| `scripts/cdn_probe.py` | Execute diagnostic commands locally (curl/dig/openssl) |
| `scripts/sts_token.py` | Verify caller identity and derive UID via the default credential chain |

## Local Probing

All external probing commands are executed locally via `cdn_probe.py`. **ALL probe commands (dig/curl/openssl) MUST be executed through scripts/cdn_probe.py — never run dig or curl directly in the shell.**

```bash
cd $SKILL_DIR && python3 scripts/cdn_probe.py '<command>'
```

Standard probes: DNS (`dig`), HTTPS (`curl -ksI`), SSL cert (`openssl`), direct origin test (`curl -ksI -H "Host: <CDN domain>"`). See [references/probe-result-routing.md](references/probe-result-routing.md) for result routing.

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| No credentials found | Default credential chain not configured | Configure the aliyun CLI default credential chain (run `aliyun configure`) |
| Identity verification failed (sts get-caller-identity) | Sandbox credentials missing or invalid | Check the runtime credential configuration; no extra authorization is needed when the default chain works |
| API error (Forbidden / InvalidParameter / Throttling / InternalError) | OpenAPI returned an error for a query | Record the error, skip the affected query, continue the remaining diagnostic steps and still output the report |
| API returns empty tasks | No refresh/preload in lookback window | Extend `--days` or verify domain/URL |
| Probe command timeout | Network unreachable or command hung | Retry or check local network connectivity |

On repeated API errors from the packaged script, verify with a direct `aliyun cdn describe-refresh-tasks` CLI call to distinguish service-side failures from script issues.
