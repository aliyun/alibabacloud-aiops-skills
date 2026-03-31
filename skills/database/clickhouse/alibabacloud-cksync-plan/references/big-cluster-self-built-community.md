# Self-Built + Cloud ClickHouse Big Cluster Federation

## Background

Self-built ClickHouse migration has complexities:
- Large data volume → slow migration
- No time-based partitioning → cannot migrate by partition
- Double-write logic increases business complexity

## Applicable Scenarios

- Large data volume
- Short allowed write-stop time (<20 min) or no write-stop allowed
- Other table engines besides MergeTree (e.g., Log engine)
- Acceptable cost of running two clusters
- High customer participation; willing to modify business read/write SQL

## Architecture

### Cluster Definitions
- **customer**: Self-built ClickHouse cluster
- **cloud**: Alibaba Cloud ClickHouse cluster
- **federation**: Combined cluster of self-built and cloud

### Data Flow
- **Write**: To cloud cluster's distributed table
- **Read**: From federation cluster's distributed table

### ReplacingMergeTree Considerations
For tables requiring data on same node:
1. After full data migration to cloud, query from `cloud` cluster instead of `federation`
2. Change `FINAL` to `GROUP BY`

---

## Migration Steps

### Step 1: Whitelist Configuration

Enable IP whitelist between self-built and cloud ClickHouse.

---

### Step 2: Configure config.xml and users.xml

**config.xml** - Add federation cluster configuration:
```xml
<?xml version="1.0" ?>
<yandex>
  <!-- Other configurations... -->
  
  <listen_host>0.0.0.0</listen_host>

  <remote_servers>
    <!-- Federation cluster: includes both self-built and cloud nodes -->
    <federation>
       <!-- Self-built nodes -->
       <shard>
         <replica>
           <host><self_built_node_ip_1></host>
           <port>9000</port>
           <user>default</user>
           <password>password</password>
         </replica>
         <internal_replication>true</internal_replication>
       </shard>
       <shard>
         <replica>
           <host><self_built_node_ip_2></host>
           <port>9000</port>
           <user>default</user>
           <password>password</password>
         </replica>
         <internal_replication>true</internal_replication>
       </shard>
       <shard>
         <replica>
           <host><self_built_node_ip_3></host>
           <port>9000</port>
           <user>default</user>
           <password>password</password>
         </replica>
         <internal_replication>true</internal_replication>
       </shard>
       <!-- Cloud nodes -->
       <shard>
         <replica>
           <host><cloud_node_ip_1></host>
           <port>3003</port>
           <user>default</user>
           <password>password</password>
         </replica>
         <internal_replication>true</internal_replication>
       </shard>
       <shard>
         <replica>
           <host><cloud_node_ip_2></host>
           <port>3003</port>
           <user>default</user>
           <password>password</password>
         </replica>
         <internal_replication>true</internal_replication>
       </shard>
       <shard>
         <replica>
           <host><cloud_node_ip_3></host>
           <port>3003</port>
           <user>default</user>
           <password>password</password>
         </replica>
         <internal_replication>true</internal_replication>
       </shard>
     </federation>
  </remote_servers>
  
  <!-- Macros for Replicated tables -->
  <macros>
    <shard>s0</shard>
    <replica>r0</replica>
  </macros>
</yandex>
```

**users.xml** - Configure network access:
```xml
<yandex>
  <users>
    <default>
      <password/>
      <profile>default</profile>
      <quota>default</quota>
      <!-- Allow IPs from all nodes -->
      <networks>
        <host><self_built_access_ip_1></host>
        <host><self_built_access_ip_2></host>
        <host><self_built_access_ip_3></host>
        <host><self_built_node_ip_1></host>
        <host><self_built_node_ip_2></host>
        <host><self_built_node_ip_3></host>
      </networks>
    </default>
  </users>
</yandex>
```

---

### Step 3: Create Tables

1. **Cloud cluster**: Create same local tables as self-built

2. **Cloud cluster**: Create distributed table for writes
```sql
-- Distributed table uses 'cloud' cluster
CREATE TABLE database.distributed_write ON CLUSTER cloud 
ENGINE = Distributed(cloud, database, local_table, sharding_key);
```

3. **Both clusters**: Create distributed table for reads
```sql
-- Execute on both clusters; replace <customer|cloud> with appropriate cluster name
-- Distributed table uses 'federation' cluster
CREATE TABLE database.distributed_read ON CLUSTER <customer|cloud> 
ENGINE = Distributed(federation, database, local_table, sharding_key);
```

---

### Step 4: Verification

- Write via `distributed_write` → Data should go to cloud only
- Read via `distributed_read` → Should return data from both clusters

---

### Step 5: First Business Switchover

- Write to `distributed_write`
- Read from `distributed_read`

---

### Step 6: (Optional) Migrate Historical Data

Migrate existing data to cloud cluster temporary table.

**Recommended**: Use OSS as intermediate storage with BACKUP/RESTORE

---

### Step 7: (Optional) Merge Historical and Incremental Data

1. Stop writes
2. Use `MOVE PARTITION` to merge data to temporary table
3. `RENAME` tables

---

### Step 8: Decommission Self-Built Cluster

When all data is on cloud, remove self-built nodes from config.xml

---

### Step 9: Second Business Switchover

Rebuild read distributed table to use `cloud` cluster only

---

## Rollback Plan

- Switch writes back to self-built cluster
- Continue using `federation` distributed table for reads (can use self-built as entry point since cloud users.xml has self-built IPs whitelisted)
- Migrate cloud data back to self-built

**Note**: ReplacingMergeTree may have issues with rollback.

---

## Special Considerations

### External Table Engines
Kafka, MaterializedMySQL, etc.: After creating target tables, migrate Kafka engine tables to cloud cluster
