# Command Quick Reference

Quick reference guide for essential Lingjun cluster management commands.

> **⚠️ Region Required (MANDATORY)** ｜ Every `aliyun eflo-controller` command example in this file **must** explicitly carry `--region <region>` (`<region>` given explicitly by the user via HITL; defaulting / reusing / persisting via environment variable is **strictly forbidden**). The endpoint is auto-derived by the aliyun CLI from `--region`; an explicit `--endpoint` is **neither needed nor desired** (see [SKILL.md §B-6 Region Required](../SKILL.md)). This rule does **not** apply to `aliyun bssopenapi` and `aliyun ecs` commands.

> **⚠️ Transient Failure Retry (MANDATORY)** ｜ All `aliyun ...` in this file's bash blocks are uniformly wrapped as `safe_aliyun aliyun ...`, matching the [SKILL.md → Transient Failure Retry (MANDATORY)](../SKILL.md) hard rule. Before running scripts you **must** first `source` the definition of `safe_aliyun` (implementation skeleton in [edge-cases.md → Appendix B.4](./edge-cases.md): `retry_with_jitter` + `retry_on_throttle` + retry blacklist). A bare `aliyun ...` call is treated as a hard-rule violation.

## Core Operations

### List All Clusters

```bash
safe_aliyun aliyun eflo-controller list-clusters \
  --region <region-id>
```

### Describe Cluster

```bash
safe_aliyun aliyun eflo-controller describe-cluster \
  --region <region-id> \
  --cluster-id <cluster-id>
```

### Extend Cluster (Add Nodes)

```bash
safe_aliyun aliyun eflo-controller extend-cluster \
  --region <region-id> \
  --cluster-id <cluster-id> \
  --node-groups '<json-array>'
```

### Shrink Cluster (Remove Nodes)

```bash
safe_aliyun aliyun eflo-controller shrink-cluster \
  --region <region-id> \
  --cluster-id <cluster-id> \
  --node-groups '<json-array>'
```

### List Cluster Nodes

```bash
safe_aliyun aliyun eflo-controller list-cluster-nodes \
  --region <region-id> \
  --cluster-id <cluster-id>
```

### Describe Task

```bash
safe_aliyun aliyun eflo-controller describe-task \
  --region <region-id> \
  --task-id <task-id>
```

### List Free Nodes

```bash
safe_aliyun aliyun eflo-controller list-free-nodes \
  --region <region-id>
```

### Describe Regions

```bash
safe_aliyun aliyun eflo-controller describe-regions
```

## Common Patterns

### Find Cluster by Name

```bash
safe_aliyun aliyun eflo-controller list-clusters \
  --region cn-wulanchabu \
  --cli-query "Clusters[?ClusterName=='<cluster-name>'].ClusterId | [0]"
```

### Monitor Task Until Complete

```bash
while true; do
  STATUS=$(safe_aliyun aliyun eflo-controller describe-task \
    --region cn-wulanchabu \
    --task-id <task-id>)
  STATE=$(echo "$STATUS" | jq -r '.TaskState')
  echo "State: $STATE"
  [ "$STATE" = "Success" ] || [ "$STATE" = "Failed" ] && break
  sleep 30
done
```

### Get Running Nodes Only

```bash
safe_aliyun aliyun eflo-controller list-cluster-nodes \
  --region cn-wulanchabu \
  --cluster-id <cluster-id> \
  --cli-query "Nodes[?OperatingState=='Running']"
```

## JSON Templates

### Extend Cluster Node Groups

```json
[
  {
    "NodeGroupId": "ng-xxxxx",
    "Nodes": [
      {
        "NodeId": "e01-cn-xxxxx",
        "Hostname": "node-001",
        "LoginPassword": "YourPassword123!"
      }
    ]
  }
]
```

### Shrink Cluster Node Groups

```json
[
  {
    "NodeGroupId": "ng-xxxxx",
    "Nodes": [
      {"NodeId": "e01-cn-xxxxx"}
    ]
  }
]
```

### Delete Node Group (empty group only, irreversible)

```bash
# Precondition: list-node-groups ground truth confirms the group's NodeCount == 0, and HITL "confirm" has been received
# See workflows/delete-node-group/schema.yaml
safe_aliyun aliyun eflo-controller delete-node-group \
  --region <region-id> \
  --cluster-id <cluster-id> \
  --node-group-id <node-group-id>
```

⚠ Missing `--cluster-id` → 403 InvalidAccount.PermissionDenied; group does not exist / not in this cluster → 400 The group [xxx] does not exist.
