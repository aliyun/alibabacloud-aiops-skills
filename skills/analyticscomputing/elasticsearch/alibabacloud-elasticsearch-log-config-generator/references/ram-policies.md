# RAM Permission Policy

This file declares the Alibaba Cloud RAM permissions required by this skill.

## required_permissions

- `elasticsearch:CreateOfflineTask` - Create an offline log ingestion task.
- `elasticsearch:GetOfflineTask` - Query an offline log ingestion task.
- `elasticsearch:GetOfflineTaskLog` - Query logs for an offline log ingestion task.

## Audit Notes

- Do not add wildcard permissions such as `elasticsearch:*`.
- Do not place multiple actions on one line.
- Do not add write or delete permissions unless a future workflow explicitly requires them and documents the reason.
