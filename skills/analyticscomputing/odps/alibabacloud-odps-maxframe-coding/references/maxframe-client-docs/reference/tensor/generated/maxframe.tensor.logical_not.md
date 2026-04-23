# maxframe.tensor.logical_not

### maxframe.tensor.logical_not(x, out=None, where=None, \*\*kwargs)

Compute the truth value of NOT x element-wise.

* **Parameters:**
  * **x** (*array_like*) – Logical NOT is applied to the elements of x.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – Boolean result with the same shape as x of the NOT operation
  on elements of x.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool) or Tensor of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`logical_and`](maxframe.tensor.logical_and.md#maxframe.tensor.logical_and), [`logical_or`](maxframe.tensor.logical_or.md#maxframe.tensor.logical_or), [`logical_xor`](maxframe.tensor.logical_xor.md#maxframe.tensor.logical_xor)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.logical_not(3).execute()
False
>>> mt.logical_not([True, False, 0, 1]).execute()
array([False,  True,  True, False])
```

```pycon
>>> x = mt.arange(5)
>>> mt.logical_not(x<3).execute()
array([False, False, False,  True,  True])
```
