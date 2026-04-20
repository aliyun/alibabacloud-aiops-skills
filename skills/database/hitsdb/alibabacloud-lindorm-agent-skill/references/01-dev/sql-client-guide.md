# Lindorm SQL 客户端开发指南

本文档提供多语言连接 Lindorm SQL 的开发参考，包括 Java、Python、Go、C/C++、C#、Rust、PHP、Node.js 等语言的连接示例、连接池配置和框架集成方案。

> **推荐**: MySQL 协议更加稳定可靠，性能更优，推荐新用户使用 MySQL 协议连接宽表引擎。

## 通用前提条件

- 已开通 MySQL 协议兼容功能（控制台 > 数据库连接 > 宽表引擎）
- 已将客户端 IP 添加至白名单
- MySQL 协议端口请以 `SKILL.md` →「代码生成规范 / 端口号速查表」为准

### 连接域名格式（Agent 根据实例类型自动选择）

Lindorm 实例分为 V1 和 V2 两种架构，域名格式不同。Agent 执行时应：

1. **查询实例详情**获取 `ServiceType`
2. **判断架构类型**：
   - `lindorm_v2*` → 使用 V2 域名格式
   - `lindorm` → 使用 V1 域名格式
3. **自动填充**正确的连接地址

| 架构 | ServiceType | 域名格式 | 内网示例 | 公网示例 |
|------|-------------|----------|----------|----------|
| **V2** | `lindorm_v2*` | `*.lindorm.aliyuncs.com` | `ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com:33060` | `ld-xxx-proxy-lindorm-pub.lindorm.aliyuncs.com:33060` |
| **V1** | `lindorm` | `*.lindorm.rds.aliyuncs.com` | `ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com:33060` | `ld-xxx-proxy-lindorm-public.lindorm.rds.aliyuncs.com:33060` |

> **V1 宽表引擎有两个 MySQL 地址**：`proxy-lindorm` 和 `proxy-sql-lindorm`，功能相同，任选其一即可。
> 
> **V1 公网地址需开通公网访问后才可用**，默认仅提供内网地址。公网地址后缀为 `-public`。
> 
> **获取方式**：控制台 → 实例详情 → 数据库连接，或执行 `aliyun hitsdb get-lindorm-instance-engine-list --instance-id <id>`

---

## 注意事项
- 只能基于本 Skill 文档中明确记载的内容回答用户问题，严禁推测、联想或凭训练知识生成文档中不存在的 SQL 语法、参数、功能或配置。
- 如果文档中没有相关信息，必须明确告知用户"当前文档未收录此内容"，并引导用户查阅阿里云官方文档（help.aliyun.com）确认。
- 生成的代码示例必须基于文档中的模板，参数和语法必须与文档一致。

---

## 执行步骤

### 步骤1：识别用户程序开发语言

---

### 步骤2：根据用户开发语言选择连接方式

#### 官方使用文档地址

**基于 SQL 的应用开发：**
https://help.aliyun.com/zh/lindorm/user-guide/add-connect-wide-table-engines-through-lindorm-query-language/

**使用 MySQL 协议的应用开发(推荐)**

1. **Java**
   - JDBC接口：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-jdbc-interface
   - 连接池Druid：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-connection-pool-druid
   - LindormDataSource：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-lindormdatasource
   - ORM框架MyBatis：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-orm-framework-mybatis
2. **Python**
   - 原生Python：https://help.aliyun.com/zh/lindorm/user-guide/python-based-application-development-1
   - ORM框架：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-python-orm-framework
3. **Go**
   - 原生Go：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-go
   - ORM框架：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-go-orm-framework
4. **C**
   - C API：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-c-api
5. **C#**
   - 原生C#：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-c
6. **Rust**
   - 原生Rust：https://help.aliyun.com/zh/lindorm/user-guide/rust-based-application-development
7. **PHP**
   - 原生PHP：https://help.aliyun.com/zh/lindorm/user-guide/php-based-application-development
8. **Node.js**
   - 原生Node.js：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-node-js
9. **ODBC**
   - ODBC接口：https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-odbc
   
**Avatica协议**（仅存量维护）

1. **Java**
- JDBC接口：https://help.aliyun.com/zh/lindorm/user-guide/call-java-api-operations-in-sql-based-connection-to-and-usage-of-lindormtable
- 连接池Druid：https://help.aliyun.com/zh/lindorm/user-guide/through-the-connection-pool-druid-connection-wide-table-engine

2. **Python**
- DB-API：https://help.aliyun.com/zh/lindorm/user-guide/use-the-lindorm-sql-api-for-a-non-java-language-to-connect-to-and-use-the-wide-table-engine-lindormtable
- 连接池DBUtils：https://help.aliyun.com/zh/lindorm/user-guide/use-dbutils-to-connect-to-lindormtable

3. **Go**
- database/sql接口：https://help.aliyun.com/zh/lindorm/user-guide/use-the-apis-provided-by-the-database-or-sql-library-of-go-to-develop-applications

---

### 步骤3：提供连接示例

---

## 常见连接示例

### MySQL 协议（推荐）

所有示例使用 `<您的连接地址>` 占位符，Agent 根据实例 ServiceType 自动填充正确的 V1/V2 域名。

#### Java

##### 1. JDBC 接口

**依赖**:
```xml
<dependency>
    <groupId>com.mysql</groupId>
    <artifactId>mysql-connector-j</artifactId>
    <version>8.3.0</version>
</dependency>
```

**连接代码**:
```java
Class.forName("com.mysql.cj.jdbc.Driver");

String username = "root";
String password = "your_password";
String database = "default";
String url = "jdbc:mysql://<您的连接地址>:33060/" + database 
    + "?sslMode=disabled&allowPublicKeyRetrieval=true&useServerPrepStmts=true"
    + "&useLocalSessionState=true&rewriteBatchedStatements=true&cachePrepStmts=true"
    + "&prepStmtCacheSize=100&prepStmtCacheSqlLimit=50000000";

Properties properties = new Properties();
properties.put("user", username);
properties.put("password", password);
Connection connection = DriverManager.getConnection(url, properties);
```

**CRUD 示例**:
```java
// 创建表
try (Statement stmt = connection.createStatement()) {
    stmt.executeUpdate("CREATE TABLE IF NOT EXISTS user_test(id VARCHAR, name VARCHAR, PRIMARY KEY(id))");
}

// 批量插入 (推荐使用 INSERT，语义与 UPSERT 相同)
String sql = "INSERT INTO user_test(id, name) VALUES(?, ?)";
try (PreparedStatement ps = connection.prepareStatement(sql)) {
    for (int i = 0; i < 100; i++) {
        ps.setString(1, "id" + i);
        ps.setString(2, "name" + i);
        ps.addBatch();
    }
    ps.executeBatch();  // batchSize 建议 50-100
}

// 查询
try (PreparedStatement ps = connection.prepareStatement("SELECT * FROM user_test WHERE id = ?")) {
    ps.setString(1, "id1");
    ResultSet rs = ps.executeQuery();
    while (rs.next()) {
        System.out.println("id=" + rs.getString(1) + ", name=" + rs.getString(2));
    }
}

// 关闭连接
connection.close();
```

##### 2. Druid 连接池

**依赖**:
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

**配置文件** (`druid.properties`):
```properties
driverClassName=com.mysql.cj.jdbc.Driver
url=jdbc:mysql://<您的连接地址>:33060/default?sslMode=disabled&allowPublicKeyRetrieval=true&useServerPrepStmts=true&useLocalSessionState=true&rewriteBatchedStatements=true&cachePrepStmts=true&prepStmtCacheSize=100&prepStmtCacheSqlLimit=50000000&socketTimeout=120000
username=root
password=your_password

init=true
initialSize=10
maxActive=40
minIdle=40
maxWait=30000

# 避免连接负载不均衡
druid.phyMaxUseCount=10000
phyTimeoutMillis=1800000

# 连接保活
druid.keepAlive=true
druid.keepAliveBetweenTimeMillis=120000
timeBetweenEvictionRunsMillis=60000
minEvictableIdleTimeMillis=300000
maxEvictableIdleTimeMillis=600000

testWhileIdle=true
testOnBorrow=false
testOnReturn=false
```

**初始化连接池**:
```java
Properties properties = new Properties();
InputStream inputStream = getClass().getClassLoader().getResourceAsStream("druid.properties");
properties.load(inputStream);
DataSource dataSource = DruidDataSourceFactory.createDataSource(properties);

// 使用连接
try (Connection conn = dataSource.getConnection()) {
    // 执行 SQL...
}
```

##### 3. LindormDataSource（官方推荐）

封装了开箱即用的最佳配置，支持多可用区就近访问。

**依赖**:
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

**使用方式**:
```java
LindormDataSourceConfig config = new LindormDataSourceConfig();
config.setJdbcUrl("jdbc:mysql://<您的连接地址>:33060/default");
config.setUsername("root");
config.setPassword("your_password");
config.setMaximumPoolSize(30);
LindormDataSource dataSource = new LindormDataSource(config);

try (Connection conn = dataSource.getConnection()) {
    // 执行 SQL...
}
```

**Spring Boot 2.x 集成**:
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
      jdbc-url: jdbc:mysql://<您的连接地址>:33060/default
      username: root
      password: your_password
      maximum-pool-size: 30
```

##### 4. MyBatis 框架

**依赖**:
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

**配置文件** (`mybatis-config.xml`):
```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE configuration PUBLIC "-//mybatis.org//DTD Config 3.0//EN" "https://mybatis.org/dtd/mybatis-3-config.dtd">
<configuration>
    <environments default="development">
        <environment id="development">
            <transactionManager type="JDBC"/>
            <dataSource type="POOLED">
                <property name="driver" value="com.mysql.cj.jdbc.Driver"/>
                <property name="url" value="jdbc:mysql://<您的连接地址>:33060/default?sslMode=disabled&amp;allowPublicKeyRetrieval=true"/>
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

**Mapper 示例**:
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

**安装**: `pip install mysql-connector-python==8.0.15`

**直连模式**:
```python
import mysql.connector

connection = mysql.connector.connect(
    host='<您的连接地址>',
    port=33060,
    user='root',
    passwd='your_password',
    database='default'
)
cursor = connection.cursor(prepared=True)

# 创建表
cursor.execute("CREATE TABLE IF NOT EXISTS test_python(c1 INTEGER, c2 INTEGER, c3 VARCHAR, PRIMARY KEY(c1))")

# 插入数据 (参数化防止 SQL 注入)
cursor.execute("UPSERT INTO test_python(c1, c2, c3) VALUES(?, ?, ?)", (1, 1, 'value1'))

# 查询
cursor.execute("SELECT * FROM test_python WHERE c1 = ?", (1,))
print(cursor.fetchall())

cursor.close()
connection.close()
```

**连接池模式**:
```python
from mysql.connector import pooling

connection_pool = pooling.MySQLConnectionPool(
    pool_name="mypool",
    pool_size=20,
    host='<您的连接地址>',
    port=33060,
    user='root',
    password='your_password',
    database='default'
)

connection = connection_pool.get_connection()
cursor = connection.cursor(prepared=True)
# ... 执行 SQL
cursor.close()
connection.close()  # 返回到连接池
```

##### 2. SQLAlchemy ORM

**安装**:
```bash
pip install PyMySQL
pip install SQLAlchemy
```

**示例**:
```python
from sqlalchemy import create_engine, Column, String, Integer, Float
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Player(Base):
    __tablename__ = 'player'
    player_id = Column(Integer, primary_key=True, autoincrement=False)
    player_name = Column(String(255))
    player_height = Column(Float)

engine = create_engine('mysql+pymysql://root:your_password@<您的连接地址>:33060/default')
Session = sessionmaker(bind=engine)

# 建表
Base.metadata.create_all(engine)

# 写入数据
session = Session()
session.add(Player(player_id=1001, player_name="john", player_height=2.08))
session.commit()

# 查询
rows = session.query(Player).filter(Player.player_id == 1001).all()
print([str(row) for row in rows])
```

---

#### Go

##### 1. database/sql + MySQL Driver

**依赖** (`go.mod`):
```go
require github.com/go-sql-driver/mysql v1.7.1
```

**示例**:
```go
package main

import (
    "database/sql"
    "fmt"
    "time"
    _ "github.com/go-sql-driver/mysql"
)

func main() {
    url := "root:your_password@tcp(<您的连接地址>:33060)/default?timeout=10s"
    db, err := sql.Open("mysql", url)
    if err != nil {
        panic(err)
    }
    defer db.Close()

    // 连接池配置
    db.SetMaxOpenConns(20)
    db.SetMaxIdleConns(20)
    db.SetConnMaxIdleTime(8 * time.Minute)
    db.SetConnMaxLifetime(30 * time.Minute)

    // 创建表
    db.Exec("CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, age INT, PRIMARY KEY(id))")

    // 插入 (参数绑定方式)
    stmt, _ := db.Prepare("UPSERT INTO user_test(id, name, age) VALUES(?, ?, ?)")
    stmt.Exec(1, "zhangsan", 17)

    // 查询
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

##### 2. GORM 框架

**依赖**:
```go
require (
    gorm.io/driver/mysql v1.5.1
    gorm.io/gorm v1.25.4
)
```

**示例**:
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
    dsn := "root:your_password@tcp(<您的连接地址>:33060)/default"
    db, _ := gorm.Open(mysql.Open(dsn), &gorm.Config{})
    
    // 重要: Lindorm 不支持事务，必须关闭
    session := db.Session(&gorm.Session{SkipDefaultTransaction: true})

    // 建表
    session.Migrator().CreateTable(&Product{})

    // 写入
    session.Create(&Product{ID: 1, Code: "D42", Price: 100.1})

    // 查询
    var product Product
    session.First(&product, 1)
}
```

---

#### C/C++

**安装** (CentOS): `yum install mysql-devel`

**示例**:
```c
#include <stdio.h>
#include "mysql/mysql.h"

int main() {
    MYSQL conn;
    mysql_init(&conn);

    if (!mysql_real_connect(&conn,
        "<您的连接地址>",
        "root", "your_password", "default", 33060, NULL, 0)) {
        printf("连接失败: %s\n", mysql_error(&conn));
        return 1;
    }

    // 创建表
    mysql_query(&conn, "CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, PRIMARY KEY(id))");

    // 插入数据
    mysql_query(&conn, "UPSERT INTO user_test(id, name) VALUES(1, 'test')");

    // 查询数据
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

**编译**: `gcc -o demo demo.c $(mysql_config --cflags) $(mysql_config --libs)`

---

#### C#

**安装**: `dotnet add package MySql.Data -v 8.0.11`

**示例**:
```csharp
using MySql.Data.MySqlClient;

string connStr = "server=<您的连接地址>;UID=root;database=default;port=33060;password=your_password";
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

**依赖** (`Cargo.toml`):
```toml
[dependencies]
mysql = "*"
```

**示例**:
```rust
use mysql::*;
use mysql::prelude::*;

fn main() {
    let opts = OptsBuilder::new()
        .ip_or_hostname(Some("<您的连接地址>"))
        .user(Some("root"))
        .pass(Some("your_password"))
        .db_name(Some("default"))
        .tcp_port(33060);

    let pool = Pool::new(opts).unwrap();
    let mut conn = pool.get_conn().unwrap();

    // 创建表
    conn.query_drop("CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, PRIMARY KEY(id))").unwrap();

    // 插入
    conn.exec_drop("UPSERT INTO user_test(id, name) VALUES(?, ?)", (1, "test")).unwrap();

    // 查询
    let result: Vec<(i32, String)> = conn.query("SELECT * FROM user_test").unwrap();
    for (id, name) in result {
        println!("id={}, name={}", id, name);
    }
}
```

---

#### PHP

**要求**: PHP 8.0+，安装 php-mysql 模块

**示例**:
```php
<?php
$lindorm_addr = "<您的连接地址>";
$lindorm_username = "root";
$lindorm_password = "your_password";
$lindorm_database = "default";
$lindorm_port = 33060;

$conn = mysqli_connect($lindorm_addr, $lindorm_username, $lindorm_password, $lindorm_database, $lindorm_port);

// 创建表
mysqli_query($conn, "CREATE TABLE IF NOT EXISTS user_test(id INT, name VARCHAR, PRIMARY KEY(id))");

// 插入数据
mysqli_query($conn, "UPSERT INTO user_test(id, name) VALUES(1, 'test')");

// 查询数据
$result = mysqli_query($conn, "SELECT * FROM user_test");
while ($row = mysqli_fetch_array($result)) {
    printf("id=%d, name=%s\n", $row["id"], $row["name"]);
}

mysqli_close($conn);
?>
```

---

#### Node.js

**安装**: `npm install mysql2`

**示例**:
```javascript
var mysql = require('mysql2');

var connection = mysql.createConnection({
    host: '<您的连接地址>',
    port: 33060,
    user: 'root',
    password: 'your_password',
    database: 'default',
    connectTimeout: 10000
});

connection.connect(function(err) {
    if (err) throw err;
    console.log("Connected!");

    // 查询
    connection.query('SHOW DATABASES', function(err, results) {
        if (err) throw err;
        console.log(results);
    });

    connection.end();
});
```

---

#### ODBC

**安装** (Linux):
```bash
# 下载 MySQL ODBC 驱动: https://dev.mysql.com/downloads/connector/odbc/
yum install unixODBC-devel
```

**配置** (`/etc/odbcinst.ini`):
```ini
[MySQL]
Description = ODBC for MySQL
Driver64 = /usr/lib64/libmyodbc8a.so
Setup64 = /usr/lib64/libmyodbc8w.so
FileUsage = 1
```

**C 代码示例**:
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
        (SQLCHAR*)"DRIVER={MySQL};SERVER=<您的连接地址>;PORT=33060;DATABASE=default;USER=root;PASSWORD=your_password",
        SQL_NTS, NULL, 0, NULL, SQL_DRIVER_COMPLETE);

    if (ret == SQL_SUCCESS) {
        printf("连接成功\n");
        // ... 执行 SQL
    }

    SQLFreeHandle(SQL_HANDLE_DBC, dbc);
    SQLFreeHandle(SQL_HANDLE_ENV, env);
    return 0;
}
```

---

### Avatica 协议（仅存量维护）

> **注意**: Avatica 协议目前处于存量维护状态，**不推荐新用户使用**。
> 
> Avatica 域名格式略有不同：
> - V2: `ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com:30060`
> - V1: `ld-xxx-proxy-lindorm.lindorm.rds.aliyuncs.com:30060`

#### Java (Avatica)

**依赖**:
```xml
<dependency>
    <groupId>com.aliyun.lindorm</groupId>
    <artifactId>lindorm-all-client</artifactId>
    <version>2.2.1.3</version>
</dependency>
```

**连接代码**:
```java
String url = "jdbc:lindorm:table:url=http://<您的连接地址>:30060";
Properties properties = new Properties();
properties.put("user", "root");
properties.put("password", "your_password");
properties.put("database", "default");
Connection connection = DriverManager.getConnection(url, properties);
```

#### Python (Avatica - phoenixdb)

**安装**: `pip install phoenixdb==1.2.0`

```python
import phoenixdb

connect_kw_args = {
    'lindorm_user': 'root',
    'lindorm_password': 'your_password',
    'database': 'default'
}
database_url = 'http://<您的连接地址>:30060'
connection = phoenixdb.connect(database_url, autocommit=True, **connect_kw_args)

with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM test_table")
    print(cursor.fetchall())

connection.close()
```

#### Go (Avatica)

**依赖** (`go.mod`):
```go
require github.com/apache/calcite-avatica-go/v5 v5.0.0
replace github.com/apache/calcite-avatica-go/v5 => github.com/aliyun/alibabacloud-lindorm-go-sql-driver/v5 v5.0.6
```

---

### 最佳实践

#### 连接参数建议

| 参数 | 建议值 | 说明 |
|------|--------|------|
| sslMode | disabled | 不使用 SSL，提升性能 |
| useServerPrepStmts | true | 启用服务端预处理 |
| rewriteBatchedStatements | true | 优化批量写入性能 |
| cachePrepStmts | true | 缓存预处理语句 |
| prepStmtCacheSize | 100 | 缓存数量 |

#### 写入性能优化

1. **使用 Batch 写入**: batchSize 建议 50-100
2. **使用 INSERT 而非 UPSERT**: MySQL 协议下 INSERT 语义与 UPSERT 相同，但有客户端优化
3. **增加并发**: 通过多线程/协程增加写入吞吐

#### 连接池配置

1. 连接保持时间不宜过长，建议配置 `phyMaxUseCount` 和 `phyTimeoutMillis`
2. 执行完查询后及时调用 `close()` 归还连接
3. 建议启用连接保活检测

#### 注意事项

- **Lindorm 不支持事务**: 使用 GORM 等 ORM 框架时需关闭事务
- **UPDATE 仅支持单行**: WHERE 条件必须指定全部主键
- **连接空闲超时**: 服务端会主动断开空闲 10 分钟的连接
