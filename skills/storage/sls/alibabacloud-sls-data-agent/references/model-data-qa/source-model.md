# Source Model exploration and definition reads

## 1. Confirm the target and model availability

Use the Project and Logstore supplied by the context by default. If the target Logstore's `sourceModelReady` is `true`, or model availability has already been confirmed, explore the model directly. Otherwise follow [Model availability checks and enablement guidance](source-model-readiness.md).

## 2. Explore the current Logstore and read definitions

### 2.1 Model overview

Use catalog overview when you need the current Logstore's model directory and the Elements holding each type of definition. Set `--sources` to `<project>.<logstore>` to limit the target Logstore.

```bash
python3 "<skill-dir>/scripts/model_qa.py" source-model catalog overview \
  --region "<region>" --project "<project>" --sources "<project>.<logstore>"
```

overview returns directory summaries and Member names, not original Member definitions. Read complete definitions, including overview detail text, through get.

- `modelScope`: the model-level directory, including term names not associated with a specific Schema.
- `sources`: source-level directories, containing semantic Element names and their Member names grouped by source.
- `unresolved`: directory content without a stable attribution; it cannot support the current analysis.

### 2.2 Member definitions

**Read selected definitions (get)**

Use get to read a selected Element or Member definition. Supply exactly one `--*-element` argument naming an Element already located. Use `--members` for the required Members; omit it to read the whole Element.

Command template:

```bash
python3 "<skill-dir>/scripts/model_qa.py" source-model catalog get \
  --region "<region>" --project "<project>" --<schema|overview|metric|term>-element "<element>" \
  [--members "member1,member2"]
```

In the result, `members` contains the original definitions returned, and `missingMembers` identifies Members requested through `--members` that do not exist.

**Read additional definitions and check adoption**

Other Members mentioned in returned definitions are not included automatically; read them separately when needed.

- **Budget omissions**: the top-level `omittedMembers` from get identifies Members whose original definitions were omitted by the byte budget. When needed, use the owning Element's type and name with get's `--members` to read them. Even if `members` is empty, the retained Element identity can be used for recovery. Increase `--max-bytes` if the additional read remains budget-limited.
- **Semantic adoption**: for a Member containing `confidence`, `confidence.status` records adoption of semantics such as field descriptions and metric calculation rules. `auto_applied` and `manually_applied` are adopted and may be used as semantic evidence. `not_applied` is not yet adopted and is only a candidate lead; verify it against actual data before establishing query calculation rules. Factual attributes such as field types are not subject to this restriction.
