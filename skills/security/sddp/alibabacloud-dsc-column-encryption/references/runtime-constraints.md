# Runtime Constraints

## Script environment and authentication

For a platform-provisioned CLI Mock evaluation, the transport preserves only
`ALIBABA_CLOUD_CLI_MOCK` and `ALIBABA_CLOUD_CLI_MOCK_PATH` among Mock controls.
It never enables Mock or changes its data itself. Credential, profile, endpoint
and debug environment overrides remain filtered. A configured Mock is not proof
that it matched: check actual fixture responses and interception evidence.
An unmatched CLI Mock may fall through to a live request, so do not run write
evaluations based solely on the presence of these variables.

The three scripts use the Python 3.10+ standard library and make API requests through the local `aliyun` CLI, without a Python SDK dependency. `scripts/requirements.txt` contains only explanatory comments; no pip installation is needed. Use CLI ≥ 3.4.10 for all supported authentication modes. Exactly CLI 3.3.23 is also accepted with a preconfigured StsToken profile, based on forced-RPC compatibility tests; other older versions and other authentication modes on 3.3.23 are rejected. Do not switch profiles or change authentication mode to bypass this check. The CLI and the selected named profile must be available in the same runtime as the scripts.

### Select one named profile

| CLI mode | Credential source configured outside the agent session | Renewal |
| --- | --- | --- |
| `OAuth` | User completes browser authorization | CLI manages supported token refresh; the user signs in again when required |
| `AK` | RAM user's AccessKey ID and AccessKey Secret | User or trusted credential-management platform rotates the long-term keys |
| `StsToken` | Temporary AccessKey ID, AccessKey Secret and SecurityToken | Does not auto-refresh; user or trusted platform must provide a fresh set after expiry |
| `RamRoleArn` | Source RAM-user AccessKey pair, target RoleArn and role-session settings | CLI calls STS AssumeRole and manages temporary-credential renewal |

OAuth remains the recommended interactive setup; the default profile name is still `dsc-oauth`. Use distinct names such as `dsc-ak`, `dsc-sts` and `dsc-role` for the alternatives. AK is supported when explicitly requested, but prefer temporary credentials or OAuth over long-term keys. Do not use an Alibaba Cloud account's root AccessKey. Other CLI modes, including automatic credential chains, are not enabled by this skill.

The user chooses **one** command below and runs it in their own interactive terminal, entering secrets privately at the CLI prompts. The agent must not execute credential setup, ask for secrets in chat, place them in command arguments, or save them in skill/plan/evaluation files. For a managed sandbox, the trusted platform provisions the selected CLI profile through its supported credential setup instead.

```bash
aliyun configure --mode OAuth --profile dsc-oauth
aliyun configure --mode AK --profile dsc-ak
aliyun configure --mode StsToken --profile dsc-sts
aliyun configure --mode RamRoleArn --profile dsc-role
```

See the official CLI guides for [credential types](https://help.aliyun.com/en/cli/configure-credentials/), [STS temporary credentials](https://www.alibabacloud.com/help/en/cli/temporary-security-credentials-sts-token) and [RAM role credentials](https://www.alibabacloud.com/help/en/cli/ram-role-credentials). `StsToken` is the exact mode name, not `STS`. Some CLI help summaries omit it; check the profile with the bundled status helper instead of changing the mode to AK.

For OAuth, a RAM administrator installs the official `official-cli` OAuth application and assigns the intended RAM user or role. A RAM user needs console login capability. The user completes browser login and authorization; `aliyun configure set` cannot replace this step. Choose `CN` for the China site. If the browser does not open, the user opens the CLI-supplied login URL in their chosen browser. See the [official OAuth prerequisites](https://help.aliyun.com/zh/cli/oauth-credentials).

For RamRoleArn, the source identity needs `sts:AssumeRole` on the intended role, and the role's trust policy must allow that identity. The target role needs the DSC query/change permissions and optional KMS inspection permission for the task. Supply the role session name and any ExternalId required by the trust policy through the user's CLI setup. RoleArn alone is not a credential. CLI role assumption is an authentication step, not a change to the DSC API contract; the Python scripts do not obtain or export its STS result.

Authentication does not grant business API permissions. See [ram-policies.md](ram-policies.md) for the Action inventory, resource boundaries and permission examples for administrator review. If permissions are insufficient, report the specific Action; do not create roles, attach policies or expand access automatically.

### Check the profile without exposing credentials

Check the CLI version with `aliyun version`. To check authentication, the agent runs only the following entry point, which returns credential-free authentication status and next-step guidance:

```bash
python3 <skill-dir>/scripts/aliyun_cli.py --profile dsc-oauth
```

Replace `dsc-oauth` with the selected name for other modes. This check invokes CLI version inspection and `aliyun configure get mode --profile <selected-profile>` only. It accepts exactly `OAuth`, `AK`, `StsToken` and `RamRoleArn` and returns the actual mode. `Configured: true` means only that a supported mode was found; `CloudAccessVerified: false` explicitly means credentials, expiry, role assumption and API permissions have not been tested. Do not read plaintext CLI configuration or token files, invoke credential-export commands, or display raw `aliyun configure list` output: the listing in CLI 3.4.10 may contain token suffix fragments.

All three business entry points support `--profile`, defaulting to `dsc-oauth`. Actual API requests select that profile without additionally passing `--mode`, preserving the CLI's retry configuration override behavior. Subprocesses ignore inherited AK/STS environment credentials and default-profile overrides in **every** mode; credentials must be configured in the selected CLI profile. No `--env-file` or direct credential flags are supported. RPC retries are set to 0, and `ALIBABA_CLOUD_THROTTLING_RETRY_ENABLED=false` disables automatic throttling retries.

If a profile is missing/unsupported, a credential expires, role assumption fails or API access is denied, stop the affected step. Do not switch profiles/modes, use ambient credentials, export tokens or install an SDK as a fallback. For `InvalidSecurityToken.Expired` in StsToken mode, ask the user or trusted platform to obtain and configure a fresh credential set; the skill cannot renew a fixed token. OAuth refresh and RamRoleArn assumption/renewal remain CLI responsibilities. An uncertain write still requires read-only state verification, never automatic resubmission.

The transport rechecks the mode before each API call and rejects a change within the workflow. Confirmation tokens bind both profile name and mode, so switching either invalidates a previous token. They do not bind an independently verified cloud identity: replacing credentials or changing the target role within the same profile/mode still requires rediscovery, fresh preflight and review of the effective plan.

After setup, run a read-only query with the chosen profile, for example:

```bash
python3 <skill-dir>/scripts/query_column_encryption.py regions --profile dsc-sts
```

The same `--profile dsc-sts` selection applies to create/manage preflight and execution; keep the existing exact-plan approval and confirmation-token requirements. Use actual read-only responses and required preflight to validate the selected identity. A successful mode check or historical test of another mode is not proof of current cloud access.

### AgentHub and release verification

Adding these profile modes does not automatically connect AgentHub's STS/RoleArn form to this skill. The execution sandbox must receive a supported **named CLI profile** through trusted platform provisioning. Injecting only AK/STS environment variables is insufficient because the transport deliberately strips them. Do not copy local CLI credential files or tokens into the sandbox. Confirm the platform's provisioning mechanism, then run a minimal real read-only query there; offline mocked tests do not prove that integration works.

Changes to authentication require fresh static/security checks and relevant dynamic tests before publishing. Do not reuse a previous OAuth-only release's scan results as proof that new credential modes are accepted by the current platform rules.

## Request User-Agent and Workflow Session

Every DSC and KMS request uses the shared User-Agent `AlibabaCloud-Agent-Skills/alibabacloud-dsc-column-encryption/{session-id} skill-version/{version}`. The version is loaded from [manifest.json](manifest.json), not hardcoded in the scripts.

The optional `ALIBABA_CLOUD_SKILL_SESSION_ID` must contain exactly 32 lowercase hexadecimal characters. Reuse one value across all script invocations in a logical workflow to correlate its requests. If the variable is absent, a UUID4 session ID is generated once per process and reused for that process's DSC and KMS requests; separate processes receive separate fallback IDs.

## Instance Capabilities

The thresholds below come from default configuration in the published `yundun-dsc-service` code. Online Diamond configuration can override version thresholds, so these values are for explanation and initial screening. Current results from `CheckDataMaskingInstance`, `GetInstanceAttribute`, and `ListDataMaskingEncryptionAlgorithms` are authoritative.

| Product or engine | Base version | Algorithms | KMS | Other restrictions |
| --- | --- | --- | --- | --- |
| RDS MySQL | MySQL 5.7/8.0; default minimum base kernel date `20240731` | Default AES-128-GCM; AES-256-GCM and SM4-128-GCM require kernel date `20241231` or later by default | Requires kernel date `20241231` or later by default; local disks/ephemeral SSDs are unsupported | Not read-only; status `Running`; algorithm changes supported |
| RDS PostgreSQL | Only `16.0`; default minimum kernel date `20241230` | AES-256-GCM only | Unsupported | Extension installed in the target database; status `Running`; algorithm changes unsupported |
| PolarDB MySQL | MySQL 5.7/8.0; default minimum proxy version `2.8.36` | Default AES-128-GCM; AES-256-GCM and SM4-128-GCM require proxy version `2.9.12` or later by default | Unsupported | Both cluster and proxy available and status `Running`; algorithm changes unsupported |
| PolarDB PostgreSQL | Major version `14`; default minimum Revision `2.0.14.15.31.0` | AES-256-GCM only | Unsupported | Revision has at least six components; status `Running` |
| PolarDB Oracle | Major version `14`; default minimum Revision `2.0.14.15.31.0` | AES-256-GCM only | Unsupported | Revision has at least six components; status `Running` |
| PolarDB-X 2.0 Enterprise | Default minimum main version `5.4.20`, kernel date `20250714` | AES-128-GCM and SM4-128-GCM; AES-256-GCM requires `5.4.21-20260414` by default | Requires `5.4.21-20260414` by default | Not `ReadOnly`; status `Running`; algorithm changes supported |
| PolarDB-X 2.0 Standard | Default minimum main version `8.4.21`, kernel date `20260423` | AES-128-GCM and SM4-128-GCM; AES-256-GCM unsupported | Requires `8.4.21-20260711` by default | Not `ReadOnly`; status `Running`; algorithm changes supported |

## Server Behavior

- The supported product codes are strictly `RDS`, `POLARDB`, and `PolarDBX2`, with Product IDs 5, 8, and 27 respectively.
- The server does not trust the engine supplied by the frontend; during creation it selects the exact Handler from remote instance attributes.
- Algorithm precedence is: an explicit request value, the current algorithm of existing rules, then the Handler's default algorithm.
- Supplying `EncryptionKeyId` enters KMS mode. A new KMS rule has no previous key to inherit, so a Key ID must be explicitly supplied.
- Explicitly selecting `client_key` clears any inheritable KMS Key ID.
- A KMS key must exist and be enabled, and the instance version and storage type must support KMS.
- `SubRuleList` and `InstanceId` are required; the database, table, and columns of each subrule must be nonempty.
- The server defines no explicit hard limit on the number of subrules. Do not use this to make arbitrarily large requests; also observe POP size limits and the 100 requests/second limit.
- Quota validation requires configured columns + unique columns added by this request + remotely authorized columns to stay within the purchased quota. Pay-as-you-go instances are rejected.
- A duplicate submission is rejected while the same column is processing and has not exceeded the approximately 60-second processing timeout. A distributed lock serializes creation, updates, and deletion for the same instance.
- After creation is persisted, execution proceeds asynchronously through a message queue. `Processing` or terminal `Failed` may appear after request acceptance and before final success.

## Allowlist Expiration

- `PRESERVE`: retain existing account expiration times; new accounts default to indefinite validity.
- `CLEAR`: remove expiration times from the selected accounts.
- `SET`: set the same expiration time for this request's `UserList`.
- `SET` requires a future Unix timestamp in milliseconds; the server truncates it to seconds.
- The upper limit is `2038-01-01T10:10:10Z`, or `2145953410000` milliseconds.

## Account Permission Matrix

| Product or engine | `fullAccess` | `restrictedAccess` | `noneAccess` |
| --- | --- | --- | --- |
| RDS MySQL | Supported | Supported | Supported only when an effective `client_key` rule currently exists |
| RDS PostgreSQL | Supported | Supported | Unsupported |
| PolarDB MySQL/PostgreSQL/Oracle | Supported | Supported | Unsupported |
| PolarDB-X 2.0 | Supported | Supported | Unsupported |

Only `fullAccess` may include `ExpireTimeOperation`. For roles other than `fullAccess`, even explicitly sending `PRESERVE` is rejected by the server, so the scripts completely omit both expiration fields.

## Kernel Upgrades

- `UpgradeTime` allows only `Immediate`, `MaintainTime`, and `SpecifyTime`.
- `SpecifyTime` must include a future Unix-millisecond `SwitchTime`; the other two modes must omit this field.
- PolarDB-X 2.0 supports only `Immediate` and `MaintainTime`.
- The target `KernelVersion` must be returned by a current `ListMiniEngineVersions` query.
- AMP's upgrade response exposes only `RequestId`, not the backend task ID. The final version can only be observed through `GetInstanceAttribute.CurrentKernelVersion`; maintenance-window or scheduled upgrades will likely return `PENDING` first.
