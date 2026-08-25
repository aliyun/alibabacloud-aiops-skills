# Error recovery

Use the structured error class and request ID to choose the next action.

| Signal | Meaning | Response |
|---|---|---|
| HTTP or envelope `401`, `AUTH_CREDENTIAL_NOT_FOUND` | Missing, expired, revoked, or cross-Region token | Verify Region, endpoint, and token validity; rotate through the Dgate console if needed |
| `403` or `ACCESS_DENIED` | Identity lacks permission for the target operation | Check real permissions and request target authorization; do not retry unchanged |
| `429` | Client or gateway rate limit | Respect `Retry-After` or the structured retry delay and back off |
| Policy-blocked execution status | Policy blocked the execution | Report the exact status, statement, target, policy reason, and request ID; treat the gate as terminal and do not ask for approval, override it, or retry |
| `TIMED_OUT_WAITING` | Execution exceeded the synchronous wait budget | Report the request ID and narrow the query or adjust the documented wait budget |
| `RESULT_TRUNCATED` or `result.truncated=true` | Only a bounded preview is present | Narrow columns, predicates, or row count; do not present the preview as complete |
| Multiple unresolved resources | Identity is ambiguous | Report distinguished candidates and the knowledge gap, then stop without further interaction |

For a historical CLI failure, use `dgate trace list`, `dgate trace show`, or `dgate trace turn`. Preserve the request ID in the answer so operators can correlate the gateway audit trail.

Retry only when the error is explicitly retryable. Repeating authorization failures or rejected operations without changing their cause wastes calls and can create misleading audit noise.
