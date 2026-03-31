# Community + Enterprise Big Cluster Federation

## Architecture Overview

### Cluster Definitions
- **community**: Community Edition ClickHouse cluster
- **enterprise**: Enterprise Edition ClickHouse cluster  
- **federation**: Combined cluster of Community and Enterprise

### Data Flow
- **Read**: Query from Community's federation distributed table (includes both clusters)
- **Write**: Can write through Community or Enterprise; gradually switch to Enterprise

## Important Notes
1. Distributed DDL across Community and Enterprise is NOT supported - execute separately
2. Do NOT use `optimize_skip_unused_shards=1` when querying

---

## Migration Steps

### Step 1: Compatibility Verification

1. Configure Enterprise compatibility parameter to match Community version:
```sql
CREATE SETTINGS PROFILE compatibility SETTINGS compatibility='24.3' TO ALL;
```

2. Verify Enterprise can execute Community queries correctly

**Reference**: https://help.aliyun.com/zh/clickhouse/user-guide/analysis-and-solution-of-cloud-compatibility-and-performance-bottleneck-of-self-built-clickhouse

3. (Optional) Modify business SQL for compatibility if needed

---

### Step 2: Network Configuration

1. **Enterprise Console**: Add Community network segment to whitelist

2. **Enterprise Keeper**: Register Community node IPs for password-free access
```python
set /clickhouse/networks '<ip>::1</ip><ip>127.0.0.1</ip><ip><community_node_ip_1></ip><ip><community_node_ip_2></ip><ip><community_node_ip_3></ip><ip><community_node_ip_4></ip>'
```

> **Warning**: Enterprise CCU scaling operations will override this configuration. Do not scale during migration.

3. **Community config.xml**: Add Enterprise nodes to remote_servers

```xml
<remote_servers>
  <default>
    <shard>
      <!--Community shard info-->
    </shard>
    <shard>
      <!--Community shard info-->
    </shard>
    ...
    <shard> <!-- Add Enterprise VPC address or endpoint -->
      <replica>
        <host><enterprise_endpoint_or_vpc_ip></host>
        <port>9000</port>
      </replica>
      <internal_replication>true</internal_replication>
    </shard>
  </default>
</remote_servers>
```

---

### Step 3: Business Switchover

1. **Write data**: Switch to Enterprise
2. **Read data**: Use Community's federation distributed table

---

### Step 4: Node Decommission

1. Gradually remove Community nodes from config.xml
2. Note: Query aggregation still happens on Community, may affect performance
3. Evaluate minimum Community nodes needed for business

---

### Step 5: Final Switchover

1. Wait for Community data to expire (based on TTL)
2. Switch read traffic to Enterprise

---

## Rollback Plan

### From Step 2
- Remove Enterprise nodes from Community config.xml
- Export Enterprise data back to Community using "INSERT FROM REMOTE" method

### From Step 3
- Switch writes back to Community
- Export Enterprise data back to Community

### From Step 5
- Switch reads back to Community
