# maxframe.tensor.angle

### maxframe.tensor.angle(z, deg=False, \*\*kwargs)

Return the angle of the complex argument.

* **Parameters:**
  * **z** (*array_like*) – A complex number or sequence of complex numbers.
  * **deg** ([*bool*](https://docs.python.org/3/library/functions.html#bool) *,* *optional*) – Return angle in degrees if True, radians if False (default).
* **Returns:**
  **angle** – The counterclockwise angle from the positive real axis on
  the complex plane, with dtype as numpy.float64.
* **Return type:**
  Tensor or scalar

#### SEE ALSO
[`arctan2`](maxframe.tensor.arctan2.md#maxframe.tensor.arctan2), [`absolute`](maxframe.tensor.absolute.md#maxframe.tensor.absolute)

### Examples

```pycon
>>> import maxframe.tensor as mt
```

```pycon
>>> mt.angle([1.0, 1.0j, 1+1j]).execute()               # in radians
array([ 0.        ,  1.57079633,  0.78539816])
>>> mt.angle(1+1j, deg=True).execute()                  # in degrees
45.0
```
