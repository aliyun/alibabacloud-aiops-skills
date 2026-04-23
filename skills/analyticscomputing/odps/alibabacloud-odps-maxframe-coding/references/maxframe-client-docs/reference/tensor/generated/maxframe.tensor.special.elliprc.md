# maxframe.tensor.special.elliprc

### maxframe.tensor.special.elliprc(x, y, \*\*kwargs)

Degenerate symmetric elliptic integral.

The function RC is defined as <sup>[1](#id3)</sup>

$$
R_{\mathrm{C}}(x, y) =
   \frac{1}{2} \int_0^{+\infty} (t + x)^{-1/2} (t + y)^{-1} dt
   = R_{\mathrm{F}}(x, y, y)
$$

* **Parameters:**
  * **x** (*array_like*) – Real or complex input parameters. x can be any number in the
    complex plane cut along the negative real axis. y must be non-zero.
  * **y** (*array_like*) – Real or complex input parameters. x can be any number in the
    complex plane cut along the negative real axis. y must be non-zero.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **R** – Value of the integral. If y is real and negative, the Cauchy
  principal value is returned. If both of x and y are real, the
  return value is real. Otherwise, the return value is complex.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`elliprf`](maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)
: Completely-symmetric elliptic integral of the first kind.

`elliprd`
: Symmetric elliptic integral of the second kind.

[`elliprg`](maxframe.tensor.special.elliprg.md#maxframe.tensor.special.elliprg)
: Completely-symmetric elliptic integral of the second kind.

[`elliprj`](maxframe.tensor.special.elliprj.md#maxframe.tensor.special.elliprj)
: Symmetric elliptic integral of the third kind.

### Notes

RC is a degenerate case of the symmetric integral RF: `elliprc(x, y) ==
elliprf(x, y, y)`. It is an elementary function rather than an elliptic
integral.

The code implements Carlson’s algorithm based on the duplication theorems
and series expansion up to the 7th order. <sup>[2](#id4)</sup>

### References

* <a id='id3'>**[1]**</a> B. C. Carlson, ed., Chapter 19 in “Digital Library of Mathematical Functions,” NIST, US Dept. of Commerce. [https://dlmf.nist.gov/19.16.E6](https://dlmf.nist.gov/19.16.E6)
* <a id='id4'>**[2]**</a> B. C. Carlson, “Numerical computation of real or complex elliptic integrals,” Numer. Algorithm, vol. 10, no. 1, pp. 13-26, 1995. [https://arxiv.org/abs/math/9409227](https://arxiv.org/abs/math/9409227) [https://doi.org/10.1007/BF02198293](https://doi.org/10.1007/BF02198293)
