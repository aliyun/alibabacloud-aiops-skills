# maxframe.tensor.exp2

### maxframe.tensor.exp2(x, out=None, where=None, \*\*kwargs)

Calculate 2\*\*p for all p in the input tensor.

* **Parameters:**
  * **x** (*array_like*) – Input values.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – Element-wise 2 to the power x.
* **Return type:**
  Tensor

#### SEE ALSO
[`power`](maxframe.tensor.power.md#maxframe.tensor.power)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.exp2([2, 3]).execute()
array([ 4.,  8.])
```
