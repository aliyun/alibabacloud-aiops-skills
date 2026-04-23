# maxframe.tensor.cosh

### maxframe.tensor.cosh(x, out=None, where=None, \*\*kwargs)

Hyperbolic cosine, element-wise.

Equivalent to `1/2 * (mt.exp(x) + mt.exp(-x))` and `mt.cos(1j*x)`.

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
  **out** – Output array of same shape as x.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.cosh(0).execute()
1.0
```

The hyperbolic cosine describes the shape of a hanging cable:

```pycon
>>> import matplotlib.pyplot as plt
>>> x = mt.linspace(-4, 4, 1000)
>>> plt.plot(x.execute(), mt.cosh(x).execute())
>>> plt.show()
```
