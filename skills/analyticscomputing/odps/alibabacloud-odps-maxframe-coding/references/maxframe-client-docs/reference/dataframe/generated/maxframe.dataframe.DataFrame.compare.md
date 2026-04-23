# maxframe.dataframe.DataFrame.compare

#### DataFrame.compare(other, align_axis: [int](https://docs.python.org/3/library/functions.html#int) | [str](https://docs.python.org/3/library/stdtypes.html#str) = 1, keep_shape: [bool](https://docs.python.org/3/library/functions.html#bool) = False, keep_equal: [bool](https://docs.python.org/3/library/functions.html#bool) = False, result_names: [Tuple](https://docs.python.org/3/library/typing.html#typing.Tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)] = ('self', 'other'))

Compare to another DataFrame and show the differences.

* **Parameters:**
  * **other** ([*DataFrame*](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)) – Object to compare with.
  * **align_axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 1*) – 

    Determine which axis to align the comparison on.
    * 0, or ‘index’
      : with rows drawn alternately from self and other.
    * 1, or ‘columns’
      : with columns drawn alternately from self and other.
  * **keep_shape** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If true, all rows and columns are kept.
    Otherwise, only the ones with different values are kept.
  * **keep_equal** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If true, the result keeps values that are equal.
    Otherwise, equal values are shown as NaNs.
  * **result_names** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *,* *default* *(* *‘self’* *,*  *‘other’* *)*) – Set the dataframes names in the comparison.
* **Returns:**
  DataFrame that shows the differences stacked side by side.

  The resulting index will be a MultiIndex with ‘self’ and ‘other’
  stacked alternately at the inner level.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)
* **Raises:**
  [**ValueError**](https://docs.python.org/3/library/exceptions.html#ValueError) – When the two DataFrames don’t have identical labels or shape.

#### SEE ALSO
[`Series.compare`](maxframe.dataframe.Series.compare.md#maxframe.dataframe.Series.compare)
: Compare with another Series and show differences.

`DataFrame.equals`
: Test whether two objects contain the same elements.

### Notes

Matching NaNs will not appear as a difference.

Can only compare identically-labeled
(i.e. same shape, identical row and column labels) DataFrames

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> df = md.DataFrame(
...     {
...         "col1": ["a", "a", "b", "b", "a"],
...         "col2": [1.0, 2.0, 3.0, mt.nan, 5.0],
...         "col3": [1.0, 2.0, 3.0, 4.0, 5.0]
...     },
...     columns=["col1", "col2", "col3"],
... )
>>> df.execute()
  col1  col2  col3
0    a   1.0   1.0
1    a   2.0   2.0
2    b   3.0   3.0
3    b   NaN   4.0
4    a   5.0   5.0
```

```pycon
>>> df2 = df.copy()
>>> df2.loc[0, 'col1'] = 'c'
>>> df2.loc[2, 'col3'] = 4.0
>>> df2.execute()
  col1  col2  col3
0    c   1.0   1.0
1    a   2.0   2.0
2    b   3.0   4.0
3    b   NaN   4.0
4    a   5.0   5.0
```

Align the differences on columns

```pycon
>>> df.compare(df2).execute()
  col1       col3
  self other self other
0    a     c  NaN   NaN
2  NaN   NaN  3.0   4.0
```

Stack the differences on rows

```pycon
>>> df.compare(df2, align_axis=0).execute()
        col1  col3
0 self     a   NaN
  other    c   NaN
2 self   NaN   3.0
  other  NaN   4.0
```

Keep the equal values

```pycon
>>> df.compare(df2, keep_equal=True).execute()
  col1       col3
  self other self other
0    a     c  1.0   1.0
2    b     b  3.0   4.0
```

Keep all original rows and columns

```pycon
>>> df.compare(df2, keep_shape=True).execute()
  col1       col2       col3
  self other self other self other
0    a     c  NaN   NaN  NaN   NaN
1  NaN   NaN  NaN   NaN  NaN   NaN
2  NaN   NaN  NaN   NaN  3.0   4.0
3  NaN   NaN  NaN   NaN  NaN   NaN
4  NaN   NaN  NaN   NaN  NaN   NaN
```

Keep all original rows and columns and also all original values

```pycon
>>> df.compare(df2, keep_shape=True, keep_equal=True).execute()
  col1       col2       col3
  self other self other self other
0    a     c  1.0   1.0  1.0   1.0
1    a     a  2.0   2.0  2.0   2.0
2    b     b  3.0   3.0  3.0   4.0
3    b     b  NaN   NaN  4.0   4.0
4    a     a  5.0   5.0  5.0   5.0
```
