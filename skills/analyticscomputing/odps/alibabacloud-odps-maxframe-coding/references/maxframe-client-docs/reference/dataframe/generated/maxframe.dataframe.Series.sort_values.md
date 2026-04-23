# maxframe.dataframe.Series.sort_values

#### Series.sort_values(axis=0, ascending=True, inplace=False, kind='quicksort', na_position='last', ignore_index=False, parallel_kind='PSRS', psrs_kinds=None)

Sort by the values.

Sort a Series in ascending or descending order by some
criterion.

* **Parameters:**
  * **series** (*input Series.*)
  * **axis** ( *{0* *or*  *'index'}* *,* *default 0*) – Axis to direct sorting. The value ‘index’ is accepted for
    compatibility with DataFrame.sort_values.
  * **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True, sort values in ascending order, otherwise descending.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, perform operation in-place.
  * **kind** ( *{'quicksort'* *,*  *'mergesort'* *or*  *'heapsort'}* *,* *default 'quicksort'*) – Choice of sorting algorithm. See also [`numpy.sort()`](https://numpy.org/doc/stable/reference/generated/numpy.sort.html#numpy.sort) for more
    information. ‘mergesort’ is the only stable  algorithm.
  * **na_position** ( *{'first'* *or*  *'last'}* *,* *default 'last'*) – Argument ‘first’ puts NaNs at the beginning, ‘last’ puts NaNs at
    the end.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting axis will be labeled 0, 1, …, n - 1.
* **Returns:**
  Series ordered by values.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> raw = pd.Series([np.nan, 1, 3, 10, 5])
>>> s = md.Series(raw)
>>> s.execute()
0     NaN
1     1.0
2     3.0
3     10.0
4     5.0
dtype: float64
```

Sort values ascending order (default behaviour)

```pycon
>>> s.sort_values(ascending=True).execute()
1     1.0
2     3.0
4     5.0
3    10.0
0     NaN
dtype: float64
```

Sort values descending order

```pycon
>>> s.sort_values(ascending=False).execute()
3    10.0
4     5.0
2     3.0
1     1.0
0     NaN
dtype: float64
```

Sort values inplace

```pycon
>>> s.sort_values(ascending=False, inplace=True)
>>> s.execute()
3    10.0
4     5.0
2     3.0
1     1.0
0     NaN
dtype: float64
```

Sort values putting NAs first
