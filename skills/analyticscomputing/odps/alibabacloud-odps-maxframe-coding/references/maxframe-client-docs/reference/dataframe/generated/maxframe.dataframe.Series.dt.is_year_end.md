# maxframe.dataframe.Series.dt.is_year_end

#### Series.dt.is_year_end

Indicate whether the date is the last day of the year.

* **Returns:**
  The same type as the original data with boolean values. Series will
  have the same name and index. DatetimeIndex will have the same
  name.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or DatetimeIndex

#### SEE ALSO
[`is_year_start`](maxframe.dataframe.Series.dt.is_year_start.md#maxframe.dataframe.Series.dt.is_year_start)
: Similar property indicating the start of the year.

### Examples

This method is available on Series with datetime values under
the `.dt` accessor, and directly on DatetimeIndex.

```pycon
>>> import maxframe.dataframe as md
>>> dates = md.Series(md.date_range("2017-12-30", periods=3))
>>> dates.execute()
0   2017-12-30
1   2017-12-31
2   2018-01-01
dtype: datetime64[ns]
```

```pycon
>>> dates.dt.is_year_end.execute()
0    False
1     True
2    False
dtype: bool
```

```pycon
>>> idx = md.date_range("2017-12-30", periods=3)
>>> idx.execute()
DatetimeIndex(['2017-12-30', '2017-12-31', '2018-01-01'],
              dtype='datetime64[ns]', freq='D')
```

```pycon
>>> idx.is_year_end.execute()
array([False,  True, False])
```
