# Error recovery

Classify the failure before taking another action. Retry at most once after a specific, verified remediation; never blind-loop writes.

## Recovery classes

| Class | Meaning | Allowed behavior |
|---|---|---|
| `retryable_once` | The intended DomainCLI leaf and target are unchanged, and one verified remediation exists. | Apply that remediation, then retry the same read or preflight once. |
| `terminal_current_step` | Authentication is blocked, target is inapplicable, permission is denied, the friendly leaf is unsupported, preview failed, or confirmation is missing. | Stop, report the confirmed state, and provide the exact safe DomainCLI next step. |
| `ambiguous_write` | A write may have reached the service, but no terminal result was returned. | Perform same-target readback or task lookup only; no automatic resubmission. Any later attempt needs resolved prior outcome, a new same-target preview and fresh confirmation. |

A different credential, target, product namespace, generated OpenAPI action, SDK, HTTP request, or console workflow is not recovery. It changes the execution contract.

| Signal | Interpretation | Recovery |
|---|---|---|
| `unknown command`, `unexpected positional argument`, or `unknown flag` | Installed command contract differs from the planned invocation. | Run the exact parent or leaf `--help`, correct the path/flag, and retry only if semantics are unchanged. |
| DomainCLI below `0.9.8` or parent CLI below `3.5.1` | Unsupported runtime baseline. | Stop and ask for supported versions to be installed. Newer compatible versions are allowed; do not emulate missing commands. |
| Parent CLI cannot be located or inspected | Plugin cannot safely delegate OAuth/profile work. | Report the resolved binary/version problem. Do not call an untrusted wrapper or read credential files manually. |
| Login required or refresh rejected | No usable intended credential source for this command. | Run or return `aliyun domain login`, then retry the original cloud command once. A missing OAuth profile alone is not failure when the installed leaf can reuse the same intended standard credentials. |
| Login waits for a browser callback that cannot complete | The runtime cannot finish interactive OAuth. | Stop as an authentication handoff after one attempt. Do not repeat login or continue with another credential. |
| OAuth profile shown as `Invalid` only in `aliyun configure list` | No currently materialized temporary credential may exist. | Let the intended cloud command attempt refresh; do not switch profile based only on this table. |
| `Forbidden.RAM` or permission denied | Identity is known but lacks an action, or the API disallows that principal type. | Report the exact authorization action and consult the command-scoped permission reference. Do not repeat login unless authentication also failed. |
| Required input missing, malformed, or inaccessible | The requested operation cannot be formed safely. | Inspect leaf help, ask for the minimum missing non-secret input or protected input-file path. Return `awaiting_input`; do not fabricate values or submit a write. |
| Throttling/rate limit on a read or preview | Temporary upstream request pressure, not an identity problem. | Honor a returned retry delay only within the current deadline, then retry the same read/preview at most once. Never retry a possibly accepted write. |
| System/transport error | Read failed, or write acceptance may be unknown. | For a read/preview, retry at most once within the deadline only if transient and not marked non-retryable; for a write, perform same-target readback only and report `outcome_unknown` if unresolved. |
| `INTERNAL` or response transformation/schema failure, especially `retryable=false` | The tool could not produce a reliable result; this is not automatically an input or ownership failure. | Stop as `blocked_runtime` with the sanitized error and same-target handoff. Do not change parameters because a required field is missing from an upstream response, repeat a non-retryable command, or bypass DomainCLI to inspect raw APIs. |
| Region or endpoint rejected | Wrong/stale plugin or an explicit override bypassed DomainCLI routing. | Remove custom `--region`/`--endpoint`, confirm versions, inspect leaf help, then retry once. |
| Price unavailable | Public pricing did not return a complete quote. | Preserve the reason. Do not substitute zero or extrapolate. Continue only along a CLI-supported browser checkout path if the user wants it. |
| Browser cannot open | Local desktop handoff failed. | For checkout, return only a safe official URL emitted by DomainCLI. For OAuth, return the same-source login command, not an authorization URL, callback code or PKCE/state parameters. Never fabricate a URL. |
| Async operation accepted | The request was submitted, not completed. | Save the task/order/deployment ID and use the corresponding task/status command. |
| Write timed out or returned ambiguous transport failure | Server outcome is unknown. | Read back the target or query the task before any retry. |
| DNS preview returns an error or no usable `plan_id` | No executable anti-stale plan exists. | Stop before confirmation. Fix authentication, permissions, or input, then generate a new DomainCLI preview. |
| DNS create reports an existing record | The desired state may already exist or may require an update. | Read the exact owner/type/line. Report `no_change` if value and TTL match; otherwise use the friendly `dns update` preview. |
| `no_change` or already in target state | Idempotency succeeded. | Report that no write was needed; do not force another mutation. |
| Upstream/mock/unsupported capability | DomainCLI has no production implementation or upstream rejected the operation. | State the limitation and stop. Do not bypass it with raw API calls. |

Classify by the specific error code before considering retryability. `retryable=false` forbids automatic retry; it does not turn a known permission or user-input error into an internal runtime error. A generic suggested next command cannot override that flag.

Only structured success output for the exact target advances the workflow. Exit attempts, command text, field-name mentions, and unrelated successful readbacks do not. Final error reports should include the attempted friendly leaf command without secrets, error class/code, confirmed state, safe next command, and whether any write may have been accepted.

## Bounded execution and handoff

Set terminating deadlines in the execution tool rather than inventing unsupported CLI flags. A tool's yield interval only returns control; it is not a process deadline. The default total execution budget for one Skill activation is 120 seconds, including local preflight, cloud calls, polling, and recovery. At the boundary, return the best supported terminal result; do not start another command, wait, poll, artifact write, or HITL request. Track elapsed time and terminate only this activation's owned process/session when the deadline expires. If the tool cannot provide safe termination, do not start an interactive login or indefinite stream; hand off instead. Use at most 20 seconds for local version/help/status, 60 seconds for a single cloud read or preview, and 120 seconds for a potentially completing browser login. For a confirmed write or generation stream, respect the leaf's documented duration but impose a finite tool deadline no longer than the remaining activation budget; interruption means acceptance may be unknown, not permission to resubmit. A stricter caller/platform deadline takes precedence.

Follow asynchronous work with its returned ID and supported read-only task/status leaf. Poll no more than 10 times and no longer than 120 seconds of elapsed time in one activation. Yield between short polls; return immediately on terminal success/failure, required user input, authentication failure, or external review. At the budget boundary, stop as `pending_external` with the last observed state and resume command. Do not poll ICP manual review or DNS propagation until completion, and do not call a stream reconnect merely to evade the wait budget.

For account-wide reads, follow the CLI's actual pagination/cursor until the requested scope is covered, within a total budget of 20 pages or 120 seconds per activation. Stop on a repeated cursor/page, an empty page with no progress despite a continuation marker, or changed target filters. Label budget or no-progress results partial, preserve the last valid continuation and reason, and never claim a global sort or complete list from one page. Distinguish server-side sorting from client-side sorting over a fully retrieved scope.

Use a Skill-level result summary without relabeling the CLI's underlying status:

| Skill result | Evidence required |
|---|---|
| `completed` / `no_change` | Same-target final readback or a documented idempotent result. |
| `awaiting_input` / `awaiting_confirmation` | Missing input or a successful preview awaiting a fresh reply; no write submitted. |
| `blocked_authentication` / `blocked_target` / `blocked_capability` | The exact failed precondition; no fallback or submission. |
| `blocked_permission` / `blocked_parameter` | The intended principal lacks permission, or invalid inputs remain after the single permitted remediation; no write submission. |
| `blocked_runtime` / `blocked_fixture` | A non-retryable or unrecognized runtime response, or required evaluation resource/input is unavailable. Neither proves a domain is absent nor completes its functional lookup. |
| `pending_external` | Accepted task/browser/review handoff with the last observed status and safe resume command. |
| `outcome_unknown` | A write may have been accepted but readback did not resolve its outcome. |

Report the exact non-secret target, last CLI status/error code, reason, and next safe step in prose, then end with the four standalone lowercase `key=value` lines defined in the entrypoint's **Fast terminal result contract**. Do not use uppercase-only labels or prose as a substitute for the footer. These are Skill summary fields, not invented CLI flags or proof of execution. A safe blocked result is not functional completion; keep both facts explicit. For supplied-state decisions, identify the given status as supplied rather than a last verified cloud response.

An input/confirmation request or external handoff ends the current step with a final answer. Do not keep a tool process or background loop waiting for a user reply. A runner should score this single-step outcome separately from any later approved continuation; never execute a write merely to make the runner finish.

In a multi-step domain request, report each independent step separately. A successful discovery with zero matching results is a completed empty query; dependent detail/preview steps are unexecuted because no identifier exists. Do not repeat an unchanged empty query, invent a record/template/task ID, or claim the downstream API succeeded. In a supplied-state decision task, describe readback and safety boundaries without executing hypothetical operations or requiring login.
