# maxframe.tensor.special.rgamma

### maxframe.tensor.special.rgamma(z, out=None)

Reciprocal of the gamma function.

Defined as $1 / \Gamma(z)$, where $\Gamma$ is the
gamma function. For more on the gamma function see gamma.

* **Parameters:**
  * **z** (*array_like*) – Real or complex valued input
  * **out** (*ndarray* *,* *optional*) – Optional output array for the function results
* **Returns:**
  Function results
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`gamma`](maxframe.tensor.special.gamma.md#maxframe.tensor.special.gamma), [`gammaln`](maxframe.tensor.special.gammaln.md#maxframe.tensor.special.gammaln), [`loggamma`](maxframe.tensor.special.loggamma.md#maxframe.tensor.special.loggamma)

### Notes

The gamma function has no zeros and has simple poles at
nonpositive integers, so rgamma is an entire function with zeros
at the nonpositive integers. See the discussion in [[dlmf]](#dlmf) for
more details.

### References
