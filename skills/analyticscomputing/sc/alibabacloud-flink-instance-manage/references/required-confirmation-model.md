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
