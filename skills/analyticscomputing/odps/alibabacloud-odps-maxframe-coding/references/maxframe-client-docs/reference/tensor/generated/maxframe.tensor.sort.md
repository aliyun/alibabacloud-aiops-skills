# maxframe.tensor.sort

### maxframe.tensor.sort(a, axis=-1, kind=None, order=None, , stable=None, parallel_kind=None, psrs_kinds=None, return_index=False, \*\*kw)

Return a sorted copy of a tensor.

* **Parameters:**
  * **a** (*array_like*) – Tensor to be sorted.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None* *,* *optional*) – Axis along which to sort. If None, the tensor is flattened before
    sorting. The default is -1, which sorts along the last axis.
  * **kind** ( *{'quicksort'* *,*  *'mergesort'* *,*  *'heapsort'* *,*  *'stable'}* *,* *optional*) – Sorting algorithm. The default is ‘quicksort’. Note that both ‘stable’
    and ‘mergesort’ use timsort or radix sort under the covers and, in general,
    the actual implementation will vary with data type. The ‘mergesort’ option
    is retained for backwards compatibility.
    Note that this argument would not take effect if a has more than
    1 chunk on the sorting axis.
  * **order** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – When a is a tensor with fields defined, this argument specifies
    which fields to compare first, second, etc.  A single field can
    be specified as a string, and not all fields need be specified,
    but unspecified fields will still be used, in the order in which
    they come up in the dtype, to break ties.
  * **stable** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Sort stability. If True, the returned array will maintain the relative
    order of a values which compare as equal. If False or None, this
    is not guaranteed. Internally, this option selects kind=’stable’.
    Default: None.
  * **parallel_kind** ( *{'PSRS'}* *,* *optional*) – Parallel sorting algorithm, for the details, refer to:
    [http://csweb.cs.wfu.edu/bigiron/LittleFE-PSRS/build/html/PSRSalgorithm.html](http://csweb.cs.wfu.edu/bigiron/LittleFE-PSRS/build/html/PSRSalgorithm.html)
  * **psrs_kinds** (*list with 3 elements* *,* *optional*) – Sorting algorithms during PSRS algorithm.
  * **return_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Return indices as well if True.
* **Returns:**
  **sorted_tensor** – Tensor of the same type and shape as a.
* **Return type:**
  Tensor

#### SEE ALSO
`Tensor.sort`
: Method to sort a tensor in-place.

[`argsort`](maxframe.tensor.argsort.md#maxframe.tensor.argsort)
: Indirect sort.

`lexsort`
: Indirect stable sort on multiple keys.

`searchsorted`
: Find elements in a sorted tensor.

[`partition`](maxframe.tensor.partition.md#maxframe.tensor.partition)
: Partial sort.

### Notes

The various sorting algorithms are characterized by their average speed,
worst case performance, work space size, and whether they are stable. A
stable sort keeps items with the same key in the same relative
order. The four algorithms implemented in NumPy have the following
properties:

| kind        |   speed | worst case   | work space   | stable   |
|-------------|---------|--------------|--------------|----------|
| ‘quicksort’ |       1 | O(n^2)       | 0            | no       |
| ‘heapsort’  |       3 | O(n\*log(n)) | 0            | no       |
| ‘mergesort’ |       2 | O(n\*log(n)) | ~n/2         | yes      |
| ‘timsort’   |       2 | O(n\*log(n)) | ~n/2         | yes      |

#### NOTE
The datatype determines which of ‘mergesort’ or ‘timsort’
is actually used, even if ‘mergesort’ is specified. User selection
at a finer scale is not currently available.

All the sort algorithms make temporary copies of the data when
sorting along any but the last axis.  Consequently, sorting along
the last axis is faster and uses less space than sorting along
any other axis.

The sort order for complex numbers is lexicographic. If both the real
and imaginary parts are non-nan then the order is determined by the
real parts except when they are equal, in which case the order is
determined by the imaginary parts.

quicksort has been changed to an introsort which will switch
heapsort when it does not make enough progress. This makes its
worst case O(n\*log(n)).

‘stable’ automatically choses the best stable sorting algorithm
for the data type being sorted. It, along with ‘mergesort’ is
currently mapped to timsort or radix sort depending on the
data type. API forward compatibility currently limits the
ability to select the implementation and it is hardwired for the different
data types.

Timsort is added for better performance on already or nearly
sorted data. On random data timsort is almost identical to
mergesort. It is now used for stable sort while quicksort is still the
default sort if none is chosen. For details of timsort, refer to
[CPython listsort.txt](https://github.com/python/cpython/blob/3.7/Objects/listsort.txt).
‘mergesort’ and ‘stable’ are mapped to radix sort for integer data types. Radix sort is an
O(n) sort instead of O(n log n).

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.array([[1,4],[3,1]])
>>> mt.sort(a).execute()                # sort along the last axis
array([[1, 4],
       [1, 3]])
>>> mt.sort(a, axis=None).execute()     # sort the flattened tensor
array([1, 1, 3, 4])
>>> mt.sort(a, axis=0).execute()        # sort along the first axis
array([[1, 1],
       [3, 4]])
```

Use the order keyword to specify a field to use when sorting a
structured array:

```pycon
>>> dtype = [('name', 'S10'), ('height', float), ('age', int)]
>>> values = [('Arthur', 1.8, 41), ('Lancelot', 1.9, 38),
...           ('Galahad', 1.7, 38)]
>>> a = mt.array(values, dtype=dtype)       # create a structured tensor
>>> mt.sort(a, order='height').execute()
array([('Galahad', 1.7, 38), ('Arthur', 1.8, 41),
       ('Lancelot', 1.8999999999999999, 38)],
      dtype=[('name', '|S10'), ('height', '<f8'), ('age', '<i4')])
```

Sort by age, then height if ages are equal:

```pycon
>>> mt.sort(a, order=['age', 'height']).execute()
array([('Galahad', 1.7, 38), ('Lancelot', 1.8999999999999999, 38),
       ('Arthur', 1.8, 41)],
      dtype=[('name', '|S10'), ('height', '<f8'), ('age', '<i4')])
```
