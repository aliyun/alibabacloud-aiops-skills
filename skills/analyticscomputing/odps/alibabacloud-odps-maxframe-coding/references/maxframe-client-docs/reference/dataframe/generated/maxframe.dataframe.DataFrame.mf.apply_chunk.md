# maxframe.dataframe.DataFrame.mf.apply_chunk

#### DataFrame.mf.apply_chunk(func: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Callable](https://docs.python.org/3/library/typing.html#typing.Callable), batch_rows=None, dtypes=None, dtype=None, name=None, output_type=None, index=None, skip_infer=False, args=(), \*\*kwargs)

Apply a function that takes pandas DataFrame and outputs pandas DataFrame/Series.
The pandas DataFrame given to the function is a chunk of the input dataframe, consider as a batch rows.

The objects passed into this function are slices of the original DataFrame, containing at most batch_rows
number of rows and all columns. It is equivalent to merging multiple `df.apply` with `axis=1` inputs and then
passing them into the function for execution, thereby improving performance in specific scenarios. The function
output can be either a DataFrame or a Series. `apply_chunk` will ultimately merge the results into a new
DataFrame or Series.

Don’t expect to receive all rows of the DataFrame in the function, as it depends on the implementation
of MaxFrame and the internal running state of MaxCompute.

* **Parameters:**
  * **func** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *Callable*) – Function to apply to the dataframe chunk.
  * **batch_rows** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Specify expected number of rows in a batch, as well as the len of function input dataframe. When the remaining
    data is insufficient, it may be less than this number.
  * **output_type** ( *{'dataframe'* *,*  *'series'}* *,* *default None*) – Specify type of returned object. See Notes for more details.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. See Notes for more details.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of returned Series. See Notes for more details.
  * **index** ([*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index) *,* *default None*) – Specify index of returned object. See Notes for more details.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **args** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple)) – Positional arguments to pass to `func` in addition to the
    array/series.
  * **\*\*kwds** – Additional keyword arguments to pass as keywords arguments to
    `func`.
* **Returns:**
  Result of applying `func` along the given chunk of the
  DataFrame.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.apply`](maxframe.dataframe.DataFrame.apply.md#maxframe.dataframe.DataFrame.apply)
: For non-batching operations.

[`Series.mf.apply_chunk`](maxframe.dataframe.Series.mf.apply_chunk.md#maxframe.dataframe.Series.mf.apply_chunk)
: Apply function to Series chunk.

### Notes

When deciding output dtypes and shape of the return value, MaxFrame will
try applying `func` onto a mock DataFrame,  and the apply call may
fail. When this happens, you need to specify the type of apply call
(DataFrame or Series) in output_type.

* For DataFrame output, you need to specify a list or a pandas Series
  as `dtypes` of output DataFrame. `index` of output can also be
  specified.
* For Series output, you need to specify `dtype` and `name` of
  output Series.
* For any input with data type `pandas.ArrowDtype(pyarrow.MapType)`, it will always
  be converted to a Python dict. And for any output with this data type, it must be
  returned as a Python dict as well.

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame([[4, 9]] * 3, columns=['A', 'B'])
>>> df.execute()
   A  B
0  4  9
1  4  9
2  4  9
```

Use different batch_rows will collect different dataframe chunk into the function.

For example, when you use `batch_rows=3`, it means that the function will wait until 3 rows are collected.

```pycon
>>> df.mf.apply_chunk(np.sum, batch_rows=3).execute()
A    12
B    27
dtype: int64
```

While, if `batch_rows=2`, the data will be divided into at least two segments. Additionally, if your function
alters the shape of the dataframe, it may result in different outputs.

```pycon
>>> df.mf.apply_chunk(np.sum, batch_rows=2).execute()
A     8
B    18
A     4
B     9
dtype: int64
```

If the function requires some parameters, you can specify them using args or kwargs.

```pycon
>>> def calc(df, x, y):
...    return df * x + y
>>> df.mf.apply_chunk(calc, args=(10,), y=20).execute()
    A    B
0  60  110
1  60  110
2  60  110
```

The batch rows will benefit the actions consume a dataframe, like sklearn predict.
You can easily use sklearn in MaxFrame to perform offline inference, and apply_chunk makes this process more
efficient. The `@with_python_requirements` provides the capability to automatically package and load
dependencies.

Once you rely on some third-party dependencies, MaxFrame may not be able to correctly infer the return type.
Therefore, using `output_type` with `dtype` or `dtypes` is necessary.

```pycon
>>> from maxframe.udf import with_python_requirements
>>> data = {
...     'A': np.random.rand(10),
...     'B': np.random.rand(10)
... }
>>> pd_df = pd.DataFrame(data)
>>> X = pd_df[['A']]
>>> y = pd_df['B']
```

```pycon
>>> from sklearn.model_selection import train_test_split
>>> from sklearn.linear_model import LinearRegression
>>> model = LinearRegression()
>>> model.fit(X, y)
```

```pycon
>>> @with_python_requirements("scikit-learn")
... def predict(df):
...     predict_B = model.predict(df[["A"]])
...     return pd.Series(predict_B, index=df.A.index)
```

```pycon
>>> df.mf.apply_chunk(predict, batch_rows=3, output_type="series", dtype="float", name="predict_B").execute()
0   -0.765025
1   -0.765025
2   -0.765025
Name: predict_B, dtype: float64
```

Create a dataframe with a dict type.

```pycon
>>> import pyarrow as pa
>>> import pandas as pd
>>> from maxframe.lib.dtypes_extension import dict_
>>> col_a = pd.Series(
...     data=[[("k1", 1), ("k2", 2)], [("k1", 3)], None],
...     index=[1, 2, 3],
...     dtype=dict_(pa.string(), pa.int64()),
... )
>>> col_b = pd.Series(
...     data=["A", "B", "C"],
...     index=[1, 2, 3],
... )
>>> df = md.DataFrame({"A": col_a, "B": col_b})
>>> df.execute()
                        A  B
1  [('k1', 1), ('k2', 2)]  A
2             [('k1', 3)]  B
3                    <NA>  C
```

Define a function that updates the map type with a new key-value pair in a batch.

```pycon
>>> def custom_set_item(df):
...     for name, value in df["A"].items():
...         if value is not None:
...             df["A"][name]["x"] = 100
...     return df
```

```pycon
>>> mf.apply_chunk(
...     process,
...     output_type="dataframe",
...     dtypes=md_df.dtypes.copy(),
...     batch_rows=2,
...     skip_infer=True,
...     index=md_df.index,
... )
                                    A  B
1  [('k1', 1), ('k2', 2), ('x', 10))]  A
2              [('k1', 3), ('x', 10)]  B
3                                <NA>  C
```
