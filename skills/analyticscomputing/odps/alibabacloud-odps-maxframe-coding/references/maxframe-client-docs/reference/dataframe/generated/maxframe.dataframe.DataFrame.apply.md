# maxframe.dataframe.DataFrame.apply

#### DataFrame.apply(func, axis=0, raw=False, result_type=None, args=(), dtypes=None, dtype=None, name=None, output_type=None, index=None, elementwise=None, skip_infer=False, \*\*kwds)

Apply a function along an axis of the DataFrame.

Objects passed to the function are Series objects whose index is
either the DataFrame’s index (`axis=0`) or the DataFrame’s columns
(`axis=1`). By default (`result_type=None`), the final return type
is inferred from the return type of the applied function. Otherwise,
it depends on the result_type argument.

* **Parameters:**
  * **func** (*function*) – Function to apply to each column or row.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – 

    Axis along which the function is applied:
    * 0 or ‘index’: apply function to each column.
    * 1 or ‘columns’: apply function to each row.
  * **raw** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – 

    Determines if row or column is passed as a Series or ndarray object:
    * `False` : passes each row or column as a Series to the
      function.
    * `True` : the passed function will receive ndarray objects
      instead.
      If you are just applying a NumPy reduction function this will
      achieve much better performance.
  * **result_type** ( *{'expand'* *,*  *'reduce'* *,*  *'broadcast'* *,* *None}* *,* *default None*) – 

    These only act when `axis=1` (columns):
    * ’expand’ : list-like results will be turned into columns.
    * ’reduce’ : returns a Series if possible rather than expanding
      list-like results. This is the opposite of ‘expand’.
    * ’broadcast’ : results will be broadcast to the original shape
      of the DataFrame, the original index and columns will be
      retained.

    The default behaviour (None) depends on the return value of the
    applied function: list-like results will be returned as a Series
    of those. However if the apply function returns a Series these
    are expanded to columns.
  * **output_type** ( *{'dataframe'* *,*  *'series'}* *,* *default None*) – Specify type of returned object. See Notes for more details.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. See Notes for more details.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of returned Series. See Notes for more details.
  * **index** ([*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index) *,* *default None*) – Specify index of returned object. See Notes for more details.
  * **elementwise** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – 

    Specify whether `func` is an elementwise function:
    * `False` : The function is not elementwise. MaxFrame will try
      concatenating chunks in rows (when `axis=0`) or in columns
      (when `axis=1`) and then apply `func` onto the concatenated
      chunk. The concatenation step can cause extra latency.
    * `True` : The function is elementwise. MaxFrame will apply
      `func` to original chunks. This will not introduce extra
      concatenation step and reduce overhead.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **args** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple)) – Positional arguments to pass to func in addition to the
    array/series.
  * **\*\*kwds** – Additional keyword arguments to pass as keywords arguments to
    func.
* **Returns:**
  Result of applying `func` along the given axis of the
  DataFrame.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.applymap`](maxframe.dataframe.DataFrame.applymap.md#maxframe.dataframe.DataFrame.applymap)
: For elementwise operations.

[`DataFrame.aggregate`](maxframe.dataframe.DataFrame.aggregate.md#maxframe.dataframe.DataFrame.aggregate)
: Only perform aggregating type operations.

[`DataFrame.transform`](maxframe.dataframe.DataFrame.transform.md#maxframe.dataframe.DataFrame.transform)
: Only perform transforming type operations.

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

Using a reducing function on either axis

```pycon
>>> df.apply(np.sum, axis=0).execute()
A    12
B    27
dtype: int64
```

```pycon
>>> df.apply(lambda row: int(np.sum(row)), axis=1).execute()
0    13
1    13
2    13
dtype: int64
```

Passing `result_type='expand'` will expand list-like results
to columns of a Dataframe

```pycon
>>> df.apply(lambda x: [1, 2], axis=1, result_type='expand').execute()
   0  1
0  1  2
1  1  2
2  1  2
```

Returning a Series inside the function is similar to passing
`result_type='expand'`. The resulting column names
will be the Series index.

```pycon
>>> df.apply(lambda x: pd.Series([1, 2], index=['foo', 'bar']), axis=1).execute()
   foo  bar
0    1    2
1    1    2
2    1    2
```

Passing `result_type='broadcast'` will ensure the same shape
result, whether list-like or scalar is returned by the function,
and broadcast it along the axis. The resulting column names will
be the originals.

```pycon
>>> df.apply(lambda x: [1, 2], axis=1, result_type='broadcast').execute()
   A  B
0  1  2
1  1  2
2  1  2
```

Create a dataframe with a map type.

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

Define a function that updates the map type with a new key-value pair.

```pycon
>>> def custom_set_item(x):
...     if x["A"] is not None:
...         x["A"]["k2"] = 10
...     return x
```

```pycon
>>> df.apply(
...     custom_set_item,
...     axis=1,
...     output_type="dataframe",
...     dtypes=df.dtypes.copy(),
... ).execute()
                         A  B
1  [('k1', 1), ('k2', 10)]  A
2  [('k1', 3), ('k2', 10)]  B
3                     <NA>  C
```
