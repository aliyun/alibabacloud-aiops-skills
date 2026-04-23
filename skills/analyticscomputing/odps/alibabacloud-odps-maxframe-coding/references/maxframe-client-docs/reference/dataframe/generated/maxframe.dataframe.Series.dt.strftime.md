# maxframe.dataframe.Series.dt.strftime

#### Series.dt.strftime(\*args, \*\*kwargs)

Convert to Index using specified date_format.

Return an Index of formatted strings specified by date_format, which
supports the same string format as the python standard library. Details
of the string format can be found in [python string format
doc](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior).

Formats supported by the C strftime API but not by the python string format
doc (such as “%R”, “%r”) are not officially supported and should be
preferably replaced with their supported equivalents (such as “%H:%M”,
“%I:%M:%S %p”).

Note that PeriodIndex support additional directives, detailed in
Period.strftime.

* **Parameters:**
  **date_format** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Date format string (e.g. “%Y-%m-%d”).
* **Returns:**
  NumPy ndarray of formatted strings.
* **Return type:**
  ndarray[[object](https://docs.python.org/3/library/functions.html#object)]

#### SEE ALSO
[`to_datetime`](maxframe.dataframe.to_datetime.md#maxframe.dataframe.to_datetime)
: Convert the given argument to datetime.

`DatetimeIndex.normalize`
: Return DatetimeIndex with times to midnight.

`DatetimeIndex.round`
: Round the DatetimeIndex to the specified freq.

`DatetimeIndex.floor`
: Floor the DatetimeIndex to the specified freq.

`Timestamp.strftime`
: Format a single Timestamp.

`Period.strftime`
: Format a single Period.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> rng = md.date_range(md.Timestamp("2018-03-10 09:00"),
...                     periods=3, freq='s')
>>> rng.strftime('%B %d, %Y, %r').execute()
Index(['March 10, 2018, 09:00:00 AM', 'March 10, 2018, 09:00:01 AM',
       'March 10, 2018, 09:00:02 AM'],
      dtype='object')
```
