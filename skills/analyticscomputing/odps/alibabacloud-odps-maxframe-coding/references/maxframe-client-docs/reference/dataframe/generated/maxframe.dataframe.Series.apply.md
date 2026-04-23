# maxframe.dataframe.Series.apply

#### Series.apply(func, convert_dtype=True, output_type=None, args=(), dtypes=None, dtype=None, name=None, index=None, skip_infer=False, \*\*kwds)

Invoke function on values of Series.

Can be ufunc (a NumPy function that applies to the entire Series)
or a Python function that only works on single values.

* **Parameters:**
  * **func** (*function*) – Python function or NumPy ufunc to apply.
  * **convert_dtype** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Try to find better dtype for elementwise function results. If
    False, leave as dtype=object.
  * **output_type** ( *{'dataframe'* *,*  *'series'}* *,* *default None*) – Specify type of returned object. See Notes for more details.
  * **dtypes** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series) *,* *default None*) – Specify dtypes of returned DataFrames. See Notes for more details.
  * **dtype** ([*numpy.dtype*](https://numpy.org/doc/stable/reference/generated/numpy.dtype.html#numpy.dtype) *,* *default None*) – Specify dtype of returned Series. See Notes for more details.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Specify name of returned Series. See Notes for more details.
  * **index** ([*Index*](maxframe.dataframe.Index.md#maxframe.dataframe.Index) *,* *default None*) – Specify index of returned object. See Notes for more details.
  * **args** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple)) – Positional arguments passed to func after the series value.
  * **skip_infer** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Whether infer dtypes when dtypes or output_type is not specified.
  * **\*\*kwds** – Additional keyword arguments passed to func.
* **Returns:**
  If func returns a Series object the result will be a DataFrame.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`Series.map`](maxframe.dataframe.Series.map.md#maxframe.dataframe.Series.map)
: For element-wise operations.

[`Series.agg`](maxframe.dataframe.Series.agg.md#maxframe.dataframe.Series.agg)
: Only perform aggregating type operations.

[`Series.transform`](maxframe.dataframe.Series.transform.md#maxframe.dataframe.Series.transform)
: Only perform transforming type operations.

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
argument to `apply()`.

```pycon
>>> def square(x):
...     return x ** 2
>>> s.apply(square).execute()
London      400
New York    441
Helsinki    144
dtype: int64
```

Square the values by passing an anonymous function as an
argument to `apply()`.

```pycon
>>> s.apply(lambda x: x ** 2).execute()
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
>>> s.apply(subtract_custom_value, args=(5,)).execute()
London      15
New York    16
Helsinki     7
dtype: int64
```

Define a custom function that takes keyword arguments
and pass these arguments to `apply`.

```pycon
>>> def add_custom_values(x, **kwargs):
...     for month in kwargs:
...         x += kwargs[month]
...     return x
```

```pycon
>>> s.apply(add_custom_values, june=30, july=20, august=25).execute()
London      95
New York    96
Helsinki    87
dtype: int64
```

Create a series with a map type.

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

Define a function that updates the map type with a new key-value pair.

```pycon
>>> def custom_set_item(x):
...     if x is not None:
...         x["k2"] = 10
...     return x
```

```pycon
>>> s.apply(custom_set_item, output_type="series", dtype=dict_(pa.string(), pa.int64())).execute()
1    [('k1', 1), ('k2', 10)]
2    [('k1', 3), ('k2', 10)]
3                       <NA>
dtype: map<string, int64>[pyarrow]
```
