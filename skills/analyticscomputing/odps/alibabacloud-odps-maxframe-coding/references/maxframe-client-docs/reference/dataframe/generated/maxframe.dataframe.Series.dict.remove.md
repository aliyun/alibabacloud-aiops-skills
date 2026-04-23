# maxframe.dataframe.Series.dict.remove

#### Series.dict.remove(query_key, ignore_key_error: [bool](https://docs.python.org/3/library/functions.html#bool) = False)

Remove the item by the key from each dict of the Series.

* **Parameters:**
  * **query_key** (*Any*) – The key to remove, must be in the same key type of the dict.
  * **ignore_key_error** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional* *,* *default False*) – When the `query_key` is not in the dict, if `ignore_key_error` is True,
    nothing will happen in the dict. If `ignore_key_error` is `False`, an
    `KeyError` will be raised. If the dict is `None`, returns `None`.
* **Returns:**
  A Series with the same data type. If the dict is `None`.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  **KeyError :** – If the `query_key` is not in one dict and `ignore_key_error` is `False`.

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
>>> s.dict.remove("k2", ignore_key_error=True).execute()
1    [('k1', 1)]
2    [('k1', 3)]
3           <NA>
dtype: map<string, int64>[pyarrow]
```
