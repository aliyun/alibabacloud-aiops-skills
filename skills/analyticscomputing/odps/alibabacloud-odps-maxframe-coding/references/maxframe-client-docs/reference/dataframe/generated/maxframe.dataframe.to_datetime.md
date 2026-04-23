# maxframe.dataframe.to_datetime

### maxframe.dataframe.to_datetime(arg, errors: [str](https://docs.python.org/3/library/stdtypes.html#str) = 'raise', dayfirst: [bool](https://docs.python.org/3/library/functions.html#bool) = False, yearfirst: [bool](https://docs.python.org/3/library/functions.html#bool) = False, utc: [bool](https://docs.python.org/3/library/functions.html#bool) = None, format: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, exact: [bool](https://docs.python.org/3/library/functions.html#bool) = True, unit: [str](https://docs.python.org/3/library/stdtypes.html#str) = None, infer_datetime_format: [bool](https://docs.python.org/3/library/functions.html#bool) = False, origin: [Any](https://docs.python.org/3/library/typing.html#typing.Any) = 'unix', cache: [bool](https://docs.python.org/3/library/functions.html#bool) = True)

Convert argument to datetime.

* **Parameters:**
  * **arg** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*float*](https://docs.python.org/3/library/functions.html#float) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *datetime* *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* *1-d array* *,* *Series DataFrame/dict-like*) – The object to convert to a datetime.
  * **errors** ( *{'ignore'* *,*  *'raise'* *,*  *'coerce'}* *,* *default 'raise'*) – 
    - If ‘raise’, then invalid parsing will raise an exception.
    - If ‘coerce’, then invalid parsing will be set as NaT.
    - If ‘ignore’, then invalid parsing will return the input.
  * **dayfirst** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Specify a date parse order if arg is str or its list-likes.
    If True, parses dates with the day first, eg 10/11/12 is parsed as
    2012-11-10.
    Warning: dayfirst=True is not strict, but will prefer to parse
    with day first (this is a known bug, based on dateutil behavior).
  * **yearfirst** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – 

    Specify a date parse order if arg is str or its list-likes.
    - If True parses dates with the year first, eg 10/11/12 is parsed as
      2010-11-12.
    - If both dayfirst and yearfirst are True, yearfirst is preceded (same
      as dateutil).

    Warning: yearfirst=True is not strict, but will prefer to parse
    with year first (this is a known bug, based on dateutil behavior).
  * **utc** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default None*) – Return UTC DatetimeIndex if True (converting any tz-aware
    datetime.datetime objects as well).
  * **format** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – The strftime to parse time, eg “%d/%m/%Y”, note that “%f” will parse
    all the way up to nanoseconds.
    See strftime documentation for more information on choices:
    [https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior).
  * **exact** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *True by default*) – Behaves as:
    - If True, require an exact format match.
    - If False, allow the format to match anywhere in the target string.
  * **unit** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 'ns'*) – The unit of the arg (D,s,ms,us,ns) denote the unit, which is an
    integer or float number. This will be based off the origin.
    Example, with unit=’ms’ and origin=’unix’ (the default), this
    would calculate the number of milliseconds to the unix epoch start.
  * **infer_datetime_format** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True and no format is given, attempt to infer the format of the
    datetime strings, and if it can be inferred, switch to a faster
    method of parsing them. In some cases this can increase the parsing
    speed by ~5-10x.
  * **origin** (*scalar* *,* *default 'unix'*) – 

    Define the reference date. The numeric values would be parsed as number
    of units (defined by unit) since this reference date.
    - If ‘unix’ (or POSIX) time; origin is set to 1970-01-01.
    - If ‘julian’, unit must be ‘D’, and origin is set to beginning of
      Julian Calendar. Julian day number 0 is assigned to the day starting
      at noon on January 1, 4713 BC.
    - If Timestamp convertible, origin is set to Timestamp identified by
      origin.
  * **cache** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True, use a cache of unique, converted dates to apply the datetime
    conversion. May produce significant speed-up when parsing duplicate
    date strings, especially ones with timezone offsets. The cache is only
    used when there are at least 50 values. The presence of out-of-bounds
    values will render the cache unusable and may slow down parsing.
* **Returns:**
  If parsing succeeded.
  Return type depends on input:
  - list-like: DatetimeIndex
  - Series: Series of datetime64 dtype
  - scalar: Timestamp

  In case when it is not possible to return designated types (e.g. when
  any element of input is before Timestamp.min or after Timestamp.max)
  return will have datetime.datetime type (or corresponding
  array/Series).
* **Return type:**
  datetime

#### SEE ALSO
[`DataFrame.astype`](maxframe.dataframe.DataFrame.astype.md#maxframe.dataframe.DataFrame.astype)
: Cast argument to a specified dtype.

`to_timedelta`
: Convert argument to timedelta.

`convert_dtypes`
: Convert dtypes.

### Examples

Assembling a datetime from multiple columns of a DataFrame. The keys can be
common abbreviations like [‘year’, ‘month’, ‘day’, ‘minute’, ‘second’,
‘ms’, ‘us’, ‘ns’]) or plurals of the same

```pycon
>>> import maxframe.dataframe as md
```

```pycon
>>> df = md.DataFrame({'year': [2015, 2016],
...                    'month': [2, 3],
...                    'day': [4, 5]})
>>> md.to_datetime(df).execute()
0   2015-02-04
1   2016-03-05
dtype: datetime64[ns]
```

If a date does not meet the [timestamp limitations](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-timestamp-limits), passing errors=’ignore’
will return the original input instead of raising any exception.

Passing errors=’coerce’ will force an out-of-bounds date to NaT,
in addition to forcing non-dates (or non-parseable dates) to NaT.

```pycon
>>> md.to_datetime('13000101', format='%Y%m%d', errors='ignore').execute()
datetime.datetime(1300, 1, 1, 0, 0)
>>> md.to_datetime('13000101', format='%Y%m%d', errors='coerce').execute()
NaT
```

Passing infer_datetime_format=True can often-times speedup a parsing
if its not an ISO8601 format exactly, but in a regular format.

```pycon
>>> s = md.Series(['3/11/2000', '3/12/2000', '3/13/2000'] * 1000)
>>> s.head().execute()
0    3/11/2000
1    3/12/2000
2    3/13/2000
3    3/11/2000
4    3/12/2000
dtype: object
```

Using a unix epoch time

```pycon
>>> md.to_datetime(1490195805, unit='s').execute()
Timestamp('2017-03-22 15:16:45')
>>> md.to_datetime(1490195805433502912, unit='ns').execute()
Timestamp('2017-03-22 15:16:45.433502912')
```

#### WARNING
For float arg, precision rounding might happen. To prevent
unexpected behavior use a fixed-width exact type.

Using a non-unix epoch origin

```pycon
>>> md.to_datetime([1, 2, 3], unit='D',
...                origin=md.Timestamp('1960-01-01')).execute()
DatetimeIndex(['1960-01-02', '1960-01-03', '1960-01-04'], dtype='datetime64[ns]', freq=None)
```
