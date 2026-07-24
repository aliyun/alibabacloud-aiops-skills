# Related Commands

This document summarizes all CLI commands used by this Skill, including `session_manager.py` subcommands, `starops_manager.py` invocation formats, and `aliyun configure` related commands. In the commands, `<skill-root>` refers to the skill base directory provided by the agent runtime, and `$PWD` is the project root directory.

## session_manager.py Subcommands

| Product/Script | CLI Command | Description |
|----------------|-------------|-------------|
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py env-check --cwd "$PWD"` | Check all environment prerequisites (aliyun CLI, STAROps config, Python deps, accounts cross-validation) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py init --cwd "$PWD" [--uid <uid>] [--profile <p>] [--employee-id <id>] [--workspace <ws>]` | Create a new session, can bind UID->profile->digital employee |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py update --session "<id>" --cwd "$PWD" --status "<status>"` | Advance session status (pending/triaged/planned/validated/executed/failed) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py status --session "<id>" --cwd "$PWD"` | Query session status |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py list --cwd "$PWD"` | List all sessions |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py cleanup --cwd "$PWD"` | Clean up expired sessions (TTL=300s default) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py configure-check --cwd "$PWD"` | Check STAROps configuration availability |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py configure-set --cwd "$PWD" --scope project --employee-id "<id>" --workspace "<ws>" --uid "<uid>" [--profile "<p>"]` | Write STAROps configuration (upsert into accounts[]) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py list-accounts --cwd "$PWD"` | List all registered UIDs and their profile/employeeId/workspace mappings |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py account-add --cwd "$PWD" --uid "<uid>" --employee-id "<id>" --workspace "<ws>" [--profile "<p>"]` | Add UID->profile->digital employee mapping (credentials must be configured externally via `aliyun configure`) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py account-update --cwd "$PWD" --uid "<uid>" [--profile ...] [--employee-id ...] [--workspace ...]` | Update existing UID's profile or digital employee mapping |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py account-delete --cwd "$PWD" --uid "<uid>" [--confirm]` | Delete UID mapping (`--confirm` to also delete aliyun profile) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py starops-cap-cache-get --uid "<uid>" --employee-id "<id>" --workspace "<ws>"` | Read capability cache (key=uid\|employeeId\|workspace) |
| session_manager.py | `python3 <skill-root>/scripts/session_manager.py starops-cap-cache-set --uid "<uid>" --employee-id "<id>" --workspace "<ws>" --capabilities-text-stdin` | Write capability cache |

> `list-accounts` / `account-add` / `account-update` / `account-delete` are **Profile Management** commands (user-explicitly-triggered configuration actions). The diagnostic/inspection main workflow is read-only and does not call these write commands. See [starops-config.md](starops-config.md).

## starops_manager.py Invocation Format

| Product/Script | CLI Command | Description |
|----------------|-------------|-------------|
| starops_manager.py | `python3 <skill-root>/scripts/starops_manager.py chat "<thread-id>" "<diagnostic-prompt>" --config "<config.json-path>" [--uid "<uid>"] [--idle-timeout <seconds>] [--endpoint <host>] [--stream] [--raw] [--json]` | Call CreateChat based on an existing threadId, parse SSE stream and output diagnostic text (`--stream` shows thinking process, `--raw` debug SSE, `--json` structured output) |
| starops_manager.py | `python3 <skill-root>/scripts/starops_manager.py create-thread --employee-id "<id>" --config "<config.json-path>" [--uid "<uid>"] [--profile "<p>"] [--workspace "<ws>"] [--title "<title>"] [--endpoint <host>]` | Call CreateThread to create a diagnostic session, return threadId |
| starops_manager.py | `python3 <skill-root>/scripts/starops_manager.py list-employees [--profile "<p>"] [--max-results <N>] [--endpoint <host>]` | Call ListDigitalEmployees to enumerate digital employees under the account (for onboarding) |
| starops_manager.py | `python3 <skill-root>/scripts/starops_manager.py get-employee "<name>" [--profile "<p>"] [--endpoint <host>]` | Call GetDigitalEmployee to get digital employee details (for onboarding) |
| starops_manager.py | `python3 <skill-root>/scripts/starops_manager.py create-employee --display-name "<name>" [--description "<desc>"] [--profile "<p>"] [--endpoint <host>]` | Call CreateDigitalEmployee to create a STAROps digital employee (onboarding) |
| starops_manager.py | `python3 <skill-root>/scripts/starops_manager.py delete-employee "<name>" [--profile "<p>"] [--endpoint <host>]` | Call DeleteDigitalEmployee to delete a STAROps digital employee (onboarding) |

> For `chat` / `create-thread` subcommands with multiple accounts, `--uid` is required (missing it raises an error and lists available UIDs). Single-account or legacy flat format can omit `--uid`. The `list-employees` / `get-employee` subcommands specify credential source via `--profile`. `--idle-timeout` defaults to 120 seconds, `--endpoint` defaults to `starops.cn-beijing.aliyuncs.com`. See [starops-api.md](starops-api.md).

## aliyun configure Related

| Product/Script | CLI Command | Description |
|----------------|-------------|-------------|
| aliyun | `aliyun configure list` | List all configured aliyun CLI profiles and the current profile |
| aliyun | `aliyun configure set --profile "<profile>" --mode AK --access-key-id "<AK>" --access-key-secret "<SK>" --region "<region>"` | Set credentials for the specified profile (non-interactive). Users must run this directly; the skill never handles credentials |
| aliyun | `aliyun configure delete --profile "<profile>"` | Delete the specified profile (linked execution when `account-delete --confirm` is used) |

> The sole storage location for credentials is always aliyun CLI (`~/.aliyun/config.json`). `.starops/config.json` only stores `uid -> profile -> digital employee` mappings. For aliyun CLI installation/upgrade, see [cli-installation-guide.md](cli-installation-guide.md).
