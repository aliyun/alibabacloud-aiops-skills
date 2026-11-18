# Required confirmation model

Use a hard confirmation gate for every create operation. Missing confirmation
flags is a policy violation.

## 1) Pre-execution hard gate (mandatory)

Before executing any create command:

1. Build the full command string first.
2. Validate the required confirmation flag is present.
3. If the flag is missing, do not execute. Rebuild the command with the correct flag.
4. Never bypass this check, even if a previous step failed.
5. Keep confirmation evidence in logs/output (`SafetyCheckRequired` or `--confirm`).

## 2) Command-to-flag mapping

- `create`: `--confirm`
- `create_namespace`: `--confirm`

Query commands do not require confirmation flags.

## 3) AI service writes

Present the exact plan and wait for explicit human approval before passing `--confirm` to `open_flink_ai_service`, `close_flink_ai_service`, or `modify_ai_service_protection`. Each approval covers one write to the stated account and region. Include the requested `--deletion_protection` value for either direction of a protection change. [AI service write authorization](../SKILL.md#ai-service-write-authorization)
