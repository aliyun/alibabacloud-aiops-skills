# MaxFrame Advanced Topics and Complementary Reference

This document contains advanced topics, configuration options, and detailed API compatibility information not covered in `key-modules.md`. For basic DataFrame, Tensor, and ML operations, see `key-modules.md`.

## Table of Contents

- [Configuration and Options](#configuration-and-options)
- [Remote Execution](#remote-execution)
- [User-Defined Functions (UDFs)](#user-defined-functions-udfs)
- [Best Practices](#best-practices)
- [Error Handling](#error-handling)
- [Complete Example](#complete-example)
- [API Compatibility](#api-compatibility)
- [Additional API Usage Examples](#additional-api-usage-examples)

---

## Configuration and Options

MaxFrame provides a configuration system for customizing behavior.

```python
from maxframe import options

# Execution mode
options.execution_mode = 'trigger'  # or 'eager'

# Progress display
options.show_progress = True  # or False, 'auto'

# Chunk size
options.chunk_size = 1024

# Session configuration
options.session.max_alive_seconds = 3600
options.session.max_idle_seconds = 600
options.session.quota_name = 'your_quota'

# DataFrame backend
options.dataframe.dtype_backend = 'numpy'  # or 'pyarrow'

# Retry configuration
options.retry_times = 4
options.retry_delay = 0.1
```

### Option Context

```python
from maxframe.config import option_context

# Temporary options
with option_context({'show_progress': True, 'chunk_size': 2048}):
    # Operations with custom options
    df.execute()
```

### Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `show_progress` | `'auto'` | Show progress bar during execution |
| `execution_mode` | `'trigger'` | Execution mode: 'trigger' or 'eager' |
| `chunk_size` | `None` | Size of data chunks |
| `session.max_alive_seconds` | `259200` | Maximum session lifetime (3 days) |
| `session.max_idle_seconds` | `3600` | Maximum idle time (1 hour) |
| `session.quota_name` | `None` | MaxCompute quota to use |
| `dataframe.dtype_backend` | `'numpy'` | Backend for dtypes: 'numpy' or 'pyarrow' |
| `retry_times` | `4` | Number of retry attempts |

---

## Remote Execution

Execute custom Python code remotely on MaxCompute.

```python
from maxframe import remote

# Define remote function
@remote.spawn
def my_function(x, y):
    return x + y

# Execute remotely
result = my_function(10, 20)
result.execute()
```

### Run Scripts Remotely

```python
from maxframe.remote import run_script

# Execute Python script on cluster
result = run_script(
    script_path='path/to/script.py',
    args=['arg1', 'arg2']
)
```

---

## User-Defined Functions (UDFs)

MaxFrame supports custom Python functions with dependency management.

```python
from maxframe.udf import with_python_requirements

# Function with dependencies
@with_python_requirements("numpy", "scipy")
def process_data(df):
    import numpy as np
    return np.sqrt(df['value'])

# Apply UDF
result = df['value'].apply(process_data)
```

For resource allocation (CPU, memory, GPU) in UDFs, see `key-modules.md` → UDF Resource Allocation.

---

## Best Practices

### Performance Optimization

1. **Use Lazy Execution**: Build computation graphs before execution
2. **Batch Operations**: Use `apply_chunk` for batch processing
3. **Appropriate Chunk Size**: Configure based on data size
4. **Minimize Data Movement**: Read and write to MaxCompute tables directly
5. **Use Built-in Functions**: Prefer MaxFrame functions over custom UDFs
6. **Partitioning**: Read only necessary partitions from tables

### Common Patterns

**ETL Pipeline:**

```python
# Read -> Transform -> Write
df = md.read_odps_table("source_table", partitions=["pt=20240101"])
transformed = df[df['status'] == 'active'].groupby('category').agg({'value': 'sum'})
transformed.to_odps_table("target_table", partition="pt=20240101").execute()
```

**Data Quality Check:**

```python
# Check for nulls
null_counts = df.isnull().sum()

# Check duplicates
duplicates = df.duplicated().sum()

# Value ranges
summary = df.describe()
```

**Incremental Processing:**

```python
# Process new data only
new_data = md.read_odps_table(
    "source_table",
    partitions=[f"dt={today}"]
)

processed = new_data.groupby('key').sum()
processed.to_odps_table(
    "result_table",
    partition=f"dt={today}"
).execute()
```

---

## Error Handling

### Common Issues

**Session Timeout:**

```python
# Increase session timeout
from maxframe import options
options.session.max_alive_seconds = 7200  # 2 hours
```

**Memory Issues:**

```python
# Reduce chunk size
options.chunk_size = 512
```

**Connection Issues:**

```python
# Increase retry attempts
options.retry_times = 10
options.retry_delay = 1.0
```

---

## Complete Example

### End-to-End Example

```python
import os
import maxframe.dataframe as md
from maxframe import new_session, options
from odps import ODPS

# Setup
o = ODPS(
    access_id=os.getenv('ODPS_ACCESS_ID'),
    secret_access_key=os.getenv('ODPS_ACCESS_KEY'),
    project='my_project',
    endpoint='http://service.odps.aliyun.com/api',
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)

# Configure options
options.show_progress = True
options.session.quota_name = 'my_quota'

# Create session
with new_session(o) as session:
    # Read data
    users = md.read_odps_table('users')
    orders = md.read_odps_table('orders', partitions=['dt=20240101'])

    # Transform
    # Filter active users
    active_users = users[users['status'] == 'active']

    # Join with orders
    user_orders = orders.merge(
        active_users[['user_id', 'name', 'email']],
        on='user_id'
    )

    # Aggregate
    daily_summary = user_orders.groupby('user_id').agg({
        'order_id': 'count',
        'amount': ['sum', 'mean']
    })
    # Flatten column names
    daily_summary.columns = ['order_count', 'total_amount', 'avg_amount']

    # Filter high-value users
    high_value = daily_summary[daily_summary['total_amount'] > 1000]

    # Write results
    high_value.to_odps_table(
        'high_value_users',
        partition='dt=20240101'
    ).execute()

    print("Processing complete!")
```

---

## API Compatibility

### Pandas API Support

MaxFrame aims for high compatibility with pandas APIs. Most common pandas operations are supported:

**Fully Supported:**
- DataFrame/Series creation and basic operations
- Indexing and selection (loc, iloc, boolean indexing)
- GroupBy operations and aggregations
- Merge, join, concat operations
- String and datetime accessors
- Missing data handling
- Sorting and ranking
- Mathematical operations (mean, median, std, var, min, max, sum)
- Array operations (rank, unique, duplicated, factorize)
- Eval and query expressions
- Rolling and expanding window operations
- Categorical operations

**Partially Supported:**
- Some advanced groupby operations (nth, interpolation not available)
- Complex multi-index operations
- Certain time series operations
- Eval/query with custom parser/engine parameters

**Not Supported:**
- Operations requiring full data in memory on client
- Some specialized statistical functions
- Direct matplotlib integration (use `.plot()` methods)
- Pandas internal APIs (pd.core.algorithms, pd.core.nanops)
- Numexpr/Numba configuration (MaxFrame uses its own engine)
- Parser/engine parameters for eval (only default 'maxframe' parser)

---

### MaxFrame-Specific Patterns and Workarounds

#### Index Creation Pattern

MaxFrame's `md.Index` wraps pandas Index objects rather than creating them directly. When you need specific Index types (RangeIndex, CategoricalIndex, DatetimeIndex, MultiIndex), create them with pandas first, then wrap with `md.Index()`:

```python
import pandas as pd
import maxframe.dataframe as md

# Create pandas Index objects first
pd_range_index = pd.RangeIndex(0, 10000, 1, name="range_index")
pd_categorical_index = pd.CategoricalIndex(['A', 'B', 'C'] * 100, name="cat_idx")
pd_datetime_index = pd.DatetimeIndex(pd.date_range('2024-01-01', periods=100))
pd_multi_index = pd.MultiIndex.from_tuples([('A', 1), ('A', 2), ('B', 1)])

# Wrap with MaxFrame Index
mf_range_index = md.Index(pd_range_index)
mf_categorical_index = md.Index(pd_categorical_index)
mf_datetime_index = md.Index(pd_datetime_index)
mf_multi_index = md.Index(pd_multi_index)

# Use in DataFrame
df = md.DataFrame({'value': range(100)}, index=mf_range_index)
```

#### Eval and Query Limitations

MaxFrame supports `eval()` and `query()` methods but with some limitations:

```python
# ✅ Supported: DataFrame.eval() for column assignments
df.eval("new_col = col1 + col2")
df.eval("""
col3 = col1 * col2
col4 = col1 / col2
""")

# ✅ Supported: query() for boolean filtering
df.query("age > 25 and salary > 50000")

# ✅ Supported: local_dict parameter
x = 10
md.eval("df.A + x", local_dict={"df": df, "x": x})

# ✅ Supported: target parameter
md.eval("new_col = df.A + df.B", target=df)

# ❌ Not Supported: parser parameter (raises NotImplementedError)
# df.eval("A + B", parser='python')  # Will fail

# ❌ Not Supported: engine parameter (raises NotImplementedError)
# df.eval("A + B", engine='numexpr')  # Will fail

# Default behavior: MaxFrame uses its own parser='maxframe'
```

#### GroupBy Operations

Most groupby operations work as expected, with a few exceptions:

```python
# ✅ Supported: Standard aggregations
df.groupby('category').mean()
df.groupby('category').agg({'value': ['sum', 'mean', 'std']})

# ✅ Supported: Apply operations (use skip_infer for complex functions)
df.groupby('category').apply(
    lambda x: md.Series({'max': x['value'].max(), 'min': x['value'].min()}),
    skip_infer=True
)

# ✅ Supported: Parameters
df.groupby('category').mean(numeric_only=True)
df.groupby('category').sum(min_count=1)
df.groupby('category').std(ddof=0)

# ❌ Not Supported: nth() method
# df.groupby('category').nth(0)  # Not available

# ❌ Not Supported: quantile with interpolation parameter
# df.groupby('category').quantile(0.5, interpolation='linear')  # Not available
```

#### Statistical Operations

MaxFrame handles NaN values automatically in statistical operations:

```python
# All these operations handle NaN automatically (skipna=True by default)
df['column'].mean()      # Equivalent to pandas nanmean
df['column'].std()       # Equivalent to pandas nanstd
df['column'].var()       # Equivalent to pandas nanvar
df['column'].sum()       # Equivalent to pandas nansum
df['column'].median()    # Equivalent to pandas nanmedian

# Correlation and covariance
df.corr()               # Handles NaN automatically
df.cov()                # Handles NaN automatically

# No need to use pandas internal APIs like pd.core.nanops
# MaxFrame's public API methods handle NaN values correctly
```

#### Apply Operations with skip_infer

For complex apply operations, use `skip_infer=True` to improve performance:

```python
# For complex transformations that return Series
result = df.groupby('category').apply(
    lambda x: md.Series({
        'total': x['value'].sum(),
        'avg': x['value'].mean(),
        'count': len(x)
    }),
    skip_infer=True  # Skip type inference for better performance
)

# For Series apply with custom functions
result = df['column'].apply(
    lambda x: complex_function(x),
    skip_infer=True
)
```

#### Lazy Execution Best Practices

Always remember to call `.execute()` on MaxFrame objects:

```python
# ❌ Wrong: Result is not computed
result = df[df['age'] > 25].groupby('city').mean()
print(result)  # Shows computation graph, not data

# ✅ Correct: Execute to get results
result = df[df['age'] > 25].groupby('city').mean()
result = result.execute()  # Now result contains actual data
print(result)  # Shows the data

# ✅ Chain operations before executing
result = (df[df['age'] > 25]
          .groupby('city')
          .agg({'salary': 'mean', 'count': 'size'})
          .execute())
```

#### Working with Different Data Types

```python
# ✅ Supported: Basic dtype conversions
df['int_col'].astype('float64')
df['string_col'].astype('category')
df['int_col'].astype('string')

# ✅ Supported: Categorical operations
df['cat_col'].cat.categories
df['cat_col'].cat.codes
df['cat_col'].cat.add_categories(['new_cat'])
df['cat_col'].cat.remove_categories(['old_cat'])

# ⚠️ Limited: Nullable dtypes (Int64, Float64, boolean, string)
# These work but may have limited support compared to pandas
df['col'].astype('Int64')
df['col'].astype('Float64')
df['col'].astype('boolean')
```

#### Array Operations

MaxFrame supports common array operations through its public API:

```python
# ✅ Supported: Rank operations
df['column'].rank(method='average')
df['column'].rank(method='min')

# ✅ Supported: Unique and duplicated
df['column'].unique()
df['column'].duplicated()
df.drop_duplicates()

# ✅ Supported: Factorize
codes, uniques = md.factorize(df['column'])

# ❌ Don't use: Internal pandas APIs
# from pandas.core.algorithms import rank  # Don't use internal APIs
# Use MaxFrame's public methods instead
```

#### Performance Tips

1. **Batch Operations**: Use `.mf.apply_chunk()` for processing large datasets in batches
2. **Skip Infer**: Use `skip_infer=True` in apply operations when you know the output type
3. **Minimize Executions**: Build computation graphs and execute once rather than multiple times
4. **Use Built-in Functions**: MaxFrame's built-in aggregations are optimized for distributed execution
5. **Avoid Internal APIs**: Always use MaxFrame's public API methods

```python
# ✅ Good: Single execution of complex pipeline
result = (df
          .query("age > 25")
          .groupby('category')
          .agg({'value': ['sum', 'mean', 'std']})
          .execute())

# ❌ Bad: Multiple executions
filtered = df.query("age > 25").execute()
grouped = filtered.groupby('category').execute()
result = grouped.agg({'value': 'sum'}).execute()
```

---

## Additional API Usage Examples

### Index Operations

```python
# Creating different types of indexes
import pandas as pd

# RangeIndex
pd_range_index = pd.RangeIndex(0, 10000, 1, name="range_index")
range_index = md.Index(pd_range_index)

# CategoricalIndex
categories = ["A", "B", "C"]
cat_data = ["A", "B", "C", "A", "B"]  # example data
pd_cat_index = pd.CategoricalIndex(cat_data, categories=categories, name="cat_index")
cat_index = md.Index(pd_cat_index)

# DatetimeIndex
dates = pd.date_range("2020-01-01", periods=1000, freq="D")
pd_datetime_index = pd.DatetimeIndex(dates, name="datetime_index")
datetime_index = md.Index(pd_datetime_index)

# MultiIndex
level1 = ["A", "B"] * 500
level2 = list(range(1000))
pd_multi_index = pd.MultiIndex.from_arrays([level1, level2], names=["first", "second"])
multi_index = md.Index(pd_multi_index)

# Common index operations
idx_unique = index.unique()
idx_sorted = index.sort_values()
idx_dropped = index.drop_duplicates()  # New API discovered in benchmarks
idx_to_frame = index.to_frame()       # New API discovered in benchmarks

# Index to dataframe conversion
df_from_index = index.to_frame(name="custom_name")
```

### Series Operations

```python
# Series creation
series = md.Series([1, 2, 3, 4, 5], name="values")

# Basic operations
result = series + 10
result = result * 2
result = result / 5

# Aggregations
mean_val = series.mean()
sum_val = series.sum()
min_val = series.min()
max_val = series.max()

# Statistical operations
median_val = series.median()
std_val = series.std()
var_val = series.var()
q25 = series.quantile(0.25)
q75 = series.quantile(0.75)

# Apply and map
applied = series.apply(lambda x: x ** 2)
mapped = series.map({1: "one", 2: "two", 3: "three"})

# String operations on series
string_series = md.Series(["hello", "world", "test"])
upper_strings = string_series.str.upper()
string_lengths = string_series.str.len()

# Value operations
value_counts = series.value_counts()
unique_vals = series.unique()

# Series to dataframe conversion
series_df = series.to_frame()
named_series_df = series.to_frame(name="custom_name")

# Groupby operations on series
grouped = series.groupby(level=0)
grouped_mean = grouped.mean()

# Rolling and expanding operations
rolling_mean = series.rolling(window=10).mean()
expanding_sum = series.expanding().sum()

# Sorting
sorted_series = series.sort_values()
sorted_by_index = series.sort_index()

# Missing value operations
missing_mask = series.isna()
not_missing_mask = series.notna()
filled_series = series.fillna(0)
dropped_na = series.dropna()
```

### DataFrame Operations

```python
# Create a sample dataframe
df = md.DataFrame({
    "int_col": [1, 2, 3, 4, 5],
    "float_col": [1.1, 2.2, 3.3, 4.4, 5.5],
    "category_col": ["A", "B", "A", "C", "B"],
    "group_col": ["Group1", "Group1", "Group2", "Group2", "Group1"]
})

# Describe operations
description = df.describe()
series_description = df["int_col"].describe()

# Apply operations
df_result = df.apply(lambda x: x["int_col"] * x["float_col"], axis=1)

# GroupBy operations
grouped = df.groupby("group_col")
agg_result = grouped.agg({"int_col": ["mean", "sum", "count"]})
transform_result = grouped["int_col"].transform(lambda x: x - x.mean())

# Merge operations
df2 = md.DataFrame({
    "int_col": [1, 2, 3],
    "additional_col": [10, 20, 30]
})
merged = md.merge(df, df2, on="int_col", how="inner")
left_joined = md.merge(df, df2, on="int_col", how="left")

# Head and tail operations
head_result = df.head(10)
tail_result = df.tail(10)

# Sample operations
sampled = df.sample(n=100, random_state=42)

# Query operations
filtered = df.query("int_col > 2 and float_col < 4.0")
complex_filtered = df.query("int_col > 30 and float_col > 80000 and score > 70")

# Cross-tabulation and pivot tables
crosstab_result = md.crosstab(df["category_col"], df["group_col"])
pivot_result = md.pivot_table(
    df,
    values="float_col",
    index="category_col",
    columns="group_col",
    aggfunc="mean"
)

# Melt operations
melted = md.melt(df, id_vars=["group_col"], value_vars=["int_col", "float_col"])
```

### Utility Functions

```python
# Binning operations
ages = md.Series([25, 35, 45, 55, 65])
age_groups = md.cut(ages, bins=3)  # Equal-width bins
age_groups = md.cut(ages, bins=[0, 30, 50, 100], labels=["Young", "Adult", "Senior"])

# Quantile-based binning
salaries = md.Series([30000, 50000, 70000, 90000, 120000])
salary_quartiles = md.qcut(salaries, q=4)  # Quartiles
salary_quartiles = md.qcut(salaries, q=4, labels=["Low", "Medium", "High", "Very High"])

# One-hot encoding
df_with_categorical = md.DataFrame({"department": ["IT", "HR", "Sales", "IT"]})
dummies = md.get_dummies(df_with_categorical, columns=["department"])
dummies_prefix = md.get_dummies(df_with_categorical, columns=["department"], prefix="dept")
dummies_dropped = md.get_dummies(df_with_categorical, columns=["department"], drop_first=True)

# Type conversion
string_numbers = md.Series(["100", "200.5", "300"])
numeric_series = md.to_numeric(string_numbers, errors="coerce")  # Invalid values become NaN
integer_series = md.to_numeric(string_numbers, downcast="integer")

# Expression evaluation
eval_df = md.DataFrame({
    "a": [1, 2, 3],
    "b": [4, 5, 6],
    "c": [7, 8, 9],
    "d": [10, 11, 12]
})
result_df = eval_df.eval("result = a + b")
eval_df = eval_df.eval("result = (a + b) * c / d")
flagged_df = eval_df.eval("flag = a > b")
multi_assign_df = eval_df.eval("""
x = a + b
y = c * d
""")

# Record operations
records = [{"id": i, "value": i * 10, "name": f"item_{i}"} for i in range(5)]
records_df = md.DataFrame.from_records(records)
dict_df = md.DataFrame.from_dict({
    "id": [1, 2, 3],
    "value": [10, 20, 30],
    "name": ["item_1", "item_2", "item_3"]
})

# Array utilities
unique_vals = md.unique(df["category_col"])
codes, uniques = md.factorize(df["category_col"])

# Missing value functions
missing_mask = md.isna(df["int_col"])
not_missing_mask = md.notna(df["int_col"])
```

### Advanced Operations

```python
# Categorical operations
cat_series = df["category_col"].astype("category")
categories = cat_series.cat.categories
codes = cat_series.cat.codes
is_ordered = cat_series.cat.ordered
cat_with_new = cat_series.cat.add_categories(["F", "G"])
cat_removed = cat_series.cat.remove_categories(["C"])

# String accessor operations (series)
text_series = md.Series(["Hello World", "MaxFrame Test", "Data Processing"])
lower_text = text_series.str.lower()
upper_text = text_series.str.upper()
text_len = text_series.str.len()
contains_pattern = text_series.str.contains("Hello")
replaced_text = text_series.str.replace("Hello", "Hi")
split_text = text_series.str.split(" ")
string_slice = text_series.str.slice(0, 5)

# Datetime accessor operations
dates = ["2021-01-01", "2021-02-15", "2021-03-20"]
datetime_series = md.to_datetime(md.Series(dates))
years = datetime_series.dt.year
months = datetime_series.dt.month
days = datetime_series.dt.day
weekdays = datetime_series.dt.weekday
quarters = datetime_series.dt.quarter

# Date range generation
date_range = md.date_range(start="2020-01-01", end="2024-12-31", freq="D")
monthly_range = md.date_range(start="2020-01-01", end="2024-12-31", freq="MS")
business_days = md.date_range(start="2020-01-01", end="2024-12-31", freq="B")

# Mathematical and statistical operations
series_with_nans = md.Series([1, 2, None, 4, 5])
mean_val = series_with_nans.mean()  # Automatically handles NaN
std_val = series_with_nans.std()    # Automatically handles NaN
sum_val = series_with_nans.sum()    # Automatically handles NaN

# Correlation and covariance
numeric_df = md.DataFrame({
    "A": [1, 2, 3, 4, 5],
    "B": [2, 4, 6, 8, 10],
    "C": [5, 3, 1, 4, 2]
})
corr_matrix = numeric_df.corr()
cov_matrix = numeric_df.cov()

# Skewness and kurtosis
skewness = numeric_df["A"].skew()
kurtosis = numeric_df["A"].kurtosis()
```

---

*For basic operations and module reference, see `key-modules.md`. For official documentation, visit https://maxframe.readthedocs.io*
