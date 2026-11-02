# Exploring a Context Model and Reading Definitions

## 1. Identify the business model

Use the Context Model provided by the user or context by default; UUIDs in `contextModels` are valid model names. Supply the model endpoint through `--endpoint` or `SLS_CONTEXT_MODEL_ENDPOINT`, and use it only for `context-model` calls. If the endpoint is missing and cannot be determined from a user-provided region, ask the user to supply it. If no Context Model has been provided, run `context-model list` to list candidates and ask the user to confirm a model.

## 2. Explore the model and read definitions

### 2.1 Model overview

Use catalog overview to discover available sources and the Elements containing each type of definition.

```bash
python3 scripts/model_qa.py context-model catalog overview \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>"
```

`overview` returns catalog summaries and Member names, not the original Member definitions. Use search/get to read complete definitions, including the full text of overview details.

- `modelScope`: The model-level catalog, including names of terms that are not associated with a specific Schema.
- `sources`: The source-level catalog, with semantic Element names and their Member names grouped by source.
- `unresolved`: Catalog entries whose associations cannot be reliably resolved; do not use these entries as a basis for the current analysis.

### 2.2 Member definitions

**Find relevant definitions (search)**

Use search to find definitions relevant to the business question. Describe the current question or answer branch in `--query`, preserving the known analysis targets, scope and names. To restrict sources, pass confirmed source values through `--sources`.

```bash
python3 scripts/model_qa.py context-model catalog search \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>" --query "<full-intent-of-question-or-answer-branch>" \
  [--sources "<confirmed-source>"]
```

`search` returns the original definitions of selected Members. `results` groups them by Element, with definitions in each group's `members`.

- Empty `results` do not prove that the model lacks relevant knowledge.

**Read specific definitions (get)**

Use get to read definitions for a specific Element or Member. Provide exactly one `--*-element` argument with an Element name already identified. Use `--members` to select Members; omit it to read the entire Element.

```bash
python3 scripts/model_qa.py context-model catalog get \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>" --<schema|overview|metric|term|example-query>-element "<element>" \
  [--members "member1,member2"]
```

In the response, `members` contains the returned original definitions. `missingMembers` lists Members requested through `--members` that do not exist.

**Additional reads and semantic acceptance**

Search results do not necessarily contain every definition needed for the question. Other Members referenced by a returned definition are not included automatically; read them separately when needed.

- **Budget omissions**: `omittedMembers` in each search `results` group or at the top level of a get response lists Members whose definitions were omitted due to the byte budget. Retrieve needed definitions with get, using their Element type and name and `--members`. Even when `members` is empty, use the retained Element information to retrieve the omitted definitions. If the additional read still exceeds the budget, increase `--max-bytes`.
- **Semantic acceptance**: For a Member with `confidence`, `confidence.status` indicates whether its semantics, such as a field description or metric definition, have been accepted for use. Both `auto_applied` and `manually_applied` indicate accepted semantics that can be used to interpret the data. `not_applied` means the semantics have not yet been accepted: use them only as candidate clues and verify them against actual data before determining the query criteria. Factual attributes, such as field types, are not subject to this restriction.

## 3. Determine query locations

Use `catalog resolve` to obtain query locations for an answer branch. Provide exactly one of `--schema` or `--source`. If the Schema for the current data selection is already confirmed, reuse it; otherwise choose the input using the following table.

| `elementType` | Resolve input |
| --- | --- |
| `schema` | Pass the result's `element` to `--schema`. |
| `metric` / `overview` | Pass the result's `source` to `--source`. |
| `term` | Select the current Member's valid `model_bindings[].name` values according to the business scope and pass each to `--schema`. A model-level term does not determine a query location. Multiple bindings do not automatically require querying all sources, merging results or using JOIN. |
| `exampleQuery` | Pass the current Member's valid `model_binding.name` to `--schema`. |

```bash
# Known Schema
python3 scripts/model_qa.py context-model catalog resolve \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>" --schema "<schema-element>"

# Only the source is known
python3 scripts/model_qa.py context-model catalog resolve \
  --endpoint "<context-model-endpoint>" \
  --name "<model-name>" --source "<source>"
```

The returned `schema` is the resolved Schema name. Within the same analysis of the same business model, identify the same target by this name and reuse its query location information instead of resolving it again.

`datasources` contains candidate query locations for the current answer branch. Each entry identifies a location for log queries, with `store` corresponding to the query command's `--logstore` argument. Multiple candidates do not automatically create separate branches. Determine query scope as follows:

- If the user specifies one resource, query only that resource. If the user specifies a resource set, query all locations within that set.
- If the investigation target's location is unknown, query all relevant candidates.
- Ask the user to confirm when scope is unclear, there are too many candidates, or the aggregation approach is uncertain. Do not choose a "primary" data source on your own.
