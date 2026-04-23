# maxframe.dataframe.Series.dt.days_in_month

#### Series.dt.days_in_month

The number of days in the month.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["1/1/2020 10:00:00+00:00", "2/1/2020 11:00:00+00:00"])
>>> s = md.to_datetime(s)
>>> s.execute()
0   2020-01-01 10:00:00+00:00
1   2020-02-01 11:00:00+00:00
dtype: datetime64[ns, UTC]
>>> s.dt.daysinmonth.execute()
0    31
1    29
dtype: int32
```
