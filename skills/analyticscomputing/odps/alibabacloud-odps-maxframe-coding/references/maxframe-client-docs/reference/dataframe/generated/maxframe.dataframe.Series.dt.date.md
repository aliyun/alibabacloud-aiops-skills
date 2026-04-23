# maxframe.dataframe.Series.dt.date

#### Series.dt.date

Returns numpy array of python [`datetime.date`](https://docs.python.org/3/library/datetime.html#datetime.date) objects.

Namely, the date part of Timestamps without time and
timezone information.

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
>>> s.dt.date.execute()
0    2020-01-01
1    2020-02-01
dtype: object
```

For DatetimeIndex:

```pycon
>>> idx = md.DatetimeIndex(["1/1/2020 10:00:00+00:00",
...                         "2/1/2020 11:00:00+00:00"])
>>> idx.date.execute()
array([datetime.date(2020, 1, 1), datetime.date(2020, 2, 1)], dtype=object)
```
