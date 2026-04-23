# maxframe.dataframe.Series.dt.to_pydatetime

#### Series.dt.to_pydatetime() → [ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray)

Return the data as an array of [`datetime.datetime`](https://docs.python.org/3/library/datetime.html#datetime.datetime) objects.

#### Deprecated
Deprecated since version 2.1.0: The current behavior of dt.to_pydatetime is deprecated.
In a future version this will return a Series containing python
datetime objects instead of a ndarray.

Timezone information is retained if present.

#### WARNING
Python’s datetime uses microsecond resolution, which is lower than
pandas (nanosecond). The values are truncated.

* **Returns:**
  Object dtype array containing native Python datetime objects.
* **Return type:**
  [numpy.ndarray](https://numpy.org/doc/stable/reference/generated/numpy.ndarray.html#numpy.ndarray)

#### SEE ALSO
[`datetime.datetime`](https://docs.python.org/3/library/datetime.html#datetime.datetime)
: Standard library value for a datetime.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s = md.Series(md.date_range('20180310', periods=2))
>>> s.execute()
0   2018-03-10
1   2018-03-11
dtype: datetime64[ns]
```

```pycon
>>> s.dt.to_pydatetime().execute()
array([datetime.datetime(2018, 3, 10, 0, 0),
       datetime.datetime(2018, 3, 11, 0, 0)], dtype=object)
```

pandas’ nanosecond precision is truncated to microseconds.

```pycon
>>> s = md.Series(md.date_range('20180310', periods=2, freq='ns'))
>>> s.execute()
0   2018-03-10 00:00:00.000000000
1   2018-03-10 00:00:00.000000001
dtype: datetime64[ns]
```

```pycon
>>> s.dt.to_pydatetime().execute()
array([datetime.datetime(2018, 3, 10, 0, 0),
       datetime.datetime(2018, 3, 10, 0, 0)], dtype=object)
```
