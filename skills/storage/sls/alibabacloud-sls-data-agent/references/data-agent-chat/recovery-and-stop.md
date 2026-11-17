# SLS DataAgent Chat recovery and stopping

## Verify request status

When the call outcome is unknown, reading was interrupted, or additional output is needed, query the corresponding thread's history:

```bash
aliyun sls get-thread-data --name "<agent-name>" --thread-id "<actual-threadId>" \
  --region "<chat-region>" --max-results 100
```

- **Locate the request**: use the existing user message's `messageId`, related `requestId`/`traceId`, and call associations to find the corresponding records; the response's top-level `requestId` belongs to this history query.
- **Read further pages**: if the response includes `nextToken` and the request still needs to be located, append `--next-token "<actual-nextToken>"` to read the next page.

Choose the next step from the corresponding request's execution records and pending interactions. Do not infer completion from only the latest record or existing body text:

| Verified state | Next step |
| --- | --- |
| The request has ended with no pending interactions | Use the verified result or error; call `send` to continue the conversation |
| Pending interactions exist | If the current complete script result is available, return the user's response according to the [interaction reference](interactions.md); otherwise stop automatic operations |
| The request is still running and more output is needed | Call `reconnect` |
| The request cannot be located, or its processing status or interaction completeness cannot be confirmed | Explain what is missing and stop automatic operations; do not resend messages or interaction results, and do not keep polling |

## Resume receiving output

After verifying through the CLI that the request is still running and more output is needed, call `reconnect`:

```bash
python3 "<skill-dir>/scripts/chat.py" reconnect \
  --name "<agent-name>" --region "<chat-region>" --thread-id "<actual-threadId>"
```

When pending interactions are known to exist, append `--context-file "<known-context.json>"` with the previous complete script result containing all current pending items; stop automatic operations if it cannot be provided.

Handle the returned JSON according to the main [result table](../data-agent-chat.md#handle-results). If it is still `unknown`, stop this automatic operation and explain what remains unconfirmed.

## Stop generation

When the user asks to cancel the current request, send a `stop` request to the corresponding thread:

```bash
aliyun sls create-chat --name "<agent-name>" --thread-id "<actual-threadId>" \
  --region "<chat-region>" --action stop
```

`task_finished.success=true` in this stop response means the stop request was handled successfully. Report an error if the call fails; if no explicit acknowledgment was received, state that the outcome of stopping is unconfirmed.
