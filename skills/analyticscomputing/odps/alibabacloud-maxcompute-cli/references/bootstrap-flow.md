> Load on demand when `aliyun maxc` is unavailable or `auth whoami --json` reports missing or invalid configuration.

# Bootstrap flow

Alibaba Cloud CLI provides the command-line entry point for MaxCompute. The `aliyun maxc` command group handles MaxCompute data-plane operations.

Honor the command-plan rule in `SKILL.md` before following these phases. An
explicit “only run” plan or a no-execution request skips every phase and command
not authorized by that request.

Reuse the session User-Agent declared in SKILL.md for every command below that
calls a cloud API: `--user-agent "$MAXC_AGENT_UA"`. Local help, `agent context`,
and `session show` may omit it.

Follow the phases below until each verification succeeds:

```text
Phase 1: Alibaba Cloud CLI and aliyun maxc  -> setup-install.md
Phase 2: Identity, project, and endpoint    -> bootstrap-auth.md
Phase 3: Effective identity verification    -> aliyun maxc auth whoami --json
```

## Phase 1: Verify the CLI

```bash
aliyun version
aliyun maxc --version
```

- If `aliyun` is missing or does not expose `maxc`, read [setup-install.md](setup-install.md).

- Obtain explicit user confirmation before installing or updating the selected CLI distribution.

## Phase 2: Configure identity and MaxCompute context

Current supported releases expose direct OAuth. If the installed runtime
conflicts with this guide, inspect its local help and upgrade before remote work:

```bash
aliyun maxc auth login --help
```

For interactive public-cloud authentication, start the direct OAuth flow. If
the target is not yet known:

```bash
aliyun maxc auth login --oauth --user-agent "$MAXC_AGENT_UA" --json
```

When the project and endpoint are known, provide both to the same OAuth command.
The Alibaba Cloud CLI root reserves `--endpoint`, so pass the verified
MaxCompute endpoint through the child environment.

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun maxc auth login --oauth --project "<project>" --user-agent "$MAXC_AGENT_UA" --json
```

In JSON mode, monitor stderr for `Sign-in URL: ...`; the final envelope is not
written until sign-in completes or the command reaches a later
project-selection state. Keep the command running while the user completes the
flow. The browser redirect must reach the loopback callback on the machine
running the CLI. Direct OAuth also requires a RAM administrator to have
installed and assigned the Alibaba Cloud `official-cli` OAuth application. Do
not request credentials in chat or place secrets directly in commands.

For `--site-type INTL`, pass a known project and MaxCompute endpoint directly.
If the project is unknown and default discovery is unavailable, obtain the
applicable Catalog endpoint from the user or verified configuration and pass
`--catalog-endpoint`; `--site-type` does not select that endpoint automatically.

### Optional fallback: Alibaba Cloud CLI OAuth profile

If an unsupported older runtime lacks direct OAuth, prefer a user-approved
update. Use the profile flow below only if that runtime must remain in use.

Inspect profile names without exposing secrets:

```bash
aliyun configure list
```

Create a new OAuth profile only when the user chooses that fallback:

```bash
aliyun configure --mode OAuth --profile "<profile>"
```

The Alibaba Cloud CLI root consumes `--profile` before it launches the `maxc`
extension. Verify the selected profile without changing the Alibaba Cloud CLI
default or persisting a MaxCompute credential provider:

```bash
aliyun --profile "<profile>" maxc auth whoami --user-agent "$MAXC_AGENT_UA" --json
```

If that runtime must persist the profile's currently injected credentials,
use the root flag together with the core parser's `--from-env` flow:

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun --profile "<profile>" maxc auth login --from-env --project "<project>" --user-agent "$MAXC_AGENT_UA" --json
```

The `configure --mode OAuth` command opens the Alibaba Cloud OAuth flow. Reuse
an existing OAuth profile when the user has already selected one. The
`auth login --from-env` command imports only the profile's current credentials
into `~/.maxc`; it is not a durable link. Rerun that bootstrap after expiry, or
upgrade to direct OAuth.

An explicit credential provider saved under `~/.maxc` suppresses credentials
injected from the selected Alibaba Cloud CLI profile for ordinary commands. Do
not infer the effective identity from the profile name; verify the principal,
`identity_source`, token-expiry information when present, and warnings reported
by `auth whoami --json`.

Do not use plain `auth login` as a generic way to edit context: it can replace a
saved direct-OAuth or external provider and discard its refresh configuration.
For direct OAuth, rerun the OAuth flow with the new context:

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun maxc auth login --oauth --project "<project>" --user-agent "$MAXC_AGENT_UA" --json
```

If only the default project or schema changes while the endpoint and identity
remain valid, use `session set` and verify the effective context. For an
external provider, rerun `auth login-external` with the same user-approved
helper and the new context. Use plain `auth login` only for a verified
access-key/STS provider being intentionally retained.

In CI, provide the project with `--project`, provide the verified endpoint with
`MAXCOMPUTE_ENDPOINT`, and add `--no-picker`. Use an existing non-interactive
identity source approved for that environment without enumerating its
secret-bearing variables. When
the user has approved a credential helper, use `auth login-external` as
documented in [bootstrap-auth.md](bootstrap-auth.md); do not invent or inspect
the helper's secret output.

On first setup with no saved project, omitting `--project` can open the picker.
If a project is already saved and the user explicitly wants another one, check
runtime help for `--reselect` and use `auth login --oauth --reselect ...` to
force selection. In non-interactive mode, inspect a `status="pending"`
envelope and present `data.identity.projects`. After the user selects an entry,
rerun the same provider-specific login with its `project_id` and verified
`endpoint`, preserving applicable flags such as `--site-type INTL`,
`--catalog-endpoint`, and `--no-browser`. If the endpoint is absent, obtain it
before continuing; do not copy an incomplete suggested action or guess a value.

Project names and environment suffixes are organization-specific. Use a discovered or user-provided project name; do not derive one by adding or removing `_dev`, `_prod`, or another suffix.

See [bootstrap-auth.md](bootstrap-auth.md) for identity sources, project selection, configuration precedence, and recovery.

## Phase 3: Verify the effective context

```bash
aliyun maxc auth whoami --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc session show --json
```

Then run the online readiness gate:

```bash
aliyun maxc agent doctor --online --user-agent "$MAXC_AGENT_UA" --json
```

Continue only when `data.ready=true`.

Confirm `status="success"`, `data.identity.authenticated=true`, the intended principal, and the intended project and endpoint.

| `validation_status` | Meaning | Action |
|---|---|---|
| `verified` | Remote identity check passed | Continue |
| `configuration_only` | Settings were saved without a remote check | Run a low-risk metadata command before relying on them |
| `failed` or `validation_failed` | Remote check failed | Read `error` and `agent_hints`; verify the effective identity, project, endpoint, and network |
| `missing_configuration` | Required context is incomplete | Return to Phase 2 |

## Common precedence problems

- `~/.maxc/config.yaml` or a project-local `.maxc/config.yaml`, `.maxc.yaml`, or `.maxc` file can provide MaxCompute settings or an explicit credential provider. Use `session show --json` to inspect `data.config_sources`.
- Without an explicit saved credential provider, supported environment values can supply connection settings. When an explicit provider is active, those values are suppressed for ordinary commands. Do not print their values; use `data.identity.identity_source` from `auth whoami`, `data.config_sources` from `session show`, and the reported principal to identify the effective source.
- If the identity is valid but one object is inaccessible, verify the exact project and object permission before changing authentication.

## Related references

- Alibaba Cloud CLI installation and update details: [setup-install.md](setup-install.md)
- Identity source and MaxCompute context details: [bootstrap-auth.md](bootstrap-auth.md)
