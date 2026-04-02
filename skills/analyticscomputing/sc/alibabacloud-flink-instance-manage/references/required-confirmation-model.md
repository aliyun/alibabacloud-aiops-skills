# Required confirmation model

Use a hard confirmation gate for every mutating operation. Missing confirmation
flags is a policy violation, not a recoverable runtime detail.

## 2.1 Pre-execution hard gate (mandatory)

Before executing any write command:

1. Build the full command string first.
2. Validate the required confirmation flag is present.
3. If the flag is missing, **do not execute**. Rebuild the command with the
   correct flag, then execute once.
4. Never bypass this check, even if a previous step failed.

## 2.2 Command-to-flag mapping

- `create`, `renew`: `--confirm`
- `modify_spec`, `convert`: `--confirm_price`
- `delete`: `--force_confirmation`
- `create_namespace`, `delete_namespace`, `modify_namespace_spec`: `--confirm`
- `tag_resources`, `untag_resources`: `--confirm`

If uncertain about a command's required flags, run:

```bash
python scripts/instance_ops.py <command> --help
```
