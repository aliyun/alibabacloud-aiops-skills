# maxframe.dataframe.Series.dt.dayofyear

#### Series.dt.dayofyear

The ordinal day of the year.

### Examples

For Series:

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(["1/1/2020 10:00:00+00:00", "2/1/2020 11:00:00+00:00"])
>>> s = md.to_datetime(s)
>>> s.execute()
0   2020-01-01 10:00:00+00:00
1   2020-02-01 11:00:00+00:00
dtype: datetime64[ns, UTC]
>>> s.dt.dayofyear.execute()
0    1
1   32
dtype: int32
```

For DatetimeIndex:

```pycon
>>> idx = md.DatetimeIndex(["1/1/2020 10:00:00+00:00",
...                         "2/1/2020 11:00:00+00:00"])
>>> idx.dayofyear.execute()
Index([1, 32], dtype='int32')
```
