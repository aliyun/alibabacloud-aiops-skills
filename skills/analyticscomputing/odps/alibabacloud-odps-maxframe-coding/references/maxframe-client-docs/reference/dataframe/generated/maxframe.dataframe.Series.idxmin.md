# maxframe.dataframe.Series.idxmin

#### Series.idxmin(axis=0, skipna=True)

Return the row label of the minimum value.

If multiple values equal the minimum, the first row label with that
value is returned.

* **Parameters:**
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0*) – For compatibility with DataFrame.idxmin. Redundant for application
    on Series.
  * **skipna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Exclude NA/null values. If the entire Series is NA, the result
    will be NA.
  * **\*args** – Additional arguments and keywords have no effect but might be
    accepted for compatibility with NumPy.
  * **\*\*kwargs** – Additional arguments and keywords have no effect but might be
    accepted for compatibility with NumPy.
* **Returns:**
  Label of the minimum value.
* **Return type:**
  [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – If the Series is empty.

#### SEE ALSO
[`numpy.argmin`](https://numpy.org/doc/stable/reference/generated/numpy.argmin.html#numpy.argmin)
: Return indices of the minimum values along the given axis.

[`DataFrame.idxmin`](maxframe.dataframe.DataFrame.idxmin.md#maxframe.dataframe.DataFrame.idxmin)
: Return index of first occurrence of minimum over requested axis.

[`Series.idxmin`](#maxframe.dataframe.Series.idxmin)
: Return index *label* of the first occurrence of minimum of values.

### Notes

This method is the Series version of `ndarray.argmin`. This method
returns the label of the minimum, while `ndarray.argmin` returns
the position. To get the position, use `series.values.argmin()`.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(data=[1, None, 4, 3, 4],
...               index=['A', 'B', 'C', 'D', 'E'])
>>> s.execute()
A    1.0
B    NaN
C    4.0
D    3.0
E    4.0
dtype: float64
```

```pycon
>>> s.idxmin().execute()
'C'
```

If skipna is False and there is an NA value in the data,
the function returns `nan`.

```pycon
>>> s.idxmin(skipna=False).execute()
nan
```
