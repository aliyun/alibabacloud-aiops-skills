# maxframe.tensor.special.loggamma

### maxframe.tensor.special.loggamma(z, out=None)

Principal branch of the logarithm of the gamma function.

Defined to be $\log(\Gamma(x))$ for $x > 0$ and
extended to the complex plane by analytic continuation. The
function has a single branch cut on the negative real axis.

* **Parameters:**
  * **z** (*array_like*) – Values in the complex plane at which to compute `loggamma`
  * **out** (*ndarray* *,* *optional*) – Output array for computed values of `loggamma`
* **Returns:**
  **loggamma** – Values of `loggamma` at z.
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gammaln`](maxframe.tensor.special.gammaln.md#maxframe.tensor.special.gammaln)
: logarithm of the absolute value of the gamma function

[`gammasgn`](maxframe.tensor.special.gammasgn.md#maxframe.tensor.special.gammasgn)
: sign of the gamma function

### Notes

It is not generally true that $\log\Gamma(z) =
\log(\Gamma(z))$, though the real parts of the functions do
agree. The benefit of not defining loggamma as
$\log(\Gamma(z))$ is that the latter function has a
complicated branch cut structure whereas loggamma is analytic
except for on the negative real axis.

The identities

$$
\exp(\log\Gamma(z)) &= \Gamma(z) \\
\log\Gamma(z + 1) &= \log(z) + \log\Gamma(z)

$$

make loggamma useful for working in complex logspace.

On the real line loggamma is related to gammaln via
`exp(loggamma(x + 0j)) = gammasgn(x)*exp(gammaln(x))`, up to
rounding error.

The implementation here is based on [[hare1997]](#hare1997).

### References
