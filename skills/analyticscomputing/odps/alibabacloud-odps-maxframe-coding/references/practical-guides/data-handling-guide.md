# Data Handling Guide

This guide covers common data handling scenarios in MaxFrame, including JSON processing, data type handling, and schema management.

## JSON Data Processing

### Parsing JSON Strings

MaxFrame v1.0.0+ supports the `flatjson` method for extracting multiple JSON fields:

```python
# Extract multiple fields from JSON strings
df.mf.flatjson("json_column", ["field1", "field2", "field3"])
```

For more complex JSON parsing, use `apply` with custom functions:

```python
import json
import pandas as pd
import numpy as np


def parse_json(row):
    data = json.loads(row["json_text"])
    return pd.Series({
        "field1": data.get("field1"),
        "field2": data.get("field2"),
    })


result = df.apply(
    parse_json,
    axis=1,
    dtypes={"field1": np.str_, "field2": np.str_},
    output_type="dataframe"
)
```

### Handling Invalid JSON

When parsing JSON, invalid strings will cause errors:

```python
def simple_failure(row):
    import json
    text = row["json_text"]
    data = json.loads(text)  # Fails if text is not valid JSON
    return data
```

**Solution:** Add error handling:

```python
def safe_parse_json(row):
    import json
    try:
        data = json.loads(row["json_text"])
        return pd.Series({"result": data, "error": None})
    except json.JSONDecodeError as e:
        return pd.Series({"result": None, "error": str(e)})


result = df.apply(
    safe_parse_json,
    axis=1,
    dtypes={"result": np.object_, "error": np.str_},
    output_type="dataframe"
)
```

## Data Type Handling

### Type System Overview

MaxFrame uses MaxCompute's type system. Key types include:

| MaxCompute Type | NumPy Type | Python Type |
|----------------|------------|-------------|
| BIGINT | np.int64 | int |
| DOUBLE | np.float64 | float |
| STRING | np.str_ | str |
| BOOLEAN | np.bool_ | bool |
| DATETIME | np.datetime64 | datetime |
| ARRAY | - | list |
| MAP | - | dict |

### Enabling 2.0 Data Types

Some operations require MaxCompute 2.0 data types:

```python
from maxframe import config

config.options.sql.settings = {
    "odps.sql.type.system.odps2": "true"
}
```

### Handling NULL Values

In Pandas, BIGINT/INT columns cannot contain NULL (converted to FLOAT). To handle this:

```python
# Fill NULL before printing
df["int_column"] = df["int_column"].fillna(0)

# Or convert to float
df["int_column"] = df["int_column"].astype(float)
```

### Specifying Output Types

When UDFs return DataFrames or Series, specify output types:

```python
import numpy as np


def process(row):
    return pd.Series({
        "id": int(row["id"]),
        "name": str(row["name"]),
        "score": float(row["score"]),
    })


result = df.apply(
    process,
    axis=1,
    dtypes={"id": np.int64, "name": np.str_, "score": np.float64},
    output_type="dataframe"
)
```

### Complex Types (ARRAY/MAP/STRUCT)

For columns containing complex types:

```python
# Access array elements
df["first_element"] = df["array_column"].apply(
    lambda x: x[0] if x else None,
    dtype=np.str_
)

# Access map values
df["value"] = df["map_column"].apply(
    lambda x: x.get("key"),
    dtype=np.str_
)
```

## Schema Management

### Reading Tables with Index

When reading tables, specify an index column to avoid "no CMF" errors:

```python
import maxframe.dataframe as md

# Specify index column
df = md.read_odps_table("table_name", index_col="id")

# Later reset index if needed
df = df.reset_index()
```

### Writing Tables

Write results to MaxCompute tables:

```python
# Write to existing table
df.to_odps_table("project.schema.table_name")

# Write with partition
df.to_odps_table("project.schema.table_name", partition="dt=20250101")
```

## String Handling

### Maximum String Length

MaxCompute has a maximum string length of 268,435,456 characters. For longer strings:

**Option 1: Truncate or filter**
```python
from maxframe.dataframe import functions as F

# Filter rows with strings under limit
df = df[df["text_column"].str.len() < 268435456]

# Truncate strings
df["text_column"] = df["text_column"].str.slice(0, 1000000)
```

**Option 2: Compress data**
```python
import gzip


def compress_string(input_string):
    encoded_string = input_string.encode('utf-8')
    compressed_bytes = gzip.compress(encoded_string)
    return compressed_bytes


def decompress_string(compressed_bytes):
    return gzip.decompress(compressed_bytes).decode('utf-8')
```

## Data Transformation Patterns

### Row-wise Processing

Use `axis=1` for row-wise operations:

```python
def process_row(row):
    # Access columns by name
    value1 = row["col1"]
    value2 = row["col2"]
    result = value1 + value2
    return result


df["new_col"] = df.apply(process_row, axis=1, dtype=np.float64)
```

### Element-wise Processing

For simple element-wise operations, use vectorized operations:

```python
# Preferred: vectorized
df["sum"] = df["col1"] + df["col2"]

# Instead of: apply with simple function
df["sum"] = df.apply(lambda row: row["col1"] + row["col2"], axis=1)
```

### Chunk Processing

For memory-intensive operations, use `apply_chunk`:

```python
def process_chunk(chunk):
    # Process entire chunk at once
    result = chunk.groupby("key").agg({"value": "sum"})
    return result


result = df.apply_chunk(
    process_chunk,
    dtypes={"key": np.str_, "value": np.float64},
    output_type="dataframe"
)
```

## Data Validation

### Checking Data Types

```python
# Check column types
print(df.dtypes)

# Check for NULL values
null_counts = df.isnull().sum()

# Check unique values
unique_counts = df.nunique()
```

### Validating Before Processing

```python
def validate_row(row):
    # Check required fields
    if pd.isna(row["required_field"]):
        return pd.Series({"valid": False, "error": "missing required field"})

    # Check data format
    if not isinstance(row["numeric_field"], (int, float)):
        return pd.Series({"valid": False, "error": "invalid numeric field"})

    return pd.Series({"valid": True, "error": None})


validation = df.apply(
    validate_row,
    axis=1,
    dtypes={"valid": np.bool_, "error": np.str_},
    output_type="dataframe"
)

# Filter invalid rows
invalid_rows = df[~validation["valid"]]
```

## Common Patterns

### Conditional Transformation

```python
import numpy as np


def conditional_transform(row):
    if row["type"] == "A":
        return row["value"] * 2
    elif row["type"] == "B":
        return row["value"] * 3
    else:
        return row["value"]


df["transformed"] = df.apply(conditional_transform, axis=1, dtype=np.float64)
```

### Lookup and Join

```python
# Join with another DataFrame
result = df1.merge(df2, on="key", how="left")

# Or use map for simple lookups
lookup_dict = {"A": 1, "B": 2, "C": 3}
df["lookup_value"] = df["category"].map(lookup_dict)
```

### Aggregation

```python
# Group by and aggregate
result = df.groupby("group_column").agg({
    "numeric_col": ["sum", "mean", "count"],
    "string_col": "first"
})
```
