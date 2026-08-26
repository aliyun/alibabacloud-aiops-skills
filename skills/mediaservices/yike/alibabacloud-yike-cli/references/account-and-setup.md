# Authentication, Account & Setup

Read this document when authentication, context, account, update, or bundled skill installation is involved. See root `SKILL.md` for shared rules.

## Authentication & Context

When checking credentials, logging in, or configuring the default Workspace/Project, run the corresponding commands with `--format json` appended explicitly.

```bash
yike auth status --format json
yike auth login --format json
yike auth login --no-open --format json
yike auth login --url https://your-api-host/oauth/authorize --format json
yike auth logout --format json
yike config get --format json
yike config set workspaceId <workspaceId> --format json
yike config list projectId --format json
yike config set projectId <projectId> --format json
```

### Authorization Entry URL

Read the authorization entry URL from stderr, open it in a browser; the server responds with a 302 redirect to the authorization page. Complete authorization and wait for the callback:

| Scenario | Authorization Entry | Trigger |
| --- | --- | --- |
| Default login | `https://api.yikeai.com/oauth/authorize?...` | `yike auth login --format json` |
| Custom authorization entry | `<authorizeUrl>?...` | `yike auth login --url <authorizeUrl>` |

- `--url` must be the full backend `GET /oauth/authorize` endpoint; do not pass a frontend `/oauth` page or a homepage URL with a hash.
- If the browser cannot redirect back to the local machine, re-run `yike auth login` or set the `YIKE_API_TOKEN` environment variable.

### Login Blocking & Agent Handling

Execution protocol:

1. Run `yike auth login --format json` in the foreground; append `--no-open` when the authorization page must be opened manually.
2. Read the authorization URL from stderr; do not treat stderr progress lines as the final JSON.
3. Wait for the browser callback, up to 5 minutes.
4. Read the final JSON from stdout.
5. Run `yike auth status --format json`; only proceed with commands requiring authentication after `loggedIn:true`.

| Condition | Action |
| --- | --- |
| Environment cannot wait in the foreground | Run `yike auth login --format json` in the background; poll `yike auth status --format json` |
| Using `--no-open` | Copy the authorization URL from stderr; complete authorization in the browser and wait for the callback |
| Browser cannot reach the callback address on the CLI machine | Set the `YIKE_API_TOKEN` environment variable |
| `auth status` shows `loggedIn:true` but the API returns a credential error | Re-login per `details.reauthCommand` |
| Need to actively log out of the current CLI session | Run `yike auth logout --format json` |

### Failure Codes & Recovery

When authentication is working, continue with the original task without adding authentication steps or reporting internal handling to the user. Only when a command ultimately returns an authentication error, parse the JSON `error`, `details.code`, `details.reauthCommand`, and `details.hint`; if `details.reauthCommand` exists, recover using it — do not differentiate errors by exit code.

| Phase | `details.code` | Action |
| --- | --- | --- |
| Browser callback | `CALLBACK_TIMEOUT` | No callback within 5 minutes; re-run `yike auth login` and complete authorization in the browser promptly |
| Browser callback | — (HTTP 400) | On erroneous or missing state, the CLI rejects that callback and continues waiting for a valid one; if this persists, check for concurrent logins or authorization page pass-through |
| Browser callback | `CALLBACK_MISSING_CODE` | Authorization page did not return a code; check the authorization page/account and retry |
| Browser callback | `access_denied` or other OAuth error | User denied or authorization failed; re-initiate login |
| Credential validation | `TOKEN_MISSING` / `TOKEN_INVALID` / `TOKEN_EXPIRED` / `TOKEN_REVOKED` | Re-login per `details.reauthCommand` (`yike auth login`) |
| Business API call | `PROJECT_ACCESS_DENIED` / `WORKSPACE_ACCESS_DENIED` | For project errors, first run `yike config list projectId --format json` to get available IDs, then set explicitly; for workspace errors, switch per `details.hint` or ask the administrator to grant access |
| Setting project | `PROJECT_NOT_FOUND` | Target project is not in the current workspace's available list (deleted or no access) when running `config set projectId`; first run `yike config list projectId --format json` then select a valid ID |
| HTTP layer | Format `HTTP <status>` | Report the final status code when the command fails |

When authentication credentials are invalidated, expired, or revoked, re-login per the `reauthCommand` returned by the command. To actively log out, use `yike auth logout --format json`.

### Security Boundaries

- Never read browser cookies, LocalStorage, profile files, or other web login credentials.
- To manually inject a token, use only the `YIKE_API_TOKEN` environment variable. When reporting to the user, only show `hasApiToken` — never output the token in plaintext.
- After a successful `auth logout`, local authentication credentials are cleared; non-sensitive configuration (e.g., `workspaceId`, `projectId`) is preserved.

Configurable keys:

- `workspaceId`
- `projectId`
- `defaultModel`

Context selection rules:

- `--workspace-id` / `--project-id` / `--production-id` override only the current command.
- `config set workspaceId/projectId` writes to the default context.
- `config set projectId <id>` validates against the current workspace's available project list first; a deleted or inaccessible ID fails with `PROJECT_NOT_FOUND` and is not written to local configuration.
- `config set workspaceId` clears the saved `projectId` when switching to a different workspace to avoid stale project context; after switching, re-run `config list projectId` and set `projectId` again.
- When the Agent needs to select a project, first run `yike config list projectId --format json`, present `projects[].projectId` and `projects[].title` to the user as options, then write the selection with `yike config set projectId <id> --format json`; do not omit the ID in JSON or non-TTY mode; do not use a historical ID that is not in the list.
- Projects without a server-side title can still be selected: `projects[].title` is `(untitled)` with `titleMissing: true`; also show the `projectId` to the user.
- Humans in an interactive terminal can directly run `yike config set projectId` and select a project by number.
- When a specific project/production ID is already known, explicitly pass `--project-id` or `--production-id`.

## Account & Updates

```bash
yike whoami --format json
yike account --format json
yike update --check --format json
yike update --format json
```

| Condition | Command / Action |
| --- | --- |
| Query the current user | After login, run `yike whoami --format json` or `yike account --format json` |
| Check for a new version only | Run `yike update --check --format json` |
| User explicitly requests a CLI update | Run `yike update --format json` |

After login or running `yike whoami --format json` / `yike account --format json`, the model catalog in `yike generate video --help` syncs the Wonder video models available to the account; if help does not list them, re-run `yike account --format json` first, then check help.

When parsing the `account` / `whoami` JSON, read:

| Field | Meaning |
| --- | --- |
| `user.membership.level` | Membership tier |
| `user.membership.endTime` | Raw expiration time |
| `user.membership.endTimeIso` | ISO-formatted expiration time |
| `user.membership.description` | Membership summary |

Only read and report the public membership fields listed above. Do not infer account capabilities from unlisted response fields, and do not forward those fields to the user.

## Skill Installation

When the user requests installing the bundled `using-yike-cli` skill, run:

```bash
yike self skill install --format json
yike self skill install --target ~/.agents/skills --format json
```

Default installation targets include:

- `~/.agents/skills`
- `~/.claude/skills`
- `~/.qoder/skills`
- `~/.codex/skills`

To customize the target directory, use `--target <path>` or set `YIKE_SKILL_DIR`.

## Quick Error Reference

| Condition | Resolution |
| --- | --- |
| `Not logged in` | Run `yike auth login --format json` or configure `apiToken` |
| Token invalidated, expired, or revoked | Re-login per `details.reauthCommand` |
| Insufficient workspace/project permissions | Switch `workspaceId` / `projectId`, or ask the administrator to grant access |
