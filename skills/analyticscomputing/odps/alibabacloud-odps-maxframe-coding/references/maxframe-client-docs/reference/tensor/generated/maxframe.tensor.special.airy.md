# maxframe.tensor.special.airy

### maxframe.tensor.special.airy(z, out=None)

Airy functions and their derivatives.

* **Parameters:**
  * **z** (*array_like*) – Real or complex argument.
  * **out** ([*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of* *ndarray* *,* *optional*) – Optional output arrays for the function values
* **Returns:**
  **Ai, Aip, Bi, Bip** – Airy functions Ai and Bi, and their derivatives Aip and Bip.
* **Return type:**
  4-tuple of scalar or ndarray

#### SEE ALSO
[`airye`](maxframe.tensor.special.airye.md#maxframe.tensor.special.airye)
: exponentially scaled Airy functions.

### Notes

The Airy functions Ai and Bi are two independent solutions of

$$
y''(x) = x y(x).

$$

For real z in [-10, 10], the computation is carried out by calling
the Cephes <sup>[1](#id3)</sup> airy routine, which uses power series summation
for small z and rational minimax approximations for large z.

Outside this range, the AMOS <sup>[2](#id4)</sup> zairy and zbiry routines are
employed.  They are computed using power series for $|z| < 1$ and
the following relations to modified Bessel functions for larger z
(where $t \equiv 2 z^{3/2}/3$):

$$
Ai(z) = \frac{1}{\pi \sqrt{3}} K_{1/3}(t)

Ai'(z) = -\frac{z}{\pi \sqrt{3}} K_{2/3}(t)

Bi(z) = \sqrt{\frac{z}{3}} \left(I_{-1/3}(t) + I_{1/3}(t) \right)

Bi'(z) = \frac{z}{\sqrt{3}} \left(I_{-2/3}(t) + I_{2/3}(t)\right)
$$

### References

* <a id='id3'>**[1]**</a> Cephes Mathematical Functions Library, [http://www.netlib.org/cephes/](http://www.netlib.org/cephes/)
* <a id='id4'>**[2]**</a> Donald E. Amos, “AMOS, A Portable Package for Bessel Functions of a Complex Argument and Nonnegative Order”, [http://netlib.org/amos/](http://netlib.org/amos/)
