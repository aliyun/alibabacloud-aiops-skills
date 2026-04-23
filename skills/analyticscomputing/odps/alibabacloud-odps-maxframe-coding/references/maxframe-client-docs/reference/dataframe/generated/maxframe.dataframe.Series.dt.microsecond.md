# maxframe.dataframe.Series.dt.microsecond

#### Series.dt.microsecond

The microseconds of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="us")
... )
>>> datetime_series.execute()
0   2000-01-01 00:00:00.000000
1   2000-01-01 00:00:00.000001
2   2000-01-01 00:00:00.000002
dtype: datetime64[ns]
>>> datetime_series.dt.microsecond.execute()
0       0
1       1
2       2
dtype: int32
```
