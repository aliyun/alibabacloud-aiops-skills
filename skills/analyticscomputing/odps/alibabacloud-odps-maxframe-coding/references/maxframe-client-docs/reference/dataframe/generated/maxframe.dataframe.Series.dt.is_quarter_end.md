# maxframe.dataframe.Series.dt.is_quarter_end

#### Series.dt.is_quarter_end

Indicator for whether the date is the last day of a quarter.

* **Returns:**
  **is_quarter_end** – The same type as the original data with boolean values. Series will
  have the same name and index. DatetimeIndex will have the same
  name.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or DatetimeIndex

#### SEE ALSO
[`quarter`](maxframe.dataframe.Series.dt.quarter.md#maxframe.dataframe.Series.dt.quarter)
: Return the quarter of the date.

[`is_quarter_start`](maxframe.dataframe.Series.dt.is_quarter_start.md#maxframe.dataframe.Series.dt.is_quarter_start)
: Similar property indicating the quarter start.

### Examples

This method is available on Series with datetime values under
the `.dt` accessor, and directly on DatetimeIndex.

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'dates': md.date_range("2017-03-30",
...                    periods=4)})
>>> df.assign(quarter=df.dates.dt.quarter,
...           is_quarter_end=df.dates.dt.is_quarter_end).execute()
       dates  quarter    is_quarter_end
0 2017-03-30        1             False
1 2017-03-31        1              True
2 2017-04-01        2             False
3 2017-04-02        2             False
```

```pycon
>>> idx = md.date_range('2017-03-30', periods=4)
>>> idx.execute()
DatetimeIndex(['2017-03-30', '2017-03-31', '2017-04-01', '2017-04-02'],
              dtype='datetime64[ns]', freq='D')
```

```pycon
>>> idx.is_quarter_end.execute()
array([False,  True, False, False])
```
