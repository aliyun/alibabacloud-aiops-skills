# maxframe.tensor.deg2rad

### maxframe.tensor.deg2rad(x, out=None, where=None, \*\*kwargs)

Convert angles from degrees to radians.

* **Parameters:**
  * **x** (*array_like*) – Angles in degrees.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **y** – The corresponding angle in radians.
* **Return type:**
  Tensor

#### SEE ALSO
[`rad2deg`](maxframe.tensor.rad2deg.md#maxframe.tensor.rad2deg)
: Convert angles from radians to degrees.

`unwrap`
: Remove large jumps in angle by wrapping.

### Notes

`deg2rad(x)` is `x * pi / 180`.

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.deg2rad(180).execute()
3.1415926535897931
```
