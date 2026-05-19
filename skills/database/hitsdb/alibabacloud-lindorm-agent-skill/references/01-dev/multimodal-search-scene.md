# Multimodal Image-Text Search Scene

本指南说明如何组合 Lindorm 搜索引擎、向量引擎和 AI 引擎构建多模态图文检索。参考工程思路是：CSV 商品数据入库时，对图片 URL 做 VL 描述和多模态 embedding，将 CSV 字段、图片描述、向量一起写入 Lindorm；查询时支持以图搜图、以文搜图和可选过滤。

## 场景目标

| 能力 | 默认实现 |
|------|----------|
| 实例注册 | 记录实例 ID、region、账号引用、访问入口、网络类型 |
| 存量数据检索 | 先 schema discovery，再按实际字段执行 KNN / RRF |
| 新业务接入 | 从 CSV 推导 schema，默认索引名 `test_index_$date` |
| 以图搜图 | 图片 URL -> 多模态 embedding -> KNN |
| 以文搜图 | 文本 -> 多模态 embedding + 描述全文检索 -> RRF |
| 过滤条件 | 分类、品牌、价格、时间、租户等字段进入 `filter` |

## 实例注册

多模态检索不要假设只有一个实例或一个连接。执行前必须明确以下字段：

| 字段 | 说明 |
|------|------|
| `instance_id` | Lindorm 实例 ID |
| `region` | 实例所在地域 |
| `network` | `public` 或 `vpc` |
| `search_endpoint` | 搜索引擎入口，端口 `30070` |
| `wide_table_endpoint` | 可选，宽表 SQL 入口 |
| `ai_endpoint` | AI 引擎入口，端口 `9002` |
| `username` / `password` | 凭证引用，不在文档或日志中明文展示 |
| `dataset_name` | 业务数据集名称 |
| `index_name` | 搜索索引名称；新建默认 `test_index_$date` |
| `vector_field` | 推荐 `embedding`，存量数据必须从 schema 发现 |
| `text_field` | 推荐 `vl_description` 或存量描述字段 |
| `model_config` | VL、embedding、rerank 模型及向量维度 |

## 存量数据检索

### 1. Schema Discovery

如果用户提供数据集名称但没有提供 schema，必须先调用搜索引擎查看索引结构：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XGET "http://<search_endpoint>:30070/<index_name>?pretty"
```

需要识别：

| 角色 | 推荐字段 | 识别规则 |
|------|----------|----------|
| 图片 URL | `url` / `image_url` / `pic_url` | keyword 或 text 字段，值可访问图片 |
| 图片描述 | `vl_description` / `img_desc` / `description` | text 字段，参与全文/RRF |
| 多模态向量 | `embedding` / `vector` / 自定义字段 | `type=knn_vector`，记录 dimension |
| 过滤字段 | `category` / `brand` / `price` / `create_time` | keyword、numeric、date 等标量字段 |

若存在多个向量字段且无法判断统一多模态向量字段，停止并让用户选择，不能猜测。

### 2. 以图搜图

流程：

```text
query_image_url
-> Lindorm AI multimodal embedding(input=image)
-> KNN on schema-derived vector_field
-> optional filter
-> return image_url + metadata + score
```

检索请求：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["id", "url", "vl_description", "category", "brand"],
    "query": {
      "knn": {
        "<vector_field>": {
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

带过滤：

```json
"filter": {
  "bool": {
    "filter": [
      { "term": { "category": "dress" } },
      { "range": { "price": { "lte": 500 } } }
    ]
  }
}
```

### 3. 以文搜图

默认使用 RRF 融合检索：文本 embedding 负责语义召回，图片描述字段负责全文召回。

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["id", "url", "vl_description", "category", "brand"],
    "query": {
      "knn": {
        "<vector_field>": {
          "vector": [0.01, 0.02, 0.03],
          "filter": {
            "match": {
              "<text_field>": "适合夏天通勤的白色衬衫"
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

可选 rerank：对召回结果中的 `<text_field>` 列表调用 `ai-guide.md` 的 rerank 接口，按 `relevance_score` 重新排序。

## 新业务接入

### 1. CSV 输入约定

CSV 至少需要一列图片 URL。推荐字段：

| 字段 | 说明 |
|------|------|
| `id` | 文档 ID；没有则生成稳定 ID |
| `url` / `pic_url` / `image_url` | 图片 URL |
| `title` | 商品标题 |
| `category` | 分类 |
| `brand` | 品牌 |
| `price` | 价格 |
| `create_time` | 创建时间 |
| 其他字段 | 作为 metadata 或普通可过滤字段写入 |

若未指定数据集名称，使用 `test_index_$date`。实现时 `$date` 使用当天日期，例如 `test_index_20260512`。

### 2. 建索引

默认 HNSW 适合快速接入。字段名推荐：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | keyword | 文档 ID |
| `url` | keyword | 图片 URL |
| `title` | text | 商品标题 |
| `vl_description` | text | VL 生成描述 |
| `embedding` | knn_vector | 多模态向量 |
| `category` / `brand` | keyword | 过滤字段 |
| `price` | double | 过滤字段 |
| `create_time` | date | 过滤字段 |

索引创建参见 `vector-guide.md` 的 HNSW 模板。若数据量超过百万并选择 IVFPQ / IVFBQ，必须在写入后执行索引构建并等待完成。

### 3. 入库处理

每行 CSV 的处理流程：

```text
read csv row
-> normalize id and image url
-> AI VL: image url -> vl_description
-> AI multimodal embedding: image url -> embedding
-> merge csv fields + vl_description + embedding
-> write to Lindorm Search _bulk
-> refresh/count validation
```

要求：

| 检查 | 说明 |
|------|------|
| 图片 URL 可访问 | VL 和 embedding 都依赖服务端访问图片 |
| embedding 维度 | 必须等于索引 `embedding.dimension` |
| 失败处理 | 单行失败要记录行号、ID、错误类型；不能伪造向量 |
| 批量写入 | 推荐 `_bulk`，每批记录数按 payload 大小控制 |
| 完成验证 | `COUNT == CSV 有效行数` 或报告失败行列表 |

### 4. 检索验证

新数据集接入完成后至少验证：

| 验证项 | 成功证据 |
|--------|----------|
| 索引存在 | `GET /<index_name>` 返回 mapping |
| 数据写入 | `_count` 返回有效行数 |
| 以图搜图 | KNN 返回命中，结果包含图片 URL |
| 以文搜图 | RRF 返回命中，结果包含描述字段 |
| 过滤条件 | 带 `category` 或 `brand` 过滤仍可返回或解释为空原因 |

## 输出格式

```text
[Target] instance=<instance_id> region=<region> network=<public|vpc>
[Dataset] dataset=<dataset_name> index=<index_name> mode=<existing|new_csv>
[Schema] vector_field=<field> dimension=<n> text_field=<field> image_url_field=<field>
[Import] rows=<n> succeeded=<n> failed=<n>
[Search] image_knn_hits=<n> text_rrf_hits=<n> filter_hits=<n>
[Evidence] count=<n> sample_id=<id> sample_score=<score>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA|BLOCKED_MODEL> reason=<reason>
```
