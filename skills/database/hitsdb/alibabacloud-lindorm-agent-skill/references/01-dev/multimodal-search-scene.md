# Multimodal Image-Text Search Scene

This guide describes how to combine the Lindorm search engine, vector engine, and AI engine to build multimodal image-text retrieval. The reference workflow is: when CSV product data is imported, generate a VL description and a multimodal embedding for each image URL, write the CSV fields, image description, and vector into Lindorm, and then support image-to-image search, text-to-image search, and optional filters at query time.

## Scenario Goals

| Capability | Default implementation |
|------------|------------------------|
| Instance registration | Record instance ID, region, account reference, access endpoint, and network type |
| Existing data retrieval | Perform schema discovery first, then run KNN / RRF according to the actual fields |
| New business onboarding | Infer the schema from CSV and use `test_index_$date` as the default index name |
| Image-to-image search | Image URL -> multimodal embedding -> KNN |
| Text-to-image search | Text -> multimodal embedding plus description full-text retrieval -> RRF |
| Filters | Put category, brand, price, time, tenant, and other fields into `filter` |

## Instance Registration

Do not assume that multimodal retrieval has only one instance or one connection. Before execution, clearly identify the following fields:

| Field | Description |
|-------|-------------|
| `instance_id` | Lindorm instance ID |
| `region` | Region where the instance resides |
| `network` | `public` or `vpc` |
| `search_endpoint` | Search engine endpoint, port `30070` |
| `wide_table_endpoint` | Optional wide table SQL endpoint |
| `ai_endpoint` | AI engine endpoint, port `9002` |
| `username` / `password` | Credential reference. Do not display plaintext values in documents or logs |
| `dataset_name` | Business dataset name |
| `index_name` | Search index name. The default for a new index is `test_index_$date` |
| `vector_field` | Recommended value is `embedding`. For existing data, derive it from schema discovery |
| `text_field` | Recommended value is `vl_description`, or use the existing description field |
| `model_config` | VL model, embedding model, rerank model, and vector dimension |

## Existing Data Retrieval

### 1. Schema Discovery

If the user provides a dataset name but no schema, first call the search engine to inspect the index structure:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XGET "http://<search_endpoint>:30070/<index_name>?pretty"
```

Identify the following roles:

| Role | Recommended fields | Identification rule |
|------|--------------------|---------------------|
| Image URL | `url` / `image_url` / `pic_url` | A keyword or text field whose value is an accessible image URL |
| Image description | `vl_description` / `img_desc` / `description` | A text field used for full-text retrieval or RRF |
| Multimodal vector | `embedding` / `vector` / custom field | `type=knn_vector`; record its dimension |
| Filter fields | `category` / `brand` / `price` / `create_time` | Scalar fields such as keyword, numeric, or date |

If multiple vector fields exist and the unified multimodal vector field cannot be determined, stop and ask the user to choose. Do not guess.

### 2. Image-to-image Search

Flow:

```text
query_image_url
-> Lindorm AI multimodal embedding(input=image)
-> KNN on schema-derived vector_field
-> optional filter
-> return image_url + metadata + score
```

Retrieval request:

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

With filters:

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

### 3. Text-to-image Search

Use RRF hybrid retrieval by default: text embedding handles semantic recall, and the image description field handles full-text recall.

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
              "<text_field>": "white shirt suitable for summer commuting"
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

Optional rerank: call the rerank API in `ai-guide.md` for the `<text_field>` list in the recalled results, and sort again by `relevance_score`.

## New Business Onboarding

### 1. CSV Input Convention

The CSV must contain at least one image URL column. Recommended fields:

| Field | Description |
|-------|-------------|
| `id` | Document ID. Generate a stable ID if this field is absent |
| `url` / `pic_url` / `image_url` | Image URL |
| `title` | Product title |
| `category` | Category |
| `brand` | Brand |
| `price` | Price |
| `create_time` | Creation time |
| Other fields | Write as metadata or normal filterable fields |

If no dataset name is specified, use `test_index_$date`. In implementation, `$date` should use the current date, for example `test_index_20260512`.

### 2. Index Creation

HNSW is suitable for quick onboarding by default. Recommended field names:

| Field | Type | Description |
|-------|------|-------------|
| `id` | keyword | Document ID |
| `url` | keyword | Image URL |
| `title` | text | Product title |
| `vl_description` | text | Description generated by VL |
| `embedding` | knn_vector | Multimodal vector |
| `category` / `brand` | keyword | Filter fields |
| `price` | double | Filter field |
| `create_time` | date | Filter field |

For index creation, see the HNSW template in `vector-guide.md`. If the data volume exceeds one million records and IVFPQ / IVFBQ is selected, build the index after writing data and wait until the build is complete.

### 3. Data Ingestion

Processing flow for each CSV row:

```text
read csv row
-> normalize id and image url
-> AI VL: image url -> vl_description
-> AI multimodal embedding: image url -> embedding
-> merge csv fields + vl_description + embedding
-> write to Lindorm Search _bulk
-> refresh/count validation
```

Requirements:

| Check | Description |
|-------|-------------|
| Image URL accessibility | Both VL and embedding depend on server-side access to the image |
| Embedding dimension | Must equal the index `embedding.dimension` |
| Failure handling | Record row number, ID, and error type for failed rows. Do not fabricate vectors |
| Bulk write | Use `_bulk`; control the batch size according to payload size |
| Completion validation | `COUNT == valid CSV rows`, or report the failed row list |

### 4. Retrieval Validation

After a new dataset is onboarded, validate at least the following items:

| Validation item | Success evidence |
|-----------------|------------------|
| Index exists | `GET /<index_name>` returns the mapping |
| Data written | `_count` returns the number of valid rows |
| Image-to-image search | KNN returns hits, and the result contains image URLs |
| Text-to-image search | RRF returns hits, and the result contains the description field |
| Filters | Queries with `category` or `brand` filters still return results, or clearly explain why the result is empty |

## Output Format

```text
[Target] instance=<instance_id> region=<region> network=<public|vpc>
[Dataset] dataset=<dataset_name> index=<index_name> mode=<existing|new_csv>
[Schema] vector_field=<field> dimension=<n> text_field=<field> image_url_field=<field>
[Import] rows=<n> succeeded=<n> failed=<n>
[Search] image_knn_hits=<n> text_rrf_hits=<n> filter_hits=<n>
[Evidence] count=<n> sample_id=<id> sample_score=<score>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA|BLOCKED_MODEL> reason=<reason>
```
