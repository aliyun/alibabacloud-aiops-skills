# SLS DataAgent Chat

Use the selected SLS DataAgent for questions, analysis, or operations, and continue the conversation in the same thread.

## Invocation conventions

`chat.py` invokes DataAgent through `aliyun sls`. The following connection parameters apply to both the script and CLI commands:

| Parameter | Usage |
| --- | --- |
| `--region` | Specify the Chat service region. Currently supported: `cn-beijing`, `ap-southeast-1`. Do not derive it from the log resource region; ask for clarification if it is unknown. |
| `--profile` | Specify when needed to override the CLI's default credential configuration. |
| `--endpoint` | Specify when needed to override the CLI's default service endpoint; do not use the model endpoint. |

## 1. Select the DataAgent

Prefer the resource `name` already confirmed by the user or context. If it has not been determined, list candidates and ask the user to confirm:

```bash
aliyun sls list-data-agents --region "<chat-region>" --max-results 100
```

Present candidates using `name`, `displayName`, `description`, and `contextModels`. Use the confirmed resource `name` in subsequent calls.

Additional options:

- When there is a clue in the name, display name, or description, append `--keyword "<keyword>"` to narrow the search.
- If the response includes `nextToken` and more candidates are needed, append `--next-token "<actual-nextToken>"` to read the next page.

## 2. Converse with the DataAgent

### Send a message

Send a message to the confirmed DataAgent:

```bash
python3 "<skill-dir>/scripts/chat.py" send \
  --name "<agent-name>" --region "<chat-region>" --message "<user-request-and-existing-constraints>"
```

Start or continue a conversation:

- **New conversation**: omit `--thread-id`; the script creates a thread.
- **Continue a conversation**: pass the script's returned `threadId` through `--thread-id`, retain the DataAgent and connection configuration, and make calls serially.

Additional options:

- **For long or multiline messages**, replace `--message` with `--message-file "<message.txt>"` to read UTF-8 text; `-` means stdin.
- **When a language and time zone must be specified**, for example confirmed Chinese and Shanghai time, append `--variables '{"language":"zh","timeZone":"Asia/Shanghai"}'`. This applies to both direct text and file input; the server handles unspecified variables. Pass these variables on every `send` when the setting must persist.

### Handle results

Read the complete JSON from `stdout` and handle this call according to `status`:

| Returned status | Next action |
| --- | --- |
| `completed` | Deliver the answer and artifacts to the user, accurately reporting downstream failures or limitations; send a new message in the same thread to continue the conversation |
| `interactive` | Obtain the user's actual response according to the [interaction reference](data-agent-chat/interactions.md), then call `respond` |
| `failed` | Explain the failure; confirm the processing status of this user request before continuing operations |
| `unknown` | Verify the processing status of this user request; do not automatically resend messages or interaction results |

Read the [recovery and stopping reference](data-agent-chat/recovery-and-stop.md) when the script result cannot be parsed, `status` is unrecognized or `unknown`, or the request's processing status must be verified, output retrieved, or generation canceled. If identifiers required for the next operation are missing, stop continuation and explain what is missing.

## Optional usage

The following options apply to `send` (send a message), `respond` (return an interaction result), and `reconnect` (resume receiving output).

### Reuse identifiers

In a multiround conversation, add `--session-file "<session.json>"` to record identifiers and avoid repeating parameters such as `--name`, `--region`, and `--thread-id` in later calls.

**First use**: provide the target and specify a session file that does not yet exist. The script creates it automatically.

```bash
python3 "<skill-dir>/scripts/chat.py" send \
  --name "<agent-name>" --region "<chat-region>" \
  --session-file "<session.json>" --message "<user-request-and-existing-constraints>"
```

**Subsequent use**: specify the same session file; recorded identifiers can be omitted. If recorded identifiers are also passed explicitly, their values must match the session file or the script rejects the call.

```bash
python3 "<skill-dir>/scripts/chat.py" send \
  --session-file "<session.json>" --message "<follow-up-message>"
```

### Progress notices

Progress notices are enabled by default and report execution stages and elapsed wait time to `stderr`; use `--no-progress` to disable them. `stderr` also carries necessary diagnostics. Base business decisions on the `stdout` JSON.
