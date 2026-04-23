# maxframe.tensor.argsort

### maxframe.tensor.argsort(a, axis=-1, kind=None, order=None, , stable=None, parallel_kind=None, psrs_kinds=None)

Returns the indices that would sort a tensor.

Perform an indirect sort along the given axis using the algorithm specified
by the kind keyword. It returns a tensor of indices of the same shape as
a that index data along the given axis in sorted order.

* **Parameters:**
  * **a** (*array_like*) – Tensor to sort.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None* *,* *optional*) – Axis along which to sort.  The default is -1 (the last axis). If None,
    the flattened tensor is used.
  * **kind** ( *{'quicksort'* *,*  *'mergesort'* *,*  *'heapsort'* *,*  *'stable'}* *,* *optional*) – 

    Sorting algorithm. The default is ‘quicksort’. Note that both ‘stable’
    and ‘mergesort’ use timsort under the covers and, in general, the
    actual implementation will vary with data type. The ‘mergesort’ option
    is retained for backwards compatibility.

    #### Versionchanged
    Changed in version 1.15.0.: The ‘stable’ option was added.
  * **order** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – When a is a tensor with fields defined, this argument specifies
    which fields to compare first, second, etc.  A single field can
    be specified as a string, and not all fields need be specified,
    but unspecified fields will still be used, in the order in which
    they come up in the dtype, to break ties.
  * **stable** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Sort stability. If True, the returned array will maintain the relative
    order of a values which compare as equal. If False or None, this
    is not guaranteed. Internally, this option selects kind=’stable’.
    Default: None.
* **Returns:**
  **index_tensor** – Tensor of indices that sort a along the specified axis.
  If a is one-dimensional, `a[index_tensor]` yields a sorted a.
  More generally, `np.take_along_axis(a, index_tensor, axis=axis)`
  always yields the sorted a, irrespective of dimensionality.
* **Return type:**
  Tensor, [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`sort`](maxframe.tensor.sort.md#maxframe.tensor.sort)
: Describes sorting algorithms used.

`lexsort`
: Indirect stable sort with multiple keys.

`Tensor.sort`
: Inplace sort.

[`argpartition`](maxframe.tensor.argpartition.md#maxframe.tensor.argpartition)
: Indirect partial sort.

### Notes

See sort for notes on the different sorting algorithms.

### Examples

One dimensional tensor:

```pycon
>>> import maxframe.tensor as mt
>>> x = mt.array([3, 1, 2])
>>> mt.argsort(x).execute()
array([1, 2, 0])
```

Two-dimensional tensor:

```pycon
>>> x = mt.array([[0, 3], [2, 2]])
>>> x.execute()
array([[0, 3],
       [2, 2]])
```

```pycon
>>> ind = mt.argsort(x, axis=0)  # sorts along first axis (down)
>>> ind.execute()
array([[0, 1],
       [1, 0]])
#>>> mt.take_along_axis(x, ind, axis=0).execute()  # same as np.sort(x, axis=0)
#array([[0, 2],
#       [2, 3]])
```

```pycon
>>> ind = mt.argsort(x, axis=1)  # sorts along last axis (across)
>>> ind.execute()
array([[0, 1],
       [0, 1]])
#>>> mt.take_along_axis(x, ind, axis=1).execute()  # same as np.sort(x, axis=1)
#array([[0, 3],
#       [2, 2]])
```

Indices of the sorted elements of a N-dimensional array:

```pycon
>>> ind = mt.unravel_index(mt.argsort(x, axis=None), x.shape)
>>> ind.execute()
(array([0, 1, 1, 0]), array([0, 0, 1, 1]))
>>> x[ind].execute()  # same as np.sort(x, axis=None)
array([0, 2, 2, 3])
```

Sorting with keys:

```pycon
>>> x = mt.array([(1, 0), (0, 1)], dtype=[('x', '<i4'), ('y', '<i4')])
>>> x.execute()
array([(1, 0), (0, 1)],
      dtype=[('x', '<i4'), ('y', '<i4')])
```

```pycon
>>> mt.argsort(x, order=('x','y')).execute()
array([1, 0])
```

```pycon
>>> mt.argsort(x, order=('y','x')).execute()
array([0, 1])
```
