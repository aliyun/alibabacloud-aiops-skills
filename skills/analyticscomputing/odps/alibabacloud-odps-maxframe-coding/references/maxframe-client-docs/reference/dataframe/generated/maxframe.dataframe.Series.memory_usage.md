# maxframe.dataframe.Series.memory_usage

#### Series.memory_usage(index=True, deep=False)

Return the memory usage of the Series.

The memory usage can optionally include the contribution of
the index and of elements of object dtype.

* **Parameters:**
  * **index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Specifies whether to include the memory usage of the Series index.
  * **deep** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, introspect the data deeply by interrogating
    object dtypes for system-level memory consumption, and include
    it in the returned value.
* **Returns:**
  Bytes of memory consumed.
* **Return type:**
  [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`numpy.ndarray.nbytes`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.nbytes.html#numpy.ndarray.nbytes)
: Total bytes consumed by the elements of the array.

[`DataFrame.memory_usage`](maxframe.dataframe.DataFrame.memory_usage.md#maxframe.dataframe.DataFrame.memory_usage)
: Bytes consumed by a DataFrame.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(range(3))
>>> s.memory_usage().execute()
152
```

Not including the index gives the size of the rest of the data, which
is necessarily smaller:

```pycon
>>> s.memory_usage(index=False).execute()
24
```

The memory footprint of object values is ignored by default:

```pycon
>>> s = md.Series(["a", "b"])
>>> s.values.execute()
array(['a', 'b'], dtype=object)
```

```pycon
>>> s.memory_usage().execute()
144
```

```pycon
>>> s.memory_usage(deep=True).execute()
260
```
