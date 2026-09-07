# Lingjun Node State Chinese Mapping Table (Node OperatingState i18n - MANDATORY in zh sessions)

> Authoritative source: "Lingjun customer-facing state (OperatingState) zh-en mapping table" (DingTalk doc QOG9lyrgJPPNL2rXIlxXreBjJzN67Mw4, synced 2026-08-21).
> In zh sessions, node states in any user-facing output (query results, confirmation tables, receipts, progress reports, final reports) **must** be translated to Chinese per this table; this table is the sole authoritative rendering and must not be freely paraphrased. States not listed here stay in English and are annotated as "unlisted state".
> The OperatingState returned by the API is the customer-facing state, converged by mapping from internal control states (NodeState, ~200 stacked states).

## I. Basic lifecycle

```bash
| English state | Chinese state | Description |
|---|---|---|
| Using | `使用中` | Node delivered to the cluster, normally available |
| Unused | `未使用` | Node purchased but not joined to any cluster (resource-pool state) |
| Extending | `扩容中` | Node is joining the cluster |
| Cutting | `缩容中` | Node is being removed from the cluster |
| Operating | `操作中` | An O&M operation is running (e.g. reimage, RunCommand) |
| Diagnosing | `诊断中` | Node hardware / AI-job-log diagnosis in progress |
| Switching | `切换中` | Node switching in progress |
```

## II. Service suspension (expiry / overdue related)

```bash
| English state | Chinese state | Description |
|---|---|---|
| ClusterNodeStopping | `集群节点停服中` | In-cluster node is being suspended |
| ClusterNodeStopped | `集群节点已停服` | In-cluster node has been suspended |
| UnusedNodeStopping | `未使用节点停服中` | Unused node is being suspended |
| UnusedNodeStopped | `未使用节点已停服` | Unused node has been suspended |
| ClusterNodeRecovering | `集群节点续费恢复中` | Recovering online after renewal following suspension |
| UnusedNodeRecovering | `未使用节点续费恢复中` | Unused node recovering after renewal |
```

## III. Shutdown

```bash
| English state | Chinese state | Description |
|---|---|---|
| ClusterNodeShuttingDown | `集群节点关机中` | Shutting down |
| ClusterNodeShutdown | `集群节点已关机` | Shut down |
```

## IV. Repair (fault-handling chain)

```bash
| English state | Chinese state | Description |
|---|---|---|
| ClusterNodeRepairPendingApproval | `集群节点维修待审批` | Cluster node faulty, awaiting user approval for repair |
| PreparationForRepairingClusterNode | `集群节点维修下线中` | Post-approval pre-processing for repair offline |
| ClusterNodeRepairing | `集群节点维修中` | Hardware repair in progress |
| RecoveringClusterNode | `集群节点维修上线中` | Repair completed, recovering online |
| UnusedNodeRepairPendingApproval | `未使用节点维修待审批` | Unused node awaiting repair approval |
| UnusedNodeRepairing | `未使用节点维修中` | Unused node under repair (internal pending-repair/offline/online states all converge to this) |
| RecoveringUnusedNode | `未使用节点维修上线中` | Unused node recovering online after repair |
| ClusterNodeApprovalPendingRenew | `集群节点维修待审批已停服` | Repair pending approval and already suspended |
| ClusterNodeRepairingPendingRenew | `集群节点维修中已停服` | Under repair and already suspended |
```

## V. Reboot repair (self-healing)

```bash
| English state | Chinese state | Description |
|---|---|---|
| ClusterNodeRebootPendingApproval | `集群节点重启待审批` | Reboot repair needed, awaiting user approval |
| UnusedNodeRebootPendingApproval | `未使用节点重启待审批` | Unused node awaiting reboot approval |
| ClusterNodeRebooting | `集群节点重启修复中` | Within the reboot self-healing window |
| UnusedNodeRebooting | `未使用节点重启修复中` | Unused node under reboot repair |
```

## VI. Release / replace / reconfigure / upgrade

```bash
| English state | Chinese state | Description |
|---|---|---|
| ReleaseLocking | `待释放` | Pre-release validation lock |
| Releasing | `释放中` | Node is being released / unsubscribed |
| Replacing | `节点替换中` | Faulty node being replaced by a new node |
| ClusterNodeReconfiguring | `集群节点变配中` | Spec reconfiguration in progress (internal PendingReconfig-family states map here) |
| ClusterNodeUpgradePendingApproval | `集群节点升级待审批` | Cluster node upgrade awaiting approval |
| UnusedNodeUpgradePendingApproval | `未使用节点升级待审批` | Unused node upgrade awaiting approval |
| ClusterNodeUpgrading | `集群节点升级中` | Cluster node upgrade executing |
| UnusedNodeUpgrading | `未使用节点升级中` | Unused node upgrade executing |
| SoftwareRestoring | `软件恢复中` | Software-state recovery |
```

## Rendering rules

- zh sessions: the state column / state value renders the **Chinese state** (literal from the mapping table above); when an exact cross-check against the raw API value is needed, the Chinese-state-plus-English form may be written, but tables / listings default to pure Chinese.
- en sessions: keep the original English state.
- Decision logic (scripts / jq / precheck conditions) still compares against the raw English value; translation happens only at the user-facing rendering layer.
- Hyper nodes have a separate HyperNodeState (health-granular states such as HealthyUsing / SubhealthyUsing / AbnormalUsing); hyper-node states not covered by this table stay in English verbatim.
