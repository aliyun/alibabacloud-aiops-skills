# Error Troubleshooting Guide

This guide covers common error codes and their solutions in MaxFrame.

## Data Type Errors

### ODPS-0130071: invalid type INT for function UDF definition

**Error:** `invalid type INT for function UDF definition, you need to set odps.sql.type.system.odps2=true`

**Cause:** Using MaxCompute 2.0 data types without enabling the 2.0 data type version.

**Solution:**
```python
from maxframe import config

# Add before new_session
config.options.sql.settings = {
    "odps.sql.type.system.odps2": "true"
}
```

### ODPS-0130071: column values_list has incompatible type ARRAY/MAP/STRUCT

**Cause:** The data being processed contains arrays, dictionaries, or structs.

**Possible reasons:**
- Type declaration issue - the target column is not expected to be an array/dict/struct
- MaxFrame type system bug

**Solution:**
1. Upgrade MaxFrame client: `pip install -U maxframe`
2. Contact MaxFrame team if issue persists

## Dependency Errors

### UDF: No module named 'cloudpickle'

**Cause:** Missing cloudpickle package dependency.

**Solution:**
```python
from maxframe import config

# Add before new_session
config.options.sql.settings = {
    "odps.session.image": "common",
}
```

### TypeError: Cannot accept arguments append_partitions

**Cause:** PyODPS version compatibility issue.

**Solution:** Upgrade PyODPS to version 0.12.0 or later.

## Job Execution Errors

### ODPS-0010000: Fuxi job failed - Job failed for unknown reason

**Cause:** Dependency installation failed when using `@with_python_requirements`.

**Solution:**
1. Retry the job (may be temporary network issue)
2. For periodic jobs, cache PythonPack results:
```python
from maxframe import options

options.pythonpack.task.settings = {"odps.pythonpack.production": "true"}
```
3. Use offline packaging with PyODPS-Pack and upload as MaxCompute Resource

### ODPS-0123144: Fuxi job failed - kInstanceMonitorTimeout CRASH_EXIT

**Cause:** UDF execution timeout.

**Solution:** Adjust batch size and timeout:
```python
from maxframe import options

options.sql.settings = {
    "odps.sql.executionengine.batch.rowcount": "1",
    "odps.function.timeout": "3600",
}
```

### ODPS-0123144: Fuxi job failed - Job exceed live limit

**Cause:** MaxCompute job exceeded maximum timeout (default 24 hours).

**Solution:**
```python
from maxframe import options

# Set MaxFrame Session maximum lifetime
options.session.max_alive_seconds = 72 * 60 * 60
# Set MaxFrame Session maximum idle timeout
options.session.max_idle_seconds = 72 * 60 * 60

options.sql.settings = {
    # Set SQL job maximum runtime, default 24h, maximum 72h
    "odps.sql.job.max.time.hours": 72,
}
```

### ODPS-0130071: physical plan generation failed - no CMF

**Cause:** Missing index column specification.

**Solution:** Add `index_col` parameter:
```python
df2 = md.read_odps_table("tablename", index_col="column").to_pandas()
df2 = df2.reset_index(inplace=True)
```

### ODPS-0130071: unable to retrieve row count of file

**Cause:** Using flags like `odps.sql.split.dop` to specify split count, but source table lacks meta file.

**Solution:** Use `odps.stage.mapper.split.size` instead (unit: MB, default 256, minimum 1).

To ensure meta file generation when writing tables:
```python
from maxframe import options

options.sql.settings = {
    "odps.task.merge.enabled": "false",
    "odps.sql.reshuffle.dynamicpt": "false",
    "odps.sql.enable.dynaparts.stats.collection": "true",
    "odps.optimizer.dynamic.partition.is.first.nth.value.split.enable": "false",
    "odps.sql.stats.collection.aggressive": "true",
}
```

### ODPS-0130071: task instance count exceeds limit 99999

**Cause:** Source table is very large, and splitting by 256MB produces more than 99,999 chunks.

**Solution:**
1. Use `odps.stage.mapper.split.size` with a larger value
2. Use `odps.sql.split.dop` to specify expected split count

```python
from maxframe import options

options.sql.settings = {
    "odps.stage.mapper.split.size": "512",  # MB
    # or
    "odps.sql.split.dop": "10000",
}
```

## Memory and Resource Errors

### ODPS-0010000: System internal error - process exited with code 0

**Cause:** UDF/AI Function OOM.

**Solution:**
1. Contact MaxFrame team to confirm actual memory usage
2. Increase memory allocation:
```python
from maxframe import with_running_options


@with_running_options(memory="8GB")
def udf_func(row):
    return row
```

### ODPS-0010000: process killed by signal 7

**Cause:** UDF sent an abnormal signal.

**Solution:**
1. Check if UDF uses signal to send cancel/timeout
2. Contact MaxCompute team

### ODPS-0010000: StdException:vector::_M_range_insert

**Cause:** UDF cannot allocate enough memory.

**Solution:**
1. Check UDF for memory issues
2. Check native dependencies for memory problems
3. Increase UDF memory allocation

### ODPS-0020011: Total resource size must be <= 2048MB

**Cause:** UDF depends on resources exceeding the 2048MB limit.

**Solution:** Use external volume with OSS for faster downloads and higher limits.

## Session and Table Errors

### NoTaskServerResponseError

**Cause:** MaxFrame Session expired (idle for more than 1 hour in Jupyter Notebook).

**Solution:**
1. Recreate the Session (previous computation state will be lost)
2. For expected long intervals, set:
```python
from maxframe import options

options.session.max_idle_seconds = 60 * 60 * 24  # 24 hours
```

### ODPS-0110061: Table not found

**Cause:** MaxFrame job running over 24 hours; temporary tables expired.

**Solution:** Increase temporary table lifecycle:
```python
from maxframe import options

options.sql.settings = {
    "session.temp_table_lifecycle": 3,  # days
}
```

### ODPS-0010000: Database not found

**Cause:** Cannot find specified schema/project/table.

**Solution:**
1. Check SQL for correct project.schema.table names
2. Contact MaxCompute team

## Data Errors

### ODPS-0020041: StringOutOfMaxLength

**Cause:** String length exceeds maximum allowed (268,435,456).

**Solution:**
1. Truncate or filter long strings using `LENGTH` in `read_odps_query`
2. Compress data (e.g., gzip):
```python
def compress_string(input_string):
    encoded_string = input_string.encode('utf-8')
    compressed_bytes = gzip.compress(encoded_string)
    return compressed_bytes
```

### IntCastingNaNError: Cannot convert non-finite values to integer

**Cause:** Printing BIGINT/INT columns containing NULL or INF values in Jupyter.

**Solution:**
1. Use `fillna` before printing
2. Use `astype` to convert to FLOAT before printing
3. Avoid printing problematic columns

## Shuffle Errors

### Shuffle output too large

**Solution:**
```python
from maxframe import options

options.sql.settings = {
    "odps.sql.sys.flag.fuxi_JobMaxInternalFolderSize": "10240",  # MB
}
```

### ODPS-0010000: SQL job failed after failover for too many times

**Cause:** Job Master OOM due to large shuffle data.

**Solution:**
1. Reduce mapper and reducer/joiner counts (keep under 10,000)
2. Contact MaxCompute team

## External Table Errors

### ODPS-0123131: User defined function exception - Fatal Error Happened

**Cause:** Internal error in external table read/write.

**Solution:** Contact MaxCompute team.
