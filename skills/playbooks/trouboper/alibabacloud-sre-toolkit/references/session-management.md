# Session Management

alibabacloud-sre-toolkit includes a built-in `scripts/session_manager.py` script for managing the Session lifecycle under the `.aliyun-sre/` directory. All session management operations are performed through this script.

## Script Path

```
<skill-root>/scripts/session_manager.py
```

`<skill-root>` refers to the skill base directory provided by the agent runtime (e.g., Claude Code's `Base directory for this skill`).

## Command Overview

| Command | Purpose | Example |
|---------|---------|---------|
| `env-check` | Check all environment prerequisites | `python3 <skill-root>/scripts/session_manager.py env-check --cwd "$PWD"` |
| `init` | Create a new session (can bind UID) | `python3 <skill-root>/scripts/session_manager.py init --cwd "$PWD" --uid "<UID>"` |
| `update --status <status>` | Advance session status | `python3 <skill-root>/scripts/session_manager.py update --session "<id>" --cwd "$PWD" --status "triaged"` |
| `configure-check` | Check STAROps configuration availability | `python3 <skill-root>/scripts/session_manager.py configure-check --cwd "$PWD"` |
| `configure-set` | Write STAROps configuration (upsert into accounts[]) | `python3 <skill-root>/scripts/session_manager.py configure-set --cwd "$PWD" --scope project --employee-id "..." --workspace "..." --uid "..." [--profile "..."]` |
| `list-accounts` | List all registered UIDs and their profile/digital employee mappings | `python3 <skill-root>/scripts/session_manager.py list-accounts --cwd "$PWD"` |
| `account-add` | Add UID->profile->digital employee mapping (optional non-interactive profile authorization) | See [Profile Management Commands](#profile-management-commands-account-add--account-update) below |
| `account-update` | Update existing UID's profile/digital employee mapping | See [Profile Management Commands](#profile-management-commands-account-add--account-update) below |
| `account-delete` | Delete UID mapping (`--confirm` to also delete aliyun profile) | `python3 <skill-root>/scripts/session_manager.py account-delete --cwd "$PWD" --uid "..." [--confirm]` |
| `starops-cap-cache-get` | Read capability cache (key=uid\|employeeId\|workspace) | `python3 <skill-root>/scripts/session_manager.py starops-cap-cache-get --uid "..." --employee-id "..." --workspace "..."` |
| `starops-cap-cache-set` | Write capability cache | `... starops-cap-cache-set --uid "..." --employee-id "..." --workspace "..." --capabilities-text-stdin` |
| `status` | Query session status | `python3 <skill-root>/scripts/session_manager.py status --session "<id>" --cwd "$PWD"` |
| `list` | List all sessions | `python3 <skill-root>/scripts/session_manager.py list --cwd "$PWD"` |
| `cleanup` | Clean up expired sessions | `python3 <skill-root>/scripts/session_manager.py cleanup --cwd "$PWD"` |

> `list-accounts` / `account-add` / `account-update` / `account-delete` are **Profile Management** commands (user-explicitly-triggered configuration actions). See [STAROps Configuration Management - Profile Management](starops-config.md). The diagnostic/inspection main workflow is read-only and does not call these write commands.

### init with UID Binding

`init` supports `--uid` / `--profile` / `--employee-id` / `--workspace` (all optional) to strictly bind a new session to a UID:

```bash
python3 <skill-root>/scripts/session_manager.py init --cwd "$PWD" --uid "<UID>"
```

Resolution priority: explicit parameters > matched (or default first) account in `.starops/config.json` > aliyun CLI current profile. Resolution results are written to the `uid`/`profile`/`employeeId`/`workspace` fields in status.json and echoed in the returned JSON.

### Profile Management Commands (account-add / account-update)

> Profile management is a **user-explicitly-triggered configuration action**, independent of the read-only diagnostic/inspection main workflow. Full documentation at [STAROps Configuration Management - Profile Management](starops-config.md#profile-management-user-explicitly-triggered-configuration-action).

`account-add` / `account-update` register a UID -> profile -> digital-employee mapping. Credentials must be configured externally via `aliyun configure` before running these commands.

```bash
# Add (uid/employee-id/workspace required)
python3 <skill-root>/scripts/session_manager.py account-add --cwd "$PWD" \
  --uid "<UID>" --employee-id "<digital-employee-id>" --workspace "<workspace>" \
  --profile "<profile-name>"

# Update (uid required and must already exist; other fields optional, unspecified fields remain unchanged)
python3 <skill-root>/scripts/session_manager.py account-update --cwd "$PWD" \
  --uid "<UID>" [--profile "..."] [--employee-id "..."] [--workspace "..."]
```

> **Credentials are never handled by this skill**: Users must configure credentials externally via `aliyun configure` (interactive) or `aliyun configure set` (non-interactive). `.starops/config.json` only stores the `uid -> profile -> digital employee` (employeeId/workspace) mapping.

## State Machine

```
pending -> triaged -> planned -> validated -> executed
                                    ↑
                            (self-validate)

any -> failed (on error)
```

| State | Trigger | Corresponding SKILL.md Step |
|-------|---------|-----------------------------|
| `pending` | `init` creates session | Step 1 |
| `triaged` | After triage-summary.md is generated | Step 3 |
| `planned` | After plan/solution.md is generated | Step 5 |
| `validated` | After self-validation passes | Step 6 |
| `executed` | After report output is complete | Step 8 |
| `failed` | Error at any step | On exception |

The **inspection-governance** scenario skips `planned` / `validated`, going directly from `triaged` to `executed`.

States can only advance forward, not roll back (except to `failed`, which any state can transition to).

## Directory Structure

The `init` command creates the following directory and files:

```
.aliyun-sre/<session-id>/
├── tasks/
│   └── status.json       # Status file (managed by session_manager.py)
├── observations/          # Observation records (written by diagnostic steps)
├── plan/                  # Solutions (incident-response / alert-analysis)
├── triage-summary.md      # Triage summary (written at Step 3)
├── diagnostic-report.md   # Diagnostic report (written at Step 7)
└── inspection-report.md   # Inspection report (written at Step 7, inspection-governance scenario)
```

## status.json Structure

```json
{
  "session": "2026-07-01T00-26-29-2e3c8d30",
  "status": "triaged",
  "created": "2026-07-01T00:26:29+00:00",
  "updated": "2026-07-01T00:30:00+00:00",
  "cwd": "/absolute/path/to/project",
  "uid": "123456",
  "profile": "acct-a",
  "employeeId": "emp-1",
  "workspace": "ws-1",
  "threadId": null,
  "current_hypothesis": null,
  "hypothesis_status": null,
  "reasoning_log_entries": 0,
  "replan_count": 0,
  "max_replans": 3
}
```

| Field | Description |
|-------|-------------|
| `uid` | The Alibaba Cloud account UID bound to this session (single session, single UID) |
| `profile` | The aliyun CLI profile bound to this UID (falls back to aliyun current when empty) |
| `employeeId` | The bound STAROps digital employee ID |
| `workspace` | The bound STAROps workspace |
| `threadId` | The reused STAROps session Thread ID (written during diagnosis phase and reused) |

> **Single session, single UID, single digital employee**: Each session is bound to one UID -> one profile -> one digital employee (employeeId/workspace) at `init` time. All subsequent capability discovery, diagnosis, and reporting are based on this binding context.

## Output Format

All commands output JSON to stdout, which can be parsed directly. On error, the JSON includes an `"error"` field and the command exits with code 1.

## env-check Output Format

The `env-check` command checks four prerequisites (aliyun CLI, STAROps configuration, Python dependencies, accounts cross-validation) and returns aggregated results.

- `aliyun_cli` check includes `profiles: [{name, mode, has_credentials}]`, enumerating all configured profiles (**without modifying `current`**).
- `accounts` check cross-validates each account's profile in `.starops/config.json` (falls back to aliyun current when empty) against the aliyun profile list, reporting accounts with missing profiles or invalid credentials.

### All Passed

```json
{
  "status": "pass",
  "critical_failures": 0,
  "checks": {
    "aliyun_cli": {
      "status": "pass",
      "installed": true,
      "cli_path": "/usr/local/bin/aliyun",
      "configured": true,
      "config_path": "/Users/xxx/.aliyun/config.json",
      "active_profile": "default",
      "has_credentials": true,
      "profiles": [
        {"name": "acct-a", "mode": "AK", "has_credentials": true}
      ],
      "details": "OK",
      "remediation": null
    },
    "starops": {
      "status": "pass",
      "available": true,
      "source": "project_config",
      "config_path": "/path/.starops/config.json",
      "missing_keys": [],
      "details": "OK",
      "remediation": null
    },
    "python_deps": {
      "status": "pass",
      "all_available": true,
      "packages": {
        "requests": {"available": true},
        "alibabacloud_credentials": {"available": true}
      },
      "details": "OK",
      "remediation": null
    },
    "accounts": {
      "status": "pass",
      "count": 1,
      "accounts": [
        {"uid": "123456", "profile": "acct-a", "employeeId": "emp-1", "workspace": "ws-1", "status": "pass"}
      ],
      "invalid": [],
      "details": "OK",
      "remediation": null
    }
  }
}
```

### With Failures

```json
{
  "status": "fail",
  "critical_failures": 1,
  "checks": {
    "aliyun_cli": {
      "status": "fail",
      "installed": false,
      "cli_path": null,
      "configured": false,
      "config_path": "/Users/xxx/.aliyun/config.json",
      "active_profile": null,
      "has_credentials": false,
      "details": "aliyun CLI not installed / not found in PATH",
      "remediation": "Install aliyun CLI:\n  macOS: brew install aliyun-cli\n  ..."
    },
    "starops": { "...": "..." },
    "python_deps": { "...": "..." },
    "accounts": {
      "status": "fail",
      "count": 1,
      "invalid": [
        {"uid": "123456", "profile": "acct-a", "status": "fail", "reason": "profile 'acct-a' missing valid credentials"}
      ],
      "details": "1 account profile missing or invalid / invalid account profiles",
      "remediation": "Associate valid profiles via account-add/account-update"
    }
  }
}
```

When `status` is `fail`, the exit code is 1. The agent should stop subsequent steps and display the `remediation` content of the failed items to the user.
