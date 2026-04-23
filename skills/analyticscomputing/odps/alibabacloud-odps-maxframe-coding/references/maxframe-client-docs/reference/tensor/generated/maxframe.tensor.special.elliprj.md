# maxframe.tensor.special.elliprj

### maxframe.tensor.special.elliprj(x, y, z, p, \*\*kwargs)

Symmetric elliptic integral of the third kind.

The function RJ is defined as <sup>[1](#id10)</sup>

$$
R_{\mathrm{J}}(x, y, z, p) =
   \frac{3}{2} \int_0^{+\infty} [(t + x) (t + y) (t + z)]^{-1/2}
   (t + p)^{-1} dt
$$

#### WARNING
This function should be considered experimental when the inputs are
unbalanced.  Check correctness with another independent implementation.

* **Parameters:**
  * **x** (*array_like*) – Real or complex input parameters. x, y, or z are numbers in
    the complex plane cut along the negative real axis (subject to further
    constraints, see Notes), and at most one of them can be zero. p must
    be non-zero.
  * **y** (*array_like*) – Real or complex input parameters. x, y, or z are numbers in
    the complex plane cut along the negative real axis (subject to further
    constraints, see Notes), and at most one of them can be zero. p must
    be non-zero.
  * **z** (*array_like*) – Real or complex input parameters. x, y, or z are numbers in
    the complex plane cut along the negative real axis (subject to further
    constraints, see Notes), and at most one of them can be zero. p must
    be non-zero.
  * **p** (*array_like*) – Real or complex input parameters. x, y, or z are numbers in
    the complex plane cut along the negative real axis (subject to further
    constraints, see Notes), and at most one of them can be zero. p must
    be non-zero.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **R** – Value of the integral. If all of x, y, z, and p are real, the
  return value is real. Otherwise, the return value is complex.

  If p is real and negative, while x, y, and z are real,
  non-negative, and at most one of them is zero, the Cauchy principal
  value is returned. <sup>[1](#id10)</sup> <sup>[2](#id11)</sup>
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`elliprc`](maxframe.tensor.special.elliprc.md#maxframe.tensor.special.elliprc)
: Degenerate symmetric integral.

`elliprd`
: Symmetric elliptic integral of the second kind.

[`elliprf`](maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)
: Completely-symmetric elliptic integral of the first kind.

[`elliprg`](maxframe.tensor.special.elliprg.md#maxframe.tensor.special.elliprg)
: Completely-symmetric elliptic integral of the second kind.

### Notes

The code implements Carlson’s algorithm based on the duplication theorems
and series expansion up to the 7th order. <sup>[3](#id12)</sup> The algorithm is slightly
different from its earlier incarnation as it appears in <sup>[1](#id10)</sup>, in that the
call to elliprc (or `atan`/`atanh`, see <sup>[4](#id13)</sup>) is no longer needed in
the inner loop. Asymptotic approximations are used where arguments differ
widely in the order of magnitude. <sup>[5](#id14)</sup>

The input values are subject to certain sufficient but not necessary
constraints when input arguments are complex. Notably, `x`, `y`, and
`z` must have non-negative real parts, unless two of them are
non-negative and complex-conjugates to each other while the other is a real
non-negative number. <sup>[1](#id10)</sup> If the inputs do not satisfy the sufficient
condition described in Ref. <sup>[1](#id10)</sup> they are rejected outright with the output
set to NaN.

In the case where one of `x`, `y`, and `z` is equal to `p`, the
function `elliprd` should be preferred because of its less restrictive
domain.

### References

* <a id='id10'>**[1]**</a> B. C. Carlson, “Numerical computation of real or complex elliptic integrals,” Numer. Algorithm, vol. 10, no. 1, pp. 13-26, 1995. [https://arxiv.org/abs/math/9409227](https://arxiv.org/abs/math/9409227) [https://doi.org/10.1007/BF02198293](https://doi.org/10.1007/BF02198293)
* <a id='id11'>**[2]**</a> B. C. Carlson, ed., Chapter 19 in “Digital Library of Mathematical Functions,” NIST, US Dept. of Commerce. [https://dlmf.nist.gov/19.20.iii](https://dlmf.nist.gov/19.20.iii)
* <a id='id12'>**[3]**</a> B. C. Carlson, J. FitzSimmons, “Reduction Theorems for Elliptic Integrands with the Square Root of Two Quadratic Factors,” J. Comput. Appl. Math., vol. 118, nos. 1-2, pp. 71-85, 2000. [https://doi.org/10.1016/S0377-0427(00)00282-X](https://doi.org/10.1016/S0377-0427(00)00282-X)
* <a id='id13'>**[4]**</a> F. Johansson, “Numerical Evaluation of Elliptic Functions, Elliptic Integrals and Modular Forms,” in J. Blumlein, C. Schneider, P. Paule, eds., “Elliptic Integrals, Elliptic Functions and Modular Forms in Quantum Field Theory,” pp. 269-293, 2019 (Cham, Switzerland: Springer Nature Switzerland) [https://arxiv.org/abs/1806.06725](https://arxiv.org/abs/1806.06725) [https://doi.org/10.1007/978-3-030-04480-0](https://doi.org/10.1007/978-3-030-04480-0)
* <a id='id14'>**[5]**</a> B. C. Carlson, J. L. Gustafson, “Asymptotic Approximations for Symmetric Elliptic Integrals,” SIAM J. Math. Anls., vol. 25, no. 2, pp. 288-303, 1994. [https://arxiv.org/abs/math/9310223](https://arxiv.org/abs/math/9310223) [https://doi.org/10.1137/S0036141092228477](https://doi.org/10.1137/S0036141092228477)
