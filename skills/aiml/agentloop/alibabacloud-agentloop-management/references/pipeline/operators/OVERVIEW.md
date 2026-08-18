> **🔗 Reference navigation** | Current: SPL operator specs (internal semantic reference, never surfaced)
> | [API Node definitions (primary external reference)](../nodes/)

# Pipeline Operator Overview

> This file is the quick index for every Pipeline operator. For the full
> definition, parameters, and SQL implementation template of an operator, read its
> own document.

---

## 1. Operator list

### Basic operators (built into SLS SPL)

| Operator | Function |
| --- | --- |
| [`project`](project.md) | Field selection — select and rename fields from the raw log, declaring the Pipeline input schema |
| [`extend`](extend.md) | Field extension — compute new columns or overwrite existing ones with expressions (all SQL functions are available) |
| [`where`](where.md) | Filtering — keep rows that satisfy a condition |
| [`limit`](limit.md) | Row limit — cap the number of output records, equivalent to SQL LIMIT |

> These already exist in SLS SPL; for their syntax see the
> [SLS SPL documentation](https://help.aliyun.com/zh/sls/field-operation-instructions).

### Data assembly

| Operator | Function |
| --- | --- |
| [`make-instance`](make-instance.md) | Instance building — aggregate discrete events by a grouping key into a row-level wide sample table (pure CPU, reusing stats) |

### Data cleaning

| Operator | Function |
| --- | --- |
| [`dedup-exact`](dedup-exact.md) | Exact dedup — keep only one record per fully matching SimHash fingerprint |
| [`dedup-fuzzy`](dedup-fuzzy.md) | Near dedup — treat records within the SimHash Hamming-distance threshold as duplicates |
| [`dedup-semantic`](dedup-semantic.md) | Semantic dedup — treat records within the embedding vector-distance threshold as duplicates |

### Feature computation

| Operator | Function |
| --- | --- |
| [`embedding`](embedding.md) | Vectorization — generate an embedding vector for a text field |
| [`doc-stats`](doc-stats.md) | Document statistics — compute character, word, and line counts and emit JSON |

### Data sampling

| Operator | Function |
| --- | --- |
| [`semantic-cluster`](semantic-cluster.md) | Semantic clustering — assign a cluster ID from the embedding vector |
| [`sample`](sample.md) | Random sampling — sample by ratio or fixed count, optionally per group |

### AI processing

| Operator | Function |
| --- | --- |
| [`llm-call`](llm-call.md) | LLM invocation — template rendering, model selection, and output parsing (recommended); supports rich scenarios such as **AI evaluation**, **AI labeling**, and **AI synthesis** |
| [`agentic-call`](agentic-call.md) | Agent invocation — call a digital employee (agentic agent) for an intelligent conversation, covering SOP analysis, knowledge Q&A, and data insight |

> **In-flight drafts**: the design drafts of in-flight or abandoned operators
> (`ai-gen`, `make-conversation`) live in a separate `drafts/` directory. They are
> not surfaced and are not part of the official operator set.

---

## 2. Scenarios and examples

### Scenario 1: select, extend, and filter fields

The basic operator combination: select fields from the raw log, extend fields into
new columns with string, JSON, or regular-expression handling, then filter by
condition.

```
* | project question=a, input=b, output=c
  | extend question=regexp_extract(question, 'User question: (.*)', 1)
  | where length(question) > 10
  | extend summary=concat(question, ' - ', output)
```

### Scenario 2: three-stage dedup (exact → fuzzy → semantic)

Dedup stage by stage. Compute cost rises while row count falls, so putting exact
dedup first sharply reduces the input size of the later operators.

```
* | project question=a, input=b, output=c
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | dedup-semantic -field=question -threshold='0.1'
```

### Scenario 3: diversity sampling (dedup → cluster → per-group sample)

After semantic dedup, reuse `__dedup_emb` for clustering and sample within each
cluster to guarantee semantic diversity.

```
* | project question=a, input=b, output=c
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3'
  | dedup-semantic -field=question -threshold='0.1'
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=1 by __cluster_id
```

### Scenario 4: complete AI pipeline (dedup → sample → evaluate + label)

Dedup → cluster sampling → several LLM calls. The same `llm-call` operator covers
both evaluation and labeling, just with different prompts.

```
* | project question=a, input=b, output=c
  | dedup-exact -field=question
  | dedup-fuzzy -field=question -threshold='3' -global -workspace='my-ws' -dataset='my-ds'
  | dedup-semantic -field=question -threshold='0.1' -global -workspace='my-ws' -dataset='my-ds'
  | semantic-cluster -field=__dedup_emb -n=100
  | sample -n=3 by __cluster_id
  | llm-call -prompt='@eval/prompt.md' -fields=question,input,output -format=json as eval
  | llm-call -prompt='@anno/prompt.md' -fields=output -format=json -model='qwen-plus' as anno
```

### Scenario 5: simple sampling plus translation

No dedup needed; sample and then run LLM processing.

```
* | project content=raw_text
  | sample -n=200
  | llm-call -prompt='Translate the following into English: {{content}}' -fields=content as translation
```

### Scenario 6: data analysis (vectorize → cluster → measure)

A pure analysis scenario with no dedup and no AI processing.

```
* | project question=a, input=b, output=c
  | embedding -field=question
  | semantic-cluster -field=question_embedding -n=20
  | doc-stats -field=question
```

---

## 3. Pipeline orchestration guide

### Data-flow picture

```
Raw log (event level, N rows per sample)
  │
  ▼
┌─────────────────────────────────────────────┐
│  project / extend / where                   │  select, extend, filter fields
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────┐
    │   Data assembly (aggregate) │
    │  make-instance              │  many rows → one row
    └──────────────┬──────────────┘
                   │  from here on, one row = one complete sample
    ┌──────────────▼──────────────┐
    │    Data cleaning (dedup)    │
    │  dedup-exact                │
    │  dedup-fuzzy                │  row count falls
    │  dedup-semantic             │  ↓
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │   Data sampling (reduce)    │
    │  semantic-cluster → sample  │  row count falls
    └──────────────┬──────────────┘
                   │
    ┌──────────────▼──────────────┐
    │  AI processing (add columns)│
    │  llm-call (eval/label/expand)│ row count unchanged
    │  agentic-call (agent)       │
    │  doc-stats (statistics)     │
    └──────────────┬──────────────┘
                   │
                   ▼
            Output Dataset
```

### Orchestration principles

| Principle | Description |
| --- | --- |
| **Schema first** | Start the pipeline with `project` to select fields and `extend` to compute derived ones, declaring one consistent set of Pipeline field names |
| **Assemble early** | Aggregate discrete event data into row-level samples with `make-instance` before any further processing |
| **Reduce before enrich** | Dedup and sample first (fewer rows), then run AI processing (more columns). LLM calls are expensive, so always run them after the volume has come down |
| **Coarse to fine** | Dedup order: exact → fuzzy → semantic. Compute cost rises along the way, but the earlier stages have already cut the data down |
| **Reuse derived columns** | Derived columns produced upstream (such as `__dedup_emb` and `__cluster_id`) can be referenced directly downstream without recomputation |
| **Operator atomicity** | Every operator has one responsibility: clustering only labels the cluster ID, sampling only drops rows, AI only adds columns. Compose the pipeline to express complex logic |
