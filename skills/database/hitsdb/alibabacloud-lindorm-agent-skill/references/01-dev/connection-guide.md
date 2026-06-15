# Connection Information Retrieval Scenario

When the user asks "how do I connect to an instance", "what is the connection endpoint", or "which SDK do I need", follow this guide.

## Trigger Conditions

Typical user expressions:
- "How do I connect to ld-xxx?"
- "Give me the connection endpoint."
- "How do I connect with Java?"
- "What is the port of the time series engine?"
- "Give me a connection example."

## Core Principles

**The agent is a solution provider, not a pointer to documentation**:
1. **Extract key information** and organize it into a complete answer, including code examples, dependency configuration, and parameter descriptions.
2. **Let the user obtain executable connection code inside the conversation** without leaving the chat.
3. If the connection endpoint cannot be obtained from an API, **clearly provide the exact console path**, down to the button location.
4. Documentation links are supplementary references for users who want deeper details.

---

## Execution Flow

### Phase 1: Obtain basic instance information

Run the following commands to obtain the architecture version, connection endpoints, and network configuration of the instance:

```bash
# 1. Get instance details and identify the V1/V2 architecture
aliyun hitsdb get-lindorm-instance \
    --instance-id <instance-id>

# 2. Get connection endpoints of each engine
aliyun hitsdb get-lindorm-instance-engine-list \
    --instance-id <instance-id>
```

**Key information to extract**:

| Item | Source field | Description |
|------|--------------|-------------|
| Architecture version | `ServiceType` | `lindorm_v2*` = V2 architecture; `lindorm` = V1 architecture |
| Connection endpoint | `NetInfoList` | Domain names and ports of each engine. This field is used by both V1 and V2 |
| Network type | `NetType` | `"0"` = public network available; `"2"` = VPC private network only. The value is a string and is the same for V1/V2 |
| Engine version | `EngineList` | Version number of each engine |

> **Note**: `get-lindorm-instance-engine-list` returns `NetInfoList` and `NetType` for both V1 and V2. Another V2-only API, `get-lindorm-v2-instance-details`, returns `ConnectAddressList` and `Type=INTRANET/INTERNET`. See Phase 2.

**Endpoint domain format**:

For endpoint formats, see [sql-client-guide.md](sql-client-guide.md). It includes V1/V2 `ServiceType` identification logic and complete examples.

---

### Phase 2: Confirm connection prerequisites

Before providing connection code, confirm the following two items.

#### 1. Public-network access check

**Method 1: Use `get-lindorm-instance-engine-list` for both V1 and V2**

Check the string field `NetType` in `NetInfoList`:
- `"0"`: public network available
- `"2"`: VPC private network only

**Method 2: Use `get-lindorm-v2-instance-details` for V2 only**

Check the `Type` field in `ConnectAddressList`:
- `INTERNET`: public network available
- `INTRANET`: VPC private network only

**If only a VPC private endpoint exists (`NetType="2"` or `Type=INTRANET`)**:
> ⚠️ The SQL port of the current instance only supports VPC private-network access. To connect from a local computer:
> 1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/).
> 2. Click the instance ID, then go to **Database Connection** → **Engine**.
> 3. Click **Enable Public Endpoint** in the upper-right corner.
> 4. Configure the whitelist with your local IP address.
>
> Alternatively, run the connection and operations on an Alibaba Cloud ECS instance in the same VPC as Lindorm.

#### 2. Password retrieval and confirmation

**V2 instances**:
```bash
aliyun hitsdb get-lindorm-v2-instance-details \
    --instance-id <instance-id>
```

Extract the `InitialRootPassword` field. The username is `root`.

> ⚠️ **Password retrieval and confirmation flow:**
> 1. **First connection**: use `InitialRootPassword`.
> 2. **Connection failure or password error**: stop execution and **ask the user for the current password**.
> 3. **Change operations** such as creating tables or modifying configurations: **obtain explicit user authorization first**.

**V1 instances**:
- **Default username**: `root`
- **Default password**: `root`
- **If the password is forgotten**: modify it through the cluster management system.
  - Path: [Lindorm console](https://lindorm.console.aliyun.com/) → instance ID → **Database Connection** → **Wide Table Engine** → **Lindorm Insight** → **User Management**
  - After changing the password, **restart the engine** for the change to take effect.

---

### Phase 3: Provide connection information

Organize the information obtained in Phases 1 and 2 and directly provide a complete connection plan to the user:

```text
Instance ld-xxx has the following engines enabled:
- Wide table engine, version 2.8.6, V2 architecture
- Time series engine, version 2.7.15

[Connection endpoints] Obtained from API
- VPC private endpoint: ld-xxx-proxy-lindorm-vpc.lindorm.aliyuncs.com:33060
- Public endpoint: ld-xxx-proxy-lindorm-pub.lindorm.aliyuncs.com:33060

> ⚠️ When connecting from the public network, such as a local computer, use the public endpoint (`-pub`). Do not use the private endpoint (`-vpc`), otherwise the connection will time out.

[SQL credentials]
- Username: root
- Password: for a V2 instance, the `InitialRootPassword` has been obtained through `get-lindorm-v2-instance-details`; for a V1 instance, view it in Lindorm Insight → User Management in the console.
```

**Connectivity verification with the MySQL command line**:

```bash
mysql -h <connection_endpoint> -P 33060 -u root -p \
  --get-server-public-key --ssl-mode=DISABLED
```

After the connection succeeds, tell the user:
> The connection has been verified successfully. Do you need a complete example for creating tables and writing data? Tell me the engine type, and I can provide complete code.

**Engine port quick reference**:

| Engine | Protocol | Port |
|--------|----------|------|
| Wide table engine | MySQL protocol, recommended | 33060 |
| Wide table engine | HBase API | 30020 |
| Time series engine | HTTP SQL API | 8242 |
| Search engine | Elasticsearch API | 30070 |
| Streaming engine | MySQL protocol | 33060 |

**Connection method overview for each engine**. Route the user to the correct guide according to the requirement:

| Engine | Connection method | Recommendation | Official documentation |
|--------|-------------------|----------------|------------------------|
| Wide table engine | MySQL protocol SQL | ⭐ Recommended | [Java JDBC](https://help.aliyun.com/zh/lindorm/user-guide/application-development-based-on-java-jdbc-interface), [Python](https://help.aliyun.com/zh/lindorm/user-guide/python-based-application-development-1), and more languages in [sql-client-guide.md](sql-client-guide.md) |
| Wide table engine | HBase API | Common | [Java](https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-java-to-connect-to-and-use-the-wide-table-engine), [non-Java](https://help.aliyun.com/zh/lindorm/user-guide/use-the-hbase-api-for-a-non-java-language-to-connect-to-and-use-the-wide-table-engine), and examples in [quick-start-guide.md Scenario F](quick-start-guide.md#scenario-f-wide-table-engine-hbase-api-quick-start) |
| Wide table engine | Cassandra CQL | Existing workloads | [Java Driver](https://help.aliyun.com/zh/lindorm/user-guide/use-a-cassandra-client-driver-for-java-to-connect-to-and-use-the-wide-table-engine), [non-Java](https://help.aliyun.com/zh/lindorm/user-guide/use-a-multi-language-cassandra-client-driver-to-connect-to-and-use-the-wide-table-engine) |
| Wide table engine | S3 protocol | Existing workloads | [Java](https://help.aliyun.com/zh/lindorm/user-guide/connect-and-use-the-wide-table-engine-with-the-s3), [non-Java](https://help.aliyun.com/zh/lindorm/user-guide/connect-via-s3-non-java-api-and-use-the-wide-table) |
| Time series engine | JDBC Driver | ⭐ Recommended | [JDBC Driver](https://help.aliyun.com/zh/lindorm/user-guide/use-the-jdbc-driver-for-lindorm-to-connect-to-and-use-lindormtsdb) |
| Time series engine | HTTP SQL API | Lightweight | [HTTP API](https://help.aliyun.com/zh/lindorm/user-guide/http-sql-api-user-guide) |
| Search engine | Elasticsearch API | ⭐ Recommended | [Java REST Client](https://help.aliyun.com/zh/lindorm/user-guide/java-low-level-rest-client) |
| Vector engine | Elasticsearch API | ⭐ Recommended | Reuse search engine port `30070`. See the [vector development guide](https://help.aliyun.com/zh/lindorm/user-guide/foundation) |
| Streaming engine | MySQL protocol ETL SQL | ⭐ Recommended | [Real-time ETL](https://help.aliyun.com/zh/lindorm/user-guide/real-time-etl) |
| Streaming engine | Kafka client | Data ingestion | [Kafka write](https://help.aliyun.com/zh/lindorm/use-an-open-source-apache-kafka-client-to-write-data-to-the-lindorm-streaming-engine) |
| LindormDFS | HDFS Shell / client | - | [Underlying file access overview](https://help.aliyun.com/zh/lindorm/user-guide/lindormdfs), [operations guide](https://help.aliyun.com/zh/lindorm/user-guide/lindormdfs-user-guide/) |
| Compute engine | JDBC / JAR / Python | - | [JDBC access](https://help.aliyun.com/zh/lindorm/user-guide/use-sql-to-connect-to-ldps), [JAR job](https://help.aliyun.com/zh/lindorm/user-guide/jar-job-development-practice) |

> The Skill does not provide code examples for **LindormDFS or the compute engine**. If the user asks about them, guide the user to the official documentation above or the [connection overview](https://help.aliyun.com/zh/lindorm/getting-started/connect-to-an-instance).

---

### Phase 4: Whitelist check

**The agent proactively checks the whitelist**:

```bash
aliyun hitsdb get-instance-ip-white-list \
    --instance-id <instance-id>
```

**Provide clear recommendations after analysis**:

```text
[Whitelist check]

Current whitelist configuration: 10.0.0.0/8

[Analysis]
- If your client IP is within 10.0.0.0/8, you can connect directly.
- If your client IP is not in the whitelist, you need to add it.

[Add a whitelist entry]
1. Log on to the [Lindorm console](https://lindorm.console.aliyun.com/) → on the instance list page, click the target instance ID → in the left navigation pane, click Access Control → Whitelist.
2. Click Create Whitelist Group, or modify an existing group.
3. Add the client IP. Use the VPC IP for private-network environments and the public IP for public-network environments.
   - Single IP: 192.168.1.100
   - CIDR block: 192.168.1.0/24
4. Click OK to save.

Tip: view your public IP with `curl ifconfig.me`.

[Security note]
- Avoid using 0.0.0.0/0, which allows all IP addresses and introduces security risks.
- Add only necessary IP addresses or VPC CIDR blocks.

Do you want me to help troubleshoot the connection issue?
```

---

## Next-Step Guidance

After connection verification succeeds, guide the user according to the requirement:

- **Create tables, write data, or query data**: see [quick-start-guide.md](quick-start-guide.md), which contains complete examples for the wide table, time series, search, vector, and streaming engines.
- **Troubleshoot connection failures**: see [connection-troubleshoot.md](../02-ops/connection-troubleshoot.md).
- **Manage user permissions**: see [user-permission.md](../02-ops/user-permission.md).
