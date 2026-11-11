# SinkUpsertMaterializer: When to Disable SUM

SUM here means **SinkUpsertMaterializer**, not the SQL `SUM()` aggregate. Use this guide when a primary-key Upsert Sink has materialization overhead or a user asks whether SUM can be removed.

Disable SUM only when the Sink can still apply every insert, update, and retraction correctly for each primary key. Lower CPU or state usage does not establish correctness.

## Purpose and Configuration

SUM keeps candidate rows in state keyed by the Sink primary key. An addition stores a candidate and emits an upsert; a retraction removes the matching candidate. Removing an older candidate need not delete the current Sink row. Matching uses an input Upsert Key when available, otherwise the whole row ignoring RowKind. This follows `SinkUpsertMaterializer.addRow` and `retractRow` in the VVR runtime.

SUM is not an event-time sorter and does not repair arbitrary disorder already present in a CDC Source.

| `table.exec.sink.upsert-materialize` | Meaning |
| --- | --- |
| `AUTO` | Default; let the planner decide whether materialization is needed. |
| `NONE` | Disable materialization; correctness must hold without it. |
| `FORCE` | Request materialization where supported by the target planner. |

These modes are documented in the [Apache Flink 1.20 configuration reference](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/dev/table/config/#table-exec-sink-upsert-materialize). Check the target VVR version and compiled plan; do not assume `FORCE` inserts SUM for every Sink or for INSERT-only input.

## The Key Compatibility Rule

A **Unique Key** identifies a row in the current logical result. An **Upsert Key** additionally describes a key whose update history retains usable ordering. Matching Source and Sink primary-key names does not prove that intervening operators preserve that history.

For updating input into a primary-key Upsert Sink, the inspected VVR planner's `AUTO` decision uses:

- `S`: the Sink primary-key columns mapped to Sink-input column positions.
- `U`: one inferred Upsert Key at the final Sink input.

If any `U` is a subset of `S`, the planner can omit SUM:

```text
U is a subset of S
```

The **Sink primary key contains an input Upsert Key**; the reverse containment is insufficient. Unknown keys or no compatible key cause conservative materialization. The V2 implementation also recognizes equivalent columns. This is an implementation-derived rule; verify it against the target release.

Inspect the complete path to the Sink. Aggregation can establish an Upsert Key; later Calc, Join, LookupJoin, or Exchange operators can change its availability. `FlinkRelMdUpsertKeys` is the VVR metadata implementation to inspect when the final keys are unclear.

## Cases to Evaluate

| Situation | Decision |
| --- | --- |
| The final Sink input is strictly INSERT-only. | SUM is unnecessary. An append-only Source alone is insufficient: aggregation or deduplication can produce updates. |
| A final input Upsert Key fits the Sink primary key. | Prefer `AUTO`; it normally already omits SUM. |
| Key uniqueness and ordering hold, but metadata cannot prove them. | Consider `NONE` only after proving those invariants and validating results. |
| The complete relevant path processes an ordered update history at parallelism one. | A candidate only if each Sink key identifies one logical result row and no original-input, branch, or asynchronous reordering remains. Sink parallelism one alone is insufficient. |

If an unnecessary `FORCE` setting is the cause, first compile with `AUTO` and inspect the resulting plan.

For example, aggregation by `(shop_id, channel)` normally establishes that pair as an Upsert Key. A Sink primary key of `(shop_id, channel)` is compatible if later operators preserve it. A Sink primary key of `(shop_id)` makes different channels compete for the same row; define the intended reduction or selection instead of simply disabling SUM.

Key expressions require particular care. An encoding must be injective: no truncation, ambiguous concatenation, or NULL/default collisions. For `GROUPING SETS` followed by `COALESCE`, verify that detail, subtotal, and total rows retain distinct keys. The syntax itself does not prove safe removal; the [Alibaba Cloud Changelog guide](https://help.aliyun.com/zh/flink/realtime-flink/use-cases/processing-changelog-events-out-of-orderness-in-flink-sql) describes conservative inference in this situation.

## Why One Sink Task or a Final Shuffle Is Insufficient

Consider a Join keyed by a mutable `category_id`, while the Sink is keyed by `item_id`. Changing an item's category can route its old and new versions through different Join tasks. A possible Sink arrival order is:

```text
+I (item_id=7, category_id=10)
+U (item_id=7, category_id=20)
-U (item_id=7, category_id=10)
```

If a Sink applies the final retraction as a primary-key delete, the newer row disappears. SUM can remove the old candidate without deleting the new candidate. One Sink task can still receive interleaved upstream channels.

A final keyed shuffle co-locates records; it cannot reconstruct ordering already lost upstream. The [keyed-shuffle documentation](https://nightlies.apache.org/flink/flink-docs-release-1.20/docs/dev/table/config/#table-exec-sink-keyed-shuffle) explicitly requires the upstream to preserve primary-key order. Upsert support, idempotent writes, or exactly-once delivery alone do not resolve this ordering problem.

## State Growth Is a Separate Diagnosis

When no input Upsert Key is available, changed nondeterministic fields can prevent whole-row retraction matching. Expired candidate state can also make a later retraction impossible to match. Investigate unmatched retractions before changing SUM or TTL. A shorter TTL trades retained history for a possible correctness loss; it is not evidence that SUM is unnecessary. These pitfalls are covered in the [Alibaba Cloud usage notes](https://help.aliyun.com/zh/flink/realtime-flink/use-cases/processing-changelog-events-out-of-orderness-in-flink-sql).

## Validation Before Recommending NONE

1. Obtain the target engine version, complete SQL, Sink DDL, relevant configuration, and compiled plan. Identify every Sink affected by the setting.
2. Determine each final Sink input's ChangelogMode and Upsert Keys. Map key columns to the Sink schema and trace ordering through the entire path, including Join distribution and asynchronous modes. If metadata is unavailable, state that the decision remains unproven.
3. Validate expected per-key results for consecutive updates, deletes, mutable Join keys, key-expression collisions, and NULL/rollup cases relevant to the query. A short successful run, total row count, or absence of errors is insufficient.
4. After proving correctness, compile with the setting below and verify the physical plan. SUM may be chained into a Sink vertex. Removing a stateful operator also requires checking restore compatibility before deployment.

```sql
SET 'table.exec.sink.upsert-materialize' = 'NONE';
```

Report the evidence, remaining assumptions, and affected Sinks. If correctness cannot be established, keep `AUTO` and investigate the cause of materialization.

## VVR Implementation Checkpoints

For release-specific investigation, inspect these classes in the target VVR source; the general guidance above is not a guarantee that every release has identical inference:

- `SatisfyUpdateKindTraitVisitorV2.analyzeUpsertMaterializeStrategy` and `UpsertKeyUtil.givenKeyContainsUpsertKey`: insertion decision and key containment.
- `FlinkRelMdUpsertKeys`: key propagation through relational operators.
- `CommonExecSinkBase`: runtime materialization and keyed-shuffle wiring.
- `SinkUpsertMaterializer`: candidate state and retraction matching.
