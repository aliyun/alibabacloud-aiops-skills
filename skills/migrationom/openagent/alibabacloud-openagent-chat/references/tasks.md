# Tasks, conversations, and recovery

## Ordinary work

Run `task new` once for a new host conversation. It generates a local UUID without accessing an account. Submit work with `task ask --local-session <local-uuid> --text <business-request>`. Retain the returned `local_session` for follow-ups, recovery, and a resumed host conversation. The client creates the cloud conversation on first use, saves its binding, and journals a `turn_ref` for each logical request. Existing saved bindings remain usable after an upgrade.

A new host conversation or an explicit request to start over uses `task new`; a changed topic alone does not require a reset. Do not invent identifiers, use an account or project label, or select a global last-used conversation. Independent host conversations can run in parallel with separate local UUIDs. Within one conversation, resolve or recover preceding work before a conflicting submission; do not create a replacement to bypass a pending task or decision.

The client accepts direct text, a UTF-8 file with `--input-file <path>`, or standard input with `--input-file -`. Files are optional. Use structured subprocess arguments or correct shell quoting, and never include secrets.

Normal output contains the business answer, status, and recovery identifiers. Internal tool arguments, results, activity payloads, and reasoning are omitted and do not request local execution. A completed Run may still ask a natural-language question; completion alone does not prove that a resource change succeeded.

Call output raw only when stdout is preserved unchanged; label derived explanations separately. When recording actions, include failures and corrections, and distinguish received counts from displayed counts. Attribute service statements to the service, separately from independent verification. Without exposed internal calls or independent evidence, do not claim to have verified that no internal query or re-query occurred.

## Questions and approvals

Present actual questions using the host's question card or equivalent interaction when available. Preserve meaning, scope, constraints, choices, consequences, and expiry. Do not omit material caveats, invent choices or decision identifiers, or submit a suggested default on the user's behalf. Silence and timeouts are not approval.

Without a structured decision, send the actual natural-language reply using `task ask` in the same local conversation. Confirmation, refusal, and clarification use the client-managed MESSAGE reference. Present a confirmation request and wait for the user's answer rather than generating confirmation text for them.

For structured questions, use the original `interactions[].data.questions`, preserving question IDs and option values. Do not query status merely to recover choices already returned. When a structured decision is pending, use `describe respond` for its input format, collect actual responses for all pending decisions, and submit them with `task respond --session <conversation> --run <task> --text <answers-json> --authorization-ref <user-decision-reference>`. Standard input and input files also work. The client checks identifiers and expiry. Explain an operation's business effect before asking for a decision. If its resource, action, or settings change, present the revised operation and obtain authorization for that version; one approval is not permanent permission.

For externally managed approval, show the returned destination and instructions, whether text or an approval card. The conversation stays blocked pending that decision. Never fabricate external approval or submit a local answer or cancellation on its behalf. Ask whether the user wants continued observation, continue only after agreement, and stop when asked. Authorization to submit a proposal for review does not authorize execution; present any later request to exceed that scope.

After the external decision, recover the original local conversation. The client checks for a completed follow-up task without replaying the resource request. Report the actual result: it may be refusal, withdrawal, or a request for final confirmation rather than execution. Obtain any requested confirmation before continuing in the same conversation.

## Recover without replaying

- `task local-status --local-session <local-uuid>` reads the saved binding and latest submission journal.
- `task status --session <conversation> --run <task>` reads cloud state.
- `task watch --session <conversation> --run <task>` resumes observation.
- `task result --session <conversation> --run <task>` retrieves the result.
- `operation status --operation-ref <reference>` inspects a specific submission.

After a disconnect or process restart, use `task recover --local-session <original-local-uuid>`. It reads the saved binding, checks the original task, and retrieves available results. Follow its observation guidance if still active. Repeating the same submission reference retrieves the saved outcome rather than submitting again. If recovery identifiers were not saved, report the unconfirmed operation and stop; other local files or conversations are not substitutes. Stopping local observation does not cancel cloud execution.

Missing original identifiers are a stop condition, not a reason to start over. Do not recommend creating a new local UUID or cloud conversation and sending the original request again as a recovery method, required step, or only path forward. This applies to all delivered reports, examples, scripts, action logs, and subsequent advice, even when the final reply correctly stops and no new request was executed. Explain only the recovery paths available if the user later supplies the original identifiers. A separate, actual user request may authorize distinct new work, but it must be identified as new work, keep the old outcome unknown, and never bypass that uncertainty by duplicating the old request.

Use `task cancel` only for the user's explicit cancellation request, with the exact saved identifiers and actual authorization reference. The client allocates the cancellation reference; verify the eventual state. Cancellation and observation may run concurrently. Resolve pending decisions as described above before new work.

Resolve the cancellation target from the current host conversation's saved binding or the user's explicit selection of the original Session and Run. If neither is available, ask for the target and stop. Do not cancel a task discovered in a list merely because it is the only running task, is the newest, or has a plausible title. Connection setup consent is not target confirmation. An instruction to start a specific new task and then cancel that same task already identifies its target; retain that new task's binding instead of choosing another conversation.

Retain useful partial answers. Extra fields, missing timestamps or counts, and descriptive schema differences are compatibility hints, not business failure. Missing essential task status or message history triggers bounded read-only checks of the same task. If a gap remains, explain it with the available answer: an unknown outcome is not success, and absent history is not proof that no resources exist. Do not invent ownership, decision identifiers, or write parameters, or replay an unconfirmed write to compensate.

## Manage existing conversations

Use `session list` with pagination to list cloud conversations and `session get --session <conversation>` to inspect a selected one. Local task records are not a complete cloud conversation list. If listing fails, report the failure instead of enumerating saved identifiers. For a cloud conversation explicitly selected by the user, use `task continue --session <conversation> --text <request>` with that exact Session. New work normally uses `task new` and `task ask`; no separate cloud-session creation command is needed. Renaming, pinning, deletion, and custom tool-definition management are outside this skill.

Keep the same bounded record set across the final reply and user-facing result files, including IDs or titles in notes. Separate execution logs may faithfully record all actual responses and distinguish received from displayed counts; label formatted or redacted logs as derived and reserve raw for unchanged stdout. Do not invent service fields or relabel result files as logs to evade the limit. Prefer requesting the smaller of the user's per-page limit and the remaining total allowance; stop when the result limit is reached.

Use `messages list` for explicit paging and respect `complete` and `next_token`. Result history is bounded; incomplete history is not a complete result. Request `--details` only for a specific diagnostic need, and omit internal timelines from the user's answer.

## Automatic operation references

`task ask`, `task continue`, `task respond`, `task cancel`, and `run cancel` accept an omitted `--operation-ref`. MESSAGE, RESUME, and CancelRun use separate persisted slots scoped to the selected connection and conversation; responses and cancellations also identify the target Run. Repeating an unchanged command after a restart reuses its reference and idempotency information. An `operation_ref` is a recovery identifier, never evidence of user approval.

Unchanged text defaults to recovery of the latest matching turn. Use `--new-turn` only for an actual new turn after a known outcome; it cannot bypass an unknown outcome, active task, or pending decision. Different follow-up text starts a new turn only after previous work has ended. For a confirmed failed or rejected business task, explain the outcome and obtain a new user decision before another attempt, since earlier work may have taken effect. Retry in the same conversation with `--new-turn --authorization-ref <new-user-decision>`. Unrelated new work can proceed normally; safe connection recovery needs no new business authorization.

Keep `operation_ref` and `turn_ref` when reporting or inspecting uncertainty. Explicit operation references remain supported for legacy recovery and diagnostics, and conflicting reuse is rejected. Legacy messages reuse their saved journal; responses without parent metadata and cancellations without a logical index need their original known reference. A RESUME reference belongs to the parent Run and actual response; retry its unchanged command to inspect the saved child Run even when the parent is no longer waiting. Never reuse a MESSAGE or cancellation reference for it.

## Connection and result troubleshooting

Start with the client error and saved task status. Do not inspect source code, write ad hoc SDK calls, guess routes, or enumerate unrelated profiles for an ordinary failure.

- Missing dependencies: invoke the absolute client entry with `bootstrap`.
- Local file access denied: obtain host permission for the reported OpenAgent paths or correct their permissions, then repeat a local-only check. Recover submitted work instead of resending it.
- State busy: keep the reported conversation and operation references and wait for the conflicting command. Do not delete locks or create replacement work.
- Missing or rejected credentials: use `credentials inspect` and have the user repair the selected source privately. An explicit source change uses `setup configure`; never switch automatically or print secrets.
- Unsupported or incomplete connection: use `setup status` and [setup](setup.md). Do not edit endpoints to bypass supported regions.
- Interrupted observation or service failure: follow saved recovery guidance. The client makes bounded attempts where safe; report exhaustion with the error and request reference. Do not resubmit an unknown operation or retry a confirmed failed business task without a new user decision.

Use `doctor` for local installation checks and `doctor --online` only for connection diagnosis. Online diagnosis reads one conversation page through the saved connection. It does not inspect account controls or model keys, change settings, prove resource-write permissions, or establish cloud identity.

For denied or unavailable APIs, report the workflow, error code, and request reference. Have the administrator check the selected identity's effective permissions, explicit denies, service region, and availability. Request only a verified missing action at the appropriate scope; do not request broad administrator access, infer access from another account, or call an unverified failure transient. A permission grant does not make an unavailable API work.

Use natural-language clarification for missing business information. Compatibility hints are bounded and value-free; they do not authorize resubmission or downloading another client. This skill reports its installed `version`; package replacement belongs to the host's installation process.
