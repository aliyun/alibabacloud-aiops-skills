# Related Alibaba Cloud Flink APIs

This document lists the Ververica APIs exposed by the unified Flink SQL lifecycle CLI.

## SQL Development APIs

| API action | Description |
|------------|-------------|
| CreateFolder | Create a Folder for organizing Drafts |
| UpdateFolder | Update Folder information |
| DeleteFolder | Delete an empty Folder |
| GetFolder | Get Folder details |
| CreateDeploymentDraft | Create an SQL Deployment Draft |
| UpdateDeploymentDraft | Update an SQL Deployment Draft |
| DeleteDeploymentDraft | Delete an SQL Deployment Draft |
| GetDeploymentDraft | Get Draft details |
| ListDeploymentDrafts | List all Drafts |
| GetDeploymentDraftLock | Get the Draft editing-lock state |
| ValidateDeploymentDraftAsync | Validate a Draft in depth (asynchronous) |
| GetValidateDeploymentDraftResult | Get a validation result by ticket ID |
| ValidateSqlStatement | Quickly validate SQL syntax |
| DeployDeploymentDraftAsync | Deploy a Draft to production (asynchronous) |
| GetDeployDeploymentDraftResult | Get a deployment result by ticket ID |

## Deployment and Job Operations APIs

| API action | Description |
|------------|-------------|
| CreateDeployment | Create a Deployment |
| UpdateDeployment | Update a Deployment |
| GetDeployment | Get Deployment details |
| ListDeployments | List all Deployments |
| DeleteDeployment | Delete a Deployment (irreversible) |
| GetDeploymentsByName | Search for Deployments by name |
| GetDeploymentsByLabel | Search for Deployments by label |
| GetDeploymentsByIp | Search for Deployments by IP address |
| GetEvents | Get Deployment runtime events |
| StartJobWithParams | Start a Job instance |
| StopJob | Stop a Job instance |
| GetJob | Get Job-instance details |
| ListJobs | List Job instances for a Deployment |
| DeleteJob | Delete a Job instance that is not running |
| HotUpdateJob | Hot-update a running Job |
| GetHotUpdateJobResult | Get the HotUpdate result |
| GetLatestJobStartLog | Get the latest Job startup log |
| GetJobDiagnosis | Diagnose Job failure |
| CreateSavepoint | Create a Savepoint |
| GetSavepoint | Get Savepoint details |
| DeleteSavepoint | Delete a Savepoint (irreversible) |
| ListSavepoints | List Savepoints for a Deployment |
| GenerateResourcePlanWithFlinkConfAsync | Generate a resource plan (asynchronous) |
| GetGenerateResourcePlanResult | Get the resource-plan generation result |
| GetLineageInfo | Get Job lineage information |
| FlinkApiProxy | Proxy the Flink REST API (read-only) |

## Session Cluster APIs

| API action | Description |
|------------|-------------|
| CreateSessionCluster | Create a Session Cluster |
| UpdateSessionCluster | Update Session Cluster configuration |
| DeleteSessionCluster | Delete a Session Cluster (irreversible) |
| GetSessionCluster | Get Session Cluster details |
| ListSessionClusters | List all Session Clusters |
| StartSessionCluster | Start a Session Cluster |
| StopSessionCluster | Stop a Session Cluster |

## SQL Development Resource APIs

| API action | Description |
|------------|-------------|
| CreateUdfArtifact | Create a UDF Artifact |
| UpdateUdfArtifact | Update a UDF Artifact |
| GetUdfArtifacts | List UDF Artifacts |
| DeleteUdfArtifact | Delete a UDF Artifact |
| RegisterUdfFunction | Register one or more UDF Functions |
| DeleteUdfFunction | Delete a UDF Function |
| ListCustomConnectors | List custom Connectors |
| RegisterCustomConnector | Register a custom Connector |
| DeleteCustomConnector | Delete a custom Connector |
| GetCatalogs | List Catalogs or get Catalog details |
| GetDatabases | List Databases or get Database details |
| GetTables | List Tables or get Table details |
| ExecuteSqlStatement | Execute a DDL/DML SQL statement (DQL is unsupported) |
| ListEngineVersionMetadata | List supported engine versions |

## SQL Runtime Resource APIs

| API action | Description |
|------------|-------------|
| CreateVariable | Create a variable |
| UpdateVariable | Update a variable |
| DeleteVariable | Delete a variable |
| ListVariables | List all variables |
| CreateDeploymentTargetV2 | Create a Deployment Target (V2) |
| UpdateDeploymentTargetV2 | Update a Deployment Target (V2) |
| DeleteDeploymentTarget | Delete a Deployment Target |
| ListDeploymentTargets | List all Deployment Targets |
