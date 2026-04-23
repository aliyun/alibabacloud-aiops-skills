# maxframe.tensor.special.ellipeinc

### maxframe.tensor.special.ellipeinc(phi, m, \*\*kwargs)

Incomplete elliptic integral of the second kind

This function is defined as

$$
E(\phi, m) = \int_0^{\phi} [1 - m \sin(t)^2]^{1/2} dt

$$

* **Parameters:**
  * **phi** (*array_like*) – amplitude of the elliptic integral.
  * **m** (*array_like*) – parameter of the elliptic integral.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **E** – Value of the elliptic integral.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`ellipkm1`](maxframe.tensor.special.ellipkm1.md#maxframe.tensor.special.ellipkm1)
: Complete elliptic integral of the first kind, near m = 1

[`ellipk`](maxframe.tensor.special.ellipk.md#maxframe.tensor.special.ellipk)
: Complete elliptic integral of the first kind

[`ellipkinc`](maxframe.tensor.special.ellipkinc.md#maxframe.tensor.special.ellipkinc)
: Incomplete elliptic integral of the first kind

[`ellipe`](maxframe.tensor.special.ellipe.md#maxframe.tensor.special.ellipe)
: Complete elliptic integral of the second kind

`elliprd`
: Symmetric elliptic integral of the second kind.

[`elliprf`](maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)
: Completely-symmetric elliptic integral of the first kind.

[`elliprg`](maxframe.tensor.special.elliprg.md#maxframe.tensor.special.elliprg)
: Completely-symmetric elliptic integral of the second kind.

### Notes

Wrapper for the Cephes <sup>[1](#id4)</sup> routine ellie.

Computation uses arithmetic-geometric means algorithm.

The parameterization in terms of $m$ follows that of section
17.2 in <sup>[2](#id5)</sup>. Other parameterizations in terms of the
complementary parameter $1 - m$, modular angle
$\sin^2(\alpha) = m$, or modulus $k^2 = m$ are also
used, so be careful that you choose the correct parameter.

The Legendre E incomplete integral can be related to combinations
of Carlson’s symmetric integrals R_D, R_F, and R_G in multiple
ways <sup>[3](#id6)</sup>. For example, with $c = \csc^2\phi$,

$$
E(\phi, m) = R_F(c-1, c-k^2, c)
  - \frac{1}{3} k^2 R_D(c-1, c-k^2, c) .

$$

### References

* <a id='id4'>**[1]**</a> Cephes Mathematical Functions Library, [http://www.netlib.org/cephes/](http://www.netlib.org/cephes/)
* <a id='id5'>**[2]**</a> Milton Abramowitz and Irene A. Stegun, eds. Handbook of Mathematical Functions with Formulas, Graphs, and Mathematical Tables. New York: Dover, 1972.
* <a id='id6'>**[3]**</a> NIST Digital Library of Mathematical Functions. [http://dlmf.nist.gov/](http://dlmf.nist.gov/), Release 1.0.28 of 2020-09-15. See Sec. 19.25(i) [https://dlmf.nist.gov/19.25#i](https://dlmf.nist.gov/19.25#i)
