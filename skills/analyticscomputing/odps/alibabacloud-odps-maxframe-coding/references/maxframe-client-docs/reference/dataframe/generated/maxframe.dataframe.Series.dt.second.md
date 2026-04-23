# maxframe.dataframe.Series.dt.second

#### Series.dt.second

The seconds of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="s")
... )
>>> datetime_series.execute()
0   2000-01-01 00:00:00
1   2000-01-01 00:00:01
2   2000-01-01 00:00:02
dtype: datetime64[ns]
>>> datetime_series.dt.second.execute()
0    0
1    1
2    2
dtype: int32
```
