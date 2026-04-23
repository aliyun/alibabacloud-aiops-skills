# maxframe.tensor.atleast_1d

### maxframe.tensor.atleast_1d(\*tensors)

Convert inputs to tensors with at least one dimension.

Scalar inputs are converted to 1-dimensional tensors, whilst
higher-dimensional inputs are preserved.

* **Parameters:**
  * **tensors1** (*array_like*) – One or more input tensors.
  * **tensors2** (*array_like*) – One or more input tensors.
  * **...** (*array_like*) – One or more input tensors.
* **Returns:**
  **ret** – An tensor, or list of tensors, each with `a.ndim >= 1`.
  Copies are made only if necessary.
* **Return type:**
  Tensor

#### SEE ALSO
[`atleast_2d`](maxframe.tensor.atleast_2d.md#maxframe.tensor.atleast_2d), [`atleast_3d`](maxframe.tensor.atleast_3d.md#maxframe.tensor.atleast_3d)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.atleast_1d(1.0).execute()
array([ 1.])
```

```pycon
>>> x = mt.arange(9.0).reshape(3,3)
>>> mt.atleast_1d(x).execute()
array([[ 0.,  1.,  2.],
       [ 3.,  4.,  5.],
       [ 6.,  7.,  8.]])
>>> mt.atleast_1d(x) is x
True
```

```pycon
>>> mt.atleast_1d(1, [3, 4]).execute()
[array([1]), array([3, 4])]
```
