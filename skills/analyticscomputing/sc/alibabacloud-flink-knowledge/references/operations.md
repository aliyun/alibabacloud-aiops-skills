# Alibaba Cloud Realtime Compute for Apache Flink — Operations Management Reference

## Operations Management Full Workflow Overview

```
Write SQL → Deep Inspection → Debug → Deploy (deployment target: resource queue / Session cluster) → Start → Monitor/Alert → Tune/Diagnose
```

## Job Deployment

### Deployment Process

1. On the job editing page, click **Deploy** in the upper-right corner
2. Enter a version note (recommended)
3. Select deployment target and resources
4. Confirm deployment (deployment does not affect running jobs)

### Deployment Target Selection

| Deployment Target | Suitable Environment | Key Features |
|---|---|---|
| **Resource Queue** | Production | Dedicated resources with no preemption; supports resource isolation and management; suitable for long-running high-priority tasks |
| **Session Cluster** | Dev/Test | Multiple jobs share the same JM; fast startup; suitable for debugging and lightweight tasks |

> **Important**: Jobs running on Session clusters **cannot view job logs**.

## Job Startup

- Entry: **O&M Center > Job O&M** → Click **Start**
- Startup modes:
  - **Stateless Start**: Does not restore state; runs from scratch
  - **Restore from Latest Checkpoint**: Automatically selects the most recent Checkpoint
  - **Restore from Specified Savepoint**: Restores from a specified Savepoint path

### Startup Parameter Configuration

- Maximum retry attempts allowed
- Restart strategy (fixed-delay restart, exponential backoff restart, etc.)

## Job Stop

- Entry: **O&M Center > Job O&M** → Click **Stop**
- Scenarios requiring stop-then-restart:
  - SQL code modifications
  - Adding, removing, or modifying WITH parameters
  - Updating non-dynamically-effective parameters
  - Updating the job engine version (when state is incompatible)
  - Wanting a fresh start for the job (without reusing State)

## Job Logs

### Log Types

| Log Type | How to View | Description |
|---|---|---|
| **Startup Logs** | Job O&M page → Logs | Logs during job startup; for troubleshooting startup failures |
| **Runtime Logs** | Task Managers → Select Task → Logs | Business logs during job execution |
| **Exception Logs** | Job O&M page → Exception Logs | Stack traces and error information for runtime exceptions |
| **Historical Instance Logs** | Historical Jobs → Logs | Logs from stopped/expired job instances |

### Log Configuration

- Job log levels are configurable (INFO/WARN/ERROR/DEBUG)
- Supports separate output for different log levels

## State Management (Checkpoint & Savepoint)

### Concepts

| Concept | Description |
|---|---|
| **Checkpoint** | State snapshots automatically created by the system at regular intervals; used for automatic failure recovery |
| **Savepoint** | Manually created complete state snapshots; used for job upgrades, migration, and state reuse |

### Operations

| Operation | Description |
|---|---|
| **Create Savepoint** | Actively creates a state snapshot while the job is running |
| **View State Collection** | View Checkpoint and Savepoint lists and details |
| **Start from Savepoint** | Start a job by selecting a specified Savepoint path |
| **State Compatibility Check** | Before upgrading versions, check whether old and new version states are compatible |
| **Clean Up Historical State** | Delete unneeded Checkpoints/Savepoints to free storage |

### Best Practices

- Always enable Checkpoint for production jobs; set interval based on latency requirements (default 60s)
- Create a Savepoint before upgrading or migrating jobs
- Periodically clean up unneeded state data

## Smart Tuning & Diagnostics

### Smart Tuning

- Monitors job throughput, resource utilization, backpressure, and other metrics
- Automatically adjusts resource configuration (CPU/Memory)
- Resolves issues such as **insufficient job throughput** and **resource waste**

### Scheduled Tuning

- System automatically checks at configured intervals and provides tuning recommendations
- Tuning configurations are automatically applied after user confirmation

### Smart Diagnostics

Can detect and diagnose the following issues:
- **Abnormal Job Execution**
- **Data Skew** (one partition processes far more data than others)
- **Backpressure** (upstream data production rate exceeds downstream processing rate)
- **TM Disconnection** (TaskManager node disconnects abnormally)
- **Checkpoint Timeout or Failure**

Provides understandable and actionable recommendations after diagnosis.

### Common Backpressure Troubleshooting Directions

1. **Slow Sink writes**: Check downstream database performance, batch size, concurrency
2. **Data skew**: Check for hot keys; consider salting, local-global two-phase aggregation
3. **Upstream data bursts**: Limit consumption rate; increase partitions
4. **Excessive state size**: Enable state compression (TTL); use incremental checkpoints

## Dynamic Parameter Updates

- Adjust certain parameter configurations **without restarting the job**
- Typical scenarios:
  - Dynamic TM scaling (increase/decrease TaskManager count)
  - Adjust Checkpoint interval
  - Update log level
  - Adjust parallelism (certain scenarios)

## Monitoring and Alerting

### Monitoring Services

| Service | Positioning |
|---|---|
| **CloudMonitor** (Free) | Basic metrics monitoring and alerting |
| **ARMS** | Application-level advanced monitoring with richer features |

### Key Metrics

- **Data Latency** (Source Delay): Time from data generation to processing
- **Throughput** (Records/sec): Number of records processed per second
- **CPU/Memory Utilization**: Resource consumption status
- **Backpressure Ratio**: Proportion of TaskManagers in backpressure state
- **Checkpoint Duration/Size**: Core health indicators
- **JVM GC Time**: Impact of garbage collection on job performance

### Alert Configuration

Supported notification methods: **DingTalk**, **Email**, **SMS**. Can integrate with external monitoring systems such as **Prometheus**.

## Data Lineage

- View data flow relationships between jobs (data tracing/tracking)
- Quickly locate upstream and downstream dependencies
- Assess the impact scope of changes

## Workflow Management (Task Orchestration)

- Create visual DAGs (Directed Acyclic Graphs) via **drag-and-drop**
- Define scheduling strategies (timed execution, dependency triggers, etc.)
- Supports inter-node dependency management
- Workflow instance and node instance management

## Resource Management

### Storage Types

Select when activating a workspace:
- **Fully Managed Storage**: System-managed; no infrastructure concerns
- **Bound OSS Bucket**: Bring-your-own storage; suitable for scenarios with existing OSS resources

### Resource Queues

- Implements resource isolation and management
- Resources between different queues are non-preemptive
- Suitable for multi-tenant, multi-team scenarios

## Version Management

- Supports **multi-version job management**
- Code comparison between versions
- Version rollback
- Supports remote **Git repository integration** (GitHub/GitLab/Gitee)

## VS Code Local Development

- Install the Alibaba Cloud Flink VS Code extension
- Write SQL/JAR/Python code locally
- One-click deployment to the cloud
- Suitable for developers who prefer IDEs

## Common Issue Troubleshooting Quick Reference

| Symptom | Troubleshooting Direction |
|---|---|
| Job startup failure | Check startup logs, resource configuration, connector dependencies, network connectivity |
| High job latency | Check backpressure, data skew, sink bottlenecks, slow lookup table queries |
| Persistent Checkpoint failures | Reduce state size, adjust intervals, check storage availability |
| OOM | Increase TM memory; check for unbounded state growth |
| Data loss | Check whether watermark settings are correct; check if out-of-order tolerance is too small causing data discard |
| Job cannot connect to external systems | Check VPC network connectivity, whitelist configuration, Kerberos authentication |

## Official Documentation Links

- [Deploy Jobs](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/create-a-deployment)
- [Start Jobs](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/start-a-deployment)
- [Job State Management](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/state-management/)
- [Tuning and Diagnostics](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/deployment-diagnostics-and-optimization/)
- [Job Logs](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/job-logs/)
- [Dynamic Parameter Updates](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/dynamically-update-deployment-parameters)
- [Job Monitoring and Alerting](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/monitoring-and-alerting/)
- [View Data Lineage](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/view-data-lineage)
- [Manage Workflows](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-workflows)
- [Resource Management](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/resource-management)
- [Manage Resource Queues](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-resource-queues)
- [Manage Job Versions](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/manage-job-versions)
- [VS Code Local Development](https://help.aliyun.com/zh/flink/realtime-flink/user-guide/vscode-extension-for-local-development)
