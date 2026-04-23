# maxframe.dataframe.Series.list.len

#### Series.list.len()

Get the length of each list of the Series.

* **Returns:**
  A Series with data type `pandas.ArrowDtype(pyarrow.int64)`. Each element
  represents the length of the list, or `None` if the list is `None`.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

Create a series with list type data.

```pycon
>>> import maxframe.dataframe as md
>>> import pyarrow as pa
>>> from maxframe.lib.dtypes_extension import list_
>>> s = md.Series(
...     data=[[1, 2, 3], [4, 5, 6], None],
...     index=[1, 2, 3],
...     dtype=list_(pa.int64()),
... )
>>> s.execute()
1    [1, 2, 3]
2    [4, 5, 6]
3         <NA>
dtype: list<int64>[pyarrow]
```

```pycon
>>> s.list.len().execute()
1       2
2       1
3    <NA>
dtype: int64[pyarrow]
```
