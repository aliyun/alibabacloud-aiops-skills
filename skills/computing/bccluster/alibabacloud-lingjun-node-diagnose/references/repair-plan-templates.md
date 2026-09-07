# Repair Plan Templates

This skill never "auto-repairs" - every repair CLI must go through the `safe_mutate` two-phase commit + the confirmation word (session-language dependent; the zh word lives in `lib/core/i18n.sh`, en word is "confirm"). This file gives the Phase 1 warning box + one-shot execution template for each repair plan.

---

## A. Reboot Nodes (reversible, most common)

Applies to: BasicCheck SOFT-class faults, NCCL/CUDA subprocess zombification, container-runtime anomalies.

### Phase 1 warning box

```
🛑 About to submit node reboot (mutating, but reversible):

  Action            : reboot-nodes
  Region            : cn-hangzhou
  ClusterId         : <cid>
  Targets (1)       :
    - Type=Node  NodeId=e01-cn-xxx  Hostname=node-001  MachineType=efg1.nvga1
  IgnoreFailedNodeTasks : false (default)
  CLI               : aliyun eflo-controller reboot-nodes \
                        --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
                        --region cn-hangzhou \
                        --cluster-id <cid> --nodes e01-cn-xxx

⚠️ Impact: the node shuts down and reboots immediately; AI Jobs running on it are interrupted. After the reboot the node returns to Using automatically (~5–10 min).

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```

### Verification

`describe-node.OperatingState` returns to `Using` within 5-10 min.

---

## B. Reimage Nodes (destructive, use with caution)

Applies to: BasicCheck detected severe driver/firmware/kernel pollution (reboot ineffective), user explicitly wants to "reset the whole machine". (Network diagnostics NetConfigCheck/NetRuntimeCheck were deprecated on 2026-08-19.)

### Phase 1 warning box (must display the double-confirmation wording)

```
🛑 About to submit node reimage (mutating, ⚠️⚠️⚠️ system disk will be wiped):

  Action            : reimage-nodes
  Region            : cn-hangzhou
  ClusterId         : <cid>
  Targets (1)       :
    - Type=Node  NodeId=e01-cn-xxx  Hostname=node-001  MachineType=efg1.nvga1
  ImageId           : <ImageId>      ← forbidden_inference, user-selected from list-images
  LoginPassword     : ******         ← forbidden_inference, user-typed
  Hostname          : node-001       ← forbidden_inference, user-typed or kept original
  CLI               : aliyun eflo-controller reimage-nodes \
                        --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
                        --region cn-hangzhou --cluster-id <cid> \
                        --nodes Hostname=node-001 ImageId=<imgid> LoginPassword='******' NodeId=e01-cn-xxx

⚠️ DESTRUCTIVE: all data on the system disk is permanently erased (user-space directories, ephemeral images, training checkpoints) and cannot be recovered.
   Mounted data disks / NAS / OSS are unaffected.

Reply "confirm" to submit ("confirm" counts as acknowledgement of the wipe risk above); any other input cancels.
```

### Verification

`describe-node.OperatingState=Using` AND `describe-node.ImageId=<new ImageId>`.

---

## C. Stop Nodes (reversible, offline maintenance)

Applies to: the user explicitly wants to "shut down for a while for offline handling". Note the CLI has **no `--cluster-id`**.

### Phase 1 warning box

```
🛑 About to submit node shutdown (mutating, reversible):

  Action            : stop-nodes
  Region            : cn-hangzhou
  Targets (2)       :
    - NodeId=e01-cn-xxx  Hostname=node-001
    - NodeId=e01-cn-yyy  Hostname=node-002
  IgnoreFailedNodeTasks : false (default)
  CLI               : aliyun eflo-controller stop-nodes \
                        --endpoint eflo-controller.cn-hangzhou.aliyuncs.com \
                        --region cn-hangzhou --nodes e01-cn-xxx e01-cn-yyy

⚠️ Impact: the node enters Stopped state and running jobs are interrupted; billing follows the "stopped" policy while stopped (see cluster billing docs).
   Restarting requires start-nodes from the console (out of scope for this skill).

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```

### Verification

`describe-node.OperatingState=Stopped`.

---

## D. Report Node Status (fault reporting, spawns deep diagnosis)

Applies to: hardware-class faults (GPU/HBM ECC, NIC port faults, disk bad blocks, fan/power/cable alarms) that require Alibaba Cloud offline hardware ops intervention. This is the general-user fault-reporting API (`ReportNodeStatus`) - it **replaces** the legacy PAI-only `report-nodes-status` (`--nodes` / `--reason` / `--issue-category` / `--start-time`), which must no longer be used.

### Parameter constraints

- `--node-id`: a single NodeId per call (not a list).
- `--diagnosis-type`: two reserved enums `QUICK` / `COMPREHENSIVE`, but only `COMPREHENSIVE` is accepted today (`QUICK` is reserved and rejected with 400 "Only COMPREHENSIVE diagnosis type is supported").
- `--description`: the user's own words, verbatim (`forbidden_inference`; LLM composing/splicing is forbidden).
- Preconditions: the node must be in `Using` state; daily quota (default 10% of account machines); duplicate account+node report is rejected.

### Phase 1 warning box

```
🛑 About to report node anomaly (mutating; the platform creates a fault report and spawns deep diagnosis):

  Action            : report-node-status
  Region            : cn-hangzhou
  NodeId            : e01-cn-xxx  Hostname=node-001  MachineType=efg1.nvga1
  DiagnosisType     : COMPREHENSIVE
  Description       : "GPU0 reported HBM ECC=128, NCCL hang at iter 3200"
  CLI               : aliyun eflo-controller report-node-status \
                        --endpoint eflo-controller.cn-hangzhou.aliyuncs.com --region cn-hangzhou \
                        --node-id e01-cn-xxx --diagnosis-type COMPREHENSIVE \
                        --description 'GPU0 reported HBM ECC=128, NCCL hang at iter 3200'

⚠️ Impact: the platform immediately creates a fault report (Status=Processing, visible via list-fault-reports); the node transitions to PreparationForDiagnosingClusterNode and deep diagnosis begins.

If everything checks out, reply "confirm" to submit; to modify parameters or abort, just let me know.
```

### Verification

CLI returns 2xx + `ReportId` (i-<12 digits>) + `RequestId` means the report succeeded; `list-fault-reports` shows the new report with `Status=Processing`. Subsequent deep-diagnosis progress is tracked via Feature 8 (fault-report-tracking).

---

## E. Escalate to Cluster-Scaling Skill (permanent removal, irreversible)

Applies to: the node is damaged beyond recovery and must be permanently removed from the cluster.

This skill does **not** execute permanent removal directly; instead it prompts the user to switch to the `alibabacloud-lingjun-cluster-scaling` skill to run `shrink-cluster` + `delete-node` / `delete-hyper-node`.

```text
👉 This fault is beyond the diagnosis/repair scope. Switch to the `alibabacloud-lingjun-cluster-scaling` skill to run:
   1. shrink-cluster to detach the node from the cluster
   2. delete-node / delete-hyper-node to release it permanently
   The flow requires the `CONFIRM REMOVE` strong confirmation word.
```
