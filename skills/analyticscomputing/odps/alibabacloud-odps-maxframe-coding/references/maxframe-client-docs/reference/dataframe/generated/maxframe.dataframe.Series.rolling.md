# maxframe.dataframe.Series.rolling

#### Series.rolling(window, min_periods=None, center=False, win_type=None, on=None, axis=0, closed=None)

Provide rolling window calculations.

* **Parameters:**
  * **window** ([*int*](https://docs.python.org/3/library/functions.html#int) *, or* *offset*) – Size of the moving window. This is the number of observations used for
    calculating the statistic. Each window will be a fixed size.
    If its an offset then this will be the time period of each window. Each
    window will be a variable sized based on the observations included in
    the time-period. This is only valid for datetimelike indexes. This is
    new in 0.19.0
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Minimum number of observations in window required to have a value
    (otherwise result is NA). For a window that is specified by an offset,
    min_periods will default to 1. Otherwise, min_periods will default
    to the size of the window.
  * **center** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – Set the labels at the center of the window.
  * **win_type** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Provide a window type. If `None`, all points are evenly weighted.
    See the notes below for further information.
  * **on** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – For a DataFrame, a datetime-like column on which to calculate the rolling
    window, rather than the DataFrame’s index. Provided integer column is
    ignored and excluded from result since an integer index is not used to
    calculate the rolling window.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 0*)
  * **closed** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – Make the interval closed on the ‘right’, ‘left’, ‘both’ or
    ‘neither’ endpoints.
    For offset-based windows, it defaults to ‘right’.
    For fixed windows, defaults to ‘both’. Remaining cases not implemented
    for fixed windows.
* **Return type:**
  a Window or Rolling sub-classed for the particular operation

#### SEE ALSO
[`expanding`](maxframe.dataframe.Series.expanding.md#maxframe.dataframe.Series.expanding)
: Provides expanding transformations.

[`ewm`](maxframe.dataframe.Series.ewm.md#maxframe.dataframe.Series.ewm)
: Provides exponential weighted functions.

### Notes

By default, the result is set to the right edge of the window. This can be
changed to the center of the window by setting `center=True`.
To learn more about the offsets & frequency strings, please see [this link](http://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases).

The recognized win_types are:
\* `boxcar`
\* `triang`
\* `blackman`
\* `hamming`
\* `bartlett`
\* `parzen`
\* `bohman`
\* `blackmanharris`
\* `nuttall`
\* `barthann`
\* `kaiser` (needs beta)
\* `gaussian` (needs std)
\* `general_gaussian` (needs power, width)
\* `slepian` (needs width)
\* `exponential` (needs tau), center is set to None.

If `win_type=None` all points are evenly weighted. To learn more about
different window types see [scipy.signal window functions](https://docs.scipy.org/doc/scipy/reference/signal.html#window-functions).

### Examples

```pycon
>>> import numpy as np
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'B': [0, 1, 2, np.nan, 4]})
>>> df.execute()
     B
0  0.0
1  1.0
2  2.0
3  NaN
4  4.0
```

Rolling sum with a window length of 2, using the ‘triang’
window type.

```pycon
>>> df.rolling(2, win_type='triang').sum().execute()
     B
0  NaN
1  0.5
2  1.5
3  NaN
4  NaN
```

Rolling sum with a window length of 2, min_periods defaults
to the window length.

```pycon
>>> df.rolling(2).sum().execute()
     B
0  NaN
1  1.0
2  3.0
3  NaN
4  NaN
```

Same as above, but explicitly set the min_periods

```pycon
>>> df.rolling(2, min_periods=1).sum().execute()
     B
0  0.0
1  1.0
2  3.0
3  2.0
4  4.0
```

A ragged (meaning not-a-regular frequency), time-indexed DataFrame

```pycon
>>> df = md.DataFrame({'B': [0, 1, 2, np.nan, 4]},
>>>                   index = [md.Timestamp('20130101 09:00:00'),
>>>                            md.Timestamp('20130101 09:00:02'),
>>>                            md.Timestamp('20130101 09:00:03'),
>>>                            md.Timestamp('20130101 09:00:05'),
>>>                            md.Timestamp('20130101 09:00:06')])
>>> df.execute()
                       B
2013-01-01 09:00:00  0.0
2013-01-01 09:00:02  1.0
2013-01-01 09:00:03  2.0
2013-01-01 09:00:05  NaN
2013-01-01 09:00:06  4.0
```

Contrasting to an integer rolling window, this will roll a variable
length window corresponding to the time period.
The default for min_periods is 1.

```pycon
>>> df.rolling('2s').sum().execute()
                       B
2013-01-01 09:00:00  0.0
2013-01-01 09:00:02  1.0
2013-01-01 09:00:03  3.0
2013-01-01 09:00:05  NaN
2013-01-01 09:00:06  4.0
```
