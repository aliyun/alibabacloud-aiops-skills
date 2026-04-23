# maxframe.dataframe.Series.dt.tz_convert

#### Series.dt.tz_convert(\*args, \*\*kwargs)

Convert tz-aware Datetime Array/Index from one time zone to another.

* **Parameters:**
  **tz** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *pytz.timezone* *,* *dateutil.tz.tzfile* *,* [*datetime.tzinfo*](https://docs.python.org/3/library/datetime.html#datetime.tzinfo) *or* *None*) – Time zone for time. Corresponding timestamps would be converted
  to this time zone of the Datetime Array/Index. A tz of None will
  convert to UTC and remove the timezone information.
* **Return type:**
  Array or [Index](maxframe.dataframe.Index.md#maxframe.dataframe.Index)
* **Raises:**
  [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – If Datetime Array/Index is tz-naive.

#### SEE ALSO
`DatetimeIndex.tz`
: A timezone that has a variable offset from UTC.

`DatetimeIndex.tz_localize`
: Localize tz-naive DatetimeIndex to a given time zone, or remove timezone from a tz-aware DatetimeIndex.

### Examples

With the tz parameter, we can change the DatetimeIndex
to other time zones:

```pycon
>>> import maxframe.dataframe as md
>>> dti = md.date_range(start='2014-08-01 09:00',
...                     freq='h', periods=3, tz='Europe/Berlin')
```

```pycon
>>> dti.execute()
DatetimeIndex(['2014-08-01 09:00:00+02:00',
               '2014-08-01 10:00:00+02:00',
               '2014-08-01 11:00:00+02:00'],
              dtype='datetime64[ns, Europe/Berlin]', freq='h')
```

```pycon
>>> dti.tz_convert('US/Central').execute()
DatetimeIndex(['2014-08-01 02:00:00-05:00',
               '2014-08-01 03:00:00-05:00',
               '2014-08-01 04:00:00-05:00'],
              dtype='datetime64[ns, US/Central]', freq='h')
```

With the `tz=None`, we can remove the timezone (after converting
to UTC if necessary):

```pycon
>>> dti = md.date_range(start='2014-08-01 09:00', freq='h',
...                     periods=3, tz='Europe/Berlin')
```

```pycon
>>> dti.execute()
DatetimeIndex(['2014-08-01 09:00:00+02:00',
               '2014-08-01 10:00:00+02:00',
               '2014-08-01 11:00:00+02:00'],
                dtype='datetime64[ns, Europe/Berlin]', freq='h')
```

```pycon
>>> dti.tz_convert(None).execute()
DatetimeIndex(['2014-08-01 07:00:00',
               '2014-08-01 08:00:00',
               '2014-08-01 09:00:00'],
                dtype='datetime64[ns]', freq='h')
```
