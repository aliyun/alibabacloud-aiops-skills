# maxframe.dataframe.Series.dt.minute

#### Series.dt.minute

The minutes of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="min")
... )
>>> datetime_series.execute()
0   2000-01-01 00:00:00
1   2000-01-01 00:01:00
2   2000-01-01 00:02:00
dtype: datetime64[ns]
>>> datetime_series.dt.minute.execute()
0    0
1    1
2    2
dtype: int32
```
