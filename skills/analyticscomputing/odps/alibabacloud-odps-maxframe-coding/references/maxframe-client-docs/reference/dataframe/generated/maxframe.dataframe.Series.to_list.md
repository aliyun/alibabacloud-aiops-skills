# maxframe.dataframe.Series.to_list

#### Series.to_list(batch_size=10000, session=None)

Return a list of the values.

These are each a scalar type, which is a Python scalar
(for str, int, float) or a pandas scalar
(for Timestamp/Timedelta/Interval/Period)

* **Return type:**
  [list](https://docs.python.org/3/library/stdtypes.html#list)

#### SEE ALSO
[`numpy.ndarray.tolist`](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.tolist.html#numpy.ndarray.tolist)
: Return the array as an a.ndim-levels deep nested list of Python scalars.

### Examples

For Series

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([1, 2, 3])
>>> s.to_list()
[1, 2, 3]
```

For Index:

```pycon
>>> idx = md.Index([1, 2, 3])
>>> idx.execute()
Index([1, 2, 3], dtype='int64')
```

```pycon
>>> idx.to_list()
[1, 2, 3]
```
