# Command Quick Reference

> **All commands must be executed as `safe_aliyun aliyun ...`** (see [scripts.md](scripts.md)). This file is a command-skeleton quick reference; all examples use `cn-hangzhou`.

---

## 1. Resource Locator (Feature 1)

```bash
# List all clusters
safe_aliyun aliyun eflo-controller list-clusters \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou

# Cluster detail
safe_aliyun aliyun eflo-controller describe-cluster \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid>

# Regular nodes in the cluster
safe_aliyun aliyun eflo-controller list-cluster-nodes \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid>

# Hyper nodes in the cluster
safe_aliyun aliyun eflo-controller list-cluster-hyper-nodes \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid>

# Node / hyper node detail
safe_aliyun aliyun eflo-controller describe-node \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --node-id <nid>

safe_aliyun aliyun eflo-controller describe-hyper-node \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --hyper-node-id <hnid>

# Available images — the only legitimate source of ImageId for reimage-nodes (forbidden_inference)
safe_aliyun aliyun eflo-controller list-images \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  [--max-results 20] [--next-token <tok>]

# Region discovery seed — the sole command allowed to use cn-hangzhou without a user-specified Region
safe_aliyun aliyun eflo-controller describe-regions \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou
```

---

## 2. Diagnostic (Features 2-4)

```bash
# Submit a diagnostic task (BasicCheck / NodeHardwareCheck / CheckByAiJobLogs; enum re-verified 2026-08-19; NetConfigCheck/NetRuntimeCheck deprecated)
safe_mutate create-diagnostic-task aliyun eflo-controller create-diagnostic-task \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid> \
  --diagnostic-type BasicCheck \
  --node-ids <nid1> <nid2>

# CheckByAiJobLogs requires the extra --ai-job-log-info JSON
safe_mutate create-diagnostic-task aliyun eflo-controller create-diagnostic-task \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid> \
  --diagnostic-type CheckByAiJobLogs \
  --node-ids <nid1> \
  --ai-job-log-info '{"StartTime":"2026-05-16T08:00:00+0800","EndTime":"2026-05-16T09:00:00+0800","AiJobLogs":[{"NodeId":"<nid1>","AiInstance":"job-xxx","Logs":["/var/log/nccl.log"]}]}'

# Query a single diagnostic (polling)
safe_aliyun aliyun eflo-controller describe-diagnostic-result \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --diagnostic-id <did>

# Diagnostic history list (with type filter)
safe_aliyun aliyun eflo-controller list-diagnostic-results \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --diag-type NetDiag [--max-results 100] [--next-token <tok>]   # --diag-type is required; the read endpoint only accepts the legacy enum NetDiag/ServerDiag/BasicCheck (enum split, see api-parameters.md #9)
```

---

## 3. Repair (Feature 6)

```bash
# Reboot
safe_mutate reboot-nodes aliyun eflo-controller reboot-nodes \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid> --nodes <nid1> <nid2>

# Reimage (structured list; ImageId / LoginPassword must come from HITL)
safe_mutate reimage-nodes aliyun eflo-controller reimage-nodes \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --cluster-id <cid> \
  --nodes Hostname=<h1> ImageId=<imgid> LoginPassword='<pw>' NodeId=<nid1>

# Stop (note: no --cluster-id)
safe_mutate stop-nodes aliyun eflo-controller stop-nodes \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --nodes <nid1> <nid2>

# Fault declaration (single node; --diagnosis-type only accepts COMPREHENSIVE)
safe_mutate report-node-status aliyun eflo-controller report-node-status \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --node-id <nid1> --diagnosis-type COMPREHENSIVE \
  --description 'GPU ECC errors observed'
```

---

## 4. Auxiliary Telemetry (Feature 7)

```bash
# --from-time / --to-time are epoch-second integers (the Agent converts ISO8601 to epoch before issuing; see SKILL.md Feature 7)
safe_aliyun aliyun eflo-controller list-syslogs \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --node-id <nid> \
  --from-time <epoch_from> \
  --to-time <epoch_to> \
  [--query 'error OR fail OR panic'] [--reverse true]
```

---

## 5. Fault Report Tracking (Feature 8)

```bash
# Historical fault report list (optional filter by node / status; a non-empty NextToken must be exhausted)
safe_aliyun aliyun eflo-controller list-fault-reports \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  [--nodes <nid1> <nid2>] \
  [--status Processing|DiagnosisTerminating|DiagnosisTerminated|DiagnosisPassed|FaultConfirmed|FaultFinish] \
  [--max-results 20] [--next-token <tok>]

# Fault report detail (--report-id required, e.g. i-997086804007)
safe_aliyun aliyun eflo-controller describe-fault-report \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --report-id <rid>

# Stop an in-progress fault diagnosis (mutating; go through the safe_mutate two-phase flow; confirm a stoppable state via describe-fault-report before submitting)
safe_mutate stop-node-diagnostic aliyun eflo-controller stop-node-diagnostic \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --report-id <rid>

# Approve a platform-raised maintenance proposal (mutating; safe_mutate two-phase; closed enum only,
# match the measured pending state: RepairMachine<-ClusterNodeRepairPendingApproval,
# RebootMachine<-ClusterNodeRebootPendingApproval, UpgradeMachine<-ClusterNodeUpgradePendingApproval)
safe_mutate approve-operation aliyun eflo-controller approve-operation \
  --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
  --node-id <nid> --operation-type <RepairMachine|RebootMachine|UpgradeMachine>
```
