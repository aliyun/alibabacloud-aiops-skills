# maxframe.dataframe.date_range

### maxframe.dataframe.date_range(start=None, end=None, periods=None, freq=None, tz=None, normalize=False, name=None, closed=<no_default>, inclusive=None, chunk_size=None, \*\*kwargs)

Return a fixed frequency DatetimeIndex.

* **Parameters:**
  * **start** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *datetime-like* *,* *optional*) – Left bound for generating dates.
  * **end** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *datetime-like* *,* *optional*) – Right bound for generating dates.
  * **periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – Number of periods to generate.
  * **freq** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *DateOffset* *,* *default 'D'*) – Frequency strings can have multiples, e.g. ‘5H’. See
    [here](https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases) for a list of
    frequency aliases.
  * **tz** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *tzinfo* *,* *optional*) – Time zone name for returning localized DatetimeIndex, for example
    ‘Asia/Hong_Kong’. By default, the resulting DatetimeIndex is
    timezone-naive.
  * **normalize** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Normalize start/end dates to midnight before generating date range.
  * **name** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Name of the resulting DatetimeIndex.
  * **inclusive** ( *{“both”* *,*  *“neither”* *,*  *“left”* *,*  *“right”}* *,* *default “both”*) – Include boundaries; Whether to set each bound as closed or open.
  * **\*\*kwargs** – For compatibility. Has no effect on the result.
* **Returns:**
  **rng**
* **Return type:**
  DatetimeIndex

#### SEE ALSO
`DatetimeIndex`
: An immutable container for datetimes.

`timedelta_range`
: Return a fixed frequency TimedeltaIndex.

`period_range`
: Return a fixed frequency PeriodIndex.

`interval_range`
: Return a fixed frequency IntervalIndex.

### Notes

Of the four parameters `start`, `end`, `periods`, and `freq`,
exactly three must be specified. If `freq` is omitted, the resulting
`DatetimeIndex` will have `periods` linearly spaced elements between
`start` and `end` (closed on both sides).

To learn more about the frequency strings, please see [this link](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases).

### Examples

**Specifying the values**

The next four examples generate the same DatetimeIndex, but vary
the combination of start, end and periods.

Specify start and end, with the default daily frequency.
>>> import maxframe.dataframe as md

```pycon
>>> md.date_range(start='1/1/2018', end='1/08/2018').execute()
DatetimeIndex(['2018-01-01', '2018-01-02', '2018-01-03', '2018-01-04',
               '2018-01-05', '2018-01-06', '2018-01-07', '2018-01-08'],
              dtype='datetime64[ns]', freq='D')
```

Specify start and periods, the number of periods (days).

```pycon
>>> md.date_range(start='1/1/2018', periods=8).execute()
DatetimeIndex(['2018-01-01', '2018-01-02', '2018-01-03', '2018-01-04',
               '2018-01-05', '2018-01-06', '2018-01-07', '2018-01-08'],
              dtype='datetime64[ns]', freq='D')
```

Specify end and periods, the number of periods (days).

```pycon
>>> md.date_range(end='1/1/2018', periods=8).execute()
DatetimeIndex(['2017-12-25', '2017-12-26', '2017-12-27', '2017-12-28',
               '2017-12-29', '2017-12-30', '2017-12-31', '2018-01-01'],
              dtype='datetime64[ns]', freq='D')
```

Specify start, end, and periods; the frequency is generated
automatically (linearly spaced).

```pycon
>>> md.date_range(start='2018-04-24', end='2018-04-27', periods=3).execute()
DatetimeIndex(['2018-04-24 00:00:00', '2018-04-25 12:00:00',
               '2018-04-27 00:00:00'],
              dtype='datetime64[ns]', freq=None)
```

**Other Parameters**

Changed the freq (frequency) to `'M'` (month end frequency).

```pycon
>>> md.date_range(start='1/1/2018', periods=5, freq='M').execute()
DatetimeIndex(['2018-01-31', '2018-02-28', '2018-03-31', '2018-04-30',
               '2018-05-31'],
              dtype='datetime64[ns]', freq='M')
```

Multiples are allowed

```pycon
>>> md.date_range(start='1/1/2018', periods=5, freq='3M').execute()
DatetimeIndex(['2018-01-31', '2018-04-30', '2018-07-31', '2018-10-31',
               '2019-01-31'],
              dtype='datetime64[ns]', freq='3M')
```

freq can also be specified as an Offset object.

```pycon
>>> md.date_range(start='1/1/2018', periods=5, freq=md.offsets.MonthEnd(3)).execute()
DatetimeIndex(['2018-01-31', '2018-04-30', '2018-07-31', '2018-10-31',
               '2019-01-31'],
              dtype='datetime64[ns]', freq='3M')
```

Specify tz to set the timezone.

```pycon
>>> md.date_range(start='1/1/2018', periods=5, tz='Asia/Tokyo').execute()
DatetimeIndex(['2018-01-01 00:00:00+09:00', '2018-01-02 00:00:00+09:00',
               '2018-01-03 00:00:00+09:00', '2018-01-04 00:00:00+09:00',
               '2018-01-05 00:00:00+09:00'],
              dtype='datetime64[ns, Asia/Tokyo]', freq='D')
```

inclusive controls whether to include start and end that are on the
boundary. The default, “both”, includes boundary points on either end.

```pycon
>>> md.date_range(start='2017-01-01', end='2017-01-04', inclusive='both').execute()
DatetimeIndex(['2017-01-01', '2017-01-02', '2017-01-03', '2017-01-04'],
              dtype='datetime64[ns]', freq='D')
```

Use `inclusive='left'` to exclude end if it falls on the boundary.

```pycon
>>> md.date_range(start='2017-01-01', end='2017-01-04', closed='left').execute()
DatetimeIndex(['2017-01-01', '2017-01-02', '2017-01-03'],
              dtype='datetime64[ns]', freq='D')
```

Use `inclusive='right'` to exclude start if it falls on the boundary,
and similarly inclusive=’neither’ will exclude both start and end.

```pycon
>>> md.date_range(start='2017-01-01', end='2017-01-04', closed='right').execute()
DatetimeIndex(['2017-01-02', '2017-01-03', '2017-01-04'],
              dtype='datetime64[ns]', freq='D')
```

#### NOTE
Pandas 1.4.0 or later is required to use `inclusive='neither'`.
Otherwise an error may be raised.
