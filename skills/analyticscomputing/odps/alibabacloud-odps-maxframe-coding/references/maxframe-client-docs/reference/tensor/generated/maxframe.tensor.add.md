# maxframe.tensor.add

### maxframe.tensor.add(x1, x2, out=None, where=None, \*\*kwargs)

Add arguments element-wise.

* **Parameters:**
  * **x1** (*array_like*) – The tensors to be added.  If `x1.shape != x2.shape`, they must be
    broadcastable to a common shape (which may be the shape of one or
    the other).
  * **x2** (*array_like*) – The tensors to be added.  If `x1.shape != x2.shape`, they must be
    broadcastable to a common shape (which may be the shape of one or
    the other).
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **add** – The sum of x1 and x2, element-wise.  Returns a scalar if
  both  x1 and x2 are scalars.
* **Return type:**
  Tensor or scalar

### Notes

Equivalent to x1 + x2 in terms of tensor broadcasting.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.add(1.0, 4.0).execute()
5.0
>>> x1 = mt.arange(9.0).reshape((3, 3))
>>> x2 = mt.arange(3.0)
>>> mt.add(x1, x2).execute()
array([[  0.,   2.,   4.],
       [  3.,   5.,   7.],
       [  6.,   8.,  10.]])
```
