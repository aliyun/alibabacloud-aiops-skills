# Context Model exploration and definition reads

## 1. Select the business model

Use the Context Model supplied by the context by default (`contextModels` UUIDs are also valid model names). An injected endpoint applies only to `context-model` calls. If no Context Model is available, run `context-model list` to list candidates and ask the user to confirm.

## 2. Explore the model and read definitions

### 2.1 Model overview

Use catalog overview when you need the model directory to identify available sources and the Elements holding each type of definition.

```bash
python3 "<skill-dir>/scripts/model_qa.py" context-model catalog overview \
  --region "<region>" --name "<model-name>"
```

overview returns directory summaries and Member names, not original Member definitions. Read complete definitions, including overview detail text, through get.

- `modelScope`: the model-level directory, including term names not associated with a specific Schema.
- `sources`: source-level directories, containing semantic Element names and their Member names grouped by source.
- `unresolved`: directory content without a stable attribution; it cannot support the current analysis.

### 2.2 Member definitions

**Read selected definitions (get)**

Use get to read a selected Element or Member definition. Supply exactly one `--*-element` argument naming an Element already located. Use `--members` for the required Members; omit it to read the whole Element.

```bash
python3 "<skill-dir>/scripts/model_qa.py" context-model catalog get \
  --region "<region>" --name "<model-name>" --<schema|overview|metric|term|example-query>-element "<element>" \
  [--members "member1,member2"]
```

In the result, `members` contains the original definitions returned, and `missingMembers` identifies Members requested through `--members` that do not exist.

**Read additional definitions and check adoption**

Other Members mentioned in returned definitions are not included automatically; read them separately when needed.

- **Budget omissions**: the top-level `omittedMembers` from get identifies Members whose original definitions were omitted by the byte budget. When needed, use the owning Element's type and name with get's `--members` to read them. Even if `members` is empty, the retained Element identity can be used for recovery. Increase `--max-bytes` if the additional read remains budget-limited.
- **Semantic adoption**: for a Member containing `confidence`, `confidence.status` records adoption of semantics such as field descriptions and metric calculation rules. `auto_applied` and `manually_applied` are adopted and may be used as semantic evidence. `not_applied` is not yet adopted and is only a candidate lead; verify it against actual data before establishing query calculation rules. Factual attributes such as field types are not subject to this restriction.

## 3. Determine execution coordinates

Use `catalog resolve` when you need an answer branch's execution coordinates. Supply exactly one of `--schema` and `--source`. Reuse the Schema already confirmed for the current object of analysis; otherwise choose the input from the table below.

| `elementType` | resolve input |
| --- | --- |
| `schema` | Pass the result's `element` to `--schema`. |
| `metric` / `overview` | Pass the result's `source` to `--source`. |
| `term` | Select valid `model_bindings[].name` entries for the current Member according to business scope, and pass each to `--schema`. Model-level terms do not determine a query location on their own; multiple bindings do not automatically require querying all, combining results, or JOINs. |
| `exampleQuery` | Pass the current Member's valid `model_binding.name` to `--schema`. |

```bash
# Known Schema
python3 "<skill-dir>/scripts/model_qa.py" context-model catalog resolve \
  --region "<region>" --name "<model-name>" --schema "<schema-element>"

# Only the source is known
python3 "<skill-dir>/scripts/model_qa.py" context-model catalog resolve \
  --region "<region>" --name "<model-name>" --source "<source>"
```

The returned `schema` is the Schema name actually resolved. Within the same business model and analysis, use that name to identify the same target, reuse execution coordinates already obtained, and avoid resolving them again.

`datasources` contains execution candidates for the current answer branch. Each item is a set of log-query coordinates, where `store` corresponds to the query command's `--logstore`. Multiple candidates do not automatically create separate branches. Determine query scope as follows:

- For a single resource specified by the user, query only that resource; for a specified collection, query every set of coordinates within the scope.
- When the investigation object's location is unknown, query all relevant candidates.
- Ask the user to confirm when scope is unclear, there are too many candidates, or the aggregation method is uncertain. Do not select a "primary" data source yourself.
