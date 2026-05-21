
## Architecture Selection

Choose the right Tair architecture based on data volume, throughput requirements, and read/write ratio.

### Key Concepts

| Component | Description |
|-----------|-------------|
| Node | Smallest unit, runs Redis-compatible process |
| Shard | Group of nodes storing a subset of data |
| Master node | Handles write operations |
| Replica node | Copy of master, provides failover |
| Read-only node | Serves read traffic only (read/write splitting) |
| Proxy node | Routes requests to appropriate nodes |

### Architecture Comparison

| Dimension | Standard | Cluster |
|-----------|----------|---------|
| Structure | One master + replicas | Multiple shards, each with master + replicas |
| Data partitioning | No (single shard) | Yes (distributed across shards) |
| Best for | Small data, stable QPS | Large data, high QPS, throughput-intensive |
| Read/write splitting | Supported | Supported |

### Standard Architecture

Master-replica architecture where master handles all reads/writes, replica maintains real-time copy.

**When to use:**
- Data fits on single instance
- Stable query rate within single-node capacity
- Need persistent storage with high availability

**Standard + Read/Write Splitting:**
- Add proxy nodes + read-only nodes
- Proxy routes writes to master, distributes reads
- Use when: high QPS with read-heavy workload

### Cluster Architecture

Data partitioned across multiple shards. Each shard uses master-replica for HA.

**When to use:**
- Large data volumes exceeding single-node capacity
- High QPS requirements
- Throughput-intensive workloads

**Cluster + Read/Write Splitting:**
- Each shard adds dedicated read-only nodes
- Use when: read traffic exceeds master node capacity per shard

### Selection Decision Tree

**Example:**

```
Data volume > single-node capacity?
├── Yes → Cluster architecture
│   └── Read-heavy? → Enable read/write splitting
└── No → Standard architecture
    └── Read-heavy? → Enable read/write splitting
```

**Reference:** [Tair Product Architecture](https://www.alibabacloud.com/help/en/redis/product-overview/product-architecture)
