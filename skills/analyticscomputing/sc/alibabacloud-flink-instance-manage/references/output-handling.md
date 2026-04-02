# Output handling

`scripts/instance_ops.py` writes JSON results. Always inspect:

- `success`: true or false
- `operation`: operation name
- `data`: successful response payload
- `error.code` and `error.message`: failure diagnostics
- `confirmation_check` (create operations): auditable confirmation gate status

## Retry policy (strict)

Never use blind retries. Maximum attempts for the same command: **2 total**
(initial run + one corrected retry).

1. `error.code == SafetyCheckRequired`
   - Cause: missing confirmation flag.
   - Action: add the required flag from `required-confirmation-model.md` and retry once.
2. Input/argument issues (`MissingParameter`, `ValueError`, invalid format)
   - Action: correct parameters according to `error.message`, then retry once.
   - If error indicates missing credentials, fix default credential chain and retry once.
3. Permission issues (`AccessDenied`, `Forbidden`, `Unauthorized`)
   - Action: do not retry until permissions are fixed; report required RAM policy.
4. Transient platform issues (`Throttling`, timeout, internal error)
   - Query operations: retry once after short backoff.
   - Create operations: first run a read check to verify whether request already took effect;
     only retry once if not applied.
5. Create command reports success, but read-back verification fails
   - Treat as incomplete, not successful.
   - Check region/instance/resource identifiers first.
   - Run one corrected create retry only when verification confirms state did not change.
6. Idempotent result handling
   - `AlreadyExists`: success only if read-back fully matches expected target state.
   - Any mismatch after read-back means incomplete task.
7. Create command fails with business mismatch (`NamespaceNotFound`, missing required options)
   - Action: stop and ask user for clarification.
   - Do not switch to a different operation automatically.
8. `create_namespace` fails with `InsufficientResources`
   - Action: mark lifecycle chain as not completed; provide next action.
   - State clearly that this skill does not support instance scale-up/update.
   - Ask user to manually expand/reallocate resources, then retry.
   - Do not label overall flow as completed.

If the corrected retry still fails, stop and return a clear remediation message
instead of continuing attempts.

## Eventual consistency read-back

After successful create, read-back may lag briefly. Use this sequence:

1. immediate read check
2. short backoff, second read check
3. short backoff, third read check

Do not perform extra create retries before completing these read checks.

## Completion rule

Do not conclude task success from create response alone. Success requires:

1. create response success
2. read-back state verification success

## Final response template (recommended)

Use a concise closure report:

- `operation`: target operation name
- `create_result`: success/failure + key error code when failed
- `verify_result`: read-back result summary
- `status`: completed/failed/not_ready
- `next_action`: remediation when not completed

For lifecycle flows requiring both instance and namespace create:
- `status=completed` is allowed only when both create operations succeeded and were verified.
