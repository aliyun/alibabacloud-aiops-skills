# Authentication Flow (Reference)

> This file contains the detailed authentication flow for QianWen CLI.
> Main SKILL.md only includes the TL;DR — load this file when the agent needs the full procedure.
> For credential system details, see the Security section in SKILL.md.

## TL;DR — 3-Step Auth Path

1. `qianwen auth status --format json` → `authenticated: true` → skip to commands
2. `qianwen auth login --init-only --format json` → extract `verification_url` → open in browser
3. `qianwen auth login --complete --format json` → poll until `success` event

## Quick Check: Already Logged In?

```bash
qianwen auth status --format json
```

If `authenticated: true` and token is not expired, skip login entirely.

## Recommended: Two-Phase Login

Works in all environments (desktop, headless, remote container).

### Step 1 — Initialize login (non-blocking)

```bash
qianwen auth login --init-only --format json
```

Exits immediately. Parse the stdout JSON `events` array:
- `already_authenticated` → user is logged in, skip to commands
- `device_code` → extract `verification_url` and present it to the user

On desktop environments with a browser, open the URL for the user:
```bash
open "$VERIFICATION_URL"          # macOS
xdg-open "$VERIFICATION_URL"      # Linux
start "" "$VERIFICATION_URL"      # Windows
```

### Step 2 — IMMEDIATELY start polling (do NOT wait)

```bash
qianwen auth login --complete --format json
```

Parse the stdout JSON `events` array:
- `success` → login complete, proceed to commands
- `expired` → device code expired, go back to Step 1
- `error` → report failure

## TTY Environments

If the agent is running in a TTY, simply run `qianwen auth login`. The CLI will automatically open the browser and poll until authorization completes.

## JSON Event Structure

Both `--init-only` and `--complete` output a single JSON document:
```json
{
  "events": [
    {"event": "device_code", "verification_url": "...", "expires_in": 300},
    {"event": "success", "authenticated": true, "user": {"aliyunId": "..."}}
  ]
}
```

Event types: `already_authenticated`, `device_code`, `success`, `expired`, `error`, `pending`.

## NEVER

- ❌ Ask the user "Have you completed authorization?" before running `--complete`
- ❌ Wait for user confirmation before polling — run `--complete` immediately after presenting the URL
- ❌ Re-run `--init-only` without completing (this creates a new device code and invalidates the previous one)
