# maxframe.dataframe.Series.dt.month

#### Series.dt.month

The month as January=1, December=12.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="ME")
... )
>>> datetime_series.execute()
0   2000-01-31
1   2000-02-29
2   2000-03-31
dtype: datetime64[ns]
>>> datetime_series.dt.month.execute()
0    1
1    2
2    3
dtype: int32
```
