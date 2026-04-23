# maxframe.tensor.logical_xor

### maxframe.tensor.logical_xor(x1, x2, out=None, where=None, \*\*kwargs)

Compute the truth value of x1 XOR x2, element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Logical XOR is applied to the elements of x1 and x2.  They must
    be broadcastable to the same shape.
  * **x2** (*array_like*) – Logical XOR is applied to the elements of x1 and x2.  They must
    be broadcastable to the same shape.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – Boolean result of the logical XOR operation applied to the elements
  of x1 and x2; the shape is determined by whether or not
  broadcasting of one or both arrays was required.
* **Return type:**
  [bool](https://docs.python.org/3/library/functions.html#bool) or Tensor of [bool](https://docs.python.org/3/library/functions.html#bool)

#### SEE ALSO
[`logical_and`](maxframe.tensor.logical_and.md#maxframe.tensor.logical_and), [`logical_or`](maxframe.tensor.logical_or.md#maxframe.tensor.logical_or), [`logical_not`](maxframe.tensor.logical_not.md#maxframe.tensor.logical_not), [`bitwise_xor`](maxframe.tensor.bitwise_xor.md#maxframe.tensor.bitwise_xor)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.logical_xor(True, False).execute()
True
>>> mt.logical_xor([True, True, False, False], [True, False, True, False]).execute()
array([False,  True,  True, False])
```

```pycon
>>> x = mt.arange(5)
>>> mt.logical_xor(x < 1, x > 3).execute()
array([ True, False, False, False,  True])
```

Simple example showing support of broadcasting

```pycon
>>> mt.logical_xor(0, mt.eye(2)).execute()
array([[ True, False],
       [False,  True]])
```
