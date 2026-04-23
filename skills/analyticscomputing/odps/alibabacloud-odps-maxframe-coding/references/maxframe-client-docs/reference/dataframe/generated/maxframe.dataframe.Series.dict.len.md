# maxframe.dataframe.Series.dict.len

#### Series.dict.len()

Get the length of each dict of the Series.

* **Returns:**
  A Series with data type `pandas.ArrowDtype(pyarrow.int64)`. Each element
  represents the length of the dict, or `None` if the dict is `None`.
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
>>> s.dict.len().execute()
1       2
2       1
3    <NA>
dtype: int64[pyarrow]
```
