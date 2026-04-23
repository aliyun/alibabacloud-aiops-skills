# maxframe.tensor.negative

### maxframe.tensor.negative(x, out=None, where=None, \*\*kwargs)

Numerical negative, element-wise.

* **Parameters:**
  * **x** (*array_like* *or* *scalar*) – Input tensor.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs** – For other keyword-only arguments, see the
    [ufunc docs](https://numpy.org/doc/stable/reference/ufuncs.html#ufuncs-kwargs).
* **Returns:**
  **y** – Returned array or scalar: y = -x.
* **Return type:**
  Tensor or scalar

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.negative([1.,-1.]).execute()
array([-1.,  1.])
```
