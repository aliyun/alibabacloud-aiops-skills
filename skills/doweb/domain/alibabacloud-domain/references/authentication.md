# Authentication

Current DomainCLI can reuse the intended standard credentials resolved by the parent Alibaba Cloud CLI, including AK/temporary STS, or authorize/refresh a selected China-site OAuth profile when credentials are unavailable. Let the CLI handle credentials internally. `profileRequired: false` means the plugin can start without a parent profile; it does not mean cloud operations require no identity. Inspect the installed authentication leaf help because implementations can change within the minimum supported version.

## Commands and meanings

| Command | Purpose | Important boundary |
|---|---|---|
| `aliyun domain auth` | Show local guidance and whether a standard credential source or OAuth profile is configured. | It does not log in, refresh credentials, or verify cloud identity. |
| `aliyun domain login` | Verify/reuse the intended parent-resolved credentials; start China-site OAuth when none are usable. | It does not guarantee a browser will open or that product permissions exist. |
| `aliyun domain logout` | Preview local logout; rerun with the leaf's confirmation flag to remove the selected local profile. | A preview is not logout, and local deletion is not guaranteed server-token revocation. |
| `aliyun domain whoami` | Use the same selected source to call read-only STS GetCallerIdentity and return verified principal/account metadata. | Cloud identity is not Domain permission, domain ownership, or DNS-zone authority. A failure is not verified identity. |

## Normal flow

1. Do not force login for public commands such as `whois`, `price --suffix`, or `icp fill`.
2. For a cloud command, let DomainCLI use the intended source it resolves internally. A usable caller-selected AK/STS source does not require an OAuth conversion or headless browser login. If the user specifically requests an OAuth identity, keep that requirement instead of substituting standard credentials.
3. If the CLI reports authorization is required or refresh was rejected, run `aliyun domain login` in an interactive terminal or return that exact next step.
4. Retry the original command once after successful login, preserving the original intended account and selectors. Do not choose another profile or account to evade a failure.
5. If the cloud API returns `Forbidden.RAM`, authentication may be valid but authorization insufficient. Report the exact action and do not loop login.

## Authentication execution gate

| Observed state | Allowed next action | Forbidden continuation |
|---|---|---|
| Remembered OAuth profile exists, but local status is not ready | Let the intended DomainCLI cloud command attempt one refresh. | Declaring the account authenticated from local metadata alone. |
| DomainCLI has already resolved usable intended standard credentials | Continue the requested friendly leaf; use `whoami` when identity verification is requested or needed. | Opening a browser solely because the credential mode is not OAuth, or copying credentials into a new profile. |
| DomainCLI returns authorization required or refresh rejected | Run `aliyun domain login` once for the same intended account and configuration store. | Selecting a different default/profile, credential mode, RAM role, or account as a fallback. |
| Login is waiting for a browser callback that the runtime cannot complete | Stop as `blocked_authentication` and tell the user to complete login in a browser-capable terminal. | Repeating login, copying an OAuth URL into reports, or continuing with another cloud command. |
| Browser callback completed | Retry the original DomainCLI cloud command once. | Treating callback completion as proof of product permission or account ownership. |
| Original command succeeds with structured cloud data | Continue the requested workflow. | Using unrelated identity output as substitute evidence. |

One activation gets at most one recovery login attempt and one retry of the original command. If the runtime is known to have no browser or reachable interactive callback path, return the safe login command without starting a wait. Otherwise give the execution tool a login deadline of at most 120 seconds. On expiry, stop only the login child started by this activation and return `blocked_authentication`; do not kill unrelated processes, free ports globally, or leave a background login running. A separate STS GetCallerIdentity call verifies only the credentials used for that call; it must never be presented as the identity of the DomainCLI OAuth profile.

## Important interpretations

- `aliyun configure list` can display an OAuth profile as `Invalid` when no currently materialized temporary AK is available. DomainCLI may still refresh it during a cloud operation; the table alone is not the final verdict.
- Current `whoami` makes a cloud identity read. Claim a verified identity only when its structured output explicitly proves success; preserve its status and identity scope. Older local-only `whoami` output is not a verified account even if a profile name is present. `auth` remains local-only.
- An OAuth browser callback proves the authorization page returned to the local CLI. It does not prove Domain API, Beian, Company Registration, Alidns, or WebsiteBuild permission.
- Do not add `--region` to login. Current parent CLI OAuth configuration does not accept that flag. DomainCLI owns the default `cn-hangzhou` service routing.
- When `--config-path` or a named profile is intentionally used, keep the same selector for login, status, and later operations.
- `login --name` and `whoami --name` name the authentication configuration; operational leaves may use the parent `--profile` selector instead. Inspect the leaf help rather than passing unsupported `--name` to every leaf. Preserve the same intended account/configuration store across these different selector spellings.

## Safe handling

- Never read or print `~/.aliyun/config.json`, environment credential values, token caches, process arguments containing secrets, or OAuth callback codes.
- Never migrate credentials with `aliyun configure set`, `--access-key-id`, `--access-key-secret`, `--sts-token`, copied JSON, or shell defaults. These are not OAuth remediation, even when a supplied environment credential appears valid.
- Do not copy a full OAuth authorization URL, state, PKCE challenge, or callback parameter into chat, logs, or repository artifacts. Let DomainCLI own the browser handoff; if it cannot complete, return the safe login command only.
- Never choose a different valid AK, ProcessCommand, RAM role, or OAuth profile as a fallback. Internal reuse of the original intended parent-resolved source is allowed; credential extraction, conversion, or account switching is not. Ask the user to authorize the intended account if that source cannot be used.
- On a missing configuration file, `login` should initialize the OAuth flow. If the installed binary cannot do that, report a CLI/plugin version or installation problem instead of creating credential files manually.
