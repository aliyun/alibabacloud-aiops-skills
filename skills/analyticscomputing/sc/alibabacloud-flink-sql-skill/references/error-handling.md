# Flink SQL Lifecycle Error Handling

Read this document only after a command fails.

## 1. Failure Signals

Treat an operation as failed when either condition applies:

- The CLI exits with a nonzero code.
- The JSON output contains `success: false`.

Do not continue with later workflow steps until the failure is handled.

## 2. Parse Before Handling

Extract these fields from the response:

- `operation`
- `error.code`
- `error.message`
- `request_id`, when present.

## 3. Recovery Matrix

| Error code | Meaning | Recovery action |
|------------|---------|-----------------|
| `SafetyCheckRequired` | A mutating or destructive command is missing `--confirm` | Verify whether the user authorized the exact target. Valid advance confirmation in the current request satisfies the high-risk gate; otherwise obtain specific confirmation before retrying with `--confirm` |
| `ValidationError` | A parameter is missing or invalid | Ask only for the missing value, then retry |
| `SkillIdentityError` | The skill manifest or session ID is missing or invalid | Stop cloud calls and repair the identity according to [configuration.md](configuration.md#skill-identity-and-session) |
| `ConfigurationExists` | The target file for `config_init` already exists | Confirm whether the user intends to replace the single default scope; after confirming the change, add `--overwrite` |
| `ResourceNotFound` | The ID or scope is wrong, or the resource has been deleted | Verify the scope and use `list_*`/`get_*` to locate the correct resource |
| `PermissionDenied` / `Forbidden.RAM` | The RAM Policy grants insufficient permissions | Stop the operation and check the RAM Policy and granted permissions in the [RAM console](https://ram.console.aliyun.com/) |
| `MissingCredentials` | No credentials are available | Ask the user to configure the default credential chain locally, preferably with `aliyun configure --mode OAuth --profile default`; never request credentials in the conversation |
| `ResourceConflict` | A resource is duplicated or conflicts with another resource | Choose another identifier, or clean up the existing resource after obtaining authorization |
| `QuotaExceeded` | A service quota has been reached | Stop, report the quota, and ask whether to clean up resources or request a quota increase |
| `GitConfigurationError` | The Git repository URL, local path, or branch is invalid | Correct the non-sensitive Git settings and initialize again; never store a token, password, or private key in the configuration |
| `GitSyncError` | Git clone/fetch/checkout/commit/push failed, or the local repository is unsafe | Preserve any successful platform result; inspect origin, branch, local changes, and local Git credentials, then retry synchronization manually after repair |
| `MetricAuthError` / `MetricQueryError` | Cookie authentication or a VVP historical Metric query failed | Follow [job-observability.md](diagnosis/job-observability.md) to supply a Cookie, or verify permissions, network access, query scope, and the actual error |

## 4. Standard Recovery Flow

1. Briefly report the failure (`operation` + `code` + `message`).
2. Propose one concrete next action.
3. After the user confirms, retry once with corrected input.
4. If the retry still fails or recovery is impossible, stop and ask how to proceed.

## 5. Safety Constraints During Recovery

- Never claim success after receiving a failure response.
- Do not hide the original error code or message.
- Do not guess unknown IDs or fabricate parameters.
- Do not perform destructive cleanup without explicit deletion authorization.
- Git recovery must follow the repository-protection and credential rules in [git-sync.md](git-sync.md).

## 6. Response Template

Use the “Operation Failed or Result Unconfirmed” template in [output-schemas.md](output-schemas.md). Include at least the command, `error.code`, key `error.message`, request ID, completed and unexecuted steps, and one safe recovery action that can be run directly.
