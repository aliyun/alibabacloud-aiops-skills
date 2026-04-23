# maxframe.tensor.cbrt

### maxframe.tensor.cbrt(x, out=None, where=None, \*\*kwargs)

Return the cube-root of an tensor, element-wise.

* **Parameters:**
  * **x** (*array_like*) – The values whose cube-roots are required.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – An tensor of the same shape as x, containing the cube
  cube-root of each element in x.
  If out was provided, y is a reference to it.
* **Return type:**
  Tensor

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.cbrt([1,8,27]).execute()
array([ 1.,  2.,  3.])
```
