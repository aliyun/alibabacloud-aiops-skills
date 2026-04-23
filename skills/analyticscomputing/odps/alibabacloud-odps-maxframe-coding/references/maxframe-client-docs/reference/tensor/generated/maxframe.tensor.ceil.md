# maxframe.tensor.ceil

### maxframe.tensor.ceil(x, out=None, where=None, \*\*kwargs)

Return the ceiling of the input, element-wise.

The ceil of the scalar x is the smallest integer i, such that
i >= x.  It is often denoted as $\lceil x \rceil$.

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
  **y** – The ceiling of each element in x, with float dtype.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor), [`trunc`](maxframe.tensor.trunc.md#maxframe.tensor.trunc), [`rint`](maxframe.tensor.rint.md#maxframe.tensor.rint)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([-1.7, -1.5, -0.2, 0.2, 1.5, 1.7, 2.0])
>>> mt.ceil(a).execute()
array([-1., -1., -0.,  1.,  2.,  2.,  2.])
```
