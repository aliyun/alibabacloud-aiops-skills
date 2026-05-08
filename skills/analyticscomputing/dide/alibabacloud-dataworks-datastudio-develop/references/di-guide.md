# DI Data Synchronization Development Guide

DI (Data Integration) is DataWorks' offline data synchronization service that supports data migration and synchronization across heterogeneous data sources. This document covers ONLY how a DI node is mounted in FlowSpec and the local file workflow for creating one.

> ⚠️ **DI content (i.e., the DIJob JSON inside `script.content`) field definitions are NOT in this document.** When generating or modifying DI content, you MUST strictly follow the authoritative references listed below — see [DIJob Content Reference (Progressive Loading)](#dijob-content-reference-progressive-loading).

---

## DI Node Overview

DI node type identifiers in FlowSpec:

| Field | Value |
|------|------|
| `script.runtime.command` | `DI` |
| `script.language` | `di` |
| Code file extension | `.json` |
| `datasourceType` | `null` (no node-level datasource needed; datasources are configured inside the DIJob content) |

The DI node's code file is a JSON-formatted DIJob definition that describes the complete configuration for data reading (Reader) and writing (Writer).

> ⚠️ **Mandatory**: The DIJob content (the JSON string inside `script.content`) MUST be generated strictly according to the authoritative references in `references/nodetypes/data_integration/`. Do NOT invent fields based on memory or examples from other sources.

---

## DIJob Content Reference (Progressive Loading)

The DI node's `script.content` is a standalone DIJob JSON sub-structure. **Its field definitions live in dedicated authoritative documents, not in this guide.**

When generating or modifying DI content, load the following references **in this exact order**:

| Step | Document | Purpose |
|------|----------|---------|
| 1 | `references/nodetypes/data_integration/DI.md` | DI node entry point + mandatory constraint checklist |
| 2 | `references/nodetypes/data_integration/DATAX.md` | Top-level `content` skeleton + `extend` block (REQUIRED) |
| 3 | `references/nodetypes/data_integration/datasources/{Reader-DS}/{DS}-Source.md` | Reader `parameter` field table |
| 4 | `references/nodetypes/data_integration/datasources/{Writer-DS}/{DS}-Destination.md` | Writer `parameter` field table |
| 5 | `references/nodetypes/data_integration/settings.md` | `setting` block field table (speed / errorLimit / executeMode / etc.) |

**Available data sources**: see the subdirectories under `references/nodetypes/data_integration/datasources/` (60+ data sources, each with `Source` and `Destination` field documents).

### Prohibited Behaviors

- ❌ Do NOT reference any historical examples or field shapes that previously existed in this document
- ❌ Do NOT construct `parameter` fields from memory or convention — every key MUST appear in the corresponding `{DS}-Source.md` / `{DS}-Destination.md` field table
- ❌ Do NOT omit the top-level `extend` block (DATAX.md marks it as REQUIRED)
- ❌ Do NOT write `errorLimit: { "record": 0 }` — settings.md requires `errorLimit.strategy` (enum: `Ignore` / `Tolerance` / `ZeroTolerance`); `record` is only valid when `strategy = Tolerance`
- ❌ Do NOT use `column: ["*"]` — both source and destination column lists must be explicitly enumerated
- ❌ Do NOT mix shapes from different data source documents (e.g., do not assume MySQL Reader uses the same structure as PostgreSQL Reader — always re-read each `{DS}-Source.md`)

---

## DI Node Creation Process

The DI node creation process is the same as for regular nodes; the only difference is that the code file is in JSON format and its content MUST be generated against the authoritative references above.

```bash
# 1. Create the node directory
mkdir -p ./sync_user_to_odps

# 2. Edit spec.json
#    - name: sync_user_to_odps
#    - script.runtime.command: DI
#    - script.language: di
#    - No `datasource` field at node level (DI datasources live inside the DIJob content)

# 3. Write the DI code file (DIJob JSON)
#    Generate sync_user_to_odps.json by strictly following, in order:
#      - references/nodetypes/data_integration/DI.md
#      - references/nodetypes/data_integration/DATAX.md
#      - references/nodetypes/data_integration/datasources/{Reader-DS}/{DS}-Source.md
#      - references/nodetypes/data_integration/datasources/{Writer-DS}/{DS}-Destination.md
#      - references/nodetypes/data_integration/settings.md

# 4. Create dataworks.properties
cat > ./sync_user_to_odps/dataworks.properties << 'EOF'
projectIdentifier=my_project
spec.runtimeResource.resourceGroup=S_res_group_xxx
EOF

# 5. Build the merged spec JSON
python $SKILL/scripts/build.py ./sync_user_to_odps > /tmp/spec.json

# 6. Validate before submission (especially that script.content embeds valid DIJob JSON)
python $SKILL/scripts/validate.py ./sync_user_to_odps
python3 - <<'PY'
import json
spec = json.load(open('/tmp/spec.json'))
content = spec['spec']['nodes'][0]['script'].get('content', '')
assert content.strip(), 'DI script.content is empty'
json.loads(content)
print('DI content OK, length=', len(content))
PY

# 7. Submit via API
aliyun dataworks-public create-node \
  --project-id {{project_id}} \
  --scene DATAWORKS_PROJECT \
  --spec "$(cat /tmp/spec.json)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-dataworks-datastudio-develop
```

---

## Important Notes

1. **Datasource name consistency**: Every `parameter.datasource` value inside the DIJob content MUST exactly match a datasource name registered in DataWorks. Verify with `ListDataSources` before generating.
2. **Column count alignment**: Reader and Writer column lists must have identical length and one-to-one positional correspondence.
3. **MaxCompute partition format**: Use `dt=${bizdate}` style; supports scheduling parameter substitution. See `datasources/MaxCompute/MaxCompute-Destination.md` for the exact `partition` parameter rules.
4. **Concurrency**: Setting `setting.speed.concurrent` too high may overload the source database; tune based on actual load. See `settings.md` for the valid range and defaults.
5. **No node-level `datasource`**: Unlike `ODPS_SQL` and similar nodes, the DI node's spec.json does NOT need a `datasource` field; all datasource information is configured inside `parameter.datasource` within the DIJob content.
6. **`extend` block is REQUIRED**: The DIJob content MUST include a top-level `extend` block with `mode`, `__new__`, `formatType`, `resourceGroup`, and `cu`. See `DATAX.md` for the exact specification.
7. **No guessing**: If a parameter you need is not documented in the corresponding `{DS}-Source.md` / `{DS}-Destination.md` / `settings.md`, do NOT invent it — ask the user or check the live environment with `GetNode` against an existing similar node.
