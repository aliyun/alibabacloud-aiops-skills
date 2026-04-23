# maxframe.tensor.multiply

### maxframe.tensor.multiply(x1, x2, out=None, where=None, \*\*kwargs)

Multiply arguments element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Input arrays to be multiplied.
  * **x2** (*array_like*) – Input arrays to be multiplied.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The product of x1 and x2, element-wise. Returns a scalar if
  both  x1 and x2 are scalars.
* **Return type:**
  Tensor

### Notes

Equivalent to x1 \* x2 in terms of array broadcasting.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.multiply(2.0, 4.0).execute()
8.0
```

```pycon
>>> x1 = mt.arange(9.0).reshape((3, 3))
>>> x2 = mt.arange(3.0)
>>> mt.multiply(x1, x2).execute()
array([[  0.,   1.,   4.],
       [  0.,   4.,  10.],
       [  0.,   7.,  16.]])
```
