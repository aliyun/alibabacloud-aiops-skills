# MaxFrame Local Debug Mode Guide

This guide provides comprehensive instructions for using MaxFrame's local debug mode, which enables offline UDF development with full IDE debugging support.

## Overview

MaxFrame Local Debug Mode is designed for data development engineers to debug UDF (User-Defined Functions) locally without connecting to remote MaxCompute services. It provides a seamless development experience with IDE breakpoint support for functions like `apply()` and `apply_chunk()`.

## Core Value

| Feature | Traditional Approach | Local Debug Mode |
|---------|---------------------|------------------|
| Breakpoint Debugging | ❌ Not supported | ✅ Full IDE support |
| Remote Dependency | ❌ Requires cluster connection | ✅ Completely offline |
| Debug Cycle | ❌ Submit to remote each time | ✅ Local immediate execution |
| Code Changes | ❌ Multiple code versions | ✅ Same code for dev/prod |

### Key Benefits

1. **Zero-Configuration Startup**: Simply use `debug=True` or `debug="local"` - no additional tools or services required
2. **Completely Offline**: No dependency on network or remote cluster resources
3. **Native IDE Support**: Breakpoints, variable inspection, step-by-step execution - all debugging capabilities preserved
4. **Flexible Data Sources**: Support for in-memory data, local files, or MaxCompute tables
5. **Seamless Production Switch**: Remove `debug=True` parameter and code runs directly in production

## When to Use Local Debug Mode

Use local debug mode when:
- Developing UDF functions (`apply`, `apply_chunk`)
- Need IDE breakpoints and step-by-step debugging
- Want to debug offline without network access
- Working on complex logic that requires iterative testing
- Need to verify data transformation logic quickly

**Use remote debug mode instead when:**
- Testing with production-scale data on MaxCompute
- Need to verify execution on actual cluster
- Investigating runtime issues that require logview URLs
- Debugging distributed execution problems

## Quick Start

### Prerequisites

```bash
pip install --upgrade maxframe  # Requires MaxFrame SDK 2.5.0 or later
```

### Basic Example

```python
from odps import ODPS
from maxframe import new_session
import maxframe.dataframe as md
import pandas as pd

# Initialize ODPS object
# Note: In local debug mode, ODPS object is only used for schema validation
# Actual credentials are not used for execution
o = ODPS(
    access_id=os.getenv('ODPS_ACCESS_ID', 'dummy_access_id'),
    secret_access_key=os.getenv('ODPS_ACCESS_KEY', 'dummy_secret_key'),
    project=os.getenv('ODPS_PROJECT', 'dummy_project'),
    endpoint=os.getenv('ODPS_ENDPOINT', 'dummy_endpoint'),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

# Enable local debug mode
session = new_session(o, debug=True)

# Prepare sample data
df = md.DataFrame(pd.DataFrame({
    "sales": [5000, 8000, 12000, 3000],
    "region": ["A", "B", "C", "D"]
}))

def calculate_commission(row):
    sales = row['sales']
    if sales > 10000:  # Set breakpoint here
        rate = 0.15
        print(rate)
    elif sales > 5000:  # Set breakpoint here
        rate = 0.10
        print(rate)
    else:
        rate = 0.05
    return sales * rate

# Execute and get results
result = df.apply(calculate_commission, axis=1).execute().fetch()
print(result)
```

## Key Features

### 1. Zero-Configuration Startup

Simply add `debug=True` or `debug="local"` when creating a session:

```python
# Local debug mode
session = new_session(o, debug=True)
# or
session = new_session(o, debug="local")

# Production mode (just remove debug parameter)
session = new_session(o)
```

### 2. IDE-Friendly Debugging

- **Supported IDEs**: PyCharm, VSCode, and other mainstream IDEs, as well as DataWorks Notebook
- **Breakpoints**: Set breakpoints anywhere in your UDF functions
- **Step-by-Step Execution**: Use F5/F6/F7/F8 to navigate through code
- **Variable Inspection**: View and modify variables during debugging
- **Debugging Experience**: Identical to local Python development

### 3. Multiple Data Sources

| Data Source Type | Access Method | Use Case |
|-----------------|---------------|----------|
| In-Memory Data | `md.DataFrame(pd.DataFrame())` | Quick logic validation |
| MaxCompute Table | `md.read_odps_table()` | Real data testing |
| Local Files | `pd.read_csv()` and other native Pandas interfaces | Offline development |

**Example with different data sources:**

```python
# 1. In-memory data (fastest for testing)
import pandas as pd
df = md.DataFrame(pd.DataFrame({
    "col1": [1, 2, 3],
    "col2": ["a", "b", "c"]
}))

# 2. MaxCompute table (real data)
df = md.read_odps_table("your_table_name")

# 3. Local file (offline development)
local_df = pd.read_csv("local_data.csv")
df = md.read_pandas(local_df)
```

### 4. Code Compatibility

Debugging code is identical to production code. Simply remove the `debug` parameter when deploying:

```python
# Development environment
session = new_session(o, debug=True)
# ... your code ...

# Production environment
session = new_session(o)
# ... same code ...
```

## Application Scenarios

| Scenario | Description |
|----------|-------------|
| UDF Logic Development | Real-time debugging and verification when writing complex business logic |
| Data Transformation Testing | Validate data cleaning and transformation rules |
| Problem Investigation | Identify root causes of UDF execution exceptions |
| Offline Development | Continue development work in environments without network access |

## Important Considerations

### 1. Performance Differences

Local debug mode is designed for development and verification. Performance characteristics differ from production environment:
- Execution happens locally, not distributed
- Performance is not representative of production cluster performance
- Best suited for small-scale sample data

### 2. Data Volume Limitations

For optimal debugging experience:
- Use small-scale sample data (recommended: 100-1000 rows)
- Large datasets may slow down local execution
- Focus on logic correctness rather than performance

### 3. Dependency Consistency

Ensure local Python environment matches production:
- Same Python version
- Same package versions (maxframe, pandas, numpy, etc.)
- Use `pip freeze > requirements.txt` to capture dependencies

### 4. Sensitive Data Handling

When debugging with MaxCompute tables:
- Be aware of data permissions and access controls
- Consider data masking for sensitive information
- Use sample/partitioned data to limit exposure
- Never commit sensitive credentials to version control

## Common Debugging Patterns

### Pattern 1: Breakpoint in Apply Function

```python
def process_row(row):
    # Set breakpoint on this line
    value = row['column_name']

    if value > threshold:
        # Set breakpoint here to inspect condition
        result = transform(value)
    else:
        result = default_value

    return result

df = md.DataFrame(sample_data)
result = df.apply(process_row, axis=1).execute().fetch()
```

### Pattern 2: Debugging Apply_Chunk for Batch Processing

```python
def process_batch(chunk):
    # Set breakpoint here to inspect entire chunk
    print(f"Processing batch with {len(chunk)} rows")

    # Debug data types
    print(f"Chunk dtypes:\n{chunk.dtypes}")

    # Debug transformations
    chunk['new_col'] = chunk['col1'] * 2

    # Set breakpoint here to verify results
    return chunk

result = df.mf.apply_chunk(
    process_batch,
    batch_rows=100,
    output_type='dataframe'
).execute().fetch()
```

### Pattern 3: Debugging with Print Statements

```python
def debug_function(row):
    print(f"Input row: {row.to_dict()}")

    # Step 1
    intermediate = row['col1'] + row['col2']
    print(f"After step 1: {intermediate}")

    # Step 2
    result = intermediate * 2
    print(f"Final result: {result}")

    return result

# Execute with debug output
result = df.apply(debug_function, axis=1).execute().fetch()
```

## Transitioning to Production

### Steps to Deploy

1. **Test Locally**: Develop and debug with local debug mode
2. **Verify Logic**: Ensure all transformations work correctly
3. **Remove Debug Parameter**: Change `new_session(o, debug=True)` to `new_session(o)`
4. **Test on Cluster**: Run on MaxCompute with small dataset
5. **Production Deploy**: Deploy to production environment

### Code Checklist

Before deploying to production:
- [ ] Remove `debug=True` parameter from session creation
- [ ] Verify all data source paths are correct for production
- [ ] Test with production-scale data on MaxCompute
- [ ] Remove or reduce print statements used for debugging
- [ ] Add proper error handling and logging
- [ ] Verify resource quotas and permissions

## Troubleshooting

### Issue: IDE Breakpoints Not Triggering

**Possible Causes:**
- Session created without `debug=True`
- Using incompatible IDE or debugger
- Code not actually executing through apply/apply_chunk

**Solutions:**
- Verify `debug=True` in `new_session()`
- Ensure you're using a supported IDE (PyCharm, VSCode)
- Check that `.execute()` is called to trigger execution

### Issue: Local Execution Too Slow

**Possible Causes:**
- Dataset too large for local debugging
- Complex operations not optimized for local execution

**Solutions:**
- Reduce sample data size (use `df.head(100)` or sample)
- Simplify operations for debugging purposes
- Focus on specific problematic code sections

### Issue: Results Differ from Production

**Possible Causes:**
- Data differences between sample and production data
- Environmental differences (Python version, package versions)
- Distributed vs. local execution semantics

**Solutions:**
- Verify data consistency between environments
- Check Python and package versions match
- Test on MaxCompute with `debug=False` to verify

## Summary

Local debug mode provides a powerful development experience for MaxFrame UDF development:
- Zero-configuration startup with `debug=True`
- Full IDE debugging support with breakpoints
- Flexible data source options
- Seamless transition to production
- Perfect for iterative UDF development

Use local debug mode during development for rapid iteration, then switch to remote debug mode for cluster-based testing and validation.

## Resources

- **MaxFrame Context Guide**: `./maxframe-context.md` - Comprehensive MaxFrame features and workflows
- **Interactive Coding Guide**: `./remote-debug-guide.md` - Remote debug mode with logview support
- **Key Modules Reference**: `./key-modules.md` - DataFrame, Tensor, and ML operations