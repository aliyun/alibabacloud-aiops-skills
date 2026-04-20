# 快速开始场景

当用户询问"怎么建表"、"怎么写入数据"、"怎么查询数据"等开发入门问题时，按本指南执行。

## 触发条件

用户的典型表达：
- "怎么建表？"
- "怎么写入数据？"
- "给我一个完整的示例"
- "宽表引擎怎么用？"
- "时序数据怎么存储？"

## 核心原则

**Agent 主动做重活**，而不是让用户自己探索：
1. **Agent 提取完整代码示例**，直接给用户可执行的代码
2. 只在必要时附上文档链接作为"了解更多"的补充
3. **目标**：用户拿到代码后可以直接运行，无需再自己查文档

---

## 执行流程

### 步骤 1：确认引擎类型

先询问用户使用哪个引擎（如果未明确）：

```
您想使用哪个引擎？

1. 宽表引擎（适合半结构化数据，兼容 HBase）
2. 时序引擎（适合 IoT、监控等时序数据）
3. 搜索引擎（适合全文检索）

或者告诉我您的使用场景，我来推荐引擎。
```

---

### 步骤 2：Agent 查询官方文档并生成完整示例

**⚠️ 强制要求**：在提供任何代码示例之前，**必须**从 Skill references 文档获取信息，Skill 未覆盖时查询官方文档确认。

**Agent 需要做的**：根据引擎类型，访问阿里云 Lindorm 官方文档获取最新示例

**查询目标**：
- 官方文档：https://help.aliyun.com/zh/lindorm/
- 关键信息：建表、写入、查询的完整代码示例

**必须从官方文档中提取并验证**：
- ✅ 最新的 Maven 依赖版本（不是训练数据中的旧版本）
- ✅ 正确的 API 调用方式（如 Connection vs HConnection）
- ✅ 当前推荐的建表语句格式
- ✅ 官方验证过的写入/查询代码
- ✅ 最佳实践和性能优化建议

**验证清单**：
```
在提供代码之前，Agent 必须确认：
□ 已访问官方文档获取最新示例
□ SDK 版本号是最新的（如 alilindorm-table-sdk 2.x）
□ API 调用方式是当前推荐的（不是已废弃的 API）
□ 建表/写入/查询代码经过官方验证
□ 已附上官方文档链接供用户深入学习
```

**然后整理成完整可执行的代码，直接给用户**。

---

## 按引擎类型生成完整示例

### 场景 A：宽表引擎快速开始

**Agent 执行查询后，直接给用户完整答案**：

```
【宽表引擎完整示例】

我已为您准备好从连接到查询的完整代码（基于官方文档最新版本）：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 1：添加 Maven 依赖】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<!-- MySQL 协议 JDBC（推荐） -->
<dependencies>
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
        <version>8.3.0</version>
    </dependency>
</dependencies>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 2：连接实例】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import java.sql.*;
import java.util.Properties;

public class LindormQuickStart {
    public static void main(String[] args) throws Exception {
        // 1. 配置连接（MySQL 协议，推荐）
        // Agent 根据实例 ServiceType 选择正确的域名格式，参见 sql-client-guide.md
        Class.forName("com.mysql.cj.jdbc.Driver");
        String url = "jdbc:mysql://<您的连接地址>:33060/default?sslMode=disabled";
        Properties props = new Properties();
        props.setProperty("user", "your-username");
        props.setProperty("password", "your-password");
        Connection conn = DriverManager.getConnection(url, props);
        Statement stmt = conn.createStatement();

        // 2. 建表
        stmt.execute("CREATE TABLE IF NOT EXISTS users (" +
            "id VARCHAR PRIMARY KEY," +
            "name VARCHAR," +
            "age INT," +
            "city VARCHAR)");
        System.out.println("表创建成功");

        // 3. 写入数据
        stmt.execute("INSERT INTO users (id, name, age, city) VALUES " +
            "('1', 'Alice', 25, 'Shanghai'), " +
            "('2', 'Bob', 30, 'Beijing')");
        System.out.println("数据写入成功");

        // 4. 查询数据
        ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE age > 20");
        while (rs.next()) {
            System.out.println("name=" + rs.getString("name") + ", age=" + rs.getInt("age"));
        }

        // 5. 关闭连接
        rs.close();
        stmt.close();
        conn.close();
    }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【批量写入优化】（生产环境推荐）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

// 批量写入（使用 PreparedStatement）
String sql = "INSERT INTO users (id, name, age, city) VALUES (?, ?, ?, ?)";
PreparedStatement pstmt = conn.prepareStatement(sql);
for (int i = 0; i < 10000; i++) {
    pstmt.setString(1, "id_" + i);
    pstmt.setString(2, "user_" + i);
    pstmt.setInt(3, 20 + i % 50);
    pstmt.setString(4, "city_" + i % 10);
    pstmt.addBatch();
    if (i % 1000 == 0) {
        pstmt.executeBatch();  // 每 1000 行提交一次
    }
}
pstmt.executeBatch();  // 提交剩余数据

【完整文档】如需了解更多（二级索引、全局索引、性能优化）：
https://help.aliyun.com/zh/lindorm/user-guide/lindorm-wide-table-engine
```

---

### 场景 B：时序引擎快速开始

**Agent 从官方文档提取最新示例**：

> **推荐连接方式**：官方推荐使用 [JDBC Driver](https://help.aliyun.com/zh/lindorm/user-guide/use-the-jdbc-driver-for-lindorm-to-connect-to-and-use-lindormtsdb)（支持 Java）。以下示例采用 HTTP SQL API（轻量级，适合 Python 等非 Java 语言快速验证）。

参考文档：https://help.aliyun.com/zh/lindorm/user-guide/http-sql-api-user-guide

**然后直接给用户完整代码**：

```
【时序引擎完整示例】（Python HTTP SQL API）

我已为您准备好时序数据写入和查询的完整代码：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 1：安装依赖】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pip install requests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 2：完整示例代码】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import requests
import time

# 1. 连接配置
host = "您的时序引擎连接地址"  # 从控制台"数据库连接"页面获取
port = 8242
url = f"http://{host}:{port}/api/v2/sql"

# 2. 建表
create_sql = """CREATE TABLE IF NOT EXISTS sensor (
  device_id VARCHAR NOT NULL,
  region VARCHAR NOT NULL,
  time TIMESTAMP NOT NULL,
  temperature DOUBLE,
  humidity BIGINT,
  PRIMARY KEY(device_id, region, time)
)"""
response = requests.post(url, data=create_sql)
print(f"建表结果: {response.status_code}")

# 3. 写入数据（单条）
insert_sql = f"""INSERT INTO sensor (device_id, region, time, temperature, humidity) VALUES
('F07A1260', 'north-cn', '{time.strftime('%Y-%m-%d %H:%M:%S')}', 75.3, 45)"""
response = requests.post(url, data=insert_sql)
print(f"写入结果: {response.status_code}")

# 4. 批量写入（推荐）
# 注意：主键为 (device_id, region, time)，同一设备同一时间戳会 UPSERT 覆盖
import datetime
now = datetime.datetime.now()
times = [(now + datetime.timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(4)]
batch_sql = f"""INSERT INTO sensor (device_id, region, time, temperature, humidity) VALUES
('F07A1260', 'north-cn', '{times[0]}', 75.3, 45),
('F07A1260', 'north-cn', '{times[1]}', 76.1, 47),
('F07A1261', 'south-cn', '{times[2]}', 18.1, 44),
('F07A1261', 'south-cn', '{times[3]}', 19.7, 44)"""
response = requests.post(url, data=batch_sql)
print(f"批量写入结果: {response.status_code}")

# 5. 查询数据
query_sql = "SELECT device_id, region, time, temperature FROM sensor LIMIT 100"
response = requests.post(url, data=query_sql)
result = response.json()
for row in result.get('rows', []):
    print(f"设备: {row[0]}, 区域: {row[1]}, 时间: {row[2]}, 温度: {row[3]}")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【生产环境建议】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 批量写入：每次写入 100-1000 个数据点
2. 数据压缩：时序引擎自动压缩，无需手动配置
3. TTL 设置：建议设置数据过期时间（如 90 天）
4. 异常处理：添加重试机制和错误日志

【完整文档】如需了解更多（HTTP API 详细参数、降采样、预聚合、TTL）：
https://help.aliyun.com/zh/lindorm/user-guide/http-sql-api-user-guide
```

---

### 场景 C：搜索引擎快速开始

**Agent 执行查询后，直接给用户完整答案**：

```
【搜索引擎完整示例】（兼容 Elasticsearch 7.10 API）

我已为您准备好搜索引擎的完整代码（Java Low Level REST Client）：

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 1：获取连接信息】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

控制台 → 数据库连接 → 搜索引擎页签
- Elasticsearch 兼容地址（专有网络或公网）
- 默认用户名和密码
- 端口固定为 30070

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 2：添加 Maven 依赖】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<dependency>
    <groupId>org.elasticsearch.client</groupId>
    <artifactId>elasticsearch-rest-client</artifactId>
    <version>7.10.0</version>
</dependency>
<dependency>
    <groupId>org.apache.logging.log4j</groupId>
    <artifactId>log4j-core</artifactId>
    <version>2.8.2</version>
</dependency>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 3：连接并操作】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.apache.http.impl.nio.client.HttpAsyncClientBuilder;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.Request;
import org.elasticsearch.client.Response;
import org.apache.http.util.EntityUtils;

public class LindormSearchQuickStart {
    public static void main(String[] args) throws Exception {
        // 1. 配置连接（Elasticsearch 兼容，端口 30070）
        // Agent 根据实例 ServiceType 选择域名格式：V1=.lindorm.rds.aliyuncs.com，V2=.lindorm.aliyuncs.com
        String searchUrl = "ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com";
        int searchPort = 30070;
        String username = "user";    // 从控制台获取
        String password = "test";    // 从控制台获取

        final CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
        credentialsProvider.setCredentials(AuthScope.ANY,
            new UsernamePasswordCredentials(username, password));

        RestClientBuilder builder = RestClient.builder(new HttpHost(searchUrl, searchPort));
        builder.setHttpClientConfigCallback(httpClientBuilder ->
            httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider));

        try (RestClient client = builder.build()) {
            String indexName = "products";

            // 2. 创建索引
            Request createReq = new Request("PUT", "/" + indexName);
            createReq.setJsonEntity("{" +
                "  \"settings\":{\"index.number_of_shards\": 1}," +
                "  \"mappings\":{" +
                "    \"properties\":{" +
                "      \"name\":{\"type\":\"text\"}," +
                "      \"price\":{\"type\":\"double\"}," +
                "      \"category\":{\"type\":\"keyword\"}" +
                "    }" +
                "  }" +
                "}");
            Response resp = client.performRequest(createReq);
            System.out.println("创建索引: " + EntityUtils.toString(resp.getEntity()));

            // 3. 批量写入文档
            Request bulkReq = new Request("POST", "/_bulk");
            StringBuilder bulk = new StringBuilder();
            bulk.append("{\"index\":{\"_index\":\"products\",\"_id\":\"1\"}}\n");
            bulk.append("{\"name\":\"iPhone 15\",\"price\":7999.0,\"category\":\"手机\"}\n");
            bulk.append("{\"index\":{\"_index\":\"products\",\"_id\":\"2\"}}\n");
            bulk.append("{\"name\":\"MacBook Pro\",\"price\":14999.0,\"category\":\"电脑\"}\n");
            bulk.append("{\"index\":{\"_index\":\"products\",\"_id\":\"3\"}}\n");
            bulk.append("{\"name\":\"AirPods Pro\",\"price\":1899.0,\"category\":\"耳机\"}\n");
            bulkReq.setJsonEntity(bulk.toString());
            client.performRequest(bulkReq);
            System.out.println("批量写入完成");

            // 4. 刷新索引（强制写入数据可见）
            client.performRequest(new Request("POST", "/" + indexName + "/_refresh"));

            // 5. 全文检索
            Request searchReq = new Request("GET", "/" + indexName + "/_search");
            searchReq.setJsonEntity("{" +
                "  \"query\":{" +
                "    \"match\":{\"name\":\"Pro\"}" +
                "  }" +
                "}");
            resp = client.performRequest(searchReq);
            System.out.println("搜索结果: " + EntityUtils.toString(resp.getEntity()));

            // 6. 查询单个文档
            resp = client.performRequest(new Request("GET", "/" + indexName + "/_doc/1"));
            System.out.println("文档1: " + EntityUtils.toString(resp.getEntity()));

            // 7. 删除索引
            client.performRequest(new Request("DELETE", "/" + indexName));
            System.out.println("索引已删除");
        }
    }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【curl 快速验证】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 创建索引
curl -u user:password -X PUT "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/products" \
  -H 'Content-Type: application/json' -d '
  {"settings":{"index.number_of_shards":1},
   "mappings":{"properties":{"name":{"type":"text"},"price":{"type":"double"}}}}'

# 写入文档
curl -u user:password -X POST "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/products/_doc/1" \
  -H 'Content-Type: application/json' -d '{"name":"iPhone 15","price":7999}'

# 全文检索
curl -u user:password -X GET "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/products/_search" \
  -H 'Content-Type: application/json' -d '{"query":{"match":{"name":"iPhone"}}}'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【搜索引擎关键参数】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 参数 | 值 | 说明 |
|------|-----|------|
| 端口 | **30070** | Elasticsearch 兼容端口，固定不变 |
| 协议 | HTTP | 不支持 HTTPS |
| 认证 | Basic Auth | 用户名密码从控制台获取 |
| 兼容版本 | ES 7.10 | 兼容 Elasticsearch 7.10 及更早版本 API |
| 写入后可见 | 需手动 _refresh | 或等待自动 refresh（默认1秒） |

【完整文档】搜索引擎开发指南：
https://help.aliyun.com/zh/lindorm/user-guide/lindormsearch/
https://help.aliyun.com/zh/lindorm/user-guide/java-low-level-rest-client
```

---

### 场景 D：向量引擎快速开始

**Agent 执行查询后，直接给用户完整答案**：

```
【向量引擎完整示例】（通过搜索引擎 ES API 访问）

Lindorm 向量引擎无独立连接地址，通过搜索引擎的 Elasticsearch 兼容 API 访问（端口 30070）。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 1：获取连接信息】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

与搜索引擎相同：
- 连接地址：搜索引擎的 Elasticsearch 兼容地址（公网或 VPC）
- 端口：30070
- 认证：Basic Auth（用户名/密码）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 2：创建向量索引（hnsw）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

curl -u user:password -X PUT "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test" \
  -H 'Content-Type: application/json' -d '{
    "settings": {
      "number_of_shards": 1,
      "knn": true
    },
    "mappings": {
      "_source": {"excludes": ["vector1"]},
      "properties": {
        "vector1": {
          "type": "knn_vector",
          "dimension": 3,
          "method": {
            "engine": "lvector",
            "name": "hnsw",
            "space_type": "l2",
            "parameters": {
              "m": 24,
              "ef_construction": 500
            }
          }
        },
        "field1": {"type": "long"},
        "name": {"type": "keyword"}
      }
    }
  }'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 3：写入向量数据】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

curl -u user:password -X POST "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/_bulk" \
  -H 'Content-Type: application/x-ndjson' -d '
{"index":{"_index":"vector_test","_id":"1"}}
{"field1":1,"name":"苹果","vector1":[1.2,1.3,1.4]}
{"index":{"_index":"vector_test","_id":"2"}}
{"field1":2,"name":"香蕉","vector1":[2.2,2.3,2.4]}
{"index":{"_index":"vector_test","_id":"3"}}
{"field1":3,"name":"橙子","vector1":[3.2,3.3,3.4]}
'

# 刷新索引使数据可见
curl -u user:password -X POST "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test/_refresh"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 4：KNN 近似搜索】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 查找与 [1.3,1.4,1.5] 最相似的 3 个向量
# 注意：KNN 搜索默认不返回 _source，必须显式指定需要返回的字段
curl -u user:password -X GET "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test/_search" \
  -H 'Content-Type: application/json' -d '{
    "size": 3,
    "_source": ["field1", "name"],
    "query": {
      "knn": {
        "vector1": {
          "vector": [1.3,1.4,1.5],
          "k": 3
        }
      }
    }
  }'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 5：向量+标量混合检索】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

curl -u user:password -X GET "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test/_search" \
  -H 'Content-Type: application/json' -d '{
    "size": 3,
    "_source": ["field1", "name"],
    "query": {
      "bool": {
        "must": [
          {
            "knn": {
              "vector1": {
                "vector": [1.3,1.4,1.5],
                "k": 10
              }
            }
          }
        ],
        "filter": [
          {"range": {"field1": {"gte": 1, "lte": 3}}}
        ]
      }
    }
  }'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【向量引擎关键参数】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 参数 | 值 | 说明 |
|------|-----|------|
| 接入方式 | 搜索引擎 ES API | 无独立连接地址，复用搜索引擎端口 30070 |
| 向量类型 | knn_vector | 需指定 dimension（维度） |
| 索引算法 | hnsw | 支持 l2、cosinesimil（实测均可用） |
| 写入后可见 | 需 _refresh | 或等待自动刷新 |

【完整文档】向量引擎开发指南：
https://help.aliyun.com/zh/lindorm/user-guide/foundation
```

---

### 场景 E：流引擎快速开始

**Agent 执行查询后，直接给用户完整答案**：

```
【流引擎完整示例】（ETL SQL 实时同步与预计算）

Lindorm 流引擎通过 MySQL 协议访问（端口 33060），使用 ETL SQL 实现实时数据同步和预计算。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 1：在宽表引擎创建源表和结果表】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 连接宽表引擎（MySQL 协议）
mysql -h <宽表引擎地址> -P 33060 -u root -p

-- 创建源表
CREATE TABLE source_tbl(id INT, val DOUBLE, PRIMARY KEY(id));

-- 创建镜像表（实时同步目标）
CREATE TABLE sink_tbl(id INT, val DOUBLE, PRIMARY KEY(id));

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 2：在流引擎创建 ETL（实时镜像）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 连接流引擎（MySQL 协议，端口相同）
mysql -h <流引擎地址> -P 33060 -u root -p

-- 创建实时同步 ETL
CREATE ETL sync_etl AS INSERT INTO sink_tbl SELECT * FROM source_tbl;

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 3：验证实时同步】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 在宽表引擎插入数据
INSERT INTO source_tbl(id, val) VALUES (1, 1.1), (2, 2.2);

-- 查询镜像表（数据已实时同步）
SELECT * FROM sink_tbl;
+------+------+
| id   | val  |
+------+------+
|    1 |  1.1 |
|    2 |  2.2 |
+------+------+

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 4：多表 JOIN 预计算】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 在宽表引擎创建用户表和订单表
CREATE TABLE user_tbl(user_id VARCHAR NOT NULL, user_name VARCHAR, PRIMARY KEY(user_id));

CREATE TABLE order_tbl(
  order_id VARCHAR NOT NULL,
  user_id VARCHAR,
  amount DOUBLE,
  PRIMARY KEY(order_id)
);

-- 为 JOIN 字段创建索引（必须）
CREATE INDEX idx_user_id ON order_tbl(user_id);

-- 创建结果表（预打宽，需可更新）
CREATE TABLE user_order_tbl(
  order_id VARCHAR NOT NULL,
  user_id VARCHAR,
  user_name VARCHAR,
  amount DOUBLE,
  PRIMARY KEY(order_id)
) WITH (MUTABILITY='MUTABLE_UDT');

-- 在流引擎创建 JOIN ETL（需使用完整表名）
CREATE ETL join_etl AS
INSERT INTO `lindorm_table`.`default`.`user_order_tbl`(order_id, user_id, user_name, amount)
SELECT o.order_id, o.user_id, u.user_name, o.amount
FROM `lindorm_table`.`default`.`order_tbl` o
JOIN `lindorm_table`.`default`.`user_tbl` u ON o.user_id = u.user_id;

-- 插入测试数据
INSERT INTO user_tbl VALUES ('U001', '张三'), ('U002', '李四');
INSERT INTO order_tbl VALUES ('O001', 'U001', 100.0), ('O002', 'U001', 200.0);

-- 查询结果表（已实时 JOIN）
SELECT * FROM user_order_tbl;
+----------+---------+-----------+--------+
| order_id | user_id | user_name | amount |
+----------+---------+-----------+--------+
| O001     | U001    | 张三      |  100.0 |
| O002     | U001    | 张三      |  200.0 |
+----------+---------+-----------+--------+

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【流引擎关键参数】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 参数 | 值 | 说明 |
|------|-----|------|
| 连接方式 | MySQL 协议 | 与宽表引擎相同，端口 33060 |
| 核心语法 | CREATE ETL | `CREATE ETL name AS INSERT INTO ... SELECT ...` |
| 表名格式 | 完整路径 | 跨库查询需用 `lindorm_table.default.tablename` |
| JOIN 要求 | 必须有索引 | JOIN key 需有二级索引，否则报错 |
| 结果表 | MUTABLE_UDT | 预计算结果表需支持更新 |
| 实时性 | 近实时 | 数据变更后秒级同步 |

【管理 ETL】
-- 查看所有 ETL
SHOW ETLS;

-- 删除 ETL
DROP ETL IF EXISTS etl_name;

【完整文档】流引擎开发指南：
https://help.aliyun.com/zh/lindorm/user-guide/real-time-etl
```

---

### 场景 F：宽表引擎 HBase API 快速开始

**适用场景**：已有 HBase 应用迁移、需要 KV 级操作的场景。新用户推荐优先使用场景 A（MySQL 协议 SQL）。

参考文档：https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-java-to-connect-to-and-use-the-wide-table-engine

HBase SDK 安装：https://help.aliyun.com/zh/lindorm/user-guide/install-and-upgrade-hbase-sdk-for-java

**Agent 从官方文档提取最新示例**：

```
【宽表引擎 HBase API 完整示例】（Java）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 1：添加 Maven 依赖】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<!-- 根据开源 HBase 客户端版本选择对应的阿里云发行版 -->
<!-- HBase 1.x 用户 -->
<dependency>
    <groupId>com.aliyun.hbase</groupId>
    <artifactId>alihbase-client</artifactId>
    <version>1.8.8</version>
</dependency>
<!-- HBase 2.x 用户 -->
<dependency>
    <groupId>com.aliyun.hbase</groupId>
    <artifactId>alihbase-client</artifactId>
    <version>2.8.7</version>
</dependency>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 2：配置连接】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.*;
import org.apache.hadoop.hbase.client.*;
import org.apache.hadoop.hbase.util.Bytes;

public class LindormHBaseQuickStart {
    public static void main(String[] args) throws Exception {
        // 1. 配置连接（端口 30020）
        // 连接地址从控制台"数据库连接"页面获取 HBase API 地址
        Configuration conf = HBaseConfiguration.create();
        conf.set("hbase.zookeeper.quorum", "<您的连接地址>:30020");
        conf.set("hbase.client.username", "用户名");
        conf.set("hbase.client.password", "密码");

        // 2. 创建连接（线程安全，全局复用，程序结束时关闭）
        Connection connection = ConnectionFactory.createConnection(conf);

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 3：DDL 操作（建表/删表）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        try (Admin admin = connection.getAdmin()) {
            // 建表
            HTableDescriptor htd = new HTableDescriptor(TableName.valueOf("tablename"));
            htd.addFamily(new HColumnDescriptor(Bytes.toBytes("family")));
            // 创建单分区表（生产环境建议预分区，避免热点）
            admin.createTable(htd);

            // 预分区建表示例（推荐）
            // byte[][] splitKeys = new byte[][] {
            //     Bytes.toBytes("10"), Bytes.toBytes("20"), Bytes.toBytes("30")
            // };
            // admin.createTable(htd, splitKeys);

            // disable 表（truncate/删除前必须先 disable）
            // admin.disableTable(TableName.valueOf("tablename"));
            // admin.truncateTable(TableName.valueOf("tablename"), true);
            // admin.deleteTable(TableName.valueOf("tablename"));
        }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【步骤 4：DML 操作（读写删查）】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

        // Table 为非线程安全对象，每个线程必须从 Connection 中获取自己的 Table
        try (Table table = connection.getTable(TableName.valueOf("tablename"))) {
            // 插入数据
            Put put = new Put(Bytes.toBytes("row"));
            put.addColumn(Bytes.toBytes("family"), Bytes.toBytes("qualifier"), Bytes.toBytes("value"));
            table.put(put);

            // 单行读取
            Get get = new Get(Bytes.toBytes("row"));
            Result res = table.get(get);

            // 删除一行数据
            Delete delete = new Delete(Bytes.toBytes("row"));
            table.delete(delete);

            // Scan 范围查询
            Scan scan = new Scan(Bytes.toBytes("startRow"), Bytes.toBytes("endRow"));
            ResultScanner scanner = table.getScanner(scan);
            for (Result result : scanner) {
                // 处理查询结果
            }
            scanner.close();
        }

        connection.close();
    }
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【HBase API 关键参数】
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

| 参数 | 值 | 说明 |
|------|-----|------|
| 端口 | **30020** | HBase API 专用端口，固定不变 |
| Connection | 线程安全 | 全局创建一次，程序结束时关闭 |
| Table | 非线程安全 | 每个线程必须获取自己的 Table 对象 |
| 建表 | 建议预分区 | 单 Region 会导致热点，生产环境必须预分区 |
| 认证 | 用户名/密码 | 从控制台获取 |

【完整文档】
- Java：https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-java-to-connect-to-and-use-the-wide-table-engine
- 非 Java（Thrift2）：https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-a-non-java-language-to-connect-to-and-use-the-wide-table-engine
```
