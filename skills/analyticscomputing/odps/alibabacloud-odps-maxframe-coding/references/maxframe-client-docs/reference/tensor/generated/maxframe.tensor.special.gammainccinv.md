# maxframe.tensor.special.gammainccinv

### maxframe.tensor.special.gammainccinv(a, b, \*\*kwargs)

Inverse of the regularized upper incomplete gamma function.

Given an input $y$ between 0 and 1, returns $x$ such
that $y = Q(a, x)$. Here $Q$ is the regularized upper
incomplete gamma function; see gammaincc. This is well-defined
because the upper incomplete gamma function is monotonic as can
be seen from its definition in [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf).

* **Parameters:**
  * **a** (*array_like*) – Positive parameter
  * **y** (*array_like*) – Argument between 0 and 1, inclusive
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the inverse of the upper incomplete gamma function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gammaincc`](maxframe.tensor.special.gammaincc.md#maxframe.tensor.special.gammaincc)
: regularized upper incomplete gamma function

[`gammainc`](maxframe.tensor.special.gammainc.md#maxframe.tensor.special.gammainc)
: regularized lower incomplete gamma function

[`gammaincinv`](maxframe.tensor.special.gammaincinv.md#maxframe.tensor.special.gammaincinv)
: inverse of the regularized lower incomplete gamma function

### References
