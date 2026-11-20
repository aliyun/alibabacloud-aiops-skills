# Model availability troubleshooting

Read this only when an availability check failed or remains unconfirmed and the task requires semantic models. Successful checks and optional enrichment do not need this document; follow [result handling](availability.md#result-handling).

Use the existing `reason`, error details and optional `recommendation` to select the relevant check. Keep the same identity, target, region and endpoint.

| Probe result or reason | Handling |
| --- | --- |
| `generation_pending` / `generation_running` | Wait for generation; do not submit another generation task. |
| `generation_failed` | Explain the generation failure using available diagnostics. |
| `model_missing` | The Source Model is confirmed missing; suggest `create` if needed. |
| `logstore_model_missing` | The Project model is complete but lacks the selected Logstore; suggest `regenerate` if needed. |
| Unconfirmed generation, inconsistent status or ambiguous coordinates | Verify the target and available status evidence. These states do not establish a missing model. Use `--legacy-status` only for a confirmed legacy status response. |
| Empty definitions or `CatalogSourceNotFound` | Check model selection and source scope; this does not establish that the physical Logstore is absent. |
| CLI, authentication, permission or connection errors | Use [common troubleshooting](../troubleshooting.md) and [model permissions](ram-policies.md) for the failing operation. |

Retry only explicitly retryable reads, with backoff, at most twice. Stop when the cause cannot be resolved from available evidence and explain what is needed.

`create` and `regenerate` are suggestions, not authorization. Execute model changes only when explicitly requested, using the relevant CLI command's `--help` and the confirmed scope. Successful submission does not establish generation completion; recheck availability before reading the guide.
