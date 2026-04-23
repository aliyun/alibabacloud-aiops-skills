# maxframe.dataframe.Series.dt.weekday

#### Series.dt.weekday

The day of the week with Monday=0, Sunday=6.

Return the day of the week. It is assumed the week starts on
Monday, which is denoted by 0 and ends on Sunday which is denoted
by 6. This method is available on both Series with datetime
values (using the dt accessor) or DatetimeIndex.

* **Returns:**
  Containing integers indicating the day number.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)

#### SEE ALSO
[`Series.dt.dayofweek`](maxframe.dataframe.Series.dt.dayofweek.md#maxframe.dataframe.Series.dt.dayofweek)
: Alias.

[`Series.dt.weekday`](#maxframe.dataframe.Series.dt.weekday)
: Alias.

[`Series.dt.day_name`](maxframe.dataframe.Series.dt.day_name.md#maxframe.dataframe.Series.dt.day_name)
: Returns the name of the day of the week.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.date_range('2016-12-31', '2017-01-08', freq='D').to_series()
>>> s.dt.dayofweek.execute()
2016-12-31    5
2017-01-01    6
2017-01-02    0
2017-01-03    1
2017-01-04    2
2017-01-05    3
2017-01-06    4
2017-01-07    5
2017-01-08    6
Freq: D, dtype: int32
```
