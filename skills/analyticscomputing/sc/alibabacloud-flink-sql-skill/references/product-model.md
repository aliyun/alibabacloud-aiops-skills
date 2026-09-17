# Alibaba Cloud Flink SQL Product Model

### Entity Hierarchy and Relationships

Workspace
 └─ Namespace: the basic unit for job management and resource isolation; every configuration, job, and permission belongs to a Namespace
     ├─ DeploymentDraft: the configuration definition (template) of a job draft, including its code Artifact, resource specification, and runtime parameters; deploying it creates a corresponding Deployment
     ├─ Deployment: the configuration definition (template) of a job, including its code Artifact, resource specification, and runtime parameters
     │    └─ Job: one runtime instance of a Deployment, with a 1:N relationship. A Job is a snapshot of its Deployment at start time, and most fields are immutable. Except for HotUpdate, job changes normally take effect by updating the Deployment and restarting the Job
     │         └─ Savepoint: a state snapshot of a running Job, with a 1:N relationship, used for stateful recovery
     ├─ SessionCluster: a shared cluster for development and testing only; monitoring alerts and automatic tuning are not supported
     ├─ ResourceQueue: the unit of compute-resource allocation; a Deployment must run on a ResourceQueue or SessionCluster
     └─ Catalog (SQL metadata): manages metadata such as Databases, Tables, and Columns used by SQL jobs
          └─ Database → Table

- Use `deployment_id` to locate a Deployment configuration and `job_id` to locate a specific runtime instance.
- Every `{namespace}` placeholder in an API path is automatically replaced with the current Namespace.

### Job Kinds (`artifact.kind`)

| Enum value | Description |
|------------|-------------|
| SQLSCRIPT | SQL job |
| MATERIALIZED_TABLE | Materialized Table job (an SQL subtype) |

### ExecutionMode

The execution mode of a Deployment and its Jobs is fixed when the Deployment is created and cannot be changed later.

| Enum value | Description |
|------------|-------------|
| STREAMING | Streaming mode continuously processes unbounded streams. A Deployment can have only one Job that has not reached a terminal state. |
| BATCH | Batch mode terminates after processing a bounded data set. A Deployment can have multiple Jobs that have not reached a terminal state. |

### Job States

STARTING → RUNNING → FINISHED / CANCELLED / FAILED

| State | Category | Description |
|-------|----------|-------------|
| STARTING | Transitional | The Job is starting |
| RUNNING | Stable | The Job is running |
| FINISHED | Terminal | A Batch or bounded-stream job has completed, or a Streaming job has terminated normally through stop-with-savepoint |
| CANCELLED | Terminal | A user explicitly stopped the Job |
| FAILED | Terminal | The Job failed |

### Engines and Versions

VVR and Flash are commercial Flink engines provided by VVP.

The `engineVersion` or `versionName` field is the engine version's display name and is unique within a `workspace`, for example `vvr-8.0.6-flink-1.17`.

The preferred order of engine-version labels is: recommended > stable > normal > EOS.

Some SQL features have version requirements, including dynamic parameter updates and operator-level State TTL. Verify support against the current online documentation.
