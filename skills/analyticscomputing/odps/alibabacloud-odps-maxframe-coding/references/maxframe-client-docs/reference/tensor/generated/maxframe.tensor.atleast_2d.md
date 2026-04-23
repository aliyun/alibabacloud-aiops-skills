# maxframe.tensor.atleast_2d

### maxframe.tensor.atleast_2d(\*tensors)

View inputs as tensors with at least two dimensions.

* **Parameters:**
  * **tensors1** (*array_like*) – One or more array-like sequences.  Non-tensor inputs are converted
    to tensors.  Tensors that already have two or more dimensions are
    preserved.
  * **tensors2** (*array_like*) – One or more array-like sequences.  Non-tensor inputs are converted
    to tensors.  Tensors that already have two or more dimensions are
    preserved.
  * **...** (*array_like*) – One or more array-like sequences.  Non-tensor inputs are converted
    to tensors.  Tensors that already have two or more dimensions are
    preserved.
* **Returns:**
  **res, res2, …** – A tensor, or list of tensors, each with `a.ndim >= 2`.
  Copies are avoided where possible, and views with two or more
  dimensions are returned.
* **Return type:**
  Tensor

#### SEE ALSO
[`atleast_1d`](maxframe.tensor.atleast_1d.md#maxframe.tensor.atleast_1d), [`atleast_3d`](maxframe.tensor.atleast_3d.md#maxframe.tensor.atleast_3d)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.atleast_2d(3.0).execute()
array([[ 3.]])
```

```pycon
>>> x = mt.arange(3.0)
>>> mt.atleast_2d(x).execute()
array([[ 0.,  1.,  2.]])
```

```pycon
>>> mt.atleast_2d(1, [1, 2], [[1, 2]]).execute()
[array([[1]]), array([[1, 2]]), array([[1, 2]])]
```
