# Playbook: Session Cluster Lifecycle

Use when user requests create/start/stop/delete operations for a Session cluster.

## Steps

1. Create or identify target session cluster.
2. Resolve `cluster_id` from create response or `list_session_clusters`.
3. Start cluster if needed for workload.
4. Stop cluster when workload ends.
5. Delete cluster only with explicit delete confirmation.
6. Verify each mutation using `get_session_cluster` or `list_session_clusters`.

## Example

```bash
python scripts/flink_ververica_ops.py create_session_cluster -w w-xxx -n default -r cn-beijing --name my-cluster --confirm
python scripts/flink_ververica_ops.py start_session_cluster -w w-xxx -n default -r cn-beijing --cluster_id <cluster_id> --confirm
python scripts/flink_ververica_ops.py stop_session_cluster -w w-xxx -n default -r cn-beijing --cluster_id <cluster_id> --confirm
python scripts/flink_ververica_ops.py delete_session_cluster -w w-xxx -n default -r cn-beijing --cluster_id <cluster_id> --confirm
```
