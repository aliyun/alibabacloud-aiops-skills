# maxframe.tensor.nextafter

### maxframe.tensor.nextafter(x1, x2, out=None, where=None, \*\*kwargs)

Return the next floating-point value after x1 towards x2, element-wise.

* **Parameters:**
  * **x1** (*array_like*) – Values to find the next representable value of.
  * **x2** (*array_like*) – The direction where to look for the next representable value of x1.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – The next representable values of x1 in the direction of x2.
* **Return type:**
  array_like

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> eps = mt.finfo(mt.float64).eps
>>> (mt.nextafter(1, 2) == eps + 1).execute()
True
>>> (mt.nextafter([1, 2], [2, 1]) == [eps + 1, 2 - eps]).execute()
array([ True,  True])
```
