# maxframe.dataframe.Series.dt.hour

#### Series.dt.hour

The hours of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="h")
... )
>>> datetime_series.execute()
0   2000-01-01 00:00:00
1   2000-01-01 01:00:00
2   2000-01-01 02:00:00
dtype: datetime64[ns]
>>> datetime_series.dt.hour.execute()
0    0
1    1
2    2
dtype: int32
```
