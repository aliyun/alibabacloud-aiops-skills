# maxframe.tensor.logical_and

### maxframe.tensor.logical_and(x1, x2, out=None, where=None, \*\*kwargs)

Compute the truth value of x1 AND x2 element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Input tensors. x1 and x2 must be of the same shape.
  * **x2** (*array_like*) – Input tensors. x1 and x2 must be of the same shape.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – Boolean result with the same shape as x1 and x2 of the logical
  AND operation on corresponding elements of x1 and x2.
* **Return type:**
  Tensor or [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`logical_or`](maxframe.tensor.logical_or.md#maxframe.tensor.logical_or), [`logical_not`](maxframe.tensor.logical_not.md#maxframe.tensor.logical_not), [`logical_xor`](maxframe.tensor.logical_xor.md#maxframe.tensor.logical_xor), [`bitwise_and`](maxframe.tensor.bitwise_and.md#maxframe.tensor.bitwise_and)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.logical_and(True, False).execute()
False
>>> mt.logical_and([True, False], [False, False]).execute()
array([False, False])
```

```pycon
>>> x = mt.arange(5)
>>> mt.logical_and(x>1, x<4).execute()
array([False, False,  True,  True, False])
```
