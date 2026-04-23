# maxframe.dataframe.Series.dt.normalize

#### Series.dt.normalize(\*args, \*\*kwargs)

Convert times to midnight.

The time component of the date-time is converted to midnight i.e.
00:00:00. This is useful in cases, when the time does not matter.
Length is unaltered. The timezones are unaffected.

This method is available on Series with datetime values under
the `.dt` accessor, and directly on Datetime Array/Index.

* **Returns:**
  The same type as the original data. Series will have the same
  name and index. DatetimeIndex will have the same name.
* **Return type:**
  DatetimeArray, DatetimeIndex or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`floor`](maxframe.dataframe.Series.dt.floor.md#maxframe.dataframe.Series.dt.floor)
: Floor the datetimes to the specified freq.

[`ceil`](maxframe.dataframe.Series.dt.ceil.md#maxframe.dataframe.Series.dt.ceil)
: Ceil the datetimes to the specified freq.

[`round`](maxframe.dataframe.Series.dt.round.md#maxframe.dataframe.Series.dt.round)
: Round the datetimes to the specified freq.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> idx = md.date_range(start='2014-08-01 10:00', freq='h',
...                     periods=3, tz='Asia/Calcutta')
>>> idx.execute()
DatetimeIndex(['2014-08-01 10:00:00+05:30',
               '2014-08-01 11:00:00+05:30',
               '2014-08-01 12:00:00+05:30'],
                dtype='datetime64[ns, Asia/Calcutta]', freq='h')
>>> idx.normalize().execute()
DatetimeIndex(['2014-08-01 00:00:00+05:30',
               '2014-08-01 00:00:00+05:30',
               '2014-08-01 00:00:00+05:30'],
               dtype='datetime64[ns, Asia/Calcutta]', freq=None)
```
