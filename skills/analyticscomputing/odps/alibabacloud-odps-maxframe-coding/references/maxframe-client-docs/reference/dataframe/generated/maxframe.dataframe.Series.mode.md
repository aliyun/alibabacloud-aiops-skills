# maxframe.dataframe.Series.mode

#### Series.mode(dropna=True, combine_size=None)

Return the mode(s) of the Series.

The mode is the value that appears most often. There can be multiple modes.

Always returns Series even if only one value is returned.

* **Parameters:**
  **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Don’t consider counts of NaN/NaT.
* **Returns:**
  Modes of the Series in sorted order.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series([2, 4, 2, 2, 4, None])
>>> s.mode().execute()
0    2.0
dtype: float64
```

More than one mode:

```pycon
>>> s = md.Series([2, 4, 8, 2, 4, None])
>>> s.mode().execute()
0    2.0
1    4.0
dtype: float64
```

With and without considering null value:

```pycon
>>> s = md.Series([2, 4, None, None, 4, None])
>>> s.mode(dropna=False).execute()
0   NaN
dtype: float64
>>> s = md.Series([2, 4, None, None, 4, None])
>>> s.mode().execute()
0    4.0
dtype: float64
```
