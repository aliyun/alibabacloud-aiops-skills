# maxframe.dataframe.Series.dt.round

#### Series.dt.round(\*args, \*\*kwargs)

Perform round operation on the data to the specified freq.

* **Parameters:**
  * **freq** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* *Offset*) – The frequency level to round the index to. Must be a fixed
    frequency like ‘S’ (second) not ‘ME’ (month end). See
    [frequency aliases](https://pandas.pydata.org/docs/user_guide/timeseries.html#timeseries-offset-aliases) for
    a list of possible freq values.
  * **ambiguous** ( *'infer'* *,* *bool-ndarray* *,*  *'NaT'* *,* *default 'raise'*) – 

    Only relevant for DatetimeIndex:
    - ’infer’ will attempt to infer fall dst-transition hours based on
      order
    - bool-ndarray where True signifies a DST time, False designates
      a non-DST time (note that this flag is only applicable for
      ambiguous times)
    - ’NaT’ will return NaT where there are ambiguous times
    - ’raise’ will raise an AmbiguousTimeError if there are ambiguous
      times.
  * **nonexistent** ( *'shift_forward'* *,*  *'shift_backward'* *,*  *'NaT'* *,* *timedelta* *,* *default 'raise'*) – 

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
  Index of the same type for a DatetimeIndex or TimedeltaIndex,
  or a Series with the same index for a Series.
* **Return type:**
  DatetimeIndex, TimedeltaIndex, or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)
* **Raises:**
  **ValueError if the freq cannot be converted.** – 

### Notes

If the timestamps have a timezone, rounding will take place relative to the
local (“wall”) time and re-localized to the same timezone. When rounding
near daylight savings time, use `nonexistent` and `ambiguous` to
control the re-localization behavior.

### Examples

**DatetimeIndex**

```pycon
>>> import maxframe.dataframe as md
>>> rng = md.date_range('1/1/2018 11:59:00', periods=3, freq='min')
>>> rng.execute()
DatetimeIndex(['2018-01-01 11:59:00', '2018-01-01 12:00:00',
               '2018-01-01 12:01:00'],
              dtype='datetime64[ns]', freq='min')
>>> rng.round('h').execute()
DatetimeIndex(['2018-01-01 12:00:00', '2018-01-01 12:00:00',
               '2018-01-01 12:00:00'],
              dtype='datetime64[ns]', freq=None)
```

**Series**

```pycon
>>> md.Series(rng).dt.round("h").execute()
0   2018-01-01 12:00:00
1   2018-01-01 12:00:00
2   2018-01-01 12:00:00
dtype: datetime64[ns]
```

When rounding near a daylight savings time transition, use `ambiguous` or
`nonexistent` to control how the timestamp should be re-localized.

```pycon
>>> rng_tz = md.DatetimeIndex(["2021-10-31 03:30:00"], tz="Europe/Amsterdam")
```

```pycon
>>> rng_tz.floor("2h", ambiguous=False).execute()
DatetimeIndex(['2021-10-31 02:00:00+01:00'],
              dtype='datetime64[ns, Europe/Amsterdam]', freq=None)
```

```pycon
>>> rng_tz.floor("2h", ambiguous=True).execute()
DatetimeIndex(['2021-10-31 02:00:00+02:00'],
              dtype='datetime64[ns, Europe/Amsterdam]', freq=None)
```
