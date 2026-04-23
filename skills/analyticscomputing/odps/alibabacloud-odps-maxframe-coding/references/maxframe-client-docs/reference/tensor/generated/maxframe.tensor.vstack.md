# maxframe.tensor.vstack

### maxframe.tensor.vstack(tup)

Stack tensors in sequence vertically (row wise).

This is equivalent to concatenation along the first axis after 1-D tensors
of shape (N,) have been reshaped to (1,N). Rebuilds tensors divided by
vsplit.

This function makes most sense for tensors with up to 3 dimensions. For
instance, for pixel-data with a height (first axis), width (second axis),
and r/g/b channels (third axis). The functions concatenate, stack and
block provide more general stacking and concatenation operations.

* **Parameters:**
  **tup** (*sequence* *of* *tensors*) – The tensors must have the same shape along all but the first axis.
  1-D tensors must have the same length.
* **Returns:**
  **stacked** – The tensor formed by stacking the given tensors, will be at least 2-D.
* **Return type:**
  Tensor

#### SEE ALSO
`stack`
: Join a sequence of tensors along a new axis.

[`concatenate`](maxframe.tensor.concatenate.md#maxframe.tensor.concatenate)
: Join a sequence of tensors along an existing axis.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([1, 2, 3])
>>> b = mt.array([2, 3, 4])
>>> mt.vstack((a,b)).execute()
array([[1, 2, 3],
       [2, 3, 4]])
```

```pycon
>>> a = mt.array([[1], [2], [3]])
>>> b = mt.array([[2], [3], [4]])
>>> mt.vstack((a,b)).execute()
array([[1],
       [2],
       [3],
       [2],
       [3],
       [4]])
```
