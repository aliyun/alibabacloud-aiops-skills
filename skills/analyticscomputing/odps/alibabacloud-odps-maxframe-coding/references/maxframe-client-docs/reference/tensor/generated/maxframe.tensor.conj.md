# maxframe.tensor.conj

### maxframe.tensor.conj(x, out=None, where=None, \*\*kwargs)

Return the complex conjugate, element-wise.

The complex conjugate of a complex number is obtained by changing the
sign of its imaginary part.

* **Parameters:**
  * **x** (*array_like*) – Input value.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The complex conjugate of x, with same dtype as y.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.conjugate(1+2j).execute()
(1-2j)
```

```pycon
>>> x = mt.eye(2) + 1j * mt.eye(2)
>>> mt.conjugate(x).execute()
array([[ 1.-1.j,  0.-0.j],
       [ 0.-0.j,  1.-1.j]])
```
