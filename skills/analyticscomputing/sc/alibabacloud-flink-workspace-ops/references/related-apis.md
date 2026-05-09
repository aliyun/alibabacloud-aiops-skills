# Related APIs

This document lists all the Ververica APIs used by the alibabacloud-flink-workspace-ops skill.

## W1: SQL Development APIs

| API Action | Description |
|------------|-------------|
| CreateFolder | Create a folder for organizing drafts |
| UpdateFolder | Update folder information |
| DeleteFolder | Delete an empty folder |
| GetFolder | Get folder details |
| CreateDeploymentDraft | Create a SQL deployment draft |
| UpdateDeploymentDraft | Update a SQL deployment draft |
| DeleteDeploymentDraft | Delete a SQL deployment draft |
| GetDeploymentDraft | Get draft details |
| ListDeploymentDrafts | List all drafts |
| GetDeploymentDraftLock | Get draft edit lock status |
| ValidateDeploymentDraftAsync | Deep-validate a draft (async) |
| GetValidateDeploymentDraftResult | Get validation result by ticket ID |
| ValidateSqlStatement | Quick-validate SQL syntax |
| DeployDeploymentDraftAsync | Deploy a draft to production (async) |
| GetDeployDeploymentDraftResult | Get deploy result by ticket ID |

## W2: Job Operations APIs

| API Action | Description |
|------------|-------------|
| CreateDeployment | Create a deployment |
| UpdateDeployment | Update a deployment |
| GetDeployment | Get deployment details |
| ListDeployments | List all deployments |
| DeleteDeployment | Delete a deployment (irreversible) |
| GetDeploymentsByName | Search deployments by name |
| GetDeploymentsByLabel | Search deployments by label |
| GetDeploymentsByIp | Search deployments by IP |
| GetEvents | Get deployment run events |
| StartJobWithParams | Start a job instance |
| StopJob | Stop a job instance |
| GetJob | Get job instance details |
| ListJobs | List job instances for a deployment |
| DeleteJob | Delete a non-running job instance |
| HotUpdateJob | Hot-update a running job |
| GetHotUpdateJobResult | Get hot-update result |
| GetLatestJobStartLog | Get latest job startup log |
| GetJobDiagnosis | Diagnose job failures |
| CreateSavepoint | Create a savepoint |
| GetSavepoint | Get savepoint details |
| DeleteSavepoint | Delete a savepoint (irreversible) |
| ListSavepoints | List savepoints for a deployment |
| GenerateResourcePlanWithFlinkConfAsync | Generate resource plan (async) |
| GetGenerateResourcePlanResult | Get resource plan generation result |
| GetLineageInfo | Get job lineage information |
| FlinkApiProxy | Proxy Flink REST API (read-only) |

## W3: Session Cluster APIs

| API Action | Description |
|------------|-------------|
| CreateSessionCluster | Create a Session cluster |
| UpdateSessionCluster | Update Session cluster configuration |
| DeleteSessionCluster | Delete a Session cluster (irreversible) |
| GetSessionCluster | Get Session cluster details |
| ListSessionClusters | List all Session clusters |
| StartSessionCluster | Start a Session cluster |
| StopSessionCluster | Stop a Session cluster |

## W4: Dev Resources APIs

| API Action | Description |
|------------|-------------|
| CreateUdfArtifact | Create a UDF artifact |
| UpdateUdfArtifact | Update a UDF artifact |
| GetUdfArtifacts | List UDF artifacts |
| DeleteUdfArtifact | Delete a UDF artifact |
| RegisterUdfFunction | Register UDF function(s) |
| DeleteUdfFunction | Delete a UDF function |
| ListCustomConnectors | List custom connectors |
| RegisterCustomConnector | Register a custom connector |
| DeleteCustomConnector | Delete a custom connector |
| GetCatalogs | List or get catalog details |
| GetDatabases | List or get database details |
| GetTables | List or get table details |
| ExecuteSqlStatement | Execute DDL/DML SQL statement (no DQL) |
| ListEngineVersionMetadata | List supported engine versions |

## W5: Workspace Administration APIs

| API Action | Description |
|------------|-------------|
| CreateMember | Add a member with permissions |
| UpdateMember | Update member permissions |
| DeleteMember | Delete a member |
| GetMember | Get member details |
| ListMembers | List all members |
| CreateVariable | Create a variable |
| UpdateVariable | Update a variable |
| DeleteVariable | Delete a variable |
| ListVariables | List all variables |
| CreateDeploymentTargetV2 | Create a deployment target (V2) |
| UpdateDeploymentTargetV2 | Update a deployment target (V2) |
| DeleteDeploymentTarget | Delete a deployment target |
| ListDeploymentTargets | List all deployment targets |