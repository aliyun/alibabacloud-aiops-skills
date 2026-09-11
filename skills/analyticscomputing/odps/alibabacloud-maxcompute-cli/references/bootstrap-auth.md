> Load on demand for MaxCompute authentication, project selection, endpoint setup, or identity-source diagnosis. Skip when `auth whoami --json` is verified for the intended principal and project.

# MaxCompute authentication and context

Honor the command-plan rule in `SKILL.md` before using any authentication
pattern here. An explicit command list is exhaustive; a no-execution request
means this file is descriptive only and no login, profile, or context command
may run.

Current supported releases provide direct OAuth through `auth login --oauth`.
Runtime help remains authoritative if the installed command surface conflicts
with this guide. The MaxCompute project, endpoint, session, state, and cache are
stored under `~/.maxc` unless another configuration path is selected.

Reuse the session User-Agent declared in SKILL.md for every command below that
calls a cloud API: `--user-agent "$MAXC_AGENT_UA"`. Local help and `session show`
may omit it.

Security rules:

- Do not ask the user to paste AccessKey credentials or tokens into the conversation.
- Do not place credentials directly in command arguments.
- Do not read or print credential files or secret-bearing environment variables.
- Obtain user authorization before changing a persistent identity or MaxCompute context.

## Step 1: Establish an identity

For an interactive public-cloud login, use direct OAuth. If the target is not
yet known:

```bash
aliyun maxc auth login --oauth --user-agent "$MAXC_AGENT_UA" --json
```

When the project and endpoint are known, provide both to the same OAuth command.
The Alibaba Cloud CLI root reserves `--endpoint`, so pass the verified
MaxCompute endpoint through the child environment rather than placing that
flag after `maxc`.

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun maxc auth login --oauth --project "<project>" --user-agent "$MAXC_AGENT_UA" --json
```

Direct OAuth requires a RAM administrator to have installed the Alibaba Cloud
`official-cli` OAuth application and assigned the identity. In JSON mode, the
CLI writes `Sign-in URL: ...` to stderr before it can emit the final envelope;
monitor stderr, present or open that URL, and keep the command running. The
browser redirect must reach the loopback callback on the machine running the
CLI. The JSON envelope appears only after sign-in completes or the command
reaches a later project-selection state. If project selection is required,
present the entries returned by the live envelope. After the user chooses one,
take both `project_id` and `endpoint` from that entry and rerun the same
provider-specific login with `--project` and `MAXCOMPUTE_ENDPOINT`. If the endpoint is
absent, obtain and verify it before continuing; do not guess. Preserve
applicable flags such as `--site-type INTL`, `--catalog-endpoint`, and
`--no-browser`. A suggested action can omit these contextual flags, so verify
and complete it before rerunning the login.

For an international account, add `--site-type INTL`; the direct OAuth default
is `CN`. In a terminal that cannot launch a browser, add `--no-browser` and use
the URL from stderr. This still requires the OAuth redirect to reach the CLI's
local callback; use another approved identity source when that is impossible.
When the project and MaxCompute service endpoint are known, pass both
explicitly using the child environment pattern above. If an international project's location is unknown and default
project discovery is unavailable, obtain the applicable Catalog endpoint from
the user or verified Alibaba Cloud configuration and pass `--catalog-endpoint`;
do not infer it from `--site-type`.

### Optional fallback: Alibaba Cloud CLI OAuth profile

If an unsupported older runtime lacks direct OAuth, prefer a user-approved
upgrade. Use the profile flow below only when that runtime must remain in use.

Inspect available profile names without exposing secret values:

```bash
aliyun configure list
```

Create a new Alibaba Cloud CLI OAuth profile only when the user chooses this
fallback:

```bash
aliyun configure --mode OAuth --profile "<profile>"
```

The Alibaba Cloud CLI root consumes `--profile` before launching the extension.
First verify the selected profile without changing the Alibaba Cloud CLI
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

This fallback imports the profile's current short-lived credentials into the
active MaxCompute configuration. It does not keep a durable, auto-refreshing
link to the Alibaba Cloud CLI profile. After those credentials expire, rerun
the root-profile plus `auth login --from-env` bootstrap or upgrade to direct
OAuth. When multiple profiles exist and the intended account is unclear, ask
the user to choose one.

The profile name is not proof of the effective identity. An explicit credential
provider in `~/.maxc/config.yaml` or another active MaxCompute configuration
source suppresses profile-injected environment credentials for ordinary
commands. Verify the principal, `identity_source`, token-expiry information when
present, and warnings returned by `auth whoami --json` before any data operation.

## Step 2: Check the effective identity

```bash
aliyun maxc auth whoami --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc session show --json
```

Inspect `status`, `data.identity`, `error`, and `agent_hints` from `auth whoami`.
Use `data.config_sources` from `session show` when diagnosing configuration
precedence:

| Result | Meaning | Action |
|---|---|---|
| `authenticated=true`, `validation_status=verified` | The effective identity and MaxCompute context passed remote validation | Confirm the principal and project, then continue |
| `configured=false` or `missing_configuration` | Identity, project, endpoint, or more than one of them is missing | Inspect `data.auth_options`, missing-field details, and warnings. Return to Step 1 when identity is missing; use Step 3 only when a usable identity already exists. |
| `configured=true`, validation failed | Saved context exists but remote validation failed | Verify the effective identity, project, endpoint, region, and network |

A `PERMISSION_DENIED` result for one object does not by itself indicate an authentication failure. Confirm the project, object name, and requested operation before changing identity.

## Step 3: Configure the project and endpoint

Use values supplied by the user or returned by the CLI. Do not invent an endpoint.

Choose the context command from the verified current provider. A plain
`auth login --project ...` with a new `MAXCOMPUTE_ENDPOINT` rebuilds the saved auth block and can
discard refresh configuration from OAuth or external providers.

For a saved direct-OAuth provider, rerun the OAuth flow with the new context:

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun maxc auth login --oauth --project "<project>" --user-agent "$MAXC_AGENT_UA" --json
```

If only the default project or schema needs to change and the endpoint and
identity remain valid, use `session set` instead and verify the resulting
context. For an external provider, rerun `auth login-external` with the same
user-approved helper and the new context. Use plain `auth login` only for a
verified access-key/STS provider whose saved credentials are intentionally
being retained.

On a runtime without direct OAuth, use this only for the time-bounded profile bootstrap
described in Step 1:

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun --profile "<profile>" maxc auth login --from-env --project "<project>" --user-agent "$MAXC_AGENT_UA" --json
```

This command replaces the saved MaxCompute provider with credentials currently
obtained from the selected profile. Verify the reported principal and token
expiry afterward; subsequent ordinary commands use the saved provider until it
is replaced.

On first setup with no saved project, omit `--project` from the same
provider-specific login. For direct OAuth:

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" aliyun maxc auth login --oauth --user-agent "$MAXC_AGENT_UA" --json
```

If a project is already saved and the user explicitly wants to choose another
one without supplying its ID, omitting `--project` can reuse the saved project.
When runtime help lists `--reselect`, use
`auth login --oauth --reselect ...` to force the picker, then verify the selected
project with `auth whoami --json`.

- In a TTY, select from the project picker.
- In non-interactive mode, a `status="pending"` envelope can contain `data.identity.projects`. Present the entries, let the user select one, and rerun the same provider-specific login with that entry's `project_id` and verified `endpoint`, preserving applicable OAuth flags. If the endpoint is absent, stop and obtain it rather than guessing.
- In CI, pass `--project` and `--no-picker`, and set the verified endpoint with `MAXCOMPUTE_ENDPOINT`. Use an approved non-interactive identity source; do not enumerate its secret-bearing environment.
- Use `--no-validate` only when the user explicitly requests saving configuration without a remote check; verify the context with a low-risk metadata command afterward.

For CI or another non-interactive environment with an approved credential
helper, the CLI also supports an external provider:

```bash
MAXCOMPUTE_ENDPOINT="<endpoint>" \
MAXCOMPUTE_PROJECT="<project>" \
aliyun maxc auth login-external \
  --process-command "<user-approved-credential-helper>" \
  --project "<project>" \
  --user-agent "$MAXC_AGENT_UA" \
  --json
```

The helper command executes locally and its output contains credentials. Use
only a helper supplied or approved for that environment; do not print its
output, and verify the resulting principal. This changes persistent MaxCompute
authentication, so obtain authorization unless the user's request already
includes configuring that exact identity source.

Project names are opaque. `_dev`, `_prod`, and similar suffixes are organization conventions, not a universal mapping.

## Step 4: Verify the intended context

```bash
aliyun maxc auth whoami --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc session show --json
```

Confirm:

- `status="success"`
- `data.identity.authenticated=true`
- `validation_status=verified`
- the reported principal is the intended identity
- the reported project and endpoint match the user's target
- no warning indicates an unexpected override

Then run a low-risk metadata check when remote access has not yet been verified:

```bash
aliyun maxc meta list-tables --user-agent "$MAXC_AGENT_UA" --json
```

## Configuration precedence

MaxCompute context and identity can be affected by:

- the default `~/.maxc/config.yaml`
- project-local `.maxc/config.yaml`, `.maxc.yaml`, or `.maxc` files
- a file selected with top-level `--config`
- supported environment variables
- a selected Alibaba Cloud CLI profile

Do not infer precedence from the intended command alone. When an active
MaxCompute configuration has an explicit credential provider, supported
environment credentials and Alibaba Cloud CLI profile injection are suppressed
for ordinary commands. Without an explicit provider, supported environment
values can supply missing connection settings. Use `session show --json` and
`auth whoami --json` to inspect `data.config_sources`,
`data.identity.identity_source`, the effective principal, and token-expiry
information without printing raw configuration or environment values.

`session set --project/--schema` changes the persistent MaxCompute default. Use it only when the user wants subsequent commands to inherit that setting; otherwise use a one-off `--project` argument.

## How to read `auth whoami`

Key fields:

- `authenticated`: whether the remote identity check succeeded
- `configured`: whether required MaxCompute context is present
- `validation_status`: `verified`, `missing_configuration`, `failed`, or `configuration_only`
- `identity_source`: active credential/configuration source summary under `data.identity`
- `project`, `region`, `endpoint`: effective MaxCompute context
- `config_sources`: MaxCompute configuration files under `session show`'s `data`
- `auth_options`: optional recovery suggestions under `data.auth_options` when authentication is not ready

Use the live envelope's `error.suggestion`, structured `agent_hints.actions`,
`action_ids`, and `agent_hints.warnings` when they differ from static examples
in this file. Run an action only after checking its execution and confirmation
fields.
