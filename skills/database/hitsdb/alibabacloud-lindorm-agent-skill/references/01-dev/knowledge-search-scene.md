# Knowledge Base Search Scene

本指南说明如何利用 Lindorm 搜索引擎、向量引擎和 AI 引擎构建私域知识库问答。默认路径是：上传 txt 或 CMRC 类 JSON 文档，切分为 chunk，对 chunk 文本做 embedding，写入 Lindorm，构建向量索引，通过 KNN/RRF 召回上下文，可选 rerank，再调用 Chat 模型生成答案。

## 场景目标

| 阶段 | 能力 |
|------|------|
| 数据导入 | 支持 txt 文档和 CMRC 类 JSON 数据 |
| 数据建模 | 父文档保存原文，chunk 索引保存切分文本和向量 |
| 向量化 | 通过 Lindorm AI embedding 模型生成向量 |
| 入库 | 搜索引擎 `_bulk` 或宽表 `UPSERT` |
| 索引构建 | IVFPQ / IVFBQ 显式构建并检查状态 |
| 问答检索 | KNN/RRF 召回，rerank 重排，Chat 基于上下文回答 |

## 推荐数据模型

### 搜索引擎直连模式

父文档索引 `<dataset_name>_parent`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `document_id` | keyword | 文档 ID |
| `title` | text | 标题 |
| `context` | text | 原始全文，可不参与索引 |
| `metadata` | object | 来源、文件名、业务标签 |

chunk 索引 `<dataset_name>_chunking`：

| 字段 | 类型 | 说明 |
|------|------|------|
| `document_id` | keyword | 父文档 ID |
| `chunking_position` | integer | 切分位置 |
| `chunking_number` | integer | 总 chunk 编号或序号 |
| `text_field` | text | chunk 文本 |
| `vector_field` | knn_vector | chunk embedding |
| `metadata` | object | 来源信息 |

### 宽表入口模式

宽表模式先创建表，再用 `CREATE INDEX ... USING SEARCH` 建搜索索引，pipeline 自动把 `text` 写入 `vector_field`。具体 DDL 和 pipeline 模板见 `vector-guide.md` 的 `sql-vector` 部分。

## 文档切分

### txt 文档

处理流程：

```text
read txt
-> normalize whitespace
-> split by paragraph / sentence
-> merge to chunk_size
-> keep overlap
-> assign document_id + chunking_position
```

推荐默认值：

| 参数 | 默认值 |
|------|--------|
| `chunk_size` | 500-800 中文字符 |
| `chunk_overlap` | 50-100 中文字符 |
| `min_chunk_size` | 50 中文字符 |
| `document_id` | 文件名 hash 或用户指定 ID |

### CMRC 类 JSON

CMRC 数据通常包含篇章、问题和答案。用于知识库构建时，优先把篇章 `context` 作为父文档，把切分后的上下文写入 chunk 索引；问题答案可作为 metadata 或验证集，不直接替代原文。

## 建索引

知识库可以用 HNSW 快速验证，也可以用 IVFPQ / IVFBQ 做大规模低成本检索。参考工程使用离线索引时，写入后需要显式构建。

IVFBQ chunk 索引示例：

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

父文档索引可以不包含向量字段：

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

## 向量化与入库

每个 chunk 调用 AI embedding：

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

写入 chunk：

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

入库后验证：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<dataset_name>_chunking/_count" \
  -d '{
    "query": { "match_all": {} }
  }'
```

## 构建 IVFPQ / IVFBQ 索引

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

只有状态完成后才能把大规模离线索引流程标记为成功。

## 知识库检索

### KNN 召回

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

### RRF 召回

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
              "text_field": "问题文本"
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

### Rerank 与上下文组装

对召回到的 `text_field` 列表调用 `ai-guide.md` 的 rerank 接口。随后按分数选择 top chunks，拼接上下文：

```text
已知信息：
1. <chunk_1_text>
2. <chunk_2_text>
3. <chunk_3_text>

请根据上述已知信息回答用户问题。如果无法从中得到答案，请回答“根据已知信息无法回答该问题”，不要编造。
问题：<question>
```

### 问答生成

使用 `ai-guide.md` 的 Chat 接口。回答必须附带召回证据：

| 输出项 | 说明 |
|--------|------|
| `answer` | 基于召回上下文的答案 |
| `citations` | `document_id`、`chunking_position`、score |
| `retrieval_mode` | `knn` / `rrf` / `rrf+rerank` |
| `blocked_status` | 网络、鉴权、schema、索引构建阻塞 |

## 验收证据

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
