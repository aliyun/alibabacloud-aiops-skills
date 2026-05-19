# Lindorm Vector Engine Guide

本指南说明 Lindorm 向量检索的两条接入路径：`es-vector` 和 `sql-vector`。向量引擎是 Lindorm 内置引擎，不直接提供独立访问地址；所有向量服务接口都通过搜索引擎或宽表引擎入口完成。

## 核心原则

| 原则 | 说明 |
|------|------|
| 向量引擎不直接访问 | 不存在单独的向量端口；ES 兼容查询走搜索引擎 `30070` |
| `es-vector` | 需要搜索引擎 + 向量引擎；建索引、写入、构建、查询都通过搜索引擎 REST API |
| `sql-vector` | 需要宽表引擎 + 搜索引擎 + 向量引擎；表和搜索索引用 SQL 创建，pipeline 和查询通过搜索引擎 REST API |
| 维度必须一致 | embedding 模型输出维度必须等于 `knn_vector.dimension` |
| 离线索引需要构建 | IVFPQ / IVFBQ 写入足够数据后必须触发构建并检查状态 |

## 索引算法选择

| 算法 | 推荐数据量 | 构建方式 | 典型用途 |
|------|------------|----------|----------|
| HNSW | 测试、小中规模、实时写入 | 在线索引，无需手动构建 | 默认示例、快速接入 |
| IVFPQ | 百万级以上 | 离线构建 | 大规模、低成本磁盘索引 |
| IVFBQ | 百万级以上，512-1024 维常见 | 离线构建 | 大规模、高压缩比场景 |

## 路径一：es-vector

`es-vector` 直接使用搜索引擎 Elasticsearch 兼容 API。连接地址为 `http://<search_endpoint>:30070`，认证为 HTTP Basic Auth。

### 创建 HNSW 索引

HNSW 适合快速验证和小中规模实时检索。

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

### 创建 IVFPQ 索引

IVFPQ 必须设置离线构建开关，且写入数据量需满足训练要求后才能构建。

> **关键约束（实测自 lindorm_v2 引擎）**：
> - `nlist`：聚类中心数。**写入行数必须 > nlist**，否则触发构建会返回 `500: table rows(N) too small, need > nlist(M)`。服务端最小 effective nlist=256，因此 IVFPQ **不适合数据量 < 256 的场景**。
> - `m`：PQ 子量化器数量，每个子量化器负责 `dimension/m` 个分量。**`m` 必须能整除 `dimension`**；常见取值 8/16/32/64。`m = dimension` 是退化用法（每子量化器仅 1 维），可工作但失去 PQ 压缩意义，不推荐生产使用。
> - `centroids_hnsw_*`：建索引时的整数参数，与查询时的 `ext.lvector.ef_search`（必须字符串）不同，不要混淆。

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

### 创建 IVFBQ 索引

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

### 数据写入

单条写入：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_doc/<doc_id>" \
  -d '{
    "text_field": "示例文本",
    "category": "guide",
    "embedding": [0.01, 0.02, 0.03]
  }'
```

批量写入：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/x-ndjson' \
  -XPOST "http://<search_endpoint>:30070/_bulk" \
  -d '
{"index":{"_index":"<index_name>","_id":"1"}}
{"text_field":"第一条文本","category":"guide","embedding":[0.01,0.02,0.03]}
{"index":{"_index":"<index_name>","_id":"2"}}
{"text_field":"第二条文本","category":"guide","embedding":[0.04,0.05,0.06]}
'
```

写入后可刷新：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_refresh"
```

### IVFPQ / IVFBQ 索引构建

HNSW 不需要手动构建。IVFPQ / IVFBQ 写入足量数据后触发构建：

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

查看构建状态：

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

成功证据应包含 `FINISH` 或等价完成状态。失败或超时不能当作空结果处理，应报告 `BLOCKED_INDEX_BUILD` 或 `FAILED_INDEX_BUILD`。

### KNN 检索

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

### KNN + Filter 检索

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

### RRF 全文 + 向量融合检索

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
              "text_field": "向量检索"
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

### RRF + Filter 检索

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
                { "match": { "text_field": { "query": "向量检索" } } }
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

## 路径二：sql-vector

`sql-vector` 适合已有宽表业务接入向量能力。数据主表由宽表引擎管理，搜索索引由宽表 SQL 创建，pipeline 与检索查询通过搜索引擎 REST API 管理。

### 建表

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

### 创建搜索索引

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

若使用 IVFBQ，把 `method.name` 改为 `ivfbq`，并在向量 mapping 中设置离线构建相关参数。IVFBQ 写入后必须触发构建。

### 配置 Pipeline

宽表创建搜索索引后，会生成同名 pipeline，例如 `default.test_text_vector.sidx`。需要创建自定义 embedding pipeline，并把它加入同名 pipeline。

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

查询时自动 embedding：

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

绑定查询 pipeline：

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

### 写入数据

```sql
UPSERT INTO test_text_vector
  (document_id, chunking_position, title, text, metadata, chunking_number)
VALUES
  ('doc_001', 0, '示例文档', '这是文档内容...', '{}', 1);
```

写入 `text` 后，pipeline 自动生成 `vector_field`。如果 embedding 没有生成，检查 pipeline 是否挂到同名 pipeline、AI 地址是否为可访问的内网地址、模型维度是否与索引一致。

### 构建索引

如果 `sql-vector` 的搜索索引使用 IVFPQ / IVFBQ，构建接口仍通过搜索引擎：

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

### sql-vector 查询

纯 KNN：

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
          "query_text": "人与自然",
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

KNN + Filter：

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
          "query_text": "人与自然",
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

RRF + Filter：

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
          "query_text": "人与自然",
          "filter": {
            "bool": {
              "must": [
                { "match": { "text": "人与自然" } }
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

## `ext` 参数逻辑（重要）

`ext.lvector` 是 Lindorm 向量检索请求中的扩展参数块，不同检索场景下 `ext` 的内容有固定规则，**不可混用**。

### 规则速查表

| 检索场景 | `ext.lvector` 中的字段 | 说明 |
|----------|------------------------|------|
| **纯 KNN** | `ef_search` | 只做向量近邻搜索，无过滤、无全文 |
| **KNN + 标量过滤** | `filter_type` + `ef_search` | 有 `term`/`range` 等标量 filter 条件时必须加 `filter_type` |
| **RRF 全文+向量融合** | `hybrid_search_type` + `rrf_rank_constant` + `rrf_knn_weight_factor` | filter 中包含 `match`（全文检索）时才用 RRF |
| **RRF + 标量过滤** | `filter_type` + `hybrid_search_type` + `rrf_rank_constant` + `rrf_knn_weight_factor` + `ef_search` | 同时有全文 `match` 和标量 `term`/`range` 过滤 |

### 各字段含义

| 字段 | 值 | 何时出现 |
|------|----|----------|
| `"ef_search"` | `"200"` (字符串) | 几乎所有场景都建议设置；HNSW 搜索精度参数 |
| `"filter_type"` | `"efficient_filter"` | **有标量过滤条件**（`term` / `range` / `bool.filter`）时必须设置 |
| `"hybrid_search_type"` | `"filter_rrf"` | **全文+向量 RRF 融合检索**时必须设置 |
| `"rrf_rank_constant"` | `"60"` (字符串) | 仅在 RRF 融合时设置；RRF 公式中的常数 k |
| `"rrf_knn_weight_factor"` | `"0.5"` (字符串) | 仅在 RRF 融合时设置；向量得分在融合中的权重 |
| `"nprobe"` | `"80"` (字符串) | **仅 IVFPQ / IVFBQ**：查询时探查的聚类中心数；越大召回越高、延迟越大 |
| `"reorder_factor"` | `"2"` (字符串) | **仅 IVFPQ / IVFBQ**：精排候选倍数，先用量化检索取 `k * reorder_factor`，再用原始向量精排回 k 个 |
| `"client_refactor"` | `"true"` (字符串) | **仅 IVFPQ / IVFBQ**：开启客户端精排，与 `reorder_factor` 配合使用 |

> **HNSW vs IVFPQ/IVFBQ ext 字段差异**：
> - HNSW 索引检索时只用 `ef_search`，**不要**传 `nprobe` / `reorder_factor` / `client_refactor`（这些参数对 HNSW 无意义）。
> - IVFPQ / IVFBQ 索引检索时**用 `nprobe` 替代 `ef_search`**，并按需追加 `reorder_factor` + `client_refactor` 控制精排。
> - 上面"规则速查表"和下面"判断逻辑"以 HNSW 为基准；如果索引是 IVFPQ/IVFBQ，把其中的 `ef_search` 替换为 `nprobe` 即可。

### 判断逻辑

```text
query.knn.<field>.filter 中：
├── 无 filter  → ext = { "ef_search": "200" }
├── 仅有 term/range/bool.filter（标量过滤）
│   → ext = { "filter_type": "efficient_filter", "ef_search": "200" }
├── 仅有 match（全文检索，触发 RRF）
│   → ext = { "hybrid_search_type": "filter_rrf", "rrf_rank_constant": "60", "rrf_knn_weight_factor": "0.5" }
└── 同时有 match + term/range（全文 + 标量）
    → ext = { "filter_type": "efficient_filter", "hybrid_search_type": "filter_rrf", "rrf_rank_constant": "60", "rrf_knn_weight_factor": "0.5", "ef_search": "200" }
```

### 常见错误

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 纯 KNN 时加了 `filter_type` | 不影响但冗余 | 去掉 `filter_type` |
| 有标量 filter 但没加 `filter_type` | 过滤可能不生效或性能差 | 加 `"filter_type": "efficient_filter"` |
| 纯全文匹配却加了 RRF 三件套 | 语义错误 | 纯全文直接用 `match` query 不需要 knn |
| RRF 场景漏了 `hybrid_search_type` | 向量和全文不会融合，只返回向量结果 | 必须加完整 RRF 三件套 |
| 把 `rrf_rank_constant` 写成数字 `60` | 类型错误 | 必须是字符串 `"60"` |

## 验收证据

向量检索流程完成后，至少报告：

```text
[Target] instance=<instance_id> network=<public|vpc>
[Connection] search=<masked_endpoint>:30070 wide_table=<masked_endpoint> ai=<masked_endpoint>:9002
[Vector] path=<es-vector|sql-vector> index=<index_name> field=<vector_field> dimension=<n> algorithm=<hnsw|ivfpq|ivfbq>
[IndexBuild] required=<true|false> status=<FINISH|RUNNING|FAILED|not_required>
[Query] type=<knn|knn_filter|rrf|rrf_filter> top_k=<n> hits=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA|BLOCKED_INDEX_BUILD> reason=<reason>
```
