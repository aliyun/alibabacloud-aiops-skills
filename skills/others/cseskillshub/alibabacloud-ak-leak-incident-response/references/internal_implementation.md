# Internal Implementation Details

This document contains technical implementation details referenced by the entry script. These are NOT capabilities the Agent should invoke directly.

## API Sequence

The entry script executes APIs in this order:
1. Security Center `DescribeAccesskeyLeakList` (notification check)
2. ActionTrail `LookupEvents` (audit leaked AK operations)
3. RAM `GetAccessKeyLastUsed` (AK last usage)
4. RAM `ListUsers` / `ListAccessKeys` (chain tracing)
5. STS `GetCallerIdentity` (account derivation)

## Dual Backend

- **CLI backend (preferred):** when the `aliyun` binary is on `PATH`, calls run as `aliyun <product> <Action> …`
- **HTTP backend (fallback):** when the CLI is absent, calls are signed with OpenAPI V3 signature (ACS3-HMAC-SHA256) via `requests`

Both backends return identical raw API JSON. Force backend with `AK_LEAK_BACKEND=cli|http`.

## Error Recovery Details

| Error | Cause | Script Resolution |
|-------|-------|-------------------|
| `NoPermission` / `Forbidden.NoPermission` (Security Center) | credential lacks `yundun-aegis:DescribeAccesskeyLeakList` (RAM action prefix is `yundun-aegis:`, NOT `sas:`) | log `[WARN]` and continue to ActionTrail |
| `MissingParameter: Parameter UserName is required` (`GetAccessKeyLastUsed`) | RAM-user / assumed-role callers must pass `UserName` | auto-discover owner (STS `GetCallerIdentity` or ActionTrail reverse-lookup), retry with `--UserName <owner>`; if unknown, last-used = `N/A` |
| `InvalidAccessKeyId` | profile/env AK/SK invalid or revoked | re-run `aliyun configure` or fix env |
| Empty event list | no activity in time window | extend `--days` or verify account |

## Internal Filter Parameters

- Security Center: `Query=ak:<AK>`
- ActionTrail: `EventAccessKeyId=<AK>`, `User=<sub-user>`
- RAM: `UserAccessKeyId=<AK>`

## 14 High-Risk Services

Ram, CloudSSO, ECS, AasSub, Eci, SMS, ECD, BDRC, RdsData, PTS, Alidns, EHPC, Dms, Notifications.

CloudSSO/AasSub/Notifications are only visible via the `User` filter.

## Known Limitations

| Feature | Status | Workaround |
|---------|--------|------------|
| Deleted-AK lifecycle traces | Unsupported | Check ActionTrail events |
| AK ban/disable status | No public API | Infer from `errorCode` (`InvalidAccessKeyId.Inactive`) |
| Security Center alerts | Returns flagged leaks only | Empty → skip |
| AK last-used products | No direct API | Infer from ActionTrail event sources |
| Login domains | Unsupported | No public API |

## Observability

Implemented in `scripts/_cli.py` via `session_id()` + `user_agent()`, applied on both backends:

- `session_id()` returns a 32-char lowercase-hex id, generated once (`uuid.uuid4().hex`) and cached for the process, so every call in one run shares it. Env `AK_LEAK_SESSION_ID` (32 hex chars) overrides it.
- `user_agent()` returns `AlibabaCloud-Agent-Skills/alibabacloud-ak-leak-incident-response/{session-id}`.
- **CLI backend** (`_call_cli`): appends `--user-agent <UA>` to every `aliyun` command.
- **HTTP fallback** (`_call_http`): sets the `User-Agent` request header after V3 signing (UA is intentionally not a signed header).
- The entry script logs the session-id + UA once at startup to stderr.
