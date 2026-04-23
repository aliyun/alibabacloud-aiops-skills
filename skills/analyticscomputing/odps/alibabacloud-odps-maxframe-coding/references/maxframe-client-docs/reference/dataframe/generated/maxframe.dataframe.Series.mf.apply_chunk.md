# maxframe.dataframe.Series.mf.apply_chunk

#### Series.mf.apply_chunk(func: [str](https://docs.python.org/3/library/stdtypes.html#str) | [Callable](https://docs.python.org/3/library/typing.html#typing.Callable), batch_rows=None, dtypes=None, dtype=None, name=None, output_type=None, index=None, skip_infer=False, args=(), \*\*kwargs)

Apply a function that takes pandas Series and outputs pandas DataFrame/Series.
The pandas DataFrame given to the function is a chunk of the input series.

The objects passed into this function are slices of the original series, containing at most batch_rows
number of elements. The function output can be either a DataFrame or a Series.
`apply_chunk` will ultimately merge the results into a new DataFrame or Series.

Don’t expect to receive all elements of series in the function, as it depends on the implementation
of MaxFrame and the internal running state of MaxCompute.

Can be ufunc (a NumPy function that applies to the entire Series)
or a Python function that only works on series.

* **Parameters:**
  * **func** (*function*) – Python function or NumPy ufunc to apply.
  * **batch_rows** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Specify expected number of elements in a batch, as well as the len of function input series.
    When the remaining data is insufficient, it may be less than this number.
  * **output_type** ( *{'dataframe'* *,*  *'series'}* *,* *default None*) – Specify type of returned object. See Notes for more details.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. See Notes for more details.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of returned Series. See Notes for more details.
  * **index** ([*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index) *,* *default None*) – Specify index of returned object. See Notes for more details.
  * **args** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple)) – Positional arguments passed to func after the series value.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **\*\*kwds** – Additional keyword arguments passed to func.
* **Returns:**
  If func returns a Series object the result will be a Series, else the result will be a DataFrame.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
`DataFrame.apply_chunk`
: Apply function to DataFrame chunk.

[`Series.apply`](maxframe.dataframe.Series.apply.md#maxframe.dataframe.Series.apply)
: For non-batching operations.

### Notes

When deciding output dtypes and shape of the return value, MaxFrame will
try applying `func` onto a mock Series, and the apply call may fail.
When this happens, you need to specify the type of apply call
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

Create a series with typical summer temperatures for each city.

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([20, 21, 12],
...               index=['London', 'New York', 'Helsinki'])
>>> s.execute()
London      20
New York    21
Helsinki    12
dtype: int64
```

Square the values by defining a function and passing it as an
argument to `apply_chunk()`.

```pycon
>>> def square(x):
...     return x ** 2
>>> s.mf.apply_chunk(square, batch_rows=2).execute()
London      400
New York    441
Helsinki    144
dtype: int64
```

Square the values by passing an anonymous function as an
argument to `apply_chunk()`.

```pycon
>>> s.mf.apply_chunk(lambda x: x**2, batch_rows=2).execute()
London      400
New York    441
Helsinki    144
dtype: int64
```

Define a custom function that needs additional positional
arguments and pass these additional arguments using the
`args` keyword.

```pycon
>>> def subtract_custom_value(x, custom_value):
...     return x - custom_value
```

```pycon
>>> s.mf.apply_chunk(subtract_custom_value, args=(5,), batch_rows=3).execute()
London      15
New York    16
Helsinki     7
dtype: int64
```

Define a custom function that takes keyword arguments
and pass these arguments to `apply_chunk`.

```pycon
>>> def add_custom_values(x, **kwargs):
...     for month in kwargs:
...         x += kwargs[month]
...     return x
```

```pycon
>>> s.mf.apply_chunk(add_custom_values, batch_rows=2, june=30, july=20, august=25).execute()
London      95
New York    96
Helsinki    87
dtype: int64
```

If func return a dataframe, the apply_chunk will return a dataframe as well.

```pycon
>>> def get_dataframe(x):
...     return pd.concat([x, x], axis=1)
```

```pycon
>>> s.mf.apply_chunk(get_dataframe, batch_rows=2).execute()
           0   1
London    20  20
New York  21  21
Helsinki  12  12
```

Provides a dtypes or dtype with name to naming the output schema.

```pycon
>>> s.mf.apply_chunk(
...    get_dataframe,
...    batch_rows=2,
...    dtypes={"A": np.int_, "B": np.int_},
...    output_type="dataframe"
... ).execute()
           A   B
London    20  20
New York  21  21
Helsinki  12  12
```

Create a series with a dict type.

```pycon
>>> import pyarrow as pa
>>> from maxframe.lib.dtypes_extension import dict_
>>> s = md.Series(
...     data=[[("k1", 1), ("k2", 2)], [("k1", 3)], None],
...     index=[1, 2, 3],
...     dtype=dict_(pa.string(), pa.int64()),
... )
>>> s.execute()
1    [('k1', 1), ('k2', 2)]
2               [('k1', 3)]
3                      <NA>
dtype: map<string, int64>[pyarrow]
```

Define a function that updates the map type with a new key-value pair in a batch.

```pycon
>>> def custom_set_item(row):
...     for _, value in row.items():
...         if value is not None:
...             value["x"] = 100
...     return row
```

```pycon
>>> s.mf.apply_chunk(
...     custom_set_item,
...     output_type="series",
...     dtype=s.dtype,
...     batch_rows=2,
...     skip_infer=True,
...     index=s.index,
... ).execute()
1    [('k1', 1), ('k2', 2), ('x', 100)]
2               [('k1', 3), ('x', 100)]
3                                  <NA>
dtype: map<string, int64>[pyarrow]
```
