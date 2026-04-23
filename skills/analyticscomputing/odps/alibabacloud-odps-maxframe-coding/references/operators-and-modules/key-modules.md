# MaxFrame Key Modules Reference

This document provides comprehensive reference for MaxFrame's key modules: DataFrame operations, Tensor operations, and Machine Learning capabilities.

## Table of Contents

- [DataFrame Operations](#dataframe-operations)
  - [Creating DataFrames](#creating-dataframes)
  - [Data Reading](#data-reading)
  - [Data Selection and Filtering](#data-selection-and-filtering)
  - [Data Transformation](#data-transformation)
  - [Aggregation and GroupBy](#aggregation-and-groupby)
  - [Join and Merge Operations](#join-and-merge-operations)
  - [Data Writing](#data-writing)
  - [MaxFrame-Specific Operations](#maxframe-specific-operations)
- [Tensor Operations](#tensor-operations)
  - [Creating Tensors](#creating-tensors)
  - [Mathematical Operations](#mathematical-operations)
  - [Statistical Operations](#statistical-operations)
  - [Linear Algebra](#linear-algebra)
  - [Array Manipulation](#array-manipulation)
- [Machine Learning](#machine-learning)
  - [Preprocessing](#preprocessing)
  - [Linear Models](#linear-models)
  - [Tree-Based Models](#tree-based-models)
  - [Model Evaluation](#model-evaluation)
  - [Model Selection](#model-selection)
- [UDF Resource Allocation](#udf-resource-allocation)
  - [with_running_options Decorator](#with_running_options-decorator)
- [Common Operations Reference Table](#common-operations-reference-table)

---

## DataFrame Operations

MaxFrame DataFrame provides pandas-compatible APIs for distributed data processing on MaxCompute. Import the module:

```python
import maxframe.dataframe as md
```

### Creating DataFrames

Create DataFrames from various data sources:

```python
# From dictionary
df = md.DataFrame({
    'id': [1, 2, 3, 4, 5],
    'name': ['Alice', 'Bob', 'Charlie', 'David', 'Eve'],
    'age': [25, 30, 35, 40, 45],
    'salary': [50000, 60000, 70000, 80000, 90000]
})

# From list of dictionaries
df = md.DataFrame([
    {'id': 1, 'name': 'Alice', 'age': 25},
    {'id': 2, 'name': 'Bob', 'age': 30}
])

# From list of tuples with columns
df = md.DataFrame(
    [(1, 'Alice', 25), (2, 'Bob', 30)],
    columns=['id', 'name', 'age']
)
```

### Data Reading

Read data from various sources:

```python
# Read from MaxCompute table
df = md.read_odps_table("my_table")

# Read with specific columns
df = md.read_odps_table("my_table", columns=['col1', 'col2'])

# Read from SQL query
df = md.read_odps_query("SELECT * FROM my_table WHERE status = 'active'")

# Read from pandas DataFrame
import pandas as pd
pd_df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
df = md.read_pandas(pd_df)

# Read from CSV (if supported in your environment)
df = md.read_csv("path/to/file.csv")
```

### Data Selection and Filtering

Select and filter data using various methods:

```python
# Select columns
df_subset = df[['name', 'age']]

# Filter by condition
filtered = df[df['age'] > 30]

# Multiple conditions
filtered = df[(df['age'] > 25) & (df['salary'] < 80000)]

# Filter using isin()
filtered = df[df['name'].isin(['Alice', 'Bob'])]

# Filter using query() method
filtered = df.query('age > 30 and salary < 80000')

# Select rows by position
first_three = df.head(3)
last_three = df.tail(3)

# Select rows by index
selected = df.iloc[0:5]  # First 5 rows
selected = df.loc[df['age'] > 30]  # Label-based selection
```

### Data Transformation

Transform data using various operations:

```python
# Add new column
df['bonus'] = df['salary'] * 0.1

# Modify existing column
df['age'] = df['age'] + 1

# Column arithmetic
df['total_compensation'] = df['salary'] + df['bonus']

# Apply function to column
df['name_upper'] = df['name'].apply(lambda x: x.upper())

# Apply function to multiple columns
df[['salary', 'bonus']] = df[['salary', 'bonus']].apply(lambda x: x * 1.05)

# Rename columns
df_renamed = df.rename(columns={'name': 'full_name', 'age': 'years_old'})

# Drop columns
df_dropped = df.drop(columns=['bonus', 'total_compensation'])

# Drop duplicates
df_unique = df.drop_duplicates(subset=['name'])

# Fill missing values
df_filled = df.fillna({'age': 0, 'salary': df['salary'].mean()})

# Sort by column
df_sorted = df.sort_values('age', ascending=True)
df_sorted = df.sort_values(['age', 'salary'], ascending=[True, False])
```

### Aggregation and GroupBy

Perform aggregation and grouping operations:

```python
# Simple aggregation
total_salary = df['salary'].sum()
average_age = df['age'].mean()
max_salary = df['salary'].max()
min_salary = df['salary'].min()
count_rows = df.count()

# Multiple aggregations
stats = df[['age', 'salary']].agg(['mean', 'std', 'min', 'max'])

# GroupBy single column
grouped = df.groupby('department')['salary'].mean()

# GroupBy multiple columns
grouped = df.groupby(['department', 'role'])['salary'].sum()

# Multiple aggregations per group
grouped = df.groupby('department').agg({
    'salary': ['mean', 'sum', 'count'],
    'age': ['mean', 'min', 'max']
})

# Apply custom function to groups
def custom_agg(group):
    return pd.Series({
        'avg_salary': group['salary'].mean(),
        'salary_range': group['salary'].max() - group['salary'].min()
    })

grouped = df.groupby('department').apply(custom_agg)

# Count unique values per group
unique_counts = df.groupby('department')['role'].nunique()
```

### Join and Merge Operations

Combine DataFrames using various join operations:

```python
# Inner join (default)
merged = df1.merge(df2, on='id')

# Left join
merged = df1.merge(df2, on='id', how='left')

# Right join
merged = df1.merge(df2, on='id', how='right')

# Outer join
merged = df1.merge(df2, on='id', how='outer')

# Join on different columns
merged = df1.merge(df2, left_on='user_id', right_on='id')

# Join on multiple columns
merged = df1.merge(df2, on=['id', 'date'])

# Join with suffixes for duplicate columns
merged = df1.merge(df2, on='id', suffixes=('_left', '_right'))

# Concatenate DataFrames vertically
concatenated = md.concat([df1, df2])

# Concatenate DataFrames horizontally
concatenated = md.concat([df1, df2], axis=1)
```

### Data Writing

Write data to various destinations:

```python
# Write to MaxCompute table
md.to_odps_table(df, "output_table", overwrite=True).execute()

# Write without overwriting
md.to_odps_table(df, "output_table", overwrite=False).execute()

# Write to DLF external table (requires configuration)
from maxframe import options
options.sql.settings = {
    "odps.maxframe.resolve_dlf_tables": "true"
}
md.to_odps_table(df, "dlf_table").execute()

# Write to CSV
df.to_csv("output.csv")

# Write to pandas DataFrame (for local processing)
pd_df = df.to_pandas().execute()

# Write to parquet
df.to_parquet("output.parquet").execute()
```

### MaxFrame-Specific Operations

MaxFrame provides additional operations for distributed processing:

```python
# Apply function in batches (efficient for large datasets)
def process_batch(chunk):
    # Process each batch of rows
    chunk['processed'] = chunk['value'] * 2
    return chunk

result = df.mf.apply_chunk(
    process_batch,
    batch_rows=1000,
    output_type='dataframe'
)

# Rebalance data distribution
df_rebalanced = df.mf.rebalance()

# Resuffle data
df_shuffled = df.mf.reshuffle()

# MapReduce operation
def mapper(row):
    return (row['category'], row['value'])

def reducer(key, values):
    return sum(values)

result = df.mf.map_reduce(mapper, reducer)

# Extract key-value pairs
kv_pairs = df.mf.extract_kv('key_column', 'value_column')

# Collect key-value pairs
result = df.mf.collect_kv()
```

---

## Tensor Operations

MaxFrame tensor provides NumPy-like operations for numerical computing. Import the module:

```python
import maxframe.tensor as mt
```

### Creating Tensors

Create tensors from various sources:

```python
# From list or array
arr = mt.array([1, 2, 3, 4, 5])

# From nested list (2D array)
matrix = mt.array([[1, 2, 3], [4, 5, 6]])

# Create zeros array
zeros = mt.zeros((3, 4))

# Create ones array
ones = mt.ones((2, 3))

# Create array with specific value
full = mt.full((3, 3), 7)

# Create identity matrix
identity = mt.eye(4)

# Create range
range_arr = mt.arange(0, 10, 2)  # [0, 2, 4, 6, 8]

# Create linspace
linspace = mt.linspace(0, 1, 5)  # [0, 0.25, 0.5, 0.75, 1]

# Create random array
random_arr = mt.random.rand(3, 4)
random_int = mt.random.randint(0, 10, size=(3, 3))
```

### Mathematical Operations

Perform mathematical operations on tensors:

```python
# Basic arithmetic
a = mt.array([1, 2, 3])
b = mt.array([4, 5, 6])

addition = a + b          # [5, 7, 9]
subtraction = a - b       # [-3, -3, -3]
multiplication = a * b    # [4, 10, 18]
division = a / b          # [0.25, 0.4, 0.5]
power = a ** 2            # [1, 4, 9]

# Scalar operations
scalar_add = a + 10       # [11, 12, 13]
scalar_mul = a * 2        # [2, 4, 6]

# Trigonometric functions
angles = mt.array([0, mt.pi/2, mt.pi])
sin_vals = mt.sin(angles)
cos_vals = mt.cos(angles)
tan_vals = mt.tan(angles)

# Exponential and logarithmic
exp_vals = mt.exp(a)
log_vals = mt.log(a)
log10_vals = mt.log10(a)

# Rounding
arr = mt.array([1.2, 2.6, 3.5, -1.7])
rounded = mt.round(arr)
floor = mt.floor(arr)
ceil = mt.ceil(arr)
```

### Statistical Operations

Calculate statistics on tensors:

```python
arr = mt.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

# Basic statistics
total = mt.sum(arr)              # Sum of all elements
mean = mt.mean(arr)              # Mean value
median = mt.median(arr)          # Median value
std = mt.std(arr)                # Standard deviation
var = mt.var(arr)                # Variance

# Axis-specific operations
row_sum = mt.sum(arr, axis=1)    # Sum of each row
col_sum = mt.sum(arr, axis=0)    # Sum of each column
row_mean = mt.mean(arr, axis=1)  # Mean of each row
col_mean = mt.mean(arr, axis=0)  # Mean of each column

# Min and max
min_val = mt.min(arr)
max_val = mt.max(arr)
row_min = mt.min(arr, axis=1)
col_max = mt.max(arr, axis=0)

# Percentiles
percentile_25 = mt.percentile(arr, 25)
percentile_50 = mt.percentile(arr, 50)
percentile_75 = mt.percentile(arr, 75)

# Correlation and covariance
corr = mt.corrcoef(arr)
cov = mt.cov(arr)
```

### Linear Algebra

Perform linear algebra operations:

```python
# Matrix multiplication
A = mt.array([[1, 2], [3, 4]])
B = mt.array([[5, 6], [7, 8]])

dot_product = mt.dot(A, B)           # Matrix multiplication
matmul = mt.matmul(A, B)             # Same as dot for 2D

# Element-wise operations
element_mul = A * B                   # Element-wise multiplication

# Transpose
transposed = mt.transpose(A)
transposed = A.T                      # Alternative syntax

# Matrix properties
determinant = mt.linalg.det(A)
rank = mt.linalg.matrix_rank(A)
trace = mt.trace(A)

# Eigenvalues and eigenvectors
eigenvalues, eigenvectors = mt.linalg.eig(A)

# Solving linear systems
b = mt.array([1, 2])
x = mt.linalg.solve(A, b)

# Matrix inverse
inverse = mt.linalg.inv(A)

# Norm
frobenius_norm = mt.linalg.norm(A)
l1_norm = mt.linalg.norm(A, ord=1)
l2_norm = mt.linalg.norm(A, ord=2)
max_norm = mt.linalg.norm(A, ord=mt.inf)

# SVD decomposition
U, S, V = mt.linalg.svd(A)

# Cholesky decomposition (for positive definite matrices)
pos_def = mt.array([[4, 12], [12, 37]])
L = mt.linalg.cholesky(pos_def)
```

### Array Manipulation

Manipulate tensor shapes and contents:

```python
arr = mt.array([[1, 2, 3], [4, 5, 6]])

# Reshape
reshaped = mt.reshape(arr, (3, 2))  # Change shape
flattened = arr.flatten()           # Flatten to 1D
raveled = arr.ravel()               # Flatten (may return view)

# Transpose operations
transposed = arr.T
swapped = mt.swapaxes(arr, 0, 1)

# Stacking
a = mt.array([1, 2, 3])
b = mt.array([4, 5, 6])
stacked = mt.stack([a, b])          # Stack along new axis
hstacked = mt.hstack([a, b])        # Horizontal stack
vstacked = mt.vstack([a, b])        # Vertical stack

# Splitting
arr = mt.array([[1, 2, 3], [4, 5, 6]])
split = mt.split(arr, 2, axis=0)    # Split into 2 arrays
hsplit = mt.hsplit(arr, 3)          # Horizontal split
vsplit = mt.vsplit(arr, 2)          # Vertical split

# Indexing and slicing
arr = mt.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
element = arr[1, 2]                 # Single element
row = arr[1, :]                     # Entire row
col = arr[:, 1]                     # Entire column
subarray = arr[0:2, 1:3]            # Subarray

# Boolean indexing
arr = mt.array([1, 2, 3, 4, 5])
mask = arr > 2
filtered = arr[mask]                # [3, 4, 5]

# Fancy indexing
arr = mt.array([10, 20, 30, 40, 50])
indices = mt.array([0, 2, 4])
selected = arr[indices]             # [10, 30, 50]

# Sorting
arr = mt.array([3, 1, 4, 1, 5, 9])
sorted_arr = mt.sort(arr)           # Returns sorted copy
argsorted = mt.argsort(arr)         # Returns indices that would sort

# Unique values
arr = mt.array([1, 2, 2, 3, 3, 3])
unique = mt.unique(arr)             # [1, 2, 3]

# Broadcasting
a = mt.array([[1], [2], [3]])
b = mt.array([4, 5, 6])
result = a + b                      # [[5, 6, 7], [6, 7, 8], [7, 8, 9]]
```

---

## Machine Learning

MaxFrame Learn provides scikit-learn-like machine learning capabilities. Import the modules:

```python
from maxframe import learn
from maxframe.learn import preprocessing
from maxframe.learn.linear_model import LinearRegression, LogisticRegression
from maxframe.learn.tree import DecisionTreeClassifier, RandomForestClassifier
from maxframe.learn.metrics import accuracy_score, mean_squared_error
```

### Preprocessing

Prepare data for machine learning:

```python
# Standardization (zero mean, unit variance)
from maxframe.learn import preprocessing

scaler = preprocessing.StandardScaler()
X_scaled = scaler.fit_transform(X)

# Only fit on training data, then transform test data
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Min-Max scaling (scale to [0, 1])
minmax_scaler = preprocessing.MinMaxScaler()
X_normalized = minmax_scaler.fit_transform(X)

# Robust scaling (using median and quartiles)
robust_scaler = preprocessing.RobustScaler()
X_robust = robust_scaler.fit_transform(X)

# Label encoding (convert categorical to numeric)
label_encoder = preprocessing.LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# One-hot encoding
onehot_encoder = preprocessing.OneHotEncoder()
X_onehot = onehot_encoder.fit_transform(X_categorical)

# Polynomial features
poly = preprocessing.PolynomialFeatures(degree=2)
X_poly = poly.fit_transform(X)

# Train-test split
from maxframe.learn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# K-Fold cross-validation
from maxframe.learn.model_selection import KFold
kf = KFold(n_splits=5, shuffle=True, random_state=42)
for train_idx, test_idx in kf.split(X):
    X_train, X_test = X[train_idx], X[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
```

### Linear Models

Train linear models for regression and classification:

```python
# Linear Regression
from maxframe.learn.linear_model import LinearRegression

model = LinearRegression()
model.fit(X_train, y_train)
predictions = model.predict(X_test)

# Get model coefficients
coefficients = model.coef_
intercept = model.intercept_

# Logistic Regression
from maxframe.learn.linear_model import LogisticRegression

clf = LogisticRegression(max_iter=1000)
clf.fit(X_train, y_train)
predictions = clf.predict(X_test)
probabilities = clf.predict_proba(X_test)

# Ridge Regression (L2 regularization)
from maxframe.learn.linear_model import Ridge

ridge = Ridge(alpha=1.0)
ridge.fit(X_train, y_train)
predictions = ridge.predict(X_test)

# Lasso Regression (L1 regularization)
from maxframe.learn.linear_model import Lasso

lasso = Lasso(alpha=1.0)
lasso.fit(X_train, y_train)
predictions = lasso.predict(X_test)

# Elastic Net (combined L1 and L2)
from maxframe.learn.linear_model import ElasticNet

elastic_net = ElasticNet(alpha=1.0, l1_ratio=0.5)
elastic_net.fit(X_train, y_train)
predictions = elastic_net.predict(X_test)
```

### Tree-Based Models

Train tree-based models:

```python
# Decision Tree Classifier
from maxframe.learn.tree import DecisionTreeClassifier

dt_clf = DecisionTreeClassifier(max_depth=5, random_state=42)
dt_clf.fit(X_train, y_train)
predictions = dt_clf.predict(X_test)

# Decision Tree Regressor
from maxframe.learn.tree import DecisionTreeRegressor

dt_reg = DecisionTreeRegressor(max_depth=5, random_state=42)
dt_reg.fit(X_train, y_train)
predictions = dt_reg.predict(X_test)

# Random Forest Classifier
from maxframe.learn.ensemble import RandomForestClassifier

rf_clf = RandomForestClassifier(n_estimators=100, random_state=42)
rf_clf.fit(X_train, y_train)
predictions = rf_clf.predict(X_test)

# Random Forest Regressor
from maxframe.learn.ensemble import RandomForestRegressor

rf_reg = RandomForestRegressor(n_estimators=100, random_state=42)
rf_reg.fit(X_train, y_train)
predictions = rf_reg.predict(X_test)

# Gradient Boosting
from maxframe.learn.ensemble import GradientBoostingClassifier

gb_clf = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, random_state=42)
gb_clf.fit(X_train, y_train)
predictions = gb_clf.predict(X_test)
```

### Model Evaluation

Evaluate model performance:

```python
from maxframe.learn import metrics

# Classification metrics
accuracy = metrics.accuracy_score(y_test, predictions)
precision = metrics.precision_score(y_test, predictions, average='weighted')
recall = metrics.recall_score(y_test, predictions, average='weighted')
f1 = metrics.f1_score(y_test, predictions, average='weighted')

# Confusion matrix
conf_matrix = metrics.confusion_matrix(y_test, predictions)

# Classification report
report = metrics.classification_report(y_test, predictions)

# ROC AUC score
probabilities = clf.predict_proba(X_test)
roc_auc = metrics.roc_auc_score(y_test, probabilities[:, 1])

# Regression metrics
mse = metrics.mean_squared_error(y_test, predictions)
rmse = metrics.mean_squared_error(y_test, predictions, squared=False)
mae = metrics.mean_absolute_error(y_test, predictions)
r2 = metrics.r2_score(y_test, predictions)

# Cross-validation score
from maxframe.learn.model_selection import cross_val_score
scores = cross_val_score(model, X, y, cv=5)
mean_score = scores.mean()
```

### Model Selection

Select and tune models:

```python
# Grid search for hyperparameter tuning
from maxframe.learn.model_selection import GridSearchCV

param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.01, 0.1, 0.2]
}

grid_search = GridSearchCV(
    estimator=GradientBoostingClassifier(),
    param_grid=param_grid,
    cv=5,
    scoring='accuracy'
)

grid_search.fit(X_train, y_train)
best_model = grid_search.best_estimator_
best_params = grid_search.best_params_

# Random search for hyperparameter tuning
from maxframe.learn.model_selection import RandomizedSearchCV

random_search = RandomizedSearchCV(
    estimator=RandomForestClassifier(),
    param_distributions=param_grid,
    n_iter=10,
    cv=5,
    scoring='accuracy'
)

random_search.fit(X_train, y_train)
best_model = random_search.best_estimator_
```

---

## UDF Resource Allocation

### with_running_options Decorator

The `@with_running_options` decorator from `maxframe.udf` allows you to allocate computational resources (CPU, memory, GPU units) for user-defined functions (UDFs) executed on the DPE (Data Processing Engine) engine. This is essential for optimizing performance and ensuring functions have adequate resources.

#### Import

```python
from maxframe.udf import with_running_options
```

#### Parameters

| Parameter | Type | Description | Example Values |
|-----------|------|-------------|----------------|
| `engine` | str | Execution engine type | `"dpe"` (recommended for UDFs) |
| `cpu` | int | Number of CPU cores to allocate | 1, 2, 4, 8 |
| `memory` | int | Memory allocation in **gigabytes (GB)** | 2, 4, 8, 16 |
| `gu` | int | Number of GPU Units (GU) for GPU-accelerated processing | 1, 2, 4 |
| `gu_quota` | str | GPU quota name for GU allocation | `"your_gu_quota_name"` |

**IMPORTANT**: The `memory` parameter expects values in **gigabytes (GB)**, not megabytes (MB). For example:
- `memory=4` means 4 GB
- `memory=2` means 2 GB
- ❌ **Wrong**: `memory=4096` (this would request 4096 GB = 4 TB!)

#### Basic Usage

##### 1. CPU and Memory Allocation

Allocate CPU cores and memory for compute-intensive UDFs:

```python
from maxframe.udf import with_running_options
import maxframe.dataframe as md

# Allocate 2 CPU cores and 4 GB memory
@with_running_options(engine="dpe", cpu=2, memory=4)
def process_data(batch):
    """Process data with allocated resources."""
    result = batch.copy()
    result['computed'] = result['value'] * 2
    return result

# Apply the function
df = md.read_odps_table("input_table")
result = df.mf.apply_chunk(
    process_data,
    batch_rows=1000,
    output_type='dataframe'
)
result.execute()
```

##### 2. GPU Acceleration with GPU Units (GU)

Allocate GPU units for GPU-accelerated workloads:

```python
from maxframe.udf import with_running_options
import maxframe.dataframe as md

# Allocate 1 GPU Unit for GPU-accelerated processing
# Replace 'your_gu_quota' with your actual GU quota name
@with_running_options(engine="dpe", gu=1, gu_quota="your_gu_quota")
def gpu_accelerated_function(row):
    """Process data with GPU acceleration."""
    # Your GPU-accelerated logic here
    # Example: matrix operations, ML inference, etc.
    result = row.copy()
    result['processed'] = row['value'] * 2
    return result

# Apply the GPU-accelerated function
df = md.read_odps_table("ml_features")
result = df.apply(
    gpu_accelerated_function,
    axis=1,
    dtypes=df.dtypes,
    output_type='dataframe',
    skip_infer=True
)
result.execute()
```

##### 3. Resource Allocation for Classes (MapReduce)

Use with class-based UDFs such as reducers in MapReduce operations:

```python
from collections import defaultdict
from maxframe.udf import with_running_options

# Allocate resources for a reducer class
@with_running_options(cpu=2, memory=4)
class WordCountReducer:
    """Reducer for word count with allocated resources."""

    def __init__(self):
        self._word_to_count = defaultdict(lambda: 0)

    def __call__(self, batch, end=False):
        """Process batch and aggregate counts."""
        word = None
        for _, row in batch.iterrows():
            word = row.iloc[0]
            self._word_to_count[row.iloc[0]] += row.iloc[1]

        if end:
            return pd.DataFrame(
                [[word, self._word_to_count[word]]],
                columns=["word", "count"]
            )

# Use in MapReduce
df = md.read_odps_table("documents")
result = df.mf.map_reduce(mapper_func, WordCountReducer)
result.execute()
```

#### When to Use

Use `@with_running_options` when:

1. **Your UDF is compute-intensive**: Functions with complex calculations, large data transformations, or ML inference
2. **Processing large batches**: `apply_chunk()` operations with large `batch_rows`
3. **GPU acceleration needed**: Deep learning inference, matrix operations, or other GPU-accelerated workloads
4. **Memory-intensive operations**: Functions that load models, process large arrays, or create intermediate data structures
5. **MapReduce reducers**: Class-based reducers that aggregate data and benefit from more resources

#### Resource Allocation Guidelines

##### CPU Allocation

| Use Case | Recommended CPU | Example |
|----------|----------------|---------|
| Simple transformations | 1 core | String operations, basic arithmetic |
| Moderate computation | 2 cores | Aggregations, filtering, joins |
| Heavy computation | 4-8 cores | ML inference, complex calculations |

##### Memory Allocation

| Use Case | Recommended Memory | Example |
|----------|-------------------|---------|
| Small batches (<1000 rows) | 2 GB | Simple row transformations |
| Medium batches (1000-10000 rows) | 4 GB | Grouping, sorting, merging |
| Large batches (>10000 rows) | 8-16 GB | Large-scale aggregations, model inference |
| Model loading | 16+ GB | Deep learning models, large embeddings |

**Important**:
- Start with conservative allocations (2 CPU, 4 GB) and increase as needed
- Monitor resource usage via logview URLs to optimize allocations
- Over-allocation wastes resources; under-allocation causes failures
- Memory is specified in **GB**, not MB!

##### GPU Unit Allocation

| Use Case | Recommended GU | Notes |
|----------|---------------|-------|
| ML inference (small models) | 1 GU | LightGBM, small neural networks |
| ML inference (large models) | 2-4 GU | Deep learning, transformers |
| GPU-accelerated computation | 1-2 GU | Matrix operations, signal processing |

**Important**:
- Requires `gu_quota` parameter with your quota name
- Check your MaxCompute account for available GU quotas
- GPU resources are more expensive than CPU; use only when needed

#### Complete Example: Resource-Aware Data Processing Pipeline

```python
import os
import maxframe.dataframe as md
from maxframe.session import new_session
from maxframe.udf import with_running_options
from maxframe.config import options
from odps import ODPS

# Configure DPE engine
options.dag.settings = {
    "engine_order": ["DPE"],
    "unavailable_engines": ["MCSQL", "SPE"],
}
options.sql.settings = {"odps.session.image": "maxframe_service_dpe_runtime"}

# Create session
o = ODPS(
    access_id=os.getenv("ODPS_ACCESS_ID"),
    secret_access_key=os.getenv("ODPS_ACCESS_KEY"),
    project=os.getenv("ODPS_PROJECT"),
    endpoint=os.getenv("ODPS_ENDPOINT"),
    user_agent='AlibabaCloud-Agent-Skills/alibabacloud-odps-maxframe-coding'
)
session = new_session(o)

# Define resource-intensive processing function
@with_running_options(engine="dpe", cpu=4, memory=8)
def complex_transformation(batch):
    """
    Complex data transformation requiring significant resources.

    This function:
    - Loads a pre-trained model
    - Performs feature engineering
    - Runs batch inference
    - Post-processes results
    """
    # Feature engineering
    batch['feature_1'] = batch['value_1'] * batch['value_2']
    batch['feature_2'] = batch['value_1'] / (batch['value_2'] + 1e-6)

    # Complex aggregation
    batch['rolling_mean'] = batch['value_1'].rolling(window=100).mean()

    # Post-processing
    batch['result'] = batch['feature_1'] + batch['rolling_mean']

    return batch

# Process data
try:
    df = md.read_odps_table("large_dataset")

    # Apply transformation with allocated resources
    result = df.mf.apply_chunk(
        complex_transformation,
        batch_rows=5000,  # Larger batches for efficiency
        output_type='dataframe'
    )

    # Write results
    md.to_odps_table(result, "processed_data", overwrite=True).execute()

    print(f"Processing complete. Logview: {session.get_logview_address()}")

finally:
    session.destroy()
```

#### Best Practices

1. **Start Small, Scale Up**: Begin with `cpu=2, memory=4` and increase based on actual needs
2. **Monitor via Logview**: Use logview URLs to check resource utilization and execution performance
3. **Match Batch Size**: Align `batch_rows` in `apply_chunk()` with allocated resources
   - Small batches (<1000): `cpu=1-2, memory=2-4`
   - Medium batches (1000-10000): `cpu=2-4, memory=4-8`
   - Large batches (>10000): `cpu=4-8, memory=8-16`
4. **GPU for ML**: Use GPU units (GU) for ML inference and GPU-accelerated operations
5. **Test Locally First**: Use `debug=True` to test UDF logic locally before allocating resources
6. **Avoid Over-allocation**: Don't request more resources than needed; it wastes quota and may delay scheduling

#### Common Patterns

##### Pattern 1: Simple Data Transformation

```python
@with_running_options(engine="dpe", cpu=1, memory=2)
def simple_transform(batch):
    batch['new_col'] = batch['col_a'] + batch['col_b']
    return batch
```

##### Pattern 2: Aggregation with Moderate Resources

```python
@with_running_options(engine="dpe", cpu=2, memory=4)
def aggregate_processing(batch):
    result = batch.groupby('category').agg({
        'value': ['sum', 'mean', 'count']
    })
    return result
```

##### Pattern 3: ML Inference with High Resources

```python
@with_running_options(engine="dpe", cpu=4, memory=16)
def ml_inference(batch):
    # Load model (requires more memory)
    # model = load_model()

    # Run inference
    # predictions = model.predict(batch)

    batch['prediction'] = batch['feature'] * 2  # Simplified
    return batch
```

##### Pattern 4: GPU-Accelerated Processing

```python
@with_running_options(engine="dpe", gu=1, gu_quota="ml_gpu_quota")
def gpu_processing(batch):
    # GPU-accelerated operations
    # Ideal for: deep learning, matrix operations, signal processing
    return batch
```

#### Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| **Out of memory error** | Insufficient memory allocation | Increase `memory` parameter (e.g., from 4 to 8) |
| **Slow execution** | Under-allocated CPU | Increase `cpu` parameter (e.g., from 2 to 4) |
| **Resource unavailable** | Quota limits reached | Check MaxCompute quota or reduce allocation |
| **GPU not found** | Missing `gu_quota` or invalid quota name | Verify GU quota name in MaxCompute console |
| **Task timeout** | Insufficient resources for workload | Increase both CPU and memory |
| **High cost** | Over-allocation | Monitor usage and reduce allocation to minimum needed |

#### Related Resources

- **Examples**: See `assets/examples/gpu_unit_dpe_processing.py` for GPU usage
- **Examples**: See `assets/examples/fs_mount_example.py` for combined filesystem and resource allocation
- **Examples**: See `assets/examples/oss_multi_mount.py` for multiple OSS mounts with resource allocation
- **Local Debugging**: Use `debug=True` parameter for local testing without resource allocation

---

## Common Operations Reference Table

### DataFrame Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `md.DataFrame()` | Create DataFrame | `df = md.DataFrame({'A': [1, 2, 3]})` |
| `md.read_odps_table()` | Read from MaxCompute table | `df = md.read_odps_table("my_table")` |
| `md.read_odps_query()` | Read from SQL query | `df = md.read_odps_query("SELECT * FROM table")` |
| `df.head()` | Get first n rows | `df.head(5)` |
| `df.tail()` | Get last n rows | `df.tail(5)` |
| `df.describe()` | Get summary statistics | `df.describe()` |
| `df.info()` | Get DataFrame info | `df.info()` |
| `df.columns` | Get column names | `df.columns` |
| `df.shape` | Get dimensions | `df.shape` |
| `df.dtypes` | Get column data types | `df.dtypes` |
| `df.filter()` | Filter columns | `df.filter(['col1', 'col2'])` |
| `df.drop()` | Drop columns/rows | `df.drop(columns=['col1'])` |
| `df.rename()` | Rename columns | `df.rename(columns={'old': 'new'})` |
| `df.sort_values()` | Sort by values | `df.sort_values('col', ascending=False)` |
| `df.sort_index()` | Sort by index | `df.sort_index()` |
| `df.drop_duplicates()` | Remove duplicates | `df.drop_duplicates()` |
| `df.fillna()` | Fill missing values | `df.fillna(0)` |
| `df.dropna()` | Drop missing values | `df.dropna()` |
| `df.groupby()` | Group data | `df.groupby('col').sum()` |
| `df.agg()` | Aggregate | `df.agg({'col': ['mean', 'sum']})` |
| `df.merge()` | Merge DataFrames | `df1.merge(df2, on='key')` |
| `df.join()` | Join DataFrames | `df1.join(df2, on='key')` |
| `md.concat()` | Concatenate DataFrames | `md.concat([df1, df2])` |
| `df.apply()` | Apply function | `df['new'] = df['col'].apply(func)` |
| `df.mf.apply_chunk()` | Apply in batches | `df.mf.apply_chunk(func, batch_rows=1000)` |
| `df.mf.rebalance()` | Rebalance data | `df.mf.rebalance()` |
| `df.mf.reshuffle()` | Shuffle data | `df.mf.reshuffle()` |
| `md.to_odps_table()` | Write to MaxCompute | `md.to_odps_table(df, "table")` |
| `df.to_pandas()` | Convert to pandas | `df.to_pandas()` |
| `df.execute()` | Execute lazy operations | `result.execute()` |

### Tensor Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `mt.array()` | Create tensor | `arr = mt.array([1, 2, 3])` |
| `mt.zeros()` | Create zeros array | `mt.zeros((3, 4))` |
| `mt.ones()` | Create ones array | `mt.ones((2, 3))` |
| `mt.eye()` | Create identity matrix | `mt.eye(4)` |
| `mt.arange()` | Create range | `mt.arange(0, 10)` |
| `mt.linspace()` | Create linspace | `mt.linspace(0, 1, 5)` |
| `mt.sum()` | Sum elements | `mt.sum(arr)` |
| `mt.mean()` | Mean value | `mt.mean(arr)` |
| `mt.median()` | Median value | `mt.median(arr)` |
| `mt.std()` | Standard deviation | `mt.std(arr)` |
| `mt.var()` | Variance | `mt.var(arr)` |
| `mt.min()` | Minimum value | `mt.min(arr)` |
| `mt.max()` | Maximum value | `mt.max(arr)` |
| `mt.dot()` | Dot product | `mt.dot(A, B)` |
| `mt.matmul()` | Matrix multiplication | `mt.matmul(A, B)` |
| `mt.transpose()` | Transpose | `mt.transpose(arr)` |
| `mt.reshape()` | Reshape array | `mt.reshape(arr, (3, 2))` |
| `mt.flatten()` | Flatten array | `arr.flatten()` |
| `mt.sort()` | Sort array | `mt.sort(arr)` |
| `mt.unique()` | Unique values | `mt.unique(arr)` |
| `mt.stack()` | Stack arrays | `mt.stack([a, b])` |
| `mt.concat()` | Concatenate arrays | `mt.concat([a, b])` |
| `mt.linalg.inv()` | Matrix inverse | `mt.linalg.inv(A)` |
| `mt.linalg.det()` | Determinant | `mt.linalg.det(A)` |
| `mt.linalg.eig()` | Eigenvalues | `mt.linalg.eig(A)` |
| `mt.linalg.solve()` | Solve linear system | `mt.linalg.solve(A, b)` |
| `mt.linalg.norm()` | Matrix norm | `mt.linalg.norm(A)` |

### Machine Learning Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `preprocessing.StandardScaler()` | Standardize features | `scaler = StandardScaler()` |
| `preprocessing.MinMaxScaler()` | Min-max scaling | `scaler = MinMaxScaler()` |
| `preprocessing.LabelEncoder()` | Encode labels | `encoder = LabelEncoder()` |
| `preprocessing.OneHotEncoder()` | One-hot encoding | `encoder = OneHotEncoder()` |
| `train_test_split()` | Split train/test | `X_train, X_test, y_train, y_test = train_test_split(X, y)` |
| `LinearRegression()` | Linear regression | `model = LinearRegression()` |
| `LogisticRegression()` | Logistic regression | `clf = LogisticRegression()` |
| `Ridge()` | Ridge regression | `model = Ridge(alpha=1.0)` |
| `Lasso()` | Lasso regression | `model = Lasso(alpha=1.0)` |
| `DecisionTreeClassifier()` | Decision tree classifier | `clf = DecisionTreeClassifier()` |
| `DecisionTreeRegressor()` | Decision tree regressor | `reg = DecisionTreeRegressor()` |
| `RandomForestClassifier()` | Random forest classifier | `clf = RandomForestClassifier()` |
| `RandomForestRegressor()` | Random forest regressor | `reg = RandomForestRegressor()` |
| `GradientBoostingClassifier()` | Gradient boosting | `clf = GradientBoostingClassifier()` |
| `model.fit()` | Train model | `model.fit(X_train, y_train)` |
| `model.predict()` | Make predictions | `predictions = model.predict(X_test)` |
| `model.predict_proba()` | Get probabilities | `probs = model.predict_proba(X_test)` |
| `metrics.accuracy_score()` | Accuracy | `accuracy_score(y_test, predictions)` |
| `metrics.precision_score()` | Precision | `precision_score(y_test, predictions)` |
| `metrics.recall_score()` | Recall | `recall_score(y_test, predictions)` |
| `metrics.f1_score()` | F1 score | `f1_score(y_test, predictions)` |
| `metrics.mean_squared_error()` | MSE | `mean_squared_error(y_test, predictions)` |
| `metrics.mean_absolute_error()` | MAE | `mean_absolute_error(y_test, predictions)` |
| `metrics.r2_score()` | R2 score | `r2_score(y_test, predictions)` |
| `cross_val_score()` | Cross-validation | `cross_val_score(model, X, y, cv=5)` |
| `GridSearchCV()` | Grid search | `grid = GridSearchCV(model, param_grid, cv=5)` |
| `RandomizedSearchCV()` | Random search | `search = RandomizedSearchCV(model, param_dist, n_iter=10)` |

---

## Additional Resources

For more detailed information, refer to:

- **MaxFrame Client Documentation**: `references/maxframe-client-docs/`
- **Online API Reference**: https://maxframe.readthedocs.io/en/latest/reference/index.html
- **Source Code**: https://github.com/aliyun/alibabacloud-odps-maxframe-client.git