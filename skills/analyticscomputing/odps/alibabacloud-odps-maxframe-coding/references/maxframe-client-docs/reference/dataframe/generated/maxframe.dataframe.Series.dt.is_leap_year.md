# maxframe.dataframe.Series.dt.is_leap_year

#### Series.dt.is_leap_year

Boolean indicator if the date belongs to a leap year.

A leap year is a year, which has 366 days (instead of 365) including
29th of February as an intercalary day.
Leap years are years which are multiples of four with the exception
of years divisible by 100 but not by 400.

* **Returns:**
  Booleans indicating if dates belong to a leap year.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or ndarray

### Examples

This method is available on Series with datetime values under
the `.dt` accessor, and directly on DatetimeIndex.

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.date_range("2012-01-01", "2015-01-01", freq="YE")
>>> idx.execute()
DatetimeIndex(['2012-12-31', '2013-12-31', '2014-12-31'],
              dtype='datetime64[ns]', freq='YE-DEC')
>>> idx.is_leap_year.execute()
array([ True, False, False])
```

```pycon
>>> dates_series = md.Series(idx)
>>> dates_series.execute()
0   2012-12-31
1   2013-12-31
2   2014-12-31
dtype: datetime64[ns]
>>> dates_series.dt.is_leap_year.execute()
0     True
1    False
2    False
dtype: bool
```
