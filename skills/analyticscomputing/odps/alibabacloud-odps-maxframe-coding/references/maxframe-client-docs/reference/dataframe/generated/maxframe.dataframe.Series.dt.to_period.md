# maxframe.dataframe.Series.dt.to_period

#### Series.dt.to_period(\*args, \*\*kwargs)

Cast to PeriodArray/PeriodIndex at a particular frequency.

Converts DatetimeArray/Index to PeriodArray/PeriodIndex.

* **Parameters:**
  **freq** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *Period* *,* *optional*) – One of pandas’ [period aliases](https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-period-aliases)
  or an Period object. Will be inferred by default.
* **Return type:**
  PeriodArray/PeriodIndex
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – When converting a DatetimeArray/Index with non-regular values,
      so that a frequency cannot be inferred.

#### SEE ALSO
`PeriodIndex`
: Immutable ndarray holding ordinal values.

`DatetimeIndex.to_pydatetime`
: Return DatetimeIndex as object.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({"y": [1, 2, 3]},
...                   index=md.to_datetime(["2000-03-31 00:00:00",
...                                         "2000-05-31 00:00:00",
...                                         "2000-08-31 00:00:00"]))
>>> df.index.to_period("M").execute()
PeriodIndex(['2000-03', '2000-05', '2000-08'],
            dtype='period[M]')
```

Infer the daily frequency

```pycon
>>> idx = md.date_range("2017-01-01", periods=2)
>>> idx.to_period().execute()
PeriodIndex(['2017-01-01', '2017-01-02'],
            dtype='period[D]')
```
