# maxframe.dataframe.Series.dt.is_quarter_start

#### Series.dt.is_quarter_start

Indicator for whether the date is the first day of a quarter.

* **Returns:**
  **is_quarter_start** – The same type as the original data with boolean values. Series will
  have the same name and index. DatetimeIndex will have the same
  name.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or DatetimeIndex

#### SEE ALSO
[`quarter`](maxframe.dataframe.Series.dt.quarter.md#maxframe.dataframe.Series.dt.quarter)
: Return the quarter of the date.

[`is_quarter_end`](maxframe.dataframe.Series.dt.is_quarter_end.md#maxframe.dataframe.Series.dt.is_quarter_end)
: Similar property for indicating the quarter end.

### Examples

This method is available on Series with datetime values under
the `.dt` accessor, and directly on DatetimeIndex.

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'dates': md.date_range("2017-03-30",
...                   periods=4)})
>>> df.assign(quarter=df.dates.dt.quarter,
...           is_quarter_start=df.dates.dt.is_quarter_start).execute()
       dates  quarter  is_quarter_start
0 2017-03-30        1             False
1 2017-03-31        1             False
2 2017-04-01        2              True
3 2017-04-02        2             False
```

```pycon
>>> idx = md.date_range('2017-03-30', periods=4)
>>> idx.execute()
DatetimeIndex(['2017-03-30', '2017-03-31', '2017-04-01', '2017-04-02'],
              dtype='datetime64[ns]', freq='D')
```

```pycon
>>> idx.is_quarter_start.execute()
array([False, False,  True, False])
```
