# Lindorm Search Engine Guide

This guide describes how to use the Lindorm search engine independently. The search engine exposes an Elasticsearch-compatible access endpoint on the fixed port `30070`. It is used for full-text search, filtered search, index inspection, count statistics, and also serves as the main entry point for vector retrieval.

## Applicable Scenarios

| User intent | Handling method |
|-------------|-----------------|
| Check whether the search engine is reachable | Confirm that LindormSearch is enabled for the instance, then probe port `30070` |
| View an existing index schema | Call `GET /<index_name>` and read `mappings.properties` |
| Count documents in an index | Call `POST /<index_name>/_count` |
| Full-text search | Use `match` / `multi_match` to query text fields |
| Filtered search | Use `term` / `range` / `bool.filter` to query structured fields |
| Vector retrieval | Route to `vector-guide.md`; calls still go through the search engine on port `30070` |

## Connection and Connectivity

The search engine endpoint comes from the instance engine list or the Database Connection page in the console. Public endpoints usually contain `-proxy-search-pub`; private endpoints usually contain `-proxy-search-vpc`.

| Network type | Endpoint example | Applicable environment |
|--------------|------------------|-------------------------|
| VPC private network | `<instance_id>-proxy-search-vpc.lindorm.aliyuncs.com:30070` | ECS, containers, and services inside the VPC |
| Public network | `<instance_id>-proxy-search-pub.lindorm.aliyuncs.com:30070` | Local computers or public-network clients |

Before public-network access, complete the whitelist check: obtain the client public IP, query the instance whitelist, and append the IP to the `default` group if it is not already included. Do not overwrite existing whitelist entries. For CLI commands and console paths, see `references/01-dev/connection-guide.md` and `references/02-ops/connection-troubleshoot.md`.

### Port 30070 probe

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -XGET "http://<search_endpoint>:30070/"
```

A successful response usually returns cluster or service metadata. If the request times out, distinguish the following cases first:

| Symptom | Possible cause | Handling |
|---------|----------------|----------|
| DNS resolution failure | Incorrect endpoint or public endpoint not enabled | Retrieve the search engine endpoint again |
| connect timeout | Public whitelist does not allow the client, or a VPC endpoint is used from outside the VPC | Check the whitelist and network type |
| `401` / `403` | Incorrect username or password | Use the Lindorm account and password of the current instance |
| `404` | Incorrect access path | Access `/` or `/<index_name>` first |

## Basic ES Usage

The following examples all use the search engine entry point `http://<search_endpoint>:30070` and HTTP Basic Auth. Do not write real passwords to documents, logs, or eval output.

### View index schema

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XGET "http://<search_endpoint>:30070/<index_name>?pretty"
```

Key information to extract:

| Field | Purpose |
|-------|---------|
| `settings.index.number_of_shards` | Determine shard and resource configuration |
| `mappings.properties` | Determine field types, full-text fields, keyword fields, and vector fields |
| `knn_vector.dimension` | Verify model dimension before vector retrieval |
| `method.name` / `method.engine` | Identify index algorithms such as HNSW, IVFPQ, and IVFBQ |

### Count documents

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_count" \
  -d '{
    "query": { "match_all": {} }
  }'
```

Count with filters:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_count" \
  -d '{
    "query": {
      "bool": {
        "filter": [
          { "term": { "category": "phone" } },
          { "range": { "price": { "gte": 1000 } } }
        ]
      }
    }
  }'
```

### Full-text search

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["id", "title", "content", "category"],
    "query": {
      "match": {
        "content": "vector retrieval"
      }
    }
  }'
```

Search multiple fields:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": true,
    "query": {
      "multi_match": {
        "query": "wireless earphones noise cancellation",
        "fields": ["title^2", "description"]
      }
    }
  }'
```

### Filtered search

Put structured filters in `bool.filter`. Filter conditions do not affect relevance scoring and are suitable for fields such as category, tenant, time, and price.

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_search?pretty" \
  -d '{
    "size": 10,
    "_source": ["id", "title", "category", "price", "create_time"],
    "query": {
      "bool": {
        "must": [
          { "match": { "description": "lightweight laptop" } }
        ],
        "filter": [
          { "term": { "category": "computer" } },
          { "range": { "price": { "lte": 8000 } } },
          { "range": { "create_time": { "gte": "2026-01-01 00:00:00" } } }
        ]
      }
    }
  }'
```

## Write and Refresh

Write a single document:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_doc/<doc_id>" \
  -d '{
    "title": "Lindorm Search",
    "content": "The search engine supports full-text search and filtered search",
    "category": "guide"
  }'
```

Refresh the index to make writes immediately visible:

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_refresh"
```

## Evidence Output Format

When the agent reports search engine operation results, provide auditable evidence:

```text
[Target] instance=<instance_id> region=<region> network=<public|vpc>
[Connection] engine=search endpoint=<masked_search_endpoint>:30070
[Index] name=<index_name> schema_status=<ok|blocked|failed>
[Action] type=<connectivity|get_index|count|fulltext|filter>
[Evidence] http_status=<status> count=<n> hits=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA> reason=<reason>
```

Do not output passwords, access keys, or complete sensitive connection strings in the final answer.
