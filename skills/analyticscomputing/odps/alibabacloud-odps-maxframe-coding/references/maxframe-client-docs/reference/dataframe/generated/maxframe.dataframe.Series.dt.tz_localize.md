# maxframe.dataframe.Series.dt.tz_localize

#### Series.dt.tz_localize(\*args, \*\*kwargs)

Localize tz-naive Datetime Array/Index to tz-aware Datetime Array/Index.

This method takes a time zone (tz) naive Datetime Array/Index object
and makes this time zone aware. It does not move the time to another
time zone.

This method can also be used to do the inverse – to create a time
zone unaware object from an aware object. To that end, pass tz=None.

* **Parameters:**
  * **tz** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *pytz.timezone* *,* *dateutil.tz.tzfile* *,* [*datetime.tzinfo*](https://docs.python.org/3/library/datetime.html#datetime.tzinfo) *or* *None*) – Time zone to convert timestamps to. Passing `None` will
    remove the time zone information preserving local time.
  * **ambiguous** ( *'infer'* *,*  *'NaT'* *,* *bool array* *,* *default 'raise'*) – 

    When clocks moved backward due to DST, ambiguous times may arise.
    For example in Central European Time (UTC+01), when going from
    03:00 DST to 02:00 non-DST, 02:30:00 local time occurs both at
    00:30:00 UTC and at 01:30:00 UTC. In such a situation, the
    ambiguous parameter dictates how ambiguous times should be
    handled.
    - ’infer’ will attempt to infer fall dst-transition hours based on
      order
    - bool-ndarray where True signifies a DST time, False signifies a
      non-DST time (note that this flag is only applicable for
      ambiguous times)
    - ’NaT’ will return NaT where there are ambiguous times
    - ’raise’ will raise an AmbiguousTimeError if there are ambiguous
      times.
  * **nonexistent** ( *'shift_forward'* *,*  *'shift_backward* *,*  *'NaT'* *,* *timedelta* *,* *default 'raise'*) – 

    A nonexistent time does not exist in a particular timezone
    where clocks moved forward due to DST.
    - ’shift_forward’ will shift the nonexistent time forward to the
      closest existing time
    - ’shift_backward’ will shift the nonexistent time backward to the
      closest existing time
    - ’NaT’ will return NaT where there are nonexistent times
    - timedelta objects will shift nonexistent times by the timedelta
    - ’raise’ will raise an NonExistentTimeError if there are
      nonexistent times.
* **Returns:**
  Array/Index converted to the specified time zone.
* **Return type:**
  Same type as self
* **Raises:**
  [**TypeError**](https://docs.python.org/3/library/exceptions.html#TypeError) – If the Datetime Array/Index is tz-aware and tz is not None.

#### SEE ALSO
`DatetimeIndex.tz_convert`
: Convert tz-aware DatetimeIndex from one time zone to another.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> tz_naive = md.date_range('2018-03-01 09:00', periods=3)
>>> tz_naive.execute()
DatetimeIndex(['2018-03-01 09:00:00', '2018-03-02 09:00:00',
               '2018-03-03 09:00:00'],
              dtype='datetime64[ns]', freq='D')
```

Localize DatetimeIndex in US/Eastern time zone:

```pycon
>>> tz_aware = tz_naive.tz_localize(tz='US/Eastern')
>>> tz_aware.execute()
DatetimeIndex(['2018-03-01 09:00:00-05:00',
               '2018-03-02 09:00:00-05:00',
               '2018-03-03 09:00:00-05:00'],
              dtype='datetime64[ns, US/Eastern]', freq=None)
```

With the `tz=None`, we can remove the time zone information
while keeping the local time (not converted to UTC):

```pycon
>>> tz_aware.tz_localize(None).execute()
DatetimeIndex(['2018-03-01 09:00:00', '2018-03-02 09:00:00',
               '2018-03-03 09:00:00'],
              dtype='datetime64[ns]', freq=None)
```

Be careful with DST changes. When there is sequential data, pandas can
infer the DST time:

```pycon
>>> s = md.to_datetime(md.Series(['2018-10-28 01:30:00',
...                               '2018-10-28 02:00:00',
...                               '2018-10-28 02:30:00',
...                               '2018-10-28 02:00:00',
...                               '2018-10-28 02:30:00',
...                               '2018-10-28 03:00:00',
...                               '2018-10-28 03:30:00']))
>>> s.dt.tz_localize('CET', ambiguous='infer').execute()
0   2018-10-28 01:30:00+02:00
1   2018-10-28 02:00:00+02:00
2   2018-10-28 02:30:00+02:00
3   2018-10-28 02:00:00+01:00
4   2018-10-28 02:30:00+01:00
5   2018-10-28 03:00:00+01:00
6   2018-10-28 03:30:00+01:00
dtype: datetime64[ns, CET]
```

In some cases, inferring the DST is impossible. In such cases, you can
pass an ndarray to the ambiguous parameter to set the DST explicitly

```pycon
>>> s = md.to_datetime(md.Series(['2018-10-28 01:20:00',
...                               '2018-10-28 02:36:00',
...                               '2018-10-28 03:46:00']))
>>> s.dt.tz_localize('CET', ambiguous=mt.array([True, True, False])).execute()
0   2018-10-28 01:20:00+02:00
1   2018-10-28 02:36:00+02:00
2   2018-10-28 03:46:00+01:00
dtype: datetime64[ns, CET]
```

If the DST transition causes nonexistent times, you can shift these
dates forward or backwards with a timedelta object or ‘shift_forward’
or ‘shift_backwards’.

```pycon
>>> s = md.to_datetime(md.Series(['2015-03-29 02:30:00',
...                               '2015-03-29 03:30:00']))
>>> s.dt.tz_localize('Europe/Warsaw', nonexistent='shift_forward').execute()
0   2015-03-29 03:00:00+02:00
1   2015-03-29 03:30:00+02:00
dtype: datetime64[ns, Europe/Warsaw]
```

```pycon
>>> s.dt.tz_localize('Europe/Warsaw', nonexistent='shift_backward').execute()
0   2015-03-29 01:59:59.999999999+01:00
1   2015-03-29 03:30:00+02:00
dtype: datetime64[ns, Europe/Warsaw]
```

```pycon
>>> s.dt.tz_localize('Europe/Warsaw', nonexistent=md.Timedelta('1h')).execute()
0   2015-03-29 03:30:00+02:00
1   2015-03-29 03:30:00+02:00
dtype: datetime64[ns, Europe/Warsaw]
```
