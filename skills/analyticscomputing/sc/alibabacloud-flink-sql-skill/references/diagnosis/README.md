# Job Performance Assessment and Troubleshooting

Unified entry flow: define the objective → select evidence → query and analyze as needed. Reuse existing evidence and query only missing items during analysis.

## Document Responsibilities

| File | Responsibility | Read when |
|------|----------------|-----------|
| [job-observability.md](job-observability.md) | Defines query methods, authentication, API boundaries, and evidence conventions | The required data has been identified |
| [sql-perf-knowledge.md](sql-perf-knowledge.md) | Documents symptoms, causes, verification points, and applicability of optimizations for common issues | Looking up performance knowledge or applying a known pattern during diagnosis |
| [sql-perf-diagnosis.md](sql-perf-diagnosis.md) | Locates common issues through runtime Metrics and diagnosis rules | Diagnosing a common performance issue in an actual job |
| [job-deep-anlysis.md](job-deep-anlysis.md) | Explains complex behavior from SQL, execution plans, configuration, and runtime evidence | Common patterns are insufficient, or the issue involves plan or computation semantics |

## 1. Define the Objective and Scope

First distinguish the user's objective:

- **Performance assessment:** a single data query, overall runtime assessment, or before/after comparison. Define the object, time, data items, and the relevant throughput, latency, resources, or stability. For comparisons, verify that the Jobs, versions, configurations, and loads are comparable.
- **Troubleshooting:** an anomaly or question about a specific job. Define actual versus expected behavior, impact scope, and incident period, then validate candidate causes against observed evidence.
- **Performance knowledge:** a general concept, typical symptom, common cause, configuration meaning, or optimization condition that needs explanation. Consult the applicable knowledge and its scope.

For a query or diagnosis of an actual job, derive the region, Workspace, Namespace, Deployment, and Job from the job URL or existing context. Ask only for values that cannot be determined from existing information or read-only queries. Distinguish the current moment, a specified historical moment, and a time range, and fix the time zone. If a historical instance cannot be identified, do not substitute the current instance.

## 2. Select Evidence

Choose the required data and its purpose from the objective and existing evidence:

| Objective or symptom | Query first | Add when evidence requires it |
|----------------------|-------------|-------------------------------|
| Single data query | The requested data item, object, and time | Entity identity, unit, and aggregation semantics |
| Overall performance | Job state, SQL/configuration, runtime topology, throughput, latency, busy/idle/backpressure, resources, and Checkpoint summary | Historical trends, Subtask distribution, and resource plan |
| Falling throughput, backlog, or increasing latency | Input/output rate, source backlog, backpressure, operator and Subtask load, and TM resources | External calls, GC, State access, and an available flame graph or thread dump |
| CPU or memory anomaly | Resource Metrics during the incident, configuration, TM distribution, logs, and events | GC, allocation hotspots, State, caches, and batch buffers |
| Checkpoint or recovery anomaly | Checkpoint records/details, State Backend and restore configuration, exceptions, and relevant logs | Backpressure, I/O, resources, and Savepoint information from the same period |
| Startup failure, restart, or scheduling anomaly | Target-instance state, startup logs, platform events, exceptions, and platform diagnosis | Runtime logs, resource configuration, and dependencies |
| No output, delayed trigger, or incorrect result | SQL semantics, inputs/outputs, Watermarks, execution plan, and exceptions | Lineage, TTL, Changelog, and Sink commit conditions |
| Topology, parallelism, or resource-allocation question | Actual execution plan, Job configuration, runtime resources, and ResourcePlan | Table/field lineage, operator load, and official version notes |

Record the object and time, required data, purpose, existing evidence, and gaps.

## 3. Query Consistently

Execute the selected queries according to [job-observability.md](job-observability.md), preserving its authentication, entity, and time conventions, then extract or aggregate the requested data. Failure of one item does not block independent queries; retain successful results and state coverage gaps.

## 4. Analyze as Needed

- **Performance knowledge:** read [sql-perf-knowledge.md](sql-perf-knowledge.md) for typical symptoms, common causes, investigation methods, configuration meaning, and optimization conditions. When applying it to an actual job, verify applicability against observed evidence.
- **Common performance issues:** read [sql-perf-diagnosis.md](sql-perf-diagnosis.md), select the relevant diagnosis branch using the target Job's configuration, runtime topology, Metrics, logs, and Checkpoints, and validate candidate bottlenecks. Consult the knowledge base when pattern details are needed.
- **Complex plan or computation semantics:** read [job-deep-anlysis.md](job-deep-anlysis.md) and provide the target version, SQL/configuration, Plan, incident period, and existing evidence.
- **Additional query required:** state which hypothesis the query will test, then obtain the missing evidence through [job-observability.md](job-observability.md). When no API or permission is available, state the limitation; do not start profiling, restart the Job, or change configuration without authorization.
