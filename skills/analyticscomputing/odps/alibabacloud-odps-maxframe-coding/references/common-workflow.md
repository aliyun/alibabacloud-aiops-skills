# Common Workflow Complete Guide

Detailed guide for the complete MaxFrame development workflow with comprehensive examples.

## Session Setup Patterns

### Pattern 1: Auto-detect (DataWorks/MaxCompute Notebook)

```python
import os
import maxframe.dataframe as md
from maxframe.session import new_session
from odps import ODPS

# Auto-detect from environment (preferred in DataWorks/MaxCompute Notebook)
session = new_session()
```

### Pattern 2: Explicit ODPS Connection

```python
import os
import dotenv
import maxframe.dataframe as md
from maxframe.session import new_session
from odps import ODPS

dotenv.load_dotenv()

o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)
session = new_session(o)
```

### Pattern 3: Production-ready Session

```python
import logging
import maxframe.dataframe as md
from maxframe.session import new_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session = new_session()
try:
    logger.info(f"Session created. Logview: {session.get_logview_address()}")
    # Your operations
    ...
finally:
    session.destroy()
    logger.info("Session destroyed")
```

## Reading Data Patterns

### Pattern 1: Basic Table Read

```python
# Read from MaxCompute table
df = md.read_odps_table("table_name")

# Read with index column
df = md.read_odps_table("table_name", index_col="id")

# With column selection
df = md.read_odps_table("table_name", columns=['id', 'value', 'timestamp'])

# With partition filter
df = md.read_odps_table("table_name", partition='ds=2024-01-01')
```

### Pattern 2: SQL Query Read

```python
# Read from SQL query with filters
df = md.read_odps_query(
    "SELECT * FROM table WHERE date >= '2024-01-01' AND status = 'active'"
)

# Complex SQL with joins
df = md.read_odps_query(
    "SELECT a.*, b.value FROM table_a a JOIN table_b b ON a.id = b.id"
)
```

### Pattern 3: Sample Data Construction

When user doesn't provide input table name, construct pandas DataFrame:

```python
import pandas as pd
import numpy as np

# Time series analysis example
example_pd_df = pd.DataFrame({
    'timestamp': pd.date_range('2026-01-01', periods=1000, freq='H'),
    'metric_name': np.random.choice(['cpu', 'memory', 'disk'], 1000),
    'value': np.random.randn(1000) * 10 + 50,
    'host_id': np.random.choice(['host1', 'host2', 'host3'], 1000)
})

# Load into MaxFrame
df = md.read_pandas(example_pd_df)
```

**Key guidelines for sample data:**
- Match data types and structure to job requirements
- Use realistic value ranges for the domain
- Include 100-1000 rows to demonstrate logic
- Use descriptive column names matching operations

## Operator Selection Workflow

### Step 1: Identify Required Operations

Break down the task into specific operations needed:
- Filtering
- Grouping
- Aggregation
- Transformation
- Merging
- Sorting

### Step 2: Find MaxFrame Operators

Use operator-selector agent or script:

```bash
# Search for operators by task description
python scripts/lookup_operator.py search "time series resampling"

# Check if a specific operator exists
python scripts/lookup_operator.py info apply_chunk

# Get detailed operator information
python scripts/lookup_operator.py info groupby
```

### Step 3: Present Options to User

```
For your data aggregation task, I've identified these options:

1. `groupby().agg()` - Standard pandas-compatible approach
   - Pros: Familiar API, good for standard aggregations
   - Cons: May be slow for large datasets with custom logic

2. `mf.apply_chunk()` - For custom aggregation with large datasets
   - Pros: Efficient batch processing, custom logic support
   - Cons: More complex, requires batch size tuning

Which approach do you prefer, or would you like me to explore other options?
```

### Step 4: Get User Confirmation

**MANDATORY:** Do not proceed without user confirmation.

## Processing Patterns

### Pattern 1: Standard pandas Operations

```python
# Filter
filtered = df[df['column'] > 10]

# GroupBy and aggregate
result = df.groupby('category').agg({'value': 'sum'})

# Add columns
df['new_col'] = df['col1'] + df['col2']

# Sort
df_sorted = df.sort_values('column')

# Merge
df_merged = df1.merge(df2, on='key')

# Multiple aggregations
result = df.groupby('category').agg({
    'value': ['sum', 'mean', 'count'],
    'price': 'max'
})
```

### Pattern 2: Batch Processing (Large Datasets)

```python
def process_batch(chunk):
    # Custom processing logic
    return chunk * 2

result = df.mf.apply_chunk(
    process_batch,
    batch_rows=1024,  # Tune batch size for performance
    output_type='dataframe'
)
```

### Pattern 3: UDF with Resource Allocation

```python
from maxframe.udf import with_running_options

@with_running_options(engine="dpe", cpu=2, memory=4)
def process_batch(batch):
    # CRITICAL: memory=4 means 4 GB, NOT 4 MB
    return batch * 2

result = df.mf.apply_chunk(process_batch)
```

## Writing Data Patterns

### Pattern 1: Write to MaxCompute Table

```python
# Write to MaxCompute table
md.to_odps_table(df, "output_table", overwrite=True).execute()
```

### Pattern 2: Write to DLF External Table

```python
from maxframe import options

# Enable DLF support
options.sql.settings = {
    "odps.maxframe.resolve_dlf_tables": "true"
}

md.to_odps_table(df, "dlf_table").execute()
```

### Pattern 3: Multiple Output Tables

```python
try:
    md.to_odps_table(df1, "output_table1").execute()
    md.to_odps_table(df2, "output_table2").execute()
finally:
    session.destroy()
```

## Execution and Cleanup Patterns

### Pattern 1: Basic Execution

```python
# Execute operations (required for lazy execution)
result.execute()

# Destroy session when done
session.destroy()
```

### Pattern 2: Safe Cleanup (Production)

```python
try:
    # Execute operations
    result.execute()
finally:
    # Destroy session (always runs, even on error)
    session.destroy()
```

### Pattern 3: Comprehensive Cleanup

```python
import logging

logger = logging.getLogger(__name__)

try:
    result.execute()
    logger.info("Execution successful")
except Exception as e:
    logger.error(f"Execution failed: {e}")
    raise
finally:
    try:
        session.destroy()
        logger.info("Session destroyed")
    except Exception as cleanup_error:
        logger.warning(f"Cleanup error: {cleanup_error}")
```

## Verification Pattern

Use `py_compile` to test generated job script:

```bash
python -m py_compile your_script.py
```

## Complete Example Pipeline

```python
import os
import logging
import dotenv
import maxframe.dataframe as md
from maxframe.session import new_session

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup session
session = new_session()
try:
    logger.info(f"Session created. Logview: {session.get_logview_address()}")

    # Read data
    df = md.read_odps_table("source_table", columns=['id', 'value', 'category'])

    # Process (after confirming operators with user)
    filtered = df[df['value'] > 100]
    result = filtered.groupby('category').agg({'value': 'sum'})

    # Write output
    md.to_odps_table(result, "output_table", overwrite=True).execute()

    logger.info("Job completed successfully")
    logger.info(f"Final Logview: {session.get_logview_address()}")

finally:
    session.destroy()
    logger.info("Session destroyed")
```