# maxframe.tensor.special.iv

### maxframe.tensor.special.iv(v, z, out=None)

Modified Bessel function of the first kind of real order.

* **Parameters:**
  * **v** (*array_like*) – Order. If z is of real type and negative, v must be integer
    valued.
  * **z** (*array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float) *or* [*complex*](https://docs.python.org/3/library/functions.html#complex)) – Argument.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the modified Bessel function.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`ive`](maxframe.tensor.special.ive.md#maxframe.tensor.special.ive)
: This function with leading exponential behavior stripped off.

`i0`
: Faster version of this function for order 0.

`i1`
: Faster version of this function for order 1.

### Notes

For real z and $v \in [-50, 50]$, the evaluation is carried out
using Temme’s method <sup>[1](#id3)</sup>.  For larger orders, uniform asymptotic
expansions are applied.

For complex z and positive v, the AMOS <sup>[2](#id4)</sup> zbesi routine is
called. It uses a power series for small z, the asymptotic expansion
for large abs(z), the Miller algorithm normalized by the Wronskian
and a Neumann series for intermediate magnitudes, and the uniform
asymptotic expansions for $I_v(z)$ and $J_v(z)$ for large
orders. Backward recurrence is used to generate sequences or reduce
orders when necessary.

The calculations above are done in the right half plane and continued
into the left half plane by the formula,

$$
I_v(z \exp(\pm\imath\pi)) = \exp(\pm\pi v) I_v(z)

$$

(valid when the real part of z is positive).  For negative v, the
formula

$$
I_{-v}(z) = I_v(z) + \frac{2}{\pi} \sin(\pi v) K_v(z)

$$

is used, where $K_v(z)$ is the modified Bessel function of the
second kind, evaluated using the AMOS routine zbesk.

### References

* <a id='id3'>**[1]**</a> Temme, Journal of Computational Physics, vol 21, 343 (1976)
* <a id='id4'>**[2]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
