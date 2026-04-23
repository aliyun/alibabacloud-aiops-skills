# maxframe.dataframe.Series.dict._\_setitem_\_

#### Series.dict.\_\_setitem_\_(query_key, value)

Set the value with the key to each dict of the Series.

* **Parameters:**
  * **query_key** (*Any*) – The key of the value to set to, must be in the same key type of the dict.
  * **value** (*Any*) – The value to set, must be in the same value type of the dict. If the `query_key`
    exists, the value will be replaced. Otherwise, the value will be added. A dict
    will be skipped if it’s `None`.
* **Returns:**
  A Series with the same data type.
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
...     dtype=dict_(pa.string(), pa.int64()),
... )
>>> s.execute()
1    [('k1', 1), ('k2', 2)]
2               [('k1', 3)]
3                      <NA>
dtype: map<string, int64>[pyarrow]
```

```pycon
>>> s.dict["k2"] = 4
>>> s.execute()
1    [('k1', 1), ('k2', 4)]
2    [('k1', 3), ('k2', 4)]
3                      <NA>
dtype: map<string, int64>[pyarrow]
```
