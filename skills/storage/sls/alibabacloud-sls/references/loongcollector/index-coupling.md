# Config / Index Coupling

## 1. Coordinated change sequence

When processors add, delete or rename a field, config and index changes should be
planned and applied together. Showing both changes as diffs is recommended.
Do not defer index planning until after the config is effective: this creates a
"config effective but field not selectable" loop.

Planning and execution should follow:
**snapshot config/index → render target config → validate target config → config diff
→ index diff → config dry-run → index dry-run → config write → index write → verification**.
Use `render_pipeline.py` and `validate_pipeline.py` for the Pipeline target.
`normalize_diff.py --kind config` and `--kind index` provide the two diffs.
The resource changes require user authorization. If either dry-run fails, execute
neither write. If one write succeeds and the other fails, record the partial result
and follow the error-recovery procedure in `workflow.md` §6.

Change-plan contents:
- Show both changes together, preferably as two diffs: `config_update_diff` + `index_update_diff` (whenever processors introduce/rename/remove fields).
- For `processor_rename`, remove every `SourceKeys` entry from the full index object and add the paired `DestKeys` entry. Do not retain stale source-field indexes; status destinations such as `http_status` default to `long`.
- New field must specify index type (text/long/double/json) and token suggestion.
- Verify with an explicit `select <new_field...>` (never `select *`) after ~1 minute.

## 2. Index update via aliyun sls

For a new full-text index, generate the [recommended token delimiters](../index/index-configuration.md#recommended-token-delimiters)
locally with `python3 scripts/index/tokens.py`, then place the generated array
literally in `line.token`. The example below uses three explicit delimiters.
For updates, preserve the existing `line.token` and other writable index settings
unless the requested change affects them.

```bash
# Snapshot the current index; merge changes into the complete writable configuration:
aliyun sls index get --project <p> --logstore <l> --region <r> --format json
aliyun sls index update --project <p> --logstore <l> \
  --keys '{"status_code":{"type":"long","doc_value":true},"request_time":{"type":"double","doc_value":true},"level":{"type":"text","token":[","," ",":"],"caseSensitive":false}}' \
  --line '{"token":[","," ",":"],"chn":true}' \
  --region <r> --format json
```
`--keys` is the field-index JSON; `--line` is the full-text index object.
`index update` replaces the configuration, so include all settings to retain.
Use `--from-file` with the complete writable object when preserving additional settings.

`--keys` payload contract:
- `token` belongs to `text` keys only and must be a JSON **array** of delimiter strings, e.g. `[",", " ", ":"]`. Passing the delimiters as one concatenated string (`" ,:"`) is rejected with `400 IndexInfoInvalid: field token is of error format`.
- `long` / `double` keys carry no `token`; use `doc_value: true` to keep them aggregatable.
- `--line '{"token":[","," ",":"],"chn":true}'` supplies the required token array and enables Chinese word segmentation. Preserve the existing delimiters and `chn` setting during unrelated updates.
- Send `--keys` as a single-quoted literal in one standalone command. Do not chain the call after another write with `&&`, and do not switch to `file://` or reshape the JSON after a failure — fix only the field the error names and re-issue the identical command.
When the user says `request_time float`, the approval diff must explicitly show that SLS stores this as index type `double`.

## 3. Field-type mapping (index_type)

| Field class | Index type | Token / note |
|---|---|---|
| time string (log_time) | text | `[" ","-",":","."]`; keep `__time__` for range queries |
| level | text | `[" ","-"]`, caseSensitive=false |
| pid/tid, line_number | long | integer; doc_value for aggregation |
| duration/latency/request_time with fractional values | double | SLS has no `float` index type; map user-facing float semantics to `double` |
| file_path | text | `["/","."]` |
| HTTP status (`status`,`status_code`,`http_status`,`http_status_code`) | long | default long for range/aggregation; text only if user explicitly wants string search |
| message | text | `[","," ","\t",":"]` |
| service/trace_id/labels | text | `[","," "]` |
| JSON nested | json | query with `json_extract_scalar(<f>,'$.<sub>')`; declare common subkeys |

## 4. Anti-patterns (block these)

- COUP-001: config-then-index serial deadlock (update config -> sleep -> fields null -> then index). Fix: emit index diff at plan time.
- COUP-002: index type mismatched with processor output (pid/line_number as text; log_time as long). Fix: use the table.
- COUP-003: using `select *` to verify new fields. Fix: explicit `select <field...>`.
- COUP-004: config-first, index-deferred ("add index later"). Fix: forbidden; config diff + index diff same batch (unless all fields already indexed).
- COUP-005: Prefix change not synced to index (e.g. `processor_json` Prefix `_`->`""` renames `_user_id`->`user_id` but index keeps old name). Fix: rename index keys with the Prefix change.
- COUP-006: HTTP status code built as text. Fix: use long per the table; text only on explicit string-search request.

## 5. Invalid config patterns (check before write)

- IC-001: `processor_parse_delimiter_native` with `Quote="\u0000"` on `<2.0` -> config fails to load. Fix: use a valid quote.
- IC-002: strict processor (`NoMatchError=true`/`NoKeyError=true`) collecting the collector's own logs -> self-collection recursion + `REGEX_UNMATCHED_ALARM` storm. Fix: safe defaults `NoMatchError=false`/`NoKeyError=false`/`FullMatch=false`; exclude the collector's own log paths.
- IC-003: `input_file` FilePaths too broad, overlapping other configs -> `MULTI_CONFIG_MATCH_ALARM`. Fix: Plan 1 `AllowingIncludedByMultiConfigs=true` on the current config; Plan 2 ask to retire old config; Plan 3 (only if user asks) change path.

Forbidden: FA-001 logging into the collector host/container/pod (SSH/kubectl exec/docker exec/scp) — not allowed at all.
