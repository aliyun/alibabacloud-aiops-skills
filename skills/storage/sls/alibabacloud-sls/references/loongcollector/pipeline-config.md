# Pipeline Config Model

Executed via `aliyun sls logtail-pipeline-config create/get/update/delete` (see `cli-contracts.yaml`). Plugin field details are authoritative in the runtime tool schema and official docs.

## 1. Pipeline config skeleton

A Logtail pipeline config defines "what to collect + how to parse + where to send".

```yaml
configName: "<config_name>"          # set via --logtail-pipeline-config; immutable after create
logSample: "<optional_sample_log>"   # --log-sample
global:                               # --global (JSON object)
  TopicType: "filepath|machine_group_topic|custom"
inputs:                               # --inputs (JSON list) — exactly 1 input
  - Type: "input_file|input_container_stdio|input_agentsight"
processors:                           # --processors (JSON list) — optional
  - Type: "processor_parse_json_native|processor_parse_regex_native|..."
aggregators: []                       # --aggregators; only with extended plugins, max 1
flushers:                             # --flushers (JSON list) — exactly 1 flusher_sls
  - Type: "flusher_sls"
    Logstore: "<target_logstore>"
```

Hard constraints:
- Exactly 1 input, exactly 1 `flusher_sls`.
- Reject any plugin `Type` outside the phase-one allowlist below; a matching `input_`/`processor_` prefix alone is not proof that a plugin exists.
- Native and extended plugins cannot be mixed in one config.
- The parse chain should follow: parse -> time -> reshape -> filter/desensitize.

## 2. Create example (aliyun sls)

```bash
aliyun sls logtail-pipeline-config create \
  --project <project> --logtail-pipeline-config <config> \
  --inputs '[{"Type":"input_file","FilePaths":["/var/log/app/*.log"]}]' \
  --processors '[{"Type":"processor_parse_json_native","SourceKey":"content","KeepingSourceWhenParseFail":true}]' \
  --flushers '[{"Type":"flusher_sls","Logstore":"<logstore>"}]' \
  --global '{"TopicType":"machine_group_topic"}' \
  --log-sample '{"level":"INFO","msg":"ok"}' \
  --region <r> --format json
```
Render and validate the target configuration, and obtain user authorization for the change. Showing changes as a diff is recommended. For verified create/apply no-ops, skip dry-run and write, subject to the config.modify and AgentSight exceptions in `workflow.md` §6. Otherwise run dry-run before the actual write. Coupled config/index changes should follow the sequence in `index-coupling.md`.

## 3. Get-then-Update (overwrite semantics)

`logtail-pipeline-config update` overwrites. Before updating:

1. `logtail-pipeline-config get --project <p> --logtail-pipeline-config <c>` and keep the full object as snapshot.
2. Apply the minimal field change on the full body (carry back unchanged inputs/processors/flushers/global).
3. Use `scripts/loongcollector/render_pipeline.py` to render the target. Carry the unchanged writable fields into the complete target and validate it with `scripts/loongcollector/validate_pipeline.py`. Showing the config changes as a diff is recommended; `normalize_diff.py --kind config` and `--kind index` provide diffs for coupled changes.
4. If processors add/rename/remove a field, the plan should include its corresponding index changes (`index-coupling.md`).

`create` and `update` accept a complete writable configuration through `--from-file`.
Pass `--project` and `--logtail-pipeline-config` on the command line. For an update
whose writable fields cannot be preserved by `--from-file`, use `--raw-body-file`
with the complete body. The render helper's JSON report contains the configuration
under `config`; extract that object before using it as a request file.

## 4. Version-before-plugin

Read the collector major version first (`machine-group list-machines` `.binary`; `plugin-version-gates.yaml`). `>=3.x` -> native plugins and full pipeline; `1.x/2.x` -> gated plugin set. If the version is unknown, ask the user for the collector version. Do not assume a plugin family and do not ask Lens.

## 5. Native-first plugin selection

- inputs: `input_file` (host / docker_file / k8s_file), `input_container_stdio` (docker_stdio / k8s_stdio), `input_agentsight` (host_agentsight / Agentloop; Linux host eBPF, kernel `>=5.10`, collector `>=3.3.9`). Empty `ProbeConfig` injects 9 cmdline + 7 HTTPS builtins. Agentloop fixed names: config `runtime-ebpf-agentsight-config`, Logstore `ebpf-event`.
- processors (native, preferred): `processor_parse_json_native`, `processor_parse_regex_native`, `processor_parse_delimiter_native`, `processor_parse_timestamp_native`, `processor_filter_regex_native`, `processor_desensitize_native`.
- extended (only when native cannot meet the need; state the trade-off; cannot mix with native): `processor_json`, `processor_grok`, `processor_rename`, `processor_spl` (SPL requires a dedicated validator; do not hand-write Script).
- Safe defaults for regex/strict processors: `NoMatchError=false`, `NoKeyError=false`, `FullMatch=false`, keep source on parse fail (`KeepingSourceWhenParseFail=true`) to avoid self-collection recursion (`index-coupling.md` COUP / invalid-config IC-002).

### 5.1 Rename a parsed JSON child field

`processor_rename` is extended, so it cannot follow `processor_parse_json_native`. Convert the complete processor chain to extended plugins:

```json
[
  {
    "Type": "processor_json",
    "SourceKey": "content",
    "Prefix": "",
    "NoKeyError": false,
    "KeepSource": false,
    "KeepSourceIfParseError": true,
    "UseSourceKeyAsPrefix": false
  },
  {
    "Type": "processor_rename",
    "SourceKeys": ["response_code"],
    "DestKeys": ["http_status"],
    "NoKeyError": false
  }
]
```

Hard checks:
- `SourceKeys` and `DestKeys` are plural string arrays, non-empty, and equal in length.
- `SourceKey`, `DestKey`, and `processor_rename_native` are invalid for field rename.
- `RenamedSourceKey` on `processor_parse_json_native` renames the retained source field only; it does not rename an extracted JSON child.
- The coupled index diff removes each source key and adds its paired destination key; `response_code -> http_status` therefore removes `response_code` and adds `http_status` as `long`.
- Run `scripts/loongcollector/validate_pipeline.py` on the full target config before diff/approval.

## 6. CRD management plane

- Write target: `ClusterAliyunPipelineConfig` (`telemetry.alibabacloud.com/v1alpha1`, cluster-scoped). Status: `success`, `message`, `lastUpdateTime`, `lastAppliedConfig`.
- K8s collection **defaults to** `aliyun sls logtail-pipeline-config create/update` + bind the official group.
- CRD is opt-in only when the user explicitly asks for GitOps/CR management, the kube-apiserver is reachable, RBAC permits `ClusterAliyunPipelineConfig` creation, and the controller is running.
- One config = one management plane. Double-write → STOP. Do not update via API a CR-owned config (controller will overwrite).
- Do not create `AliyunLogConfig` or `NamespaceAliyunPipelineConfig`.
