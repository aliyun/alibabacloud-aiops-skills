# Authentication Flow (Reference)

> Full authentication procedure for QianWen platform.
> Main SKILL.md only includes the TL;DR — load this file when login is needed.

## TL;DR — 3-Step Path

1. `qianwen auth status --format json` → `authenticated: true` → skip to commands
2. `qianwen auth login --init-only --format json` → extract `verification_url` → open in browser
3. `qianwen auth login --complete --format json` → poll until `success` event

## Quick Check: Already Logged In?

```bash
qianwen auth status --format json
```

If `authenticated: true` and token is not expired, skip login entirely.

## Two-Phase Login

### Step 1 — Initialize login (non-blocking)

```bash
qianwen auth login --init-only --format json
```

Parse the stdout JSON `events` array:
- `already_authenticated` → user is logged in, skip to commands
- `device_code` → extract `verification_url` and present it to the user

### Step 2 — IMMEDIATELY start polling

```bash
qianwen auth login --complete --format json
```

Parse the stdout JSON `events` array:
- `success` → login complete, proceed to commands
- `expired` → device code expired, go back to Step 1
- `error` → report failure

## API Backend Authentication

When using the API backend (no CLI), the token can be provided via:
- Environment variable: `QIANWEN_ACCESS_TOKEN`
- macOS keychain: service `qianwen-cli`, account `cli_credentials`

The script auto-detects the token source.

## NEVER

- ❌ Ask the user "Have you completed authorization?" before running `--complete`
- ❌ Wait for user confirmation before polling — run `--complete` immediately
- ❌ Re-run `--init-only` without completing (invalidates previous device code)
