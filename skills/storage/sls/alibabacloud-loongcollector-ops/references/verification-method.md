# Verification Method — per-step commands

All cloud-API commands append `--region <r>` and `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/<session-id>`. Execute each displayed `aliyun sls` line as its own direct tool call with literal values. Use a separate `--cli-dry-run` call before writes; if get/list proves exact target-state equality, emit `Idempotent-Skip` and call neither dry-run nor write.
For `ParameterInvalid`, throttling, internal errors, or permission failures, preserve error code/requestID and follow the bounded recovery matrix in `SKILL.md` §6. Never treat an error response as successful verification.

## Preflight
```bash
aliyun version                 # >= 3.3.3
aliyun sls --help              # confirms aliyun-cli-sls plugin active
aliyun configure list          # a valid profile exists (never prints AK/SK)
```

## U1 — config object
```bash
aliyun sls get-logtail-pipeline-config --project <p> --config-name <c> --region <r> --user-agent <ua>
# pass: object returned; inputs[] and flushers[] non-empty
```

## U2 — group binding (both directions must agree)
```bash
aliyun sls get-applied-configs --project <p> --machine-group <g> --region <r> --user-agent <ua>
aliyun sls get-applied-machine-groups --project <p> --config-name <c> --region <r> --user-agent <ua>
# pass: config appears for the group AND group appears for the config
```

## U3 — applied state
```bash
# API path: get-logtail-pipeline-config succeeds and recent update readable.
# CRD path is detection-only and requires user-provided status evidence; this skill never runs kubectl.
```

## U4 — heartbeat & version
```bash
aliyun sls list-machines --project <p> --machine-group <g> --region <r> --user-agent <ua>
# pass: target machine present; lastHeartbeatTime recent; version readable (else Lens logtail_status.version)
```

## U5 — data arrival (business logstore, bounded polling 15s x <=4)
```bash
python3 -c 'import time; end=int(time.time()); print(end-120, end)' # separate local call
aliyun sls get-logs-v2 --project <p> --logstore <l> --from <unix_from> --to <unix_to> \
  --query "* | select __time__ order by __time__ desc limit 5" --region <r> --user-agent <ua>
# pass: >=1 new row in window. If none and source produced no logs -> mark "not verifiable", stop.
# if meta.progress=Incomplete: output [Query: Incomplete] attempt=<n>/4 and retry this identical literal command after 15s, up to 4 total attempts.
```

## U6 — field & index (never select *)
```bash
# index present:
aliyun sls get-index --project <p> --logstore <l> --region <r> --user-agent <ua>
# fields queryable:
python3 -c 'import time; end=int(time.time()); print(end-120, end)' # separate local call
aliyun sls get-logs-v2 --project <p> --logstore <l> --from <unix_from> --to <unix_to> \
  --query "* | select __time__, <field1>, <field2> limit 5" --region <r> --user-agent <ua>
# pass: key fields present with correct types (status_code numeric, etc.)
# apply the same 4-total-attempt Incomplete rule before using query rows.
# AgentSight / ebpf-event: * | select __time__, "event.name", "gen_ai.agent.type", "gen_ai.session.id" limit 5
# Pair request/response by gen_ai.turn.id / gen_ai.step.id; event.id is unique per line.
```

## Lens run-log check
```bash
python3 -c 'import time; end=int(time.time()); print(end-900, end)' # separate local call
aliyun sls get-logs-v2 --project <lens_project> --logstore <lens_logstore> --from <unix_from> --to <unix_to> \
  --query "__topic__:logtail_alarm and project:<business_project> | select __time__,project,logstore,source_ip,alarm_type,alarm_message,version,config_name order by __time__ desc limit 50" \
  --region <lens_region> --user-agent <ua>
# check meta.progress. On Incomplete, output [Query: Incomplete] attempt=<n>/4 and retry this byte-for-byte identical command after 15s, up to 4 total attempts; otherwise mark INCOMPLETE. Report Lens project/logstore/topic/window/version-route.
```

## Idempotent verification mapping
- `create-project` → `get-project`; compare exact name, region, and requested attributes.
- `create-log-store` → `get-log-store`; compare name, shard count, TTL, and mode.
- `create-index` → `get-index`; compare the full normalized `keys` and `line` objects.
- `create-machine-group` → `get-machine-group`; compare identify type and complete member list.
- `create-logtail-pipeline-config` → `get-logtail-pipeline-config`; compare the full normalized config.
- `apply-config-to-machine-group` → both commands in U2; both relation directions must agree.

Only exact target-state equality permits skipping dry-run/write. Record every no-op in final `Changes` with the exact `[Idempotent-Skip]` sentence. An `AlreadyExist` response uses the same mapping; a differing object is `[BLOCKED: EXISTING_RESOURCE_CONFLICT]`, not an implicit update.

## Dry-run example (write safety)
```bash
aliyun sls create-logtail-pipeline-config --project <p> --config-name <c> \
  --inputs '[{"Type":"input_file","FilePaths":["/var/log/app/*.log"]}]' \
  --flushers '[{"Type":"flusher_sls","Logstore":"<l>"}]' \
  --cli-dry-run --region <r> --user-agent <ua>
# approval must already be explicit; inspect this dry-run, then re-run as a separate actual-write call.
```
