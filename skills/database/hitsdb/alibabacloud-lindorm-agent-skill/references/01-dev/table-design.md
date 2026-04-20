# Lindorm SQL 建表语句指南

本文档提供 Lindorm 宽表建表语句的完整指南，包括语法、最佳实践和高级特性。

## 数据类型

### 数据类型查找规则
当使用 Lindorm 宽表引擎建表时，需要了解其支持的数据类型。Lindorm 宽表引擎支持基础数据类型、JSON 数据类型和空间数据类型。
1. 当用户提到的数据类型不在 Lindorm 宽表引擎支持的数据类型范围内时，需要提示用户 Lindorm 宽表引擎支持的数据类型，并提供相关文档链接。
2. 数据类型优先从下文的表格中选择。
3. 当数据类型不在下文表格中时，需要查找官方文档：
   - **基础数据类型**: https://help.aliyun.com/zh/lindorm/developer-reference/basic-data-types
   - **JSON 数据类型**: https://help.aliyun.com/zh/lindorm/developer-reference/json-data-type
   - **空间数据类型**: https://help.aliyun.com/zh/lindorm/developer-reference/spatial-data-type-1
4. 如果数据类型仍然不在支持范围内，需要提示用户不支持该数据类型或联系技术支持。

### 基本数据类型

| 类型 | 字节长度 | 说明 | Java 映射 | 取值范围/精度 |
|------|----------|------|-----------|----------------|
| BOOLEAN | 1 字节 | 布尔型 | java.lang.Boolean | true / false |
| TINYINT | 1 字节 | 8 位精确数值 | java.lang.Byte | -128 ~ 127 (有符号) |
| SMALLINT | 2 字节 | 16 位精确数值 | java.lang.Short | -32768 ~ 32767 |
| INTEGER | 4 字节 | 32 位精确数值 | java.lang.Integer | -2^31 ~ 2^31-1 |
| BIGINT | 8 字节 | 64 位精确数值 | java.lang.Long | -2^63 ~ 2^63-1 |
| FLOAT | 4 字节 | 单精度浮点数 | java.lang.Float | 约 7 位有效数字 |
| DOUBLE | 8 字节 | 双精度浮点数 | java.lang.Double | 约 15-17 位有效数字，科学计数法表示 |
| DECIMAL(precision, scale) | 变长 | 高精度十进制 | java.math.BigDecimal | precision: [1,38], scale: [0,precision] |
| VARCHAR | 变长 | 变长字符串 | java.lang.String | 最大 2MB，支持中文 |
| CHAR(n) | n 字节 | 定长字符串 | java.lang.String | 固定长度 n，不足自动补空格 |
| BINARY(n) | n 字节 | 定长二进制 | byte[] | 固定 n 字节，不足补 0，超出截断 |
| VARBINARY | 变长 | 变长二进制 | byte[] | 作为主键时只能是最后一列 |
| DATE | 4 字节 | 日期（仅日期无时间） | java.sql.Date | YYYY-MM-DD，**不推荐**（时区转换易出错） |
| TIME | 4 字节 | 时间 | java.sql.Time | HH:mm:ss，受时区影响 |
| TIMESTAMP | 8 字节 | 时间戳 | java.sql.Timestamp | 0001-01-01 00:00:00 ~ 9999-12-31 23:59:59 |

**重要说明**:
- **TIMESTAMP**: Lindorm 支持的最大值为 `9999-12-31 23:59:59`，而 MySQL 仅支持到 `2038-01-19 03:14:07`
- **DECIMAL**: 适用于金额等高精度场景，监控等精度要求不高的场景推荐使用 FLOAT/DOUBLE
- **DATE/TIME**: 在时区转换过程中易出现日期错误，建议避免使用

### JSON 数据类型

**适用引擎**: 仅宽表引擎支持（要求版本 2.6.2+）

**限制**: 主键列不支持 JSON 类型

**建表语法**:
```sql
-- 创建表时指定 JSON 列
CREATE TABLE tb (
    p1 INT,
    c1 VARCHAR,
    c2 JSON,
    PRIMARY KEY(p1)
);

-- 修改表添加 JSON 列
ALTER TABLE tb ADD c3 JSON;
```

### 类型使用建议

- **主键列**: 推荐使用 VARCHAR 或 BIGINT，VARBINARY 只能作为最后一列主键
- **时间戳**: 优先使用 TIMESTAMP（范围更大），或使用 BIGINT (毫秒)
- **大文本**: 使用 VARCHAR，最大 2MB
- **二进制**: 使用 BINARY(n) 或 VARBINARY
- **高精度数值**: 使用 DECIMAL(如金额)
- **一般数值**: 使用 INTEGER/BIGINT/FLOAT/DOUBLE
- **避免使用**: DATE、TIME（时区问题）

## 基础语法

**注意事项**:
- 只能基于本 Skill 文档中明确记载的内容回答用户问题，严禁推测、联想或生成文档中不存在的 SQL 语法、参数、功能或配置。
- 如果文档中没有相关信息，必须明确告知用户“当前文档未收录此内容”，并引导用户查阅官方文档。
- 生成的代码示例必须基于文档中的模板，参数和语法必须与文档一致。

### CREATE TABLE 语法

```sql
CREATE TABLE [ IF NOT EXISTS ] table_identifier
'('
  column_definition
  ( ',' column_definition )*
  ',' PRIMARY KEY '(' primary_key ')'
  ( ',' {KEY|INDEX} [index_identifier]
    [ USING index_method_definition ]
    [ INCLUDE column_identifier ( ',' column_identifier )* ]
    [ WITH index_options ]
  )*
')'
[ WITH table_options ]
```

**语法要素说明：**

| 语法要素 | 说明                                                                    |
|---------|-----------------------------------------------------------------------|
| column_definition | `column_identifier data_type [ NOT NULL ] [ DEFAULT default_value ] ` |
| primary_key | `column_identifier [ ',' column_identifier (ASC\|DESC)]`              |
| index_method_definition | `{ KV \| SEARCH }`                                                    |
| index_options | `'(' option_definition (',' option_definition )*')'`                  |
| table_options | `'(' option_definition (',' option_definition )* ')'`                 |
| option_definition | `option_identifier '=' string_literal`                                |

### DEFAULT 子句

列定义支持通过 DEFAULT 子句设置默认值。

**限制：**
- 默认值只能是列类型的常量表达式或无参函数 `NOW()`
- 不可以设置为 NULL

**示例：**
```sql
CREATE TABLE orders (
  id VARCHAR NOT NULL,
  status INTEGER DEFAULT -1,
  create_time TIMESTAMP DEFAULT NOW(),
  remark VARCHAR DEFAULT 'pending',
  PRIMARY KEY(id)
);
```

### 命名规范

**表名（table_identifier）：**
- 可包含数字、大小写英文字符、半角句号（.）、中划线（-）和下划线（_）
- 不能以半角句号（.）或中划线（-）开头
- 长度为 1~255 字符

**列名（column_identifier）：**
- 可包含数字、大小写英文字符、半角句号（.）、中划线（-）和下划线（_）
- 不允许使用系统保留关键字
- 长度不能超过 255 字节

### 基础建表示例

```sql
-- 基础表
CREATE TABLE orders (
  channel VARCHAR NOT NULL,
  id VARCHAR NOT NULL,
  ts TIMESTAMP NOT NULL,
  status VARCHAR,
  location VARCHAR,
  PRIMARY KEY(channel, id, ts)
);

-- 带表属性的表
CREATE TABLE orders (
  channel VARCHAR NOT NULL,
  id VARCHAR NOT NULL,
  ts TIMESTAMP NOT NULL,
  status VARCHAR,
  PRIMARY KEY(channel, id, ts)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '86400'
);
```

## 主键设计

### 主键特性

- **不可修改**：主键在建表时确定，建表后不可增加、删除、更换顺序或修改数据类型
- **唯一性**：所有主键列共同组成 RowKey，在一张表里是唯一的
- **聚簇索引**：数据按照主键顺序存储，遵循最左匹配原则

### 主键限制

- 单个主键列的最大长度为 2 KB
- 所有主键列的长度之和不能超过 30 KB
- 单个非主键列的最大长度不能超过 2 MB

### 主键设计最佳实践

#### 避免热点问题

```sql
-- 错误示例：递增主键导致写入热点
CREATE TABLE logs (
  timestamp BIGINT NOT NULL,
  message VARCHAR,
  PRIMARY KEY(timestamp)
);

-- 正确示例：使用 HASH 打散
CREATE TABLE logs (
  timestamp BIGINT NOT NULL,
  hostname VARCHAR NOT NULL,
  message VARCHAR,
  PRIMARY KEY(hash32(timestamp), timestamp, hostname)
);
```

#### 主键设计原则

1. **主键第一列尽量分散**：不建议使用相同前缀
2. **避免自增数据**：如时间戳列作为第一列
3. **避免枚举值**：如 order_type 作为第一列
4. **主键列数量**：建议控制在 1~3 个
5. **主键值长度**：建议尽量短小，使用固定长度类型

#### 常见场景设计

**日志/时序数据：**
```sql
-- 查询某机器某指标某段时间数据
CREATE TABLE logs (
  hostname VARCHAR NOT NULL,
  log_event VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  content VARCHAR,
  PRIMARY KEY(hostname, log_event, timestamp)
);

-- 查询最新数据（倒序）
CREATE TABLE logs (
  hostname VARCHAR NOT NULL,
  log_event VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  content VARCHAR,
  PRIMARY KEY(hostname, log_event, timestamp DESC)
);

-- 时间维度数据量大，使用分桶打散
CREATE TABLE logs (
  bucket BIGINT NOT NULL,
  timestamp BIGINT NOT NULL,
  hostname VARCHAR NOT NULL,
  log_event VARCHAR NOT NULL,
  content VARCHAR,
  PRIMARY KEY(bucket, timestamp, hostname, log_event)
);
-- 写入时：bucket = timestamp % numBuckets
```

**交易数据：**
```sql
-- 按卖家查询
CREATE TABLE seller_orders (
  seller_id VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  order_number VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(seller_id, timestamp, order_number)
);

-- 按买家查询
CREATE TABLE buyer_orders (
  buyer_id VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  order_number VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(buyer_id, timestamp, order_number)
);

-- 按订单号查询
CREATE TABLE order_index (
  order_number VARCHAR NOT NULL,
  seller_id VARCHAR,
  buyer_id VARCHAR,
  PRIMARY KEY(order_number)
);
```

## HASH 主键打散

使用 HASH 函数将数据分散到不同分片，避免数据倾斜和热点问题。

### 支持的 HASH 算法

| 算法 | 说明 |
|------|------|
| hash8 | 8 位 HASH，存储消耗最小 |
| hash32 | 32 位 HASH，每对 keyValue 额外消耗 4 Bytes |
| hash64 | 64 位 HASH，存储消耗最大 |

### 使用示例

```sql
-- 对单个主键列使用 HASH
CREATE TABLE t1 (
  p1 BIGINT,
  p2 INTEGER,
  c1 INTEGER,
  c2 VARCHAR,
  PRIMARY KEY(hash32(p1), p1, p2)
);

-- 对多个主键列使用 HASH
CREATE TABLE t2 (
  p1 BIGINT,
  p2 INTEGER,
  c1 INTEGER,
  c2 VARCHAR,
  PRIMARY KEY(hash8(p1, p2), p1, p2)
);
```

### 注意事项

- HASH 函数表达式必须放在主键最前面
- 已使用 HASH 算法的主键列不支持修改
- 查询时必须指定所有已使用 HASH 算法的主键列的值
- HASH 列只支持等值查询，不支持范围查询
- 使用主键 HASH 打散后，不支持 bulkload 方式导入数据

## 表属性（WITH 子句）

### 常用表属性

| 属性 | 类型 | 说明 |
|------|------|------|
| COMPRESSION | STRING | 压缩算法：SNAPPY、ZSTD、LZ4。默认 ZSTD |
| TTL | INT | 数据有效期，单位秒。默认为空（不过期） |
| NUMREGIONS | INT | 预分区 Region 数 |
| STARTKEY / ENDKEY | 与主键第一列类型相同 | 预分区起止 Key |
| SPLITKEYS | 与主键第一列类型相同 | 预分区分裂点 |
| DYNAMIC_COLUMNS | STRING | 是否开启动态列，'true' 或 'false' |
| MUTABILITY | STRING | 索引写入模式：IMMUTABLE、MUTABLE_LATEST 等 |
| CONSISTENCY | STRING | 一致性级别：eventual（默认）、strong |

### 示例

```sql
-- 设置压缩和 TTL
CREATE TABLE logs (
  id VARCHAR NOT NULL,
  content VARCHAR,
  PRIMARY KEY(id)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '2592000'  -- 30 天
);

-- 设置预分区
CREATE TABLE orders (
  id VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(id)
) WITH (
  NUMREGIONS = '16',
  STARTKEY = 'a',
  ENDKEY = 'z'
);
```

## 动态列

动态列允许在建表时未显式定义的列在运行时动态写入。

### 开启动态列

```sql
-- 建表时开启
CREATE TABLE t_dynamic (
  p1 INT,
  c1 INT,
  c2 VARCHAR,
  PRIMARY KEY(p1)
) WITH (DYNAMIC_COLUMNS = 'true');

-- 已有表开启
ALTER TABLE t_dynamic SET 'DYNAMIC_COLUMNS' = 'true';
```

### 写入动态列

动态列的数据类型均为 VARBINARY（字节数组）。

```sql
-- SQL 文本写入（值为 HexString）
UPSERT INTO t_dynamic (p1, c2, c3) VALUES (1, '1', '41');

-- 使用 x'' 语法指定 HexString（SQL 引擎 2.6.8+）
UPSERT INTO t_dynamic (p1, c4) VALUES (3, x'ef0011');
```

### 查询动态列

```sql
-- 显式指定动态列
SELECT p1, c2, c3, c4 FROM t_dynamic WHERE p1 = 1;

-- 使用 SELECT *（必须添加 LIMIT）
SELECT * FROM t_dynamic LIMIT 10;
```

## 通配符列

通配符列实现多数据类型动态列写入，解决动态列仅支持 VARBINARY 的限制。

### 支持的通配符

| 通配符 | 说明 |
|--------|------|
| * | 匹配任意字符序列，包括空序列 |
| ? | 匹配任意单个字符 |

### 使用示例

```sql
-- 创建带通配符列的表
CREATE TABLE tb (
  pk INTEGER,
  c1 VARCHAR,
  `c2*` BIGINT,
  `c3*` VARCHAR,
  PRIMARY KEY(pk)
) WITH (wildcard_column = 'c2*,c3*');

-- 写入数据
UPSERT INTO tb(pk, c1, c2, c21, c22, c31) VALUES (1, 'a1', 2, 21, 22, 'c3');
```

### 限制

- 通配符列不能作为主键
- SELECT * 查询必须添加 LIMIT
- 仅支持为通配符列创建搜索索引，不支持二级索引
- 不支持使用通配符列名进行数据查询，必须使用实际列名

## 索引（建表时创建）

在 CREATE TABLE 语句中通过 KEY 或 INDEX 子句创建索引。

### 语法

```sql
CREATE TABLE table_name (
  column_definitions,
  PRIMARY KEY(pk_columns),
  {KEY|INDEX} [index_name]
    [ USING { KV | SEARCH } ]
    [ INCLUDE (columns) ]
    [ WITH (index_options) ]
);
```

### 索引类型

| 类型 | 关键字 | 说明 |
|------|--------|------|
| 二级索引 | KV（默认） | 适用于非主键匹配场景 |
| 搜索索引 | SEARCH | 适用于多维查询、分词、模糊查询场景 |

### 冗余列设置

在建表时创建索引，可通过 INCLUDE 或 WITH (INDEX_COVERED_TYPE) 设置冗余列：

```sql
-- 显式指定冗余列
CREATE TABLE sensor (
    device_id VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    time TIMESTAMP NOT NULL,
    temperature DOUBLE,
    humidity BIGINT,
    PRIMARY KEY(device_id, region, time),
    KEY (temperature, time) INCLUDE (humidity)
);

-- 冗余所有已定义列
CREATE TABLE sensor (
    device_id VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    time TIMESTAMP NOT NULL,
    temperature DOUBLE,
    humidity BIGINT,
    PRIMARY KEY(device_id, region, time),
    KEY (temperature, time) WITH (INDEX_COVERED_TYPE = 'COVERED_ALL_COLUMNS_IN_SCHEMA')
);
```

### 示例

```sql
-- 创建表同时创建二级索引
CREATE TABLE orders (
  order_id VARCHAR NOT NULL,
  user_id VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(order_id),
  INDEX idx_user USING KV (user_id) INCLUDE (amount)
);

-- 创建表同时创建搜索索引
CREATE TABLE products (
  id VARCHAR NOT NULL,
  name VARCHAR,
  description VARCHAR,
  PRIMARY KEY(id),
  INDEX idx_search USING SEARCH (name, description)
);
```

## CREATE INDEX 语法

单独创建索引的语法。

```sql
CREATE INDEX [IF NOT EXISTS] [index_name]
  [ USING { KV | SEARCH | COLUMNAR } ]
  ON table_name (index_key_expression)
  [ INCLUDE (columns) ]
  [ { ASYNC | SYNC } ]
  [ WITH (index_options) ];
```

### 索引类型

| 参数 | 索引类型 | 说明 |
|------|----------|------|
| KV | 二级索引 | 默认类型，每表最多 3 个 |
| SEARCH | 搜索索引 | 全文搜索，每表最多 1 个 |
| COLUMNAR | 列存索引 | 分析计算，每表最多 1 个 |

### 列存索引开通条件

**旧版列存索引**（默认，已正式发布）：

| 引擎 | 作用 |
|------|------|
| 宽表引擎 | 源数据存储 |
| LindormDFS | 文件存储（版本 >= 4.0.0） |
| 计算引擎 | 执行分析查询 |

**开通说明**：

1. **开通 Lindorm 计算引擎**
2. **购买计算资源**（为宽表引擎到计算引擎的数据同步购买计算资源）

**控制台开通路径**：

1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
2. 在实例列表页，单击**目标实例ID**
3. 在左侧导航栏，选择**宽表引擎**
4. 单击**列存索引**页签，并单击**立即开通**
5. 在弹出的对话框中单击**确定**

**创建列存索引示例**（旧版，已正式发布）：

```sql
-- 创建列存索引（旧版，同步延迟约15分钟）
CREATE INDEX idx_columnar USING COLUMNAR ON my_table(
  pk0, pk1, pt_d, col0, col1
)
PARTITION BY ENUMERABLE (pt_d, bucket(16, pk0))
WITH (
  `lindorm_columnar.user.index.database` = 'my_index_db',  -- 列存索引所在库名
  `lindorm_columnar.user.index.table` = 'my_index_tbl'     -- 列存索引表名
);
```

**查询列存索引**：

```sql
-- 使用 HINT 指定走列存索引查询
SELECT /*+ _use_ldps_(cg_name), _columnar_index_ */
  pk1, SUM(col0)
FROM my_db.my_table
WHERE pt_d = '2024-01-01'
GROUP BY pk1;
```

> **注意**：`cg_name` 为计算引擎 OLAP 资源组的名称。

---

### 新版列存索引（实时同步）

> ⚠️ **如需秒级同步延迟**，可使用新版列存索引，目前处于**邀测阶段**。

**新旧版对比**：

| 特性 | 旧版列存索引 | 新版列存索引 |
|------|-------------|-------------|
| **同步延迟** | 15 分钟 | **实时（秒级）** |
| **数据新鲜度** | 延迟较高 | 近实时 |
| **适用场景** | 离线分析 | 实时分析 |
| **版本状态** | 已正式发布 | 邀测阶段 |

**申请方式**：
- 联系 Lindorm 技术支持申请使用（可在阿里云官网提交工单或联系您的客户经理）

**新版引擎版本要求**：

| 引擎 | 版本要求 | 作用 |
|------|---------|------|
| 宽表引擎 | >= 2.8.6 | 源数据存储 |
| LTS | >= 3.9.1 | 日志实时订阅 |
| 列存引擎 | >= 3.10.15 | 索引数据存储 |
| 计算引擎 | - | 执行分析查询 |

> **重要区别**：新版列存索引依赖**列存引擎**存储索引数据，支持秒级同步；旧版不依赖列存引擎，同步延迟约15分钟。

**新版创建语法**：

新增 `lindorm_columnar.user.index.type = 'LCE'` 属性：

```sql
-- 创建列存索引（新版，秒级同步）
CREATE INDEX idx_columnar USING COLUMNAR ON my_table(
  pk0, pk1, pt_d, col0, col1
)
PARTITION BY ENUMERABLE (pt_d, bucket(16, pk0))
WITH (
  `lindorm_columnar.user.index.database` = 'my_index_db',  -- 列存索引所在库名
  `lindorm_columnar.user.index.table` = 'my_index_tbl',     -- 列存索引表名
  `lindorm_columnar.user.index.type` = 'LCE'               -- 新版必填，指定走新版链路
);
```

> **重要**：`lindorm_columnar.user.index.type = 'LCE'` 为新版必填项，缺失则走旧版链路（15分钟延迟）。

**官方文档**：[列存索引新版](https://help.aliyun.com/zh/lindorm/user-guide/column-store-index-new-version)

### 搜索索引开通条件

> ⚠️ **重要**：搜索索引需要先在控制台开通后才能使用，否则创建索引会报 `SERVER INTERNAL ERROR`。

**开通步骤**：

1. 登录 [Lindorm 控制台](https://lindorm.console.aliyun.com/)
2. 在实例列表页，单击**目标实例ID**
3. 在左侧导航栏，单击**宽表引擎** → **搜索索引**
4. 点击「立即开通」
4. 配置以下参数：

| 参数 | 说明 | 建议 |
|------|------|------|
| 搜索节点规格 | 搜索引擎处理能力 | 16核64GB（QPS 500+，写入 TPS 50000+） |
| 搜索节点数量 | 搜索节点个数 | 至少 2 个（避免单点故障） |
| LTS 数据同步规格 | 数据同步服务 | 4核16GB |
| LTS 节点数量 | 同步节点个数 | 建议 2 个 |
| 存储空间 | 搜索引擎存储大小 | 按数据量评估 |

> **依赖说明**：搜索索引依赖 LTS 数据同步服务，开通时会同时开通 LTS。如已开通备份恢复或数据订阅功能，则无需重复开通 LTS。

**官方文档**：https://help.aliyun.com/zh/lindorm/user-guide/enable-the-search-index-feature

#### 搜索索引适用场景

| 场景 | 说明 | 示例 |
|------|------|------|
| 多维组合查询 | 任意索引列随机组合查询 | `WHERE c1=? AND c2=?` 或 `WHERE c3=?` |
| 分词查询 | 文本分词匹配 | `MATCH(content) AGAINST('关键词')` |
| 模糊查询 | LIKE 后缀/包含 | `WHERE name LIKE '%关键词%'` |
| 聚合分析 | COUNT/SUM/MIN/MAX/AVG | `SELECT COUNT(*) GROUP BY` |
| 排序分页 | 任意索引列排序 | `ORDER BY create_time DESC LIMIT 10` |

#### 分词查询语法（MATCH AGAINST）

搜索索引支持分词查询，使用 `MATCH ... AGAINST` 语法：

```sql
-- 创建带分词器的搜索索引
CREATE INDEX idx_text USING SEARCH ON articles (
  title(type=text, analyzer=ik),
  content(type=text, analyzer=ik)
);

-- 分词查询：查询 content 列包含"功能介绍"的记录
SELECT * FROM articles WHERE MATCH(content) AGAINST('功能介绍');

-- 会匹配包含"功能"、"介绍"或"功能介绍"的记录
```

**支持的分词器**：

| 分词器 | 说明 |
|--------|------|
| standard | 标准分词器（默认） |
| ik | 中文智能分词（推荐） |
| english | 英文分词 |
| whitespace | 按空格分词 |
| comma | 按逗号分词 |

#### 数据类型限制

> ⚠️ 搜索索引**不支持以下数据类型**：DECIMAL、DATE、TIME。如需使用，请用 DOUBLE 替代 DECIMAL，用 TIMESTAMP 替代 DATE/TIME。

**错误示例**：搜索索引列使用 DECIMAL 会报错 `Incompatible data type casting`

#### 索引构建时间

| 索引类型 | 构建时间（实测参考） |
|---------|-------------------|
| 二级索引(KV) | 约 10 秒 |
| 搜索索引(SEARCH) | **约 30 秒** |

> 在索引构建完成前执行查询仍会报"低效查询拦截"错误。实际构建时间因数据量而异，建议创建索引后等待足够时间再查询。

#### 冷热分离场景注意事项

> ⚠️ 如果实例已开启冷热分离功能，搜索索引构建过程会回查数据，冷存储（容量型云存储）的限流会直接影响索引构建效率，可能导致写入操作出现反压现象。

**开通冷存储前提**：
- 需先在控制台开通**容量型云存储**作为冷存储介质
- 开通路径：登录 Lindorm 控制台 → 选择地域 → 实例列表 → 目标实例ID → 左侧导航栏**冷存储** → 单击**开通**
- ⚠️ **警告**：开通过程需要**滚动重启实例**，可能导致读写请求**延迟波动或连接中断**，建议在业务低峰期操作
- 实例存储类型为**本地 HDD 盘**时，不支持开通容量型云存储

**建议**：
- 在数据写入热存储期间完成索引构建
- 或临时提升冷存储读取限流

### 二级索引冗余列（INCLUDE）

冗余列用于将其他列的数据复制到索引表中，避免查询时回表主表，提升查询性能。

**默认行为**：
- Lindorm SQL 2.9.3.10 及以上版本：未指定 INCLUDE 时，默认**不冗余**任何列
- Lindorm SQL 2.9.3.10 之前版本：未指定 INCLUDE 时，默认**冗余所有列**

**冗余所有列（INDEX_COVERED_TYPE）**：

如果需要冗余所有列，可通过索引属性 `INDEX_COVERED_TYPE` 设置：

| 取值 | 说明 |
|------|------|
| COVERED_ALL_COLUMNS_IN_SCHEMA | 冗余主表中所有已定义的列 |
| COVERED_DYNAMIC_COLUMNS | 冗余所有列，包括动态列（适用于动态表） |

```sql
-- 冗余所有已定义列
CREATE INDEX idx_user ON orders (user_id) 
  WITH (INDEX_COVERED_TYPE = 'COVERED_ALL_COLUMNS_IN_SCHEMA');

-- 动态表冗余所有列（包括动态列）
CREATE INDEX idx_user ON orders (user_id) 
  WITH (INDEX_COVERED_TYPE = 'COVERED_DYNAMIC_COLUMNS');
```

**使用建议**：
- 建议显式指定需要冗余的列，避免依赖默认行为
- 冗余列会增加存储空间，建议只冗余查询中常用的列
- 仅二级索引支持冗余列，搜索索引和列存索引不支持

**注意事项**：
- 显式指定的冗余列不可以包含主键列和索引列

**显式指定冗余列示例**：
```sql
-- 显式指定冗余列
CREATE INDEX idx_user ON orders (user_id) INCLUDE (amount, status);

-- 查询时可直接从索引获取 amount 和 status，无需回表
SELECT user_id, amount, status FROM orders WHERE user_id = 'u001';
```

### 示例

```sql
-- 创建二级索引
CREATE INDEX idx_user ON orders (user_id);

-- 创建带冗余列的二级索引
CREATE INDEX idx_user ON orders (user_id) INCLUDE (amount, status);

-- 创建搜索索引
CREATE INDEX idx_search USING SEARCH ON products (name, description);

-- 使用通配符创建搜索索引
CREATE INDEX idx_all USING SEARCH ON products (*);

-- 使用函数表达式创建索引
CREATE INDEX idx_hash ON orders (hash64(user_id, order_date), user_id, order_date);
```

### 搜索索引键属性

```sql
-- 使用分词器
CREATE INDEX idx_text USING SEARCH ON articles (
  title(type=text, analyzer=ik),
  content(type=text, analyzer=ik)
);
```

| 属性 | 说明 |
|------|------|
| indexed | 是否创建索引，默认 true |
| rowStored | 是否存储原始数据，默认 false |
| columnStored | 是否列存储，默认 true |
| type | 分词字段设为 text |
| analyzer | 分词器：standard、english、ik、whitespace、comma |

## 冷热分离

### 基于时间戳的冷热分离

```sql
-- 建表时设置
CREATE TABLE dt (
  p1 INTEGER,
  p2 INTEGER,
  c1 VARCHAR,
  c2 BIGINT,
  PRIMARY KEY(p1 DESC)
) WITH (
  COMPRESSION = 'ZSTD',
  CHS = '86400',           -- 冷热分界线，单位秒
  CHS_L2 = 'storagetype=COLD'
);

-- 已有表开启
ALTER TABLE dt SET 'CHS' = '86400', 'CHS_L2' = 'storagetype=COLD';
```

### 基于自定义时间列的冷热分离

```sql
-- 建表时设置
CREATE TABLE dt (
  p1 INTEGER,
  p2 BIGINT,
  p3 BIGINT,
  c1 VARCHAR,
  PRIMARY KEY(p1, p2, p3)
) WITH (
  COMPRESSION = 'ZSTD',
  CHS = '86400',
  CHS_L2 = 'storagetype=COLD',
  CHS_COLUMN = 'COLUMN=p2'  -- 指定时间列
);

-- 指定时间单位
CREATE TABLE dt (
  p1 INTEGER,
  p2 BIGINT,
  p3 BIGINT,
  c1 VARCHAR,
  PRIMARY KEY(p1, p2, p3)
) WITH (
  COMPRESSION = 'ZSTD',
  CHS = '86400',
  CHS_L2 = 'storagetype=COLD',
  CHS_COLUMN = 'COLUMN=p2|TIMEUNIT=SECONDS'
);
```

**CHS_COLUMN 注意事项：**
- 自定义时间列必须为主键
- 自定义时间列不能作为主键第一列
- 仅支持 BIGINT 和 TIMESTAMP 类型

### 修改和取消冷热分离

```sql
-- 修改冷热分界线
ALTER TABLE dt SET 'CHS' = '1000';

-- 取消冷热分离
ALTER TABLE dt SET 'CHS' = '', 'CHS_L2' = '', 'CHS_COLUMN' = '';
```

## 纠删码（EC）

纠删码是一种数据冗余存储机制，可在保证相同可靠性的同时节约存储空间。

### 前提条件

- 宽表引擎 2.5.4+，底层存储 4.3.4+
- 至少 7 个节点
- 本地 HDD 盘

### 使用方法

```sql
-- 建表时开启
CREATE TABLE dt (
  p1 INTEGER,
  p2 INTEGER,
  PRIMARY KEY(p1)
) WITH (EC_POLICY = 'RS-4-2');

-- 修改纠删码算法
ALTER TABLE dt SET 'EC_POLICY' = 'RS-4-2';

-- 删除纠删码算法
ALTER TABLE dt SET 'EC_POLICY' = '';
```

**说明：** RS-4-2 算法在存储效率上等价于 1.5 副本。

## 预分区

建议在数据量大或使用 Bulkload 导入数据时设置预分区。

### 预分区数量建议

| 场景 | 建议分区数 |
|------|-----------|
| SQL/HBase API 写入 | 节点数 × 4 |
| Bulkload 批量导入 | 数据量(GB) ÷ 8 |

### 示例

```sql
-- 指定分区数和起止 Key
CREATE TABLE orders (
  id VARCHAR NOT NULL,
  amount BIGINT,
  PRIMARY KEY(id)
) WITH (
  NUMREGIONS = '16',
  STARTKEY = 'a',
  ENDKEY = 'z'
);

-- 指定分裂点
CREATE TABLE orders (
  id INTEGER NOT NULL,
  amount BIGINT,
  PRIMARY KEY(id)
) WITH (
  SPLITKEYS = '100,200,300,400,500'
);
```

## 完整建表示例

### 物联网设备数据表

```sql
CREATE TABLE iot_device_data (
  device_id VARCHAR NOT NULL,
  timestamp BIGINT NOT NULL,
  metric_name VARCHAR NOT NULL,
  metric_value DOUBLE,
  `extra_*` VARCHAR,
  PRIMARY KEY(hash32(device_id), device_id, timestamp DESC, metric_name)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '7776000',              -- 90 天
  DYNAMIC_COLUMNS = 'true',
  wildcard_column = 'extra_*',
  CHS = '2592000',              -- 30 天后归档到冷存储
  CHS_L2 = 'storagetype=COLD',
  CHS_COLUMN = 'COLUMN=timestamp|TIMEUNIT=SECONDS'
);

-- 创建按设备类型查询的二级索引
CREATE INDEX idx_metric ON iot_device_data (metric_name) INCLUDE (metric_value);
```

### 电商订单表

```sql
CREATE TABLE orders (
  order_id VARCHAR NOT NULL,
  user_id VARCHAR NOT NULL,
  create_time BIGINT NOT NULL,
  status VARCHAR,
  amount BIGINT,
  items VARCHAR,
  PRIMARY KEY(hash32(order_id), order_id),
  INDEX idx_user USING KV (user_id, create_time DESC) INCLUDE (status, amount)
) WITH (
  COMPRESSION = 'ZSTD',
  CONSISTENCY = 'strong',
  MUTABILITY = 'MUTABLE_LATEST',
  NUMREGIONS = '32'
);

-- 创建搜索索引支持商品搜索
CREATE INDEX idx_search USING SEARCH ON orders (items(type=text, analyzer=ik));
```

### 日志分析表

```sql
CREATE TABLE app_logs (
  bucket INTEGER NOT NULL,
  timestamp BIGINT NOT NULL,
  app_id VARCHAR NOT NULL,
  level VARCHAR NOT NULL,
  message VARCHAR,
  stack_trace VARCHAR,
  PRIMARY KEY(bucket, timestamp, app_id, level)
) WITH (
  COMPRESSION = 'ZSTD',
  TTL = '604800',                -- 7 天
  EC_POLICY = 'RS-4-2',
  CHS = '86400',                 -- 1 天后归档
  CHS_L2 = 'storagetype=COLD'
);
-- 写入时：bucket = timestamp % 16
```
