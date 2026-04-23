# maxframe.tensor.special.elliprf

### maxframe.tensor.special.elliprf(x, y, z, \*\*kwargs)

Completely-symmetric elliptic integral of the first kind.

The function RF is defined as <sup>[1](#id3)</sup>

$$
R_{\mathrm{F}}(x, y, z) =
   \frac{1}{2} \int_0^{+\infty} [(t + x) (t + y) (t + z)]^{-1/2} dt
$$

* **Parameters:**
  * **x** (*array_like*) – Real or complex input parameters. x, y, or z can be any number in
    the complex plane cut along the negative real axis, but at most one of
    them can be zero.
  * **y** (*array_like*) – Real or complex input parameters. x, y, or z can be any number in
    the complex plane cut along the negative real axis, but at most one of
    them can be zero.
  * **z** (*array_like*) – Real or complex input parameters. x, y, or z can be any number in
    the complex plane cut along the negative real axis, but at most one of
    them can be zero.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **R** – Value of the integral. If all of x, y, and z are real, the return
  value is real. Otherwise, the return value is complex.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`elliprc`](maxframe.tensor.special.elliprc.md#maxframe.tensor.special.elliprc)
: Degenerate symmetric integral.

`elliprd`
: Symmetric elliptic integral of the second kind.

[`elliprg`](maxframe.tensor.special.elliprg.md#maxframe.tensor.special.elliprg)
: Completely-symmetric elliptic integral of the second kind.

[`elliprj`](maxframe.tensor.special.elliprj.md#maxframe.tensor.special.elliprj)
: Symmetric elliptic integral of the third kind.

### Notes

The code implements Carlson’s algorithm based on the duplication theorems
and series expansion up to the 7th order (cf.:
[https://dlmf.nist.gov/19.36.i](https://dlmf.nist.gov/19.36.i)) and the AGM algorithm for the complete
integral. <sup>[2](#id4)</sup>

### References

* <a id='id3'>**[1]**</a> B. C. Carlson, ed., Chapter 19 in “Digital Library of Mathematical Functions,” NIST, US Dept. of Commerce. [https://dlmf.nist.gov/19.16.E1](https://dlmf.nist.gov/19.16.E1)
* <a id='id4'>**[2]**</a> B. C. Carlson, “Numerical computation of real or complex elliptic integrals,” Numer. Algorithm, vol. 10, no. 1, pp. 13-26, 1995. [https://arxiv.org/abs/math/9409227](https://arxiv.org/abs/math/9409227) [https://doi.org/10.1007/BF02198293](https://doi.org/10.1007/BF02198293)
