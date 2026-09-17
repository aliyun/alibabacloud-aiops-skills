# In-Depth Job Analysis

Read when the [diagnosis entry point](README.md) leads to complex performance, execution-plan, or operator-behavior analysis. Combine the execution plan (Plan), SQL, and runtime evidence to determine the cause. See [job-observability.md](job-observability.md) for exact CLI syntax.

## Analysis Flow

### 1. Get Basic Job Information

Follow [Deployment Configuration and Runtime Instances](job-observability.md#deployment-configuration-and-runtime-instances). For a streaming job, identify the Deployment first; for a batch job or historical issue, use the specific Job instance.

Key information:

- `artifact.sqlArtifact.sqlScript`: actual SQL script.
- `engineVersion`: target engine version.
- `flinkConf`: Flink configuration.
- Job kind, runtime, parallelism, and resource configuration.

Use `artifact.kind` to distinguish an SQL job from a CDC YAML job, and use the configuration and script belonging to the affected instance.

### 2. Get the Execution Plan

Follow [Runtime Topology and Plan](job-observability.md#runtime-topology-and-plan) to retrieve the runtime plan and identify nodes and edges.

Focus on:

- `nodes[].description`: operator or operator-chain description, interpreted with the relevant SQL fragment.
- `nodes[].parallelism`: operator parallelism.
- `nodes[].inputs[].id`: upstream node ID.
- `nodes[].inputs[].ship_strategy`: distribution strategy such as FORWARD, HASH, RESCALE, BCAST, or CUSTOM.
- `nodes[].inputs[].exchange`: data-exchange mode; use the actual response.

Build the Source → downstream operators → Sink data flow from input edges, then verify partitioning, operator chains, and parallelism. See the query documentation for the Plan response structure.

### 3. Get Runtime Operator Metrics

Query the relevant Vertex according to [Current Metrics](job-observability.md#current-time) and [Backpressure Details](job-observability.md#backpressure-details).

Focus on busy time, backpressure, and input/output rates, using the actually reported `busyTimeMsPerSecond`, `backPressuredTimeMsPerSecond`, `numRecordsInPerSecond`, and `numRecordsOutPerSecond` IDs.

Map Metrics to Plan nodes. Inspect internal operator differences with [Subtask Metrics](job-observability.md#subtask-metrics). For historical issues, use [Historical Metrics](job-observability.md#specified-historical-time-and-time-range) for the affected instance and period.

## Analysis Scenarios

### Scenario 1: Locate a Performance Bottleneck

**Symptom:** low job throughput and high backpressure.

**Steps:**

1. Identify operator chains and upstream/downstream edges from the Plan.
2. Obtain busy-time, backpressure, and throughput Metrics for relevant operators.
3. Locate candidate bottlenecks. For example, busy time near 1,000 ms/s is a busy signal; verify the constrained stage with Subtask distribution and TM resources.
4. Inspect the SQL for possible optimization, including reducing computation or changing operator chains or parallelism, while verifying semantics and network cost.

**Example:**

```text
Plan: Source -> Transform -> Sink
Metrics: Transform busyTime=980 ms/s, backpressure=0
Assessment: Transform is a candidate bottleneck; verify throughput, Subtask distribution, and TM resources
Optimization: after confirming the cause, evaluate changes to parallelism or operator chaining
```

### Scenario 2: Unexpected Execution Plan

**Symptom:** SQL execution efficiency differs from expectations.

**Steps:**

1. Compare SQL and Plan nodes to check whether computation occurs at the expected location.
2. Check whether `ship_strategy` satisfies partitioning requirements for Joins and aggregations, and identify avoidable exchanges.
3. Check parallelism distribution, source partitions, and operator chains for uneven load or resource contention.
4. Consult official optimization guidance for the target version and verify the applicability of pushdown, partitioning, operator chaining, and related optimizations.

**Common issues:**

- Pushdown supported by the Connector and allowed by SQL semantics did not take effect.
- Partitioning and key distribution cause data skew.
- Operator chaining causes resource contention.

### Scenario 3: Unexpected Operator Behavior

**Symptom:** an operator's output differs from expectations.

**Steps:**

1. Locate the operator in the Plan's `description`.
2. Compare the applicable SQL, input/output examples, primary keys, and time/State configuration to the expected computation.
3. Use [Exceptions](job-observability.md#exceptions) and [Runtime Logs](job-observability.md#runtime-logs) to confirm the trigger.
4. Consult official documentation for the target version to distinguish a semantic, configuration, data, or version issue. A version issue requires evidence matching the observed conditions.

**Example:**

```text
Plan: Schema-processing node connected to the target Sink
Log: an incompatible-type error appears after a field change
Check: YAML, upstream and downstream schemas, mapping rules, and Connector Schema Evolution support
Verify: determine whether incompatibility occurs during transformation or writing
```

### Scenario 4: CDC YAML Job Analysis

**Symptom:** CDC synchronization latency or inconsistent data.

Obtain the actual YAML, CDC/Connector version, and Plan for the target job.

**Steps:**

1. Identify CDC operator structure from the Plan:
   - Source: MySQL Source, Kafka Source, and similar operators.
   - Transform: Schema Transform and Data Transform.
   - Sink: Paimon Sink, Hologres Sink, and similar operators.
2. Inspect `inputs[].ship_strategy`:
   - `FORWARD`: one-to-one transfer.
   - `HASH` or an explicit key-partitioning description: distribution by the actual key/bucket. The word `SHUFFLE` alone is insufficient to establish key-partitioning semantics.
   - `CUSTOM`: custom partitioning, such as partitioning by table.
3. Analyze the data flow from YAML, schemas, transformation and routing rules, and runtime logs, distinguishing Schema processing, data transformation, and Sink writes/commits.

**Topology example** (use the actual Plan for distribution strategies):

```text
Source: MySQL Source
  ↓ FORWARD
Transform: Schema -> Data
  ↓ CUSTOM (partitioned by table)
SchemaOperator (alignment)
  ↓ key partitioning (using the actual bucket strategy)
Sink: Paimon Writer -> Committer
```

## Notes

- `<br/>` in a Plan description represents a line break; a node can contain an entire operator chain.
- Trace upstream dependencies through `inputs`; do not assume a fixed traversal order for the `nodes` array.
- The Plan of a terminated instance may be unavailable. Use saved incident evidence.
