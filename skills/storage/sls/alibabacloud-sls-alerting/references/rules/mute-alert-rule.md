# Temporarily mute or unmute an alert rule

Use [mute_alert.py](../../scripts/mute_alert.py) (Python 3.7+, standard library
only) to set `configuration.muteUntil` to an integer Unix timestamp in **seconds**.
Cancel a mute by removing the field; do not set it to `0`, `null`, or a past time.

Complete the skill prerequisites and resolve `SLS_ALERT_USER_AGENT` according to
the skill's Observability section. Set `SLS_SKILL_DIR` to the skill's absolute
root directory.

Optional `--region`, `--endpoint`, and `--profile` override the CLI's configured
defaults; see [region and endpoint routing](../regions.md).

Exit `0` indicates success, `1` an operation or verification failure, and `2`
invalid arguments.

## Mute

Determine `--mute-until` from the requested duration or end time as a future
Unix timestamp in seconds, and set `SLS_MUTE_UNTIL` to that value. Ask for missing
timing information; do not invent a duration.

```bash
python3 "$SLS_SKILL_DIR/scripts/mute_alert.py" \
  --project "$SLS_PROJECT" --alert-name "$SLS_ALERT_ID" \
  --mute-until "$SLS_MUTE_UNTIL" \
  --user-agent "$SLS_ALERT_USER_AGENT"
```

## Unmute

Cancel the mute with `--unmute`; no end time is needed.

```bash
python3 "$SLS_SKILL_DIR/scripts/mute_alert.py" \
  --project "$SLS_PROJECT" --alert-name "$SLS_ALERT_ID" \
  --unmute --user-agent "$SLS_ALERT_USER_AGENT"
```
