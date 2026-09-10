# Verify a rule change

## Validate the configuration

Before creating or updating a rule, run the [validator](../../scripts/validate_alert.py)
on the complete CLI-oriented document. Set `SLS_SKILL_DIR` to the absolute
directory containing this skill's `SKILL.md`:

```bash
python3 "$SLS_SKILL_DIR/scripts/validate_alert.py" --json "$SLS_ALERT_FILE"
```

Exit `0` means local checks passed; `1` means invalid input and `2` means CLI
usage error. Review warnings; unknown fields are retained. The script checks
structure and known CLI incompatibilities. Validate SQL and result fields in
[query validation](queries/verify-alert-query.md#validate-a-new-or-changed-query), and trigger
expressions in [trigger conditions](triggering/trigger-conditions.md). Local validation
does not establish service acceptance or delivery.
