# maxframe.dataframe.Series.dict.get

#### Series.dict.get(query_key, default_value=None)

Get the value by the key of each dict in the Series.

* **Parameters:**
  * **query_key** (*Any*) – The key to check, must be in the same key type of the dict.
  * **default_value** (*Any* *,* *optional*) – The value to return if the key is not in the dict, by default None.
* **Returns:**
  A Series with the dict value’s data type. The value will be `default_value`
  if the key is not in the dict, or `None` if the dict is None.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`Series.dict.__getitem__`](maxframe.dataframe.Series.dict.__getitem__.md#maxframe.dataframe.Series.dict.__getitem__)
: Get the value by the key of each dict in the Series.

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
>>> s.dict.get("k2", 9).execute()
1       2
2       9
3    <NA>
Name: k2, dtype: int64[pyarrow]
```
