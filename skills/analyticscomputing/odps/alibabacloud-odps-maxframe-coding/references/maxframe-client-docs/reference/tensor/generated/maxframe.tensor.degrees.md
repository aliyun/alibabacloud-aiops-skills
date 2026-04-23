# maxframe.tensor.degrees

### maxframe.tensor.degrees(x, out=None, where=None, \*\*kwargs)

Convert angles from radians to degrees.

* **Parameters:**
  * **x** (*array_like*) – Input tensor in radians.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The corresponding degree values; if out was supplied this is a
  reference to it.
* **Return type:**
  Tensor of floats

#### SEE ALSO
[`rad2deg`](maxframe.tensor.rad2deg.md#maxframe.tensor.rad2deg)
: equivalent function

### Examples

Convert a radian array to degrees

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> rad = mt.arange(12.)*mt.pi/6
>>> mt.degrees(rad).execute()
array([   0.,   30.,   60.,   90.,  120.,  150.,  180.,  210.,  240.,
        270.,  300.,  330.])
```

```pycon
>>> out = mt.zeros((rad.shape))
>>> r = mt.degrees(out)
>>> mt.all(r == out).execute()
True
```
