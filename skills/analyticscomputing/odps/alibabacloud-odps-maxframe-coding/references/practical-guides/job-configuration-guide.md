# Job Configuration Guide

This guide covers MaxFrame job configuration, tuning, and session management.

## SQL Settings Configuration

MaxFrame allows configuring SQL execution settings using `config.options.sql.settings`. These settings correspond to MaxCompute SQL flags.

### Basic Configuration

```python
from maxframe import config

config.options.sql.settings = {
    "odps.sql.type.system.odps2": "true",
}
```

### Common Settings

#### Stage Parallelism

```python
from maxframe import config

config.options.sql.settings = {
    # Mapper split size in MB (default 256, minimum 1)
    "odps.stage.mapper.split.size": "8",
    # Number of joiner instances
    "odps.stage.joiner.num": "20",
    # Number of reducer instances
    "odps.stage.reducer.num": "100",
}
```

#### Batch Processing

```python
from maxframe import options

options.sql.settings = {
    # Batch size for UDF processing (default 1024, minimum 1)
    "odps.sql.executionengine.batch.rowcount": "1",
    # Batch timeout in seconds (default 1800, maximum 3600)
    "odps.function.timeout": "3600",
}
```

## Session Management

### Session Lifetime

MaxFrame sessions have configurable lifetime and idle timeout settings.

```python
from maxframe import options

# Maximum session lifetime (default 24 hours)
options.session.max_alive_seconds = 72 * 60 * 60  # 72 hours

# Maximum idle timeout (default 1 hour)
options.session.max_idle_seconds = 72 * 60 * 60  # 72 hours
```

### SQL Job Timeout

```python
from maxframe import options

options.sql.settings = {
    # SQL job maximum runtime in hours (default 24, maximum 72)
    "odps.sql.job.max.time.hours": 72,
}
```

### Temporary Table Lifecycle

For long-running jobs that span multiple days, increase temporary table lifecycle:

```python
from maxframe import options

options.sql.settings = {
    # Temporary table lifecycle in days (default 1)
    "session.temp_table_lifecycle": 3,
}
```

## PythonPack Configuration

### Production Caching

For periodic jobs, cache PythonPack results to improve stability:

```python
from maxframe import options

# Cache PythonPack results for production use
options.pythonpack.task.settings = {"odps.pythonpack.production": "true"}
```

### Force Rebuild

To ignore cache and rebuild dependencies:

```python
from maxframe import with_python_requirements


@with_python_requirements("package_name", force_rebuild=True)
def process(data):
    ...
```

## Resource Configuration

### UDF Memory Settings

Configure memory for individual UDFs:

```python
from maxframe import with_running_options


@with_running_options(memory="8GB")
def memory_intensive_udf(row):
    # Process large data
    return result
```

### AI Function Resource Settings

For AI Functions, set resources in the function call:

```python
result = ai_function(
    ...,
    running_options={"memory": "8GB"}
)
```

## Split Configuration

### Split by Size

Use `odps.stage.mapper.split.size` for size-based splitting:

```python
from maxframe import options

options.sql.settings = {
    # Split size in MB (default 256, minimum 1)
    "odps.stage.mapper.split.size": "512",
}
```

### Split by Count

Use `odps.sql.split.dop` to specify target split count:

```python
from maxframe import options

options.sql.settings = {
    # Target number of splits
    "odps.sql.split.dop": "1000",
}
```

**Note:** The actual split count may differ from the target due to various constraints. Setting a value near the maximum (99,999) may still cause errors.

## Shuffle Configuration

### Shuffle Size

Adjust shuffle output size for large data operations:

```python
from maxframe import options

options.sql.settings = {
    # Shuffle folder size in MB
    "odps.sql.sys.flag.fuxi_JobMaxInternalFolderSize": "10240",
}
```

## Instance Count Limits

MaxCompute SQL jobs have a maximum of 99,999 instances per task. To avoid exceeding this limit:

1. Increase split size to reduce mapper instances
2. Reduce reducer/joiner counts
3. Keep total instances under 10,000 for best performance

```python
from maxframe import options

options.sql.settings = {
    # Larger split size reduces mapper instances
    "odps.stage.mapper.split.size": "1024",  # 1GB
    # Limit reducer instances
    "odps.stage.reducer.num": "100",
    "odps.stage.joiner.num": "100",
}
```

## Metadata Statistics Collection

To ensure proper split functionality and meta file generation:

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

## Image Configuration

### Using Base Image

Reference MaxCompute base image for common dependencies:

```python
from maxframe import config

config.options.sql.settings = {
    "odps.session.image": "common",
}
```

### Custom Runtime Image

For custom dependencies and environments, use a custom DPE runtime image:

```python
from maxframe import config

config.options.sql.settings = {
    "odps.session.image": "<your_custom_image>",
}
```

## Configuration Best Practices

### For Interactive Development (Jupyter)

```python
from maxframe import config, options, new_session

# Enable 2.0 data types
config.options.sql.settings = {
    "odps.sql.type.system.odps2": "true",
}

# Longer idle timeout for interactive sessions
options.session.max_idle_seconds = 60 * 60 * 4  # 4 hours

session = new_session()
```

### For Production Jobs

```python
from maxframe import config, options, new_session

# Enable 2.0 data types
config.options.sql.settings = {
    "odps.sql.type.system.odps2": "true",
    "odps.session.image": "common",
}

# Longer session lifetime
options.session.max_alive_seconds = 72 * 60 * 60  # 72 hours

# Cache PythonPack results
options.pythonpack.task.settings = {"odps.pythonpack.production": "true"}

# Increase temp table lifecycle for long jobs
options.sql.settings["session.temp_table_lifecycle"] = 3

session = new_session()
```

### For Large Data Processing

```python
from maxframe import config, options, new_session

# Optimize for large data
config.options.sql.settings = {
    # Larger split size for fewer mappers
    "odps.stage.mapper.split.size": "512",
    # More parallelism
    "odps.stage.reducer.num": "200",
    # Longer timeout
    "odps.function.timeout": "3600",
    # Larger shuffle space
    "odps.sql.sys.flag.fuxi_JobMaxInternalFolderSize": "20480",
}

session = new_session()
```
