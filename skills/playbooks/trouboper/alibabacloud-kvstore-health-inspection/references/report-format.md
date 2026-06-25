# KVStore Health Inspection Report Format Specification

This document specifies the output formats supported by the health inspection tool.

## Supported Formats

The tool supports three output formats, selected via the `--format` parameter:

1. **html** (default) - Interactive HTML report with ECharts visualizations
2. **markdown** - Markdown text report suitable for documentation
3. **text** - Plain text report with box-drawing characters for terminal display

## 1. HTML Report Format

### File Naming

```
kvstore_health_inspection_<instance-id>_<YYYYMMDD_HHMMSS>.html
```

Example: `kvstore_health_inspection_r-bp1234567890_20260315_143052.html`

### Structure

The HTML report is a self-contained single file with embedded CSS and JavaScript (ECharts loaded from CDN).

#### Header Section

```html
<div class="header">
  <h1>Redis Instance Health Inspection Report</h1>
  <div class="timestamp">Generated: YYYY-MM-DD HH:MM:SS</div>
  <div class="instance-info">
    <span>Instance: <instance-id></span>
    <span>Region: <region></span>
  </div>
</div>
```

#### Section 1: Instance Basic Information

Table layout with key-value pairs:

| Field | Description |
|-------|-------------|
| Instance ID | Instance identifier |
| Instance Name | User-defined name |
| Instance Class | Specification (e.g., redis.master.small.default) |
| Instance Type | Tair or Redis |
| Engine Version | Redis version (e.g., 6.0) |
| Architecture | standard/cluster/readwrite |
| Status | Running/Stopped/etc |
| Max Connections | Connection limit |
| Max Bandwidth | Bandwidth limit (MB/s) |
| Capacity | Storage capacity (MB) |
| Create Time | Instance creation timestamp |

For cluster/readwrite architectures, include:
- DB Node Details table (node ID, role, capacity, connections, bandwidth)
- Proxy Node Details table (node ID, connections)

#### Section 2: Current Sessions

**Connection Summary Grid:**
- Max Connections
- Used Connections (Peak)
- Connection Usage (Avg/Peak)
- Proxy Connection Usage (Avg/Peak) - cluster/readwrite only

**Source Statistics Table:**
| Client IP | Sessions |
|-----------|----------|
| 192.168.1.100 | 150 |
| 192.168.1.101 | 120 |

Top 20 client IPs by session count.

**Session Details Table:**
| # | Addr | Cmd | Age(s) | Idle(s) | DB | Node | Flags |
|---|------|-----|--------|---------|----|----- |-------|
| 1 | 192.168.1.100:54321 | GET | 3600 | 0 | 0 | db-0 | S |

Top 50 sessions sorted by idle time (ascending).

#### Section 3: Resource Usage

**Summary Table:**

| Metric | Average | Peak | Status |
|--------|---------|------|--------|
| CPU Usage | 45.32% | 85.67% | ❌ HIGH |
| Connection Usage | 32.15% | 62.40% | ⚠️ MED |
| Memory Usage | 78.90% | 92.15% | ⚠️ MED |
| Input Bandwidth | 12.45% | 25.80% | ✅ OK |
| Output Bandwidth | 18.76% | 35.92% | ✅ OK |

**Status Icons:**
- ✅ OK: peak <= 60%
- ⚠️ MED: 60% < peak <= 80%
- ❌ HIGH: peak > 80%

**ECharts Line Charts:**

Five interactive charts (one per metric):
- CPU Usage
- Connection Usage
- Memory Usage
- Input Bandwidth
- Output Bandwidth

Each chart includes:
- Time series line plot
- Data zoom slider
- Tooltip with timestamp and value
- Responsive layout (2 columns on desktop, 1 column on mobile)

For proxy-enabled architectures, additional charts:
- Proxy CPU Usage
- Proxy Connection Usage
- Proxy Memory Usage
- Proxy Input Bandwidth
- Proxy Output Bandwidth

#### Section 4: Big Key / Hot Key

**Large Keys Table (Top 10):**

| # | DB | Type | Memory | Key |
|---|----|------|--------|-----|
| 1 | 0 | string | 25.60MB | user:session:large:... |

**Big Keys Table (Top 10):**

| # | DB | Type | Elements | Key |
|---|----|------|----------|-----|
| 1 | 0 | hash | 150000 | product:details:... |

**Hot Keys Table (Top 10):**

| # | DB | Type | QPS | Key |
|---|----|------|-----|-----|
| 1 | 0 | string | 1250 | hot:counter:... |

#### Section 5: Slow Log Analysis

**Slow Commands Table (Top 15):**

| # | Command | Count | Total(ms) | Avg(ms) | Max(ms) | Sample Key |
|---|---------|-------|-----------|---------|---------|------------|
| 1 | KEYS | 150 | 15234.56 | 101.56 | 523.45 | user:* |

Sorted by total elapsed time (descending).

#### Section 6: Alert History

**Alert Rules Table:**

| Rule Name | Metric | Critical | Warn | Info | State |
|-----------|--------|----------|------|------|-------|
| High CPU | CpuUsage | 90% | 80% | 70% | 🟢 OK |

**Alert Records Table (Top 20):**

| Time | Level | Rule | Metric | Value | Threshold |
|------|-------|------|--------|-------|-----------|
| 2026-03-15 14:30 | 🔴 P1 | High CPU | CpuUsage | 92.5% | 90% |

Level icons:
- 🔴 P1/P2: Critical
- 🟡 P3/P4: Warning

#### Section 7: Suggestions

**High Risk (danger level):**

Ordered list of critical issues requiring immediate attention.

**Medium Risk (warning level):**

Ordered list of issues that should be monitored or addressed.

Each suggestion includes bilingual text (English/Chinese) with `data-en` and `data-zh` attributes for language switching.

#### Footer

```html
<div class="footer">
  Generated by alibabacloud-kvstore-health-inspection
</div>
```

### Styling

- Modern responsive design
- Color-coded status indicators
- Sticky table headers
- Mobile-friendly layout
- Print-optimized CSS

### Language Support

The HTML report includes a language switcher (EN/中文) that toggles all bilingual content using JavaScript.

## 2. Markdown Report Format

### File Naming

```
kvstore_health_inspection_<instance-id>_<YYYYMMDD_HHMMSS>.md
```

### Structure

Standard Markdown with tables and headers:

```markdown
# Redis Instance Health Inspection Report

**Generated:** YYYY-MM-DD HH:MM:SS  
**Instance:** <instance-id>  
**Region:** <region>

## 1. Instance Basic Information

| Field | Value |
|-------|-------|
| Instance ID | <instance-id> |
| Instance Name | <name> |
| ... | ... |

## 2. Current Sessions

### Connection Summary

- Max Connections: 10000
- Used Connections (Peak): 6240
- Connection Usage (Avg/Peak): 32.15% / 62.40%

### Source Statistics (Top 10)

| Client IP | Sessions |
|-----------|----------|
| 192.168.1.100 | 150 |
| ... | ... |

## 3. Resource Usage (Last 7 Days)

| Metric | Average | Peak | Status |
|--------|---------|------|--------|
| CPU Usage | 45.32% | 85.67% | ❌ HIGH |
| ... | ... | ... | ... |

## 4. Big Key / Hot Key

### Large Keys (by Memory)

| # | DB | Type | Memory | Key |
|---|----|------|--------|-----|
| 1 | 0 | string | 25.60MB | user:session:... |

### Big Keys (by Elements)

...

### Hot Keys (by QPS)

...

## 5. Slow Log Analysis (Last 7 Days)

| # | Command | Count | Total(ms) | Avg(ms) | Max(ms) | Sample Key |
|---|---------|-------|-----------|---------|---------|------------|
| 1 | KEYS | 150 | 15234.56 | 101.56 | 523.45 | user:* |

## 6. Alert History

### Alert Rules

| Rule Name | Metric | Critical | Warn | Info | State |
|-----------|--------|----------|------|------|-------|
| High CPU | CpuUsage | 90% | 80% | 70% | 🟢 OK |

### Alert Records

| Time | Level | Rule | Metric | Value | Threshold |
|------|-------|------|--------|-------|-----------|
| 2026-03-15 14:30 | 🔴 P1 | High CPU | CpuUsage | 92.5% | 90% |

## 7. Suggestions

### 🔴 High Risk

1. CPU usage peak 85.67% (> 80%) - correlated with 3 hot keys
   - Optimize hot key access patterns
   - Consider adding read replicas

### 🟡 Medium Risk

1. Memory usage peak 92.15% (> 80%)
   - Review large key usage
   - Consider key splitting or expiration policies

---

*Generated by alibabacloud-kvstore-health-inspection*
```

## 3. Text Report Format

### File Naming

```
kvstore_health_inspection_<instance-id>_<YYYYMMDD_HHMMSS>.txt
```

### Structure

Plain text with Unicode box-drawing characters for visual structure:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Redis Instance Health Inspection Report                   │
└──────────────────────────────────────────────────────────────────────────────┘

Generated: 2026-03-15 14:30:52
Instance: r-bp1234567890
Region: cn-hangzhou

════════════════════════════════════════════════════════════════════════════════
1. Instance Basic Information
════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────┬────────────────────────────────────────────┐
│ Item                            │ Value                                      │
├─────────────────────────────────┼────────────────────────────────────────────┤
│ Instance ID                     │ r-bp1234567890                             │
│ Instance Name                   │ Production Redis                           │
│ Instance Class                  │ redis.master.small.default                 │
│ Instance Type                   │ Redis                                      │
│ Engine Version                  │ 6.0                                        │
│ Architecture                    │ standard                                   │
│ Status                          │ Running                                    │
│ Max Connections                 │ 10000                                      │
│ Max Bandwidth                   │ 128 MB/s                                   │
│ Capacity                        │ 2048 MB                                    │
│ Create Time                     │ 2025-01-15 10:30:00                        │
└─────────────────────────────────┴────────────────────────────────────────────┘

════════════════════════════════════════════════════════════════════════════════
2. Current Sessions
════════════════════════════════════════════════════════════════════════════════

Max Connections: 10000
Used Connections (Peak): 6240
Connection Usage (Avg/Peak): 32.15% / 62.40%

[Source Statistics - Top 10]
┌────────────────────────────────────┬───────────────┐
│ Client IP                          │ Sessions      │
├────────────────────────────────────┼───────────────┤
│ 192.168.1.100                      │ 150           │
│ 192.168.1.101                      │ 120           │
│ ...                                │ ...           │
└────────────────────────────────────┴───────────────┘

════════════════════════════════════════════════════════════════════════════════
3. Resource Usage (Last 7 Days)
════════════════════════════════════════════════════════════════════════════════

┌─────────────────┬─────────────────────┬─────────────────────┬────────────────┐
│ Metric          │ Average             │ Peak                │ Status         │
├─────────────────┼─────────────────────┼─────────────────────┼────────────────┤
│ CPU             │      45.32%         │      85.67%         │ ❌ HIGH        │
│ Connection      │      32.15%         │      62.40%         │ ⚠️ MED         │
│ Memory          │      78.90%         │      92.15%         │ ⚠️ MED         │
│ Input BW        │      12.45%         │      25.80%         │ ✅ OK          │
│ Output BW       │      18.76%         │      35.92%         │ ✅ OK          │
└─────────────────┴─────────────────────┴─────────────────────┴────────────────┘

════════════════════════════════════════════════════════════════════════════════
4. Big Key / Hot Key
════════════════════════════════════════════════════════════════════════════════

[Large Keys (by Memory) - Top 10]
  #  DB  Type      Memory        Key
───  ───  ────────  ────────────  ──────────────────────────────
  1    0  string    25.60MB       user:session:large:...

[Big Keys (by Elements) - Top 10]
  #  DB  Type      Elements    Key
───  ───  ────────  ──────────  ──────────────────────────────
  1    0  hash      150000      product:details:...

[Hot Keys (by QPS) - Top 10]
  #  DB  Type      QPS         Key
───  ───  ────────  ──────────  ──────────────────────────────
  1    0  string    1250        hot:counter:...

════════════════════════════════════════════════════════════════════════════════
5. Slow Log Analysis (Last 7 Days)
════════════════════════════════════════════════════════════════════════════════

Total: 245 records

  #  Command       Count  Total(ms)   Avg(ms)   Max(ms)  Sample Key
───  ────────────  ─────  ──────────  ─────────  ─────────  ────────────────────
  1  KEYS            150    15234.56     101.56     523.45  user:*
  2  SMEMBERS         95     8234.12      86.67     412.30  product:tags:...

════════════════════════════════════════════════════════════════════════════════
6. Alert History
════════════════════════════════════════════════════════════════════════════════

Alert Rules: 3 configured
┌─────────────────────────┬───────────────────┬──────────┬──────────┬──────────┬─────────┐
│ Rule Name               │ Metric            │ Critical │ Warn     │ Info     │ State   │
├─────────────────────────┼───────────────────┼──────────┼──────────┼──────────┼─────────┤
│ High CPU                │ CpuUsage          │ 90%      │ 80%      │ 70%      │ OK      │
│ High Memory             │ MemoryUsage       │ 95%      │ 85%      │ 75%      │ OK      │
│ High Connections        │ ConnectionUsage   │ 90%      │ 80%      │ 70%      │ OK      │
└─────────────────────────┴───────────────────┴──────────┴──────────┴──────────┴─────────┘

Alert Records: 12 total
┌───────────────────┬──────┬─────────────────┬───────────────┬──────────┬──────────┐
│ Time              │ Lvl  │ Rule            │ Metric        │ Value    │ Threshold│
├───────────────────┼──────┼─────────────────┼───────────────┼──────────┼──────────┤
│ 2026-03-15 14:30  │ P1   │ High CPU        │ CpuUsage      │ 92.5%    │ 90%      │
│ 2026-03-14 09:15  │ P2   │ High Memory     │ MemoryUsage   │ 88.3%    │ 85%      │
└───────────────────┴──────┴─────────────────┴───────────────┴──────────┴──────────┘

════════════════════════════════════════════════════════════════════════════════
7. Suggestions
════════════════════════════════════════════════════════════════════════════════

[🔴 High Risk]
1. CPU usage peak 85.67% (> 80%) - correlated with 3 hot keys
   Optimize hot key access patterns, consider adding read replicas

[🟡 Medium Risk]
1. Memory usage peak 92.15% (> 80%)
   Review large key usage, consider key splitting or expiration policies
2. Connection usage peak 62.40% (> 60%)
   Monitor trend, review connection pooling strategy

────────────────────────────────────────────────────────────────────────────────
Generated by alibabacloud-kvstore-health-inspection
```

## Conditional Sections

When using the `--item` parameter to select specific inspection dimensions, the report will only include the selected sections:

- `--item resource` → Only Section 3 (Resource Usage)
- `--item session` → Only Section 2 (Current Sessions)
- `--item bigkey` → Only Section 4 (Big Key / Hot Key)
- `--item slowlog` → Only Section 5 (Slow Log Analysis)
- `--item alert` → Only Section 6 (Alert History)

Sections 1 (Instance Info) and 7 (Suggestions) are always included.

## Output Location

- **Single instance**: `~/Downloads/` (default) or specified via `--output`
- **Multiple instances**: `~/Downloads/kvstore_health_inspection/` with an `index.html` summary page

## Character Encoding

All reports use UTF-8 encoding to support bilingual content and Unicode symbols.
