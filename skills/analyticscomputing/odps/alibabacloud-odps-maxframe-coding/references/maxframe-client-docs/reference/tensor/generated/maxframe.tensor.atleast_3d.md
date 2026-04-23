# maxframe.tensor.atleast_3d

### maxframe.tensor.atleast_3d(\*tensors)

View inputs as tensors with at least three dimensions.

* **Parameters:**
  * **tensors1** (*array_like*) – One or more tensor-like sequences.  Non-tensor inputs are converted to
    tensors.  Tensors that already have three or more dimensions are
    preserved.
  * **tensors2** (*array_like*) – One or more tensor-like sequences.  Non-tensor inputs are converted to
    tensors.  Tensors that already have three or more dimensions are
    preserved.
  * **...** (*array_like*) – One or more tensor-like sequences.  Non-tensor inputs are converted to
    tensors.  Tensors that already have three or more dimensions are
    preserved.
* **Returns:**
  **res1, res2, …** – A tensor, or list of tensors, each with `a.ndim >= 3`.  Copies are
  avoided where possible, and views with three or more dimensions are
  returned.  For example, a 1-D tensor of shape `(N,)` becomes a view
  of shape `(1, N, 1)`, and a 2-D tensor of shape `(M, N)` becomes a
  view of shape `(M, N, 1)`.
* **Return type:**
  Tensor

#### SEE ALSO
[`atleast_1d`](maxframe.tensor.atleast_1d.md#maxframe.tensor.atleast_1d), [`atleast_2d`](maxframe.tensor.atleast_2d.md#maxframe.tensor.atleast_2d)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.atleast_3d(3.0).execute()
array([[[ 3.]]])
```

```pycon
>>> x = mt.arange(3.0)
>>> mt.atleast_3d(x).shape
(1, 3, 1)
```

```pycon
>>> x = mt.arange(12.0).reshape(4,3)
>>> mt.atleast_3d(x).shape
(4, 3, 1)
```

```pycon
>>> for arr in mt.atleast_3d([1, 2], [[1, 2]], [[[1, 2]]]).execute():
...     print(arr, arr.shape)
...
[[[1]
  [2]]] (1, 2, 1)
[[[1]
  [2]]] (1, 2, 1)
[[[1 2]]] (1, 1, 2)
```
