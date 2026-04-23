# maxframe.dataframe.Series.dt.time

#### Series.dt.time

Returns numpy array of [`datetime.time`](https://docs.python.org/3/library/datetime.html#datetime.time) objects.

The time part of the Timestamps.

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
>>> s.dt.time.execute()
0    10:00:00
1    11:00:00
dtype: object
```

For DatetimeIndex:

```pycon
>>> idx = md.DatetimeIndex(["1/1/2020 10:00:00+00:00",
...                         "2/1/2020 11:00:00+00:00"])
>>> idx.time.execute()
array([datetime.time(10, 0), datetime.time(11, 0)], dtype=object)
```
