# maxframe.dataframe.Series.dt.year

#### Series.dt.year

The year of the datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> datetime_series = md.Series(
...     md.date_range("2000-01-01", periods=3, freq="YE")
... )
>>> datetime_series.execute()
0   2000-12-31
1   2001-12-31
2   2002-12-31
dtype: datetime64[ns]
>>> datetime_series.dt.year.execute()
0    2000
1    2001
2    2002
dtype: int32
```
