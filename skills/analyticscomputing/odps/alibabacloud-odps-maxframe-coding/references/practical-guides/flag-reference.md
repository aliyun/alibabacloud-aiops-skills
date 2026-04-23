# MaxFrame Flag Reference

This document provides a comprehensive reference for MaxCompute Flags, runtime flags, and MaxFrame runtime parameters, including their meanings, default values, valid ranges, and typical use cases.

## Configuration Overview

### MaxCompute SQL Flags

All MaxCompute SQL-related flags are managed through the `options.sql.settings` dictionary:

```python
from maxframe import options

options.sql.settings = {
    # Example: Set maximum job runtime to 72 hours
    "odps.sql.job.max.time.hours": 72,
    # Example: Specify custom runtime image
    "odps.session.image": "common",
    # Example: Set split DOP to 50000 for all tables
    "odps.sql.split.dop": '{"*":50000}',
    # Example: Set batch size to 1024 rows
    "odps.sql.executionengine.batch.rowcount": 1024,
}
```

### MaxFrame Options

MaxFrame's own runtime parameters are configured directly via `options.xxx`:

```python
from maxframe import options

# Example: Set LogView retention to 24 hours
options.session.logview_hours = 24

# Example: Set retry count for retryable errors
options.retry_times = 3

# Example: Enable MaxCompute query optimization
options.sql.enable_mcqa = True
```

## MaxCompute SQL Flags Reference

### Parallelism and Split

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.sql.split.dop` | Configure data read parallelism (DOP) based on column statistics (CMF). Format: `{table_name: count}`. Use `*` for all tables, e.g., `{"*":50000}`. | 1-99999; No default | Enable explicitly for large tables or large-scale tasks |
| `odps.stage.mapper.split.size` | Split size (MB) when CMF is unavailable | ≥1; Default 256MB | Usually keep default |

### Resources and Memory

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.stage.mapper.mem` | Memory (MB) for single Mapper instance | 1024-12288; Default 1024 | Increase for OOM with large data or complex processing |
| `odps.stage.reducer.mem` | Memory (MB) for single Reducer instance | 1024-12288; Default 1024 | Increase for OOM during shuffle operations |
| `odps.stage.joiner.mem` | Memory (MB) for single Joiner instance | 1024-12288; Default 1024 | Increase for OOM during complex joins |
| `odps.stage.reducer.num` | Number of Reducer instances | Max 10000; Default: auto | Increase for large-scale shuffle or data skew |
| `odps.stage.joiner.num` | Number of Joiner instances | Max 10000; Default: auto | Increase for large joins or data skew |

### Shuffle and Output Safety

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.sql.runtime.flag.fuxi_streamline_x_EnableNormalCheckpoint` | Enable backup for Mapper intermediate data | Default: disabled | Enable for long-running, large shuffle jobs |
| `fuxi_ShuffleService_client_CheckpointMaxCopy` | Number of backup copies | Default: 1 | Set to 2 for improved fault tolerance in large shuffle jobs |
| `odps.sql.sys.flag.fuxi_JobMaxInternalFolderSize` | Maximum shuffle intermediate data size (MB) | Default: system limit | Increase if encountering "Internal data size exceeds limit" errors |

### Computation Stability and Monitoring

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.sql.runtime.flag.fuxi_EnableInstanceMonitor` | Enable Fuxi scheduler heartbeat monitoring | Default: enabled | Use with `fuxi_InstanceMonitorTimeout` to prevent false "dead" termination |
| `fuxi_InstanceMonitorTimeout` | Instance monitor timeout (seconds) | Default: system | Requires allowlist from technical support |
| `odps.job.instance.retry.times` | Maximum retry count for failed workers | Default: 3; Max: 100 | Requires allowlist for values above default |
| `odps.dag2.compound.config` | Worker reuse strategy. Set `fuxi.worker.reuse.policy:NO_REUSE` to disable | Default: enabled | Disable when UDF has memory leaks or state pollution |

### Execution Efficiency

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.sql.executionengine.batch.rowcount` | Batch size (rows) for data processing | Default: 1024 | Balance between memory and performance. Reduce for large rows causing OOM |
| `odps.sql.runtime.flag.executionengine_EnableVectorizedExpr` | Enable vectorized expression engine | Default: disabled | Enable for compute-intensive operations with `rand()` or arithmetic |
| `odps.optimizer.enable.conditional.mapjoin` | Enable conditional map join | Default: system | Use with `cbo.rule.filter.black` |
| `odps.optimizer.cbo.rule.filter.black` | Disable specific optimization rules. Set to `"hj"` to disable HashJoin | Default: none | Expert option - use with caution |
| `odps.sql.split.cluster.parallel_explore` | Parallel CMF reading during split | Default: disabled | Enable when split phase takes too long |
| `odps.sql.jobmaster.memory` | JobMaster memory (MB) | Default: system | Increase for large-scale shuffle, e.g., 30000MB |

### UDF and Function Safety

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.sql.udf.timeout` | UDF batch execution timeout (seconds) | 1-3600; Default 1800 | 0 has no effect |
| `odps.function.timeout` | Function batch execution timeout (seconds) | 1-3600; Default 1800 | 0 has no effect |
| `odps.sql.runtime.flag.executionengine_PythonStdoutMaxsize` | Maximum stdout log size (MB) for Python UDF | Max: 100; Default: 20 | Requires allowlist from technical support |

### Resources and Environment

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.session.image` | Custom runtime image name | Must exist in project | Use for custom dependencies |
| `odps.task.major.version` | Lock job to specific MaxCompute version | Expert option | Do not configure without understanding impact |
| `odps.storage.orc.row.group.stride` | ORC file row group size | Expert option | Do not configure without understanding |
| `odps.storage.meta.file.version` | CMF metadata file version | Expert option | Do not configure without understanding |

### General Parameters

| Flag | Description | Range/Default | Recommendation |
|------|-------------|---------------|----------------|
| `odps.sql.allow.fullscan` | Allow full table scan on partitioned tables | Default: disabled | Enable cautiously - may cause high costs |
| `odps.sql.cfile2.field.maxsize` | Maximum field size (bytes) | Max: 268435456 (256MB); Default: 8388608 (8MB) | Increase for large text, HTML, or Base64 fields |
| `odps.sql.job.max.time.hours` | Maximum job runtime (hours) | Max: 72; Default: 24 | Increase for long-running jobs |
| `odps.sql.always.commit.result` | Enable partial commit | Default: disabled | Use with `EnableWorkerCommit` for ETL allowing partial success |
| `odps.sql.runtime.flag.executionengine_EnableWorkerCommit` | Enable worker-level commit | Default: disabled | Use with `always.commit.result` |

### CMF Generation (Fixed Configuration)

For writing to dynamic partition tables with proper CMF generation:

```python
options.sql.settings = {
    "odps.task.merge.enabled": "false",
    "odps.sql.reshuffle.dynamicpt": "false",
    "odps.sql.enable.dynaparts.stats.collection": "true",
    "odps.optimizer.dynamic.partition.is.first.nth.value.split.enable": "false",
    "odps.sql.stats.collection.aggressive": "true",
}
```

This ensures fast and correct CMF generation for dynamic partition tables, which is essential for downstream jobs using `odps.sql.split.dop`.

## MaxFrame Options Reference

### Session Configuration

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `options.session.quota_name` | Quota resource for job execution | str/None | None |
| `options.session.logview_hours` | LogView link retention (hours) | int | 24 |
| `options.session.max_alive_seconds` | Maximum session lifetime | int | 86400 (24h) |
| `options.session.max_idle_seconds` | Maximum idle time before session recycling | int | 3600 (1h) |
| `options.session.temp_table_lifecycle` | Temporary table lifecycle (days) | int | 1 |
| `options.session.auto_purge_temp_tables` | Auto-cleanup temp tables on session end | bool | False |

### SQL Configuration

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `options.sql.enable_mcqa` | Enable MaxCompute query acceleration | bool | True |
| `options.sql.generate_comments` | Add comments to generated SQL | bool | True |
| `options.sql.auto_use_common_image` | Auto-configure common image for dependencies | bool | True |

### Other Options

| Option | Description | Type | Default |
|--------|-------------|------|---------|
| `options.local_timezone` | Local timezone for date/time functions | str/None | None |
| `options.retry_times` | Retry count for retryable errors | int | 3 |
| `options.function.default_running_options` | Default resources for `@remote` functions | dict | {} |

### DPE Engine Settings

```python
# UDF external network access whitelist
options.dpe.settings = {
    "substep.public_network_whitelist": ["xxxxxx"]
}

# UDF internal network access whitelist
options.dpe.settings = {
    "substep.internal_network_whitelist": ["xxxxx"]
}
```

## Important Notes

1. **Allowlist Requirements**: Many special flags require allowlist approval from MaxCompute technical support before use.

2. **Custom Images**: Some flags depend on custom runtime images being properly configured.

3. **CMF Dependencies**: Split-related flags like `odps.sql.split.dop` require proper CMF statistics.

4. **Expert Options**: Flags marked as "expert options" should only be configured with full understanding of their impact on execution plans.

5. **Technical Support**: Always confirm with MaxCompute technical support before configuring advanced options.
