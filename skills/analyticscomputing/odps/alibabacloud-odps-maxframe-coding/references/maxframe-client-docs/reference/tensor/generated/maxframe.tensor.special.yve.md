# maxframe.tensor.special.yve

### maxframe.tensor.special.yve(v, z, out=None)

Exponentially scaled Bessel function of the second kind of real order.

Returns the exponentially scaled Bessel function of the second
kind of real order v at complex z:

```default
yve(v, z) = yv(v, z) * exp(-abs(z.imag))
```

* **Parameters:**
  * **v** (*array_like*) – Order (float).
  * **z** (*array_like*) – Argument (float or complex).
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  **Y** – Value of the exponentially scaled Bessel function.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`yv`](maxframe.tensor.special.yv.md#maxframe.tensor.special.yv)
: Unscaled Bessel function of the second kind of real order.

### Notes

For positive v values, the computation is carried out using the
AMOS <sup>[1](#id2)</sup> zbesy routine, which exploits the connection to the Hankel
Bessel functions $H_v^{(1)}$ and $H_v^{(2)}$,

$$
Y_v(z) = \frac{1}{2\imath} (H_v^{(1)} - H_v^{(2)}).

$$

For negative v values the formula,

$$
Y_{-v}(z) = Y_v(z) \cos(\pi v) + J_v(z) \sin(\pi v)

$$

is used, where $J_v(z)$ is the Bessel function of the first kind,
computed using the AMOS routine zbesj.  Note that the second term is
exactly zero for integer v; to improve accuracy the second term is
explicitly omitted for v values such that v = floor(v).

Exponentially scaled Bessel functions are useful for large z:
for these, the unscaled Bessel functions can easily under-or overflow.

### References

* <a id='id2'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
