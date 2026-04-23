# maxframe.tensor.trunc

### maxframe.tensor.trunc(x, out=None, where=None, \*\*kwargs)

Return the truncated value of the input, element-wise.

The truncated value of the scalar x is the nearest integer i which
is closer to zero than x is. In short, the fractional part of the
signed number x is discarded.

* **Parameters:**
  * **x** (*array_like*) – Input data.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The truncated value of each element in x.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`ceil`](maxframe.tensor.ceil.md#maxframe.tensor.ceil), [`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor), [`rint`](maxframe.tensor.rint.md#maxframe.tensor.rint)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([-1.7, -1.5, -0.2, 0.2, 1.5, 1.7, 2.0])
>>> mt.trunc(a).execute()
array([-1., -1., -0.,  0.,  1.,  1.,  2.])
```
