# Config / Index Coupling (hard rule)

> Source: `loongcollector-oncall/knowledge/base/collection-config/field-naming-and-index.md`, `invalid-config-patterns.md`.

## 1. Same-batch rule

When processors add, delete, or rename a field, the **config update diff and the index update diff must be shown in the same user approval and applied in the same batch**. Never "update config now, add index later" — that creates a "config effective but field not selectable" loop.
Plan order is fixed: snapshot config/index → validate target config → normalize config diff with `--kind config` → normalize index diff with `--kind index`. After approval, execute `config dry-run → index dry-run → config write → index write`; the two actual writes are back-to-back with no intervening operation. If either dry-run fails, execute neither write.

Output contract:
- Emit two diffs together: `config_update_diff` + `index_update_diff` (whenever processors introduce/rename/remove fields).
- For `processor_rename`, remove every `SourceKeys` entry from the full index object and add the paired `DestKeys` entry. Do not retain stale source-field indexes; status destinations such as `http_status` default to `long`.
- New field must specify index type (text/long/double/json) and token suggestion.
- Verify with an explicit `select <new_field...>` (never `select *`) after ~1 minute.

## 2. Index update via aliyun sls

```bash
# get current index (snapshot), merge new keys, then overwrite:
aliyun sls get-index --project <p> --logstore <l> --region <r> --user-agent <ua>
aliyun sls update-index --project <p> --logstore <l> \
  --keys '{"status_code":{"type":"long","doc_value":true},"request_time":{"type":"double","doc_value":true},"level":{"type":"text","token":[","," ",":"],"caseSensitive":false}}' \
  --region <r> --user-agent <ua>
```
`--keys` is the field-index JSON; `--line` is the full-text index object. `update-index` overwrites — merge new keys with existing before writing.

`--keys` payload contract:
- `token` belongs to `text` keys only and must be a JSON **array** of delimiter strings, e.g. `[",", " ", ":"]`. Passing the delimiters as one concatenated string (`" ,:"`) is rejected with `400 IndexInfoInvalid: field token is of error format`.
- `long` / `double` keys carry no `token`; use `doc_value: true` to keep them aggregatable.
- `--line '{"chn": true}'` enables Chinese word segmentation for the full-text index; keep it whenever the existing index has it.
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
