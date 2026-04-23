# maxframe.dataframe.DataFrame.shift

#### DataFrame.shift(periods=1, freq=None, axis=0, fill_value=None)

Shift index by desired number of periods with an optional time freq.

When freq is not passed, shift the index without realigning the data.
If freq is passed (in this case, the index must be date or datetime,
or it will raise a NotImplementedError), the index will be
increased using the periods and the freq.

* **Parameters:**
  * **periods** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Number of periods to shift. Can be positive or negative.
  * **freq** (*DateOffset* *,* *tseries.offsets* *,* *timedelta* *, or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – Offset to use from the tseries module or time rule (e.g. ‘EOM’).
    If freq is specified then the index values are shifted but the
    data is not realigned. That is, use freq if you would like to
    extend the index when shifting and preserve the original data.
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'* *,* *None}* *,* *default None*) – Shift direction.
  * **fill_value** ([*object*](https://docs.python.org/3/library/functions.html#object) *,* *optional*) – The scalar value to use for newly introduced missing values.
    the default depends on the dtype of self.
    For numeric data, `np.nan` is used.
    For datetime, timedelta, or period data, etc. `NaT` is used.
    For extension dtypes, `self.dtype.na_value` is used.
* **Returns:**
  Copy of input object, shifted.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
`Index.shift`
: Shift values of Index.

`DatetimeIndex.shift`
: Shift values of DatetimeIndex.

`PeriodIndex.shift`
: Shift values of PeriodIndex.

[`tshift`](maxframe.dataframe.DataFrame.tshift.md#maxframe.dataframe.DataFrame.tshift)
: Shift the time index, using the index’s frequency if available.

### Examples

```pycon
>>> import maxframe.dataframe as md
```

```pycon
>>> df = md.DataFrame({'Col1': [10, 20, 15, 30, 45],
...                    'Col2': [13, 23, 18, 33, 48],
...                    'Col3': [17, 27, 22, 37, 52]})
```

```pycon
>>> df.shift(periods=3).execute()
   Col1  Col2  Col3
0   NaN   NaN   NaN
1   NaN   NaN   NaN
2   NaN   NaN   NaN
3  10.0  13.0  17.0
4  20.0  23.0  27.0
```

```pycon
>>> df.shift(periods=1, axis='columns').execute()
   Col1  Col2  Col3
0   NaN  10.0  13.0
1   NaN  20.0  23.0
2   NaN  15.0  18.0
3   NaN  30.0  33.0
4   NaN  45.0  48.0
```

```pycon
>>> df.shift(periods=3, fill_value=0).execute()
   Col1  Col2  Col3
0     0     0     0
1     0     0     0
2     0     0     0
3    10    13    17
4    20    23    27
```
