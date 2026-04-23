# maxframe.tensor.nonzero

### maxframe.tensor.nonzero(a)

Return the indices of the elements that are non-zero.

Returns a tuple of tensors, one for each dimension of a,
containing the indices of the non-zero elements in that
dimension. The values in a are always tested and returned.
The corresponding non-zero
values can be obtained with:

```default
a[nonzero(a)]
```

To group the indices by element, rather than dimension, use:

```default
transpose(nonzero(a))
```

The result of this is always a 2-D array, with a row for
each non-zero element.

* **Parameters:**
  **a** (*array_like*) – Input tensor.
* **Returns:**
  **tuple_of_arrays** – Indices of elements that are non-zero.
* **Return type:**
  [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)

#### SEE ALSO
[`flatnonzero`](maxframe.tensor.flatnonzero.md#maxframe.tensor.flatnonzero)
: Return indices that are non-zero in the flattened version of the input tensor.

`Tensor.nonzero`
: Equivalent tensor method.

[`count_nonzero`](maxframe.tensor.count_nonzero.md#maxframe.tensor.count_nonzero)
: Counts the number of non-zero elements in the input tensor.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([[1,0,0], [0,2,0], [1,1,0]])
>>> x.execute()
array([[1, 0, 0],
       [0, 2, 0],
       [1, 1, 0]])
>>> mt.nonzero(x).execute()
(array([0, 1, 2, 2]), array([0, 1, 0, 1]))
```

```pycon
>>> x[mt.nonzero(x)].execute()
```

```pycon
>>> mt.transpose(mt.nonzero(x)).execute()
```

A common use for `nonzero` is to find the indices of an array, where
a condition is True.  Given an array a, the condition a > 3 is a
boolean array and since False is interpreted as 0, np.nonzero(a > 3)
yields the indices of the a where the condition is true.

```pycon
>>> a = mt.array([[1,2,3],[4,5,6],[7,8,9]])
>>> (a > 3).execute()
array([[False, False, False],
       [ True,  True,  True],
       [ True,  True,  True]])
>>> mt.nonzero(a > 3).execute()
(array([1, 1, 1, 2, 2, 2]), array([0, 1, 2, 0, 1, 2]))
```

The `nonzero` method of the boolean array can also be called.

```pycon
>>> (a > 3).nonzero().execute()
(array([1, 1, 1, 2, 2, 2]), array([0, 1, 2, 0, 1, 2]))
```
