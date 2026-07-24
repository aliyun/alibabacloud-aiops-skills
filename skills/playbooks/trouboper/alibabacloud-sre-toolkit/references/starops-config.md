# STAROps Configuration Management

## Configuration File Location

STAROps configuration **must** be stored in the project-local directory:

```
<project-root>/.starops/config.json
```

> **Security Constraint**: Do not store `.starops/config.json` in the following locations:
> - User home directory `~/.starops/` (global configuration, credentials may leak across projects)
> - Agent runtime global directories (e.g., Claude Code / Codex / Qoder / Qoder-Worker system-level configuration paths)
> - Any non-project-local path
>
> `session_manager.py` and `starops_manager.py` only read configuration files from the project-local directory and do not fall back to global directories.

## Configuration Format

The current configuration uses an `accounts` array, supporting registration of **multiple Alibaba Cloud accounts (UIDs)** in the same project. Each UID is bound to its own aliyun CLI profile and a unique digital employee (employeeId, workspace optional). **Each diagnostic/inspection session is strictly bound to one UID -> one profile -> one digital employee**.

```json
{
  "accounts": [
    {
      "uid": "123456",
      "profile": "acct-a",
      "employeeId": "emp-1",
      "workspace": "ws-1"
    },
    {
      "uid": "789012",
      "profile": "acct-b",
      "employeeId": "emp-2",
      "workspace": "ws-2"
    }
  ]
}
```

| Field | Description |
|-------|-------------|
| `uid` | Alibaba Cloud account UID, the unique key for the session |
| `profile` | The aliyun CLI profile name bound to this UID. When empty, falls back to aliyun CLI's current profile (`current` in `~/.aliyun/config.json`) |
| `employeeId` | STAROps digital employee ID, used as the CreateThread / CreateChat API path parameter |
| `workspace` | STAROps workspace name (optional). A session attribute of CreateThread/CreateChat, not an intrinsic property of digital employees |

> **Credentials are never persisted**: `.starops/config.json` only stores the `uid -> profile -> digital employee` (employeeId, workspace optional) mapping. **It never stores AccessKey / STS Token or other credentials**. Credentials are managed exclusively by aliyun CLI (`~/.aliyun/config.json`). This skill resolves them read-only at runtime by `profile`.

### Environment Variable Credential Fallback

When no aliyun CLI profile is specified (or profile is empty), `starops_manager.py` falls back to checking `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` environment variables as a credential source. Aliyun profiles take priority over env vars.

The `env-check` command reports the active credential mode:
- `"single"` -- one credential source (1 aliyun profile, or env vars only when 0 profiles)
- `"multi"` -- multiple aliyun profiles with credentials (user must select)
- `"none"` -- no credentials available

In single-account mode, UID selection is auto-skipped: `init` auto-resolves the UID via `aliyun sts get-caller-identity`, no user interaction required.

### Backward Compatibility with Legacy Flat Format

The legacy single-account flat format is still supported (top-level `employeeId` / `workspace` (optional) / `uid`, optional `profile`). When read, it is automatically normalized to a single-element `accounts` array. When `profile` is missing, it falls back to the aliyun CLI current profile:

```json
{
  "employeeId": "<digital-employee-id>",
  "workspace": "<workspace-name-optional>",
  "uid": "<alibaba-cloud-account-uid>"
}
```

`starops_manager.py` is also compatible with both formats: when `accounts[]` exists, it selects the account by `--uid` (single account can omit `--uid`; multi-account without `--uid` raises an error). The legacy flat format is used directly as a single account.

## Profile Management (User-Explicitly-Triggered Configuration Action)

> Profile management is a **user-explicitly-triggered configuration action**, independent of the read-only diagnostic/inspection main workflow. The diagnostic/inspection itself does not write any configuration. `.starops/config.json` and aliyun profiles are only modified when the user actively adds/updates/deletes account mappings.

### Auto-Discover Digital Employees via API (when profile credentials exist)

When `env-check` shows valid aliyun CLI profile credentials but STAROps configuration is missing, read-only APIs can semi-automatically complete configuration, eliminating manual lookup of `employeeId` / `uid`:

1. **Select profile**: List candidates from `env-check`'s `aliyun_cli.profiles[]` (those with credentials). Ask user to confirm selection. Even with one candidate, user confirmation is required. With multiple candidates, user must explicitly choose one.
2. **Auto-resolve UID**: Call `aliyun sts get-caller-identity --profile "<selected profile>"` via `aliyun` CLI. Extract `AccountId` as `uid` (read-only, not persisted).
3. **Enumerate digital employees**: Call `list-employees --profile "<selected profile>"` via `starops_manager.py` (STAROps `ListDigitalEmployees`, paginated with `nextToken`). Parse `digitalEmployees[].name` (= `employeeId`) / `displayName` / `description` (see [starops-api.md - Digital Employee Discovery API](starops-api.md#digital-employee-discovery-api-for-onboarding)).
4. **User selects** a digital employee (`name` -> `employeeId`).
5. **workspace (optional)**: `workspace` is an optional session attribute of CreateThread, not an intrinsic property of digital employees. It cannot be auto-discovered from APIs. The user may provide it manually if needed. If not provided, it is omitted.
6. **Write configuration**: Use the `uid` (auto-resolved) / `employeeId` (selected) / `profile` (selected) to call `account-add` (`workspace` optional; credentials are already in aliyun CLI, no AK/SK transmitted, only write the mapping, see below).

### List Available UIDs

```bash
python3 <skill-root>/scripts/session_manager.py list-accounts --cwd "$PWD"
```

Outputs all registered UIDs and their `profile` / `effective_profile` (the aliyun current fallback when profile is empty) / `profile_source` (`config` / `aliyun_current` / `none`) / `employeeId` / `workspace`.

### Add Account (account-add)

```bash
python3 <skill-root>/scripts/session_manager.py account-add --cwd "$PWD" \
  --uid "<UID>" --employee-id "<digital-employee-id>" [--workspace "<workspace-name>"] \
  --profile "<profile-name>"
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--uid` | Yes | Alibaba Cloud account UID |
| `--employee-id` | Yes | STAROps digital employee ID |
| `--workspace` | No | STAROps workspace name (optional session attribute of CreateThread) |
| `--profile` | No | Bound aliyun CLI profile name. When missing, session falls back to aliyun current. Credentials must be configured externally via `aliyun configure` |

- `account-add` only writes the `uid -> profile -> employeeId` (workspace optional) mapping to `.starops/config.json`. Credentials are never accepted or handled -- users must configure them externally via `aliyun configure` before running this command.
- After writing, a lightweight validation is automatically performed. Results are reported in the `validation` field of the returned JSON (STAROps required fields + profile credential availability).

### Update Account (account-update)

```bash
python3 <skill-root>/scripts/session_manager.py account-update --cwd "$PWD" \
  --uid "<UID>" [--profile ...] [--employee-id ...] [--workspace ...]
```

- `--uid` is required and must already exist (otherwise an error is raised, suggesting `account-add`). Other fields are optional. Unspecified fields remain unchanged.
- Validation results are reported in `validation` after writing.

### Delete Account (account-delete)

```bash
python3 <skill-root>/scripts/session_manager.py account-delete --cwd "$PWD" \
  --uid "<UID>" [--confirm]
```

- By default, only removes the UID mapping from `accounts[]` and **retains** the aliyun profile.
- **Only when `--confirm` is provided**, it additionally executes `aliyun configure delete --profile <profile>` to delete the corresponding aliyun profile.

### Cross-Location Consistency

The aliyun profile and `.starops/config.json` accounts maintain consistency: add/update authorizes the profile via `aliyun configure set` and writes the mapping; delete optionally synchronizes profile removal. The sole storage location for credentials is always aliyun CLI. `.starops/config.json` only stores the mapping relationship.

### Concurrency Protection

Writes to `.starops/config.json` are **concurrency-safe**: `configure-set` / `account-add` / `account-update` / `account-delete` all complete the entire "read-modify-write" cycle under the protection of a lock file `.starops/config.lock` (`fcntl.flock` exclusive lock). Writes use **temporary file + `rename` atomic replacement** (each writer uses an independent `config.<pid>.<uuid>.tmp` to avoid overwriting each other). Therefore, concurrent `account-add` / `account-update` / `account-delete` calls will not lose each other's entries or produce corrupted half-written configurations.

> **Platform Requirement**: Cross-process locking relies on POSIX `fcntl` (Linux / macOS). On platforms without `fcntl` (e.g., Windows), write configuration commands explicitly error rather than silently degrading to lock-free writes.

## Check Configuration

```bash
python3 <skill-root>/scripts/session_manager.py configure-check --cwd "$PWD"
```

### When Configuration is Available

By default, selects the first account in `accounts[]` and backfills that account's `profile` / `profile_source`. The `accounts` field always returns all registered accounts:

```json
{
  "available": true,
  "source": "project_config",
  "config_path": "/path/to/project/.starops/config.json",
  "accounts": [
    {"uid": "123456", "profile": "acct-a", "employeeId": "emp-1", "workspace": "ws-1"}
  ],
  "employeeId": "emp-1",
  "workspace": "ws-1",
  "uid": "123456",
  "profile": "acct-a",
  "profile_source": "config",
  "missing_keys": []
}
```

| Field | Description |
|-------|-------------|
| `accounts` | All registered accounts (uid/profile/employeeId/workspace) |
| `profile` | The selected account's profile. When empty, falls back to aliyun current |
| `profile_source` | Profile source: `config` (specified in configuration) / `aliyun_current` (fallback to current) / `none` (neither) |

### When Configuration is Missing

```json
{
  "available": false,
  "source": null,
  "config_path": null,
  "accounts": [],
  "missing_keys": ["employeeId", "uid"],
  "searched_paths": ["/path/to/project/.starops/config.json (not found)"]
}
```

## Write Configuration

```bash
python3 <skill-root>/scripts/session_manager.py configure-set --cwd "$PWD" \
  --scope project \
  --employee-id "<digital-employee-id>" \
  [--workspace "<workspace-name>"] \
  --uid "<alibaba-cloud-account-uid>" \
  --profile "<profile-name>"
```

> **Note**: `--scope` must be `project` (default), writing to `<cwd>/.starops/config.json`. The `user` scope has been disabled.
>
> `configure-set` writes the UID into `accounts[]` in an upsert manner (update if exists, add if not). `--profile` is optional. To also authorize aliyun profile credentials, use the [Profile Management](#profile-management-user-explicitly-triggered-configuration-action) `account-add` / `account-update` commands.
>
> **Concurrency Protection**: Writes to `.starops/config.json` use lock file `.starops/config.lock` + temporary file + `rename` atomic write. Safe for concurrent `configure-set` / `account-add` / `account-update` / `account-delete` (see [Cross-Location Consistency - Concurrency Protection](#concurrency-protection)).
