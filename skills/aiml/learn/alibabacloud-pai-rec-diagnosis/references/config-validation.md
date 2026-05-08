# PAI-Rec Engine Configuration Validation

Reference for `scripts/validate.py` — the JSON Schema + rule-based validator used by
Workflow 2 (Engine Configuration Validation) in `SKILL.md`.

---

## 1. Files

| Path | Purpose |
|------|---------|
| `scripts/validate.py` | Validator entry point (CLI + library). |
| `references/schema.json` | JSON Schema (Draft-7) describing the top-level engine-config structure. |

Both files live inside this skill — no external skill dependency.

---

## 2. Dependencies

- Python 3.8+
- `jsonschema` (optional but recommended):
  ```bash
  pip install jsonschema
  ```
  If `jsonschema` is not installed the script **still runs** but skips Schema checks
  and relies on the built-in rule validator only. A single warning-equivalent note
  is NOT emitted in this case, so install `jsonschema` for full coverage.

---

## 3. CLI Usage

```bash
# From a saved JSON file
python3 scripts/validate.py /tmp/engine-config.json

# Inline JSON string
python3 scripts/validate.py '{"RunMode":"product","RecallConfs":[...]}'

# From stdin (recommended when ConfigValue is already in a shell variable)
printf '%s' "$CONFIG_VALUE" | python3 scripts/validate.py --stdin
```

### Exit codes

| Code | Meaning |
|------|---------|
| `0`  | Validation passed (no errors; warnings may still be printed). |
| `1`  | Validation failed (at least one `error`-severity finding). |
| `2`  | Input error — argument is not a readable file, not valid JSON, or stdin decode failed. |

### Output format

```
Validation finished: <E> error(s), <W> warning(s)

  [ERROR]   <json.path>: <message>
  [WARNING] <json.path>: <message>
  ...
```

`<json.path>` uses dotted / bracketed notation, e.g.
`RecallConfs[3]`, `SceneConfs.default.default.RecallNames[1]`,
`FilterConfs[0].DaoConf`.

### Fragment auto-wrapping

If the input is a single fragment (object containing `RecallType`, `FilterType`, or
`SortType` at the top level) and the corresponding `*Confs` array is missing, the
script automatically wraps it into `{ "<Conf>s": [ <fragment> ] }` before
validation. This lets you validate one recall / filter / sort entry in isolation.

---

## 4. Library Usage

```python
from scripts.validate import validate_config, ValidationError

errors: list[ValidationError] = validate_config(config_dict, use_schema=True)
for e in errors:
    print(e.severity, e.path, e.message)
```

`ValidationError` fields: `path`, `message`, `severity` (`"error"` | `"warning"`).

---

## 5. Rule Catalogue

### 5.1 Structural / Type checks (JSON Schema)

Enforced by `references/schema.json` via `jsonschema.Draft7Validator`. Covers:

- Top-level keys: `RunMode`, `ListenConf`, `RecallConfs`, `FilterConfs`,
  `SortConfs`, `AlgoConfs`, `SceneConfs`, `FilterNames`, `SortNames`, `RankConf`,
  `GeneralRankConfs`, `FeatureConfs`, `UserFeatureConfs`, `DebugConfs`,
  `FeatureLogConfs`, `CallBackConfs`, `PipelineConfs`, `HologresConfs`,
  `RedisConfs`, `MysqlConfs`, `TableStoreConfs`, `FeatureStoreConfs`,
  `ClickHouseConfs`, `GraphConfs`, `LindormConfs`, `RecallEngineConfs`, …
- Required fields and primitive types for every nested object.
- Enumerations for `AdapterType`, operation modes, etc. where representable in
  JSON Schema.

### 5.2 Enum validation (rule-based)

| Field | Allowed values |
|-------|----------------|
| `RunMode` | `daily`, `prepub`, `product` |
| `RecallConfs[*].RecallType` | `UserCollaborativeFilterRecall`, `UserTopicRecall`, `VectorRecall`, `UserCustomRecall`, `HologresVectorRecall`, `ItemCollaborativeFilterRecall`, `UserGroupHotRecall`, `UserGlobalHotRecall`, `I2IVectorRecall`, `ColdStartRecall`, `MilvusVectorRecall`, `RealTimeU2IRecall`, `OnlineHologresVectorRecall`, `OnlineVectorRecall`, `GraphRecall`, `MockRecall`, `RecallEngineRecall` |
| `FilterConfs[*].FilterType` | `User2ItemExposureFilter`, `User2ItemCustomFilter`, `AdjustCountFilter`, `PriorityAdjustCountFilter`, `PriorityAdjustCountFilterV2`, `ItemStateFilter`, `ItemCustomFilter`, `CompletelyFairFilter`, `GroupWeightCountFilter`, `DimensionFieldUniqueFilter`, `User2ItemExposureWithConditionFilter`, `ConditionFilter`, `DiversityAdjustCountFilter`, `SnakeFilter`, `UniqueFilter` |
| `SortConfs[*].SortType` | `ItemRankScore`, `BoostScoreSort`, `BoostScoreByWeight`, `DiversityRuleSort`, `DPPSort`, `SSDSort`, `AlgoScoreSort`, `TrafficControlSort`, `MultiRecallMixSort`, `DistinctIdSort`, `CustomFieldSort`, `ConditionSort` |
| `AlgoConfs[*].EasConf.ResponseFuncName` | Must match one of the response funcs registered in `pairec/algorithm/eas/client.go` `SetResponseFunc()`: `pssmartResponseFunc`, `tfResponseFunc`, `alinkFMResponseFunc`, `tfMutValResponseFunc`, `easyrecResponseFunc`, `easyrecResponseFuncDebug`, `easyrecMutValResponseFunc`, `easyrecMutValResponseFuncDebug`, `easyrecMutClassificationResponseFunc`, `easyrecMutClassificationResponseFuncDebug`, `easyrecUserEmbResponseFunc`, `easyrecUserRealtimeEmbeddingResponseFunc`, `easyrecUserRealtimeEmbeddingMindResponseFunc`, `tfServingResponseFunc`, `torchrecMutValResponseFunc`, `torchrecMutValResponseFuncDebug`, `torchrecEmbeddingResponseFunc`, `torchrecEmbeddingItemsResponseFunc`, `torchrecEmbeddingItemsResponseFuncDebug`, `tfUseEmbResponseFunc`, `torchrecMutClassificationResponseFunc`, `torchrecMutClassificationResponseFuncDebug` |
| `DebugConfs.OutputType` | Validated; `Rate` must be an integer in `[0, 100]`. |
| `GeneralRankConfs.*.ActionConfs[*].ActionType` | Validated against supported action types. |

### 5.2a Built-in recall instance names

`SceneConfs.<scene>.<category>.RecallNames[]` may reference the following
built-in recall instances that are implemented inside the engine and do NOT
need to appear in `RecallConfs`:

| Name | Source |
|------|--------|
| `ContextItemRecall` | Engine built-in — reads item list from the request context. |

### 5.2b Built-in sort (rerank) instance names

`SceneConfs.<scene>.<category>.SortNames[]` (and the top-level `SortNames[]`)
may reference the following built-in sort instances that are implemented
inside the engine and do NOT need to appear in `SortConfs`. The validator
treats these names as pre-defined and will not emit an "undefined sort name"
error when they are referenced:

| Name | Source |
|------|--------|
| `ItemRankScore` | Engine built-in rerank module — sorts items in descending order by the `RankScore` produced by `RankConf` (scoring algorithms listed in `RankAlgoList`). See the Aliyun PAI-Rec [Rerank Configuration](https://help.aliyun.com/zh/airec/what-is-pai-rec/user-guide/rearrange-configuration) docs. |

Note: if a `SortConfs[*]` entry is defined with `SortType: ItemRankScore`, the
enum check in §5.2 still applies; the built-in name above covers the case
where `ItemRankScore` is referenced directly in `SortNames[]` without any
`SortConfs` definition.

### 5.3 Required-field checks

- `RecallConfs[*]`: `Name`, `RecallType`, `RecallCount` (positive integer).
- `FilterConfs[*]`: `Name`, `FilterType`.
- `SortConfs[*]`: `Name`, `SortType`.
- `AlgoConfs[*]`: `Name`, `Type`.
- Data-source adapter blocks (`HologresConfs[*]`, `RedisConfs[*]`, …): connection
  identifiers required by Schema.

### 5.4 Reference-consistency (cross-section)

The validator resolves every name reference and reports errors when a referenced
entity is not defined:

| Referencing location | Must resolve to |
|----------------------|-----------------|
| `SceneConfs.<scene>.<category>.RecallNames[]` | `RecallConfs[*].Name` |
| `SceneConfs.<scene>.<category>.FilterNames[]` and top-level `FilterNames[]` | `FilterConfs[*].Name` |
| `SceneConfs.<scene>.<category>.SortNames[]` and top-level `SortNames[]` → each entry's `Name` | `SortConfs[*].Name` |
| `RankConf.<scene>.RankAlgoList[]` | `AlgoConfs[*].Name` |
| `RankConf.<scene>.ContextFeatures[*].FeatureName` | `FeatureConfs.<scene>.FeatureLoadConfs[*]` outputs (when present) |
| `FeatureConfs.<scene>.FeatureLoadConfs[*].FeatureDaoConf.<AdapterType>` + `*Name` | Matching `*Confs` block (see 5.5) |
| `UserFeatureConfs.<scene>.FeatureLoadConfs[*].FeatureDaoConf` | Same as above. |
| `RecallConfs[*].DaoConf` / `FilterConfs[*].DaoConf` | Matching `*Confs` block. |
| `FeatureLogConfs`, `CallBackConfs`, `PipelineConfs` `*.DaoConf` | Matching `*Confs` block. |

### 5.5 Data-source adapter mapping

`DaoConf.AdapterType` (case-insensitive) is mapped to the top-level confs key
holding the connection definition; the `*Name` field inside `DaoConf` must match
an entry there:

| `AdapterType` | Top-level confs key |
|---------------|---------------------|
| `hologres`    | `HologresConfs` |
| `redis`       | `RedisConfs` |
| `mysql`       | `MysqlConfs` |
| `tablestore`  | `TableStoreConfs` |
| `featurestore`| `FeatureStoreConfs` |
| `clickhouse`  | `ClickHouseConfs` |
| `graph`       | `GraphConfs` |
| `lindorm`     | `LindormConfs` |
| `recallengine`| `RecallEngineConfs` |

Any other `AdapterType` is flagged as invalid.

### 5.6 Business rules

- **`User2ItemExposureFilter` + FeatureStore pseudo-exposure**
  When `WriteLog == true` and `DaoConf.AdapterType == "featurestore"`,
  `TimeInterval` is required and must be a **positive integer** (seconds).
  Missing or non-positive values are flagged as errors.

- **`PriorityAdjustCountFilter` accumulator mode**
  Inside `AdjustCountConfs[*]`, for entries with `Type == "accumulator"`
  (the default), the sequence of `Count` values must be **strictly increasing**.
  A non-increasing pair emits a `warning` with a hint that
  `Type = "fix"` should be used for independent per-recall caps. Reported once
  per filter to avoid duplicates.

- **`PipelineConfs[*].Name` uniqueness**
  All pipeline names must be globally unique across `PipelineConfs`.

- **`DebugConfs.Rate`**
  Must be an integer in `[0, 100]` (inclusive). Values outside this range or of
  non-integer types are errors.

### 5.7 Duplicate-name detection

Within each of `RecallConfs`, `FilterConfs`, `SortConfs`, `AlgoConfs` the `Name`
field must be unique; duplicates yield errors at the later occurrence.

---

## 6. How the Skill Uses the Validator

Workflow 2 (SKILL.md §"Workflow 2") runs the following sequence after fetching
the configuration from `pairecservice get-engine-config`:

1. Extract the `ConfigValue` string from the API response.
2. Pipe it to `python3 scripts/validate.py --stdin`.
3. Capture stdout + exit code.
4. Translate the output into the evidence-grounded ✅ / ⚠️ / ❌ report defined in
   SKILL.md §"Workflow 2 / Step 4". Every ⚠️ / ❌ line MUST quote the exact
   `[SEVERITY] path: message` produced by the script (or the exact JSON fragment
   of `ConfigValue` for findings that come from manual inspection outside the
   script's rule set).

---

## 7. Extending the Validator

When adding new rules:

1. Prefer expressing structural constraints in `references/schema.json` (Draft-7).
2. Put cross-section / business-logic rules in
   `PairecConfigValidator._validate_*` methods of `scripts/validate.py`.
3. Keep `ValidationError.severity` aligned with real impact:
   - `error` — config will break at runtime or is definitely invalid.
   - `warning` — likely misconfiguration that has a legitimate alternative.
4. Add/extend the enum sets (`VALID_RECALL_TYPES`, `VALID_FILTER_TYPES`,
   `VALID_SORT_TYPES`, `VALID_RESPONSE_FUNC_NAMES`, `BUILTIN_RECALL_NAMES`,
   `DATASOURCE_ADAPTER_MAP`) at the top of `validate.py` when new types are
   supported. For `VALID_RESPONSE_FUNC_NAMES`, keep in sync with upstream
   `pairec/algorithm/eas/client.go` `SetResponseFunc()`.
