# Lindorm CLI & HBase Shell Guide

Lindorm 专用命令行工具指南，覆盖 Lindorm CLI（SQL/TSDB）和 HBase Shell（alihbase）。

---

## Lindorm CLI

Lindorm CLI is the official command-line client for connecting to and operating Lindorm wide table engine (SQL) and time series engine (TSDB).

> **Official Doc**: https://help.aliyun.com/zh/lindorm/user-guide/use-lindorm-cli-to-connect-to-and-use-lindormtable

### Installation

#### Download Links

| Platform | Download URL |
|----------|-------------|
| Linux x64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-linux-latest.tar.gz` |
| Linux ARM64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-linux-arm64-latest.tar.gz` |
| macOS AMD64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-amd64-latest.tar.gz` |
| macOS ARM64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-arm64-latest.tar.gz` |
| Windows x64 | `https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-windows-x64-latest.zip` |

#### Installation Steps (macOS/Linux)

```bash
# 1. Download (example: macOS ARM64)
curl -L -o lindorm-cli.tar.gz "https://tsdbtools.oss-cn-hangzhou.aliyuncs.com/lindorm-cli-mac-arm64-latest.tar.gz"

# 2. Extract
tar -xzf lindorm-cli.tar.gz

# 3. Move to PATH
sudo mv lindorm-cli /usr/local/bin/

# 4. Verify
lindorm-cli -version
# Expected output: lindorm-cli version: 2.2.0 (or later)
```

#### Installation Steps (Windows)

1. Download the ZIP file from the table above
2. Extract the ZIP
3. Add the directory to PATH
4. Verify: `lindorm-cli -version`

### Connection Methods

Lindorm CLI supports two connection protocols:

#### 1. MySQL Protocol (Wide Table Engine)

```bash
# Connect to wide table engine via MySQL protocol
lindorm-cli -url <lindorm_mysql_host>:33060 -username root -password <password> -database <db_name>

# Example (V2 instance)
lindorm-cli -url ld-uf6nbdlx5n34q6l6t-proxy-lindorm-pub.lindorm.aliyuncs.com:33060 \
  -username root -password XUzmhKMpuyhx -database default

# URL can also use mysql:// prefix
lindorm-cli -url mysql://ld-xxx-proxy-lindorm-pub.lindorm.aliyuncs.com:33060 \
  -username root -password <pwd> -database <db>
```

#### 2. Avatica/TSDB Protocol (Time Series Engine)

```bash
# Connect to TSDB engine via Avatica JDBC protocol
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <password>

# Example (V2 instance)
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://ld-uf6nbdlx5n34q6l6t-proxy-tsdb-pub.lindorm.aliyuncs.com:8242' \
  -username root -password XUzmhKMpuyhx
```

### Usage Modes

#### Non-Interactive Mode (-execute)

Execute a single SQL command and quit:

```bash
lindorm-cli -url <host>:33060 -username root -password <pwd> \
  -database <db> -execute "SELECT * FROM my_table" -format table
```

#### Interactive Mode (Pipe)

Pipe multiple SQL commands:

```bash
echo "UPSERT INTO t1 VALUES ('k1','v1',10); SELECT * FROM t1;" | \
  lindorm-cli -url <host>:33060 -username root -password <pwd> -database <db> -format table
```

#### Output Format Options

| Format | Description | Example |
|--------|-------------|---------|
| `table` | Formatted table with borders | Default, good for terminal |
| `csv` | CSV format | Good for data export |
| `column` | Column-aligned plain text | Compact display |
| `vertical` | Vertical (one field per line) | Like MySQL `\G` |
| `json` | JSON with base64-encoded strings | Use `-pretty` for readable JSON |

```bash
# Table format (default)
lindorm-cli ... -execute "SELECT * FROM t1" -format table

# CSV format
lindorm-cli ... -execute "SELECT * FROM t1" -format csv

# JSON format with pretty print
lindorm-cli ... -execute "SELECT * FROM t1" -format json -pretty

# Write output to file
lindorm-cli ... -execute "SELECT * FROM t1" -format table -output result.txt
```

#### Precision for TSDB Queries

```bash
# Timestamp formats for TSDB queries
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://...' ... -precision ms    # milliseconds
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://...' ... -precision s     # seconds
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://...' ... -precision rfc3339 # RFC 3339 format
```

### SQL Syntax Notes for Lindorm CLI

> **Important**: Lindorm CLI's SQL parser has subtle differences from the mysql CLI client.

#### CREATE TABLE Syntax

Lindorm CLI requires `PRIMARY KEY` to be specified **inside** the column definition parentheses (MySQL standard style), not as a separate clause outside:

```sql
-- ✅ Correct: PRIMARY KEY inside column list (also works in mysql client)
CREATE TABLE t1 (id VARCHAR NOT NULL, name VARCHAR, score INT, PRIMARY KEY(id));

-- ❌ Wrong: PRIMARY KEY as separate clause (works in mysql client but fails in lindorm-cli -execute)
CREATE TABLE t1 (id VARCHAR NOT NULL, name VARCHAR, score INT) PRIMARY KEY (id);
```

> The `PRIMARY KEY` outside the parentheses syntax works with the `mysql` CLI client but causes `"Encountered PRIMARY PRIMARY"` error in lindorm-cli `-execute` mode.

#### UPSERT vs INSERT

Lindorm SQL uses `UPSERT` as the primary write operation (INSERT is also UPSERT semantics):

```sql
-- UPSERT is recommended
UPSERT INTO t1 (id, name, score) VALUES ('k1', 'Alice', 88);

-- Bulk UPSERT
UPSERT INTO t1 (id, name, score) VALUES ('k1','Alice',88), ('k2','Bob',95), ('k3','Carol',72);
```

#### Reserved Words

Avoid using SQL reserved words as column names (e.g., `value`, `key`, `timestamp`). If needed, quote with backticks:

```sql
-- ❌ Error: "value" is reserved
CREATE TABLE t1 (id VARCHAR, value INT, PRIMARY KEY(id));

-- ✅ Correct: use backticks or avoid reserved words
CREATE TABLE t1 (id VARCHAR, `value` INT, PRIMARY KEY(id));
```

### Lindorm CLI Common Operations

```bash
# Show databases
lindorm-cli -url <host>:33060 -username root -password <pwd> -execute "SHOW DATABASES" -format table

# Create database
lindorm-cli -url <host>:33060 -username root -password <pwd> -execute "CREATE DATABASE my_db" -format table

# Create table (use inline PRIMARY KEY syntax)
lindorm-cli -url <host>:33060 -username root -password <pwd> -database my_db \
  -execute "CREATE TABLE users (id VARCHAR NOT NULL, name VARCHAR, age INT, PRIMARY KEY(id))" -format table

# Insert data
lindorm-cli -url <host>:33060 -username root -password <pwd> -database my_db \
  -execute "UPSERT INTO users (id, name, age) VALUES ('u1','Alice',25)" -format table

# Query data
lindorm-cli -url <host>:33060 -username root -password <pwd> -database my_db \
  -execute "SELECT * FROM users" -format table

# Create secondary index (no USING KV in mysql protocol)
lindorm-cli -url <host>:33060 -username root -password <pwd> -database my_db \
  -execute "CREATE INDEX idx_age ON users (age)" -format table

# Describe table
lindorm-cli -url <host>:33060 -username root -password <pwd> -database my_db \
  -execute "DESCRIBE users" -format table

# Drop table
lindorm-cli -url <host>:33060 -username root -password <pwd> -database my_db \
  -execute "DROP TABLE IF EXISTS users" -format table
```

### TSDB Operations via Lindorm CLI

```bash
# Connect to TSDB
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <pwd>

# Show databases
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <pwd> -execute "SHOW DATABASES" -format table

# Create TSDB table
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <pwd> \
  -execute "CREATE TABLE ts_test (p VARCHAR NOT NULL, t TIMESTAMP NOT NULL, v DOUBLE, PRIMARY KEY(p, t))" -format table

# Upsert time series data
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <pwd> \
  -execute "UPSERT INTO ts_test (p, t, v) VALUES ('cpu', '2024-01-01 10:00:00', 85.5)" -format table

# Query with time range
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <pwd> \
  -execute "SELECT * FROM ts_test WHERE p='cpu' AND t >= '2024-01-01 00:00:00'" -format table

# Query with millisecond precision
lindorm-cli -url 'jdbc:lindorm:tsdb:url=http://<tsdb_host>:8242' \
  -username root -password <pwd> \
  -execute "SELECT * FROM ts_test" -format table -precision ms
```

### Lindorm CLI Limitations

1. **Avatica (port 30060) not supported for wide table**: lindorm-cli only supports MySQL protocol for wide table and `jdbc:lindorm:tsdb:` URL for TSDB. It cannot connect to the generic Avatica SQL port (30060) — use `mysql` client or `phoenixdb` Python library for that.
2. **CREATE TABLE syntax**: Must use inline `PRIMARY KEY` inside column list, not as separate clause.
3. **JSON format encoding**: JSON output uses base64 encoding for VARCHAR values. Use `table` or `csv` format for readable output.
4. **Non-interactive only**: lindorm-cli `-execute` mode runs one command per invocation. For multi-command workflows, use pipe or multiple invocations.

### Lindorm CLI References

- Official Documentation (Wide Table): https://help.aliyun.com/zh/lindorm/user-guide/use-lindorm-cli-to-connect-to-and-use-lindormtable
- Official Documentation (TSDB): https://help.aliyun.com/zh/lindorm/user-guide/use-lindorm-cli-to-connect-to-and-use-lindorm-tsdb

---

## HBase Shell (alihbase)

HBase Shell is used for native HBase API operations on Lindorm wide table engine. **Lindorm requires the dedicated `alihbase shell` (not the open-source Apache HBase Shell)**.

> **Critical**: The open-source Apache HBase Shell cannot connect to Lindorm's public network endpoint. It resolves ZK addresses to internal IPs that are inaccessible from outside. You must use `alihbase shell` from Alibaba Cloud.

### alihbase Shell Installation

> **Download URL**: The `alihbase shell` can be downloaded directly from the public OSS URL:
> `https://hbaseuepublic.oss-cn-beijing.aliyuncs.com/hbaseue-shell.tar.gz`

#### Step-by-Step Installation

1. **Download alihbase shell**:

```bash
curl -L -o hbaseue-shell.tar.gz "https://hbaseuepublic.oss-cn-beijing.aliyuncs.com/hbaseue-shell.tar.gz"
```

2. **Extract and install**:

```bash
# Extract (creates alihbase-2.0.22 directory)
tar -xzf hbaseue-shell.tar.gz

# Navigate to the directory
cd alihbase-2.0.22

# Run alihbase shell
./bin/hbase shell
```

#### Connection Configuration

alihbase shell connects to Lindorm via ZooKeeper address with username/password authentication:

```bash
# Option 2: Configuration file (hbase-site.xml) — recommended
# Place in conf/ directory:
cat > conf/hbase-site.xml << 'EOF'
<?xml version="1.0"?>
<configuration>
  <property>
    <name>hbase.zookeeper.quorum</name>
    <value><lindorm_hbase_host>:30020</value>
  </property>
  <property>
    <name>hbase.client.username</name>
    <value>root</value>
  </property>
  <property>
    <name>hbase.client.password</name>
    <value><InitialRootPassword_from_GetLindormV2InstanceDetails></value>
  </property>
</configuration>
EOF

./bin/alihbase shell
```

#### Java Requirements

- **JDK 8+** is required
- Verify: `java -version`

### alihbase Shell Common Operations

```ruby
# Create table with column family
create 'my_table', 'cf1'

# Put data
put 'my_table', 'row1', 'cf1:name', 'Alice'
put 'my_table', 'row1', 'cf1:age', '25'

# Get a row
get 'my_table', 'row1'

# Scan table
scan 'my_table'

# Scan with limit
scan 'my_table', {LIMIT => 10}

# Delete a column
delete 'my_table', 'row1', 'cf1:age'

# Describe table
describe 'my_table'

# Count rows
count 'my_table'

# Disable and drop table
disable 'my_table'
drop 'my_table'
```

### Alternative: HBase Operations via SQL

If alihbase shell is not available, you can perform equivalent HBase operations using SQL through `mysql` client or `lindorm-cli`:

| HBase Shell Command | SQL Equivalent |
|--------------------|----------------|
| `create 't', 'cf1'` | `CREATE TABLE t (pk VARCHAR NOT NULL, cf1:col VARCHAR, PRIMARY KEY(pk)) WITH (DYNAMIC_COLUMNS=true)` |
| `put 't', 'r1', 'cf1:name', 'Alice'` | `UPSERT INTO t (pk, `cf1:name`) VALUES ('r1', 'Alice')` |
| `get 't', 'r1'` | `SELECT * FROM t WHERE pk='r1'` |
| `scan 't'` | `SELECT * FROM t` |
| `delete 't', 'r1', 'cf1:age'` | `DELETE FROM t WHERE pk='r1'` (deletes entire row) |

> Note: SQL operations on HBase-style tables use `DYNAMIC_COLUMNS=true` table property and colon-separated column family syntax (`cf1:col_name`).

### HBase Shell References

- Official Documentation: https://help.aliyun.com/zh/lindorm/user-guide/use-hbase-shell-to-connect-to-and-use-the-wide-table-engine
- alihbase-client Maven: `com.aliyun.hbase:alihbase-client:2.8.11`
- alihbase-shell Maven: `com.aliyun.hbase:alihbase-shell:2.8.7` (JAR only, not standalone binary)
