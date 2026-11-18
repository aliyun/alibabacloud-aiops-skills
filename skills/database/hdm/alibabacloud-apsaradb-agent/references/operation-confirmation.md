# Live service confirmation

This client calls ApsaraDB Agent through DAS; the remote service selects its product
Skill, performs discovery/pricing, prepares parameters and enforces its operation
permissions. Do not rebuild a local positive API allowlist or product-field schema.

## Start and review the actual card

Save the user's non-secret business request in an absolute query file. Initialize
and export the versioned Skill observability values as described in SKILL.md.
Start one job, using a new absolute directory:

```bash
python3 "$SKILL_ROOT/scripts/agent_job.py" start \
  --job-dir "$JOB_DIR" --query-file "$QUERY_FILE" -- \
  --source "$SOURCE"
python3 "$SKILL_ROOT/scripts/agent_job.py" wait --job-dir "$JOB_DIR" --seconds 30
```

For a related turn, also pass the actual earlier `--session-id` and same source.
Readonly-only tasks instead append `--extra-info '{"mode":"readonly"}'`; they
cannot approve cards. The job owns its confirmation directory; never substitute
another job's inbox or edit pending/decision files directly.

`state=awaiting_confirmation` means the service emitted a real pending
`humanConfirm` event. Read the current `stdout` file as well as the `confirmation`
object in the status: the service's preceding answer may contain the final quote,
impact or service agreements that are absent from the API parameters. Present
those details together with `tool` and masked `arguments` and ask for the user's
approval/rejection of **this concrete card**. Do not finalize the business task or
keep silently polling while human input is required.

A request to select a recommended offer can initiate service order preparation;
it does not authorize the client to approve the resulting card. Do not add a
second approval step before service preparation. The final live-card decision is
the authorization. A text table or service statement that a card exists is not
an actual pending event.

## Submit the decision and keep the same stream

After the user explicitly decides, copy the ID/session/hash from that pending
status (not from an old report) and submit exactly once:

```bash
python3 "$SKILL_ROOT/scripts/agent_job.py" confirm \
  --job-dir "$JOB_DIR" \
  --confirmation-id "$CONFIRMATION_ID" \
  --session-id "$CARD_SESSION_ID" \
  --plan-sha256 "$PLAN_SHA256" --decision approve
```

Use `--decision reject` for rejection. These identifiers are supplied by the tool,
not questions the user must answer. The digest binds the actual operation and
full parameter values, including nested structures. Changed arguments or a new
card require a new decision; there is no wildcard or blanket approval. Decisions
are exclusive: conflicting/duplicate decisions, stale cards and dead jobs fail.
The client consumes the local decision before invoking the official DAS callback,
passing only confirmation ID, boolean decision and original session. It never
overrides the server's tool arguments or invokes a product write API.

The local card deadline is 90 seconds, within the service's default 120-second
confirmation wait. Review and ask promptly. Rejection or deadline expiry sends
no approval. If the user answers too late, do not reuse the old ID or silently
restart; explain that the card expired. Starting a newly confirmed request after
expiry requires the user's explicit request and verification that the previous
operation did not execute. Different server timeout configurations may expire
sooner; the callback response remains authoritative.

Continue `wait` on this same job, then `result`. A successful user rejection is reported as `outcome=cancelled`, with a nonzero helper exit and `request_succeeded=false`; that means the operation did not complete, not that the client should retry it. The original request may emit
another operation card. Each needs a fresh user decision; completing one operation
never automatically approves the next. A confirmation acknowledgement proves
only delivery of the decision, not product execution.

## Forbidden actions and sensitive fields

Deletion/drop/truncate/purge, resource/connection release and disabling deletion
protection are refused regardless of service availability or user approval.
API names are checked in PascalCase/kebab-case; CLI wrapper cards also inspect
the underlying action. Known deletion-protection settings are checked even in
nested/JSON-encoded arguments. Do not disguise destructive work in generic
queries or another operation. Removing tags and cancelling operation tasks are
not resource deletion. Unknown business semantics require clarification from the
service rather than assuming that a harmless API name proves a harmless effect.

Do not collect passwords, AK/SK or authentication tokens in local queries or
approval arguments. If the service provides a supported account-management flow,
secret fields in pending metadata are masked and only their original digest is
retained. Do not reveal them or ask the user to paste them. Use a secure service
or console input channel when secret entry is necessary. `ClientToken` is a
non-secret idempotency identifier; it does not grant permission or safe retries.

## Verify the business result

After the stream finishes, retain its exit status, SessionID and timestamps.
The official CLI may end normally at EOF without an explicit Done marker. Exit 0
with a parsed response (and post-approval content for an operation) completes the
request; it does not verify the business result. `[StreamCompleted]` describes this
normal EOF, and `[OperationVerificationRequired]` requires independent verification.
Nonzero CLI exits, parser errors, or missing/unknown operation responses remain
failed requests. Independently query the
specific resource/order/task with readonly mode, using returned identifiers.
For orders distinguish accepted, unpaid, provisioning and ready. For restarts,
parameters, privileges, networking or tasks, verify their corresponding stored
state/task completion. Do not mark an intended operation successful from a plan,
a callback acknowledgement, HTTP 200 or a different session's output.

Never replay an accepted/uncertain write or callback, change names to retry, or
perform automatic destructive cleanup. Follow the remote buying Skill's returned
payment/result links and phase boundaries; do not reconstruct a local creation
API, force static network defaults or replace an order workflow with CLI writes.
