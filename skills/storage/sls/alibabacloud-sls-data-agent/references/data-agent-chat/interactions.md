# SLS DataAgent Chat interaction responses

## Handle interaction requests

Each element in the current script result's `interactions` is a pending interaction. Select one, use its zero-based array position as `index`, and fill in `result` according to its `payload.type`.

| `payload.type` | Interaction |
| --- | --- |
| `user_ack` | Confirmation of an operation |
| `ask_user_question` | One or more questions to answer |

For an unsupported interaction type, retain the complete script result, explain the limitation, and stop automatic responses.

### Operation confirmation (`user_ack`)

Present the operation, hints, and `options` in `payload.userAck`, and obtain the user's actual selection. Set `result.decision` to the selected option's `value` (`yes` or `no`).

For example, the DataAgent requests confirmation:

> **Update the description of Context Model `payment-prod` to "Production log analysis for the payment service"?**
>
> - Confirm (`yes`)
> - Cancel (`no`)
>
> **User selection: Confirm**

If this interaction has index `0`, return:

```json
{"index": 0, "result": {"decision": "yes"}}
```

### Question answers (`ask_user_question`)

Present the questions and field requirements in `payload.askUserQuestion.questions`, and obtain the user's answers. Set `result.decision` to `yes` and put the answers in `result.answers`.

For example, the DataAgent asks:

> **Which time range of logs do you want to analyze?**
>
> - Last 1 hour
> - Last 24 hours
>
> **User selection: Last 1 hour**

The question's `id` is `analysis_time_range`, its field name (`schematic.fields[].name`) is `time_range`, and the selected option's `value` is `last_1h`. If the interaction has index `0`, return:

```json
{
  "index": 0,
  "result": {
    "decision": "yes",
    "answers": [{"questionId": "analysis_time_range", "answer": {"time_range": "last_1h"}}]
  }
}
```

Additional cases:

- **Multiple questions in one interaction**: put a separate answer for each question in the same `result.answers`; each `questionId` is the corresponding question's `id`, and `answer` holds that question's field values.
- **Multiple selections**: for example, if the field is `focus` and the user selects "Error types" (`error_types`) and "Request latency" (`latency`), use `{"focus":["error_types","latency"]}` as `answer`.
- **Text input**: for example, the DataAgent asks for a description of the anomaly in field `symptom`. If the user enters "5xx", use `{"symptom":"5xx"}` as `answer`.
- **Reject or skip the entire questionnaire**: use `{"decision":"no"}` as `result`, without `answers`.

## Return an interaction result

Each `respond` submits the result for only one pending interaction. Use these files:

| Parameter | File contents |
| --- | --- |
| `--context-file` | The previous complete stdout JSON saved unchanged, containing all current pending interactions |
| `--interaction-result-file` | One `index`/`result` object to return in this call |

```bash
python3 "<skill-dir>/scripts/chat.py" respond \
  --name "<agent-name>" --region "<chat-region>" --thread-id "<actual-threadId>" \
  --context-file "<interactive.json>" \
  --interaction-result-file "<interaction-result.json>"
```

For a short result, pass it directly with `--interaction-result '<index/result JSON>'`; use either this option or `--interaction-result-file`. For piped input, use `--interaction-result-file -`.

Handle the returned JSON according to the main [result table](../data-agent-chat.md#handle-results). Before another response, save the newly returned complete JSON for `--context-file` and select `index` again from the new result's `interactions`.
