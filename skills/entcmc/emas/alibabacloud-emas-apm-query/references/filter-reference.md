# `--filter` structure and usage

All 4 APIs (`get-issues` / `get-issue` / `get-errors` / `get-error`) accept an optional `--filter` argument to narrow results on the server side. Semantics match the console's "filter conditions"; see candidate fields in `assets/system-filters/*.json`.

## Wire format: a single JSON string

Verified via `--cli-dry-run`, the **only** way for the CLI to produce a proper `Filter=<string>` is to pass **the whole JSON string as the value of `--filter`**:

```bash
aliyun emas-appmonitor get-issues \
  --app-key 335695934 --os iphoneos --biz-module crash \
  --time-range StartTime=$START EndTime=$END Granularity=1 GranularityUnit=DAY \
  --filter '{"Key":"appVersion","Operator":"in","Values":["3.5.0","3.5.1"]}'
```

In the dry-run output `Body.Filter` must be a **string literal** (notice the outer quotes):

```json
{
  "AppKey": 335695934,
  "Os": "iphoneos",
  "BizModule": "crash",
  "TimeRange": { "...": "..." },
  "Filter": "{\"Key\":\"appVersion\",\"Operator\":\"in\",\"Values\":[\"3.5.0\",\"3.5.1\"]}"
}
```

### Why not the flat `Key=... Operator=... Values.1=...` form

`--filter` is declared as `style: "json"` (not `"flat"`) in the `.cspec`. Attempting the flat form (e.g. `--filter Key=appVersion Operator=in Values.1=1.0.0`) does **not** get serialized into a top-level `Filter` field in the dry-run; it is split into odd query-string fragments and the server returns `InvalidRequest`.

## Filter object structure

```jsonc
{
  "Key": "appVersion",         // required, filter_code (from assets/system-filters)
  "Operator": "in",            // required, operator enum (see below)
  "Values": ["1.0.0"],         // used for leaf conditions; required on leaves
  "SubFilters": []             // used for composite nodes; exclusive with Values
}
```

### Complete operator set

| Operator | Meaning | Used on | Typical values |
| --- | --- | --- | --- |
| `=` / `!=` | equal / not equal | `Key` is a single-value field | `Values:["3.5.0"]` |
| `in` / `not in` | in set / not in set | `Key` is an enum / string field | `Values:["3.5.0","3.5.1"]` |
| `>` / `<` / `>=` / `<=` | numeric comparison | `Key` is numeric (e.g. `lagCost`) | `Values:["200"]` (numbers as strings; backend coerces) |
| `and` | logical AND | composite node, `SubFilters` non-empty | `Values` empty |
| `or` | logical OR | composite node, `SubFilters` non-empty | `Values` empty |
| `not` | logical NOT | usually with one nested level | `Values` empty |

### Leaf vs composite

- **Leaf node**: has `Key` + `Operator` + `Values`, no `SubFilters` (or empty array).
- **Composite node**: `Operator` is `and` / `or` / `not`; `SubFilters` is an **array consisting of leaves or further composite nodes**.
- **`SubFilters` element type**: OpenAPI declares `SubFilters` as `array<string>`, meaning **each child filter must first be `JSON.stringify`-ed to a string** and then placed in the array.

### Composite example: APP version in [3.5.0, 3.5.1] AND brand = Apple

```bash
# Stringify each leaf first
SUB1='{"Key":"appVersion","Operator":"in","Values":["3.5.0","3.5.1"]}'
SUB2='{"Key":"brand","Operator":"=","Values":["Apple"]}'

# Then assemble the AND node; each element of SubFilters is a JSON string (another layer of escaping)
FILTER=$(jq -cn --arg s1 "$SUB1" --arg s2 "$SUB2" \
  '{Key:"",Operator:"and",Values:[],SubFilters:[$s1,$s2]}')

aliyun emas-appmonitor get-issues \
  --app-key 335695934 --os iphoneos --biz-module crash \
  --time-range StartTime=$START EndTime=$END Granularity=1 GranularityUnit=DAY \
  --filter "$FILTER"
```

In the dry-run `Body.Filter` should look like:

```json
"Filter": "{\"Key\":\"\",\"Operator\":\"and\",\"Values\":[],\"SubFilters\":[\"{\\\"Key\\\":\\\"appVersion\\\",\\\"Operator\\\":\\\"in\\\",\\\"Values\\\":[\\\"3.5.0\\\",\\\"3.5.1\\\"]}\",\"{\\\"Key\\\":\\\"brand\\\",\\\"Operator\\\":\\\"=\\\",\\\"Values\\\":[\\\"Apple\\\"]}\"]}"
```

(Three levels of escaping; constructing with `jq` is far more reliable than writing the double backslashes by hand.)

## Commonly used filter snippets (copy-paste)

```bash
# 1. A specific APP version
--filter '{"Key":"appVersion","Operator":"=","Values":["3.5.0"]}'

# 2. Multiple versions (in is cleaner than OR)
--filter '{"Key":"appVersion","Operator":"in","Values":["3.5.0","3.5.1","3.5.2"]}'

# 3. Exclude a version
--filter '{"Key":"appVersion","Operator":"not in","Values":["3.5.0-beta"]}'

# 4. Specific device models only
--filter '{"Key":"deviceModel","Operator":"in","Values":["iPhone14,5","iPhone14,2"]}'

# 5. Specific OS versions only
--filter '{"Key":"osVersion","Operator":"in","Values":["17.0","17.1","17.2"]}'

# 6. Specific brand only
--filter '{"Key":"brand","Operator":"=","Values":["Apple"]}'

# 7. lag: lag duration >= 500 ms
--filter '{"Key":"lagCost","Operator":">=","Values":["500"]}'

# 8. memory_leak: is OOM
--filter '{"Key":"isOom","Operator":"=","Values":["1"]}'
```

## Source of `filter_code` values

All legal `Key` values are listed in `filters[*].filterCode` of `assets/system-filters/<biz_module>-<platform>.json`. Each record also carries:

| Field | Purpose |
| --- | --- |
| `filterName` | Display name in the console (e.g. "App Version" in Chinese on the console) |
| `filterType` | `checkbox` / `radio` / `text` / `select`; determines the shape of `Values` |
| `dynamic` | `true` means candidate values are produced dynamically after integration (e.g. `appVersion` / `deviceModel` emitted by the app); `false` means a static enum |
| `filterValues` | Candidate values for static enums. **Usually empty when `dynamic=true`**; the user must supply real values (e.g. from the console or the app release notes) |

For `dynamic=true` fields, the Skill consumer must provide the values. The Skill does NOT "pull dynamic candidates at runtime"; it only ships **the static enum + filter_code list**.

## Differences across biz_modules

The same `filterCode` may have different semantics under different `biz_module`s:

- `isOom` under `crash` = whether the crash is OOM; under `memory_leak` = whether the leak reached the OOM threshold.
- `errorCode` under `custom` is a string reported by the business; other modules do not have this field.
- `lag` has its own `lagCost` and `lagType` (lag type: `UI` / `IO` / `Network`).
- `memory_alloc` has its own `allocSizeBucket`.

When unsure which `filterCode`s the current `biz_module` supports, read the corresponding `assets/system-filters/<biz_module>-<platform>.json` directly.

## 3 steps to verify that a filter takes effect

1. Call `get-issues` / `get-errors` **without** the filter once; record `Model.Total`.
2. Call it **with** the filter (keeping all other parameters identical); the new `Model.Total` should be **significantly smaller** than step 1, otherwise the filter probably did not take effect.
3. Use `--cli-dry-run` together with `--log-level debug` to confirm the `"Filter"` field in the HTTP body is the expected JSON string with the correct number of escape layers.

## Common pitfalls

- **Use `"` inside the JSON string, not `'`**: wrap the whole JSON with single quotes in bash; keys/values use double quotes.
- **Nested `SubFilters` need multiple escape layers**: error-prone by hand; always build with `jq -cn`.
- **Numbers in `Values` must be strings**: `Values:["200"]`, not `Values:[200]`; the backend coerces; some CLI versions raise parse errors on the reverse form.
- **Empty filter = no filter**: if `Key=""` and `SubFilters=[]`, the backend treats the filter as invalid and ignores it (equivalent to not passing `--filter`).
- **The CLI does NOT validate values when `dynamic=true`**: an incorrect `appVersion` string matches nothing and returns `Total=0`, without any error.
