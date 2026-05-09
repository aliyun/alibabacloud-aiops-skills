# Error Handling

Use this file only when command execution fails.

## 1) Failure Signal

Treat the operation as failed when either condition is true:

- CLI returns non-zero exit code
- JSON output includes `success: false`

Do not continue workflow steps until failure is handled.

## 2) Parse First, Then Act

Extract these fields from response:

- `operation`
- `error.code`
- `error.message`
- `request_id` (if present)

## 3) Recovery Matrix

| Error Code | Meaning | Recovery Action |
|------------|---------|-----------------|
| `SafetyCheckRequired` | mutating/destructive command missing `--confirm` | ask explicit approval, then retry with `--confirm` |
| `ValidationError` | missing or invalid parameter | ask only for missing value, then retry |
| `ResourceNotFound` | wrong ID/scope or resource deleted | verify scope, run `list_*`/`get_*` to locate correct resource |
| `PermissionDenied` / `Forbidden.RAM` | insufficient RAM policy | stop; check RAM policies and attached permissions in [RAM Console](https://ram.console.aliyun.com/) |
| `MissingCredentials` | credentials not available | ask user to configure credentials (`aliyun configure`) |
| `ResourceConflict` | duplicate or conflicting resource | choose another identifier or clean up existing resource (with approval) |
| `QuotaExceeded` | service quota reached | stop, report quota limit, ask user whether to clean up or request increase |

## 4) Standard Recovery Flow

1. Report concise failure summary (operation + code + message).
2. Propose one concrete next action.
3. If user confirms, retry once with corrected input.
4. If still failing or unrecoverable, stop and ask user how to proceed.

## 5) Safety Constraints During Recovery

- Never claim success after a failed response.
- Never hide original error code/message.
- Never guess unknown IDs or fabricate parameters.
- Never execute destructive cleanup without explicit delete approval.

## 6) Response Template

```text
Operation failed.
- Command: <subcommand>
- Error: <error.code>
- Message: <error.message>
- Request ID: <request_id or N/A>

Suggested next step: <single actionable step>
```
