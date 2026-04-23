# maxframe.tensor.argpartition

### maxframe.tensor.argpartition(a, kth, axis=-1, kind='introselect', order=None, \*\*kw)

Perform an indirect partition along the given axis using the
algorithm specified by the kind keyword. It returns an array of
indices of the same shape as a that index data along the given
axis in partitioned order.

#### Versionadded
Added in version 1.8.0.

* **Parameters:**
  * **a** (*array_like*) – Tensor to sort.
  * **kth** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *sequence* *of* *ints*) – Element index to partition by. The k-th element will be in its
    final sorted position and all smaller elements will be moved
    before it and all larger elements behind it. The order all
    elements in the partitions is undefined. If provided with a
    sequence of k-th it will partition all of them into their sorted
    position at once.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None* *,* *optional*) – Axis along which to sort. The default is -1 (the last axis). If
    None, the flattened tensor is used.
  * **kind** ( *{'introselect'}* *,* *optional*) – Selection algorithm. Default is ‘introselect’
  * **order** ([*str*](https://docs.python.org/3/library/stdtypes.html#str) *or* [*list*](https://docs.python.org/3/library/stdtypes.html#list) *of* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – When a is a tensor with fields defined, this argument
    specifies which fields to compare first, second, etc. A single
    field can be specified as a string, and not all fields need be
    specified, but unspecified fields will still be used, in the
    order in which they come up in the dtype, to break ties.
* **Returns:**
  **index_tensor** – Tensor of indices that partition a along the specified axis.
  If a is one-dimensional, `a[index_tensor]` yields a partitioned a.
  More generally, `np.take_along_axis(a, index_tensor, axis=a)` always
  yields the partitioned a, irrespective of dimensionality.
* **Return type:**
  Tensor, [int](https://docs.python.org/3/library/functions.html#int)

#### SEE ALSO
[`partition`](maxframe.tensor.partition.md#maxframe.tensor.partition)
: Describes partition algorithms used.

`Tensor.partition`
: Inplace partition.

[`argsort`](maxframe.tensor.argsort.md#maxframe.tensor.argsort)
: Full indirect sort

### Notes

See partition for notes on the different selection algorithms.

### Examples

One dimensional tensor:

```pycon
>>> import maxframe.tensor as mt
>>> x = mt.array([3, 4, 2, 1])
>>> x[mt.argpartition(x, 3)].execute()
array([2, 1, 3, 4])
>>> x[mt.argpartition(x, (1, 3))].execute()
array([1, 2, 3, 4])
```

```pycon
>>> x = [3, 4, 2, 1]
>>> mt.array(x)[mt.argpartition(x, 3)].execute()
array([2, 1, 3, 4])
```
