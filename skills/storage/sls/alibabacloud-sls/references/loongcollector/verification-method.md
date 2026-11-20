# Verification Method — per-step commands

Use the [shared observability setup](../../SKILL.md#observability) and append `--region <r>` to cloud-API commands. Execute each displayed `aliyun sls` line as its own direct tool call with literal values. Use a separate `--cli-dry-run` call before writes; if get/list proves exact target-state equality, record the skipped operation and call neither dry-run nor write. The `config.modify` and AgentSight exceptions in `workflow.md` §6 still apply.
Use the command exit code to determine success. On failure, preserve the available HTTP status, request ID, error code and error message, and follow the bounded recovery matrix in `references/loongcollector/workflow.md` §6. Never treat a failed command as successful verification.

## Preflight
```bash
aliyun configure list          # a valid profile exists (never prints AK/SK)
```

## U1 — config object
```bash
aliyun sls logtail-pipeline-config get --project <p> --logtail-pipeline-config <c> --region <r> --format json
# pass: object returned; inputs[] and flushers[] non-empty
```

## U2 — group binding (both directions must agree)
```bash
aliyun sls machine-group get-applied-configs --project <p> --machine-group <g> --region <r> --format json
aliyun sls logtail-pipeline-config get-applied-machine-groups --project <p> --logtail-pipeline-config <c> --region <r> --format json
# pass: config appears for the group AND group appears for the config
```

## U1 — config object (CRD path)
```bash
kubectl get clusteraliyunpipelineconfigs <c> -o yaml
# pass: kind ClusterAliyunPipelineConfig; spec.config.inputs and flushers non-empty
# after reconcile, optional: aliyun sls logtail-pipeline-config get --project <p> --logtail-pipeline-config <c>
```

## U3 — applied state
```bash
# API path: logtail-pipeline-config get succeeds and recent update readable.
# CRD path (opt-in only; default K8s collection is SLS API):
kubectl get clusteraliyunpipelineconfigs <c> -o yaml
# pass: status.success==true and lastAppliedConfig non-empty
```

## U4 — heartbeat & version
```bash
aliyun sls machine-group list-machines --project <p> --machine-group <g> --region <r> --format json
# pass: target machine present; lastHeartbeatTime recent; version readable (else Lens logtail_status.version)
```

## U5 — data arrival (business logstore, bounded polling 15s x <=4)
```bash
python3 -c 'import time; end=int(time.time()); print(end-120, end)' # separate local call
aliyun sls query --project <p> --logstore <l> --from <unix_from> --to <unix_to> \
  --query "* | select __time__ order by __time__ desc limit 5" --region <r> --format json
# pass: >=1 new row in window. If none and source produced no logs -> mark "not verifiable", stop.
# if meta.progress=Incomplete: record Incomplete and retry this identical literal command after 15s, up to 4 total attempts.
```

## U6 — field & index (never select *)
```bash
# index present:
aliyun sls index get --project <p> --logstore <l> --region <r> --format json
# fields queryable:
python3 -c 'import time; end=int(time.time()); print(end-120, end)' # separate local call
aliyun sls query --project <p> --logstore <l> --from <unix_from> --to <unix_to> \
  --query "* | select __time__, <field1>, <field2> limit 5" --region <r> --format json
# pass: key fields present with correct types (status_code numeric, etc.)
# apply the same 4-total-attempt Incomplete rule before using query rows.
# AgentSight / ebpf-event: * | select __time__, "event.name", "gen_ai.agent.type", "gen_ai.session.id" limit 5
# Pair request/response by gen_ai.turn.id / gen_ai.step.id; event.id is unique per line.
```

## Lens run-log check
```bash
python3 -c 'import time; end=int(time.time()); print(end-900, end)' # separate local call
aliyun sls query --project <lens_project> --logstore <lens_logstore> --from <unix_from> --to <unix_to> \
  --query "__topic__:logtail_alarm and project:<business_project> | select __time__,project,logstore,source_ip,alarm_type,alarm_message,version,config_name order by __time__ desc limit 50" \
  --region <lens_region> --format json
# check meta.progress. On Incomplete, record Incomplete and retry this byte-for-byte identical command after 15s, up to 4 total attempts; otherwise mark INCOMPLETE. Report Lens project/logstore/topic/window/version-route.
```

## Idempotent verification mapping
- `project create` → `project get`; compare exact name, region, and requested attributes.
- `logstore create` → `logstore get`; compare name, shard count, TTL, and mode.
- `index create` → `index get`; compare the full normalized `keys` and `line` objects.
- `machine-group create` → `machine-group get`; compare identify type and complete member list.
- `logtail-pipeline-config create` → `logtail-pipeline-config get`; compare the full normalized config.
- `logtail-pipeline-config apply-to-machine-group` → both commands in U2; both relation directions must agree.
- `kubectl apply -f <cr.yaml>` → `kubectl get clusteraliyunpipelineconfigs <c> -o yaml` (U1/U3) plus U2 cloud binding after reconcile.

Only exact target-state equality permits skipping dry-run/write, subject to the `config.modify` and AgentSight exceptions in `workflow.md` §6. Record skipped operations and the get/list verification used. An `AlreadyExist` response uses the same mapping outside those exceptions; report a differing object as an existing-resource conflict rather than implicitly updating it.

## Dry-run example (write safety)
```bash
aliyun sls logtail-pipeline-config create --project <p> --logtail-pipeline-config <c> \
  --inputs '[{"Type":"input_file","FilePaths":["/var/log/app/*.log"]}]' \
  --flushers '[{"Type":"flusher_sls","Logstore":"<l>"}]' \
  --cli-dry-run --region <r> --format json
# user authorization is required; inspect this dry-run, then re-run as a separate actual-write call.
```
