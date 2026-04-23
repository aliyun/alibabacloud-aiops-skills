# maxframe.tensor.special.gammaincc

### maxframe.tensor.special.gammaincc(a, b, \*\*kwargs)

Regularized lower incomplete gamma function.

It is defined as

$$
P(a, x) = \frac{1}{\Gamma(a)} \int_0^x t^{a - 1}e^{-t} dt
$$

for $a > 0$ and $x \geq 0$. See [[dlmf]](maxframe.tensor.special.rgamma.md#dlmf) for details.

* **Parameters:**
  * **a** (*array_like*) – Positive parameter
  * **x** (*array_like*) – Nonnegative argument
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function values
* **Returns:**
  Values of the lower incomplete gamma function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gammaincc`](#maxframe.tensor.special.gammaincc)
: regularized upper incomplete gamma function

[`gammaincinv`](maxframe.tensor.special.gammaincinv.md#maxframe.tensor.special.gammaincinv)
: inverse of the regularized lower incomplete gamma function

[`gammainccinv`](maxframe.tensor.special.gammainccinv.md#maxframe.tensor.special.gammainccinv)
: inverse of the regularized upper incomplete gamma function

### Notes

The function satisfies the relation `gammainc(a, x) +
gammaincc(a, x) = 1` where gammaincc is the regularized upper
incomplete gamma function.

The implementation largely follows that of [[boost]](#boost).

### References
