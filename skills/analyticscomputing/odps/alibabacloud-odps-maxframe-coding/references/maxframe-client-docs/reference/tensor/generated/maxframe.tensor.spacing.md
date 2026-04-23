# maxframe.tensor.spacing

### maxframe.tensor.spacing(x, out=None, where=None, \*\*kwargs)

Return the distance between x and the nearest adjacent number.

* **Parameters:**
  * **x** (*array_like*) – Values to find the spacing of.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **out** – The spacing of values of x1.
* **Return type:**
  array_like

### Notes

It can be considered as a generalization of EPS:
`spacing(mt.float64(1)) == mt.finfo(mt.float64).eps`, and there
should not be any representable number between `x + spacing(x)` and
x for any finite x.

Spacing of +- inf and NaN is NaN.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> (mt.spacing(1) == mt.finfo(mt.float64).eps).execute()
True
```
