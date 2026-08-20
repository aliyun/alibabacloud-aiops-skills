# Java GC Diagnosis Guide

## Diagnosis Mode Selection

### Log Analysis Mode (gclog_only)

**Applicable scenarios**: Java process has GC logging configured (JDK8: `-XX:+PrintGCDetails -Xloggc:<path>`; JDK11+: `-Xlog:gc*:file=<path>`)

**Characteristics**:
- Returns results immediately (no collection wait)
- Analyzes historical GC logs for retrospective troubleshooting
- No additional performance overhead

**Limitations**: Requires an existing GC log file; unavailable if JDK8 has no logging configured

**Parameters**: `diagMode=gclog_only`, duration parameter is ignored

### Incremental Collection Mode (collect)

**Applicable scenarios**: No GC logging configured, or precise JFR time-series data needed, or JDK11+ environment

**Characteristics**:
- Collects JFR + GC logs + OS metrics (5-10 minutes)
- Does not require pre-configured GC logging (JDK11+ can enable dynamically)
- Provides complete time-series, heap trends, and OS correlation analysis

**Limitations**: Requires waiting for the duration period; JDK8 cannot enable JFR dynamically and will fall back to GC log collection

**Parameters**: `diagMode=collect`, `duration=5` (default; recommended 5-10 minutes)

## Mode Selection Decision Tree

1. User explicitly mentions "GC logs" or "logging is enabled" → `gclog_only`
2. User describes performance issues without mentioning logs → Ask whether GC logging is enabled
3. User is unsure or has not configured logging → `collect` (more comprehensive, no prerequisites)
4. JDK8 environment + no logging configured → `collect` (automatically falls back to log collection mode)

## Agent Reply Template

When the user has not specified a mode, ask:

> GC diagnosis supports two modes:
> 1. **Log analysis**: directly analyze existing GC logs and return results immediately. Suitable when the Java process is already configured with `-Xlog:gc*` or `-XX:+PrintGCDetails`.
> 2. **Incremental collection**: collect 5-10 minutes of JFR + GC data in real time for deep analysis. No prior GC log configuration required, but you must wait for collection to complete.
>
> Is GC logging already enabled on your Java process?

## Command

`sysom-osops java analyze --type gc [--diagMode <gclog_only|collect>] [--duration <minutes>] [--pid <PID>]`

| Parameter | Description |
|-----------|-------------|
| --diagMode | Diagnosis mode: gclog_only / collect, default collect |
| --duration | Collection duration (minutes), default 5 for collect mode, ignored for gclog_only |
| --pid | Optional; auto-detects Java process when not specified |
| --pod | Optional; specifies pod name in container scenarios |

## Collection execution discipline (collect mode)

`collect` mode samples JFR + GC logs for **5–10 minutes** (minutes-scale, like
memory profiling):

- Tell the user the expected wait before starting; they can continue other work.
- Size the shell/tool timeout to at least **`(duration + 3)` minutes**; do not
  use 120–180 second timeouts for a 5-minute collection.
- Launch **once**. On client timeout with no envelope, do **not** auto-re-fire
  the same command; say it may still be running and ask whether to wait or check
  task status.

## Result Interpretation

The envelope contains GC diagnosis analysis results:
- GC event time-series and pause distribution
- Throughput assessment and optimization recommendations
- Heap memory usage trends

### Common Patterns

| Pattern | Symptoms | Recommendation |
|---------|----------|----------------|
| Frequent Full GC | Old generation full, promotion rate too high | Combine with `--type memory` for deeper heap analysis |
| Young GC jitter | Object allocation rate fluctuations causing unstable STW frequency | Check application-layer caching or batch processing logic |
| Mixed GC reclamation lag | G1 Mixed GC frequency cannot keep up with object promotion | Adjust InitiatingHeapOccupancyPercent |
| Excessive GC overhead | Application pause ratio > 10% | Evaluate GC algorithm selection and heap size configuration |


## Cross-Domain Diagnosis

- **GC causing high CPU** → Combine with `--type cpu` to analyze GC thread stack proportion
- **Root cause of frequent Full GC** → Combine with `--type memory` for heap analysis to locate leak source
- **Memory not released after GC** → Combine with `--type memory --duration 5` to track allocation trends
