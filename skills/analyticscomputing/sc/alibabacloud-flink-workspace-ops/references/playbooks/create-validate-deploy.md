# Playbook: Create -> Validate -> Deploy

Use when user asks for end-to-end SQL delivery from draft creation to deployment.

## Steps

1. Create draft (`create_draft`).
2. Validate SQL syntax (`validate_sql`) or deep validate draft (`validate_draft`).
3. Deploy draft (`deploy_draft`) with explicit approval and `--confirm`.
4. If async command is used, poll result command until terminal state.
5. Verify deployment state with read-back.

## Example

```bash
python scripts/flink_ververica_ops.py create_draft -w w-xxx -n default -r cn-beijing --name my-job --content "SELECT * FROM source" --confirm
python scripts/flink_ververica_ops.py validate_sql -w w-xxx -n default -r cn-beijing --statement "SELECT * FROM source"
python scripts/flink_ververica_ops.py deploy_draft -w w-xxx -n default -r cn-beijing --draft_id <draft_id_from_create_or_list> --confirm
```
