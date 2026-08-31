# Error Handling Reference

> Loaded when a command fails. Main SKILL.md keeps the summary — this file has
> the full classification table, retry parameters, and exit codes.

## Error Classification

When a command fails, **classify first, recover, then retry**. Never silently skip to fallback.

| Category | Recovery |
|----------|----------|
| `auth-failure` | Run 3-step login (see Authentication Flow) -> **retry the original command** |
| `not-installed` | Show install command (`npm install -g @qianwenai/qianwen-cli`) -> ask user to install -> retry, or fall back to API backend with `QIANWEN_ACCESS_TOKEN` |
| `version-mismatch` | Suggest `qianwen update` -> upgrade -> retry |
| `network-timeout` | Retry once after 2s; only after second failure ask whether to retry later |
| `rate-limit` | Inform user, wait and retry |
| `ticket-not-found` | Verify ticket ID with `list` -> correct and retry |
| `terminal-status` | Ticket is closed/resolved/confirmed -> refuse reply/close, offer to create a new ticket |
| `other` | Show raw error; link to web portal |

## Retry Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| CLI command timeout | 30 s | Per CLI invocation |
| API request timeout | 30 s | Per HTTP request |
| Retry interval | 2 s | Wait between retries |
| Max retries | 1 | Only retry once for network-timeout; second failure -> fallback |
| Total max wait | 60 s | Sum of all retries for a single operation |

> **Rule:** Never retry more than once. If the retry also fails, immediately fall back to the web portal guidance. Do not create retry loops.

## Cascading Failure Handling

When a recovery strategy itself fails:
1. Do **not** retry the same recovery more than once
2. If the second attempt also fails, **stop automated recovery**
3. **Final fallback**: Guide the user to the web portal: `https://platform.qianwenai.com/home/support`
4. Provide a summary of what was attempted so the user can include it in their web ticket

## CLI Command Hang

If a CLI command hangs (e.g., `qianwen auth login --complete` does not return):
1. Wait up to 30 seconds for the command to complete
2. If still hanging, interrupt the command (timeout)
3. **Fallback**: guide the user to submit via the web portal: `https://platform.qianwenai.com/home/support`
4. Inform: "The CLI is not responding. You can submit this ticket directly on the web portal."

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General/usage error |
| 2 | Authentication error |
| 3 | Network error |
| 4 | Configuration error |
| 130 | Interrupted |

## Full Diagnostic Capabilities (Phase 1 auto-resolve)

| Problem category | CLI auto-resolve |
|---|---|
| CLI session expired / `qianwen support` 401 | `qianwen auth login` then verify with `qianwen auth status` |
| Model API 401 (API Key issue) | Distinguish source; report Key status only; guide to web portal |
| Quota exhausted | `qianwen usage summary --format json` -> suggest model switch or plan upgrade |
| CLI version mismatch | `qianwen update` then verify with `qianwen version` |
| Config error | `qianwen config list --format json` -> identify and fix |
| Network/connectivity | `qianwen doctor --format json` -> report diagnostics |
| Model not found | `qianwen models search "<keyword>" --format json` -> suggest alternatives |
| 4xx/5xx errors or request-id lookup | `qianwen usage logs --format json` -> query by status code or request-id (CLI v1.4.0+) |
