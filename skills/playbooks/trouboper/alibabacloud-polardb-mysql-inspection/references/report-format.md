# Inspection Report Output Format Specification

## 1. Text Report Format (must be strictly followed)

> **Important**: All inspection report output **must** follow the format below. Do not modify the format structure. Use box-drawing characters for table rendering.

### Standard Output Format

```
+------------------------------------------------------------------------------+
|                    PolarDB MySQL Instance Health Inspection Report            |
+------------------------------------------------------------------------------+
  Inspection Time: {InspectTime}
  Instance ID:     {DBClusterId}
  Region:          {RegionId}

================================================================================
 1. Instance Basic Information
================================================================================

  +------------------------------+----------------------------------------------+
  | Item                         | Value                                        |
  +------------------------------+----------------------------------------------+
  | Database Type                | MySQL                                        |
  | Major Version                | MySQL {DBVersion}                            |
  | Kernel Minor Version         | {DBRevisionVersion}                          |
  | Latest Available Version     | {DBLatestVersion}                            |
  | Version Status               | Up-to-date / Upgradable                      |
  | Proxy Version                | {ProxyRevisionVersion}                       |
  | Cluster Status               | {DBClusterStatus}                            |
  | Storage Type                 | {StorageType}                                |
  | Storage Used                 | {StorageUsed}                                |
  | Storage Max                  | {StorageMax}                                 |
  +------------------------------+----------------------------------------------+

  Node Details ({NodeCount} nodes):
  +--------------------------+--------+----------+--------------------------+------+----------+----------+----------+
  | Node ID                  | Role   | Status   | Spec                     | CPU  | Memory   | Max Conn | Max IOPS |
  +--------------------------+--------+----------+--------------------------+------+----------+----------+----------+
  | {NodeId}                 | Writer | Running  | {NodeClass}              | {N}  | {N}GB    | {N}      | {N}      |
  | {NodeId}                 | Reader | Running  | {NodeClass}              | {N}  | {N}GB    | {N}      | {N}      |
  +--------------------------+--------+----------+--------------------------+------+----------+----------+----------+

================================================================================
 2. Resource Usage (Last 24 Hours)
================================================================================

  [Cluster Overview]
  +----------------+----------------------+----------------------+--------+
  | Metric         | Average              | Peak                 | Status |
  +----------------+----------------------+----------------------+--------+
  | CPU            | {avg}%               | {peak}%              |        |
  | Memory         | {avg}%               | {peak}%              |        |
  | Space          | {pct}% ({size})      | {pct}% ({size})      |        |
  | IO Throughput  | {avg} KB/s           | {peak} KB/s          |        |
  | Connections    | {n}/{max} ({pct}%)   | {n}/{max} ({pct}%)   |        |
  +----------------+----------------------+----------------------+--------+

  [Per-Node Details]

  > {NodeId} ({Role})
    CPU:    Average {avg}%  Peak {peak}%  {status_icon}
    Memory: Average {avg}%  Peak {peak}%  {status_icon}
    Conn:   Average {n}  Peak {n}  Usage {pct}% (max {max})  {status_icon}
    Active: Average {n}  Peak {n}

================================================================================
 3. Space Usage Details TOP20
================================================================================

  #   Database            Table                    Total      Data       Index      Rows
  --------------------------------------------------------------------------------------------
  1   {DbName}            {TableName}              {Total}    {Data}     {Index}    {Rows}
  ...

  Total Used Space: {TotalUsed}
  Daily Growth:     +{DailyIncrement} / -{DailyDecrement}

================================================================================
 4. Slow Log Statistics (Last 7 Days)
================================================================================

  #   Database         Count    Total(s)     Max(s)    SQL Summary
  --------------------------------------------------------------------------------------------
  1   {DBName}         {Count}  {TotalTime}  {MaxTime} {SQLText}...
  ...

  Total {N} slow query entries

================================================================================
 5. Inspection Conclusions and Suggestions
================================================================================

  Kernel version upgradable: current {current} -> latest {latest}
  {Specific suggestions based on data}

+------------------------------------------------------------------------------+
|                              Inspection Complete                             |
+------------------------------------------------------------------------------+
```

### Format Requirements (mandatory)

1. **Must use box-drawing characters** for table borders
2. **Node details must show every node**: Node ID, role, status, spec, CPU cores, memory, max connections, max IOPS
3. **Resource usage must have two parts**: cluster overview table + per-node detail sections
4. **Each node's resources** shown independently: CPU, memory, connections (with usage rate and active connections)
5. **Version info must include minor version**: kernel minor version (DBRevisionVersion), latest available version, version status, Proxy version
6. **Status icon rules** must not be changed

### Status Determination Rules

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| CPU Usage | < 60% | 60% - 80% | > 80% |
| Memory Usage | < 60% | 60% - 80% | > 80% |
| Space Usage | < 70% | 70% - 85% | > 85% |
| Connection Usage | < 60% | 60% - 80% | > 80% |

### Inspection Conclusion Generation Rules

Generate targeted suggestions based on inspection data:
- **Version is not latest**: Suggest upgrade, show current and latest version numbers
- **CPU peak > 80%**: Suggest analyzing high-CPU slow queries, consider upgrading node spec or adding read-only nodes
- **Memory peak > 80%**: Suggest checking buffer pool configuration, analyze memory-intensive queries
- **Space usage > 85%**: Suggest cleaning unused data, archiving historical tables, consider expanding storage
- **Connection usage > 80%**: Suggest checking connection pool configuration, investigate connection leaks
- **Slow log count > 10**: Suggest optimizing top slow query SQL, add indexes or rewrite SQL

---

## 2. HTML Report Format Specification (`--format html`)

> **Important**: HTML reports use ECharts for rendering monitoring trend charts. All charts must strictly follow the layout specifications below.

### Overall Structure

1. **Instance Basic Information** — Three-column grid layout, compact key-value display
2. **Resource Usage** — Horizontal comparison table (nodes as column headers, metrics as rows), horizontally scrollable when many nodes
3. **Status Icons** — Placed in the last table row, not mixed into data cells

### Monitoring Trend Chart Groups

Split into two groups, each with an `<h3>` subtitle:

- **Proxy Monitoring Trends** (2 charts):
  - Proxy CPU Usage (single line, Y-axis `max:100`)
  - Proxy Session Routing (LsnNotMatch + QueriesInTrx dual-line in one chart, Y-axis `max:null` auto-scale)
- **DB Monitoring Trends** (4 charts in 2x2 grid):
  - CPU Usage | Memory Usage | IOPS Usage | Connection Usage (each chart shows one line per node, Y-axis `max:100`)

### ECharts Unified Layout Parameters (must follow)

All 6 charts must use the same layout parameters; do not adjust individually:

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

The dataZoom of all 6 charts must be linked — dragging the time axis on any chart synchronizes all others.

### Legend Labels

- Use full node ID + role, e.g., `pi-bp1gwm8d0w0488z87(ReadWrite)`, no abbreviations
- Use `type:'scroll'` to prevent overflow when there are many nodes

### SQL Summary Column

- CSS truncation: `max-width:400px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap`
- Full SQL in `title` attribute for hover viewing
- Add `cursor:pointer` to indicate interactivity
