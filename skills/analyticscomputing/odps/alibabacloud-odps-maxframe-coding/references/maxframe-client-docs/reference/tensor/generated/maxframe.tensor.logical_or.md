# maxframe.tensor.logical_or

### maxframe.tensor.logical_or(x1, x2, out=None, where=None, \*\*kwargs)

Compute the truth value of x1 OR x2 element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Logical OR is applied to the elements of x1 and x2.
    They have to be of the same shape.
  * **x2** (*array_like*) – Logical OR is applied to the elements of x1 and x2.
    They have to be of the same shape.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – Boolean result with the same shape as x1 and x2 of the logical
  OR operation on elements of x1 and x2.
* **Return type:**
  Tensor or [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`logical_and`](maxframe.tensor.logical_and.md#maxframe.tensor.logical_and), [`logical_not`](maxframe.tensor.logical_not.md#maxframe.tensor.logical_not), [`logical_xor`](maxframe.tensor.logical_xor.md#maxframe.tensor.logical_xor), [`bitwise_or`](maxframe.tensor.bitwise_or.md#maxframe.tensor.bitwise_or)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.logical_or(True, False).execute()
True
>>> mt.logical_or([True, False], [False, False]).execute()
array([ True, False])
```

```pycon
>>> x = mt.arange(5)
>>> mt.logical_or(x < 1, x > 3).execute()
array([ True, False, False, False,  True])
```
