## VVP Product Concept Model

### Entity Hierarchy and Relationships

Workspace
 └─ Namespace: the basic unit of job management and resource isolation; all configurations, jobs, and permissions live under a single Namespace
     ├─ DeploymentDraft: the configuration definition (template) of a job draft, including code artifact, resource specs, and runtime parameters. After deployment, a corresponding Deployment is generated
     ├─ Deployment: the configuration definition (template) of a job, including code artifact, resource specs, and runtime parameters
     │    └─ Job: a single run instance of a Deployment [1:N]. A Job is a snapshot of its Deployment; most fields are immutable. Changes to a job are mainly applied by modifying the deployment and restarting the Job (except HotUpdate).
     │         └─ Savepoint: a state snapshot of a running Job [1:N], used for stateful recovery
     ├─ SessionCluster: a shared cluster for development/testing only; does not support monitoring alerts or autotuning
     ├─ ResourceQueue: the allocation unit of compute resources; a Deployment must run on a resource queue or a SessionCluster
     └─ Catalog (SQL metadata): manages metadata such as databases, tables, and columns used in SQL jobs
          └─ Database → Table

- Users locate a deployment configuration via deployment_id and a specific run instance via job_id
- `{namespace}` in all API paths is automatically replaced with the current namespace

### Job Types (artifact.kind)

| Enum Value | Description |
|--------|------|
| SQLSCRIPT | SQL job |
| MATERIALIZED_TABLE | Materialized table job (SQL subtype) |
| JAR | JAR job |
| PYTHON | Python job |
| YAML | Flink CDC data ingestion job (SQL subtype) (VVR 8.0.9+) |

### ExecutionMode
The execution mode of a deployment and its jobs is fixed at creation time and cannot be changed.

| Enum Value | Description |
|--------|------|
| STREAMING | Streaming mode, runs continuously to process unbounded data streams. A deployment can have only one non-terminal job. |
| BATCH | Batch mode, finishes after processing a bounded dataset. A deployment can have multiple non-terminal jobs. |

### Job State

STARTING → RUNNING → FINISHED / CANCELLED / FAILED

| State | Category | Description |
|------|------|------|
| STARTING | Transitional | Job is starting |
| RUNNING | Stable | Job is running |
| FINISHED | Terminal | A batch or bounded-stream job completed, or a streaming job completed after stop-with-savepoint. |
| CANCELLED | Terminal | Stopped intentionally by the user |
| FAILED | Terminal | Job run failed |

### Engines and Versions

Both VVR and Flash are commercial Flink engines provided by VVP.

The `engineVersion` or `versionName` field is the display name of an engine version, unique within a `workspace`, e.g. "vvr-8.0.6-flink-1.17".

Engine version labels, in order of preference: recommended > stable > normal > EOS.

Some features have version requirements (e.g., dynamic parameter update requires VVR 8.0.1+, operator-level TTL requires VVR 8.0.7+, YAML jobs require VVR 8.0.9+).
