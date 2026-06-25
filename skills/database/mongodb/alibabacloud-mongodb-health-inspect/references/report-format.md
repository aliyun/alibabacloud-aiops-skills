# Inspection Report Output Format Specification

## 1. Text Report Format (must be strictly followed)

> **Important**: All inspection report output **must** follow the format below. Do not modify the format structure. Use box-drawing characters for table rendering.

### Standard Output Format

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                  MongoDB (DDS) Instance Health Inspection Report              │
└──────────────────────────────────────────────────────────────────────────────┘
  Inspect Time: {InspectTime}
  Instance ID:  {DBInstanceId}
  Region:       {RegionId}
  Time Window:  {StartTime} ~ {EndTime}

════════════════════════════════════════════════════════════════════════════════
 Section 1: Configuration Risk Assessment
════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────┬──────────┬──────────────────────────────────────┬──────────────────────────────────────────────┐
  │ Check Item           │ Risk     │ Result                               │ Suggestion                                   │
  ├──────────────────────┼──────────┼──────────────────────────────────────┼──────────────────────────────────────────────┤
  │ Instance Status      │ ✅/⚠️/🔴 │ Running / Other                      │ No action / Needs attention                  │
  │ Architecture         │ ✅       │ Sharding / ReplicaSet                │ Current architecture fits the workload        │
  │ Storage Engine       │ ✅       │ WiredTiger / RocksDB                 │ Default engine, no change needed              │
  │ Disk Type            │ ✅/⚠️   │ Cloud Disk / Local Disk              │ Local disk has SPOF risk, consider cloud disk │
  │ Billing / Expiry     │ ✅/⚠️/🔴 │ PayAsYouGo / Subscription (N days)   │ Watch balance / Renew before expiry           │
  │ AZ Deployment        │ ✅/⚠️   │ Multi-AZ / Single-AZ                 │ Single-AZ has DC-level failure risk            │
  │ Lock Status          │ ✅/🔴   │ Unlocked / Locked({reason})          │ No action / Locked, immediate action needed   │
  │ MongoDB Version      │ ✅/⚠️   │ {EngineVersion} ({KernelVersion})    │ Outdated, upgrade recommended / Up to date    │
  │ Node Specs           │ ✅       │ Mongos:{spec}x{n}, Shard:{spec}x{n} │ Spec configuration is complete                │
  └──────────────────────┴──────────┴──────────────────────────────────────┴──────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════════
 Section 2: Instance Basic Information
════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────┬──────────────────────────────────────────────┐
  │ Item                         │ Value                                        │
  ├──────────────────────────────┼──────────────────────────────────────────────┤
  │ Instance Type                │ Sharding / ReplicaSet                        │
  │ Major Version                │ MongoDB {EngineVersion}                      │
  │ Kernel Version               │ {CurrentKernelVersion}                       │
  │ Storage Engine               │ {StorageEngine}                              │
  │ Storage Type                 │ {StorageType}                                │
  │ Charge Type                  │ {ChargeType}                                 │
  │ Instance Status              │ {DBInstanceStatus}                           │
  │ Creation Time                │ {CreationTime}                               │
  │ Max Connections              │ {MaxConnections}                             │
  │ Max IOPS                     │ {MaxIOPS}                                    │
  └──────────────────────────────┴──────────────────────────────────────────────┘

  Mongos Nodes ({Count}):
  ┌──────────────────────────┬──────────────────────────┬──────────┬──────────┐
  │ Node ID                  │ Spec                     │ Max Conn │ Status   │
  ├──────────────────────────┼──────────────────────────┼──────────┼──────────┤
  │ {NodeId}                 │ {NodeClass}              │ {N}      │ Running  │
  └──────────────────────────┴──────────────────────────┴──────────┴──────────┘

  Shard Nodes ({Count}):
  ┌──────────────────────────┬──────────────────────────┬──────────┬──────────┬──────────┬──────────┐
  │ Node ID                  │ Spec                     │ Disk(GB) │ Max Conn │ Max IOPS │ Status   │
  ├──────────────────────────┼──────────────────────────┼──────────┼──────────┼──────────┼──────────┤
  │ {NodeId}                 │ {NodeClass}              │ {N}      │ {N}      │ {N}      │ Running  │
  └──────────────────────────┴──────────────────────────┴──────────┴──────────┴──────────┴──────────┘

════════════════════════════════════════════════════════════════════════════════
 Section 3: Resource Usage (Last {N} Days)
════════════════════════════════════════════════════════════════════════════════

  [Shard Node Details]

  > {NodeId} (Shard)
    CPU:          avg {avg}%  peak {peak}%  {StatusIcon}
    Memory:       avg {avg}%  peak {peak}%  {StatusIcon}
    Connections:  avg {n}/{max} ({pct}%)  peak {n}/{max} ({pct}%)  {StatusIcon}
    Disk Usage:   avg {avg}%  peak {peak}%  {StatusIcon}
    IOPS Usage:   avg {avg}%  peak {peak}%  {StatusIcon}
    Disk BW:      avg {avg}% (R:{r}% W:{w}%)  peak {peak}% (R:{r}% W:{w}%)  {StatusIcon}
    Disk Space:   avg {size}  peak {size}
    Network:      in {n} B/s  out {n} B/s  req {n} ops
    Opcounters:   insert {avg}/{peak} | query {avg}/{peak} | update {avg}/{peak}
                  delete {avg}/{peak} | getmore {avg}/{peak} | command {avg}/{peak}

  [Mongos Node Details]

  > {NodeId} (Mongos)
    CPU:          avg {avg}%  peak {peak}%  {StatusIcon}
    Connections:  avg {n}  peak {n}  {StatusIcon}

════════════════════════════════════════════════════════════════════════════════
 Section 4: Space Usage TOP20
════════════════════════════════════════════════════════════════════════════════

  #   Database            Collection                   Total      Data       Index      Docs
  ─────────────────────────────────────────────────────────────────────────────────────────────
  1   {DbName}         {Collection}              {Total}    {Data}    {Index}    {Count}
  ...

  Total Used: {TotalUsed}

════════════════════════════════════════════════════════════════════════════════
 Section 5: Current Sessions
════════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────┬──────────┬──────────┬────────────┬────────┐
  │ Node ID                  │ Total    │ Active   │ Longest(s) │ Status │
  ├──────────────────────────┼──────────┼──────────┼────────────┼────────┤
  │ {NodeId}                 │ {N}      │ {N}      │ {N}        │ icon   │
  └──────────────────────────┴──────────┴──────────┴────────────┴────────┘

  Long-running sessions (>10s):
  {NodeId}: op {Op}, running {N}s, ns {Ns}, client {Client}

════════════════════════════════════════════════════════════════════════════════
 Section 6: Slow Log Statistics (Last {N} Days)
════════════════════════════════════════════════════════════════════════════════

  Total {N} slow query records

  > {NodeId} ({Count} records)
  #   Database       Time(ms)   Timestamp               Operation
  ────────────────────────────────────────────────────────────────────────
  1   {DBName}    {Time}    {ExecutionStartTime}   {SQLText}
  ...

════════════════════════════════════════════════════════════════════════════════
 Section 7: Alert History (Last {N} Days)
════════════════════════════════════════════════════════════════════════════════

  Total {N} alert records

  #   Time                  Level   Metric          Description
  ─────────────────────────────────────────────────────────────────────
  1   {Time}            crit    {Metric}      {Message}
  ...

════════════════════════════════════════════════════════════════════════════════
 Section 8: Inspection Conclusion & Suggestions
════════════════════════════════════════════════════════════════════════════════

  crit/warn/info {Specific suggestion}

┌──────────────────────────────────────────────────────────────────────────────┐
│                            Inspection Complete                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Format Requirements (mandatory)

1. **Must use box-drawing characters** (┌─┬┐│├┤└┘═) for table borders
2. **Configuration risk assessment must be a four-column table**: Check Item | Risk Level | Result | Suggestion
3. **Risk level icons**: ✅ Normal / ⚠️ Warning / 🔴 Critical / 🔵 Info
4. **Node details must show every node**: Node ID, role, spec, max connections, max IOPS
5. **Resource usage must be grouped**: Shard details + Mongos details (Sharding instances); ReplicaSet instances use Shard notation
6. **Each Shard node must include**: CPU / memory / connections / disk usage / IOPS usage / disk bandwidth / disk space / network / Opcounters
7. **Status icon rules** must not be changed

### Status Determination Rules

| Metric | Normal (🟢) | Warning (🟡) | Critical (🔴) |
|--------|------------|-------------|--------------|
| CPU Usage | < 60% | 60% - 80% | > 80% |
| Memory Usage | < 60% | 60% - 80% | > 80% |
| Connection Usage | < 60% | 60% - 80% | > 80% |
| Disk Usage | < 70% | 70% - 85% | > 85% |
| IOPS Usage | < 60% | 60% - 80% | > 80% |
| Disk Bandwidth Usage | < 60% | 60% - 80% | > 80% |
| Long Session (s) | < 60 | 60 - 300 | > 300 |

### Inspection Conclusion Generation Rules

Generate targeted suggestions based on inspection data:

**Configuration risk:**
- **Local disk instance**: ⚠️ Local disk has single-point failure risk, data reliability depends on a single physical machine. Suggest migrating to cloud disk instance and ensure auto-backup is enabled
- **Subscription expiry < 30 days**: ⚠️ Instance is about to expire, please renew in time to avoid service interruption
- **Subscription expiry < 7 days**: 🔴 Instance is about to be locked due to expiry, please renew immediately
- **Single AZ deployment**: ⚠️ Single availability zone deployment has datacenter-level failure risk. Suggest migrating to multi-AZ for higher availability
- **Instance locked**: 🔴 Instance is locked (reason: {LockMode}), requires immediate action. LockByExpiration = renew; LockByDiskQuota = expand storage
- **MongoDB version < 4.4**: ⚠️ Current version is outdated, suggest upgrading to 4.4+ for better performance and security patches
- **Pay-as-you-go instance**: 🔵 Remind to watch account balance, arrears will cause instance lockdown

**Resource performance:**
- **CPU peak > 80%**: Suggest upgrading Shard spec, adding Shards, or optimizing high-CPU slow queries
- **Memory peak > 80%**: Suggest upgrading spec or checking if working set exceeds memory
- **Connection usage > 80%**: Suggest checking connection pool configuration, investigate connection leaks
- **Disk usage > 85%**: Suggest cleaning unused collections, archiving historical data, consider expanding storage
- **IOPS usage > 80%**: Suggest optimizing IO-intensive operations, checking indexes, or upgrading spec
- **Disk bandwidth usage > 80%**: Suggest optimizing bulk reads/writes or upgrading spec
- **Slow log count > 10**: Suggest optimizing top slow queries, adding indexes
- **Long session > 5 minutes**: Suggest investigating blocking operations, reviewing long transactions
- **Alert events > 0**: Remind user to follow up on corresponding alert rules in the console

---

## 2. HTML Report Format Specification (`--format html`)

> **Important**: HTML reports use ECharts for rendering monitoring trend charts. All charts must strictly follow the layout specifications below.

### Overall Structure

1. **Configuration Risk Assessment** — Four-column table (Check Item/Risk Level/Result/Suggestion), risk items highlighted
2. **Instance Basic Information** — Three-column grid layout, compact key-value display
3. **Node List** — Mongos / Shard / ConfigServer tables
4. **Resource Usage Horizontal Comparison Table** — Nodes as column headers, metrics as rows (horizontally scrollable when many nodes)
5. **Status Icons** — Placed in the last table row, not mixed into data cells

### Monitoring Trend Chart Groups

Split by instance type, each group with an `<h3>` subtitle:

- **Sharding Instance**:
  - **Shard Monitoring Trends** (4 charts in 2×2 grid): CPU / Memory / Connection Usage / IOPS Usage (each chart shows one line per Shard node)
  - **Mongos Monitoring Trends** (2 charts): CPU / Connection Count (all Mongos nodes)
- **ReplicaSet Instance**:
  - **Node Monitoring Trends** (4 charts in 2×2 grid): CPU / Memory / Connection Usage / IOPS Usage (all nodes)

### ECharts Unified Layout Parameters (must follow)

All charts must use the same layout parameters; do not adjust individually:

```javascript
legend: { top: 0, type: 'scroll', textStyle: { fontSize: 10 } }
grid:   { left: 45, right: 15, top: 30, bottom: 55 }
dataZoom: [
  { type: 'inside' },
  { type: 'slider', height: 20, bottom: 5 }
]
```

**Prohibited**: legend using `bottom` positioning (will be obscured by dataZoom slider)

### Chart Linkage

Charts within the same group must have linked dataZoom — dragging the time axis on any chart synchronizes all others.

### Legend Labels

- Use full node ID + role, e.g., `d-bp1xxx(Shard)` / `s-bp1yyy(Mongos)`, no abbreviations
- Use `type:'scroll'` to prevent overflow when there are many nodes

### SQL Summary Column

- CSS truncation: `max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap`
- Full SQLText in `title` attribute for hover viewing
- Add `cursor:pointer` to indicate interactivity

### Multi-Instance Summary Page (index.html)

For multi-instance inspections, generate an additional `index.html` in the output directory:
- Top: title + inspection time
- Status filters (All / Abnormal / Warning / Normal / Failed)
- Risk detail cards (aggregating high/medium risk items across all instances)
- Instance card grid: each card shows Instance ID, Region, spec, key metrics (CPU/memory/connections/disk/IOPS average & peak), slow log/alert counts, status color blocks, detail links
