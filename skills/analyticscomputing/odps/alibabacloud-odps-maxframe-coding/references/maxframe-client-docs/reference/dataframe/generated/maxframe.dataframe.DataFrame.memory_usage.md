# maxframe.dataframe.DataFrame.memory_usage

#### DataFrame.memory_usage(index=True, deep=False)

Return the memory usage of each column in bytes.

The memory usage can optionally include the contribution of
the index and elements of object dtype.

This value is displayed in DataFrame.info by default. This can be
suppressed by setting `pandas.options.display.memory_usage` to False.

* **Parameters:**
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Specifies whether to include the memory usage of the DataFrame’s
    index in returned Series. If `index=True`, the memory usage of
    the index is the first item in the output.
  * **deep** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, introspect the data deeply by interrogating
    object dtypes for system-level memory consumption, and include
    it in the returned values.
* **Returns:**
  A Series whose index is the original column names and whose values
  is the memory usage of each column in bytes.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`numpy.ndarray.nbytes`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.nbytes.html#numpy.ndarray.nbytes)
: Total bytes consumed by the elements of an ndarray.

[`Series.memory_usage`](maxframe.dataframe.Series.memory_usage.md#maxframe.dataframe.Series.memory_usage)
: Bytes consumed by a Series.

`Categorical`
: Memory-efficient array for string values with many repeated values.

`DataFrame.info`
: Concise summary of a DataFrame.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> dtypes = ['int64', 'float64', 'complex128', 'object', 'bool']
>>> data = dict([(t, mt.ones(shape=5000).astype(t))
...              for t in dtypes])
>>> df = md.DataFrame(data)
>>> df.head().execute()
   int64  float64            complex128  object  bool
0      1      1.0    1.000000+0.000000j       1  True
1      1      1.0    1.000000+0.000000j       1  True
2      1      1.0    1.000000+0.000000j       1  True
3      1      1.0    1.000000+0.000000j       1  True
4      1      1.0    1.000000+0.000000j       1  True
```

```pycon
>>> df.memory_usage().execute()
Index           128
int64         40000
float64       40000
complex128    80000
object        40000
bool           5000
dtype: int64
```

```pycon
>>> df.memory_usage(index=False).execute()
int64         40000
float64       40000
complex128    80000
object        40000
bool           5000
dtype: int64
```

The memory footprint of object dtype columns is ignored by default:

```pycon
>>> df.memory_usage(deep=True).execute()
Index            128
int64          40000
float64        40000
complex128     80000
object        160000
bool            5000
dtype: int64
```

Use a Categorical for efficient storage of an object-dtype column with
many repeated values.

```pycon
>>> df['object'].astype('category').memory_usage(deep=True).execute()
5216
```
