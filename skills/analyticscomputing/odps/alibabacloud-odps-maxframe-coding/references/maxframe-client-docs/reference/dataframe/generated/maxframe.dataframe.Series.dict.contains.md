# maxframe.dataframe.Series.dict.contains

#### Series.dict.contains(query_key)

Check whether the key is in each dict of the Series.

* **Parameters:**
  **query_key** (*Any*) – The key to check, must be in the same key type of the dict.
* **Returns:**
  A Series with data type `pandas.ArrowDtype(pyarrow.bool_)`. The value will
  be `True` if the key is in the dict, `False` otherwise, or `None` if the
  dict is None.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

Create a series with dict type data.

```pycon
>>> import maxframe.dataframe as md
>>> import pyarrow as pa
>>> from maxframe.lib.dtypes_extension import dict_
>>> s = md.Series(
...     data=[[("k1", 1), ("k2", 2)], [("k1", 3)], None],
...     index=[1, 2, 3],
...     dtype=map_(pa.string(), pa.int64()),
... )
>>> s.execute()
1    [('k1', 1), ('k2', 2)]
2               [('k1', 3)]
3                      <NA>
dtype: map<string, int64>[pyarrow]
```

```pycon
>>> s.dict.contains("k2").execute()
1     True
2    False
3     <NA>
dtype: bool[pyarrow]
```
