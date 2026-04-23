# maxframe.tensor.argmin

### maxframe.tensor.argmin(a, axis=None, out=None)

Returns the indices of the minimum values along an axis.

* **Parameters:**
  * **a** (*array_like*) – Input tensor.
  * **axis** ([*int*](https://docs.python.org/3/library/functions.html#int) *,* *optional*) – By default, the index is into the flattened tensor, otherwise
    along the specified axis.
  * **out** (*Tensor* *,* *optional*) – If provided, the result will be inserted into this tensor. It should
    be of the appropriate shape and dtype.
* **Returns:**
  **index_array** – Tensor of indices into the tensor. It has the same shape as a.shape
  with the dimension along axis removed.
* **Return type:**
  Tensor of ints

#### SEE ALSO
`Tensor.argmin`, [`argmax`](maxframe.tensor.argmax.md#maxframe.tensor.argmax)

`amin`
: The minimum value along a given axis.

[`unravel_index`](maxframe.tensor.unravel_index.md#maxframe.tensor.unravel_index)
: Convert a flat index into an index tuple.

### Notes

In case of multiple occurrences of the minimum values, the indices
corresponding to the first occurrence are returned.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.arange(6).reshape(2,3)
>>> a.execute()
array([[0, 1, 2],
       [3, 4, 5]])
>>> mt.argmin(a).execute()
0
>>> mt.argmin(a, axis=0).execute()
array([0, 0, 0])
>>> mt.argmin(a, axis=1).execute()
array([0, 0])
```

Indices of the minimum elements of a N-dimensional tensor:

```pycon
>>> ind = mt.unravel_index(mt.argmin(a, axis=None), a.shape)
>>> ind.execute()
(0, 0)
>>> a[ind]
```

```pycon
>>> b = mt.arange(6)
>>> b[4] = 0
>>> b.execute()
array([0, 1, 2, 3, 0, 5])
>>> mt.argmin(b).execute()  # Only the first occurrence is returned.
0
```
