# Lindorm Search Engine Guide

本指南说明 Lindorm 搜索引擎的独立用法。搜索引擎通过 Elasticsearch 兼容协议提供访问入口，固定端口为 `30070`，用于全文检索、过滤检索、索引信息查看、计数统计，也作为向量检索的主要入口。

## 适用场景

| 用户意图 | 处理方式 |
|----------|----------|
| 检查搜索引擎是否可访问 | 先确认实例已开通 LindormSearch，再探测 `30070` |
| 查看已有索引结构 | 调用 `GET /<index_name>`，读取 `mappings.properties` |
| 统计索引数据量 | 调用 `POST /<index_name>/_count` |
| 全文检索 | 使用 `match` / `multi_match` 查询文本字段 |
| 过滤检索 | 使用 `term` / `range` / `bool.filter` 查询结构化字段 |
| 向量检索 | 路由到 `vector-guide.md`，仍通过搜索引擎 `30070` 调用 |

## 连接与连通性

搜索引擎连接地址来自实例的引擎列表或控制台数据库连接页面。公网地址通常包含 `-proxy-search-pub`，私网地址通常包含 `-proxy-search-vpc`。

| 网络类型 | 地址示例 | 适用环境 |
|----------|----------|----------|
| VPC 私网 | `<instance_id>-proxy-search-vpc.lindorm.aliyuncs.com:30070` | ECS、容器、VPC 内服务 |
| Public 公网 | `<instance_id>-proxy-search-pub.lindorm.aliyuncs.com:30070` | 本地电脑或公网客户端 |

公网访问前必须完成白名单检查：获取客户端公网 IP，查询实例白名单，如不在白名单中则追加到 `default` 分组，不能覆盖已有白名单。CLI 命令和控制台路径见 `references/01-dev/connection-guide.md` 与 `references/02-ops/connection-troubleshoot.md`。

### 30070 端口探测

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -XGET "http://<search_endpoint>:30070/"
```

成功时通常返回集群或服务元信息。若超时，先区分：

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| DNS 解析失败 | endpoint 填错或公网未开通 | 重新获取搜索引擎连接地址 |
| connect timeout | 公网白名单未放行或使用了 VPC 地址 | 检查白名单和网络类型 |
| `401` / `403` | 用户名或密码错误 | 使用当前实例的 Lindorm 账号密码 |
| `404` | 访问路径错误 | 先访问 `/` 或 `/<index_name>` |

## 基本 ES 用法

以下示例均使用搜索引擎入口 `http://<search_endpoint>:30070`，认证方式为 HTTP Basic Auth。不要把真实密码写入文档、日志或 eval 输出。

### 查看索引结构

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XGET "http://<search_endpoint>:30070/<index_name>?pretty"
```

需要提取的关键信息：

| 字段 | 用途 |
|------|------|
| `settings.index.number_of_shards` | 判断分片与资源配置 |
| `mappings.properties` | 判断字段类型、全文字段、keyword 字段、向量字段 |
| `knn_vector.dimension` | 向量检索前验证模型维度 |
| `method.name` / `method.engine` | 判断 HNSW、IVFPQ、IVFBQ 等索引算法 |

### 统计文档数量

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_count" \
  -d '{
    "query": { "match_all": {} }
  }'
```

带过滤条件统计：

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

### 全文检索

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
        "content": "向量检索"
      }
    }
  }'
```

多个字段检索：

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
        "query": "无线耳机 降噪",
        "fields": ["title^2", "description"]
      }
    }
  }'
```

### 过滤检索

结构化过滤推荐放在 `bool.filter`，过滤条件不参与相关性评分，适合分类、租户、时间、价格等字段。

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
          { "match": { "description": "轻薄 笔记本" } }
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

## 写入和刷新

单条写入：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -H 'Content-Type: application/json' \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_doc/<doc_id>" \
  -d '{
    "title": "Lindorm Search",
    "content": "搜索引擎支持全文检索和过滤检索",
    "category": "guide"
  }'
```

刷新索引使写入立即可见：

```bash
curl --connect-timeout 10 -m 60 \
  -u <username>:<password> \
  -XPOST "http://<search_endpoint>:30070/<index_name>/_refresh"
```

## 输出证据格式

Agent 回答搜索引擎操作结果时，应给出可审计证据：

```text
[Target] instance=<instance_id> region=<region> network=<public|vpc>
[Connection] engine=search endpoint=<masked_search_endpoint>:30070
[Index] name=<index_name> schema_status=<ok|blocked|failed>
[Action] type=<connectivity|get_index|count|fulltext|filter>
[Evidence] http_status=<status> count=<n> hits=<n>
[Blocked] status=<BLOCKED_NETWORK|BLOCKED_AUTH|BLOCKED_SCHEMA> reason=<reason>
```

不要把密码、访问密钥或完整敏感连接串输出到最终答案。
