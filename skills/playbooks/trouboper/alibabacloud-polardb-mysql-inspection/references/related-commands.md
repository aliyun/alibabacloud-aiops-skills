# Related Commands

## PolarDB API

| API | Product | Description |
|---|---|---|
| `describe-db-cluster-attribute` | polardb | Get cluster basic information (spec, storage, status, nodes) |
| `describe-db-nodes` | polardb | Get node list with roles and specs |
| `describe-db-cluster-version` | polardb | Get cluster version details (major, minor, revision, proxy) |
| `describe-db-cluster-performance` | polardb | Get cluster-level performance metrics (CPU, memory, disk, IO, connections) |
| `describe-db-node-performance` | polardb | Get node-level performance metrics |
| `describe-db-proxy-performance` | polardb | Get Proxy performance metrics (CPU, LSN mismatch, queries in transaction) |
| `describe-db-cluster-parameters` | polardb | Get running parameters (e.g., max_connections) |
| `describe-slow-logs` | polardb | Get slow query log statistics |
| `describe-das-config` | polardb | Get DAS configuration (for ESSD instances) |

## DAS API

| API | Product | Description |
|---|---|---|
| `create-storage-analysis-task` | das | Create a storage analysis task for space Top20 |
| `get-storage-analysis-result` | das | Get storage analysis task results |
| `get-auto-increment-usage-statistic` | das | Get auto-increment primary key usage statistics |
| `get-mysql-all-session-async` | das | Get current session information (async) |

## CloudMonitor API

| API | Product | Description |
|---|---|---|
| `describe-alert-log-list` | cms | Get alert history records (filtered by PolarDB + cluster ID) |

## Local Utility Commands (no --user-agent)

| Command | Description |
|---|---|
| `aliyun configure list` | Check current credential profiles |
| `aliyun version` | Check Aliyun CLI version (must be >= 3.3.3) |
| `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |
| `aliyun plugin update` | Update all installed plugins to latest version |
