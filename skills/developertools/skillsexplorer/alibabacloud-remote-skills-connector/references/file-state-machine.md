# File State-Machine Contract

The bundled A2A runtime maintains local state by session, Agent, and task under `~/.aliyun_agenthub/a2a_tasks`. Path components are validated or hashed. Callers must never construct a path manually from user input.

## States

- `pending`: the current approval round is waiting for remote authorization results or a later check.
- `input_required`: the remote Agent is waiting for additional user input.
- `running`: the remote task is in progress.
- `ready`: a terminal result is persisted and waiting to be claimed.
- `delivered`: the result has been shown or claimed in the foreground.

## Critical Transitions

| Remote event or local action | Local result |
|---|---|
| First `auth_required` | Write `pending`, establish `hitlRound`, and emit a typed control event only after persistence succeeds |
| Same-round `auth_required` probe | Keep the same `pending` record and round, update attempt data, and keep the original `action-ref` stable |
| Working after `pending` | Transition to `running` |
| Another `auth_required` after working | Establish a new `hitlRound`, clear the previous follow-up fields, and invalidate the old `action-ref` |
| `input_required` | Transition to `input_required` and wait for the user's original input |
| Still processing after `continue_task` | Transition to `running` |
| Terminal result to be claimed later | Transition to `ready` |
| `view_task` displays a ready result | Transition to `delivered` |
| Foreground send or continuation already displays a terminal result | Transition directly to `delivered` and retain the corresponding delivery mode |
| Task is absent and confirmed unrecoverable | Remove the current local record |

`continue_task` may start only from `input_required`. Terminal states such as completed, failed, canceled, and rejected, as well as ordinary conversation, cannot be continued.

Existing delivery-mode names and semantics must remain stable. `view_task` means claiming a ready result; `auth_subscribe` means an approval streaming follow-up returned a terminal result; `auth_followup` means post-approval polling returned a terminal result; `continue_task_foreground` means the foreground additional-input call returned a terminal result; and `send_streaming_foreground` means the initial foreground streaming send returned a terminal result. Do not change these values when refactoring the control channel.

## Task ID Binding

Initial `SendStreamingMessage` allows the first non-empty `taskId` to establish the stream identity. Every later event must remain consistent. `SubscribeToTask`, `continue_task`, and `GetTask` bind to the known `taskId` when the request is sent. A missing ID may be handled according to the operation's existing semantics, but any non-empty mismatched ID must be rejected as `InvalidResponse` before a state transition. Never switch transactions, update another task, or write another task's response into the current record. After rejection, preserve any legitimately entered `pending` or `running` state and existing delivery-mode semantics so a later `check_task` can recover.

## Approval Follow-Up

Persist `auth_required` before notifying the parent through the typed control FD. The parent must match the event's `taskId` and `hitlRound` to the current local `pending` record before it may emit:

```bash
python3 scripts/agenthub.py follow_task --session-id "<CLIENT_SESSION_ID>" --task-id "<TASK_ID>" --action-ref "<ACTION_REF>"
```

The caller must show approval details first and then execute the action immediately in the foreground within the same client turn. It must not send a final response, ask the user to return after approval, background the action, or switch conversations. `follow_task` selects either internal streaming `subscribe_task` or bounded polling from the structured Agent Card capability.

Allow only one streaming subscription attempt per approval round and persist its deduplication state. A non-streaming Agent uses bounded polling. A wait timeout does not consume `action-ref`; it may be retried while the record remains `pending` in the same round. A new round generates a new reference and permits its own subscription attempt.

On same-round `auth_required`, a streaming subscription continues waiting. On a new round, stop following the old round and emit the new reference. A connection error, connection close, server-event idle timeout, or polling timeout must not fabricate `ready` or `delivered`; retain `pending` or `running` and the end reason.

## Public Operations

```bash
python3 scripts/agenthub.py list_tasks --session-id "<CLIENT_SESSION_ID>"
python3 scripts/agenthub.py check_task --session-id "<CLIENT_SESSION_ID>" --task-id "<TASK_ID>"
python3 scripts/agenthub.py follow_task --session-id "<CLIENT_SESSION_ID>" --task-id "<TASK_ID>" --action-ref "<ACTION_REF>"
python3 scripts/agenthub.py view_task --session-id "<CLIENT_SESSION_ID>" --task-id "<TASK_ID>"
python3 scripts/agenthub.py cancel_task --session-id "<CLIENT_SESSION_ID>" --task-id "<TASK_ID>"
python3 scripts/agenthub.py continue_task --session-id "<CLIENT_SESSION_ID>" --task-id "<TASK_ID>" --message-input-id "<INPUT_ID>"
```

Task commands restore the Agent and endpoint from validated local records. `follow_task` requires all three CLI-generated session, task, and action-reference values. Session and task values are equality assertions against the record restored from `action-ref`; they do not participate in routing. Callers cannot add endpoint, agent ID, or polling parameters.

## Storage Safety

- Private directories use `0700`; state files use `0600`.
- Accept only regular files owned by the current user. Reject symlinks, extra hard links, an unexpected owner, and overly broad permissions.
- Protect each logical record's entire read-modify-write sequence with a sidecar lock.
- Write through a random temporary file in the same directory, call `fsync`, atomically replace the target, and call `fsync` on the parent directory.
- A legacy path owned safely by the current user may have its permissions tightened or be migrated. Fail closed when the path cannot be verified.
- Task records do not store a user-message preview.

Never manually edit, move, copy, rename, or delete task-state files, and never simulate a state transition from the shell. State-maintenance code must preserve existing `stateRevision`, `attempts`, `hitlRound`, deduplication fields, and delivery-mode semantics.
