# maxframe.tensor.absolute

### maxframe.tensor.absolute(x, out=None, where=None, \*\*kwargs)

Calculate the absolute value element-wise.

* **Parameters:**
  * **x** (*array_like*) – Input tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **absolute** – An tensor containing the absolute value of
  each element in x.  For complex input, `a + ib`, the
  absolute value is $\sqrt{ a^2 + b^2 }$.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> x = mt.array([-1.2, 1.2])
>>> mt.absolute(x).execute()
array([ 1.2,  1.2])
>>> mt.absolute(1.2 + 1j).execute()
1.5620499351813308
```
