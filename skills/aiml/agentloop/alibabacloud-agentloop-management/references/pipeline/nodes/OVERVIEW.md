> **Link: Reference navigation** | Current: API Node definitions (primary external reference)
> | [SPL operator specs (internal semantic reference, never surfaced)](../operators/)

# Pipeline Node Overview

> This file is the quick index for every Pipeline node. For the full definition
> and parameter details of a node, read its own document.

---

## 1. Node list

### Basic processing

| Node | Function |
|------|----------|
| [`project`](project.md) | Field selection - select and rename fields from the raw data, declaring the Pipeline input schema |
| [`extend`](extend.md) | Field extension - compute new columns or overwrite existing ones with expressions (all built-in functions are available) |
| [`where`](where.md) | Filtering - keep rows that satisfy a condition expression |
| [`limit`](limit.md) | Row limit - cap the number of output records, equivalent to SQL LIMIT |

### Data assembly

| Node | Function |
|------|----------|
| [`make-instance`](make-instance.md) | Instance building - aggregate discrete events by a grouping key into a row-level wide sample table (pure CPU) |

### Data cleaning

| Node | Function |
|------|----------|
| [`dedup-exact`](dedup-exact.md) | Exact dedup - keep only one record among fully identical texts |
| [`dedup-fuzzy`](dedup-fuzzy.md) | Near dedup - treat highly similar texts (minimal literal difference) as duplicates |
| [`dedup-semantic`](dedup-semantic.md) | Semantic dedup - treat differently worded but equivalent texts as duplicates |

### Feature computation

| Node | Function |
|------|----------|
| [`embedding`](embedding.md) | Vector generation - produce an embedding vector for a text field |
| [`doc-stats`](doc-stats.md) | Document statistics - compute character, word, and line counts and similar metrics |

### Data sampling

| Node | Function |
|------|----------|
| [`semantic-cluster`](semantic-cluster.md) | Semantic clustering - assign a cluster ID to each row from its embedding vector |
| [`sample`](sample.md) | Random sampling - sample by ratio or fixed count, optionally per group |

### AI processing

| Node | Function |
|------|----------|
| [`llm-call`](llm-call.md) | LLM invocation - template rendering, model inference, and output parsing for evaluation, labeling, and synthesis |
| [`agentic-call`](agentic-call.md) | Agent invocation - call a digital employee for an intelligent conversation, covering SOP analysis, knowledge Q&A, and data insight |

---

## 2. Scenarios and examples

### Scenario 1: select, extend, and filter fields

The basic node combination: select fields from the raw data, extend fields with
string, JSON, or regular-expression handling, then filter by condition.

```json
{
  "nodes": [
    {
      "id": "n1", "type": "project",
      "parameters": { "question": "a", "input": "b", "output": "c" }
    },
    {
      "id": "n2", "type": "extend",
      "parameters": { "question": "regexp_extract(question, 'User question: (.*)', 1)" }
    },
    {
      "id": "n3", "type": "where",
      "parameters": { "filter": "length(question) > 10" }
    }
  ]
}
```

### Scenario 2: three-stage dedup (exact -> fuzzy -> semantic)

Dedup stage by stage. Compute cost rises while row count falls, so putting exact
dedup first sharply reduces the work of the later nodes.

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3" } },
    { "id": "n4", "type": "dedup-semantic", "parameters": { "field": "question", "threshold": "0.1" } }
  ]
}
```

### Scenario 3: diversity sampling (dedup -> cluster -> per-group sample)

After semantic dedup, cluster on the generated vector column and sample within
each cluster to guarantee semantic diversity.

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3" } },
    { "id": "n4", "type": "dedup-semantic", "parameters": { "field": "question", "threshold": "0.1" } },
    { "id": "n5", "type": "semantic-cluster", "parameters": { "field": "__dedup_emb", "n": 100 } },
    { "id": "n6", "type": "sample", "parameters": { "by": "__cluster_id", "n": 1 } }
  ]
}
```

### Scenario 4: complete AI pipeline (dedup -> sample -> evaluate + label)

```json
{
  "nodes": [
    { "id": "n1", "type": "project", "parameters": { "question": "a", "input": "b", "output": "c" } },
    { "id": "n2", "type": "dedup-exact", "parameters": { "field": "question" } },
    { "id": "n3", "type": "dedup-fuzzy", "parameters": { "field": "question", "threshold": "3", "global": true, "workspace": "my-ws", "dataset": "my-ds" } },
    { "id": "n4", "type": "dedup-semantic", "parameters": { "field": "question", "threshold": "0.1", "global": true, "workspace": "my-ws", "dataset": "my-ds" } },
    { "id": "n5", "type": "semantic-cluster", "parameters": { "field": "__dedup_emb", "n": 100 } },
    { "id": "n6", "type": "sample", "parameters": { "by": "__cluster_id", "n": 3 } },
    { "id": "n7", "type": "llm-call", "parameters": { "prompt": "@eval/prompt.md", "fields": "question,input,output", "format": "json", "as": "eval" } },
    { "id": "n8", "type": "llm-call", "parameters": { "prompt": "@anno/prompt.md", "fields": "output", "format": "json", "model": "qwen-plus", "as": "anno" } }
  ]
}
```

---

## 3. Pipeline orchestration guide

### Data-flow picture

```
Raw data (event level, N rows per sample)
  |
  v
+---------------------------------------------+
|  project / extend / where                   |  select, extend, filter fields
+------------------+--------------------------+
                   |
    +--------------v--------------+
    |   Data assembly (aggregate) |
    |  make-instance              |  many rows -> one row
    +--------------+--------------+
                   |  from here on, one row = one complete sample
    +--------------v--------------+
    |    Data cleaning (dedup)    |
    |  dedup-exact                |
    |  dedup-fuzzy                |  row count falls
    |  dedup-semantic             |  v
    +--------------+--------------+
                   |
    +--------------v--------------+
    |   Data sampling (reduce)    |
    |  semantic-cluster -> sample  |  row count falls
    +--------------+--------------+
                   |
    +--------------v--------------+
    |  AI processing (add columns)|
    |  llm-call (eval/label/synth)|  row count unchanged
    |  agentic-call (agent)       |
    |  doc-stats (statistics)     |
    +--------------+--------------+
                   |
                   v
            Output Dataset
```

### Orchestration principles

| Principle | Description |
|-----------|-------------|
| **Schema first** | Start the Pipeline with `project` to select fields and `extend` to derive fields, declaring one consistent set of field names |
| **Assemble early** | Aggregate discrete event data into row-level samples with `make-instance` before any further processing |
| **Reduce before enrich** | Dedup and sample first (fewer rows), then run AI processing (more columns). LLM calls are expensive, so always run them after the volume has come down |
| **Coarse to fine** | Dedup order: exact -> fuzzy -> semantic. Compute cost rises along the way, but the earlier stages have already cut the data down |
| **Reuse derived columns** | Derived columns produced upstream (such as `__dedup_emb` and `__cluster_id`) can be referenced directly downstream without recomputation |
| **Node atomicity** | Every node has one responsibility: clustering only labels the cluster ID, sampling only drops rows, AI only adds columns. Compose the Pipeline to express complex logic |
