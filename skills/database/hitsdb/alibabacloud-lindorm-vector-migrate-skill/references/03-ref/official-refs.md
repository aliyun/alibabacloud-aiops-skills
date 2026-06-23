# Official Documentation References

Official documentation links for each product. The Agent can refer to these when unsure about API details.

## Lindorm Search Engine

> Alibaba Cloud documentation center: https://help.aliyun.com/zh/lindorm/
>
> Lindorm product llms.txt index: https://help.aliyun.com/zh/lindorm/llms.txt

| Document | Link |
|----------|------|
| Access vector engine via curl | https://help.aliyun.com/zh/lindorm/user-guide/accessing-the-vector-engine-through-curl |
| Connect to search engine with curl | https://help.aliyun.com/zh/lindorm/user-guide/connect-and-use-the-search-engine-with-the-curl-command |
| Full-text vector hybrid retrieval | https://help.aliyun.com/zh/lindorm/user-guide/full-text-vector-hybrid-retrieval |
| Auto embedding for write and search | https://help.aliyun.com/zh/lindorm/user-guide/searching-for-embedded-text |
| Custom routing keys | https://help.aliyun.com/zh/lindorm/user-guide/custom-routing-keys |
| Scalar pushdown accelerated vector-scalar hybrid retrieval | https://help.aliyun.com/zh/lindorm/user-guide/scalar-attribute-pushdown-accelerated-vector-scalar-query-hybrid-retrieval |
| Enable search engine | https://help.aliyun.com/zh/lindorm/user-guide/activation-guide-elasticsearch-compatible-version |
| Enable search index | https://help.aliyun.com/zh/lindorm/user-guide/enable-the-search-index-feature |
| Manage search index | https://help.aliyun.com/zh/lindorm/user-guide/manage-search-index |
| Vector search (knn_vector) | https://help.aliyun.com/zh/lindorm/user-guide/vector-search |
| Search engine vector retrieval setup | https://help.aliyun.com/zh/lindorm/user-guide/vector-retrieval |
| Search engine SQL (JDBC) | https://help.aliyun.com/zh/lindorm/user-guide/use-sql-to-connect-to-and-use-lindormsearch |
| Search SQL UPSERT (bulk write) | https://help.aliyun.com/zh/lindorm/user-guide/ddl-upsert |
| Build full data index | https://help.aliyun.com/zh/lindorm/user-guide/build-indexes-to-complete-full-data-synchronization |
| Python opensearch-py vector engine | https://help.aliyun.com/zh/lindorm/user-guide/accessing-the-vector-engine-through-python-opensearchpy |
| Search engine user and permission management | https://help.aliyun.com/zh/lindorm/user-guide/user-management |
| Search engine release notes | https://help.aliyun.com/zh/lindorm/product-overview/release-notes-of-lindormsearch |

## Elasticsearch

> Official documentation: https://www.elastic.co/docs/reference/elasticsearch

| Document | Link |
|----------|------|
| Bulk API | https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-bulk |
| Point in Time API | https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-open-point-in-time |
| search_after / Pagination | https://www.elastic.co/docs/reference/elasticsearch/rest-apis/paginate-search-results |
| dense_vector field type | https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/dense-vector |
| Mapping overview | https://www.elastic.co/docs/manage-data/data-store/mapping |
| Indices API (create/delete index) | https://www.elastic.co/docs/api/doc/elasticsearch/group/endpoint-indices |
| Search API | https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search |
| Python Client (elasticsearch-py) | https://elasticsearch-py.readthedocs.io/en/stable/helpers.html |

## Milvus / Zilliz

> Official documentation: https://milvus.io/docs
>
> Milvus documentation requires the `.md` extension; URLs without the extension return 404.

| Document | Link |
|----------|------|
| Query Iterator | https://milvus.io/docs/with-iterators.md |
| Primary key search | https://milvus.io/docs/primary-key-search.md |
| Scalar query | https://milvus.io/docs/get-and-scalar-query.md |
| Vector search | https://milvus.io/docs/single-vector-search.md |
| Data import | https://milvus.io/docs/import-data.md |
| Connect to Milvus | https://milvus.io/docs/connect-to-milvus-server.md |
| Schema design | https://milvus.io/docs/schema.md |
| Dynamic Field | https://milvus.io/docs/enable-dynamic-field.md |
| Index type overview | https://milvus.io/docs/index-explained.md |
| Vector index management | https://milvus.io/docs/index-vector-fields.md |
| Distance metrics (Metric Type) | https://milvus.io/docs/metric.md |
| Collection management | https://milvus.io/docs/manage-collections.md |
| PyMilvus SDK | https://github.com/milvus-io/pymilvus |
| Zilliz Cloud documentation | https://docs.zilliz.com/docs/quick-start |

## Qdrant

> Official documentation: https://qdrant.tech/documentation/
>
> Qdrant has migrated `/documentation/concepts/` paths to a new structure (`manage-data/`, `search/`, etc.); old URLs redirect via meta refresh.

| Document | Link |
|----------|------|
| Quick start | https://qdrant.tech/documentation/quickstart/ |
| Points API (upsert/get/delete/scroll) | https://qdrant.tech/documentation/manage-data/points/ |
| Collections | https://qdrant.tech/documentation/manage-data/collections/ |
| Distance metrics | https://qdrant.tech/documentation/manage-data/collections/#distance-metrics |
| Payload Schema (type inference) | https://qdrant.tech/documentation/manage-data/payload/ |
| Vector search | https://qdrant.tech/documentation/search/search/ |
| Bulk upload | https://qdrant.tech/documentation/tutorials-develop/bulk-upload/ |
| REST API reference (OpenAPI) | https://api.qdrant.tech/ |
| API & SDKs | https://qdrant.tech/documentation/interfaces/ |
| Python Client (GitHub) | https://github.com/qdrant/qdrant-client |

## Alibaba Cloud OSS

> Official documentation: https://help.aliyun.com/zh/oss/
>
> Note: This section only retains documentation related to reading CSV/files from OSS as a migration source (Python SDK V1).

| Document | Link |
|----------|------|
| Python SDK V1 overview and initialization | https://help.aliyun.com/zh/oss/developer-reference/python-sdk-v1/ |
| Streaming download (get_object) | https://help.aliyun.com/zh/oss/developer-reference/streaming-download-1 |
| Download to local file | https://help.aliyun.com/zh/oss/developer-reference/download-objects-as-files-1 |
| List objects (list_objects) | https://help.aliyun.com/zh/oss/developer-reference/list-objects-by-python-sdk-v1 |
| OSS Python SDK GitHub | https://github.com/aliyun/aliyun-oss-python-sdk |
