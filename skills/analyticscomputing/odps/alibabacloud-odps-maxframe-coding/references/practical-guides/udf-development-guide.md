# UDF Development Guide

This guide covers best practices and patterns for developing User-Defined Functions (UDFs) in MaxFrame.

## Resource Reuse in UDFs

In some UDF scenarios, you may need to create or destroy resources multiple times (e.g., initializing database connections, loading models). You can leverage Python's function parameter default value initialization behavior to achieve resource reuse.

### Pattern: Resource Initialization

The default value of a function parameter is initialized only once. You can use this to cache resources:

```python
def predict(s, _ctx={}):
    from ultralytics import YOLO
    # _ctx's initial value is an empty dict, initialized only once during Python execution.
    # Check if the model exists in _ctx; if not, load it and store in the dict.
    if not _ctx.get("model", None):
        model = YOLO(os.path.join("./", "yolo11n.pt"))
        _ctx["model"] = model
    model = _ctx["model"]

    # Subsequent model operations
    ...
```

### Pattern: Resource Cleanup with Classes

For resources that need cleanup (like database connections), use a class with `__del__`:

```python
class MyConnector:
    def __init__(self):
        # Create database connection in __init__
        self.conn = create_connection()

    def __del__(self):
        # Close connection in __del__
        try:
            self.conn.close()
        except:
            pass


def process(s, connector=MyConnector()):
    # Use the connector's database connection directly
    connector.conn.execute("xxxxx")
```

**Note:** The actual number of initializations depends on the number of Workers running the UDF. Each Worker executes the UDF in a separate Python environment. For example, if a UDF call needs to process 100,000 rows and is distributed across 10 UDF Workers, each processing 10,000 rows, initialization will occur 10 times total—one per Worker.

## Specifying Output Types

When using methods like `apply` with custom functions, MaxFrame attempts to infer the return type of the UDF. However, in some cases, you need to explicitly specify `dtypes`:

- The UDF cannot execute properly in the current environment (depends on custom images, third-party dependencies, or incorrect parameters)
- The actual return type doesn't match the specified `output_type`

### Examples

Return a DataFrame with one int column:
```python
df.apply(..., dtypes=pd.Series([np.int_]), output_type="dataframe")
```

Return a DataFrame with columns A and B:
```python
df.apply(..., dtypes={"A": np.int_, "B": np.str_}, output_type="dataframe")
```

Return a bool Series named "flag":
```python
df.apply(..., dtype="bool", name="flag", output_type="series")
```

## Using Third-Party Packages

### Using with_resources

```python
from maxframe.udf import with_resources


@with_resources("resource_name")
def process(row):
    ...
```

### Using PythonPack

For installing dependencies dynamically, you can cache PythonPack results for stability:

```python
from maxframe import options

# Cache PythonPack results for production use
options.pythonpack.task.settings = {"odps.pythonpack.production": "true"}
```

To ignore the cache and rebuild, add `force_rebuild=True` in `@with_python_requirements`.

Alternatively, you can:
- Use PyODPS-Pack to package dependencies offline and upload as MaxCompute Resource
- Reference resources in your job using `@with_resources`

## Network Access in UDFs

By default, network access is disabled in MaxCompute UDF containers. If your UDF needs network access:

```python
def request_external(row):
    import requests
    url = "https://example.com/api"
    response = requests.get(url)
    return response.text
```

Without network access enabled, this will fail with:
```
ConnectionRefusedError: [Errno 111] Connection refused
```

**Solution:** Enable network access through the network开通 process. Contact your administrator for network configuration.

## UDF Timeout Handling

### Error: kInstanceMonitorTimeout / CRASH_EXIT

This typically means the UDF execution timed out. In MaxCompute offline computing, UDFs are monitored by batch rows—if a UDF doesn't complete processing N rows within M time, it times out.

**Solution:** Adjust batch size and timeout:

```python
from maxframe import options

options.sql.settings = {
    # Batch size, default 1024, minimum 1
    "odps.sql.executionengine.batch.rowcount": "1",
    # Batch timeout in seconds, default 1800, maximum 3600
    "odps.function.timeout": "3600",
}
```

## UDF Memory Configuration

### Error: OOM in UDF

If your UDF runs out of memory, configure more memory:

```python
from maxframe import with_running_options


@with_running_options(memory="8GB")
def udf_func(row):
    return row
```

For AI Functions, set memory in the function call:
```python
result = ai_function(..., running_options={"memory": "8GB"})
```

## Debugging UDF Errors

### Error: ODPS-0123055 User script exception

This is the most common error type in MaxFrame, occurring during UDF execution (apply, apply_chunk, flatmap, map, transform operators).

**Common causes:**

1. **Code logic errors** - Check the function logic
2. **Unhandled exceptions** - Review try-except blocks
3. **Network access without permission** - Enable network access
4. **Type mismatch** - Ensure declared dtypes match actual return types
5. **Missing dependencies** - Ensure all dependencies are available

**Debugging approach:**

1. Check the stderr of the failed instance for the full stack trace
2. Identify the function and line number from the trace
3. Test locally by constructing test data:

```python
def udf_func(row):
    import json
    text = row["json_text"]
    data = json.loads(text)
    return data

# Test locally with constructed input
udf_func(pd.Series(['{"hello": "maxframe"}'], index=["json_text"]))
```

### Error: ModuleNotFoundError during deserialization

If you see errors like `No module named 'xxhash'` during unpickling, it means the UDF references a dependency that's not available in the runtime environment.

**Solution:** Install the dependency via PythonPack or include it as a resource.

### Error: Type mismatch

```python
def type_failure(row):
    text = row["A"]
    # Returns a float
    return text

# Declared as str but returns float
df.apply(type_failure, axis=1, dtypes={"A": np.str_}, output_type="dataframe").execute()
```

Error message:
```
TypeError: return value expected <class 'unicode'> but <class 'float'> found
```

**Solution:** Ensure declared dtypes match actual return types.
