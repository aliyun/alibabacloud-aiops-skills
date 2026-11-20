# Exploring a Source Model and Reading Definitions

## 1. Confirm the target and model availability

Use the Project and Logstore provided by the user or context by default. Pass the confirmed `--region` explicitly to both CLI commands and the search/readiness helpers. If availability for this Logstore has not been confirmed, follow [Availability checks](availability.md).

## 2. Explore the current Logstore and read definitions

### 2.1 Model overview

Use catalog overview to inspect the current Logstore's model catalog and the Elements containing each type of definition. Set `--sources` to `<project>.<logstore>` to restrict the request to the target Logstore.

```bash
aliyun sls source-model catalog overview --format json \
  --region "<region>" --project "<project>" --sources "<project>.<logstore>"
```

`overview` returns catalog summaries and Member names, not the original Member definitions. Use search/get to read complete definitions, including the full text of overview details.

- `modelScope`: The model-level catalog, including names of terms that are not associated with a specific Schema.
- `sources`: The source-level catalog, with semantic Element names and their Member names grouped by source.
- `unresolved`: Catalog entries whose associations cannot be reliably resolved; do not use these entries as a basis for the current analysis.

### 2.2 Member definitions

**Find relevant definitions (search)**

Use the search helper to find definitions relevant to the business question. It invokes the Aliyun CLI for model reads; pass the same `--profile`, `--region` and `--endpoint` overrides as the other model commands when needed. See [command routing](commands.md#endpoints-and-credentials). Describe the current question or answer branch in `--query`, preserving the known analysis targets, scope and names. Set `--sources` to `<project>.<logstore>` to restrict the request to the target Logstore.

```bash
python3 scripts/semantic-model/model_qa.py source-model catalog search \
  --region "<region>" --project "<project>" --query "<full-intent-of-question-or-answer-branch>" \
  --sources "<project>.<logstore>"
```

`search` returns the original definitions of selected Members. `results` groups them by Element, with definitions in each group's `members`.

- Empty `results` do not prove that the model lacks relevant knowledge.

**Read specific definitions (get)**

Use get to read definitions for a specific Element or Member. Provide exactly one `--*-element` argument with an Element name already identified. Use `--members` to select Members; omit it to read the entire Element.

Command template:

```bash
aliyun sls source-model catalog get --format json \
  --region "<region>" --project "<project>" --<schema|overview|metric|term>-element "<element>" \
  [--members "member1,member2"]
```

In the response, `members` contains the returned original definitions. `missingMembers` lists Members requested through `--members` that do not exist.

**Additional reads and semantic acceptance**

Search results do not necessarily contain every definition needed for the question. Other Members referenced by a returned definition are not included automatically; read them separately when needed.

- **Budget omissions**: `omittedMembers` in each search `results` group or at the top level of a get response lists Members whose definitions were omitted due to the byte budget. Retrieve needed definitions with get, using their Element type and name and `--members`. Even when `members` is empty, use the retained Element information to retrieve the omitted definitions. If the additional read still exceeds the budget, increase `--max-bytes`.
- **Semantic acceptance**: For a Member with `confidence`, `confidence.status` indicates whether its semantics, such as a field description or metric definition, have been accepted for use. Both `auto_applied` and `manually_applied` indicate accepted semantics that can be used to interpret the data. `not_applied` means the semantics have not yet been accepted: use them only as candidate clues and verify them against actual data before determining the query criteria. Factual attributes, such as field types, are not subject to this restriction.
