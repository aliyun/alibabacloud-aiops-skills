# Output handling

`scripts/instance_ops.py` writes JSON results. Always inspect:

- `success`: true or false
- `operation`: operation name
- `data`: successful response payload
- `error.code` and `error.message`: failure diagnostics

## 4.1 Retry policy (strict)

Never use blind retries. Maximum attempts for the same command: **2 total**
(initial run + one corrected retry).

1. `error.code == SafetyCheckRequired`
   - Cause: missing confirmation flag.
   - Action: add the required flag from `required-confirmation-model.md` section 2.2 and retry once.
2. Input/argument issues (`MissingParameter`, `ValueError`, invalid format)
   - Action: correct parameters according to `error.message`, then retry once.
   - If error indicates missing credentials, fix the default credential chain
     (for example, `aliyun configure` or RAM role) and retry once.
3. Permission issues (`AccessDenied`, `Forbidden`, `Unauthorized`)
   - Action: do not retry until permissions are fixed; report required RAM policy.
4. Transient platform issues (`Throttling`, timeout, internal error)
   - Read operations: retry once after short backoff.
   - Write operations: first run a read check (`describe*`/`list*`) to verify
     whether the previous request already took effect; only retry once if not applied.
5. Write command reports success, but read-back verification fails
   - Treat as incomplete, not successful.
   - Check region/instance/resource identifiers first.
   - Run one corrected write retry only when verification confirms state did not change.
6. Idempotent result handling
   - `AlreadyExists`: not automatic success; success only if read-back fully
     matches expected target state.
   - `NotFound` on delete/untag: success only if read-back confirms absence.
   - Any mismatch after read-back means incomplete task.
   - Lifecycle continuity: do not switch to another resource ID/name to bypass a
     failure unless user explicitly approves the substitution.
7. Write command fails with business/semantic mismatch (`NamespaceNotFound`, missing `--ha`, incompatible billing mode)
   - Action: stop and ask user for clarification.
   - Do not switch to a different write operation automatically.
   - Example: `modify_namespace_spec` failure must not auto-trigger `create_namespace`.

If the corrected retry still fails, stop and return a clear remediation message
instead of continuing attempts.

### Hard guardrail: no cross-operation retries

Retry can only re-run the same operation with corrected parameters.
Any operation change (`modify_*` -> `create_*`, `delete_*` -> `create_*`, etc.)
requires explicit user approval before execution.

## 4.2 Eventual consistency read-back

After a successful write, read-back may lag briefly. Use this sequence:

1. immediate read check
2. short backoff, second read check
3. short backoff, third read check

Do not perform extra write retries before completing these read checks.

## Completion rule

Do not conclude task success from write response alone. Success requires:

1. write response success
2. read-back state verification success

## 4.3 Final response template (recommended)

Use a concise closure report:

- `operation`: target operation name
- `write_result`: success/failure + key error code when failed
- `verify_result`: exact read-back evidence
- `final_status`: completed/incomplete
- `next_action`: remediation when incomplete
