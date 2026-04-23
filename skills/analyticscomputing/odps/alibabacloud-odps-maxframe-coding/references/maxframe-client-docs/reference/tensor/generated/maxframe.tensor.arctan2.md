# maxframe.tensor.arctan2

### maxframe.tensor.arctan2(x1, x2, out=None, where=None, \*\*kwargs)

Element-wise arc tangent of `x1/x2` choosing the quadrant correctly.

The quadrant (i.e., branch) is chosen so that `arctan2(x1, x2)` is
the signed angle in radians between the ray ending at the origin and
passing through the point (1,0), and the ray ending at the origin and
passing through the point (x2, x1).  (Note the role reversal: the
“y-coordinate” is the first function parameter, the “x-coordinate”
is the second.)  By IEEE convention, this function is defined for
x2 = +/-0 and for either or both of x1 and x2 = +/-inf (see
Notes for specific values).

This function is not defined for complex-valued arguments; for the
so-called argument of complex values, use angle.

* **Parameters:**
  * **x1** (*array_like* *,* *real-valued*) – y-coordinates.
  * **x2** (*array_like* *,* *real-valued*) – x-coordinates. x2 must be broadcastable to match the shape of
    x1 or vice versa.
  * **out** (*Tensor* *,* *None* *, or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *Tensor and None* *,* *optional*) – A location into which the result is stored. If provided, it must have
    a shape that the inputs broadcast to. If not provided or None,
    a freshly-allocated tensor is returned. A tuple (possible only as a
    keyword argument) must have length equal to the number of outputs.
  * **where** (*array_like* *,* *optional*) – Values of True indicate to calculate the ufunc at that position, values
    of False indicate to leave the value in the output alone.
  * **\*\*kwargs**
* **Returns:**
  **angle** – Array of angles in radians, in the range `[-pi, pi]`.
* **Return type:**
  Tensor

#### SEE ALSO
[`arctan`](maxframe.tensor.arctan.md#maxframe.tensor.arctan), [`tan`](maxframe.tensor.tan.md#maxframe.tensor.tan), [`angle`](maxframe.tensor.angle.md#maxframe.tensor.angle)

### Notes

*arctan2* is identical to the atan2 function of the underlying
C library.  The following special values are defined in the C
standard: <sup>[1](#id2)</sup>

| x1     | x2     | arctan2(x1,x2)   |
|--------|--------|------------------|
| +/- 0  | +0     | +/- 0            |
| +/- 0  | -0     | +/- pi           |
| > 0    | +/-inf | +0 / +pi         |
| < 0    | +/-inf | -0 / -pi         |
| +/-inf | +inf   | +/- (pi/4)       |
| +/-inf | -inf   | +/- (3\*pi/4)    |

Note that +0 and -0 are distinct floating point numbers, as are +inf
and -inf.

### References

* <a id='id2'>**[1]**</a> ISO/IEC standard 9899:1999, “Programming language C.”

### Examples

Consider four points in different quadrants:
>>> import maxframe.tensor as mt

```pycon
>>> x = mt.array([-1, +1, +1, -1])
>>> y = mt.array([-1, -1, +1, +1])
>>> (mt.arctan2(y, x) * 180 / mt.pi).execute()
array([-135.,  -45.,   45.,  135.])
```

Note the order of the parameters. arctan2 is defined also when x2 = 0
and at several other special points, obtaining values in
the range `[-pi, pi]`:

```pycon
>>> mt.arctan2([1., -1.], [0., 0.]).execute()
array([ 1.57079633, -1.57079633])
>>> mt.arctan2([0., 0., mt.inf], [+0., -0., mt.inf]).execute()
array([ 0.        ,  3.14159265,  0.78539816])
```
