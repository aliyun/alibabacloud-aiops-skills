# maxframe.tensor.special.betaincinv

### maxframe.tensor.special.betaincinv(a, b, y, out=None, \*\*kwargs)

Inverse of the regularized incomplete beta function.

Computes $x$ such that:

$$
y = I_x(a, b) = \frac{\Gamma(a+b)}{\Gamma(a)\Gamma(b)}
\int_0^x t^{a-1}(1-t)^{b-1}dt,
$$

where $I_x$ is the normalized incomplete beta function betainc
and $\Gamma$ is the gamma function <sup>[1](#id2)</sup>.

* **Parameters:**
  * **a** (*array_like*) – Positive, real-valued parameters
  * **b** (*array_like*) – Positive, real-valued parameters
  * **y** (*array_like*) – Real-valued input
  * **out** (*ndarray* *,* *optional*) – Optional output array for function values
* **Returns:**
  Value of the inverse of the regularized incomplete beta function
* **Return type:**
  scalar or ndarray

#### SEE ALSO
[`betainc`](maxframe.tensor.special.betainc.md#maxframe.tensor.special.betainc)
: regularized incomplete beta function

[`gamma`](maxframe.tensor.special.gamma.md#maxframe.tensor.special.gamma)
: gamma function

### References

* <a id='id2'>**[1]**</a> NIST Digital Library of Mathematical Functions [https://dlmf.nist.gov/8.17](https://dlmf.nist.gov/8.17)
