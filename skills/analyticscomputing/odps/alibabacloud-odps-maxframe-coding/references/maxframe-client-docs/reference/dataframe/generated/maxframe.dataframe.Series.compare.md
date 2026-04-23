# maxframe.dataframe.Series.compare

#### Series.compare(other, align_axis: [int](https://docs.python.org/3/library/functions.html#int) | [str](https://docs.python.org/3/library/stdtypes.html#str) = 1, keep_shape: [bool](https://docs.python.org/3/library/functions.html#bool) = False, keep_equal: [bool](https://docs.python.org/3/library/functions.html#bool) = False, result_names: [Tuple](https://docs.python.org/3/library/typing.html#typing.Tuple)[[str](https://docs.python.org/3/library/stdtypes.html#str), [str](https://docs.python.org/3/library/stdtypes.html#str)] = ('self', 'other'))

Compare to another Series and show the differences.

* **Parameters:**
  * **other** ([*Series*](maxframe.dataframe.Series.md#maxframe.dataframe.Series)) – Object to compare with.
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
  If axis is 0 or ‘index’ the result will be a Series.
  The resulting index will be a MultiIndex with ‘self’ and ‘other’
  stacked alternately at the inner level.

  If axis is 1 or ‘columns’ the result will be a DataFrame.
  It will have two columns namely ‘self’ and ‘other’.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series) or [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame)

#### SEE ALSO
[`DataFrame.compare`](maxframe.dataframe.DataFrame.compare.md#maxframe.dataframe.DataFrame.compare)
: Compare with another DataFrame and show differences.

### Notes

Matching NaNs will not appear as a difference.

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> s1 = md.Series(["a", "b", "c", "d", "e"])
>>> s2 = md.Series(["a", "a", "c", "b", "e"])
```

Align the differences on columns

```pycon
>>> s1.compare(s2).execute()
  self other
1    b     a
3    d     b
```

Stack the differences on indices

```pycon
>>> s1.compare(s2, align_axis=0).execute()
1  self     b
   other    a
3  self     d
   other    b
dtype: object
```

Keep all original rows

```pycon
>>> s1.compare(s2, keep_shape=True).execute()
  self other
0  NaN   NaN
1    b     a
2  NaN   NaN
3    d     b
4  NaN   NaN
```

Keep all original rows and also all original values

```pycon
>>> s1.compare(s2, keep_shape=True, keep_equal=True).execute()
  self other
0    a     a
1    b     a
2    c     c
3    d     b
4    e     e
```
