# maxframe.dataframe.Series.reindex_like

#### Series.reindex_like(other, method=None, copy=True, limit=None, tolerance=None)

Return an object with matching indices as other object.

Conform the object to the same index on all axes. Optional
filling logic, placing NaN in locations having no value
in the previous index. A new object is produced unless the
new index is equivalent to the current one and copy=False.

* **Parameters:**
  * **other** (*Object* *of* *the same data type*) – Its row and column indices are used to define the new indices
    of this object.
  * **method** ( *{None* *,*  *'backfill'/'bfill'* *,*  *'pad'/'ffill'* *,*  *'nearest'}*) – 

    Method to use for filling holes in reindexed DataFrame.
    Please note: this is only applicable to DataFrames/Series with a
    monotonically increasing/decreasing index.
    * None (default): don’t fill gaps
    * pad / ffill: propagate last valid observation forward to next
      valid
    * backfill / bfill: use next valid observation to fill gap
    * nearest: use nearest valid observations to fill gap.
  * **copy** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Return a new object, even if the passed indexes are the same.
  * **limit** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *default None*) – Maximum number of consecutive labels to fill for inexact matches.
  * **tolerance** (*optional*) – 

    Maximum distance between original and new labels for inexact
    matches. The values of the index at the matching locations must
    satisfy the equation `abs(index[indexer] - target) <= tolerance`.

    Tolerance may be a scalar value, which applies the same tolerance
    to all values, or list-like, which applies variable tolerance per
    element. List-like includes list, tuple, array, Series, and must be
    the same size as the index and its dtype must exactly match the
    index’s type.
* **Returns:**
  Same type as caller, but with changed indices on each axis.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.set_index`](maxframe.dataframe.DataFrame.set_index.md#maxframe.dataframe.DataFrame.set_index)
: Set row labels.

[`DataFrame.reset_index`](maxframe.dataframe.DataFrame.reset_index.md#maxframe.dataframe.DataFrame.reset_index)
: Remove row labels or move them to new columns.

[`DataFrame.reindex`](maxframe.dataframe.DataFrame.reindex.md#maxframe.dataframe.DataFrame.reindex)
: Change to new indices or expand indices.

### Notes

Same as calling
`.reindex(index=other.index, columns=other.columns,...)`.

### Examples

```pycon
>>> import pandas as pd
>>> import maxframe.dataframe as md
>>> df1 = md.DataFrame([[24.3, 75.7, 'high'],
...                     [31, 87.8, 'high'],
...                     [22, 71.6, 'medium'],
...                     [35, 95, 'medium']],
...                    columns=['temp_celsius', 'temp_fahrenheit',
...                             'windspeed'],
...                    index=md.date_range(start='2014-02-12',
...                                        end='2014-02-15', freq='D'))
```

```pycon
>>> df1.execute()
           temp_celsius temp_fahrenheit windspeed
2014-02-12         24.3            75.7      high
2014-02-13           31            87.8      high
2014-02-14           22            71.6    medium
2014-02-15           35              95    medium
```

```pycon
>>> df2 = md.DataFrame([[28, 'low'],
...                     [30, 'low'],
...                     [35.1, 'medium']],
...                    columns=['temp_celsius', 'windspeed'],
...                    index=pd.DatetimeIndex(['2014-02-12', '2014-02-13',
...                                            '2014-02-15']))
```

```pycon
>>> df2.execute()
            temp_celsius windspeed
2014-02-12          28.0       low
2014-02-13          30.0       low
2014-02-15          35.1    medium
```

```pycon
>>> df2.reindex_like(df1).execute()
            temp_celsius  temp_fahrenheit windspeed
2014-02-12          28.0              NaN       low
2014-02-13          30.0              NaN       low
2014-02-14           NaN              NaN       NaN
2014-02-15          35.1              NaN    medium
```
