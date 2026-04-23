# maxframe.tensor.special.yv

### maxframe.tensor.special.yv(v, z, out=None)

Bessel function of the second kind of real order and complex argument.

* **Parameters:**
  * **v** (*array_like*) – Order (float).
  * **z** (*array_like*) – Argument (float or complex).
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  **Y** – Value of the Bessel function of the second kind, $Y_v(x)$.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`yve`](maxframe.tensor.special.yve.md#maxframe.tensor.special.yve)
: $Y_v$ with leading exponential behavior stripped off.

`y0`
: faster implementation of this function for order 0

`y1`
: faster implementation of this function for order 1

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

### References

* <a id='id2'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
