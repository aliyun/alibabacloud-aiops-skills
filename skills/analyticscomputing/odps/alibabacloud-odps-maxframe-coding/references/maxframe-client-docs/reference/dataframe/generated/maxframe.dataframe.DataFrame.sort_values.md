# maxframe.dataframe.DataFrame.sort_values

#### DataFrame.sort_values(by, axis=0, ascending=True, inplace=False, kind='quicksort', na_position='last', ignore_index=False, parallel_kind='PSRS', psrs_kinds=None, default_index_type=None)

Sort by the values along either axis.

* **Parameters:**
  * **df** (*MaxFrame DataFrame*) – Input dataframe.
  * **by** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Name or list of names to sort by.
  * **axis** ( *%* *(**axes_single_arg* *)**s* *,* *default 0*) – Axis to be sorted.
  * **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Sort ascending vs. descending. Specify list for multiple sort
    orders.  If this is a list of bools, must match the length of
    the by.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, perform operation in-place.
  * **kind** ( *{'quicksort'* *,*  *'mergesort'* *,*  *'heapsort'}* *,* *default 'quicksort'*) – Choice of sorting algorithm. See also ndarray.np.sort for more
    information.  mergesort is the only stable algorithm. For
    DataFrames, this option is only applied when sorting on a single
    column or label.
  * **na_position** ( *{'first'* *,*  *'last'}* *,* *default 'last'*) – Puts NaNs at the beginning if first; last puts NaNs at the
    end.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting axis will be labeled 0, 1, …, n - 1.
  * **parallel_kind** ( *{'PSRS'}* *,* *default 'PSRS'*) – Parallel sorting algorithm, for the details, refer to:
    [http://csweb.cs.wfu.edu/bigiron/LittleFE-PSRS/build/html/PSRSalgorithm.html](http://csweb.cs.wfu.edu/bigiron/LittleFE-PSRS/build/html/PSRSalgorithm.html)
* **Returns:**
  **sorted_obj** – DataFrame with sorted values if inplace=False, None otherwise.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or None

### Examples

```pycon
>>> import maxframe.dataframe as md
>>> df = md.DataFrame({
...     'col1': ['A', 'A', 'B', np.nan, 'D', 'C'],
...     'col2': [2, 1, 9, 8, 7, 4],
...     'col3': [0, 1, 9, 4, 2, 3],
... })
>>> df.execute()
    col1 col2 col3
0   A    2    0
1   A    1    1
2   B    9    9
3   NaN  8    4
4   D    7    2
5   C    4    3
```

Sort by col1

```pycon
>>> df.sort_values(by=['col1']).execute()
    col1 col2 col3
0   A    2    0
1   A    1    1
2   B    9    9
5   C    4    3
4   D    7    2
3   NaN  8    4
```

Sort by multiple columns

```pycon
>>> df.sort_values(by=['col1', 'col2']).execute()
    col1 col2 col3
1   A    1    1
0   A    2    0
2   B    9    9
5   C    4    3
4   D    7    2
3   NaN  8    4
```

Sort Descending

```pycon
>>> df.sort_values(by='col1', ascending=False).execute()
    col1 col2 col3
4   D    7    2
5   C    4    3
2   B    9    9
0   A    2    0
1   A    1    1
3   NaN  8    4
```
