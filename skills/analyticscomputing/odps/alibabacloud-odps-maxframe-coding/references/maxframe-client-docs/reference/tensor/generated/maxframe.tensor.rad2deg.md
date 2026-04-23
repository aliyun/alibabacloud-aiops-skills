# maxframe.tensor.rad2deg

### maxframe.tensor.rad2deg(x, out=None, where=None, \*\*kwargs)

Convert angles from radians to degrees.

* **Parameters:**
  * **x** (*array_like*) – Angle in radians.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The corresponding angle in degrees.
* **Return type:**
  Tensor

#### SEE ALSO
[`deg2rad`](maxframe.tensor.deg2rad.md#maxframe.tensor.deg2rad)
: Convert angles from degrees to radians.

### Notes

rad2deg(x) is `180 * x / pi`.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.rad2deg(mt.pi/2).execute()
90.0
```
