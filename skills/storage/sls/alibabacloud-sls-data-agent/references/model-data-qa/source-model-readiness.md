# Source Model availability checks and enablement guidance

## 1. Check the model

Use the following commands to check model generation for the current Project and the status of its Logstore nodes. Reuse sufficient existing results instead of querying again.

**Project task status:**

```bash
python3 "<skill-dir>/scripts/model_qa.py" source-model status \
  --region "<region>" --project "<project>"
```

- `elementCount` must be a valid nonnegative integer. Project generation is complete when `taskState=succeeded`. Only when an older response is known to genuinely lack `taskState`, accept `elementCount>0` for compatibility.
- `taskState=none` does not meet the generation-complete condition. An `elementCount=0` in that state also does not prove the model has not been enabled; still check the Logstore node.

**Target Logstore generation status:**

```bash
python3 "<skill-dir>/scripts/model_qa.py" source-model query \
  --region "<region>" --project "<project>" --query-file - <<'SPL'
.umodel
| where kind = 'sls_logstore'
| extend region = json_extract_scalar(spec, '$.region')
| extend project = json_extract_scalar(spec, '$.project')
| extend logstore = json_extract_scalar(spec, '$.store')
| extend status = json_extract_scalar(metadata, '$.tags.generate_status')
| project region, project, logstore, status, metadata
SPL
```

- Accept only responses with CLI exit code 0, no error envelope, valid structure, `responseStatus.result == "Success"`, and `level == "Info"`. A complete successful response with `header=[]` and `data=[]` is a valid empty table.
- Interpret the two-dimensional `data` by the column names in `header`, matching the current Logstore's full resource coordinates. If an older response lacks Region/Project, cross-check with confirmed resource information. Availability cannot be confirmed when attribution is not unique, coordinates conflict, or status is unrecognized. Also check the generation status of the corresponding nodes when referencing definitions for other Logstores.

**Execution constraints:** reuse results only from the same round, identity, environment, and target, and only when they support the current decision. Retry only explicitly retryable reads with backoff, at most twice.

## 2. Decide and act

| Check result | Action |
| --- | --- |
| Explicit Project/Logstore not-found error that is not a correctable parameter error | Stop and explain the cause; a generic 404 is not sufficient for this decision |
| The Project meets the model generation-complete condition and the uniquely matched Logstore node is `finish` | Return to [Source Model guidance](source-model.md) to explore and validate model definitions |
| Explicit `SourceModelNotExist`, with no evidence of ongoing generation, failure, or contradiction | Hand off to the original SQL analysis workflow and suggest `create-source-model` |
| The Project meets the model generation-complete condition, the model query succeeds completely, but no node matches the current Logstore | Hand off to the original SQL analysis workflow and suggest `regenerate-source-model` to add the current Logstore |
| Any other unavailable or unconfirmed state, including ongoing/failed generation, read errors, unavailable sources, or unusable definitions | Explain the actual cause and conditionally hand off to the original SQL analysis workflow |

- Suggest enablement only for the two explicit missing-model cases in the table. Unknown status or a failed check is not evidence that enablement is needed. `CatalogSourceNotFound` means only that a model source is absent, not that the physical resource or entire model does not exist. Treat the model as unavailable when definitions remain absent or unsuitable after excluding read failures and budget omissions.
- When the Project or target is `pending/running`, advise waiting; when the Project is `failed`, explain the failure. In both cases, do not use residual old `finish` nodes or submit generation tasks automatically.
- The fallback requires a separately available SLS SQL analysis workflow in the current environment; stop Source checks in this branch after handoff. Run it only when log access is authorized and business calculation rules can be verified independently. Preserve query coordinates, data source scope, fixed times, filters, the question, and the cause. If independent evidence collection is impossible or that workflow is unavailable in the current environment, explain the gap or stop.

## 3. Enablement guidance

Show the command corresponding to the decision. For an initial `create-source-model`, recommend the whole Project by default and also offer the current-Logstore-only option. Ordinary data analysis does not execute model writes.

```bash
# Enable the whole Project for the first time
aliyun sls create-source-model \
  --region "<region>" --project "<project>"

# Enable only the current Logstore for the first time
aliyun sls create-source-model \
  --region "<region>" --project "<project>" --logstores "<logstore>"

# Add the current Logstore to an existing model
aliyun sls regenerate-source-model \
  --region "<region>" --project "<project>" --logstores "<logstore>"
```

Omitting `--logstores` from `create-source-model` applies to the whole Project. For multiple Logstores use `--logstores "<logstore1>" "<logstore2>"`. If the user explicitly requests execution, hand off to the host's existing management/HIL workflow. Successful submission does not mean generation has completed.
