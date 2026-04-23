# maxframe.dataframe.Series.dt.nanosecond

#### Series.dt.nanosecond

The nanoseconds of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="ns")
... )
>>> datetime_series.execute()
0   2000-01-01 00:00:00.000000000
1   2000-01-01 00:00:00.000000001
2   2000-01-01 00:00:00.000000002
dtype: datetime64[ns]
>>> datetime_series.dt.nanosecond.execute()
0       0
1       1
2       2
dtype: int32
```
