# maxframe.dataframe.Series.dt.is_month_start

#### Series.dt.is_month_start

Indicates whether the date is the first day of the month.

* **Returns:**
  For Series, returns a Series with boolean values.
  For DatetimeIndex, returns a boolean array.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or array

#### SEE ALSO
[`is_month_start`](#maxframe.dataframe.Series.dt.is_month_start)
: Return a boolean indicating whether the date is the first day of the month.

[`is_month_end`](maxframe.dataframe.Series.dt.is_month_end.md#maxframe.dataframe.Series.dt.is_month_end)
: Return a boolean indicating whether the date is the last day of the month.

### Examples

This method is available on Series with datetime values under
the `.dt` accessor, and directly on DatetimeIndex.

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(md.date_range("2018-02-27", periods=3))
>>> s.execute()
0   2018-02-27
1   2018-02-28
2   2018-03-01
dtype: datetime64[ns]
>>> s.dt.is_month_start.execute()
0    False
1    False
2    True
dtype: bool
>>> s.dt.is_month_end.execute()
0    False
1    True
2    False
dtype: bool
```

```pycon
>>> idx = md.date_range("2018-02-27", periods=3)
>>> idx.is_month_start.execute()
array([False, False, True])
>>> idx.is_month_end.execute()
array([False, True, False])
```
