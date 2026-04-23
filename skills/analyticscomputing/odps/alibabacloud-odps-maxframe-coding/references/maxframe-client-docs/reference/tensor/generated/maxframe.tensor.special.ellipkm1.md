# maxframe.tensor.special.ellipkm1

### maxframe.tensor.special.ellipkm1(x, \*\*kwargs)

Complete elliptic integral of the first kind around m = 1

This function is defined as

$$
K(p) = \int_0^{\pi/2} [1 - m \sin(t)^2]^{-1/2} dt

$$

where m = 1 - p.

* **Parameters:**
  * **p** (*array_like*) – Defines the parameter of the elliptic integral as m = 1 - p.
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  **K** – Value of the elliptic integral.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`ellipk`](maxframe.tensor.special.ellipk.md#maxframe.tensor.special.ellipk)
: Complete elliptic integral of the first kind

[`ellipkinc`](maxframe.tensor.special.ellipkinc.md#maxframe.tensor.special.ellipkinc)
: Incomplete elliptic integral of the first kind

[`ellipe`](maxframe.tensor.special.ellipe.md#maxframe.tensor.special.ellipe)
: Complete elliptic integral of the second kind

[`ellipeinc`](maxframe.tensor.special.ellipeinc.md#maxframe.tensor.special.ellipeinc)
: Incomplete elliptic integral of the second kind

[`elliprf`](maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)
: Completely-symmetric elliptic integral of the first kind.

### Notes

Wrapper for the Cephes <sup>[1](#id2)</sup> routine ellpk.

For p <= 1, computation uses the approximation,

$$
K(p) \approx P(p) - \log(p) Q(p),

$$

where $P$ and $Q$ are tenth-order polynomials.  The
argument p is used internally rather than m so that the logarithmic
singularity at m = 1 will be shifted to the origin; this preserves
maximum accuracy.  For p > 1, the identity

$$
K(p) = K(1/p)/\sqrt(p)

$$

is used.

### References

* <a id='id2'>**[1]**</a> Cephes Mathematical Functions Library, [http://www.netlib.org/cephes/](http://www.netlib.org/cephes/)
