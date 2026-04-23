# maxframe.tensor.special.ellipk

### maxframe.tensor.special.ellipk(x, \*\*kwargs)

Complete elliptic integral of the first kind.

This function is defined as

$$
K(m) = \int_0^{\pi/2} [1 - m \sin(t)^2]^{-1/2} dt

$$

* **Parameters:**
  * **m** (*array_like*) – The parameter of the elliptic integral.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **K** – Value of the elliptic integral.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`ellipkm1`](maxframe.tensor.special.ellipkm1.md#maxframe.tensor.special.ellipkm1)
: Complete elliptic integral of the first kind around m = 1

[`ellipkinc`](maxframe.tensor.special.ellipkinc.md#maxframe.tensor.special.ellipkinc)
: Incomplete elliptic integral of the first kind

[`ellipe`](maxframe.tensor.special.ellipe.md#maxframe.tensor.special.ellipe)
: Complete elliptic integral of the second kind

[`ellipeinc`](maxframe.tensor.special.ellipeinc.md#maxframe.tensor.special.ellipeinc)
: Incomplete elliptic integral of the second kind

[`elliprf`](maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)
: Completely-symmetric elliptic integral of the first kind.

### Notes

For more precision around point m = 1, use ellipkm1, which this
function calls.

The parameterization in terms of $m$ follows that of section
17.2 in <sup>[1](#id3)</sup>. Other parameterizations in terms of the
complementary parameter $1 - m$, modular angle
$\sin^2(\alpha) = m$, or modulus $k^2 = m$ are also
used, so be careful that you choose the correct parameter.

The Legendre K integral is related to Carlson’s symmetric R_F
function by <sup>[2](#id4)</sup>:

$$
K(m) = R_F(0, 1-k^2, 1) .

$$

### References

* <a id='id3'>**[1]**</a> Milton Abramowitz and Irene A. Stegun, eds. Handbook of Mathematical Functions with Formulas, Graphs, and Mathematical Tables. New York: Dover, 1972.
* <a id='id4'>**[2]**</a> NIST Digital Library of Mathematical Functions. [http://dlmf.nist.gov/](http://dlmf.nist.gov/), Release 1.0.28 of 2020-09-15. See Sec. 19.25(i) [https://dlmf.nist.gov/19.25#i](https://dlmf.nist.gov/19.25#i)
