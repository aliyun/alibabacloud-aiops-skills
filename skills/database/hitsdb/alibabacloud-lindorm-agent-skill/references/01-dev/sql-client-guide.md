# Lindorm SQL Client Development Guide

This document provides development references for connecting to Lindorm SQL in multiple languages, including Java, Python, Go, C/C++, C#, Rust, PHP, Node.js, connection pool configuration, and framework integration.

> **Recommendation**: The MySQL protocol is more stable, reliable, and performant. New users are advised to connect to the wide table engine through the MySQL protocol.

## Common Prerequisites

- The MySQL protocol compatibility feature is enabled. Console path: Database Connection > Wide Table Engine.
- The client IP has been added to the whitelist.
- For the MySQL protocol port, follow `SKILL.md` -> "Code generation specifications / port quick reference".

### Connection Domain Format

Lindorm instances have two architecture versions, V1 and V2, and their domain formats are different. During execution, the agent should:

1. **Query instance details** to obtain `ServiceType`.
2. **Identify the architecture type**:
   - `lindorm_v2*` -> use the V2 domain format.
   - `lindorm` -> use the V1 domain format.
3. **Automatically fill in** the correct connection endpoint.

| Architecture | ServiceType | Domain format | Private endpoint example | Public endpoint example |
|--------------|-------------|---------------|--------------------------|-------------------------|
| **V2** | `lindorm_v2*` | `*.lindorm.aliyuncs.com` | `ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com:33060` | `ld-xxx-proxy-lindorm-pub.lindorm.aliyuncs.com:33060` |
| **V1** | `lindorm` | `*.lindorm.rds.aliyuncs.com` | `ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com:33060` | `ld-xxx-proxy-lindorm-public.lindorm.rds.aliyuncs.com:33060` |

> **A V1 wide table engine has two MySQL endpoints**: `proxy-lindorm` and `proxy-sql-lindorm`. They provide the same functionality. Either one can be used.
>
> **A V1 public endpoint is available only after public access is enabled**. By default, only the private endpoint is provided. The public endpoint suffix is `-public`.
>
> **How to obtain it**: console -> instance details -> Database Connection, or run `aliyun hitsdb get-lindorm-instance-engine-list --instance-id <id>`.

---

## Notes

- Answer user questions only based on content explicitly documented in this Skill. Do not infer, associate, or generate SQL syntax, parameters, features, or configurations that are not present in the documentation from training knowledge.
- If the documentation does not contain relevant information, clearly tell the user "This content is not included in the current documentation" and guide the user to Alibaba Cloud official documentation at `help.aliyun.com` for confirmation.
- Generated code examples must be based on templates in the documentation. Parameters and syntax must be consistent with the documentation.

---

## Execution Steps

### Step 1: Identify the user's development language

---

### Step 2: Select the connection method based on the development language

#### Official documentation links

**SQL-based application development:**
https://help.aliyun.com/zh/lindorm/user-guide/add-connect-wide-table-engines-through-lindorm-query-language/

**Application development with the MySQL protocol, recommended**

1. **Java**
   - JDBC interface: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-jdbc-interface
   - Druid connection pool: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-connection-pool-druid
   - LindormDataSource: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-lindormdatasource
   - ORM framework MyBatis: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-orm-framework-mybatis
2. **Python**
   - Native Python: https://help.aliyun.com/zh/lindorm/user-guide/python-based-application-development-1
   - ORM framework: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-python-orm-framework
3. **Go**
   - Native Go: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-go
   - ORM framework: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-go-orm-framework
4. **C**
   - C API: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-c-api
5. **C#**
   - Native C#: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-c
6. **Rust**
   - Native Rust: https://help.aliyun.com/zh/lindorm/user-guide/rust-based-application-development
7. **PHP**
   - Native PHP: https://help.aliyun.com/zh/lindorm/user-guide/php-based-application-development
8. **Node.js**
   - Native Node.js: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-node-js
9. **ODBC**
   - ODBC interface: https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-odbc

**Avatica protocol, existing-workload maintenance only**

1. **Java**
- JDBC interface: https://help.aliyun.com/zh/lindorm/user-guide/call-java-api-operations-in-sql-based-connection-to-and-usage-of-lindormtable
- Druid connection pool: https://help.aliyun.com/zh/lindorm/user-guide/through-the-connection-pool-druid-connection-wide-table-engine

2. **Python**
- DB-API: https://help.aliyun.com/zh/lindorm/user-guide/use-the-lindorm-sql-api-for-a-non-java-language-to-connect-to-and-use-the-wide-table-engine-lindormtable
- DBUtils connection pool: https://help.aliyun.com/zh/lindorm/user-guide/use-dbutils-to-connect-to-lindormtable

3. **Go**
- database/sql interface: https://help.aliyun.com/zh/lindorm/user-guide/use-the-apis-provided-by-the-database-or-sql-library-of-go-to-develop-applications

---

### Step 3: Provide connection examples

---

## Common Connection Examples

### MySQL Protocol, Recommended

All examples use the `<connection-endpoint>` placeholder. The agent automatically fills in the correct V1/V2 domain according to the instance `ServiceType`.

#### Java

##### 1. JDBC Interface

**Dependency**:
```xml
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>8.3.0</version>
</dependency>
```

**Connection code**:
```java
Class.forName("com.mysql.cj.jdbc.Driver");

String username = "root";
String password = "your_password";
String database = "default";
String url = "jdbc:mysql://<connection-endpoint>:33060/" + database 
    + "?sslMode=disabled&allowPublicKeyRetrieval=true&useServerPrepStmts=true"
    + "&useLocalSessionState=true&rewriteBatchedStatements=true&cachePrepStmts=true"
    + "&prepStmtCacheSize=100&prepStmtCacheSqlLimit=50000000";

Properties properties = new Properties();
properties.put("user", username);
properties.put("password", password);
Connection connection = DriverManager.getConnection(url, properties);
```

**CRUD example**:
```java
// Create table
try (Statement stmt = connection.createStatement()) {
    stmt.executeUpdate("CREATE TABLE IF NOT EXISTS user_test(id VARCHAR, name VARCHAR, PRIMARY KEY(id))");
}

// Batch insert. INSERT is recommended and has the same semantics as UPSERT.
String sql = "INSERT INTO user_test(id, name) VALUES(?, ?)";
try (PreparedStatement ps = connection.prepareStatement(sql)) {
    for (int i = 0; i < 100; i++) {
        ps.setString(1, "id" + i);
        ps.setString(2, "name" + i);
        ps.addBatch();
    }
    ps.executeBatch();  // Recommended batchSize: 50-100
}

// Query
try (PreparedStatement ps = connection.prepareStatement("SELECT * FROM user_test WHERE id = ?")) {
    ps.setString(1, "id1");
    ResultSet rs = ps.executeQuery();
    while (rs.next()) {
        System.out.println("id=" + rs.getString(1) + ", name=" + rs.getString(2));
    }
}

// Close the connection
connection.close();
```

##### 2. Druid Connection Pool

**Dependency**:
```xml
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>druid</artifactId>
    <version>1.2.11</version>
</dependency>
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>8.3.0</version>
</dependency>
```

**Configuration file** (`druid.properties`):
```properties
driverClassName=com.mysql.cj.jdbc.Driver
url=jdbc:mysql://<connection-endpoint>:33060/default?sslMode=disabled&allowPublicKeyRetrieval=true&useServerPrepStmts=true&useLocalSessionState=true&rewriteBatchedStatements=true&cachePrepStmts=true&prepStmtCacheSize=100&prepStmtCacheSqlLimit=50000000&socketTimeout=120000
username=root
password=your_password

init=true
initialSize=10
maxActive=40
minIdle=40
maxWait=30000

# Avoid uneven connection load distribution
druid.phyMaxUseCount=10000
phyTimeoutMillis=1800000

# Connection keepalive
druid.keepAlive=true
druid.keepAliveBetweenTimeMillis=120000
timeBetweenEvictionRunsMillis=60000
minEvictableIdleTimeMillis=300000
maxEvictableIdleTimeMillis=600000

testWhileIdle=true
testOnBorrow=false
testOnReturn=false
```

**Initialize the connection pool**:
```java
Properties properties = new Properties();
InputStream inputStream = getClass().getClassLoader().getResourceAsStream("druid.properties");
properties.load(inputStream);
DataSource dataSource = DruidDataSourceFactory.createDataSource(properties);

// Use the connection
try (Connection conn = dataSource.getConnection()) {
    // Execute SQL...
}
```

##### 3. LindormDataSource, Officially Recommended

It encapsulates out-of-the-box best-practice configurations and supports zone-aware access in multi-zone deployments.

**Dependency**:
```xml
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>8.3.0</version>
</dependency>
<dependency>
    <groupId>com.aliyun.lindorm</groupId>
    <artifactId>lindorm-sql-datasource</artifactId>
    <version>2.2.1.4</version>
</dependency>
```

**Usage**:
```java
LindormDataSourceConfig config = new LindormDataSourceConfig();
config.setJdbcUrl("jdbc:mysql://<connection-endpoint>:33060/default");
config.setUsername("root");
config.setPassword("your_password");
config.setMaximumPoolSize(30);
LindormDataSource dataSource = new LindormDataSource(config);

try (Connection conn = dataSource.getConnection()) {
    // Execute SQL...
}
```

**Spring Boot 2.x integration**:
```xml
<dependency>
    <groupId>com.aliyun.lindorm</groupId>
    <artifactId>lindorm-sql-datasource-springboot-starter</artifactId>
    <version>2.2.1.4</version>
</dependency>
```

```yaml
# application.yml
spring:
  datasource:
    lindorm:
      jdbc-url: jdbc:mysql://<connection-endpoint>:33060/default
      username: root
      password: your_password
      maximum-pool-size: 30
```

##### 4. MyBatis Framework

**Dependency**:
```xml
<dependency>
    <groupId>org.mybatis</groupId>
    <artifactId>mybatis</artifactId>
    <version>3.5.14</version>
</dependency>
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>8.3.0</version>
</dependency>
```

**Configuration file** (`mybatis-config.xml`):
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE configuration PUBLIC "-//mybatis.org//DTD Config 3.0//EN" "https://mybatis.org/dtd/mybatis-3-config.dtd">
<configuration>
    <environments default="development">
        <environment id="development">
            <transactionManager type="JDBC"/>
            <dataSource type="POOLED">
                <property name="driver" value="com.mysql.cj.jdbc.Driver"/>
                <property name="url" value="jdbc:mysql://<connection-endpoint>:33060/default?sslMode=disabled&amp;allowPublicKeyRetrieval=true"/>
                <property name="username" value="root"/>
                <property name="password" value="your_password"/>
            </dataSource>
        </environment>
    </environments>
    <mappers>
        <mapper class="org.example.UserMapper"/>
    </mappers>
</configuration>
```

**Mapper example**:
```java
public interface UserMapper {
    @Update("CREATE TABLE IF NOT EXISTS demo_user(id INT, name VARCHAR, PRIMARY KEY(id))")
    void createUserTable();

    @Insert("UPSERT INTO demo_user(id, name) VALUES(#{userId}, #{userName})")
    int upsertUser(User user);

    @Select("SELECT * FROM demo_user WHERE id = #{userId}")
    User selectOneUser(@Param("userId") int userId);

    @Delete("DELETE FROM demo_user WHERE id = #{userId}")
    int deleteUser(@Param("userId") int userId);
}
```

---

#### Python

##### 1. mysql-connector-python

**Installation**: `pip install mysql-connector-python==8.0.15`

**Direct connection mode**:
```python
import mysql.connector

connection = mysql.connector.connect(
    host='<connection-endpoint>',
    port=33060,
    user='root',
    passwd='your_password',
    database='default'
)
cursor = connection.cursor(prepared=True)

# Create table
cursor.execute("CREATE TABLE IF NOT EXISTS test_python(c1 INTEGER, c2 INTEGER, c3 VARCHAR, PRIMARY KEY(c1))")

# Insert data. Use parameterization to prevent SQL injection.
cursor.execute("UPSERT INTO test_python(c1, c2, c3) VALUES(?, ?, ?)", (1, 1, 'value1'))

# Query
cursor.execute("SELECT * FROM test_python WHERE c1 = ?", (1,))
print(cursor.fetchall())

cursor.close()
connection.close()
```

**Connection pool mode**:
```python
from mysql.connector import pooling

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=20,
    host='<connection-endpoint>',
    port=33060,
    user='root',
    password='your_password',
    database='default'
)

connection = connection_pool.get_connection()
cursor = connection.cursor(prepared=True)
# ... Execute SQL
cursor.close()
connection.close()  # Return to the connection pool
```

##### 2. SQLAlchemy ORM

**Installation**:
```bash
pip install PyMySQL
pip install SQLAlchemy
```

**Example**:
```python
from sqlalchemy import create_engine, Column, String, Integer, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Player(Base):
    __tablename__ = 'player'
    player_id = Column(Integer, primary_key=True, autoincrement=False)
    player_name = Column(String(255))
    player_height = Column(Float)

engine = create_engine('mysql+pymysql://root:your_password@<connection-endpoint>:33060/default')
Session = sessionmaker(bind=engine)

# Create table
Base.metadata.create_all(engine)

# Write data
session = Session()
session.add(Player(player_id=1001, player_name="john", player_height=2.08))
session.commit()

# Query
rows = session.query(Player).filter(Player.player_id == 1001).all()
print([str(row) for row in rows])
```

---

#### Go

##### 1. database/sql + MySQL Driver

**Dependency** (`go.mod`):
```go
require github.com/go-sql-driver/mysql v1.7.1
```

**Example**:
```go
package main

import (
    "database/sql"
    "fmt"
    "time"
    _ "github.com/go-sql-driver/mysql"
)

func main() {
    url := "root:your_password@tcp(<connection-endpoint>:33060)/default?timeout=10s"
    db, err := sql.Open("mysql", url)
    if err != nil {
        panic(err)
    }
    defer db.Close()

    // Connection pool configuration
    db.SetMaxOpenConns(20)
    db.SetMaxIdleConns(20)
    db.SetConnMaxIdleTime(8 * time.Minute)
    db.SetConnMaxLifetime(30 * time.Minute)

    // Create table
    db.Exec("CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, age INT, PRIMARY KEY(id))")

    // Insert with parameter binding
    stmt, _ := db.Prepare("UPSERT INTO user_test(id, name, age) VALUES(?, ?, ?)")
    stmt.Exec(1, "zhangsan", 17)

    // Query
    rows, _ := db.Query("SELECT * FROM user_test")
    defer rows.Close()
    for rows.Next() {
        var id, age int
        var name string
        rows.Scan(&id, &name, &age)
        fmt.Printf("id=%d, name=%s, age=%d\n", id, name, age)
    }
}
```

##### 2. GORM Framework

**Dependency**:
```go
require (
    gorm.io/driver/mysql v1.5.1
    gorm.io/gorm v1.25.4
)
```

**Example**:
```go
package main

import (
    "gorm.io/driver/mysql"
    "gorm.io/gorm"
)

type Product struct {
    ID    int64   `gorm:"primaryKey;autoIncrement:false"`
    Code  string  `gorm:"type:varchar"`
    Price float64
}

func main() {
    dsn := "root:your_password@tcp(<connection-endpoint>:33060)/default"
    db, _ := gorm.Open(mysql.Open(dsn), &gorm.Config{})
    
    // Important: Lindorm does not support transactions. Disable them.
    session := db.Session(&gorm.Session{SkipDefaultTransaction: true})

    // Create table
    session.Migrator().CreateTable(&Product{})

    // Write
    session.Create(&Product{ID: 1, Code: "D42", Price: 100.1})

    // Query
    var product Product
    session.First(&product, 1)
}
```

---

#### C/C++

**Installation** (CentOS): `yum install mysql-devel`

**Example**:
```c
#include <stdio.h>
#include "mysql/mysql.h"

int main() {
    MYSQL conn;
    mysql_init(&conn);

    if (!mysql_real_connect(&conn,
        "<connection-endpoint>",
        "root", "your_password", "default", 33060, NULL, 0)) {
        printf("Connection failed: %s\n", mysql_error(&conn));
        return 1;
    }

    // Create table
    mysql_query(&conn, "CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, PRIMARY KEY(id))");

    // Insert data
    mysql_query(&conn, "UPSERT INTO user_test(id, name) VALUES(1, 'test')");

    // Query data
    mysql_query(&conn, "SELECT * FROM user_test");
    MYSQL_RES *result = mysql_store_result(&conn);
    MYSQL_ROW row;
    while ((row = mysql_fetch_row(result))) {
        printf("id=%s, name=%s\n", row[0], row[1]);
    }

    mysql_close(&conn);
    return 0;
}
```

**Compile**: `gcc -o demo demo.c $(mysql_config --cflags) $(mysql_config --libs)`

---

#### C#

**Installation**: `dotnet add package MySql.Data -v 8.0.11`

**Example**:
```csharp
using MySql.Data.MySqlClient;

string connStr = "server=<connection-endpoint>;UID=root;database=default;port=33060;password=your_password";
MySqlConnection conn = new MySqlConnection(connStr);

conn.Open();
MySqlCommand cmd = new MySqlCommand("SHOW DATABASES", conn);
MySqlDataReader rdr = cmd.ExecuteReader();
while (rdr.Read()) {
    Console.WriteLine(rdr[0]);
}
conn.Close();
```

---

#### Rust

**Dependency** (`Cargo.toml`):
```toml
[dependencies]
mysql = "*"
```

**Example**:
```rust
use mysql::*;
use mysql::prelude::*;

fn main() {
    let opts = OptsBuilder::new()
        .ip_or_hostname(Some("<connection-endpoint>"))
        .user(Some("root"))
        .pass(Some("your_password"))
        .db_name(Some("default"))
        .tcp_port(33060);

    let pool = Pool::new(opts).unwrap();
    let mut conn = pool.get_conn().unwrap();

    // Create table
    conn.query_drop("CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, PRIMARY KEY(id))").unwrap();

    // Insert
    conn.exec_drop("UPSERT INTO user_test(id, name) VALUES(?, ?)", (1, "test")).unwrap();

    // Query
    let result: Vec<(i32, String)> = conn.query("SELECT * FROM user_test").unwrap();
    for (id, name) in result {
        println!("id={}, name={}", id, name);
    }
}
```

---

#### PHP

**Requirement**: PHP 8.0+ with the php-mysql module installed

**Example**:
```php
<?php
$lindorm_addr = "<connection-endpoint>";
$lindorm_username = "root";
$lindorm_password = "your_password";
$lindorm_database = "default";
$lindorm_port = 33060;

$conn = mysqli_connect($lindorm_addr, $lindorm_username, $lindorm_password, $lindorm_database, $lindorm_port);

// Create table
mysqli_query($conn, "CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, PRIMARY KEY(id))");

// Insert data
mysqli_query($conn, "UPSERT INTO user_test(id, name) VALUES(1, 'test')");

// Query data
$result = mysqli_query($conn, "SELECT * FROM user_test");
while ($row = mysqli_fetch_array($result)) {
    printf("id=%d, name=%s\n", $row["id"], $row["name"]);
}

mysqli_close($conn);
?>
```

---

#### Node.js

**Installation**: `npm install mysql2`

**Example**:
```javascript
var mysql = require('mysql2');

var connection = mysql.createConnection({
    host: '<connection-endpoint>',
    port: 33060,
    user: 'root',
    password: 'your_password',
    database: 'default',
    connectTimeout: 10000
});

connection.connect(function(err) {
    if (err) throw err;
    console.log("Connected!");

    // Query
    connection.query('SHOW DATABASES', function(err, results) {
        if (err) throw err;
        console.log(results);
    });

    connection.end();
});
```

---

#### ODBC

**Installation** (Linux):
```bash
# Download the MySQL ODBC driver: https://dev.mysql.com/downloads/connector/odbc/
yum install unixODBC-devel
```

**Configuration** (`/etc/odbcinst.ini`):
```ini
[MySQL]
Description = ODBC for MySQL
Driver64 = /usr/lib64/libmyodbc8a.so
Setup64 = /usr/lib64/libmyodbc8w.so
FileUsage = 1
```

**C code example**:
```c
#include <sql.h>
#include <sqlext.h>

int main() {
    SQLHENV env;
    SQLHDBC dbc;
    SQLRETURN ret;

    SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &env);
    SQLSetEnvAttr(env, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, SQL_IS_INTEGER);
    SQLAllocHandle(SQL_HANDLE_DBC, env, &dbc);

    ret = SQLDriverConnect(dbc, NULL,
        (SQLCHAR*)"DRIVER={MySQL};SERVER=<connection-endpoint>;PORT=33060;DATABASE=default;USER=root;PASSWORD=your_password",
        SQL_NTS, NULL, 0, NULL, SQL_DRIVER_COMPLETE);

    if (ret == SQL_SUCCESS) {
        printf("Connection succeeded\n");
        // ... Execute SQL
    }

    SQLFreeHandle(SQL_HANDLE_DBC, dbc);
    SQLFreeHandle(SQL_HANDLE_ENV, env);
    return 0;
}
```

---

### Avatica Protocol, Existing-Workload Maintenance Only

> **Note**: The Avatica protocol is currently in existing-workload maintenance mode and is **not recommended for new users**.
> 
> The Avatica domain format is slightly different:
> - V2: `ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com:30060`
> - V1: `ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com:30060`

#### Java (Avatica)

**Dependency**:
```xml
<dependency>
    <groupId>com.aliyun.lindorm</groupId>
    <artifactId>lindorm-all-client</artifactId>
    <version>2.2.1.3</version>
</dependency>
```

**Connection code**:
```java
String url = "jdbc:lindorm:table:url=http://<connection-endpoint>:30060";
Properties properties = new Properties();
properties.put("user", "root");
properties.put("password", "your_password");
properties.put("database", "default");
Connection connection = DriverManager.getConnection(url, properties);
```

#### Python (Avatica - phoenixdb)

**Installation**: `pip install phoenixdb==1.2.0`

```python
import phoenixdb

connect_kw_args = {
    'lindorm_user': 'root',
    'lindorm_password': 'your_password',
    'database': 'default'
}
database_url = 'http://<connection-endpoint>:30060'
connection = phoenixdb.connect(database_url, autocommit=True, **connect_kw_args)

with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM test_table")
    print(cursor.fetchall())

connection.close()
```

#### Go (Avatica)

**Dependency** (`go.mod`):
```go
require github.com/apache/calcite-avatica-go/v5 v5.0.0
replace github.com/apache/calcite-avatica-go/v5 => github.com/aliyun/alibabacloud-lindorm-go-sql-driver/v5 v5.0.6
```

---

### Best Practices

#### Recommended Connection Parameters

| Parameter | Recommended value | Description |
|------|--------|------|
| sslMode | disabled | Do not use SSL to improve performance |
| useServerPrepStmts | true | Enable server-side prepared statements |
| rewriteBatchedStatements | true | Optimize batch write performance |
| cachePrepStmts | true | Cache prepared statements |
| prepStmtCacheSize | 100 | Number of cached statements |

#### Write Performance Optimization

1. **Use batch writes**: recommended batchSize is 50-100.
2. **Use INSERT instead of UPSERT**: under the MySQL protocol, INSERT has the same semantics as UPSERT but benefits from client-side optimization.
3. **Increase concurrency**: improve write throughput with multiple threads or goroutines.

#### Connection Pool Configuration

1. Do not keep connections alive for too long. Configure `phyMaxUseCount` and `phyTimeoutMillis`.
2. Call `close()` promptly after queries are complete to return connections to the pool.
3. Enable connection keepalive checks.

#### Notes

- **Lindorm does not support transactions**: disable transactions when using ORM frameworks such as GORM.
- **UPDATE supports only single-row updates**: the WHERE condition must specify the full primary key.
- **Idle connection timeout**: the server proactively closes connections that have been idle for 10 minutes.
