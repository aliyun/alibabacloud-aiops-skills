# maxframe.dataframe.Series.list._\_getitem_\_

#### Series.list.\_\_getitem_\_(query_index)

Get the value by the index of each list in the Series. If the index
is not in the list, raise IndexError.

* **Parameters:**
  **query_index** (*Any*) – The index to check, must be integer.
* **Returns:**
  A Series with the list value’s data type. Return `None` if the list is None.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  [**KeyError**](https://docs.python.org/3/library/exceptions.html#KeyError) – If the index is not in one list.

#### SEE ALSO
`Series.list.get`
: Get the value by the index of each list in the Series.

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
>>> s.list.get(0).execute()
1       1
2       4
3    <NA>
dtype: int64[pyarrow]
```
