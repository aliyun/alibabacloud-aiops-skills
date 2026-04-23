# maxframe.tensor.special.ive

### maxframe.tensor.special.ive(v, z, out=None)

Exponentially scaled modified Bessel function of the first kind.

Defined as:

```default
ive(v, z) = iv(v, z) * exp(-abs(z.real))
```

For imaginary numbers without a real part, returns the unscaled
Bessel function of the first kind iv.

* **Parameters:**
  * **v** (*array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float)) – Order.
  * **z** (*array_like* *of* [*float*](https://docs.python.org/3/library/functions.html#float) *or* [*complex*](https://docs.python.org/3/library/functions.html#complex)) – Argument.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the exponentially scaled modified Bessel function.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`iv`](maxframe.tensor.special.iv.md#maxframe.tensor.special.iv)
: Modified Bessel function of the first kind

`i0e`
: Faster implementation of this function for order 0

`i1e`
: Faster implementation of this function for order 1

### Notes

For positive v, the AMOS <sup>[1](#id2)</sup> zbesi routine is called. It uses a
power series for small z, the asymptotic expansion for large
abs(z), the Miller algorithm normalized by the Wronskian and a
Neumann series for intermediate magnitudes, and the uniform asymptotic
expansions for $I_v(z)$ and $J_v(z)$ for large orders.
Backward recurrence is used to generate sequences or reduce orders when
necessary.

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

ive is useful for large arguments z: for these, iv easily overflows,
while ive does not due to the exponential scaling.

### References

* <a id='id2'>**[1]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
