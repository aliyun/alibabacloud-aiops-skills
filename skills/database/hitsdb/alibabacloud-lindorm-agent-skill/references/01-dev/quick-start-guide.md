# Quick Start Scenarios

When the user asks beginner development questions such as "how do I create a table", "how do I write data", or "how do I query data", follow this guide.

## Trigger Conditions

Typical user expressions:
- "How do I create a table?"
- "How do I write data?"
- "Give me a complete example."
- "How do I use the wide table engine?"
- "How should I store time series data?"

## Core Principles

**The agent should do the heavy lifting instead of asking the user to explore by themselves**:
1. **Extract complete code examples** and provide executable code directly.
2. Attach documentation links only when they are needed as supplementary "learn more" references.
3. **Goal**: the user can run the code directly after receiving it, without searching documentation again.

---

## Execution Flow

### Step 1: Confirm the engine type

Ask which engine the user wants to use if it is not clear:

```text
Which engine do you want to use?

1. Wide table engine, suitable for semi-structured data and compatible with HBase
2. Time series engine, suitable for IoT and monitoring time series data
3. Search engine, suitable for full-text search

Or tell me your use case, and I will recommend an engine.
```

---

### Step 2: Use reference documentation and generate a complete example

**Mandatory requirement**: before providing any code example, **obtain information from the Skill references first**. If the Skill references do not cover the case, query the official documentation for confirmation.

**What the agent must do**: based on the engine type, access the Alibaba Cloud Lindorm official documentation and obtain the latest examples.

**Query target**:
- Official documentation: `https://help.aliyun.com/zh/lindorm/`
- Key information: complete code examples for table creation, data writes, and queries

**Must extract and verify from official documentation**:
- Latest Maven dependency versions, not old versions from training data
- Correct API usage, such as `Connection` instead of deprecated `HConnection`
- Currently recommended table creation statement format
- Officially verified write and query code
- Best practices and performance optimization suggestions

**Verification checklist**:

```text
Before providing code, the agent must confirm:
- Official documentation has been accessed for the latest example.
- The SDK version is up to date, such as alilindorm-table-sdk 2.x.
- The API usage is currently recommended and not deprecated.
- The table creation, write, and query code has been verified by official documentation.
- Official documentation links are attached for further learning.
```

Then organize the result into complete executable code and provide it directly to the user.

---

## Complete Examples by Engine Type

### Scenario A: Wide Table Engine Quick Start

After checking the required references, provide a complete answer directly:

```text
[Wide table engine complete example]

I have prepared complete code from connection to query, based on the latest official documentation.

[Step 1: Add Maven dependency]

<!-- MySQL protocol JDBC, recommended -->
<dependencies>
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
        <version>8.3.0</version>
    </dependency>
</dependencies>

[Step 2: Connect to the instance]

import java.sql.*;
import java.util.Properties;

public class LindormQuickStart {
    public static void main(String[] args) throws Exception {
        // 1. Configure the connection. MySQL protocol is recommended.
        // The agent selects the correct domain format according to instance ServiceType. See sql-client-guide.md.
        Class.forName("com.mysql.cj.jdbc.Driver");
        String url = "jdbc:mysql://<connection-endpoint>:33060/default?sslMode=disabled";
        Properties props = new Properties();
        props.setProperty("user", "your-username");
        props.setProperty("password", "your-password");
        Connection conn = DriverManager.getConnection(url, props);
        Statement stmt = conn.createStatement();

        // 2. Create a table.
        stmt.execute("CREATE TABLE IF NOT EXISTS users (" +
            "id VARCHAR PRIMARY KEY," +
            "name VARCHAR," +
            "age INT," +
            "city VARCHAR)");
        System.out.println("Table created successfully");

        // 3. Write data.
        stmt.execute("INSERT INTO users (id, name, age, city) VALUES " +
            "('1', 'Alice', 25, 'Shanghai'), " +
            "('2', 'Bob', 30, 'Beijing')");
        System.out.println("Data written successfully");

        // 4. Query data.
        ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE age > 20");
        while (rs.next()) {
            System.out.println("name=" + rs.getString("name") + ", age=" + rs.getInt("age"));
        }

        // 5. Close the connection.
        rs.close();
        stmt.close();
        conn.close();
    }
}

[Batch write optimization, recommended for production]

// Batch write with PreparedStatement.
String sql = "INSERT INTO users (id, name, age, city) VALUES (?, ?, ?, ?)";
PreparedStatement pstmt = conn.prepareStatement(sql);
for (int i = 0; i < 10000; i++) {
    pstmt.setString(1, "id_" + i);
    pstmt.setString(2, "user_" + i);
    pstmt.setInt(3, 20 + i % 50);
    pstmt.setString(4, "city_" + i % 10);
    pstmt.addBatch();
    if (i % 1000 == 0) {
        pstmt.executeBatch();
    }
}
pstmt.executeBatch();

[Complete documentation]
For more information, such as secondary indexes, global indexes, and performance optimization:
https://help.aliyun.com/zh/lindorm/user-guide/lindorm-wide-table-engine
```

---

### Scenario B: Time Series Engine Quick Start

Extract the latest example from official documentation first.

> **Recommended connection method**: official documentation recommends the [JDBC Driver](https://help.aliyun.com/zh/lindorm/user-guide/use-the-jdbc-driver-for-lindorm-to-connect-to-and-use-lindormtsdb), which supports Java. The following example uses the HTTP SQL API because it is lightweight and suitable for quick validation in Python and other non-Java languages.

Reference documentation: `https://help.aliyun.com/zh/lindorm/user-guide/http-sql-api-user-guide`

Then provide complete code directly:

```text
[Time series engine complete example, Python HTTP SQL API]

I have prepared complete code for writing and querying time series data.

[Step 1: Install dependency]

pip install requests

[Step 2: Complete example code]

import requests
import time
import datetime

# 1. Connection configuration.
host = "your-time-series-engine-endpoint"
port = 8242
url = f"http://{host}:{port}/api/v2/sql"

# 2. Create a table.
create_sql = """CREATE TABLE IF NOT EXISTS sensor (
  device_id VARCHAR NOT NULL,
  region VARCHAR NOT NULL,
  time TIMESTAMP NOT NULL,
  temperature DOUBLE,
  humidity BIGINT,
  PRIMARY KEY(device_id, region, time)
)"""
response = requests.post(url, data=create_sql)
print(f"Create table result: {response.status_code}")

# 3. Write one row.
insert_sql = f"""INSERT INTO sensor (device_id, region, time, temperature, humidity) VALUES
('F07A1260', 'north-cn', '{time.strftime('%Y-%m-%d %H:%M:%S')}', 75.3, 45)"""
response = requests.post(url, data=insert_sql)
print(f"Write result: {response.status_code}")

# 4. Batch write, recommended.
# Note: the primary key is (device_id, region, time). The same device with the same timestamp performs UPSERT overwrite.
now = datetime.datetime.now()
times = [(now + datetime.timedelta(seconds=i)).strftime('%Y-%m-%d %H:%M:%S') for i in range(4)]
batch_sql = f"""INSERT INTO sensor (device_id, region, time, temperature, humidity) VALUES
('F07A1260', 'north-cn', '{times[0]}', 75.3, 45),
('F07A1260', 'north-cn', '{times[1]}', 76.1, 47),
('F07A1261', 'south-cn', '{times[2]}', 18.1, 44),
('F07A1261', 'south-cn', '{times[3]}', 19.7, 44)"""
response = requests.post(url, data=batch_sql)
print(f"Batch write result: {response.status_code}")

# 5. Query data.
query_sql = "SELECT device_id, region, time, temperature FROM sensor LIMIT 100"
response = requests.post(url, data=query_sql)
result = response.json()
for row in result.get('rows', []):
    print(f"device: {row[0]}, region: {row[1]}, time: {row[2]}, temperature: {row[3]}")

[Production recommendations]

1. Batch writes: write 100 to 1000 data points each time.
2. Data compression: the time series engine compresses data automatically; no manual configuration is required.
3. TTL: configure data expiration, such as 90 days.
4. Error handling: add retry logic and error logs.

[Complete documentation]
For more information, such as HTTP API parameters, downsampling, pre-aggregation, and TTL:
https://help.aliyun.com/zh/lindorm/user-guide/http-sql-api-user-guide
```

---

### Scenario C: Search Engine Quick Start

After checking the required references, provide a complete answer directly:

```text
[Search engine complete example, compatible with Elasticsearch 7.10 API]

I have prepared complete search engine code with Java Low Level REST Client.

[Step 1: Obtain connection information]

Console -> Database Connection -> Search Engine tab
- Elasticsearch-compatible endpoint, either VPC or public network
- Default username and password
- Fixed port: 30070

[Step 2: Add Maven dependencies]

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

[Step 3: Connect and operate]

import org.apache.http.HttpHost;
import org.apache.http.auth.AuthScope;
import org.apache.http.auth.UsernamePasswordCredentials;
import org.apache.http.client.CredentialsProvider;
import org.apache.http.impl.client.BasicCredentialsProvider;
import org.elasticsearch.client.RestClient;
import org.elasticsearch.client.RestClientBuilder;
import org.elasticsearch.client.Request;
import org.elasticsearch.client.Response;
import org.apache.http.util.EntityUtils;

public class LindormSearchQuickStart {
    public static void main(String[] args) throws Exception {
        // 1. Configure the connection. Elasticsearch-compatible API uses port 30070.
        // Select the domain format according to ServiceType: V1=.lindorm.rds.aliyuncs.com, V2=.lindorm.aliyuncs.com.
        String searchUrl = "ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com";
        int searchPort = 30070;
        String username = "user";
        String password = "test";

        final CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
        credentialsProvider.setCredentials(AuthScope.ANY,
            new UsernamePasswordCredentials(username, password));

        RestClientBuilder builder = RestClient.builder(new HttpHost(searchUrl, searchPort));
        builder.setHttpClientConfigCallback(httpClientBuilder ->
            httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider));

        try (RestClient client = builder.build()) {
            String indexName = "products";

            // 2. Create an index.
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
            System.out.println("Create index: " + EntityUtils.toString(resp.getEntity()));

            // 3. Bulk write documents.
            Request bulkReq = new Request("POST", "/_bulk");
            StringBuilder bulk = new StringBuilder();
            bulk.append("{\"index\":{\"_index\":\"products\",\"_id\":\"1\"}}\n");
            bulk.append("{\"name\":\"iPhone 15\",\"price\":7999.0,\"category\":\"phone\"}\n");
            bulk.append("{\"index\":{\"_index\":\"products\",\"_id\":\"2\"}}\n");
            bulk.append("{\"name\":\"MacBook Pro\",\"price\":14999.0,\"category\":\"computer\"}\n");
            bulk.append("{\"index\":{\"_index\":\"products\",\"_id\":\"3\"}}\n");
            bulk.append("{\"name\":\"AirPods Pro\",\"price\":1899.0,\"category\":\"earphones\"}\n");
            bulkReq.setJsonEntity(bulk.toString());
            client.performRequest(bulkReq);
            System.out.println("Bulk write completed");

            // 4. Refresh the index to make written data visible.
            client.performRequest(new Request("POST", "/" + indexName + "/_refresh"));

            // 5. Full-text search.
            Request searchReq = new Request("GET", "/" + indexName + "/_search");
            searchReq.setJsonEntity("{" +
                "  \"query\":{" +
                "    \"match\":{\"name\":\"Pro\"}" +
                "  }" +
                "}");
            resp = client.performRequest(searchReq);
            System.out.println("Search result: " + EntityUtils.toString(resp.getEntity()));

            // 6. Query a single document.
            resp = client.performRequest(new Request("GET", "/" + indexName + "/_doc/1"));
            System.out.println("Document 1: " + EntityUtils.toString(resp.getEntity()));

            // 7. Delete the index.
            client.performRequest(new Request("DELETE", "/" + indexName));
            System.out.println("Index deleted");
        }
    }
}

[curl quick validation]

# Create index.
curl --connect-timeout 10 -m 60 -u user:password -X PUT "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/products"   -H 'Content-Type: application/json' -d '
  {"settings":{"index.number_of_shards":1},
   "mappings":{"properties":{"name":{"type":"text"},"price":{"type":"double"}}}}'

# Write document.
curl --connect-timeout 10 -m 60 -u user:password -X POST "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/products/_doc/1"   -H 'Content-Type: application/json' -d '{"name":"iPhone 15","price":7999}'

# Full-text search.
curl --connect-timeout 10 -m 60 -u user:password -X GET "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/products/_search"   -H 'Content-Type: application/json' -d '{"query":{"match":{"name":"iPhone"}}}'

[Search engine key parameters]

| Parameter | Value | Description |
|-----------|-------|-------------|
| Port | 30070 | Fixed Elasticsearch-compatible port |
| Protocol | HTTP | HTTPS is not supported |
| Authentication | Basic Auth | Obtain username and password from the console |
| Compatibility | ES 7.10 | Compatible with Elasticsearch 7.10 and earlier APIs |
| Visibility after writes | Manual `_refresh` required | Or wait for automatic refresh, which defaults to 1 second |

[Complete documentation]
Search engine development guide:
https://help.aliyun.com/zh/lindorm/user-guide/lindormsearch/
https://help.aliyun.com/zh/lindorm/user-guide/java-low-level-rest-client
```

---

### Scenario D: Vector Engine Quick Start

After checking the required references, provide a complete answer directly:

```text
[Vector engine complete example, accessed through the search engine ES API]

The Lindorm vector engine has no independent connection endpoint. Access it through the Elasticsearch-compatible API of the search engine on port 30070.

[Step 1: Obtain connection information]

Same as the search engine:
- Endpoint: Elasticsearch-compatible search engine endpoint, public or VPC
- Port: 30070
- Authentication: Basic Auth with username and password

[Step 2: Create a vector index with HNSW]

curl --connect-timeout 10 -m 60 -u user:password -X PUT "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test"   -H 'Content-Type: application/json' -d '{
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

[Step 3: Write vector data]

curl --connect-timeout 10 -m 60 -u user:password -X POST "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/_bulk"   -H 'Content-Type: application/x-ndjson' -d '
{"index":{"_index":"vector_test","_id":"1"}}
{"field1":1,"name":"apple","vector1":[1.2,1.3,1.4]}
{"index":{"_index":"vector_test","_id":"2"}}
{"field1":2,"name":"banana","vector1":[2.2,2.3,2.4]}
{"index":{"_index":"vector_test","_id":"3"}}
{"field1":3,"name":"orange","vector1":[3.2,3.3,3.4]}
'

# Refresh the index to make data visible.
curl --connect-timeout 10 -m 60 -u user:password -X POST "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test/_refresh"

[Step 4: KNN approximate search]

# Find the three vectors most similar to [1.3,1.4,1.5].
# Note: KNN search does not return _source by default. Explicitly specify returned fields.
curl --connect-timeout 10 -m 60 -u user:password -X GET "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test/_search"   -H 'Content-Type: application/json' -d '{
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

[Step 5: Hybrid vector and scalar retrieval]

curl --connect-timeout 10 -m 60 -u user:password -X GET "http://ld-xxxx-proxy-search-pub.lindorm.rds.aliyuncs.com:30070/vector_test/_search"   -H 'Content-Type: application/json' -d '{
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

[Vector engine key parameters]

| Parameter | Value | Description |
|-----------|-------|-------------|
| Access method | Search engine ES API | No independent endpoint. Reuse search engine port 30070 |
| Vector type | knn_vector | `dimension` must be specified |
| Index algorithm | hnsw | Supports `l2` and `cosinesimil`, both verified as usable |
| Visibility after writes | `_refresh` required | Or wait for automatic refresh |

[Complete documentation]
Vector engine development guide:
https://help.aliyun.com/zh/lindorm/user-guide/foundation
```

---

### Scenario E: Streaming Engine Quick Start

After checking the required references, provide a complete answer directly:

```text
[Streaming engine complete example, ETL SQL real-time synchronization and precomputation]

The Lindorm streaming engine is accessed through the MySQL protocol on port 33060. It uses ETL SQL for real-time data synchronization and precomputation.

[Step 1: Create source and result tables in the wide table engine]

-- Connect to the wide table engine through the MySQL protocol.
mysql -h <wide-table-engine-endpoint> -P 33060 -u root -p

-- Create a source table.
CREATE TABLE source_tbl(id INT, val DOUBLE, PRIMARY KEY(id));

-- Create a mirror table as the real-time synchronization target.
CREATE TABLE sink_tbl(id INT, val DOUBLE, PRIMARY KEY(id));

[Step 2: Create ETL in the streaming engine for real-time mirroring]

-- Connect to the streaming engine through the MySQL protocol on the same port.
mysql -h <streaming-engine-endpoint> -P 33060 -u root -p

-- Create real-time synchronization ETL.
CREATE ETL sync_etl AS INSERT INTO sink_tbl SELECT * FROM source_tbl;

[Step 3: Verify real-time synchronization]

-- Insert data in the wide table engine.
INSERT INTO source_tbl(id, val) VALUES (1, 1.1), (2, 2.2);

-- Query the mirror table. Data has been synchronized in real time.
SELECT * FROM sink_tbl;
+------+------+
| id   | val  |
+------+------+
|    1 |  1.1 |
|    2 |  2.2 |
+------+------+

[Step 4: Multi-table JOIN precomputation]

-- Create user and order tables in the wide table engine.
CREATE TABLE user_tbl(user_id VARCHAR NOT NULL, user_name VARCHAR, PRIMARY KEY(user_id));

CREATE TABLE order_tbl(
  order_id VARCHAR NOT NULL,
  user_id VARCHAR,
  amount DOUBLE,
  PRIMARY KEY(order_id)
);

-- Create an index for the JOIN field. This is required.
CREATE INDEX idx_user_id ON order_tbl(user_id);

-- Create a denormalized result table that supports updates.
CREATE TABLE user_order_tbl(
  order_id VARCHAR NOT NULL,
  user_id VARCHAR,
  user_name VARCHAR,
  amount DOUBLE,
  PRIMARY KEY(order_id)
) WITH (MUTABILITY='MUTABLE_UDT');

-- Create JOIN ETL in the streaming engine. Use full table names.
CREATE ETL join_etl AS
INSERT INTO `lindorm_table`.`default`.`user_order_tbl`(order_id, user_id, user_name, amount)
SELECT o.order_id, o.user_id, u.user_name, o.amount
FROM `lindorm_table`.`default`.`order_tbl` o
JOIN `lindorm_table`.`default`.`user_tbl` u ON o.user_id = u.user_id;

-- Insert test data.
INSERT INTO user_tbl VALUES ('U001', 'Alice'), ('U002', 'Bob');
INSERT INTO order_tbl VALUES ('O001', 'U001', 100.0), ('O002', 'U001', 200.0);

-- Query the result table. JOIN results have been generated in real time.
SELECT * FROM user_order_tbl;
+----------+---------+-----------+--------+
| order_id | user_id | user_name | amount |
+----------+---------+-----------+--------+
| O001     | U001    | Alice     |  100.0 |
| O002     | U001    | Alice     |  200.0 |
+----------+---------+-----------+--------+

[Streaming engine key parameters]

| Parameter | Value | Description |
|-----------|-------|-------------|
| Connection method | MySQL protocol | Same as the wide table engine, port 33060 |
| Core syntax | CREATE ETL | `CREATE ETL name AS INSERT INTO ... SELECT ...` |
| Table name format | Full path | Use `lindorm_table.default.tablename` for cross-database queries |
| JOIN requirement | Index required | JOIN keys must have secondary indexes, otherwise an error is returned |
| Result table | MUTABLE_UDT | Precomputed result tables must support updates |
| Real-time behavior | Near real time | Data changes are synchronized within seconds |

[Manage ETL]
-- Show all ETLs.
SHOW ETLS;

-- Drop an ETL.
DROP ETL IF EXISTS etl_name;

[Complete documentation]
Streaming engine development guide:
https://help.aliyun.com/zh/lindorm/user-guide/real-time-etl
```

---

### Scenario F: Wide Table Engine HBase API Quick Start

**Applicable scenarios**: migration of existing HBase applications and KV-level operations. For new users, prefer Scenario A, which uses MySQL protocol SQL.

Reference documentation: `https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-java-to-connect-to-and-use-the-wide-table-engine`

HBase SDK installation: `https://help.aliyun.com/zh/lindorm/user-guide/install-and-upgrade-hbase-sdk-for-java`

Extract the latest example from official documentation first:

```text
[Wide table engine HBase API complete example, Java]

[Step 1: Add Maven dependency]

<!-- Select the corresponding Alibaba Cloud distribution according to the open-source HBase client version. -->
<!-- HBase 1.x users -->
<dependency>
    <groupId>com.aliyun.hbase</groupId>
    <artifactId>alihbase-client</artifactId>
    <version>1.8.8</version>
</dependency>
<!-- HBase 2.x users -->
<dependency>
    <groupId>com.aliyun.hbase</groupId>
    <artifactId>alihbase-client</artifactId>
    <version>2.8.7</version>
</dependency>

[Step 2: Configure the connection]

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.hbase.*;
import org.apache.hadoop.hbase.client.*;
import org.apache.hadoop.hbase.util.Bytes;

public class LindormHBaseQuickStart {
    public static void main(String[] args) throws Exception {
        // 1. Configure the connection on port 30020.
        // Obtain the HBase API endpoint from the Database Connection page in the console.
        Configuration conf = HBaseConfiguration.create();
        conf.set("hbase.zookeeper.quorum", "<connection-endpoint>:30020");
        conf.set("hbase.client.username", "username");
        conf.set("hbase.client.password", "password");

        // 2. Create a connection. It is thread-safe, should be reused globally, and closed when the program exits.
        Connection connection = ConnectionFactory.createConnection(conf);

[Step 3: DDL operations, such as create and delete tables]

        try (Admin admin = connection.getAdmin()) {
            // Create a table.
            HTableDescriptor htd = new HTableDescriptor(TableName.valueOf("tablename"));
            htd.addFamily(new HColumnDescriptor(Bytes.toBytes("family")));
            // Create a table with one region. Use pre-splitting in production to avoid hotspots.
            admin.createTable(htd);

            // Pre-split table creation example, recommended.
            // byte[][] splitKeys = new byte[][] {
            //     Bytes.toBytes("10"), Bytes.toBytes("20"), Bytes.toBytes("30")
            // };
            // admin.createTable(htd, splitKeys);

            // Disable the table before truncate or delete.
            // admin.disableTable(TableName.valueOf("tablename"));
            // admin.truncateTable(TableName.valueOf("tablename"), true);
            // admin.deleteTable(TableName.valueOf("tablename"));
        }

[Step 4: DML operations, such as read, write, delete, and scan]

        // Table is not thread-safe. Each thread must obtain its own Table object from Connection.
        try (Table table = connection.getTable(TableName.valueOf("tablename"))) {
            // Insert data.
            Put put = new Put(Bytes.toBytes("row"));
            put.addColumn(Bytes.toBytes("family"), Bytes.toBytes("qualifier"), Bytes.toBytes("value"));
            table.put(put);

            // Read a single row.
            Get get = new Get(Bytes.toBytes("row"));
            Result res = table.get(get);

            // Delete one row.
            Delete delete = new Delete(Bytes.toBytes("row"));
            table.delete(delete);

            // Range scan.
            Scan scan = new Scan(Bytes.toBytes("startRow"), Bytes.toBytes("endRow"));
            ResultScanner scanner = table.getScanner(scan);
            for (Result result : scanner) {
                // Process query results.
            }
            scanner.close();
        }

        connection.close();
    }
}

[HBase API key parameters]

| Parameter | Value | Description |
|-----------|-------|-------------|
| Port | 30020 | Fixed port dedicated to the HBase API |
| Connection | Thread-safe | Create once globally and close when the program exits |
| Table | Not thread-safe | Each thread must obtain its own Table object |
| Table creation | Pre-splitting recommended | A single region causes hotspots. Pre-splitting is required in production |
| Authentication | Username and password | Obtain them from the console |

[Complete documentation]
- Java: https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-java-to-connect-to-and-use-the-wide-table-engine
- Non-Java, Thrift2: https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-a-non-java-language-to-connect-to-and-use-the-wide-table-engine
```
