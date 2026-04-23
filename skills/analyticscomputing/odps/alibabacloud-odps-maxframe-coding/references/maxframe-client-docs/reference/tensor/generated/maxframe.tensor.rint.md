# maxframe.tensor.rint

### maxframe.tensor.rint(x, out=None, where=None, \*\*kwargs)

Round elements of the tensor to the nearest integer.

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
  **out** – Output array is same shape and type as x.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`ceil`](maxframe.tensor.ceil.md#maxframe.tensor.ceil), [`floor`](maxframe.tensor.floor.md#maxframe.tensor.floor), [`trunc`](maxframe.tensor.trunc.md#maxframe.tensor.trunc)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> a = mt.array([-1.7, -1.5, -0.2, 0.2, 1.5, 1.7, 2.0])
>>> mt.rint(a).execute()
array([-2., -2., -0.,  0.,  2.,  2.,  2.])
```
