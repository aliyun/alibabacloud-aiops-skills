# Pipeline Config Model

> Source: `loongcollector-oncall/knowledge/base/collection-config/config-model.md`, `input-plugins.md`, `processor-plugins.md`. Executed via `aliyun sls create/get/update/delete-logtail-pipeline-config` (see `cli-contracts.yaml`). Plugin field details are authoritative in the runtime tool schema and official docs.

## 1. Pipeline config skeleton

A Logtail pipeline config defines "what to collect + how to parse + where to send".

```yaml
configName: "<config_name>"          # set via --config-name; immutable after create
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
- Parse chain order: parse -> time -> reshape -> filter/desensitize.

## 2. Create example (aliyun sls)

```bash
aliyun sls create-logtail-pipeline-config \
  --project <project> --config-name <config> \
  --inputs '[{"Type":"input_file","FilePaths":["/var/log/app/*.log"]}]' \
  --processors '[{"Type":"processor_parse_json_native","SourceKey":"content","KeepingSourceWhenParseFail":true}]' \
  --flushers '[{"Type":"flusher_sls","Logstore":"<logstore>"}]' \
  --global '{"TopicType":"machine_group_topic"}' \
  --log-sample '{"level":"INFO","msg":"ok"}' \
  --region <r> --user-agent AlibabaCloud-Agent-Skills/alibabacloud-loongcollector-ops/<session-id>
```
Render/validate and obtain explicit approval first. If Get-before-Create proves exact equality, emit the required `Idempotent-Skip` and run neither dry-run nor write. Otherwise, Execute uses separate direct dry-run and actual-write calls. For coupled config/index changes, run both dry-runs first and then both actual writes back-to-back as specified in `index-coupling.md`.

## 3. Get-then-Update (overwrite semantics)

`update-logtail-pipeline-config` overwrites. Before updating:
1. `get-logtail-pipeline-config --project <p> --config-name <c>` and keep the full object as snapshot.
2. Apply the minimal field change on the full body (carry back unchanged inputs/processors/flushers/global).
3. Render the full target (`scripts/render_pipeline.py` is the preferred helper but optional), MUST validate it with `scripts/validate_pipeline.py`, and MUST run `scripts/normalize_diff.py` for the config diff (plus a separate index invocation when coupled).
4. If processors add/rename/remove a field, produce the index diff in the SAME batch (`index-coupling.md`).

## 4. Version-before-plugin

Read the collector major version first (`sls-lens-contracts.md` version discovery; `plugin-version-gates.yaml`). `>=3.x` -> native plugins and full pipeline; `1.x/2.x` -> gated plugin set. Do not generate a config before confirming version when a version-gated plugin is involved.

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
- Run `scripts/validate_pipeline.py` on the full target config before diff/approval.

## 6. CRD awareness (detection only)

- The K8s management plane uses `ClusterAliyunPipelineConfig` (`telemetry.alibabacloud.com/v1alpha1`, cluster-scoped). Its status carries `success`, `message`, `lastUpdateTime`, `lastAppliedConfig`.
- One config = one management plane. If a config appears managed by both API and CRD (double-write), STOP and report; do not silently update via API a config owned by a CRD (the controller will re-sync and overwrite).
- CRD create/update execution is out of scope. Only detect ownership and read CRD status when the user provides cluster access context (read-only).
