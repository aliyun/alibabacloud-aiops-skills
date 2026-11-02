# Source Model Availability Checks and Enablement Guidance

## 1. Check the model

Use the following commands to check the current Project's model generation status and the Logstore node status. Do not repeat reads when sufficient reusable results are already available.

Python's `readiness` command combines reads of the Project task status and the target Logstore node, returning `available`, `reason` and, where applicable, `recommendation`:

```bash
python3 scripts/model_qa.py source-model readiness \
  --region "<region>" --project "<project>" --logstore "<logstore>"
```

- `elementCount` must be a valid nonnegative integer. Model generation for the Project is complete when `taskState=succeeded`. Only when the endpoint is known to return a legacy response without `taskState`, pass `--legacy-status` to accept `elementCount>0` as the completion criterion.
- `taskState=none` does not establish generation completion. Even with `elementCount=0`, it does not prove that Source Model has not been enabled; the Logstore nodes must still be checked.
- Accept node-read responses only when they are structurally valid and have `responseStatus.result == "Success"` and `level == "Info"`. A complete, successful `header=[]` and `data=[]` response is a valid empty table. The script interprets the two-dimensional `data` by the column names in `header` and matches the current Logstore's full resource coordinates.
- If a legacy response omits Region or Project, verify it against confirmed resource information. Ambiguous associations, conflicting coordinates or unrecognized states cannot establish availability. When referencing another Logstore's model definitions, also verify that node's generation status.

To inspect Project status separately:

```bash
python3 scripts/model_qa.py source-model status \
  --region "<region>" --project "<project>"
```

**Execution constraints:** Reuse results only within the same analysis, identity, environment and target, and only when they are sufficient for the current decision. Retry only explicitly retryable reads, with backoff, at most twice.

## 2. Decide and proceed

| Check result | Handling |
| --- | --- |
| An explicit Project/Logstore-not-found error that is not caused by a correctable parameter error | Stop and explain the cause. Do not infer this from a generic 404. |
| Model generation for the Project meets the completion criteria, and the uniquely matched Logstore node has status `finish` | Return to [Source Model exploration](source-model.md) to explore and validate model definitions. |
| Explicit `SourceModelNotExist`, with no evidence of generation in progress, failure or contradictions | Switch to the existing SQL analysis workflow and suggest `create`. |
| Model generation for the Project meets the completion criteria, the model query succeeded and returned complete results, but no node was found for the current Logstore | Switch to the existing SQL analysis workflow and suggest `regenerate` to add the current Logstore. |
| Other unavailable or unconfirmed states, including generation in progress, failure, read errors, or unavailable sources or definitions | Explain the actual cause and switch to the existing SQL analysis workflow only under the conditions below. |

- Suggest enablement only for the two explicit missing-model cases in the table. Unknown states or failed checks are not evidence that enablement is needed. `CatalogSourceNotFound` means only that the model source is missing, not that the physical resource or entire model is absent. If definitions remain missing or unsuitable after ruling out read failures and budget omissions, treat the model as unavailable.
- If the Project task or target Logstore node is `pending/running`, advise waiting. If the Project task is `failed`, report the failure. Do not use leftover nodes marked `finish` from a previous generation in these cases or automatically submit generation tasks.
- The host's `sls-sql-generation` skill handles the existing SQL analysis workflow. After handing off, stop checking Source Model availability for this branch. Proceed only when the logs themselves are accessible and the business definitions can be independently verified. Preserve query locations, data-source scope, fixed time bounds, filters, the question and the reason for fallback. If independent evidence cannot be obtained or the host lacks that skill, explain the gap or stop.

## 3. Enablement guidance

Explain the appropriate `create` or `regenerate` operation based on the decision. For initial creation, recommend the entire Project by default and also offer the option of modeling only the current Logstore. If an existing model lacks the current Logstore, use regenerate to add it. Ordinary data analysis does not execute model writes.

This Python skill does not provide model-write commands. When the user explicitly requests execution, hand off to the host's existing model management or human-in-the-loop (HIL) workflow. Successful submission does not mean generation has completed.
