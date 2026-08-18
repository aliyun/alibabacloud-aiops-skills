# Pipeline Verification Method

## Contents

- [1. Prerequisites and Command Surface](#1-prerequisites-and-command-surface)
- [2. Source Profile and Field Contract](#2-source-profile-and-field-contract)
- [3. Preview Gate](#3-preview-gate)
- [4. Create and RunOnce State Machine](#4-create-and-runonce-state-machine)
- [5. Run Verification](#5-run-verification)
- [6. Dataset Reconciliation](#6-dataset-reconciliation)
- [7. Migration and Reuse Verification](#7-migration-and-reuse-verification)
- [8. Reporting](#8-reporting)

## 1. Prerequisites and Command Surface

```bash
aliyun version
aliyun plugin show --name agentloop
aliyun configure list
aliyun agentloop create-pipeline --help
aliyun agentloop preview-pipeline --help
aliyun agentloop run-pipeline --help
aliyun agentloop list-pipeline-runs --help
aliyun agentloop get-pipeline-run --help
```

Expected:

- Aliyun CLI is 3.3.15 or later.
- `aliyun-cli-agentloop` is 0.7.4 or later and exposes API `2026-05-20`.
- The same explicit profile, region, AgentSpace, and session-scoped user agent are used throughout.
- Current help still confirms that preview has no sink and manual run has neither sink override nor client token.

If the installed command differs, stop and update the plan from current public help instead of forcing an older payload.

## 2. Source Profile and Field Contract

Before preview, record without exposing raw contents:

- SLS project and Logstore.
- Exact query and bounded `[from, to)` window.
- Complete/accurate source selection count.
- Case-sensitive source field names and types.
- Null/empty counts for required fields.
- Stable lineage field and duplicate count.
- Expected filters and the count each filter may exclude.
- Target Dataset schema and downstream consumer requirements.

Freeze a contract for each emitted field:

```text
target field | source/expression | required/nullable | sensitivity | consumer
```

The contract must distinguish raw fields (`input`, `output`) from derived fields (`question`). Row count is not a field contract.

## 3. Preview Gate

Use a narrow bounded window that covers representative and edge-case records. Validate at least:

- Every expected target field is present.
- `input` and `output` remain present after `project` when the contract requires them.
- `question` is clean for structured `<userQuery>` input, wrapper-prefixed input, and plain input.
- Wrapper residue is absent from `question`.
- Rows with empty derived questions are excluded only by the declared filter.
- Source-null `output` remains distinguishable from a transform that dropped a non-null output.
- Lineage fields still identify the source record.
- Values are not truncated.

Do not print real raw `input` or `output` to the terminal, conversation, test snapshots, or reports. Prefer:

- field-presence booleans;
- value lengths and null counts;
- stable non-secret IDs;
- hashes for identity comparison;
- synthetic or redacted samples.

Preview is accepted only when both structure and representative transformations pass. Five correct `question` values are not enough if the same preview omitted raw `input` or `output`.

## 4. Create and RunOnce State Machine

Use this state machine for a `runOnce` Pipeline:

```text
preview accepted
-> create-pipeline
-> get-pipeline
-> poll list-pipeline-runs over a bounded observation window
   -> existing RunOnce run: monitor it
   -> no run before timeout: ambiguous; do not manually trigger
-> get-pipeline-run until terminal
-> reconcile Dataset
```

Hard rule: a create response with `lastRunId` null or absent, or one immediate empty run list, is not evidence that no run exists. Creation may produce the `RunOnce` record asynchronously. Poll with a bounded timeout and stable Pipeline/window filters. A timeout means `ambiguous`, not `not_started`; `run-pipeline` has no client token, so it must not be used as the automatic fallback for this newly created `runOnce` Pipeline.

Only consider a later manual run when independent evidence establishes that the automatic run cannot still start, the target Dataset has been reconciled for partial/late writes, and the user explicitly accepts the remaining duplicate-write risk. Otherwise stop with the ambiguous state and request platform-state resolution.

After a create timeout or ambiguous response, reuse the original create client token and first read back the Pipeline and poll its runs. Do not create another name or trigger another run until state is resolved.

## 5. Run Verification

Use `list-pipeline-runs` to capture the intended run ID and trigger type, then `get-pipeline-run` until terminal. Verify:

- Pipeline name and run ID match the intended resource.
- Trigger type is the expected `RunOnce`, `Manual`, or `Scheduled` value.
- The run covers the intended source window.
- Terminal status is explicit.
- Processed, filtered, failed, and output counts are internally consistent where exposed.
- Any failure has an error class, failing node, and request ID.

`Succeeded` proves only that the Pipeline service completed the run. It does not prove that the selected source set, emitted fields, transformation semantics, or Dataset contents are correct.

## 6. Dataset Reconciliation

Query the Dataset through the Dataset domain. For a bounded import, reconcile the full selected set when practical; for a large recurring Pipeline, use complete aggregates plus stratified samples and stable lineage checks.

Minimum checks:

```text
source_selected_count
target_count_for_this_migration_or_run
expected_filtered_count
missing_source_ids
extra_target_ids
duplicate_source_ids
duplicate_target_lineage_ids
required_field_non_null_counts
source_vs_target_empty_field_ids
raw_field_identity_mismatches
question_transform_failures
wrapper_residue_count
truncated_value_count
```

Expected relationship:

```text
target_count = source_selected_count - explained_filtered_count - explained_failed_count
```

Classify every unexpected empty or missing value rather than collapsing it into “Pipeline lost data”:

| Classification | Meaning |
| --- | --- |
| `source_already_empty` | The same stable source record was empty before processing. |
| `migration_dropped_nonempty_value` | Source was non-empty but target is empty or missing. |
| `transform_failed` | A derived expression failed or produced an invalid value. |
| `redacted_by_policy` | A declared privacy rule intentionally removed the value. |
| `truncated` | The value was shortened by a service/query output limit. |
| `missing_field` | The expected column was not emitted or stored. |

For each anomaly, use its stable lineage ID to run a narrow source preview and narrow Dataset query. Do not expose the raw value while comparing it.

Acceptance requires:

- no unexplained missing or extra lineage IDs;
- no source-nonempty to target-empty loss for required preserved fields;
- no unexpected duplicate lineage IDs;
- no wrapper residue or transform failures outside the declared policy;
- all expected exclusions explained by filters;
- downstream smoke tests can read every required column.

## 7. Migration and Reuse Verification

For a versioned schema correction:

1. Confirm the old Dataset and Pipeline remain unchanged.
2. Get the new Dataset and verify all raw, derived, and lineage fields before Pipeline creation.
3. Get the new Pipeline and verify its sink is the new Dataset.
4. Verify only one intended initial run exists.
5. Reconcile new target data against the original source, not against the flawed old Dataset.
6. Run the downstream Evaluation/Experiment variable-mapping smoke test.
7. Switch consumers only after acceptance; do not delete the old version without explicit authorization.

For historical Pipeline reuse, compare the old and new complete definitions. The intended sink/name change must be visible, while unrequested source, node, and execute-policy changes must be absent.

## 8. Reporting

Report:

- profile name (not credentials), region, and AgentSpace;
- Pipeline and Dataset names;
- source window and query fingerprint;
- Pipeline run ID, trigger type, terminal state, and request IDs;
- source, filtered, output, and target counts;
- field-contract pass/fail matrix;
- anomaly classifications and stable non-secret lineage IDs;
- whether downstream consumer smoke tests passed;
- unresolved evidence gaps.

Never report “import correct” from a successful status or row count alone. If source access, output completeness, or lineage is unavailable, use `insufficient_evidence` and state the missing oracle.
