# maxframe.dataframe.DataFrame.combine

#### DataFrame.combine(other, func, fill_value=None, overwrite=True)

Perform column-wise combine with another DataFrame.

Combines a DataFrame with other DataFrame using func
to element-wise combine columns. The row and column indexes of the
resulting DataFrame will be the union of the two.

* **Parameters:**
  * **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – The DataFrame to merge column-wise.
  * **func** (*function*) – Function that takes two series as inputs and return a Series or a
    scalar. Used to merge the two dataframes column by columns.
  * **fill_value** (*scalar value* *,* *default None*) – The value to fill NaNs with prior to passing any column to the
    merge func.
  * **overwrite** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True, columns in self that do not exist in other will be
    overwritten with NaNs.
* **Returns:**
  Combination of the provided DataFrames.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.combine_first`](maxframe.dataframe.DataFrame.combine_first.md#maxframe.dataframe.DataFrame.combine_first)
: Combine two DataFrame objects and default to non-null values in frame calling the method.

### Examples

Combine using a simple function that chooses the smaller column.

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df1 = md.DataFrame({'A': [0, 0], 'B': [4, 4]})
>>> df2 = md.DataFrame({'A': [1, 1], 'B': [3, 3]})
>>> take_smaller = lambda s1, s2: s1 if s1.sum() < s2.sum() else s2
>>> df1.combine(df2, take_smaller).execute()
   A  B
0  0  3
1  0  3
```

Example using a true element-wise combine function.

```pycon
>>> df1 = md.DataFrame({'A': [5, 0], 'B': [2, 4]})
>>> df2 = md.DataFrame({'A': [1, 1], 'B': [3, 3]})
>>> df1.combine(df2, mt.minimum).execute()
   A  B
0  1  2
1  0  3
```

Using fill_value fills Nones prior to passing the column to the
merge function.

```pycon
>>> df1 = md.DataFrame({'A': [0, 0], 'B': [None, 4]})
>>> df2 = md.DataFrame({'A': [1, 1], 'B': [3, 3]})
>>> df1.combine(df2, take_smaller, fill_value=-5).execute()
   A    B
0  0 -5.0
1  0  4.0
```

However, if the same element in both dataframes is None, that None
is preserved

```pycon
>>> df1 = md.DataFrame({'A': [0, 0], 'B': [None, 4]})
>>> df2 = md.DataFrame({'A': [1, 1], 'B': [None, 3]})
>>> df1.combine(df2, take_smaller, fill_value=-5).execute()
    A    B
0  0 -5.0
1  0  3.0
```

Example that demonstrates the use of overwrite and behavior when
the axis differ between the dataframes.

```pycon
>>> df1 = md.DataFrame({'A': [0, 0], 'B': [4, 4]})
>>> df2 = md.DataFrame({'B': [3, 3], 'C': [-10, 1], }, index=[1, 2])
>>> df1.combine(df2, take_smaller).execute()
     A    B     C
0  NaN  NaN   NaN
1  NaN  3.0 -10.0
2  NaN  3.0   1.0
```

```pycon
>>> df1.combine(df2, take_smaller, overwrite=False).execute()
     A    B     C
0  0.0  NaN   NaN
1  0.0  3.0 -10.0
2  NaN  3.0   1.0
```

Demonstrating the preference of the passed in dataframe.

```pycon
>>> df2 = md.DataFrame({'B': [3, 3], 'C': [1, 1], }, index=[1, 2])
>>> df2.combine(df1, take_smaller).execute()
   A    B   C
0  0.0  NaN NaN
1  0.0  3.0 NaN
2  NaN  3.0 NaN
```

```pycon
>>> df2.combine(df1, take_smaller, overwrite=False).execute()
     A    B   C
0  0.0  NaN NaN
1  0.0  3.0 1.0
2  NaN  3.0 1.0
```
