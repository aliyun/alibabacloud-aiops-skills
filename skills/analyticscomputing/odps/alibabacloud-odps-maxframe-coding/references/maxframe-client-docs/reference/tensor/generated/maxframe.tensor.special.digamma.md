# maxframe.tensor.special.digamma

### maxframe.tensor.special.digamma(x, out=None, \*\*kwargs)

psi(z, out=None)

The digamma function.

The logarithmic derivative of the gamma function evaluated at `z`.

* **Parameters:**
  * **z** (*array_like*) – Real or complex argument.
  * **out** (*ndarray* *,* *optional*) – Array for the computed values of `psi`.
* **Returns:**
  **digamma** – Computed values of `psi`.
* **Return type:**
  scalar or ndarray

### Notes

For large values not close to the negative real axis, `psi` is
computed using the asymptotic series (5.11.2) from <sup>[1](#id5)</sup>. For small
arguments not close to the negative real axis, the recurrence
relation (5.5.2) from <sup>[1](#id5)</sup> is used until the argument is large
enough to use the asymptotic series. For values close to the
negative real axis, the reflection formula (5.5.4) from <sup>[1](#id5)</sup> is
used first. Note that `psi` has a family of zeros on the
negative real axis which occur between the poles at nonpositive
integers. Around the zeros the reflection formula suffers from
cancellation and the implementation loses precision. The sole
positive zero and the first negative zero, however, are handled
separately by precomputing series expansions using <sup>[2](#id6)</sup>, so the
function should maintain full accuracy around the origin.

### References

* <a id='id5'>**[1]**</a> NIST Digital Library of Mathematical Functions [https://dlmf.nist.gov/5](https://dlmf.nist.gov/5)
* <a id='id6'>**[2]**</a> Fredrik Johansson and others. “mpmath: a Python library for arbitrary-precision floating-point arithmetic” (Version 0.19) [http://mpmath.org/](http://mpmath.org/)
