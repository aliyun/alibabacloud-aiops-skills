# Knowledge Base Search Scene

This guide describes how to build private-domain knowledge-base Q&A with the Lindorm search engine, vector engine, and AI engine. The default path is: upload txt or CMRC-style JSON documents, split them into chunks, generate embeddings for chunk text, write the chunks to Lindorm, build a vector index, recall context through KNN or RRF, optionally rerank the candidates, and then call the Chat model to generate an answer.

## Scenario Goals

| Phase | Capability |
|-------|------------|
| Data import | Support txt documents and CMRC-style JSON data |
| Data modeling | Store the original text in parent documents and store split text plus vectors in the chunk index |
| Vectorization | Generate vectors through the Lindorm AI embedding model |
| Data ingestion | Use search engine `_bulk` or wide table `UPSERT` |
| Index building | Explicitly build IVFPQ / IVFBQ indexes and check the status |
| Q&A retrieval | Recall by KNN/RRF, rerank candidates, and answer with Chat based on context |

## Recommended Data Model

### Direct Search Engine Mode

Parent document index `<dataset_name>_parent`:

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | keyword | Document ID |
| `title` | text | Title |
| `context` | text | Original full text. It may be excluded from indexing |
| `metadata` | object | Source, file name, and business tags |

Chunk index `<dataset_name>_chunking`:

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | keyword | Parent document ID |
| `chunking_position` | integer | Chunk position |
| `chunking_number` | integer | Total chunk number or sequence number |
| `text_field` | text | Chunk text |
| `vector_field` | knn_vector | Chunk embedding |
| `metadata` | object | Source information |

### Wide Table Entry Mode

In wide table mode, create a table first and then create a search index with `CREATE INDEX ... USING SEARCH`. The pipeline automatically writes `text` into `vector_field`. For the specific DDL and pipeline template, see the `sql-vector` section in `vector-guide.md`.

## Document Chunking

### txt documents

Processing flow:

```text
read txt
-> normalize whitespace
-> split by paragraph / sentence
-> merge to chunk_size
-> keep overlap
-> assign document_id + chunking_position
```

Recommended defaults:

| Parameter | Default value |
|-----------|---------------|
| `chunk_size` | 500-800 Chinese characters |
| `chunk_overlap` | 50-100 Chinese characters |
| `min_chunk_size` | 50 Chinese characters |
| `document_id` | File-name hash or user-specified ID |

### CMRC-style JSON

CMRC data usually contains passages, questions, and answers. When building a knowledge base, prefer using the passage `context` as the parent document, and write the split context into the chunk index. Questions and answers can be used as metadata or a validation set, but should not directly replace the original text.

## Index Creation

A knowledge base can use HNSW for quick validation, or IVFPQ / IVFBQ for large-scale low-cost retrieval. When an offline index is used, as in the reference project, explicitly build the index after data is written.

Example IVFBQ chunk index:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/<dataset_name>_chunking?pretty" \
  -d '{
    "settings": {
      "index": {
        "number_of_shards": 4,
        "knn": true,
        "knn.offline.construction": true
      }
    },
    "mappings": {
      "_source": { "excludes": ["vector_field"] },
      "properties": {
        "document_id": { "type": "keyword" },
        "chunking_position": { "type": "integer" },
        "chunking_number": { "type": "integer" },
        "text_field": { "type": "text", "analyzer": "ik_max_word" },
        "vector_field": {
          "type": "knn_vector",
          "dimension": 1024,
          "data_type": "float",
          "method": {
            "engine": "lvector",
            "name": "ivfbq",
            "space_type": "cosinesimil",
            "parameters": {
              "exbits": 2,
              "nlist": 50
            }
          }
        },
        "metadata": { "type": "object" }
      }
    }
  }'
```

The parent document index may omit vector fields:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/<dataset_name>_parent?pretty" \
  -d '{
    "settings": {
      "index": { "number_of_shards": 2 }
    },
    "mappings": {
      "properties": {
        "document_id": { "type": "keyword" },
        "title": { "type": "text", "analyzer": "ik_max_word" },
        "context": { "type": "text", "index": false },
        "metadata": { "type": "object" }
      }
    }
  }'
```

## Vectorization and Data Ingestion

Call AI embedding for each chunk:

```bash
curl --connect-timeout 10 -m 60 \
  -H 'Content-Type: application/json' \
  -H 'x-ld-ak: <username>' \
  -H 'x-ld-sk: <password>' \
  -XPOST "http://<ai_endpoint>:9002/dashscope/compatible-mode/v1/embeddings" \
  -d '{
    "model": "text-embedding-v4",
    "input": "<chunk_text>"
  }'
```

Write chunks:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/x-ndjson' \
  -XPOST "http://<search_endpoint>:30070/_bulk" \
  -d '
{"index":{"_index":"<dataset_name>_chunking","_id":"doc_001_0"}}
{"document_id":"doc_001","chunking_position":0,"chunking_number":1,"text_field":"<chunk_text>","vector_field":[0.01,0.02,0.03],"metadata":{"source":"upload"}}
'
```

Verify after ingestion:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<dataset_name>_chunking/_count" \
  -d '{
    "query": { "match_all": {} }
  }'
```

## Build IVFPQ / IVFBQ Indexes

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/_plugins/_vector/index/build" \
  -d '{
    "indexName": "<dataset_name>_chunking",
    "fieldName": "vector_field",
    "removeOldIndex": "true"
  }'
```

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XGET "http://<search_endpoint>:30070/_plugins/_vector/index/tasks" \
  -d '{
    "indexName": "<dataset_name>_chunking",
    "fieldName": "vector_field",
    "taskIds": "[]"
  }'
```

Only mark the large-scale offline indexing process as successful after the task status is complete.

## Knowledge Base Retrieval

### KNN recall

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<dataset_name>_chunking/_search?pretty" \
  -d '{
    "size": 5,
    "_source": ["document_id", "chunking_position", "text_field", "metadata"],
    "query": {
      "knn": {
        "vector_field": {
          "vector": [0.01, 0.02, 0.03],
          "k": 10
        }
      }
    },
    "ext": {
      "lvector": {
        "nprobe": "80",
        "reorder_factor": "2",
        "client_refactor": "true"
      }
    }
  }'
```

### RRF recall

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<dataset_name>_chunking/_search?pretty" \
  -d '{
    "size": 5,
    "_source": ["document_id", "chunking_position", "text_field", "metadata"],
    "query": {
      "knn": {
        "vector_field": {
          "vector": [0.01, 0.02, 0.03],
          "filter": {
            "match": {
              "text_field": "question text"
            }
          },
          "k": 10
        }
      }
    },
    "ext": {
      "lvector": {
        "hybrid_search_type": "filter_rrf",
        "rrf_rank_constant": "60",
        "rrf_knn_weight_factor": "0.5"
      }
    }
  }'
```

### Reranking and context assembly

Call the rerank API in `ai-guide.md` for the recalled `text_field` list. Then select the top chunks by score and concatenate the context:

```text
Known information:
1. <chunk_1_text>
2. <chunk_2_text>
3. <chunk_3_text>

Answer the user question based only on the known information above. If the answer cannot be derived from the known information, answer "The question cannot be answered based on the known information." Do not fabricate.
Question: <question>
```

### Q&A generation

Use the Chat API in `ai-guide.md`. The answer must include retrieval evidence:

| Output item | Description |
|-------------|-------------|
| `answer` | Answer based on recalled context |
| `citations` | `document_id`, `chunking_position`, and score |
| `retrieval_mode` | `knn` / `rrf` / `rrf+rerank` |
| `blocked_status` | Network, authentication, schema, or index-building blocker |

## Acceptance Evidence

```text
[Target] instance=<instance_id> region=<region> network=<public|vpc>
[Dataset] name=<dataset_name> parent_index=<name> chunk_index=<name>
[Chunking] documents=<n> chunks=<n> chunk_size=<n> overlap=<n>
[Embedding] model=<model_name> dimension=<n> succeeded=<n> failed=<n>
[IndexBuild] algorithm=<hnsw|ivfpq|ivfbq> status=<FINISH|not_required|FAILED>
[Retrieval] mode=<knn|rrf|rrf+rerank> question=<masked_question> hits=<n>
[Answer] generated=<true|false> citations=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA|BLOCKED_INDEX_BUILD|BLOCKED_MODEL> reason=<reason>
```
