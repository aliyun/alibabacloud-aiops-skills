# Verification Method

## Script Execution Verification

**Success indicators:**
- Script exits with code 0
- Output contains `Report saved:` (single instance) or `Summary report:` (multi-instance) followed by a file path
- The report file exists at the indicated path and is non-empty

**Failure indicators:**
- `❌ aliyun CLI not found` — Aliyun CLI not installed or not in PATH
- `❌ Cluster {cluster_id} not found` — Cluster ID not found in any region (check ID correctness and credentials)
- `❌ No PolarDB MySQL instances found` — No PolarDB MySQL instances in the account (--all mode)
- `[WARN] ... Forbidden` or `... NoPermission` — RAM permission insufficient; refer to `ram-policies.md`

## Report Content Verification

### Single Instance Report
A complete single-instance HTML report should contain the following sections (when full inspection is run):
1. **Instance Information** — Cluster ID, version, spec, storage type, node list
2. **Resource Usage** — CPU / memory / IOPS / connections average and peak values with trend charts
3. **Space Analysis** — Top 20 tables by space, auto-increment primary key usage
4. **Slow Query Log** — Slow SQL statistics (count, max execution time, total time)
5. **Session Information** — Per-node total / active session counts
6. **Alert History** — CloudMonitor alert records within the inspection period

### Multi-Instance Report
- An `index.html` summary page listing all inspected instances with health scores
- Individual detail report files per instance in the same directory
- Aggregated statistics (total instances, danger / warning / healthy counts)

## Error State Verification

| Error Message | Meaning | Action |
|---|---|---|
| `[WARN] polardb describe-db-cluster-performance: ...` | Performance API call failed for one metric | Marked as "retrieval failed" in report; do NOT retry via alternative methods |
| `⚠️ Timed out` (space analysis) | DAS storage analysis task timed out after 150s | Space section shows "retrieval failed" |
| `⚠️ Failed` (session/auto-increment) | DAS async session or auto-increment API failed | Corresponding section shows "retrieval failed" |
| `Channel silenced` alerts filtered | Channel-silenced alerts are excluded from results | Expected behavior, not an error |
