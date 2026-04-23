# maxframe.dataframe.DataFrame.stack

#### DataFrame.stack(level=-1, dropna=True)

Stack the prescribed level(s) from columns to index.

Return a reshaped DataFrame or Series having a multi-level
index with one or more new inner-most levels compared to the current
DataFrame. The new inner-most levels are created by pivoting the
columns of the current dataframe:

> - if the columns have a single level, the output is a Series;
> - if the columns have multiple levels, the new index
>   level(s) is (are) taken from the prescribed level(s) and
>   the output is a DataFrame.
* **Parameters:**
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *,* *default -1*) – Level(s) to stack from the column axis onto the index
    axis, defined as one index or label, or a list of indices
    or labels.
  * **dropna** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Whether to drop rows in the resulting Frame/Series with
    missing values. Stacking a column level onto the index
    axis can create combinations of index and column values
    that are missing from the original dataframe. See Examples
    section.
* **Returns:**
  Stacked dataframe or series.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

#### SEE ALSO
[`DataFrame.unstack`](maxframe.dataframe.DataFrame.unstack.md#maxframe.dataframe.DataFrame.unstack)
: Unstack prescribed level(s) from index axis onto column axis.

[`DataFrame.pivot`](maxframe.dataframe.DataFrame.pivot.md#maxframe.dataframe.DataFrame.pivot)
: Reshape dataframe from long format to wide format.

[`DataFrame.pivot_table`](maxframe.dataframe.DataFrame.pivot_table.md#maxframe.dataframe.DataFrame.pivot_table)
: Create a spreadsheet-style pivot table as a DataFrame.

### Notes

The function is named by analogy with a collection of books
being reorganized from being side by side on a horizontal
position (the columns of the dataframe) to being stacked
vertically on top of each other (in the index of the
dataframe).

### Examples

**Single level columns**

```pycon
>>> import maxframe.dataframe as md
>>> df_single_level_cols = md.DataFrame([[0, 1], [2, 3]],
...                                     index=['cat', 'dog'],
...                                     columns=['weight', 'height'])
```

Stacking a dataframe with a single level column axis returns a Series:

```pycon
>>> df_single_level_cols.execute()
     weight height
cat       0      1
dog       2      3
>>> df_single_level_cols.stack().execute()
cat  weight    0
     height    1
dog  weight    2
     height    3
dtype: int64
```

**Multi level columns: simple case**

```pycon
>>> multicol1 = pd.MultiIndex.from_tuples([('weight', 'kg'),
...                                        ('weight', 'pounds')])
>>> df_multi_level_cols1 = md.DataFrame([[1, 2], [2, 4]],
...                                     index=['cat', 'dog'],
...                                     columns=multicol1)
```

Stacking a dataframe with a multi-level column axis:

```pycon
>>> df_multi_level_cols1.execute()
     weight
         kg    pounds
cat       1        2
dog       2        4
>>> df_multi_level_cols1.stack().execute()
            weight
cat kg           1
    pounds       2
dog kg           2
    pounds       4
```

**Missing values**

```pycon
>>> multicol2 = pd.MultiIndex.from_tuples([('weight', 'kg'),
...                                        ('height', 'm')])
>>> df_multi_level_cols2 = md.DataFrame([[1.0, 2.0], [3.0, 4.0]],
...                                     index=['cat', 'dog'],
...                                     columns=multicol2)
```

It is common to have missing values when stacking a dataframe
with multi-level columns, as the stacked dataframe typically
has more values than the original dataframe. Missing values
are filled with NaNs:

```pycon
>>> df_multi_level_cols2.execute()
    weight height
        kg      m
cat    1.0    2.0
dog    3.0    4.0
>>> df_multi_level_cols2.stack().execute()
        height  weight
cat kg     NaN     1.0
    m      2.0     NaN
dog kg     NaN     3.0
    m      4.0     NaN
```

**Prescribing the level(s) to be stacked**

The first parameter controls which level or levels are stacked:

```pycon
>>> df_multi_level_cols2.stack(0).execute()
             kg    m
cat height  NaN  2.0
    weight  1.0  NaN
dog height  NaN  4.0
    weight  3.0  NaN
>>> df_multi_level_cols2.stack([0, 1]).execute()
cat  height  m     2.0
     weight  kg    1.0
dog  height  m     4.0
     weight  kg    3.0
dtype: float64
```

**Dropping missing values**

```pycon
>>> df_multi_level_cols3 = md.DataFrame([[None, 1.0], [2.0, 3.0]],
...                                     index=['cat', 'dog'],
...                                     columns=multicol2)
```

Note that rows where all values are missing are dropped by
default but this behaviour can be controlled via the dropna
keyword parameter:

```pycon
>>> df_multi_level_cols3.execute()
    weight height
        kg      m
cat    NaN    1.0
dog    2.0    3.0
>>> df_multi_level_cols3.stack(dropna=False).execute()
        height  weight
cat kg     NaN     NaN
    m      1.0     NaN
dog kg     NaN     2.0
    m      3.0     NaN
>>> df_multi_level_cols3.stack(dropna=True).execute()
        height  weight
cat m      1.0     NaN
dog kg     NaN     2.0
    m      3.0     NaN
```
