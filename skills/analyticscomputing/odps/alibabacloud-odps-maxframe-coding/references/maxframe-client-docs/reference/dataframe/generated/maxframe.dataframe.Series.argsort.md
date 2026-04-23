# maxframe.dataframe.Series.argsort

#### Series.argsort(axis=0, kind='quicksort', order=None, stable=None)

Return the integer indices that would sort the Series values.

Override ndarray.argsort. Argsorts the value, omitting NA/null values,
and places the result in the same locations as the non-NA values.

* **Parameters:**
  * **axis** ( *{0* *or*  *'index'}*) – Unused. Parameter needed for compatibility with DataFrame.
  * **kind** ( *{'mergesort'* *,*  *'quicksort'* *,*  *'heapsort'* *,*  *'stable'}* *,* *default 'quicksort'*) – Choice of sorting algorithm. See [`numpy.sort()`](https://numpy.org/doc/stable/reference/generated/numpy.sort.html#numpy.sort) for more
    information. ‘mergesort’ and ‘stable’ are the only stable algorithms.
  * **order** (*None*) – Has no effect but is accepted for compatibility with numpy.
  * **stable** (*None*) – Has no effect but is accepted for compatibility with numpy.
* **Returns:**
  Positions of values within the sort order with -1 indicating
  nan values.
* **Return type:**
  [Series](maxframe.dataframe.Series.md#maxframe.dataframe.Series)[np.intp]

#### SEE ALSO
[`maxframe.tensor.argsort`](../../tensor/generated/maxframe.tensor.argsort.md#maxframe.tensor.argsort)
: Returns the indices that would sort this array.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> import maxframe.dataframe as md
>>> s = md.Series([3, 2, 1])
>>> s.argsort().execute()
0    2
1    1
2    0
dtype: int64
```
