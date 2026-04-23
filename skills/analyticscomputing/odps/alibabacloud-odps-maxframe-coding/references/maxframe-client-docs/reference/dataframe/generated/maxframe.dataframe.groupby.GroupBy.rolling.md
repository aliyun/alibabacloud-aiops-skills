# maxframe.dataframe.groupby.GroupBy.rolling

#### GroupBy.rolling(window, min_periods=None, , center=False, win_type=None, on=None, axis=0, closed=None, shift=0, order_cols=None, ascending=True) → RollingGroupby

Return a rolling grouper, providing rolling functionality per group.

* **Parameters:**
  * **window** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *timedelta* *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *offset* *, or* *BaseIndexer subclass*) – 

    Size of the moving window.

    If an integer, the fixed number of observations used for
    each window.

    If a timedelta, str, or offset, the time period of each window. Each
    window will be a variable sized based on the observations included in
    the time-period. This is only valid for datetimelike indexes.
    To learn more about the offsets & frequency strings, please see [this link](https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases).

    If a BaseIndexer subclass, the window boundaries
    based on the defined `get_window_bounds` method. Additional rolling
    keyword arguments, namely `min_periods`, `center`, `closed` and
    `step` will be passed to `get_window_bounds`.
  * **min_periods** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – 

    Minimum number of observations in window required to have a value;
    otherwise, result is `np.nan`.

    For a window that is specified by an offset,
    `min_periods` will default to 1.

    For a window that is specified by an integer, `min_periods` will default
    to the size of the window.
  * **center** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – 

    If False, set the window labels as the right edge of the window index.

    If True, set the window labels as the center of the window index.
  * **win_type** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – 

    If `None`, all points are evenly weighted.

    If a string, it must be a valid [scipy.signal window function](https://docs.scipy.org/doc/scipy/reference/signal.windows.html#module-scipy.signal.windows).

    Certain Scipy window types require additional parameters to be passed
    in the aggregation function. The additional parameters must match
    the keywords specified in the Scipy window type method signature.
  * **on** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – 

    For a DataFrame, a column label or Index level on which
    to calculate the rolling window, rather than the DataFrame’s index.

    Provided integer column is ignored and excluded from result since
    an integer index is not used to calculate the rolling window.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default 0*) – 

    If `0` or `'index'`, roll across the rows.

    If `1` or `'columns'`, roll across the columns.

    For Series this parameter is unused and defaults to 0.
  * **closed** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *default None*) – 

    If `'right'`, the first point in the window is excluded from calculations.

    If `'left'`, the last point in the window is excluded from calculations.

    If `'both'`, no points in the window are excluded from calculations.

    If `'neither'`, the first and last points in the window are excluded
    from calculations.

    Default `None` (`'right'`).
  * **shift** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default 0*) – If specified, the window will be shifted by shift rows (or data will be
    shifted by -shift rows) before computing window function.
* **Returns:**
  Return a new grouper with our rolling appended.
* **Return type:**
  maxframe.dataframe.groupby.RollingGroupby

#### SEE ALSO
`Series.rolling`
: Calling object with Series data.

`DataFrame.rolling`
: Calling object with DataFrames.

`Series.groupby`
: Apply a function groupby to a Series.

`DataFrame.groupby`
: Apply a function groupby.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({'A': [1, 1, 2, 2],
...                    'B': [1, 2, 3, 4],
...                    'C': [0.362, 0.227, 1.267, -0.562]})
>>> df.execute()
      A  B      C
0     1  1  0.362
1     1  2  0.227
2     2  3  1.267
3     2  4 -0.562
```

```pycon
>>> df.groupby('A').rolling(2).sum().execute()
    B      C
A
1 0  NaN    NaN
  1  3.0  0.589
2 2  NaN    NaN
  3  7.0  0.705
```

```pycon
>>> df.groupby('A').rolling(2, min_periods=1).sum().execute()
    B      C
A
1 0  1.0  0.362
  1  3.0  0.589
2 2  3.0  1.267
  3  7.0  0.705
```

```pycon
>>> df.groupby('A').rolling(2, on='B').sum().execute()
    B      C
A
1 0  1    NaN
  1  2  0.589
2 2  3    NaN
  3  4  0.705
```
