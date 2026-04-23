# maxframe.tensor.special.elliprg

### maxframe.tensor.special.elliprg(x, y, z, \*\*kwargs)

Completely-symmetric elliptic integral of the second kind.

The function RG is defined as <sup>[1](#id4)</sup>

$$
R_{\mathrm{G}}(x, y, z) =
   \frac{1}{4} \int_0^{+\infty} [(t + x) (t + y) (t + z)]^{-1/2}
   \left(\frac{x}{t + x} + \frac{y}{t + y} + \frac{z}{t + z}\right) t
   dt
$$

* **Parameters:**
  * **x** (*array_like*) – Real or complex input parameters. x, y, or z can be any number in
    the complex plane cut along the negative real axis.
  * **y** (*array_like*) – Real or complex input parameters. x, y, or z can be any number in
    the complex plane cut along the negative real axis.
  * **z** (*array_like*) – Real or complex input parameters. x, y, or z can be any number in
    the complex plane cut along the negative real axis.
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

[`elliprf`](maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)
: Completely-symmetric elliptic integral of the first kind.

[`elliprj`](maxframe.tensor.special.elliprj.md#maxframe.tensor.special.elliprj)
: Symmetric elliptic integral of the third kind.

### Notes

The implementation uses the relation <sup>[1](#id4)</sup>

$$
2 R_{\mathrm{G}}(x, y, z) =
   z R_{\mathrm{F}}(x, y, z) -
   \frac{1}{3} (x - z) (y - z) R_{\mathrm{D}}(x, y, z) +
   \sqrt{\frac{x y}{z}}
$$

and the symmetry of x, y, z when at least one non-zero parameter can
be chosen as the pivot. When one of the arguments is close to zero, the AGM
method is applied instead. Other special cases are computed following Ref.
<sup>[2](#id5)</sup>

### References

* <a id='id4'>**[1]**</a> B. C. Carlson, “Numerical computation of real or complex elliptic integrals,” Numer. Algorithm, vol. 10, no. 1, pp. 13-26, 1995. [https://arxiv.org/abs/math/9409227](https://arxiv.org/abs/math/9409227) [https://doi.org/10.1007/BF02198293](https://doi.org/10.1007/BF02198293)
* <a id='id5'>**[2]**</a> B. C. Carlson, ed., Chapter 19 in “Digital Library of Mathematical Functions,” NIST, US Dept. of Commerce. [https://dlmf.nist.gov/19.16.E1](https://dlmf.nist.gov/19.16.E1) [https://dlmf.nist.gov/19.20.ii](https://dlmf.nist.gov/19.20.ii)
