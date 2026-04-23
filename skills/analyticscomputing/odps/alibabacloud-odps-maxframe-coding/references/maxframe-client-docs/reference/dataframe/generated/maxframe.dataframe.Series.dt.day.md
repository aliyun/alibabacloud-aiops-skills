# maxframe.dataframe.Series.dt.day

#### Series.dt.day

The day of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="D")
... )
>>> datetime_series.execute()
0   2000-01-01
1   2000-01-02
2   2000-01-03
dtype: datetime64[ns]
>>> datetime_series.dt.day.execute()
0    1
1    2
2    3
dtype: int32
```
