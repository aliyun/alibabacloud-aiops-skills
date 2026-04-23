# maxframe.dataframe.Series.sort_index

#### Series.sort_index(axis=0, level=None, ascending=True, inplace=False, kind='quicksort', na_position='last', sort_remaining=True, ignore_index: [bool](https://docs.python.org/3/library/functions.html#bool) = False, parallel_kind='PSRS', psrs_kinds=None, default_index_type=None)

Sort object by labels (along an axis).

* **Parameters:**
  * **a** (*Input DataFrame* *or* *Series.*)
  * **axis** ( *{0* *or*  *'index'* *,* *1* *or*  *'columns'}* *,* *default 0*) – The axis along which to sort.  The value 0 identifies the rows,
    and 1 identifies the columns.
  * **level** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *level name* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *ints* *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* *level names*) – If not None, sort on values in specified index level(s).
  * **ascending** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – Sort ascending vs. descending.
  * **inplace** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, perform operation in-place.
  * **kind** ( *{'quicksort'* *,*  *'mergesort'* *,*  *'heapsort'}* *,* *default 'quicksort'*) – Choice of sorting algorithm. See also ndarray.np.sort for more
    information.  mergesort is the only stable algorithm. For
    DataFrames, this option is only applied when sorting on a single
    column or label.
  * **na_position** ( *{'first'* *,*  *'last'}* *,* *default 'last'*) – Puts NaNs at the beginning if first; last puts NaNs at the end.
    Not implemented for MultiIndex.
  * **sort_remaining** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default True*) – If True and sorting by level and index is multilevel, sort by other
    levels too (in order) after sorting by specified level.
  * **ignore_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *default False*) – If True, the resulting axis will be labeled 0, 1, …, n - 1.
  * **parallel_kind** ( *{'PSRS'}* *,* *optional.*) – Parallel sorting algorithm, for the details, refer to:
    [http://csweb.cs.wfu.edu/bigiron/LittleFE-PSRS/build/html/PSRSalgorithm.html](http://csweb.cs.wfu.edu/bigiron/LittleFE-PSRS/build/html/PSRSalgorithm.html)
  * **psrs_kinds** (*Sorting algorithms during PSRS algorithm.*)
* **Returns:**
  **sorted_obj** – DataFrame with sorted index if inplace=False, None otherwise.
* **Return type:**
  [DataFrame](maxframe.dataframe.DataFrame.md#maxframe.dataframe.DataFrame) or None
