# Playbook: List -> Filter -> Act

Use when user needs to operate on a resource but only knows partial identity (for example by name or status).

## Steps

1. List candidate resources.
2. Identify target resource ID with user.
3. Fetch details if needed.
4. Execute action with safety gate (`--confirm` for mutations).
5. Verify result by read-back.

## Example

```bash
python scripts/flink_ververica_ops.py list_deployments -w w-xxx -n default -r cn-beijing -o table
python scripts/flink_ververica_ops.py get_deployment -w w-xxx -n default -r cn-beijing --deployment_id d-target -o json
python scripts/flink_ververica_ops.py start_job -w w-xxx -n default -r cn-beijing --deployment_id d-target --restore_strategy LATEST --confirm
```
