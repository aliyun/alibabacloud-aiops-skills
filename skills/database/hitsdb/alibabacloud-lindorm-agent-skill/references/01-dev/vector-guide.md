# Lindorm Vector Engine Guide

This guide describes the two access paths for Lindorm vector search: `es-vector` and `sql-vector`. The vector engine is a built-in Lindorm engine and does not directly provide an independent access endpoint. All vector service interfaces are accessed through the search engine or wide table engine entry point.

## Core Principles

| Principle | Description |
|------|------|
| The vector engine is not accessed directly | There is no separate vector port. ES-compatible queries use search engine port `30070`. |
| `es-vector` | Requires the search engine and vector engine. Index creation, writes, build operations, and queries are all performed through the search engine REST API. |
| `sql-vector` | Requires the wide table engine, search engine, and vector engine. Tables and search indexes are created by SQL, and pipelines and queries are managed through the search engine REST API. |
| Dimensions must match | The output dimension of the embedding model must be equal to `knn_vector.dimension`. |
| Offline indexes require building | After enough data is written to IVFPQ / IVFBQ, index building must be triggered and the status must be checked. Before building, the data volume must be `> 256` and `> nlist * 30`. |

## Index Algorithm Selection

| Algorithm | Recommended Data Volume | Build Method | Typical Use |
|------|------------|----------|----------|
| HNSW | Testing, small to medium scale, real-time writes | Online index, no manual build required | Default examples and quick access |
| IVFPQ | Millions of records or more | Offline build | Large-scale, low-cost disk index |
| IVFBQ | Millions of records or more, commonly 512 to 1024 dimensions | Offline build | Large-scale scenarios with high compression ratio |

## Path 1: es-vector

`es-vector` directly uses the Elasticsearch-compatible API of the search engine. The connection endpoint is `http://<search_endpoint>:30070`, and authentication uses HTTP Basic Auth.

### Create an HNSW Index

HNSW is suitable for quick verification and small to medium-scale real-time search.

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/<index_name>?pretty" \
  -d '{
    "settings": {
      "index": {
        "number_of_shards": 2,
        "knn": true
      }
    },
    "mappings": {
      "_source": { "excludes": ["embedding"] },
      "properties": {
        "embedding": {
          "type": "knn_vector",
          "dimension": 1024,
          "data_type": "float",
          "method": {
            "engine": "lvector",
            "name": "hnsw",
            "space_type": "cosinesimil",
            "parameters": {
              "m": 24,
              "ef_construction": 500
            }
          }
        },
        "text_field": { "type": "text", "analyzer": "ik_max_word" },
        "category": { "type": "keyword" },
        "tenant_id": { "type": "keyword" },
        "create_time": { "type": "date", "format": "yyyy-MM-dd HH:mm:ss||strict_date_optional_time" }
      }
    }
  }'
```

### Create an IVFPQ Index

IVFPQ must set the offline build switch. The written data volume must meet the training requirements before the index can be built. Before initiating index build, the number of written records must be greater than `256` and greater than `nlist * 30`.

> **Key constraints, verified on the lindorm_v2 engine**:
> - `nlist`: Number of cluster centers. **The number of written rows must be > 256 and > nlist * 30**. If the data is insufficient, triggering build may return `500: table rows(N) too small...`. The minimum effective nlist on the server side is 256, so IVFPQ is **not suitable for scenarios with fewer than 256 records**.
> - `m`: Number of PQ sub-quantizers. Each sub-quantizer processes `dimension/m` components. **`m` must divide `dimension` exactly**. Common values are 8, 16, 32, and 64. `m = dimension` is a degraded usage, where each sub-quantizer has only 1 dimension. It can work but loses the compression meaning of PQ and is not recommended for production.
> - `centroids_hnsw_*`: Integer parameters used during index creation. They are different from `ext.lvector.ef_search`, which must be a string during queries. Do not confuse them.

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/<index_name>?pretty" \
  -d '{
    "settings": {
      "index": {
        "number_of_shards": 4,
        "knn": true,
        "knn.offline.construction": true
      }
    },
    "mappings": {
      "_source": { "excludes": ["embedding"] },
      "properties": {
        "embedding": {
          "type": "knn_vector",
          "dimension": 1024,
          "data_type": "float",
          "method": {
            "engine": "lvector",
            "name": "ivfpq",
            "space_type": "cosinesimil",
            "parameters": {
              "m": 1024,
              "nlist": 10000,
              "centroids_use_hnsw": true,
              "centroids_hnsw_m": 48,
              "centroids_hnsw_ef_construct": 500,
              "centroids_hnsw_ef_search": 200
            }
          }
        },
        "text_field": { "type": "text", "analyzer": "ik_max_word" },
        "category": { "type": "keyword" }
      }
    }
  }'
```

### Create an IVFBQ Index

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/<index_name>?pretty" \
  -d '{
    "settings": {
      "index": {
        "number_of_shards": 4,
        "knn": true,
        "knn.offline.construction": true
      }
    },
    "mappings": {
      "_source": { "excludes": ["embedding"] },
      "properties": {
        "embedding": {
          "type": "knn_vector",
          "dimension": 1024,
          "data_type": "float",
          "method": {
            "engine": "lvector",
            "name": "ivfbq",
            "space_type": "cosinesimil",
            "parameters": {
              "exbits": 2,
              "nlist": 10000,
              "centroids_use_hnsw": true,
              "centroids_hnsw_m": 48,
              "centroids_hnsw_ef_construct": 500,
              "centroids_hnsw_ef_search": 200
            }
          }
        },
        "text_field": { "type": "text", "analyzer": "ik_max_word" },
        "category": { "type": "keyword" }
      }
    }
  }'
```

### Data Write

Single-document write:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_doc/<doc_id>" \
  -d '{
    "text_field": "sample text",
    "category": "guide",
    "embedding": [0.01, 0.02, 0.03]
  }'
```

Bulk write:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/x-ndjson' \
  -XPOST "http://<search_endpoint>:30070/_bulk" \
  -d '
{"index":{"_index":"<index_name>","_id":"1"}}
{"text_field":"first text","category":"guide","embedding":[0.01,0.02,0.03]}
{"index":{"_index":"<index_name>","_id":"2"}}
{"text_field":"second text","category":"guide","embedding":[0.04,0.05,0.06]}
'
```

You can refresh after writing:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_refresh"
```

### IVFPQ / IVFBQ Index Build

HNSW does not require manual build. After enough data is written to IVFPQ / IVFBQ, trigger index build. Before initiating `_plugins/_vector/index/build`, you must confirm that the written data volume is sufficient: the data volume must be greater than `256` records and greater than `nlist * 30`. It is recommended to trigger index build after offline data import is complete. After index build is complete, you can perform KNN queries and write operations normally.

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/_plugins/_vector/index/build" \
  -d '{
    "indexName": "<index_name>",
    "fieldName": "embedding",
    "removeOldIndex": "true"
  }'
```

View build status:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XGET "http://<search_endpoint>:30070/_plugins/_vector/index/tasks" \
  -d '{
    "indexName": "<index_name>",
    "fieldName": "embedding",
    "taskIds": "[]"
  }'
```

Successful evidence should contain `FINISH` or an equivalent completed status. Failure or timeout must not be treated as an empty result. Report `BLOCKED_INDEX_BUILD` or `FAILED_INDEX_BUILD`.

### KNN Search

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["text_field", "category"],
    "query": {
      "knn": {
        "embedding": {
          "vector": [0.01, 0.02, 0.03],
          "k": 10
        }
      }
    },
    "ext": {
      "lvector": {
        "ef_search": "200"
      }
    }
  }'
```

### KNN + Filter Search

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["text_field", "category", "tenant_id"],
    "query": {
      "knn": {
        "embedding": {
          "vector": [0.01, 0.02, 0.03],
          "k": 10,
          "filter": {
            "bool": {
              "filter": [
                { "term": { "tenant_id": "tenant_a" } },
                { "term": { "category": "guide" } }
              ]
            }
          }
        }
      }
    },
    "ext": {
      "lvector": {
        "filter_type": "efficient_filter",
        "ef_search": "200"
      }
    }
  }'
```

### RRF Full-text + Vector Fusion Search

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["text_field", "category"],
    "query": {
      "knn": {
        "embedding": {
          "vector": [0.01, 0.02, 0.03],
          "filter": {
            "match": {
              "text_field": "vector search"
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

### RRF + Filter Search

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["text_field", "category", "tenant_id"],
    "query": {
      "knn": {
        "embedding": {
          "vector": [0.01, 0.02, 0.03],
          "filter": {
            "bool": {
              "must": [
                { "match": { "text_field": { "query": "vector search" } } }
              ],
              "filter": [
                { "term": { "tenant_id": "tenant_a" } },
                { "term": { "category": "guide" } }
              ]
            }
          },
          "k": 10
        }
      }
    },
    "ext": {
      "lvector": {
        "filter_type": "efficient_filter",
        "hybrid_search_type": "filter_rrf",
        "rrf_rank_constant": "60",
        "rrf_knn_weight_factor": "0.5"
      }
    }
  }'
```

## Path 2: sql-vector

`sql-vector` is suitable for adding vector capabilities to existing wide table businesses. The primary data table is managed by the wide table engine. The search index is created by wide table SQL. Pipelines and search queries are managed through the search engine REST API.

### Create a Table

```sql
CREATE TABLE IF NOT EXISTS test_text_vector (
    document_id VARCHAR,
    chunking_position INT,
    title VARCHAR,
    text VARCHAR,
    vector_field VARCHAR,
    metadata JSON,
    chunking_number INT,
    PRIMARY KEY (document_id, chunking_position)
);
```

### Create a Search Index

```sql
CREATE INDEX IF NOT EXISTS sidx USING SEARCH ON test_text_vector (
    document_id,
    chunking_position(indexed=false, columnStored=false),
    title(type=text, analyzer=ik),
    metadata(indexed=false, columnStored=false),
    chunking_number(indexed=false, columnStored=false),
    text(type=text, analyzer=ik),
    vector_field(mapping='{
        "type": "knn_vector",
        "dimension": 1024,
        "data_type": "float",
        "method": {
            "engine": "lvector",
            "name": "hnsw",
            "space_type": "cosinesimil",
            "parameters": {
                "m": 48,
                "ef_construction": 500
            }
        }
    }')
) WITH (
    INDEX_SETTINGS='{
        "index": {
            "knn": "true",
            "knn.vector_empty_value_to_keep": true,
            "origin.vector_source_only_includes.enabled": true
        }
    }',
    SOURCE_SETTINGS='{
        "excludes": ["vector_field", "update_version_l", "delete_version_l", "_searchindex_id"]
    }'
);
```

If IVFBQ is used, change `method.name` to `ivfbq` and set offline build-related parameters in the vector mapping. After IVFBQ data is written, index build must be triggered.

### Configure Pipeline

After a search index is created for the wide table, a pipeline with the same name is generated, for example `default.test_text_vector.sidx`. You need to create a custom embedding pipeline and add it to the pipeline with the same name.

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/_ingest/pipeline/demo_chunking_embedding_pipeline" \
  -d '{
    "description": "demo embedding pipeline",
    "processors": [
      {
        "text-embedding": {
          "inputFields": ["text"],
          "outputFields": ["vector_field"],
          "userName": "<username>",
          "password": "<password>",
          "url": "http://<ai_vpc_endpoint>:9002/dashscope/compatible-mode/v1/embeddings",
          "modeName": "text-embedding-v4"
        }
      }
    ]
  }'
```

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/_ingest/pipeline/default.test_text_vector.sidx" \
  -d '{
    "processors": [
      { "pipeline": { "name": "_copy_id" } },
      { "pipeline": { "name": "demo_chunking_embedding_pipeline" } }
    ]
  }'
```

Automatic embedding during queries:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/_search/pipeline/search_embedding_pipeline" \
  -d '{
    "request_processors": [
      {
        "text-embedding": {
          "tag": "auto-query-embedding",
          "description": "Auto query embedding",
          "model_config": {
            "inputFields": ["text"],
            "outputFields": ["vector_field"],
            "userName": "<username>",
            "password": "<password>",
            "url": "http://<ai_vpc_endpoint>:9002/dashscope/compatible-mode/v1/embeddings",
            "modeName": "text-embedding-v4"
          }
        }
      }
    ]
  }'
```

Bind the query pipeline:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPUT "http://<search_endpoint>:30070/default.test_text_vector.sidx/_settings" \
  -d '{
    "index": {
      "search.default_pipeline": "search_embedding_pipeline"
    }
  }'
```

### Write Data

```sql
UPSERT INTO test_text_vector
  (document_id, chunking_position, title, text, metadata, chunking_number)
VALUES
  ('doc_001', 0, 'sample document', 'This is the document content...', '{}', 1);
```

After `text` is written, the pipeline automatically generates `vector_field`. If the embedding is not generated, check whether the pipeline is attached to the pipeline with the same name, whether the AI endpoint is an accessible internal network endpoint, and whether the model dimension is consistent with the index.

### Build Index

If the search index of `sql-vector` uses IVFPQ / IVFBQ, the build interface is still called through the search engine. Before initiating `_plugins/_vector/index/build`, you must confirm that the written data volume is sufficient: the data volume must be greater than `256` records and greater than `nlist * 30`. It is recommended to trigger index build after offline data import is complete. After index build is complete, you can perform KNN queries and write operations normally.

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/_plugins/_vector/index/build" \
  -d '{
    "indexName": "default.test_text_vector.sidx",
    "fieldName": "vector_field",
    "removeOldIndex": "true"
  }'
```

### sql-vector Query

Pure KNN:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/default.test_text_vector.sidx/_search?pretty" \
  -d '{
    "size": 10,
    "_source": true,
    "query": {
      "knn": {
        "vector_field": {
          "query_text": "human and nature",
          "k": 10
        }
      }
    },
    "ext": {
      "lvector": {
        "ef_search": "200"
      }
    }
  }'
```

KNN + Filter:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/default.test_text_vector.sidx/_search?pretty" \
  -d '{
    "size": 10,
    "_source": true,
    "query": {
      "knn": {
        "vector_field": {
          "query_text": "human and nature",
          "k": 10,
          "filter": {
            "term": {
              "document_id": "doc_001"
            }
          }
        }
      }
    },
    "ext": {
      "lvector": {
        "filter_type": "efficient_filter",
        "ef_search": "200"
      }
    }
  }'
```

RRF + Filter:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/default.test_text_vector.sidx/_search?pretty" \
  -d '{
    "size": 10,
    "_source": true,
    "query": {
      "knn": {
        "vector_field": {
          "query_text": "human and nature",
          "filter": {
            "bool": {
              "must": [
                { "match": { "text": "human and nature" } }
              ],
              "filter": [
                { "term": { "document_id": "doc_001" } }
              ]
            }
          },
          "k": 10
        }
      }
    },
    "ext": {
      "lvector": {
        "filter_type": "efficient_filter",
        "hybrid_search_type": "filter_rrf",
        "rrf_rank_constant": "60",
        "rrf_knn_weight_factor": "0.5",
        "ef_search": "200"
      }
    }
  }'
```

## `ext` Parameter Logic (Important)

`ext.lvector` is the extension parameter block in Lindorm vector search requests. The content of `ext` follows fixed rules for different search scenarios and **must not be mixed incorrectly**.

### Quick Rule Table

| Search Scenario | Fields in `ext.lvector` | Description |
|----------|------------------------|------|
| **Pure KNN** | `ef_search` | Performs only vector nearest-neighbor search, without filtering or full-text search |
| **KNN + scalar filtering** | `filter_type` + `ef_search` | `filter_type` must be added when scalar filter conditions such as `term` or `range` exist |
| **RRF full-text + vector fusion** | `hybrid_search_type` + `rrf_rank_constant` + `rrf_knn_weight_factor` | RRF is used only when the filter contains `match`, which means full-text search |
| **RRF + scalar filtering** | `filter_type` + `hybrid_search_type` + `rrf_rank_constant` + `rrf_knn_weight_factor` + `ef_search` | Used when both full-text `match` and scalar `term` or `range` filtering exist |

### Field Meanings

| Field | Value | When It Appears |
|------|----|----------|
| `"ef_search"` | `"200"` (string) | Recommended in almost all scenarios. It is the HNSW search accuracy parameter. |
| `"filter_type"` | `"efficient_filter"` | Must be set when **scalar filter conditions** exist, such as `term`, `range`, or `bool.filter`. |
| `"hybrid_search_type"` | `"filter_rrf"` | Must be set for **full-text + vector RRF fusion search**. |
| `"rrf_rank_constant"` | `"60"` (string) | Set only during RRF fusion. It is the constant k in the RRF formula. |
| `"rrf_knn_weight_factor"` | `"0.5"` (string) | Set only during RRF fusion. It is the weight of the vector score in fusion. |
| `"nprobe"` | `"80"` (string) | **IVFPQ / IVFBQ only**: Number of cluster centers probed during query. A larger value improves recall but increases latency. |
| `"reorder_factor"` | `"2"` (string) | **IVFPQ / IVFBQ only**: Candidate multiplier for reranking. Quantized search first retrieves `k * reorder_factor` candidates, then original vectors are used to rerank back to k results. |
| `"client_refactor"` | `"true"` (string) | **IVFPQ / IVFBQ only**: Enables client-side reranking and is used together with `reorder_factor`. |

> **Differences between HNSW and IVFPQ/IVFBQ ext fields**:
> - HNSW index search uses only `ef_search`. **Do not** pass `nprobe`, `reorder_factor`, or `client_refactor`, because these parameters are meaningless for HNSW.
> - IVFPQ / IVFBQ index search **uses `nprobe` instead of `ef_search`**, and can optionally add `reorder_factor` + `client_refactor` to control reranking.
> - The preceding "Quick Rule Table" and following "Decision Logic" use HNSW as the baseline. If the index is IVFPQ/IVFBQ, replace `ef_search` with `nprobe`.

### Decision Logic

```text
In query.knn.<field>.filter:
├── No filter  → ext = { "ef_search": "200" }
├── Only term/range/bool.filter exists, which means scalar filtering
│   → ext = { "filter_type": "efficient_filter", "ef_search": "200" }
├── Only match exists, which means full-text search and triggers RRF
│   → ext = { "hybrid_search_type": "filter_rrf", "rrf_rank_constant": "60", "rrf_knn_weight_factor": "0.5" }
└── Both match and term/range exist, which means full-text + scalar filtering
    → ext = { "filter_type": "efficient_filter", "hybrid_search_type": "filter_rrf", "rrf_rank_constant": "60", "rrf_knn_weight_factor": "0.5", "ef_search": "200" }
```

### Common Mistakes

| Mistake | Consequence | Correct Practice |
|------|------|----------|
| Adding `filter_type` for pure KNN | Does not affect results but is redundant | Remove `filter_type` |
| Having a scalar filter but not adding `filter_type` | Filtering may not take effect or performance may be poor | Add `"filter_type": "efficient_filter"` |
| Adding the three RRF fields for pure full-text matching | Semantic error | Use a pure `match` query directly; knn is not needed |
| Missing `hybrid_search_type` in an RRF scenario | Vector and full-text results are not fused, and only vector results are returned | Add the complete set of RRF fields |
| Writing `rrf_rank_constant` as number `60` | Type error | It must be the string `"60"` |

## Acceptance Evidence

After the vector search workflow is complete, report at least:

```text
[Target] instance=<instance_id> network=<public|vpc>
[Connection] search=<masked_endpoint>:30070 wide_table=<masked_endpoint> ai=<masked_endpoint>:9002
[Vector] path=<es-vector|sql-vector> index=<index_name> field=<vector_field> dimension=<n> algorithm=<hnsw|ivfpq|ivfbq>
[IndexBuild] required=<true|false> status=<FINISH|RUNNING|FAILED|not_required>
[Query] type=<knn|knn_filter|rrf|rrf_filter> top_k=<n> hits=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA|BLOCKED_INDEX_BUILD> reason=<reason>
```
