# maxframe.tensor.partition

### maxframe.tensor.partition(a, kth, axis=-1, kind='introselect', order=None, \*\*kw)

Return a partitioned copy of a tensor.

Creates a copy of the tensor with its elements rearranged in such a
way that the value of the element in k-th position is in the
position it would be in a sorted tensor. All elements smaller than
the k-th element are moved before this element and all equal or
greater are moved behind it. The ordering of the elements in the two
partitions is undefined.

* **Parameters:**
  * **a** (*array_like*) – Tensor to be sorted.
  * **kth** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *ints*) – Element index to partition by. The k-th value of the element
    will be in its final sorted position and all smaller elements
    will be moved before it and all equal or greater elements behind
    it. The order of all elements in the partitions is undefined. If
    provided with a sequence of k-th it will partition all elements
    indexed by k-th  of them into their sorted position at once.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None* *,* *optional*) – Axis along which to sort. If None, the tensor is flattened before
    sorting. The default is -1, which sorts along the last axis.
  * **kind** ( *{'introselect'}* *,* *optional*) – Selection algorithm. Default is ‘introselect’.
  * **order** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – When a is a tensor with fields defined, this argument
    specifies which fields to compare first, second, etc.  A single
    field can be specified as a string.  Not all fields need be
    specified, but unspecified fields will still be used, in the
    order in which they come up in the dtype, to break ties.
* **Returns:**
  **partitioned_tensor** – Tensor of the same type and shape as a.
* **Return type:**
  Tensor

#### SEE ALSO
`Tensor.partition`
: Method to sort a tensor in-place.

[`argpartition`](maxframe.tensor.argpartition.md#maxframe.tensor.argpartition)
: Indirect partition.

[`sort`](maxframe.tensor.sort.md#maxframe.tensor.sort)
: Full sorting

### Notes

The various selection algorithms are characterized by their average
speed, worst case performance, work space size, and whether they are
stable. A stable sort keeps items with the same key in the same
relative order. The available algorithms have the following
properties:

| kind          |   speed | worst case   |   work space | stable   |
|---------------|---------|--------------|--------------|----------|
| ‘introselect’ |       1 | O(n)         |            0 | no       |

All the partition algorithms make temporary copies of the data when
partitioning along any but the last axis.  Consequently,
partitioning along the last axis is faster and uses less space than
partitioning along any other axis.

The sort order for complex numbers is lexicographic. If both the
real and imaginary parts are non-nan then the order is determined by
the real parts except when they are equal, in which case the order
is determined by the imaginary parts.

### Examples

```pycon
>>> import maxframe.tensor as mt
>>> a = mt.array([3, 4, 2, 1])
>>> mt.partition(a, 3).execute()
array([2, 1, 3, 4])
```

```pycon
>>> mt.partition(a, (1, 3)).execute()
array([1, 2, 3, 4])
```
