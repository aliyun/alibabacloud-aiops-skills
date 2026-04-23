# maxframe.tensor.argwhere

### maxframe.tensor.argwhere(a)

Find the indices of tensor elements that are non-zero, grouped by element.

* **Parameters:**
  **a** (*array_like*) – Input data.
* **Returns:**
  **index_tensor** – Indices of elements that are non-zero. Indices are grouped by element.
* **Return type:**
  Tensor

#### SEE ALSO
[`where`](maxframe.tensor.where.md#maxframe.tensor.where), [`nonzero`](maxframe.tensor.nonzero.md#maxframe.tensor.nonzero)

### Notes

`mt.argwhere(a)` is the same as `mt.transpose(mt.nonzero(a))`.

The output of `argwhere` is not suitable for indexing tensors.
For this purpose use `nonzero(a)` instead.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.arange(6).reshape(2,3)
>>> x.execute()
array([[0, 1, 2],
       [3, 4, 5]])
>>> mt.argwhere(x>1).execute()
array([[0, 2],
       [1, 0],
       [1, 1],
       [1, 2]])
```
