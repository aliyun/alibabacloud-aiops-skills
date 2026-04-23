# maxframe.tensor.unique

### maxframe.tensor.unique(ar, return_index=False, return_inverse=False, return_counts=False, axis=None, method='auto', aggregate_size=None, sort=True, use_na_sentinel=False, na_position=None)

Find the unique elements of a tensor.

Returns the sorted unique elements of a tensor. There are three optional
outputs in addition to the unique elements:

* the indices of the input tensor that give the unique values
* the indices of the unique tensor that reconstruct the input tensor
* the number of times each unique value comes up in the input tensor

* **Parameters:**
  * **ar** (*array_like*) – Input tensor. Unless axis is specified, this will be flattened if it
    is not already 1-D.
  * **return_index** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, also return the indices of ar (along the specified axis,
    if provided, or in the flattened tensor) that result in the unique tensor.
  * **return_inverse** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, also return the indices of the unique tensor (for the specified
    axis, if provided) that can be used to reconstruct ar.
  * **return_counts** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – If True, also return the number of times each unique item appears
    in ar.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* *None* *,* *optional*) – The axis to operate on. If None, ar will be flattened. If an integer,
    the subarrays indexed by the given axis will be flattened and treated
    as the elements of a 1-D tensor with the dimension of the given axis,
    see the notes for more details.  Object tensors or structured tensors
    that contain objects are not supported if the axis kwarg is used. The
    default is None.
* **Returns:**
  * **unique** (*Tensor*) – The sorted unique values.
  * **unique_indices** (*Tensor, optional*) – The indices of the first occurrences of the unique values in the
    original tensor. Only provided if return_index is True.
  * **unique_inverse** (*Tensor, optional*) – The indices to reconstruct the original tensor from the
    unique tensor. Only provided if return_inverse is True.
  * **unique_counts** (*Tensor, optional*) – The number of times each of the unique values comes up in the
    original tensor. Only provided if return_counts is True.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.unique([1, 1, 2, 2, 3, 3]).execute()
array([1, 2, 3])
>>> a = mt.array([[1, 1], [2, 3]])
>>> mt.unique(a).execute()
array([1, 2, 3])
```

Return the unique rows of a 2D tensor

```pycon
>>> a = mt.array([[1, 0, 0], [1, 0, 0], [2, 3, 4]])
>>> mt.unique(a, axis=0).execute()
array([[1, 0, 0], [2, 3, 4]])
```

Return the indices of the original tensor that give the unique values:

```pycon
>>> a = mt.array(['a', 'b', 'b', 'c', 'a'])
>>> u, indices = mt.unique(a, return_index=True)
>>> u.execute()
array(['a', 'b', 'c'],
       dtype='|S1')
>>> indices.execute()
array([0, 1, 3])
>>> a[indices].execute()
array(['a', 'b', 'c'],
       dtype='|S1')
```

Reconstruct the input array from the unique values:

```pycon
>>> a = mt.array([1, 2, 6, 4, 2, 3, 2])
>>> u, indices = mt.unique(a, return_inverse=True)
>>> u.execute()
array([1, 2, 3, 4, 6])
>>> indices.execute()
array([0, 1, 4, 3, 1, 2, 1])
>>> u[indices].execute()
array([1, 2, 6, 4, 2, 3, 2])
```
