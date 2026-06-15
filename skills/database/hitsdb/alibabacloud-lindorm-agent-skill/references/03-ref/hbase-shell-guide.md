# HBase Shell (alihbase) Agent Skill Guide

HBase Shell usage guide for AI Agents. HBase Shell is used to operate the Lindorm wide table engine through the native HBase API. **Lindorm must use the Alibaba Cloud dedicated alihbase package. Do not use the open-source Apache HBase Shell.**

> **Critical**: The open-source Apache HBase Shell cannot connect to Lindorm public endpoints. It resolves the ZK address to internal IP addresses that cannot be accessed externally. You must use the alihbase package provided by Alibaba Cloud, and start it through `./bin/hbase shell` after extraction.

---

## Installation

### Download

The alihbase shell can be downloaded directly from the public OSS URL:

```text
https://hbaseuepublic.oss-cn-beijing.aliyuncs.com/hbaseue-shell.tar.gz
```

### Installation Steps

```bash
# 1. Download.
curl --connect-timeout 30 -m 120 -L -o hbaseue-shell.tar.gz "https://hbaseuepublic.oss-cn-beijing.aliyuncs.com/hbaseue-shell.tar.gz"

# 2. Extract, which generates the alihbase-2.0.22 directory.
tar -xzf hbaseue-shell.tar.gz
cd alihbase-2.0.22

# 3. Verify Java environment. JDK 8+ is required.
java -version

# 4. Start hbase shell.
./bin/hbase shell
```

> **Prerequisite**: JDK 8+, verified by `java -version`.

---

## Connection Configuration

The alihbase shell connects to Lindorm through the ZooKeeper address and uses username/password authentication.

### Method 1: Configuration File, Recommended

Configure `conf/hbase-site.xml`:

```xml
<?xml version="1.0"?>
<configuration>
  <property>
    <name>hbase.zookeeper.quorum</name>
    <value>&lt;lindorm_hbase_host&gt;:30020</value>
  </property>
  <property>
    <name>hbase.client.username</name>
    <value>root</value>
  </property>
  <property>
    <name>hbase.client.password</name>
    <value>&lt;password&gt;</value>
  </property>
</configuration>
```

Start directly after configuration:

```bash
./bin/hbase shell
```

### Obtain Connection Address

Use Alibaba Cloud CLI to obtain the HBase API connection address:

```bash
aliyun hitsdb get-lindorm-instance-engine-list --instance-id <id>
```

Find the connection address whose engine type is `lindorm` in the returned result. Both V1 and V2 instances use this engine code. The port is `30020`.

> **Security rules**:
> - **NEVER** echo password values in the conversation.
> - It is recommended to pass the password through the configuration file to avoid command-line exposure.

### Connection Failure Troubleshooting

| Symptom | Possible Cause | Handling Method |
|------|---------|---------|
| Connection refused | Port is unreachable / whitelist is not added | Check IP whitelist and network reachability |
| Authentication failed | Username or password is incorrect | Confirm credentials |
| ZooKeeper connection timeout | Internal address is used while the client is not in the same VPC | Use a public address or confirm VPC connectivity |
| Could not connect to ZK | Open-source HBase Shell connects to public endpoint | Use `./bin/hbase shell` from the alihbase package |

**Troubleshooting steps**:

1. Check whitelist: `aliyun hitsdb get-instance-ip-white-list --instance-id <id>`
2. Test port reachability: `nc -zv <host> 30020 -w 5`
3. Confirm that `./bin/hbase shell` from the alihbase package is used, not open-source HBase Shell.

---

## Common Operations

### Table Operations

```ruby
# Create a table with one column family.
create 'my_table', 'cf1'

# Create a table with multiple column families.
create 'my_table', 'cf1', 'cf2'

# View table description.
describe 'my_table'

# Check whether the table exists.
exists 'my_table'

# List all tables.
list

# Disable a table. Must disable before deletion.
disable 'my_table'

# Drop a table.
drop 'my_table'

# Disable + drop, completed step by step.
disable 'my_table'
drop 'my_table'
```

### Data Write

```ruby
# Write a single row.
put 'my_table', 'row1', 'cf1:name', 'Alice'
put 'my_table', 'row1', 'cf1:age', '25'
put 'my_table', 'row1', 'cf1:email', 'alice@example.com'

# Write different rows.
put 'my_table', 'row2', 'cf1:name', 'Bob'
put 'my_table', 'row2', 'cf1:age', '30'
```

### Data Read

```ruby
# Read a single row.
get 'my_table', 'row1'

# Read a specified column.
get 'my_table', 'row1', 'cf1:name'

# Scan the full table.
scan 'my_table'

# Limit scan row count.
scan 'my_table', {LIMIT => 10}

# Specify column family:column.
scan 'my_table', {COLUMNS => ['cf1:name', 'cf1:age']}

# Range scan.
scan 'my_table', {STARTROW => 'row1', STOPROW => 'row3'}

# Filter scan.
scan 'my_table', {FILTER => "ValueFilter(=,'binary:Alice')"}
```

### Data Delete

```ruby
# Delete a specified column.
delete 'my_table', 'row1', 'cf1:age'

# Delete the whole row.
deleteall 'my_table', 'row1'
```

### Other Operations

```ruby
# Count rows.
count 'my_table'

# Clear a table. Disable first and then truncate.
truncate 'my_table'

# View table status, enabled/disabled.
is_enabled 'my_table'
```

---

## SQL Alternatives

When the alihbase package is unavailable, equivalent HBase operations can be completed through SQL by using the `mysql` client or `lindorm-cli`:

| HBase Shell Command | SQL Equivalent |
|-----------------|-------------|
| `create 't', 'cf1'` | `CREATE TABLE t (pk VARCHAR NOT NULL, cf1:col VARCHAR, PRIMARY KEY(pk)) WITH (DYNAMIC_COLUMNS=true)` |
| `put 't', 'r1', 'cf1:name', 'Alice'` | `UPSERT INTO t (pk, \`cf1:name\`) VALUES ('r1', x'416c696365')` |
| `get 't', 'r1'` | `SELECT * FROM t WHERE pk='r1' LIMIT 1` |
| `scan 't'` | `SELECT * FROM t LIMIT 100` |
| `delete 't', 'r1', 'cf1:age'` | `UPDATE t SET \`cf1:age\` = NULL WHERE pk='r1'`, delete specified column |
| `count 't'` | `SELECT COUNT(*) FROM t` |

> **Description**: When operating HBase-style tables through SQL, the `DYNAMIC_COLUMNS=true` table property must be used, and column names use the column-family syntax separated by a colon, such as `cf1:col_name`.
>
> **⚠️ Two key limits**:
> 1. **Dynamic column values must be hex-encoded**: Tables with `DYNAMIC_COLUMNS=true` require dynamic column values to be hex strings or byte arrays. Strings must be converted to hex before writing, such as `'Alice'` → `x'416c696365'`, and are returned as hex when read.
> 2. **SELECT * must include LIMIT**: When running `SELECT *` on a table with `DYNAMIC_COLUMNS=true`, `LIMIT` must be specified. Otherwise, the error `Illegal operation: Limit of this select statement is not set or exceeds` is reported.

### SQL Alternative Operation Examples

```bash
# Create an HBase-style dynamic column table.
lindorm-cli --format json --execute "CREATE TABLE hbase_style (pk VARCHAR NOT NULL, cf1:col VARCHAR, PRIMARY KEY(pk)) WITH (DYNAMIC_COLUMNS=true)" 2>/dev/null

# Write data. Dynamic column values must be hex strings.
lindorm-cli --format json --execute "UPSERT INTO hbase_style (pk, \`cf1:name\`) VALUES ('r1', x'416c696365')" 2>/dev/null

# Read data. SELECT * must include LIMIT.
lindorm-cli --format json --execute "SELECT * FROM hbase_style WHERE pk='r1' LIMIT 10" 2>/dev/null

# Scan the full table.
lindorm-cli --format json --execute "SELECT * FROM hbase_style LIMIT 100" 2>/dev/null

# Delete specified column by setting it to NULL.
lindorm-cli --format json --execute "UPDATE hbase_style SET \`cf1:name\` = NULL WHERE pk='r1'" 2>/dev/null
```

---

## Notes

1. **The alihbase package must be used**: Start it through `./bin/hbase shell`. Although the package name is alihbase-2.0.22, the startup command is `hbase`, not `alihbase`. The open-source Apache HBase Shell cannot connect to Lindorm public endpoints.
2. **Java dependency**: JDK 8+ is required.
3. **Deleting a table requires two steps**: `disable` first, then `drop`.
4. **truncate is equivalent to disable + drop + create**: It rebuilds an empty table and clears all original data.
5. **Column-family colon syntax**: In HBase, the column name format is `column_family:column_name`, such as `cf1:name`.
6. **HBase Shell does not support SQL**: HBase Shell uses the native HBase API, Ruby syntax, and is completely different from Lindorm SQL syntax.

---

## References

- Official documentation: https://help.aliyun.com/zh/lindorm/user-guide/use-hbase-shell-to-connect-to-and-use-the-wide-table-engine
- alihbase-client Maven: `com.aliyun.hbase:alihbase-client:2.8.11`
- alihbase-shell Maven: `com.aliyun.hbase:alihbase-shell:2.8.7`, JAR only, not a standalone binary
