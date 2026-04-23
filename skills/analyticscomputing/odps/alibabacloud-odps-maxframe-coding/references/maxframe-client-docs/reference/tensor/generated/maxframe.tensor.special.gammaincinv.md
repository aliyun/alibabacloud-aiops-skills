# maxframe.tensor.special.gammaincinv

### maxframe.tensor.special.gammaincinv(a, b, \*\*kwargs)

Inverse to the regularized lower incomplete gamma function.

Given an input $y$ between 0 and 1, returns $x$ such
that $y = P(a, x)$. Here $P$ is the regularized lower
incomplete gamma function; see gammainc. This is well-defined
because the lower incomplete gamma function is monotonic as can be
seen from its definition in [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf).

* **Parameters:**
  * **a** (*array_like*) – Positive parameter
  * **y** (*array_like*) – Parameter between 0 and 1, inclusive
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the inverse of the lower incomplete gamma function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gammainc`](maxframe.tensor.special.gammainc.md#maxframe.tensor.special.gammainc)
: regularized lower incomplete gamma function

[`gammaincc`](maxframe.tensor.special.gammaincc.md#maxframe.tensor.special.gammaincc)
: regularized upper incomplete gamma function

[`gammainccinv`](maxframe.tensor.special.gammainccinv.md#maxframe.tensor.special.gammainccinv)
: inverse of the regularized upper incomplete gamma function

### References
