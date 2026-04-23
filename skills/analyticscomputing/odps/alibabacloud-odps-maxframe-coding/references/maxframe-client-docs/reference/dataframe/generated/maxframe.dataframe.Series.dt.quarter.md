# maxframe.dataframe.Series.dt.quarter

#### Series.dt.quarter

The quarter of the date.

### Examples

For Series:

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["1/1/2020 10:00:00+00:00", "4/1/2020 11:00:00+00:00"])
>>> s = md.to_datetime(s)
>>> s.execute()
0   2020-01-01 10:00:00+00:00
1   2020-04-01 11:00:00+00:00
dtype: datetime64[ns, UTC]
>>> s.dt.quarter.execute()
0    1
1    2
dtype: int32
```

For DatetimeIndex:

```pycon
>>> idx = md.DatetimeIndex(["1/1/2020 10:00:00+00:00",
...                         "2/1/2020 11:00:00+00:00"])
>>> idx.quarter.execute()
Index([1, 1], dtype='int32')
```
