# maxframe.dataframe.Series.dict._\_getitem_\_

#### Series.dict.\_\_getitem_\_(query_key)

Get the value by the key of each dict in the Series. If the key is not in the dict,
raise KeyError.

* **Parameters:**
  **query_key** (*Any*) – The key to check, must be in the same key type of the dict.
* **Returns:**
  A Series with the dict value’s data type. Return `None` if the dict is None.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If the key is not in one dict.

#### SEE ALSO
[`Series.dict.get`](maxframe.dataframe.Series.dict.get.md#maxframe.dataframe.Series.dict.get)
: Get the value by the key of each dict in the Series with an optional

`default`

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
>>> s.dict["k1"].execute()
1       1
2       3
3    <NA>
Name: k1, dtype: int64[pyarrow]
```
