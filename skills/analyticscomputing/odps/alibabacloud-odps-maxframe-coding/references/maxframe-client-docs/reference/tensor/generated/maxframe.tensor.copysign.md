# maxframe.tensor.copysign

### maxframe.tensor.copysign(x1, x2, out=None, where=None, \*\*kwargs)

Change the sign of x1 to that of x2, element-wise.

If both arguments are arrays or sequences, they have to be of the same
length. If x2 is a scalar, its sign will be copied to all elements of
x1.

* **Parameters:**
  * **x1** (*array_like*) – Values to change the sign of.
  * **x2** (*array_like*) – The sign of x2 is copied to x1.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – The values of x1 with the sign of x2.
* **Return type:**
  array_like

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.copysign(1.3, -1).execute()
-1.3
>>> (1/mt.copysign(0, 1)).execute()
inf
>>> (1/mt.copysign(0, -1)).execute()
-inf
```

```pycon
>>> mt.copysign([-1, 0, 1], -1.1).execute()
array([-1., -0., -1.])
>>> mt.copysign([-1, 0, 1], mt.arange(3)-1).execute()
array([-1.,  0.,  1.])
```
